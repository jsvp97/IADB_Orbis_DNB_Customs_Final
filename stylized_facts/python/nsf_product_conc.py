"""
SF-B, the neat framing: PRODUCT-LEVEL export concentration, naive vs
ownership-adjusted. For each HS6 (pooled across LAC), compute concentration
(HHI, top-1 share, effective # exporters) treating each exporting affiliate
(country,Tax_ID) as a separate firm -- then regroup affiliates of the same
parent (within country, then across countries). The rise in concentration is
the part hidden by counting one multinational as many local firms.

No firm names used -- only concentration statistics.

Unit source: base -> (hs, country, Tax_ID) with value, matched, parent group.
"""
from __future__ import annotations
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import BASE_FILE, INT, EXCLUDED_ORIGINS, parquet_chunks  # noqa: E402

CACHE = INT / "nsf_hs_firm.parquet"
def clean(s): return s.astype("string").str.strip().replace({"": pd.NA, ".": pd.NA})

if CACHE.exists():
    print(">>> loading (hs,country,Tax_ID) cache"); df = pd.read_parquet(CACHE)
else:
    t0 = time.time(); parts = []
    cols = ["country_orig", "hs07_6d", "Tax_ID", "value_fob", "_merge_DNB_Orbis",
            "ent_name_par", "globalultimatebusinessname"]
    for i, ch in enumerate(parquet_chunks(BASE_FILE, cols, 1_000_000), 1):
        ch = ch[~ch.country_orig.isin(EXCLUDED_ORIGINS)]
        ch = ch[ch.Tax_ID.notna() & ch.hs07_6d.notna()]
        ch["v"] = ch.value_fob.abs()
        ch = ch[ch.v > 0]
        ch["matched"] = (ch._merge_DNB_Orbis == 3).astype("int8")
        par = clean(ch.ent_name_par).fillna(clean(ch.globalultimatebusinessname)).str.upper().str.strip()
        ch["parent"] = par.where(ch.matched == 1)
        ch["hs"] = ch.hs07_6d.astype(str)
        parts.append(ch.groupby(["hs", "country_orig", "Tax_ID"], as_index=False)
                       .agg(value=("v", "sum"), matched=("matched", "max"), parent=("parent", "first")))
        print(f"    chunk {i}: {time.time()-t0:.0f}s")
    df = (pd.concat(parts, ignore_index=True)
            .groupby(["hs", "country_orig", "Tax_ID"], as_index=False)
            .agg(value=("value", "sum"), matched=("matched", "max"), parent=("parent", "first")))
    df.to_parquet(CACHE, index=False)
    print(f"  (hs,country,Tax_ID) rows: {len(df):,} ({time.time()-t0:.0f}s)")

df["value"] = df["value"].astype(float)
has_par = (df["matched"] == 1) & df["parent"].notna()
tin = df["country_orig"].astype(str) + "|" + df["Tax_ID"].astype(str)
df["u_naive"]  = tin
df["u_within"] = np.where(has_par, df["country_orig"].astype(str) + "|P|" + df["parent"].astype(str), tin)
df["u_cross"]  = np.where(has_par, "P|" + df["parent"].astype(str), tin)

hs_tot = df.groupby("hs")["value"].sum().rename("hstot")

def conc(unit):
    g = df.groupby(["hs", unit])["value"].sum().reset_index()
    g = g.merge(hs_tot, on="hs")
    g["sh"] = g["value"] / g["hstot"]
    hhi = g.assign(s2=g.sh ** 2).groupby("hs")["s2"].sum().rename("hhi")
    top1 = g.groupby("hs")["sh"].max().rename("top1")
    nfirm = g.groupby("hs").size().rename("nfirm")
    return pd.concat([hhi, top1, nfirm], axis=1)

print("\ncomputing product-level concentration (naive / within / cross) ...")
res = {}
for u in ["u_naive", "u_within", "u_cross"]:
    res[u] = conc(u)

M = res["u_naive"].join(res["u_within"], rsuffix="_w").join(res["u_cross"], rsuffix="_c")
M = M.join(hs_tot)
w = M["hstot"]

def wmean(x): return np.average(x, weights=w)

print(f"\nproducts (HS6): {len(M):,} | total LAC export value ${w.sum()/1e9:.0f}bn")
print(f"\n{'measure':30s} {'naive':>10} {'within-ctry':>12} {'cross-ctry':>11}")
print(f"{'value-wtd mean HHI':30s} {wmean(M.hhi):10.3f} {wmean(M.hhi_w):12.3f} {wmean(M.hhi_c):11.3f}")
print(f"{'value-wtd mean top-1 share':30s} {wmean(M.top1):10.2%} {wmean(M.top1_w):12.2%} {wmean(M.top1_c):11.2%}")
print(f"{'value-wtd eff. # firms (1/HHI)':30s} {wmean(1/M.hhi):10.1f} {wmean(1/M.hhi_w):12.1f} {wmean(1/M.hhi_c):11.1f}")

# where does grouping bite? products with meaningful MNE presence
mne_sh = (df[has_par].groupby("hs")["value"].sum() / hs_tot).rename("mne_sh").reindex(M.index).fillna(0)
heavy = M[mne_sh >= 0.5]; wh = heavy["hstot"]
print(f"\nMNE-heavy products (MNE >=50% of product exports): {len(heavy):,} "
      f"({wh.sum()/w.sum():.0%} of value)")
print(f"   HHI naive->cross: {np.average(heavy.hhi,weights=wh):.3f} -> {np.average(heavy.hhi_c,weights=wh):.3f}")
print(f"   top-1 naive->cross: {np.average(heavy.top1,weights=wh):.1%} -> {np.average(heavy.top1_c,weights=wh):.1%}")
print(f"   eff #firms naive->cross: {np.average(1/heavy.hhi,weights=wh):.1f} -> {np.average(1/heavy.hhi_c,weights=wh):.1f}")

# distribution of the concentration jump
M["dhhi"] = M.hhi_c - M.hhi
print(f"\nvalue-wtd share of products where cross-grouping raises HHI: {wmean((M.dhhi>1e-9).astype(float)):.0%}")
print(f"median HHI increase (value-wtd via quantiles):")
for q in (0.5,0.75,0.9,0.99):
    # weighted quantile approx
    order=np.argsort(M.dhhi.values); dv=M.dhhi.values[order]; ww=w.values[order]; cw=np.cumsum(ww)/ww.sum()
    print(f"   p{int(q*100)}: {dv[np.searchsorted(cw,q)]:.3f}")
M.reset_index().to_parquet(INT / "nsf_hs_conc.parquet", index=False)
print("\n>>> nsf_product_conc done.")
