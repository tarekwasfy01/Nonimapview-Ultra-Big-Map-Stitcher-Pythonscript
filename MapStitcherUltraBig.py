import os
import re
import numpy as np
from PIL import Image
from tkinter import Tk, filedialog, simpledialog
import tifffile

# =========================================================
# PROFESSIONAL VERSION
# BigTIFF + Row-based + Low RAM Usage
# Safe for very large image sets
# =========================================================

# Required once:
# pip install pillow tifffile numpy

# =========================================================
# Explorer popup for folder + filename input
# =========================================================

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

# Final output name
final_name = simpledialog.askstring(
    "Final TIFF File",
    "Enter final TIFF filename (without .tiff)"
)

if not final_name:
    final_name = "FINAL_BIGTIFF"

final_output = os.path.join(folder, f"{final_name}.tiff")

# =========================================================
# Regex for files like:
# All_x7y1.jpg
# =========================================================

pattern = re.compile(
    rf"{re.escape(base_name)}_x(\d+)y(\d+)\.jpg"
)

# =========================================================
# Scan all tiles
# =========================================================

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
    print("Expected example:", f"{base_name}_x0y0.jpg")
    exit()

print("\n======================================")
print(f"Found tiles: {len(tiles)}")
print(f"Grid size: {max_x + 1} x {max_y + 1}")
print("======================================\n")

# =========================================================
# Determine tile size
# =========================================================

first_key = (0, 0)

if first_key not in tiles:
    first_key = next(iter(tiles.keys()))

first_path = os.path.join(folder, tiles[first_key])

with Image.open(first_path) as first_img:
    tile_w, tile_h = first_img.size

full_width = (max_x + 1) * tile_w
full_height = (max_y + 1) * tile_h

print(f"Tile size: {tile_w} x {tile_h}")
print(f"Final image size: {full_width} x {full_height}")
print()

# =========================================================
# BigTIFF Writer
# Row-by-row writing
# Very low RAM usage
# =========================================================

print("Creating BigTIFF...")
print("This may take a while for large projects.\n")

with tifffile.TiffWriter(final_output, bigtiff=True) as tif:

    for y in range(max_y + 1):
        print(f"Processing row {y + 1} / {max_y + 1}")

        # One row only in memory
        row_array = np.zeros(
            (tile_h, full_width, 3),
            dtype=np.uint8
        )

        for x in range(max_x + 1):
            key = (x, y)

            if key not in tiles:
                print(f"Missing tile: x={x}, y={y}")
                continue

            img_path = os.path.join(folder, tiles[key])

            try:
                with Image.open(img_path) as img:
                    img = img.convert("RGB")
                    img_np = np.array(img)

                    start_x = x * tile_w
                    end_x = start_x + tile_w

                    row_array[:, start_x:end_x, :] = img_np

            except Exception as e:
                print(f"Error loading: {img_path}")
                print(e)

        # Append row as TIFF page
        tif.write(
            row_array,
            compression="deflate",
            photometric="rgb"
        )

print("\n======================================")
print("DONE")
print("BigTIFF saved at:")
print(final_output)
print("======================================")
