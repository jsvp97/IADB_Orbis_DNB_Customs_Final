"""
sf_explore_by_def.py
====================

Exploration: side-by-side comparison of MNE_total, MNE_ext, and MNE_dom
value shares across product and destination cuts.

By construction (post-2026-05-23 convention):
    share_ext + share_dom = share_total

So the three lines/bars in each chart are mutually consistent and
let us see WHICH MNE component drives any given pattern.

Inputs (built by earlier scripts):
    opy_value_cache.parquet  (origin x hs6 x year)
    ody_value_cache.parquet  (origin x destination x year)

Outputs:
    2_Output/Graphs/Exploration_ByDef/*.{pdf,png,eps}
    2_Output/Tables/Exploration_ByDef/*.tex
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

G_OUT = GRAPHS / "Exploration_ByDef"
T_OUT = TABLES / "Exploration_ByDef"
for d in (G_OUT, T_OUT):
    ensure_dir(d)


# ---------------------------------------------------------------------
# Load + filter both caches
# ---------------------------------------------------------------------
opy = pd.read_parquet(INT / "opy_value_cache.parquet")
opy = opy[~opy["country_orig"].isin(EXCLUDED_ORIGINS)]
opy = opy[(opy["total_value"] > 0) & opy["hs07_6d"].notna()].copy()
opy["val_ext"] = opy["val_total"] - opy["val_dom"]   # enforce new convention

ody = pd.read_parquet(INT / "ody_value_cache.parquet")
ody = ody[~ody["country_orig"].isin(EXCLUDED_ORIGINS)]
ody = ody[(ody["total_value"] > 0) & ody["country_dest"].notna()].copy()
ody["val_ext"] = ody["val_total"] - ody["val_dom"]

print(f"OPY rows: {len(opy):,} | HS6 codes: {opy['hs07_6d'].nunique():,}")
print(f"ODY rows: {len(ody):,} | destinations: {ody['country_dest'].nunique():,}")


# ---------------------------------------------------------------------
# Aggregate helpers
# ---------------------------------------------------------------------

def shares_by(d: pd.DataFrame, by) -> pd.DataFrame:
    """Value-weighted MNE shares (total / ext / dom) grouped by `by`."""
    if isinstance(by, str):
        by = [by]
    d = d.dropna(subset=by)
    g = (d.groupby(by, as_index=False)
           .agg(total_value=("total_value", "sum"),
                val_total=("val_total", "sum"),
                val_dom=("val_dom", "sum")))
    g["val_ext"]   = g["val_total"] - g["val_dom"]
    g["sh_total"]  = g["val_total"] / g["total_value"]
    g["sh_ext"]    = g["val_ext"]   / g["total_value"]
    g["sh_dom"]    = g["val_dom"]   / g["total_value"]
    return g


def grouped_hbar_3def(g: pd.DataFrame, label_col: str, fname: str, *,
                     title: str | None = None, xmax: float = 0.9,
                     sort_by: str = "sh_total", figsize=None) -> None:
    """Horizontal grouped-bar chart, three colours per category."""
    g = g.sort_values(sort_by, ascending=True).reset_index(drop=True)
    n = len(g)
    h = max(4, 0.55 * n + 1.5) if figsize is None else figsize[1]
    fig, ax = plt.subplots(figsize=(8.5, h) if figsize is None else figsize)
    y = np.arange(n)
    bar_h = 0.27
    ax.barh(y - bar_h,     g["sh_dom"],   bar_h, color=C_MNE_DOM, edgecolor=C_MNE_DOM,
            label="MNE-dom")
    ax.barh(y,             g["sh_ext"],   bar_h, color=C_MNE_EXT, edgecolor=C_MNE_EXT,
            label="MNE-ext (foreign)")
    ax.barh(y + bar_h,     g["sh_total"], bar_h, color=C_MNE_TOT, edgecolor=C_MNE_TOT,
            label="MNE-total")
    for yi, (_, row) in enumerate(g.iterrows()):
        ax.text(row["sh_total"] + 0.005, yi + bar_h, f"{row['sh_total']:.2f}",
                va="center", fontsize=7, color="black")
    ax.set_yticks(y)
    ax.set_yticklabels(g[label_col].astype(str), fontsize=9)
    ax.set_xlim(0, xmax)
    ax.set_xticks(np.arange(0, xmax + 1e-9, 0.1))
    ax.set_xlabel("Share in export value (value-weighted, pooled 2006–2022)")
    if title:
        ax.set_title(title, fontsize=11)
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    save_figure(fig, fname, G_OUT)


def lines_3def(g: pd.DataFrame, x_col: str, fname: str, *,
              title: str | None = None, xlabel: str = "") -> None:
    """Overlaid lines (3 defs) on a shared x-axis."""
    g = g.sort_values(x_col)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(g[x_col], g["sh_total"], marker="o", color=C_MNE_TOT,
            label="MNE-total", linewidth=1.5)
    ax.plot(g[x_col], g["sh_ext"],   marker="s", color=C_MNE_EXT,
            label="MNE-ext (foreign)", linewidth=1.5)
    ax.plot(g[x_col], g["sh_dom"],   marker="^", color=C_MNE_DOM,
            label="MNE-dom", linewidth=1.5)
    ax.set_ylim(0, max(0.85, g["sh_total"].max() * 1.1))
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Share in export value")
    if title:
        ax.set_title(title, fontsize=11)
    ax.legend(frameon=False, fontsize=9, loc="best")
    save_figure(fig, fname, G_OUT)


def write_table_3def(g: pd.DataFrame, label_col: str, label_header: str,
                     fname: str) -> None:
    g = g.sort_values("sh_total", ascending=False).reset_index(drop=True)
    lines = [r"\begin{tabular}{lccc r}", r"\toprule",
             rf"{label_header} & MNE$_{{\text{{total}}}}$ & MNE$_{{\text{{ext}}}}$ & MNE$_{{\text{{dom}}}}$ & Value (\$bn) \\",
             r"\midrule"]
    for _, r in g.iterrows():
        lab = str(r[label_col]).replace("&", r"\&")
        lines.append(
            f"{lab} & {r['sh_total']:.3f} & {r['sh_ext']:.3f} & "
            f"{r['sh_dom']:.3f} & {r['total_value']/1e9:7.2f} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}"]
    (T_OUT / f"{fname}.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------
# Decile helper (value-weighted bins of a continuous characteristic)
# ---------------------------------------------------------------------

def decile_3def(d: pd.DataFrame, char_col: str, char_label: str, fname: str) -> None:
    s = (d.dropna(subset=[char_col])
           .groupby("hs07_6d", as_index=False)
           .agg(total_value=("total_value", "sum"),
                val_total=("val_total", "sum"),
                val_dom=("val_dom", "sum"),
                ch=(char_col, "first")))
    s["decile"] = pd.qcut(s["ch"], 10, labels=False, duplicates="drop") + 1
    g = shares_by(s.assign(total_value=s["total_value"],
                           val_total=s["val_total"],
                           val_dom=s["val_dom"]), "decile")
    lines_3def(g, "decile", fname,
               title=f"{char_label}: MNE shares by decile",
               xlabel=f"{char_label} decile (1 = lowest, 10 = highest)")
    write_table_3def(g, "decile", "Decile", fname)


# ---------------------------------------------------------------------
# PRODUCT cuts
# ---------------------------------------------------------------------
print("\n>>> Product cuts:")

# 1. HS section (21 categories)
g_hs = shares_by(opy, "hs_section")
grouped_hbar_3def(g_hs, "hs_section", "byd_prod_hs_section",
                  title="MNE shares by HS section (LAC9, pooled)")
write_table_3def(g_hs, "hs_section", "HS section", "byd_prod_hs_section")
print("  byd_prod_hs_section")

# 2. Lall 2000 technology category
g_lall = shares_by(opy, "lall2000_category")
grouped_hbar_3def(g_lall, "lall2000_category", "byd_prod_lall2000",
                  title="MNE shares by Lall 2000 technology category")
write_table_3def(g_lall, "lall2000_category", "Lall 2000 category", "byd_prod_lall2000")
print("  byd_prod_lall2000")

# 3. IPC1 (Lybbert-Zolas)
g_ipc = shares_by(opy, "ipc1")
grouped_hbar_3def(g_ipc, "ipc1", "byd_prod_ipc1",
                  title="MNE shares by IPC patent section (Lybbert-Zolas)")
write_table_3def(g_ipc, "ipc1", "IPC section", "byd_prod_ipc1")
print("  byd_prod_ipc1")

# 4-7. Continuous characteristics by decile
for char, lbl in [
    ("upstreamness",   "Upstreamness"),
    ("sigma",          "σ (Broda-Weinstein)"),
    ("complexity",     "Product Complexity Index"),
    ("quality_ladder", "Quality ladder"),
]:
    decile_3def(opy, char, lbl, f"byd_prod_{char}_decile")
    print(f"  byd_prod_{char}_decile")


# ---------------------------------------------------------------------
# DESTINATION cuts
# ---------------------------------------------------------------------
print("\n>>> Destination cuts:")

INCOME_LBL = {1: "Low", 2: "Lower-middle", 3: "Upper-middle", 4: "High"}
DIST_LBL   = {1: "Q1 (closest)", 2: "Q2", 3: "Q3", 4: "Q4", 5: "Q5 (farthest)"}

# 1. Income group
g_inc = shares_by(ody, "income_group_dest")
g_inc["label"] = g_inc["income_group_dest"].map(INCOME_LBL)
grouped_hbar_3def(g_inc, "label", "byd_dest_income_group",
                  title="MNE shares by destination income group",
                  xmax=0.8)
write_table_3def(g_inc, "label", "Income group", "byd_dest_income_group")
print("  byd_dest_income_group")

# 2. Region
g_reg = shares_by(ody, "dest_region")
grouped_hbar_3def(g_reg, "dest_region", "byd_dest_region",
                  title="MNE shares by destination region", xmax=0.8)
write_table_3def(g_reg, "dest_region", "Destination region", "byd_dest_region")
print("  byd_dest_region")

# 3. Distance quintile (overlaid lines)
g_dist = shares_by(ody, "dist_quintile").rename(columns={"dist_quintile": "x"})
lines_3def(g_dist, "x", "byd_dest_dist_quintile",
           title="MNE shares by bilateral distance quintile",
           xlabel="Distance quintile (1 = closest, 5 = farthest)")
g_dist["label"] = g_dist["x"].map(DIST_LBL)
write_table_3def(g_dist, "label", "Distance quintile", "byd_dest_dist_quintile")
print("  byd_dest_dist_quintile")

# 4. Intra/extra
g_intra = shares_by(ody, "intra_regional")
g_intra["label"] = g_intra["intra_regional"].map({0: "Extra-regional", 1: "Intra-regional"})
grouped_hbar_3def(g_intra, "label", "byd_dest_intra_regional",
                  title="MNE shares: intra- vs extra-regional", xmax=0.8)
write_table_3def(g_intra, "label", "", "byd_dest_intra_regional")
print("  byd_dest_intra_regional")

# 5. Contiguous
g_ctg = shares_by(ody, "contig")
g_ctg["label"] = g_ctg["contig"].map({0: "Non-contiguous", 1: "Contiguous"})
grouped_hbar_3def(g_ctg, "label", "byd_dest_contig",
                  title="MNE shares: border-sharing", xmax=0.8)
write_table_3def(g_ctg, "label", "", "byd_dest_contig")
print("  byd_dest_contig")

# 6. FTA
g_fta = shares_by(ody, "fta_wto")
g_fta["label"] = g_fta["fta_wto"].map({0: "No FTA / WTO", 1: "FTA / WTO"})
grouped_hbar_3def(g_fta, "label", "byd_dest_fta",
                  title="MNE shares: FTA / WTO membership", xmax=0.8)
write_table_3def(g_fta, "label", "", "byd_dest_fta")
print("  byd_dest_fta")


# ---------------------------------------------------------------------
# Numerical summary: spread per def per cut
# ---------------------------------------------------------------------
print("\n>>> Spread of value-weighted share by MNE definition per cut:")
print(f"  {'cut':30s} | {'tot range':>14s} | {'ext range':>14s} | {'dom range':>14s}")
print("  " + "-" * 80)
cuts = {
    "hs_section (product)":    g_hs,
    "lall2000 (product)":      g_lall,
    "ipc1 (product)":          g_ipc,
    "income_group (dest)":     g_inc,
    "region (dest)":           g_reg,
    "dist_quintile (dest)":    g_dist,
    "intra_regional (dest)":   g_intra,
    "contig (dest)":           g_ctg,
    "fta_wto (dest)":          g_fta,
}
def rng(s): return f"{s.min():.2f}–{s.max():.2f}"
for name, g in cuts.items():
    print(f"  {name:30s} | {rng(g['sh_total']):>14s} | {rng(g['sh_ext']):>14s} | {rng(g['sh_dom']):>14s}")

print(f"\n>>> Outputs in {G_OUT} and {T_OUT}")
