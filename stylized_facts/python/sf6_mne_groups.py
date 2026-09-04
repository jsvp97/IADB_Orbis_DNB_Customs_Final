"""
SF6 --- Large multinational groups dominate exports.

Main exhibit: export value is concentrated in parents with large global
affiliate networks (fig_sf6_network).
Subpoint: product markets are more concentrated than a firm-by-firm count
implies, because one MNE exports through many nominally-separate affiliates
(within a country and across countries) -> fig_sf6_hhi (all vs MNE-intensive).
Appendix: parent-level regression of export value on network size.

Reads caches from nsf_prep.py / nsf_product_conc.py. Writes into the MAIN
Stylized_Facts doc structure (2_Output + Overleaf mirror).
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (INT, GRAPHS, REGS, OVERLEAF_SF, C_MNE_EXT, C_MNE_DOM,
                     ensure_dir, save_figure)  # noqa: E402
import pyfixest as pf  # noqa: E402

G6 = GRAPHS / "SF6_MNEGroups"; OL_G6 = OVERLEAF_SF / "Graphs" / "SF6_MNEGroups"
R6 = REGS / "SF6_MNEGroups";   OL_R6 = OVERLEAF_SF / "Regressions" / "SF6_MNEGroups"
for d in (G6, OL_G6, R6, OL_R6): ensure_dir(d)
NAVY, MID, GRAY = C_MNE_EXT, "#c8a24a", C_MNE_DOM

# =====================================================================
# 1. Network-size main figure
# =====================================================================
par = pd.read_parquet(INT / "nsf_parent.parquet")
pa = par[par["has_network"]].copy()
pa["export_value"] = pa["export_value"].astype(float)
edges = [0, 1, 10, 100, np.inf]; lab = ["1", "2--10", "11--100", "$>$100"]
b = pd.cut(pa["total_affiliates"], edges, labels=lab, right=True, include_lowest=True)
g = pa.groupby(b, observed=True).agg(npar=("export_value", "size"), v=("export_value", "sum"))
g["sv"] = g.v / g.v.sum(); g["sp"] = g.npar / g.npar.sum()

fig, ax = plt.subplots(figsize=(7, 4.2))
x = np.arange(len(g))
ax.bar(x - 0.2, g["sv"], 0.4, color=NAVY, label="share of export value")
ax.bar(x + 0.2, g["sp"], 0.4, color=GRAY, label="share of parents")
ax.set_xticks(x); ax.set_xticklabels(g.index)
ax.set_xlabel("Parent global affiliate count"); ax.set_ylabel("Share")
ax.legend(frameon=False)
for xi, v in zip(x - 0.2, g["sv"]):
    ax.text(xi, v + 0.01, f"{v:.0%}", ha="center", va="bottom", fontsize=8)
save_figure(fig, "fig_sf6_network", G6, OL_G6)
print("network bins (share value):", {k: round(v, 3) for k, v in g["sv"].items()})

# =====================================================================
# 2. Product-concentration HHI: naive -> within -> across countries
# =====================================================================
conc = pd.read_parquet(INT / "nsf_hs_conc.parquet")
firm = pd.read_parquet(INT / "nsf_hs_firm.parquet")
has_par = (firm["matched"] == 1) & firm["parent"].notna()
mne_sh = (firm[has_par].groupby("hs")["value"].sum()
          / firm.groupby("hs")["value"].sum()).rename("mne_sh")
conc = conc.merge(mne_sh, on="hs", how="left")
conc["mne_sh"] = conc["mne_sh"].fillna(0.0)

def wm(d, col): return float(np.average(d[col], weights=d["hstot"]))
levels = ["hhi", "hhi_w", "hhi_c"]
xlab = ["naive\n(each affiliate)", "group within\ncountry", "group across\ncountries"]
panels = [("All products", conc), ("MNE-intensive products", conc[conc["mne_sh"] >= 0.5])]

fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.3), sharey=True)
for ax, (title, d) in zip(axes, panels):
    vals = [wm(d, c) for c in levels]
    ax.bar(range(3), vals, color=[GRAY, MID, NAVY], width=0.6)
    ax.set_xticks(range(3)); ax.set_xticklabels(xlab, fontsize=9)
    ax.set_title(f"{title}\n({len(d):,} HS6, {d.hstot.sum()/conc.hstot.sum():.0%} of value)", fontsize=10)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.004, f"{v:.3f}", ha="center", fontsize=9)
    ax.set_ylim(0, max(vals) * 1.18)
axes[0].set_ylabel("Value-weighted mean product HHI")
save_figure(fig, "fig_sf6_hhi", G6, OL_G6)
for title, d in panels:
    print(f"HHI {title}: naive {wm(d,'hhi'):.3f} -> within {wm(d,'hhi_w'):.3f} -> cross {wm(d,'hhi_c'):.3f} "
          f"| top-1 {wm(d,'top1'):.1%} -> {wm(d,'top1_c'):.1%}")

# =====================================================================
# 3. Appendix regression: export value on network size
# =====================================================================
d = pa[(pa["total_affiliates"] >= 1) & (pa["export_value"] > 0)].copy()
d["ly"] = np.log(d["export_value"]); d["l_aff"] = np.log(d["total_affiliates"].astype(float))
d["l_ctry"] = np.log(d["n_countries"].astype(float) + 1)
d["l_sect"] = np.log(d["n_sectors"].astype(float) + 1)
d["hq"] = d["iso3_parent"].astype(str)
fits = [pf.feols("ly ~ l_aff", data=d, vcov="hetero"),
        pf.feols("ly ~ l_aff | hq", data=d, vcov="hetero"),
        pf.feols("ly ~ l_aff + l_ctry + l_sect | hq", data=d, vcov="hetero")]
lab_r = {"l_aff": r"$\ln$ global affiliates", "l_ctry": r"$\ln$ countries of presence",
         "l_sect": r"$\ln$ sectors of presence"}
lines = [r"\begin{tabular}{lccc}", r"\toprule", r"& (1) & (2) & (3) \\",
         r"\cmidrule(lr){2-4}",
         r"\multicolumn{4}{l}{\textit{Dependent variable: $\ln$ parent export value}} \\", r"\midrule"]
for rv in ["l_aff", "l_ctry", "l_sect"]:
    cs, ses = [], []
    for f in fits:
        co, se, pv = f.coef(), f.se(), f.pvalue()
        if rv in co.index:
            st = "***" if pv[rv] < .01 else "**" if pv[rv] < .05 else "*" if pv[rv] < .1 else ""
            cs.append(f"{co[rv]:.3f}{st}"); ses.append(f"({se[rv]:.3f})")
        else:
            cs.append(""); ses.append("")
    lines.append(f"{lab_r[rv]} & " + " & ".join(cs) + r" \\")
    lines.append(" & " + " & ".join(ses) + r" \\[2pt]")
lines += [r"\midrule", r"HQ-country fixed effects & & $\checkmark$ & $\checkmark$ \\",
          "Observations & " + " & ".join(f"{int(f._N):,}" for f in fits) + r" \\",
          r"\bottomrule",
          r"\multicolumn{4}{p{0.82\textwidth}}{\footnotesize \emph{Notes.} Parent level; "
          r"foreign MNEs with a network record. Robust (HC1) SE. \sym{*}$\,p<0.1$, "
          r"\sym{**}$\,p<0.05$, \sym{***}$\,p<0.01$.} \\", r"\end{tabular}"]
txt = "\n".join(lines) + "\n"
(R6 / "reg_sf6_network.tex").write_text(txt, encoding="utf-8")
(OL_R6 / "reg_sf6_network.tex").write_text(txt, encoding="utf-8")
print("\n>>> SF6 exhibits written (fig_sf6_network, fig_sf6_hhi, reg_sf6_network).")
