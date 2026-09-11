"""
wp_build_overleaf.py -- assemble THREE Overleaf projects from the wp_* outputs (revision 3, 2026-09-08)
========================================================================================================

  1. WP_total      all goods: the six stylized facts, each with its original exhibit reproduced on the
                   current base and every variant under it; products at HS6; the four sectors at a glance.
  2. WP_sectors    the same block for each sector (Agriculture, Manufacturing, Mining & fuels, Rest), plus
                   the sub-classification block (HS sections, BEC end use, BEC categories, SITC, NAICS, Lall,
                   agro inputs) and the parent-country composition tables.
  3. WP_countries  the exhibits that separate cleanly by exporting country: parent region x destination
                   region, the parent x destination heat map, the home-share figure, the top-15 HS6 lines.

    python wp_build_overleaf.py            -> output/wp/overleaf_WP_{total,sectors,countries}/  (+ .zip, + docs/*.pdf)
    python wp_build_overleaf.py total      -> one of them

Nothing here is hand-edited; re-run after any wp script is re-run. Every exhibit appears once per document.
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
DOCS = W.ROOT / "docs"
PDFLATEX = shutil.which("pdflatex") or r"C:\Users\Sebastian\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe"
ORIGINS = ["ARG", "CHL", "COL", "CRI", "DOM", "PER", "PRY", "SLV", "URY"]
TODAY = date.today().strftime("%Y-%m-%d")
SECTOR_SCOPES = ["agro", "manufacturing", "mining", "rest"]
SANITIZE = {"…": "...", "–": "--", "—": "---", "’": "'", "‘": "`", "“": "``", "”": "''", "×": r"$\times$", "≥": r"$\geq$", "≤": r"$\leq$",
            "°": r"$^{\circ}$", "σ": r"$\sigma$", "θ": r"$\theta$", "≈": r"$\approx$", "µ": r"$\mu$", "\u00a0": " ", "\u2009": " "}

DST: Path = None   # set per document
STRICT = True      # print a [pending] marker for missing exhibits (total) or skip silently (sectors/countries)
MISSING: list = []


def sanitize(text: str) -> str:
    for k, v in SANITIZE.items():
        text = text.replace(k, v)
    return "\n".join(W._balance_braces(l) for l in text.split("\n"))


def exists(scope, kind, name): return (SRC / scope / kind / name).exists()


NOTE_RE = re.compile(r"^\\multicolumn\{\d+\}\{p\{[0-9.]*\\textwidth\}\}\{\\footnotesize\s*(.*)\}\s*\\\\\s*$")


def split_note(text: str):
    """Remove the table note (a full-width \multicolumn after \bottomrule) from a fragment and return it
    separately; the builder sets it under the table so it never widens the tabular."""
    out, note = [], None
    for line in text.split("\n"):
        m = NOTE_RE.match(line.strip())
        if m and note is None:
            note = m.group(1).strip()
            while note.endswith("}") and note.count("}") > note.count("{"):
                note = note[:-1].rstrip()
        else:
            out.append(line)
    return "\n".join(out), note


def copy_fragment(scope, kind, name):
    rel = f"{kind}/{scope}/{name}"; dst = DST / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    body, note = split_note(sanitize((SRC / scope / kind / name).read_text(encoding="utf-8")))
    dst.write_text(body, encoding="utf-8")
    return rel[:-4], note


def copy_fig(scope, name):
    rel = f"Graphs/{scope}/{name}.pdf"; dst = DST / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SRC / scope / "Graphs" / f"{name}.pdf", dst)
    return rel


def missing(kind, scope, name):
    MISSING.append(f"{scope}/{name}")
    if not STRICT:
        return ""
    return r"\par\textbf{[pending " + kind + ": " + f"{scope}/{name}".replace("_", r"\_") + r"]}\par" + "\n"


def fig(scope, name, caption, label, width=0.95, note=""):
    if not exists(scope, "Graphs", f"{name}.pdf"):
        return missing("figure", scope, name)
    path = copy_fig(scope, name)
    n = rf"\par\vspace{{2pt}}\parbox{{0.92\textwidth}}{{\footnotesize\textit{{Note:}} {note}}}" if note else ""
    return (rf"\begin{{figure}}[H]\centering\includegraphics[width={width}\textwidth,height=0.86\textheight,keepaspectratio]{{{path}}}"
            rf"\caption{{{caption}}}\label{{fig:{label}}}{n}\end{{figure}}" "\n")


def tab(scope, kind, name, caption, label, size=r"\small"):
    if not exists(scope, kind, name):
        return missing("table", scope, name)
    path, note = copy_fragment(scope, kind, name)
    n = rf"\par\vspace{{3pt}}\begin{{minipage}}{{0.95\textwidth}}\footnotesize {note}\end{{minipage}}" if note else ""
    return (rf"\begin{{table}}[H]\centering{size}\caption{{{caption}}}\label{{tab:{label}}}"
            rf"\adjustbox{{max width=\textwidth, max totalheight=0.8\textheight}}{{\input{{{path}}}}}{n}\end{{table}}" "\n")


def sec(title, label=None): return f"\n\\section{{{title}}}" + (f"\\label{{sec:{label}}}" if label else "") + "\n"
def sub(title): return f"\n\\subsection{{{title}}}\n"
def ssub(title): return f"\n\\subsubsection{{{title}}}\n"
def par(text): return text.strip() + "\n\n"


def preamble(title, subtitle):
    return r"""\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{mathptmx}
