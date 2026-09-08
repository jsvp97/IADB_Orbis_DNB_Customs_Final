"""
wp_build_overleaf.py -- assemble the Overleaf project: the stylized-facts document's skeleton,
each original exhibit reproduced on the current base, and every new variant under it.
=====================================================================================================

Skeleton = the six facts of "Stylized Facts on Multinational Firms and Trade" (v. 2026-07-29):
  1 origin shares (Fig. 1) · 2 complex products (Figs 2-3) · 3 parent countries (Fig. 4) ·
  4 large groups (Figs 5-6) · 5 presence and trade volume (Table 1) · 6 distance (Table 2);
then two new sections (products at HS6; agriculture and the four sectors) and appendices.

    python wp_build_overleaf.py   -> output/wp/overleaf_WP_extensions/{main.tex, Graphs/, Tables/, Regressions/}
                                     output/wp/overleaf_WP_extensions.zip   (Overleaf: New project > Upload)
                                     docs/WP_extensions_<date>.pdf           (compiled copy)

Re-run after any wp script is re-run; nothing here is hand-edited. Revision 2026-09-08:
top-5 parents in every country split, top-10 two-way tables (heat maps 15x15), compact HS6
tables, originals reproduced (wp1a originals(), wp0_fact4_groups.py, reg_wp0_table{1,2}_repro).
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
TODAY = date.today().strftime("%Y-%m-%d")

SANITIZE = {"…": "...", "–": "--", "—": "---", "’": "'", "‘": "`", "“": "``", "”": "''", "×": r"$\times$",
            "≥": r"$\geq$", "≤": r"$\leq$", "°": r"$^{\circ}$", "σ": r"$\sigma$", "θ": r"$\theta$", "≈": r"$\approx$",
            "µ": r"$\mu$", "\u00a0": " ", "\u2009": " "}


def sanitize(text: str) -> str:
    for k, v in SANITIZE.items():
        text = text.replace(k, v)
    return "\n".join(W._balance_braces(l) for l in text.split("\n"))


def copy_fragment(scope: str, kind: str, name: str) -> str:
    src = SRC / scope / kind / name
    rel = f"{kind}/{scope}/{name}"
    dst = DST / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(sanitize(src.read_text(encoding="utf-8")), encoding="utf-8")
    return rel[:-4]


def copy_fig(scope: str, name: str) -> str:
    src = SRC / scope / "Graphs" / f"{name}.pdf"
    rel = f"Graphs/{scope}/{name}.pdf"
    dst = DST / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return rel


def exists(scope, kind, name):
    return (SRC / scope / kind / name).exists()


# ---------------------------------------------------------------------
def pending(kind, scope, name, label=None):
    print(f"   MISSING {kind} {scope}/{name}")
    lab = rf"\label{{tab:{label}}}" if label else ""
    return r"\par\textbf{[pending " + kind + ": " + f"{scope}/{name}".replace("_", r"\_") + "]}" + lab + r"\par" + "\n"


def fig(scope, name, caption, label, width=0.95, note=""):
    if not exists(scope, "Graphs", f"{name}.pdf"):
        return pending("figure", scope, name)
    path = copy_fig(scope, name)
    n = rf"\par\vspace{{2pt}}\parbox{{0.92\textwidth}}{{\footnotesize\textit{{Note:}} {note}}}" if note else ""
    return (rf"\begin{{figure}}[H]\centering\includegraphics[width={width}\textwidth]{{{path}}}"
            rf"\caption{{{caption}}}\label{{fig:{label}}}{n}\end{{figure}}" "\n")


def tab(scope, kind, name, caption, label, landscape=False, size=r"\small"):
    if not exists(scope, kind, name):
        return pending("table", scope, name, label)
    path = copy_fragment(scope, kind, name)
    body = (rf"\begin{{table}}[H]\centering{size}\caption{{{caption}}}\label{{tab:{label}}}"
            rf"\adjustbox{{max width=\textwidth, max totalheight=0.88\textheight}}{{\input{{{path}}}}}\end{{table}}" "\n")
    if landscape:
        body = body.replace(r"max width=\textwidth", r"max width=\linewidth").replace(r"0.88\textheight", r"0.85\textheight")
        return r"\begin{landscape}" + "\n" + body + r"\end{landscape}" + "\n"
    return body


def sec(title, label=None): return f"\n\\section{{{title}}}" + (f"\\label{{sec:{label}}}" if label else "") + "\n"
def sub(title): return f"\n\\subsection{{{title}}}\n"
def ssub(title): return f"\n\\subsubsection{{{title}}}\n"
def par(text): return text.strip() + "\n\n"


SCOPE_NAME = {"all": "All goods", "agro": "Agriculture (HS 01--24)", "mining": "Mining \\& fuels (HS 25--27, 71)", "manufacturing": "Manufacturing"}


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
\captionsetup{font=small,labelfont=bf,skip=4pt}
\hypersetup{colorlinks,linkcolor=blue!50!black,urlcolor=blue!50!black}
\setlength{\parskip}{4pt}
\title{Stylized Facts on Multinational Firms and Trade in Latin America\\[4pt]\large Each fact with its original exhibit reproduced on the current base and the variants for the working paper}
\author{Ignacio Marra de Arti\~nano \and Gabriel Scattolo \and Sebasti\'an Vel\'asquez \and Christian Volpe Martincus}
\date{""" + date.today().strftime("%B %d, %Y") + r""" --- draft for internal review}
\begin{document}
\maketitle
\tableofcontents
\clearpage
""")

    # ================================================================ 0
    L.append(sec("How to read this document"))
    L.append(par(r"""
The document follows the six stylized facts of the July-2026 note (v.\ 2026-07-29). Each
section opens with the fact, reproduces its \emph{original} exhibit on the current base, and
then places under it every variant prepared for the working paper: (1a) the figures with the
foreign-MNE bar split by the multinational's home country; (1b) alternative
product-sophistication measures for Figure~2, including the Fontagn\'e--Guimbard--Orefice (2022)
elasticities; (1c, 1d) two-way tables and heat maps of parent country $\times$ destination;
(1e) headquarters versus affiliates and MNE counts; (1f) products at HS6 with descriptions;
(2) the agriculture version and the four-sector comparison. Appendices hold the per-origin
tables and the numbers behind the figures. Everything is generated by
\texttt{stylized\_facts/python/wp\_*.py} in the project repository
(\texttt{github.com/jsvp97/IADB\_Orbis\_DNB\_Customs\_Final}); the reader's guide is
\texttt{docs/WP\_RESULTS\_2026-09-07.md}.

\paragraph{Conventions (identical to the note).} Matched = the firm was found in Orbis or D\&B
(\texttt{\_merge\_DNB\_Orbis}=3); domestic MNE = parent in the exporting country; foreign MNE =
matched minus domestic, so matched firms with no recorded parent count as foreign; nine
origins (Ecuador excluded); value-weighted; pooled 2006--2022; navy = foreign, light gray =
domestic. Wherever the foreign bar is split by home country, the five largest parent countries
(by foreign-MNE export value in the scope) are shown and every other foreign MNE---including
those with no recorded parent---is pooled into ``Other foreign MNEs''. Scopes: all goods
(\$2,394\,bn), agriculture (HS 01--24, \$788\,bn), mining \& fuels (HS 25--27 and 71,
\$810\,bn), manufacturing (\$795\,bn).

\paragraph{Same data as the note.} The regressions that do not depend on the parent country
reproduce the note to the last digit: Table~\ref{tab:t1_repro} returns the note's Table~1
coefficients and observation counts (e.g.\ 2.0685, 0.9414, 0.2391; $N=1{,}008{,}185$), and
Table~\ref{tab:t2_repro} the note's Table~2 within rounding. The base is therefore the same
5.45\,M firm--destination--product--year rows. The one field that differs is the
\emph{parent country}: the current base carries a recorded parent for 92\,\% of foreign-MNE
export value (script 02 and the AI review of unknown parents, merged in the 2026-04-21 build),
whereas the note's Figure~4 was drawn on a copy in which about half of that value had no
recorded parent. Consequences, visible below: the parent ranking becomes USA $>$ GBR $>$ CAN $>$
LIE $>$ DEU $>$ NLD (Table~\ref{tab:parent_share_all}); Liechtenstein appears (foundations owning
Argentine and Chilean exporters of copper ore, oil-cake and cereals---a conduit, to be treated
like PAN/CHE/NLD); and the domestic-MNE share rises where the recovered parents are the origin
country (COL 0.28 $\to$ 0.39, CHL 0.02 $\to$ 0.14 in Figure~\ref{fig:f1_orig}), so the
``foreign $\gg$ domestic'' statement of Fact~1 needs a qualification for Colombia.

\paragraph{One data limit.} ``Headquarters exporters'' are not identifiable: every matched
exporter has a global ultimate owner different from itself (0 of 5.45\,M rows), because the
match runs through ownership links. What is identifiable is the group's presence \emph{at the
destination} through its headquarters (the affiliate ships to the parent's country) or through
another affiliate---Sections~\ref{sec:f5} and \ref{sec:f6} use that.
"""))

    # ================================================================ FACT 1
    L.append(sec("Fact 1 --- Multinational corporations account for a large share of export values across countries", "f1"))
    L.append(sub("Original exhibit"))
    L.append(fig("all", "fig_wp0_fig1_origin", "Figure 1 of the note, reproduced on the current base: MNE share of export value by origin, foreign vs domestic.", "f1_orig", 0.8,
                 "Value-weighted; pooled 2006--2022; nine LAC origins. Bar length = total MNE share; numbers behind the bars in Table~\\ref{tab:a_f1_all}."))
    L.append(sub("Variant: the foreign bar split by the multinational's home country (item 1a)"))
    L.append(par(r"""The five largest parents in all goods are the United States, the United Kingdom, Canada,
Liechtenstein and Germany. US parents dominate the maquila and Central-American origins (CRI, PRY,
SLV) and are minor in the Andean and Southern-Cone commodity exporters; British parents are the
largest in Chile and Peru (copper), Canadian ones in the Dominican Republic (gold)."""))
    L.append(fig("all", "fig_wp1a_origin_by_parent", "MNE share of export value by origin, foreign bar split by parent country (top 5, Other foreign, Domestic).", "f1_parent", 0.9))
    L.append(fig("all", "fig_wp1a_origin_x_parent_heatmap", "Companion heat map: share of each origin's export value by parent-country group (\\%).", "f1_hm", 0.85))
    L.append(sub("Variant: by sector (item 2)"))
    for sc in ("agro", "mining", "manufacturing"):
        L.append(fig(sc, "fig_wp0_fig1_origin", f"{SCOPE_NAME[sc]}: Figure 1 reproduced for the sector.", f"f1_orig_{sc}", 0.72))
        L.append(fig(sc, "fig_wp1a_origin_by_parent", f"{SCOPE_NAME[sc]}: foreign bar split by parent country.", f"f1_parent_{sc}", 0.85))

    # ================================================================ FACT 2
    L.append(sec("Fact 2 --- Foreign multinationals specialize in complex products, domestic ones in primary goods", "f2"))
    L.append(sub("Original exhibits"))
    L.append(fig("all", "fig_wp0_fig2_pci", "Figure 2 of the note, reproduced: MNE share of export value by Product Complexity Index quintile.", "f2_orig", 0.78,
                 "Value-weighted at HS6; quintiles of the Hausmann--Hidalgo PCI over HS6 products (Q1 = least complex)."))
    L.append(fig("all", "fig_wp0_fig3_lall", "Figure 3 of the note, reproduced: MNE share of export value by Lall (2000) technology category.", "f3_orig", 0.78))
    L.append(sub("Variant: split by the multinational's home country (item 1a)"))
    L.append(par(r"""The rising foreign share across complexity quintiles is carried by US, German and Japanese
parents (vehicles and machinery in Q5); British and Canadian parents sit in the least complex
quintile (ores and metals). Domestic MNEs fall from Q1 to Q5."""))
    L.append(fig("all", "fig_wp1a_pci_by_parent", "Figure 2 with the foreign bar split by parent country.", "f2_parent", 0.9))
    L.append(fig("all", "fig_wp1a_lall_by_parent", "Figure 3 with the foreign bar split by parent country.", "f3_parent", 0.9))
    L.append(sub("Variant: other measures of product sophistication; substitution elasticities (item 1b)"))
    L.append(par(r"""The hypothesis was that more substitutable products (a larger import-demand elasticity in
absolute value) are less complex, so the foreign-MNE share should fall across elasticity
quintiles as it rises across PCI quintiles. The Fontagn\'e--Guimbard--Orefice (2022) elasticities
(CEPII ProTEE, HS6 rev.\ 2007; 90\,\% of HS6 lines, 78\,\% of export value) do not show this:
there is no monotone gradient across $|\sigma|$ quintiles, the elasticity measures are
essentially orthogonal to complexity (Table~\ref{tab:corr}), and in the note's Table~A.4 ladder
$|\sigma|$ enters \emph{positive} for the foreign share conditional on PCI
(Table~\ref{tab:reg_fgo}). Only PCI and RHCI sort foreign presence monotonically."""))
    L.append(fig("all", "fig_wp1b_panel_quintiles", "Figure 2 redrawn for six sophistication measures (foreign navy, domestic gray; quintiles over HS6 products).", "f2_panel", 1.0))
    L.append(fig("all", "fig_wp1b_sigma_fgo_abs_quintile", "Figure 2 with $|\\sigma|$ from Fontagn\\'e, Guimbard and Orefice (2022) in place of the PCI.", "f2_fgo", 0.78))
    L.append(tab("all", "Tables", "tab_wp1b_quintile_shares.tex", "Foreign and domestic MNE shares by quintile, six sophistication measures", "quint"))
    L.append(tab("all", "Tables", "tab_wp1b_measure_corr.tex", "Correlations across sophistication measures (HS6, value-weighted)", "corr"))
    L.append(tab("all", "Tables", "tab_wp1b_bec.tex", "MNE shares by BEC end use", "bec_all"))
    L.append(tab("all", "Regressions", "reg_wp1b_odpy_fgo.tex", "Note's Table A.4 ladder with the FGO elasticity added (ODPY cells, MNE value share)", "reg_fgo"))
    L.append(sub("Agriculture (item 2)"))
    L.append(fig("agro", "fig_wp0_fig2_pci", "Agriculture: Figure 2 reproduced within HS 01--24.", "f2_orig_agro", 0.72))
    L.append(fig("agro", "fig_wp0_fig3_lall", "Agriculture: Figure 3 reproduced within HS 01--24.", "f3_orig_agro", 0.72))
    L.append(fig("agro", "fig_wp1a_pci_by_parent", "Agriculture: Figure 2 split by parent country.", "f2_parent_agro", 0.85))
    L.append(fig("agro", "fig_wp1a_lall_by_parent", "Agriculture: Figure 3 split by parent country.", "f3_parent_agro", 0.85))
    L.append(fig("agro", "fig_wp1b_panel_quintiles", "Agriculture: six sophistication measures.", "f2_panel_agro", 1.0))
    L.append(tab("agro", "Tables", "tab_wp1b_quintile_shares.tex", "Agriculture: MNE shares by quintile, six measures", "quint_agro"))

    # ================================================================ FACT 3
    L.append(sec("Fact 3 --- Multinational corporations from a small set of countries dominate exports", "f3"))
    L.append(sub("Original exhibit"))
    L.append(fig("all", "fig_wp1a_parent_share", "Figure 4 of the note, reproduced on the current base: foreign-MNE export value by parent country, top 15 plus Other.", "f4_orig", 0.78,
                 "Foreign MNEs with a recorded parent country (92\\,\\% of foreign-MNE value here, against about half in the note). Numbers in Table~\\ref{tab:parent_share_all}."))
    L.append(tab("all", "Tables", "tab_wp1a_parent_share.tex", "Foreign-MNE export value by parent country (numbers behind Figure~\\ref{fig:f4_orig})", "parent_share_all"))
    L.append(sub("Variant: parent country $\\times$ export destination --- tables (item 1c)"))
    L.append(par(r"""Rows are the parent's region or country, columns the destination; the three panels give
value, row percentages (the destination mix of each parent group) and column percentages (who
supplies each destination). Domestic MNEs and local exporters are added as rows for comparison.
Only 9.1\,\% of known-parent foreign-MNE exports go to the parent's own country; European and
Panamanian parents in LAC are China-facing commodity platforms, Japanese, German and Dutch parents
are Brazil-facing, and only US and Canadian parents ship home in size."""))
    for stem, cap in (("value", "export value (USD bn)"), ("rowpct", "row \\%"), ("colpct", "column \\%")):
        L.append(tab("all", "Tables", f"tab_wp1c_region_{stem}.tex", f"Parent region $\\times$ destination region, {cap}", f"1c_reg_{stem}"))
    for stem, cap in (("value", "export value (USD bn)"), ("rowpct", "row \\%"), ("colpct", "column \\%")):
        L.append(tab("all", "Tables", f"tab_wp1c_country_{stem}.tex", f"Top-10 parents $\\times$ top-10 destinations, {cap}", f"1c_cty_{stem}"))
    L.append(tab("all", "Tables", "tab_wp1c_origin_x_destregion_foreign.tex", "Foreign-MNE exports: destination region by LAC origin (row \\%)", "1c_odr_f"))
    L.append(tab("all", "Tables", "tab_wp1c_origin_x_destregion_local.tex", "Local (unmatched) firms: destination region by LAC origin (row \\%)", "1c_odr_l"))
    L.append(sub("Variant: heat maps (item 1d)"))
    L.append(fig("all", "fig_wp1d_heatmap_region_rowpct", "Parent region $\\times$ destination region, row \\%.", "1d_reg", 0.9))
    L.append(fig("all", "fig_wp1d_heatmap_country_rowpct", "Top-15 parents $\\times$ top-15 destinations: \\% of the parent's LAC export value going to each destination.", "1d_row", 1.0))
    L.append(fig("all", "fig_wp1d_heatmap_country_cellpct", "Top-15 parents $\\times$ top-15 destinations: cell share of all foreign-MNE export value (\\%).", "1d_cell", 1.0))
    L.append(fig("all", "fig_wp1d_home_share_by_parent", "Share of each parent's LAC export value shipped to the parent's own country.", "1d_home", 0.85))
    L.append(sub("Agriculture (item 2)"))
    L.append(fig("agro", "fig_wp1a_parent_share", "Agriculture: Figure 4 reproduced within HS 01--24.", "f4_orig_agro", 0.72))
    L.append(tab("agro", "Tables", "tab_wp1c_region_rowpct.tex", "Agriculture: parent region $\\times$ destination region, row \\%", "1c_reg_row_agro"))
    L.append(tab("agro", "Tables", "tab_wp1c_country_value.tex", "Agriculture: top-10 parents $\\times$ top-10 destinations, USD bn", "1c_cty_val_agro"))
    L.append(fig("agro", "fig_wp1d_heatmap_country_rowpct", "Agriculture: top-15 parents $\\times$ top-15 destinations, row \\%.", "1d_row_agro", 1.0))
    L.append(fig("agro", "fig_wp1d_home_share_by_parent", "Agriculture: share shipped to the parent's own country, by parent.", "1d_home_agro", 0.85))

    # ================================================================ FACT 4
    L.append(sec("Fact 4 --- A small set of large multinational groups accounts for the bulk of exports", "f4"))
    L.append(sub("Original exhibits"))
    L.append(fig("all", "fig_wp0_fig5_network", "Figure 5 of the note, reproduced: foreign-MNE export value and parent counts by global affiliate-network size.", "f5_orig", 0.7,
                 "Foreign-MNE parents with a matched global-network record (Orbis $\\cup$ D\\&B roster). Numbers and coverage in Table~\\ref{tab:f5_tab}."))
    L.append(tab("all", "Tables", "tab_wp0_fig5_network.tex", "Numbers behind Figure~\\ref{fig:f5_orig}", "f5_tab"))
    L.append(fig("all", "fig_wp0_fig6_hhi", "Figure 6 of the note, reproduced: product-level export concentration, naive firm count vs grouping affiliates by parent.", "f6_orig", 0.9))
    L.append(tab("all", "Tables", "tab_wp0_fig6_hhi.tex", "Numbers behind Figure~\\ref{fig:f6_orig}: HHI, top-exporter share, effective number of exporters", "f6_tab"))
    L.append(sub("Variant: groups versus affiliates inside the market cells (item 1e, ``MNE cantidad'')"))
    L.append(par(r"""Counting multinational \emph{groups} instead of affiliates changes nothing at the
origin--destination--product--year grain: a group almost never exports the same product to the
same destination through two affiliates (Table~\ref{tab:grp_aff}), so the count regressions of
Fact~5 are identical whichever unit is used (Table~\ref{tab:reg_groups}). The grouping matters
at the product level (Figure~\ref{fig:f6_orig}), not in the market cells."""))
    L.append(tab("all", "Tables", "tab_wp1e_groups_vs_affiliates.tex", "Affiliates per group in the origin--destination--product--year cells", "grp_aff"))
    L.append(tab("all", "Regressions", "reg_wp1e_groups.tex", "Fact-5 regressions with ln(\\# MNE groups) in place of ln(\\# MNE firms)", "reg_groups"))
    L.append(sub("Agriculture (item 2)"))
    L.append(fig("agro", "fig_wp0_fig5_network", "Agriculture: Figure 5 reproduced within HS 01--24.", "f5_orig_agro", 0.7))
    L.append(fig("agro", "fig_wp0_fig6_hhi", "Agriculture: Figure 6 reproduced within HS 01--24.", "f6_orig_agro", 0.9))

    # ================================================================ FACT 5
    L.append(sec("Fact 5 --- Greater multinational presence is associated with higher trade volumes", "f5"))
    L.append(sub("Original exhibit"))
    L.append(tab("all", "Regressions", "reg_wp0_table1_repro.tex", "Table 1 of the note, reproduced: multinational presence and trade volume (intensive and extensive margins)", "t1_repro"))
    L.append(sub("Variant: presence through headquarters, through another affiliate, or not present; MNE counts (item 1e)"))
    L.append(par(r"""Of foreign-MNE export value, 8.4\,\% is shipped to the parent's own country (presence
through headquarters), 40.5\,\% to destinations where the group has another affiliate, and
51.1\,\% to destinations where the group is not present (Table~\ref{tab:pres_sh}). Splitting the
count of multinationals by presence type (Table~\ref{tab:reg_counts}) shows that the positive
association between MNE presence and local exports is strongest for foreign MNEs with \emph{no}
presence at the destination and weakest, but still positive, for those shipping to their own
headquarters' country."""))
    L.append(tab("all", "Tables", "tab_wp1e_presence_shares.tex", "Foreign-MNE export value by the group's presence at the destination, by origin", "pres_sh"))
    L.append(tab("all", "Regressions", "reg_wp1e_counts.tex", "Table 1 with the MNE count split by presence type", "reg_counts"))
    L.append(sub("Agriculture (item 2)"))
    L.append(tab("agro", "Regressions", "reg_wp0_table1_repro.tex", "Agriculture: Table 1 reproduced within HS 01--24", "t1_repro_agro"))
    L.append(tab("agro", "Tables", "tab_wp1e_presence_shares.tex", "Agriculture: foreign-MNE value by presence type and origin", "pres_sh_agro"))
    L.append(tab("agro", "Regressions", "reg_wp1e_counts.tex", "Agriculture: Table 1 with counts by presence type", "reg_counts_agro"))
    L.append(tab("agro", "Regressions", "reg_wp1e_groups.tex", "Agriculture: groups vs affiliates", "reg_groups_agro"))

    # ================================================================ FACT 6
    L.append(sec("Fact 6 --- Distance is a weaker barrier to trade for multinational corporations", "f6"))
    L.append(sub("Original exhibit"))
    L.append(tab("all", "Regressions", "reg_wp0_table2_repro.tex", "Table 2 of the note, reproduced: distance and firm exports, multinationals split by presence at the destination", "t2_repro"))
    L.append(sub("Variant: foreign presence through headquarters vs through another affiliate; domestic MNEs (item 1e)"))
    L.append(par(r"""Distance attenuation is essentially the same whether the foreign group is present through
its headquarters or through another affiliate, and smaller when it is not present at all;
domestic MNEs whose group has an affiliate in the destination show the largest attenuation
(Table~\ref{tab:reg_dist_hq})."""))
    L.append(tab("all", "Regressions", "reg_wp1e_distance_hq.tex", "Table 2 with foreign presence split into headquarters / another affiliate / not present, and domestic MNEs split by presence", "reg_dist_hq"))

    # ================================================================ HS6
    L.append(sec("Products at HS6, with descriptions (item 1f)", "hs6"))
    L.append(par(r"""Top-30 tables by export value, by foreign-MNE value, by foreign share and by domestic share
(products $\geq$ \$500\,m), with product descriptions and the leading parent country; the top-20
products stacked by owner type and by parent; the distribution of the HS6 foreign share; and
the concentration of foreign-MNE exports across products. Per-origin top-15 tables are in
Appendix~\ref{sec:app_hs6}."""))
    L.append(fig("all", "fig_wp1f_top20_hs6_stacked", "Top-20 HS6 products by export value: foreign MNE / domestic MNE / local shares.", "1f_stack", 1.0))
    L.append(fig("all", "fig_wp1f_top20_hs6_by_parent", "Top-20 HS6 products: foreign bar split by parent country (remainder = local firms).", "1f_parent", 1.0))
    L.append(fig("all", "fig_wp1f_foreign_share_distribution", "Distribution of the HS6 foreign-MNE share: share of export value and of products by bin.", "1f_dist", 0.85))
    L.append(fig("all", "fig_wp1f_lorenz_foreign", "Concentration of exports across HS6 products: foreign-MNE exports vs all exports.", "1f_lorenz", 0.6))
    L.append(tab("all", "Tables", "tab_wp1f_top_hs6_by_value.tex", "Top 30 HS6 products by export value", "1f_val", size=r"\footnotesize"))
    L.append(tab("all", "Tables", "tab_wp1f_top_hs6_by_foreign_value.tex", "Top 30 HS6 products by foreign-MNE export value", "1f_fval", size=r"\footnotesize"))
    L.append(tab("all", "Tables", "tab_wp1f_top_hs6_by_foreign_share.tex", "HS6 products ($\\geq$ \\$500m) with the highest foreign-MNE share", "1f_fsh", size=r"\footnotesize"))
    L.append(tab("all", "Tables", "tab_wp1f_top_hs6_by_domestic_share.tex", "HS6 products ($\\geq$ \\$500m) with the highest domestic-MNE share", "1f_dsh", size=r"\footnotesize"))
    L.append(tab("all", "Tables", "tab_wp1f_foreign_share_distribution.tex", "Distribution of the HS6 foreign share, numbers", "1f_disttab"))
    L.append(sub("Agriculture (item 2)"))
    L.append(fig("agro", "fig_wp1f_top20_hs6_stacked", "Agriculture: top-20 HS6 products, owner-type shares.", "1f_stack_agro", 1.0))
    L.append(fig("agro", "fig_wp1f_top20_hs6_by_parent", "Agriculture: top-20 HS6 products, foreign bar split by parent country.", "1f_parent_agro", 1.0))
    L.append(tab("agro", "Tables", "tab_wp1f_top_hs6_by_value.tex", "Agriculture: top 30 HS6 products by export value", "1f_val_agro", size=r"\footnotesize"))
    L.append(tab("agro", "Tables", "tab_wp1f_top_hs6_by_foreign_share.tex", "Agriculture: HS6 products ($\\geq$ \\$500m) with the highest foreign-MNE share", "1f_fsh_agro", size=r"\footnotesize"))

    # ================================================================ AGRO / SECTORS
    L.append(sec("Agriculture focus and the four-sector version (item 2)", "agro"))
    L.append(sub("Four sectors"))
    L.append(par(r"""Agriculture = HS 01--24; mining \& fuels = HS 25--27 plus 71 (precious metals and stones);
manufacturing = the rest. Services are not observable in customs merchandise data; the memo
table reports the only service-related information available (the matched affiliate's own NAICS)."""))
    L.append(tab("sectors", "Tables", "tab_wp2_four_sectors.tex", "The three observable sectors: value, MNE shares, leading parents", "2_sectors"))
    L.append(fig("sectors", "fig_wp2_four_sectors", "Foreign and domestic MNE shares by sector.", "2_sectors_fig", 0.75))
    L.append(fig("sectors", "fig_wp2_origin_x_sector_foreign_share", "Foreign-MNE share by origin and sector (\\%).", "2_ox_fsh", 0.8))
    L.append(fig("sectors", "fig_wp2_origin_x_sector_value_share", "Composition of each origin's exports by sector (\\%).", "2_ox_vsh", 0.8))
    L.append(tab("sectors", "Tables", "tab_wp2_origin_x_sector_foreign_share.tex", "Foreign-MNE share by origin and sector, numbers", "2_ox_fsh_t"))
    L.append(tab("sectors", "Tables", "tab_wp2_origin_x_sector_value_share.tex", "Composition of exports by origin and sector, numbers", "2_ox_vsh_t"))
    L.append(tab("sectors", "Tables", "tab_wp2_sector_x_destregion_foreign.tex", "Foreign-MNE exports: destination region by sector (row \\%)", "2_sdr"))
    L.append(tab("sectors", "Tables", "memo_wp2_services.tex", "Memo: service-sector affiliates among matched exporters (NAICS of the affiliate)", "2_services"))
    L.append(sub("Agriculture: sub-classifications"))
    L.append(par(r"""Each split gives the foreign and domestic MNE shares and the leading parents, then an
origin $\times$ sub-sector heat map of the foreign share with its two-panel table (Panel A:
composition of the origin's agricultural exports, rows sum to 100; Panel B: the foreign-MNE
share within each cell, with the origin's overall share in the ``All'' column). The BEC end-use
classification (UNSD HS07$\to$BEC Rev.\,4) is the ``consumption goods vs inputs'' cut; the
agro-inputs flag isolates fertilisers, agrochemicals, seeds for sowing, animal feed, agricultural
machinery and live animals (whole soybeans are output, not seed)."""))
    AGRO = [("hs_section", "HS sections I--IV", None),
            ("bec_enduse", "BEC Rev.\\,4 end use", None),
            ("bec4", "BEC Rev.\\,4 detailed categories", None),
            ("inputs", "Agricultural inputs versus output", "top_inputs_hs6"),
            ("sitc2", "SITC Rev.\\,3 divisions", None),
            ("naics3", "NAICS 3-digit (product-based)", None),
            ("lall", "Lall (2000) categories", None)]
    for stem, title, extra in AGRO:
        L.append(ssub(title))
        L.append(tab("agro", "Tables", f"tab_wp2_agro_{stem}.tex", f"Agriculture by {title}: value, MNE shares, leading parents", f"2_{stem}"))
        L.append(fig("agro", f"fig_wp2_agro_{stem}", f"Agriculture: foreign and domestic MNE shares by {title}.", f"2_{stem}_fig", 0.85))
        L.append(fig("agro", f"fig_wp2_agro_origin_x_{stem}", f"Agriculture: foreign-MNE share by origin and {title} (\\%).", f"2_{stem}_hm", 0.9))
        L.append(tab("agro", "Tables", f"tab_wp2_agro_origin_x_{stem}.tex", f"Agriculture: composition (Panel A) and foreign-MNE share (Panel B) by origin and {title}", f"2_{stem}_ht", size=r"\footnotesize"))
        if extra:
            L.append(tab("agro", "Tables", f"tab_wp2_agro_{extra}.tex", "Agriculture: top HS6 lines among agricultural inputs", f"2_{extra}", size=r"\footnotesize"))
    L.append(ssub("Cross-classifications and parents"))
    L.append(tab("agro", "Tables", "tab_wp2_agro_section_x_enduse_value.tex", "Agriculture: HS section $\\times$ BEC end use, export value (USD bn)", "2_sxe_val"))
    L.append(tab("agro", "Tables", "tab_wp2_agro_section_x_enduse_foreignshare.tex", "Agriculture: HS section $\\times$ BEC end use, foreign-MNE share (\\%)", "2_sxe_fsh"))
    for stem, title in (("hs_section", "HS section"), ("bec_enduse", "BEC end use"), ("inputs", "inputs vs output")):
        L.append(tab("agro", "Tables", f"tab_wp2_agro_{stem}_by_parent.tex", f"Agriculture: parent-country composition of exports by {title} (\\%)", f"2_{stem}_par"))

    # ================================================================ APPENDICES
    L.append(r"\appendix" + "\n")
    L.append(sec("Numbers behind the figures of Facts 1--2 (all scopes)", "a1"))
    for sc in ("all", "agro", "mining", "manufacturing"):
        L.append(sub(SCOPE_NAME[sc]))
        if exists(sc, "Tables", "tab_wp0_fig1_origin.tex"):
            L.append(tab(sc, "Tables", "tab_wp0_fig1_origin.tex", f"{SCOPE_NAME[sc]}: Figure 1 numbers (foreign, domestic, total)", f"a_f1_{sc}"))
        for stem, cap in (("origin", "Figure 1 by parent"), ("pci", "Figure 2 by parent"), ("lall", "Figure 3 by parent")):
            L.append(tab(sc, "Tables", f"tab_wp1a_{stem}_by_parent.tex", f"{SCOPE_NAME[sc]}: {cap}, numbers", f"a1a_{stem}_{sc}"))
        if sc != "all":
            L.append(tab(sc, "Tables", "tab_wp1a_parent_share.tex", f"{SCOPE_NAME[sc]}: Figure 4 numbers (top-15 parents)", f"a_f4_{sc}"))
    L.append(sec("Parent region $\\times$ destination region, by origin (row \\%)", "a1c"))
    for sc in ("all", "agro"):
        L.append(sub(SCOPE_NAME[sc]))
        for o in ORIGINS:
            L.append(tab(sc, "Tables", f"tab_wp1c_byorigin_{o}.tex", f"{SCOPE_NAME[sc]}, exports from {o}: parent region $\\times$ destination region, row \\%", f"a1c_{sc}_{o}"))
    L.append(sec("Remaining parent $\\times$ destination matrices", "a1c2"))
    for stem, cap in (("value", "USD bn"), ("colpct", "column \\%")):
        L.append(tab("agro", "Tables", f"tab_wp1c_region_{stem}.tex", f"Agriculture: parent region $\\times$ destination region, {cap}", f"a1c_agro_r{stem}"))
    for stem, cap in (("rowpct", "row \\%"), ("colpct", "column \\%")):
        L.append(tab("agro", "Tables", f"tab_wp1c_country_{stem}.tex", f"Agriculture: top-10 parents $\\times$ top-10 destinations, {cap}", f"a1c_agro_c{stem}"))
    L.append(fig("agro", "fig_wp1d_heatmap_region_rowpct", "Agriculture: parent region $\\times$ destination region, row \\%.", "a1d_reg_agro", 0.9))
    L.append(fig("agro", "fig_wp1d_heatmap_country_cellpct", "Agriculture: cell share of all foreign-MNE agricultural exports (\\%).", "a1d_cell_agro", 1.0))
    L.append(tab("agro", "Tables", "tab_wp1c_origin_x_destregion_foreign.tex", "Agriculture, foreign-MNE exports: destination region by origin (row \\%)", "a1c_odr_f_agro"))
    L.append(sec("Top-15 HS6 products by origin", "app_hs6"))
    for sc in ("all", "agro"):
        L.append(sub(SCOPE_NAME[sc]))
        for o in ORIGINS:
            L.append(tab(sc, "Tables", f"tab_wp1f_top_hs6_{o}.tex", f"{SCOPE_NAME[sc]}: top 15 HS6 products exported by {o}", f"a1f_{sc}_{o}", size=r"\footnotesize"))
    L.append(sec("Fact 2, remaining single-measure figures", "a1b"))
    for m in ("complexity", "sigma_bw", "upstreamness", "quality_ladder", "rhci"):
        L.append(fig("all", f"fig_wp1b_{m}_quintile", f"Figure 2 with \\texttt{{{m.replace('_', ' ')}}} in place of the PCI.", f"a1b_{m}", 0.72))
    L.append(fig("all", "fig_wp1b_bec", "MNE shares by BEC end use.", "a1b_bec", 0.72))
    L.append(sec("Agriculture, remaining HS6 tables", "a_agro_hs6"))
    L.append(tab("agro", "Tables", "tab_wp1f_top_hs6_by_foreign_value.tex", "Agriculture: top 30 HS6 products by foreign-MNE export value", "a1f_fval_agro", size=r"\footnotesize"))
    L.append(tab("agro", "Tables", "tab_wp1f_top_hs6_by_domestic_share.tex", "Agriculture: HS6 products ($\\geq$ \\$500m) with the highest domestic-MNE share", "a1f_dsh_agro", size=r"\footnotesize"))
    L.append(fig("agro", "fig_wp1f_foreign_share_distribution", "Agriculture: distribution of the HS6 foreign share.", "a1f_dist_agro", 0.8))
    L.append(fig("agro", "fig_wp1f_lorenz_foreign", "Agriculture: concentration of exports across HS6 products.", "a1f_lorenz_agro", 0.6))
    L.append(r"\end{document}" + "\n")

    main = DST / "main.tex"
    main.write_text("".join(L), encoding="utf-8")
    nfig = sum(1 for _ in DST.glob("Graphs/*/*.pdf")); ntab = sum(1 for _ in DST.glob("Tables/*/*.tex")) + sum(1 for _ in DST.glob("Regressions/*/*.tex"))
    print(f"main.tex written: {nfig} figures, {ntab} table fragments")
    return main


