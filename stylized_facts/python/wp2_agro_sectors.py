"""
wp2_agro_sectors.py  --  Volpe item 2 (agriculture focus; four-sector version)
==============================================================================

(a) FOUR-SECTOR comparison: agriculture (HS 01-24), mining & fuels (HS 25-27, plus HS 71
    precious metals -- MINING_INCLUDES_HS71 in wp_common), manufacturing (the rest).
    Services are NOT in customs merchandise data: the only service-like information is the
    matched affiliate's NAICS (naics_aff_2 = 5x), reported as a memo line.
(b) AGRICULTURE sub-classifications -- "consumption goods vs agricultural inputs", and
    sub-sectors by SITC / NAICS:
      · HS sections I-IV (as in src/07)
      · BEC Rev.4 end use (UNSD HS07->BEC: Intermediate / Consumption / Capital) and the
        detailed BEC categories (primary/processed x industry/household) -- the classification
        Volpe calls "VEC" in the notes is read as BEC
      · SITC Rev.3 divisions (2-digit) and groups (3-digit), from HS_2007_to_SITC3
      · NAICS (HS6 -> NAICS 2017): 111 crops, 112 animals, 113/114, 311 food mfg, 312 beverages/tobacco, 325 agrochemicals
      · Lall (2000): primary vs resource-based agro manufactures
      · an explicit AGRO-INPUTS flag (fertilisers, agrochemicals, seeds, feed, machinery, live animals)
    Each split gives foreign / domestic MNE shares, the leading parent countries, and an
    origin x sub-sector heat map.

The scope-specific Figures 1-4 (by parent) and Figure-2 variants for agriculture are
produced by wp1a / wp1b / wp1cd / wp1e / wp1f with scope="agro" (see those scripts).

Outputs: output/wp/sectors/ (four-sector) and output/wp/agro/ (sub-classifications).
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_common as W  # noqa: E402

SITC_DIV = {"00": "Live animals", "01": "Meat", "02": "Dairy & eggs", "03": "Fish & seafood", "04": "Cereals",
            "05": "Vegetables & fruit", "06": "Sugar & honey", "07": "Coffee, tea, cocoa, spices", "08": "Animal feed",
            "09": "Misc. edible products", "11": "Beverages", "12": "Tobacco", "21": "Hides & skins", "22": "Oil seeds",
            "23": "Rubber", "24": "Cork & wood", "26": "Textile fibres", "29": "Crude animal/veg. materials n.e.s.",
            "41": "Animal oils & fats", "42": "Fixed vegetable oils", "43": "Processed oils & fats", "56": "Fertilisers",
            "59": "Chemical materials n.e.s."}
NAICS3 = {"111": "111 Crop production", "112": "112 Animal production", "113": "113 Forestry & logging",
          "114": "114 Fishing, hunting", "311": "311 Food manufacturing", "312": "312 Beverage & tobacco mfg",
          "313": "313 Textile mills", "325": "325 Chemicals (agrochemicals)", "424": "424 Wholesale", "339": "339 Misc. mfg"}


def agg(d: pd.DataFrame, by, order=None, min_share=0.0) -> pd.DataFrame:
    by = [by] if isinstance(by, str) else by
    g = d.dropna(subset=by).groupby(by, as_index=False).agg(total_value=("value", "sum"), val_ext=("val_ext", "sum"),
                                                              val_dom=("val_dom", "sum"), val_total=("val_total", "sum"),
                                                              n_hs6=("hs07_6d", "nunique"))
    for k in ("ext", "dom", "total"):
        g[f"sh_{k}"] = g[f"val_{k}"] / g["total_value"]
    g["sh_of_scope"] = g["total_value"] / g["total_value"].sum()
    if order is not None:
        g = g.set_index(by[0]).reindex([o for o in order if o in set(g[by[0]])]).reset_index()
    if min_share > 0:
        g = g[g["sh_of_scope"] >= min_share]
    return g


def lead_parents(d: pd.DataFrame, by: str, k: int = 3) -> pd.Series:
    e = d[d["owner_type"] == "ext"].groupby([by, "iso3_parent"])["value"].sum().reset_index()
    e["tot"] = e.groupby(by)["value"].transform("sum"); e["sh"] = e["value"] / e["tot"]
    e = e.sort_values([by, "value"], ascending=[True, False])
    e["rank"] = e.groupby(by).cumcount()
    e = e[e["rank"] < k]
    e["txt"] = e["iso3_parent"].astype(str) + " " + e["sh"].map(lambda v: f"{v:.2f}")
    return e.groupby(by)["txt"].agg(", ".join)


def vbar_2def(g: pd.DataFrame, labels, fname: str, gdir: Path, xlabel: str = "", ymax: float = 0.9, figsize=(8.5, 4.5), rot=0):
    n = len(g); x = np.arange(n); bw = 0.38
    fig, ax = plt.subplots(figsize=figsize)
    ax.bar(x - bw / 2, g["sh_ext"], bw, color=W.C_MNE_EXT, edgecolor=W.C_MNE_EXT, label="Foreign MNEs")
    ax.bar(x + bw / 2, g["sh_dom"], bw, color=W.C_MNE_DOM, edgecolor="#9e9e9e", linewidth=0.5, label="Domestic MNEs")
    for xi, r in zip(x, g.itertuples()):
        ax.text(xi - bw / 2, r.sh_ext + 0.01, f"{r.sh_ext:.2f}", ha="center", fontsize=8)
        ax.text(xi + bw / 2, r.sh_dom + 0.01, f"{r.sh_dom:.2f}", ha="center", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels(labels, rotation=rot, ha="right" if rot else "center", fontsize=8)
    ax.set_xlabel(xlabel); ax.set_ylabel("Share in export value (value-weighted)"); ax.set_ylim(0, ymax)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    W.savefig(fig, fname, gdir)


def hbar_2def(g: pd.DataFrame, labels, fname: str, gdir: Path, xmax: float = 0.9):
    n = len(g); y = np.arange(n)[::-1]; bh = 0.38
    fig, ax = plt.subplots(figsize=(9, max(3, 0.55 * n + 1.2)))
    ax.barh(y + bh / 2, g["sh_ext"], bh, color=W.C_MNE_EXT, label="Foreign MNEs")
    ax.barh(y - bh / 2, g["sh_dom"], bh, color=W.C_MNE_DOM, edgecolor="#9e9e9e", linewidth=0.5, label="Domestic MNEs")
    for yi, r in zip(y, g.itertuples()):
        ax.text(r.sh_ext + 0.006, yi + bh / 2, f"{r.sh_ext:.2f}", va="center", fontsize=7)
        ax.text(r.sh_dom + 0.006, yi - bh / 2, f"{r.sh_dom:.2f}", va="center", fontsize=7)
        ax.text(xmax * 0.995, yi, f"${r.total_value / 1e9:,.1f}bn", va="center", ha="right", fontsize=7, color="#555555")
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=8); ax.set_xlim(0, xmax)
    ax.set_xlabel("Share in export value (value-weighted)"); ax.legend(frameon=False, fontsize=8, loc="lower right")
    W.savefig(fig, fname, gdir)


def write_split_table(g: pd.DataFrame, label_col: str, hdr: str, path: Path, leads: pd.Series | None, note: str) -> None:
    lines = [r"\begin{tabular}{lrrrrrl}", r"\toprule",
             f"{hdr} & Value (\\$bn) & \\% of scope & Foreign & Domestic & N HS6 & Leading parents (share of foreign) \\\\", r"\midrule"]
    for _, r in g.iterrows():
        lp = leads.get(r[label_col], "--") if leads is not None else ""
        lines.append(f"{W.tex_escape(r[label_col])} & {r['total_value'] / 1e9:,.1f} & {100 * r['sh_of_scope']:.1f} & {r['sh_ext']:.2f} & {r['sh_dom']:.2f} & {int(r['n_hs6']):,} & {lp} \\\\")
    lines += [r"\bottomrule", rf"\multicolumn{{7}}{{p{{0.95\textwidth}}}}{{\footnotesize {note}}} \\", r"\end{tabular}"]
    W.write_tex(lines, path)


def origin_heatmap(d: pd.DataFrame, by: str, labels: dict, fname: str, gdir: Path, tdir: Path, order=None, min_share=0.01):
    dd = d.dropna(subset=[by])
    g = dd.groupby(["country_orig", by]).agg(v=("value", "sum"), e=("val_ext", "sum")).reset_index()
    g["sh"] = g["e"] / g["v"]
    tot = dd.groupby(by)["value"].sum(); keep = tot[tot / tot.sum() >= min_share].index
    mat = g[g[by].isin(keep)].pivot(index="country_orig", columns=by, values="sh")
    if order: mat = mat.reindex(columns=[c for c in order if c in mat.columns])
    mat.columns = [labels.get(c, str(c)) if labels else str(c) for c in mat.columns]
    ovs = dd.groupby("country_orig")[["val_ext", "value"]].sum()
    ov = (ovs["val_ext"] / ovs["value"]).sort_values(ascending=False)
    mat = mat.reindex(ov.index)
    W.heatmap(mat * 100, fname, gdir, cbar_label="foreign-MNE share of export value (%)", fmt="{:.0f}", vmin=0, vmax=100,
              cmap="Blues", xlabel="", ylabel="exporting country")
    W.write_matrix_tex(mat * 100, tdir / f"tab_{fname[4:]}.tex", fmt="{:.1f}", corner="Origin", note="Foreign-MNE share of export value, percent; sub-sectors with at least 1% of the scope's exports.")


# ---------------------------------------------------------------------
def four_sectors(cube: pd.DataFrame, cls: pd.DataFrame, fdpy_naics: pd.DataFrame | None) -> None:
    G, T, R = W.outdirs("sectors")
    d = W.mne_flags(cube); d = d[d["value"] > 0].copy()
    d["sector4"] = W.sector4(d["hs2"])
    g = agg(d, "sector4", W.SECTOR_ORDER)
    leads = lead_parents(d, "sector4", 5)
    note = ("Agriculture = HS 01--24; Mining \\& fuels = HS 25--27" + (" and 71 (precious metals and stones)" if W.MINING_INCLUDES_HS71 else "")
            + "; Manufacturing = all other chapters. Services are not observable in customs merchandise data. Pooled 2006--2022, nine LAC origins.")
    write_split_table(g, "sector4", "Sector", T / "tab_wp2_four_sectors.tex", leads, note)
    vbar_2def(g, g["sector4"], "fig_wp2_four_sectors", G)
    print("\n=== four sectors:\n" + g[["sector4", "total_value", "sh_of_scope", "sh_ext", "sh_dom", "n_hs6"]].to_string())

    # origin x sector: foreign share and value share
    for val, nm, lab in (("sh_ext", "foreign_share", "foreign-MNE share of export value (%)"), ("total_value", "value_share", "% of the origin's exports")):
        m = d.groupby(["country_orig", "sector4"]).agg(v=("value", "sum"), e=("val_ext", "sum")).reset_index()
        if val == "sh_ext":
            m["x"] = m["e"] / m["v"]
        else:
            m["x"] = m["v"] / m.groupby("country_orig")["v"].transform("sum")
        mat = m.pivot(index="country_orig", columns="sector4", values="x").reindex(columns=W.SECTOR_ORDER) * 100
        W.heatmap(mat, f"fig_wp2_origin_x_sector_{nm}", G, cbar_label=lab, fmt="{:.0f}", vmin=0, vmax=100, xlabel="", ylabel="exporting country")
        W.write_matrix_tex(mat, T / f"tab_wp2_origin_x_sector_{nm}.tex", fmt="{:.1f}", corner="Origin")

    # destination mix and top parents by sector
    d["dest_region"] = d["country_dest"].map(W.classify_region)
    e = d[d["owner_type"].isin(["ext", "ext_unknown"])]
    m = e.pivot_table(index="sector4", columns="dest_region", values="value", aggfunc="sum", fill_value=0.0).reindex(W.SECTOR_ORDER).reindex(columns=W.REGION_ORDER)
    W.write_matrix_tex(100 * m.div(m.sum(axis=1), axis=0), T / "tab_wp2_sector_x_destregion_foreign.tex", fmt="{:.1f}", corner="Sector \\ Destination region",
                       row_total=m.sum(axis=1) / 1e9, note="Foreign-MNE exports by sector: destination mix (row %); last column = row total, USD bn.")
    # services memo: matched exporters whose affiliate NAICS is a service sector
    if fdpy_naics is not None:
        s = fdpy_naics.copy()
        s["svc"] = s["naics_aff_2"].astype(str).str.strip().str[:1].isin(["5", "6", "7", "8"]) | s["naics_aff_2"].astype(str).str.strip().isin(["42", "44", "45", "48", "49"])
        tot = s.loc[s["m"] == 1, "value_fob"].sum()
        svc = s.loc[(s["m"] == 1) & s["svc"], "value_fob"].sum()
        W.write_tex([f"% memo: matched exporters classified in services/trade NAICS (2-digit 42-49, 5x-8x) account for {100 * svc / tot:.1f}\\% of matched export value ({svc / 1e9:,.1f} bn of {tot / 1e9:,.1f} bn). Customs data record goods only; a services version of the facts would need a different source."],
                    T / "memo_wp2_services.tex")
        print(f"   memo: service-NAICS affiliates = {100 * svc / tot:.1f}% of matched export value")


def agro_subsectors(cube: pd.DataFrame, cls: pd.DataFrame) -> None:
    G, T, R = W.outdirs("agro")
    d = W.scope_filter(W.mne_flags(cube), "agro"); d = d[d["value"] > 0]
    d = d.merge(cls[["hs07_6d", "hs6_desc", "agro_section", "bec4", "bec4_label", "bec_enduse", "sitc2", "sitc3_3d", "sitc3_desc",
                     "naics3", "lall2000_category", "agro_input"]], on="hs07_6d", how="left")
    d["agro_section_lbl"] = d["agro_section"].map(W.AGRO_SECTION_LABEL)
    d["sitc2_lbl"] = d["sitc2"].map(lambda c: f"{c} {SITC_DIV.get(c, '')}".strip() if isinstance(c, str) else np.nan)
    d["naics3_lbl"] = d["naics3"].map(lambda c: NAICS3.get(c, f"{c} other") if isinstance(c, str) else np.nan)
    d["input_lbl"] = np.where(d["agro_input"] == 1, "Agricultural inputs", "Agricultural output (food, fibres, beverages)")
    d["bec4_lbl"] = d["bec4"].map(lambda c: f"{c} {W.BEC4_LABEL.get(c, '')}" if isinstance(c, str) else np.nan)
    d["lall_lbl"] = d["lall2000_category"].replace({"Resource-based manufactures: agro-based": "Resource-based mfg: agro-based",
                                                      "Resource-based manufactures: other": "Resource-based mfg: other"})
    tot = d["value"].sum()
    print(f"\n=== agro: ${tot / 1e9:,.1f} bn; foreign share {d['val_ext'].sum() / tot:.3f}, domestic {d['val_dom'].sum() / tot:.3f}")
    note = "Agricultural exports (HS 01--24), pooled 2006--2022, nine LAC origins. Foreign/Domestic = MNE shares of the row's export value."

    SPLITS = [  # (column, header, file stem, order, min share, rotate labels)
        ("agro_section_lbl", "HS section", "hs_section", list(W.AGRO_SECTION_LABEL.values()), 0.0, 15),
        ("bec_enduse", "BEC end use", "bec_enduse", W.ENDUSE_ORDER, 0.0, 0),
        ("bec4_lbl", "BEC Rev.4 category", "bec4", None, 0.005, 30),
        ("input_lbl", "Inputs vs output", "inputs", ["Agricultural inputs", "Agricultural output (food, fibres, beverages)"], 0.0, 0),
        ("sitc2_lbl", "SITC Rev.3 division", "sitc2", None, 0.01, 45),
        ("naics3_lbl", "NAICS (product-based)", "naics3", None, 0.01, 30),
        ("lall_lbl", "Lall (2000) category", "lall", None, 0.005, 30),
    ]
    for col, hdr, stem, order, min_share, rot in SPLITS:
        g = agg(d, col, order, min_share)
        if order is None:
            g = g.sort_values("total_value", ascending=False)
        leads = lead_parents(d, col, 3)
        write_split_table(g, col, hdr, T / f"tab_wp2_agro_{stem}.tex", leads, note + (f" Categories with at least {min_share:.1%} of agricultural exports." if min_share else ""))
        if len(g) <= 6:
            vbar_2def(g, g[col].astype(str).str.replace(" (", "\n(", regex=False), f"fig_wp2_agro_{stem}", G, rot=rot)
        else:
            hbar_2def(g, g[col].astype(str), f"fig_wp2_agro_{stem}", G)
        origin_heatmap(d, col, {}, f"fig_wp2_agro_origin_x_{stem}", G, T, order, min_share=max(min_share, 0.01))
        print(f"   {hdr:22s}: " + "; ".join(f"{str(r[col])[:28]} ext {r['sh_ext']:.2f}/dom {r['sh_dom']:.2f} ({100 * r['sh_of_scope']:.0f}%)" for _, r in g.head(6).iterrows()))

    # BEC end use x HS section (the two-way Volpe asked to "explore")
    m = d.pivot_table(index="agro_section_lbl", columns="bec_enduse", values="value", aggfunc="sum", fill_value=0.0)
    m = m.reindex(columns=[c for c in W.ENDUSE_ORDER if c in m.columns])
    W.write_matrix_tex(m / 1e9, T / "tab_wp2_agro_section_x_enduse_value.tex", fmt="{:,.1f}", corner="HS section \\ BEC end use",
                       row_total=m.sum(axis=1) / 1e9, col_total=m.sum(axis=0) / 1e9, note="Agricultural export value, USD bn.")
    e = d.pivot_table(index="agro_section_lbl", columns="bec_enduse", values="val_ext", aggfunc="sum", fill_value=0.0).reindex(columns=m.columns)
    W.write_matrix_tex(100 * e / m, T / "tab_wp2_agro_section_x_enduse_foreignshare.tex", fmt="{:.1f}", corner="HS section \\ BEC end use",
                       note="Foreign-MNE share of export value, percent, by HS section and BEC end use.")

    # inputs vs output by parent country (stacked), and top HS6 agro inputs
    top = W.top_parents(d, 8)
    d["pgrp"] = W.parent_group(d, top)
    groups = top + ["Other", "Unknown", "Domestic"]
    for col, stem in (("input_lbl", "inputs"), ("bec_enduse", "bec_enduse"), ("agro_section_lbl", "hs_section")):
        totc = d.groupby(col)["value"].sum()
        mat = d.pivot_table(index=col, columns="pgrp", values="value", aggfunc="sum", fill_value=0.0)
        mat = mat.reindex(columns=[g for g in groups if g in mat.columns], fill_value=0.0).div(totc, axis=0)
        W.write_matrix_tex(100 * mat, T / f"tab_wp2_agro_{stem}_by_parent.tex", fmt="{:.1f}", corner=stem.replace("_", " "),
                           note="Share of the row's export value by the exporter's parent country (percent); remainder = local firms.")
    inputs = d[d["agro_input"] == 1].groupby(["hs07_6d", "hs6_desc"], as_index=False).agg(total_value=("value", "sum"), val_ext=("val_ext", "sum"), val_dom=("val_dom", "sum"))
    inputs["sh_ext"] = inputs["val_ext"] / inputs["total_value"]; inputs["sh_dom"] = inputs["val_dom"] / inputs["total_value"]
    inputs = inputs.sort_values("total_value", ascending=False).head(20)
    lines = [r"\begin{tabular}{llrrr}", r"\toprule", r"HS6 & Description & Value (\$bn) & Foreign & Domestic \\", r"\midrule"]
    for _, r in inputs.iterrows():
        lines.append(f"{r['hs07_6d']} & {W.tex_escape(str(r['hs6_desc'])[:60])} & {r['total_value'] / 1e9:,.2f} & {r['sh_ext']:.2f} & {r['sh_dom']:.2f} \\\\")
    lines += [r"\bottomrule", r"\multicolumn{5}{p{0.9\textwidth}}{\footnotesize Top 20 agricultural-input products (fertilisers HS 31, agrochemicals 3808, seeds, animal feed 2301--2309, agricultural machinery 8432--8437, tractors 8701, live animals) exported from the nine LAC origins.}} \\", r"\end{tabular}"]
    W.write_tex(lines, T / "tab_wp2_agro_top_inputs_hs6.tex")


def main():
    cube = W.build_cube(); cls = W.build_classifications()
    try:
        f = W.load_fdpy()
        f = f[~f["country_orig"].isin(W.excluded_origins())]
        fn = f[["value_fob", "naics_aff_2"]].assign(m=W.matched_flag(f))
    except Exception as e:  # noqa: BLE001
        print("   (no FDPY cache for the services memo:", e, ")"); fn = None
    four_sectors(cube, cls, fn)
    agro_subsectors(cube, cls)
    print("\n>>> wp2 done")


if __name__ == "__main__":
    main()
