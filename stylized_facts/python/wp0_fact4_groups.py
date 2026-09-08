"""
wp0_fact4_groups.py -- the document's Fact 4 exhibits (Figures 5 and 6), reproduced on the current base
======================================================================================================

Figure 5  Foreign-MNE export value and parent counts by global affiliate-network size
          (bins 1 / 2-10 / 11-100 / >100 affiliates, as in sf6_mne_groups.py). Network size comes from
          data/intermediate/wp/parent_network_size.dta (src/16: one row per parent name, max
          total_affiliates in the Orbis+D&B roster), merged on the parent name key used everywhere
          (upper(trim(coalesce(ent_name_par, globalultimatebusinessname)))).
Figure 6  Product-level export concentration (value-weighted mean HHI across HS6): naive (each
          exporting Tax ID a firm) -> affiliates of the same parent grouped within a country -> grouped
          across countries; two panels (all HS6; MNE-intensive HS6 = matched firms >= 50% of the product).
          Same construction as nsf_product_conc.py.

Both for scope "all" (the document) and "agro". Outputs: output/wp/<scope>/Graphs/fig_wp0_fig5_network,
fig_wp0_fig6_hhi and the numbers behind them (Tables/tab_wp0_fig5_network.tex, tab_wp0_fig6_hhi.tex).
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyreadstat

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_common as W  # noqa: E402

NET_DTA = W.WP_INT / "parent_network_size.dta"
SCOPES = ["all", "agro"]
EDGES = [0, 1, 10, 100, np.inf]
BINLAB = ["1", "2--10", "11--100", "$>$100"]
MID = "#c8a24a"


def load_firm_level() -> pd.DataFrame:
    f = W.load_fdpy()
    f = f[(~f["country_orig"].isin(W.excluded_origins())) & (f["value_fob"] > 0)].copy()
    f["hs2"] = f["hs07_6d"].str[:2]
    m = f["m_dnb" if W.CONVENTION == "sf" else "m_fr"].astype(bool)
    par = f["iso3_parent"].fillna("").astype(str)
    f["is_dom"] = m & (par == f["country_orig"])
    f["is_ext"] = m & ~f["is_dom"] if W.CONVENTION == "sf" else (m & (par != "") & (par != f["country_orig"]))
    f["matched"] = m
    f["pkey"] = f["parent_key"].fillna("").astype(str).str.upper().str.strip()
    return f


def fig5_network(f: pd.DataFrame, G: Path, T: Path, scope: str) -> None:
    net, _ = pyreadstat.read_dta(str(NET_DTA), encoding="latin1")
    net["pkey"] = net["name_parent_adj"].astype(str).str.upper().str.strip()
    net = net.groupby("pkey", as_index=False).agg(total_affiliates=("total_affiliates", "max"), n_countries=("n_countries", "max"))
    ext = f[f["is_ext"] & (f["pkey"] != "")]
    par = ext.groupby("pkey", as_index=False).agg(export_value=("value_fob", "sum"))
    par = par.merge(net, on="pkey", how="left")
    par["has_network"] = par["total_affiliates"].notna()
    cov_n = par["has_network"].mean(); cov_v = par.loc[par["has_network"], "export_value"].sum() / par["export_value"].sum()
    pa = par[par["has_network"]].copy()
    b = pd.cut(pa["total_affiliates"], EDGES, labels=BINLAB, right=True, include_lowest=True)
    g = pa.groupby(b, observed=True).agg(npar=("export_value", "size"), v=("export_value", "sum"))
    g["sv"] = g["v"] / g["v"].sum(); g["sp"] = g["npar"] / g["npar"].sum()
    fig, ax = plt.subplots(figsize=(7, 4.2))
    x = np.arange(len(g))
    ax.bar(x - 0.2, g["sv"], 0.4, color=W.C_MNE_EXT, label="share of export value")
    ax.bar(x + 0.2, g["sp"], 0.4, color=W.C_MNE_DOM, label="share of parents")
    ax.set_xticks(x); ax.set_xticklabels(g.index)
    ax.set_xlabel("Parent global affiliate count"); ax.set_ylabel("Share")
    ax.legend(frameon=False)
    for xi, v in zip(x - 0.2, g["sv"]):
        ax.text(xi, v + 0.01, f"{v:.0%}", ha="center", va="bottom", fontsize=8)
    for xi, v in zip(x + 0.2, g["sp"]):
        ax.text(xi, v + 0.01, f"{v:.0%}", ha="center", va="bottom", fontsize=8)
    W.savefig(fig, "fig_wp0_fig5_network", G)
    lines = [r"\begin{tabular}{lrrrr}", r"\toprule", r"Global affiliate count & Parents & Share of parents (\%) & Export value (\$bn) & Share of value (\%) \\", r"\midrule"]
    for lab, r in g.iterrows():
        lines.append(f"{lab} & {int(r['npar']):,} & {100 * r['sp']:.1f} & {r['v'] / 1e9:,.1f} & {100 * r['sv']:.1f} \\\\")
    lines += [r"\midrule", f"All parents with a network record & {int(g['npar'].sum()):,} & 100 & {g['v'].sum() / 1e9:,.1f} & 100 \\\\", r"\bottomrule",
              rf"\multicolumn{{5}}{{p{{0.9\textwidth}}}}{{\footnotesize Foreign-MNE parents (parent name key) exporting from the nine origins; {100 * cov_n:.0f}\% of parents and {100 * cov_v:.0f}\% of foreign-MNE export value have a matched global-network record (Orbis $\cup$ D\&B roster, src/16). Network size = number of distinct worldwide affiliates.}} \\", r"\end{tabular}"]
    W.write_tex(lines, T / "tab_wp0_fig5_network.tex")
    print(f"   [{scope}] Fig 5: " + ", ".join(f"{lab}: {100 * r['sv']:.0f}% of value / {100 * r['sp']:.0f}% of parents" for lab, r in g.iterrows())
          + f" | network coverage {cov_n:.0%} of parents, {cov_v:.0%} of value")


def fig6_hhi(f: pd.DataFrame, G: Path, T: Path, scope: str) -> None:
    df = f.groupby(["hs07_6d", "country_orig", "Tax_ID"], as_index=False).agg(value=("value_fob", "sum"), matched=("matched", "max"), pkey=("pkey", "first"))
    has_par = (df["matched"] == 1) & (df["pkey"] != "")
    tin = df["country_orig"] + "|" + df["Tax_ID"].astype(str)
    df["u_naive"] = tin
    df["u_within"] = np.where(has_par, df["country_orig"] + "|P|" + df["pkey"], tin)
    df["u_cross"] = np.where(has_par, "P|" + df["pkey"], tin)
    hs_tot = df.groupby("hs07_6d")["value"].sum().rename("hstot")

    def conc(unit):
        g = df.groupby(["hs07_6d", unit])["value"].sum().reset_index().merge(hs_tot, on="hs07_6d")
        g["sh"] = g["value"] / g["hstot"]
        return pd.concat([g.assign(s2=g["sh"] ** 2).groupby("hs07_6d")["s2"].sum().rename("hhi"),
                          g.groupby("hs07_6d")["sh"].max().rename("top1"), g.groupby("hs07_6d").size().rename("nfirm")], axis=1)

    M = conc("u_naive").join(conc("u_within"), rsuffix="_w").join(conc("u_cross"), rsuffix="_c").join(hs_tot)
    mne_sh = (df[has_par].groupby("hs07_6d")["value"].sum() / hs_tot).reindex(M.index).fillna(0)
    panels = [("All products", M), (r"MNE-intensive products (MNE $\geq$ 50\% of exports)", M[mne_sh >= 0.5])]

    def wm(d, col): return float(np.average(d[col], weights=d["hstot"]))
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.3), sharey=True)
    rows = []
    for ax, (title, d) in zip(axes, panels):
        vals = [wm(d, "hhi"), wm(d, "hhi_w"), wm(d, "hhi_c")]
        ax.bar(range(3), vals, color=[W.C_MNE_DOM, MID, W.C_MNE_EXT], width=0.6)
        ax.set_xticks(range(3)); ax.set_xticklabels(["Naive\n(each affiliate\na firm)", "Grouped by parent\nwithin country", "Grouped by parent\nacross countries"], fontsize=9)
        ax.set_title(f"{title.replace(chr(92) + 'geq', '>=').replace(chr(92) + '%', '%').replace('$', '')}\n({len(d):,} HS6, {d['hstot'].sum() / M['hstot'].sum():.0%} of value)", fontsize=10)
        for i, v in enumerate(vals):
            ax.text(i, v + 0.004, f"{v:.3f}", ha="center", fontsize=9)
        ax.set_ylim(0, max(vals) * 1.18)
        rows.append((title, len(d), d["hstot"].sum() / M["hstot"].sum(), vals, [wm(d, "top1"), wm(d, "top1_w"), wm(d, "top1_c")],
                     [wm(d.assign(e=1 / d["hhi"]), "e"), wm(d.assign(e=1 / d["hhi_w"]), "e"), wm(d.assign(e=1 / d["hhi_c"]), "e")]))
    axes[0].set_ylabel("Value-weighted mean product HHI")
    fig.tight_layout()
    W.savefig(fig, "fig_wp0_fig6_hhi", G)
    lines = [r"\begin{tabular}{llrrr}", r"\toprule", r"Sample & Measure & Naive & Within country & Across countries \\", r"\midrule"]
    for title, n, vsh, hhi, top1, eff in rows:
        lines.append(rf"\multicolumn{{5}}{{l}}{{\textit{{{title}: {n:,} HS6, {100 * vsh:.0f}\% of value}}}} \\")
        lines.append(" & Mean HHI & " + " & ".join(f"{v:.3f}" for v in hhi) + r" \\")
        lines.append(" & Mean top-exporter share & " + " & ".join(f"{100 * v:.1f}\\%" for v in top1) + r" \\")
        lines.append(" & Effective number of exporters (1/HHI) & " + " & ".join(f"{v:.1f}" for v in eff) + r" \\")
    lines += [r"\bottomrule", r"\multicolumn{5}{p{0.9\textwidth}}{\footnotesize Value-weighted means across HS6 products (nine origins, Ecuador excluded). Naive: each exporting affiliate (Tax ID) is a firm; then affiliates of the same global parent are grouped within a country and across countries.}} \\", r"\end{tabular}"]
    W.write_tex(lines, T / "tab_wp0_fig6_hhi.tex")
    for title, n, vsh, hhi, top1, eff in rows:
        print(f"   [{scope}] Fig 6 {title[:22]}: HHI {hhi[0]:.3f} -> {hhi[1]:.3f} -> {hhi[2]:.3f}; top1 {top1[0]:.1%} -> {top1[2]:.1%}; eff firms {eff[0]:.1f} -> {eff[2]:.1f}")


def main():
    f = load_firm_level()
    for scope in SCOPES:
        G, T, R = W.outdirs(scope)
        d = f if scope == "all" else f[f["hs2"].astype(int).between(1, 24)]
        print(f"\n=== scope {scope}: {len(d):,} firm-cells, ${d['value_fob'].sum() / 1e9:,.1f} bn")
        fig5_network(d, G, T, scope)
        fig6_hhi(d, G, T, scope)
    print("\n>>> wp0 (Fact 4 reproductions) done")


if __name__ == "__main__":
    main()
