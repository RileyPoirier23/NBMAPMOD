"""Furniture library + room furnishing for generated buildings.

Library sources, in order of preference:
  1. `python -m nbmap furniture --tilezed <TileZed folder>` harvests TileZed's own
     BuildingFurniture.txt (the palette BuildingEd shows you), so every tile name is one your
     tools already know. Group labels are keyword-matched to room types below.
  2. `python -m nbmap furniture --tbx <folder of .tbx>` harvests furniture from any buildings
     you or the community already made (keyed by the room they stand in).
Both write tools/nbmap/data/furniture.json, which buildings.py uses on the next build.
"""
from __future__ import annotations

import json
import random
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

DATA = Path(__file__).parent / "data"
ORIENTS = ("W", "N", "E", "S")

# room InternalName -> list of (keyword regex for a furniture group, how many to place, wall?)
ROOM_PLAN = {
    "bedroom":      [("bed", 1, True), ("wardrobe|dresser|closet", 1, True), ("nightstand|bedside|table", 1, True), ("lamp|plant", 1, False)],
    "livingroom":   [("sofa|couch", 1, True), ("tv|television", 1, True), ("bookcase|bookshelf|shelv", 1, True), ("coffee|table", 1, False), ("armchair|chair", 1, False)],
    "kitchen":      [("fridge|refrigerat", 1, True), ("stove|oven|cooker", 1, True), ("counter|cabinet|cupboard", 3, True), ("sink", 1, True), ("table", 1, False)],
    "bathroom":     [("toilet", 1, True), ("bath|tub|shower", 1, True), ("sink|basin", 1, True)],
    "garage":       [("shelv|rack|tool", 2, True), ("crate|box", 1, False), ("workbench|bench", 1, True)],
    "shed":         [("shelv|rack|tool", 1, True), ("crate|box", 1, False)],
    "barn":         [("hay|crate|box|barrel", 2, False), ("shelv|rack", 1, True)],
    "storage":      [("shelv|rack|crate", 3, True)],
    "warehouse":    [("shelv|rack|crate|pallet", 4, True), ("crate|box", 2, False)],
    "office":       [("desk", 1, True), ("chair", 1, False), ("filing|cabinet", 1, True), ("shelv|bookcase", 1, True)],
    "classroom":    [("desk", 3, False), ("chair", 3, False), ("shelv|bookcase|locker", 1, True)],
    "hall":         [("bench|chair|seat", 2, True), ("vending|machine", 1, True)],
    "library":      [("bookcase|bookshelf|shelv", 4, True), ("desk|table", 1, False)],
    "medical":      [("bed|gurney|stretcher", 1, True), ("cabinet|medicine|shelv", 2, True), ("desk", 1, True)],
    "church":       [("pew|bench", 4, True), ("altar|table", 1, True)],
    "gym":          [("locker|bench|weight|machine", 2, True)],
    "lockerroom":   [("locker", 3, True), ("bench", 1, False)],
    "restaurant":   [("table", 3, False), ("chair", 3, False), ("counter|bar", 1, True)],
    "restaurantkitchen": [("fridge|refrigerat", 1, True), ("stove|oven|fryer|grill", 2, True), ("counter|cabinet", 2, True), ("sink", 1, True)],
    "cafe":         [("table", 2, False), ("chair", 2, False), ("counter|display|coffee", 1, True)],
    "bar":          [("bar|counter", 2, True), ("stool|chair", 2, False), ("table", 1, False), ("shelv|liquor|bottle", 1, True)],
    "barkitchen":   [("fridge|refrigerat", 1, True), ("counter|cabinet", 1, True), ("sink", 1, True)],
    "generalstore": [("shelv|shelf|display|rack", 4, True), ("counter|register|checkout", 1, True)],
    "grocery":      [("shelv|shelf|display|grocery|produce|freezer|fridge", 6, True), ("counter|register|checkout", 1, True)],
    "grocerystorage": [("shelv|rack|crate|pallet", 3, True)],
    "conveniencestore": [("shelv|shelf|display|fridge|freezer", 4, True), ("counter|register", 1, True)],
    "gasstore":     [("shelv|shelf|display|fridge", 3, True), ("counter|register", 1, True)],
    "gasstorage":   [("shelv|rack|crate", 2, True)],
    "pharmacy":     [("shelv|shelf|display|medicine|pharmac", 4, True), ("counter|register", 1, True)],
    "pharmacystorage": [("shelv|rack|crate|cabinet", 2, True)],
    "toolstore":    [("shelv|shelf|display|tool|hardware", 4, True), ("counter|register", 1, True)],
    "toolstorage":  [("shelv|rack|crate", 2, True)],
    "clothingstore":[("rack|clothes|clothing|mannequin|display", 4, True), ("counter|register", 1, True)],
    "clothingstorage": [("rack|shelv|crate", 2, True)],
    "departmentstore": [("shelv|shelf|display|rack", 5, True), ("counter|register", 1, True)],
    "electronicsstore": [("shelv|shelf|display|tv|electronic", 4, True), ("counter|register", 1, True)],
    "furniturestore": [("sofa|couch|bed|table|wardrobe", 5, True)],
    "gardenstore":  [("shelv|shelf|display|plant|garden|sack", 4, True), ("counter|register", 1, True)],
    "petstore":     [("shelv|shelf|display|cage|aquarium", 3, True), ("counter|register", 1, True)],
    "bookstore":    [("bookcase|bookshelf|shelv|magazine", 4, True), ("counter|register", 1, True)],
    "liquorstore":  [("shelv|shelf|liquor|bottle|display|fridge", 4, True), ("counter|register", 1, True)],
    "bakery":       [("display|counter|shelv|bread", 3, True)],
    "bakerykitchen":[("oven|stove", 1, True), ("counter|cabinet", 2, True), ("sink", 1, True)],
    "butcher":      [("counter|display|freezer|fridge|meat", 3, True)],
    "butcherstorage": [("freezer|fridge|shelv", 2, True)],
    "gunstore":     [("gun|rifle|weapon|display|counter|cabinet", 4, True)],
    "gunstorestorage": [("cabinet|locker|shelv|crate", 2, True)],
    "sportstore":   [("shelv|shelf|display|rack|sport", 4, True), ("counter|register", 1, True)],
    "sportstorage": [("shelv|rack|crate", 2, True)],
    "cardealer":    [("desk", 1, True), ("chair", 1, False), ("shelv|display", 1, True)],
    "mechanic":     [("shelv|rack|tool|workbench|tire|tyre", 3, True), ("crate|box|barrel", 1, False)],
    "policestorage":[("locker|cabinet|gun|weapon|shelv", 4, True)],
    "firestorage":  [("locker|shelv|rack", 3, True)],
    "greenhouse":   [("plant|pot|table|shelv", 3, False)],
    "parkingstall": [],
}
DEFAULT_PLAN = [("shelv|table|crate", 2, True)]


