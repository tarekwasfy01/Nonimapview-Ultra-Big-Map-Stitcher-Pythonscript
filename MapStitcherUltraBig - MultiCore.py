import os
import re
import numpy as np
from PIL import Image
from tkinter import Tk, filedialog, simpledialog
from concurrent.futures import ProcessPoolExecutor
import tifffile


# =========================================================
# Multi-core tile loader function
# MUST stay outside __main__
# =========================================================

def load_tile(args):
    x, y, img_path, tile_w, tile_h = args

    from PIL import Image
    import numpy as np

    try:
        with Image.open(img_path) as img:
            img = img.convert("RGB")
            img_np = np.array(img)

            h, w, _ = img_np.shape

            paste_h = min(tile_h, h)
            paste_w = min(tile_w, w)

            return (
                x,
                img_np[0:paste_h, 0:paste_w, :]
            )

    except Exception as e:
        print(f"Error loading: {img_path}")
        print(e)
        return None


# =========================================================
# MAIN PROGRAM
# Required for Windows + ProcessPoolExecutor
# =========================================================

if __name__ == "__main__":

    # =====================================================
    # Explorer popup for folder + filename input
    # =====================================================

    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    # Select folder
    folder = filedialog.askdirectory(
        title="Select the folder containing the image tiles"
    )

    if not folder:
        print("No folder selected. Program terminated.")
        exit()

    # Base filename
    # Example input: All
    # Expected files: All_x0y0.jpg
    base_name = simpledialog.askstring(
        "Base Filename",
        "Enter the base filename (example: All)"
    )

    if not base_name:
        print("No base filename entered. Program terminated.")
        exit()

    # Final TIFF filename
    final_name = simpledialog.askstring(
        "Final TIFF File",
        "Enter final TIFF filename (without .tiff)"
    )

    if not final_name:
        final_name = "FINAL_BIGTIFF"

    final_output = os.path.join(
        folder,
        f"{final_name}.tiff"
    )

    # Folder for saved row images
    rows_folder = os.path.join(
        folder,
        "rows_temp"
    )
    os.makedirs(rows_folder, exist_ok=True)

    # =====================================================
    # Regex for files like:
    # All_x7y1.jpg
    # =====================================================

    pattern = re.compile(
        rf"{re.escape(base_name)}_x(\d+)y(\d+)\.jpg"
    )

    # =====================================================
    # Scan all tiles
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
        print("No matching files found.")
        print(
            "Expected example:",
            f"{base_name}_x0y0.jpg"
        )
        exit()

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

    full_width = max_x * tile_w
    full_height = max_y * tile_h

    print(f"Tile size: {tile_w} x {tile_h}")
    print(f"Final image size: {full_width} x {full_height}")
    print()

    # =====================================================
    # STEP 1
    # Create and save each row separately
    # Multi-core enabled
    # =====================================================

    print("STEP 1: Creating row images...\n")

    for y in range(max_y):
        print(f"Creating row {y + 1} / {max_y}")

        row_array = np.zeros(
            (tile_h, full_width, 3),
            dtype=np.uint8
        )

        tasks = []

        for x in range(max_x):
            key = (x, y)

            if key not in tiles:
                print(f"Missing tile: x={x}, y={y}")
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

        with ProcessPoolExecutor(
            max_workers=6
        ) as executor:
            results = executor.map(
                load_tile,
                tasks
            )

        for result in results:
            if result is None:
                continue

            x, img_np = result

            start_x = x * tile_w
            h, w, _ = img_np.shape

            row_array[
                0:h,
                start_x:start_x + w,
                :
            ] = img_np

        row_path = os.path.join(
            rows_folder,
            f"row_{y:04d}.tiff"
        )

        tifffile.imwrite(
            row_path,
            row_array,
            compression="deflate"
        )

    print("\nAll row images saved.\n")

    # =====================================================
    # STEP 2
    # Merge saved rows into ONE final BigTIFF
    # =====================================================

    print("STEP 2: Creating final BigTIFF...\n")

    final_memmap = tifffile.memmap(
        final_output,
        shape=(
            full_height,
            full_width,
            3
        ),
        dtype=np.uint8,
        bigtiff=True
    )

    for y in range(max_y):
        print(f"Inserting row {y + 1} / {max_y}")

        row_path = os.path.join(
            rows_folder,
            f"row_{y:04d}.tiff"
        )

        if not os.path.exists(row_path):
            print(
                f"Missing row file: {row_path}"
            )
            continue

        try:
            row_data = tifffile.imread(
                row_path
            )

            start_y = y * tile_h
            end_y = start_y + tile_h

            final_memmap[
                start_y:end_y,
                :,
                :
            ] = row_data

        except Exception as e:
            print(
                f"Error loading row: {row_path}"
            )
            print(e)

    final_memmap.flush()

    print("\n======================================")
    print("DONE")
    print("Final BigTIFF saved at:")
    print(final_output)
    print("======================================")
