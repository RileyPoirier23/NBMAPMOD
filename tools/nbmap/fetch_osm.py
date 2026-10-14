"""Download OpenStreetMap data for every configured area via the Overpass API.

Usage:  python -m nbmap fetch [--out data/osm] [--area moncton]

OSM is open data (ODbL). Output: one JSON file per area in Overpass JSON format.
If you already have an export (overpass-turbo "Export -> raw OSM data" JSON) you
can drop it in the output folder named <area>.json and skip this step.
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

# Everything we render. Relations give us lakes, rivers, big forests and multipolygon buildings.
QUERY = """
[out:json][timeout:600][maxsize:1073741824];
(
  way["highway"]({bbox});
  way["railway"]({bbox});
  way["building"]({bbox});
  relation["building"]({bbox});
  way["natural"]({bbox});
  relation["natural"]({bbox});
  way["landuse"]({bbox});
  relation["landuse"]({bbox});
  way["leisure"]({bbox});
  relation["leisure"]({bbox});
  way["amenity"]({bbox});
  relation["amenity"]({bbox});
  way["waterway"]({bbox});
  relation["waterway"]({bbox});
  way["water"]({bbox});
  way["wetland"]({bbox});
  way["barrier"]({bbox});
  way["man_made"]({bbox});
  way["power"]({bbox});
  way["shop"]({bbox});
  node["amenity"]({bbox});
  node["shop"]({bbox});
  node["place"]({bbox});
  node["natural"="tree"]({bbox});
  node["highway"="street_lamp"]({bbox});
);
(._;>;);
out body;
"""


def fetch_area(area: config.Area, out_dir: Path, force: bool = False) -> Path:
    import requests

    out = out_dir / f"{area.key}.json"
    if out.exists() and not force:
        print(f"[fetch] {area.key}: already have {out} ({out.stat().st_size//1024} KiB), skipping")
        return out
    q = QUERY.format(bbox=area.bbox)
    last_err: Exception | None = None
    for attempt in range(6):
        url = MIRRORS[attempt % len(MIRRORS)]
        try:
            print(f"[fetch] {area.key}: {url} (attempt {attempt+1})")
            r = requests.post(url, data={"data": q}, timeout=900,
                              headers={"User-Agent": "nbmap-zomboid-generator/0.1 (github.com/RileyPoirier23/nbmapmod)"})
            if r.status_code == 429 or r.status_code == 504:
                raise RuntimeError(f"HTTP {r.status_code} (busy)")
            r.raise_for_status()
            data = r.json()
            if "elements" not in data:
                raise RuntimeError(f"unexpected response: {str(data)[:200]}")
            out_dir.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(data))
            print(f"[fetch] {area.key}: {len(data['elements'])} elements -> {out}")
            return out
        except Exception as e:  # noqa: BLE001
            last_err = e
            wait = 2 ** attempt * 5
            print(f"[fetch] {area.key}: failed ({e}); retrying in {wait}s", file=sys.stderr)
            time.sleep(wait)
    raise SystemExit(f"[fetch] giving up on {area.key}: {last_err}")


def main(argv: list[str]) -> None:
    import argparse

    p = argparse.ArgumentParser(prog="nbmap fetch")
    p.add_argument("--out", default="data/osm")
    p.add_argument("--area", action="append", help="only these area keys (repeatable)")
    p.add_argument("--force", action="store_true")
    a = p.parse_args(argv)
    out_dir = Path(a.out)
    for area in config.AREAS:
        if a.area and area.key not in a.area:
            continue
        fetch_area(area, out_dir, a.force)
        time.sleep(3)  # be polite to Overpass


if __name__ == "__main__":
    main(sys.argv[1:])
