"""Points of interest: landmarks named on the in-game map, snapped to real OSM features."""
from __future__ import annotations

import json
from pathlib import Path

from shapely.geometry import Point

from . import config, geo
from .osm import OSMData

SNAP_RADIUS = 1500   # tiles (metres)


def resolve(data: OSMData) -> list[dict]:
    named = [f for f in data.features if f.tag("name")]
    out = []
    for title, kind, lat, lon, needle in config.POIS:
        x, y = geo.lonlat_to_tile(lon, lat)
        p = Point(x, y)
        best, bestd = None, SNAP_RADIUS
        n = needle.lower()
        for f in named:
            if n in f.tag("name").lower():
                d = f.geom.distance(p)
                if d < bestd:
                    best, bestd = f, d
        if best is not None:
            c = best.geom.centroid
            x, y, snapped = c.x, c.y, best.tag("name")
        else:
            snapped = None
        out.append(dict(name=title, kind=kind, x=int(x), y=int(y), cell=[int(x // config.CELL), int(y // config.CELL)],
                        snapped_to=snapped, lat=lat, lon=lon))
    return out


def generate(data: OSMData, out: Path) -> list[dict]:
    pois = resolve(data)
    (out / "pois.json").write_text(json.dumps(pois, indent=1))
    lines = ["# Points of interest", "", "| Name | Kind | Tiles (x, y) | Cell | Snapped to OSM |", "| --- | --- | --- | --- | --- |"]
    for p in pois:
        lines.append(f"| {p['name']} | {p['kind']} | {p['x']}, {p['y']} | {p['cell'][0]}, {p['cell'][1]} | {p['snapped_to'] or '(approximate)'} |")
    (out / "POIS.md").write_text("\n".join(lines) + "\n")
    snapped = sum(1 for p in pois if p["snapped_to"])
    print(f"[pois] {len(pois)} points of interest, {snapped} snapped to named OSM features")
    return pois
