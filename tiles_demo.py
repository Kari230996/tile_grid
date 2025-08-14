"""
tiles_demo.py — Мини-проект по XYZ-тайлам (Web Mercator).
Функции:
- Перевод (lat, lon, zoom) → tile (x, y) и пиксели внутри тайла.
- Рендер сетки тайлов NxN вокруг точки для нескольких zoom.
- Сохранение PNG с подписями X/Y и координат.

Зависимости: Pillow (PIL) — установи:  pip install pillow

Пример запуска:
    python tiles_demo.py --lat 53.1959 --lon 50.1008 --zooms 12 13 14 --grid 3 --out ./out
"""
import argparse
import math
import os
from typing import Tuple, List

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception as e:
    raise SystemExit(
        "Ошибка: не удалось импортировать Pillow. "
        "Установите библиотеку командой: pip install pillow\n"
        f"Подробности: {e}"
    )

# ---------- Гео <-> Тайлы  ----------
def clamp_lat(lat: float) -> float:
    """Ограничить широту допустимым диапазоном Web Mercator (~±85.0511°)."""
    return max(min(lat, 85.05112878), -85.05112878)

def latlon_to_tile(lat: float, lon: float, z: int, tile_size: int = 256) -> Tuple[int, int, int, int]:
    """
    Переводит lat/lon (WGS84) в координаты тайла (x, y) на уровне масштабирования z
    и возвращает также пиксельные координаты внутри тайла (px, py).
    Схема XYZ/Web Mercator (EPSG:3857).
    """
    lat = clamp_lat(lat)
    if not (-180.0 <= lon <= 180.0):
        raise ValueError("Долгота должна быть в диапазоне [-180, 180].")
    if not (0 <= z <= 22):
        raise ValueError("Уровень масштабирования z должен быть в диапазоне [0, 22].")

    n = 2 ** z
    lat_rad = math.radians(lat)

    x_norm = (lon + 180.0) / 360.0
    y_norm = (1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0

    x_tile = int(math.floor(x_norm * n))
    y_tile = int(math.floor(y_norm * n))

    x_px_total = x_norm * n * tile_size
    y_px_total = y_norm * n * tile_size

    px_in_tile = int(x_px_total) % tile_size
    py_in_tile = int(y_px_total) % tile_size

    x_tile = max(0, min(x_tile, n - 1))
    y_tile = max(0, min(y_tile, n - 1))
    return x_tile, y_tile, px_in_tile, py_in_tile

def tile_to_bounds(x: int, y: int, z: int) -> Tuple[float, float, float, float]:
    """Границы тайла (lon_min, lat_min, lon_max, lat_max)."""
    n = 2 ** z
    def lon_deg(tx: int) -> float:
        return tx / n * 360.0 - 180.0
    def lat_deg(ty: int) -> float:
        yv = math.pi * (1 - 2 * ty / n)
        return math.degrees(math.atan(math.sinh(yv)))
    lon_min = lon_deg(x)
    lon_max = lon_deg(x + 1)
    lat_min = lat_deg(y + 1)
    lat_max = lat_deg(y)
    return lon_min, lat_min, lon_max, lat_max

# ---------- Рендер ----------
def try_load_font(size: int = 14) -> ImageFont.FreeTypeFont:
    """Пытается загрузить системный шрифт; при неудаче — встроенный."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:\\Windows\\Fonts\\consola.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()

def draw_grid(lat: float, lon: float, z: int, grid: int = 3, tile_size: int = 256) -> Image.Image:
    """
    Рисует сетку grid×grid тайлов с центрированием на тайле, где находится точка (lat, lon).
    Центр сетки — тайл с точкой; точка отмечается маркером.
    """
    if grid % 2 == 0 or grid < 1:
        raise ValueError("grid должен быть нечётным положительным числом, например 3 или 5.")

    x_c, y_c, px, py = latlon_to_tile(lat, lon, z, tile_size=tile_size)
    half = grid // 2

    width = grid * tile_size
    height = grid * tile_size
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    font = try_load_font(14)
    font_big = try_load_font(18)

    # Линии сетки
    for i in range(grid + 1):
        x = i * tile_size
        draw.line([(x, 0), (x, height)], fill=(0, 0, 0), width=1)
        y = i * tile_size
        draw.line([(0, y), (width, y)], fill=(0, 0, 0), width=1)

    # Подписи тайлов X/Y
    for gy in range(grid):
        for gx in range(grid):
            xt = x_c + (gx - half)
            yt = y_c + (gy - half)
            text = f"X={xt}  Y={yt}\nZ={z}"
            tx = gx * tile_size + 6
            ty = gy * tile_size + 6
            draw.text((tx, ty), text, fill=(0, 0, 0), font=font)

    # Маркер точки в центральном тайле
    cx = half * tile_size + px
    cy = half * tile_size + py
    r = 4
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(220, 0, 0), outline=(0, 0, 0))

    header = (
        f"Point: lat={lat:.6f}, lon={lon:.6f} | Z={z}\n"
        f"Center tile: X={x_c}, Y={y_c} | px={px}, py={py} (tile_size={tile_size})"
    )
    draw.text((10, height - 40), header, fill=(0, 0, 0), font=font_big)
    return img

def render_zooms(lat: float, lon: float, zooms: List[int], grid: int, tile_size: int, out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    for z in zooms:
        try:
            img = draw_grid(lat, lon, z, grid=grid, tile_size=tile_size)
            out_path = os.path.join(out_dir, f"grid_z{z}.png")
            img.save(out_path, format="PNG")
            x, y, px, py = latlon_to_tile(lat, lon, z, tile_size=tile_size)
            print(f"[OK] Z={z}: сохранено {out_path} | tile=({x},{y}) px=({px},{py})")
        except Exception as e:
            print(f"[ERROR] Не удалось построить изображение для Z={z}: {e}")

# ---------- CLI ----------
def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Рендер сетки тайлов вокруг точки для заданных уровней zoom (Web Mercator/XYZ).",
        epilog=(
            "Примеры:\n"
            "  python tiles_demo.py --lat 53.1959 --lon 50.1008 --zooms 12 13 14 --grid 3 --out ./out\n"
            "  python tiles_demo.py --lat 59.9386 --lon 30.3141 --zooms 12 --grid 5 --tile-size 256 --out ./out_spb\n"
        ),
        formatter_class=argparse.RawTextHelpFormatter
    )
    p.add_argument("--lat", type=float, required=True, help="Широта в градусах (WGS84). ~[-85.0511, 85.0511].")
    p.add_argument("--lon", type=float, required=True, help="Долгота в градусах (WGS84). [-180, 180].")
    p.add_argument("--zooms", type=int, nargs="+", required=True, help="Список уровней масштаба, напр.: 12 13 14")
    p.add_argument("--grid", type=int, default=3, help="Размер сетки (нечётное число). По умолчанию 3.")
    p.add_argument("--tile-size", type=int, default=256, help="Размер тайла в пикселях. По умолчанию 256.")
    p.add_argument("--out", type=str, default="./out", help="Папка для сохранения изображений.")
    return p

def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    # Валидация с понятными сообщениями
    try:
        if not (-180.0 <= args.lon <= 180.0):
            raise ValueError("Аргумент --lon вне диапазона [-180, 180].")
        if not (-90.0 <= args.lat <= 90.0):
            raise ValueError("Аргумент --lat вне диапазона [-90, 90].")
        if args.grid < 1 or args.grid % 2 == 0:
            raise ValueError("Аргумент --grid должен быть положительным нечётным числом (напр., 3 или 5).")
        if args.tile_size < 8 or args.tile_size > 2048:
            raise ValueError("Аргумент --tile-size должен быть в разумном диапазоне [8..2048].")
        for z in args.zooms:
            if z < 0 or z > 22:
                raise ValueError("Элемент в --zooms должен быть в диапазоне [0..22].")
    except Exception as e:
        print(f"[ERROR] Некорректные аргументы: {e}")
        return

    try:
        render_zooms(
            lat=args.lat,
            lon=args.lon,
            zooms=args.zooms,
            grid=args.grid,
            tile_size=args.tile_size,
            out_dir=args.out
        )
    except Exception as e:
        print(f"[ERROR] Во время рендера произошла ошибка: {e}")

if __name__ == "__main__":
    main()
