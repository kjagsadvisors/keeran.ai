#!/usr/bin/env python3
"""Download the CC0 Poly Haven lighting and materials the Blender scenes use.

Usage (from the template or project folder):
    python3 blender/fetch_assets.py            # 2k, skips files already present
    python3 blender/fetch_assets.py --res 4k   # sharper close-ups, ~4x the size

Everything lands in blender/assets/ (gitignored). Poly Haven assets are CC0.
"""

import argparse
import json
import pathlib
import urllib.request

HDRIS = [
    "studio_small_09",  # soft product studio
    "photo_studio_loft_hall",  # big windows, raking daylight
    "empty_warehouse_01",  # gallery / exhibition space
    "kloofendal_48d_partly_cloudy_puresky",  # open sky for outdoor signage
]

TEXTURES = [
    "concrete_floor_02",
    "grey_plaster",
    "white_plaster_02",
    "rough_linen",
    "wood_table_001",
    "marble_01",
]

# Poly Haven map names → our file suffixes
MAPS = {"Diffuse": "diff", "Rough": "rough", "nor_gl": "nor"}

API = "https://api.polyhaven.com/files/"
UA = {"User-Agent": "keeran.ai/match-frame"}


def get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA)) as r:
        return json.load(r)


def download(url, dest):
    if dest.exists():
        print(f"  have {dest.name}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA)) as r, open(tmp, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    tmp.rename(dest)
    print(f"  got  {dest.name} ({dest.stat().st_size / 1e6:.1f} MB)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", default="2k", choices=["1k", "2k", "4k"])
    args = ap.parse_args()
    root = pathlib.Path(__file__).resolve().parent / "assets"

    for name in HDRIS:
        print(name)
        files = get_json(API + name)
        download(files["hdri"][args.res]["hdr"]["url"], root / "hdri" / f"{name}.hdr")

    for name in TEXTURES:
        print(name)
        files = get_json(API + name)
        for key, suffix in MAPS.items():
            download(files[key][args.res]["jpg"]["url"], root / "tex" / name / f"{suffix}.jpg")


if __name__ == "__main__":
    main()
