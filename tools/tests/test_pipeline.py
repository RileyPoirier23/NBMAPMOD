"""Offline smoke test: synthetic OSM fixture -> full build. Run: python -m pytest tools/tests or python tools/tests/test_pipeline.py"""
import json
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent


def test_build():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        subprocess.run([sys.executable, str(HERE / "make_fixture.py"), str(td / "osm")], check=True)
        subprocess.run([sys.executable, "-m", "nbmap", "build", "--osm", str(td / "osm"), "--out", str(td / "build")], cwd=TOOLS, check=True)
        b = td / "build"
        world = json.loads((b / "world.json").read_text())
        assert world["chunks"], "no chunks rendered"
        for ch in world["chunks"]:
            assert (b / ch["base"]).exists() and (b / ch["veg"]).exists()
        lots = json.loads((b / "lots.json").read_text())
        assert len(lots) >= 15
        for l in lots:
            ET.parse(b / l["file"])                      # every .tbx is well-formed XML
        mapdir = b / "mod" / "NBMap_Moncton" / "media" / "maps" / "Moncton, NB"
        ET.parse(mapdir / "worldmap.xml")
        xml = (mapdir / "worldmap.xml").read_text()
        pois = json.loads((b / "pois.json").read_text())
        assert any(p["snapped_to"] for p in pois), "POI snapping failed"
        assert 'name="poi"' in xml and "Hopewell Rocks" in xml
        assert 'value="Main Street"' in xml and 'value="Trans-Canada Highway"' in xml
        obj = (mapdir / "objects.lua").read_text()
        assert obj.count("{") == obj.count("}") and "TownZone" in obj and 'type = "Vehicle"' in obj
        assert "function SpawnPoints" in (mapdir / "spawnpoints.lua").read_text()
        ET.parse(b / "NewBrunswick.pzw")
        assert (b / "mod" / "NBMap_Moncton" / "mod.info").exists()
        assert (b / "zombie_spawn_map.png").exists()
        print("ok:", len(lots), "buildings,", len(world["cells"]), "cells")


if __name__ == "__main__":
    test_build()
