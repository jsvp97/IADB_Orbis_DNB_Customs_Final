"""
wp2_agro_sectors.py  --  Volpe item 2 (revision 3, 2026-09-08): the four sectors and their sub-classifications
=================================================================================================================

(a) FOUR SECTORS: Agriculture (HS 01-24), Mining & fuels (HS 25-27 and 71), Manufacturing (HS 28-97
    excl. 71) and REST (HS 98-99, chapter 00 and unclassifiable codes). Services are not in customs
    merchandise data; the Rest category holds what is left and a memo table reports the only
    service-related information available (the matched affiliate's own NAICS).
(b) For EVERY sector scope, the sub-classification block: HS sections within the sector, BEC Rev.4
    end use (consumption vs inputs -- the classification the notes call "VEC"), BEC detailed
    categories, SITC Rev.3 divisions, NAICS 3-digit (product-based), Lall (2000) categories and,
    for agriculture only, an agro-inputs flag. Each split gives (table) total exports, MNE exports,
    % foreign, % domestic and the three leading parents; (figure) foreign/domestic shares; (heat
    map + two-panel table) origin x sub-sector composition and foreign share; and a table of the
    parent-country composition (top-10 + Other + Domestic).

Outputs: output/wp/sectors/ (four-sector comparison) and output/wp/<scope>/Tables|Graphs/tab|fig_wp2_<stem>*
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_common as W  # noqa: E402

SITC_DIV = {"00": "Live animals", "01": "Meat", "02": "Dairy & eggs", "03": "Fish & seafood", "04": "Cereals", "05": "Vegetables & fruit",
            "06": "Sugar & honey", "07": "Coffee, tea, cocoa, spices", "08": "Animal feed", "09": "Misc. edible products", "11": "Beverages",
            "12": "Tobacco", "21": "Hides & skins", "22": "Oil seeds", "23": "Rubber", "24": "Cork & wood", "25": "Pulp & paper", "26": "Textile fibres",
            "27": "Crude fertilisers & minerals", "28": "Metalliferous ores", "29": "Crude animal/veg. materials", "32": "Coal", "33": "Petroleum",
            "34": "Gas", "41": "Animal oils & fats", "42": "Fixed vegetable oils", "43": "Processed oils & fats", "51": "Organic chemicals",
            "52": "Inorganic chemicals", "53": "Dyeing materials", "54": "Pharmaceuticals", "55": "Essential oils, cosmetics", "56": "Fertilisers",
            "57": "Plastics, primary", "58": "Plastics, non-primary", "59": "Chemical materials n.e.s.", "61": "Leather", "62": "Rubber manufactures",
            "63": "Cork & wood manufactures", "64": "Paper", "65": "Textile yarn & fabrics", "66": "Non-metallic mineral mfg", "67": "Iron & steel",
            "68": "Non-ferrous metals", "69": "Metal manufactures", "71": "Power machinery", "72": "Specialised machinery", "73": "Metalworking machinery",
            "74": "General industrial machinery", "75": "Office machines", "76": "Telecom equipment", "77": "Electrical machinery", "78": "Road vehicles",
            "79": "Other transport equipment", "81": "Prefab buildings, lighting", "82": "Furniture", "83": "Travel goods", "84": "Apparel", "85": "Footwear",
            "87": "Instruments", "88": "Photo & optical goods", "89": "Misc. manufactures", "93": "Special transactions", "96": "Coin", "97": "Gold"}
NAICS3 = {"111": "111 Crop production", "112": "112 Animal production", "113": "113 Forestry & logging", "114": "114 Fishing, hunting",
          "211": "211 Oil & gas extraction", "212": "212 Mining (excl. oil & gas)", "311": "311 Food manufacturing", "312": "312 Beverage & tobacco",
          "313": "313 Textile mills", "314": "314 Textile products", "315": "315 Apparel", "316": "316 Leather", "321": "321 Wood products",
          "322": "322 Paper", "324": "324 Petroleum & coal products", "325": "325 Chemicals", "326": "326 Plastics & rubber", "327": "327 Non-metallic minerals",
          "331": "331 Primary metals", "332": "332 Fabricated metals", "333": "333 Machinery", "334": "334 Computers & electronics", "335": "335 Electrical equipment",
          "336": "336 Transport equipment", "337": "337 Furniture", "339": "339 Misc. manufacturing", "424": "424 Wholesale (non-durable)", "423": "423 Wholesale (durable)"}
MIN_SHARE_TABLE = 0.005   # sub-sectors below 0.5% of the scope are pooled into "Other"


# ---------------------------------------------------------------------
def agg(d: pd.DataFrame, by: str, order=None, min_share=MIN_SHARE_TABLE, other_label="Other") -> pd.DataFrame:
    dd = d.dropna(subset=[by]).copy()
    tot = dd.groupby(by)["value"].sum()
    small = tot[tot / tot.sum() < min_share].index
    if len(small) > 1:
        dd[by] = dd[by].where(~dd[by].isin(small), other_label)
    g = dd.groupby(by, as_index=False).agg(total_value=("value", "sum"), val_ext=("val_ext", "sum"), val_dom=("val_dom", "sum"),
                                           val_total=("val_total", "sum"), n_hs6=("hs07_6d", "nunique"))
    for k in ("ext", "dom", "total"):
        g[f"sh_{k}"] = g[f"val_{k}"] / g["total_value"]
    g["sh_of_scope"] = g["total_value"] / g["total_value"].sum()
    if order is not None:
        keep = [o for o in order if o in set(g[by])] + ([other_label] if other_label in set(g[by]) else [])
        g = g.set_index(by).reindex(keep).reset_index()
    else:
        g = g.sort_values("total_value", ascending=False)
        if other_label in set(g[by]):
            g = pd.concat([g[g[by] != other_label], g[g[by] == other_label]])
    return g, dd


def lead_parents(dd: pd.DataFrame, by: str, k: int = 3) -> pd.Series:
    e = dd[dd["owner_type"] == "ext"].groupby([by, "iso3_parent"])["value"].sum().reset_index()
    e["tot"] = e.groupby(by)["value"].transform("sum"); e["sh"] = e["value"] / e["tot"]
    e = e.sort_values([by, "value"], ascending=[True, False])
    e["rank"] = e.groupby(by).cumcount(); e = e[e["rank"] < k]
    e["txt"] = e["iso3_parent"].astype(str) + " " + e["sh"].map(lambda v: f"{v:.2f}")
    return e.groupby(by)["txt"].agg(", ".join)


def write_split_table(g: pd.DataFrame, label_col: str, hdr: str, path: Path, leads: pd.Series, note: str) -> None:
    """Total exports | MNE exports | % foreign | % domestic | leading parents (top 3)."""
    lines = [r"\begin{tabular}{@{}l r r r r l@{}}", r"\toprule",
             f"{hdr} & Total exports (\\$bn) & MNE exports (\\$bn) & Foreign (\\%) & Domestic (\\%) & Leading parents (share of foreign) \\\\", r"\midrule"]
    for _, r in g.iterrows():
        lines.append(f"{W.tex_escape(r[label_col])} & {r['total_value'] / 1e9:,.1f} & {r['val_total'] / 1e9:,.1f} & {100 * r['sh_ext']:.1f} & {100 * r['sh_dom']:.1f} & {leads.get(r[label_col], '--')} \\\\")
    tv, tm = g["total_value"].sum(), g["val_total"].sum()
    lines += [r"\midrule", f"All & {tv / 1e9:,.1f} & {tm / 1e9:,.1f} & {100 * g['val_ext'].sum() / tv:.1f} & {100 * g['val_dom'].sum() / tv:.1f} & \\\\",
              r"\bottomrule", rf"\multicolumn{{6}}{{p{{0.95\textwidth}}}}{{\footnotesize {note} Foreign / Domestic = share of the row's export value; leading parents = the three largest parent countries among the row's foreign MNEs with their share of the row's foreign-MNE value.}} \\", r"\end{tabular}"]
    W.write_tex(lines, path)


def hbar_2def(g: pd.DataFrame, labels, fname: str, gdir: Path, xmax: float = 1.0):
    import textwrap
    n = len(g); y = np.arange(n)[::-1]; bh = 0.38
    fig, ax = plt.subplots(figsize=(9, max(3.2, 0.42 * n + 1.6)))
    ax.barh(y + bh / 2, g["sh_ext"], bh, color=W.C_MNE_EXT, label="Foreign MNEs")
    ax.barh(y - bh / 2, g["sh_dom"], bh, color=W.C_MNE_DOM, edgecolor="#9e9e9e", linewidth=0.5, label="Domestic MNEs")
    vfmt = "${:,.2f}bn" if g["total_value"].max() < 20e9 else "${:,.1f}bn"
    for yi, r in zip(y, g.itertuples()):
        ax.text(r.sh_ext + 0.006, yi + bh / 2, f"{r.sh_ext:.2f}", va="center", fontsize=8)
        ax.text(r.sh_dom + 0.006, yi - bh / 2, f"{r.sh_dom:.2f}", va="center", fontsize=8)
        ax.text(xmax * 0.995, yi, vfmt.format(r.total_value / 1e9), va="center", ha="right", fontsize=8, color="#333333")
    ax.set_yticks(y); ax.set_yticklabels([textwrap.fill(str(l), 40) for l in labels], fontsize=9); ax.set_xlim(0, xmax)
    ax.set_xlabel("Share in export value (value-weighted); right margin = total exports of the row", fontsize=10)
    h, l = ax.get_legend_handles_labels()
    fig.legend(h, l, frameon=False, fontsize=9, loc="lower center", ncol=2, bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(rect=(0, 0.5 / fig.get_figheight(), 1, 1))   # leave a strip under the x-label for the legend
    W.savefig(fig, fname, gdir)


def origin_table_and_heatmap(dd: pd.DataFrame, by: str, fname: str, gdir: Path, tdir: Path, order=None, min_share=0.01):
    """Heat map (foreign share; sub-sectors >= min_share) + two-panel table (composition / foreign share)."""
    tot = dd.groupby(by)["value"].sum()
    cols = [c for c in (order or list(tot.sort_values(ascending=False).index)) if c in tot.index]
    g = dd.groupby(["country_orig", by]).agg(v=("value", "sum"), e=("val_ext", "sum")).reset_index()
    comp = g.pivot(index="country_orig", columns=by, values="v").reindex(columns=cols).fillna(0.0).sort_index()
    fsh = (g.pivot(index="country_orig", columns=by, values="e").reindex(columns=cols) / comp.replace(0, np.nan)).sort_index()
    ovs = dd.groupby("country_orig")[["val_ext", "value"]].sum()
    comp_pct = 100 * comp.div(comp.sum(axis=1), axis=0)
    all_comp = 100 * comp.sum(axis=0) / comp.values.sum()
    all_fsh = 100 * g.groupby(by)["e"].sum().reindex(cols) / g.groupby(by)["v"].sum().reindex(cols)
    keep = [c for c in cols if tot[c] / tot.sum() >= min_share]
    wide = len(cols) > 6   # many sub-sectors: sub-sectors on the rows, origins on the columns
    if keep:
        hm = (100 * fsh[keep]).reindex((ovs["val_ext"] / ovs["value"]).sort_values(ascending=False).index)
        if wide:
            W.heatmap(hm.T, fname, gdir, cbar_label="foreign-MNE share of export value (%)", fmt="{:.0f}", vmin=0, vmax=100, cmap="Blues", xlabel="exporting country", ylabel="")
        else:
            W.heatmap(hm, fname, gdir, cbar_label="foreign-MNE share of export value (%)", fmt="{:.0f}", vmin=0, vmax=100, cmap="Blues", xlabel="", ylabel="exporting country")

    def row(lab, vals, extra):
        return W.tex_escape(str(lab)) + " & " + " & ".join("--" if pd.isna(v) else f"{v:.1f}" for v in vals) + f" & {extra:.1f}" + r" \\"

    fsh_all = 100 * ovs["val_ext"] / ovs["value"]
    if not wide:
        ncol = len(cols) + 1
        lines = [rf"\begin{{tabular}}{{l{'r' * ncol}}}", r"\toprule", "Origin & " + " & ".join(W.tex_escape(str(c)) for c in cols) + r" & All \\", r"\midrule",
                 rf"\multicolumn{{{ncol + 1}}}{{l}}{{\textit{{Panel A: composition of the origin's exports in the scope, \% (rows sum to 100)}}}} \\"]
        for o in comp_pct.index:
            lines.append(row(o, comp_pct.loc[o].values, 100.0))
        lines.append(row("All origins", all_comp.values, 100.0))
        lines += [r"\midrule", rf"\multicolumn{{{ncol + 1}}}{{l}}{{\textit{{Panel B: foreign-MNE share of export value within the cell, \%}}}} \\"]
        for o in fsh.index:
            lines.append(row(o, (100 * fsh.loc[o]).values, fsh_all.loc[o]))
        lines.append(row("All origins", all_fsh.values, 100 * ovs["val_ext"].sum() / ovs["value"].sum()))
        note = ("Pooled 2006--2022. Panel A: share of each sub-sector in the origin's exports within the scope (rows sum to 100). "
                "Panel B: foreign-MNE share of export value in each origin $\\times$ sub-sector cell (`--' = no exports); `All' = the origin's overall foreign-MNE share in the scope.")
    else:
        origins = list(comp_pct.index); ncol = len(origins) + 1
        lines = [rf"\begin{{tabular}}{{l{'r' * ncol}}}", r"\toprule", "Sub-sector & " + " & ".join(origins) + r" & All \\", r"\midrule",
                 rf"\multicolumn{{{ncol + 1}}}{{l}}{{\textit{{Panel A: composition of the origin's exports in the scope, \% (columns sum to 100)}}}} \\"]
        for c in cols:
            lines.append(row(c, comp_pct[c].values, all_comp.loc[c]))
        lines.append(row("All sub-sectors", [100.0] * len(origins), 100.0))
        lines += [r"\midrule", rf"\multicolumn{{{ncol + 1}}}{{l}}{{\textit{{Panel B: foreign-MNE share of export value within the cell, \%}}}} \\"]
        for c in cols:
            lines.append(row(c, (100 * fsh[c]).values, all_fsh.loc[c]))
        lines.append(row("All sub-sectors", fsh_all.reindex(origins).values, 100 * ovs["val_ext"].sum() / ovs["value"].sum()))
        note = ("Pooled 2006--2022. Sub-sectors on the rows, exporting countries on the columns. Panel A: share of each sub-sector in the origin's exports within the scope (columns sum to 100); "
                "`All' = the sub-sector's share of the scope's exports. Panel B: foreign-MNE share of export value in each origin $\\times$ sub-sector cell (`--' = no exports); "
                "`All' = the sub-sector's overall foreign-MNE share; last row = the origin's overall foreign-MNE share in the scope.")
    lines += [r"\bottomrule", rf"\multicolumn{{{ncol + 1}}}{{p{{0.95\textwidth}}}}{{\footnotesize {note}}} \\", r"\end{tabular}"]
    W.write_tex(lines, tdir / f"tab_{fname[4:]}.tex")


def parent_composition_table(dd: pd.DataFrame, by: str, order, path: Path, top: list, hdr: str) -> None:
    dd = dd.copy(); dd["pgrp"] = W.parent_group(dd, top)
    groups = top + ["Other", "Domestic"]
    mat = dd.pivot_table(index=by, columns="pgrp", values="value", aggfunc="sum", fill_value=0.0)
    mat = mat.reindex([o for o in order if o in mat.index]).reindex(columns=[g for g in groups if g in mat.columns], fill_value=0.0)
    tot = dd.groupby(by)["value"].sum().reindex(mat.index)
    W.write_matrix_tex(100 * mat.div(tot, axis=0), path, fmt="{:.1f}", corner=hdr,
                       note=f"Share of the row's export value by parent-country group, percent. {W.PARENT_GROUPS_NOTE.replace('five', 'ten')} The remainder of each row is local (unmatched) firms.")


# ---------------------------------------------------------------------
def four_sectors(cube: pd.DataFrame, fdpy_naics: pd.DataFrame | None) -> None:
    G, T, R = W.outdirs("sectors")
    d = W.mne_flags(cube); d = d[d["value"] > 0].copy()
    d["sector4"] = W.sector4(d["hs2"])
    g, dd = agg(d, "sector4", W.SECTOR_ORDER, min_share=0)
    leads = lead_parents(dd, "sector4", 3)
    note = ("Agriculture = HS 01--24; Mining \\& fuels = HS 25--27" + (" and 71 (precious metals and stones)" if W.MINING_INCLUDES_HS71 else "")
            + "; Manufacturing = HS 28--97 (excl.\\ 71); Rest = HS 98--99, chapter 00 and unclassifiable codes. Services are not observable in customs merchandise data. Pooled 2006--2022, nine LAC origins.")
    write_split_table(g, "sector4", "Sector", T / "tab_wp2_four_sectors.tex", leads, note)
    hbar_2def(g, g["sector4"], "fig_wp2_four_sectors", G)
    origin_table_and_heatmap(dd, "sector4", "fig_wp2_origin_x_sector", G, T, W.SECTOR_ORDER, min_share=0)
    dd["dest_region"] = dd["country_dest"].map(W.classify_region)
    e = dd[dd["owner_type"].isin(["ext", "ext_unknown"])]
    m = pd.crosstab(e["sector4"], e["dest_region"], values=e["value"], aggfunc="sum").fillna(0.0).reindex(W.SECTOR_ORDER).reindex(columns=W.REGION_ORDER, fill_value=0.0)
    W.write_matrix_tex(100 * m.div(m.sum(axis=1), axis=0), T / "tab_wp2_sector_x_destregion_foreign.tex", fmt="{:.1f}", corner="Sector / Destination region",
                       row_total=m.sum(axis=1) / 1e9, note="Foreign-MNE exports: destination mix of each sector, row percentages; last column = row total, USD bn.")
    print("\n=== four sectors:\n" + g[["sector4", "total_value", "val_total", "sh_ext", "sh_dom", "n_hs6"]].to_string())
    if fdpy_naics is not None:
        f = fdpy_naics[(~fdpy_naics["country_orig"].isin(W.excluded_origins())) & (fdpy_naics["value_fob"] > 0)]
        m_ = f["m_dnb" if W.CONVENTION == "sf" else "m_fr"].astype(bool)
        n2 = pd.to_numeric(f["naics_aff_2"], errors="coerce")
        cat = pd.Series("goods-producing or unknown", index=f.index, dtype="object")
        cat[n2.between(42, 45)] = "wholesale / retail trade (42--45)"
        cat[n2.between(48, 49)] = "transport, logistics (48--49)"
        cat[n2.between(51, 56)] = "information, finance, professional, holdings (51--56)"
        cat[n2.between(61, 92)] = "other services (61--92)"
        mm = f[m_].groupby(cat[m_])["value_fob"].sum(); mm = mm / mm.sum()
        lines = [r"\begin{tabular}{lr}", r"\toprule", r"NAICS sector of the matched exporting affiliate & \% of matched export value \\", r"\midrule"]
        for k, v in mm.sort_values(ascending=False).items():
            lines.append(f"{W.tex_escape(k)} & {100 * v:.1f} \\\\")
        lines += [r"\bottomrule", r"\multicolumn{2}{p{0.9\textwidth}}{\footnotesize Memo. Customs data record goods; `services' can only be approached through the affiliate's own industry code. Matched exporters whose NAICS is a trade, logistics, finance or holding code export goods produced elsewhere in the group or bought from local suppliers.}} \\", r"\end{tabular}"]
        W.write_tex(lines, T / "memo_wp2_services.tex")
        print(f"   memo: service-NAICS affiliates = {100 * mm.drop('goods-producing or unknown', errors='ignore').sum():.1f}% of matched export value")


def sector_subclassifications(cube: pd.DataFrame, cls: pd.DataFrame, scope: str) -> None:
    G, T, R = W.outdirs(scope)
    d = W.scope_filter(W.mne_flags(cube), scope); d = d[d["value"] > 0].copy()
    if len(d) < 500:
        print(f"   [{scope}] too few rows; skipped"); return
    d = d.merge(cls[["hs07_6d", "bec_enduse", "bec4", "bec4_label", "sitc2", "naics3", "lall2000_category", "agro_input"]], on="hs07_6d", how="left")
    d["hs_section"] = W.hs_section_label(d["hs2"])
    d["bec4_lab"] = d["bec4"].astype(str).str.cat(d["bec4_label"].astype(str).str.slice(0, 48), sep=" ")
    d.loc[d["bec4"].isna(), "bec4_lab"] = np.nan
    d["sitc2_lab"] = d["sitc2"].map(lambda c: f"{c} {SITC_DIV.get(c, '')}".strip() if isinstance(c, str) else np.nan)
    d["naics3_lab"] = d["naics3"].map(lambda c: NAICS3.get(c, f"{c}") if isinstance(c, str) else np.nan)
    d["inputs"] = np.where(d["agro_input"] == 1, "Agricultural inputs", "Agricultural output (food, fibres, beverages)")
    top = W.top_parents(d)
    tot = d["value"].sum()
    label = W.SCOPE_LABEL[scope].replace("\\\\&", "\\&")
    note = f"{label}, pooled 2006--2022, nine LAC origins."
    print(f"\n=== {scope}: ${tot / 1e9:,.1f} bn; foreign {d['val_ext'].sum() / tot:.3f}, domestic {d['val_dom'].sum() / tot:.3f}; top parents {top}")
    SPLITS = [("hs_section", "HS section", W.HS_SECTION_ORDER), ("bec_enduse", "BEC end use", W.ENDUSE_ORDER), ("bec4_lab", "BEC Rev.\\,4 category", None),
              ("sitc2_lab", "SITC Rev.\\,3 division", None), ("naics3_lab", "NAICS 3-digit (product-based)", None), ("lall2000_category", "Lall (2000) category", None)]
    if scope == "agro":
        SPLITS.append(("inputs", "Inputs vs output", ["Agricultural inputs", "Agricultural output (food, fibres, beverages)"]))
    for col, hdr, order in SPLITS:
        g, dd = agg(d, col, order)
        if len(g) == 0:
            continue
        stem = col.replace("_lab", "")
        leads = lead_parents(dd, col, 3)
        write_split_table(g, col, hdr, T / f"tab_wp2_{stem}.tex", leads, note)
        hbar_2def(g, g[col], f"fig_wp2_{stem}", G)
        origin_table_and_heatmap(dd, col, f"fig_wp2_origin_x_{stem}", G, T, list(g[col]))
        parent_composition_table(dd, col, list(g[col]), T / f"tab_wp2_{stem}_by_parent.tex", top, hdr)
        print(f"   {hdr:28s}: " + "; ".join(f"{str(r[col])[:28]} ext {r['sh_ext']:.2f}/dom {r['sh_dom']:.2f} ({100 * r['sh_of_scope']:.0f}%)" for _, r in g.head(6).iterrows()))
    # cross: HS section x BEC end use
    dd = d.dropna(subset=["bec_enduse"])
    if len(dd) == 0 or dd["value"].sum() <= 0:
        print(f"   [{scope}] no BEC-classified value; cross tables skipped"); return
    m = pd.crosstab(dd["hs_section"], dd["bec_enduse"], values=dd["value"], aggfunc="sum").fillna(0.0)
    m = m.reindex([s for s in W.HS_SECTION_ORDER if s in m.index]).reindex(columns=[c for c in W.ENDUSE_ORDER if c in m.columns])
    e = pd.crosstab(dd["hs_section"], dd["bec_enduse"], values=dd["val_ext"], aggfunc="sum").reindex_like(m)
    W.write_matrix_tex(m / 1e9, T / "tab_wp2_section_x_enduse_value.tex", fmt="{:,.1f}", corner="HS section / BEC end use", row_total=m.sum(axis=1) / 1e9, col_total=m.sum(axis=0) / 1e9, note="Export value, USD bn. " + note)
    W.write_matrix_tex(100 * e / m.replace(0, np.nan), T / "tab_wp2_section_x_enduse_foreignshare.tex", fmt="{:.1f}", corner="HS section / BEC end use", note="Foreign-MNE share of export value, percent. " + note)
    if scope == "agro":
        inp = d[d["agro_input"] == 1].groupby("hs07_6d").agg(value=("value", "sum"), e=("val_ext", "sum"), m=("val_dom", "sum")).sort_values("value", ascending=False).head(20)
        inp = inp.join(cls.set_index("hs07_6d")["hs6_desc"])
        inp["hs6_desc"] = inp["hs6_desc"].where(inp["hs6_desc"].notna(), W.hs6_desc_fallback(pd.Series(inp.index, index=inp.index)))
        lines = [r"\begin{tabular}{@{}l p{7.5cm} r r r@{}}", r"\toprule", r"HS6 & Description & \$bn & Foreign (\%) & Domestic (\%) \\", r"\midrule"]
        for h, r in inp.iterrows():
            lines.append(f"{h} & {W.tex_escape(str(r['hs6_desc']))} & {r['value'] / 1e9:,.2f} & {100 * r['e'] / r['value']:.0f} & {100 * r['m'] / r['value']:.0f} \\\\")
        lines += [r"\bottomrule", r"\multicolumn{5}{p{0.9\textwidth}}{\footnotesize Top-20 HS6 lines flagged as agricultural inputs (fertilisers, agrochemicals, seeds for sowing, animal feed, agricultural machinery, live animals); Foreign / Domestic = MNE shares of the line's export value, percent.} \\", r"\end{tabular}"]
        W.write_tex(lines, T / "tab_wp2_top_inputs_hs6.tex")


def main():
    cube = W.build_cube(); cls = W.build_classifications()
    try:
        fn = W.load_fdpy()[["country_orig", "value_fob", "m_dnb", "m_fr", "naics_aff_2"]]
    except Exception:  # noqa: BLE001
        fn = None
    four_sectors(cube, fn)
    for scope in W.SCOPES_SECTORS:
        sector_subclassifications(cube, cls, scope)
    print("\n>>> wp2 done")


if __name__ == "__main__":
    main()
