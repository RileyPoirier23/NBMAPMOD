#!/usr/bin/env python3
"""Build the RCMP_NB mod from your Project Zomboid install.

    python tools/rcmp/make_rcmp.py --pz-dir "C:/Program Files (x86)/Steam/steamapps/common/ProjectZomboid" --out mods/RCMP_NB

What it does (all derived from the vanilla files so it tracks game updates):
  * finds every vehicle script whose name contains "Police", recolours its textures to the
    white RCMP livery and writes them to the same relative path inside the mod, so the vanilla
    police vehicles become RCMP cruisers without touching vehicle scripts;
  * renames those vehicles in the UI translation ("... (RCMP)");
  * clones the vanilla police clothing (shirt, t-shirt, trousers, jacket, hat, vest) into new
    RCMP items with recoloured textures: grey duty shirt, navy breeches with the yellow stripe
    tint, red serge tunic, forage cap, Stetson (from the ranger/campaign hat model), vest;
  * writes clothingItems XML + fileGuidTable.xml, and two outfits (RCMP duty, RCMPRiot) that the
    Lua in media/lua/server points police zombies at.
Pixel-art stripes/badges are beyond an automatic recolour: hand-paint over the generated PNGs
in mods/RCMP_NB/media/textures if you want the real decals.
"""
from __future__ import annotations

import argparse
import colorsys
import json
import re
import shutil
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import decals as decal_art  # noqa: E402

DECALS_CFG = Path(__file__).resolve().parent / "decals.json"

NS = uuid.UUID("5d2c7f0e-6b8e-4c2a-9c3b-7a1f0e5c9d11")

# --------------------------------------------------------------------------- colour helpers

def _recolor(img, fn):
    """Apply fn(h, s, v, a) -> (h, s, v) to every pixel."""
    img = img.convert("RGBA")
    px = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            hh, ss, vv = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            nh, ns, nv = fn(hh, ss, vv, a)
            r2, g2, b2 = colorsys.hsv_to_rgb(nh, ns, nv)
            px[x, y] = (int(r2 * 255), int(g2 * 255), int(b2 * 255), a)
    return img


def is_blue(h, s):
    return 0.52 <= h <= 0.75 and s > 0.25


def vehicle_livery(h, s, v, a):
    # black bodywork -> white; keep windows (bluish grey), lights, chrome
    if v < 0.22 and s < 0.35:
        return (h, 0.0, 0.92)
    if is_blue(h, s) and v > 0.3:          # blue doors/decals -> RCMP blue stripe tone
        return (0.62, 0.85, 0.55)
    return (h, s, v)


def grey_shirt(h, s, v, a):
    if is_blue(h, s):
        return (0.08, 0.06, min(0.72, 0.35 + v * 0.5))
    return (h, s, v)


def red_serge(h, s, v, a):
    if is_blue(h, s) or (s < 0.2 and 0.25 < v < 0.9):
        return (0.0, 0.88, max(0.35, min(0.75, v + 0.15)))
    return (h, s, v)


def navy_breeches(h, s, v, a):
    if is_blue(h, s) or (s < 0.25 and v < 0.5):
        return (0.64, 0.75, 0.22)
    if 0.1 <= h <= 0.2 and s > 0.4:         # any existing yellow stripe pixels get the RCMP gold
        return (0.13, 0.95, 0.9)
    return (h, s, v)


def forage_cap(h, s, v, a):
    if is_blue(h, s) or v < 0.3:
        return (0.64, 0.8, 0.2)
    return (h, s, v)


def stetson(h, s, v, a):
    if s < 0.6:
        return (0.09, 0.45, max(0.5, min(0.85, v + 0.2)))
    return (h, s, v)


def vest(h, s, v, a):
    if is_blue(h, s) or v < 0.3:
        return (0.64, 0.5, 0.18)
    return (h, s, v)


