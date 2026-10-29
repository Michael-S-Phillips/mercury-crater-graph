"""Cut a global simple-cylindrical Mercury mosaic into the explorer's basemap tile pyramid.

Tile scheme (equirectangular, east longitude 0-360, as in mars-crater-graph):
  level z has 8 * 2**z pixels per degree; tiles are 360 x 360 px and span 45 / 2**z degrees;
  rows r = 0 .. 4 * 2**z - 1 from 90N southward; columns c = 0 .. 8 * 2**z - 1 from 0E eastward;
  file: <out>/<z>/<r>/<c>.jpg

Two passes:
  --top Z      read the source in latitude strips and write level Z (resumable: rows with a .done marker are skipped)
  --pyramid Z  build levels Z-1 .. 0, each tile from the 2 x 2 tiles of the level above (existing tiles are kept)

  python make_tiles.py SRC OUT --top 4 [--quality 78] [--budget 160]
  python make_tiles.py SRC OUT --pyramid 4

The MESSENGER MDIS mosaics (USGS) use an equirectangular grid on a sphere of radius 2,439.4 km with the
central meridian at 0, so x runs from -180 to 180 degrees.
"""
import argparse, math, os, sys, time
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.enums import Resampling
from PIL import Image

TILE = 360
R_MERCURY = 2439400.0

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("out")
ap.add_argument("--top", type=int, default=None)
ap.add_argument("--pyramid", type=int, default=None)
ap.add_argument("--quality", type=int, default=78)
ap.add_argument("--budget", type=float, default=160, help="stop after this many seconds (rerun to resume)")
a = ap.parse_args()
t0 = time.time()
k = math.radians(1) * R_MERCURY


def central_meridian(ds):
    try:
        return float(ds.crs.to_dict().get("lon_0", 0.0))
    except Exception:
        return 0.0


def read_strip(ds, lat_top, lat_bot, ppd):
    """Strip covering 0-360E at ppd pixels/degree between two latitudes, shape (bands, h, w)."""
    h = int(round((lat_top - lat_bot) * ppd))
    cm = central_meridian(ds)
    halves = []
    for lon0 in (0, 180):
        x0 = ((lon0 - cm + 180) % 360) - 180
        w = from_bounds(x0 * k, lat_bot * k, (x0 + 180) * k, lat_top * k, transform=ds.transform)
        halves.append(ds.read(window=w, out_shape=(ds.count, h, int(180 * ppd)), resampling=Resampling.average))
    return np.concatenate(halves, axis=2)


def save(arr, path):
    img = Image.fromarray(arr[0] if arr.shape[0] == 1 else np.moveaxis(arr[:3], 0, -1))
    img.save(path, "JPEG", quality=a.quality, optimize=True)


if a.top is not None:
    z = a.top
    ppd, span = 8 * 2 ** z, 45 / 2 ** z
    nrow, ncol = 4 * 2 ** z, 8 * 2 ** z
    with rasterio.open(a.src) as ds:
        for r in range(nrow):
            d = os.path.join(a.out, str(z), str(r))
            if os.path.exists(os.path.join(d, ".done")):
                continue
            if time.time() - t0 > a.budget:
                print(f"budget reached at z={z} r={r}"); sys.exit(0)
            lat_top = 90 - r * span
            strip = read_strip(ds, lat_top, lat_top - span, ppd)
            os.makedirs(d, exist_ok=True)
            for c in range(ncol):
                t = strip[:, :, c * TILE:(c + 1) * TILE]
                if not (t > 0).any():
                    continue
                save(t, os.path.join(d, f"{c}.jpg"))
            open(os.path.join(d, ".done"), "w").close()
            print(f"z={z} row {r + 1}/{nrow} ({time.time() - t0:.0f}s)", flush=True)
    print(f"top level {z} done")

if a.pyramid is not None:
    for z in range(a.pyramid - 1, -1, -1):
        nrow, ncol = 4 * 2 ** z, 8 * 2 ** z
        for r in range(nrow):
            d = os.path.join(a.out, str(z), str(r))
            os.makedirs(d, exist_ok=True)
            for c in range(ncol):
                p = os.path.join(d, f"{c}.jpg")
                if os.path.exists(p):
                    continue
                canvas, any_child = None, False
                for dr in (0, 1):
                    for dc in (0, 1):
                        q = os.path.join(a.out, str(z + 1), str(2 * r + dr), f"{2 * c + dc}.jpg")
                        if not os.path.exists(q):
                            continue
                        im = Image.open(q)
                        if canvas is None:
                            canvas = Image.new(im.mode, (2 * TILE, 2 * TILE))
                        canvas.paste(im, (dc * TILE, dr * TILE)); any_child = True
                if any_child:
                    canvas.resize((TILE, TILE), Image.BOX).save(p, "JPEG", quality=a.quality, optimize=True)
        print(f"z={z} built ({time.time() - t0:.0f}s)", flush=True)
    print("pyramid done")
