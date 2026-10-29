"""Export compact JSON for the interactive explorer page.

  python scripts/export_explorer.py            (reads outputs/ and inputs/, writes explorer/data/)

Writes explorer/data/nodes.json, edges.json, hollows.json, and meta.json. The global overview images
explorer/data/relief_mdis.jpg and relief_color.jpg are assembled from tile level 0 (scripts/make_tiles.py).
"""
import json, os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
OUT, INP, DEST = os.path.join(ROOT, "outputs"), os.path.join(ROOT, "inputs"), os.path.join(ROOT, "explorer", "data")
os.makedirs(DEST, exist_ok=True)

n = pd.read_csv(os.path.join(OUT, "crater_dag_nodes.csv.gz"), dtype={"id": str, "parent_id": str}, keep_default_na=False, low_memory=False,
                na_values={"rho": [""], "z_max": [""], "z_own": [""]})
c = pd.read_csv(os.path.join(INP, "herrick2018_craters_with_hosts.csv"), dtype={"unique_id": str})
names = dict(zip(c.unique_id, c.name.fillna("").astype(str).str.strip()))
h = pd.read_csv(os.path.join(INP, "hollows.csv"))
h["host"] = h.host_uid.dropna().astype(int).astype(str).reindex(h.index)
n09 = h[h.rho <= 0.9].host.value_counts(); nall = h.host.value_counts()

N = len(n)
parent = n.parent.astype(int).values
order = np.argsort(-n.D.values, kind="stable")          # parents precede children (already sorted, kept explicit)
height = np.zeros(N, int); ndesc = np.zeros(N, int); ndesch = np.zeros(N, int)
host09 = n.id.map(n09).fillna(0).astype(int).values
for i in order[::-1]:                                   # children before parents
    p = parent[i]
    if p >= 0:
        height[p] = max(height[p], height[i] + 1); ndesc[p] += ndesc[i] + 1; ndesch[p] += ndesch[i] + (host09[i] > 0)
zone = {"none": 0, "peak": 1, "floor": 2, "wall": 3}
pres = {"f": 3, "s": 2, "d": 1}
nm = [names.get(i, "") if k == "crater" else i.replace("orgel_", "") for i, k in zip(n.id, n.kind)]
nodes = {
    "id": n.id.tolist(), "name": nm,
    "kind": (n.kind == "basin").astype(int).tolist(),
    "lat": (n.lat * 1e4).round().astype(int).tolist(), "lon": (n.lon * 1e4).round().astype(int).tolist(),
    "D": (n.D * 100).round().astype(int).tolist(),
    "parent": parent.tolist(),
    "rho": np.nan_to_num(n.rho.astype(float).values * 1000, nan=-1).round().astype(int).tolist(),
    "zone": [zone.get(z, 0) for z in n.zone],
    "depth": n.chain.astype(int).tolist(), "height": height.tolist(),
    "nDesc": ndesc.tolist(), "nDescHost": ndesch.tolist(),
    "n09": host09.tolist(), "nAll": n.id.map(nall).fillna(0).astype(int).tolist(),
    "pres": [pres.get(str(p).strip(), 0) for p in n.preserved],
    "zOwn": (n.z_own.astype(float) * 100).round().astype(int).tolist(),
    "zMax": (n.z_max.astype(float) * 100).round().astype(int).tolist(),
    "fillOnly": n.fill_only.astype(str).str.lower().eq("true").astype(int).tolist(),
    "ring": n.possible_ring.astype(str).str.lower().eq("true").astype(int).tolist(),
}
ch = n[n.parent >= 0]
edges = {"o": ch.parent.astype(int).tolist(), "y": ch.index.astype(int).tolist()}
idx = {k: i for i, k in enumerate(n.id)}
hol = {"lat": (h.lat * 1e4).round().astype(int).tolist(), "lon": ((h.lon % 360) * 1e4).round().astype(int).tolist(),
       "host": [idx.get(x, -1) if isinstance(x, str) else -1 for x in h.host],
       "in09": (h.rho <= 0.9).astype(int).tolist()}
rec = json.load(open(os.path.join(OUT, "crater_dag_record.json")))
tst = json.load(open(os.path.join(OUT, "crater_dag_tests_record.json")))
sen = json.load(open(os.path.join(OUT, "crater_dag_sens_record.json")))
craters = n.kind == "crater"
meta = {"summary": {
    "craters": int(craters.sum()), "basins": int((n.kind == "basin").sum()),
    "nested": int(((n.parent >= 0) & craters).sum()), "chain_max": int(n.chain.max()) + 1,
    "hollows": int(len(h)), "hosts09": int(((host09 > 0) & craters.values).sum())},
    "results": {"nested_OR": sen["all"]["nested"], "inherit_OR": sen["inherit_all"]["parent_h09"],
                "within_parent": tst["within_parent_clogit_h09"]["params"]["inner"]}}
for name, obj in (("nodes", nodes), ("edges", edges), ("hollows", hol), ("meta", meta)):
    json.dump(obj, open(os.path.join(DEST, f"{name}.json"), "w"), separators=(",", ":"))
for f in sorted(os.listdir(DEST)):
    print(f, os.path.getsize(os.path.join(DEST, f)))
print(json.dumps(meta))
