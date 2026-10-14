"""worldmap.xml for the in-game map: every street with its real name, buildings, water, forest."""
from __future__ import annotations

import json
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

from . import config
from .config import CELL
from .osm import OSMData, lines, polygons

HIGHWAY_MAP = {  # OSM -> vanilla worldmap style classes
    "motorway": "primary", "motorway_link": "primary", "trunk": "primary", "trunk_link": "primary",
    "primary": "primary", "primary_link": "secondary", "secondary": "secondary", "secondary_link": "tertiary",
    "tertiary": "tertiary", "tertiary_link": "tertiary", "unclassified": "residential", "residential": "residential",
    "living_street": "residential", "service": "service", "track": "trail", "path": "trail", "footway": "trail",
    "cycleway": "trail", "bridleway": "trail", "pedestrian": "residential",
}


def _feature(out: list, geom_type: str, coords, props: dict):
    out.append("        <feature>")
    out.append(f'            <geometry type="{geom_type}">')
    out.append("                <coordinates>")
    for x, y in coords:
        out.append(f'                    <point x="{x:.1f}" y="{y:.1f}"/>')
    out.append("                </coordinates>")
    out.append("            </geometry>")
    out.append("            <properties>")
    for k, v in props.items():
        if v is not None and v != "":
            out.append(f"                <property name={quoteattr(k)} value={quoteattr(str(v))}/>")
    out.append("            </properties>")
    out.append("        </feature>")


def generate(data: OSMData, out: Path) -> Path:
    world = json.loads((out / "world.json").read_text())
    active = {tuple(c) for c in world["cells"]}
    lots = {(l["x"], l["y"]): l for l in json.loads((out / "lots.json").read_text())} if (out / "lots.json").exists() else {}
    percell: dict[tuple[int, int], list[str]] = {}

    def cell_of(f):
        x0, y0, x1, y1 = f.bounds
        return int((x0 + x1) / 2 // CELL), int((y0 + y1) / 2 // CELL)

    for f in data.features:
        c = cell_of(f)
        if c not in active:
            continue
        buf = percell.setdefault(c, [])
        hw = f.tag("highway")
        if hw in HIGHWAY_MAP and lines(f.geom):
            for ln in lines(f.geom):
                _feature(buf, "LineString", ln.coords, {"highway": HIGHWAY_MAP[hw], "name": f.tag("name"), "ref": f.tag("ref"),
                                                        "bridge": f.tag("bridge"), "osm_highway": hw})
        elif f.tag("railway") in ("rail", "disused", "abandoned") and lines(f.geom):
            for ln in lines(f.geom):
                _feature(buf, "LineString", ln.coords, {"railway": "rail", "name": f.tag("name")})
        elif "building" in f.tags and polygons(f.geom):
            for p in polygons(f.geom):
                props = {"building": "yes", "name": f.tag("name"), "amenity": f.tag("amenity"), "shop": f.tag("shop"),
                         "addr:housenumber": f.tag("addr:housenumber"), "addr:street": f.tag("addr:street")}
                _feature(buf, "Polygon", p.exterior.coords, props)
        elif (f.tag("natural") == "water" or f.tag("water") or f.tag("waterway") == "riverbank") and polygons(f.geom):
            for p in polygons(f.geom):
                _feature(buf, "Polygon", p.exterior.coords, {"natural": "water", "name": f.tag("name")})
        elif f.tag("waterway") in ("river", "stream") and lines(f.geom):
            for ln in lines(f.geom):
                _feature(buf, "LineString", ln.coords, {"waterway": f.tag("waterway"), "name": f.tag("name")})
        elif (f.tag("landuse") == "forest" or f.tag("natural") in ("wood", "scrub")) and polygons(f.geom):
            for p in polygons(f.geom):
                _feature(buf, "Polygon", p.exterior.coords, {"natural": "forest", "name": f.tag("name")})
        elif f.tag("leisure") in ("park", "golf_course", "pitch", "playground", "nature_reserve") and polygons(f.geom):
            for p in polygons(f.geom):
                _feature(buf, "Polygon", p.exterior.coords, {"leisure": f.tag("leisure"), "name": f.tag("name")})
        elif f.tag("landuse") in ("farmland", "cemetery", "industrial", "commercial", "retail", "residential") and polygons(f.geom):
            for p in polygons(f.geom):
                _feature(buf, "Polygon", p.exterior.coords, {"landuse": f.tag("landuse"), "name": f.tag("name")})
        elif f.tag("place") and f.geom.geom_type == "Point":
            _feature(buf, "Point", [(f.geom.x, f.geom.y)], {"place": f.tag("place"), "name": f.tag("name")})
    if (out / "pois.json").exists():
        for poi in json.loads((out / "pois.json").read_text()):
            c = tuple(poi["cell"])
            buf = percell.setdefault(c, [])
            _feature(buf, "Point", [(poi["x"], poi["y"])], {"poi": poi["kind"], "name": poi["name"], "place": "poi"})
    xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<world version="1.0">']
    for (cx, cy), feats in sorted(percell.items()):
        xml.append(f'    <cell x="{cx}" y="{cy}">')
        xml.extend(feats)
        xml.append("    </cell>")
    xml.append("</world>")
    mapdir = out / "mod" / config.MOD_ID / "media" / "maps" / config.MAP_FOLDER
    mapdir.mkdir(parents=True, exist_ok=True)
    path = mapdir / "worldmap.xml"
    path.write_text("\n".join(xml) + "\n", encoding="utf-8")
    nfeat = sum(len(v) for v in percell.values()) // 8
    print(f"[worldmap] {path} ({len(percell)} cells)")
    return path
