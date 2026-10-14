"""objects.lua (zones), spawnpoints.lua, spawnregions.lua and the zombie spawn map."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from . import config, geo
from .config import CELL, ZONE_GRID
from .osm import OSMData, polygons

LUA_ESC = str.maketrans({'"': '\\"', "\\": "\\\\"})


def _zone(name: str, ztype: str, x: int, y: int, w: int, h: int, props: dict | None = None) -> str:
    s = f'\t{{ name = "{name.translate(LUA_ESC)}", type = "{ztype}", x = {x}, y = {y}, z = 0, width = {w}, height = {h}'
    if props:
        s += ", properties = { " + ", ".join(f'{k} = "{v}"' for k, v in props.items()) + " }"
    return s + " },"


def _grid_boxes(mask: np.ndarray, ox: int, oy: int, step: int, min_cover: float = 0.35):
    """Yield (x, y, w, h) tiles for step x step blocks whose coverage exceeds min_cover."""
    h, w = mask.shape
    for gy in range(0, h, step):
        for gx in range(0, w, step):
            blk = mask[gy:gy + step, gx:gx + step]
            if blk.mean() >= min_cover:
                yield ox + gx, oy + gy, blk.shape[1], blk.shape[0]


def _merge_rows(boxes):
    """Merge horizontally adjacent equal-height boxes to keep objects.lua small."""
    boxes = sorted(boxes, key=lambda b: (b[1], b[0]))
    out = []
    for b in boxes:
        if out and out[-1][1] == b[1] and out[-1][3] == b[3] and out[-1][0] + out[-1][2] == b[0]:
            out[-1] = (out[-1][0], out[-1][1], out[-1][2] + b[2], out[-1][3])
        else:
            out.append(tuple(b))
    return out


class ZoneBuilder:
    def __init__(self, data: OSMData, world: dict, lots: list[dict], out: Path):
        self.data, self.world, self.lots, self.out = data, world, lots, out
        x0, y0, x1, y1 = world["cell_bounds"]
        self.ox, self.oy = x0 * CELL, y0 * CELL
        self.W, self.H = (x1 - x0 + 1) * CELL, (y1 - y0 + 1) * CELL
        self.active = {tuple(c) for c in world["cells"]}

    def mask(self, pred, buffer=0.0, lines=None) -> np.ndarray:
        img = Image.new("L", (self.W, self.H), 0)
        d = ImageDraw.Draw(img)
        for f in self.data.features:
            if not pred(f):
                continue
            g = f.geom.buffer(buffer) if buffer else f.geom
            for p in polygons(g):
                d.polygon([(x - self.ox, y - self.oy) for x, y in p.exterior.coords], fill=255)
                for r in p.interiors:
                    d.polygon([(x - self.ox, y - self.oy) for x, y in r.coords], fill=0)
        return np.asarray(img) > 0

    # ------------------------------------------------------------------ objects.lua
    def objects_lua(self) -> str:
        lines = ["objects = {"]
        # Town zones: blocks with enough buildings (drives zombie outfits/loot and 'urban' behaviour)
        counts = {}
        for l in self.lots:
            k = ((l["x"] - self.ox) // ZONE_GRID, (l["y"] - self.oy) // ZONE_GRID)
            counts[k] = counts.get(k, 0) + 1
        town = [(self.ox + gx * ZONE_GRID, self.oy + gy * ZONE_GRID, ZONE_GRID, ZONE_GRID)
                for (gx, gy), c in counts.items() if c >= config.TOWN_ZONE_BUILDING_DENSITY]
        for x, y, w, h in _merge_rows(town):
            lines.append(_zone("", "TownZone", x, y, w, h))
        # Trailer parks
        for f in self.data.features:
            if f.tag("tourism") == "caravan_site" or f.tag("landuse") == "static_caravan":
                x0, y0, x1, y1 = f.bounds
                lines.append(_zone("", "TrailerPark", int(x0), int(y0), int(x1 - x0) + 1, int(y1 - y0) + 1))
        # Forest / DeepForest / Vegitation (foraging + erosion) from landuse
        forest = self.mask(lambda f: f.tag("landuse") == "forest" or f.tag("natural") == "wood")
        deep = Image.fromarray(forest.astype(np.uint8) * 255)
        from PIL import ImageFilter
        for _ in range(8):
            deep = deep.filter(ImageFilter.MinFilter(3))
        deep = np.asarray(deep) > 0
        for x, y, w, h in _merge_rows(_grid_boxes(deep, self.ox, self.oy, ZONE_GRID, 0.6)):
            lines.append(_zone("", "DeepForest", x, y, w, h))
        for x, y, w, h in _merge_rows(_grid_boxes(forest & ~deep, self.ox, self.oy, ZONE_GRID, 0.4)):
            lines.append(_zone("", "Forest", x, y, w, h))
        veg = self.mask(lambda f: f.tag("natural") in ("scrub", "heath", "wetland", "grassland") or f.tag("landuse") in ("meadow", "grass"))
        for x, y, w, h in _merge_rows(_grid_boxes(veg, self.ox, self.oy, ZONE_GRID, 0.4)):
            lines.append(_zone("", "Vegitation", x, y, w, h))
        farm = self.mask(lambda f: f.tag("landuse") in ("farmland", "farmyard", "orchard"))
        for x, y, w, h in _merge_rows(_grid_boxes(farm, self.ox, self.oy, ZONE_GRID, 0.5)):
            lines.append(_zone("", "FarmLand", x, y, w, h))
        # Everything active that isn't town/forest gets the generic wilderness 'Forest' zone so
        # foraging works in the unmapped Acadian forest between communities.
        covered = forest | veg | farm
        for cx, cy in self.active:
            x, y = cx * CELL, cy * CELL
            sub = covered[y - self.oy:y - self.oy + CELL, x - self.ox:x - self.ox + CELL]
            if sub.size and sub.mean() < 0.2 and not any((cx * CELL <= l["x"] < (cx + 1) * CELL and cy * CELL <= l["y"] < (cy + 1) * CELL) for l in self.lots):
                lines.append(_zone("", "Forest", x, y, CELL, CELL))
        # Vehicle zones: parking lots, special buildings
        for f in self.data.features:
            if not polygons(f.geom):
                continue
            x0, y0, x1, y1 = (int(v) for v in f.bounds)
            w, h = max(1, x1 - x0), max(1, y1 - y0)
            if f.tag("amenity") == "parking" and w * h >= 20:
                name = config.VEHICLE_ZONES["parking"]
                if f.tag("parking") == "multi-storey":
                    continue
                lines.append(_zone(name, "Vehicle", x0, y0, w, h, {"Direction": "N" if w >= h else "W"}))
            elif f.tag("amenity") == "police":
                lines.append(_zone("police", "Vehicle", x0 - 6, y0 - 6, w + 12, h + 12, {"Direction": "N"}))
            elif f.tag("amenity") == "fire_station":
                lines.append(_zone("fire", "Vehicle", x0 - 6, y0 - 6, w + 12, h + 12, {"Direction": "N"}))
            elif f.tag("amenity") == "hospital":
                lines.append(_zone("medical", "Vehicle", x0 - 6, y0 - 6, w + 12, h + 12, {"Direction": "N"}))
            elif f.tag("landuse") == "farmyard":
                lines.append(_zone("farm", "Vehicle", x0, y0, w, h, {"Direction": "N"}))
            elif f.tag("shop") == "car":
                lines.append(_zone("cardealer", "Vehicle", x0 - 4, y0 - 4, w + 8, h + 8, {"Direction": "N"}))
            elif f.tag("landuse") == "landfill" or f.tag("industrial") == "scrap_yard":
                lines.append(_zone("junkyard", "Vehicle", x0, y0, w, h, {"Direction": "N"}))
        # Residential driveways: a small parkingstall zone in front of each house, facing its road
        for l in self.lots:
            if l["key"] in ("house", "detached", "residential", "yes", "bungalow", "semidetached_house", "farm"):
                lines.append(_zone("parkingstall", "Vehicle", l["x"] - 2, l["y"] + l["h"], 4, 7, {"Direction": "N"}))
        # Highway traffic jams and roadside wrecks along the Trans-Canada
        for f in self.data.features:
            if f.tag("highway") in ("motorway", "trunk") and f.geom.geom_type == "LineString" and f.geom.length > 400:
                for i, (x, y) in enumerate(f.geom.coords[::25]):
                    if i % 3 == 0:
                        lines.append(_zone("trafficjamw" if i % 2 else "trafficjamn", "Vehicle", int(x) - 10, int(y) - 10, 20, 20, {"Direction": "N"}))
        lines.append("}")
        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------------ spawn points
    def spawnpoints_lua(self) -> str:
        houses = [l for l in self.lots if l["key"] in ("house", "detached", "residential", "yes", "bungalow", "semidetached_house", "apartments")]
        pts = []
        for title, (lat, lon) in config.SPAWN_POINTS.items():
            x, y = geo.lonlat_to_tile(lon, lat)
            if houses:
                best = min(houses, key=lambda l: (l["x"] - x) ** 2 + (l["y"] - y) ** 2)
                px, py = best["x"] + best["w"] // 2, best["y"] + best["h"] // 2
            else:
                px, py = int(x), int(y)
            pts.append((title, px, py))
        body = []
        for prof in ("unemployed", "constructionworker", "fireofficer", "policeofficer", "parkranger", "securityguard"):
            body.append(f"\t\t{prof} = {{")
            for title, px, py in pts:
                body.append(f"\t\t\t{{ worldX = {px // CELL}, worldY = {py // CELL}, posX = {px % CELL}, posY = {py % CELL} }}, -- {title}")
            body.append("\t\t},")
        return "function SpawnPoints()\n\treturn {\n" + "\n".join(body) + "\n\t}\nend\n"

    def spawnregions_lua(self) -> str:
        return ("function SpawnRegions()\n\treturn {\n"
                f'\t\t{{ name = "{config.MAP_FOLDER}", file = "media/maps/{config.MAP_FOLDER}/spawnpoints.lua" }},\n'
                "\t}\nend\n")

    # ------------------------------------------------------------------ zombie density (GenerateLots spawn map)
    def zombie_map(self, path: Path) -> None:
        """8-bit image, 1 px per tile, covering the active cell bounds. Black = no zombies."""
        z = np.full((self.H, self.W), config.ZOMBIE_DENSITY["forest"], np.uint8)
        urban = self.mask(lambda f: f.tag("landuse") in ("residential",))
        z[urban] = config.ZOMBIE_DENSITY["suburb"]
        com = self.mask(lambda f: f.tag("landuse") in ("commercial", "retail"))
        z[com] = config.ZOMBIE_DENSITY["commercial"]
        ind = self.mask(lambda f: f.tag("landuse") == "industrial")
        z[ind] = config.ZOMBIE_DENSITY["industrial"]
        farm = self.mask(lambda f: f.tag("landuse") in ("farmland", "farmyard", "meadow"))
        z[farm] = config.ZOMBIE_DENSITY["rural"]
        # downtown Moncton / Dieppe cores: dense building blocks
        img = Image.new("L", (self.W, self.H), 0)
        d = ImageDraw.Draw(img)
        counts = {}
        for l in self.lots:
            k = ((l["x"] - self.ox) // 100, (l["y"] - self.oy) // 100)
            counts[k] = counts.get(k, 0) + 1
        for (gx, gy), c in counts.items():
            if c >= 12:
                d.rectangle([gx * 100, gy * 100, gx * 100 + 99, gy * 100 + 99], fill=255)
            elif c >= 4:
                d.rectangle([gx * 100, gy * 100, gx * 100 + 99, gy * 100 + 99], fill=128)
        m = np.asarray(img)
        z[m == 255] = config.ZOMBIE_DENSITY["downtown"]
        z[(m == 128) & (z < config.ZOMBIE_DENSITY["town"])] = config.ZOMBIE_DENSITY["town"]
        water = self.mask(lambda f: f.tag("natural") == "water" or f.tag("water"))
        z[water] = 0
        Image.fromarray(z, "L").save(path, optimize=True)


def generate(data: OSMData, out: Path, zombie_map: bool = True) -> dict:
    world = json.loads((out / "world.json").read_text())
    lots = json.loads((out / "lots.json").read_text()) if (out / "lots.json").exists() else []
    zb = ZoneBuilder(data, world, lots, out)
    mapdir = out / "mod" / config.MOD_ID / "media" / "maps" / config.MAP_FOLDER
    mapdir.mkdir(parents=True, exist_ok=True)
    (mapdir / "objects.lua").write_text(zb.objects_lua())
    (mapdir / "spawnpoints.lua").write_text(zb.spawnpoints_lua())
    (mapdir / "spawnregions.lua").write_text(zb.spawnregions_lua())
    if zombie_map:
        zb.zombie_map(out / "zombie_spawn_map.png")
    print(f"[zones] objects.lua / spawnpoints.lua written to {mapdir}")
    return dict(origin=(zb.ox, zb.oy), size=(zb.W, zb.H))