\usepackage[margin=2.2cm]{geometry}
\usepackage{graphicx,booktabs,amsmath,amssymb,adjustbox,float,caption,hyperref,xcolor,enumitem}
\captionsetup{font=small,labelfont=bf,skip=4pt}
\hypersetup{colorlinks,linkcolor=blue!50!black,urlcolor=blue!50!black}
\setlength{\parskip}{4pt}
\title{""" + title + r"""\\[4pt]\large """ + subtitle + r"""}
\author{Ignacio Marra de Arti\~nano \and Gabriel Scattolo \and Sebasti\'an Vel\'asquez \and Christian Volpe Martincus}
\date{""" + date.today().strftime("%B %d, %Y") + r""" --- draft for internal review}
\begin{document}
\maketitle
\tableofcontents
\clearpage
"""


CONVENTIONS = r"""
\paragraph{Conventions (identical to the note).} Matched = the firm was found in Orbis or D\&B
(\path{_merge_DNB_Orbis}=3); domestic MNE = parent in the exporting country; foreign MNE =
matched minus domestic, so matched firms with no recorded parent count as foreign; nine origins
(Ecuador excluded); value-weighted; pooled 2006--2022; navy = foreign, light gray = domestic.
Wherever the foreign bar is split by home country, the ten largest parent countries (by
foreign-MNE export value in the scope) are shown in shades of navy (rank 1 darkest) and every
other foreign MNE---including those with no recorded parent---is pooled into ``Other foreign
MNEs'' (gray-blue); domestic MNEs keep the light gray. Two-way country tables show the top-10
parents and destinations; heat maps the top 15. Regressions use plain logs (a zero count drops
the cell from that column; no $\ln(1+x)$) and cluster at origin--destination. Sectors:
agriculture = HS 01--24; mining \& fuels = HS 25--27 and 71; manufacturing = HS 28--97 excluding
71; rest = HS 98--99, chapter 00 and unclassifiable codes (services are not in customs data).
"""

DATA_FACTS = r"""
\paragraph{Same data as the note.} The regressions that depend only on the matched flag
reproduce the note to the last digit: Table~\ref{tab:t1_repro_all} returns the note's Table~1
Panel~A coefficients and every observation count (2.0823 / 2.0685 / 0.9414; extensive 1.4622 /
1.4591 / 0.6818; N = 1,008,472 \ldots\ 1,137,550) and Table~\ref{tab:t2_repro_all} the note's
Table~2 pooled coefficients ($-0.1639$ / $-0.1848$; $0.0461$ / $0.0458$; N = 5,081,547 /
5,081,360); Figure~\ref{fig:f5_orig_all} gives the note's 56\,\% of value for parents with more
than 100 affiliates. The cells that use the group's affiliate links differ in the third decimal
only (Table~1 Panel~B 1.3536 vs the note's 1.3522; Table~2 ``present'' 0.0689 vs 0.0673), because
the current base carries the affiliate and parent links of the 2026-04-21 build. The base is
therefore the same 5.45\,M firm--destination--product--year rows. The field that differs
materially is the \emph{parent country}:
the current base carries a recorded parent for 92\,\% of foreign-MNE export value (script 02 and
the AI review of unknown parents, merged in the 2026-04-21 build), whereas the note's Figure~4
was drawn on a copy in which about half of that value had no recorded parent. The parent
ranking becomes USA $>$ GBR $>$ CAN $>$ LIE $>$ DEU $>$ NLD (Liechtenstein: foundations owning
Argentine and Chilean exporters of copper ore, oil-cake and cereals---a conduit), and the
domestic-MNE share rises where the recovered parents are the origin country (COL 0.28 $\to$
0.39, CHL 0.02 $\to$ 0.14), so Fact~1's ``foreign $\gg$ domestic'' needs a qualification for
Colombia.

\paragraph{Two data limits.} (i) ``Headquarters exporters'' are not identifiable: every matched
exporter has a global ultimate owner different from itself (0 of 5.45\,M rows), because the match
runs through ownership links. What is identifiable is the group's presence \emph{at the
destination} through its headquarters (the affiliate ships to the parent's country); Facts~5
and~6 decompose foreign MNEs on that. (ii) On the substitution elasticities: Fontagn\'e, Guimbard
and Orefice (2022) estimate one import-demand elasticity per HS6 product (rev.\ 2007), common to
all exporters and importers---the elasticity is identified from tariff variation across the
universe of bilateral flows of the product and is a characteristic of the product, not of the
origin. Assigning the same $|\sigma|$ to a product whatever its exporting country is therefore
the intended use of the database (non-significant or positive HS6 estimates are replaced by
the source with the HS4 average and flagged); no origin-specific adjustment is needed or
possible. The Rauch (1999) classification (conservative, SITC 3/4 digits mapped to HS6) is
added; the Micro-D classification of Bernini, Gonz\'alez, Hallak and Vicondoa (2018) is defined
on Argentina's 12-digit nomenclature from package-size attributes and cannot be carried to HS6
data for other countries.
"""


def intro_total():
    return sec("How to read this document") + par(r"""
The document follows the six stylized facts of the July-2026 note (v.\ 2026-07-29). Each
section opens with the fact, reproduces its \emph{original} exhibit on the current base, and
then places under it every variant prepared for the working paper: the figures with the
foreign-MNE bar split by the multinational's home country (item 1a); alternative
product-sophistication measures for Figure~2, including the Fontagn\'e--Guimbard--Orefice (2022)
elasticities, with the full distributions (1b); two-way tables and heat maps of parent country
$\times$ destination (1c, 1d); the decomposition of multinationals into foreign vs domestic and
of foreign MNEs into present-through-headquarters vs not, in the presence and distance
regressions (1e); products at HS6 with descriptions (1f). The four sectors are summarised at the
end; the sector-by-sector version of every exhibit is the companion document
\emph{WP\_sectors}, and the country-by-country exhibits are in \emph{WP\_countries}. Everything is
generated by \path{stylized_facts/python/wp_*.py} in the project repository
(\url{https://github.com/jsvp97/IADB_Orbis_DNB_Customs_Final}); the reader's guide is
\path{docs/WP_RESULTS_2026-09-07.md}.""") + CONVENTIONS + DATA_FACTS


def intro_sectors():
    return sec("How to read this document") + par(r"""
Companion to \emph{WP\_total}: the same six facts and the HS6 section, computed within each
sector---agriculture (HS 01--24), manufacturing (HS 28--97 excluding 71), mining \& fuels (HS
25--27 and 71) and the rest (HS 98--99, chapter 00 and unclassifiable codes; services are not
observable in customs merchandise data)---followed, for each sector, by the sub-classification
block: HS sections, BEC Rev.\,4 end use (consumption goods vs inputs), BEC detailed categories,
SITC Rev.\,3 divisions, NAICS 3-digit, Lall (2000) categories and, for agriculture, an
agro-inputs flag. Each split gives total and MNE exports, foreign and domestic shares, the three
leading parents, the foreign/domestic bars, an origin $\times$ sub-sector heat map with its
two-panel table (composition; foreign share) and the parent-country composition. Quintiles,
top-10 lists and parent rankings are recomputed within the sector.""") + CONVENTIONS


def intro_countries():
    return sec("How to read this document") + par(r"""
Companion to \emph{WP\_total}: the exhibits that separate cleanly by exporting country, one
section per origin---the parent region $\times$ destination region matrix (row \%), the
parent $\times$ destination heat map (cell share of the origin's foreign-MNE exports), the share
of each parent's exports from the origin shipped to the parent's own country, and the top-15
HS6 products, for all goods and for each sector. Exhibits that pool the nine origins by
construction (the regressions, the quintile figures, the parent rankings) are in the other two
documents; the origin dimension of Figure~1 and of the sub-sector tables is in their
origin $\times$ category heat maps there.""") + CONVENTIONS


# ---------------------------------------------------------------------
def fact_block(sc: str, L: list, tag: str, with_originals=True) -> None:
    """The six facts + HS6 for one scope. `tag` distinguishes labels across scopes."""
    S = W.SCOPE_LABEL[sc].replace("\\\\&", "\\&")
    P = "" if sc == "all" else f"{S}: "
    # ---------------- Fact 1
    L.append(sec("Fact 1 --- Multinational corporations account for a large share of export values across countries", f"f1_{tag}"))
    L.append(sub("Original exhibit"))
    L.append(fig(sc, "fig_wp0_fig1_origin", f"{P}Figure 1 of the note, reproduced on the current base: MNE share of export value by origin, foreign vs domestic.", f"f1_orig_{tag}", 0.8,
                 "Value-weighted; pooled 2006--2022; nine LAC origins. Bar length = total MNE share; numbers in the appendix."))
    L.append(sub("Variant: the foreign bar split by the multinational's home country (item 1a)"))
    L.append(fig(sc, "fig_wp1a_origin_by_parent", f"{P}MNE share of export value by origin, foreign bar split by parent country (top 10, Other foreign, Domestic).", f"f1_parent_{tag}", 0.92))
    L.append(fig(sc, "fig_wp1a_origin_x_parent_heatmap", f"{P}companion heat map: share of each origin's export value by parent-country group (\\%).", f"f1_hm_{tag}", 0.9))
    # ---------------- Fact 2
    L.append(sec("Fact 2 --- Foreign multinationals specialize in complex products, domestic ones in primary goods", f"f2_{tag}"))
    if not exists(sc, "Graphs", "fig_wp0_fig2_pci.pdf"):
        L.append(par(r"""Not computable for this scope: its HS codes (chapters 98--99, chapter 00 and unclassifiable
lines) carry no product characteristics (PCI, Lall, elasticities), so the product-sophistication
exhibits have no content here."""))
    else:
        fact2_body(sc, L, tag, P)
    # ---------------- Fact 3
    L.append(sec("Fact 3 --- Multinational corporations from a small set of countries dominate exports", f"f3_{tag}"))
    L.append(sub("Original exhibit"))
    L.append(fig(sc, "fig_wp1a_parent_share", f"{P}Figure 4 of the note, reproduced on the current base: foreign-MNE export value by parent country, top 15 plus Other.", f"f4_orig_{tag}", 0.78,
                 "Foreign MNEs with a recorded parent country."))
    L.append(tab(sc, "Tables", "tab_wp1a_parent_share.tex", f"{P}Foreign-MNE export value by parent country (numbers behind the figure)", f"parent_share_{tag}"))
    L.append(sub("Variant: parent country $\\times$ export destination --- tables (item 1c)"))
    for stem, cap in (("value", "export value (USD bn)"), ("rowpct", "row \\%"), ("colpct", "column \\%")):
        L.append(tab(sc, "Tables", f"tab_wp1c_region_{stem}.tex", f"{P}Parent region $\\times$ destination region, {cap}", f"1c_reg_{stem}_{tag}"))
    for stem, cap in (("value", "export value (USD bn)"), ("rowpct", "row \\%"), ("colpct", "column \\%")):
        L.append(tab(sc, "Tables", f"tab_wp1c_country_{stem}.tex", f"{P}Top-10 parents $\\times$ top-10 destinations, {cap}", f"1c_cty_{stem}_{tag}"))
    L.append(tab(sc, "Tables", "tab_wp1c_origin_x_destregion_foreign.tex", f"{P}Foreign-MNE exports: destination region by LAC origin (row \\%)", f"1c_odr_f_{tag}"))
    L.append(tab(sc, "Tables", "tab_wp1c_origin_x_destregion_local.tex", f"{P}Local (unmatched) firms: destination region by LAC origin (row \\%)", f"1c_odr_l_{tag}"))
    L.append(sub("Variant: heat maps (item 1d)"))
    L.append(fig(sc, "fig_wp1d_heatmap_region_rowpct", f"{P}Parent region $\\times$ destination region, row \\%.", f"1d_reg_{tag}", 0.9))
    L.append(fig(sc, "fig_wp1d_heatmap_country_rowpct", f"{P}Top-15 parents $\\times$ top-15 destinations: \\% of the parent's export value going to each destination.", f"1d_row_{tag}", 1.0))
    L.append(fig(sc, "fig_wp1d_heatmap_country_cellpct", f"{P}Top-15 parents $\\times$ top-15 destinations: cell share of all foreign-MNE export value (\\%).", f"1d_cell_{tag}", 1.0))
    L.append(fig(sc, "fig_wp1d_home_share_by_parent", f"{P}Share of each parent's export value shipped to the parent's own country.", f"1d_home_{tag}", 0.85))
    # ---------------- Fact 4
    L.append(sec("Fact 4 --- A small set of large multinational groups accounts for the bulk of exports", f"f4_{tag}"))
    L.append(sub("Original exhibits"))
    L.append(fig(sc, "fig_wp0_fig5_network", f"{P}Figure 5 of the note, reproduced: foreign-MNE export value and parent counts by global affiliate-network size.", f"f5_orig_{tag}", 0.7))
    L.append(tab(sc, "Tables", "tab_wp0_fig5_network.tex", f"{P}Numbers behind Figure 5", f"f5_tab_{tag}"))
    L.append(fig(sc, "fig_wp0_fig6_hhi", f"{P}Figure 6 of the note, reproduced: product-level export concentration, naive firm count vs grouping affiliates by parent.", f"f6_orig_{tag}", 0.9))
    L.append(tab(sc, "Tables", "tab_wp0_fig6_hhi.tex", f"{P}Numbers behind Figure 6: HHI, top-exporter share, effective number of exporters", f"f6_tab_{tag}"))
    L.append(sub("Variant: groups versus affiliates inside the market cells (item 1e, ``MNE cantidad'')"))
    L.append(tab(sc, "Tables", "tab_wp1e_groups_vs_affiliates.tex", f"{P}Affiliates per group in the origin--destination--product--year cells", f"grp_aff_{tag}"))
    L.append(tab(sc, "Regressions", "reg_wp1e_groups.tex", f"{P}Fact-5 regressions with ln(\\# MNE groups) in place of ln(\\# MNE firms)", f"reg_groups_{tag}"))
    # ---------------- Fact 5
    L.append(sec("Fact 5 --- Greater multinational presence is associated with higher trade volumes", f"f5_{tag}"))
    L.append(sub("Original exhibit"))
    L.append(tab(sc, "Regressions", "reg_wp0_table1_repro.tex", f"{P}Table 1 of the note, reproduced: multinational presence and trade volume (intensive and extensive margins)", f"t1_repro_{tag}"))
    L.append(sub("Variant: foreign vs domestic MNEs; foreign MNEs present through headquarters vs not (item 1e)"))
    L.append(tab(sc, "Tables", "tab_wp1e_presence_shares.tex", f"{P}MNE export value by origin: domestic share, and foreign-MNE value by the group's presence at the destination", f"pres_sh_{tag}"))
    L.append(tab(sc, "Regressions", "reg_wp1e_counts.tex", f"{P}Intensive margin: ln(\\# MNE firms) decomposed into foreign / domestic and foreign through HQ / not through HQ", f"reg_counts_{tag}"))
    L.append(tab(sc, "Regressions", "reg_wp1e_extensive.tex", f"{P}Extensive margin: presence dummies decomposed into foreign / domestic and foreign through HQ / not through HQ", f"reg_ext_{tag}"))
    # ---------------- Fact 6
    L.append(sec("Fact 6 --- Distance is a weaker barrier to trade for multinational corporations", f"f6_{tag}"))
    L.append(sub("Original exhibit"))
    L.append(tab(sc, "Regressions", "reg_wp0_table2_repro.tex", f"{P}Table 2 of the note, reproduced: distance and firm exports, multinationals split by presence at the destination", f"t2_repro_{tag}"))
    L.append(sub("Variant: foreign vs domestic MNEs; foreign MNEs present through headquarters vs not (item 1e)"))
    L.append(tab(sc, "Regressions", "reg_wp1e_distance_hq.tex", f"{P}Distance and firm exports: foreign / domestic, then foreign through HQ / not through HQ", f"reg_dist_hq_{tag}"))
    # ---------------- HS6
    L.append(sec("Products at HS6, with descriptions (item 1f)", f"hs6_{tag}"))
    L.append(fig(sc, "fig_wp1f_top20_hs6_stacked", f"{P}Top-20 HS6 products by export value: foreign MNE / domestic MNE / local shares.", f"1f_stack_{tag}", 1.0))
    L.append(fig(sc, "fig_wp1f_top20_hs6_by_parent", f"{P}Top-20 HS6 products: foreign bar split by parent country (remainder = local firms).", f"1f_parent_{tag}", 1.0))
    L.append(fig(sc, "fig_wp1f_foreign_share_distribution", f"{P}Distribution of the HS6 foreign-MNE share: share of export value, and MNE share of exporting firms, by bin.", f"1f_dist_{tag}", 0.85))
    L.append(fig(sc, "fig_wp1f_lorenz_foreign", f"{P}Concentration of exports across HS6 products: foreign-MNE exports vs all exports.", f"1f_lorenz_{tag}", 0.6))
    L.append(tab(sc, "Tables", "tab_wp1f_hs_sections.tex", f"{P}HS sections by export value: MNE shares and leading parent", f"1f_sections_{tag}", size=r"\footnotesize"))
    L.append(tab(sc, "Tables", "tab_wp1f_top_hs6_by_value.tex", f"{P}Top 30 HS6 products by export value", f"1f_val_{tag}", size=r"\footnotesize"))
    L.append(tab(sc, "Tables", "tab_wp1f_top_hs6_by_foreign_value.tex", f"{P}Top 30 HS6 products by foreign-MNE export value", f"1f_fval_{tag}", size=r"\footnotesize"))
    L.append(tab(sc, "Tables", "tab_wp1f_top_hs6_by_foreign_share.tex", f"{P}HS6 products ($\\geq$ \\$500m) with the highest foreign-MNE share", f"1f_fsh_{tag}", size=r"\footnotesize"))
    L.append(tab(sc, "Tables", "tab_wp1f_top_hs6_by_domestic_share.tex", f"{P}HS6 products ($\\geq$ \\$500m) with the highest domestic-MNE share", f"1f_dsh_{tag}", size=r"\footnotesize"))
    L.append(tab(sc, "Tables", "tab_wp1f_foreign_share_distribution.tex", f"{P}Distribution of the HS6 foreign share, numbers", f"1f_disttab_{tag}"))


def fact2_body(sc: str, L: list, tag: str, P: str) -> None:
    L.append(sub("Original exhibits"))
    L.append(fig(sc, "fig_wp0_fig2_pci", f"{P}Figure 2 of the note, reproduced: MNE share of export value by Product Complexity Index quintile.", f"f2_orig_{tag}", 0.78,
                 "Value-weighted at HS6; quintiles of the Hausmann--Hidalgo PCI over the scope's HS6 products (Q1 = least complex)."))
    L.append(fig(sc, "fig_wp0_fig3_lall", f"{P}Figure 3 of the note, reproduced: MNE share of export value by Lall (2000) technology category.", f"f3_orig_{tag}", 0.78))
    L.append(sub("Variant: split by the multinational's home country (item 1a)"))
    L.append(fig(sc, "fig_wp1a_pci_by_parent", f"{P}Figure 2 with the foreign bar split by parent country.", f"f2_parent_{tag}", 0.92))
    L.append(fig(sc, "fig_wp1a_lall_by_parent", f"{P}Figure 3 with the foreign bar split by parent country.", f"f3_parent_{tag}", 0.92))
    L.append(sub("Variant: other measures of product sophistication; substitution elasticities (item 1b)"))
    L.append(fig(sc, "fig_wp1b_panel_quintiles", f"{P}Figure 2 redrawn for six sophistication measures (foreign navy, domestic gray; quintiles over the scope's HS6 products).", f"f2_panel_{tag}", 1.0))
    L.append(fig(sc, "fig_wp1b_sigma_fgo_abs_quintile", f"{P}Figure 2 with $|\\sigma|$ from Fontagn\\'e, Guimbard and Orefice (2022) in place of the PCI.", f"f2_fgo_{tag}", 0.78))
    L.append(fig(sc, "fig_wp1b_panel_hist", f"{P}Full distributions: export value across bins of each measure, stacked by owner type, with the foreign-MNE share of each bin (line, right axis).", f"f2_hist_{tag}", 1.0))
    L.append(fig(sc, "fig_wp1b_hist_sigma_fgo_abs", f"{P}Distribution over $|\\sigma|$ (FGO 2022): export value by owner type and foreign share per bin (left); number of HS6 products per bin (right).", f"f2_hist_fgo_{tag}", 1.0))
    L.append(fig(sc, "fig_wp1b_hist_complexity", f"{P}Distribution over the PCI: export value by owner type and foreign share per bin (left); number of HS6 products per bin (right).", f"f2_hist_pci_{tag}", 1.0))
    L.append(tab(sc, "Tables", "tab_wp1b_quintile_shares.tex", f"{P}Foreign and domestic MNE shares by quintile, six sophistication measures", f"quint_{tag}"))
    L.append(tab(sc, "Tables", "tab_wp1b_measure_corr.tex", f"{P}Correlations across sophistication measures (HS6, value-weighted)", f"corr_{tag}"))
    L.append(tab(sc, "Tables", "tab_wp1b_rauch.tex", f"{P}MNE shares by Rauch (1999) class", f"rauch_{tag}"))
    L.append(tab(sc, "Tables", "tab_wp1b_bec.tex", f"{P}MNE shares by BEC end use", f"bec_{tag}"))
    L.append(tab(sc, "Regressions", "reg_wp1b_odpy_fgo.tex", f"{P}Note's Table A.4 ladder with the FGO elasticity added (ODPY cells, MNE value share)", f"reg_fgo_{tag}"))


def numbers_appendix(sc: str, L: list, tag: str) -> None:
    L.append(sub(W.SCOPE_LABEL[sc].replace("\\\\&", "\\&")))
    L.append(tab(sc, "Tables", "tab_wp0_fig1_origin.tex", "Figure 1 numbers (foreign, domestic, total)", f"a_f1_{tag}"))
    for stem, cap in (("origin", "Figure 1 by parent"), ("pci", "Figure 2 by parent"), ("lall", "Figure 3 by parent")):
        L.append(tab(sc, "Tables", f"tab_wp1a_{stem}_by_parent.tex", f"{cap}, numbers", f"a1a_{stem}_{tag}"))


def subclass_block(sc: str, L: list, tag: str) -> None:
    S = W.SCOPE_LABEL[sc].replace("\\\\&", "\\&")
    L.append(sec(f"Sub-classifications within the sector", f"sub_{tag}"))
    L.append(par(r"""Each split: total and MNE exports, foreign and domestic shares and the three leading parents
(table); the foreign/domestic bars (figure); the origin $\times$ sub-sector heat map of the foreign
share with its two-panel table (Panel A composition of the origin's exports in the sector, rows
sum to 100; Panel B foreign-MNE share within the cell); and the parent-country composition
(top-10 parents, Other foreign, Domestic). Sub-sectors below 0.5\,\% of the sector are pooled
into ``Other'' in the tables and omitted from the heat maps below 1\,\%."""))
    SPLITS = [("hs_section", "HS sections"), ("bec_enduse", "BEC Rev.\\,4 end use"), ("bec4", "BEC Rev.\\,4 detailed categories"),
              ("sitc2", "SITC Rev.\\,3 divisions"), ("naics3", "NAICS 3-digit (product-based)"), ("lall2000_category", "Lall (2000) categories")]
    if sc == "agro":
        SPLITS.append(("inputs", "Agricultural inputs versus output"))
    for stem, title in SPLITS:
        if not exists(sc, "Tables", f"tab_wp2_{stem}.tex"):
            continue
        L.append(ssub(title))
        L.append(tab(sc, "Tables", f"tab_wp2_{stem}.tex", f"{S} by {title}: total and MNE exports, shares, leading parents", f"2_{stem}_{tag}", size=r"\footnotesize"))
        L.append(fig(sc, f"fig_wp2_{stem}", f"{S}: foreign and domestic MNE shares by {title}.", f"2_{stem}_fig_{tag}", 0.9))
        L.append(fig(sc, f"fig_wp2_origin_x_{stem}", f"{S}: foreign-MNE share by origin and {title} (\\%).", f"2_{stem}_hm_{tag}", 0.95))
        L.append(tab(sc, "Tables", f"tab_wp2_origin_x_{stem}.tex", f"{S}: composition (Panel A) and foreign-MNE share (Panel B) by origin and {title}", f"2_{stem}_ht_{tag}", size=r"\footnotesize"))
        L.append(tab(sc, "Tables", f"tab_wp2_{stem}_by_parent.tex", f"{S}: parent-country composition of exports by {title} (\\%)", f"2_{stem}_par_{tag}", size=r"\footnotesize"))
        if stem == "inputs":
            L.append(tab(sc, "Tables", "tab_wp2_top_inputs_hs6.tex", f"{S}: top HS6 lines among agricultural inputs", f"2_topinputs_{tag}", size=r"\footnotesize"))
    L.append(ssub("Cross-classification: HS section $\\times$ BEC end use"))
    L.append(tab(sc, "Tables", "tab_wp2_section_x_enduse_value.tex", f"{S}: HS section $\\times$ BEC end use, export value (USD bn)", f"2_sxe_val_{tag}"))
    L.append(tab(sc, "Tables", "tab_wp2_section_x_enduse_foreignshare.tex", f"{S}: HS section $\\times$ BEC end use, foreign-MNE share (\\%)", f"2_sxe_fsh_{tag}"))


# ---------------------------------------------------------------------
def build_total() -> Path:
    L = [preamble("Stylized Facts on Multinational Firms and Trade in Latin America",
                  "Each fact with its original exhibit reproduced on the current base and the variants for the working paper --- all goods")]
    L.append(intro_total())
    fact_block("all", L, "all")
    L.append(sec("The four sectors at a glance (item 2)", "sectors"))
    L.append(par(r"""Sector definitions in the conventions above. The full set of exhibits within each sector is in
the companion document \emph{WP\_sectors}."""))
    L.append(tab("sectors", "Tables", "tab_wp2_four_sectors.tex", "The four sectors: total and MNE exports, shares, leading parents", "2_sectors"))
    L.append(fig("sectors", "fig_wp2_four_sectors", "Foreign and domestic MNE shares by sector.", "2_sectors_fig", 0.8))
    L.append(fig("sectors", "fig_wp2_origin_x_sector", "Foreign-MNE share by origin and sector (\\%).", "2_ox_fsh", 0.8))
    L.append(tab("sectors", "Tables", "tab_wp2_origin_x_sector.tex", "Composition (Panel A) and foreign-MNE share (Panel B) by origin and sector", "2_ox_t"))
    L.append(tab("sectors", "Tables", "tab_wp2_sector_x_destregion_foreign.tex", "Foreign-MNE exports: destination region by sector (row \\%)", "2_sdr"))
    L.append(tab("sectors", "Tables", "memo_wp2_services.tex", "Memo: service-sector affiliates among matched exporters (NAICS of the affiliate)", "2_services"))
    L.append(r"\appendix" + "\n" + sec("Numbers behind the figures", "a1"))
    numbers_appendix("all", L, "all")
    L.append(r"\end{document}" + "\n")
    return write_main(L)


def build_sectors() -> Path:
    L = [preamble("Stylized Facts on Multinational Firms and Trade in Latin America",
                  "Sector-by-sector version: agriculture, manufacturing, mining \\& fuels, rest")]
    L.append(intro_sectors())
    L.append(tab("sectors", "Tables", "tab_wp2_four_sectors.tex", "The four sectors: total and MNE exports, shares, leading parents", "2_sectors"))
    L.append(fig("sectors", "fig_wp2_four_sectors", "Foreign and domestic MNE shares by sector.", "2_sectors_fig", 0.8))
    L.append(fig("sectors", "fig_wp2_origin_x_sector", "Foreign-MNE share by origin and sector (\\%).", "2_ox_fsh", 0.8))
    L.append(tab("sectors", "Tables", "tab_wp2_origin_x_sector.tex", "Composition (Panel A) and foreign-MNE share (Panel B) by origin and sector", "2_ox_t"))
    L.append(tab("sectors", "Tables", "memo_wp2_services.tex", "Memo: service-sector affiliates among matched exporters (NAICS of the affiliate)", "2_services"))
    for sc in SECTOR_SCOPES:
        S = W.SCOPE_LABEL[sc].replace("\\\\&", "\\&")
        L.append(r"\clearpage\part{" + S + "}\n")
        fact_block(sc, L, sc)
        subclass_block(sc, L, sc)
    L.append(r"\appendix" + "\n" + sec("Numbers behind the figures", "a1"))
    for sc in SECTOR_SCOPES:
        numbers_appendix(sc, L, sc)
    L.append(r"\end{document}" + "\n")
    return write_main(L)


def build_countries() -> Path:
    L = [preamble("Stylized Facts on Multinational Firms and Trade in Latin America", "Country-by-country exhibits")]
    L.append(intro_countries())
    for o in ORIGINS:
        L.append(sec(o, f"c_{o}"))
        L.append(sub("Parents and destinations"))
        L.append(tab("all", "Tables", f"tab_wp1c_byorigin_{o}.tex", f"{o}: parent region $\\times$ destination region, row \\% (all goods)", f"c_reg_{o}"))
        L.append(fig("all", f"fig_wp1d_heatmap_country_cellpct_{o}", f"{o}: top-15 parents $\\times$ top-15 destinations, cell share of the origin's foreign-MNE export value (\\%).", f"c_hm_{o}", 1.0))
        L.append(fig("all", f"fig_wp1d_home_share_by_parent_{o}", f"{o}: share of each parent's export value from {o} shipped to the parent's own country (top-10 parents).", f"c_home_{o}", 0.85))
        for sc in SECTOR_SCOPES:
            if exists(sc, "Tables", f"tab_wp1c_byorigin_{o}.tex"):
                L.append(tab(sc, "Tables", f"tab_wp1c_byorigin_{o}.tex", f"{o}, {W.SCOPE_LABEL[sc].replace(chr(92)*2 + '&', chr(92) + '&')}: parent region $\\times$ destination region, row \\%", f"c_reg_{o}_{sc}"))
        L.append(sub("Products"))
        L.append(tab("all", "Tables", f"tab_wp1f_top_hs6_{o}.tex", f"{o}: top 15 HS6 products (all goods)", f"c_hs6_{o}", size=r"\footnotesize"))
        for sc in SECTOR_SCOPES:
            if exists(sc, "Tables", f"tab_wp1f_top_hs6_{o}.tex"):
                L.append(tab(sc, "Tables", f"tab_wp1f_top_hs6_{o}.tex", f"{o}, {W.SCOPE_LABEL[sc].replace(chr(92)*2 + '&', chr(92) + '&')}: top 15 HS6 products", f"c_hs6_{o}_{sc}", size=r"\footnotesize"))
    L.append(r"\end{document}" + "\n")
    return write_main(L)


def write_main(L) -> Path:
    main = DST / "main.tex"
    main.write_text("".join(L), encoding="utf-8")
    nfig = sum(1 for _ in DST.glob("Graphs/*/*.pdf")); ntab = sum(1 for _ in DST.glob("Tables/*/*.tex")) + sum(1 for _ in DST.glob("Regressions/*/*.tex"))
    print(f"   main.tex written: {nfig} figures, {ntab} table fragments; {len(MISSING)} missing exhibits")
    for m in MISSING[:12]:
        print("      missing:", m)
    return main


def compile_pdf(main: Path) -> bool:
    for _ in range(3):
        r = subprocess.run([PDFLATEX, "-interaction=nonstopmode", "-halt-on-error", main.name], cwd=main.parent, capture_output=True, text=True, errors="replace")
    ok = (main.parent / "main.pdf").exists() and r.returncode == 0
    log = (main.parent / "main.log").read_text(encoding="utf-8", errors="replace")
    if not ok:
        i = log.find("\n!"); print("   pdflatex FAILED:\n" + (log[i:i + 1500] if i >= 0 else r.stdout[-2000:]))
    else:
        warn = [l for l in log.split("\n") if "undefined" in l.lower() or "multiply" in l.lower()]
        pages = log[log.rfind("Output written"):].split("(")[1].split(" page")[0] if "Output written" in log else "?"
        print(f"   compiled OK: {pages} pages" + (f"   ({len(warn)} reference warnings)" if warn else ""))
        for l in warn[:6]:
            print("      ", l.strip())
    return ok


def zip_project(folder: Path) -> Path:
    out = folder.with_suffix(".zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in folder.rglob("*"):
            if p.is_file() and (p.suffix in {".tex"} or (p.suffix == ".pdf" and p.parent != folder)):
                z.write(p, p.relative_to(folder))
    print(f"   zip -> {out.name} ({out.stat().st_size / 1e6:.1f} MB)")
    return out


DOCS_SPEC = {"total": (build_total, True), "sectors": (build_sectors, False), "countries": (build_countries, False)}

if __name__ == "__main__":
    want = sys.argv[1:] or list(DOCS_SPEC)
    for name in want:
        builder, strict = DOCS_SPEC[name]
        DST = W.WP_OUT / f"overleaf_WP_{name}"
        STRICT = strict; MISSING.clear()
        if DST.exists():
            shutil.rmtree(DST)
        DST.mkdir(parents=True)
        print(f"\n### WP_{name}")
        main = builder()
        if compile_pdf(main):
            shutil.copy2(main.parent / "main.pdf", DOCS / f"WP_{name}_{TODAY}.pdf")
            print("   copied ->", DOCS / f"WP_{name}_{TODAY}.pdf")
        zip_project(DST)
