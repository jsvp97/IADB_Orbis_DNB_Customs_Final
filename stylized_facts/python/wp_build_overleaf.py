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
  4. WP_draft      (revision 6) the working-paper draft for the coauthors: only the exhibits the internal
                   review marks MOSTRAR (main text) and APOYO / APENDICE (appendix), clean captions, a short
                   data paragraph, no reading guide.
  6. WP_draft2     (2026-09-23) second version of WP_draft: main text and appendix as two separate parts,
                   referee-facing titles and short notes (fragment notes replaced, internal labels relabelled).
  5. WP_paper      THE working paper itself: title page with abstract, introduction and data section written
                   out, the [Main text] exhibits of WP_draft in fact order with a short reading paragraph per
                   fact, the [Appendix] ones in the appendix, and the remaining sections (literature, model,
                   conclusions) stated but not developed.

    python wp_build_overleaf.py            -> output/wp/overleaf_WP_{total,sectors,countries,draft,paper}/  (+ .zip, + docs/*.pdf)
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
DRAFT_MODE = False # set while building WP_draft: strips references to the July note from the fragment notes
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
    if DRAFT_MODE and note:   # the working-paper draft does not refer to the July note
        note = re.sub(r"\s*Reproduction of the note's Table \d on the current base(: |\.\s*)", " ", note).strip()
        note = note[:1].upper() + note[1:] if note else note
    n = rf"\par\vspace{{3pt}}\begin{{minipage}}{{0.95\textwidth}}\footnotesize {note}\end{{minipage}}" if note else ""
    return (rf"\begin{{table}}[H]\centering{size}\caption{{{caption}}}\label{{tab:{label}}}"
            rf"\adjustbox{{max width=\textwidth, max totalheight=0.8\textheight}}{{\input{{{path}}}}}{n}\end{{table}}" "\n")


def sec(title, label=None): return f"\n\\section{{{title}}}" + (f"\\label{{sec:{label}}}" if label else "") + "\n"
def sub(title): return f"\n\\subsection{{{title}}}\n"
def ssub(title): return f"\n\\subsubsection{{{title}}}\n"
def par(text): return text.strip() + "\n\n"


def preamble(title, subtitle, datestr=None, toc=True):
    datestr = datestr or (date.today().strftime("%B %d, %Y") + " --- draft for internal review")
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
\date{""" + datestr + r"""}
\begin{document}
\maketitle
""" + (r"""\tableofcontents
\clearpage
""" if toc else "")


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
regressions (1e); products at HS6 with descriptions (1f). Revision 6 (2026-09-18) adds the
destination side of Fact~3---who carries the exports that reach the United States, China and the
EU-27, and which lines US-parent MNEs ship home---and the cross-sector summaries (US-parent share by
origin $\times$ sector, home share by parent $\times$ sector, Facts~5 and~6 in one table each). The four
sectors are summarised at the end; the sector-by-sector version of every exhibit is the companion document
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
    if sc == "all":
        L.append(sub("Variant: the US-parent share of exports by origin and sector (revision 6)"))
        L.append(fig("sectors", "fig_wp3_us_share_origin_sector", "Share of each origin's export value moved by multinationals with a US parent, all goods and by sector.", "f1_us_ox_sector", 1.0,
                     "Share of the cell's export value (all destinations); origins sorted by the all-goods share. Sector versions of Figure~\\ref{fig:f1_parent_all} are in \\emph{WP\\_sectors}; this figure replaces them for the US-parent question."))
        L.append(tab("sectors", "Tables", "tab_wp3_us_share_origin_sector.tex", "US-parent MNE share of exports and US-parent export value, by origin and sector", "us_ox_sector"))
        L.append(fig(sc, "fig_wp3_us_three_shares_total", "Exports of the nine origins: share going to the USA, share carried by US-parent MNEs, and both (same denominator: total exports; revision 7).", "us3_total", 0.6))
        L.append(fig(sc, "fig_wp3_us_three_shares_origin", "The same three shares by origin.", "us3_origin", 1.0))
        L.append(tab(sc, "Tables", "tab_wp3_us_three_shares.tex", "Exports going to the USA, carried by US-parent MNEs, and both, as shares of total exports: all origins and by origin", "us3_tab"))
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
    L.append(fig(sc, "fig_wp1a_parent_share_total", f"{P}The same ranking with total exports as the denominator: share of total export value by parent country, other foreign MNEs and domestic MNEs (revision 8).", f"f4_total_{tag}", 0.85))
    L.append(tab(sc, "Tables", "tab_wp1a_parent_share_total.tex", f"{P}Share of total export value by parent country (numbers behind the figure)", f"parent_share_total_{tag}"))
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
    L.append(tab(sc, "Tables", "tab_wp1c_parent_x_parentdest_rowpct.tex", f"{P}Top-10 parents $\\times$ the same ten countries as destinations (row \\%): the diagonal is the home share (revision 7)", f"1c_pxp_{tag}"))
    L.append(fig(sc, "fig_wp1d_home_share_by_parent_consolidated", f"{P}Home share with parents consolidated: dependencies folded into their sovereign, stand-alone tax havens and conduits pooled (revision 7).", f"1d_home_cons_{tag}", 0.85))
    L.append(tab(sc, "Tables", "tab_wp1d_home_share_by_parent_consolidated.tex", f"{P}Home share by consolidated parent (numbers behind the figure)", f"1d_home_cons_tab_{tag}"))
    L.append(fig(sc, "fig_wp1d_home_share_haven_panels", f"{P}Home share: Panel A the ten largest non-haven parents (dependencies folded into their sovereign), Panel B the ten largest tax-haven and conduit jurisdictions (revision 8).", f"1d_home_havens_{tag}", 1.0))
    L.append(tab(sc, "Tables", "tab_wp1d_home_share_haven_panels.tex", f"{P}Home share, non-haven parents and haven jurisdictions (numbers behind the figure)", f"1d_home_havens_tab_{tag}"))
    if sc == "all":
        L.append(fig("sectors", "fig_wp3_home_share_by_parent_sectors", "Share of each parent's export value shipped to the parent's own country: all goods and the three sectors, top-10 parents.", "1d_home_sectors", 0.95,
                     "Hatched bars: the parent exports less than \\$1bn in the sector, so the share is fragile; the parent's exports in each scope are in parentheses."))
        L.append(tab("sectors", "Tables", "tab_wp3_home_share_by_parent_sectors.tex", "Home share by parent, all goods and by sector (numbers behind the figure)", "1d_home_sectors_tab", size=r"\footnotesize"))
    destination_side(sc, L, tag, P)
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
    if sc == "all":
        L.append(sub("Summary across sectors (revision 6)"))
        L.append(tab("sectors", "Tables", "tab_wp3_fact5_summary.tex", "Fact 5 in one table: ln(\\# foreign MNEs) and ln(\\# domestic MNEs), all goods and by sector", "fact5_summary"))
    # ---------------- Fact 6
    L.append(sec("Fact 6 --- Distance is a weaker barrier to trade for multinational corporations", f"f6_{tag}"))
    L.append(sub("Original exhibit"))
    L.append(tab(sc, "Regressions", "reg_wp0_table2_repro.tex", f"{P}Table 2 of the note, reproduced: distance and firm exports, multinationals split by presence at the destination", f"t2_repro_{tag}"))
    L.append(sub("Variant: foreign vs domestic MNEs; foreign MNEs present through headquarters vs not (item 1e)"))
    L.append(tab(sc, "Regressions", "reg_wp1e_distance_hq.tex", f"{P}Distance and firm exports: foreign / domestic, then foreign through HQ / not through HQ", f"reg_dist_hq_{tag}"))
    if sc == "all":
        L.append(sub("Summary across sectors (revision 6)"))
        L.append(tab("sectors", "Tables", "tab_wp3_fact6_summary.tex", "Fact 6 in one table: distance elasticity and its attenuation for foreign and domestic MNEs, all goods and by sector", "fact6_summary"))
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


def destination_side(sc: str, L: list, tag: str, P: str) -> None:
    """Revision 6: Fact 3 seen from the destination -- who carries the exports that reach the USA (and the other main
    markets), and which lines US-parent MNEs ship home. Cross-sector versions come from output/wp/sectors/."""
    if not exists(sc, "Tables", "tab_wp3_dest_carriers.tex") and not exists(sc, "Tables", "tab_wp3_to_usa_carriers.tex"):
        return
    L.append(sub("Variant: seen from the destination --- who carries the exports that reach each market (revision 6)"))
    L.append(par(r"""The exhibits above ask where each parent ships. These turn the question around: of the value that
reaches a destination, how much is moved by multinationals whose parent sits in that destination, by US-parent
MNEs, by other foreign MNEs, by domestic MNEs and by local (unmatched) firms."""))
    if sc == "all":
        L.append(fig("sectors", "fig_wp3_to_usa_carriers_total_manuf", "Exports to the United States by origin: share moved by US-parent MNEs, other foreign MNEs, domestic MNEs and local firms --- all goods (left) and manufacturing (right).", "to_usa_total_manuf", 1.0,
                     "Origins sorted by the all-goods US-parent share; right margin = the origin's exports to the USA in the scope."))
        L.append(tab("sectors", "Tables", "tab_wp3_to_usa_carriers_by_sector.tex", "Exports to the United States by sector: who carries them (\\%)", "to_usa_by_sector"))
        L.append(tab(sc, "Tables", "tab_wp3_to_usa_carriers.tex", "Exports to the United States by origin, all goods: who carries them (numbers behind the left panel)", f"to_usa_{tag}"))
    else:
        L.append(fig(sc, "fig_wp3_to_usa_carriers", f"{P}Exports to the United States by origin: share moved by US-parent MNEs, other foreign MNEs, domestic MNEs and local firms.", f"f_to_usa_{tag}", 0.9))
        L.append(tab(sc, "Tables", "tab_wp3_to_usa_carriers.tex", f"{P}Exports to the United States by origin: who carries them (\\%)", f"to_usa_{tag}"))
    L.append(fig(sc, "fig_wp3_dest_carriers", f"{P}The largest destination markets (EU-27 pooled): share of the value reaching each one moved by MNEs with a parent in the destination, US-parent MNEs, other foreign MNEs, domestic MNEs and local firms.", f"f_dest_{tag}", 0.95))
    L.append(tab(sc, "Tables", "tab_wp3_dest_carriers.tex", f"{P}The largest destination markets: who carries the exports that reach them (\\%)", f"dest_{tag}", size=r"\footnotesize"))
    L.append(tab(sc, "Tables", "tab_wp3_us_home_products.tex", f"{P}What US-parent MNEs ship to the United States: top-15 HS6 lines, and the US-parent share of everything LAC exports of the line to the USA", f"us_home_prod_{tag}", size=r"\footnotesize"))
    L.append(fig(sc, "fig_wp3_us_home_products", f"{P}US-parent MNEs' share of LAC exports to the United States, for the 15 lines they ship home in the largest value.", f"f_us_home_prod_{tag}", 0.95))
    L.append(tab(sc, "Tables", "tab_wp3_to_usa_top_products.tex", f"{P}The 15 largest LAC export lines to the United States: who carries them (\\%)", f"to_usa_prod_{tag}", size=r"\footnotesize"))


def fact2_body(sc: str, L: list, tag: str, P: str) -> None:
    L.append(sub("Original exhibits"))
    L.append(fig(sc, "fig_wp0_fig2_pci", f"{P}Figure 2 of the note, reproduced: MNE share of export value by Product Complexity Index quintile.", f"f2_orig_{tag}", 0.78,
                 "Value-weighted at HS6; quintiles of the Hausmann--Hidalgo PCI over the scope's HS6 products (Q1 = least complex)."))
    L.append(fig(sc, "fig_wp0_fig3_lall", f"{P}Figure 3 of the note, reproduced: MNE share of export value by Lall (2000) technology category.", f"f3_orig_{tag}", 0.78))
    L.append(sub("Variant: split by the multinational's home country (item 1a)"))
    L.append(fig(sc, "fig_wp1a_pci_by_parent", f"{P}Figure 2 with the foreign bar split by parent country.", f"f2_parent_{tag}", 0.92))
    L.append(fig(sc, "fig_wp1a_lall_by_parent", f"{P}Figure 3 with the foreign bar split by parent country.", f"f3_parent_{tag}", 0.92))
    L.append(fig(sc, "fig_wp1a_pci_lall_by_oecd", f"{P}Figures 2 (Panel A) and 3 (Panel B) with the foreign bar split into OECD-parent and non-OECD-parent multinationals (revision 7).", f"f23_oecd_{tag}", 1.0))
    L.append(sub("Variant: other measures of product sophistication; substitution elasticities (item 1b)"))
    L.append(fig(sc, "fig_wp1b_panel_quintiles", f"{P}Figure 2 redrawn for six sophistication measures (foreign navy, domestic gray; quintiles over the scope's HS6 products).", f"f2_panel_{tag}", 1.0))
    L.append(fig(sc, "fig_wp1b_sigma_fgo_abs_quintile", f"{P}Figure 2 with $|\\sigma|$ from Fontagn\\'e, Guimbard and Orefice (2022) in place of the PCI.", f"f2_fgo_{tag}", 0.78))
    L.append(fig(sc, "fig_wp1b_panel_hist", f"{P}Full distributions: export value across bins of each measure, stacked by owner type, with the foreign-MNE share of each bin (line, right axis).", f"f2_hist_{tag}", 1.0))
    L.append(fig(sc, "fig_wp1b_hist_sigma_fgo_abs", f"{P}Distribution over $|\\sigma|$ (FGO 2022): export value by owner type and foreign share per bin (left); number of HS6 products per bin (right).", f"f2_hist_fgo_{tag}", 1.0))
    L.append(fig(sc, "fig_wp1b_hist_complexity", f"{P}Distribution over the PCI: export value by owner type and foreign share per bin (left); number of HS6 products per bin (right).", f"f2_hist_pci_{tag}", 1.0))
    L.append(tab(sc, "Tables", "tab_wp1b_quintile_shares.tex", f"{P}Foreign and domestic MNE shares by quintile, six sophistication measures", f"quint_{tag}"))
    L.append(tab(sc, "Tables", "tab_wp1b_measure_corr.tex", f"{P}Correlations across sophistication measures (HS6, value-weighted)", f"corr_{tag}"))
    L.append(tab(sc, "Tables", "tab_wp1b_rauch.tex", f"{P}MNE shares by Rauch (1999) class", f"rauch_{tag}"))
    L.append(tab(sc, "Tables", "tab_wp1b_rauch2.tex", f"{P}MNE shares by Rauch (1999) class, two classes: differentiated vs non-differentiated (reference-priced + homogeneous)", f"rauch2_{tag}"))
    L.append(fig(sc, "fig_wp1b_rauch2", f"{P}Foreign vs domestic MNE shares of export value: differentiated vs non-differentiated products (Rauch 1999; non-differentiated = reference-priced + homogeneous).", f"f_rauch2_{tag}", 0.7))
    L.append(tab(sc, "Tables", "tab_wp1b_bec.tex", f"{P}MNE shares by BEC end use", f"bec_{tag}"))
    L.append(tab(sc, "Regressions", "reg_wp1b_odpy_fgo.tex", f"{P}Note's Table A.4 ladder with the FGO elasticity added (ODPY cells, MNE value share)", f"reg_fgo_{tag}"))
    L.append(tab(sc, "Regressions", "reg_wp1b_odpy_measures.tex", f"{P}Product sophistication and MNE shares: PCI, Lall categories and Rauch classes, each in a separate regression (revision 7)", f"reg_meas_{tag}", size=r"\footnotesize"))


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
    L.append(sub("The sectors side by side (revision 6)"))
    L.append(fig("sectors", "fig_wp3_us_share_origin_sector", "Share of each origin's export value moved by multinationals with a US parent, all goods and by sector.", "f1_us_ox_sector", 1.0))
    L.append(tab("sectors", "Tables", "tab_wp3_us_share_origin_sector.tex", "US-parent MNE share of exports and US-parent export value, by origin and sector", "us_ox_sector"))
    L.append(fig("sectors", "fig_wp3_home_share_by_parent_sectors", "Share of each parent's export value shipped to the parent's own country: all goods and the three sectors, top-10 parents.", "1d_home_sectors", 0.95,
                 "Hatched bars: the parent exports less than \\$1bn in the sector, so the share is fragile; the parent's exports in each scope are in parentheses."))
    L.append(tab("sectors", "Tables", "tab_wp3_home_share_by_parent_sectors.tex", "Home share by parent, all goods and by sector (numbers behind the figure)", "1d_home_sectors_tab", size=r"\footnotesize"))
    L.append(fig("sectors", "fig_wp3_to_usa_carriers_total_manuf", "Exports to the United States by origin: share moved by US-parent MNEs, other foreign MNEs, domestic MNEs and local firms --- all goods (left) and manufacturing (right).", "to_usa_total_manuf", 1.0))
    L.append(tab("sectors", "Tables", "tab_wp3_to_usa_carriers_by_sector.tex", "Exports to the United States by sector: who carries them (\\%)", "to_usa_by_sector"))
    L.append(tab("sectors", "Tables", "tab_wp3_fact5_summary.tex", "Fact 5 in one table: ln(\\# foreign MNEs) and ln(\\# domestic MNEs), all goods and by sector", "fact5_summary"))
    L.append(tab("sectors", "Tables", "tab_wp3_fact6_summary.tex", "Fact 6 in one table: distance elasticity and its attenuation for foreign and domestic MNEs, all goods and by sector", "fact6_summary"))
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


DRAFT_DATA = r"""
\paragraph{Data.} Customs transactions of nine Latin American exporters (Argentina, Chile, Colombia, Costa
Rica, the Dominican Republic, El Salvador, Paraguay, Peru and Uruguay), 2006--2022, at the firm $\times$
destination $\times$ HS6 product $\times$ year level, matched to the ownership records of Orbis and Dun \&
Bradstreet. A matched exporter is an affiliate of a multinational group: a \emph{domestic} multinational when
its ultimate parent is in the exporting country, a \emph{foreign} multinational otherwise (matched firms with no
recorded parent country count as foreign); unmatched exporters are \emph{local} firms. Shares are value-weighted
and pooled over 2006--2022. Sectors: agriculture = HS 01--24; mining and fuels = HS 25--27 and 71; manufacturing =
HS 28--97 excluding 71. Where the foreign bar is split by the parent's country, the ten largest parent countries
are shown individually and every other foreign multinational is pooled. Matched exporters whose parent country
is not recorded (7.5\,\% of foreign-MNE export value) are allocated to parent countries in proportion to the
recorded parents of the same group, so every share by parent country refers to all foreign MNEs and adds up with
the domestic and local shares; a share by parent country computed among recorded parents is therefore identical
to the share of all foreign MNEs. Regressions use plain logarithms and
cluster standard errors at origin--destination. Dollar values are annual averages: each origin's pooled
value divided by the number of years it is observed (Argentina 2011--2019, Chile 2009--2022, Colombia
2010--2021, Costa Rica 2010--2019, Dominican Republic 2012--2019, Peru 2010--2019, Paraguay 2012--2020,
El Salvador 2006--2018, Uruguay 2010--2019).
"""


MAIN, APP = r"\textbf{[Main text]}", r"\textbf{[Appendix]}"


def panel_fig(items, caption, label, width=0.48, note=""):
    """One figure with lettered panels (A, B, C ...), each an existing graph. `items` = [(scope, name, panel title)]."""
    parts = []
    for k, (scope, name, title) in enumerate(items):
        if not exists(scope, "Graphs", f"{name}.pdf"):
            return missing("figure", scope, name)
        path = copy_fig(scope, name)
        parts.append(rf"\begin{{minipage}}[t]{{{width}\textwidth}}\centering\textbf{{Panel {chr(65 + k)}. {title}}}\\[2pt]"
                     rf"\includegraphics[width=\linewidth,height=0.42\textheight,keepaspectratio]{{{path}}}\end{{minipage}}")
    sep = r"\hfill" if width <= 0.5 else r"\\[8pt]"
    n = rf"\par\vspace{{2pt}}\parbox{{0.92\textwidth}}{{\footnotesize\textit{{Note:}} {note}}}" if note else ""
    return rf"\begin{{figure}}[H]\centering" + sep.join(parts) + rf"\caption{{{caption}}}\label{{fig:{label}}}{n}\end{{figure}}" + "\n"


def build_draft() -> Path:
    """The working-paper draft for the coauthors (revision 8). Order of the 2026-09-18 draft; every caption starts
    with a bold [Main text] / [Appendix] tag (Volpe's assignment); the former appendix exhibits sit next to the
    exhibit they document; dollar values are annual averages and figures carry none; every share exhibit comes
    from the single share engine (W.flow_shares) and the captions state the denominator and the identities that
    link exhibits (10.0 % = US-parent share of total exports; 22.3 % = share of US-parent exports going home;
    2.2 % = 10.0 % x 22.3 %)."""
    L = [preamble("Multinational Firms and Trade in Latin America", "Six stylized facts --- working paper draft",
                  datestr=date.today().strftime("%B %Y"), toc=False)]
    L.append(DRAFT_DATA)
    A, M, MI, S = "all", "manufacturing", "mining", "sectors"
    # ---- Fact 1
    L.append(sec("Fact 1 --- Multinational corporations account for a large share of export values across countries"))
    L.append(fig(A, "fig_wp0_fig1_origin", f"{MAIN} MNE share of export value by origin: foreign and domestic multinationals.", "d_f1", 0.8))
    L.append(tab(A, "Tables", "tab_wp0_fig1_origin.tex", f"{APP} Numbers behind the previous figure: foreign, domestic and total MNE shares by origin", "d_f1n"))
    L.append(fig(A, "fig_wp1a_origin_by_parent", f"{APP} MNE share of export value by origin, foreign bar split by the parent's country (top 10, other foreign, domestic).", "d_f1_parent", 0.92))
    L.append(tab(A, "Tables", "tab_wp1a_origin_by_parent.tex", f"{APP} Numbers behind the previous figure", "d_f1pn"))
    L.append(fig(S, "fig_wp3_fig1_by_sector_panels", f"{APP} MNE share of export value by origin within each sector: foreign and domestic multinationals (Panel A agriculture, Panel B manufacturing, Panel C mining and fuels).", "d_f1_sectors", 1.0))
    L.append(tab(S, "Tables", "tab_wp2_four_sectors.tex", f"{APP} The four sectors: total and MNE exports, foreign and domestic shares, leading parents", "d_sectors"))
    L.append(sub("The United States"))
    L.append(fig(A, "fig_wp3_us_three_shares_total", f"{MAIN} Exports of the nine origins, as shares of total exports: going to the United States, carried by US-parent MNEs, and both.", "d_us3_total", 0.6,
                 "Same denominator for the three bars: total export value of the nine origins, all firms and destinations. The second bar is the USA's share of foreign-MNE value (23.3\\,\\%, Fact 3) times the foreign-MNE share of exports (46.3\\,\\%, Figure~\\ref{fig:d_f1}); the third bar is the second times the share of US-parent exports that goes to the United States (22.3\\,\\%, the USA row of the parent $\\times$ destination tables in Fact 3)."))
    L.append(fig(A, "fig_wp3_us_three_shares_origin", f"{MAIN} The same three shares by origin (denominator: the origin's total exports).", "d_us3_origin", 1.0))
    L.append(tab(A, "Tables", "tab_wp3_us_three_shares.tex", f"{MAIN} Exports going to the United States, carried by US-parent MNEs, and both, as shares of total exports; and the US-parent share of the exports going to the United States", "d_us3_tab"))
    # ---- Fact 2
    L.append(sec("Fact 2 --- Foreign multinationals specialize in complex products, domestic ones in primary goods"))
    L.append(panel_fig([(A, "fig_wp0_fig2_pci", "By quintile of the Product Complexity Index (Q1 = least complex)"), (A, "fig_wp0_fig3_lall", "By Lall (2000) technology category")],
                       f"{MAIN} MNE share of export value by product sophistication: foreign and domestic multinationals.", "d_f2f3", width=0.72))
    L.append(fig(A, "fig_wp1a_pci_lall_by_oecd", f"{MAIN} MNE share by PCI quintile (Panel A) and Lall category (Panel B), foreign bar split into OECD-parent and non-OECD-parent multinationals.", "d_f2_oecd", 1.0,
                 "OECD = the 38 member countries; matched firms with no recorded parent country are counted with the non-OECD parents."))
    L.append(tab(A, "Tables", "tab_wp1b_rauch.tex", f"{MAIN} MNE shares by Rauch (1999) class: differentiated, reference-priced, homogeneous", "d_rauch"))
    L.append(fig(A, "fig_wp1b_rauch", f"{MAIN} Foreign vs domestic MNE shares of export value by Rauch (1999) class: differentiated, reference-priced, homogeneous.", "d_rauch_fig", 0.7))
    L.append(tab(A, "Tables", "tab_wp1b_bec.tex", f"{MAIN} MNE shares by BEC end use: intermediate, consumption and capital goods", "d_bec"))
    L.append(tab(A, "Regressions", "reg_wp1b_odpy_measures.tex", f"{MAIN} Product sophistication and MNE shares: PCI, Lall categories and Rauch classes, each in a separate regression (one observation = origin $\\times$ destination $\\times$ HS6 product $\\times$ year)", "d_ladder", size=r"\footnotesize"))
    L.append(sub("Within manufacturing"))
    L.append(fig(M, "fig_wp0_fig2_pci", f"{APP} Manufacturing: MNE share of export value by PCI quintile (quintiles over manufacturing HS6 products).", "d_f2_manuf", 0.78))
    L.append(fig(M, "fig_wp1b_rauch", f"{MAIN} Manufacturing: foreign vs domestic MNE shares by Rauch (1999) class: differentiated, reference-priced, homogeneous.", "d_rauch_manuf", 0.7))
    # ---- Fact 3
    L.append(sec("Fact 3 --- Multinational corporations from a small set of countries dominate exports"))
    L.append(fig(A, "fig_wp1a_parent_share", f"{MAIN} Foreign-MNE export value by the parent's country: top 15 and other (Figure 4 of the July note).", "d_f4", 0.78,
                 "Share of all foreign-MNE export value. Foreign MNEs export 46.3\\,\\% of total exports (Figure~\\ref{fig:d_f1}), so the USA's 23.3\\,\\% of foreign-MNE value is $0.233 \\times 46.3 = 10.8\\,\\%$ of total exports, the US-parent share reported in the US three-share exhibit."))
    L.append(tab(A, "Tables", "tab_wp1c_country_rowpct.tex", f"{MAIN} Top-10 parents $\\times$ top-10 destinations: destination mix of each parent's exports (row \\%)", "d_pxd"))
    L.append(tab(A, "Tables", "tab_wp1c_parent_x_parentdest_rowpct.tex", f"{MAIN} Top-10 parents $\\times$ the same ten countries as destinations (row \\%): the diagonal is the share of each parent's exports shipped to the parent's own country (USA 22.3\\,\\%)", "d_pxp"))
    L.append(tab(A, "Tables", "tab_wp1c_region_rowpct.tex", f"{APP} Parent region $\\times$ destination region: destination mix of each group (row \\%)", "d_a_reg"))
    L.append(fig(A, "fig_wp1d_heatmap_country_rowpct", f"{APP} Top-15 parents $\\times$ top-15 destinations: \\% of the parent's export value going to each destination.", "d_a_hm_row", 1.0))
    L.append(fig(A, "fig_wp1d_home_share_by_parent", f"{APP} Share of each parent's export value shipped to the parent's own country, parents as recorded (the diagonal of the previous tables).", "d_home", 0.85))
    L.append(fig(A, "fig_wp1d_home_share_haven_panels", f"{APP} Share of each parent's export value shipped to the parent's own jurisdiction: Panel A, the ten largest parent countries that are not tax havens (dependencies folded into their sovereign); Panel B, the ten largest tax-haven and conduit jurisdictions.", "d_home_havens", 1.0))
    L.append(fig(S, "fig_wp3_home_share_by_parent_sectors", f"{APP} Share of each parent's export value shipped to the parent's own country: all goods and the three sectors, top-10 parents.", "d_home_sectors", 0.95,
                 "The all-goods bars are the diagonal of the parent $\\times$ destination table above (USA 22.3\\,\\%). Hatched bars: the parent's pooled exports in the sector are below \\$1bn, so the share is fragile."))
    L.append(sub("The United States"))
    L.append(fig(S, "fig_wp3_to_usa_carriers_total_manuf", f"{APP} Exports to the United States by origin: share moved by US-parent MNEs, other foreign MNEs, domestic MNEs and local firms --- all goods (left) and manufacturing (right).", "d_to_usa", 1.0,
                 "Denominator: the origin's exports to the United States. The US-parent bars of the left panel are column (4) of the three-share table."))
    L.append(tab(S, "Tables", "tab_wp3_to_usa_carriers_by_sector.tex", f"{APP} Exports to the United States by sector: who carries them (\\%)", "d_to_usa_sector"))
    L.append(fig(A, "fig_wp3_dest_carriers", f"{MAIN} The largest destination markets (EU-27 pooled): share of the value reaching each one moved by MNEs with a parent in the destination, by US-, EU-27- and CAN-parent MNEs (when the destination is not their home), other foreign MNEs, domestic MNEs and local firms.", "d_dest", 1.0,
                 "EU-27 = the 27 member states; the United Kingdom is a separate destination and a separate parent country. The USA row's first segment is the all-goods US-parent share of exports to the United States, column (4) of the three-share table."))
    # ---- Fact 4
    L.append(sec("Fact 4 --- A small set of large multinational groups accounts for the bulk of exports"))
    L.append(fig(A, "fig_wp0_fig5_network", f"{MAIN} Foreign-MNE export value and number of parents by size of the group's global affiliate network.", "d_f5", 0.7))
    L.append(tab(A, "Tables", "tab_wp0_fig5_network.tex", f"{APP} Parents and foreign-MNE export value by global affiliate-network size", "d_f5_tab"))
    # ---- Fact 5
    L.append(sec("Fact 5 --- Greater multinational presence is associated with higher trade volumes"))
    L.append(tab(A, "Regressions", "reg_wp0_table1_repro.tex", f"{MAIN} Multinational presence and trade volume: intensive and extensive margins", "d_t1"))
    L.append(tab(A, "Tables", "tab_wp1e_presence_shares.tex", f"{APP} MNE export value by origin: domestic share, and foreign-MNE value by the group's presence at the destination", "d_pres"))
    L.append(tab(A, "Regressions", "reg_wp1e_counts.tex", f"{MAIN} Intensive margin: ln(\\# MNE firms) decomposed into foreign / domestic and foreign through HQ / not through HQ", "d_counts"))
    L.append(tab(A, "Regressions", "reg_wp1e_extensive.tex", f"{MAIN} Extensive margin: presence indicators decomposed into foreign / domestic and foreign through HQ / not through HQ", "d_ext"))
    L.append(tab(S, "Tables", "tab_wp3_fact5_summary.tex", f"{APP} Fact 5 by sector, intensive margin: number of foreign and of domestic MNEs exporting the product to the destination, all goods and the three sectors", "d_f5sum"))
    L.append(tab(S, "Tables", "tab_wp3_fact5ext_summary.tex", f"{APP} Fact 5 by sector, extensive margin: presence of foreign and of domestic MNEs exporting the product to the destination, all goods and the three sectors", "d_f5extsum"))
    # ---- Fact 6
    L.append(sec("Fact 6 --- Distance is a weaker barrier to trade for multinational corporations"))
    L.append(tab(A, "Regressions", "reg_wp0_table2_repro.tex", f"{MAIN} Distance and firm exports: multinationals split by presence at the destination", "d_t2"))
    L.append(tab(A, "Regressions", "reg_wp1e_distance_hq.tex", f"{MAIN} Distance and firm exports: foreign / domestic, then foreign through HQ / not through HQ", "d_dist"))
    L.append(tab(S, "Tables", "tab_wp3_fact6_summary.tex", f"{APP} Fact 6 by sector: distance elasticity and its attenuation for foreign and domestic MNEs", "d_f6sum"))
    # ---- HS6
    L.append(sec("Products"))
    L.append(fig(A, "fig_wp1f_top20_hs6_stacked", f"{MAIN} Top-20 HS6 products by export value: foreign MNE, domestic MNE and local shares.", "d_hs6", 1.0))
    L.append(fig(A, "fig_wp1f_top20_hs6_by_parent", f"{MAIN} Top-20 HS6 products: foreign bar split by the parent's country (remainder = local firms).", "d_hs6_parent", 1.0))
    L.append(fig(A, "fig_wp1f_foreign_share_distribution", f"{APP} Distribution of the HS6 foreign-MNE share: share of export value and MNE share of exporting firms, by bin.", "d_a_dist", 0.85))
    L.append(tab(A, "Tables", "tab_wp1f_foreign_share_distribution.tex", f"{APP} Numbers behind the previous figure", "d_a_dist_tab"))
    L.append(tab(A, "Tables", "tab_wp1f_hs_sections.tex", f"{MAIN} HS sections by export value: MNE shares and leading parent", "d_sections", size=r"\footnotesize"))
    # ---- sector sub-classifications
    L.append(sec("Sectors"))
    for sc, stem, title in (("agro", "sitc2", "Agriculture by SITC Rev.\\,3 division"), (M, "hs_section", "Manufacturing by HS section"),
                            (M, "bec_enduse", "Manufacturing by BEC end use"), (MI, "bec_enduse", "Mining and fuels by BEC end use")):
        L.append(tab(sc, "Tables", f"tab_wp2_{stem}.tex", f"{MAIN} {title}: total and MNE exports, shares, leading parents", f"d_2_{sc}_{stem}", size=r"\footnotesize"))
    L.append(tab(A, "Tables", "tab_wp3_us_home_products.tex", f"{APP} What US-parent MNEs ship to the United States: top-15 HS6 lines, the US-parent share of everything the nine origins export of the line to the USA, and the main origins", "d_us_prod", size=r"\footnotesize"))
    L.append(r"\end{document}" + "\n")
    return write_main(L)




# =====================================================================
# WP_paper / WP_paper_agro -- the working-paper drafts for the coauthors
# =====================================================================

PAPER_ABSTRACT = r"""
We match the customs export records of nine Latin American countries for 2006--2022 to the
ownership data of Orbis and Dun \& Bradstreet, so that every exporter is an affiliate of a foreign
multinational group, an affiliate of a domestic group, or a local firm. The data cover 165,543
exporters, 5,930 products, 253 destinations and US\$2.4 trillion of exports, and give the country
of the ultimate owner for 92\% of what foreign affiliates sell abroad. Six facts follow.
Multinational affiliates sell 61\% of the region's exports, and most of that is foreign owned.
Foreign affiliates concentrate in complex and differentiated goods, domestic ones in primary and
homogeneous goods. The owners come from few countries: the United States, the United Kingdom and
Canada together account for half of foreign-affiliate exports. Groups with more than a hundred
affiliates worldwide are 9\% of parents and 56\% of the value. Where multinationals are present,
exports are higher, and the association is about three times larger for foreign affiliates than
for domestic ones. Distance holds multinational affiliates back less than it holds back other
firms. US groups are a case of their own: they own 10.8\% of the region's exports and they are the
only large investor that ships a sizeable part of what it produces in the region back home, 22.3\%
against 0.6\% for British parents and close to zero for Swiss and Liechtenstein ones.
"""

AGRO_ABSTRACT = r"""
We match the customs export records of nine Latin American countries for 2006--2022 to the
ownership data of Orbis and Dun \& Bradstreet, and use them to describe who owns the region's
agricultural exporters. Agriculture here is HS chapters 01--24 and is worth US\$78.9 billion a
year across the nine countries. Multinational affiliates sell 48\% of it, 38\% foreign owned and
10\% domestically owned, with shares that run from 29\% in El Salvador to 66\% in Paraguay. The
owners are concentrated in a handful of countries, most of them grain traders and the holding
jurisdictions they use. Foreign presence is heaviest in oil seeds, cereals and animal feed and
lightest in sugar and beverages. Two of the patterns that hold for the region's exports as a whole
do not hold inside agriculture: foreign affiliates are no more concentrated in complex or
differentiated goods than in simple ones, and the product range is too narrow for a complexity
gradient to appear. The other four hold. A few large groups carry the value, cells with more
multinationals trade more, and distance holds multinational affiliates back less than other firms.
"""

PAPER_KEYWORDS = "Multinational Firms, Foreign Direct Investment, Exports, Ownership, Firm-Level Data, Latin America"
AGRO_KEYWORDS = "Multinational Firms, Agricultural Trade, Ownership, Firm-Level Data, Latin America"
PAPER_JEL = "F14, F23, D22, L25"
AGRO_JEL = "F14, F23, Q17, L25"


def paper_preamble(title, subtitle, abstract, keywords, jel) -> str:
    return r"""\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{mathptmx}
\usepackage[margin=2.5cm]{geometry}
\usepackage{graphicx,booktabs,amsmath,amssymb,adjustbox,float,caption,hyperref,xcolor,enumitem}
\captionsetup{font=small,labelfont=bf,skip=4pt}
\hypersetup{colorlinks,linkcolor=blue!50!black,urlcolor=blue!50!black,citecolor=blue!50!black}
\setlength{\parskip}{3pt}
\newcommand{\tbw}[1]{\textcolor{gray}{\textit{#1}}}
\title{\textbf{""" + title + r"""}\\[6pt]\large """ + subtitle + r"""}
\author{Ignacio Marra de Arti\~nano\thanks{Universit\'e Libre de Bruxelles (ECARES).}
 \and Gabriel Scattolo\thanks{Inter-American Development Bank.}
 \and Sebasti\'an Vel\'asquez\thanks{Inter-American Development Bank.}
 \and Christian Volpe Martincus\thanks{Inter-American Development Bank and CESifo. The views and
interpretations in this paper are strictly those of the authors and should not be attributed to
the Inter-American Development Bank, its executive directors, or its member countries.}}
\date{This version: """ + date.today().strftime("%B %Y") + r""" \\[2pt] \small Preliminary draft, please do not circulate}
\begin{document}
\maketitle
\thispagestyle{empty}
\begin{abstract}\noindent """ + abstract.strip() + r"""
\end{abstract}
\vspace{4pt}
\noindent\textbf{Keywords:} """ + keywords + r""" \\
\noindent\textbf{JEL codes:} """ + jel + r"""
\clearpage
\tableofcontents
\clearpage
"""


PAPER_INTRO = r"""
Customs records show what a country sells abroad and to whom. They do not show who owns the
seller. For Latin America this is a large blind spot, because much of the export base belongs to
firms whose owners sit in another country. Aggregate investment statistics do not close it. They
record where capital goes, not which firm ships which product to which market.

This paper closes it for nine countries: Argentina, Chile, Colombia, Costa Rica, the Dominican
Republic, El Salvador, Paraguay, Peru and Uruguay. We match their customs export records for
2006--2022 to the ownership records of Orbis and Dun \& Bradstreet. The result is a dataset of 5.1
million firm, destination, product and year cells in which every exporter carries a label, foreign
affiliate, domestic affiliate or local firm, and in which the sales of foreign affiliates can be
traced back to the country of their parent.

Six facts come out of it. First, multinational affiliates sell 61\% of the region's exports, from
47\% in Peru to 74\% in Colombia, and most of that is foreign owned. Second, foreign affiliates
concentrate in complex and differentiated goods and domestic ones in primary and homogeneous
goods, with the clearest gradient inside manufacturing. Third, the owners come from few countries:
the United States, the United Kingdom and Canada account for half of foreign-affiliate exports.
Fourth, a few large groups carry the value, since parents with more than a hundred affiliates
worldwide are 9\% of parents and 56\% of what foreign affiliates sell. Fifth, cells with more
multinationals trade more, and the association is about three times larger for foreign affiliates
than for domestic ones, including for the local firms selling in the same cell. Sixth, distance
reduces the exports of multinational affiliates less than it reduces those of other firms.

The United States runs through all six facts and is the paper's main story. It is both the largest
owner of the region's exporters and its largest single market, and the two roles almost never
meet. US groups own 10.8\% of what the nine countries export, 18.4\% of those exports go to
the United States, and the overlap is 2.5\%. What sets US parents apart is that they buy from
their own affiliates at all. Of what their Latin American affiliates sell abroad, 22.3\% goes to
the United States, against 0.6\% for British parents, 2.2\% for Dutch ones and close to zero for
Swiss and Liechtenstein ones. Only Canadian (19.5\%) and Brazilian (18.6\%) parents come near.
The overlap is concentrated in Central America and the Caribbean, where US affiliates move 41\% of
what El Salvador sends to the United States, 40\% of Costa Rica's and 26\% of the Dominican
Republic's, and in manufacturing, where they move 27\% of everything the region ships north. In
the Southern Cone and the Andes it is small. The nationality of the owner predicts the
destination, and it predicts a different one for each owner: British and Liechtenstein groups send
mining products to Asia, German and Japanese groups export from Argentina to Brazil.

\tbw{Contribution to the literature: to be written.}

Section~\ref{sec:lit} reviews the related literature. Section~\ref{sec:data} describes the data
and how exporters are classified by ownership. Section~\ref{sec:facts} presents the six facts.
Section~\ref{sec:products} takes them to the product and sector level. Section~\ref{sec:model}
sketches the model and Section~\ref{sec:concl} concludes.
"""

AGRO_INTRO = r"""
Customs records show what a country sells abroad and to whom. They do not show who owns the
seller. In agriculture that gap is wide, because a large part of what Latin America ships is
handled by grain traders, processors and food companies headquartered elsewhere, and the aggregate
investment statistics do not say which firm ships which crop to which market.

This paper closes the gap for nine countries: Argentina, Chile, Colombia, Costa Rica, the
Dominican Republic, El Salvador, Paraguay, Peru and Uruguay. We match their customs export records
for 2006--2022 to the ownership records of Orbis and Dun \& Bradstreet, label every exporter as a
foreign affiliate, a domestic affiliate or a local firm, and restrict the result to agriculture,
defined as HS chapters 01--24. That is US\$78.9 billion a year, a third of what the nine countries
export. Everything here is for the region as a whole.

Five results are worth stating up front. Multinational affiliates sell 48\% of the region's
agricultural exports, 38\% of it foreign owned, and the share ranges from 29\% in El Salvador to
66\% in Paraguay. Ownership is concentrated in a few countries, most of them grain traders and the
holding jurisdictions they use. Within agriculture the foreign share is highest in oil seeds
(62\%), miscellaneous edible products (71\%) and tobacco (55\%), and lowest in sugar (19\%) and
beverages (29\%). Groups with more than a hundred affiliates worldwide are 12\% of parents and
half of foreign-affiliate value, while 45\% of parents have a single affiliate. And the two
regularities that hold for merchandise exports as a whole do not survive inside agriculture: there
is no complexity gradient and no difference between differentiated and homogeneous goods.

\tbw{Contribution to the literature: to be written.}

Section~\ref{sec:lit} reviews the related literature. Section~\ref{sec:data} describes the data.
Section~\ref{sec:facts} presents the facts within agriculture. Section~\ref{sec:sub} looks inside
the sector. Section~\ref{sec:model} sketches the model and Section~\ref{sec:concl} concludes.
"""


def data_section(agro: bool = False) -> str:
    scope = (r"""

Agriculture is HS chapters 01--24, which covers live animals, meat, fish, dairy, vegetables,
fruit, cereals, oil seeds, fats and oils, prepared foods, beverages and tobacco. Every figure in
this paper is computed on that subset of the records described above, for the nine countries
pooled. We do not report country-specific or partner-specific analyses.
""" if agro else "")
    return r"""
\subsection{Customs transactions}

The trade data are the export records of the customs authorities of nine Latin American countries,
obtained by the Inter-American Development Bank under its agreements with the national agencies. A
record gives the value exported (FOB, current US dollars) by one identified firm, of one six-digit
HS 2007 product, to one destination, in one year. Firms are identified by their national tax
number, which is unique within a country, and by the name written on the declaration.

Coverage is the universe of merchandise exports in the years each country made available. Those
years differ, from Chile's 2009--2022 to Paraguay's 2012--2020, and all nine overlap between 2012
and 2018. Because the panel is unbalanced, every dollar figure in this paper is an annual average,
the country's pooled value divided by the number of years it is observed, while shares are
computed on pooled values. Ecuador is in the raw data but excluded throughout. Services do not
appear in customs merchandise records and are outside the paper.""" + scope + r"""

\subsection{Ownership records}

Ownership comes from two commercial databases. Orbis (Bureau van Dijk) gives the ownership links
between companies: for each subsidiary, the identity and country of its global ultimate owner at
the 25\% control threshold. Dun \& Bradstreet gives an independent roster with the DUNS number of
each establishment and of its global ultimate, together with names, countries and industries. We
merge the two into one file in which each firm carries a group identifier, the parent's country
and name, and the number of affiliates the group has worldwide, which is the measure of network
size behind Fact~4. The two sources overlap without coinciding: Orbis covers the ownership chain
better, Dun \& Bradstreet the operating establishments, and some exporters appear in only one.

\subsection{Matching exporters to their owners}

Customs gives a tax number and a name typed into a declaration. The corporate databases give a
registered company name and, for some countries, the same tax number. Matching runs in four steps.

\begin{enumerate}[leftmargin=1.4em,itemsep=1pt,topsep=2pt]
\item \textbf{Tax identifier.} Direct match on the national tax number wherever the corporate
database records it. This step delivers about 60\% of matched export value.
\item \textbf{Fuzzy name matching, country by country.} For the rest, company names are compared
with a character-level TF--IDF trigram similarity. Character sequences survive the abbreviations
that customs declarations make to company names; words do not. A large language model then accepts
or rejects each candidate pair.
\item \textbf{Fuzzy name matching, pooled.} A second pass over the firms still unmatched, this
time against the corporate databases of all countries at once, which catches affiliates registered
under a group name rather than a local one.
\item \textbf{Manual review.} For the 500 largest unmatched exporters of each country, the match
was checked by hand against company websites, corporate registries and public filings. These firms
are few and carry a large share of export value, so they drive the aggregate shares.
\end{enumerate}

A parallel step recovers the parent's country when the ownership record names the parent but not
its location, first from the raw Orbis links and then from a model-assisted review of the parent's
name and registered address. After it, the country of the ultimate owner is known for 92.5\% of
what foreign affiliates export.

\subsection{Who counts as a multinational}

An exporter found in Orbis or Dun \& Bradstreet is an affiliate of a multinational group. We split
matched exporters by where the group's ultimate owner sits: a \textbf{domestic} affiliate when the
owner is in the exporting country, a \textbf{foreign} affiliate otherwise. Matched exporters whose
parent country is unknown count as foreign, so the foreign category is what is left of matched
firms after the domestic ones. An exporter found in neither database is a \textbf{local} firm.

Two consequences matter for reading the exhibits. Because the foreign category is a residual, the
aggregate foreign share does not depend on how many parent countries were recovered, which is what
Facts~1, 2, 5 and~6 need. And wherever an exhibit splits the foreign bar \emph{by} parent country,
the 7.5\% of foreign-affiliate value with an unknown parent is allocated across parent countries
in proportion to the recorded parents of the same group, so those shares still refer to all
foreign affiliates and still add up with the domestic and local ones.

One limit is worth stating. The match runs through ownership links, so a group's head company
cannot be identified as an exporter: every matched exporter in the data has an ultimate owner
different from itself, and a Latin American group's head company exporting from home falls among
the unmatched. What the data do show is whether the group is present \emph{at the destination},
either because the affiliate ships to its parent's country or because the group has another
affiliate there. Facts~5 and~6 use that distinction.

\subsection{Product classifications and other sources}

Products carry the Hausmann--Hidalgo Product Complexity Index, the four technology categories of
Lall (2000), the conservative Rauch (1999) split into differentiated, reference-priced and
exchange-traded goods, BEC Rev.\,4 end use and categories, SITC Rev.\,3 divisions, NAICS codes,
upstreamness, and the import-demand elasticities of Fontagn\'e, Guimbard and Orefice (2022), all
mapped to HS 2007 six-digit lines. Sectors are defined on HS chapters: agriculture 01--24, mining
and fuels 25--27 and 71, manufacturing 28--97 excluding 71. Distance, contiguity, common language
and trade agreements come from the CEPII gravity database.

\subsection{The working sample}
"""


PAPER_SAMPLE_TEXT = r"""
Table~\ref{tab:p_sample} describes the sample country by country and Table~\ref{tab:p_counts}
summarizes it. The nine countries contribute 5.1 million firm, destination, product and year
records, 165,543 exporters of which 31,350 are matched to a corporate database, 5,930 HS6 lines,
253 destinations and US\$2,394 billion of pooled export value. The matched exporters belong to
17,094 groups whose owners sit in 165 countries. Regressions use plain logarithms, so a cell with
a zero count drops out of that column, and cluster standard errors at the origin--destination
level.
"""

AGRO_SAMPLE_TEXT = r"""
Table~\ref{tab:p_sample} describes the agricultural sample country by country and
Table~\ref{tab:p_counts} summarizes it. Regressions use plain logarithms, so a cell with a zero
count drops out of that column, and cluster standard errors at the origin--destination level.
"""


PAPER_FACT_TEXT = {
1: r"""
Figure~\ref{fig:p_f1} gives, for each country, the share of export value sold by multinational
affiliates, split into foreign and domestic owners. Multinationals sell between 47\% (Peru) and
74\% (Colombia) of exports, and 61\% for the nine pooled. Foreign owners dominate: 46\% of total
exports against 14\% for domestic multinationals. Colombia is the exception, where the state oil
company and its subsidiaries push the domestic share above the foreign one, and Chile is the near
exception, where copper and pulp do the same on a smaller scale. A large domestic multinational
presence is a natural-resource story in two countries.

The United States is both the largest owner and the largest market, so it is worth separating the
two roles at the start. Of the region's exports, 18.4\% go to the United States and 10.8\% are
sold by affiliates of US groups. Only 2.5\% is both, and US affiliates move 13.6\% of everything
the nine countries ship to the United States. The overlap sits in Central America and the
Caribbean, at 19.0\% of El Salvador's exports, 15.1\% of Costa Rica's and 12.5\% of the Dominican
Republic's, and is small everywhere else.
""",
2: r"""
Figure~\ref{fig:p_f2f3} sorts products by sophistication. The foreign share climbs from 0.46 in
the least complex quintile of the Product Complexity Index to 0.65 in the most complex one, and is
highest in high- and medium-technology manufactures. Domestic multinationals run the other way,
concentrated in primary and resource-based goods. Figure~\ref{fig:p_f2_oecd} shows that affiliates
of OECD-headquartered groups carry the gradient.

The same ordering shows up in classifications that use no complexity index. Foreign affiliates
hold 56\% of differentiated products and 55\% of reference-priced ones against 34\% of
exchange-traded goods, where the domestic share is four times its average (Table~\ref{tab:p_rauch}
and Figure~\ref{fig:p_rauch_fig}). By end use they hold 65\% of capital goods against 48\% of
intermediates and 44\% of consumption goods (Table~\ref{tab:p_bec}).
Table~\ref{tab:p_ladder} runs the same comparison in origin, destination, product and year cells.
The pattern is sharpest inside manufacturing (Figure~\ref{fig:p_rauch_manuf}). It is noisy inside
agriculture and absent inside mining, where too few products exist for the quintiles to order
anything.
""",
3: r"""
Figure~\ref{fig:p_f4} ranks the owners of foreign affiliates by their share of foreign-affiliate
export value. The United States (23\%), the United Kingdom (19\%) and Canada (8\%) account for
half of it, the ten largest owners for more than three quarters, and the remaining 150 countries
for the rest.

Where the goods go depends on who owns the seller. Tables~\ref{tab:p_pxd} and~\ref{tab:p_pxp} give
the destination mix of the ten largest owners, the second using the owners' own countries as
destinations, so its diagonal is the share each group of affiliates ships home. Three routes stand
out. British and Liechtenstein groups, concentrated in mining, sell to Asia. German and Japanese
groups export from Argentina to Brazil, treating the region as a platform for Mercosur. And US
groups ship home: 22.3\% of what their affiliates sell, against 0.6\% for British owners and 2.2\%
for Dutch ones, with only Canada (19.5\%) and Brazil (18.6\%) close behind. Figure~\ref{fig:p_dest}
looks at the same pattern from the destination side and asks, for each large market, how much of
what arrives is carried by affiliates of groups headquartered there.
""",
4: r"""
Figure~\ref{fig:p_f5} groups the owners of foreign affiliates by the number of affiliates their
group has worldwide. Almost half of the owners have a single affiliate, while owners with more
than a hundred are 9\% of the total and sell 56\% of foreign-affiliate export value. The region's
foreign-owned export capacity sits inside a small number of large corporate networks.
""",
5: r"""
Table~\ref{tab:p_t1} relates the exports of an origin, destination, product and year cell to the
multinational presence in it, on the intensive margin (how many affiliates sell the product there)
and on the extensive one (whether any does). Both associations are large and survive an
increasingly demanding set of fixed effects, and both hold when the dependent variable is the
exports of the \emph{non-multinational} firms in the same cell (Panel B).

Table~\ref{tab:p_f5counts} splits the intensive margin by owner. The coefficient is about three
times larger for foreign affiliates than for domestic ones, 1.21 against 0.44, and the same gap
appears for the exports of local firms in the cell, 1.13 against 0.47. On the extensive margin the
two are almost identical, 1.50 against 1.47 (Table~\ref{tab:p_ext}), so what separates foreign
affiliates is how much presence they bring rather than whether they are there at all. Columns
(5)--(6) split foreign affiliates further by whether the group reaches the destination through its
own headquarters; they rest on far fewer cells and should be read as suggestive.
""",
6: r"""
Table~\ref{tab:p_t2} estimates the distance elasticity of firm-level exports and how it changes
for multinational affiliates. The baseline elasticity is $-0.16$ and roughly a third of it goes
away for multinationals. Table~\ref{tab:p_dist} splits that attenuation: 0.049 for foreign
affiliates against 0.032 for domestic ones, and 0.064 for foreign affiliates whose group reaches
the destination through its headquarters, which is to say for affiliates selling to their own
parent's country.
""",
}

AGRO_FACT_TEXT = {
1: r"""
Figure~\ref{fig:p_f1} gives, for each country, the share of agricultural export value sold by
multinational affiliates. Multinationals sell 48\% of the region's agricultural exports, 38\%
foreign owned and 10\% domestically owned. The spread across countries is wide: 66\% in Paraguay
and 62\% in Uruguay at one end, 29\% in El Salvador and 37\% in Peru at the other. Foreign owners
are ahead of domestic ones everywhere, and the gap is narrowest in Chile (30\% against 19\%),
where fruit and wine have domestically owned groups of some size.
""",
2: r"""
This is where agriculture parts company with the rest of the region's exports. Across merchandise
exports as a whole the foreign share rises with product complexity and is higher in differentiated
goods. Inside agriculture neither holds. Across quintiles of the Product Complexity Index the
foreign share reads 0.29, 0.49, 0.38, 0.42, 0.55, so the two ends go the right way and the middle
does not (Figure~\ref{fig:p_f2f3}). By Rauch class the foreign share is 41\% in differentiated goods,
32\% in reference-priced ones and 41\% in exchange-traded ones (Table~\ref{tab:p_rauch} and
Figure~\ref{fig:p_rauch_fig}). The domestic share sits near 9\% in all three. By end use the
foreign share is 41\% in intermediates against 35\% in consumption goods (Table~\ref{tab:p_bec}),
a small difference next to the 65\% against 44\% found in manufacturing. Agricultural products
occupy a narrow band of the complexity range, and inside that band sophistication does not sort
owners.
""",
3: r"""
Figure~\ref{fig:p_f4} ranks the owners of foreign affiliates in agriculture by their share of
foreign-affiliate export value. Ownership is concentrated: the ten largest owner countries account
for roughly three quarters of it. The list is a list of the grain trade and the jurisdictions it
holds assets through, with Switzerland (11\%), the Netherlands (9.5\%) and Liechtenstein (7.6\%)
high in the ranking next to the United States (24\%). Where each owner's affiliates sell is in
Tables~\ref{tab:ap_pxd} and~\ref{tab:ap_pxp} in the appendix.
""",
4: r"""
Figure~\ref{fig:p_f5} groups the owners of foreign affiliates by the size of their worldwide
network. Agriculture has a long tail of small owners: 45\% of them have a single affiliate, a
larger share than in the region's exports as a whole. The value still sits with the large groups,
with owners of more than a hundred affiliates accounting for 12\% of owners and 50\% of
foreign-affiliate export value.
""",
5: r"""
Table~\ref{tab:p_t1} relates the agricultural exports of an origin, destination, product and year
cell to the multinational presence in it. The associations are the same as for merchandise exports
as a whole, and they hold for the exports of the non-multinational firms in the same cell
(Panel~B). Table~\ref{tab:p_f5counts} splits the intensive margin by owner: 1.30 for foreign
affiliates against 0.52 for domestic ones, the same factor of roughly three found in the region's
exports as a whole. The extensive margin is in Table~\ref{tab:p_ext}.
""",
6: r"""
Table~\ref{tab:p_t2} estimates the distance elasticity of firm-level agricultural exports.
The baseline elasticity is $-0.21$, steeper than for merchandise exports as a whole, and
Table~\ref{tab:p_dist} shows the attenuation for multinationals: 0.037 for foreign affiliates
against 0.019 for domestic ones. Distance matters more in agriculture, and multinational
affiliates escape less of it than they do elsewhere, but the ordering between foreign and domestic
owners is unchanged.
""",
}

PAPER_PRODUCTS_TEXT = r"""
The facts above average over a very uneven product range.
Figure~\ref{fig:p_hs6} shows the twenty largest HS6 lines with the foreign, domestic and local
shares of each. Crude petroleum is three quarters domestically owned, copper concentrates are four
fifths foreign owned, gold sits in between. Figure~\ref{fig:p_hs6_parent} splits the foreign bar
by owner country and gives a readable map of who owns what: British groups in copper and coal,
Canadian groups in gold, US groups in soybeans, maize and apparel, German groups in trucks, Swiss
groups in soybean cake. Table~\ref{tab:p_sections} aggregates to HS sections with the leading
owner of each.

Tables~\ref{tab:p_agro_sitc} to~\ref{tab:p_mining_bec} give the same breakdowns within each
sector: agriculture by SITC Rev.\,3 division, manufacturing by HS section and by BEC end use,
mining and fuels by BEC end use.
"""

AGRO_SUB_TEXT = r"""
Agriculture is not one market. Table~\ref{tab:a_sitc} splits it into SITC Rev.\,3 divisions and
Figure~\ref{fig:a_sitc} shows the same shares. Animal feed is the largest division at US\$13.8
billion a year, followed by vegetables and fruit (10.6), cereals (10.3), oil seeds (6.7) and fixed
vegetable oils (6.0). Foreign presence varies by a factor of four across them: 71\% in
miscellaneous edible products, 62\% in oil seeds, 55\% in tobacco and 49\% in cereals, against
31\% in coffee, tea and cocoa, 29\% in beverages and 19\% in sugar and honey. Domestic
multinationals are largest in dairy (20\%), coffee (16\%) and sugar (15\%).

Two other cuts are worth keeping. Table~\ref{tab:a_hssection} and Figure~\ref{fig:a_hssection}
take the HS sections inside agriculture, which separate live animals and animal products,
vegetable products, fats and oils, and prepared foodstuffs. Table~\ref{tab:a_inputs} and
Figure~\ref{fig:a_inputs} split the sector into agricultural inputs and everything else, with the
largest input lines in Table~\ref{tab:a_topinputs}. Table~\ref{tab:a_bec} adds the BEC end-use
split, which separates what leaves the region for further processing from what leaves it ready for
a household.

At the product level, Figure~\ref{fig:a_hs6} gives the twenty largest HS6 lines in agriculture
with the foreign, domestic and local shares of each, and Figure~\ref{fig:a_hs6_parent} splits the
foreign bar by owner country.
"""

PAPER_TAIL = {
"lit": r"""
\tbw{To be written. Three strands: firm-level evidence on multinational production and trade;
ownership, market power and trade policy; and descriptive evidence on multinational firms in Latin
America.}
""",
"model": r"""
\tbw{To be written. The framework is the companion theory paper: an oligopoly model with
multinational ownership in which the object of interest is the ownership-weighted Herfindahl
rather than the country-level ownership share. The section will state the environment, the
objects the facts discipline, and how the model's ownership share maps to the measured one.}
""",
"concl": r"""
\tbw{To be written.}
""",
}

REFS_BLOCK = r"""
\tbw{To be completed with the literature section. The sources of the classifications used above
are:}
\begin{list}{}{\leftmargin=1.5em \itemindent=-1.5em \itemsep=2pt \topsep=4pt}
\item Fontagn\'e, L., Guimbard, H. and Orefice, G., 2022. Tariff-Based Product-Level Trade
Elasticities. \emph{Journal of International Economics}, 137.
\item Hausmann, R. and Hidalgo, C., 2011. The Network Structure of Economic Output.
\emph{Journal of Economic Growth}, 16(4).
\item Lall, S., 2000. The Technological Structure and Performance of Developing Country
Manufactured Exports, 1985--98. \emph{Oxford Development Studies}, 28(3).
\item Rauch, J., 1999. Networks versus Markets in International Trade. \emph{Journal of
International Economics}, 48(1).
\item United Nations Statistics Division, 2022. \emph{Classification by Broad Economic
Categories}, Rev.\,4. New York.
\end{list}
"""

APPENDIX_OPEN = ("\n" + r"\clearpage" + "\n" + r"\appendix" + "\n"
                 + r"\setcounter{figure}{0}\renewcommand{\thefigure}{A.\arabic{figure}}" + "\n"
                 + r"\setcounter{table}{0}\renewcommand{\thetable}{A.\arabic{table}}" + "\n")

REFS_HEAD = "\n" + r"\section*{References}\addcontentsline{toc}{section}{References}\label{sec:refs}" + "\n"


def build_paper() -> Path:
    """The working paper for the coauthors: introduction and data written out, the [Main text]
    exhibits of the 2026-09-21 draft in fact order with a short reading paragraph each, the
    [Appendix] ones in the appendix, literature / model / conclusions stated but not developed."""
    L = [paper_preamble("Multinational Firms and Trade in Latin America",
                        "Six Stylized Facts on Ownership and Exports",
                        PAPER_ABSTRACT, PAPER_KEYWORDS, PAPER_JEL)]
    A, M, MI, S = "all", "manufacturing", "mining", "sectors"

    L.append(sec("Introduction", "intro")); L.append(par(PAPER_INTRO))
    L.append(sec("Related Literature", "lit")); L.append(par(PAPER_TAIL["lit"]))

    L.append(sec("Data", "data"))
    L.append(par(data_section(agro=False)))
    L.append(par(PAPER_SAMPLE_TEXT))
    L.append(tab(A, "Tables", "tab_paper_sample.tex", "The working sample: coverage by exporting country", "p_sample", size=r"\footnotesize"))
    L.append(tab(A, "Tables", "tab_paper_sample_counts.tex", "The working sample in figures", "p_counts"))

    L.append(sec("Six Stylized Facts on Multinational Firms and Trade", "facts"))

    L.append(sub("Fact 1: Multinational corporations account for a large share of export values across countries"))
    L.append(par(PAPER_FACT_TEXT[1]))
    L.append(fig(A, "fig_wp0_fig1_origin", "MNE share of export value by origin: foreign and domestic multinationals.", "p_f1", 0.8))
    L.append(fig(A, "fig_wp3_us_three_shares_total", "Exports of the nine origins, as shares of total exports: going to the United States, carried by US-parent MNEs, and both.", "p_us3_total", 0.6,
                 "Same denominator for the three bars: total export value of the nine origins, all firms and destinations. The second bar is the USA's share of foreign-MNE value (23.3\\,\\%, Fact 3) times the foreign-MNE share of exports (46.3\\,\\%, Figure~\\ref{fig:p_f1}); the third bar is the second times the share of US-parent exports that goes to the United States (22.3\\,\\%, the diagonal of Table~\\ref{tab:p_pxp})."))
    L.append(fig(A, "fig_wp3_us_three_shares_origin", "The same three shares by origin (denominator: the origin's total exports).", "p_us3_origin", 1.0))
    L.append(tab(A, "Tables", "tab_wp3_us_three_shares.tex", "Exports going to the United States, carried by US-parent MNEs, and both, as shares of total exports; and the US-parent share of the exports going to the United States", "p_us3_tab"))

    L.append(sub("Fact 2: Foreign multinationals specialize in complex products, domestic ones in primary goods"))
    L.append(par(PAPER_FACT_TEXT[2]))
    L.append(panel_fig([(A, "fig_wp0_fig2_pci", "By quintile of the Product Complexity Index (Q1 = least complex)"), (A, "fig_wp0_fig3_lall", "By Lall (2000) technology category")],
                       "MNE share of export value by product sophistication: foreign and domestic multinationals.", "p_f2f3", width=0.72))
    L.append(fig(A, "fig_wp1a_pci_lall_by_oecd", "MNE share by PCI quintile (Panel A) and Lall category (Panel B), foreign bar split into OECD-parent and non-OECD-parent multinationals.", "p_f2_oecd", 1.0,
                 "OECD = the 38 member countries; matched firms with no recorded parent country are counted with the non-OECD parents."))
    L.append(tab(A, "Tables", "tab_wp1b_rauch.tex", "MNE shares by Rauch (1999) class: differentiated, reference-priced, homogeneous", "p_rauch"))
    L.append(fig(A, "fig_wp1b_rauch", "Foreign vs domestic MNE shares of export value by Rauch (1999) class.", "p_rauch_fig", 0.7))
    L.append(tab(A, "Tables", "tab_wp1b_bec.tex", "MNE shares by BEC end use: intermediate, consumption and capital goods", "p_bec"))
    L.append(tab(A, "Regressions", "reg_wp1b_odpy_measures.tex", "Product sophistication and MNE shares: PCI, Lall categories and Rauch classes, each in a separate regression", "p_ladder", size=r"\footnotesize"))
    L.append(fig(M, "fig_wp1b_rauch", "Manufacturing: foreign vs domestic MNE shares by Rauch (1999) class.", "p_rauch_manuf", 0.7))

    L.append(sub("Fact 3: Multinational corporations from a small set of countries dominate exports"))
    L.append(par(PAPER_FACT_TEXT[3]))
    L.append(fig(A, "fig_wp1a_parent_share", "Foreign-MNE export value by the parent's country: top 15 and other.", "p_f4", 0.78,
                 "Share of all foreign-MNE export value. Foreign MNEs export 46.3\\,\\% of total exports (Figure~\\ref{fig:p_f1}), so the USA's 23.3\\,\\% of foreign-MNE value is $0.233 \\times 46.3 = 10.8\\,\\%$ of total exports, the US-parent share of Table~\\ref{tab:p_us3_tab}."))
    L.append(tab(A, "Tables", "tab_wp1c_country_rowpct.tex", "Top-10 parents $\\times$ top-10 destinations: destination mix of each parent's exports (row \\%)", "p_pxd"))
    L.append(tab(A, "Tables", "tab_wp1c_parent_x_parentdest_rowpct.tex", "Top-10 parents $\\times$ the same ten countries as destinations (row \\%): the diagonal is the share of each parent's exports shipped to the parent's own country", "p_pxp"))
    L.append(fig(A, "fig_wp3_dest_carriers", "The largest destination markets (EU-27 pooled): share of the value reaching each one moved by MNEs with a parent in the destination, by US-, EU-27- and CAN-parent MNEs (when the destination is not their home), other foreign MNEs, domestic MNEs and local firms.", "p_dest", 1.0,
                 "EU-27 = the 27 member states; the United Kingdom is a separate destination and a separate parent country. The USA row's first segment is the all-goods US-parent share of exports to the United States, column (4) of Table~\\ref{tab:p_us3_tab}."))

    L.append(sub("Fact 4: A small set of large multinational groups accounts for the bulk of exports"))
    L.append(par(PAPER_FACT_TEXT[4]))
    L.append(fig(A, "fig_wp0_fig5_network", "Foreign-MNE export value and number of parents by size of the group's global affiliate network.", "p_f5", 0.7))

    L.append(sub("Fact 5: Greater multinational presence is associated with higher trade volumes"))
    L.append(par(PAPER_FACT_TEXT[5]))
    L.append(tab(A, "Regressions", "reg_wp0_table1_repro.tex", "Multinational presence and trade volume: intensive and extensive margins", "p_t1"))
    L.append(tab(A, "Regressions", "reg_wp1e_counts.tex", "Intensive margin: ln(\\# MNE firms) decomposed into foreign / domestic and foreign through HQ / not through HQ", "p_f5counts"))
    L.append(tab(A, "Regressions", "reg_wp1e_extensive.tex", "Extensive margin: presence indicators decomposed into foreign / domestic and foreign through HQ / not through HQ", "p_ext"))

    L.append(sub("Fact 6: Distance is a weaker barrier to trade for multinational corporations"))
    L.append(par(PAPER_FACT_TEXT[6]))
    L.append(tab(A, "Regressions", "reg_wp0_table2_repro.tex", "Distance and firm exports: multinationals split by presence at the destination", "p_t2"))
    L.append(tab(A, "Regressions", "reg_wp1e_distance_hq.tex", "Distance and firm exports: foreign / domestic, then foreign through HQ / not through HQ", "p_dist"))

    L.append(sec("Products and Sectors", "products"))
    L.append(par(PAPER_PRODUCTS_TEXT))
    L.append(fig(A, "fig_wp1f_top20_hs6_stacked", "Top-20 HS6 products by export value: foreign MNE, domestic MNE and local shares.", "p_hs6", 1.0))
    L.append(fig(A, "fig_wp1f_top20_hs6_by_parent", "Top-20 HS6 products: foreign bar split by the parent's country (remainder = local firms).", "p_hs6_parent", 1.0))
    L.append(tab(A, "Tables", "tab_wp1f_hs_sections.tex", "HS sections by export value: MNE shares and leading parent", "p_sections", size=r"\footnotesize"))
    for sc, stem, title, lab in (("agro", "sitc2", "Agriculture by SITC Rev.\\,3 division", "p_agro_sitc"),
                                 (M, "hs_section", "Manufacturing by HS section", "p_manuf_hs"),
                                 (M, "bec_enduse", "Manufacturing by BEC end use", "p_manuf_bec"),
                                 (MI, "bec_enduse", "Mining and fuels by BEC end use", "p_mining_bec")):
        L.append(tab(sc, "Tables", f"tab_wp2_{stem}.tex", f"{title}: total and MNE exports, shares, leading parents", lab, size=r"\footnotesize"))

    L.append(sec("Theoretical Framework", "model")); L.append(par(PAPER_TAIL["model"]))
    L.append(sec("Concluding Remarks", "concl")); L.append(par(PAPER_TAIL["concl"]))
    L.append(REFS_HEAD); L.append(par(REFS_BLOCK))

    L.append(APPENDIX_OPEN)
    L.append(sec("Appendix: Additional Exhibits", "app"))
    L.append(par(r"""This appendix collects the exhibits that document or extend the figures and
tables of the main text, and the numbers behind them, in the order of the facts."""))

    L.append(sub("Fact 1"))
    L.append(tab(A, "Tables", "tab_wp0_fig1_origin.tex", "Numbers behind Figure~\\ref{fig:p_f1}: foreign, domestic and total MNE shares by origin", "a_f1n"))
    L.append(fig(A, "fig_wp1a_origin_by_parent", "MNE share of export value by origin, foreign bar split by the parent's country (top 10, other foreign, domestic).", "a_f1_parent", 0.92))
    L.append(tab(A, "Tables", "tab_wp1a_origin_by_parent.tex", "Numbers behind the previous figure", "a_f1pn"))
    L.append(fig(S, "fig_wp3_fig1_by_sector_panels", "MNE share of export value by origin within each sector: foreign and domestic multinationals (Panel A agriculture, Panel B manufacturing, Panel C mining and fuels).", "a_f1_sectors", 1.0))
    L.append(tab(S, "Tables", "tab_wp2_four_sectors.tex", "The four sectors: total and MNE exports, foreign and domestic shares, leading parents", "a_sectors"))

    L.append(sub("Fact 2"))
    L.append(fig(M, "fig_wp0_fig2_pci", "Manufacturing: MNE share of export value by PCI quintile (quintiles over manufacturing HS6 products).", "a_f2_manuf", 0.78))

    L.append(sub("Fact 3"))
    L.append(tab(A, "Tables", "tab_wp1c_region_rowpct.tex", "Parent region $\\times$ destination region: destination mix of each group (row \\%)", "a_reg"))
    L.append(fig(A, "fig_wp1d_heatmap_country_rowpct", "Top-15 parents $\\times$ top-15 destinations: \\% of the parent's export value going to each destination.", "a_hm_row", 1.0))
    L.append(fig(A, "fig_wp1d_home_share_by_parent", "Share of each parent's export value shipped to the parent's own country, parents as recorded (the diagonal of Table~\\ref{tab:p_pxp}).", "a_home", 0.85))
    L.append(fig(A, "fig_wp1d_home_share_haven_panels", "Share of each parent's export value shipped to the parent's own jurisdiction: Panel A, the ten largest parent countries that are not tax havens (dependencies folded into their sovereign); Panel B, the ten largest tax-haven and conduit jurisdictions.", "a_home_havens", 1.0))
    L.append(fig(S, "fig_wp3_home_share_by_parent_sectors", "Share of each parent's export value shipped to the parent's own country: all goods and the three sectors, top-10 parents.", "a_home_sectors", 0.95,
                 "Hatched bars: the parent's pooled exports in the sector are below \\$1bn, so the share is fragile."))
    L.append(fig(S, "fig_wp3_to_usa_carriers_total_manuf", "Exports to the United States by origin: share moved by US-parent MNEs, other foreign MNEs, domestic MNEs and local firms: all goods (left) and manufacturing (right).", "a_to_usa", 1.0,
                 "Denominator: the origin's exports to the United States. The US-parent bars of the left panel are column (4) of Table~\\ref{tab:p_us3_tab}."))
    L.append(tab(S, "Tables", "tab_wp3_to_usa_carriers_by_sector.tex", "Exports to the United States by sector: who carries them (\\%)", "a_to_usa_sector"))
    L.append(tab(A, "Tables", "tab_wp3_us_home_products.tex", "What US-parent MNEs ship to the United States: top-15 HS6 lines, the US-parent share of everything the nine origins export of the line to the USA, and the main origins", "a_us_prod", size=r"\footnotesize"))

    L.append(sub("Fact 4"))
    L.append(tab(A, "Tables", "tab_wp0_fig5_network.tex", "Parents and foreign-MNE export value by global affiliate-network size", "a_f5_tab"))

    L.append(sub("Fact 5"))
    L.append(tab(A, "Tables", "tab_wp1e_presence_shares.tex", "MNE export value by origin: domestic share, and foreign-MNE value by the group's presence at the destination", "a_pres"))
    L.append(tab(S, "Tables", "tab_wp3_fact5_summary.tex", "Fact 5 by sector, intensive margin: number of foreign and of domestic MNEs exporting the product to the destination, all goods and the three sectors", "a_f5sum"))
    L.append(tab(S, "Tables", "tab_wp3_fact5ext_summary.tex", "Fact 5 by sector, extensive margin: presence of foreign and of domestic MNEs exporting the product to the destination, all goods and the three sectors", "a_f5extsum"))

    L.append(sub("Fact 6"))
    L.append(tab(S, "Tables", "tab_wp3_fact6_summary.tex", "Fact 6 by sector: distance elasticity and its attenuation for foreign and domestic MNEs", "a_f6sum"))

    L.append(sub("Products"))
    L.append(fig(A, "fig_wp1f_foreign_share_distribution", "Distribution of the HS6 foreign-MNE share: share of export value and MNE share of exporting firms, by bin.", "a_dist", 0.85))
    L.append(tab(A, "Tables", "tab_wp1f_foreign_share_distribution.tex", "Numbers behind the previous figure", "a_dist_tab"))

    L.append(r"\end{document}" + "\n")
    return write_main(L)


def build_paper_agro() -> Path:
    """The agriculture-only companion: the same six facts and the same data section, computed
    within HS 01--24 for the nine origins pooled. No United States section and no country-specific
    or destination-specific analysis; everything is region-wide and sectoral."""
    G = "agro"
    L = [paper_preamble("Multinational Firms and Agricultural Trade in Latin America",
                        "Ownership and Exports in HS 01--24",
                        AGRO_ABSTRACT, AGRO_KEYWORDS, AGRO_JEL)]

    L.append(sec("Introduction", "intro")); L.append(par(AGRO_INTRO))
    L.append(sec("Related Literature", "lit")); L.append(par(PAPER_TAIL["lit"]))

    L.append(sec("Data", "data"))
    L.append(par(data_section(agro=True)))
    L.append(par(AGRO_SAMPLE_TEXT))
    L.append(tab(G, "Tables", "tab_paper_sample.tex", "The agricultural sample: coverage by exporting country", "p_sample", size=r"\footnotesize"))
    L.append(tab(G, "Tables", "tab_paper_sample_counts.tex", "The agricultural sample in figures", "p_counts"))

    L.append(sec("The Six Facts within Agriculture", "facts"))

    L.append(sub("Fact 1: Multinational corporations account for a large share of agricultural export values"))
    L.append(par(AGRO_FACT_TEXT[1]))
    L.append(fig(G, "fig_wp0_fig1_origin", "Agriculture: MNE share of export value by origin, foreign and domestic multinationals.", "p_f1", 0.8))
    L.append(tab(G, "Tables", "tab_wp0_fig1_origin.tex", "Numbers behind the previous figure", "p_f1n"))

    L.append(sub("Fact 2: Inside agriculture, sophistication does not sort owners"))
    L.append(par(AGRO_FACT_TEXT[2]))
    L.append(panel_fig([(G, "fig_wp0_fig2_pci", "By quintile of the Product Complexity Index (Q1 = least complex)"), (G, "fig_wp0_fig3_lall", "By Lall (2000) technology category")],
                       "Agriculture: MNE share of export value by product sophistication.", "p_f2f3", width=0.72))
    L.append(tab(G, "Tables", "tab_wp1b_rauch.tex", "Agriculture: MNE shares by Rauch (1999) class", "p_rauch"))
    L.append(fig(G, "fig_wp1b_rauch", "Agriculture: foreign vs domestic MNE shares of export value by Rauch (1999) class.", "p_rauch_fig", 0.7))
    L.append(tab(G, "Tables", "tab_wp1b_bec.tex", "Agriculture: MNE shares by BEC end use", "p_bec"))
    L.append(tab(G, "Regressions", "reg_wp1b_odpy_measures.tex", "Agriculture: product sophistication and MNE shares, each measure in its own regression", "p_ladder", size=r"\footnotesize"))

    L.append(sub("Fact 3: Ownership is concentrated in a few countries"))
    L.append(par(AGRO_FACT_TEXT[3]))
    L.append(fig(G, "fig_wp1a_parent_share", "Agriculture: foreign-MNE export value by the parent's country, top 15 and other.", "p_f4", 0.78))
    L.append(tab(G, "Tables", "tab_wp1a_parent_share.tex", "Numbers behind the previous figure", "p_f4n"))

    L.append(sub("Fact 4: A small set of large groups accounts for the bulk of exports"))
    L.append(par(AGRO_FACT_TEXT[4]))
    L.append(fig(G, "fig_wp0_fig5_network", "Agriculture: foreign-MNE export value and number of parents by size of the group's global affiliate network.", "p_f5", 0.7))
    L.append(tab(G, "Tables", "tab_wp0_fig5_network.tex", "Numbers behind the previous figure", "p_f5_tab"))

    L.append(sub("Fact 5: Greater multinational presence is associated with higher trade volumes"))
    L.append(par(AGRO_FACT_TEXT[5]))
    L.append(tab(G, "Regressions", "reg_wp0_table1_repro.tex", "Agriculture: multinational presence and trade volume, intensive and extensive margins", "p_t1"))
    L.append(tab(G, "Regressions", "reg_wp1e_counts.tex", "Agriculture, intensive margin: ln(\\# MNE firms) decomposed into foreign / domestic", "p_f5counts"))
    L.append(tab(G, "Regressions", "reg_wp1e_extensive.tex", "Agriculture, extensive margin: presence indicators decomposed into foreign / domestic", "p_ext"))

    L.append(sub("Fact 6: Distance is a weaker barrier to trade for multinational corporations"))
    L.append(par(AGRO_FACT_TEXT[6]))
    L.append(tab(G, "Regressions", "reg_wp0_table2_repro.tex", "Agriculture: distance and firm exports, multinationals split by presence at the destination", "p_t2"))
    L.append(tab(G, "Regressions", "reg_wp1e_distance_hq.tex", "Agriculture: distance and firm exports, foreign / domestic", "p_dist"))

    L.append(sec("Inside Agriculture", "sub"))
    L.append(par(AGRO_SUB_TEXT))
    L.append(tab(G, "Tables", "tab_wp2_sitc2.tex", "Agriculture by SITC Rev.\\,3 division: total and MNE exports, shares, leading parents", "a_sitc", size=r"\footnotesize"))
    L.append(fig(G, "fig_wp2_sitc2", "Agriculture by SITC Rev.\\,3 division: foreign and domestic MNE shares of export value.", "a_sitc", 0.9))
    L.append(tab(G, "Tables", "tab_wp2_hs_section.tex", "Agriculture by HS section: total and MNE exports, shares, leading parents", "a_hssection", size=r"\footnotesize"))
    L.append(fig(G, "fig_wp2_hs_section", "Agriculture by HS section: foreign and domestic MNE shares of export value.", "a_hssection", 0.9))
    L.append(tab(G, "Tables", "tab_wp2_bec_enduse.tex", "Agriculture by BEC end use: total and MNE exports, shares, leading parents", "a_bec", size=r"\footnotesize"))
    L.append(tab(G, "Tables", "tab_wp2_inputs.tex", "Agricultural inputs vs other agricultural goods: total and MNE exports, shares, leading parents", "a_inputs", size=r"\footnotesize"))
    L.append(fig(G, "fig_wp2_inputs", "Agricultural inputs vs other agricultural goods: foreign and domestic MNE shares.", "a_inputs", 0.7))
    L.append(tab(G, "Tables", "tab_wp2_top_inputs_hs6.tex", "The largest agricultural-input HS6 lines", "a_topinputs", size=r"\footnotesize"))
    L.append(fig(G, "fig_wp1f_top20_hs6_stacked", "Agriculture, top-20 HS6 products by export value: foreign MNE, domestic MNE and local shares.", "a_hs6", 1.0))
    L.append(fig(G, "fig_wp1f_top20_hs6_by_parent", "Agriculture, top-20 HS6 products: foreign bar split by the parent's country (remainder = local firms).", "a_hs6_parent", 1.0))

    L.append(sec("Theoretical Framework", "model")); L.append(par(PAPER_TAIL["model"]))
    L.append(sec("Concluding Remarks", "concl")); L.append(par(PAPER_TAIL["concl"]))
    L.append(REFS_HEAD); L.append(par(REFS_BLOCK))

    L.append(APPENDIX_OPEN)
    L.append(sec("Appendix: Additional Exhibits", "app"))
    L.append(par(r"""This appendix collects the exhibits that document or extend those of the main
text, all of them computed within agriculture for the nine origins pooled."""))

    L.append(sub("Fact 1"))
    L.append(fig(G, "fig_wp1a_origin_by_parent", "Agriculture: MNE share of export value by origin, foreign bar split by the parent's country.", "ap_f1_parent", 0.92))
    L.append(tab(G, "Tables", "tab_wp1a_origin_by_parent.tex", "Numbers behind the previous figure", "ap_f1pn"))

    L.append(sub("Fact 2"))
    L.append(tab(G, "Tables", "tab_wp1b_quintile_shares.tex", "Agriculture: foreign and domestic MNE shares by quintile of each sophistication measure", "ap_quint", size=r"\footnotesize"))

    L.append(sub("Fact 3"))
    L.append(tab(G, "Tables", "tab_wp1c_country_rowpct.tex", "Agriculture, top-10 parents $\\times$ top-10 destinations: destination mix of each parent's exports (row \\%)", "ap_pxd"))
    L.append(tab(G, "Tables", "tab_wp1c_parent_x_parentdest_rowpct.tex", "Agriculture, top-10 parents $\\times$ the same ten countries as destinations (row \\%)", "ap_pxp"))
    L.append(tab(G, "Tables", "tab_wp1c_region_rowpct.tex", "Agriculture, parent region $\\times$ destination region: destination mix of each group (row \\%)", "ap_reg"))
    L.append(fig(G, "fig_wp1d_heatmap_country_rowpct", "Agriculture, top-15 parents $\\times$ top-15 destinations: \\% of the parent's export value going to each destination.", "ap_hm", 1.0))
    L.append(fig(G, "fig_wp1d_home_share_by_parent", "Agriculture: share of each parent's export value shipped to the parent's own country.", "ap_home", 0.85))

    L.append(sub("Fact 5"))
    L.append(tab(G, "Tables", "tab_wp1e_presence_shares.tex", "Agriculture: MNE export value by origin, domestic share and foreign-MNE value by the group's presence at the destination", "ap_pres"))

    L.append(sub("Inside agriculture"))
    L.append(fig(G, "fig_wp2_origin_x_sitc2", "Agriculture: origin $\\times$ SITC division, foreign-MNE share of export value.", "ap_oxs", 1.0))
    L.append(tab(G, "Tables", "tab_wp2_origin_x_sitc2.tex", "Numbers behind the previous figure", "ap_oxs_tab", size=r"\footnotesize"))
    L.append(tab(G, "Tables", "tab_wp2_sitc2_by_parent.tex", "Agriculture by SITC division: parent-country composition of foreign-MNE exports", "ap_sitc_par", size=r"\footnotesize"))
    L.append(tab(G, "Tables", "tab_wp1f_hs_sections.tex", "Agriculture: HS sections by export value, MNE shares and leading parent", "ap_sections", size=r"\footnotesize"))
    L.append(fig(G, "fig_wp1f_foreign_share_distribution", "Agriculture: distribution of the HS6 foreign-MNE share.", "ap_dist", 0.85))
    L.append(tab(G, "Tables", "tab_wp1f_foreign_share_distribution.tex", "Numbers behind the previous figure", "ap_dist_tab"))

    L.append(r"\end{document}" + "\n")
    return write_main(L)


# =====================================================================
# WP_draft2 -- second version of the 2026-09-21 exhibit draft (2026-09-23)
#   main body and appendix as two separate parts; Tables 8, 16, 25, 26, 27 of the
#   2026-09-21 draft moved to the appendix; referee-facing titles; short notes that
#   replace the notes carried by the fragments; internal labels in the fragments relabelled.
# =====================================================================

D2_SRC = r"\textit{Source:} Authors' calculations based on customs data matched to Orbis and Dun \& Bradstreet."
D2_STARS = r"*** $p<0.01$, ** $p<0.05$, * $p<0.1$."

# internal labels inside the fragments -> referee-facing labels (this document only)
D2_RELABEL = [
    (r"\textit{Panel A: MNE$_{total}$ share}", r"\textit{Panel A. Dependent variable: share of all MNEs}"),
    (r"\textit{Panel B: MNE$_{ext}$ share}", r"\textit{Panel B. Dependent variable: share of foreign MNEs}"),
    (r"\textit{Panel C: MNE$_{dom}$ share}", r"\textit{Panel C. Dependent variable: share of domestic MNEs}"),
    (r"\textit{Panel A: all exports ($\ln$)}", r"\textit{Panel A. Dependent variable: $\ln$ exports, all firms}"),
    (r"\textit{Panel B: non-MNE exports ($\ln$)}", r"\textit{Panel B. Dependent variable: $\ln$ exports, non-MNE firms}"),
    (r"\textit{Panel A. Dependent variable: $\ln$ exports of the product from the origin to the destination in the year, all firms}",
     r"\textit{Panel A. Dependent variable: $\ln$ exports, all firms}"),
    (r"\textit{Panel B. Dependent variable: $\ln$ exports of the product from the origin to the destination in the year, local (non-MNE) firms only}",
     r"\textit{Panel B. Dependent variable: $\ln$ exports, non-MNE firms}"),
    (r"Number of foreign MNEs exporting the product to the destination ($\ln$)", r"$\ln$(\# foreign MNEs)"),
    (r"Number of domestic MNEs exporting the product to the destination ($\ln$)", r"$\ln$(\# domestic MNEs)"),
    (r"Foreign through HQ / not through HQ / domestic", r"Foreign by destination, domestic"),
    (r"foreign MNEs present through HQ", r"foreign MNEs, parent-country destination"),
    (r"foreign MNEs not present through HQ", r"foreign MNEs, other destinations"),
    (r"Any foreign MNE present through HQ", r"Any foreign MNE, parent-country destination"),
    (r"Any foreign MNE not present through HQ", r"Any foreign MNE, other destination"),
    (r"foreign MNE, present through HQ", r"foreign MNE, parent-country destination"),
    (r"foreign MNE, not present through HQ", r"foreign MNE, other destination"),
    (r"$\times$ MNE, present &", r"$\times$ MNE, present at destination &"),
    (r"$\times$ MNE, not present &", r"$\times$ MNE, not present at destination &"),
    (r"Observations (all exports)", r"Observations (Panel A)"),
    (r"Observations (non-MNE exports)", r"Observations (Panel B)"),
    (r" (column (1) of the full table)", ""),
    (r" (column (2))", ""),
    (r"MNE total", r"All MNEs"),
    (r"& Dom. &", r"& Domestic &"),
    (r"HS section & \$bn/yr & For. & Dom. & Local & Lead parent",
     r"HS section & US\$bn/yr & Foreign (\%) & Domestic (\%) & Local (\%) & Leading parent"),
    (r"N HS6", r"HS6 products"),
    (r"Global affiliate count", r"Affiliates worldwide"),
    (r"All parents with a network record", r"All parents"),
    (r"\% of foreign-MNE value: group present at destination", r"\% of foreign-MNE value, by destination"),
    (r"through headquarters", r"parent country"),
    (r"not through HQ (of which via another affiliate)", r"other (of which: group affiliate there)"),
    (r"(\$bn/yr)", r"(US\$bn/yr)"),
]


def d2_relabel(text: str) -> str:
    for a, b in D2_RELABEL:
        text = text.replace(a, b)
    return text


def d2_note(note: str) -> str:
    """Notes first, then the source on its own line (Sebastian, 2026-09-23)."""
    note = note.replace(D2_SRC, "").strip()
    return rf"\textit{{Notes:}} {note}\\[3pt]{D2_SRC}"


def tab2(scope, kind, name, caption, label, note, size=r"\small"):
    """Like tab(), but relabels the fragment for an external reader and replaces its note."""
    if not exists(scope, kind, name):
        return missing("table", scope, name)
    rel = f"{kind}/{scope}/{name}"; dst = DST / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    body, _ = split_note(sanitize((SRC / scope / kind / name).read_text(encoding="utf-8")))
    dst.write_text(d2_relabel(body), encoding="utf-8")
    n = rf"\par\vspace{{3pt}}\begin{{minipage}}{{0.95\textwidth}}\footnotesize {d2_note(note)}\end{{minipage}}"
    return (rf"\begin{{table}}[H]\centering{size}\caption{{{caption}}}\label{{tab:{label}}}"
            rf"\adjustbox{{max width=\textwidth, max totalheight=0.8\textheight}}{{\input{{{rel[:-4]}}}}}{n}\end{{table}}" "\n")


def fig2(scope, name, caption, label, note, width=0.95):
    if not exists(scope, "Graphs", f"{name}.pdf"):
        return missing("figure", scope, name)
    path = copy_fig(scope, name)
    n = rf"\par\vspace{{2pt}}\parbox{{0.92\textwidth}}{{\footnotesize {d2_note(note)}}}"
    return (rf"\begin{{figure}}[H]\centering\includegraphics[width={width}\textwidth,height=0.8\textheight,keepaspectratio]{{{path}}}"
            rf"\caption{{{caption}}}\label{{fig:{label}}}{n}\end{{figure}}" "\n")


def panel_fig2(items, caption, label, note, width=0.72):
    parts = []
    for k, (scope, name, title) in enumerate(items):
        if not exists(scope, "Graphs", f"{name}.pdf"):
            return missing("figure", scope, name)
        path = copy_fig(scope, name)
        parts.append(rf"\begin{{minipage}}[t]{{{width}\textwidth}}\centering\textbf{{Panel {chr(65 + k)}. {title}}}\\[2pt]"
                     rf"\includegraphics[width=\linewidth,height=0.38\textheight,keepaspectratio]{{{path}}}\end{{minipage}}")
    n = rf"\par\vspace{{2pt}}\parbox{{0.92\textwidth}}{{\footnotesize {d2_note(note)}}}"
    return rf"\begin{{figure}}[H]\centering" + r"\\[8pt]".join(parts) + rf"\caption{{{caption}}}\label{{fig:{label}}}{n}\end{{figure}}" + "\n"


D2_DATA = r"""
\section*{Data}
\addcontentsline{toc}{section}{Data}

The data are the customs export records of nine Latin American countries at the firm, destination,
HS6 product and year level, matched to the ownership records of Orbis and Dun \& Bradstreet. The
years covered are Argentina 2011--2019, Chile 2009--2022, Colombia 2010--2021, Costa Rica
2010--2019, the Dominican Republic 2012--2019, El Salvador 2006--2018, Paraguay 2012--2020, Peru
2010--2019 and Uruguay 2010--2019.

An exporter found in Orbis or Dun \& Bradstreet is a multinational affiliate (MNE). It is a
\emph{domestic} MNE when its ultimate parent is located in the exporting country and a
\emph{foreign} MNE otherwise; matched exporters without a recorded parent country (7.5 percent of
foreign-MNE export value) are counted as foreign. Exporters not found in either database are
\emph{local} firms. Sectors are defined on HS chapters: agriculture 01--24, mining and fuels
25--27 and 71, manufacturing 28--97 excluding 71.
"""


def usec(title): return f"\n\\section*{{{title}}}\\addcontentsline{{toc}}{{section}}{{{title}}}\n"
def usub(title): return f"\n\\subsection*{{{title}}}\n"


def build_draft_v2() -> Path:
    """Second version of the 2026-09-21 exhibit draft for the coauthors."""
    L = [preamble("Multinational Firms and Trade in Latin America", "Stylized Facts: Tables and Figures",
                  datestr=date.today().strftime("%B %Y"), toc=False)]
    L.append(D2_DATA)
    A, M, MI, S = "all", "manufacturing", "mining", "sectors"
    reg_cells = r"Observations are origin--destination--HS6--year cells."
    reg_firms = r"Observations are firm--destination--HS6--year cells."
    cl = r"Standard errors clustered by origin--destination pair in parentheses. " + D2_STARS
    shares = r"Shares of export value, all available years pooled."
    usd = r"Values are annual averages in US\$ billion."
    lead = r"Leading parents: the three largest parent countries and their share of the row's foreign-MNE exports."
    rauch = (r"Rauch (1999) conservative classification: homogeneous goods are traded on organized exchanges, "
             r"reference-priced goods have a price quoted in trade publications, and differentiated goods have neither.")
    lall = (r"Lall (2000) technology classes: primary and resource-based products, and low-, medium- and "
            r"high-technology manufactures.")
    pci = r"Quintiles of the Hausmann--Hidalgo Product Complexity Index across HS6 products (Q1 = least complex)."
    dep_t1 = r"Dependent variable: $\ln$ exports of the cell (Panel A) and of the non-MNE firms in the cell (Panel B)."

    # ================================================================ MAIN BODY
    L.append(r"\part*{Main Text}\addcontentsline{toc}{part}{Main Text}" + "\n")

    L.append(usec(r"Fact 1: Multinationals Account for a Large Share of Exports"))
    L.append(fig2(A, "fig_wp0_fig1_origin", "Multinational Share of Export Value, by Exporting Country", "d_f1",
                  f"{shares} The figure at the end of each bar is the total MNE share.", 0.8))
    L.append(usub("The United States"))
    L.append(fig2(A, "fig_wp3_us_three_shares_total", "Exports to the United States and Exports by US-Parent Multinationals", "d_us3_total",
                  "Shares of the total exports of the nine countries. The third bar is exports by US-parent MNEs shipped to the United States.", 0.6))
    L.append(fig2(A, "fig_wp3_us_three_shares_origin", "Exports to the United States and Exports by US-Parent Multinationals, by Exporting Country", "d_us3_origin",
                  "Shares of each country's total exports.", 1.0))
    L.append(tab2(A, "Tables", "tab_wp3_us_three_shares.tex", "Exports to the United States and Exports by US-Parent Multinationals, by Exporting Country", "d_us3_tab",
                  f"Columns (1)--(3): percent of each country's total exports. Column (4): percent of exports to the United States shipped by US-parent MNEs. Countries sorted by column (3). {usd}"))

    L.append(usec(r"Fact 2: Foreign Multinationals Specialize in Complex Products, Domestic Multinationals in Primary Goods"))
    L.append(panel_fig2([(A, "fig_wp0_fig2_pci", "Product Complexity Index quintile"), (A, "fig_wp0_fig3_lall", "Lall (2000) technology class")],
                        "Multinational Share of Export Value, by Product Sophistication", "d_f2f3",
                        f"{shares} Panel A: {pci} Panel B: {lall}"))
    L.append(tab2(A, "Tables", "tab_wp1b_rauch.tex", "Multinational Share of Export Value, by Rauch Product Class", "d_rauch",
                  f"{shares} {rauch} {usd}"))
    L.append(fig2(A, "fig_wp1b_rauch", "Multinational Share of Export Value, by Rauch Product Class", "d_rauch_fig",
                  f"{shares} {rauch}", 0.7))
    L.append(tab2(A, "Tables", "tab_wp1b_bec.tex", "Multinational Share of Export Value, by End Use", "d_bec",
                  f"{shares} End use from BEC Rev.\\,4; HS6 products without a BEC correspondence are excluded. {usd}"))
    L.append(tab2(A, "Regressions", "reg_wp1b_odpy_measures.tex", "Product Sophistication and Multinational Shares", "d_ladder",
                  f"{reg_cells} Dependent variable: share of the cell's export value shipped by each type of MNE. Omitted categories: primary and resource-based products (Lall) and homogeneous products (Rauch). Robust standard errors in parentheses. {D2_STARS}", size=r"\footnotesize"))
    L.append(usub("Manufacturing"))
    L.append(fig2(M, "fig_wp1b_rauch", "Manufacturing: Multinational Share of Export Value, by Rauch Product Class", "d_rauch_manuf",
                  f"Shares of manufacturing export value (HS 28--97 excluding 71), all available years pooled. {rauch}", 0.7))

    L.append(usec(r"Fact 3: Multinationals from a Small Set of Countries Dominate Exports"))
    L.append(fig2(A, "fig_wp1a_parent_share", "Foreign-Multinational Exports, by Parent Country", "d_f4",
                  "Percent of foreign-MNE export value, by country of the ultimate parent.", 0.78))
    L.append(tab2(A, "Tables", "tab_wp1c_parent_x_parentdest_rowpct.tex", "Foreign-Multinational Exports to the Parent Countries, by Parent Country", "d_pxp",
                  "Percent of each parent country's exports, by destination (rows add to 100). Destinations are the ten largest parent countries; the diagonal is the share shipped to the parent's own country."))
    L.append(usub("The United States"))
    L.append(fig2(A, "fig_wp3_dest_carriers", "Ownership of Exports to the Main Destination Markets", "d_dest",
                  "Percent of the export value reaching each destination, by type of exporter. The first segment is exports by MNEs whose parent is located in that destination. EU-27 member states are pooled.", 1.0))

    L.append(usec(r"Fact 4: A Small Set of Large Multinational Groups Accounts for Most Exports"))
    L.append(fig2(A, "fig_wp0_fig5_network", "Foreign-Multinational Exports and Number of Parents, by Size of the Group's Global Network", "d_f5",
                  "Shares of foreign-MNE export value and of parents, by the number of affiliates the group has worldwide.", 0.7))

    L.append(usec(r"Fact 5: Multinational Presence Is Associated with Higher Exports"))
    L.append(tab2(A, "Regressions", "reg_wp0_table1_repro.tex", "Multinational Presence and Exports", "d_t1",
                  f"{reg_cells} {dep_t1} Intensive margin: $\\ln$ number of MNEs, cells with at least one MNE. Extensive margin: indicator for at least one MNE. {cl}"))
    L.append(tab2(A, "Regressions", "reg_wp1e_counts.tex", "Multinational Presence and Exports: Intensive Margin, by Type of Multinational", "d_counts",
                  f"{reg_cells} {dep_t1} Regressors: $\\ln$ number of MNEs of each type. Columns (5)--(6) split foreign MNEs by whether the destination is the parent's country. {cl}"))

    L.append(usec(r"Fact 6: Distance Is a Weaker Barrier for Multinationals"))
    L.append(tab2(A, "Regressions", "reg_wp0_table2_repro.tex", "Distance and Firm Exports: Multinationals by Presence at the Destination", "d_t2",
                  f"{reg_firms} Dependent variable: $\\ln$ exports. Non-MNE firms are the omitted group. Present: the group has an affiliate in the destination or the destination is the parent's country. {cl}"))
    L.append(tab2(A, "Regressions", "reg_wp1e_distance_hq.tex", "Distance and Firm Exports: Foreign and Domestic Multinationals", "d_dist",
                  f"{reg_firms} Dependent variable: $\\ln$ exports. Non-MNE firms are the omitted group. Columns (3)--(4) split foreign MNEs by whether the destination is the parent's country. {cl}"))

    L.append(usec("Products"))
    L.append(fig2(A, "fig_wp1f_top20_hs6_stacked", "Ownership of the Twenty Largest Export Products", "d_hs6",
                  "Shares of each product's export value. Twenty largest HS6 products by export value.", 1.0))
    L.append(fig2(A, "fig_wp1f_top20_hs6_by_parent", "Ownership of the Twenty Largest Export Products, by Parent Country", "d_hs6_parent",
                  "Shares of each product's export value. Foreign-MNE share split by country of the ultimate parent; the unfilled part of each bar is local firms.", 1.0))
    L.append(tab2(A, "Tables", "tab_wp1f_hs_sections.tex", "Exports and Multinational Shares, by HS Section", "d_sections",
                  f"Foreign, domestic and local: percent of each section's export value. Leading parent: largest parent country and its share of the section's foreign-MNE exports. {usd}", size=r"\footnotesize"))

    # ================================================================ APPENDIX
    L.append("\n" + r"\clearpage" + "\n" + r"\appendix" + "\n"
             + r"\setcounter{figure}{0}\renewcommand{\thefigure}{A.\arabic{figure}}" + "\n"
             + r"\setcounter{table}{0}\renewcommand{\thetable}{A.\arabic{table}}" + "\n"
             + r"\part*{Appendix}\addcontentsline{toc}{part}{Appendix}" + "\n")

    L.append(usec("Fact 1"))
    L.append(tab2(A, "Tables", "tab_wp0_fig1_origin.tex", "Multinational Share of Export Value, by Exporting Country", "a_f1n",
                  f"Shares of each country's export value, all available years pooled. {usd}"))
    L.append(fig2(A, "fig_wp1a_origin_by_parent", "Multinational Share of Export Value, by Exporting Country and Parent Country", "a_f1_parent",
                  "Shares of each country's export value. Foreign MNEs split by country of the ultimate parent; the ten largest parent countries are shown separately.", 0.92))
    L.append(tab2(A, "Tables", "tab_wp1a_origin_by_parent.tex", "Multinational Share of Export Value, by Exporting Country and Parent Country", "a_f1pn",
                  f"Shares of each country's export value. Other: all remaining foreign parents. {usd}"))
    L.append(fig2(S, "fig_wp3_fig1_by_sector_panels", "Multinational Share of Export Value, by Exporting Country and Sector", "a_f1_sectors",
                  "Shares of each country's export value in the sector. Panel A: agriculture (HS 01--24). Panel B: manufacturing (HS 28--97 excluding 71). Panel C: mining and fuels (HS 25--27 and 71).", 1.0))
    L.append(tab2(S, "Tables", "tab_wp2_four_sectors.tex", "Exports and Multinational Shares, by Sector", "a_sectors",
                  f"Foreign and domestic: percent of the sector's export value. Rest: HS 98--99 and unclassified codes. {lead} {usd}"))

    L.append(usec("Fact 2"))
    L.append(fig2(A, "fig_wp1a_pci_lall_by_oecd", "Multinational Share of Export Value, by Product Sophistication and Location of the Parent", "a_f2_oecd",
                  f"{shares} Foreign MNEs are split by whether the ultimate parent is in an OECD member country. Panel A: {pci} Panel B: {lall}", 1.0))
    L.append(fig2(M, "fig_wp0_fig2_pci", "Manufacturing: Multinational Share of Export Value, by Product Complexity Quintile", "a_f2_manuf",
                  "Shares of manufacturing export value, all available years pooled. Quintiles computed over manufacturing HS6 products.", 0.78))

    L.append(usec("Fact 3"))
    L.append(tab2(A, "Tables", "tab_wp1c_country_rowpct.tex", "Destination of Foreign-Multinational Exports, by Parent Country", "a_pxd",
                  "Percent of each parent country's exports, by destination (rows add to 100). Ten largest parent countries and ten largest destinations by foreign-MNE export value."))
    L.append(tab2(A, "Tables", "tab_wp1c_region_rowpct.tex", "Destination of Multinational Exports, by Parent Region", "a_reg",
                  "Percent of each group's exports, by destination region (rows add to 100). Domestic MNEs and local firms are shown for comparison."))
    L.append(fig2(A, "fig_wp1d_heatmap_country_rowpct", "Destination of Foreign-Multinational Exports: Fifteen Largest Parent Countries and Destinations", "a_hm_row",
                  "Percent of each parent country's exports going to each destination (rows add to 100 including other destinations).", 1.0))
    L.append(fig2(A, "fig_wp1d_home_share_by_parent", "Share of Foreign-Multinational Exports Shipped to the Parent Country", "a_home",
                  "Percent of each parent country's exports shipped to that same country.", 0.85))
    L.append(fig2(A, "fig_wp1d_home_share_haven_panels", "Share of Foreign-Multinational Exports Shipped to the Parent Jurisdiction", "a_home_havens",
                  "Percent of each parent jurisdiction's exports shipped to that same jurisdiction. Panel A: largest parent countries, excluding tax havens; dependencies are assigned to their sovereign state. Panel B: largest tax-haven and conduit jurisdictions.", 1.0))
    L.append(fig2(S, "fig_wp3_home_share_by_parent_sectors", "Share of Foreign-Multinational Exports Shipped to the Parent Country, by Sector", "a_home_sectors",
                  "Percent of each parent country's exports shipped to that same country, by sector. Hatched bars: the parent country's exports in the sector are below US\\$1 billion over the period.", 0.95))
    L.append(fig2(S, "fig_wp3_to_usa_carriers_total_manuf", "Exports to the United States, by Type of Exporter and Exporting Country", "a_to_usa",
                  "Percent of each country's exports to the United States, by type of exporter. Left: all goods. Right: manufacturing.", 1.0))
    L.append(tab2(S, "Tables", "tab_wp3_to_usa_carriers_by_sector.tex", "Exports to the United States, by Type of Exporter and Sector", "a_to_usa_sector",
                  f"Percent of each sector's exports to the United States, by type of exporter. {usd}"))
    L.append(tab2(A, "Tables", "tab_wp3_us_home_products.tex", "Main Products Shipped by US-Parent Multinationals to the United States", "a_us_prod",
                  f"Fifteen HS6 products with the largest exports by US-parent MNEs to the United States. {usd}", size=r"\footnotesize"))

    L.append(usec("Fact 4"))
    L.append(tab2(A, "Tables", "tab_wp0_fig5_network.tex", "Foreign-Multinational Exports and Number of Parents, by Size of the Group's Global Network", "a_f5_tab",
                  "Number and share of parents, and share of foreign-MNE export value, by the number of affiliates the group has worldwide. Parents with a network record in Orbis or Dun \\& Bradstreet: 98 percent of parents and 97 percent of foreign-MNE export value."))

    L.append(usec("Fact 5"))
    L.append(tab2(A, "Regressions", "reg_wp1e_extensive.tex", "Multinational Presence and Exports: Extensive Margin, by Type of Multinational", "a_ext",
                  f"{reg_cells} {dep_t1} Regressors: indicators for at least one MNE of each type. Columns (5)--(6) split foreign MNEs by whether the destination is the parent's country. {cl}"))
    L.append(tab2(A, "Tables", "tab_wp1e_presence_shares.tex", "Multinational Exports by Exporting Country and Destination Type", "a_pres",
                  f"MNE and foreign-MNE export value by country, and the split of foreign-MNE value by destination. Parent country: exports to the country of the ultimate parent. Other: all remaining destinations; in parentheses, destinations where the group has another affiliate. {usd}"))
    L.append(tab2(S, "Tables", "tab_wp3_fact5_summary.tex", "Multinational Presence and Exports by Sector: Intensive Margin", "a_f5sum",
                  f"{reg_cells} {dep_t1} Specification of columns (3)--(4) of Table~\\ref{{tab:d_counts}}, estimated by sector. Blank: too few observations. {cl}"))
    L.append(tab2(S, "Tables", "tab_wp3_fact5ext_summary.tex", "Multinational Presence and Exports by Sector: Extensive Margin", "a_f5extsum",
                  f"{reg_cells} {dep_t1} Specification of columns (3)--(4) of Table~\\ref{{tab:a_ext}}, estimated by sector. {cl}"))

    L.append(usec("Fact 6"))
    L.append(tab2(S, "Tables", "tab_wp3_fact6_summary.tex", "Distance and Firm Exports, by Sector", "a_f6sum",
                  f"{reg_firms} Dependent variable: $\\ln$ exports. Specification of columns (1)--(2) of Table~\\ref{{tab:d_dist}}, estimated by sector. {cl}"))

    L.append(usec("Products"))
    L.append(fig2(A, "fig_wp1f_foreign_share_distribution", "Distribution of Export Value by Product-Level Foreign-Multinational Share", "a_dist",
                  "Share of total export value and MNE share of exporting firms, by the foreign-MNE share of each HS6 product's export value.", 0.85))
    L.append(tab2(A, "Tables", "tab_wp1f_foreign_share_distribution.tex", "Distribution of Export Value by Product-Level Foreign-Multinational Share", "a_dist_tab",
                  "Share of total export value and MNE share of exporting firms, by the foreign-MNE share of each HS6 product's export value. MNE share of exporting firms: MNE firm--destination--product--year observations over all observations in the bin."))
    L.append(tab2("agro", "Tables", "tab_wp2_sitc2.tex", "Agriculture: Exports and Multinational Shares, by SITC Division", "a_agro_sitc",
                  f"Agriculture: HS 01--24. Foreign and domestic: percent of the division's export value. {lead} {usd}", size=r"\footnotesize"))
    L.append(tab2(M, "Tables", "tab_wp2_hs_section.tex", "Manufacturing: Exports and Multinational Shares, by HS Section", "a_manuf_hs",
                  f"Manufacturing: HS 28--97 excluding 71. Foreign and domestic: percent of the section's export value. {lead} {usd}", size=r"\footnotesize"))
    L.append(tab2(M, "Tables", "tab_wp2_bec_enduse.tex", "Manufacturing: Exports and Multinational Shares, by End Use", "a_manuf_bec",
                  f"End use from BEC Rev.\\,4. Foreign and domestic: percent of the category's export value. {lead} {usd}", size=r"\footnotesize"))
    L.append(tab2(MI, "Tables", "tab_wp2_bec_enduse.tex", "Mining and Fuels: Exports and Multinational Shares, by End Use", "a_mining_bec",
                  f"Mining and fuels: HS 25--27 and 71. End use from BEC Rev.\\,4. Foreign and domestic: percent of the category's export value. {lead} {usd}", size=r"\footnotesize"))

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


DOCS_SPEC = {"total": (build_total, True), "sectors": (build_sectors, False), "countries": (build_countries, False),
             "draft": (build_draft, True), "paper": (build_paper, True), "paperagro": (build_paper_agro, True),
             "draft2": (build_draft_v2, True)}

if __name__ == "__main__":
    want = sys.argv[1:] or list(DOCS_SPEC)
    for name in want:
        builder, strict = DOCS_SPEC[name]
        DST = W.WP_OUT / f"overleaf_WP_{name}"
        STRICT = strict; MISSING.clear(); DRAFT_MODE = name in ("draft", "paper", "paperagro", "draft2")
        if DST.exists():
            shutil.rmtree(DST)
        DST.mkdir(parents=True)
        print(f"\n### WP_{name}")
        main = builder()
        if compile_pdf(main):
            shutil.copy2(main.parent / "main.pdf", DOCS / f"WP_{name}_{TODAY}.pdf")
            print("   copied ->", DOCS / f"WP_{name}_{TODAY}.pdf")
        zip_project(DST)