CLOTHES = [
    # vanilla item         new item           display name                 recolour     body location kept from source
    ("Shirt_PoliceBlue",   "Shirt_RCMPGrey",  "RCMP Duty Shirt",           grey_shirt),
    ("Shirt_PoliceGrey",   "Shirt_RCMPGreyLS","RCMP Duty Shirt (grey)",    grey_shirt),
    ("Tshirt_PoliceBlue",  "Tshirt_RCMPGrey", "RCMP T-Shirt",              grey_shirt),
    ("Trousers_Police",    "Trousers_RCMP",   "RCMP Breeches",             navy_breeches),
    ("Jacket_Police",      "Jacket_RCMPSerge","RCMP Red Serge Tunic",      red_serge),
    ("Hat_Police",         "Hat_RCMPForage",  "RCMP Forage Cap",           forage_cap),
    ("Hat_Ranger",         "Hat_RCMPStetson", "RCMP Stetson",              stetson),
    ("Vest_BulletPolice",  "Vest_BulletRCMP", "RCMP Bullet Vest",          vest),
    ("Hat_RiotHelmet",     "Hat_RCMPRiot",    "RCMP Riot Helmet",          forage_cap),
]
OUTFITS = {
    "RCMP":      ["Shirt_RCMPGrey", "Trousers_RCMP", "Vest_BulletRCMP", "Hat_RCMPForage"],
    "RCMPRiot":  ["Shirt_RCMPGrey", "Trousers_RCMP", "Vest_BulletRCMP", "Hat_RCMPRiot"],
    "RCMPSerge": ["Jacket_RCMPSerge", "Trousers_RCMP", "Hat_RCMPStetson"],
}

# --------------------------------------------------------------------------- decals

