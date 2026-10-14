"""WorldEd project (.pzw) in the exact layout pzworlded's WorldWriter produces, plus the
default Rules/Blends/MapBase files, so the build folder opens in WorldEd in one go."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from . import config
from .config import CELL

DATA = Path(__file__).parent / "data" / "worlded"


def generate(out: Path) -> Path:
    world = json.loads((out / "world.json").read_text())
    lots = json.loads((out / "lots.json").read_text()) if (out / "lots.json").exists() else []
    x0, y0, x1, y1 = world["cell_bounds"]
    W, H = x1 + 1, y1 + 1
    mapdir = f"mod/{config.MOD_ID}/media/maps/{config.MOD_FOLDER_SAFE}"
    x = ['<?xml version="1.0" encoding="UTF-8"?>', f'<world version="1.0" width="{W}" height="{H}">']
    x.append("    <BMPToTMX>")
    x.append('        <tmxexportdir path="export_tmx"/>')
    x.append('        <rulesfile path="Rules.txt"/>')
    x.append('        <blendsfile path="Blends.txt"/>')
    x.append('        <mapbasefile path="MapBaseXML.txt"/>')
    x.append('        <assign-maps-to-world checked="true"/>')
    x.append('        <warn-unknown-colors checked="true"/>')
    x.append('        <compress checked="true"/>')
    x.append('        <copy-pixels checked="true"/>')
    x.append('        <update-existing checked="false"/>')
    x.append("    </BMPToTMX>")
    x.append("    <GenerateLots>")
    x.append(f'        <exportdir path="{mapdir}"/>')
    x.append('        <ZombieSpawnMap path="zombie_spawn_map.png"/>')
    x.append('        <TileDefFolder path=""/>')
    x.append('        <worldOrigin origin="0,0"/>')
    x.append("    </GenerateLots>")
    x.append("    <LuaSettings>")
    x.append(f'        <spawnPointsFile path="{mapdir}/spawnpoints.lua"/>')
    x.append(f'        <worldObjectsFile path="{mapdir}/objects.lua"/>')
    x.append("    </LuaSettings>")
    for ch in world["chunks"]:
        x.append(f'    <bmp path="{ch["base"]}" x="{ch["cx"] * CELL}" y="{ch["cy"] * CELL}" width="{ch["size"]}" height="{ch["size"]}"/>')
    for ch in world["chunks"]:
        x.append(f'    <bmp path="{ch["veg"]}" x="{ch["cx"] * CELL}" y="{ch["cy"] * CELL}" width="{ch["size"]}" height="{ch["size"]}"/>')
    x.append('    <propertydef name="Direction" default="N"/>')
    for zt in ("TownZone", "Forest", "DeepForest", "Vegitation", "FarmLand", "Farm", "TrailerPark", "Vehicle", "Nav"):
        x.append(f'    <objecttype name="{zt}"/>')
    bycell: dict[tuple[int, int], list[dict]] = {}
    for l in lots:
        bycell.setdefault(tuple(l["cell"]), []).append(l)
    for cx, cy in sorted({tuple(c) for c in world["cells"]}):
        cell_lots = bycell.get((cx, cy), [])
        if not cell_lots:
            continue   # WorldWriter skips empty cells too
        x.append(f'    <cell x="{cx}" y="{cy}" map="">')
        for l in cell_lots:
            # lot x/y are cell-relative tiles (MapComposite::addMap(info, lot->pos(), level))
            x.append(f'        <lot x="{l["x"] - cx * CELL}" y="{l["y"] - cy * CELL}" level="0" '
                     f'width="{l["w"]}" height="{l["h"]}" map="{l["file"]}"/>')
        x.append("    </cell>")
    x.append("</world>")
    path = out / "NewBrunswick.pzw"
    path.write_text("\n".join(x) + "\n")
    rules = (DATA / "Rules.txt").read_text() + (DATA / "Rules_nb_extra.txt").read_text()
    (out / "Rules.txt").write_text(rules)
    shutil.copy(DATA / "Blends.txt", out / "Blends.txt")
    shutil.copy(DATA / "MapBaseXML.txt", out / "MapBaseXML.txt")
    (out / "export_tmx").mkdir(exist_ok=True)
    (out / "README_WORLDED.txt").write_text(WORLDED_STEPS)
    print(f"[pzw] {path}: {W}x{H} cells, {len(world['chunks'])} bitmaps, {len(lots)} lots")
    return path


WORLDED_STEPS = """How to turn this build folder into the playable map
=====================================================
1. Install TileZed + WorldEd + BuildingEd (The Indie Stone mapping tools, or the maintained
   community build at https://github.com/Unjammer/PZ_Mapping_Tools).
   Rules.txt / Blends.txt / MapBaseXML.txt here are WorldEd's defaults plus NB extras.
2. TileZed: Tools > Tilesets, point it at your game's media/texturepacks so tile names resolve.
   BuildingEd: Tiles > Tiles, same thing.
3. WorldEd: File > Open > NewBrunswick.pzw. The project already lists every bitmap at its
   world position and every building lot in its cell.
4. File > BMP to TMX > All cells. Writes one TMX per cell into export_tmx/.
   The world is large; expect this to take a while and need a few GB of RAM.
5. File > Generate Lots > All cells. Writes *.lotheader / *.lotpack / chunkdata into
   mod/NBMap_Moncton/media/maps/<map>/ (the export dir is pre-set).
6. Copy mod/NBMap_Moncton to %USERPROFILE%/Zomboid/mods/ and enable it. Spawn in Moncton.
7. To improve a building, open its .tbx in BuildingEd, edit, save, then re-run Generate Lots
   for that cell (right-click the cell > Generate Lots).
"""
