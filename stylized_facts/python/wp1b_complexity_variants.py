"""
wp1b_complexity_variants.py  --  Volpe item 1b
==============================================

Figure 2 (foreign vs domestic MNE share by product-sophistication quintile) redrawn for
alternative sophistication measures, in particular the TARIFF-BASED IMPORT-DEMAND
ELASTICITIES of Fontagne, Guimbard & Orefice (2022, JIE 137: 103593) -- CEPII
"Product-Level Trade Elasticities", HS6 rev. 2007, downloaded to data/raw/ProTEE_0_1.csv.
Volpe's reading: more substitutable (a larger elasticity in absolute value) = less complex,
so the foreign-MNE share should FALL across |sigma_FGO| quintiles while it RISES across PCI
quintiles.

Measures (all at HS6): PCI (document's Figure 2, for reference) · |sigma| FGO 2022 ·
sigma Broda-Weinstein (Ignacio's appendix) · upstreamness (Antras-Chor) · quality ladder
(Khandelwal) · RHCI (UNCTAD) · Rauch (1999) classification · BEC end use.

Same geometry as sf3_products.py grouped_vbar_2def (navy foreign / gray domestic), same
unweighted HS6 quintiles, same ODPY regression ladder as Tables A.4/A.5 with the FGO
elasticity added.

Outputs (output/wp/<scope>/):
  Graphs/fig_wp1b_<measure>_quintile        one Figure-2 clone per measure
  Graphs/fig_wp1b_panel_quintiles           all continuous measures in one 2x3 panel
  Tables/tab_wp1b_quintile_shares.tex       foreign / domestic share by quintile, all measures
  Tables/tab_wp1b_rauch.tex, tab_wp1b_bec.tex
  Tables/tab_wp1b_measure_corr.tex          correlations across measures (HS6, value-weighted)
  Regressions/reg_wp1b_odpy_fgo.tex         A.4 ladder with |sigma| FGO (+ PCI, upstreamness)
"""
from __future__ import annotations

import gc
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyfixest as pf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_common as W  # noqa: E402

SCOPES = W.SCOPES_ALL
QLBL = {1: "Q1", 2: "Q2", 3: "Q3", 4: "Q4", 5: "Q5"}
MEASURES = [  # (column, short label (figures), axis label, expected sign of the foreign gradient)
    ("complexity",     "PCI",            "PCI quintile (1 = lowest complexity, 5 = highest)",                         "+"),
    ("sigma_fgo_abs",  "|σ| FGO (2022)", "|import-demand elasticity| quintile, FGO 2022 (1 = least substitutable)",   "−"),
    ("sigma_bw",       "σ Broda–Weinstein", "σ Broda–Weinstein quintile (1 = least substitutable)",                   "−"),
    ("upstreamness",   "Upstreamness",   "Upstreamness quintile (Antràs–Chor; 1 = closest to final demand)",         "?"),
    ("quality_ladder", "Quality ladder", "Quality-ladder quintile (Khandelwal; 1 = shortest)",                       "+"),
    ("rhci",           "RHCI",           "RHCI quintile (UNCTAD; 1 = lowest human-capital intensity)",               "+"),
]
TEX_LABEL = {  # pdflatex-safe versions of the short labels (Greek letters in math mode)
    "PCI": "PCI", "|σ| FGO (2022)": r"$|\sigma|$ FGO (2022)", "σ Broda–Weinstein": r"$\sigma$ Broda--Weinstein",
    "Upstreamness": "Upstreamness", "Quality ladder": "Quality ladder", "RHCI": "RHCI",
}
RAUCH_ORDER = ["Differentiated", "Reference-priced", "Homogeneous (exchange)"]
MIN_HS6_MEASURE = 30   # a measure enters a scope's quintile figures/tables only with >= 30 classified HS6 products


def _insufficient(ax, short, n):
    ax.set_axis_off()
    ax.text(0.5, 0.5, f"{short}\nnot shown: only {n} HS6 products\nwith this measure in the scope", ha="center", va="center", fontsize=10, color="#555555", transform=ax.transAxes)


def hs6_cross_section(d: pd.DataFrame, cls: pd.DataFrame) -> pd.DataFrame:
    hs6 = d.groupby("hs07_6d", as_index=False).agg(total_value=("value", "sum"), val_ext=("val_ext", "sum"),
                                                     val_dom=("val_dom", "sum"), val_total=("val_total", "sum"))
    hs6 = hs6.merge(cls[["hs07_6d"] + [m[0] for m in MEASURES] + ["rauch", "bec_enduse", "hs6_desc"]],
                    on="hs07_6d", how="left")
    for k in ("ext", "dom", "total"):
        hs6[f"sh_{k}"] = hs6[f"val_{k}"] / hs6["total_value"]
    return hs6


