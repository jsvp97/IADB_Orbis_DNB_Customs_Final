"""
wp1f_hs6_products.py  --  Volpe item 1f
=======================================

"What happens at the product level: the export share at HS6, with descriptions, so all
of this can be visualised."  HS6 cross-section of the parent cube, with product
descriptions (WITS HS 2007 nomenclature, data/raw/JobID-46_Concordance_H3_to_H2.CSV).

Outputs (output/wp/<scope>/):
  Tables/tab_wp1f_top_hs6_by_value.tex        top 30 HS6 by export value: foreign/domestic/local shares, leading parent
  Tables/tab_wp1f_top_hs6_by_foreign_value.tex top 30 HS6 by foreign-MNE value
  Tables/tab_wp1f_top_hs6_by_foreign_share.tex HS6 (>= $500m) with the highest foreign-MNE share
  Tables/tab_wp1f_top_hs6_by_domestic_share.tex ... highest domestic-MNE share
  Tables/tab_wp1f_top_hs6_<ISO>.tex           top 15 HS6 per origin
  Graphs/fig_wp1f_top20_hs6_stacked            top 20 HS6 by value, stacked local / domestic / foreign
  Graphs/fig_wp1f_top20_hs6_by_parent          same, foreign bar split by parent country
  Graphs/fig_wp1f_foreign_share_distribution   value-weighted distribution of the HS6 foreign share
  Graphs/fig_wp1f_lorenz_foreign               cumulative foreign-MNE value vs cumulative products
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
TOP_N = 30
MIN_VALUE = 5e8


def short(desc, n=58) -> str:
    s = str(desc) if desc is not None and not (isinstance(desc, float) and np.isnan(desc)) else ""
    s = s.replace("&", "and")
    return (s[: n - 1] + "…") if len(s) > n else s


def hs6_table(d: pd.DataFrame, cls: pd.DataFrame, top: list[str]) -> pd.DataFrame:
    d = d.copy()
    d["pgrp"] = W.parent_group(d, top)
    d["n_mne_firms"] = d["n_firms"] * (d["owner_type"] != "local")
    g = d.groupby("hs07_6d", as_index=False).agg(total_value=("value", "sum"), val_ext=("val_ext", "sum"),
                                                   val_dom=("val_dom", "sum"), val_total=("val_total", "sum"),
                                                   n_firms=("n_firms", "sum"), n_mne_firms=("n_mne_firms", "sum"))
    lead = (d[d["owner_type"] == "ext"].groupby(["hs07_6d", "iso3_parent"])["value"].sum().reset_index()
              .sort_values(["hs07_6d", "value"], ascending=[True, False]).drop_duplicates("hs07_6d"))
    lead = lead.rename(columns={"iso3_parent": "lead_parent", "value": "lead_value"})
    g = g.merge(lead, on="hs07_6d", how="left").merge(cls[["hs07_6d", "hs6_desc", "hs2", "sector4"]], on="hs07_6d", how="left")
    g["sh_ext"] = g["val_ext"] / g["total_value"]; g["sh_dom"] = g["val_dom"] / g["total_value"]
    g["sh_local"] = 1 - g["val_total"] / g["total_value"]
    g["lead_share"] = g["lead_value"] / g["val_ext"]
    miss = g["hs6_desc"].isna()
    if miss.any():   # later-revision HS codes and national lines are not in the HS 2007 table
        g.loc[miss, "hs6_desc"] = W.hs6_desc_fallback(g.loc[miss, "hs07_6d"])
    return g, d


def write_hs6_table(g: pd.DataFrame, path: Path, title_note: str, share_of: pd.Series | None = None) -> None:
    """Compact layout: wrapped description column, shares in percent, leading parent code + its share."""
    vfmt = "{:,.2f}" if (len(g) and g["total_value"].max() < 20e9) else "{:,.1f}"   # two decimals when the scope is small (Rest)
    lines = [r"\begin{tabular}{@{}l p{6.4cm} r r r r l@{}}", r"\toprule",
             r"HS6 & Description & \$bn & For. & Dom. & Local & Lead parent \\", r"\midrule"]
    for _, r in g.iterrows():
        lp = f"{r['lead_parent']} ({r['lead_share']:.2f})" if isinstance(r["lead_parent"], str) else "--"
        desc = W.tex_escape(short(r['hs6_desc'], 95)).replace("/", "/\\allowbreak{}")
        lines.append(f"{r['hs07_6d']} & {desc} & {vfmt.format(r['total_value'] / 1e9)} & "
                     f"{100 * r['sh_ext']:.0f} & {100 * r['sh_dom']:.0f} & {100 * r['sh_local']:.0f} & {lp} \\\\")
    lines += [r"\bottomrule",
              rf"\multicolumn{{7}}{{p{{0.97\textwidth}}}}{{\footnotesize {title_note} For./Dom./Local = foreign-MNE, domestic-MNE and "
              r"local-firm shares of the product's export value, percent (pooled 2006--2022, nine LAC origins). Foreign = matched firms whose "
              r"parent is abroad or unknown; Domestic = parent in the exporting country; Local = unmatched. Lead parent = largest parent country "
              r"among the product's foreign MNEs and its share of the product's foreign-MNE value.}} \\",
              r"\end{tabular}"]
    W.write_tex(lines, path)


def run_scope(cube: pd.DataFrame, cls: pd.DataFrame, scope: str) -> None:
    G, T, R = W.outdirs(scope)
    d = W.scope_filter(W.mne_flags(cube), scope)
    d = d[d["value"] > 0]
    top = W.top_parents(d)
    g, d = hs6_table(d, cls, top)
    tot = g["total_value"].sum()
    if len(g) < 25:
        print(f"   [{scope}] too few HS6 products ({len(g)}); skipped"); return
    print(f"\n=== scope {scope}: {len(g):,} HS6, ${tot / 1e9:,.1f} bn")

    # tables ------------------------------------------------------------------------------------
    by_val = g.sort_values("total_value", ascending=False).head(TOP_N)
    write_hs6_table(by_val, T / "tab_wp1f_top_hs6_by_value.tex", f"Top {TOP_N} HS6 products by export value ({by_val['total_value'].sum() / tot:.0%} of the scope's exports).")
    by_ext = g.sort_values("val_ext", ascending=False).head(TOP_N)
    write_hs6_table(by_ext, T / "tab_wp1f_top_hs6_by_foreign_value.tex", f"Top {TOP_N} HS6 products by foreign-MNE export value ({by_ext['val_ext'].sum() / g['val_ext'].sum():.0%} of foreign-MNE exports).")
    big = g[g["total_value"] >= MIN_VALUE]
    write_hs6_table(big.sort_values("sh_ext", ascending=False).head(TOP_N), T / "tab_wp1f_top_hs6_by_foreign_share.tex",
                    f"HS6 products with export value $\\geq$ \\${MIN_VALUE / 1e6:.0f}m ranked by the foreign-MNE share ({len(big):,} products qualify).")
    write_hs6_table(big.sort_values("sh_dom", ascending=False).head(TOP_N), T / "tab_wp1f_top_hs6_by_domestic_share.tex",
                    f"HS6 products with export value $\\geq$ \\${MIN_VALUE / 1e6:.0f}m ranked by the domestic-MNE share.")
    for o in sorted(d["country_orig"].unique()):
        go, _ = hs6_table(d[d["country_orig"] == o], cls, top)
        write_hs6_table(go.sort_values("total_value", ascending=False).head(15), T / f"tab_wp1f_top_hs6_{o}.tex", f"Top 15 HS6 products exported by {o}.")

    # figure: top 20 by value, stacked local / domestic / foreign -------------------------------------
    t20 = g.sort_values("total_value", ascending=False).head(20).iloc[::-1]
    labels = [f"{r['hs07_6d']} {short(r['hs6_desc'], 40)}" for _, r in t20.iterrows()]
    y = np.arange(len(t20))
    fig, ax = plt.subplots(figsize=(9, 9.5))
    ax.barh(y, t20["sh_ext"], color=W.C_MNE_EXT, edgecolor="white", label="Foreign MNEs")
    ax.barh(y, t20["sh_dom"], left=t20["sh_ext"], color=W.C_MNE_DOM, edgecolor="white", label="Domestic MNEs")
    ax.barh(y, t20["sh_local"], left=t20["sh_ext"] + t20["sh_dom"], color="#e8e8e8", edgecolor="white", label="Local firms")
    for yi, r in zip(y, t20.itertuples()):
        if r.sh_ext > 0.06: ax.text(r.sh_ext / 2, yi, f"{r.sh_ext:.2f}", ha="center", va="center", color="white", fontsize=8)
        ax.text(1.01, yi, (f"${r.total_value / 1e9:,.1f}bn" if r.total_value < 20e9 else f"${r.total_value / 1e9:,.0f}bn"), va="center", fontsize=8)
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlim(0, 1.14); ax.set_xlabel("share of the product's export value", fontsize=10)
    ax.legend(frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.07), ncol=3)
    W.savefig(fig, "fig_wp1f_top20_hs6_stacked", G)

    # figure: same 20, foreign split by parent ---------------------------------------------------------
    groups = top + ["Other", "Domestic"]
    sub = d[d["hs07_6d"].isin(t20["hs07_6d"])]
    mat = sub.pivot_table(index="hs07_6d", columns="pgrp", values="value", aggfunc="sum", fill_value=0.0)
    mat = mat.reindex(t20["hs07_6d"]).reindex(columns=[c for c in groups if c in mat.columns], fill_value=0.0)
    mat = mat.div(t20.set_index("hs07_6d")["total_value"], axis=0)
    fig, ax = plt.subplots(figsize=(9, 9.5))
    left = np.zeros(len(mat))
    for i, c in enumerate(mat.columns):
        kw = dict(color=W.parent_color(c, i), edgecolor="white", linewidth=0.5, label={"Other": "Other foreign MNEs", "Domestic": "Domestic MNEs"}.get(c, c))
        if c == "Unknown": kw.update(hatch="///", edgecolor="#6b7a99")
        ax.barh(y, mat[c].values, left=left, **kw); left += mat[c].values
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlim(0, 1.0); ax.set_xlabel("share of the product's export value (remainder = local firms)", fontsize=10)
    ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.07), ncol=4)
    W.savefig(fig, "fig_wp1f_top20_hs6_by_parent", G)

    # distribution of the HS6 foreign share, value-weighted -----------------------------------------------
    bins = np.arange(0, 1.01, 0.1)
    g["bin"] = pd.cut(g["sh_ext"].clip(0, 1), bins, include_lowest=True, labels=[f"{int(b * 100)}–{int((b + .1) * 100)}" for b in bins[:-1]])
    dist = g.groupby("bin", observed=False).agg(value=("total_value", "sum"), n=("hs07_6d", "count"),
                                                 nf=("n_firms", "sum"), nm=("n_mne_firms", "sum"))
    dist["sh_value"] = dist["value"] / tot; dist["sh_n"] = dist["nm"] / dist["nf"].replace(0, np.nan)
    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    x = np.arange(len(dist)); bw = 0.38
    ax.bar(x - bw / 2, dist["sh_value"], bw, color=W.C_MNE_EXT, label="share of export value")
    ax.bar(x + bw / 2, dist["sh_n"], bw, color=W.C_MNE_DOM, label="MNE share of exporting firms in the bin's products")
    for xi, r in zip(x, dist.itertuples()):
        if not np.isnan(r.sh_n): ax.text(xi + bw / 2, r.sh_n + 0.005, f"{r.sh_n:.2f}", ha="center", fontsize=7)
    for xi, r in zip(x, dist.itertuples()):
        ax.text(xi - bw / 2, r.sh_value + 0.005, f"{r.sh_value:.2f}", ha="center", fontsize=7)
    ax.set_xticks(x); ax.set_xticklabels(dist.index, rotation=0, fontsize=8)
    ax.set_xlabel("foreign-MNE share of the product's export value (%)"); ax.set_ylabel("share"); ax.set_ylim(0, max(0.5, float(np.nanmax(dist[["sh_value", "sh_n"]].values)) * 1.15))
    ax.legend(frameon=False, fontsize=9)
    W.savefig(fig, "fig_wp1f_foreign_share_distribution", G)
    above = g.loc[g["sh_ext"] > 0.5, "total_value"].sum() / tot
    print(f"   {above:.0%} of export value is in HS6 products where foreign MNEs hold > 50%; "
          f"top 30 products = {by_val['total_value'].sum() / tot:.0%} of value")
    W.write_matrix_tex(dist[["sh_value", "sh_n", "n"]].rename(columns={"sh_value": "Share of value", "sh_n": "MNE share of exporting firms", "n": "N HS6"}).astype(float),
                       T / "tab_wp1f_foreign_share_distribution.tex", fmt={"Share of value": "{:.3f}", "MNE share of exporting firms": "{:.3f}", "N HS6": "{:,.0f}"}, corner="Foreign share bin (%)",
                       note="MNE share of exporting firms = matched firm-cells (firm x destination x HS6 x year) over all firm-cells in the bin's products.")

    # HS sections by export value (same structure as the HS6 tables) --------------------------------------
    d2 = d.copy(); d2["section"] = W.hs_section_label(d2["hs2"])
    gs = d2.groupby("section").agg(total_value=("value", "sum"), val_ext=("val_ext", "sum"), val_dom=("val_dom", "sum"), val_total=("val_total", "sum"))
    lead = (d2[d2["owner_type"] == "ext"].groupby(["section", "iso3_parent"])["value"].sum().reset_index()
              .sort_values(["section", "value"], ascending=[True, False]).drop_duplicates("section").set_index("section"))
    gs["lead_parent"] = lead["iso3_parent"]; gs["lead_share"] = lead["value"] / gs["val_ext"]
    gs["sh_ext"] = gs["val_ext"] / gs["total_value"]; gs["sh_dom"] = gs["val_dom"] / gs["total_value"]; gs["sh_local"] = 1 - gs["val_total"] / gs["total_value"]
    gs = gs.sort_values("total_value", ascending=False)
    lines = [r"\begin{tabular}{@{}p{7.2cm} r r r r l@{}}", r"\toprule", r"HS section & \$bn & For. & Dom. & Local & Lead parent \\", r"\midrule"]
    for sec, r in gs.iterrows():
        lp = f"{r['lead_parent']} ({r['lead_share']:.2f})" if isinstance(r["lead_parent"], str) else "--"
        lines.append(f"{W.tex_escape(sec)} & {r['total_value'] / 1e9:,.1f} & {100 * r['sh_ext']:.0f} & {100 * r['sh_dom']:.0f} & {100 * r['sh_local']:.0f} & {lp} \\\\")
    lines += [r"\bottomrule", r"\multicolumn{6}{p{0.95\textwidth}}{\footnotesize HS sections ranked by export value. For./Dom./Local = foreign-MNE, domestic-MNE and local-firm shares of the section's export value, percent; Lead parent = largest parent country among the section's foreign MNEs and its share of the section's foreign-MNE value.} \\", r"\end{tabular}"]
    W.write_tex(lines, T / "tab_wp1f_hs_sections.tex")

    # Lorenz: concentration of foreign-MNE exports across products -------------------------------------------
    s = g.sort_values("val_ext", ascending=False)
    cum_v = np.cumsum(s["val_ext"].values) / s["val_ext"].sum(); cum_n = np.arange(1, len(s) + 1) / len(s)
    s2 = g.sort_values("total_value", ascending=False)
    cum_v2 = np.cumsum(s2["total_value"].values) / s2["total_value"].sum()
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(cum_n, cum_v, color=W.C_MNE_EXT, label="foreign-MNE exports")
    ax.plot(cum_n, cum_v2, color="#7f7f7f", linestyle="--", label="all exports")
    ax.plot([0, 1], [0, 1], color="black", linewidth=0.5)
    k = int(np.searchsorted(cum_v, 0.5)) + 1
    ax.axvline(k / len(s), color=W.C_MNE_EXT, linewidth=0.5, linestyle=":")
    ax.text(k / len(s) + 0.01, 0.1, f"{k} products = 50% of foreign-MNE exports", fontsize=8)
    ax.set_xlabel("cumulative share of HS6 products (ranked by value)"); ax.set_ylabel("cumulative share of export value")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    W.savefig(fig, "fig_wp1f_lorenz_foreign", G)
    print(f"   {k} HS6 products account for 50% of foreign-MNE exports")


def main():
    cube = W.build_cube(); cls = W.build_classifications()
    for scope in SCOPES:
        run_scope(cube, cls, scope)
    print("\n>>> wp1f done")


if __name__ == "__main__":
    main()
