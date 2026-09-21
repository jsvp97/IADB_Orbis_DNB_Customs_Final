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

SCOPES = W.SCOPES_ALL
TOP_TAB = 10    # parents/destinations shown in the two-way TABLES
TOP_MAP = 15    # parents/destinations shown in the HEAT MAPS


def region_rows(d: pd.DataFrame) -> pd.Series:
    """Row label: parent REGION for foreign MNEs (known parent); fixed labels otherwise."""
    lab = pd.Series("", index=d.index, dtype="object")
    ext = d["owner_type"] == "ext"
    lab[ext] = d.loc[ext, "iso3_parent"].map(W.classify_region)
    lab[d["owner_type"] == "ext_unknown"] = "Foreign MNE, parent country not recorded"
    lab[d["owner_type"] == "dom"] = "Domestic MNEs"
    lab[d["owner_type"] == "local"] = "Local firms (unmatched)"
    return lab


ROW_ORDER = W.REGION_ORDER + ["Foreign MNE, parent country not recorded", "Domestic MNEs", "Local firms (unmatched)"]


def two_way(d: pd.DataFrame, row: pd.Series, col: pd.Series, row_order=None, col_order=None, value: str = "value"):
    mat = pd.crosstab(row, col, values=d[value], aggfunc="sum").fillna(0.0)
    if row_order: mat = mat.reindex([r for r in row_order if r in mat.index])
    if col_order: mat = mat.reindex(columns=[c for c in col_order if c in mat.columns])
    return mat


def write_three(mat: pd.DataFrame, T: Path, stem: str, corner: str, note: str, mat_yr: pd.DataFrame | None = None) -> None:
    rt, ct = mat.sum(axis=1), mat.sum(axis=0)
    my = mat_yr.reindex(index=mat.index, columns=mat.columns).fillna(0.0) if mat_yr is not None else mat
    W.write_matrix_tex(my / 1e9, T / f"tab_{stem}_value.tex", fmt="{:,.1f}", corner=corner,
                       row_total=my.sum(axis=1) / 1e9, col_total=my.sum(axis=0) / 1e9, note=f"Export value, USD bn per year. {W.VAL_NOTE} " + note)
    W.write_matrix_tex(100 * mat.div(rt, axis=0), T / f"tab_{stem}_rowpct.tex", fmt="{:.1f}", corner=corner,
                       row_total=pd.Series(100.0, index=mat.index), note="Row percentages: destination mix of each row group. " + note)
    W.write_matrix_tex(100 * mat.div(ct, axis=1), T / f"tab_{stem}_colpct.tex", fmt="{:.1f}", corner=corner,
                       col_total=pd.Series(100.0, index=mat.columns), note="Column percentages: who supplies each destination. " + note)


def home_share_figure(ext: pd.DataFrame, parents: list, fname: str, G: Path, origin_label: str, parent_col: str = "iso3_parent",
                      home_flag: pd.Series | None = None) -> pd.DataFrame:
    """Bars = share of each parent's exports shipped to the parent's own country. No dollar values on the figure
    (revision 7); `home_flag` lets the caller define `home` for consolidated parents."""
    hf = home_flag if home_flag is not None else (ext["country_dest"] == ext[parent_col])
    home = ext.assign(home=hf.astype(int) * ext["value"])
    hs = home.groupby(parent_col).agg(value=("value", "sum"), home=("home", "sum"))
    hs = hs.reindex([p for p in parents if p in hs.index]); hs["share"] = hs["home"] / hs["value"]
    fig, ax = plt.subplots(figsize=(8, 5.5))
    y = np.arange(len(hs))[::-1]
    ax.barh(y, hs["share"], color=W.C_MNE_EXT)
    for yi, (i, r) in zip(y, hs.iterrows()):
        ax.text(r["share"] + 0.005, yi, f"{r['share'] * 100:.1f}%", va="center", fontsize=9)
    ax.set_yticks(y); ax.set_yticklabels(hs.index, fontsize=9)
    ax.set_xlim(0, max(0.5, float(hs["share"].max()) * 1.2 if len(hs) else 0.5))
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v * 100:.0f}%"))
    ax.set_xlabel(f"share of the parent's export value from {origin_label} shipped to the parent's own country")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    W.savefig(fig, fname, G)
    return home