class Decaler:
    def __init__(self, decal_dir: Path, preview: bool):
        from PIL import Image

        self.cfg = json.loads(DECALS_CFG.read_text())["textures"]
        self.art = {p.stem: Image.open(p).convert("RGBA") for p in decal_dir.glob("*.png")}
        self.preview = preview
        self.count = 0

    def apply(self, img, name: str, kind: str):
        from PIL import Image, ImageDraw

        img = img.convert("RGBA")
        W, H = img.size
        for entry in self.cfg:
            if entry["kind"] != kind or entry["match"].lower() not in name.lower():
                continue
            for dc in entry["decals"]:
                art = self.art.get(dc["decal"])
                if art is None:
                    continue
                fx, fy, fw, fh = dc["region"]
                x, y, w, h = int(fx * W), int(fy * H), max(1, int(fw * W)), max(1, int(fh * H))
                layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                if dc.get("tile_x"):
                    tile = art.resize((max(1, int(art.width * h / art.height)), h))
                    for tx in range(0, w, tile.width):
                        layer.alpha_composite(tile, (tx, 0))
                elif dc.get("tile_y"):
                    tile = art.resize((w, max(1, int(art.height * w / art.width))))
                    for ty in range(0, h, tile.height):
                        layer.alpha_composite(tile, (0, ty))
                else:
                    scale = min(w / art.width, h / art.height)
                    fitted = art.resize((max(1, int(art.width * scale)), max(1, int(art.height * scale))))
                    layer.alpha_composite(fitted, ((w - fitted.width) // 2, (h - fitted.height) // 2))
                if dc.get("rotate"):
                    layer = layer.rotate(dc["rotate"], expand=False)
                img.alpha_composite(layer, (x, y))
                self.count += 1
        if self.preview:
            d = ImageDraw.Draw(img)
            step = max(16, W // 16)
            for gx in range(0, W, step):
                d.line([(gx, 0), (gx, H)], fill=(255, 0, 255, 120))
                d.text((gx + 2, 2), f"{gx / W:.2f}", fill=(255, 0, 255, 255))
            for gy in range(0, H, step):
                d.line([(0, gy), (W, gy)], fill=(255, 0, 255, 120))
                d.text((2, gy + 2), f"{gy / H:.2f}", fill=(255, 0, 255, 255))
        return img


# --------------------------------------------------------------------------- vanilla parsing

def find_item_blocks(scripts_dir: Path) -> dict[str, str]:
    """item NAME { ... } blocks from every .txt under media/scripts."""
    items = {}
    for p in scripts_dir.rglob("*.txt"):
        text = p.read_text(errors="ignore")
        for m in re.finditer(r"\bitem\s+(\w+)\s*\{", text):
            name = m.group(1)
            depth, i = 1, m.end()
            while i < len(text) and depth:
                depth += {"{": 1, "}": -1}.get(text[i], 0)
                i += 1
            items[name] = text[m.end():i - 1]
    return items


def find_vehicle_textures(scripts_dir: Path) -> set[str]:
    out = set()
    for p in scripts_dir.rglob("*.txt"):
        text = p.read_text(errors="ignore")
        for m in re.finditer(r"\bvehicle\s+(\w*Police\w*)\s*\{", text):
            depth, i = 1, m.end()
            while i < len(text) and depth:
                depth += {"{": 1, "}": -1}.get(text[i], 0)
                i += 1
            block = text[m.end():i - 1]
            for t in re.findall(r"\btexture\s*=\s*([\w/\\.-]+)", block):
                out.add(t.replace("\\", "/").removesuffix(".png"))
            for t in re.findall(r"\bskin\s*\{[^}]*texture\s*=\s*([\w/\\.-]+)", block):
                out.add(t.replace("\\", "/").removesuffix(".png"))
    return out


def guid(name: str) -> str:
    return str(uuid.uuid5(NS, name))


# --------------------------------------------------------------------------- build

def build(pz: Path, out: Path, preview: bool = False) -> None:
    from PIL import Image

    decal_dir = out / "media" / "textures" / "Decals"
    decal_art.build(decal_dir)
    decaler = Decaler(decal_dir, preview)

    media = pz / "media"
    if not media.is_dir():
        raise SystemExit(f"{pz} does not look like a Project Zomboid install (no media/ folder)")
    textures = media / "textures"
    scripts = media / "scripts"
    items = find_item_blocks(scripts)
    print(f"[rcmp] {len(items)} vanilla item scripts parsed")

    # ---- vehicles: override textures in place
    vt = find_vehicle_textures(scripts)
    n = 0
    for rel in sorted(vt):
        src = textures / f"{rel}.png"
        if not src.exists():
            alt = list(textures.rglob(Path(rel).name + ".png"))
            if not alt:
                print(f"[rcmp] vehicle texture not found: {rel}")
                continue
            src = alt[0]
            rel = src.relative_to(textures).with_suffix("").as_posix()
        dst = out / "media" / "textures" / f"{rel}.png"
        dst.parent.mkdir(parents=True, exist_ok=True)
        img = decaler.apply(_recolor(Image.open(src), vehicle_livery), dst.stem, "vehicle")
        img.save(dst)
        if preview:
            img.save(dst.with_name(dst.stem + "_layout.png"))
        n += 1
    print(f"[rcmp] {n} police vehicle textures recoloured to RCMP livery")

    # ---- translations: vehicle names + new items
    tr_lines = []
    ig = media / "lua" / "shared" / "Translate" / "EN" / "IG_UI_EN.txt"
    if ig.exists():
        for line in ig.read_text(errors="ignore").splitlines():
            m = re.match(r'\s*(IGUI_VehicleName\w*Police\w*)\s*=\s*"(.*)"', line)
            if m:
                tr_lines.append(f'    {m.group(1)} = "{m.group(2).replace("Police", "RCMP")}",')
    trdir = out / "media" / "lua" / "shared" / "Translate" / "EN"
    trdir.mkdir(parents=True, exist_ok=True)
    (trdir / "IG_UI_EN.txt").write_text("IG_UI_EN = {\n" + "\n".join(tr_lines) + "\n}\n")
    item_tr = [f'    ItemName_Base.{new} = "{disp}",' for _, new, disp, _ in CLOTHES]
    (trdir / "ItemName_EN.txt").write_text("ItemName_EN = {\n" + "\n".join(item_tr) + "\n}\n")

    # ---- clothing items
    ci_src = media / "clothing" / "clothingItems"
    ci_dst = out / "media" / "clothing" / "clothingItems"
    ci_dst.mkdir(parents=True, exist_ok=True)
    guid_table = []
    script_blocks = []
    made = {}
    for src_item, new_item, disp, fn in CLOTHES:
        if src_item not in items:
            print(f"[rcmp] vanilla item {src_item} not found, skipping {new_item}")
            continue
        block = items[src_item]
        block = re.sub(r"DisplayName\s*=\s*[^,]+,", f"DisplayName = {disp},", block)
        block = re.sub(r"ClothingItem\s*=\s*\w+,", f"ClothingItem = {new_item},", block)
        block = re.sub(r"Icon\s*=\s*(\w+),", r"Icon = \1,", block)
        script_blocks.append(f"    item {new_item}\n    {{{block}}}\n")
        # clothingItem xml
        xml_src = ci_src / f"{src_item}.xml"
        if not xml_src.exists():
            m = re.search(r"ClothingItem\s*=\s*(\w+)", items[src_item])
            xml_src = ci_src / f"{m.group(1)}.xml" if m else xml_src
        if not xml_src.exists():
            print(f"[rcmp] no clothingItem xml for {src_item}")
            continue
        xml = xml_src.read_text(errors="ignore")
        g = guid(new_item)
        xml = re.sub(r"<m_GUID>.*?</m_GUID>", f"<m_GUID>{g}</m_GUID>", xml)
        choices = re.findall(r"<textureChoices>(.*?)</textureChoices>", xml)
        new_choices = []
        for c in choices:
            tsrc = textures / f"{c}.png"
            if not tsrc.exists():
                alt = list(textures.rglob(Path(c).name + ".png"))
                tsrc = alt[0] if alt else None
            tname = f"{Path(c).parent.as_posix()}/{new_item}"
            if tsrc:
                tdst = out / "media" / "textures" / f"{tname}.png"
                tdst.parent.mkdir(parents=True, exist_ok=True)
                img = decaler.apply(_recolor(Image.open(tsrc), fn), new_item, "clothing")
                img.save(tdst)
                if preview:
                    img.save(tdst.with_name(tdst.stem + "_layout.png"))
            new_choices.append(tname)
            break   # one texture per RCMP item (uniforms are uniform)
        xml = re.sub(r"\s*<textureChoices>.*?</textureChoices>", "", xml, flags=re.S)
        xml = xml.replace("</clothingItem>", "".join(f"  <textureChoices>{c}</textureChoices>\n" for c in new_choices) + "</clothingItem>")
        xml = re.sub(r"<m_AllowRandomHue>.*?</m_AllowRandomHue>", "<m_AllowRandomHue>false</m_AllowRandomHue>", xml)
        xml = re.sub(r"<m_AllowRandomTint>.*?</m_AllowRandomTint>", "<m_AllowRandomTint>false</m_AllowRandomTint>", xml)
        (ci_dst / f"{new_item}.xml").write_text(xml)
        guid_table.append((f"media/clothing/clothingItems/{new_item}.xml", g))
        made[new_item] = g
        # icon: reuse vanilla icon
        m = re.search(r"Icon\s*=\s*(\w+)", block)
        if m:
            ico = textures / f"Item_{m.group(1)}.png"
            if ico.exists():
                shutil.copy(ico, out / "media" / "textures" / ico.name)
    sdir = out / "media" / "scripts" / "clothing"
    sdir.mkdir(parents=True, exist_ok=True)
    (sdir / "clothing_rcmp.txt").write_text("module Base\n{\n    imports { Base }\n\n" + "\n".join(script_blocks) + "}\n")

    # ---- outfits
    def outfit_xml(name: str, items_: list[str]) -> str:
        rows = []
        for it in items_:
            if it in made:
                rows.append(f"        <m_items>\n            <probability>1.0</probability>\n            <itemGUID>{made[it]}</itemGUID>\n        </m_items>")
        body = "\n".join(rows)
        return (f"    <m_Name>{name}</m_Name>\n    <m_Guid>{guid('outfit:' + name)}</m_Guid>\n"
                "    <m_Top>false</m_Top>\n    <m_Pants>false</m_Pants>\n    <m_AllowPantsHue>false</m_AllowPantsHue>\n"
                "    <m_AllowTopTint>false</m_AllowTopTint>\n    <m_AllowTShirtDecal>false</m_AllowTShirtDecal>\n" + body)

    outfits = ['<?xml version="1.0" encoding="utf-8"?>', "<outfitManager>"]
    for sex in ("m_MaleOutfits", "m_FemaleOutfits"):
        for name, its in OUTFITS.items():
            outfits.append(f"  <{sex}>\n{outfit_xml(name, its)}\n  </{sex}>")
    outfits.append("</outfitManager>")
    (out / "media" / "clothing").mkdir(parents=True, exist_ok=True)
    (out / "media" / "clothing" / "clothing.xml").write_text("\n".join(outfits) + "\n")
    gt = ['<?xml version="1.0" encoding="utf-8"?>', "<fileGuidTable>"]
    for path, g in guid_table:
        gt.append(f"  <files>\n    <path>{path}</path>\n    <guid>{g}</guid>\n  </files>")
    gt.append("</fileGuidTable>")
    (out / "media" / "fileGuidTable.xml").write_text("\n".join(gt) + "\n")
    # poster
    img = Image.new("RGB", (256, 256), (200, 16, 46))
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    d.rectangle([0, 200, 255, 255], fill=(0, 32, 91))
    d.rectangle([0, 196, 255, 200], fill=(255, 205, 0))
    d.text((70, 90), "R C M P", fill=(255, 205, 0))
    d.text((40, 215), "New Brunswick", fill=(255, 255, 255))
    img.save(out / "poster.png")
    print(f"[rcmp] {decaler.count} decals composited (regions: tools/rcmp/decals.json)")
    print(f"[rcmp] {len(made)} RCMP clothing items, {len(OUTFITS)} outfits -> {out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pz-dir", required=True, help="Project Zomboid install folder (contains media/)")
    ap.add_argument("--out", default="mods/RCMP_NB")
    ap.add_argument("--preview-layout", action="store_true", help="also write *_layout.png with a labelled grid to place decal regions")
    a = ap.parse_args()
    build(Path(a.pz_dir), Path(a.out), a.preview_layout)


if __name__ == "__main__":
    main()
