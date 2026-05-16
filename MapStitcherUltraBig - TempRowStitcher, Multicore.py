import os
from tkinter import Tk, filedialog, simpledialog
import tifffile
import numpy as np

# =========================================================
# Merge existing row TIFF files into one final BigTIFF
# Example row files:
# row_0000.tiff
# row_0001.tiff
# row_0002.tiff
# =========================================================

# Required once:
# pip install tifffile numpy

# =========================================================
# Explorer popup for folder selection
# =========================================================

root = Tk()
root.withdraw()
root.attributes("-topmost", True)

# Select folder containing row TIFF files
rows_folder = filedialog.askdirectory(
    title="Select the folder containing the row TIFF files"
)

if not rows_folder:
    print("No folder selected. Program terminated.")
    exit()

# Ask for final output filename
final_name = simpledialog.askstring(
    "Final TIFF File",
    "Enter final TIFF filename (without .tiff)"
)

if not final_name:
    final_name = "FINAL_BIGTIFF"

# Save final file one level above rows_temp if possible
parent_folder = os.path.dirname(rows_folder)

final_output = os.path.join(
    parent_folder,
    f"{final_name}.tiff"
)

# =========================================================
# Find row TIFF files
# =========================================================

row_files = []

for file in os.listdir(rows_folder):
    if file.lower().startswith("row_") and file.lower().endswith(".tiff"):
        row_files.append(file)

if not row_files:
    print("No row TIFF files found.")
    print("Expected example: row_0000.tiff")
    exit()

# Sort correctly
row_files.sort()

print("\n======================================")
print(f"Found row files: {len(row_files)}")
print("======================================\n")

# =========================================================
# Determine row size from first file
# =========================================================

first_row_path = os.path.join(rows_folder, row_files[0])

first_row = tifffile.imread(first_row_path)

row_height, full_width, channels = first_row.shape
full_height = row_height * len(row_files)

print(f"Row size: {full_width} x {row_height}")
print(f"Final image size: {full_width} x {full_height}")
print()

# =========================================================
# Create final BigTIFF using memmap
# =========================================================

print("Creating final BigTIFF...\n")

final_memmap = tifffile.memmap(
    final_output,
    shape=(full_height, full_width, channels),
    dtype=np.uint8,
    bigtiff=True
)

# =========================================================
# Insert each saved row
# =========================================================

for index, file in enumerate(row_files):
    print(f"Inserting row {index + 1} / {len(row_files)}")

    row_path = os.path.join(rows_folder, file)

    try:
        row_data = tifffile.imread(row_path)

        start_y = index * row_height
        end_y = start_y + row_height

        final_memmap[
            start_y:end_y,
            :,
            :
        ] = row_data

    except Exception as e:
        print(f"Error loading row file: {row_path}")
        print(e)

# Write to disk
final_memmap.flush()

print("\n======================================")
print("DONE")
print("Final BigTIFF saved at:")
print(final_output)
print("======================================")
