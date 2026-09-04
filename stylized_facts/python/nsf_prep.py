"""
Prep for the two NEW stylized facts (network size + cross-country shared parents).

Backbone table: foreign-MNE export value by (parent group, origin country), where
the parent group = name_parent_adj = upper-trim of ent_name_par (Orbis) or, if
missing, globalultimatebusinessname (D&B) -- the SAME key used in
build_network_size.py, so the two merge cleanly.

Sample: matched firms (_merge_DNB_Orbis==3), FOREIGN MNE (iso3_parent != origin),
with a non-empty parent name. Ecuador excluded. Value = |value_fob|.

Outputs (1_Input/Intermediate/):
  nsf_parent_country.parquet   parent x origin -> export value (+ iso3_parent)
  nsf_parent.parquet           parent -> total export value, #origins exported,
                               merged with network size (total_affiliates, n_countries,
                               n_sectors, ...)
"""
from __future__ import annotations
import sys, time
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import BASE_FILE, INT, EXCLUDED_ORIGINS, parquet_chunks  # noqa: E402

PC_CACHE = INT / "nsf_parent_country.parquet"   # name-based (for SF-A network merge + SF-B robustness)
ID_CACHE = INT / "nsf_id_country.parquet"       # guo25/ID-based (SF-B primary, robust across borders)
P_CACHE  = INT / "nsf_parent.parquet"
NET      = INT / "network_size_by_parent.parquet"

def clean(s):
    return s.astype("string").str.strip().replace({"": pd.NA, ".": pd.NA})

t0 = time.time()
cols = ["country_orig", "value_fob", "_merge_DNB_Orbis", "iso3_parent",
        "ent_name_par", "globalultimatebusinessname", "ID_Orbis_DNB"]
parts_n, parts_i = [], []
print(">>> building parent x country foreign-MNE export tables (name + id keys) ...")
for i, ch in enumerate(parquet_chunks(BASE_FILE, cols, 1_000_000), 1):
    ch = ch[ch["_merge_DNB_Orbis"] == 3]
    ch = ch[~ch["country_orig"].isin(EXCLUDED_ORIGINS)]
    if ch.empty:
        continue
    ip = clean(ch["iso3_parent"])
    foreign = ip.notna() & (ip != ch["country_orig"])
    if not foreign.any():
        continue
    pe = clean(ch["ent_name_par"]); gu = clean(ch["globalultimatebusinessname"])
    npar = pe.fillna(gu).str.upper().str.strip()
    # Sebastian's cleaned unified Orbis+D&B parent id (100% coverage on matched)
    idv = clean(ch["ID_Orbis_DNB"])
    val = ch["value_fob"].abs()
    co = ch["country_orig"]

    kn = foreign & npar.notna()
    if kn.any():
        s = pd.DataFrame({"name_parent_adj": npar[kn], "country_orig": co[kn],
                          "iso3_parent": ip[kn], "val": val[kn]})
        parts_n.append(s.groupby(["name_parent_adj", "country_orig"], as_index=False)
                        .agg(val=("val", "sum"), iso3_parent=("iso3_parent", "first")))
    ki = foreign & idv.notna()
    if ki.any():
        s = pd.DataFrame({"ID_Orbis_DNB": idv[ki], "country_orig": co[ki],
                          "iso3_parent": ip[ki], "name": npar[ki], "val": val[ki]})
        parts_i.append(s.groupby(["ID_Orbis_DNB", "country_orig"], as_index=False)
                        .agg(val=("val", "sum"), iso3_parent=("iso3_parent", "first"),
                             name=("name", "first")))
    print(f"    chunk {i}: {time.time()-t0:.0f}s")

pc = (pd.concat(parts_n, ignore_index=True)
        .groupby(["name_parent_adj", "country_orig"], as_index=False)
        .agg(val=("val", "sum"), iso3_parent=("iso3_parent", "first")))
pc.to_parquet(PC_CACHE, index=False)
idc = (pd.concat(parts_i, ignore_index=True)
         .groupby(["ID_Orbis_DNB", "country_orig"], as_index=False)
         .agg(val=("val", "sum"), iso3_parent=("iso3_parent", "first"), name=("name", "first")))
idc.to_parquet(ID_CACHE, index=False)
print(f"  NAME key: {len(pc):,} rows | {pc['name_parent_adj'].nunique():,} parents "
      f"| mean origins/parent {len(pc)/pc['name_parent_adj'].nunique():.2f}")
print(f"  ID   key: {len(idc):,} rows | {idc['ID_Orbis_DNB'].nunique():,} groups "
      f"| mean origins/group  {len(idc)/idc['ID_Orbis_DNB'].nunique():.2f}")

# parent-level totals
par = (pc.groupby("name_parent_adj", as_index=False)
         .agg(export_value=("val", "sum"),
              n_origins=("country_orig", "nunique"),
              iso3_parent=("iso3_parent", "first")))
# merge network size
net = pd.read_parquet(NET, columns=["name_parent_adj", "total_affiliates",
                                    "total_affiliates_lac", "n_countries",
                                    "n_countries_lac", "n_sectors", "merge_DNB"])
par = par.merge(net, on="name_parent_adj", how="left")
par["has_network"] = par["total_affiliates"].notna()
par.to_parquet(P_CACHE, index=False)

matched = par["has_network"].mean()
print(f"  parents (exporting, foreign): {len(par):,} | matched to network table: {matched:.1%}")
print(f"  total foreign-MNE export value: ${par['export_value'].sum()/1e9:.1f}bn")
print(f"\n  saved {PC_CACHE.name} and {P_CACHE.name}  ({time.time()-t0:.0f}s)")
