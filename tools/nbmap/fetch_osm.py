"""Get OpenStreetMap data for every configured area.

Two sources:
  python -m nbmap fetch                 Overpass API, each area split into small tiles with one
                                        compact query per tile (Overpass 504s on big queries)
  python -m nbmap fetch --geofabrik     download the New Brunswick extract (~60 MB .osm.pbf) once
                                        and filter it locally with pyosmium. Most reliable.
Output is one Overpass-style JSON per area in data/osm/. Existing files are skipped.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from . import config

MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://z.overpass-api.de/api/interpreter",
]
KEYS = ["highway", "railway", "building", "natural", "landuse", "leisure", "amenity", "waterway", "water",
        "wetland", "barrier", "man_made", "power", "shop", "place", "tourism", "sport"]
TILE_DEG = 0.04          # ~3 x 4.5 km tiles keep each Overpass query small
UA = {"User-Agent": "nbmap-zomboid-generator/0.2 (github.com/RileyPoirier23/NBMAPMOD)"}

QUERY = """[out:json][timeout:180];
nwr[~"^({keys})$"~"."]({bbox});
(._;>;);
out body;
"""


# ----------------------------------------------------------------------------- Overpass (tiled)

def _tiles(area: config.Area):
    lat = area.south
    while lat < area.north:
        lon = area.west
        while lon < area.east:
            yield f"{lat:.4f},{lon:.4f},{min(lat + TILE_DEG, area.north):.4f},{min(lon + TILE_DEG, area.east):.4f}"
            lon += TILE_DEG
        lat += TILE_DEG


def _overpass(bbox: str, label: str) -> list[dict]:
    import requests

    q = QUERY.format(keys="|".join(KEYS), bbox=bbox)
    last = None
    for attempt in range(8):
        url = MIRRORS[attempt % len(MIRRORS)]
        try:
            r = requests.post(url, data={"data": q}, timeout=300, headers=UA)
            if r.status_code in (429, 504, 502, 503):
                raise RuntimeError(f"HTTP {r.status_code} (busy)")
            r.raise_for_status()
            return r.json()["elements"]
        except Exception as e:  # noqa: BLE001
            last = e
            wait = min(120, 5 * 2 ** attempt)
            print(f"[fetch] {label}: {e}; retry in {wait}s", file=sys.stderr)
            time.sleep(wait)
    raise SystemExit(f"[fetch] giving up on {label}: {last}")


def fetch_area_overpass(area: config.Area, out_dir: Path) -> Path:
    out = out_dir / f"{area.key}.json"
    if out.exists():
        print(f"[fetch] {area.key}: have {out}, skipping")
        return out
    tiles = list(_tiles(area))
    seen: dict[tuple[str, int], dict] = {}
    for i, bbox in enumerate(tiles, 1):
        print(f"[fetch] {area.key}: tile {i}/{len(tiles)} {bbox}")
        for el in _overpass(bbox, f"{area.key} tile {i}"):
            seen.setdefault((el["type"], el["id"]), el)
        time.sleep(2)
    out_dir.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"elements": list(seen.values())}))
    print(f"[fetch] {area.key}: {len(seen)} elements -> {out}")
    return out


# ----------------------------------------------------------------------------- Geofabrik (local)

PBF_URL = "https://download.geofabrik.de/north-america/canada/new-brunswick-latest.osm.pbf"


def _download_pbf(path: Path) -> Path:
    import requests

    if path.exists() and path.stat().st_size > 0:
        print(f"[fetch] using cached {path}")
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[fetch] downloading {PBF_URL}")
    with requests.get(PBF_URL, stream=True, timeout=600, headers=UA) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        done = 0
        with open(path, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
                done += len(chunk)
                if total:
                    print(f"\r[fetch] {done * 100 // total}%", end="", flush=True)
    print()
    return path


def fetch_geofabrik(areas: list[config.Area], out_dir: Path, pbf: Path) -> None:
    try:
        import osmium
    except ImportError:
        raise SystemExit("pip install osmium   (pyosmium) is needed for --geofabrik")

    pbf = _download_pbf(pbf)
    todo = [a for a in areas if not (out_dir / f"{a.key}.json").exists()]
    if not todo:
        print("[fetch] all areas present")
        return
    boxes = {a.key: (a.south, a.west, a.north, a.east) for a in todo}

    def in_box(lat, lon, b):
        return b[0] <= lat <= b[2] and b[1] <= lon <= b[3]

    def wanted(tags):
        return any(k in tags for k in KEYS)

    # pass 1: multipolygon relations whose members we must keep even when untagged
    class Rels(osmium.SimpleHandler):
        def __init__(self):
            super().__init__()
            self.member_ways: dict[str, set[int]] = {k: set() for k in boxes}
            self.rels: dict[str, list[dict]] = {k: [] for k in boxes}
            self.rel_members: dict[int, list[int]] = {}

        def relation(self, r):
            tags = dict(r.tags)
            if tags.get("type") != "multipolygon" or not wanted(tags):
                return
            members = [m.ref for m in r.members if m.type == "w"]
            self.rel_members[r.id] = members
            self._pending = getattr(self, "_pending", [])
            self._pending.append((r.id, tags, [(m.type, m.ref, m.role) for m in r.members]))

    rels = Rels()
    rels.apply_file(str(pbf))
    pending = getattr(rels, "_pending", [])
    all_member_ways = {ref for _, _, ms in pending for t, ref, _ in ms if t == "w"}

    # pass 2: ways (with node locations) -> decide per area, keep member ways of relations
    class Ways(osmium.SimpleHandler):
        def __init__(self):
            super().__init__()
            self.ways: dict[str, dict[int, dict]] = {k: {} for k in boxes}
            self.nodes: dict[str, dict[int, tuple[float, float]]] = {k: {} for k in boxes}
            self.way_box: dict[int, tuple] = {}
            self.member_geo: dict[int, tuple[list[int], list[tuple[float, float]]]] = {}

        def node(self, n):
            tags = dict(n.tags)
            if not tags or not wanted(tags):
                return
            for k, b in boxes.items():
                if in_box(n.location.lat, n.location.lon, b):
                    self.nodes[k][n.id] = (n.location.lat, n.location.lon)
                    self.ways[k][("n", n.id)] = {"type": "node", "id": n.id, "lat": n.location.lat, "lon": n.location.lon, "tags": tags}

        def way(self, w):
            tags = dict(w.tags)
            pts = [(nd.ref, nd.location.lat, nd.location.lon) for nd in w.nodes if nd.location.valid()]
            if not pts:
                return
            lats = [p[1] for p in pts]
            lons = [p[2] for p in pts]
            wb = (min(lats), min(lons), max(lats), max(lons))
            is_member = w.id in all_member_ways
            if is_member:
                self.member_geo[w.id] = ([p[0] for p in pts], [(p[1], p[2]) for p in pts])
            if not tags or not wanted(tags):
                if not is_member:
                    return
            for k, b in boxes.items():
                if wb[2] < b[0] or wb[0] > b[2] or wb[3] < b[1] or wb[1] > b[3]:
                    continue
                if not (tags and wanted(tags)) and not is_member:
                    continue
                self.ways[k][w.id] = {"type": "way", "id": w.id, "nodes": [p[0] for p in pts], "tags": tags}
                for ref, lat, lon in pts:
                    self.nodes[k][ref] = (lat, lon)

    ways = Ways()
    ways.apply_file(str(pbf), locations=True)

    for a in todo:
        k = a.key
        b = boxes[k]
        elements = []
        for nid, (lat, lon) in ways.nodes[k].items():
            elements.append({"type": "node", "id": nid, "lat": lat, "lon": lon})
        for key, w in ways.ways[k].items():
            if isinstance(key, tuple):
                elements.append(w)          # tagged node
            else:
                elements.append(w)
        # relations whose member ways touch this area
        for rid, tags, members in pending:
            touch = False
            for t, ref, _ in members:
                if t == "w" and ref in ways.member_geo:
                    for lat, lon in ways.member_geo[ref][1]:
                        if in_box(lat, lon, b):
                            touch = True
                            break
                if touch:
                    break
            if not touch:
                continue
            for t, ref, _ in members:
                if t == "w" and ref in ways.member_geo and ref not in ways.ways[k]:
                    refs, pts = ways.member_geo[ref]
                    elements.append({"type": "way", "id": ref, "nodes": refs, "tags": {}})
                    for r_, (lat, lon) in zip(refs, pts):
                        if r_ not in ways.nodes[k]:
                            elements.append({"type": "node", "id": r_, "lat": lat, "lon": lon})
            elements.append({"type": "relation", "id": rid, "tags": tags,
                             "members": [{"type": "way" if t == "w" else t, "ref": ref, "role": role} for t, ref, role in members]})
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{k}.json"
        out.write_text(json.dumps({"elements": elements}))
        print(f"[fetch] {k}: {len(elements)} elements -> {out}")


# ----------------------------------------------------------------------------- CLI

def main(argv: list[str]) -> None:
    import argparse

    p = argparse.ArgumentParser(prog="nbmap fetch", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", default="data/osm")
    p.add_argument("--area", action="append", help="only these area keys (repeatable)")
    p.add_argument("--geofabrik", action="store_true", help="use the Geofabrik New Brunswick extract instead of Overpass")
    p.add_argument("--pbf", default="data/new-brunswick-latest.osm.pbf")
    a = p.parse_args(argv)
    out_dir = Path(a.out)
    areas = [ar for ar in config.AREAS if not a.area or ar.key in a.area]
    if a.geofabrik:
        fetch_geofabrik(areas, out_dir, Path(a.pbf))
        return
    for area in areas:
        fetch_area_overpass(area, out_dir)


if __name__ == "__main__":
    main(sys.argv[1:])