def aggregate(hs6: pd.DataFrame, by: str, order=None) -> pd.DataFrame:
    g = hs6.dropna(subset=[by]).groupby(by, as_index=False).agg(
        total_value=("total_value", "sum"), val_ext=("val_ext", "sum"), val_dom=("val_dom", "sum"),
        val_total=("val_total", "sum"), n_hs6=("hs07_6d", "nunique"))
    for k in ("ext", "dom", "total"):
        g[f"sh_{k}"] = g[f"val_{k}"] / g["total_value"]
    if order is not None:
        g = g.set_index(by).reindex([o for o in order if o in set(g[by])]).reset_index()
    return g


def vbar_2def(ax, g: pd.DataFrame, xlabels, xlabel: str, ymax: float = 0.8, fontsize=8):
    """Ignacio's grouped_vbar_2def, drawn on a given axis."""
    n = len(g); x = np.arange(n); bw = 0.38
    ax.bar(x - bw / 2, g["sh_ext"], bw, color=W.C_MNE_EXT, edgecolor=W.C_MNE_EXT, label="Foreign MNEs")
    ax.bar(x + bw / 2, g["sh_dom"], bw, color=W.C_MNE_DOM, edgecolor="#9e9e9e", linewidth=0.5, label="Domestic MNEs")
    for xi, r in zip(x, g.itertuples()):
        ax.text(xi - bw / 2, r.sh_ext + 0.01, f"{r.sh_ext:.2f}", ha="center", fontsize=fontsize)
        ax.text(xi + bw / 2, r.sh_dom + 0.01, f"{r.sh_dom:.2f}", ha="center", fontsize=fontsize)
    ax.set_xticks(x); ax.set_xticklabels([xlabels.get(v, str(v)) if isinstance(xlabels, dict) else str(v) for v in g.iloc[:, 0]])
    ax.set_xlabel(xlabel, fontsize=fontsize + 1); ax.set_ylabel("Share in export value (value-weighted)", fontsize=fontsize + 1)
    ax.set_ylim(0, ymax)


def histograms(hs6: pd.DataFrame, G: Path, nbins: int = 25) -> None:
    """For every continuous measure: the distribution of export value across measure bins, stacked
    by owner type (foreign / domestic / local), with the foreign-MNE share of each bin as a line,
    and the number of HS6 products per bin. One figure per measure and a 2x3 panel."""
    fig_p, axes_p = plt.subplots(3, 2, figsize=(11, 13))
    tot = hs6["total_value"].sum()
    for (col, short, xlabel, sign), axp in zip(MEASURES, axes_p.ravel()):
        q = hs6.dropna(subset=[col]).copy()
        if len(q) < MIN_HS6_MEASURE:
            _insufficient(axp, short, len(q)); continue
        lo, hi = q[col].quantile(0.005), q[col].quantile(0.995)
        q[col] = q[col].clip(lo, hi)
        edges = np.linspace(lo, hi, nbins + 1)
        q["bin"] = pd.cut(q[col], edges, include_lowest=True, labels=False)
        g = q.groupby("bin").agg(v=("total_value", "sum"), e=("val_ext", "sum"), d=("val_dom", "sum"), n=("hs07_6d", "size")).reindex(range(nbins)).fillna(0.0)
        g["l"] = g["v"] - g["e"] - g["d"]
        mids = 0.5 * (edges[:-1] + edges[1:]); w = (edges[1] - edges[0]) * 0.9
        fig, (ax, ax2) = plt.subplots(1, 2, figsize=(12, 4.3), gridspec_kw={"width_ratios": [3, 2]})
        for a in (ax, axp):
            a.bar(mids, g["e"] / tot, w, color=W.C_MNE_EXT, label="Foreign MNEs")
            a.bar(mids, g["d"] / tot, w, bottom=g["e"] / tot, color=W.C_MNE_DOM, label="Domestic MNEs")
            a.bar(mids, g["l"] / tot, w, bottom=(g["e"] + g["d"]) / tot, color="#e8e8e8", edgecolor="#cccccc", linewidth=0.3, label="Local firms")
            a.set_xlabel(xlabel.split(" quintile")[0].replace("|import-demand elasticity|", "|import-demand elasticity| (FGO 2022)"), fontsize=9)
            a.set_ylabel("share of the scope's export value", fontsize=9)
            ar = a.twinx()
            sh = np.where(g["v"] / tot >= 0.002, g["e"] / g["v"].replace(0, np.nan), np.nan)   # line only where the bin holds >= 0.2% of value
            ar.plot(mids, sh, color="#c8a24a", marker="o", markersize=3, linewidth=1.2, label="foreign-MNE share of the bin")
            ar.set_ylim(0, 1); ar.set_ylabel("foreign-MNE share within bin", fontsize=9, color="#8a6d1f"); ar.tick_params(axis="y", colors="#8a6d1f", labelsize=8)
        ax2.bar(mids, g["n"], w, color=W.C_MNE_DOM, edgecolor="#9e9e9e", linewidth=0.4)
        ax2.set_xlabel("same bins", fontsize=9); ax2.set_ylabel("number of HS6 products", fontsize=9)
        ax.legend(frameon=False, fontsize=8, loc="upper right")
        fig.tight_layout()
        W.savefig(fig, f"fig_wp1b_hist_{col}", G)
        axp.set_title(short, fontsize=12)
    axes_p[0, 0].legend(frameon=False, fontsize=9, loc="upper right")
    fig_p.tight_layout()
    W.savefig(fig_p, "fig_wp1b_panel_hist", G)


