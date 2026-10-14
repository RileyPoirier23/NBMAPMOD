"""Static mod files: mod.info, map.info, poster, translations."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from . import config

DESCRIPTION = (
    "A 1:1 recreation of south-eastern New Brunswick, Canada built from OpenStreetMap: "
    "Moncton, Dieppe and Riverview, Salisbury, Petitcodiac and Havelock, joined by Route 2 "
    "(Trans-Canada), Route 106, Route 112 and Route 880. Every street carries its real name on the "
    "in-game map; buildings stand on their real footprints; forests, fields, marshes and the "
    "Petitcodiac River are where they really are. Map data (c) OpenStreetMap contributors, ODbL."
)


def generate(out: Path) -> Path:
    mod = out / "mod" / config.MOD_ID
    mapdir = mod / "media" / "maps" / config.MAP_FOLDER
    mapdir.mkdir(parents=True, exist_ok=True)
    (mod / "mod.info").write_text(
        f"name={config.MOD_NAME}\n"
        f"id={config.MOD_ID}\n"
        f"description={DESCRIPTION}\n"
        "poster=poster.png\n"
        "url=https://github.com/RileyPoirier23/nbmapmod\n"
        "versionMin=41.78\n"
    )
    (mapdir / "map.info").write_text(
        f"title={config.MOD_NAME}\n"
        "lots=Muldraugh, KY\n"
        f"description={DESCRIPTION}\n"
        "fixed2x=true\n"
    )
    # poster: NB flag colours, no trademarked artwork
    img = Image.new("RGB", (256, 256), (218, 41, 28))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 255, 96], fill=(255, 205, 0))
    d.rectangle([0, 96, 255, 102], fill=(0, 0, 0))
    d.text((12, 110), "NEW BRUNSWICK", fill=(255, 255, 255))
    d.text((12, 130), "Moncton - Salisbury", fill=(255, 255, 255))
    d.text((12, 146), "Petitcodiac - Havelock", fill=(255, 255, 255))
    d.text((12, 180), "1:1 from OpenStreetMap", fill=(255, 205, 0))
    img.save(mod / "poster.png")
    img.save(mapdir / "thumb.png")
    print(f"[modfiles] {mod}")
    return mod
