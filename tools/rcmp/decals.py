#!/usr/bin/env python3
"""Draw the RCMP decal artwork used by make_rcmp.py (and usable on their own in BuildingEd/TileZed).

    python tools/rcmp/decals.py --out mods/RCMP_NB/media/textures/Decals

Produces transparent PNGs:
  RCMP_Stripe.png        blue livery band with the red and gold pinstripes (tileable horizontally)
  RCMP_Wordmark.png      "RCMP  GRC" door text
  RCMP_Police.png        "POLICE" rear/quarter text
  RCMP_Roundel.png       stylised maple-leaf roundel (an original design, not the protected RCMP crest)
  RCMP_ShoulderFlash.png shoulder flash for the duty shirt and the serge
  RCMP_YellowStripe.png  breech stripe (tileable vertically)
  RCMP_HatBand.png       forage cap / Stetson band
  RCMP_Badge.png         small cap badge
  RCMP_Sign.png          detachment wall sign (for a TileZed custom tile / poster)
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BLUE = (0, 32, 91, 255)
RED = (200, 16, 46, 255)
GOLD = (255, 205, 0, 255)
WHITE = (255, 255, 255, 255)
NAVY = (12, 22, 56, 255)

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/Library/Fonts/Arial Bold.ttf",
]


def font(size: int) -> ImageFont.FreeTypeFont:
    for f in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def text_image(text: str, size: int, color, pad: int = 6, outline=None) -> Image.Image:
    f = font(size)
    tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    x0, y0, x1, y1 = tmp.textbbox((0, 0), text, font=f)
    img = Image.new("RGBA", (x1 - x0 + 2 * pad, y1 - y0 + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if outline:
        for dx in (-2, 0, 2):
            for dy in (-2, 0, 2):
                d.text((pad - x0 + dx, pad - y0 + dy), text, font=f, fill=outline)
    d.text((pad - x0, pad - y0), text, font=f, fill=color)
    return img


def maple_leaf(size: int, color) -> Image.Image:
    """A simple 11-point maple leaf polygon."""
    # right half of a sugar-maple leaf outline, mirrored for the left half
    right = [(50, 0), (55, 14), (64, 9), (62, 28), (72, 22), (70, 36), (88, 28), (82, 44), (98, 50), (86, 58),
             (90, 68), (72, 66), (74, 78), (60, 72), (56, 86), (52, 78), (52, 100)]
    pts = right + [(100 - x, y) for x, y in reversed(right[:-1])]
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(img).polygon([(x * size / 100, y * size / 100) for x, y in pts], fill=color)
    return img


def stripe(w: int = 512, h: int = 96) -> Image.Image:
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, int(h * 0.18), w, int(h * 0.82)], fill=BLUE)
    d.rectangle([0, int(h * 0.06), w, int(h * 0.14)], fill=RED)
    d.rectangle([0, int(h * 0.86), w, int(h * 0.94)], fill=GOLD)
    return img


def roundel(size: int = 256) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([0, 0, size - 1, size - 1], fill=GOLD)
    d.ellipse([size * 0.06, size * 0.06, size * 0.94, size * 0.94], fill=BLUE)
    d.ellipse([size * 0.22, size * 0.22, size * 0.78, size * 0.78], fill=WHITE)
    leaf = maple_leaf(int(size * 0.46), RED)
    img.alpha_composite(leaf, (int(size * 0.27), int(size * 0.25)))
    # ring text
    for text, centre, top in (("ROYAL CANADIAN", 270, True), ("MOUNTED POLICE", 90, False)):
        n = len(text)
        for i, ch in enumerate(text):
            step = 9.5 if top else -9.5
            deg = centre + (i - (n - 1) / 2) * step
            ang = math.radians(deg)
            cx, cy = size / 2 + math.cos(ang) * size * 0.42, size / 2 + math.sin(ang) * size * 0.42
            glyph = text_image(ch, int(size * 0.075), GOLD, pad=2).rotate(-deg - 90 if top else -deg + 90, expand=True)
            img.alpha_composite(glyph, (int(cx - glyph.width / 2), int(cy - glyph.height / 2)))
    return img


def shoulder_flash(w: int = 160, h: int = 64) -> Image.Image:
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=12, fill=BLUE, outline=GOLD, width=4)
    t = text_image("RCMP", int(h * 0.42), GOLD, pad=2)
    img.alpha_composite(t, ((w - t.width) // 2, 4))
    t2 = text_image("GRC", int(h * 0.26), WHITE, pad=2)
    img.alpha_composite(t2, ((w - t2.width) // 2, h - t2.height - 4))
    return img


def yellow_stripe(w: int = 24, h: int = 256) -> Image.Image:
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(img).rectangle([w * 0.25, 0, w * 0.75, h], fill=GOLD)
    return img


def hat_band(w: int = 512, h: int = 40) -> Image.Image:
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, h], fill=GOLD)
    d.rectangle([0, h * 0.35, w, h * 0.65], fill=BLUE)
    return img


def badge(size: int = 64) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([0, 0, size - 1, size - 1], fill=GOLD)
    d.ellipse([size * 0.12, size * 0.12, size * 0.88, size * 0.88], fill=BLUE)
    img.alpha_composite(maple_leaf(int(size * 0.5), RED), (int(size * 0.25), int(size * 0.25)))
    return img


def sign(w: int = 512, h: int = 160) -> Image.Image:
    img = Image.new("RGBA", (w, h), WHITE)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w - 1, h - 1], outline=BLUE, width=6)
    img.alpha_composite(roundel(h - 32), (16, 16))
    t = text_image("RCMP  |  GRC", int(h * 0.26), BLUE, pad=2)
    img.alpha_composite(t, (h + 8, int(h * 0.18)))
    t2 = text_image("Codiac Regional Detachment", int(h * 0.105), NAVY, pad=2)
    img.alpha_composite(t2, (h + 8, int(h * 0.6)))
    return img


def build(out: Path) -> dict[str, Path]:
    out.mkdir(parents=True, exist_ok=True)
    files = {
        "RCMP_Stripe": stripe(),
        "RCMP_Wordmark": text_image("RCMP  GRC", 72, BLUE, outline=None),
        "RCMP_Police": text_image("POLICE", 72, BLUE),
        "RCMP_Roundel": roundel(),
        "RCMP_ShoulderFlash": shoulder_flash(),
        "RCMP_YellowStripe": yellow_stripe(),
        "RCMP_HatBand": hat_band(),
        "RCMP_Badge": badge(),
        "RCMP_Sign": sign(),
    }
    paths = {}
    for name, img in files.items():
        p = out / f"{name}.png"
        img.save(p)
        paths[name] = p
    print(f"[decals] {len(paths)} decals -> {out}")
    return paths


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="mods/RCMP_NB/media/textures/Decals")
    build(Path(ap.parse_args().out))
