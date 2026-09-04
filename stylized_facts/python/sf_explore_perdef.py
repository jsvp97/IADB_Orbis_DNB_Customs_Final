"""
sf_explore_perdef.py
====================

For each MNE definition (total / ext / dom), reproduce the same set of
exploratory cuts independently — i.e. each def gets its own ranking,
its own scatter slope, its own decile pattern.

Goal: see whether the destination-side and product-side patterns we
already characterized for MNE_total look different when we instead
treat MNE_ext or MNE_dom as the share of interest.

Inputs (cached):
    opy_value_cache.parquet  (origin x hs6 x year)
    ody_value_cache.parquet  (origin x destination x year)

Outputs:
    2_Output/Graphs/Exploration_Dest_PerDef/     destination cuts per def
    2_Output/Graphs/Exploration_Products_PerDef/ product cuts per def
    + matching tables
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    INT, GRAPHS, TABLES, EXCLUDED_ORIGINS,
    C_MNE_TOT, C_MNE_EXT, C_MNE_DOM,
    ensure_dir, save_figure,
)

G_DEST = GRAPHS / "Exploration_Dest_PerDef"
T_DEST = TABLES / "Exploration_Dest_PerDef"
G_PROD = GRAPHS / "Exploration_Products_PerDef"
T_PROD = TABLES / "Exploration_Products_PerDef"
for d in (G_DEST, T_DEST, G_PROD, T_PROD):
    ensure_dir(d)

DEFS = ["total", "ext", "dom"]
DEF_COLOR = {"total": C_MNE_TOT, "ext": C_MNE_EXT, "dom": C_MNE_DOM}
DEF_LABEL = {"total": "MNE-total", "ext": "MNE-ext (foreign)", "dom": "MNE-dom"}


# ---------------------------------------------------------------------
# Load + filter
# ---------------------------------------------------------------------
opy = pd.read_parquet(INT / "opy_value_cache.parquet")
opy = opy[~opy["country_orig"].isin(EXCLUDED_ORIGINS)]
opy = opy[(opy["total_value"] > 0) & opy["hs07_6d"].notna()].copy()
opy["val_ext"] = opy["val_total"] - opy["val_dom"]

ody = pd.read_parquet(INT / "ody_value_cache.parquet")
ody = ody[~ody["country_orig"].isin(EXCLUDED_ORIGINS)]
ody = ody[(ody["total_value"] > 0) & ody["country_dest"].notna()].copy()
ody["val_ext"] = ody["val_total"] - ody["val_dom"]


# ---------------------------------------------------------------------
# Aggregation helper
# ---------------------------------------------------------------------

def aggregate(d: pd.DataFrame, by) -> pd.DataFrame:
    by = [by] if isinstance(by, str) else by
    d = d.dropna(subset=by)
    g = (d.groupby(by, as_index=False)
           .agg(total_value=("total_value", "sum"),
                val_total=("val_total", "sum"),
                val_dom=("val_dom", "sum")))
    g["val_ext"]   = g["val_total"] - g["val_dom"]
    for k in DEFS:
        g[f"sh_{k}"] = g[f"val_{k}"] / g["total_value"]
    return g


# ---------------------------------------------------------------------
# Figure / table writers
# ---------------------------------------------------------------------

def hbar_perdef(g: pd.DataFrame, label_col: str, def_: str, fname: str,
                outdir: Path, *, title: str | None = None,
                xmax: float | None = None, figsize=None) -> None:
    """Horizontal bar chart for a single MNE def, ranked by its own share."""
    g = g.sort_values(f"sh_{def_}", ascending=True).reset_index(drop=True)
    n = len(g)
    if figsize is None:
        figsize = (8.5, max(3.5, 0.45 * n + 1.5))
    fig, ax = plt.subplots(figsize=figsize)
    col = DEF_COLOR[def_]
    ax.barh(g[label_col].astype(str), g[f"sh_{def_}"], color=col, edgecolor=col)
    for y, v in zip(g[label_col].astype(str), g[f"sh_{def_}"]):
        ax.text(v + max(0.003, xmax * 0.005 if xmax else 0.005), y, f"{v:.2f}",
                va="center", fontsize=8)
    if xmax is None:
        xmax = max(0.30, g[f"sh_{def_}"].max() * 1.15)
    ax.set_xlim(0, xmax)
    step = 0.1 if xmax > 0.4 else 0.05
    ax.set_xticks(np.arange(0, xmax + 1e-9, step))
    ax.set_xlabel(f"{DEF_LABEL[def_]} share in export value")
    if title:
        ax.set_title(title, fontsize=11)
    save_figure(fig, fname, outdir)


def vbar_decile_perdef(g: pd.DataFrame, x_col: str, def_: str, fname: str,
                        outdir: Path, *, char_label: str = "") -> None:
    """Vertical bar chart for one def, sorted by x_col (e.g. decile)."""
    g = g.sort_values(x_col)
    fig, ax = plt.subplots(figsize=(8, 4))
    col = DEF_COLOR[def_]
    ax.bar(g[x_col].astype(int), g[f"sh_{def_}"], color=col, edgecolor=col, width=0.7)
    for x, v in zip(g[x_col], g[f"sh_{def_}"]):
        ax.text(x, v + 0.01, f"{v:.2f}", ha="center", fontsize=8)
    ax.set_xlabel(f"{char_label} decile (1 = lowest, 10 = highest)")
    ax.set_ylabel(f"{DEF_LABEL[def_]} share in export value")
    ax.set_xticks(range(1, 11))
    ymax = max(0.9, g[f"sh_{def_}"].max() * 1.15)
    ax.set_ylim(0, ymax)
    save_figure(fig, fname, outdir)


def scatter_perdef(d: pd.DataFrame, group_col: str, x_col: str, def_: str,
                    fname: str, outdir: Path, *, xlabel: str, ylabel: str,
                    annotate_top: int = 15) -> None:
    """Scatter share-of-def vs x_col (continuous), one point per group."""
    g = (d.dropna(subset=[x_col])
           .groupby(group_col, as_index=False)
           .agg(total_value=("total_value", "sum"),
                val_total=("val_total", "sum"),
                val_dom=("val_dom", "sum"),
                x=(x_col, "mean")))
    g["val_ext"] = g["val_total"] - g["val_dom"]
    g["sh"] = g[f"val_{def_}"] / g["total_value"]
    g = g[g["total_value"] > 0]

    fig, ax = plt.subplots(figsize=(8, 5))
    col = DEF_COLOR[def_]
    sizes = 12 + (g["total_value"] / g["total_value"].max()) * 800
    ax.scatter(g["x"], g["sh"], s=sizes, color=col, alpha=0.45, edgecolor=col)

    import statsmodels.api as sm
    Xmat = sm.add_constant(g["x"].astype(float).to_numpy())
    m = sm.OLS(g["sh"].astype(float).to_numpy(), Xmat).fit()
    xg = np.linspace(g["x"].min(), g["x"].max(), 100)
    ax.plot(xg, m.predict(sm.add_constant(xg)), color="black", linewidth=1.0)

    # Label top-N by weight
    top = g.nlargest(annotate_top, "total_value")
    for _, r in top.iterrows():
        ax.annotate(r[group_col], (r["x"], r["sh"]),
                    xytext=(4, 0), textcoords="offset points",
                    fontsize=8, color="black")

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_ylim(-0.02, max(0.9, g["sh"].max() * 1.1))
    save_figure(fig, fname, outdir)


def write_table_one_def(g: pd.DataFrame, label_col: str, def_: str, label_hdr: str,
                         fname: str, outdir: Path) -> None:
    g = g.sort_values(f"sh_{def_}", ascending=False).reset_index(drop=True)
    lines = [r"\begin{tabular}{lcr}", r"\toprule",
             rf"{label_hdr} & {DEF_LABEL[def_]} share & Value (\$bn) \\",
             r"\midrule"]
    for _, r in g.iterrows():
        lab = str(r[label_col]).replace("&", r"\&")
        lines.append(f"{lab} & {r[f'sh_{def_}']:.3f} & {r['total_value']/1e9:7.2f} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (outdir / f"{fname}.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------
# DESTINATION cuts per def
# ---------------------------------------------------------------------
print(">>> Destination cuts per def...")

INCOME_LBL = {1: "Low", 2: "Lower-middle", 3: "Upper-middle", 4: "High"}
DIST_LBL   = {1: "Q1 (closest)", 2: "Q2", 3: "Q3", 4: "Q4", 5: "Q5 (farthest)"}

# Income group
g = aggregate(ody, "income_group_dest")
g["lbl"] = g["income_group_dest"].map(INCOME_LBL)
for def_ in DEFS:
    hbar_perdef(g, "lbl", def_, f"dest_income_group_{def_}", G_DEST,
                title=f"{DEF_LABEL[def_]} share by destination income group", xmax=0.8)
    write_table_one_def(g, "lbl", def_, "Income group",
                        f"dest_income_group_{def_}", T_DEST)

# Region
g = aggregate(ody, "dest_region")
for def_ in DEFS:
    hbar_perdef(g, "dest_region", def_, f"dest_region_{def_}", G_DEST,
                title=f"{DEF_LABEL[def_]} share by destination region", xmax=0.8)
    write_table_one_def(g, "dest_region", def_, "Destination region",
                        f"dest_region_{def_}", T_DEST)

# Distance quintile (vertical bars to preserve ordering)
g = aggregate(ody, "dist_quintile")
for def_ in DEFS:
    vbar_decile_perdef(g, "dist_quintile", def_,
                        f"dest_dist_quintile_{def_}", G_DEST,
                        char_label="Distance")
    write_table_one_def(g.assign(lbl=g["dist_quintile"].map(DIST_LBL)),
                        "lbl", def_, "Distance quintile",
                        f"dest_dist_quintile_{def_}", T_DEST)

# Intra/extra
g = aggregate(ody, "intra_regional")
g["lbl"] = g["intra_regional"].map({0: "Extra-regional", 1: "Intra-regional"})
for def_ in DEFS:
    hbar_perdef(g, "lbl", def_, f"dest_intra_{def_}", G_DEST,
                title=f"{DEF_LABEL[def_]} share: intra/extra-regional", xmax=0.8,
                figsize=(7, 3))
    write_table_one_def(g, "lbl", def_, "Intra/Extra", f"dest_intra_{def_}", T_DEST)

# Contig
g = aggregate(ody, "contig")
g["lbl"] = g["contig"].map({0: "Non-contiguous", 1: "Contiguous"})
for def_ in DEFS:
    hbar_perdef(g, "lbl", def_, f"dest_contig_{def_}", G_DEST,
                title=f"{DEF_LABEL[def_]} share: border-sharing", xmax=0.8,
                figsize=(7, 3))
    write_table_one_def(g, "lbl", def_, "Border", f"dest_contig_{def_}", T_DEST)

# FTA
g = aggregate(ody, "fta_wto")
g["lbl"] = g["fta_wto"].map({0: "No FTA / WTO", 1: "FTA / WTO"})
for def_ in DEFS:
    hbar_perdef(g, "lbl", def_, f"dest_fta_{def_}", G_DEST,
                title=f"{DEF_LABEL[def_]} share: FTA / WTO", xmax=0.8,
                figsize=(7, 3))
    write_table_one_def(g, "lbl", def_, "FTA", f"dest_fta_{def_}", T_DEST)

# Top-20 destinations per def (ranked by trade volume) + scatter vs ln GDPpc
print(">>> Top-20 destinations per def...")
top_d = (ody.groupby("country_dest", as_index=False)
            .agg(total_value=("total_value", "sum"),
                 val_total=("val_total", "sum"),
                 val_dom=("val_dom", "sum"),
                 ln_gdpcap_d=("ln_gdpcap_d", "mean")))
top_d["val_ext"] = top_d["val_total"] - top_d["val_dom"]
for k in DEFS:
    top_d[f"sh_{k}"] = top_d[f"val_{k}"] / top_d["total_value"]
top20 = top_d.nlargest(20, "total_value")
for def_ in DEFS:
    hbar_perdef(top20, "country_dest", def_, f"dest_top20_{def_}", G_DEST,
                title=f"{DEF_LABEL[def_]} share — top 20 destinations by trade",
                xmax=1.0, figsize=(8, 8))
    write_table_one_def(top20, "country_dest", def_, "Destination",
                        f"dest_top20_{def_}", T_DEST)

# Scatter vs ln GDPpc_d per def
for def_ in DEFS:
    scatter_perdef(ody, "country_dest", "ln_gdpcap_d", def_,
                   f"dest_scatter_gdppc_{def_}", G_DEST,
                   xlabel="Log GDP per capita (destination)",
                   ylabel=f"{DEF_LABEL[def_]} share in export value",
                   annotate_top=15)


# ---------------------------------------------------------------------
# PRODUCT cuts per def
# ---------------------------------------------------------------------
print("\n>>> Product cuts per def...")

# HS section
g = aggregate(opy, "hs_section")
for def_ in DEFS:
    hbar_perdef(g, "hs_section", def_, f"prod_hs_section_{def_}", G_PROD,
                title=f"{DEF_LABEL[def_]} share by HS section",
                xmax=0.95, figsize=(9, 9))
    write_table_one_def(g, "hs_section", def_, "HS section",
                        f"prod_hs_section_{def_}", T_PROD)

# Lall 2000
g = aggregate(opy, "lall2000_category")
for def_ in DEFS:
    hbar_perdef(g, "lall2000_category", def_, f"prod_lall2000_{def_}", G_PROD,
                title=f"{DEF_LABEL[def_]} share by Lall technology category",
                xmax=0.95, figsize=(10, 6))
    write_table_one_def(g, "lall2000_category", def_, "Lall 2000",
                        f"prod_lall2000_{def_}", T_PROD)

# IPC1
g = aggregate(opy, "ipc1")
for def_ in DEFS:
    hbar_perdef(g, "ipc1", def_, f"prod_ipc1_{def_}", G_PROD,
                title=f"{DEF_LABEL[def_]} share by IPC patent section",
                xmax=0.85, figsize=(10, 4))
    write_table_one_def(g, "ipc1", def_, "IPC section",
                        f"prod_ipc1_{def_}", T_PROD)

# Continuous characteristic deciles (4 chars x 3 defs = 12)
def decile_one_def(d: pd.DataFrame, char_col: str, def_: str, char_label: str,
                   fname: str) -> None:
    s = (d.dropna(subset=[char_col])
           .groupby("hs07_6d", as_index=False)
           .agg(total_value=("total_value", "sum"),
                val_total=("val_total", "sum"),
                val_dom=("val_dom", "sum"),
                ch=(char_col, "first")))
    s["decile"] = pd.qcut(s["ch"], 10, labels=False, duplicates="drop") + 1
    g = aggregate(s, "decile")
    vbar_decile_perdef(g, "decile", def_, fname, G_PROD, char_label=char_label)
    write_table_one_def(g.assign(lbl="D"+g["decile"].astype(int).astype(str)),
                        "lbl", def_, "Decile", fname, T_PROD)


for char, lbl in [("upstreamness",   "Upstreamness"),
                   ("sigma",          "σ (Broda-Weinstein)"),
                   ("complexity",     "Complexity (PCI)"),
                   ("quality_ladder", "Quality ladder")]:
    for def_ in DEFS:
        decile_one_def(opy, char, def_, lbl, f"prod_{char}_decile_{def_}")


print(f"\n>>> Outputs:")
print(f"    Destination: {G_DEST}")
print(f"    Products:    {G_PROD}")
print(f"    Tables:      {T_DEST}  and  {T_PROD}")
