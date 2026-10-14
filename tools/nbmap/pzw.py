"""WorldEd project (.pzw) + Rules.txt so the whole thing opens in WorldEd in one go."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from . import config
from .config import CELL, CHUNK_CELLS

DATA = Path(__file__).parent / "data"


def generate(out: Path) -> Path:
    world = json.loads((out / "world.json").read_text())
    lots = json.loads((out / "lots.json").read_text()) if (out / "lots.json").exists() else []
    x0, y0, x1, y1 = world["cell_bounds"]
    # WorldEd worlds start at cell 0,0; we keep absolute cell numbers so the lot files land in the right place
    W, H = x1 + 1, y1 + 1
    export = out / "export_tmx"
    lots_dir = out / "mod" / config.MOD_ID / "media" / "maps" / config.MAP_FOLDER
    x = ['<?xml version="1.0" encoding="UTF-8"?>', f'<world version="1" width="{W}" height="{H}">']
    x.append(f'    <BMPToTMX rulesFile="Rules.txt" blendsFile="Blends.txt" mapbaseFile="MapBaseXML.txt" exportDir="{export.as_posix()}" '
             'assignMapsToWorld="true" warnUnknownColors="true" warnTMXExists="false"/>')
    x.append(f'    <GenerateLots exportDir="{lots_dir.as_posix()}" zombieSpawnMap="{(out / "zombie_spawn_map.png").as_posix()}" '
             f'tileDefFolder="" worldOrigin="0,0"/>')
    for ch in world["chunks"]:
        p = out / ch["base"]
        x.append(f'    <bmp path="{p.as_posix()}" x="{ch["cx"] * CELL}" y="{ch["cy"] * CELL}" width="{ch["size"]}" height="{ch["size"]}"/>')
    for ch in world["chunks"]:
        p = out / ch["veg"]
        x.append(f'    <bmp path="{p.as_posix()}" x="{ch["cx"] * CELL}" y="{ch["cy"] * CELL}" width="{ch["size"]}" height="{ch["size"]}"/>')
    for zt in ("TownZone", "Forest", "DeepForest", "Vegitation", "FarmLand", "Farm", "TrailerPark", "Vehicle", "Nav"):
        x.append(f'    <objecttype name="{zt}"/>')
    x.append('    <propertydef name="Direction" default="N"/>')
    bycell: dict[tuple[int, int], list[dict]] = {}
    for l in lots:
        bycell.setdefault(tuple(l["cell"]), []).append(l)
    for cx, cy in sorted({tuple(c) for c in world["cells"]}):
        x.append(f'    <cell x="{cx}" y="{cy}" map="">')
        for l in bycell.get((cx, cy), []):
            x.append(f'        <lot x="{l["x"]}" y="{l["y"]}" level="0" file="{(out / l["file"]).as_posix()}"/>')
        x.append("    </cell>")
    x.append("</world>")
    path = out / "NewBrunswick.pzw"
    path.write_text("\n".join(x) + "\n")
    shutil.copy(DATA / "Rules.txt", out / "Rules.txt")
    (out / "README_WORLDED.txt").write_text(WORLDED_STEPS)
    print(f"[pzw] {path}: {W}x{H} cells, {len(world['chunks'])} bitmaps, {len(lots)} lots")
    return path


WORLDED_STEPS = """How to turn this build folder into the playable map
=====================================================
1. Install TileZed + WorldEd (Project Zomboid "Mapping tools", or the B41 TileZed from theindiestone.com).
   Copy Blends.txt and MapBaseXML.txt from your WorldEd install next to NewBrunswick.pzw.
   Rules.txt here is already set up for the colours in bmp/*.png.
2. TileZed: Tools > Tilesets, point it at your game's media/texturepacks (or the 2x tiles) so tile names resolve.
3. WorldEd: File > Open > NewBrunswick.pzw.
   If WorldEd refuses the file, create a new world of the same size and add the bmp/ images via
   File > BMP to TMX > Settings (the x/y of each image is in NewBrunswick.pzw).
4. File > BMP to TMX > All cells. This writes one TMX per cell into export_tmx/.
5. (The lots are already assigned in the project.) File > Generate Lots > All cells with export dir
   mod/NBMap_Moncton/media/maps/Moncton, NB/. This writes *.lotheader / *.lotpack (+ chunkdata).
6. Copy mod/NBMap_Moncton to %USERPROFILE%/Zomboid/mods/ (or publish to the Workshop from the game).
7. Open BuildingEd on any buildings/*.tbx to furnish interiors; rebuild lots after editing.
"""
