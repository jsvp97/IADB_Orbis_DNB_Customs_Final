"""
Build a parent-level MNE network-size table from the affiliate-level
Orbis+DNB matched base (Merge_DNB_Orbis_PostIA_v2.parquet), replicating the
logic of Velasquez's "Dofile match Orbis_DNB parents.do" but with the proper
Orbis UNION DNB affiliate de-duplication (not the coalesce in v4 lines 660-695).

Output: 1_Input/Intermediate/network_size_by_parent.parquet
  one row per parent (name_parent_adj), with:
    total_affiliates      distinct affiliates worldwide (Orbis ∪ DNB)
    total_affiliates_lac  distinct affiliates in LAC
    n_countries(_lac)     distinct subsidiary countries
    n_sectors(_lac)       distinct NAICS-4 sectors (excl. 9999)
    iso3_parent, ent_name_par, globalultimatebusinessname, merge_DNB (first)

Coverage note: this file contains parents that have >=1 matched affiliate.
Parents with zero matched affiliates live only in Merge_DNB_Orbis_par_PostIA_v2
(not on disk); the dofile assigns them total=1. Not reconstructable here.
"""
from __future__ import annotations
import sys, time
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import MERGE_AFF_FILE, INT, ensure_dir  # noqa: E402

OUT = INT / "network_size_by_parent.parquet"

# LAC iso3 set (from the dofile's $lac global)
LAC = {"ARG","BOL","BRA","CHL","COL","CRI","CUB","DOM","ECU","SLV","GTM","HTI",
       "HND","JAM","MEX","NIC","PAN","PRY","PER","TTO","URY","VEN","BLZ","GUY",
       "SUR","BRB","TCA","CYM","VGB","BES","CUW","SXM","LCA","VCT","GRD","ATG",
       "DMA","KNA"}

def clean(s):
    return s.astype("string").str.strip().replace({"": pd.NA, ".": pd.NA})

t0 = time.time()
cols = ["ent_name_aff","companyname","ent_name_par","globalultimatebusinessname",
        "iso3_subsidiary","iso3_parent","naics_aff_6","naics_4_c","_merge_DNB"]
print(">>> loading affiliate-level Merge file ...")
df = pd.read_parquet(MERGE_AFF_FILE, columns=cols)
print(f"   rows={len(df):,}  ({time.time()-t0:.0f}s)")

# --- affiliate identity: Orbis name, else DNB companyname ---
na, cn = clean(df["ent_name_aff"]), clean(df["companyname"])
df["name_affiliate"] = na.fillna(cn)
# --- parent identity: Orbis ent_name_par, else DNB global ultimate ---
pe, gu = clean(df["ent_name_par"]), clean(df["globalultimatebusinessname"])
df["name_parent_adj"] = pe.fillna(gu).str.upper().str.strip()
# --- NAICS-4 sector: first 4 of naics_aff_6, else naics_4_c ---
n6 = clean(df["naics_aff_6"]).str.slice(0, 4)
df["naics4"] = n6.fillna(clean(df["naics_4_c"]))
df["iso3_sub"]  = clean(df["iso3_subsidiary"])
df["iso3_par"]  = clean(df["iso3_parent"])
df["lac"] = df["iso3_sub"].isin(LAC)

# keep rows with an identifiable parent + affiliate
df = df[df["name_parent_adj"].notna() & df["name_affiliate"].notna()].copy()
# distinct affiliates: Orbis ∪ DNB de-dup by (affiliate name, subsidiary country)
before = len(df)
df = df.drop_duplicates(["name_affiliate", "iso3_sub"])
print(f"   distinct affiliate-country rows: {len(df):,} (from {before:,})  ({time.time()-t0:.0f}s)")

# --- collapse to parent ---
g = df.groupby("name_parent_adj", sort=False)
out = pd.DataFrame({
    "total_affiliates":     g.size(),
    "total_affiliates_lac": g["lac"].sum(),
    "n_countries":          g["iso3_sub"].nunique(),
    "iso3_parent":          g["iso3_par"].first(),
    "ent_name_par":         g["ent_name_par"].first(),
    "globalultimatebusinessname": g["globalultimatebusinessname"].first(),
    "merge_DNB":            g["_merge_DNB"].first(),
})
# LAC-country count / sector counts via subsets (conditional nunique)
lac = df[df["lac"]]
out["n_countries_lac"] = lac.groupby("name_parent_adj")["iso3_sub"].nunique()
sec = df[df["naics4"].notna() & (df["naics4"] != "9999")]
out["n_sectors"] = sec.groupby("name_parent_adj")["naics4"].nunique()
sec_lac = sec[sec["lac"]]
out["n_sectors_lac"] = sec_lac.groupby("name_parent_adj")["naics4"].nunique()
for c in ["total_affiliates_lac","n_countries","n_countries_lac","n_sectors","n_sectors_lac"]:
    out[c] = out[c].fillna(0).astype("int64")
out = out.reset_index()

ensure_dir(OUT.parent)
out.to_parquet(OUT, index=False)
print(f"\n>>> saved {OUT}  ({len(out):,} parents, {time.time()-t0:.0f}s)")

# --- report: the ">100 affiliates" distribution ---
ta = out["total_affiliates"]
print("\ntotal_affiliates distribution across parents:")
print(ta.describe(percentiles=[.5,.9,.99]).to_string())
for thr in [1,5,10,50,100,500,1000]:
    n = int((ta > thr).sum())
    print(f"   parents with >{thr:>4} affiliates: {n:>7,}  ({n/len(out):.1%})")
print("\ntop 10 parents by network size:")
print(out.nlargest(10,"total_affiliates")[
    ["name_parent_adj","iso3_parent","total_affiliates","n_countries","n_sectors"]].to_string(index=False))
