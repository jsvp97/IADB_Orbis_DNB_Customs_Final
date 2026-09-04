"""
sf_explore_products_perdef_quintile.py
======================================

Full product-side analysis, per MNE definition, using QUINTILES (5 bins)
for continuous characteristics and the natural categories for the
discrete ones.

For each combination of [characteristic] x [def in {total, ext, dom}],
produce:
    * a bar chart of value-weighted MNE share by quintile / category
    * a matching tex table

Continuous chars (5-quintile bins):
    complexity (PCI), sigma (Broda-Weinstein), upstreamness (Antras-Chor),
    quality_ladder (Khandelwal), rhci (UNCTAD)

Categorical chars (natural buckets, ranked by share of that def):
    HS section (21), Lall 2000 tech category, IPC1 (Lybbert-Zolas)

Outputs:
    2_Output/Graphs/Exploration_Products_PerDef_Q/
    2_Output/Tables/Exploration_Products_PerDef_Q/
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

G_OUT = GRAPHS / "Exploration_Products_PerDef_Q"
T_OUT = TABLES / "Exploration_Products_PerDef_Q"
for d in (G_OUT, T_OUT):
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
print(f"OPY rows: {len(opy):,} | HS6: {opy['hs07_6d'].nunique():,}")


# ---------------------------------------------------------------------
# Aggregation helper
# ---------------------------------------------------------------------
def aggregate(d: pd.DataFrame, by) -> pd.DataFrame:
    by = [by] if isinstance(by, str) else by
    d = d.dropna(subset=by)
    g = (d.groupby(by, as_index=False)
           .agg(total_value=("total_value", "sum"),
                val_total=("val_total", "sum"),
                val_dom=("val_dom", "sum"),
                n_hs6=("hs07_6d", "nunique")))
    g["val_ext"]   = g["val_total"] - g["val_dom"]
    for k in DEFS:
        g[f"sh_{k}"] = g[f"val_{k}"] / g["total_value"]
    return g


# ---------------------------------------------------------------------
# Plot helpers
# ---------------------------------------------------------------------
def vbar_quintile_perdef(g: pd.DataFrame, x_col: str, def_: str, fname: str,
                         char_label: str) -> None:
    g = g.sort_values(x_col)
    fig, ax = plt.subplots(figsize=(7.5, 4))
    col = DEF_COLOR[def_]
    ax.bar(g[x_col].astype(int), g[f"sh_{def_}"], color=col, edgecolor=col, width=0.7)
    for x, v in zip(g[x_col], g[f"sh_{def_}"]):
        ax.text(x, v + 0.01, f"{v:.2f}", ha="center", fontsize=9)
    ymax = max(0.9, g[f"sh_{def_}"].max() * 1.15)
    ax.set_xlabel(f"{char_label} quintile (1 = lowest, 5 = highest)")
    ax.set_ylabel(f"{DEF_LABEL[def_]} share in export value")
    ax.set_ylim(0, ymax)
    ax.set_xticks(range(1, 6))
    save_figure(fig, fname, G_OUT)


def hbar_categorical_perdef(g: pd.DataFrame, label_col: str, def_: str,
                             fname: str, title: str, *, xmax: float = 0.95,
                             figsize=None) -> None:
    g = g.sort_values(f"sh_{def_}", ascending=True).reset_index(drop=True)
    n = len(g)
    if figsize is None:
        figsize = (8.5, max(3.5, 0.45 * n + 1.5))
    fig, ax = plt.subplots(figsize=figsize)
    col = DEF_COLOR[def_]
    ax.barh(g[label_col].astype(str), g[f"sh_{def_}"], color=col, edgecolor=col)
    for y, v in zip(g[label_col].astype(str), g[f"sh_{def_}"]):
        ax.text(v + 0.005, y, f"{v:.2f}", va="center", fontsize=8)
    ax.set_xlim(0, xmax)
    ax.set_xlabel(f"{DEF_LABEL[def_]} share in export value")
    ax.set_title(title, fontsize=11)
    save_figure(fig, fname, G_OUT)


def write_table_perdef(g: pd.DataFrame, label_col: str, def_: str,
                       label_hdr: str, fname: str) -> None:
    g = g.sort_values(f"sh_{def_}", ascending=False).reset_index(drop=True)
    lines = [r"\begin{tabular}{lccr}", r"\toprule",
             rf"{label_hdr} & {DEF_LABEL[def_]} share & N HS6 & Value (\$bn) \\",
             r"\midrule"]
    for _, r in g.iterrows():
        lab = str(r[label_col]).replace("&", r"\&")
        lines.append(f"{lab} & {r[f'sh_{def_}']:.3f} & {int(r['n_hs6']):,} & {r['total_value']/1e9:7.2f} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (T_OUT / f"{fname}.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------
# CONTINUOUS CHARACTERISTICS -> quintiles per def
# ---------------------------------------------------------------------
CONT = [
    ("complexity",     "Complexity (PCI)"),
    ("sigma",          "sigma (Broda-Weinstein)"),
    ("upstreamness",   "Upstreamness (Antras-Chor)"),
    ("quality_ladder", "Quality ladder (Khandelwal)"),
    ("rhci",           "RHCI (UNCTAD)"),
]

print("\n>>> Continuous characteristic quintiles, per def:")
for char, lbl in CONT:
    s = (opy.dropna(subset=[char])
            .groupby("hs07_6d", as_index=False)
            .agg(total_value=("total_value", "sum"),
                 val_total=("val_total", "sum"),
                 val_dom=("val_dom", "sum"),
                 ch=(char, "first")))
    s["val_ext"] = s["val_total"] - s["val_dom"]
    s["quintile"] = pd.qcut(s["ch"], 5, labels=False, duplicates="drop") + 1
    g = (s.groupby("quintile", as_index=False)
            .agg(total_value=("total_value", "sum"),
                 val_total=("val_total", "sum"),
                 val_dom=("val_dom", "sum"),
                 n_hs6=("hs07_6d", "nunique")))
    g["val_ext"] = g["val_total"] - g["val_dom"]
    for k in DEFS:
        g[f"sh_{k}"] = g[f"val_{k}"] / g["total_value"]

    # Save to console for inline reporting
    print(f"\n  {lbl} quintile:")
    print(f"  {'Q':>2} | {'total':>7} {'ext':>7} {'dom':>7} | {'n HS6':>5} | {'$bn':>7}")
    print("  " + "-" * 55)
    for _, r in g.iterrows():
        print(f"  {int(r['quintile']):>2} | {r['sh_total']:>7.3f} {r['sh_ext']:>7.3f} "
              f"{r['sh_dom']:>7.3f} | {int(r['n_hs6']):>5} | {r['total_value']/1e9:>7.1f}")

    for def_ in DEFS:
        vbar_quintile_perdef(g, "quintile", def_, f"prodq_{char}_{def_}", lbl)
    # Single table (3 defs side-by-side) per characteristic
    out = [r"\begin{tabular}{rccc rr}", r"\toprule",
           rf"Quintile & MNE$_{{\text{{total}}}}$ & MNE$_{{\text{{ext}}}}$ & MNE$_{{\text{{dom}}}}$ & N HS6 & Value (\$bn) \\",
           r"\midrule"]
    for _, r in g.iterrows():
        out.append(f"Q{int(r['quintile'])} & {r['sh_total']:.3f} & {r['sh_ext']:.3f} "
                   f"& {r['sh_dom']:.3f} & {int(r['n_hs6']):,} & {r['total_value']/1e9:7.2f} \\\\")
    out += [r"\bottomrule", r"\end{tabular}"]
    (T_OUT / f"prodq_{char}_table.tex").write_text("\n".join(out) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------
# CATEGORICAL CHARACTERISTICS -> hbar per def (ranked by that def)
# ---------------------------------------------------------------------
print("\n>>> Categorical product cuts, per def:")

# HS section
g = aggregate(opy, "hs_section")
print("\n  HS section (sorted by MNE_total share, descending):")
for _, r in g.sort_values("sh_total", ascending=False).iterrows():
    print(f"    {str(r['hs_section']):<22} tot={r['sh_total']:.3f} ext={r['sh_ext']:.3f} dom={r['sh_dom']:.3f}  ${r['total_value']/1e9:6.1f}bn")
for def_ in DEFS:
    hbar_categorical_perdef(g, "hs_section", def_,
                             f"prodq_hs_section_{def_}",
                             f"{DEF_LABEL[def_]} share by HS section",
                             figsize=(9, 9))
    write_table_perdef(g, "hs_section", def_, "HS section",
                       f"prodq_hs_section_{def_}")

# Lall 2000
g = aggregate(opy, "lall2000_category")
print("\n  Lall 2000 (sorted by MNE_total share, descending):")
for _, r in g.sort_values("sh_total", ascending=False).iterrows():
    cat = str(r['lall2000_category'])[:48]
    print(f"    {cat:<50} tot={r['sh_total']:.3f} ext={r['sh_ext']:.3f} dom={r['sh_dom']:.3f}  ${r['total_value']/1e9:6.1f}bn")
for def_ in DEFS:
    hbar_categorical_perdef(g, "lall2000_category", def_,
                             f"prodq_lall2000_{def_}",
                             f"{DEF_LABEL[def_]} share by Lall 2000 category",
                             figsize=(11, 6))
    write_table_perdef(g, "lall2000_category", def_, "Lall 2000 category",
                       f"prodq_lall2000_{def_}")

# IPC1
g = aggregate(opy, "ipc1")
print("\n  IPC1 (sorted by MNE_total share, descending):")
for _, r in g.sort_values("sh_total", ascending=False).iterrows():
    print(f"    {str(r['ipc1']):<48} tot={r['sh_total']:.3f} ext={r['sh_ext']:.3f} dom={r['sh_dom']:.3f}  ${r['total_value']/1e9:6.1f}bn")
for def_ in DEFS:
    hbar_categorical_perdef(g, "ipc1", def_,
                             f"prodq_ipc1_{def_}",
                             f"{DEF_LABEL[def_]} share by IPC patent section",
                             figsize=(10, 4))
    write_table_perdef(g, "ipc1", def_, "IPC section", f"prodq_ipc1_{def_}")


# ---------------------------------------------------------------------
# Top / bottom HS2 chapters per def (most concentrated)
# ---------------------------------------------------------------------
print("\n>>> Top 15 HS2 chapters by each def's share (min trade value $500m):")
g = aggregate(opy, "hs2")
g = g[g["total_value"] >= 5e8]   # filter tiny chapters
for def_ in DEFS:
    top = g.sort_values(f"sh_{def_}", ascending=False).head(15)
    print(f"\n  By {DEF_LABEL[def_]}:")
    print(f"  {'HS2':>4} | {'total':>7} {'ext':>7} {'dom':>7} | {'$bn':>7}")
    print("  " + "-" * 50)
    for _, r in top.iterrows():
        print(f"  {str(r['hs2']):>4} | {r['sh_total']:>7.3f} {r['sh_ext']:>7.3f} {r['sh_dom']:>7.3f} | {r['total_value']/1e9:>7.2f}")
    # And a per-def hbar of top 15
    hbar_categorical_perdef(top.copy(), "hs2", def_,
                             f"prodq_top15_hs2_{def_}",
                             f"Top 15 HS2 chapters by {DEF_LABEL[def_]} share",
                             figsize=(8.5, 7), xmax=1.0)
    write_table_perdef(top, "hs2", def_, "HS2 chapter", f"prodq_top15_hs2_{def_}")


print(f"\n>>> Done. Figures in {G_OUT}, tables in {T_OUT}")
