# TileGrid — Visualization of XYZ Tiles (Web Mercator)

A small Python utility to demonstrate the tile map scheme (XYZ) and the relation
between **geographic coordinates** (latitude/longitude, WGS84) and **cartographic**
tile coordinates (**X/Y/Z**, Web Mercator, EPSG:3857).

---

## Features

* Convert a point *(lat, lon, Z)* → tile *(X, Y)* and pixel position *(px, py)* within a tile.
* Render a **N×N** tile grid around the point with **X/Y/Z** labels and a marker.
* Configure tile size (default 256 px), zoom levels, and grid size.
* Input validation with clear error messages.

---

## Installation

Requires Python 3.8+.

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

File `requirements.txt`:

```
pillow>=10.0.0
```

---

## Usage

Basic example (Point in Samara):

```bash
python tiles_demo.py --lat 53.1959 --lon 50.1008 --zooms 12 13 14 --grid 3 --out ./out
```

Example output:

```
[OK] Z=12: saved ./out/grid_z12.png | tile=(2618,1330) px=(9,145)
[OK] Z=13: saved ./out/grid_z13.png | tile=(5236,2661) px=(18,34)
[OK] Z=14: saved ./out/grid_z14.png | tile=(10472,5322) px=(36,69)
```

Other options:

```bash
# Larger tile (512 px) at a single zoom level
python tiles_demo.py --lat 53.1959 --lon 50.1008 --zooms 14 --grid 3 --tile-size 512 --out ./out_bigtiles

# Tallinn, 5×5 grid at Z=13
python tiles_demo.py --lat 59.437 --lon 24.7536 --zooms 13 --grid 5 --out ./out_tallinn
```

The result is PNG images with a tile grid and point marker.
The footer shows: center tile *(X, Y)* and pixel coordinates *(px, py)* of the point within it.

---

## Theory

### 1) Geographic vs. Cartographic Coordinates

* **Geographic coordinates (WGS84):** latitude φ (−90..+90°) and longitude λ (−180..+180°), independent of zoom.
* **Cartographic coordinates (Web Mercator, XYZ):** the world is divided into a **2^Z × 2^Z** grid of tiles at zoom **Z**,
  each tile usually **256×256 px**. Tile coordinates are integer indices **X, Y** depending on **Z**.

### 2) Transformation (lat, lon, Z) → (X, Y) and (px, py)

Let `n = 2^Z`, `φ` in radians.

```
x_norm = (λ + 180) / 360
y_norm = (1 - ln(tan φ + sec φ) / π) / 2

X = floor(x_norm * n)
Y = floor(y_norm * n)

px_total = x_norm * n * tile_size
py_total = y_norm * n * tile_size
px = floor(px_total) % tile_size
py = floor(py_total) % tile_size
```

Latitude is limited by Web Mercator to approx. **±85.0511°**.

### 3) Why load new tiles when zooming in?

As **Z** increases, the grid becomes denser (**2^Z × 2^Z**). The point falls into a new set of tiles at higher resolution.
The client loads **new tiles** instead of stretching old ones — this preserves detail.

### 4) Tile boundaries in degrees

For a tile *(X, Y, Z)*:

```
n = 2^Z
lon_min =  X    / n * 360 - 180
lon_max = (X+1) / n * 360 - 180

lat(y) = atan(sinh(π * (1 - 2*y/n))) in degrees
lat_max = lat(Y)
lat_min = lat(Y+1)
```

---

## Common Errors and Solutions

* `ModuleNotFoundError: No module named 'PIL'` → install `pip install pillow` in the **same venv**.
* `--grid` must be an odd positive integer (3, 5, …).
* Ranges: latitude −90..90, longitude −180..180, Z — 0..22 (practically 0..19).
* If text lines are cut off at the bottom, use a larger `--tile-size` or smaller `--grid`.
