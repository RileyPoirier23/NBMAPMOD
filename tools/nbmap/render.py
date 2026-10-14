"""Render WorldEd base + vegetation bitmaps (1 px = 1 tile) from OSM features.

Output: build/bmp/chunk_<cx>_<cy>.png and chunk_<cx>_<cy>_veg.png, each
CHUNK_CELLS*300 px square, positioned at cell (cx, cy). Plus build/world.json with
the list of active cells and chunk placements used by the other generators.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import config, noise
from .config import C, V, CELL, CHUNK_CELLS
from .osm import Feature, OSMData, lines, polygons

S = CELL * CHUNK_CELLS

LANDUSE_BASE = {
    ("landuse", "residential"): "grass_medium",
    ("landuse", "commercial"): "grass_medium",
    ("landuse", "retail"): "grass_medium",
    ("landuse", "industrial"): "grass_light",
    ("landuse", "farmyard"): "dirt",
    ("landuse", "farmland"): "crop_rows",
    ("landuse", "orchard"): "grass_light",
    ("landuse", "meadow"): "grass_light",
    ("landuse", "grass"): "grass_light",
    ("landuse", "cemetery"): "grass_light",
    ("landuse", "forest"): "grass_dark",
    ("landuse", "quarry"): "dirt_gravel",
    ("landuse", "construction"): "dirt",
    ("landuse", "brownfield"): "dirt",
    ("landuse", "landfill"): "dirt",
    ("landuse", "railway"): "dirt_gravel",
    ("natural", "wood"): "grass_dark",
    ("natural", "scrub"): "grass_dark",
    ("natural", "grassland"): "grass_light",
    ("natural", "heath"): "grass_light",
    ("natural", "wetland"): "mud",
    ("natural", "mud"): "mud",
    ("natural", "sand"): "sand",
    ("natural", "beach"): "sand",
    ("natural", "bare_rock"): "dirt_gravel",
    ("natural", "scree"): "dirt_gravel",
    ("leisure", "park"): "grass_light",
    ("leisure", "garden"): "grass_light",
    ("leisure", "golf_course"): "grass_light",
    ("leisure", "pitch"): "grass_light",
    ("leisure", "playground"): "sand",
    ("leisure", "recreation_ground"): "grass_light",
    ("leisure", "track"): "dirt_gravel",
    ("amenity", "parking"): "asphalt_medium",
    ("amenity", "school"): "grass_medium",
    ("amenity", "hospital"): "grass_medium",
    ("highway", "pedestrian"): "concrete",
    ("man_made", "pier"): "concrete",
    ("man_made", "wastewater_plant"): "concrete",
}
WATER_TAGS = {("natural", "water"), ("waterway", "riverbank"), ("landuse", "reservoir"), ("landuse", "basin"), ("leisure", "swimming_pool")}
FOREST_TAGS = {("landuse", "forest"), ("natural", "wood")}
URBAN_LANDUSE = {"residential", "commercial", "retail", "industrial"}


def rgb(name: str) -> tuple[int, int, int]:
    return C[name] if name in C else V[name]


class Chunk:
    def __init__(self, cx: int, cy: int):
        self.cx, self.cy = cx, cy
        self.ox, self.oy = cx * CELL, cy * CELL
        self.base = np.zeros((S, S, 3), np.uint8)
        self.veg = np.zeros((S, S, 3), np.uint8)
        self.masks: dict[str, np.ndarray] = {}

    def _rel(self, geom_coords):
        return [(x - self.ox, y - self.oy) for x, y in geom_coords]

    def poly_mask(self, feats: list[Feature], buffer: float = 0.0) -> np.ndarray:
        img = Image.new("L", (S, S), 0)
        d = ImageDraw.Draw(img)
        for f in feats:
            g = f.geom.buffer(buffer) if buffer else f.geom
            for p in polygons(g):
                d.polygon(self._rel(p.exterior.coords), fill=255)
                for ring in p.interiors:
                    d.polygon(self._rel(ring.coords), fill=0)
        return np.asarray(img) > 0

    def line_mask(self, items: list[tuple[Feature, int]]) -> np.ndarray:
        """Exact rasterisation of a line of width w tiles (shapely buffer, round caps)."""
        img = Image.new("L", (S, S), 0)
        d = ImageDraw.Draw(img)
        for f, w in items:
            for ln in lines(f.geom):
                if len(ln.coords) < 2:
                    continue
                if w <= 1:
                    d.line(self._rel(ln.coords), fill=255, width=1)
                    continue
                for p in polygons(ln.buffer(w / 2.0, quad_segs=4)):
                    d.polygon(self._rel(p.exterior.coords), fill=255)
                    for ring in p.interiors:
                        d.polygon(self._rel(ring.coords), fill=0)
        return np.asarray(img) > 0

    def point_mask(self, feats: list[Feature], r: float = 1.0) -> np.ndarray:
        img = Image.new("L", (S, S), 0)
        d = ImageDraw.Draw(img)
        for f in feats:
            x, y = f.geom.x - self.ox, f.geom.y - self.oy
            d.ellipse([x - r, y - r, x + r, y + r], fill=255)
        return np.asarray(img) > 0

    def paint(self, layer: np.ndarray, mask: np.ndarray, color: tuple[int, int, int]):
        layer[mask] = color


def erode(mask: np.ndarray, n: int) -> np.ndarray:
    img = Image.fromarray(mask.astype(np.uint8) * 255)
    for _ in range(n):
        img = img.filter(ImageFilter.MinFilter(3))
    return np.asarray(img) > 0


def dilate(mask: np.ndarray, n: int) -> np.ndarray:
    img = Image.fromarray(mask.astype(np.uint8) * 255)
    for _ in range(n):
        img = img.filter(ImageFilter.MaxFilter(3))
    return np.asarray(img) > 0


def _road_params(f: Feature):
    hw = f.tag("highway")
    p = config.ROADS.get(hw)
    if not p:
        return None
    p = dict(p)
    if f.tag("surface") in config.UNPAVED_SURFACES and hw not in ("track", "path"):
        p["color"] = "dirt_gravel"
        p["sidewalk"] = False
    lanes = f.tag("lanes")
    if lanes and str(lanes).isdigit():
        p["width"] = max(p["width"], int(lanes) * 3 + 1)
    if f.tag("sidewalk") in ("both", "left", "right", "yes"):
        p["sidewalk"] = True
    if f.tag("sidewalk") in ("no", "none"):
        p["sidewalk"] = False
    return p


ROAD_ORDER = ["steps", "path", "bridleway", "footway", "cycleway", "track", "service", "living_street", "pedestrian",
              "residential", "unclassified", "tertiary_link", "tertiary", "secondary_link", "secondary",
              "primary_link", "primary", "trunk_link", "trunk", "motorway_link", "motorway"]


class World:
    def __init__(self, data: OSMData, out: Path):
        self.data = data
        self.out = out
        self.feats = data.features
        self.b = np.array([f.bounds for f in self.feats]) if self.feats else np.zeros((0, 4))
        self.active = self._active_cells()

    # ------------------------------------------------------------------ cells
    def _active_cells(self) -> set[tuple[int, int]]:
        cells: set[tuple[int, int]] = set()
        for f in self.feats:
            hw = f.tag("highway")
            if "building" in f.tags or (hw and hw in config.ROADS and hw not in ("path", "footway", "steps", "bridleway", "cycleway")):
                x0, y0, x1, y1 = f.bounds
                for cx in range(int(x0 // CELL), int(x1 // CELL) + 1):
                    for cy in range(int(y0 // CELL), int(y1 // CELL) + 1):
                        cells.add((cx, cy))
        halo = max(a.halo_cells for a in config.AREAS)
        out = set(cells)
        for cx, cy in cells:
            for dx in range(-halo, halo + 1):
                for dy in range(-halo, halo + 1):
                    out.add((cx + dx, cy + dy))
        return {c for c in out if c[0] >= 0 and c[1] >= 0}

    def chunks(self) -> list[tuple[int, int]]:
        ch = {(cx // CHUNK_CELLS, cy // CHUNK_CELLS) for cx, cy in self.active}
        return sorted(ch)

    def in_window(self, ox, oy, w, h) -> list[Feature]:
        if not self.feats:
            return []
        sel = (self.b[:, 2] >= ox - 40) & (self.b[:, 0] <= ox + w + 40) & (self.b[:, 3] >= oy - 40) & (self.b[:, 1] <= oy + h + 40)
        return [self.feats[i] for i in np.nonzero(sel)[0]]

    # ------------------------------------------------------------------ rendering
    def render_chunk(self, kx: int, ky: int) -> dict:
        ch = Chunk(kx * CHUNK_CELLS, ky * CHUNK_CELLS)
        ox, oy = ch.ox, ch.oy
        feats = self.in_window(ox, oy, S, S)
        vcfg = config.VEG
        seed = vcfg["seed"]

        # --- base ground: three grass tones from noise
        n = noise.fbm(ox, oy, S, S, vcfg["noise_scale"] * 3, seed)
        ch.base[:] = C["grass_medium"]
        ch.base[n < 0.40] = C["grass_dark"]
        ch.base[n > 0.62] = C["grass_light"]

        area_feats = [f for f in feats if polygons(f.geom)]
        line_feats = [f for f in feats if lines(f.geom)]
        pt_feats = [f for f in feats if f.geom.geom_type == "Point"]

        # --- landuse fills (large areas first so small ones win)
        fills = []
        for f in area_feats:
            for (k, v), col in LANDUSE_BASE.items():
                if f.tag(k) == v:
                    fills.append((f.geom.area, f, col))
        fills.sort(key=lambda t: -t[0])
        for _, f, col in fills:
            ch.paint(ch.base, ch.poly_mask([f]), C[col])

        # farmland: crop rows (alternate 2-tile strips of ploughed dirt)
        farm = [f for f in area_feats if f.tag("landuse") == "farmland"]
        farm_mask = ch.poly_mask(farm) if farm else np.zeros((S, S), bool)
        if farm:
            rows = ((np.arange(S)[None, :] + ox) // 2) % 2 == 0
            ch.base[farm_mask & rows] = C["dirt"]
            ch.base[farm_mask & ~rows] = C["mud"]

        # --- water
        water = [f for f in area_feats if any(f.tag(k) == v for k, v in WATER_TAGS) or f.tag("water")]
        water_mask = ch.poly_mask(water) if water else np.zeros((S, S), bool)
        ww = [(f, config.WATERWAY_WIDTHS[f.tag("waterway")]) for f in line_feats if f.tag("waterway") in config.WATERWAY_WIDTHS]
        if ww:
            water_mask |= ch.line_mask(ww)
        ch.paint(ch.base, water_mask, C["water"])

        # --- railways (ballast; the rails themselves need tile objects placed in TileZed)
        rail = [(f, 4) for f in line_feats if f.tag("railway") in ("rail", "disused", "abandoned", "light_rail")]
        rail_mask = ch.line_mask(rail) if rail else np.zeros((S, S), bool)
        ch.paint(ch.base, rail_mask, C["dirt_gravel"])

        # --- parking, pedestrian areas, piers already in fills.  Roads:
        roads = []
        for f in line_feats:
            p = _road_params(f)
            if p and f.tag("area") != "yes":
                roads.append((f, p))
        urban = ch.poly_mask([f for f in area_feats if f.tag("landuse") in URBAN_LANDUSE]) if area_feats else np.zeros((S, S), bool)
        order = {k: i for i, k in enumerate(ROAD_ORDER)}
        roads.sort(key=lambda t: order.get(t[0].tag("highway"), 0))
        clear_mask = np.zeros((S, S), bool)
        sidewalk_mask = np.zeros((S, S), bool)
        for f, p in roads:
            if p["sidewalk"]:
                sidewalk_mask |= ch.line_mask([(f, p["width"] + 2 * config.SIDEWALK_WIDTH)])
        near_buildings = ch.poly_mask([f for f in area_feats if "building" in f.tags], 25.0) if area_feats else np.zeros((S, S), bool)
        sidewalk_mask &= (urban | near_buildings)
        ch.paint(ch.base, sidewalk_mask & ~water_mask, C["concrete"])
        bridges = np.zeros((S, S), bool)
        road_mask = np.zeros((S, S), bool)
        for f, p in roads:
            if p["shoulder"]:
                sh = ch.line_mask([(f, p["width"] + 2 * p["shoulder_w"])])
                ch.paint(ch.base, sh & ~water_mask, C[p["shoulder"]])
                clear_mask |= ch.line_mask([(f, p["width"] + 2 * p["shoulder_w"] + 2 * p["clear"])])
            else:
                clear_mask |= ch.line_mask([(f, p["width"] + 2 * p["clear"])])
        for f, p in roads:
            m = ch.line_mask([(f, p["width"])])
            road_mask |= m
            ch.paint(ch.base, m, C[p["color"]])
            if f.tag("bridge"):
                bridges |= m
            if p["color"].startswith("asphalt"):  # the odd pothole on real roads
                pot = noise.white(ox, oy, S, S, seed + 11) < (0.0015 if f.tag("highway") in ("residential", "service", "unclassified") else 0.0004)
                ch.base[m & pot] = C["pothole_dark"]
        # water re-wins over roads except on bridges (bridge decks need TileZed objects anyway)
        ch.paint(ch.base, water_mask & ~bridges, C["water"])

        # --- buildings: ground under them stays grass; clear vegetation around them
        bld = [f for f in area_feats if "building" in f.tags]
        bld_mask = ch.poly_mask(bld) if bld else np.zeros((S, S), bool)
        clear_mask |= dilate(bld_mask, vcfg["building_clear"]) | water_mask | rail_mask | sidewalk_mask
        hard_mask = ch.poly_mask([f for f in area_feats if f.tag("amenity") == "parking" or f.tag("leisure") in ("pitch", "track", "playground") or f.tag("highway") == "pedestrian" or f.tag("man_made") == "pier"]) if area_feats else np.zeros((S, S), bool)
        clear_mask |= hard_mask

        # ================= vegetation ======================================
        veg = ch.veg
        nf = noise.fbm(ox, oy, S, S, vcfg["noise_scale"], seed + 1)
        rnd = noise.white(ox, oy, S, S, seed + 2)
        species = noise.fbm(ox, oy, S, S, 140.0, seed + 3)   # broad patches of softwood vs hardwood

        # forest
        forest_feats = [f for f in area_feats if any(f.tag(k) == v for k, v in FOREST_TAGS)]
        covered = np.zeros((S, S), bool)
        for leaf in ("needleleaved", "broadleaved", "mixed", None):
            fs = [f for f in forest_feats if f.tag("leaf_type") == leaf] if leaf else [f for f in forest_feats if f.tag("leaf_type") not in ("needleleaved", "broadleaved", "mixed")]
            if not fs:
                continue
            fm = ch.poly_mask(fs)
            covered |= fm
            interior = erode(fm, vcfg["forest_edge_tiles"])
            edge = fm & ~interior
            if leaf == "needleleaved":
                conif = np.ones((S, S), bool)
            elif leaf == "broadleaved":
                conif = np.zeros((S, S), bool)
            else:
                conif = species < vcfg["conifer_fraction"]
            dense = interior & (nf > vcfg["forest_dense_threshold"])
            gap = interior & (nf < vcfg["forest_gap_threshold"])
            mid = interior & ~dense & ~gap
            veg[dense & conif] = V["conifer_dense"]
            veg[dense & ~conif] = V["forest_dense"]
            veg[mid & conif] = V["conifer"]
            veg[mid & ~conif] = V["forest"]
            veg[gap & (rnd < 0.5)] = V["bushes"]
            veg[gap & (rnd >= 0.5)] = V["tall_grass"]
            # thinner, bushier edge
            veg[edge & (rnd < 0.45) & conif] = V["conifer"]
            veg[edge & (rnd < 0.45) & ~conif] = V["forest_light"]
            veg[edge & (rnd >= 0.45) & (rnd < 0.70)] = V["bushes"]
            veg[edge & (rnd >= 0.70) & (rnd < 0.85)] = V["tall_grass"]

        # scrub / heath / wetland / meadow / orchard
        def area_mask(pred):
            fs = [f for f in area_feats if pred(f)]
            return ch.poly_mask(fs) if fs else np.zeros((S, S), bool)

        scrub = area_mask(lambda f: f.tag("natural") in ("scrub", "heath"))
        veg[scrub & (nf > 0.5)] = V["shrubland"]
        veg[scrub & (nf <= 0.5) & (rnd < 0.6)] = V["bushes"]
        veg[scrub & (nf <= 0.5) & (rnd >= 0.6)] = V["bushes_sparse"]
        wet = area_mask(lambda f: f.tag("natural") == "wetland" or f.tag("wetland"))
        veg[wet & (nf > 0.3)] = V["wetland"]
        ch.base[wet & (nf <= 0.3)] = C["grass_dark"]
        veg[wet & (nf <= 0.3) & (rnd < 0.3)] = V["bushes"]
        veg[wet & (nf <= 0.3) & (rnd >= 0.3) & (rnd < 0.4)] = V["forest_light"]
        meadow = area_mask(lambda f: f.tag("landuse") in ("meadow", "grass") or f.tag("natural") == "grassland")
        veg[meadow & (nf > vcfg["meadow_tallgrass_threshold"])] = V["tall_grass"]
        veg[meadow & (rnd < 0.01)] = V["flowers"]
        veg[meadow & (rnd > 0.995)] = V["forest_light"]
        orchard = area_mask(lambda f: f.tag("landuse") == "orchard")
        grid = (((np.arange(S)[None, :] + ox) % 6 == 0) & ((np.arange(S)[:, None] + oy) % 6 == 0))
        veg[orchard & grid] = V["forest_light"]
        if farm:
            inner = erode(farm_mask, vcfg["field_margin_tiles"])
            # crops only grow where WorldEd allows vegetation: give the inner field a grass base
            ch.base[inner] = C["grass_light"]
            veg[inner & (rnd < 0.92)] = V["crops"]
            veg[inner & (rnd >= 0.92)] = V["crops2"]
            margin = farm_mask & ~inner
            ch.base[margin] = C["grass_medium"]
            veg[margin & (rnd < 0.5)] = V["tall_grass"]
        covered |= scrub | wet | meadow | orchard | farm_mask

        # parks, gardens, golf, cemeteries: open grass with scattered trees
        park = area_mask(lambda f: f.tag("leisure") in ("park", "garden", "golf_course", "recreation_ground", "nature_reserve") or f.tag("landuse") == "cemetery")
        veg[park & (nf > 0.6)] = V["park_scatter"]
        veg[park & (nf <= 0.6) & (rnd < vcfg["park_tree_chance"])] = V["forest_light"]
        veg[park & (nf <= 0.6) & (rnd >= vcfg["park_tree_chance"]) & (rnd < vcfg["park_tree_chance"] + 0.01)] = V["bushes_sparse"]
        veg[park & (rnd > 0.994)] = V["flowers"]
        covered |= park

        # built-up land: yards with the odd tree, bush and hedge
        built = urban.copy()
        if bld:
            built |= dilate(bld_mask, 1)
        for f, p in roads:
            if f.tag("highway") in ("residential", "living_street", "service"):
                built |= ch.line_mask([(f, 60)])
        yard = built & ~covered
        veg[yard & (rnd < vcfg["yard_tree_chance"])] = V["forest_light"]
        veg[yard & (rnd >= vcfg["yard_tree_chance"]) & (rnd < vcfg["yard_tree_chance"] + vcfg["yard_bush_chance"])] = V["bushes"]
        veg[yard & (rnd > 0.985)] = V["tall_grass"]
        covered |= built

        # everything else in New Brunswick is Acadian forest. Thinner than mapped forest polygons,
        # with meadows where the low-frequency noise says so.
        wild = ~covered
        wild_dense = wild & (nf > 0.55)
        wild_mid = wild & (nf > 0.30) & ~wild_dense
        wild_open = wild & ~wild_dense & ~wild_mid
        conif = species < vcfg["conifer_fraction"]
        veg[wild_dense & conif] = V["conifer_dense"]
        veg[wild_dense & ~conif] = V["forest_dense"]
        veg[wild_mid & conif & (rnd < 0.8)] = V["conifer"]
        veg[wild_mid & ~conif & (rnd < 0.8)] = V["forest"]
        veg[wild_mid & (rnd >= 0.8)] = V["bushes"]
        veg[wild_open & (rnd < 0.25)] = V["forest_light"]
        veg[wild_open & (rnd >= 0.25) & (rnd < 0.40)] = V["shrubland"]
        veg[wild_open & (rnd >= 0.40) & (rnd < 0.50)] = V["fir_sparse"]
        veg[wild_open & (rnd >= 0.50) & (rnd < 0.75)] = V["tall_grass"]
        surfaced = water_mask | rail_mask | sidewalk_mask | road_mask | hard_mask
        ch.base[(wild_dense | wild_mid) & ~surfaced] = C["grass_dark"]

        # individual mapped trees, tree rows, hedges
        trees = [f for f in pt_feats if f.tag("natural") == "tree"]
        if trees:
            veg[ch.point_mask(trees, 0.5)] = V["forest"]
        rows = [(f, 2) for f in line_feats if f.tag("natural") == "tree_row"]
        if rows:
            veg[ch.line_mask(rows) & (rnd < 0.7)] = V["forest_light"]
        hedges = [(f, 1) for f in line_feats if f.tag("barrier") == "hedge"]
        if hedges:
            veg[ch.line_mask(hedges)] = V["hedge"]

        # finally clear roads, buildings, water, parking
        veg[clear_mask] = V["none"]

        # --- write
        bmp = self.out / "bmp"
        bmp.mkdir(parents=True, exist_ok=True)
        name = f"chunk_{ch.cx}_{ch.cy}"
        Image.fromarray(ch.base, "RGB").save(bmp / f"{name}.png", optimize=True)
        Image.fromarray(ch.veg, "RGB").save(bmp / f"{name}_veg.png", optimize=True)
        return dict(cx=ch.cx, cy=ch.cy, base=f"bmp/{name}.png", veg=f"bmp/{name}_veg.png", size=S)

    def render_all(self, only: set[tuple[int, int]] | None = None) -> list[dict]:
        chunks = self.chunks()
        out = []
        for i, (kx, ky) in enumerate(chunks):
            if only and (kx, ky) not in only:
                continue
            print(f"[render] chunk {i+1}/{len(chunks)} at cell {kx*CHUNK_CELLS},{ky*CHUNK_CELLS}")
            out.append(self.render_chunk(kx, ky))
        return out


def write_world_json(out: Path, world: World, chunks: list[dict]) -> None:
    cells = sorted(world.active)
    meta = dict(
        cell=CELL,
        cells=cells,
        chunks=chunks,
        cell_bounds=[min(c[0] for c in cells), min(c[1] for c in cells), max(c[0] for c in cells), max(c[1] for c in cells)] if cells else [0, 0, 0, 0],
    )
    (out / "world.json").write_text(json.dumps(meta))
