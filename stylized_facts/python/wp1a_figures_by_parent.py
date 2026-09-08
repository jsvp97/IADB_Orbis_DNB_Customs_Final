"""
wp1a_figures_by_parent.py  --  Volpe item 1a
============================================

The document's Figures 1 (share by origin), 2 (share by PCI quintile), 3 (share by Lall
technology category) and 4 (foreign-MNE value by parent country), redrawn so that the
FOREIGN-MNE bar is split by the multinational's HOME COUNTRY (USA, GBR, CAN, ..., CHN,
Other, Unknown parent) -- "mirar todo desde la figura de share de origen".

Same data (the parent cube built from src/15's cache), same conventions as the July-2026
document (CONVENTION="sf": nine origins, ext = total - dom), same geometry as Ignacio's
sf1_origin.py / sf3_products.py / sf2_mne_origin.py; only the colour split is new.

Runs for every scope in SCOPES (all goods; agriculture HS 01-24; mining & fuels;
manufacturing) -- the agriculture run is the item-2 "agro version" of these figures.

Outputs (output/wp/<scope>/):
  Graphs/fig_wp1a_origin_by_parent      Figure 1 with the foreign bar split by parent
  Graphs/fig_wp1a_pci_by_parent         Figure 2 (PCI quintiles) split by parent
  Graphs/fig_wp1a_lall_by_parent        Figure 3 (Lall 4 categories) split by parent
  Graphs/fig_wp1a_parent_share          Figure 4 for the scope (top 15 + Other)
  Tables/tab_wp1a_*.tex                 the numbers behind each figure
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
TOP_K = W.TOP_K_FIG
QLBL = {1: "Q1", 2: "Q2", 3: "Q3", 4: "Q4", 5: "Q5"}
LALL_4 = {
    "Primary products": "Primary and resource-based",
    "Resource-based manufactures: agro-based": "Primary and resource-based",
    "Resource-based manufactures: other": "Primary and resource-based",
    "Low technology manufactures: textile, garment and footwear": "Low tech manufacturing",
    "Low technology manufactures: other products": "Low tech manufacturing",
    "Unclassified products": "Low tech manufacturing",
    "Medium technology manufactures: automotive": "Medium tech manufacturing",
    "Medium technology manufactures: engineering": "Medium tech manufacturing",
    "Medium technology manufactures: process": "Medium tech manufacturing",
    "High technology manufactures: electronic and electrical": "High tech manufacturing",
    "High technology manufactures: other": "High tech manufacturing",
}
LALL_4_ORDER = ["High tech manufacturing", "Medium tech manufacturing", "Low tech manufacturing",
                "Primary and resource-based"]
LALL_4_XLBL = {k: k.replace(" manufacturing", "\nmanufacturing").replace("and resource", "and\nresource") for k in LALL_4_ORDER}


# ---------------------------------------------------------------------
# Generic stacked-bar engine (segments = parent groups, in a fixed order)
# ---------------------------------------------------------------------
def shares_by(d: pd.DataFrame, by: str, groups: list[str]) -> pd.DataFrame:
    """Rows = categories of `by`; columns = share of total value by parent group (+ sh_total)."""
    tot = d.groupby(by)["value"].sum()
    mat = d.pivot_table(index=by, columns="pgrp", values="value", aggfunc="sum", fill_value=0.0)
    mat = mat.reindex(columns=[g for g in groups if g in mat.columns], fill_value=0.0)
    sh = mat.div(tot, axis=0)
    sh["sh_total"] = sh.drop(columns=[c for c in ("Local",) if c in sh.columns]).sum(axis=1)
    sh["total_value"] = tot
    return sh


def stacked_bars(sh: pd.DataFrame, groups: list[str], fname: str, gdir: Path, *, horizontal: bool,
                 xlabels: dict | None = None, axis_label: str, cat_label: str = "",
                 lim: float | None = None, figsize=None) -> None:
    cats = list(sh.index)
    n = len(cats)
    pos = np.arange(n)
    if figsize is None:
        figsize = (8, max(4, 0.55 * n + 1.2)) if horizontal else (8.5, 4.8)
    fig, ax = plt.subplots(figsize=figsize)
    left = np.zeros(n)
    for i, g in enumerate(groups):
        if g not in sh.columns:
            continue
        vals = sh[g].values
        kw = dict(color=W.parent_color(g, i), edgecolor="white", linewidth=0.6, label=GLABEL.get(g, g))
        if g == "Unknown":
            kw.update(hatch="///", edgecolor="#6b7a99")
        if horizontal:
            ax.barh(pos, vals, left=left, **kw)
        else:
            ax.bar(pos, vals, bottom=left, **kw)
        # annotate big segments
        for k in range(n):
            if vals[k] > 0.045:
                txt_color = W.text_color(g, i)
                if horizontal:
                    ax.text(left[k] + vals[k] / 2, pos[k], f"{vals[k]:.2f}", va="center", ha="center",
                            fontsize=7, color=txt_color)
                else:
                    ax.text(pos[k], left[k] + vals[k] / 2, f"{vals[k]:.2f}", va="center", ha="center",
                            fontsize=7, color=txt_color)
        left = left + vals
    # total MNE share label
    for k in range(n):
        if horizontal:
            ax.text(left[k] + 0.006, pos[k], f"{sh['sh_total'].iloc[k]:.2f}", va="center", ha="left",
                    fontsize=8, fontweight="bold")
        else:
            ax.text(pos[k], left[k] + 0.01, f"{sh['sh_total'].iloc[k]:.2f}", va="bottom", ha="center",
                    fontsize=8, fontweight="bold")
    labels = [xlabels.get(c, str(c)) if xlabels else str(c) for c in cats]
    lim = lim if lim is not None else max(0.85, float(sh["sh_total"].max()) * 1.15)
    if horizontal:
        ax.set_yticks(pos); ax.set_yticklabels(labels)
        ax.set_xlim(0, lim); ax.set_xlabel(axis_label)
        ax.set_xticks(np.arange(0, lim + 1e-9, 0.1))
        if cat_label: ax.set_ylabel(cat_label)
        ax.legend(frameon=False, fontsize=7, loc="lower right", ncol=3)
    else:
        ax.set_xticks(pos); ax.set_xticklabels(labels, rotation=0)
        ax.set_ylim(0, lim); ax.set_ylabel(axis_label)
        if cat_label: ax.set_xlabel(cat_label)
        ax.legend(frameon=False, fontsize=7, loc="upper left", ncol=4)
    W.savefig(fig, fname, gdir)


def write_share_table(sh: pd.DataFrame, groups: list[str], path: Path, corner: str, note: str,
                      xlabels: dict | None = None) -> None:
    cols = [g for g in groups if g in sh.columns]
    lines = [r"\begin{tabular}{l" + "c" * (len(cols) + 2) + "}", r"\toprule",
             W.tex_escape(corner) + " & " + " & ".join(GLABEL_TEX.get(c, c) for c in cols) + r" & MNE total & Value (\$bn) \\",
             r"\midrule"]
    for idx, r in sh.iterrows():
        lab = xlabels.get(idx, str(idx)) if xlabels else str(idx)
        lines.append(W.tex_escape(lab.replace("\n", " ")) + " & " + " & ".join(f"{r[c]:.3f}" for c in cols)
                     + f" & {r['sh_total']:.3f} & {r['total_value'] / 1e9:,.1f}" + r" \\")
    lines += [r"\bottomrule", rf"\multicolumn{{{len(cols) + 3}}}{{p{{0.95\textwidth}}}}{{\footnotesize {note}}} \\",
              r"\end{tabular}"]
    W.write_tex(lines, path)


GLABEL = {"Other": "Other foreign MNEs", "Unknown": "Foreign, parent unknown", "Domestic": "Domestic MNEs"}
GLABEL_TEX = {"Other": "Other", "Unknown": "Unknown", "Domestic": "Dom."}


# ---------------------------------------------------------------------
# Figure 4 for the scope (Ignacio's fig_sf2_mne_origin geometry)
# ---------------------------------------------------------------------
def parent_share_figure(d: pd.DataFrame, gdir: Path, tdir: Path, scope: str, top_n: int = 15) -> pd.DataFrame:
    ext = d[d["owner_type"] == "ext"].groupby("iso3_parent", as_index=False)["value"].sum()
    ext = ext.sort_values("value", ascending=False).reset_index(drop=True)
    total = ext["value"].sum()
    ext["share"] = ext["value"] / total
    top = ext.head(top_n)
    other = ext["share"].iloc[top_n:].sum()
    labels = top["iso3_parent"].tolist() + ["Other"]
    shares = top["share"].tolist() + [other]
    fig, ax = plt.subplots(figsize=(8, 6))
    y = np.arange(len(labels))[::-1]
    ax.barh(y, shares, color=W.C_MNE_EXT, edgecolor=W.C_MNE_EXT)
    for yi, s in zip(y, shares):
        ax.text(s + max(shares) * 0.01, yi, f"{s * 100:.1f}%", va="center", fontsize=9)
    ax.set_yticks(y); ax.set_yticklabels(labels)
    ax.set_xlim(0, max(shares) * 1.12)
    ax.set_xlabel("Share of foreign-MNE export value")
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v * 100:.0f}%"))
    W.savefig(fig, "fig_wp1a_parent_share", gdir)
    unknown = d.loc[d["owner_type"] == "ext_unknown", "value"].sum()
    lines = [r"\begin{tabular}{lrr}", r"\toprule", r"Parent country & Share (\%) & Value (\$bn) \\", r"\midrule"]
    for _, r in top.iterrows():
        lines.append(f"{r['iso3_parent']} & {r['share'] * 100:.1f} & {r['value'] / 1e9:,.1f} \\\\")
    lines.append(f"Other ({len(ext) - top_n} countries) & {other * 100:.1f} & {ext['value'].iloc[top_n:].sum() / 1e9:,.1f} \\\\")
    lines += [r"\midrule", f"Foreign MNEs with recorded parent & 100.0 & {total / 1e9:,.1f} \\\\",
              f"Foreign MNEs, parent unknown (excluded above) & -- & {unknown / 1e9:,.1f} \\\\",
              r"\bottomrule", r"\end{tabular}"]
    W.write_tex(lines, tdir / "tab_wp1a_parent_share.tex")
    print(f"   [{scope}] parent shares: " + ", ".join(f"{a} {b * 100:.1f}%" for a, b in zip(labels[:6], shares[:6]))
          + f" | unknown parent = {unknown / (unknown + total):.0%} of foreign-MNE value")
    return ext


# ---------------------------------------------------------------------
# The document's ORIGINAL Figures 1-3, redrawn on the current base (same geometry as
# sf1_origin.stacked_origin_bar and sf3_products.grouped_vbar_2def)
# ---------------------------------------------------------------------
def originals(d: pd.DataFrame, hs6q: pd.DataFrame, hs6l: pd.DataFrame, G: Path, T: Path) -> None:
    cross = d.groupby("country_orig").agg(v=("value", "sum"), e=("val_ext", "sum"), m=("val_dom", "sum"))
    cross["sh_ext"] = cross["e"] / cross["v"]; cross["sh_dom"] = cross["m"] / cross["v"]
    cross["sh_total"] = cross["sh_ext"] + cross["sh_dom"]
    sub = cross.sort_values("sh_total", ascending=True)
    y = np.arange(len(sub))
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(y, sub["sh_ext"], color=W.C_MNE_EXT, edgecolor="white", linewidth=0.6, label="Foreign MNEs")
    ax.barh(y, sub["sh_dom"], left=sub["sh_ext"], color=W.C_MNE_DOM, edgecolor="white", linewidth=0.6, label="Domestic MNEs")
    for yi, r in zip(y, sub.itertuples()):
        if r.sh_ext > 0.05:
            ax.text(r.sh_ext / 2, yi, f"{r.sh_ext:.2f}", va="center", ha="center", color="white", fontsize=8)
        if r.sh_dom > 0.04:
            ax.text(r.sh_ext + r.sh_dom / 2, yi, f"{r.sh_dom:.2f}", va="center", ha="center", color="black", fontsize=8)
        ax.text(r.sh_total + 0.006, yi, f"{r.sh_total:.2f}", va="center", ha="left", fontsize=8, fontweight="bold")
    ax.set_yticks(y); ax.set_yticklabels(sub.index)
    ax.set_xlabel("MNE share in export value (value-weighted)")
    xmax = max(0.85, sub["sh_total"].max() * 1.12); ax.set_xlim(0, xmax); ax.set_xticks(np.arange(0, xmax + 1e-9, 0.1))
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    W.savefig(fig, "fig_wp0_fig1_origin", G)
    lines = [r"\begin{tabular}{lrrrr}", r"\toprule", r"Origin & Foreign & Domestic & MNE total & Value (\$bn) \\", r"\midrule"]
    for o, r in sub.sort_values("sh_total", ascending=False).iterrows():
        lines.append(f"{o} & {r['sh_ext']:.3f} & {r['sh_dom']:.3f} & {r['sh_total']:.3f} & {r['v'] / 1e9:,.1f} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    W.write_tex(lines, T / "tab_wp0_fig1_origin.tex")

    def two_def(g, xlabels, xlabel, fname, ymax=0.8):
        n = len(g); x = np.arange(n); bw = 0.38
        fig, ax = plt.subplots(figsize=(8.5, 4.5))
        ax.bar(x - bw / 2, g["sh_ext"], bw, color=W.C_MNE_EXT, edgecolor=W.C_MNE_EXT, label="Foreign MNEs")
        ax.bar(x + bw / 2, g["sh_dom"], bw, color=W.C_MNE_DOM, edgecolor="#9e9e9e", linewidth=0.5, label="Domestic MNEs")
        for xi, r in zip(x, g.itertuples()):
            ax.text(xi - bw / 2, r.sh_ext + 0.01, f"{r.sh_ext:.2f}", ha="center", fontsize=8)
            ax.text(xi + bw / 2, r.sh_dom + 0.01, f"{r.sh_dom:.2f}", ha="center", fontsize=8)
        ax.set_xticks(x); ax.set_xticklabels([xlabels.get(v, str(v)) for v in g.index])
        ax.set_xlabel(xlabel); ax.set_ylabel("Share in export value (value-weighted)"); ax.set_ylim(0, ymax)
        ax.legend(frameon=False, fontsize=9, loc="upper left")
        W.savefig(fig, fname, G)

    def agg2(dd, by):
        g = dd.groupby(by).agg(v=("value", "sum"), e=("val_ext", "sum"), m=("val_dom", "sum"))
        g["sh_ext"] = g["e"] / g["v"]; g["sh_dom"] = g["m"] / g["v"]
        return g

    if hs6q is None or hs6l is None:
        print("   originals: Fig1 only (no product classification in this scope)"); return
    gq = agg2(d.merge(hs6q, on="hs07_6d", how="inner"), "quintile")
    two_def(gq, QLBL, "PCI quintile (1 = lowest complexity, 5 = highest)", "fig_wp0_fig2_pci")
    gl = agg2(d.merge(hs6l, on="hs07_6d", how="inner"), "lall_4").reindex([c for c in LALL_4_ORDER if c in set(hs6l["lall_4"])])
    two_def(gl, LALL_4_XLBL, "", "fig_wp0_fig3_lall")
    print("   originals: Fig1 " + ", ".join(f"{o}:{r.sh_ext:.2f}+{r.sh_dom:.2f}" for o, r in sub.sort_values("sh_total", ascending=False).iterrows())
          + " | Fig2 ext " + " ".join(f"{v:.2f}" for v in gq["sh_ext"]) + " | Fig3 ext " + " ".join(f"{v:.2f}" for v in gl["sh_ext"]))


# ---------------------------------------------------------------------
def run_scope(cube: pd.DataFrame, cls: pd.DataFrame, scope: str) -> None:
    G, T, R = W.outdirs(scope)
    d = W.scope_filter(W.mne_flags(cube), scope)
    d = d[d["value"] > 0]
    top = W.top_parents(d, TOP_K)
    groups = top + ["Other", "Domestic"]
    d["pgrp"] = W.parent_group(d, top)
    note_conv = ("Value-weighted; pooled 2006--2022; nine LAC origins (Ecuador excluded). " + W.PARENT_GROUPS_NOTE)
    print(f"\n=== scope {scope}: {len(d):,} cube rows, ${d['value'].sum() / 1e9:,.1f} bn, top parents {top}")

    # --- Figure 1 by parent: origins sorted by total MNE share (as in the document) -------
    sh1 = shares_by(d, "country_orig", groups).sort_values("sh_total", ascending=True)
    stacked_bars(sh1, groups, "fig_wp1a_origin_by_parent", G, horizontal=True,
                 axis_label="MNE share in export value (value-weighted)")
    write_share_table(sh1.sort_values("sh_total", ascending=False), groups, T / "tab_wp1a_origin_by_parent.tex",
                      "Origin", "Figure 1 split by parent country. " + note_conv)

    # --- Figure 2 by parent: PCI quintiles (quintiles over HS6 products, as in the document) --
    hs6 = d.groupby("hs07_6d", as_index=False)["value"].sum().merge(
        cls[["hs07_6d", "complexity", "lall2000_category"]], on="hs07_6d", how="left")
    q = hs6.dropna(subset=["complexity"]).copy()
    if len(q) < 10:
        print(f"   [{scope}] no complexity data ({len(q)} HS6); Figures 2-3 skipped")
        originals(d, None, None, G, T); parent_share_figure(d, G, T, scope); return
    q["quintile"] = pd.qcut(q["complexity"], 5, labels=False, duplicates="drop") + 1
    dq = d.merge(q[["hs07_6d", "quintile"]], on="hs07_6d", how="inner")
    sh2 = shares_by(dq, "quintile", groups)
    stacked_bars(sh2, groups, "fig_wp1a_pci_by_parent", G, horizontal=False, xlabels=QLBL,
                 axis_label="Share in export value (value-weighted)",
                 cat_label="PCI quintile (1 = lowest complexity, 5 = highest)", lim=1.0)
    write_share_table(sh2, groups, T / "tab_wp1a_pci_by_parent.tex", "PCI quintile",
                      "Figure 2 split by parent country. Quintiles of the Hausmann--Hidalgo Product Complexity Index over HS6 products. " + note_conv, xlabels=QLBL)

    # --- Figure 3 by parent: Lall 4 categories ---------------------------------------------
    hs6["lall_4"] = hs6["lall2000_category"].map(LALL_4)
    dl = d.merge(hs6[["hs07_6d", "lall_4"]].dropna(), on="hs07_6d", how="inner")
    sh3 = shares_by(dl, "lall_4", groups).reindex([c for c in LALL_4_ORDER if c in dl["lall_4"].unique()])
    stacked_bars(sh3, groups, "fig_wp1a_lall_by_parent", G, horizontal=False, xlabels=LALL_4_XLBL,
                 axis_label="Share in export value (value-weighted)", lim=1.0)
    write_share_table(sh3, groups, T / "tab_wp1a_lall_by_parent.tex", "Technology category",
                      "Figure 3 split by parent country. Lall (2000) technology classification, four categories. " + note_conv)

    # --- the document's original Figures 1-3 on the current base ---------------------------------
    originals(d, q[["hs07_6d", "quintile"]], hs6[["hs07_6d", "lall_4"]].dropna(), G, T)

    # --- Figure 4 for the scope ---------------------------------------------------------------
    parent_share_figure(d, G, T, scope)

    # --- companion: parent x origin matrix (share of each origin's exports by parent) ---------
    mat = sh1.sort_values("sh_total", ascending=False)[[g for g in groups if g in sh1.columns]] * 100
    W.heatmap(mat, "fig_wp1a_origin_x_parent_heatmap", G, cbar_label="share of origin's export value (%)",
              fmt="{:.1f}", cmap="Blues", vmin=0, xlabel="parent country of the MNE", ylabel="exporting country")

    for name, s in (("origin", sh1), ("pci", sh2), ("lall", sh3)):
        print(f"   [{scope}] {name}: USA segment = "
              + ", ".join(f"{i}:{r.get('USA', float('nan')):.2f}" for i, r in s.iterrows()))


def main():
    cube = W.build_cube()
    cls = W.build_classifications()
    for scope in SCOPES:
        run_scope(cube, cls, scope)
    print("\n>>> wp1a done ->", W.WP_OUT)


if __name__ == "__main__":
    main()
