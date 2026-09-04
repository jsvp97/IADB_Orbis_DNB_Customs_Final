"""
sf_explore_dest_by_origin.py
============================

Exploration: MNE_total value share by destination characteristic,
conditional on origin. Heatmaps with origin on the y-axis and the
destination category on the x-axis; colour = MNE_total share, value
annotated in each cell.

Cuts:
  H1. origin x destination income group
  H2. origin x destination region
  H3. origin x intra/extra-regional
  H4. origin x distance quintile
  H5. origin x FTA / WTO link
  H6. origin x contiguous

Uses the parquet cache built by sf_explore_dest.py.
Outputs (local only, exploration):
  2_Output/Graphs/Exploration_Dest/expl_byorig_<cut>.{pdf,png,eps}
  2_Output/Tables/Exploration_Dest/expl_byorig_<cut>.tex   (matrix form)
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
    ensure_dir, save_figure,
)

# ---------------------------------------------------------------------
# Output paths
# ---------------------------------------------------------------------
G_EXPL = GRAPHS / "Exploration_Dest"
T_EXPL = TABLES / "Exploration_Dest"
for d in (G_EXPL, T_EXPL):
    ensure_dir(d)

CACHE = INT / "ody_value_cache.parquet"
assert CACHE.exists(), f"Run sf_explore_dest.py first to build {CACHE}"

# ---------------------------------------------------------------------
# Load + filter
# ---------------------------------------------------------------------
df = pd.read_parquet(CACHE)
df = df[~df["country_orig"].isin(EXCLUDED_ORIGINS)].copy()
df = df[(df["total_value"] > 0) & df["country_dest"].notna()].copy()

print(f">>> Loaded {len(df):,} ODY rows, {df['country_dest'].nunique()} dest, "
      f"{df['country_orig'].nunique()} origins")


# ---------------------------------------------------------------------
# Heatmap helper
# ---------------------------------------------------------------------
INCOME_LABEL = {1: "Low", 2: "Lower-middle", 3: "Upper-middle", 4: "High"}
INTRA_LABEL  = {0: "Extra-regional", 1: "Intra-regional"}
CONTIG_LABEL = {0: "Non-contiguous", 1: "Contiguous"}
FTA_LABEL    = {0: "No FTA / WTO", 1: "FTA / WTO"}
DIST_LABEL   = {1: "Q1 (closest)", 2: "Q2", 3: "Q3", 4: "Q4", 5: "Q5 (farthest)"}


def heatmap(category_col: str, fname: str, cat_label: dict | None = None,
            column_order: list | None = None, *, vmin: float = 0.30,
            vmax: float = 0.85) -> pd.DataFrame:
    d = df.dropna(subset=[category_col]).copy()
    g = (d.groupby(["country_orig", category_col], as_index=False)
           .agg(total_value=("total_value", "sum"),
                val_total=("val_total", "sum")))
    g["share"] = g["val_total"] / g["total_value"]

    mat = g.pivot(index="country_orig", columns=category_col, values="share")
    if column_order is not None:
        mat = mat.reindex(columns=column_order)

    # Display labels
    if cat_label:
        mat.columns = [cat_label.get(c, str(c)) for c in mat.columns]

    # Sort origins by overall MNE share (descending) for readability
    overall = (df.groupby("country_orig")
                 .apply(lambda x: x["val_total"].sum() / x["total_value"].sum(),
                        include_groups=False)
                 .sort_values(ascending=False))
    mat = mat.reindex(overall.index)

    # ---- Plot ----
    fig, ax = plt.subplots(figsize=(max(5, 0.8 * mat.shape[1] + 2),
                                    max(4, 0.45 * mat.shape[0] + 1.5)))
    im = ax.imshow(mat.values, aspect="auto", cmap="Greens",
                   vmin=vmin, vmax=vmax)
    ax.set_xticks(range(mat.shape[1]))
    ax.set_xticklabels(mat.columns, rotation=30, ha="right")
    ax.set_yticks(range(mat.shape[0]))
    ax.set_yticklabels(mat.index)
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            v = mat.values[i, j]
            if np.isnan(v):
                ax.text(j, i, "—", ha="center", va="center", fontsize=9, color="gray")
            else:
                # White text on dark cells, black on light
                color = "white" if v > (vmin + vmax) / 2 else "black"
                ax.text(j, i, f"{v:.2f}", ha="center", va="center",
                        fontsize=9, color=color)
    cbar = plt.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("MNE-total share (value)", fontsize=9)
    save_figure(fig, fname, G_EXPL)

    # Write matrix as a small TeX table too
    mat_out = mat.copy()
    mat_out = mat_out.map(lambda v: "—" if pd.isna(v) else f"{v:.3f}")
    cols = " & ".join([""] + list(mat_out.columns))
    lines = [r"\begin{tabular}{l" + "c" * mat.shape[1] + r"}",
             r"\toprule",
             cols + r" \\",
             r"\midrule"]
    for orig, row in mat_out.iterrows():
        lines.append(orig + " & " + " & ".join(row.tolist()) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (T_EXPL / f"{fname}.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"  {fname:40s} -> {mat.shape[0]}x{mat.shape[1]} cells")
    return mat


# ---------------------------------------------------------------------
# Heatmaps
# ---------------------------------------------------------------------
print("\n>>> Heatmaps:")

heatmap("income_group_dest", "expl_byorig_income_group",
        cat_label=INCOME_LABEL, column_order=[1, 2, 3, 4])

heatmap("dest_region", "expl_byorig_region")

heatmap("intra_regional", "expl_byorig_intra_regional",
        cat_label=INTRA_LABEL, column_order=[0, 1])

heatmap("dist_quintile", "expl_byorig_dist_quintile",
        cat_label=DIST_LABEL, column_order=[1, 2, 3, 4, 5])

heatmap("fta_wto", "expl_byorig_fta",
        cat_label=FTA_LABEL, column_order=[0, 1])

heatmap("contig", "expl_byorig_contig",
        cat_label=CONTIG_LABEL, column_order=[0, 1])


# ---------------------------------------------------------------------
# Range summary: within-origin range vs cross-origin range per cut
# ---------------------------------------------------------------------
print("\n>>> Within-origin vs cross-origin spread per cut:")
cuts = [
    ("income_group_dest", "Income group"),
    ("dest_region",       "Region"),
    ("intra_regional",    "Intra/extra"),
    ("dist_quintile",     "Dist quintile"),
    ("fta_wto",           "FTA"),
    ("contig",            "Contig"),
]
print(f"  {'cut':16s}  {'avg within-orig range':>22s}  {'cross-orig range':>20s}")
for col, lbl in cuts:
    d = df.dropna(subset=[col]).copy()
    g = (d.groupby(["country_orig", col])
           .apply(lambda x: x["val_total"].sum() / x["total_value"].sum(),
                  include_groups=False)
           .reset_index(name="share"))
    within = g.groupby("country_orig")["share"].agg(lambda x: x.max() - x.min()).mean()
    # Cross-origin range of overall shares
    overall = (df.groupby("country_orig")
                 .apply(lambda x: x["val_total"].sum() / x["total_value"].sum(),
                        include_groups=False))
    cross = overall.max() - overall.min()
    print(f"  {lbl:16s}  {within:>22.3f}  {cross:>20.3f}")


print(f"\n>>> Done. Outputs in {G_EXPL}")