def compile_pdf(main: Path) -> bool:
    for _ in range(3):
        r = subprocess.run([PDFLATEX, "-interaction=nonstopmode", "-halt-on-error", main.name], cwd=main.parent, capture_output=True, text=True, errors="replace")
    ok = (main.parent / "main.pdf").exists() and r.returncode == 0
    if not ok:
        log = (main.parent / "main.log").read_text(encoding="utf-8", errors="replace")
        i = log.find("\n!")
        print("pdflatex FAILED:\n" + log[i:i + 1500] if i >= 0 else r.stdout[-2000:])
    else:
        log = (main.parent / "main.log").read_text(encoding="utf-8", errors="replace")
        warn = [l for l in log.split("\n") if "undefined" in l.lower() or "multiply" in l.lower()]
        print(f"compiled OK -> {main.parent / 'main.pdf'}" + (f"   ({len(warn)} reference warnings)" if warn else ""))
        for l in warn[:8]:
            print("   ", l.strip())
    return ok


def zip_project(folder: Path) -> Path:
    out = folder.with_suffix(".zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in folder.rglob("*"):
            if p.is_file() and p.suffix not in {".aux", ".log", ".out", ".toc", ".synctex.gz", ".pdf"} or p.suffix == ".pdf" and p.parent.name != folder.name:
                z.write(p, p.relative_to(folder))
    print(f"zip for Overleaf -> {out} ({out.stat().st_size / 1e6:.1f} MB)")
    return out


if __name__ == "__main__":
    main = build()
    if compile_pdf(main):
        shutil.copy2(main.parent / "main.pdf", DOCS / f"WP_extensions_{TODAY}.pdf")
        print("copied ->", DOCS / f"WP_extensions_{TODAY}.pdf")
    zip_project(DST)
