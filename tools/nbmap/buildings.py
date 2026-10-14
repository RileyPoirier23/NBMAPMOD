"""Generate BuildingEd (.tbx) buildings from OSM footprints.

Every OSM building becomes a .tbx at its exact 1:1 footprint (orthogonalised to the
tile grid), with:
  * rooms from a BSP split, named by vanilla room InternalNames (drives loot zones),
  * a front door facing the nearest road, internal doors between rooms,
  * windows on exterior walls, stairs + extra floors from building:levels,
  * a flat roof so the interior counts as "inside".

The writer targets BuildingEd's XML format (TileZed, "building version 2"). The
format is only documented by TileZed's source, so open one generated file in
BuildingEd first; everything about the layout lives in this one module.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import quoteattr

import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import Polygon
from shapely.ops import nearest_points
from shapely.strtree import STRtree

from . import config, furnish
from .config import CELL
from .osm import Feature, OSMData, lines, polygons

DATA = Path(__file__).parent / "data"

ROOM_COLORS = {}


def _room_color(name: str) -> str:
    """BuildingEd stores room colours as 'r g b'; derive a stable one from the name."""
    if name not in ROOM_COLORS:
        h = int(hashlib.md5(name.encode()).hexdigest()[:6], 16)
        ROOM_COLORS[name] = f"{(h >> 16) & 255} {(h >> 8) & 255} {h & 255}"
    return ROOM_COLORS[name]


def load_themes() -> dict:
    raw = json.loads((DATA / "themes.json").read_text())
    out = {}

    def resolve(k):
        if k in out:
            return out[k]
        t = dict(raw[k])
        base = resolve(t.pop("like")) if "like" in t else {}
        out[k] = {**base, **t}
        return out[k]

    for k in raw:
        if not k.startswith("_"):
            resolve(k)
    return out


def _sheet_offset(tile: str, n: int) -> str:
    """walls_exterior_house_01_0 + 3 -> walls_exterior_house_01_3"""
    base, idx = tile.rsplit("_", 1)
    return f"{base}_{int(idx) + n}"


# BuildingEd tile categories: (enum name, sheet offset) in the order BuildingEd writes them.
# Offsets come from TileZed's buildingtiles.cpp createEntryFromSingleTile().
CATEGORY_ENUMS = {
    "exterior_walls": [("West", 0), ("North", 1), ("NorthWest", 2), ("SouthEast", 3), ("WestWindow", 8), ("NorthWindow", 9), ("WestDoor", 10), ("NorthDoor", 11)],
    "interior_walls": [("West", 0), ("North", 1), ("NorthWest", 2), ("SouthEast", 3), ("WestWindow", 8), ("NorthWindow", 9), ("WestDoor", 10), ("NorthDoor", 11)],
    "doors": [("West", 0), ("North", 1), ("WestOpen", 2), ("NorthOpen", 3)],
    "door_frames": [("West", 0), ("North", 1)],
    "windows": [("West", 0), ("North", 1)],
    "curtains": [("West", 0), ("East", 1), ("North", 2), ("South", 3)],
    "stairs": [("West1", 0), ("West2", 1), ("West3", 2), ("North1", 8), ("North2", 9), ("North3", 10)],
    "roof_tops": [("West1", 0), ("West2", 0), ("West3", 0), ("North1", 0), ("North2", 0), ("North3", 0)],
    "floors": [("Floor", 0)],
}
# <building> root attributes (BuildingTemplate::initNames) and <room> attributes (Room::initNames)
BUILDING_SLOTS = ["ExteriorWall", "ExteriorWallTrim", "Door", "DoorFrame", "Window", "Curtains", "Shutters", "Stairs", "RoofCap", "RoofSlope", "RoofTop", "GrimeWall"]
ROOM_SLOTS = ["InteriorWall", "InteriorWallTrim", "Floor", "GrimeFloor", "GrimeWall"]


@dataclass
class Building:
    osm_id: int
    name: str
    theme: str
    rooms: list[str]
    x: int                 # world tile of the building's top-left
    y: int
    w: int
    h: int
    levels: int
    mask: np.ndarray       # (h, w) bool footprint
    front: str = "S"       # side facing the road: N/S/E/W
    tags: dict = field(default_factory=dict)

    @property
    def cell(self) -> tuple[int, int]:
        return self.x // CELL, self.y // CELL


def classify(f: Feature) -> tuple[str, dict]:
    b = f.tag("building", "yes")
    key = b
    if f.tag("amenity") in config.AMENITY_THEMES:
        key = config.AMENITY_THEMES[f.tag("amenity")]
    elif f.tag("shop") in config.SHOP_THEMES:
        key = config.SHOP_THEMES[f.tag("shop")]
    elif b not in config.BUILDING_THEMES:
        key = "yes"
    spec = config.BUILDING_THEMES.get(key) or config.BUILDING_THEMES["yes"]
    return key, spec


def _levels(f: Feature) -> int:
    lv = f.tag("building:levels")
    try:
        n = int(float(lv))
        return max(1, min(n, 6))     # Zomboid handles 8 floors; keep towers sane
    except (TypeError, ValueError):
        return config.BUILDINGS["default_levels"]


def _footprint_mask(poly: Polygon) -> tuple[int, int, np.ndarray]:
    x0, y0, x1, y1 = poly.bounds
    ox, oy = int(math.floor(x0)), int(math.floor(y0))
    w, h = int(math.ceil(x1)) - ox, int(math.ceil(y1)) - oy
    w, h = max(1, min(w, config.BUILDINGS["max_footprint"])), max(1, min(h, config.BUILDINGS["max_footprint"]))
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    for p in polygons(poly):
        d.polygon([(x - ox - 0.5, y - oy - 0.5) for x, y in p.exterior.coords], fill=255)
        for r in p.interiors:
            d.polygon([(x - ox - 0.5, y - oy - 0.5) for x, y in r.coords], fill=0)
    m = np.asarray(img) > 0
    if m.sum() < 1:   # tiny buildings: at least the centre tile
        m[h // 2, w // 2] = True
    # BuildingEd needs 1 tile of margin on the south/east for walls/roof
    out = np.zeros((h + 1, w + 1), bool)
    out[:h, :w] = m
    return ox, oy, out


def _bsp_rooms(mask: np.ndarray, n: int, rng: random.Random) -> np.ndarray:
    """Split the footprint into n rooms (1-based ids, 0 outside)."""
    h, w = mask.shape
    rooms = np.zeros((h, w), np.int32)
    ys, xs = np.nonzero(mask)
    rects = [(xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)]
    while len(rects) < n:
        rects.sort(key=lambda r: -(r[2] - r[0]) * (r[3] - r[1]))
        x0, y0, x1, y1 = rects.pop(0)
        rw, rh = x1 - x0, y1 - y0
        if max(rw, rh) < 6:        # too small to split
            rects.append((x0, y0, x1, y1))
            break
        if rw >= rh:
            cut = rng.randint(3, rw - 3) if rw > 6 else rw // 2
            rects += [(x0, y0, x0 + cut, y1), (x0 + cut, y0, x1, y1)]
        else:
            cut = rng.randint(3, rh - 3) if rh > 6 else rh // 2
            rects += [(x0, y0, x1, y0 + cut), (x0, y0 + cut, x1, y1)]
    for i, (x0, y0, x1, y1) in enumerate(rects, start=1):
        sub = rooms[y0:y1, x0:x1]
        sub[mask[y0:y1, x0:x1]] = i
    # any footprint tile left unassigned (irregular shapes) joins the nearest room id
    left = mask & (rooms == 0)
    while left.any():
        ys, xs = np.nonzero(left)
        for y, x in zip(ys, xs):
            for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                yy, xx = y + dy, x + dx
                if 0 <= yy < h and 0 <= xx < w and rooms[yy, xx]:
                    rooms[y, x] = rooms[yy, xx]
                    break
        if (mask & (rooms == 0)).sum() == left.sum():
            rooms[left] = 1
        left = mask & (rooms == 0)
    return rooms


def _exterior_edges(rooms: np.ndarray):
    """Yield (x, y, dir) for exterior wall segments. dir N = north edge of tile, W = west edge."""
    h, w = rooms.shape
    for y in range(h):
        for x in range(w):
            here = rooms[y, x] != 0
            north = rooms[y - 1, x] != 0 if y > 0 else False
            west = rooms[y, x - 1] != 0 if x > 0 else False
            if here != north:
                yield x, y, "N", "S" if here else "N"   # which side of the building faces out
            if here != west:
                yield x, y, "W", "E" if here else "W"


def _front_side(poly: Polygon, roads: STRtree, road_geoms: list) -> str:
    c = poly.centroid
    if len(road_geoms) == 0:
        return "S"
    idx = roads.nearest(c)
    p = nearest_points(c, road_geoms[idx])[1]
    dx, dy = p.x - c.x, p.y - c.y
    if abs(dx) > abs(dy):
        return "E" if dx > 0 else "W"
    return "S" if dy > 0 else "N"


class TbxWriter:
    def __init__(self, themes: dict, furniture: dict):
        self.themes = themes
        self.furniture = furniture

    def write(self, b: Building, rng: random.Random) -> str:
        t = self.themes.get(b.theme) or self.themes["house"]
        entries: list[tuple[str, list[tuple[str, str]]]] = []

        def entry(cat: str, base_tile: str) -> int:
            entries.append((cat, [(e, _sheet_offset(base_tile, off)) for e, off in CATEGORY_ENUMS[cat]]))
            return len(entries)   # 1-based; 0 = none (BuildingReader::getEntry)

        ext = entry("exterior_walls", t["exterior_walls"])
        door = entry("doors", t["doors"])
        frame = entry("door_frames", t["door_frames"])
        win = entry("windows", t["windows"])
        curt = entry("curtains", t["curtains"])
        stairs = entry("stairs", t["stairs"])
        rooftop = entry("roof_tops", t["roof_tops"])
        interior = entry("interior_walls", t["interior_walls"])
        floor = entry("floors", t["floor"])
        slots = dict(ExteriorWall=ext, ExteriorWallTrim=0, Door=door, DoorFrame=frame, Window=win, Curtains=curt,
                     Shutters=0, Stairs=stairs, RoofCap=0, RoofSlope=0, RoofTop=rooftop, GrimeWall=0)

        h, w = b.mask.shape
        n_rooms = max(1, min(len(b.rooms), (b.mask.sum() // 20) or 1))
        rooms = _bsp_rooms(b.mask, n_rooms, rng)
        ids = sorted(set(rooms[rooms > 0].tolist()))
        room_names = [b.rooms[(i - 1) % len(b.rooms)] for i in ids]

        out = ['<?xml version="1.0" encoding="UTF-8"?>']
        out.append(f'<building version="3" width="{w}" height="{h}" ' + " ".join(f'{k}="{slots[k]}"' for k in BUILDING_SLOTS) + ">")
        for cat, tiles in entries:
            out.append(f'    <tile_entry category="{cat}">')
            for e, tile in tiles:
                out.append(f'        <tile enum="{e}" tile="{tile}"/>')
            out.append('    </tile_entry>')
        for i, name in zip(ids, room_names):
            pretty = name.replace("store", " store").replace("room", " room").title()
            rs = dict(InteriorWall=interior, InteriorWallTrim=0, Floor=floor, GrimeFloor=0, GrimeWall=0)
            out.append(f'    <room Name={quoteattr(pretty)} InternalName="{name}" Color="{_room_color(name)}" '
                       + " ".join(f'{k}="{rs[k]}"' for k in ROOM_SLOTS) + "/>")

        # objects shared by all floors
        exterior = list(_exterior_edges(rooms))
        front_edges = [(x, y, d) for x, y, d, side in exterior if side == b.front]
        if not front_edges:
            front_edges = [(x, y, d) for x, y, d, _ in exterior]
        rng.shuffle(front_edges)
        doors_xy = set()
        if front_edges:
            fx, fy, fd = front_edges[0]
            doors_xy.add((fx, fy, fd))
        # internal doors: one per pair of adjacent rooms
        seen_pairs = set()
        for y in range(h):
            for x in range(w):
                a = rooms[y, x]
                if not a:
                    continue
                if x > 0 and rooms[y, x - 1] and rooms[y, x - 1] != a and (min(a, rooms[y, x - 1]), max(a, rooms[y, x - 1])) not in seen_pairs:
                    seen_pairs.add((min(a, rooms[y, x - 1]), max(a, rooms[y, x - 1])))
                    doors_xy.add((x, y, "W"))
                if y > 0 and rooms[y - 1, x] and rooms[y - 1, x] != a and (min(a, rooms[y - 1, x]), max(a, rooms[y - 1, x])) not in seen_pairs:
                    seen_pairs.add((min(a, rooms[y - 1, x]), max(a, rooms[y - 1, x])))
                    doors_xy.add((x, y, "N"))
        windows_xy = []
        spacing = config.BUILDINGS["window_spacing"]
        for i, (x, y, d, _) in enumerate(sorted(exterior)):
            if (x, y, d) in doors_xy:
                continue
            if (x + y + (0 if d == "N" else 1)) % spacing == 0:
                windows_xy.append((x, y, d))

        # stairs: in the largest room, if more than one level
        stair = None
        if b.levels > 1:
            sizes = {i: int((rooms == i).sum()) for i in ids}
            big = max(sizes, key=sizes.get)
            ys, xs = np.nonzero(rooms == big)
            x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
            if x1 - x0 >= 5:
                stair = (x0, y0 + 1, "W")          # Stairs::bounds() = 5 tiles along x
            elif y1 - y0 >= 5:
                stair = (x0 + 1, y0, "N")          # 5 tiles along y

        rooms_txt = "\n".join(",".join(str(v) for v in row) + "," for row in rooms.tolist())
        furn = furnish.Furnisher(self.furniture, rng) if self.furniture else None
        floors_furniture: list[list[tuple[int, int, str, int]]] = []
        for level in range(b.levels):
            objs: list[tuple[int, int, str, int]] = []
            if furn:
                blocked = set()
                if stair:
                    sx, sy, sd = stair
                    blocked |= {(sx + i, sy) for i in range(5)} if sd == "W" else {(sx, sy + i) for i in range(5)}
                for i, name in zip(ids, room_names):
                    objs += furn.furnish_room(rooms, i, name, blocked, doors_xy)
            floors_furniture.append(objs)
        if furn and furn.catalog:
            insert_at = len(out)
            out[insert_at:insert_at] = furn.xml()
        for level in range(b.levels):
            out.append('    <floor>')
            floor_start = len(out)
            for x, y, d in sorted(doors_xy):
                if level > 0 and front_edges and (x, y, d) == front_edges[0]:
                    continue   # no front door hanging in mid-air upstairs
                out.append(f'        <object type="door" FrameTile="{frame}" x="{x}" y="{y}" dir="{d}" Tile="{door}"/>')
            for x, y, d in windows_xy:
                out.append(f'        <object type="window" CurtainsTile="{curt}" ShuttersTile="0" x="{x}" y="{y}" dir="{d}" Tile="{win}"/>')
            if stair and level < b.levels - 1:
                sx, sy, sd = stair
                out.append(f'        <object type="stairs" x="{sx}" y="{sy}" dir="{sd}" Tile="{stairs}"/>')
            for x, y, orient, idx in floors_furniture[level]:
                out.append(f'        <object type="furniture" FurnitureTiles="{idx - 1}" orient="{orient}" x="{x}" y="{y}"/>')
            if level == b.levels - 1:
                out.append(f'        <object type="roof" width="{w - 1}" height="{h - 1}" RoofType="FlatTop" Depth="Zero" '
                           f'cappedW="true" cappedN="true" cappedE="true" cappedS="true" CapTiles="0" SlopeTiles="0" TopTiles="{rooftop}" x="0" y="0"/>')
            out.append('        <rooms>')
            out.append(rooms_txt)
            out.append('        </rooms>')
            out.append('    </floor>')
        out.append('</building>')
        return "\n".join(out) + "\n"


def generate(data: OSMData, out: Path) -> list[Building]:
    rng = random.Random(config.BUILDINGS["seed"])
    themes = load_themes()
    furniture = furnish.load()
    print(f"[buildings] furniture library: {sum(len(v) for v in furniture.get('groups', {}).values())} pieces" if furniture else "[buildings] no furniture library (run `python -m nbmap furniture`), building empty shells")
    writer = TbxWriter(themes, furniture)
    road_feats = [f for f in data.features if f.tag("highway") in config.ROADS and f.geom.geom_type != "Point"]
    road_geoms = [f.geom for f in road_feats]
    tree = STRtree(road_geoms) if road_geoms else None
    bdir = out / "buildings"
    bdir.mkdir(parents=True, exist_ok=True)
    built: list[Building] = []
    seen = set()
    for f in data.features:
        if "building" not in f.tags or not polygons(f.geom):
            continue
        poly = f.geom
        if poly.area < 2:
            continue
        key, spec = classify(f)
        ox, oy, mask = _footprint_mask(poly)
        b = Building(f.osm_id, f.tag("name", ""), spec["theme"], list(spec["rooms"]), ox, oy, mask.shape[1], mask.shape[0],
                     _levels(f), mask, _front_side(poly, tree, road_geoms) if tree else "S", f.tags)
        if (b.x, b.y) in seen:
            continue
        seen.add((b.x, b.y))
        fname = f"{key}_{f.osm_id}.tbx"
        (bdir / fname).write_text(writer.write(b, rng))
        built.append(b)
        b.tags = {"file": f"buildings/{fname}", "key": key, "name": b.name, "amenity": f.tag("amenity"), "shop": f.tag("shop")}
    lots = [dict(x=b.x, y=b.y, w=b.w, h=b.h, cell=list(b.cell), levels=b.levels, **b.tags) for b in built]
    (out / "lots.json").write_text(json.dumps(lots))
    print(f"[buildings] wrote {len(built)} .tbx files")
    return built
