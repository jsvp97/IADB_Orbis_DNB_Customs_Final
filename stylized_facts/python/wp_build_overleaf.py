"""
wp_build_overleaf.py -- assemble the Overleaf project with EVERY new exhibit
==========================================================================

Collects the figures (pdf) and LaTeX fragments produced by wp1a..wp2 into one
self-contained LaTeX project, writes main.tex (one section per item of Volpe's agenda,
short reading notes, all figures and tables, appendices with the per-origin tables),
compiles it locally with pdflatex (MiKTeX) and zips the folder for upload to Overleaf.

    python wp_build_overleaf.py            -> output/wp/overleaf_WP_extensions/{main.tex, Graphs/, Tables/, Regressions/}
                                              output/wp/overleaf_WP_extensions.zip   (upload this to Overleaf: New project > Upload)
                                              docs/WP_extensions_2026-09-07.pdf       (compiled copy)

Re-run after any wp script is re-run; nothing here is hand-edited.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import zipfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_common as W  # noqa: E402

SRC = W.WP_OUT
DST = W.WP_OUT / "overleaf_WP_extensions"
DOCS = W.ROOT / "docs"
PDFLATEX = shutil.which("pdflatex") or r"C:\Users\Sebastian\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe"
ORIGINS = ["ARG", "CHL", "COL", "CRI", "DOM", "PER", "PRY", "SLV", "URY"]

# characters that pdflatex + inputenc utf8 do not know in text mode
SANITIZE = {"…": "...", "–": "--", "—": "---", "’": "'", "‘": "`", "“": "``", "”": "''", "×": r"$\times$",
            "≥": r"$\geq$", "≤": r"$\leq$", "°": r"$^{\circ}$", "σ": r"$\sigma$", "θ": r"$\theta$", "≈": r"$\approx$",
            "µ": r"$\mu$", "\u00a0": " ", "\u2009": " "}


def sanitize(text: str) -> str:
    for k, v in SANITIZE.items():
        text = text.replace(k, v)
    return "\n".join(W._balance_braces(l) for l in text.split("\n"))


def copy_fragment(scope: str, kind: str, name: str) -> str:
    """Copy Tables/Regressions fragment (sanitised) -> returns the relative path for \\input."""
    src = SRC / scope / kind / name
    rel = f"{kind}/{scope}/{name}"
    dst = DST / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(sanitize(src.read_text(encoding="utf-8")), encoding="utf-8")
    return rel[:-4]  # without .tex


def copy_fig(scope: str, name: str) -> str:
    src = SRC / scope / "Graphs" / f"{name}.pdf"
    rel = f"Graphs/{scope}/{name}.pdf"
    dst = DST / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return rel


# ---------------------------------------------------------------------
# LaTeX helpers (emit strings)
# ---------------------------------------------------------------------
def fig(scope, name, caption, label, width=0.95, note=""):
    path = copy_fig(scope, name)
    n = rf"\\[2pt]{{\footnotesize\textit{{Note:}} {note}}}" if note else ""
    return (rf"\begin{{figure}}[H]\centering\includegraphics[width={width}\textwidth]{{{path}}}"
            rf"\caption{{{caption}}}\label{{fig:{label}}}{n}\end{{figure}}" "\n")


def tab(scope, kind, name, caption, label, landscape=False, small=True):
    path = copy_fragment(scope, kind, name)
    size = r"\small" if small else ""
    body = (rf"\begin{{table}}[H]\centering{size}\caption{{{caption}}}\label{{tab:{label}}}"
            rf"\adjustbox{{max width=\textwidth, max totalheight=0.9\textheight}}{{\input{{{path}}}}}\end{{table}}" "\n")
    if landscape:
        body = body.replace(r"max width=\textwidth", r"max width=\linewidth").replace(
            r"max totalheight=0.9\textheight", r"max totalheight=0.85\textheight")
        return r"\begin{landscape}" + "\n" + body + r"\end{landscape}" + "\n"
    return body


def sec(title): return f"\n\\section{{{title}}}\n"
def sub(title): return f"\n\\subsection{{{title}}}\n"
def ssub(title): return f"\n\\subsubsection{{{title}}}\n"
def par(text): return text.strip() + "\n\n"


def build() -> Path:
    if DST.exists():
        shutil.rmtree(DST)
    DST.mkdir(parents=True)
    L = []
    L.append(r"""\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{mathptmx}