def home_share_consolidated(ext: pd.DataFrame, G: Path, T: Path, k: int = TOP_TAB) -> None:
    """Revision 7: the home-share figure with parents CONSOLIDATED -- dependencies folded into their sovereign
    (Bermuda, Cayman, BVI, Jersey ... -> GBR; Curacao, Aruba -> NLD; Puerto Rico -> USA; Hong Kong, Macao -> CHN) and the
    stand-alone havens / conduits (LIE, CHE, LUX, PAN, BHS, ...) pooled into one group whose `home' is any of them."""
    e = ext.assign(pc=W.consolidate_parent(ext["iso3_parent"]))
    dest_c = W.consolidate_parent(e["country_dest"])
    home = e["pc"] == dest_c
    top = list(e.groupby("pc")["value"].sum().sort_values(ascending=False).index[:k])
    if W.HAVEN_GROUP_LABEL not in top:
        top.append(W.HAVEN_GROUP_LABEL)
    h = home_share_figure(e, top, "fig_wp1d_home_share_by_parent_consolidated", G, "LAC", parent_col="pc", home_flag=home)
    hs = h.groupby("pc").agg(value=("value", "sum"), value_yr=("value_yr", "sum"), home=("home", "sum")).reindex(top)
    hs["share"] = 100 * hs["home"] / hs["value"]
    lines = [r"\begin{tabular}{lrr}", r"\toprule", rf"Consolidated parent & Home share (\%) & Exports ({W.VAL_HDR}) \\", r"\midrule"]
    for p, r in hs.iterrows():
        lines.append(f"{W.tex_escape(p)} & {r['share']:.1f} & {r['value_yr'] / 1e9:,.1f} \\\\")
    dep = ", ".join(f"{c}$\\to${s}" for c, s in sorted(W.HAVEN_SOVEREIGN.items(), key=lambda x: (x[1], x[0])))
    lines += [r"\bottomrule", rf"\multicolumn{{3}}{{p{{0.95\textwidth}}}}{{\footnotesize Parents consolidated: dependencies and overseas territories folded into their sovereign ({dep}); "
              rf"the stand-alone tax havens and conduit jurisdictions ({', '.join(sorted(W.HAVEN_STANDALONE))}) pooled into `{W.tex_escape(W.HAVEN_GROUP_LABEL)}', whose home shipments are those to any of them. {W.VAL_NOTE}}} \\", r"\end{tabular}"]
    W.write_tex(lines, T / "tab_wp1d_home_share_by_parent_consolidated.tex")
    print("   consolidated home shares: " + ", ".join(f"{p} {r['share']:.1f}%" for p, r in hs.head(8).iterrows()))


def home_share_haven_panels(ext: pd.DataFrame, G: Path, T: Path, k: int = TOP_TAB) -> None:
    """Revision 8 (Volpe): Panel A = the ten largest NON-haven parents (dependencies folded into their sovereign),
    Panel B = the ten largest tax-haven / conduit jurisdictions as recorded, each with its own home share (shipments
    to that jurisdiction)."""
    sov = ext["iso3_parent"].map(W.HAVEN_SOVEREIGN).fillna(ext["iso3_parent"])
    is_haven = ext["iso3_parent"].isin(W.HAVEN_STANDALONE) | ext["iso3_parent"].isin(W.HAVEN_SOVEREIGN)
    e = ext.assign(pc=sov, dest_c=ext["country_dest"].map(W.HAVEN_SOVEREIGN).fillna(ext["country_dest"]), haven=is_haven)
    a = e[~e["haven"]]; b = e[e["haven"]]
    top_a = list(a.groupby("pc")["value"].sum().sort_values(ascending=False).index[:k])
    top_b = list(b.groupby("iso3_parent")["value"].sum().sort_values(ascending=False).index[:k])
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2))
    rows = []
    for ax, (dd, col, home_col, top, title) in zip(axes, ((a, "pc", "dest_c", top_a, "Panel A. Ten largest parent countries (not tax havens)"),
                                                          (b, "iso3_parent", "country_dest", top_b, "Panel B. Ten largest tax-haven and conduit jurisdictions"))):
        h = dd.assign(home=(dd[home_col] == dd[col]).astype(int) * dd["value"])
        hs = h.groupby(col).agg(value=("value", "sum"), value_yr=("value_yr", "sum"), home=("home", "sum")).reindex(top)
        hs["share"] = 100 * hs["home"] / hs["value"]
        y = np.arange(len(hs))[::-1]
        ax.barh(y, hs["share"], color=W.C_MNE_EXT)
        for yi, (i, r) in zip(y, hs.iterrows()):
            ax.text(r["share"] + 0.4, yi, f"{r['share']:.1f}%", va="center", fontsize=10)
        ax.set_yticks(y); ax.set_yticklabels(hs.index, fontsize=11); ax.tick_params(axis="x", labelsize=10)
        ax.set_xlim(0, max(30, float(hs["share"].max()) * 1.25)); ax.set_title(title, fontsize=12)
        ax.set_xlabel("% of the parent's LAC exports shipped to the parent's own jurisdiction", fontsize=10)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        rows.append(hs.assign(panel=title[:7]))
    fig.tight_layout()
    W.savefig(fig, "fig_wp1d_home_share_haven_panels", G)
    lines = [r"\begin{tabular}{llrr}", r"\toprule", rf"Panel & Parent & Home share (\%) & Exports ({W.VAL_HDR}) \\", r"\midrule"]
    for hs in rows:
        for p, r in hs.iterrows():
            lines.append(f"{r['panel']} & {W.tex_escape(p)} & {r['share']:.1f} & {r['value_yr'] / 1e9:,.1f} \\\\")
        lines.append(r"\midrule")
    dep = ", ".join(f"{c}$\\to${s}" for c, s in sorted(W.HAVEN_SOVEREIGN.items(), key=lambda x: (x[1], x[0])))
    lines[-1] = r"\bottomrule"
    lines += [rf"\multicolumn{{4}}{{p{{0.95\textwidth}}}}{{\footnotesize Panel A: parents that are not tax havens, with dependencies and overseas territories folded into their sovereign ({dep}). "
              rf"Panel B: the tax-haven and conduit jurisdictions as recorded ({', '.join(sorted(W.HAVEN_STANDALONE))} and the dependencies above), each with its own home share. {W.VAL_NOTE}}} \\", r"\end{tabular}"]
    W.write_tex(lines, T / "tab_wp1d_home_share_haven_panels.tex")
    print("   haven panels: A " + ", ".join(f"{p} {r['share']:.1f}" for p, r in rows[0].iterrows()) + " | B " + ", ".join(f"{p} {r['share']:.1f}" for p, r in rows[1].iterrows()))


