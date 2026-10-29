"""Build the public, account-free versions of the explorer from explorer/page.html.

  python scripts/build_public_explorer.py [--doi 10.5281/zenodo.XXXXXXX] [--repo https://github.com/<user>/mercury-crater-graph]
                                          [--tiles-url https://<user>.github.io/mercury-crater-graph/explorer/tiles]

Outputs
  explorer/index.html            full page with the tiled basemap (explorer/tiles/); opens from disk or any web server
  explorer/data/mcg_data.js      the data as a script, so the full page also works from file:// URLs
  index.html (repository root)   redirect to explorer/, for GitHub Pages
  dist/mercury_crater_graph_explorer.html
                                 one self-contained file: data and a coarse MDIS mosaic inlined; it draws the
                                 tiled basemap only when --tiles-url points at a hosted copy

Tiles are cut by scripts/make_tiles.py. Levels missing from a host are detected by the page, which then falls back
to the level below.
"""
import argparse, base64, html, json, os

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, ".."))
ap = argparse.ArgumentParser()
ap.add_argument("--src", default=os.path.join(ROOT, "explorer"))
ap.add_argument("--standalone", default=os.path.join(ROOT, "dist", "mercury_crater_graph_explorer.html"))
ap.add_argument("--doi", default="")
ap.add_argument("--repo", default="")
ap.add_argument("--tiles-url", default="", help="base URL of hosted tiles for the single-file build")
a = ap.parse_args()

body = open(os.path.join(a.src, "page.html"), encoding="utf-8").read()
title = body.split("<title>", 1)[1].split("</title>", 1)[0]
body = body.replace(f"<title>{title}</title>\n", "").replace('<meta name="claude:viewport-fit-sides" content="cover">\n', "")

links = []
if a.repo:
    links.append(f'Code and data: <a href="{html.escape(a.repo)}">{html.escape(a.repo)}</a>.')
if a.doi:
    links.append(f'Cite: <a href="https://doi.org/{html.escape(a.doi)}">doi:{html.escape(a.doi)}</a>.')
if links:
    anchor = 'Hollows: Bickel et al. (2025), georeferenced. '
    assert anchor in body
    body = body.replace(anchor, anchor + " ".join(links) + " ")

desc = ("Interactive map of Mercury's craters linked by containment, with the hollows inside them: click a crater to "
        "trace the craters and basins it formed inside and the craters that formed inside it.")
head = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{title}</title>
<meta name="description" content="{html.escape(desc)}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{html.escape(desc)}">
<style>
/* page reset (the hosted artifact supplies these itself) */
:root {{ padding-top: env(safe-area-inset-top, 0px); padding-bottom: env(safe-area-inset-bottom, 0px); box-sizing: border-box; height: 100%; }}
body {{ margin: 0; }}
img {{ max-width: 100%; }}
a {{ color: inherit; }}
</style>
"""
tail = "\n</body>\n</html>\n"
d = os.path.join(a.src, "data")
rd = lambda f: open(os.path.join(d, f), encoding="utf-8").read()
data_obj = f"nodes: {rd('nodes.json')}, edges: {rd('edges.json')}, hollows: {rd('hollows.json')}, meta: {rd('meta.json')}"
with open(os.path.join(d, "mcg_data.js"), "w", encoding="utf-8") as fh:
    fh.write("window.MCG_DATA = {" + data_obj + "};\n")


def tiles_script(base):
    cfg = {"base": base, "default": "mdis", "layers": [
        {"id": "mdis", "name": "MDIS monochrome", "maxZ": 4,
         "credit": "Basemap: MESSENGER MDIS global monochrome mosaic, 166 m/pixel, shown to 333 m/pixel (Denevi et al., 2018)."},
        {"id": "color", "name": "MDIS enhanced color", "maxZ": 3,
         "credit": "Basemap: MESSENGER MDIS enhanced-color global mosaic, 665 m/pixel; low-reflectance material appears dark blue (Denevi et al., 2018)."},
    ]}
    return f"<script>window.MCG_TILES = {json.dumps(cfg)};</script>\n"


page = head + "</head>\n<body>\n" + '<script src="data/mcg_data.js"></script>\n' + tiles_script("tiles") + body + tail
with open(os.path.join(a.src, "index.html"), "w", encoding="utf-8") as fh:
    fh.write(page)
with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as fh:
    fh.write(f'<!doctype html>\n<meta charset="utf-8">\n<title>{title}</title>\n'
             '<meta http-equiv="refresh" content="0; url=explorer/">\n'
             '<a href="explorer/">Open the Mercury crater graph explorer</a>\n')
open(os.path.join(ROOT, ".nojekyll"), "w").close()

relief = "data:image/jpeg;base64," + base64.b64encode(open(os.path.join(d, "relief_mdis.jpg"), "rb").read()).decode()
inline = "<script>window.MCG_DATA = {" + data_obj + f", relief: {json.dumps(relief)}" + "};</script>\n"
os.makedirs(os.path.dirname(a.standalone), exist_ok=True)
with open(a.standalone, "w", encoding="utf-8") as fh:
    fh.write(head + "</head>\n<body>\n" + inline + (tiles_script(a.tiles_url.rstrip("/")) if a.tiles_url else "") + body + tail)
print("page:", os.path.join(a.src, "index.html"))
print("root redirect:", os.path.join(ROOT, "index.html"))
print("standalone:", a.standalone, f"{os.path.getsize(a.standalone) / 1e6:.1f} MB")
