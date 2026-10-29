#!/usr/bin/env python3
"""Containment graph of Mercury craters and the depth of origin of material in hollow hosts.

Adapts the superposition graph of mars-crater-graph (Phillips, Zenodo 10.5281/zenodo.23675713) to Mercury. A crater whose
center lies inside a feature at least twice its diameter is younger than that feature (the larger impact would have erased
it). Edges point older -> younger; with containment only, each crater has one immediate parent (the smallest feature that
contains it), so the graph is a forest.

Depth of origin. An impact inside an earlier crater excavates and uplifts material that the earlier crater already brought
up. For each crater the script estimates the deepest pre-impact level it exposes, z_max = z_base + z_own, where
  z_own  = max(excavation depth 0.1 D_tc, stratigraphic uplift 0.086 D^1.03 for complex craters) (Croft 1985;
           Cintala and Grieve 1998), with D_tc = D_sc^0.15 D^0.85, D_sc = 12 km (D_tc = D/1.2 for simple craters);
  z_base = depth of origin of the parent's surface where the child formed: z_base(parent) + SU(parent) on the parent's
           peak (rho < 0.2), z_base(parent) + h_exc(parent) on its floor (0.2-0.6), z_base(parent) on its wall (>= 0.6),
           where rho is the child's center distance in parent radii. A child on a filled floor must first cut through
           the fill (t_fill from the depth deficit against fresh craters, Section S7); a child whose excavation does not
           exceed t_fill exposes only fill (fill_only).
These are first-order scalings; the tests below ask only whether the extra depth from nesting predicts hosting.

Inputs (inputs/ folder of this repository; see inputs/README.md): Herrick et al. (2018) craters >= 5 km with hollow-host
flags, Orgel et al. (2020) basins, crater floor depths from the USGS 665 m DEM, hollows with their host craters and radial
positions, completeness for 1 km hollows, the northern smooth plains mask, and the thermal-model grid (scripts/thermal.py).
Writes outputs/crater_dag_nodes.csv.gz, outputs/edges.csv, and outputs/crater_dag_record.json.
Usage: python3 scripts/crater_dag.py [inputs folder, default ../inputs]
"""
import sys, os, json
import numpy as np, pandas as pd
from scipy.spatial import cKDTree
import statsmodels.formula.api as smf

HERE = os.path.dirname(os.path.abspath(__file__))
INP = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "inputs"))
OUT = os.path.join(HERE, "..", "outputs"); os.makedirs(OUT, exist_ok=True)
R_M, DSC = 2439.4, 12.0
sys.path.insert(0, HERE); import thermal

# ---------------------------------------------------------------- nodes
c = pd.read_csv(f"{INP}/herrick2018_craters_with_hosts.csv")
c = pd.DataFrame(dict(id=c.unique_id.astype(str), kind="crater", lat=c.latitude, lon=c.lon360 % 360, D=c.diameter,
                      hosts=c.hosts, filled=c.filled.fillna("").str.strip().str.lower(),
                      preserved=c.preserved.fillna("").str.strip(), cent=c.cent_str.fillna("").str.strip()))
o = pd.read_csv(f"{INP}/orgel2020_basins.csv")
o = o[o.Confidence.isin(["Certain", "Probable"])]
b = pd.DataFrame(dict(id="orgel_" + o.Basin_Name.astype(str), kind="basin", lat=o.y_coord, lon=o.x_coord % 360,
                      D=o.Diam_km, hosts=np.nan, filled="", preserved="", cent=""))
def unit(lat, lon):
    la, lo = np.radians(lat), np.radians(lon)
    return np.c_[np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)]
uc, ub = unit(c.lat, c.lon), unit(b.lat, b.lon)
# drop Orgel basins that duplicate a cataloged crater (near-concentric, similar size)
dup = []
for i in range(len(b)):
    ang = np.arccos(np.clip(uc @ ub[i], -1, 1)) * R_M
    rb = b.D.iloc[i] / 2
    m = (ang < 0.15 * rb) & (c.D.values / b.D.iloc[i] > 0.7) & (c.D.values / b.D.iloc[i] < 1.43)
    dup.append(bool(m.any()))
b = b[~np.array(dup)]
n = pd.concat([c, b], ignore_index=True).sort_values("D", ascending=False).reset_index(drop=True)
u = unit(n.lat, n.lon); D = n.D.values; r = D / 2

# ---------------------------------------------------------------- containment (center inside a feature >= 2x larger)
tree = cKDTree(u)
parent = np.full(len(n), -1); rho = np.full(len(n), np.nan); ncont = np.zeros(len(n), int)
for p in np.where(D >= 10)[0]:                       # D sorted descending: later (smaller) parents overwrite
    hits = np.asarray(tree.query_ball_point(u[p], 2 * np.sin(min(r[p] / R_M, np.pi) / 2)))
    hits = hits[D[hits] <= D[p] / 2]
    if hits.size == 0: continue
    d = np.arccos(np.clip(u[hits] @ u[p], -1, 1)) * R_M
    inside = d < r[p]
    hits, d = hits[inside], d[inside]
    ncont[hits] += 1
    parent[hits] = p; rho[hits] = d / r[p]
