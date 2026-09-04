"""
sf_explore_products.py
======================

Exploration (pre-SF2): MNE_total value share across product characteristic cuts.

Builds (one-time) and reuses:
    1_Input/Intermediate/opy_value_cache.parquet  (origin x hs6 x year)

Merges product characteristics from $product:
    upstreamness, sigma, complexity (pci), quality_ladder (ladder), rca, rhci,
    lall2000 category, ipc1 (Lybbert-Zolas)

Cuts:
  1. Above/below median for each continuous characteristic
  2. Decile bars for each continuous characteristic
  3. Bar by HS section (21 sections)
  4. Bar by Lall 2000 technology category
  5. Bar by IPC1 (Lybbert-Zolas) technology section
  6. Scatter MNE_total share vs each continuous characteristic
     (one point per HS6, marker size = trade value)

Outputs (local only, exploration):
  2_Output/Graphs/Exploration_Products/expl_prod_<cut>.{pdf,png,eps}
  2_Output/Tables/Exploration_Products/expl_prod_<cut>.tex
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
    BASE_FILE, PRODUCT, INT, GRAPHS, TABLES, EXCLUDED_ORIGINS,
    C_MNE_TOT, ensure_dir, save_figure, parquet_chunks,
)

G_EXPL = GRAPHS / "Exploration_Products"
T_EXPL = TABLES / "Exploration_Products"
for d in (G_EXPL, T_EXPL):
    ensure_dir(d)

CACHE = INT / "opy_value_cache.parquet"


# ---------------------------------------------------------------------
# Build OPY cache from raw (one-time, ~30 s)
# ---------------------------------------------------------------------
def build_cache() -> pd.DataFrame:
    raw_path = BASE_FILE
    print(f">>> Building OPY cache from {raw_path}")
    t0 = time.time()

    cols = ["country_orig", "hs07_6d", "year", "value_fob",
            "_merge_DNB_Orbis", "iso3_parent"]

    accum: list[pd.DataFrame] = []
    chunk_size = 1_000_000
    total_rows = 0
    for i, chunk in enumerate(parquet_chunks(raw_path, cols, chunk_size), start=1):
        chunk["value_fob"] = chunk["value_fob"].abs()
        mne_total = (chunk["_merge_DNB_Orbis"] == 3)
        mne_dom   = mne_total & (chunk["iso3_parent"] == chunk["country_orig"])
        chunk["val_total"] = chunk["value_fob"] * mne_total
        chunk["val_dom"]   = chunk["value_fob"] * mne_dom
        chunk_agg = (chunk.groupby(["country_orig", "hs07_6d", "year"], as_index=False)
                          .agg(total_value=("value_fob", "sum"),
                               val_total=("val_total", "sum"),
                               val_dom=("val_dom", "sum")))
        accum.append(chunk_agg)
        total_rows += len(chunk)
        print(f"    chunk {i:>3} processed ({total_rows:>12,} rows so far, "
              f"{time.time()-t0:>5.0f}s)")

    df = pd.concat(accum, ignore_index=True)
    df = (df.groupby(["country_orig", "hs07_6d", "year"], as_index=False)
            .sum(numeric_only=True))
    df["val_ext"] = df["val_total"] - df["val_dom"]
    print(f"    final OPY rows: {len(df):,} ({time.time()-t0:.0f}s total)")

    # -- Product chars (hs6-level)
    print("    merging product characteristics...")
    pc, _ = pyreadstat.read_dta(str(PRODUCT / "product_characteristics_hs6_2002_adj.dta"),
                                usecols=["hs07_6d", "upstreamness", "sigma", "pci", "ladder"])
    pc = pc.rename(columns={"pci": "complexity", "ladder": "quality_ladder"})
    df = df.merge(pc, on="hs07_6d", how="left")

    rhci, _ = pyreadstat.read_dta(str(PRODUCT / "UNCTAD RHCI hs_2007_indices.dta"),
                                  usecols=["hs07_6d", "rhci"])
    df = df.merge(rhci, on="hs07_6d", how="left")

    lall, _ = pyreadstat.read_dta(str(PRODUCT / "lall2000_hs2007.dta"),
                                  usecols=["hs07_6d", "lall2000_category"])
    df = df.merge(lall, on="hs07_6d", how="left")

    ipc, _ = pyreadstat.read_dta(str(PRODUCT / "ALP_IPC_Patent_hs2007_6_to_ipc1.dta"),
                                 usecols=["hs07_6d", "ipc1", "probability_weight_ipc1"])
    # Keep highest-probability IPC1 per HS6
    ipc = ipc.sort_values("probability_weight_ipc1", ascending=False).drop_duplicates("hs07_6d")
    df = df.merge(ipc[["hs07_6d", "ipc1"]], on="hs07_6d", how="left")

    # RCA (origin x year x hs6)
    print("    merging RCA (origin x year x hs6)...")
    rca, _ = pyreadstat.read_dta(str(PRODUCT / "RCA_WITS_orig_year.dta"))
    df = df.merge(rca, on=["country_orig", "year", "hs07_6d"], how="left")

    # HS2 chapter + HS section
    df["hs2"] = df["hs07_6d"].astype(str).str.zfill(6).str[:2]
    df["hs2_int"] = pd.to_numeric(df["hs2"], errors="coerce")
    def _hs_section(hs2):
        if pd.isna(hs2): return None
        h = int(hs2)
        bounds = [
            (1,  5,  "I: Live Animals"),
            (6,  14, "II: Vegetable"),
            (15, 15, "III: Fats/Oils"),
            (16, 24, "IV: Food/Bev."),
            (25, 27, "V: Minerals"),
            (28, 38, "VI: Chemicals"),
            (39, 40, "VII: Plastics"),
            (41, 43, "VIII: Leather"),
            (44, 46, "IX: Wood"),
            (47, 49, "X: Pulp/Paper"),
            (50, 63, "XI: Textiles"),
            (64, 67, "XII: Footwear"),
            (68, 70, "XIII: Stone/Glass"),
            (71, 71, "XIV: Prec. Metals"),
            (72, 83, "XV: Base Metals"),
            (84, 85, "XVI: Machinery"),
            (86, 89, "XVII: Transport"),
            (90, 92, "XVIII: Instruments"),
            (93, 93, "XIX: Arms"),
            (94, 96, "XX: Misc. Manuf."),
            (97, 97, "XXI: Art/Antiques"),
        ]
        for lo, hi, lbl in bounds:
            if lo <= h <= hi:
                return lbl
        return None
    df["hs_section"] = df["hs2_int"].map(_hs_section)

    df.to_parquet(CACHE, index=False)
    print(f">>> Cache saved to {CACHE} ({len(df):,} rows)")
    return df


# ---------------------------------------------------------------------
# Load (or build)
# ---------------------------------------------------------------------
if CACHE.exists():
    print(f">>> Loading cached OPY data from {CACHE}")
    df = pd.read_parquet(CACHE)
    print(f"    rows: {len(df):,}")
else:
    df = build_cache()

df = df[~df["country_orig"].isin(EXCLUDED_ORIGINS)].copy()
df = df[(df["total_value"] > 0) & df["hs07_6d"].notna()].copy()
print(f">>> Post-filter rows: {len(df):,}; distinct HS6: {df['hs07_6d'].nunique():,}")


# ---------------------------------------------------------------------
# Collapse to product level (pooled across origins and years, value-weighted)
# ---------------------------------------------------------------------
def collapse_to_hs6() -> pd.DataFrame:
    cols_keep_first = ["upstreamness", "sigma", "complexity", "quality_ladder",
                       "rhci", "lall2000_category", "ipc1", "hs2", "hs_section"]
    g = (df.groupby("hs07_6d", as_index=False)
           .agg(total_value=("total_value", "sum"),
                val_total=("val_total", "sum"),
                val_dom=("val_dom", "sum"),
                **{c: (c, "first") for c in cols_keep_first}))
    g["val_ext"] = g["val_total"] - g["val_dom"]
    g["share_total"] = g["val_total"] / g["total_value"]
    g["share_ext"]   = g["val_ext"]   / g["total_value"]
    g["share_dom"]   = g["val_dom"]   / g["total_value"]
    return g


hs6 = collapse_to_hs6()
print(f">>> HS6-level cross-section: {len(hs6):,} products")


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

CONT_CHARS = [
    ("upstreamness",   "Upstreamness (Antras-Chor)"),
    ("sigma",          "σ (Broda-Weinstein)"),
    ("complexity",     "Product Complexity Index"),
    ("quality_ladder", "Quality ladder (Khandelwal)"),
    ("rhci",           "Revealed Human Capital Intensity"),
]


def value_weighted_share(d: pd.DataFrame, group_col: str) -> pd.DataFrame:
    out = (d.dropna(subset=[group_col])
             .groupby(group_col, as_index=False)
             .agg(total_value=("total_value", "sum"),
                  val_total=("val_total", "sum"),
                  n_hs6=("hs07_6d", "nunique")))
    out["share_total"] = out["val_total"] / out["total_value"]
    return out


def bar_above_below_median(char: str, char_label: str, fname: str) -> None:
    """Compute above/below median across products (value-weighted)."""
    d = hs6.dropna(subset=[char]).copy()
    med = d[char].median()
    d["above_med"] = (d[char] > med).astype(int)
    g = value_weighted_share(d, "above_med")
    g["label"] = g["above_med"].map({0: "Below median", 1: "Above median"})

    fig, ax = plt.subplots(figsize=(6, 3.5))
    g_sorted = g.sort_values("above_med")
    ax.barh(g_sorted["label"], g_sorted["share_total"],
            color=C_MNE_TOT, edgecolor=C_MNE_TOT)
    for y, v in zip(g_sorted["label"], g_sorted["share_total"]):
        ax.text(v + 0.005, y, f"{v:.2f}", va="center", fontsize=9)
    ax.set_xlim(0, 0.9)
    ax.set_xticks(np.arange(0, 0.91, 0.1))
    ax.set_xlabel("MNE-total share in export value")
    ax.set_title(f"{char_label}: median split", fontsize=11)
    save_figure(fig, fname, G_EXPL)

    # Table
    lines = [r"\begin{tabular}{lccr}", r"\toprule",
             rf"{char_label} & MNE$_{{\text{{total}}}}$ share & N HS6 & Total value (\$bn) \\",
             r"\midrule"]
    for _, r in g_sorted.iterrows():
        lines.append(f"{r['label']} & {r['share_total']:.3f} & {int(r['n_hs6']):,} & {r['total_value']/1e9:7.2f} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (T_EXPL / f"{fname}.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def bar_deciles(char: str, char_label: str, fname: str) -> None:
    d = hs6.dropna(subset=[char]).copy()
    d["decile"] = pd.qcut(d[char], 10, labels=False, duplicates="drop") + 1
    g = value_weighted_share(d, "decile")
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(g["decile"].astype(int), g["share_total"],
           color=C_MNE_TOT, edgecolor=C_MNE_TOT, width=0.7)
    for x, v in zip(g["decile"], g["share_total"]):
        ax.text(x, v + 0.01, f"{v:.2f}", ha="center", fontsize=8)
    ax.set_xlabel(f"{char_label} decile (1 = lowest, 10 = highest)")
    ax.set_ylabel("MNE-total share in export value")
    ax.set_xticks(range(1, 11))
    ax.set_ylim(0, 0.9)
    save_figure(fig, fname, G_EXPL)


def scatter_char(char: str, char_label: str, fname: str) -> None:
    d = hs6.dropna(subset=[char]).copy()
    d = d[d["total_value"] > 0]
    sizes = 3 + (d["total_value"] / d["total_value"].max()) * 600
    fig, ax = plt.subplots(figsize=(7.5, 5))
    ax.scatter(d[char], d["share_total"], s=sizes,
               color=C_MNE_TOT, alpha=0.30, edgecolor="none")

    # Value-weighted local mean by bins for a quick smoother
    nb = 20
    edges = np.quantile(d[char], np.linspace(0, 1, nb + 1))
    edges = np.unique(edges)  # robust to ties
    d["_bin"] = pd.cut(d[char], bins=edges, include_lowest=True)
    binned = (d.groupby("_bin", observed=True)
                .apply(lambda x: pd.Series({
                    "x": (x[char] * x["total_value"]).sum() / x["total_value"].sum(),
                    "y": x["val_total"].sum() / x["total_value"].sum(),
                }), include_groups=False)
                .reset_index(drop=True))
    ax.plot(binned["x"], binned["y"], color="black", linewidth=1.6,
            marker="o", markersize=4)

    ax.set_xlabel(char_label)
    ax.set_ylabel("MNE-total share in export value")
    ax.set_ylim(-0.02, 1.05)
    ax.text(0.02, 0.97,
            "Each dot = one HS6 (marker size ~ trade value).\nBlack line = value-weighted mean in 20 bins.",
            transform=ax.transAxes, fontsize=8, va="top", color="gray")
    save_figure(fig, fname, G_EXPL)


def bar_categorical(d: pd.DataFrame, group_col: str, fname: str,
                    title: str | None = None,
                    sort_by_share: bool = True) -> None:
    g = value_weighted_share(d, group_col)
    if sort_by_share:
        g = g.sort_values("share_total", ascending=True)
    fig, ax = plt.subplots(figsize=(9, max(3.5, 0.45 * len(g) + 1.5)))
    ax.barh(g[group_col].astype(str), g["share_total"],
            color=C_MNE_TOT, edgecolor=C_MNE_TOT)
    for y, v in zip(g[group_col].astype(str), g["share_total"]):
        ax.text(v + 0.005, y, f"{v:.2f}", va="center", fontsize=8)
    ax.set_xlim(0, max(0.9, g["share_total"].max() * 1.1))
    ax.set_xlabel("MNE-total share in export value")
    if title:
        ax.set_title(title, fontsize=11)
    save_figure(fig, fname, G_EXPL)

    lines = [r"\begin{tabular}{lccr}", r"\toprule",
             rf"Category & MNE$_{{\text{{total}}}}$ share & N HS6 & Total value (\$bn) \\",
             r"\midrule"]
    for _, r in g.sort_values("share_total", ascending=False).iterrows():
        cat = str(r[group_col]).replace("&", r"\&")
        lines.append(f"{cat} & {r['share_total']:.3f} & {int(r['n_hs6']):,} & {r['total_value']/1e9:7.2f} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (T_EXPL / f"{fname}.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------
# Generate cuts
# ---------------------------------------------------------------------
print("\n>>> Median splits (above vs below) per continuous characteristic:")
for char, lbl in CONT_CHARS:
    bar_above_below_median(char, lbl, f"expl_prod_{char}_median")
    print(f"  expl_prod_{char}_median")

print("\n>>> Decile bars per continuous characteristic:")
for char, lbl in CONT_CHARS:
    bar_deciles(char, lbl, f"expl_prod_{char}_decile")
    print(f"  expl_prod_{char}_decile")

print("\n>>> Scatter MNE share vs each continuous characteristic:")
for char, lbl in CONT_CHARS:
    scatter_char(char, lbl, f"expl_prod_{char}_scatter")
    print(f"  expl_prod_{char}_scatter")

print("\n>>> Categorical cuts:")
bar_categorical(hs6, "hs_section", "expl_prod_hs_section",
                title="MNE_total share by HS section", sort_by_share=True)
print(f"  expl_prod_hs_section")
bar_categorical(hs6, "lall2000_category", "expl_prod_lall2000",
                title="MNE_total share by Lall 2000 technology category",
                sort_by_share=True)
print(f"  expl_prod_lall2000")
bar_categorical(hs6, "ipc1", "expl_prod_ipc1",
                title="MNE_total share by IPC patent section (Lybbert-Zolas)",
                sort_by_share=True)
print(f"  expl_prod_ipc1")


# ---------------------------------------------------------------------
# Bivariate summary: correlations of each char with HS6-level MNE share
# (value-weighted Pearson)
# ---------------------------------------------------------------------
print("\n>>> Value-weighted correlations of MNE_total share with each characteristic:")
print(f"  {'char':18s} {'corr':>7s} {'N HS6':>10s}")
for char, _ in CONT_CHARS:
    d = hs6.dropna(subset=[char])
    if len(d) < 10:
        continue
    w = d["total_value"]
    mx = (d[char] * w).sum() / w.sum()
    my = (d["share_total"] * w).sum() / w.sum()
    cov = ((d[char] - mx) * (d["share_total"] - my) * w).sum() / w.sum()
    vx  = ((d[char] - mx) ** 2 * w).sum() / w.sum()
    vy  = ((d["share_total"] - my) ** 2 * w).sum() / w.sum()
    corr = cov / np.sqrt(vx * vy)
    print(f"  {char:18s} {corr:>+7.3f} {len(d):>10,}")


print(f"\n>>> Done. Outputs in {G_EXPL}")