def _parse_blocks(text: str) -> list:
    """Parse TileZed's `name { key = value ... nested {} }` files into nested dicts (lists for repeats)."""
    tokens = re.findall(r"\{|\}|[^{}\n]+", text)
    stack = [{"_kids": []}]
    pending = None
    for tok in tokens:
        t = tok.strip()
        if t == "{":
            node = {"_name": pending or "", "_kids": [], "_props": {}}
            stack[-1]["_kids"].append(node)
            stack.append(node)
            pending = None
        elif t == "}":
            stack.pop()
        elif t and not t.startswith("#") and not t.startswith("//"):
            if "=" in t:
                for k, v in re.findall(r"(\S+)\s*=\s*(.*?)(?=\s+\S+\s*=|$)", t):
                    stack[-1].setdefault("_props", {})[k.strip()] = v.strip()
            else:
                pending = t
    return stack[0]["_kids"]


def harvest_tilezed(tilezed: Path) -> dict:
    cands = list(tilezed.rglob("BuildingFurniture.txt"))
    if not cands:
        raise SystemExit(f"BuildingFurniture.txt not found under {tilezed}")
    groups = {}
    for node in _walk(_parse_blocks(cands[0].read_text(errors="ignore"))):
        if node["_name"] != "furniture":
            continue
        label = node["_props"].get("label", "")
        parent_label = node.get("_parent_label", "")
        pieces = {}
        for e in node["_kids"]:
            if e["_name"] != "entry":
                continue
            orient = e["_props"].get("orient", "W")
            tiles = []
            for k, v in e["_props"].items():
                m = re.match(r"^(\d+),(\d+)$", k)
                if m:
                    tiles.append([int(m.group(1)), int(m.group(2)), v])
            if tiles:
                pieces[orient] = tiles
        if pieces:
            groups.setdefault(f"{parent_label} {label}".strip() or "misc", []).append(
                dict(layer=node["_props"].get("layer", "Furniture"), tiles=pieces))
    lib = dict(source=str(cands[0]), groups=groups)
    print(f"[furniture] harvested {sum(len(v) for v in groups.values())} pieces in {len(groups)} groups from {cands[0]}")
    return lib


def _walk(nodes, parent_label=""):
    for n in nodes:
        n["_parent_label"] = parent_label
        yield n
        yield from _walk(n["_kids"], n["_props"].get("label", parent_label) if n["_name"] == "group" else parent_label)


def harvest_tbx(folder: Path) -> dict:
    """Furniture from existing .tbx files, grouped by the InternalName of the room each piece sits in."""
    groups = {}
    for p in folder.rglob("*.tbx"):
        try:
            root = ET.parse(p).getroot()
        except ET.ParseError:
            continue
        furn = []
        for f in root.findall("furniture"):
            pieces = {}
            for e in f.findall("entry"):
                pieces[e.get("orient", "W")] = [[int(t.get("x")), int(t.get("y")), t.get("tile")] for t in e.findall("tile")]
            furn.append(dict(layer=f.get("layer", "Furniture"), tiles=pieces))
        rooms = [r.get("InternalName", "") for r in root.findall("room")]
        for fl in root.findall("floor"):
            grid = [row.strip().strip(",").split(",") for row in (fl.findtext("rooms") or "").strip().splitlines()]
            for o in fl.findall("object"):
                if o.get("type") != "furniture":
                    continue
                x, y, idx = int(o.get("x")), int(o.get("y")), int(o.get("FurnitureTiles", "0")) - 1
                try:
                    rid = int(grid[y][x])
                    room = rooms[rid - 1] if rid > 0 else "outside"
                except (IndexError, ValueError):
                    room = "misc"
                if 0 <= idx < len(furn):
                    key = f"{room} {p.stem}"
                    if furn[idx] not in groups.setdefault(key, []):
                        groups[key].append(furn[idx])
    lib = dict(source=str(folder), groups=groups)
    print(f"[furniture] harvested {sum(len(v) for v in groups.values())} pieces in {len(groups)} groups from {folder}")
    return lib


