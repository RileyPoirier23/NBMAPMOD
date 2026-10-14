"""python -m nbmap <command>

  fetch     download OSM data for every area (needs internet)
  build     render terrain, buildings, zones, worldmap and the WorldEd project
  all       fetch + build
"""
from __future__ import annotations

import sys
from pathlib import Path


def _load(osm_dir: Path):
    from . import osm

    files = sorted(osm_dir.glob("*.json"))
    if not files:
        raise SystemExit(f"no OSM json in {osm_dir}; run `python -m nbmap fetch` first")
    print(f"[load] {len(files)} OSM files: {', '.join(f.stem for f in files)}")
    data = osm.load(files)
    print(f"[load] {len(data.features)} features")
    return data


def build(argv: list[str]) -> None:
    import argparse

    from . import buildings, modfiles, pzw, render, worldmap, zones

    p = argparse.ArgumentParser(prog="nbmap build")
    p.add_argument("--osm", default="data/osm")
    p.add_argument("--out", default="build")
    p.add_argument("--skip-render", action="store_true", help="reuse existing bmp/ and world.json")
    p.add_argument("--no-zombie-map", action="store_true")
    p.add_argument("--chunk", action="append", help="only render chunk kx,ky (repeatable, for previews)")
    a = p.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    data = _load(Path(a.osm))
    w = render.World(data, out)
    print(f"[build] {len(w.active)} active cells, {len(w.chunks())} chunks of {render.CHUNK_CELLS}x{render.CHUNK_CELLS} cells")
    if not a.skip_render:
        only = {tuple(int(v) for v in c.split(",")) for c in a.chunk} if a.chunk else None
        chunks = w.render_all(only)
        render.write_world_json(out, w, chunks)
    buildings.generate(data, out)
    zones.generate(data, out, zombie_map=not a.no_zombie_map)
    worldmap.generate(data, out)
    modfiles.generate(out)
    pzw.generate(out)
    print("[build] done. Next: open build/NewBrunswick.pzw in WorldEd (see build/README_WORLDED.txt)")


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return
    cmd, rest = argv[0], argv[1:]
    if cmd == "fetch":
        from . import fetch_osm

        fetch_osm.main(rest)
    elif cmd == "build":
        build(rest)
    elif cmd == "all":
        from . import fetch_osm

        fetch_osm.main([])
        build(rest)
    else:
        raise SystemExit(f"unknown command {cmd}\n{__doc__}")
