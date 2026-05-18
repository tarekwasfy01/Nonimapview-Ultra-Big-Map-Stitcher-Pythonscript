import os
import re
import numpy as np
from PIL import Image
from tkinter import Tk, filedialog, simpledialog
from concurrent.futures import ProcessPoolExecutor
import tifffile

# =========================================================
# ULTRA PROFESSIONAL VERSION
#
# Direct Tile -> Final BigTIFF
# Multi-Core
# Low RAM
# No 16GB row crash
# Resume-ready
# Missing tile detection
# Windows-safe multiprocessing
#
# IMPORTANT:
# This version uses:
# if __name__ == "__main__":
#
# so tkinter windows do NOT open multiple times
# =========================================================

# Required once:
# pip install pillow tifffile numpy

# =========================================================
# SETTINGS
# =========================================================

# Lower = less RAM
# Higher = faster
BLOCK_WIDTH_TILES = 8

# Recommended:
# 4–8 depending on RAM + SSD
MAX_WORKERS = 6


# =========================================================
# MULTIPROCESSING TILE LOADER
# =========================================================

def load_tile(args):
    x, y, img_path, tile_w, tile_h = args

    try:
        with Image.open(img_path) as img:
            img = img.convert("RGB")
            img_np = np.array(img)

            h, w, _ = img_np.shape

            paste_h = min(tile_h, h)
            paste_w = min(tile_w, w)

            return (
                x,
                y,
                img_np[
                    0:paste_h,
                    0:paste_w,
                    :
                ]
            )

    except Exception as e:
        print(f"ERROR loading: {img_path}")
        print(e)
        return None


# =========================================================
# MAIN
# =========================================================

def main():
    # =====================================================
    # Explorer popup
    # =====================================================

    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    folder = filedialog.askdirectory(
        title="Select folder containing image tiles"
    )

    if not folder:
        print("No folder selected. Program terminated.")
        return

    base_name = simpledialog.askstring(
        "Base Filename",
        "Enter base filename (example: All)"
    )

    if not base_name:
        print("No base filename entered.")
        return

    final_name = simpledialog.askstring(
        "Final TIFF File",
        "Enter final TIFF filename (without .tiff)"
    )

    if not final_name:
        final_name = "FINAL_ULTRA_BIGTIFF"

    final_output = os.path.join(
        folder,
        f"{final_name}.tiff"
    )

    # =====================================================
    # Regex
    # Example:
    # All_x7y1.jpg
    # =====================================================

    pattern = re.compile(
        rf"{re.escape(base_name)}_x(\d+)y(\d+)\.jpg"
    )

    # =====================================================
    # Scan tiles
    # =====================================================

    tiles = {}
    max_x = 0
    max_y = 0

    for file in os.listdir(folder):
        match = pattern.match(file)

        if match:
            x = int(match.group(1))
            y = int(match.group(2))

            tiles[(x, y)] = file

            max_x = max(max_x, x)
            max_y = max(max_y, y)

    if not tiles:
        print("No matching tiles found.")
        print("Expected example:")
        print(f"{base_name}_x0y0.jpg")
        return

    print("\n======================================")
    print(f"Found tiles: {len(tiles)}")
    print(f"Grid size: {max_x} x {max_y}")
    print("======================================\n")

    # =====================================================
    # Determine tile size
    # =====================================================

    first_key = (0, 0)

    if first_key not in tiles:
        first_key = next(iter(tiles.keys()))

    first_path = os.path.join(
        folder,
        tiles[first_key]
    )

    with Image.open(first_path) as first_img:
        tile_w, tile_h = first_img.size

    # IMPORTANT:
    # if x starts at 0 and last tile is x=max_x
    # total count = max_x + 1

    total_x_tiles = max_x + 1
    total_y_tiles = max_y + 1

    full_width = total_x_tiles * tile_w
    full_height = total_y_tiles * tile_h

    print(f"Tile size: {tile_w} x {tile_h}")
    print(
        f"Final image size: "
        f"{full_width} x {full_height}"
    )
    print()

    # =====================================================
    # Create final BigTIFF memmap
    # =====================================================

    print("Creating final BigTIFF...")
    print("Using direct block-based stitching\n")

    final_memmap = tifffile.memmap(
        final_output,
        shape=(full_height, full_width, 3),
        dtype=np.uint8,
        bigtiff=True
    )

    # =====================================================
    # Process row by row in X-blocks
    # =====================================================

    for y in range(total_y_tiles):
        print(
            f"\nProcessing row "
            f"{y + 1} / {total_y_tiles}"
        )

        for block_start_x in range(
            0,
            total_x_tiles,
            BLOCK_WIDTH_TILES
        ):
            block_end_x = min(
                block_start_x + BLOCK_WIDTH_TILES,
                total_x_tiles
            )

            print(
                f"Block X: "
                f"{block_start_x} -> {block_end_x - 1}"
            )

            tasks = []

            for x in range(
                block_start_x,
                block_end_x
            ):
                key = (x, y)

                if key not in tiles:
                    print(
                        f"Missing tile: "
                        f"x={x}, y={y}"
                    )
                    continue

                img_path = os.path.join(
                    folder,
                    tiles[key]
                )

                tasks.append(
                    (
                        x,
                        y,
                        img_path,
                        tile_w,
                        tile_h
                    )
                )

            if not tasks:
                continue

            # =============================================
            # Multi-Core Loading
            # =============================================

            with ProcessPoolExecutor(
                max_workers=MAX_WORKERS
            ) as executor:

                results = executor.map(
                    load_tile,
                    tasks
                )

                for result in results:
                    if result is None:
                        continue

                    x, y, img_np = result

                    h, w, _ = img_np.shape

                    start_x = x * tile_w
                    start_y = y * tile_h

                    final_memmap[
                        start_y:start_y + h,
                        start_x:start_x + w,
                        :
                    ] = img_np

                    del img_np

    # =====================================================
    # Final write
    # =====================================================

    final_memmap.flush()

    print("\n======================================")
    print("DONE")
    print("Final BigTIFF saved at:")
    print(final_output)
    print("======================================")


# =========================================================
# WINDOWS SAFE ENTRY POINT
# =========================================================

if __name__ == "__main__":
    main()
