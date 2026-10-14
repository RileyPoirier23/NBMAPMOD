"""Parse Overpass JSON into shapely geometries in tile coordinates."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.ops import linemerge, polygonize, unary_union

from . import geo

AREA_KEYS = ("building", "natural", "landuse", "leisure", "amenity", "water", "wetland", "shop", "man_made", "power")
AREA_LINE_TAGS = {  # these are lines even when closed
    ("natural", "tree_row"), ("natural", "cliff"), ("barrier", "*"), ("highway", "*"), ("railway", "*"),
    ("waterway", "river"), ("waterway", "stream"), ("waterway", "ditch"), ("waterway", "drain"), ("waterway", "canal"),
    ("power", "line"), ("power", "minor_line"), ("man_made", "pipeline"),
}


@dataclass
class Feature:
    osm_id: int
    kind: str            # "node" | "way" | "relation"
    tags: dict
    geom: object         # shapely geometry in tile coords
    bounds: tuple = field(default=None)

    def __post_init__(self):
        self.bounds = self.geom.bounds

    def tag(self, k: str, default=None):
        return self.tags.get(k, default)


@dataclass
class OSMData:
    features: list[Feature]
    nodes: dict[int, tuple[float, float]]

    def by(self, key: str) -> list[Feature]:
        return [f for f in self.features if key in f.tags]

    @property
    def bounds(self):
        xs0 = min(f.bounds[0] for f in self.features)
        ys0 = min(f.bounds[1] for f in self.features)
        xs1 = max(f.bounds[2] for f in self.features)
        ys1 = max(f.bounds[3] for f in self.features)
        return xs0, ys0, xs1, ys1


def _is_area(tags: dict, closed: bool) -> bool:
    if not closed:
        return False
    if tags.get("area") == "yes":
        return True
    if tags.get("area") == "no":
        return False
    for k, v in tags.items():
        if (k, "*") in AREA_LINE_TAGS or (k, v) in AREA_LINE_TAGS:
            return False
    return any(k in tags for k in AREA_KEYS)


def load(paths: Iterable[Path]) -> OSMData:
    nodes: dict[int, tuple[float, float]] = {}
    ways: dict[int, dict] = {}
    rels: list[dict] = []
    seen_ways: set[int] = set()
    for p in paths:
        data = json.loads(Path(p).read_text())
        for el in data["elements"]:
            t = el["type"]
            if t == "node":
                if el["id"] not in nodes:
                    nodes[el["id"]] = geo.lonlat_to_tile(el["lon"], el["lat"])
                if el.get("tags"):
                    ways.setdefault(("n", el["id"]), {"type": "node", "id": el["id"], "tags": el["tags"]})
            elif t == "way":
                if el["id"] not in seen_ways:
                    seen_ways.add(el["id"])
                    ways[el["id"]] = el
            elif t == "relation":
                rels.append(el)
    feats: list[Feature] = []
    for key, w in ways.items():
        if w.get("type") == "node":
            x, y = nodes[w["id"]]
            feats.append(Feature(w["id"], "node", w["tags"], Point(x, y)))
            continue
        pts = [nodes[n] for n in w.get("nodes", []) if n in nodes]
        if len(pts) < 2:
            continue
        tags = w.get("tags", {})
        closed = pts[0] == pts[-1] and len(pts) >= 4
        if _is_area(tags, closed):
            poly = Polygon(pts)
            if not poly.is_valid:
                poly = poly.buffer(0)
            if poly.is_empty:
                continue
            feats.append(Feature(w["id"], "way", tags, poly))
        elif tags:
            feats.append(Feature(w["id"], "way", tags, LineString(pts)))
    # multipolygon relations (lakes with islands, big forests, courtyard buildings)
    member_ways_used: set[int] = set()
    for r in rels:
        tags = r.get("tags", {})
        if tags.get("type") != "multipolygon":
            continue
        outers, inners = [], []
        for m in r.get("members", []):
            if m["type"] != "way" or m["ref"] not in ways:
                continue
            w = ways[m["ref"]]
            pts = [nodes[n] for n in w.get("nodes", []) if n in nodes]
            if len(pts) < 2:
                continue
            (inners if m.get("role") == "inner" else outers).append(LineString(pts))
            if not w.get("tags"):
                member_ways_used.add(m["ref"])
        if not outers:
            continue
        try:
            outer_polys = list(polygonize(unary_union(linemerge(outers) if len(outers) > 1 else outers[0])))
            inner_polys = list(polygonize(unary_union(linemerge(inners) if len(inners) > 1 else inners[0]))) if inners else []
            geom = unary_union(outer_polys)
            if inner_polys:
                geom = geom.difference(unary_union(inner_polys))
            if geom.is_empty:
                continue
            feats.append(Feature(r["id"], "relation", tags, geom))
        except Exception:  # noqa: BLE001 - a broken relation shouldn't kill the build
            continue
    return OSMData(feats, nodes)


def polygons(geom) -> list[Polygon]:
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, MultiPolygon):
        return list(geom.geoms)
    if hasattr(geom, "geoms"):
        out = []
        for g in geom.geoms:
            out.extend(polygons(g))
        return out
    return []


def lines(geom) -> list[LineString]:
    if isinstance(geom, LineString):
        return [geom]
    if hasattr(geom, "geoms"):
        out = []
        for g in geom.geoms:
            out.extend(lines(g))
        return out
    return []