def parent_x_parentdest(ext: pd.DataFrame, top_p: list, T: Path, note: str) -> None:
    """Revision 7: top-10 parents x the SAME ten countries as destinations (row %), so the diagonal is the home share."""
    dcol = ext["country_dest"].where(ext["country_dest"].isin(top_p), "Other destinations")
    prow = ext["iso3_parent"].where(ext["iso3_parent"].isin(top_p), "Other parents")
    mat = two_way(ext, prow, dcol, top_p + ["Other parents"], top_p + ["Other destinations"])
    W.write_matrix_tex(100 * mat.div(mat.sum(axis=1), axis=0), T / "tab_wp1c_parent_x_parentdest_rowpct.tex", fmt="{:.1f}",
                       corner="Parent / Destination", row_total=pd.Series(100.0, index=mat.index),
                       note="Row percentages: destination mix of each parent's exports, with the ten parent countries themselves as the destination columns, so the diagonal is the share shipped to the parent's own country. " + note)


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
    write_three(mat_r, T, "wp1c_region", "Parent region / Destination region", note_region,
                mat_yr=two_way(d, d["row_region"], d["dest_region"], ROW_ORDER, W.REGION_ORDER, value="value_yr"))
    rowpct_r = 100 * mat_r.div(mat_r.sum(axis=1), axis=0)
    W.heatmap(rowpct_r, "fig_wp1d_heatmap_region_rowpct", G, cbar_label="% of the row group's export value",
              fmt="{:.0f}", vmin=0, vmax=100, xlabel="destination region", ylabel="parent region of the exporter")
    print("   region row%:\n" + rowpct_r.round(0).to_string())

    # --- 1c country x country: top-10 parents x top-10 destinations (+ Other, Total) ---------------
    ext = d[d["owner_type"] == "ext"]
    tp = ext.groupby("iso3_parent")["value"].sum().sort_values(ascending=False)
    td = ext.groupby("country_dest")["value"].sum().sort_values(ascending=False)

    def country_matrix(k, value="value"):
        top_p, top_d = list(tp.index[:k]), list(td.index[:k])
        prow = ext["iso3_parent"].where(ext["iso3_parent"].isin(top_p), "Other parents")
        dcol = ext["country_dest"].where(ext["country_dest"].isin(top_d), "Other destinations")
        return top_p, top_d, two_way(ext, prow, dcol, top_p + ["Other parents"], top_d + ["Other destinations"], value=value)

    top_p, top_d, mat_c = country_matrix(TOP_TAB)
    write_three(mat_c, T, "wp1c_country", "Parent / Destination",
                f"Foreign MNEs with a recorded parent country; top {TOP_TAB} parents and top {TOP_TAB} destinations by foreign-MNE export value. " + note,
                mat_yr=country_matrix(TOP_TAB, "value_yr")[2])
    parent_x_parentdest(ext, top_p, T, f"Foreign MNEs with a recorded parent country; top {TOP_TAB} parents by foreign-MNE export value. " + note)
    home_share_consolidated(ext, G, T)
    home_share_haven_panels(ext, G, T)
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
    home = home_share_figure(ext, top_p, "fig_wp1d_home_share_by_parent", G, "LAC")
    overall_home = home["home"].sum() / home["value"].sum()

    # --- per-origin versions of the cell-share heat map and the home-share figure (scope all) --
    if scope == "all":
        for o in sorted(ext["country_orig"].unique()):
            e_o = ext[ext["country_orig"] == o]
            tp_o = e_o.groupby("iso3_parent")["value"].sum().sort_values(ascending=False)
            td_o = e_o.groupby("country_dest")["value"].sum().sort_values(ascending=False)
            p_o, d_o = list(tp_o.index[:TOP_MAP]), list(td_o.index[:TOP_MAP])
            m_o = two_way(e_o, e_o["iso3_parent"].where(e_o["iso3_parent"].isin(p_o), "Other"),
                          e_o["country_dest"].where(e_o["country_dest"].isin(d_o), "Other"), p_o + ["Other"], d_o + ["Other"])
            W.heatmap(100 * m_o.loc[p_o, d_o] / m_o.values.sum(), f"fig_wp1d_heatmap_country_cellpct_{o}", G,
                      cbar_label=f"% of all foreign-MNE export value from {o}", fmt="{:.1f}", vmin=0, cmap="Blues",
                      xlabel="destination country", ylabel=f"parent country of the MNE (exports from {o})", annotate_thresh=0.05)
            home_share_figure(e_o, list(tp_o.index[:TOP_TAB]), f"fig_wp1d_home_share_by_parent_{o}", G, o)
    print(f"   share to parent's own country, all known-parent foreign MNEs: {overall_home:.3f}")
    hs_ = home.groupby("iso3_parent").agg(value=("value", "sum"), home=("home", "sum")).reindex(top_p[:8]); hs_["share"] = hs_["home"] / hs_["value"]
    print("   by parent: " + ", ".join(f"{i} {r['share']:.2f}" for i, r in hs_.iterrows()))

    # --- by-origin region tables (one per LAC origin) -----------------------------------------
    for o in sorted(d["country_orig"].unique()):
        dd = d[d["country_orig"] == o]
        m = two_way(dd, dd["row_region"], dd["dest_region"], ROW_ORDER, W.REGION_ORDER)
        my = two_way(dd, dd["row_region"], dd["dest_region"], ROW_ORDER, W.REGION_ORDER, value="value_yr")
        W.write_matrix_tex(100 * m.div(m.sum(axis=1), axis=0), T / f"tab_wp1c_byorigin_{o}.tex", fmt="{:.1f}",
                           corner=f"{o}: parent region \\ destination", row_total=my.sum(axis=1) / 1e9,
                           note=f"Exports from {o}; row percentages; last column = row total in USD bn per year ({W.YEARS_BY_ORIGIN.get(o, '')}). " + note)
    # compact origin x destination-region for foreign MNEs vs locals (for the text)
    for grp, sel in (("foreign", d["owner_type"].isin(["ext", "ext_unknown"])), ("local", d["owner_type"] == "local")):
        m = two_way(d[sel], d.loc[sel, "country_orig"], d.loc[sel, "dest_region"], None, W.REGION_ORDER)
        my = two_way(d[sel], d.loc[sel, "country_orig"], d.loc[sel, "dest_region"], None, W.REGION_ORDER, value="value_yr")
        W.write_matrix_tex(100 * m.div(m.sum(axis=1), axis=0), T / f"tab_wp1c_origin_x_destregion_{grp}.tex", fmt="{:.1f}",
                           corner="Origin \\ Destination region", row_total=my.sum(axis=1) / 1e9,
                           note=f"{'Foreign-MNE' if grp == 'foreign' else 'Local (unmatched) firms'} exports; row percentages; last column = row total, USD bn per year. {W.VAL_NOTE}")


def main():
    cube = W.build_cube()
    for scope in SCOPES:
        run_scope(cube, scope)
    print("\n>>> wp1cd done")


if __name__ == "__main__":
    main()
