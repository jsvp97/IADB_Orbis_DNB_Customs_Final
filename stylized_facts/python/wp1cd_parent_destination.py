"""
wp1cd_parent_destination.py  --  Volpe items 1c and 1d
=======================================================

Two-way tables of the multinational's HOME country (rows) against the EXPORT DESTINATION
(columns), in value and in percent -- first by region, then by country -- and the same
matrix as a heat map. "Beyond the regression, he wants to see the tables."

Rows also include the two comparison groups the document uses: domestic MNEs and local
(unmatched) exporters, so the destination mix of foreign affiliates can be read against
them (this is the visual counterpart of src/10's T3 and of theta by destination).

Data: the parent cube (origin x dest x HS6 x year x parent), pooled over years and
products; scope "all" and "agro". Parent = recorded iso3_parent (the document's
convention); a non-conduit-owner variant is in src/11-12 and can be plugged in later.

Outputs (output/wp/<scope>/):
  Tables/tab_wp1c_region_value.tex     parent region x destination region, $bn
  Tables/tab_wp1c_region_rowpct.tex    row %: where each parent region's LAC exports go
  Tables/tab_wp1c_region_colpct.tex    column %: who supplies each destination region
  Tables/tab_wp1c_country_value.tex    top parents x top destinations, $bn (+ Other, Total)
  Tables/tab_wp1c_country_rowpct.tex   row %
  Tables/tab_wp1c_country_colpct.tex   column %
  Tables/tab_wp1c_byorigin_<ISO>.tex   region x region row % for each LAC origin
  Graphs/fig_wp1d_heatmap_country_rowpct   heat map, top parents x top destinations, row %
  Graphs/fig_wp1d_heatmap_country_cellpct  heat map, cell share of all foreign-MNE exports
  Graphs/fig_wp1d_heatmap_region_rowpct    heat map, regions
  Graphs/fig_wp1d_home_share_by_parent     share of each parent's LAC exports shipped to its own country
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_common as W  # noqa: E402

SCOPES = ["all", "agro"]
TOP_TAB = 10    # parents/destinations shown in the two-way TABLES
TOP_MAP = 15    # parents/destinations shown in the HEAT MAPS


def region_rows(d: pd.DataFrame) -> pd.Series:
    """Row label: parent REGION for foreign MNEs (known parent); fixed labels otherwise."""
    lab = pd.Series("", index=d.index, dtype="object")
    ext = d["owner_type"] == "ext"
    lab[ext] = d.loc[ext, "iso3_parent"].map(W.classify_region)
    lab[d["owner_type"] == "ext_unknown"] = "Foreign MNE, parent unknown"
    lab[d["owner_type"] == "dom"] = "Domestic MNEs"
    lab[d["owner_type"] == "local"] = "Local firms (unmatched)"
    return lab


ROW_ORDER = W.REGION_ORDER + ["Foreign MNE, parent unknown", "Domestic MNEs", "Local firms (unmatched)"]


def two_way(d: pd.DataFrame, row: pd.Series, col: pd.Series, row_order=None, col_order=None):
    mat = pd.crosstab(row, col, values=d["value"], aggfunc="sum").fillna(0.0)
    if row_order: mat = mat.reindex([r for r in row_order if r in mat.index])
    if col_order: mat = mat.reindex(columns=[c for c in col_order if c in mat.columns])
    return mat


def write_three(mat: pd.DataFrame, T: Path, stem: str, corner: str, note: str) -> None:
    rt, ct = mat.sum(axis=1), mat.sum(axis=0)
    W.write_matrix_tex(mat / 1e9, T / f"tab_{stem}_value.tex", fmt="{:,.1f}", corner=corner,
                       row_total=rt / 1e9, col_total=ct / 1e9, note="Export value, USD bn. " + note)
    W.write_matrix_tex(100 * mat.div(rt, axis=0), T / f"tab_{stem}_rowpct.tex", fmt="{:.1f}", corner=corner,
                       row_total=pd.Series(100.0, index=mat.index), note="Row percentages: destination mix of each row group. " + note)
    W.write_matrix_tex(100 * mat.div(ct, axis=1), T / f"tab_{stem}_colpct.tex", fmt="{:.1f}", corner=corner,
                       col_total=pd.Series(100.0, index=mat.columns), note="Column percentages: who supplies each destination. " + note)


def run_scope(cube: pd.DataFrame, scope: str) -> None:
    G, T, R = W.outdirs(scope)
    d = W.scope_filter(W.mne_flags(cube), scope)
    d = d[d["value"] > 0].copy()
    d["dest_region"] = d["country_dest"].map(W.classify_region)
    d["row_region"] = region_rows(d)
    note = ("Pooled 2006--2022, nine LAC origins (Ecuador excluded), all destinations. Parent = country of the "
            "multinational's ultimate parent as recorded (Orbis/D\\&B).")
    note_region = note + " Rows for domestic MNEs and local exporters are given for comparison."
    print(f"\n=== scope {scope}: ${d['value'].sum() / 1e9:,.1f} bn")

    # --- 1c region x region (all rows) -------------------------------------------------------
    mat_r = two_way(d, d["row_region"], d["dest_region"], ROW_ORDER, W.REGION_ORDER)
    write_three(mat_r, T, "wp1c_region", "Parent region / Destination region", note_region)
    rowpct_r = 100 * mat_r.div(mat_r.sum(axis=1), axis=0)
    W.heatmap(rowpct_r, "fig_wp1d_heatmap_region_rowpct", G, cbar_label="% of the row group's export value",
              fmt="{:.0f}", vmin=0, vmax=100, xlabel="destination region", ylabel="parent region of the exporter")
    print("   region row%:\n" + rowpct_r.round(0).to_string())

    # --- 1c country x country: top-10 parents x top-10 destinations (+ Other, Total) ---------------
    ext = d[d["owner_type"] == "ext"]
    tp = ext.groupby("iso3_parent")["value"].sum().sort_values(ascending=False)
    td = ext.groupby("country_dest")["value"].sum().sort_values(ascending=False)

    def country_matrix(k):
        top_p, top_d = list(tp.index[:k]), list(td.index[:k])
        prow = ext["iso3_parent"].where(ext["iso3_parent"].isin(top_p), "Other parents")
        dcol = ext["country_dest"].where(ext["country_dest"].isin(top_d), "Other destinations")
        return top_p, top_d, two_way(ext, prow, dcol, top_p + ["Other parents"], top_d + ["Other destinations"])

    top_p, top_d, mat_c = country_matrix(TOP_TAB)
    write_three(mat_c, T, "wp1c_country", "Parent / Destination",
                f"Foreign MNEs with a recorded parent country; top {TOP_TAB} parents and top {TOP_TAB} destinations by foreign-MNE export value. " + note)
    # heat maps on the 15 x 15 version
    top_p, top_d, mat_m = country_matrix(TOP_MAP)
    core = mat_m.loc[top_p, top_d]
    rowpct_c = 100 * core.div(mat_m.loc[top_p].sum(axis=1), axis=0)
    W.heatmap(rowpct_c, "fig_wp1d_heatmap_country_rowpct", G,
              cbar_label="% of the parent's LAC export value going to the destination", fmt="{:.0f}", vmin=0,
              xlabel="destination country", ylabel="parent country of the MNE")
    cellpct = 100 * core / mat_m.values.sum()
    W.heatmap(cellpct, "fig_wp1d_heatmap_country_cellpct", G,
              cbar_label="% of all foreign-MNE export value", fmt="{:.1f}", vmin=0, cmap="Blues",
              xlabel="destination country", ylabel="parent country of the MNE", annotate_thresh=0.05)

    # --- 1d companion: share shipped to the parent's own country, by parent -----------------
    home = ext.assign(home=(ext["country_dest"] == ext["iso3_parent"]).astype(int) * ext["value"])
    hs = home.groupby("iso3_parent").agg(value=("value", "sum"), home=("home", "sum"))
    hs = hs.loc[top_p]; hs["share"] = hs["home"] / hs["value"]
    fig, ax = plt.subplots(figsize=(8, 5.5))
    y = np.arange(len(hs))[::-1]
    ax.barh(y, hs["share"], color=W.C_MNE_EXT)
    for yi, (i, r) in zip(y, hs.iterrows()):
        ax.text(r["share"] + 0.005, yi, f"{r['share'] * 100:.1f}%  (${r['value'] / 1e9:,.0f}bn)", va="center", fontsize=8)
    ax.set_yticks(y); ax.set_yticklabels(hs.index)
    ax.set_xlim(0, max(0.5, hs["share"].max() * 1.35))
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v * 100:.0f}%"))
    ax.set_xlabel("share of the parent's LAC export value shipped to the parent's own country")
    W.savefig(fig, "fig_wp1d_home_share_by_parent", G)
    overall_home = home["home"].sum() / home["value"].sum()
    print(f"   share to parent's own country, all known-parent foreign MNEs: {overall_home:.3f}")
    print("   by parent: " + ", ".join(f"{i} {r['share']:.2f}" for i, r in hs.head(8).iterrows()))

    # --- by-origin region tables (one per LAC origin) -----------------------------------------
    for o in sorted(d["country_orig"].unique()):
        dd = d[d["country_orig"] == o]
        m = two_way(dd, dd["row_region"], dd["dest_region"], ROW_ORDER, W.REGION_ORDER)
        W.write_matrix_tex(100 * m.div(m.sum(axis=1), axis=0), T / f"tab_wp1c_byorigin_{o}.tex", fmt="{:.1f}",
                           corner=f"{o}: parent region \\ destination", row_total=m.sum(axis=1) / 1e9,
                           note=f"Exports from {o}; row percentages; last column = row total in USD bn. " + note)
    # compact origin x destination-region for foreign MNEs vs locals (for the text)
    for grp, sel in (("foreign", d["owner_type"].isin(["ext", "ext_unknown"])), ("local", d["owner_type"] == "local")):
        m = two_way(d[sel], d.loc[sel, "country_orig"], d.loc[sel, "dest_region"], None, W.REGION_ORDER)
        W.write_matrix_tex(100 * m.div(m.sum(axis=1), axis=0), T / f"tab_wp1c_origin_x_destregion_{grp}.tex", fmt="{:.1f}",
                           corner="Origin \\ Destination region", row_total=m.sum(axis=1) / 1e9,
                           note=f"{'Foreign-MNE' if grp == 'foreign' else 'Local (unmatched) firms'} exports; row percentages; last column = row total, USD bn.")


def main():
    cube = W.build_cube()
    for scope in SCOPES:
        run_scope(cube, scope)
    print("\n>>> wp1cd done")


if __name__ == "__main__":
    main()