\usepackage[margin=2.2cm]{geometry}
\usepackage{graphicx,booktabs,amsmath,amssymb,adjustbox,float,pdflscape,caption,hyperref,xcolor,enumitem}
\usepackage{longtable}
\captionsetup{font=small,labelfont=bf,skip=4pt}
\hypersetup{colorlinks,linkcolor=blue!50!black,urlcolor=blue!50!black}
\setlength{\parskip}{4pt}
\newcommand{\iso}[1]{\texttt{#1}}
\title{Multinational Firms and Trade in Latin America\\[4pt]\large New exhibits for the working paper --- items 1a--1f and 2 of the September-2026 agenda}
\author{Ignacio Marra de Arti\~nano \and Gabriel Scattolo \and Sebasti\'an Vel\'asquez \and Christian Volpe Martincus}
\date{""" + date.today().strftime("%B %d, %Y") + r""" --- draft for internal review}
\begin{document}
\maketitle
\tableofcontents
\clearpage
""")

    # ------------------------------------------------------------------ 0
    L.append(sec("How to read this document"))
    L.append(par(r"""
This document collects, without selection, every figure, table and regression produced for
the items Christian raised on the stylized-facts document (v.\ 2026-07-29): (1a) the
figures split by the multinational's home country; (1b) alternative product-sophistication
measures for Figure 2, in particular the Fontagn\'e--Guimbard--Orefice (2022) elasticities;
(1c, 1d) two-way tables and heat maps of parent country $\times$ destination; (1e)
headquarters versus affiliates and MNE counts; (1f) HS6-level shares with descriptions;
(2) the agriculture version and the four-sector comparison. Each section opens with a
short reading note; the exhibits follow. Appendices hold the per-origin tables. Everything
is generated by \texttt{stylized\_facts/python/wp\_*.py} in the project repository
(\texttt{github.com/jsvp97/IADB\_Orbis\_DNB\_Customs\_Final}); the reader's guide with the
same numbers is \texttt{docs/WP\_RESULTS\_2026-09-07.md}.

\paragraph{Conventions.} Identical to the stylized-facts document: matched = the firm was
found in Orbis or D\&B (\texttt{\_merge\_DNB\_Orbis}=3); domestic MNE = parent in the
exporting country; foreign MNE = matched minus domestic, so matched firms with no recorded
parent count as foreign (shown hatched wherever parents are split); nine origins (Ecuador
excluded); value-weighted; pooled 2006--2022; navy = foreign, light gray = domestic.
Scopes: \emph{all goods} (\$2,394\,bn), \emph{agriculture} (HS 01--24, \$788\,bn),
\emph{mining \& fuels} (HS 25--27 and 71, \$810\,bn), \emph{manufacturing} (\$795\,bn).

\paragraph{Three data facts to keep in mind.}
\begin{enumerate}[leftmargin=*]
\item \textbf{The base used here has a parent country for 92\,\% of foreign-MNE export
value}; the July document's Figure 4 was drawn on a copy in which about half of that value
had no recorded parent. The parent ranking therefore changes (USA 23.3\,\% $>$ GBR 19.3\,\%
$>$ CAN 7.8\,\% $>$ LIE 5.4\,\% $>$ DEU $>$ NLD; Table~\ref{tab:parent_share_all}), Liechtenstein
appears (foundations owning Argentine and Chilean exporters of copper ore, oil-cake and
cereals --- a conduit, to be treated like PAN/CHE/NLD), and the domestic-MNE share rises
where the recovered parents are the origin country (COL 0.28 $\to$ 0.39, CHL 0.02 $\to$ 0.14).
The working paper must state which base each exhibit uses.
\item \textbf{``Headquarters exporters'' are not identifiable.} Every matched exporter has
a global ultimate owner different from itself (0 of 5.45\,M firm-cells); the match runs
through ownership links, so a LAC group's head company exporting from home is in the
unmatched pool. What is identifiable is the group's presence \emph{at the destination}
through its headquarters (the affiliate ships to the parent's country) or through another
affiliate --- Section~\ref{sec:1e} is built on that.
\item \textbf{The two match flags differ by \$357\,bn.} Both flags: \$1,411\,bn; only the
document's flag: \$90\,bn; only the manual-review flag used in the matching repository
(\texttt{\_merge\_final\_review}): \$267\,bn; neither: \$819\,bn.
\end{enumerate}
"""))
    L.append(tab("all", "Tables", "tab_wp1a_parent_share.tex",
                 "Foreign-MNE export value by parent country, all goods (Figure 4 of the document redrawn on the current base)", "parent_share_all"))

    # ------------------------------------------------------------------ 1a
    L.append(sec("Item 1a --- Figures 1--4 with the foreign bar split by the parent's country"))
    L.append(par(r"""
\textbf{Reading.} The foreign-MNE bar of each figure is split by the parent's country (the
eight largest by value, China forced in, ``Other foreign'', and hatched ``parent unknown'');
domestic MNEs stay gray; the bold number is the total MNE share, as in the document.
US parents dominate the Central-American and Paraguayan origins (CRI 0.30, PRY 0.30, SLV
0.28 of \emph{all} exports) and are minor in the Andean and Southern-Cone commodity
exporters (CHL 0.03, URY 0.05, ARG 0.08, PER 0.08); GBR is the largest parent in Chile
(0.21) and Peru (0.11), CAN in the Dominican Republic (0.16, gold), LIE in Chile and
Argentina. China is at most 0.04 (Uruguay, beef). Across PCI quintiles the rising foreign
share (0.46 $\to$ 0.65) is carried by USA in Q3--Q4 and by DEU and JPN in Q5 (vehicles);
GBR and CAN sit in Q1 (ores, metals). In the Lall classification high-tech is USA (0.22),
medium-tech USA+DEU+JPN, low-tech CAN (gold) and USA (apparel), primary GBR and domestic MNEs.
"""))
    L.append(fig("all", "fig_wp1a_origin_by_parent", "MNE share in export value by origin, foreign bar split by parent country (Figure 1 of the document)", "1a_origin_all"))
    L.append(fig("all", "fig_wp1a_pci_by_parent", "MNE share by PCI quintile, foreign bar split by parent country (Figure 2 of the document)", "1a_pci_all"))
    L.append(fig("all", "fig_wp1a_lall_by_parent", "MNE share by Lall (2000) technology category, foreign bar split by parent country (Figure 3 of the document)", "1a_lall_all"))
    L.append(fig("all", "fig_wp1a_parent_share", "Foreign-MNE export value by parent country, top 15 + Other (Figure 4 of the document, current base)", "1a_parent_share_all", width=0.75))
    L.append(fig("all", "fig_wp1a_origin_x_parent_heatmap", "Share of each origin's export value by parent country of the exporter (\\%)", "1a_heat_all", width=0.85))
    L.append(sub("Agriculture (HS 01--24)"))
    L.append(par(r"Parents in agriculture: USA 23.9\,\%, CHE 11.0\,\%, NLD 9.5\,\%, LIE 7.6\,\%, BRA 3.8\,\%, ESP 3.8\,\%, DEU 3.5\,\%, SAU 3.2\,\% (Almarai/SALIC grain in ARG and BRA); 12\,\% of foreign-MNE agro value has no recorded parent. Paraguay is the outlier: US parents alone are 0.35 of all agro exports (soy crushers)."))
    L.append(fig("agro", "fig_wp1a_origin_by_parent", "Agriculture: MNE share by origin, foreign bar split by parent country", "1a_origin_agro"))
    L.append(fig("agro", "fig_wp1a_pci_by_parent", "Agriculture: MNE share by PCI quintile (quintiles over agricultural HS6 products), split by parent", "1a_pci_agro"))
    L.append(fig("agro", "fig_wp1a_lall_by_parent", "Agriculture: MNE share by Lall category, split by parent", "1a_lall_agro"))
    L.append(fig("agro", "fig_wp1a_parent_share", "Agriculture: foreign-MNE export value by parent country", "1a_parent_share_agro", width=0.75))
    L.append(fig("agro", "fig_wp1a_origin_x_parent_heatmap", "Agriculture: share of each origin's agro exports by parent country (\\%)", "1a_heat_agro", width=0.85))
    L.append(sub("Mining \\& fuels and manufacturing"))
    L.append(par(r"Mining \& fuels: GBR 36\,\%, USA 21\,\%, CAN 16\,\%, LIE 7\,\%. Manufacturing: USA 25\,\%, GBR 14\,\%, DEU 9\,\%, JPN 7\,\%, PAN 5\,\%."))
    L.append(fig("mining", "fig_wp1a_origin_by_parent", "Mining \\& fuels: MNE share by origin, split by parent", "1a_origin_min"))
    L.append(fig("mining", "fig_wp1a_parent_share", "Mining \\& fuels: foreign-MNE export value by parent country", "1a_ps_min", width=0.7))
    L.append(fig("manufacturing", "fig_wp1a_origin_by_parent", "Manufacturing: MNE share by origin, split by parent", "1a_origin_man"))
    L.append(fig("manufacturing", "fig_wp1a_parent_share", "Manufacturing: foreign-MNE export value by parent country", "1a_ps_man", width=0.7))
    L.append(fig("manufacturing", "fig_wp1a_pci_by_parent", "Manufacturing: MNE share by PCI quintile, split by parent", "1a_pci_man"))
    L.append(par(r"The numbers behind every panel of this section are in Appendix~\ref{app:1a}."))

    # ------------------------------------------------------------------ 1b
    L.append(sec("Item 1b --- Figure 2 with other sophistication measures; substitution elasticities"))
    L.append(par(r"""
\textbf{Reading.} The Fontagn\'e--Guimbard--Orefice (2022) tariff-based import-demand
elasticities (CEPII ProTEE 0.1, HS6 rev.\ 2007; 90\,\% of HS6 lines, 78\,\% of export value)
are used in absolute value: larger $|\sigma|$ = more substitutable. Christian's hypothesis
--- more substitutable = less complex = less foreign presence --- \textbf{is not in the
data}: (i) the elasticity measures are essentially orthogonal to complexity
(value-weighted corr(PCI, $|\sigma|$~FGO) = 0.08, corr(PCI, $\sigma$~BW) = 0.04,
Table~\ref{tab:1b_corr}); (ii) there is no monotone gradient across $|\sigma|$ quintiles
(0.46, 0.38, 0.45, 0.34, 0.52; Q4 is a domestic-MNE quintile: copper cathodes and crude
oil); (iii) in the Table-A.4 ladder with PCI and upstreamness as controls, $|\sigma|$ FGO
enters \emph{positive} for the foreign share (+0.034 per s.d.) and negative for the
domestic share ($-$0.042): within markets, foreign affiliates are relatively more present
in \emph{more} substitutable products (Table~\ref{tab:1b_reg}). Only PCI and RHCI (corr
0.74) sort foreign presence monotonically. Suggested use: FGO as a robustness measure,
PCI as the headline. Quintiles are over HS6 products, unweighted, as in the document.
"""))
    L.append(fig("all", "fig_wp1b_panel_quintiles", "Foreign and domestic MNE shares by quintile of six product-sophistication measures", "1b_panel", width=1.0))
    L.append(fig("all", "fig_wp1b_sigma_fgo_abs_quintile", "Figure 2 with $|\\sigma|$ FGO (2022) quintiles instead of PCI", "1b_fgo", width=0.8))
    L.append(tab("all", "Tables", "tab_wp1b_quintile_shares.tex", "Foreign and domestic MNE shares by quintile, all six measures", "1b_quint"))
    L.append(tab("all", "Tables", "tab_wp1b_measure_corr.tex", "Value-weighted correlations across the six measures (HS6 cross-section)", "1b_corr"))
    L.append(tab("all", "Tables", "tab_wp1b_bec.tex", "MNE shares by BEC end use", "1b_bec"))
    L.append(fig("all", "fig_wp1b_bec", "Foreign and domestic MNE shares by BEC end use", "1b_becfig", width=0.7))
    L.append(tab("all", "Regressions", "reg_wp1b_odpy_fgo.tex", "Table A.4 of the document with the FGO elasticity added (ODPY cells, weighted)", "1b_reg"))
    L.append(sub("Agriculture"))
    L.append(par(r"Within agriculture PCI still rises with the foreign share (0.29, 0.49, 0.38, 0.42, 0.55) and $|\sigma|$ FGO falls mildly (0.40, 0.40, 0.37, 0.29, 0.33); corr(PCI, $|\sigma|$~FGO) $= -0.17$, corr(PCI, $\sigma$~BW) $= -0.57$ among agricultural products."))
    L.append(fig("agro", "fig_wp1b_panel_quintiles", "Agriculture: MNE shares by quintile of the six measures (quintiles over agricultural HS6 products)", "1b_panel_agro", width=1.0))
    L.append(tab("agro", "Tables", "tab_wp1b_quintile_shares.tex", "Agriculture: shares by quintile, all measures", "1b_quint_agro"))
    L.append(tab("agro", "Tables", "tab_wp1b_measure_corr.tex", "Agriculture: correlations across measures", "1b_corr_agro"))

    # ------------------------------------------------------------------ 1c/1d
    L.append(sec("Items 1c and 1d --- Parent country $\\times$ destination: tables and heat maps"))
    L.append(par(r"""
\textbf{Reading.} Rows = region or country of the multinational's parent (plus domestic
MNEs and local exporters as comparison rows), columns = destination region or country;
three versions of each matrix: value (USD bn), row \% (destination mix of each parent
group) and column \% (who supplies each destination). Only \textbf{9.1\,\%} of known-parent
foreign-MNE exports go to the parent's own country (USA 0.22, CAN 0.20, JPN 0.09, DEU 0.08,
NLD 0.02, GBR 0.01, CHE and LIE 0.00). European and Panamanian parents are China-facing
commodity platforms (GBR $\to$ CHN 37\,\%, PAN $\to$ CHN 35\,\%); Japanese, German and
Dutch parents are Brazil-facing regional manufacturers (JPN $\to$ BRA 45\,\%, DEU $\to$ BRA
32\,\%); only US and Canadian parents ship home in size. Domestic MNEs sell 33\,\% to North
America; local exporters are spread evenly across regions. One row-\% table per LAC origin
is in Appendix~\ref{app:1c}.
"""))
    L.append(tab("all", "Tables", "tab_wp1c_region_value.tex", "Parent region $\\times$ destination region, export value (USD bn)", "1c_reg_val"))
    L.append(tab("all", "Tables", "tab_wp1c_region_rowpct.tex", "Parent region $\\times$ destination region, row \\% (destination mix)", "1c_reg_row"))
    L.append(tab("all", "Tables", "tab_wp1c_region_colpct.tex", "Parent region $\\times$ destination region, column \\% (who supplies each destination)", "1c_reg_col"))
    L.append(fig("all", "fig_wp1d_heatmap_region_rowpct", "Heat map: destination mix of each parent region (row \\%)", "1d_reg", width=0.8))
    L.append(tab("all", "Tables", "tab_wp1c_country_value.tex", "Top-15 parents $\\times$ top-15 destinations, export value (USD bn)", "1c_cty_val", landscape=True))
    L.append(tab("all", "Tables", "tab_wp1c_country_rowpct.tex", "Top-15 parents $\\times$ top-15 destinations, row \\%", "1c_cty_row", landscape=True))
    L.append(tab("all", "Tables", "tab_wp1c_country_colpct.tex", "Top-15 parents $\\times$ top-15 destinations, column \\%", "1c_cty_col", landscape=True))
    L.append(fig("all", "fig_wp1d_heatmap_country_rowpct", "Heat map: where each parent's LAC exports go (row \\%, top-15 parents $\\times$ top-15 destinations)", "1d_cty_row", width=0.95))
    L.append(fig("all", "fig_wp1d_heatmap_country_cellpct", "Heat map: each cell as a share of all foreign-MNE exports (\\%)", "1d_cty_cell", width=0.95))
    L.append(fig("all", "fig_wp1d_home_share_by_parent", "Share of each parent's LAC exports shipped to the parent's own country", "1d_home", width=0.75))
    L.append(tab("all", "Tables", "tab_wp1c_origin_x_destregion_foreign.tex", "Foreign-MNE exports: origin $\\times$ destination region, row \\%", "1c_od_for"))
    L.append(tab("all", "Tables", "tab_wp1c_origin_x_destregion_local.tex", "Local (unmatched) exporters: origin $\\times$ destination region, row \\%", "1c_od_loc"))
    L.append(sub("Agriculture"))
    L.append(par(r"In agriculture 5.4\,\% goes to the parent's own country (ESP 0.26 --- fruit and wine; USA 0.07); Asian parents (Saudi grain) ship 29\,\% to North America and 29\,\% to Asia."))
    L.append(tab("agro", "Tables", "tab_wp1c_region_rowpct.tex", "Agriculture: parent region $\\times$ destination region, row \\%", "1c_reg_row_agro"))
    L.append(fig("agro", "fig_wp1d_heatmap_country_rowpct", "Agriculture: where each parent's LAC agro exports go (row \\%)", "1d_cty_row_agro", width=0.95))
    L.append(fig("agro", "fig_wp1d_home_share_by_parent", "Agriculture: share shipped to the parent's own country, by parent", "1d_home_agro", width=0.75))
    L.append(tab("agro", "Tables", "tab_wp1c_country_value.tex", "Agriculture: top-15 parents $\\times$ top-15 destinations, USD bn", "1c_cty_val_agro", landscape=True))

    # ------------------------------------------------------------------ 1e
    L.append(sec("Item 1e --- Headquarters versus affiliates; MNE counts") + r"\label{sec:1e}" + "\n")
    L.append(par(r"""
\textbf{Reading.} Because every matched exporter is an affiliate (data fact 2), the
headquarters question is answered on the destination side: a foreign multinational is
present at the destination \emph{through its headquarters} (the affiliate ships to the
parent's country), \emph{through another affiliate} (Orbis/D\&B roster), or \emph{not at
all}. Of foreign-MNE export value, 8.4\,\% is shipped to the HQ country, 40.5\,\% to
destinations with another affiliate and 51.1\,\% to destinations where the group is not
present (SLV 41\,\%, DOM 29\,\% and CRI 26\,\% through HQ against PRY 2\,\%, PER 4\,\%, CHL
4\,\%). ``MNE counts'': counting distinct \emph{groups} rather than exporting firms changes
nothing at the market-cell grain (1.01 affiliates per group per cell; Table~\ref{tab:1e_grp}),
so Table~\ref{tab:1e_groups} reproduces the firm-count coefficients to the third decimal.
In the Fact-5 regressions (Table~\ref{tab:1e_counts}) the intensive-margin benchmark
reproduces the document exactly (non-MNE exports on ln \# MNE firms: 0.239 with
origin$\times$dest$\times$product and origin$\times$dest$\times$year FE) and the
\textbf{association with local exports is strongest for foreign MNEs that are \emph{not}
present at the destination} (0.135 vs 0.082 for HQ-present, tightest FE); multinationals
shipping to their own headquarters do not crowd local exporters out more than the others.
In the distance regressions (Table~\ref{tab:1e_dist}) the attenuation of the distance
elasticity is +0.065 for HQ-present, +0.067 for affiliate-present and +0.042 for
non-present foreign MNEs, and +0.104 for domestic MNEs whose group has an affiliate in the
destination.
"""))
    L.append(tab("all", "Tables", "tab_wp1e_presence_shares.tex", "Foreign-MNE export value by the group's presence at the destination, by origin", "1e_pres"))
    L.append(tab("all", "Tables", "tab_wp1e_groups_vs_affiliates.tex", "Groups versus affiliates in the market cells", "1e_grp"))
    L.append(tab("all", "Regressions", "reg_wp1e_counts.tex", "MNE presence and exports (Fact 5) with counts by presence type", "1e_counts", landscape=True))
    L.append(tab("all", "Regressions", "reg_wp1e_groups.tex", "MNE presence and exports: number of groups versus number of firms", "1e_groups", landscape=True))
    L.append(tab("all", "Regressions", "reg_wp1e_distance_hq.tex", "Distance and firm exports (Fact 6) with the presence split", "1e_dist"))
    L.append(sub("Agriculture"))
    L.append(tab("agro", "Tables", "tab_wp1e_presence_shares.tex", "Agriculture: foreign-MNE value by presence type, by origin", "1e_pres_agro"))
    L.append(tab("agro", "Regressions", "reg_wp1e_counts.tex", "Agriculture: Fact-5 regressions with counts by presence type", "1e_counts_agro", landscape=True))
    L.append(tab("agro", "Regressions", "reg_wp1e_groups.tex", "Agriculture: groups versus firms", "1e_groups_agro", landscape=True))

    # ------------------------------------------------------------------ 1f
    L.append(sec("Item 1f --- Products at HS6, with descriptions"))
    L.append(par(r"""
\textbf{Reading.} The top 30 HS6 products are 57\,\% of exports. Crude oil (\$209\,bn) is
75\,\% domestic-MNE (Ecopetrol, ENAP, YPF) and 21\,\% foreign; copper ore (\$206\,bn) 83\,\%
foreign, of which GBR 54\,\%; refined copper 32\,\% foreign and 65\,\% local (Codelco is
unmatched); gold 40\,\% foreign (CAN two thirds of it); soybeans 64\,\% foreign (USA half);
coal 77\,\% foreign (GBR, USA); trucks 85\,\% foreign (DEU, JPN); coffee 34\,\% foreign
(DEU 40\,\% of it); T-shirts 60\,\% foreign, almost all US. 38\,\% of export value is in
products where foreign MNEs hold more than half; 15 HS6 products make 50\,\% of foreign-MNE
exports (10 in agriculture). Per-origin top-15 tables are in Appendix~\ref{app:1f}.
"""))
    L.append(fig("all", "fig_wp1f_top20_hs6_stacked", "Top-20 HS6 products by export value: foreign MNE / domestic MNE / local shares", "1f_top20", width=1.0))
    L.append(fig("all", "fig_wp1f_top20_hs6_by_parent", "Top-20 HS6 products: foreign share split by parent country", "1f_top20p", width=1.0))
    L.append(tab("all", "Tables", "tab_wp1f_top_hs6_by_value.tex", "Top 30 HS6 products by export value", "1f_val", landscape=True))
    L.append(tab("all", "Tables", "tab_wp1f_top_hs6_by_foreign_value.tex", "Top 30 HS6 products by foreign-MNE export value", "1f_fval", landscape=True))
    L.append(tab("all", "Tables", "tab_wp1f_top_hs6_by_foreign_share.tex", "HS6 products ($\\geq$ \\$500m) with the highest foreign-MNE share", "1f_fsh", landscape=True))
    L.append(tab("all", "Tables", "tab_wp1f_top_hs6_by_domestic_share.tex", "HS6 products ($\\geq$ \\$500m) with the highest domestic-MNE share", "1f_dsh", landscape=True))
    L.append(fig("all", "fig_wp1f_foreign_share_distribution", "Distribution of the HS6 foreign-MNE share (share of value and of products by bin)", "1f_dist", width=0.8))
    L.append(fig("all", "fig_wp1f_lorenz_foreign", "Concentration of foreign-MNE exports across HS6 products", "1f_lorenz", width=0.6))
    L.append(tab("all", "Tables", "tab_wp1f_foreign_share_distribution.tex", "Distribution of the HS6 foreign share, numbers", "1f_disttab"))
    L.append(sub("Agriculture"))
    L.append(fig("agro", "fig_wp1f_top20_hs6_stacked", "Agriculture: top-20 HS6 products, owner-type shares", "1f_top20_agro", width=1.0))
    L.append(fig("agro", "fig_wp1f_top20_hs6_by_parent", "Agriculture: top-20 HS6 products, foreign share split by parent", "1f_top20p_agro", width=1.0))
    L.append(tab("agro", "Tables", "tab_wp1f_top_hs6_by_value.tex", "Agriculture: top 30 HS6 by export value", "1f_val_agro", landscape=True))
    L.append(tab("agro", "Tables", "tab_wp1f_top_hs6_by_foreign_share.tex", "Agriculture: HS6 ($\\geq$ \\$500m) with the highest foreign-MNE share", "1f_fsh_agro", landscape=True))
    L.append(fig("agro", "fig_wp1f_lorenz_foreign", "Agriculture: concentration of foreign-MNE exports across HS6 products", "1f_lorenz_agro", width=0.6))

    # ------------------------------------------------------------------ 2
    L.append(sec("Item 2 --- Agriculture focus and the four-sector version"))
    L.append(par(r"""
\textbf{Reading.} Agriculture (HS 01--24), mining \& fuels (HS 25--27 and 71) and
manufacturing each account for about a third of the nine origins' exports. Foreign-MNE
shares are 0.38, 0.49 and 0.52; the domestic-MNE share is 0.25 in mining (state oil and
copper companies) against 0.08--0.09 elsewhere. \textbf{Services are not observable in
customs merchandise data}; the only service-related information is the affiliate's own
NAICS: 17.6\,\% of matched export value is shipped by affiliates classified in trade and
services (wholesale, logistics, holdings). A services version needs another source.

Within agriculture: BEC end use (the classification referred to as ``VEC'' in the notes)
splits agro exports into intermediate goods (56\,\%, foreign share 0.41) and consumption
goods (44\,\%, 0.35); primary food for industry (BEC 111) has the highest foreign share
(0.49). Agricultural \emph{inputs} (fertilisers, agrochemicals, seeds for sowing, animal
feed, machinery, live animals; whole soybeans counted as output) are 17.5\,\% of agro
exports, dominated by soybean oil-cake and fishmeal, with a foreign share of 0.36 against
0.39 for food, fibres and beverages --- no input premium; their parents are the Swiss,
Liechtenstein and US grain traders. SITC divisions, NAICS 3-digit and Lall complete the
set; each split has an origin $\times$ sub-sector heat map of the foreign share.
"""))
    L.append(sub("Four sectors"))
    L.append(tab("sectors", "Tables", "tab_wp2_four_sectors.tex", "MNE shares by sector", "2_sect"))
    L.append(fig("sectors", "fig_wp2_four_sectors", "Foreign and domestic MNE shares by sector", "2_sectfig", width=0.7))
    L.append(fig("sectors", "fig_wp2_origin_x_sector_foreign_share", "Foreign-MNE share by origin and sector", "2_osf", width=0.8))
    L.append(fig("sectors", "fig_wp2_origin_x_sector_value_share", "Sector composition of each origin's exports (\\%)", "2_osv", width=0.8))
    L.append(tab("sectors", "Tables", "tab_wp2_origin_x_sector_foreign_share.tex", "Foreign-MNE share by origin and sector", "2_osf_t"))
    L.append(tab("sectors", "Tables", "tab_wp2_origin_x_sector_value_share.tex", "Sector composition of each origin's exports, \\%", "2_osv_t"))
    L.append(tab("sectors", "Tables", "tab_wp2_sector_x_destregion_foreign.tex", "Foreign-MNE exports by sector and destination region, row \\%", "2_sd"))
    L.append(tab("sectors", "Tables", "memo_wp2_services.tex", "Memo: matched exporters by the affiliate's own NAICS sector", "2_serv"))
    L.append(sub("Agriculture: sub-classifications"))
    for key, cap in [("hs_section", "HS sections I--IV"), ("bec_enduse", "BEC Rev.\\,4 end use"), ("bec4", "BEC Rev.\\,4 detailed categories"),
                     ("inputs", "agricultural inputs versus output"), ("sitc2", "SITC Rev.\\,3 divisions"), ("naics3", "NAICS 3-digit (product-based)"), ("lall", "Lall (2000) categories")]:
        L.append(ssub(cap[0].upper() + cap[1:]))
        L.append(tab("agro", "Tables", f"tab_wp2_agro_{key}.tex", f"Agriculture by {cap}: shares and leading parents", f"2_{key}"))
        L.append(fig("agro", f"fig_wp2_agro_{key}", f"Agriculture by {cap}: foreign and domestic MNE shares", f"2_{key}_f", width=0.85))
        L.append(fig("agro", f"fig_wp2_agro_origin_x_{key}", f"Agriculture: foreign-MNE share by origin and {cap}", f"2_{key}_h", width=0.85))
        L.append(tab("agro", "Tables", f"tab_wp2_agro_origin_x_{key}.tex", f"Agriculture: foreign-MNE share by origin and {cap}, numbers", f"2_{key}_ht"))
    L.append(ssub("Cross-classifications and parents"))
    L.append(tab("agro", "Tables", "tab_wp2_agro_section_x_enduse_value.tex", "Agriculture: HS section $\\times$ BEC end use, USD bn", "2_sxe_v"))
    L.append(tab("agro", "Tables", "tab_wp2_agro_section_x_enduse_foreignshare.tex", "Agriculture: HS section $\\times$ BEC end use, foreign-MNE share", "2_sxe_f"))
    L.append(tab("agro", "Tables", "tab_wp2_agro_top_inputs_hs6.tex", "Agriculture: largest input products (HS6)", "2_inp_top"))
    L.append(tab("agro", "Tables", "tab_wp2_agro_hs_section_by_parent.tex", "Agriculture: parent-country composition by HS section", "2_sec_p"))
    L.append(tab("agro", "Tables", "tab_wp2_agro_bec_enduse_by_parent.tex", "Agriculture: parent-country composition by BEC end use", "2_bec_p"))
    L.append(tab("agro", "Tables", "tab_wp2_agro_inputs_by_parent.tex", "Agriculture: parent-country composition, inputs versus output", "2_inp_p"))

    # ------------------------------------------------------------------ appendices
    L.append(r"\appendix" + "\n")
    L.append(sec("Numbers behind the Item-1a figures") + r"\label{app:1a}" + "\n")
    for scope, lab in [("all", "All goods"), ("agro", "Agriculture"), ("mining", "Mining \\& fuels"), ("manufacturing", "Manufacturing")]:
        L.append(sub(lab))
        for key, cap in [("origin", "by origin"), ("pci", "by PCI quintile"), ("lall", "by Lall category")]:
            L.append(tab(scope, "Tables", f"tab_wp1a_{key}_by_parent.tex", f"{lab}: MNE shares {cap}, split by parent country", f"a1a_{scope}_{key}"))
        if scope != "all":
            L.append(tab(scope, "Tables", "tab_wp1a_parent_share.tex", f"{lab}: foreign-MNE value by parent country", f"a1a_{scope}_ps"))
    L.append(sec("Parent region $\\times$ destination region, by origin (row \\%)") + r"\label{app:1c}" + "\n")
    for scope, lab in [("all", "All goods"), ("agro", "Agriculture")]:
        L.append(sub(lab))
        for o in ORIGINS:
            L.append(tab(scope, "Tables", f"tab_wp1c_byorigin_{o}.tex", f"{lab}, exports from {o}: parent region $\\times$ destination region, row \\%", f"a1c_{scope}_{o}"))
    L.append(sec("Top-15 HS6 products by origin") + r"\label{app:1f}" + "\n")
    for scope, lab in [("all", "All goods"), ("agro", "Agriculture")]:
        L.append(sub(lab))
        for o in ORIGINS:
            L.append(tab(scope, "Tables", f"tab_wp1f_top_hs6_{o}.tex", f"{lab}: top 15 HS6 products exported by {o}", f"a1f_{scope}_{o}", landscape=True))
    L.append(sec("Item 1b, remaining single-measure figures"))
    for m, cap in [("complexity", "PCI"), ("sigma_bw", "$\\sigma$ Broda--Weinstein"), ("upstreamness", "upstreamness"), ("quality_ladder", "quality ladder"), ("rhci", "RHCI")]:
        L.append(fig("all", f"fig_wp1b_{m}_quintile", f"Figure 2 with {cap} quintiles", f"a1b_{m}", width=0.7))
    L.append(sec("Item 1c/1d, remaining agriculture matrices"))
    L.append(tab("agro", "Tables", "tab_wp1c_region_value.tex", "Agriculture: parent region $\\times$ destination region, USD bn", "a1c_agro_val"))
    L.append(tab("agro", "Tables", "tab_wp1c_region_colpct.tex", "Agriculture: parent region $\\times$ destination region, column \\%", "a1c_agro_col"))
    L.append(tab("agro", "Tables", "tab_wp1c_country_rowpct.tex", "Agriculture: top-15 parents $\\times$ top-15 destinations, row \\%", "a1c_agro_crow", landscape=True))
    L.append(tab("agro", "Tables", "tab_wp1c_country_colpct.tex", "Agriculture: top-15 parents $\\times$ top-15 destinations, column \\%", "a1c_agro_ccol", landscape=True))
    L.append(fig("agro", "fig_wp1d_heatmap_region_rowpct", "Agriculture: heat map of the destination mix by parent region", "a1d_agro_reg", width=0.8))
    L.append(fig("agro", "fig_wp1d_heatmap_country_cellpct", "Agriculture: each cell as a share of all foreign-MNE agro exports", "a1d_agro_cell", width=0.95))
    L.append(tab("agro", "Tables", "tab_wp1c_origin_x_destregion_foreign.tex", "Agriculture, foreign-MNE exports: origin $\\times$ destination region, row \\%", "a1c_agro_odf"))
    L.append(tab("agro", "Tables", "tab_wp1c_origin_x_destregion_local.tex", "Agriculture, local exporters: origin $\\times$ destination region, row \\%", "a1c_agro_odl"))
    L.append(r"\end{document}" + "\n")

    main = DST / "main.tex"
    main.write_text("".join(L), encoding="utf-8")
    return main


def compile_pdf(main: Path) -> bool:
    ok = True
    for _ in range(2):
        r = subprocess.run([PDFLATEX, "-interaction=nonstopmode", "-halt-on-error", main.name], cwd=main.parent,
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        ok = r.returncode == 0
        if not ok:
            log = (main.parent / "main.log").read_text(encoding="utf-8", errors="replace")
            i = log.find("\n!")
            print("pdflatex FAILED:\n", log[i: i + 1500] if i >= 0 else r.stdout[-1500:])
            break
    return ok


def zip_project(folder: Path) -> Path:
    out = folder.with_suffix(".zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in folder.rglob("*"):
            if p.is_file() and p.suffix in (".tex", ".pdf", ".bib") and p.name != "main.pdf":
                z.write(p, p.relative_to(folder))
    return out


if __name__ == "__main__":
    main = build()
    n_fig = len(list((DST / "Graphs").rglob("*.pdf"))); n_tab = len(list(DST.rglob("Tables/**/*.tex"))) + len(list(DST.rglob("Regressions/**/*.tex")))
    print(f"main.tex written: {n_fig} figures, {n_tab} table fragments")
    if compile_pdf(main):
        shutil.copy2(DST / "main.pdf", DOCS / f"WP_extensions_{date.today().isoformat()}.pdf")
        z = zip_project(DST)
        print(f"compiled OK -> {DST / 'main.pdf'}\nzip for Overleaf -> {z} ({z.stat().st_size / 1e6:.1f} MB)")
    else:
        sys.exit(1)
