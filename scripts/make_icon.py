#!/usr/bin/env python3
"""Generuje aplikační ikonu BPDPManager.

Ikona je vlastní výtvor (kompatibilní s MIT licencí projektu):
modrá rounded-square (macOS Big Sur+ styl), uvnitř kniha s usměvavou
absolventskou tváří, černou čepicí se žlutým střapcem a červenou záložkou.

Skript generuje:
  - ``src/bpdpmanager/resources/icons/app_icon.png``  (master 1024×1024)
  - ``src/bpdpmanager/resources/icons/app_icon_512.png`` (pro web/README)
  - ``src/bpdpmanager/resources/icons/app_icon.icns``  (jen na macOS, vyžaduje ``iconutil``)
  - během generování taky ``app_icon.iconset/`` (smaže se)

Spuštění:
    python scripts/make_icon.py
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

REPO_ROOT = Path(__file__).resolve().parent.parent
RESOURCES = REPO_ROOT / "src" / "bpdpmanager" / "resources" / "icons"
DEFAULT_SIZE = 1024

PAL = {
    "bg_top": (38, 90, 175),
    "bg_bot": (78, 155, 235),
    "book_main": (28, 70, 145),
    "book_dark": (16, 46, 100),
    "book_highlight": (54, 110, 195),
    "pages": (250, 245, 225),
    "pages_shadow": (200, 188, 160),
    "face": (255, 213, 145),
    "face_blush": (245, 155, 135),
    "cap": (26, 28, 36),
    "cap_band": (10, 12, 18),
    "tassel": (250, 200, 60),
    "tassel_dark": (200, 155, 30),
    "bookmark": (220, 55, 55),
    "bookmark_dark": (170, 35, 35),
    "mouth": (50, 28, 18),
    "eye": (40, 22, 12),
}

ICONSET_PAIRS = [
    (16, 1), (16, 2),
    (32, 1), (32, 2),
    (128, 1), (128, 2),
    (256, 1), (256, 2),
    (512, 1), (512, 2),
]


def squircle_mask(size: int, radius_frac: float = 0.224) -> Image.Image:
    radius = int(size * radius_frac)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, size - 1, size - 1), radius=radius, fill=255
    )
    return mask


def make_master(size: int = DEFAULT_SIZE) -> Image.Image:
    """Master ikona: kniha JE celá squircle, vše ostatní je uvnitř.

    Layout:
      - kniha vyplňuje celé plátno jako macOS rounded-square
      - vpravo svislý krémový pruh (stránky)
      - dole tmavší pruh (vazba)
      - záložka visí z horní hrany
      - tvář + absolventská čepice uprostřed
    """
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2
    corner = int(size * 0.224)

    # ── tělo knihy = celá plocha ikony ─────────────────────────────────────
    d.rounded_rectangle((0, 0, size - 1, size - 1), radius=corner, fill=PAL["book_main"])

    # jemný horní highlight (vrchní třetina lehce světlejší)
    highlight = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(highlight).rounded_rectangle(
        (0, 0, size - 1, int(size * 0.45)),
        radius=corner,
        fill=PAL["book_highlight"] + (75,),
    )
    img.alpha_composite(highlight)

    # ── stránky vpravo ─────────────────────────────────────────────────────
    spine_w = int(size * 0.085)
    pages_top = int(size * 0.06)
    pages_bot = size - int(size * 0.06)
    pages_x = size - spine_w
    pages_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(pages_layer).rectangle(
        (pages_x, pages_top, size, pages_bot),
        fill=PAL["pages"] + (255,),
    )
    img.alpha_composite(pages_layer)
    # linky na stránkách (detail)
    line_w = max(1, size // 300)
    for i in range(1, 6):
        y = pages_top + i * (pages_bot - pages_top) // 6
        d.line(
            (pages_x + spine_w // 4, y, size - int(size * 0.02), y),
            fill=PAL["pages_shadow"], width=line_w,
        )
    # tmavá dělící linka
    d.line(
        (pages_x - 2, pages_top + 8, pages_x - 2, pages_bot - 8),
        fill=PAL["book_dark"], width=max(2, size // 300),
    )

    # ── spodní pás (tmavá vazba) ──────────────────────────────────────────
    band_h = int(size * 0.12)
    band_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(band_layer).rectangle(
        (0, size - band_h, size, size),
        fill=PAL["book_dark"] + (255,),
    )
    img.alpha_composite(band_layer)

    # ── záložka ────────────────────────────────────────────────────────────
    bm_w = int(size * 0.10)
    bm_x = pages_x - bm_w - int(size * 0.04)
    bm_top = 0  # od horní hrany
    bm_bot = int(size * 0.32)
    notch = int(bm_w * 0.45)
    bm_poly = [
        (bm_x, bm_top),
        (bm_x + bm_w, bm_top),
        (bm_x + bm_w, bm_bot),
        (bm_x + bm_w // 2, bm_bot - notch),
        (bm_x, bm_bot),
    ]
    d.polygon(bm_poly, fill=PAL["bookmark"])
    # tmavší stín na pravé hraně
    d.polygon(
        [
            (bm_x + bm_w * 2 // 3, bm_top),
            (bm_x + bm_w, bm_top),
            (bm_x + bm_w, bm_bot),
            (bm_x + bm_w // 2, bm_bot - notch),
        ],
        fill=PAL["bookmark_dark"],
    )

    # ── tvář ───────────────────────────────────────────────────────────────
    face_d = int(size * 0.42)
    face_cx = cx - int(size * 0.04)  # mírně doleva, ať záložka nepřekáží
    face_cy = cy + int(size * 0.04)
    face_r = face_d // 2
    d.ellipse(
        (face_cx - face_r, face_cy - face_r, face_cx + face_r, face_cy + face_r),
        fill=PAL["face"],
    )

    # blush
    blush_r = int(face_d * 0.10)
    blush_y = face_cy + int(face_d * 0.10)
    for bx in (face_cx - int(face_d * 0.27), face_cx + int(face_d * 0.27)):
        blush_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        ImageDraw.Draw(blush_layer).ellipse(
            (bx - blush_r, blush_y - blush_r, bx + blush_r, blush_y + blush_r),
            fill=PAL["face_blush"] + (160,),
        )
        blush_layer = blush_layer.filter(ImageFilter.GaussianBlur(radius=size // 200))
        img.alpha_composite(blush_layer)

    # oči
    eye_r = int(face_d * 0.08)
    eye_off_x = int(face_d * 0.18)
    eye_y = face_cy - int(face_d * 0.04)
    for ex in (face_cx - eye_off_x, face_cx + eye_off_x):
        d.ellipse(
            (ex - eye_r, eye_y - eye_r, ex + eye_r, eye_y + eye_r),
            fill=PAL["eye"],
        )

    # úsměv
    smile_w = int(face_d * 0.42)
    smile_h = int(face_d * 0.24)
    smile_bbox = (
        face_cx - smile_w // 2,
        face_cy + int(face_d * 0.04),
        face_cx + smile_w // 2,
        face_cy + int(face_d * 0.04) + smile_h,
    )
    d.arc(smile_bbox, start=10, end=170, fill=PAL["mouth"], width=max(5, size // 100))

    # ── absolventská čepice ────────────────────────────────────────────────
    # cap_body — krycí část pod mortarboardem (lichoběžník)
    cap_body_h = int(face_d * 0.26)
    cap_body_w = int(face_d * 0.94)
    cap_body_x0 = face_cx - cap_body_w // 2
    cap_body_y0 = face_cy - face_r - int(face_d * 0.02)
    cap_body_y1 = cap_body_y0 + cap_body_h
    cap_body_poly = [
        (cap_body_x0 + int(face_d * 0.04), cap_body_y0),
        (cap_body_x0 + cap_body_w - int(face_d * 0.04), cap_body_y0),
        (cap_body_x0 + cap_body_w - int(face_d * 0.10), cap_body_y1),
        (cap_body_x0 + int(face_d * 0.10), cap_body_y1),
    ]
    d.polygon(cap_body_poly, fill=PAL["cap_band"])

    # mortarboard — diamond (otočený čtverec)
    mb_w = int(face_d * 1.35)
    mb_h = int(mb_w * 0.32)
    mb_cy = cap_body_y0 - int(mb_h * 0.10)
    mb_poly = [
        (face_cx, mb_cy - mb_h // 2),
        (face_cx + mb_w // 2, mb_cy),
        (face_cx, mb_cy + mb_h // 2),
        (face_cx - mb_w // 2, mb_cy),
    ]
    d.polygon(mb_poly, fill=PAL["cap"])
    # zvýraznění hran mortarboardu
    edge_w = max(2, size // 256)
    d.line(
        [(face_cx - mb_w // 2, mb_cy), (face_cx, mb_cy + mb_h // 2),
         (face_cx + mb_w // 2, mb_cy)],
        fill=PAL["cap_band"], width=edge_w,
    )

    # knoflík uprostřed
    btn_r = int(face_d * 0.035)
    d.ellipse(
        (face_cx - btn_r, mb_cy - btn_r, face_cx + btn_r, mb_cy + btn_r),
        fill=PAL["tassel"],
    )

    # tassel — visí vpravo dolů
    tassel_start = (face_cx + int(face_d * 0.02), mb_cy + int(face_d * 0.01))
    tassel_mid = (face_cx + int(face_d * 0.50), mb_cy + int(face_d * 0.10))
    tassel_end = (face_cx + int(face_d * 0.58), mb_cy + int(face_d * 0.30))
    cord_w = max(3, size // 200)
    d.line(
        [tassel_start, tassel_mid, tassel_end],
        fill=PAL["tassel"], width=cord_w, joint="curve",
    )
    # tip (kulička střapce)
    tip_r = int(face_d * 0.07)
    d.ellipse(
        (tassel_end[0] - tip_r, tassel_end[1] - tip_r,
         tassel_end[0] + tip_r, tassel_end[1] + tip_r),
        fill=PAL["tassel"],
    )
    # detail šrafování
    for i in range(-2, 3):
        dx = i * tip_r // 3
        d.line(
            (tassel_end[0] + dx, tassel_end[1] - tip_r + 2,
             tassel_end[0] + dx, tassel_end[1] + tip_r - 2),
            fill=PAL["tassel_dark"], width=max(1, size // 600),
        )

    # ── finální squircle mask (zaoblené rohy ikony) ────────────────────────
    final_mask = squircle_mask(size)
    masked = Image.composite(
        img, Image.new("RGBA", (size, size), (0, 0, 0, 0)), final_mask
    )
    return masked


def write_iconset(master: Image.Image, iconset_dir: Path) -> None:
    if iconset_dir.exists():
        shutil.rmtree(iconset_dir)
    iconset_dir.mkdir(parents=True, exist_ok=True)
    for base, scale in ICONSET_PAIRS:
        actual = base * scale
        name = f"icon_{base}x{base}{'@2x' if scale == 2 else ''}.png"
        master.resize((actual, actual), Image.LANCZOS).save(
            iconset_dir / name, optimize=True
        )


def make_icns(iconset_dir: Path, output: Path) -> bool:
    """Zkonvertuje iconset → .icns pomocí macOS ``iconutil``.

    Vrací True při úspěchu, jinak False (např. ``iconutil`` chybí mimo macOS).
    """
    if sys.platform != "darwin":
        return False
    try:
        subprocess.run(
            ["iconutil", "--convert", "icns", str(iconset_dir), "-o", str(output)],
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"iconutil selhal: {exc}", file=sys.stderr)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--size",
        type=int,
        default=DEFAULT_SIZE,
        help=f"Velikost master ikony v px (default {DEFAULT_SIZE}).",
    )
    parser.add_argument(
        "--keep-iconset",
        action="store_true",
        help="Nechat iconset adresář (jinak smazaný po vytvoření .icns).",
    )
    args = parser.parse_args()

    RESOURCES.mkdir(parents=True, exist_ok=True)
    master = make_master(args.size)

    master_path = RESOURCES / "app_icon.png"
    master.save(master_path, optimize=True)
    print(f"✓ Master: {master_path}")

    # menší PNG pro README a fallback
    for s in (512, 256, 128):
        path = RESOURCES / f"app_icon_{s}.png"
        master.resize((s, s), Image.LANCZOS).save(path, optimize=True)
        print(f"✓ {s}×{s}: {path}")

    # macOS iconset + .icns
    iconset_dir = RESOURCES / "app_icon.iconset"
    write_iconset(master, iconset_dir)
    print(f"✓ Iconset: {iconset_dir}")

    icns_path = RESOURCES / "app_icon.icns"
    if make_icns(iconset_dir, icns_path):
        print(f"✓ .icns: {icns_path}")
    else:
        print("✗ .icns nebyl vytvořen (mimo macOS nebo chybí iconutil)")

    if not args.keep_iconset:
        shutil.rmtree(iconset_dir, ignore_errors=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