n["parent"] = parent; n["rho"] = rho; n["n_containers"] = ncont
# ring artifacts: large, near-concentric nested circles
n["possible_ring"] = (parent >= 0) & (n.rho < 0.2) & (n.D >= 20) & (n.D / np.where(parent >= 0, D[np.maximum(parent, 0)], 1) >= 0.3)

# ---------------------------------------------------------------- depth model
Dtc = np.where(D > DSC, DSC ** 0.15 * D ** 0.85, D / 1.2)
h_exc = 0.1 * Dtc
SU = np.where(D > DSC, 0.086 * D ** 1.03, 0.0)
z_own = np.maximum(h_exc, SU)
m = pd.read_csv(f"{INP}/crater_floor_depths.csv")[["uid", "depth"]]
m["id"] = m.uid.astype(str)
n = n.merge(m[["id", "depth"]], on="id", how="left")
d_fresh = 0.241 * D ** 0.486                          # km, 90th percentile depth of isolated craters (Section S7)
t_fill = np.clip(d_fresh - n.depth.values / 1000, 0, None)     # NaN where no DEM depth (craters < 10 km, basins)
t_fill = np.where(n.id == "200001", np.nan, t_fill)
cal = n.index[(n.D > 1500) & (n.D < 1700) & (abs(n.lat - 31) < 3)]
t_fill[cal] = 3.0                                     # Caloris interior plains 2.5-3.5 km (Ernst et al. 2015)
n["h_exc"], n["SU"], n["z_own"], n["t_fill"] = h_exc, SU, z_own, t_fill
zone = np.where(n.parent < 0, "none", np.where(n.rho < 0.2, "peak", np.where(n.rho < 0.6, "floor", "wall")))
# a simple-crater parent has no peak: treat its interior as floor
simple_parent = (n.parent >= 0) & (D[np.maximum(n.parent, 0)] <= DSC)
zone = np.where(simple_parent & (zone == "peak"), "floor", zone)
n["zone"] = zone
z_base = np.zeros(len(n)); z_max = z_own.copy(); fill_only = np.zeros(len(n), bool); fill_known = np.ones(len(n), bool)
for i in range(len(n)):                               # parents precede children (sorted by D)
    p = n.parent.iat[i]
    if p < 0: continue
    zb_p = z_base[p] if not fill_only[p] else 0.0
    zz = n.zone.iat[i]
    loc = SU[p] if zz == "peak" else (h_exc[p] if zz == "floor" else 0.0)
    tf = t_fill[p] if zz in ("peak", "floor") else 0.0
    if np.isnan(tf): tf = 0.0; fill_known[i] = False
    reach = z_own[i] - tf
    if reach <= 0:
        fill_only[i] = True; z_base[i] = 0.0; z_max[i] = 0.0
    else:
        z_base[i] = zb_p + loc; z_max[i] = z_base[i] + reach
n["z_base"], n["z_max"], n["fill_only"], n["fill_known"] = z_base, z_max, fill_only, fill_known
# chain depth (number of ancestors)
depth_chain = np.zeros(len(n), int)
for i in range(len(n)):
    p = n.parent.iat[i]
    if p >= 0: depth_chain[i] = depth_chain[p] + 1
n["chain"] = depth_chain

# ---------------------------------------------------------------- covariates
C1 = np.load(f"{INP}/completeness_1km_10ppd.npz")["C1"]
nsp = np.load(f"{INP}/northern_plains_mask_10ppd.npz")["mask"]
rr = ((90 - n.lat.values) * 10).astype(int).clip(0, 1799); cc = (n.lon.values * 10).astype(int).clip(0, 3599)
n["C1"] = np.nan_to_num(C1[rr, cc]); n["nsp"] = nsp[rr, cc].astype(int)
z = np.load(f"{INP}/thermal_grid.npz")
n["Tm"] = thermal.lookup(z["la"], z["lo"], z["G"], n.lat.values, n.lon.values)
n["dT"] = n.Tm - thermal.lookup(z["la"], z["lo"], z["G"], n.lat.values, np.full(len(n), 90.0))
h = pd.read_csv(f"{INP}/hollows.csv", usecols=["host_uid"])
k = h.host_uid.dropna().astype(int).astype(str).value_counts()
n["n_hollows"] = n.id.map(k).fillna(0).astype(int)
n["abslat"] = n.lat.abs(); n["logD"] = np.log10(n.D)
n["parent_id"] = np.where(n.parent >= 0, n.id.values[np.maximum(n.parent, 0)], "")
n["parent_D"] = np.where(n.parent >= 0, D[np.maximum(n.parent, 0)], np.nan)
n["parent_kind"] = np.where(n.parent >= 0, n.kind.values[np.maximum(n.parent, 0)], "")
n["parent_fresh_like"] = np.where(n.parent >= 0, n.preserved.values[np.maximum(n.parent, 0)], "")
n.drop(columns=["depth"]).to_csv(f"{OUT}/crater_dag_nodes.csv.gz", index=False)
E = n[n.parent >= 0]
pd.DataFrame(dict(older_id=n.id.values[E.parent.values], younger_id=E.id, older_D_km=D[E.parent.values], younger_D_km=E.D, rho=E.rho.round(4), zone=E.zone)).to_csv(f"{OUT}/edges.csv", index=False)