def run_scope(cube: pd.DataFrame, cls: pd.DataFrame, scope: str) -> None:
    G, T, R = W.outdirs(scope)
    d = W.scope_filter(W.mne_flags(cube), scope)
    d = d[d["value"] > 0]
    hs6 = hs6_cross_section(d, cls)
    print(f"\n=== scope {scope}: {len(hs6):,} HS6 products; FGO coverage (value) "
          f"{hs6.loc[hs6['sigma_fgo_abs'].notna(), 'total_value'].sum() / hs6['total_value'].sum():.0%}")

    if hs6.dropna(subset=["complexity"]).shape[0] < 25 or hs6.dropna(subset=["sigma_fgo_abs"]).shape[0] < 25:
        print(f"   [{scope}] too few classified HS6 products; skipped"); return

    # --- one Figure-2 clone per measure + a 2x3 panel ----------------------------------------
    rows = []
    fig_p, axes = plt.subplots(3, 2, figsize=(11, 13))
    for (col, short, xlabel, sign), ax in zip(MEASURES, axes.ravel()):
        q = hs6.dropna(subset=[col]).copy()
        if len(q) < MIN_HS6_MEASURE:
            print(f"   {short:18s} only {len(q)} HS6 products with the measure in this scope; not shown")
            _insufficient(ax, short, len(q)); continue
        q["quintile"] = pd.qcut(q[col], 5, labels=False, duplicates="drop") + 1
        g = aggregate(q, "quintile")
        fig, ax1 = plt.subplots(figsize=(8.5, 4.5))
        vbar_2def(ax1, g, QLBL, xlabel); ax1.legend(frameon=False, fontsize=9, loc="upper left")
        W.savefig(fig, f"fig_wp1b_{col}_quintile", G)
        vbar_2def(ax, g, QLBL, xlabel, fontsize=9); ax.set_title(short, fontsize=12)
        for _, r in g.iterrows():
            rows.append(dict(measure=short, quintile=int(r["quintile"]), sh_ext=r["sh_ext"], sh_dom=r["sh_dom"],
                             n_hs6=int(r["n_hs6"]), value=r["total_value"]))
        print(f"   {short:18s} foreign share Q1..Q5: " + " ".join(f"{v:.2f}" for v in g["sh_ext"])
              + f"   (expected gradient {sign})")
    axes[0, 0].legend(frameon=False, fontsize=9, loc="upper left")
    fig_p.tight_layout()
    W.savefig(fig_p, "fig_wp1b_panel_quintiles", G)

    tab = pd.DataFrame(rows)
    piv_e = tab.pivot(index="measure", columns="quintile", values="sh_ext").reindex([m[1] for m in MEASURES])
    piv_d = tab.pivot(index="measure", columns="quintile", values="sh_dom").reindex([m[1] for m in MEASURES])
    lines = [r"\begin{tabular}{lccccc|ccccc}", r"\toprule",
             r" & \multicolumn{5}{c}{Foreign MNE share} & \multicolumn{5}{c}{Domestic MNE share} \\",
             "Measure & " + " & ".join(f"Q{i}" for i in range(1, 6)) + " & " + " & ".join(f"Q{i}" for i in range(1, 6)) + r" \\", r"\midrule"]
    def cell(piv, m, i):
        v = piv.loc[m, i] if (m in piv.index and i in piv.columns) else np.nan
        return "--" if pd.isna(v) else f"{v:.2f}"

    for m in [mm[1] for mm in MEASURES]:
        lines.append(TEX_LABEL.get(m, W.tex_escape(m)) + " & "
                     + " & ".join(cell(piv_e, m, i) for i in range(1, 6)) + " & "
                     + " & ".join(cell(piv_d, m, i) for i in range(1, 6)) + r" \\")
    lines += [r"\bottomrule",
              rf"\multicolumn{{11}}{{p{{0.95\textwidth}}}}{{\footnotesize Value-weighted shares of export value within quintile; quintiles over HS6 products (unweighted); `--' = fewer than {MIN_HS6_MEASURE} HS6 products carry the measure in this scope. "
              r"$|\sigma|$ FGO: absolute value of the tariff-based import-demand elasticity of Fontagn\'e, Guimbard and Orefice (2022), HS6 rev. 2007 (non-significant or positive HS6 estimates replaced by the HS4 average by the source); larger = more substitutable. "
              r"$\sigma$ Broda--Weinstein, upstreamness (Antr\`as--Chor), quality ladder (Khandelwal), RHCI (UNCTAD) as in the document's appendix.}} \\",
              r"\end{tabular}"]
    W.write_tex(lines, T / "tab_wp1b_quintile_shares.tex")

    # --- categorical: Rauch and BEC end use ------------------------------------------------
    for col, order, fname, hdr in (("rauch", RAUCH_ORDER, "rauch", "Rauch (1999) class"),
                                   ("bec_enduse", W.ENDUSE_ORDER, "bec", "BEC end use")):
        g = aggregate(hs6, col, order)
        if len(g) == 0:
            continue
        fig, ax = plt.subplots(figsize=(8.5, 4.5))
        vbar_2def(ax, g, {}, hdr); ax.legend(frameon=False, fontsize=9, loc="upper left")
        W.savefig(fig, f"fig_wp1b_{fname}", G)
        lines = [r"\begin{tabular}{lcccrr}", r"\toprule",
                 f"{hdr} & Foreign & Domestic & MNE total & N HS6 & Value (\\$bn) \\\\", r"\midrule"]
        for _, r in g.iterrows():
            lines.append(f"{W.tex_escape(r[col])} & {r['sh_ext']:.3f} & {r['sh_dom']:.3f} & {r['sh_total']:.3f} & {int(r['n_hs6']):,} & {r['total_value'] / 1e9:,.1f} \\\\")
        lines += [r"\bottomrule", r"\end{tabular}"]
        W.write_tex(lines, T / f"tab_wp1b_{fname}.tex")

    # --- correlations across measures (HS6 cross-section, value-weighted) -------------------
    cols = [m[0] for m in MEASURES]
    labs = [TEX_LABEL[m[1]] for m in MEASURES]
    corr = pd.DataFrame(np.nan, index=labs, columns=labs); nmin, nmax = 10 ** 9, 0

    def wcorr(a, b, w):
        ma, mb = np.average(a, weights=w), np.average(b, weights=w)
        cab = np.average((a - ma) * (b - mb), weights=w)
        return cab / np.sqrt(np.average((a - ma) ** 2, weights=w) * np.average((b - mb) ** 2, weights=w))

    for i, ci in enumerate(cols):
        for j, cj in enumerate(cols):
            x = hs6.dropna(subset=[ci, cj])
            if len(x) < MIN_HS6_MEASURE:
                continue
            corr.iloc[i, j] = wcorr(x[ci].values.astype(float), x[cj].values.astype(float), x["total_value"].values)
            nmin, nmax = min(nmin, len(x)), max(nmax, len(x))
    W.write_matrix_tex(corr, T / "tab_wp1b_measure_corr.tex", fmt="{:.2f}", corner="",
                       note=f"Value-weighted Pearson correlations, pairwise: each cell uses the HS6 products carrying both measures ({nmin:,} to {nmax:,} products; `--' = fewer than {MIN_HS6_MEASURE}).")
    print("   corr(PCI, |σ|FGO) =", f"{corr.iloc[0, 1]:.2f}", "| corr(PCI, σBW) =", f"{corr.iloc[0, 2]:.2f}")

    # --- histograms: full distribution of export value / products over each measure ---------------
    histograms(hs6, G)

    # --- ODPY regression ladder (Table A.4 with FGO) ----------------------------------------
    odpy = d.groupby(["country_orig", "country_dest", "hs07_6d", "year"], as_index=False).agg(
        total_value=("value", "sum"), val_ext=("val_ext", "sum"), val_dom=("val_dom", "sum"), val_total=("val_total", "sum"))
    odpy = odpy.merge(cls[["hs07_6d", "complexity", "upstreamness", "sigma_fgo_abs"]], on="hs07_6d", how="left")
    odpy = odpy.dropna(subset=["complexity", "upstreamness", "sigma_fgo_abs"])
    for k in ("ext", "dom", "total"):
        odpy[f"sh_{k}"] = odpy[f"val_{k}"] / odpy["total_value"]
    odpy["ot"] = odpy["country_orig"] + odpy["year"].astype(str)
    odpy["dt"] = odpy["country_dest"] + odpy["year"].astype(str)
    odpy["odt"] = odpy["country_orig"] + odpy["country_dest"] + odpy["year"].astype(str)
    # standardise |sigma| so the coefficient is per 1 s.d. (PCI is already ~standardised)
    odpy["sigma_fgo_sd"] = (odpy["sigma_fgo_abs"] - odpy["sigma_fgo_abs"].mean()) / odpy["sigma_fgo_abs"].std()
    FE = [("(1)", "country_orig + country_dest + year", {"O", "D", "Y"}),
          ("(2)", "ot + dt", {"OY", "DY"}),
          ("(3)", "odt", {"ODY"})]
    FE_ROWS = [("Origin FE", "O"), ("Destination FE", "D"), ("Year FE", "Y"),
               (r"Origin $\times$ year FE", "OY"), (r"Destination $\times$ year FE", "DY"), (r"Origin $\times$ dest.\ $\times$ year FE", "ODY")]
    PANELS = [(r"Panel A: MNE$_{total}$ share", "sh_total"), (r"Panel B: MNE$_{ext}$ share", "sh_ext"), (r"Panel C: MNE$_{dom}$ share", "sh_dom")]
    REGS = [("Complexity (PCI)", "complexity"), (r"$|\sigma|$ FGO (per s.d.)", "sigma_fgo_sd"), ("Upstreamness", "upstreamness")]
    if len(odpy) < 5000:
        print(f"   [{scope}] too few ODPY cells for the regression ladder ({len(odpy):,}); skipped"); return
    res = {}
    for pi, (plab, dep) in enumerate(PANELS):
        for ci, (tag, fe, _) in enumerate(FE):
            m = W.feols(f"{dep} ~ complexity + sigma_fgo_sd + upstreamness | {fe}", data=odpy, weights="total_value", vcov="hetero")
            b, se, p = m.coef(), m.se(), m.pvalue()
            res[(pi, ci)] = ({v: (float(b[v]), float(se[v]), float(p[v])) for _, v in REGS}, int(m._N))
            print(f"   A.4+FGO {dep:8s} {tag}: " + " ".join(f"{v}={float(b[v]):+.4f}{W.stars(float(p[v]))}" for _, v in REGS))
            del m; gc.collect()
    ncol = len(FE)
    lines = [rf"\begin{{tabular}}{{l{'c' * ncol}}} \hline", " & " + " & ".join(t for t, _, _ in FE) + r" \\ \hline"]
    for pi, (plab, dep) in enumerate(PANELS):
        if pi: lines.append(r"\midrule")
        lines.append(rf"\multicolumn{{{ncol + 1}}}{{l}}{{\textit{{{plab}}}}} \\")
        for lab, v in REGS:
            lines.append(f"{lab} & " + " & ".join(f"{res[(pi, ci)][0][v][0]:.4f}{W.stars(res[(pi, ci)][0][v][2])}" for ci in range(ncol)) + r" \\")
            lines.append(" & " + " & ".join(f"({res[(pi, ci)][0][v][1]:.4f})" for ci in range(ncol)) + r" \\")
    lines.append(r"\hline")
    for lab, key in FE_ROWS:
        lines.append(f"{lab} & " + " & ".join(r"$\checkmark$" if key in FE[ci][2] else "" for ci in range(ncol)) + r" \\")
    lines.append("Observations & " + " & ".join(f"{res[(0, ci)][1]:,}" for ci in range(ncol)) + r" \\")
    lines += [r"\hline", rf"\multicolumn{{{ncol + 1}}}{{p{{0.9\textwidth}}}}{{\footnotesize Origin-destination-product-year cells; dep.\ var.\ MNE value share; weighted by total trade value; robust (HC1) SE. "
              r"$|\sigma|$ FGO standardised (mean 0, s.d.\ 1). *** p$<$0.01, ** p$<$0.05, * p$<$0.1}} \\", r"\end{tabular}"]
    W.write_tex(lines, R / "reg_wp1b_odpy_fgo.tex")


def main():
    cube = W.build_cube()
    cls = W.build_classifications()
    for scope in SCOPES:
        run_scope(cube, cls, scope)
    print("\n>>> wp1b done")


if __name__ == "__main__":
    main()
