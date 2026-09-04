"""
sf3_products.py
===============

Stylized Fact 3 — Foreign multinationals are particularly prevalent in
complex, technology-intensive products; domestic MNEs concentrate in
resource-extractive and low-human-capital products.

Main exhibits:
    fig_sf3_pci_quintile        Complexity quintile, 3 defs (vbar)
    fig_sf3_lall3               Lall 3-bucket, 3 defs (hbar)

Appendix exhibits:
    fig_sf3_lall5               Lall 5-bucket, 3 defs (hbar) -- robustness grouping
    fig_sf3_hs_section_<def>    HS section ranking per def (3 hbars)
    fig_sf3_sigma_quintile      sigma quintile, 3 defs
    fig_sf3_upstream_quintile   upstreamness quintile, 3 defs
    fig_sf3_quality_quintile    quality ladder quintile, 3 defs
    fig_sf3_rhci_quintile       RHCI quintile, 3 defs
    fig_sf3_ipc1_<def>          IPC1 ranking per def (3 hbars)
    fig_sf3_top15_hs2_<def>     Top 15 HS2 chapters per def (3 hbars)

Tables:
    tab_sf3_lall3.tex            Lall 3-bucket descriptive (3 defs side-by-side)
    tab_sf3_lall5.tex            Lall 5-bucket descriptive
    tab_sf3_pci_quintile.tex     Complexity quintile (3 defs)
    tab_sf3_hs_section_all.tex   HS section descriptive
    tab_sf3_quintile_<char>.tex  one per continuous char

Regressions (HS6 cross-section, value-weighted, robust SE):
    reg_sf3_total.tex, reg_sf3_ext.tex, reg_sf3_dom.tex
    Spec ladder per def:
      Col 1: PCI only
      Col 2: + sigma + upstreamness + quality_ladder + RHCI
      Col 3: + Lall3 medium / high dummies (low base)
      Col 4: + HS section FE

Origin exclusions: ECU (see _common.EXCLUDED_ORIGINS).
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyfixest as pf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    INT, GRAPHS, TABLES, REGS, OVERLEAF_SF, EXCLUDED_ORIGINS,
    C_MNE_TOT, C_MNE_EXT, C_MNE_DOM,
    ensure_dir, save_figure,
)


# ---------------------------------------------------------------------
# Output paths
# ---------------------------------------------------------------------
G_SF3 = GRAPHS / "SF3_Products"
T_SF3 = TABLES / "SF3_Products"
R_SF3 = REGS   / "SF3_Products"

OL_G_SF3 = OVERLEAF_SF / "Graphs"      / "SF3_Products"
OL_T_SF3 = OVERLEAF_SF / "Tables"      / "SF3_Products"
OL_R_SF3 = OVERLEAF_SF / "Regressions" / "SF3_Products"

for d in (G_SF3, T_SF3, R_SF3, OL_G_SF3, OL_T_SF3, OL_R_SF3):
    ensure_dir(d)


# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------
DEFS = ["total", "ext", "dom"]
DEF_COLOR = {"total": C_MNE_TOT, "ext": C_MNE_EXT, "dom": C_MNE_DOM}
DEF_LABEL = {"total": "MNE-total", "ext": "MNE-ext (foreign)", "dom": "MNE-dom"}
DEF_MATH  = {"total": r"MNE$_{\text{total}}$",
             "ext":   r"MNE$_{\text{ext}}$",
             "dom":   r"MNE$_{\text{dom}}$"}


# ---------------------------------------------------------------------
# Lall recodes
# ---------------------------------------------------------------------
LALL_5 = {
    # 5-bucket: Primary | Resource-based | Low-tech | Medium-tech | High-tech | Unclassified
    "Primary products":                                                "Primary",
    "Resource-based manufactures: agro-based":                         "Resource-based",
    "Resource-based manufactures: other":                              "Resource-based",
    "Low technology manufactures: textile, garment and footwear":      "Low-tech",
    "Low technology manufactures: other products":                     "Low-tech",
    "Medium technology manufactures: automotive":                      "Medium-tech",
    "Medium technology manufactures: engineering":                     "Medium-tech",
    "Medium technology manufactures: process":                         "Medium-tech",
    "High technology manufactures: electronic and electrical":         "High-tech",
    "High technology manufactures: other":                             "High-tech",
    "Unclassified products":                                           "Unclassified",
}
LALL_5_ORDER = ["Primary", "Resource-based", "Low-tech", "Medium-tech",
                "High-tech", "Unclassified"]

LALL_3 = {
    # 3-bucket: Low (primary + RB + low-tech + unclassified) | Medium | High
    "Primary products":                                                "Low-tech (incl. primary/RB)",
    "Resource-based manufactures: agro-based":                         "Low-tech (incl. primary/RB)",
    "Resource-based manufactures: other":                              "Low-tech (incl. primary/RB)",
    "Low technology manufactures: textile, garment and footwear":      "Low-tech (incl. primary/RB)",
    "Low technology manufactures: other products":                     "Low-tech (incl. primary/RB)",
    "Unclassified products":                                           "Low-tech (incl. primary/RB)",
    "Medium technology manufactures: automotive":                      "Medium-tech",
    "Medium technology manufactures: engineering":                     "Medium-tech",
    "Medium technology manufactures: process":                         "Medium-tech",
    "High technology manufactures: electronic and electrical":         "High-tech",
    "High technology manufactures: other":                             "High-tech",
}
LALL_3_ORDER = ["Low-tech (incl. primary/RB)", "Medium-tech", "High-tech"]

LALL_4 = {
    "Primary products":                                                "Primary and resource-based",
    "Resource-based manufactures: agro-based":                         "Primary and resource-based",
    "Resource-based manufactures: other":                              "Primary and resource-based",
    "Low technology manufactures: textile, garment and footwear":      "Low tech manufacturing",
    "Low technology manufactures: other products":                     "Low tech manufacturing",
    "Unclassified products":                                           "Low tech manufacturing",
    "Medium technology manufactures: automotive":                      "Medium tech manufacturing",
    "Medium technology manufactures: engineering":                     "Medium tech manufacturing",
    "Medium technology manufactures: process":                         "Medium tech manufacturing",
    "High technology manufactures: electronic and electrical":         "High tech manufacturing",
    "High technology manufactures: other":                             "High tech manufacturing",
}
LALL_4_ORDER = ["High tech manufacturing", "Medium tech manufacturing",
                "Low tech manufacturing", "Primary and resource-based"]
# Two-line x-tick labels so the four categories fit under vertical bars.
LALL_4_XLBL = {
    "High tech manufacturing":     "High tech\nmanufacturing",
    "Medium tech manufacturing":   "Medium tech\nmanufacturing",
    "Low tech manufacturing":      "Low tech\nmanufacturing",
    "Primary and resource-based":  "Primary and\nresource-based",
}


# ---------------------------------------------------------------------
# Load + filter
# ---------------------------------------------------------------------
opy = pd.read_parquet(INT / "opy_value_cache.parquet")
opy = opy[~opy["country_orig"].isin(EXCLUDED_ORIGINS)]
opy = opy[(opy["total_value"] > 0) & opy["hs07_6d"].notna()].copy()
opy["val_ext"] = opy["val_total"] - opy["val_dom"]
opy["lall_5"] = opy["lall2000_category"].map(LALL_5)
opy["lall_3"] = opy["lall2000_category"].map(LALL_3)
opy["lall_4"] = opy["lall2000_category"].map(LALL_4)


# ---------------------------------------------------------------------
# Collapse to HS6 cross-section
# ---------------------------------------------------------------------
hs6 = (opy.groupby("hs07_6d", as_index=False)
          .agg(total_value=("total_value", "sum"),
               val_total=("val_total", "sum"),
               val_dom=("val_dom", "sum"),
               upstreamness=("upstreamness", "first"),
               sigma=("sigma", "first"),
               complexity=("complexity", "first"),
               quality_ladder=("quality_ladder", "first"),
               rhci=("rhci", "first"),
               lall2000_category=("lall2000_category", "first"),
               lall_5=("lall_5", "first"),
               lall_3=("lall_3", "first"),
               lall_4=("lall_4", "first"),
               ipc1=("ipc1", "first"),
               hs2=("hs2", "first"),
               hs_section=("hs_section", "first")))
hs6["val_ext"] = hs6["val_total"] - hs6["val_dom"]
for k in DEFS:
    hs6[f"sh_{k}"] = hs6[f"val_{k}"] / hs6["total_value"]
print(f"HS6 cross-section: {len(hs6):,} products | total value: ${hs6['total_value'].sum()/1e9:.1f} bn")


# ---------------------------------------------------------------------
# Aggregator + plotters
# ---------------------------------------------------------------------
def aggregate(d: pd.DataFrame, by, value_filter: float = 0.0,
              order: list | None = None) -> pd.DataFrame:
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
    if order is not None:
        g = g.set_index(by[0]).reindex(order).reset_index()
    if value_filter > 0:
        g = g[g["total_value"] >= value_filter]
    return g


def grouped_vbar_3def(g: pd.DataFrame, x_col: str, fname: str, *,
                     title: str | None = None, xlabels: dict | None = None,
                     xlabel: str = "", figsize=(8.5, 4.5)) -> None:
    g = g.copy()
    if xlabels:
        g["xlabel"] = g[x_col].map(xlabels)
    else:
        g["xlabel"] = g[x_col].astype(str)
    n = len(g)
    x = np.arange(n)
    bw = 0.27
    fig, ax = plt.subplots(figsize=figsize)
    ax.bar(x - bw, g["sh_total"], bw, color=C_MNE_TOT, edgecolor=C_MNE_TOT, label="MNE-total")
    ax.bar(x,      g["sh_ext"],   bw, color=C_MNE_EXT, edgecolor=C_MNE_EXT, label="MNE-ext (foreign)")
    ax.bar(x + bw, g["sh_dom"],   bw, color=C_MNE_DOM, edgecolor=C_MNE_DOM, label="MNE-dom")
    for xi, r in zip(x, g.itertuples()):
        ax.text(xi - bw, r.sh_total + 0.01, f"{r.sh_total:.2f}", ha="center", fontsize=7)
        ax.text(xi,      r.sh_ext   + 0.01, f"{r.sh_ext:.2f}",   ha="center", fontsize=7)
        ax.text(xi + bw, r.sh_dom   + 0.01, f"{r.sh_dom:.2f}",   ha="center", fontsize=7)
    ax.set_xticks(x)
    ax.set_xticklabels(g["xlabel"], rotation=0)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Share in export value (value-weighted)")
    ymax = max(0.9, g["sh_total"].max() * 1.15)
    ax.set_ylim(0, ymax)
    if title:
        ax.set_title(title, fontsize=11)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save_figure(fig, fname, G_SF3, OL_G_SF3)


def grouped_hbar_3def(g: pd.DataFrame, label_col: str, fname: str, *,
                     title: str | None = None, xmax: float | None = None,
                     figsize=None) -> None:
    g = g.copy().reset_index(drop=True)
    n = len(g)
    if figsize is None:
        figsize = (9, max(3.5, 0.7 * n + 1.5))
    y = np.arange(n)
    bh = 0.27
    fig, ax = plt.subplots(figsize=figsize)
    ax.barh(y - bh, g["sh_dom"],   bh, color=C_MNE_DOM, edgecolor=C_MNE_DOM, label="MNE-dom")
    ax.barh(y,      g["sh_ext"],   bh, color=C_MNE_EXT, edgecolor=C_MNE_EXT, label="MNE-ext (foreign)")
    ax.barh(y + bh, g["sh_total"], bh, color=C_MNE_TOT, edgecolor=C_MNE_TOT, label="MNE-total")
    for yi, r in zip(y, g.itertuples()):
        ax.text(r.sh_total + 0.005, yi + bh, f"{r.sh_total:.2f}", va="center", fontsize=7)
        ax.text(r.sh_ext   + 0.005, yi,      f"{r.sh_ext:.2f}",   va="center", fontsize=7)
        ax.text(r.sh_dom   + 0.005, yi - bh, f"{r.sh_dom:.2f}",   va="center", fontsize=7)
    ax.set_yticks(y)
    ax.set_yticklabels(g[label_col].astype(str))
    if xmax is None:
        xmax = max(0.9, g["sh_total"].max() * 1.1)
    ax.set_xlim(0, xmax)
    ax.set_xlabel("Share in export value (value-weighted)")
    if title:
        ax.set_title(title, fontsize=11)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    save_figure(fig, fname, G_SF3, OL_G_SF3)


def hbar_perdef(g: pd.DataFrame, label_col: str, def_: str, fname: str, *,
                title: str | None = None, xmax: float | None = None,
                figsize=None) -> None:
    g = g.sort_values(f"sh_{def_}", ascending=True).reset_index(drop=True)
    n = len(g)
    if figsize is None:
        figsize = (9, max(3.5, 0.45 * n + 1.5))
    fig, ax = plt.subplots(figsize=figsize)
    col = DEF_COLOR[def_]
    ax.barh(g[label_col].astype(str), g[f"sh_{def_}"], color=col, edgecolor=col)
    for y, v in zip(g[label_col].astype(str), g[f"sh_{def_}"]):
        ax.text(v + 0.005, y, f"{v:.2f}", va="center", fontsize=8)
    if xmax is None:
        xmax = max(0.30, g[f"sh_{def_}"].max() * 1.15)
    ax.set_xlim(0, xmax)
    ax.set_xlabel(f"{DEF_LABEL[def_]} share in export value")
    if title:
        ax.set_title(title, fontsize=11)
    save_figure(fig, fname, G_SF3, OL_G_SF3)


def write_table_3def(g: pd.DataFrame, label_col: str, label_hdr: str,
                     fname: str, *, sort_by: str = "sh_total") -> None:
    if sort_by:
        g = g.sort_values(sort_by, ascending=False).reset_index(drop=True)
    lines = [r"\begin{tabular}{lccc rr}", r"\toprule",
             rf"{label_hdr} & {DEF_MATH['total']} & {DEF_MATH['ext']} & {DEF_MATH['dom']} & N HS6 & Value (\$bn) \\",
             r"\midrule"]
    for _, r in g.iterrows():
        lab = str(r[label_col]).replace("&", r"\&")
        lines.append(
            f"{lab} & {r['sh_total']:.3f} & {r['sh_ext']:.3f} & "
            f"{r['sh_dom']:.3f} & {int(r['n_hs6']):,} & {r['total_value']/1e9:7.2f} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}"]
    p = T_SF3 / f"{fname}.tex"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    import shutil
    shutil.copy2(p, OL_T_SF3 / f"{fname}.tex")


def add_quintile(df: pd.DataFrame, char: str) -> pd.DataFrame:
    d = df.dropna(subset=[char]).copy()
    d["quintile"] = pd.qcut(d[char], 5, labels=False, duplicates="drop") + 1
    return d


# ---------------------------------------------------------------------
# Two-definition plotters (foreign + domestic only; no MNE-total series)
#   foreign  = MNE_ext  -> navy   (C_MNE_EXT)
#   domestic = MNE_dom  -> gray   (C_MNE_DOM)
# ---------------------------------------------------------------------
def grouped_vbar_2def(g: pd.DataFrame, x_col: str, fname: str, *,
                      title: str | None = None, xlabels: dict | None = None,
                      xlabel: str = "", ymax: float | None = None,
                      figsize=(8.5, 4.5)) -> None:
    g = g.copy()
    g["xlabel"] = g[x_col].map(xlabels) if xlabels else g[x_col].astype(str)
    n = len(g)
    x = np.arange(n)
    bw = 0.38
    fig, ax = plt.subplots(figsize=figsize)
    ax.bar(x - bw / 2, g["sh_ext"], bw, color=C_MNE_EXT, edgecolor=C_MNE_EXT, label="Foreign MNEs")
    ax.bar(x + bw / 2, g["sh_dom"], bw, color=C_MNE_DOM, edgecolor="#9e9e9e",
           linewidth=0.5, label="Domestic MNEs")
    for xi, r in zip(x, g.itertuples()):
        ax.text(xi - bw / 2, r.sh_ext + 0.01, f"{r.sh_ext:.2f}", ha="center", fontsize=8)
        ax.text(xi + bw / 2, r.sh_dom + 0.01, f"{r.sh_dom:.2f}", ha="center", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(g["xlabel"], rotation=0)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Share in export value (value-weighted)")
    ax.set_ylim(0, ymax if ymax is not None else max(0.9, g["sh_ext"].max() * 1.15))
    if title:
        ax.set_title(title, fontsize=11)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save_figure(fig, fname, G_SF3, OL_G_SF3)


def grouped_hbar_2def(g: pd.DataFrame, label_col: str, fname: str, *,
                      title: str | None = None, xmax: float | None = None,
                      figsize=None) -> None:
    g = g.copy().reset_index(drop=True)
    n = len(g)
    if figsize is None:
        figsize = (9, max(3.0, 0.85 * n + 1.2))
    y = np.arange(n)
    bh = 0.38
    fig, ax = plt.subplots(figsize=figsize)
    # Draw top-to-bottom in the order given (first row at top).
    ypos = y[::-1]
    ax.barh(ypos + bh / 2, g["sh_ext"], bh, color=C_MNE_EXT, edgecolor=C_MNE_EXT, label="Foreign MNEs")
    ax.barh(ypos - bh / 2, g["sh_dom"], bh, color=C_MNE_DOM, edgecolor="#9e9e9e",
            linewidth=0.5, label="Domestic MNEs")
    for yi, r in zip(ypos, g.itertuples()):
        ax.text(r.sh_ext + 0.006, yi + bh / 2, f"{r.sh_ext:.2f}", va="center", fontsize=8)
        ax.text(r.sh_dom + 0.006, yi - bh / 2, f"{r.sh_dom:.2f}", va="center", fontsize=8)
    ax.set_yticks(ypos)
    ax.set_yticklabels(g[label_col].astype(str))
    if xmax is None:
        xmax = max(0.9, g["sh_ext"].max() * 1.12)
    ax.set_xlim(0, xmax)
    ax.set_xlabel("Share in export value (value-weighted)")
    if title:
        ax.set_title(title, fontsize=11)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    save_figure(fig, fname, G_SF3, OL_G_SF3)


# ---------------------------------------------------------------------
# MAIN FIGURES  (foreign + domestic only -- no MNE-total series)
# ---------------------------------------------------------------------
print("\n>>> Main figures...")
QLBL = {1: "Q1", 2: "Q2", 3: "Q3", 4: "Q4", 5: "Q5"}

# Shared y-axis so figures 2 and 3 are the same chart type on the same scale.
YMAX = 0.8

# 1. Complexity (PCI) quintile -- foreign vs domestic
g = aggregate(add_quintile(hs6, "complexity"), "quintile")
grouped_vbar_2def(g, "quintile", "fig_sf3_pci_quintile",
                  xlabels=QLBL, ymax=YMAX,
                  xlabel="PCI quintile (1 = lowest complexity, 5 = highest)")
write_table_3def(g.assign(lbl=g["quintile"].map(QLBL)),
                 "lbl", "PCI quintile", "tab_sf3_pci_quintile",
                 sort_by="quintile")

# 2. Lall technology category -- four categories, vertical bars (same type/scale as fig 1)
g_l4 = aggregate(hs6, "lall_4", order=LALL_4_ORDER)
grouped_vbar_2def(g_l4, "lall_4", "fig_sf3_lall4",
                  xlabels=LALL_4_XLBL, ymax=YMAX, xlabel="")
write_table_3def(g_l4, "lall_4", "Technology category", "tab_sf3_lall4", sort_by="")


# ---------------------------------------------------------------------
# APPENDIX FIGURES + REGRESSIONS  (parked -- not in the current minimal set)
#   Set MAKE_EXTRAS = True to regenerate the full appendix sweep and the
#   HS6 cross-section regressions. The code below is left intact from the
#   previous pipeline but is skipped by the early exit when False.
# ---------------------------------------------------------------------
MAKE_EXTRAS = False
if not MAKE_EXTRAS:
    print("\n>>> SF3 minimal figure set complete "
          "(PCI quintile, technology category).")
    print(f"    Figures -> {G_SF3}")
    raise SystemExit(0)

print(">>> Appendix figures...")

# Lall 5-bucket (robustness alternative grouping)
g_l5 = aggregate(hs6, "lall_5", order=LALL_5_ORDER)
g_l5 = g_l5.dropna(subset=["lall_5"])
grouped_hbar_3def(g_l5, "lall_5", "fig_sf3_lall5",
                  title="MNE shares by Lall 2000 category (5-bucket)",
                  xmax=0.95)
write_table_3def(g_l5, "lall_5", "Lall (5-bucket)", "tab_sf3_lall5")

# Quintile bars for the other continuous chars
CONT = [
    ("sigma",          "sigma (Broda-Weinstein)",        "fig_sf3_sigma_quintile"),
    ("upstreamness",   "Upstreamness (Antras-Chor)",     "fig_sf3_upstream_quintile"),
    ("quality_ladder", "Quality ladder (Khandelwal)",    "fig_sf3_quality_quintile"),
    ("rhci",           "RHCI (UNCTAD)",                  "fig_sf3_rhci_quintile"),
]
for char, lbl, fname in CONT:
    g = aggregate(add_quintile(hs6, char), "quintile")
    grouped_vbar_3def(g, "quintile", fname,
                      title=f"MNE shares by {lbl} quintile",
                      xlabels=QLBL,
                      xlabel=f"{lbl} quintile (1 = lowest, 5 = highest)")
    write_table_3def(g.assign(lbl=g["quintile"].map(QLBL)),
                     "lbl", f"{lbl} quintile",
                     f"tab_sf3_{char}_quintile",
                     sort_by="quintile")

# HS section ranking per def
g_hs = aggregate(hs6, "hs_section")
write_table_3def(g_hs, "hs_section", "HS section", "tab_sf3_hs_section_all")
for def_ in DEFS:
    hbar_perdef(g_hs, "hs_section", def_,
                f"fig_sf3_hs_section_{def_}",
                title=f"{DEF_LABEL[def_]} share by HS section",
                figsize=(9, 9))

# IPC1 ranking per def
g_ipc = aggregate(hs6, "ipc1")
write_table_3def(g_ipc, "ipc1", "IPC section", "tab_sf3_ipc1_all")
for def_ in DEFS:
    hbar_perdef(g_ipc, "ipc1", def_,
                f"fig_sf3_ipc1_{def_}",
                title=f"{DEF_LABEL[def_]} share by IPC patent section",
                figsize=(10, 4))

# Top 15 HS2 chapters per def (>= $500m)
g_h2 = aggregate(hs6, "hs2", value_filter=5e8)
for def_ in DEFS:
    top = g_h2.sort_values(f"sh_{def_}", ascending=False).head(15)
    hbar_perdef(top, "hs2", def_,
                f"fig_sf3_top15_hs2_{def_}",
                title=f"Top 15 HS2 chapters by {DEF_LABEL[def_]} share (>= \\$500m)",
                figsize=(8.5, 7), xmax=1.0)
    write_table_3def(top, "hs2", "HS2 chapter", f"tab_sf3_top15_hs2_{def_}",
                     sort_by=f"sh_{def_}")


# ---------------------------------------------------------------------
# REGRESSIONS (HS6 cross-section, value-weighted, robust SE)
# ---------------------------------------------------------------------
print("\n>>> Regressions...")

# Estimated with pyfixest (project standard). HS6 cross-section, value-weighted,
# HC1 robust SE; HS-section FE absorbed via pyfixest FE syntax in the last column.

def stars(p):
    if p < 0.01: return "***"
    if p < 0.05: return "**"
    if p < 0.10: return "*"
    return ""

work = hs6.dropna(subset=["complexity"]).copy()
# Lall dummies (3-bucket; 'Low' is base)
work["lall_med"]  = (work["lall_3"] == "Medium-tech").astype(float)
work["lall_high"] = (work["lall_3"] == "High-tech").astype(float)
# Keep a consistent sample across columns (the HS-section-FE column needs it)
work = work.dropna(subset=["hs_section"]).copy()

# Spec ladder: 4 cols. 'fe' = pyfixest FE term ('' for none).
SPEC_LADDERS = [
    {"title": "PCI",             "X": ["complexity"],                                                            "fe": ""},
    {"title": "+ chars",         "X": ["complexity", "sigma", "upstreamness", "quality_ladder", "rhci"],          "fe": ""},
    {"title": "+ Lall",          "X": ["complexity", "sigma", "upstreamness", "quality_ladder", "rhci", "lall_med", "lall_high"], "fe": ""},
    {"title": "+ HS section FE", "X": ["complexity", "sigma", "upstreamness", "quality_ladder", "rhci", "lall_med", "lall_high"], "fe": "hs_section"},
]
COEF_LABELS = [
    ("Complexity (PCI)",        "complexity"),
    ("σ (Broda-Weinstein)",     "sigma"),
    ("Upstreamness",            "upstreamness"),
    ("Quality ladder",          "quality_ladder"),
    ("RHCI",                    "rhci"),
    ("Lall: medium-tech",       "lall_med"),
    ("Lall: high-tech",         "lall_high"),
]


def _g(m, name):
    """(beta, se, p) for `name`, or (None, None, None) if absent."""
    c, s, p = m.coef(), m.se(), m.pvalue()
    if name in c.index:
        return float(c[name]), float(s[name]), float(p[name])
    return None, None, None


def run_regs(dvar: str):
    out = []
    for spec in SPEC_LADDERS:
        d = work.dropna(subset=spec["X"] + [dvar]).copy()
        fml = f"{dvar} ~ " + " + ".join(spec["X"]) + (f" | {spec['fe']}" if spec["fe"] else "")
        try:
            m = pf.feols(fml, data=d, weights="total_value", vcov="hetero")
        except Exception as e:
            print(f"  WARN: {spec['title']} {dvar}: {e}")
            continue
        out.append((spec, m))
    return out


def write_reg_table(dvar: str, def_label: str, fname: str):
    results = run_regs(dvar)
    if not results:
        return
    ncols = len(results)
    lines = []
    lines.append(rf"\begin{{tabular}}{{l{'c'*ncols}}} \hline")
    lines.append(" & " + " & ".join(f"({i+1})" for i in range(ncols)) + r" \\")
    lines.append("VARIABLES & " + " & ".join(s["title"] for s, _ in results) + r" \\ \hline")
    lines.append(" & " + " & ".join(" " for _ in results) + r" \\")
    for label, varname in COEF_LABELS:
        row_b, row_se = [], []
        for spec, m in results:
            b, se, p = _g(m, varname)
            if b is None:
                row_b.append("");  row_se.append("")
            else:
                row_b.append(f"{b:.4f}{stars(p)}");  row_se.append(f"({se:.4f})")
        lines.append(f"{label} & " + " & ".join(row_b) + r" \\")
        lines.append(" & "          + " & ".join(row_se) + r" \\")
    # Constant row (Intercept present only in the no-FE columns)
    row_b, row_se = [], []
    for spec, m in results:
        b, se, p = _g(m, "Intercept")
        if b is None:
            row_b.append("");  row_se.append("")
        else:
            row_b.append(f"{b:.4f}{stars(p)}");  row_se.append(f"({se:.4f})")
    lines.append("Constant & " + " & ".join(row_b) + r" \\")
    lines.append(" & "         + " & ".join(row_se) + r" \\")
    lines.append(" & " + " & ".join(" " for _ in results) + r" \\")
    # N, R2
    lines.append("Observations & " + " & ".join(f"{int(m._N)}" for _, m in results) + r" \\")
    lines.append("R-squared & "    + " & ".join(f"{float(getattr(m, '_r2', float('nan'))):.4f}" for _, m in results) + r" \\")
    lines.append("HS section FE & " + " & ".join("Yes" if spec["fe"] else "No" for spec, _ in results) + r" \\")
    lines.append("Weights & " + " & ".join("Trade value" for _ in results) + r" \\")
    lines.append("SE & " + " & ".join("Robust (HC1)" for _ in results) + r" \\")
    lines.append(r"\hline")
    lines.append(rf"\multicolumn{{{ncols+1}}}{{c}}{{ Robust standard errors in parentheses; HS6 cross-section; weighted by total trade value }} \\")
    lines.append(rf"\multicolumn{{{ncols+1}}}{{c}}{{ *** p$<$0.01, ** p$<$0.05, * p$<$0.1 }} \\")
    lines.append(r"\end{tabular}")
    p = R_SF3 / f"{fname}.tex"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    import shutil
    shutil.copy2(p, OL_R_SF3 / f"{fname}.tex")
    # Print summary to console
    print(f"\n  --- {def_label} ---")
    for i, (spec, m) in enumerate(results, 1):
        b_pci, se_pci, p_pci = _g(m, "complexity")
        r2 = float(getattr(m, "_r2", float("nan")))
        print(f"    ({i}) {spec['title']:18s}  PCI = {b_pci:+.4f} ({se_pci:.4f}) p={p_pci:.3f}  R2={r2:.3f}  N={int(m._N)}")


for def_ in DEFS:
    write_reg_table(f"sh_{def_}", DEF_LABEL[def_], f"reg_sf3_{def_}")


# ---------------------------------------------------------------------
# DONE
# ---------------------------------------------------------------------
print(f"\n>>> SF3 outputs written:")
print(f"    Figures      -> {G_SF3}")
print(f"    Tables       -> {T_SF3}")
print(f"    Regressions  -> {R_SF3}")
print(f"    Overleaf     -> {OVERLEAF_SF}")