# ---------------------------------------------------------------- tests (cataloged craters >= 5 km)
R = {}
s = n[(n.kind == "crater") & (~n.possible_ring)].copy()
s["nested"] = (s.parent >= 0).astype(int)
s["ln_zown"] = np.log(s.z_own); s["ln_zmax"] = np.log(np.maximum(s.z_max, 0.05))
R["counts"] = dict(nodes=int(len(n)), craters=int((n.kind == "crater").sum()), basins_kept=int((n.kind == "basin").sum()),
                   nested=int(s.nested.sum()), by_zone=s.zone.value_counts().to_dict(),
                   chain=s.chain.value_counts().sort_index().to_dict(), possible_ring=int(n.possible_ring.sum()),
                   fill_only=int(s.fill_only.sum()), fill_unknown_nested=int(((~s.fill_known) & (s.nested == 1)).sum()),
                   hosts=int(s.hosts.sum()), hosts_nested=int(s[s.nested == 1].hosts.sum()))
def fit(formula, d, name):
    mm = smf.logit(formula, data=d).fit(disp=0)
    R[name] = dict(n=int(mm.nobs), hosts=int(d.hosts.sum()), aic=float(mm.aic),
                   params={k: [float(v), float(mm.bse[k]), float(mm.pvalues[k])] for k, v in mm.params.items()})
    return mm
ctrl = "logD + abslat + C1 + nsp + dT"
fit(f"hosts ~ {ctrl}", s, "base")
fit(f"hosts ~ {ctrl} + nested", s, "nested")
s["zone_c"] = pd.Categorical(np.where(s.fill_only, "fill_only", s.zone), categories=["none", "peak", "floor", "wall", "fill_only"])
fit(f"hosts ~ {ctrl} + C(zone_c)", s, "zone")
fit(f"hosts ~ {ctrl} + z_base", s, "z_base")
fit("hosts ~ ln_zown + abslat + C1 + nsp + dT", s, "ln_zown")
fit("hosts ~ ln_zmax + abslat + C1 + nsp + dT", s, "ln_zmax")
fit("hosts ~ ln_zown + ln_zmax + abslat + C1 + nsp + dT", s, "ln_zown_zmax")
# same tests where the fill of every nested crater's parent is known, and with completeness >= 0.2
sk = s[(s.nested == 0) | (s.fill_known)]
fit(f"hosts ~ {ctrl} + z_base", sk, "z_base_fillknown")
fit("hosts ~ ln_zown + abslat + C1 + nsp + dT", sk, "ln_zown_fillknown")
fit("hosts ~ ln_zmax + abslat + C1 + nsp + dT", sk, "ln_zmax_fillknown")
sc = s[s.C1 >= 0.2]
fit(f"hosts ~ {ctrl} + C(zone_c)", sc, "zone_C02")
fit("hosts ~ ln_zown + abslat + C1 + nsp + dT", sc, "ln_zown_C02")
fit("hosts ~ ln_zmax + abslat + C1 + nsp + dT", sc, "ln_zmax_C02")
# raw rates by zone and size bin (completeness >= 0.2)
rows = []
for lo_, hi_ in [(5, 10), (10, 20), (20, 40), (40, 100), (100, 2000)]:
    t = sc[(sc.D >= lo_) & (sc.D < hi_)]
    row = dict(D=f"{lo_}-{hi_}")
    for zz in ["none", "peak", "floor", "wall", "fill_only"]:
        tt = t[t.zone_c == zz]; row[zz] = f"{int(tt.hosts.sum())}/{len(tt)}"
    rows.append(row)
R["rates_C02"] = rows
# chain depth at fixed size
fit(f"hosts ~ {ctrl} + C(chain.clip(upper=3))", s.assign(chain=s.chain), "chain")
# hollow-weighted: where do hollows sit?
hh = s[s.n_hollows > 0]
R["hollow_hosts"] = dict(n=int(len(hh)), hollows=int(hh.n_hollows.sum()),
                         frac_nested=float(hh.nested.mean()), frac_nested_all=float(s.nested.mean()),
                         z_base_median_nested_hosts=float(hh[hh.nested == 1].z_base.median()),
                         z_base_median_nested_all=float(s[s.nested == 1].z_base.median()))
json.dump(R, open(f"{OUT}/crater_dag_record.json", "w"), indent=1)
print(json.dumps(R, indent=1))