def save(lib: dict) -> Path:
    path = DATA / "furniture.json"
    path.write_text(json.dumps(lib, indent=1))
    print(f"[furniture] -> {path}")
    return path


def load() -> dict:
    lib = json.loads((DATA / "furniture.json").read_text())
    return lib if lib.get("groups") else {}


# ------------------------------------------------------------------ placement

class Furnisher:
    def __init__(self, lib: dict, rng: random.Random):
        self.groups = lib.get("groups", {})
        self.rng = rng
        self.catalog: list[dict] = []          # unique pieces, index = FurnitureTiles - 1
        self._index: dict[str, int] = {}

    def _pieces(self, pattern: str) -> list[dict]:
        rx = re.compile(pattern, re.I)
        out = []
        for label, pieces in self.groups.items():
            if rx.search(label):
                out.extend(pieces)
        if not out:   # fall back to any piece whose tile name matches
            for label, pieces in self.groups.items():
                for pc in pieces:
                    if any(rx.search(t[2]) for tiles in pc["tiles"].values() for t in tiles):
                        out.append(pc)
        return out

    def _catalog_index(self, piece: dict) -> int:
        key = json.dumps(piece, sort_keys=True)
        if key not in self._index:
            self.catalog.append(piece)
            self._index[key] = len(self.catalog)
        return self._index[key]

    def furnish_room(self, rooms: np.ndarray, rid: int, name: str, blocked: set, doors: set) -> list[tuple[int, int, str, int]]:
        """Return furniture objects (x, y, orient, FurnitureTiles) for room id `rid`."""
        plan = ROOM_PLAN.get(name, DEFAULT_PLAN)
        h, w = rooms.shape
        tiles = {(x, y) for y, x in zip(*np.nonzero(rooms == rid))}
        if len(tiles) < 4 or not plan:
            return []
        # tiles in front of doors stay clear
        keep_clear = set(blocked)
        for x, y, d in doors:
            keep_clear |= {(x, y), (x, y - 1) if d == "N" else (x - 1, y)}
        free = set(tiles) - keep_clear

        def wall_side(x, y):
            s = []
            if rooms[y - 1, x] != rid if y > 0 else True:
                s.append("N")
            if rooms[y, x - 1] != rid if x > 0 else True:
                s.append("W")
            if (rooms[y + 1, x] != rid) if y + 1 < h else True:
                s.append("S")
            if (rooms[y, x + 1] != rid) if x + 1 < w else True:
                s.append("E")
            return s

        placed = []
        for pattern, count, want_wall in plan:
            candidates = self._pieces(pattern)
            if not candidates:
                continue
            for _ in range(count):
                piece = self.rng.choice(candidates)
                spots = list(free)
                self.rng.shuffle(spots)
                done = False
                for (x, y) in spots:
                    sides = wall_side(x, y)
                    if want_wall and not sides:
                        continue
                    orient_pref = [s for s in sides if s in piece["tiles"]] or [o for o in ORIENTS if o in piece["tiles"]]
                    if not orient_pref:
                        continue
                    orient = orient_pref[0]
                    foot = {(x + tx, y + ty) for tx, ty, _ in piece["tiles"][orient]}
                    if foot <= free:
                        free -= foot
                        placed.append((x, y, orient, self._catalog_index(piece)))
                        done = True
                        break
                if not done:
                    break
        return placed

    def xml(self) -> list[str]:
        out = []
        for piece in self.catalog:
            out.append(f'    <furniture layer="{piece.get("layer", "Furniture")}">')
            for orient, tiles in piece["tiles"].items():
                out.append(f'        <entry orient="{orient}">')
                for tx, ty, tile in tiles:
                    out.append(f'            <tile x="{tx}" y="{ty}" tile="{tile}"/>')
                out.append('        </entry>')
            out.append('    </furniture>')
        return out


def main(argv: list[str]) -> None:
    import argparse

    p = argparse.ArgumentParser(prog="nbmap furniture", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tilezed", help="TileZed install folder (contains BuildingFurniture.txt)")
    p.add_argument("--tbx", help="folder of existing .tbx buildings to learn from")
    a = p.parse_args(argv)
    if a.tilezed:
        save(harvest_tilezed(Path(a.tilezed)))
    elif a.tbx:
        save(harvest_tbx(Path(a.tbx)))
    else:
        p.error("give --tilezed or --tbx")
