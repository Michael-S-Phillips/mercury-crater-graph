"""Example figure: hollow-bearing parent craters and the craters that formed inside them.

  python scripts/make_figures.py <MDIS monochrome mosaic, 166 m/pixel> [out.png]

Each panel shows one parent crater on the MESSENGER MDIS global monochrome mosaic (Denevi et al., 2018), the craters
whose centers lie inside it (children, from outputs/), arrows from the parent to each child, and the georeferenced
hollows. Children with hollows inside 0.9 of their radius are gold; children without hollows are blue.
"""
import json, math, os, sys
import numpy as np
import rasterio
from rasterio.windows import from_bounds
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, FancyArrowPatch

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
SRC = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "figures", "fig_nested_examples.png")
R_M = 2439.4; KPD = math.radians(1) * R_M; K_M = math.radians(1) * R_M * 1000
mpl.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.5, "axes.linewidth": 0.6})
INK, GOLD, BLUE, HOLLOW = "#1a1a19", "#E9A91F", "#4F97EA", "#FFE24D"

d = os.path.join(ROOT, "explorer", "data")
N = json.load(open(os.path.join(d, "nodes.json"))); H = json.load(open(os.path.join(d, "hollows.json")))
idx = {k: i for i, k in enumerate(N["id"])}
lat = np.array(N["lat"]) / 1e4; lon = np.array(N["lon"]) / 1e4; D = np.array(N["D"]) / 100
par = np.array(N["parent"]); n09 = np.array(N["n09"])
hlat = np.array(H["lat"]) / 1e4; hlon = np.array(H["lon"]) / 1e4

PANELS = [("200309", "Praxiteles"), ("200362", "Lermontov")]
fig, axs = plt.subplots(1, len(PANELS), figsize=(7.2, 3.75))
with rasterio.open(SRC) as ds:
    for ax, (pid, label) in zip(axs, PANELS):
        p = idx[pid]; la0, lo0 = lat[p], lon[p]; cl = math.cos(math.radians(la0))
        half = 0.68 * D[p] / KPD                                   # half-width in degrees of latitude
        lo_c = ((lo0 + 180) % 360) - 180                           # mosaic x runs -180..180
        w = from_bounds((lo_c - half / cl) * K_M, (la0 - half) * K_M, (lo_c + half / cl) * K_M, (la0 + half) * K_M, transform=ds.transform)
        img = ds.read(1, window=w)
        ext = half * KPD
        ax.imshow(img, cmap="gray", extent=(-ext, ext, -ext, ext), vmin=np.percentile(img, 1), vmax=np.percentile(img, 99.5), interpolation="lanczos")
        def xy(la, lo):
            return ((lo - lo0 + 540) % 360 - 180) * cl * KPD, (la - la0) * KPD
        ax.add_patch(Ellipse((0, 0), D[p], D[p], fill=False, ec="white", lw=1.2, ls=(0, (5, 3))))
        kids = np.where(par == p)[0]
        for k in kids:
            x, y = xy(lat[k], lon[k]); col = GOLD if n09[k] > 0 else BLUE
            ax.add_patch(FancyArrowPatch((0, 0), (x, y), arrowstyle="-|>", mutation_scale=7, color="white", lw=0.7, alpha=0.85, shrinkB=D[k] / 2 * 3.0))
            ax.add_patch(Ellipse((x, y), D[k], D[k], fill=False, ec=col, lw=1.6))
        m = (np.abs(hlat - la0) < half) & (np.abs(((hlon - lo0 + 540) % 360) - 180) < half / cl)
        hx, hy = xy(hlat[m], hlon[m])
        ax.scatter(hx, hy, s=5, c=HOLLOW, edgecolors="black", linewidths=0.3, zorder=5)
        ax.set_xlim(-ext, ext); ax.set_ylim(-ext, ext); ax.set_xticks([]); ax.set_yticks([])
        nh = int((n09[kids] > 0).sum())
        ax.set_title(f"{label}, {D[p]:.0f} km: {nh} of {len(kids)} craters inside have hollows", fontsize=7.5, loc="left", color=INK)
        ax.plot([ext * 0.55, ext * 0.55 + 50], [-ext * 0.9, -ext * 0.9], color="white", lw=2)
        ax.text(ext * 0.55 + 25, -ext * 0.85, "50 km", color="white", ha="center", va="bottom", fontsize=7)
        ax.text(-ext * 0.95, ext * 0.92, f"{abs(la0):.1f}°{'N' if la0 >= 0 else 'S'}, {lo0:.1f}°E", color="white", fontsize=6.5, va="top")
from matplotlib.lines import Line2D
h = [Line2D([], [], color="#555555", ls=(0, (5, 3)), lw=1.2, label="parent rim (white on map)"),
     Line2D([], [], marker="o", ls="", mfc="none", mec=GOLD, mew=1.6, ms=8, label="crater inside, with hollows"),
     Line2D([], [], marker="o", ls="", mfc="none", mec=BLUE, mew=1.6, ms=8, label="crater inside, no hollows"),
     Line2D([], [], marker="o", ls="", mfc=HOLLOW, mec="black", mew=0.3, ms=4, label="hollow")]
fig.legend(handles=h, loc="lower center", ncol=4, frameon=False, fontsize=7, bbox_to_anchor=(0.5, 0.0))
fig.subplots_adjust(left=0.01, right=0.99, top=0.92, bottom=0.09, wspace=0.04)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
fig.savefig(OUT, dpi=400, facecolor="white"); fig.savefig(OUT.replace(".png", ".pdf"), facecolor="white")
print("wrote", OUT)
