#!/usr/bin/env python3
"""
Frog Kudos Icon Switcher Utility
Usage:
  python3 scripts/apply_icon.py 1  # 經典萌眼蛙 (Classic)
  python3 scripts/apply_icon.py 2  # 榮譽金冠蛙 (Crown)
  python3 scripts/apply_icon.py 3  # 幸運嫩芽蛙 (Sprout)
  python3 scripts/apply_icon.py 4  # 幾何極簡蛙 (Vector)
"""
import sys
import os
import shutil
import subprocess
from PIL import Image

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GALLERY_DIR = os.path.join(PROJECT_ROOT, "scripts", "icons_gallery")

ICON_MAP = {
    "1": ("icon_1_classic.jpg", "經典 3D 萌眼蛙 (Classic)"),
    "2": ("icon_2_crown.jpg", "榮譽金冠蛙 (Crown Kudos)"),
    "3": ("icon_3_sprout.jpg", "幸運嫩芽蛙 (Lucky Sprout)"),
    "4": ("icon_4_vector.jpg", "幾何極簡蛙 (Modern Vector)"),
}

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ICON_MAP:
        print("請指定欲套用的圖示編號：")
        for k, (fname, desc) in sorted(ICON_MAP.items()):
            print(f"  [{k}] {desc}")
        sys.exit(1)

    choice = sys.argv[1]
    filename, desc = ICON_MAP[choice]
    src_path = os.path.join(GALLERY_DIR, filename)

    if not os.path.exists(src_path):
        print(f"錯誤：找不到來源圖檔 {src_path}")
        sys.exit(1)

    print(f"🎨 正在套用圖示：{desc} ...")
    im = Image.open(src_path).convert("RGB")

    public_dir = os.path.join(PROJECT_ROOT, "frontend", "public")
    public_icons_dir = os.path.join(public_dir, "icons")
    dist_dir = os.path.join(PROJECT_ROOT, "frontend", "dist")
    dist_icons_dir = os.path.join(dist_dir, "icons")

    os.makedirs(public_icons_dir, exist_ok=True)
    os.makedirs(dist_icons_dir, exist_ok=True)

    # 1. 512x512
    im512 = im.resize((512, 512), Image.Resampling.LANCZOS)
    im512.save(os.path.join(public_icons_dir, "icon-512.png"), "PNG", optimize=True)
    im512.save(os.path.join(dist_icons_dir, "icon-512.png"), "PNG", optimize=True)

    # 2. 192x192
    im192 = im.resize((192, 192), Image.Resampling.LANCZOS)
    im192.save(os.path.join(public_icons_dir, "icon-192.png"), "PNG", optimize=True)
    im192.save(os.path.join(dist_icons_dir, "icon-192.png"), "PNG", optimize=True)

    # 3. 180x180 (Apple Touch Icon)
    im180 = im.resize((180, 180), Image.Resampling.LANCZOS)
    for p in [
        os.path.join(public_icons_dir, "apple-touch-icon.png"),
        os.path.join(public_dir, "apple-touch-icon.png"),
        os.path.join(public_dir, "apple-touch-icon-precomposed.png"),
        os.path.join(dist_icons_dir, "apple-touch-icon.png"),
        os.path.join(dist_dir, "apple-touch-icon.png"),
        os.path.join(dist_dir, "apple-touch-icon-precomposed.png"),
    ]:
        im180.save(p, "PNG", optimize=True)

    print("✅ 靜態圖示檔已全數更新完畢！")

if __name__ == "__main__":
    main()
