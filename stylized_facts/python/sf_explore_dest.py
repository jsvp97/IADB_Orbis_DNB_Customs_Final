"""
sf_explore_dest.py
==================

Exploration (pre-SF2): MNE_total value share across destination country cuts.

Cuts:
  1. by destination income group (WB classification)
  2. by destination region (LAC / NAM / EU / Asia / Africa / Oceania / RoW)
  3. intra-regional (LAC dest) vs extra-regional
  4. contiguous vs non-contiguous
  5. by bilateral distance quintile
  6. FTA / WTO member vs not
  7. scatter MNE_total share vs ln GDPpc_d (one point per destination,
     marker size = total LAC9 export value)
  8. top-20 destinations by total LAC9 export value

Builds (one-time) and reuses:  1_Input/Intermediate/ody_value_cache.parquet
Outputs (local only, no Overleaf mirror yet):
  2_Output/Graphs/Exploration_Dest/expl_dest_<cut>.{pdf,png,eps}
  2_Output/Tables/Exploration_Dest/expl_dest_<cut>.tex
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyreadstat

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    BASE_FILE, GRAVITY, COUNTRY, INT, GRAPHS, TABLES, EXCLUDED_ORIGINS,
    C_MNE_TOT, ensure_dir, save_figure, parquet_chunks,
)


# ---------------------------------------------------------------------
# Output paths
# ---------------------------------------------------------------------
G_EXPL = GRAPHS / "Exploration_Dest"
T_EXPL = TABLES / "Exploration_Dest"
for d in (G_EXPL, T_EXPL):
    ensure_dir(d)

CACHE = INT / "ody_value_cache.parquet"


# ---------------------------------------------------------------------
# Region classification (used inside cache build)
# ---------------------------------------------------------------------
NA_CODES = {"USA", "CAN"}
OC_CODES = {"AUS", "NZL"}
LAC_CODES = {"ARG","BHS","BRB","BLZ","BOL","BRA","CHL","COL","CRI","DOM",
             "ECU","SLV","GTM","GUY","HTI","HND","JAM","MEX","NIC","PAN",
             "PRY","PER","SUR","TTO","URY","VEN"}
EU_CODES = {"AUT","BEL","BGR","CYP","CZE","DNK","EST","FIN","FRA","DEU",
            "GRC","HUN","IRL","ITA","LVA","LTU","LUX","MLT","NLD","POL",
            "PRT","ROU","SVK","SVN","ESP","SWE","GBR","CHE","NOR","ISL",
            "UKR","RUS","TUR"}
AS_CODES = {"CHN","HKG","IND","IDN","JPN","MYS","PHL","KOR","SGP","TWN",
            "THA","VNM","PAK","BGD","KAZ","ARE","SAU","ISR","LKA","MMR"}
AF_CODES = {"DZA","AGO","BEN","BWA","BFA","BDI","CMR","CPV","CAF","TCD",
            "COM","COD","COG","CIV","DJI","EGY","GNQ","ERI","ETH","GAB",
            "GMB","GHA","GIN","GNB","KEN","LSO","LBR","LBY","MDG","MWI",
            "MLI","MRT","MUS","MAR","MOZ","NAM","NER","NGA","RWA","STP",
            "SEN","SYC","SLE","SOM","ZAF","SSD","SDN","SWZ","TZA","TGO",
            "TUN","UGA","ZMB","ZWE"}


def classify_region(code: str) -> str:
    if code in LAC_CODES: return "Latin America"
    if code in NA_CODES:  return "North America"
    if code in OC_CODES:  return "Oceania"
    if code in EU_CODES:  return "Europe"
    if code in AS_CODES:  return "Asia"
    if code in AF_CODES:  return "Africa"
    return "Rest of World"


# ---------------------------------------------------------------------
# Cache build (chunked) from the 19 GB raw file
# ---------------------------------------------------------------------
def build_cache() -> pd.DataFrame:
    raw_path = BASE_FILE
    print(f">>> Building ODY cache from {raw_path}")
    print("    Loading base selectively via parquet (chunked)...")

    t0 = time.time()
    cols = ["country_orig", "country_dest", "year", "value_fob",
            "_merge_DNB_Orbis", "iso3_parent"]

    # Chunked read + per-chunk aggregation to keep RAM bounded.
    accum: list[pd.DataFrame] = []
    chunk_size = 1_000_000
    total_rows = 0
    for i, chunk in enumerate(parquet_chunks(raw_path, cols, chunk_size), start=1):
        # Sign correction on value_fob
        chunk["value_fob"] = chunk["value_fob"].abs()
        # MNE flags (new convention: ext = total - dom; deferred)
        mne_total = (chunk["_merge_DNB_Orbis"] == 3)
        mne_dom   = mne_total & (chunk["iso3_parent"] == chunk["country_orig"])
        chunk["val_total"] = chunk["value_fob"] * mne_total
        chunk["val_dom"]   = chunk["value_fob"] * mne_dom
        chunk_agg = (chunk.groupby(["country_orig", "country_dest", "year"], as_index=False)
                          .agg(total_value=("value_fob", "sum"),
                               val_total=("val_total", "sum"),
                               val_dom=("val_dom", "sum")))
        accum.append(chunk_agg)
        total_rows += len(chunk)
        print(f"    chunk {i:>3} processed ({total_rows:>12,} rows so far, "
              f"{time.time()-t0:>5.0f}s)")

    df = pd.concat(accum, ignore_index=True)
    df = (df.groupby(["country_orig", "country_dest", "year"], as_index=False)
            .sum(numeric_only=True))
    df["val_ext"] = df["val_total"] - df["val_dom"]
    print(f"    final ODY rows: {len(df):,} ({time.time()-t0:.0f}s total raw scan)")

    # ----- Merge CEPII gravity (bilateral) -----
    print("    merging CEPII gravity...")
    grav, _ = pyreadstat.read_dta(str(GRAVITY / "Gravity_V202211.dta"),
                                  usecols=["iso3_o", "iso3_d", "year",
                                           "dist", "contig", "comlang_off",
                                           "fta_wto",
                                           "pop_d", "gdp_d", "gdpcap_d",
                                           "pop_o", "gdp_o", "gdpcap_o"])
    grav = grav.rename(columns={"iso3_o": "country_orig", "iso3_d": "country_dest"})
    grav = grav.drop_duplicates(["country_orig", "country_dest", "year"])
    df = df.merge(grav, on=["country_orig", "country_dest", "year"], how="left")

    for c in ("dist", "gdpcap_d", "pop_d", "gdp_d", "gdpcap_o", "pop_o", "gdp_o"):
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("float64")
    with np.errstate(invalid="ignore", divide="ignore"):
        df["ln_dist"]     = np.log(df["dist"])
        df["ln_gdpcap_d"] = np.log(df["gdpcap_d"])
        df["ln_pop_d"]    = np.log(df["pop_d"])
        df["ln_gdp_d"]    = np.log(df["gdp_d"])
        df["ln_gdpcap_o"] = np.log(df["gdpcap_o"])

    # ----- Merge WB income group (destination) -----
    print("    merging WB income groups...")
    wdi, _ = pyreadstat.read_dta(str(COUNTRY / "WB_Income_group.dta"))
    wdi = wdi.rename(columns={"iso3": "country_dest",
                              "income_group": "income_group_dest_str"})
    df = df.merge(wdi[["country_dest", "income_group_dest_str"]],
                  on="country_dest", how="left")
    income_map = {"Low income": 1, "Lower middle income": 2,
                  "Upper middle income": 3, "High income": 4}
    df["income_group_dest"] = df["income_group_dest_str"].map(income_map)

    # ----- Region + LAC indicator -----
    df["LAC_dest"]       = df["country_dest"].isin(LAC_CODES).astype(int)
    df["intra_regional"] = df["LAC_dest"]
    df["dest_region"]    = df["country_dest"].map(classify_region)

    # ----- Distance categories -----
    df["dist_above_med"] = (df["dist"] > df["dist"].median()).astype("Int8")
    df["dist_quintile"]  = pd.qcut(df["dist"], 5, labels=False, duplicates="drop") + 1

    df.to_parquet(CACHE, index=False)
    print(f">>> Cache saved to {CACHE} ({len(df):,} rows)")
    return df


# ---------------------------------------------------------------------
# Load (or build) the cache
# ---------------------------------------------------------------------
if CACHE.exists():
    print(f">>> Loading cached ODY data from {CACHE}")
    df = pd.read_parquet(CACHE)
    print(f"    rows: {len(df):,}")
else:
    df = build_cache()


# Apply project-wide exclusion
df = df[~df["country_orig"].isin(EXCLUDED_ORIGINS)].copy()
df = df[(df["total_value"] > 0) & df["country_dest"].notna()].copy()

print(f">>> Post-filter rows: {len(df):,}")
print(f"    distinct destinations: {df['country_dest'].nunique():,}")
print(f"    origins kept: {sorted(df['country_orig'].unique())}")


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

INCOME_LABEL = {1: "Low", 2: "Lower-middle", 3: "Upper-middle", 4: "High"}


def _hbar_share(d: pd.DataFrame, ycol: str, ylabels: dict | None,
                fname: str, xtitle: str, xmax: float = 0.8,
                sort_ascending: bool = True) -> None:
    d = d.copy()
    if ylabels:
        d["_lbl"] = d[ycol].map(ylabels)
    else:
        d["_lbl"] = d[ycol].astype(str)
    d = d.sort_values("share_total", ascending=sort_ascending)
    fig, ax = plt.subplots(figsize=(8, max(3, 0.45 * len(d) + 1.5)))
    ax.barh(d["_lbl"], d["share_total"], color=C_MNE_TOT, edgecolor=C_MNE_TOT)
    for y, v in zip(d["_lbl"], d["share_total"]):
        ax.text(v + 0.005, y, f"{v:.2f}", va="center", fontsize=9)
    ax.set_xlim(0, xmax)
    ax.set_xticks(np.arange(0, xmax + 1e-9, 0.1))
    ax.set_xlabel(xtitle)
    save_figure(fig, fname, G_EXPL)


def _write_cut_table(d: pd.DataFrame, label: str, ylabels: dict | None,
                     fname: str, category_col: str) -> None:
    out = []
    out.append(r"\begin{tabular}{lcr}")
    out.append(r"\toprule")
    out.append(rf"{label} & MNE$_{{\text{{total}}}}$ share & Total value (\$bn) \\")
    out.append(r"\midrule")
    for _, r in d.iterrows():
        cat = ylabels.get(r[category_col], str(r[category_col])) if ylabels else str(r[category_col])
        out.append(f"{cat} & {r['share_total']:.3f} & {r['total_value']/1e9:7.2f} \\\\")
    out.append(r"\bottomrule")
    out.append(r"\end{tabular}")
    (T_EXPL / f"{fname}.tex").write_text("\n".join(out) + "\n", encoding="utf-8")


def cut(category_col: str, fname: str, xtitle_cut_name: str,
        ylabels: dict | None = None, *,
        order_by_share: bool = True, xmax: float = 0.8,
        keep_filter=None) -> pd.DataFrame:
    d = df.copy()
    if keep_filter is not None:
        d = d[keep_filter(d)]
    d = d.dropna(subset=[category_col])
    g = (d.groupby(category_col, as_index=False)
           .agg(total_value=("total_value", "sum"),
                val_total=("val_total", "sum")))
    g["share_total"] = g["val_total"] / g["total_value"]
    g = g.sort_values("share_total" if order_by_share else category_col,
                      ascending=order_by_share if not order_by_share else True)
    _hbar_share(g, category_col, ylabels, fname,
                xtitle=f"MNE-total share in export value", xmax=xmax,
                sort_ascending=True)
    _write_cut_table(g.sort_values(category_col), xtitle_cut_name, ylabels, fname, category_col)
    print(f"  {fname:40s}  groups={len(g)}")
    return g


# ---------------------------------------------------------------------
# Cuts
# ---------------------------------------------------------------------
print("\n>>> Generating destination cuts...")

# 1. by destination income group
cut("income_group_dest", "expl_dest_income_group", "Destination income group",
    ylabels=INCOME_LABEL, xmax=0.8)

# 2. by destination region
cut("dest_region", "expl_dest_region", "Destination region", xmax=0.8)

# 3. intra-regional vs extra-regional
cut("intra_regional", "expl_dest_intra_regional", "Intra/Extra-regional",
    ylabels={0: "Extra-regional", 1: "Intra-regional (LAC)"}, xmax=0.8)

# 4. contiguous vs non-contiguous
cut("contig", "expl_dest_contig", "Border-sharing",
    ylabels={0: "Non-contiguous", 1: "Contiguous"}, xmax=0.8)

# 5. by bilateral distance quintile
cut("dist_quintile", "expl_dest_dist_quintile", "Distance quintile (1=closest)",
    ylabels={1: "Q1 (closest)", 2: "Q2", 3: "Q3", 4: "Q4", 5: "Q5 (farthest)"},
    xmax=0.8)

# 6. FTA / WTO
cut("fta_wto", "expl_dest_fta", "FTA / WTO link",
    ylabels={0: "No FTA / WTO link", 1: "FTA / WTO member"}, xmax=0.8)


# ---------------------------------------------------------------------
# 7. Scatter MNE_total share vs ln GDPpc_d (one point per destination)
# ---------------------------------------------------------------------
print("\n>>> Building destination-level scatter...")

dest = (df.groupby("country_dest", as_index=False)
          .agg(total_value=("total_value", "sum"),
               val_total=("val_total", "sum"),
               ln_gdpcap_d=("ln_gdpcap_d", "mean")))
dest = dest[(dest["ln_gdpcap_d"].notna()) & (dest["total_value"] > 0)].copy()
dest["share_total"] = dest["val_total"] / dest["total_value"]
dest["weight"] = dest["total_value"] / dest["total_value"].sum()

fig, ax = plt.subplots(figsize=(8, 5.5))
sizes = 12 + dest["weight"] * 4000
ax.scatter(dest["ln_gdpcap_d"], dest["share_total"], s=sizes,
           color=C_MNE_TOT, alpha=0.45, edgecolor=C_MNE_TOT)
# Linear fit
import statsmodels.api as sm
Xmat = sm.add_constant(dest["ln_gdpcap_d"].astype(float).to_numpy())
m = sm.OLS(dest["share_total"].astype(float).to_numpy(), Xmat).fit()
xgrid = np.linspace(dest["ln_gdpcap_d"].min(), dest["ln_gdpcap_d"].max(), 100)
Xg = sm.add_constant(xgrid)
ax.plot(xgrid, m.predict(Xg), color="black", linewidth=1.0)

# Label top-15 destinations by trade value
top15 = dest.nlargest(15, "total_value")
for _, r in top15.iterrows():
    ax.annotate(r["country_dest"], (r["ln_gdpcap_d"], r["share_total"]),
                xytext=(5, 0), textcoords="offset points",
                fontsize=8, color="black")

ax.set_xlabel("Log GDP per capita (destination)")
ax.set_ylabel("MNE-total share in export value")
ax.set_ylim(-0.02, 1.05)
ax.text(0.02, 0.97,
        "Marker area ∝ LAC9 export value to that destination",
        transform=ax.transAxes, fontsize=8, va="top", color="gray")
save_figure(fig, "expl_dest_scatter_gdppc", G_EXPL)
print(f"  expl_dest_scatter_gdppc                  n_dests={len(dest)}")


# ---------------------------------------------------------------------
# 8. Top-20 destinations by total LAC9 export value
# ---------------------------------------------------------------------
print("\n>>> Top 20 destinations...")
top20 = (df.groupby("country_dest", as_index=False)
           .agg(total_value=("total_value", "sum"),
                val_total=("val_total", "sum")))
top20["share_total"] = top20["val_total"] / top20["total_value"]
top20 = top20.nlargest(20, "total_value").reset_index(drop=True)

fig, ax = plt.subplots(figsize=(8, 7))
sub = top20.sort_values("total_value", ascending=True)  # bottom-up so largest at top
ax.barh(sub["country_dest"], sub["share_total"], color=C_MNE_TOT, edgecolor=C_MNE_TOT)
for y, v in zip(sub["country_dest"], sub["share_total"]):
    ax.text(v + 0.005, y, f"{v:.2f}", va="center", fontsize=8)
ax.set_xlim(0, 1.0)
ax.set_xlabel("MNE-total share in export value")
ax.set_title("Top 20 destinations by total LAC9 export value (descending)", fontsize=11)
save_figure(fig, "expl_dest_top20", G_EXPL)

# Write top20 table
out = [r"\begin{tabular}{lcr}", r"\toprule",
       r"Destination & MNE$_{\text{total}}$ share & Total value (\$bn) \\",
       r"\midrule"]
for _, r in top20.iterrows():
    out.append(f"{r['country_dest']} & {r['share_total']:.3f} & {r['total_value']/1e9:7.2f} \\\\")
out += [r"\bottomrule", r"\end{tabular}"]
(T_EXPL / "expl_dest_top20.tex").write_text("\n".join(out) + "\n", encoding="utf-8")


print(f"\n>>> All outputs written:")
print(f"    Graphs -> {G_EXPL}")
print(f"    Tables -> {T_EXPL}")
