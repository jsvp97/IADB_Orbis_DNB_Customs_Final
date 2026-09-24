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


# ---------------------------------------------------------------------
# WP_total / WP_sectors / WP_countries -- rev. 2026-09-23: the WP_draft2 conventions (title-case
# captions, short notes with a plain description and a separate Source line, relabelled
# fragments) applied to the full exhibit sets. Every exhibit is kept; the numbers behind each
# figure sit next to it; there is no appendix.
# ---------------------------------------------------------------------
SC_NAME = {"all": "", "agro": "Agriculture", "manufacturing": "Manufacturing", "mining": "Mining and Fuels",
           "rest": "Other Goods"}
SC_DESC = {"all": "export value", "agro": "agricultural export value (HS 01--24)",
           "manufacturing": "manufacturing export value (HS 28--97 excluding 71)",
           "mining": "mining and fuels export value (HS 25--27 and 71)",
           "rest": "export value of other goods (HS 98--99 and unclassified codes)"}
COUNTRY_NAME = {"ARG": "Argentina", "CHL": "Chile", "COL": "Colombia", "CRI": "Costa Rica", "DOM": "Dominican Republic",
                "PER": "Peru", "PRY": "Paraguay", "SLV": "El Salvador", "URY": "Uruguay"}


def cap(sc: str, text: str) -> str:
    return f"{SC_NAME[sc]}: {text}" if SC_NAME[sc] else text


def shr(sc: str) -> str:
    return f"Shares of {SC_DESC[sc]}, all available years pooled."


def scope_word(sc: str) -> str:
    return {"all": "", "agro": "agricultural ", "manufacturing": "manufacturing ", "mining": "mining and fuels ",
            "rest": ""}[sc]


def data_block(extra: str = "") -> str:
    return D2_DATA + (par(extra) if extra else "")


def fact_block(sc: str, L: list, tag: str, with_originals=True) -> None:
    """The six facts and the product exhibits for one scope, every exhibit kept."""
    t = tag
    sw = scope_word(sc)
    cells, firms = r"Observations are origin--destination--HS6--year cells.", r"Observations are firm--destination--HS6--year cells."
    if sc != "all":
        cells += f" {SC_NAME[sc]} products only."
        firms += f" {SC_NAME[sc]} products only."
    cl = r"Standard errors clustered by origin--destination pair in parentheses. " + D2_STARS
    dep_t1 = r"Dependent variable: $\ln$ exports of the cell (Panel A) and of the non-MNE firms in the cell (Panel B)."

    # ---------------- Fact 1
    L.append(sec("Fact 1: Multinationals Account for a Large Share of Exports", f"f1_{t}"))
    L.append(fig2(sc, "fig_wp0_fig1_origin", cap(sc, "Multinational Share of Export Value, by Exporting Country"), f"f1_{t}",
                  f"{shr(sc)} The figure at the end of each bar is the total MNE share.", 0.8))
    L.append(tab2(sc, "Tables", "tab_wp0_fig1_origin.tex", cap(sc, "Multinational Share of Export Value, by Exporting Country"), f"f1n_{t}",
                  f"{shr(sc)} {N_USD}"))
    L.append(sub("By Parent Country"))
    L.append(fig2(sc, "fig_wp1a_origin_by_parent", cap(sc, "Multinational Share of Export Value, by Exporting Country and Parent Country"), f"f1p_{t}",
                  f"{shr(sc)} Foreign MNEs split by country of the ultimate parent; the ten largest parent countries are shown separately.", 0.92))
    L.append(tab2(sc, "Tables", "tab_wp1a_origin_by_parent.tex", cap(sc, "Multinational Share of Export Value, by Exporting Country and Parent Country"), f"f1pn_{t}",
                  f"{shr(sc)} Other: all remaining foreign parents. {N_USD}"))
    L.append(fig2(sc, "fig_wp1a_origin_x_parent_heatmap", cap(sc, "Export Value by Exporting Country and Parent Country"), f"f1hm_{t}",
                  f"Percent of each country's {sw}export value, by country of the ultimate parent of the exporter.", 0.9))
    if sc == "all":
        L.append(sub("The United States"))
        L.append(fig2("sectors", "fig_wp3_us_share_origin_sector", "Exports by US-Parent Multinationals, by Exporting Country and Sector", "us_ox_sector",
                      "Percent of each country's exports in each sector shipped by US-parent MNEs, to all destinations.", 1.0))
        L.append(tab2("sectors", "Tables", "tab_wp3_us_share_origin_sector.tex", "Exports by US-Parent Multinationals, by Exporting Country and Sector", "us_ox_sector_t",
                      f"Left panel: percent of each country's exports in the sector shipped by US-parent MNEs. Right panel: exports by US-parent MNEs. {N_USD}"))
        L.append(fig2(sc, "fig_wp3_us_three_shares_total", "Exports to the United States and Exports by US-Parent Multinationals", "us3_total",
                      "Shares of the total exports of the nine countries. The third bar is exports by US-parent MNEs shipped to the United States.", 0.6))
        L.append(fig2(sc, "fig_wp3_us_three_shares_origin", "Exports to the United States and Exports by US-Parent Multinationals, by Exporting Country", "us3_origin",
                      "Shares of each country's total exports.", 1.0))
        L.append(tab2(sc, "Tables", "tab_wp3_us_three_shares.tex", "Exports to the United States and Exports by US-Parent Multinationals, by Exporting Country", "us3_tab",
                      f"Columns (1)--(3): percent of each country's total exports. Column (4): percent of exports to the United States shipped by US-parent MNEs. Countries sorted by column (3). {N_USD}"))

    # ---------------- Fact 2
    L.append(sec("Fact 2: Foreign Multinationals Specialize in Complex Products, Domestic Multinationals in Primary Goods", f"f2_{t}"))
    if not exists(sc, "Graphs", "fig_wp0_fig2_pci.pdf"):
        L.append(par(r"""Product characteristics (complexity, technology class, elasticities) are not available for
these codes, so this fact cannot be computed for them."""))
    else:
        fact2_body(sc, L, t, cells)

    # ---------------- Fact 3
    L.append(sec("Fact 3: Multinationals from a Small Set of Countries Dominate Exports", f"f3_{t}"))
    L.append(sub("Parent Countries"))
    L.append(fig2(sc, "fig_wp1a_parent_share", cap(sc, "Foreign-Multinational Exports, by Parent Country"), f"f4_{t}",
                  f"Percent of foreign-MNE {sw}export value, by country of the ultimate parent.", 0.78))
    L.append(tab2(sc, "Tables", "tab_wp1a_parent_share.tex", cap(sc, "Foreign-Multinational Exports, by Parent Country"), f"f4n_{t}",
                  f"Percent of foreign-MNE {sw}export value, by country of the ultimate parent. {N_USD}"))
    L.append(fig2(sc, "fig_wp1a_parent_share_total", cap(sc, "Share of Total Exports, by Parent Country"), f"f4t_{t}",
                  f"Percent of total {sw}export value shipped by foreign MNEs of each parent country, other foreign MNEs and domestic MNEs; the remainder is local firms.", 0.85))
    L.append(tab2(sc, "Tables", "tab_wp1a_parent_share_total.tex", cap(sc, "Share of Total Exports, by Parent Country"), f"f4tn_{t}",
                  f"Percent of total {sw}export value, by type of exporter and parent country."))
    L.append(sub("Parent Region and Destination Region"))
    for stem, what, note in (("value", "Export Value", f"{N_USD} Rows: region of the ultimate parent; columns: destination region."),
                             ("rowpct", "Row Percentages", "Percent of each group's exports, by destination region (rows add to 100). Domestic MNEs and local firms are shown for comparison."),
                             ("colpct", "Column Percentages", "Percent of the exports reaching each destination region, by parent region (columns add to 100).")):
        L.append(tab2(sc, "Tables", f"tab_wp1c_region_{stem}.tex", cap(sc, f"Multinational Exports by Parent Region and Destination Region: {what}"), f"reg_{stem}_{t}", note))
    L.append(fig2(sc, "fig_wp1d_heatmap_region_rowpct", cap(sc, "Multinational Exports by Parent Region and Destination Region"), f"reg_hm_{t}",
                  "Percent of each group's exports, by destination region (rows add to 100).", 0.9))
    L.append(tab2(sc, "Tables", "tab_wp1c_origin_x_destregion_foreign.tex", cap(sc, "Foreign-Multinational Exports by Exporting Country and Destination Region"), f"odr_f_{t}",
                  f"Percent of each country's foreign-MNE {sw}exports, by destination region (rows add to 100). Last column: foreign-MNE exports. {N_USD}"))
    L.append(tab2(sc, "Tables", "tab_wp1c_origin_x_destregion_local.tex", cap(sc, "Local-Firm Exports by Exporting Country and Destination Region"), f"odr_l_{t}",
                  f"Percent of each country's {sw}exports by local firms, by destination region (rows add to 100). Last column: local-firm exports. {N_USD}"))
    L.append(sub("Parent Country and Destination Country"))
    for stem, what, note in (("value", "Export Value", f"{N_USD} Ten largest parent countries and ten largest destinations by foreign-MNE export value."),
                             ("rowpct", "Row Percentages", "Percent of each parent country's exports, by destination (rows add to 100). Ten largest parent countries and destinations."),
                             ("colpct", "Column Percentages", "Percent of the foreign-MNE exports reaching each destination, by parent country (columns add to 100). Ten largest parent countries and destinations.")):
        L.append(tab2(sc, "Tables", f"tab_wp1c_country_{stem}.tex", cap(sc, f"Foreign-Multinational Exports by Parent Country and Destination: {what}"), f"cty_{stem}_{t}", note))
    L.append(fig2(sc, "fig_wp1d_heatmap_country_rowpct", cap(sc, "Destination of Foreign-Multinational Exports: Fifteen Largest Parent Countries and Destinations"), f"hm_row_{t}",
                  "Percent of each parent country's exports going to each destination (rows add to 100 including other destinations).", 1.0))
    L.append(fig2(sc, "fig_wp1d_heatmap_country_cellpct", cap(sc, "Foreign-Multinational Exports by Parent Country and Destination: Share of the Total"), f"hm_cell_{t}",
                  "Percent of all foreign-MNE export value in each parent country and destination pair; fifteen largest parent countries and destinations.", 1.0))
    L.append(sub("Exports to the Parent Country"))
    L.append(fig2(sc, "fig_wp1d_home_share_by_parent", cap(sc, "Share of Foreign-Multinational Exports Shipped to the Parent Country"), f"home_{t}",
                  "Percent of each parent country's exports shipped to that same country.", 0.85))
    L.append(tab2(sc, "Tables", "tab_wp1c_parent_x_parentdest_rowpct.tex", cap(sc, "Foreign-Multinational Exports to the Parent Countries, by Parent Country"), f"pxp_{t}",
                  "Percent of each parent country's exports, by destination (rows add to 100). Destinations are the ten largest parent countries; the diagonal is the share shipped to the parent's own country."))
    L.append(fig2(sc, "fig_wp1d_home_share_by_parent_consolidated", cap(sc, "Share of Foreign-Multinational Exports Shipped to the Parent Jurisdiction, Consolidated Parents"), f"homec_{t}",
                  "Percent of each parent's exports shipped to its own jurisdiction. Dependencies are assigned to their sovereign state and tax havens and conduit jurisdictions are pooled.", 0.85))
    L.append(tab2(sc, "Tables", "tab_wp1d_home_share_by_parent_consolidated.tex", cap(sc, "Share of Foreign-Multinational Exports Shipped to the Parent Jurisdiction, Consolidated Parents"), f"homec_t_{t}",
                  f"Home share: percent of the parent's exports shipped to its own jurisdiction. {N_USD}"))
    L.append(fig2(sc, "fig_wp1d_home_share_haven_panels", cap(sc, "Share of Foreign-Multinational Exports Shipped to the Parent Jurisdiction"), f"homeh_{t}",
                  "Percent of each parent jurisdiction's exports shipped to that same jurisdiction. Panel A: largest parent countries, excluding tax havens; dependencies are assigned to their sovereign state. Panel B: largest tax-haven and conduit jurisdictions.", 1.0))
    L.append(tab2(sc, "Tables", "tab_wp1d_home_share_haven_panels.tex", cap(sc, "Share of Foreign-Multinational Exports Shipped to the Parent Jurisdiction"), f"homeh_t_{t}",
                  f"Home share: percent of the parent's exports shipped to its own jurisdiction. Panel A: largest parent countries, excluding tax havens. Panel B: largest tax-haven and conduit jurisdictions. {N_USD}"))
    if sc == "all":
        L.append(fig2("sectors", "fig_wp3_home_share_by_parent_sectors", "Share of Foreign-Multinational Exports Shipped to the Parent Country, by Sector", "home_sectors",
                      "Percent of each parent country's exports shipped to that same country, by sector. Hatched bars: the parent country's exports in the sector are below US\\$1 billion over the period.", 0.95))
        L.append(tab2("sectors", "Tables", "tab_wp3_home_share_by_parent_sectors.tex", "Share of Foreign-Multinational Exports Shipped to the Parent Country, by Sector", "home_sectors_t",
                      f"Left panel: percent of each parent country's exports shipped to that same country. Right panel: the parent country's exports. {N_USD}", size=r"\footnotesize"))
    destination_side(sc, L, t, sw)

    # ---------------- Fact 4
    L.append(sec("Fact 4: A Small Set of Large Multinational Groups Accounts for Most Exports", f"f4s_{t}"))
    L.append(sub("Size of the Group's Global Network"))
    L.append(fig2(sc, "fig_wp0_fig5_network", cap(sc, "Foreign-Multinational Exports and Number of Parents, by Size of the Group's Global Network"), f"net_{t}",
                  f"Shares of foreign-MNE {sw}export value and of parents, by the number of affiliates the group has worldwide.", 0.7))
    L.append(tab2(sc, "Tables", "tab_wp0_fig5_network.tex", cap(sc, "Foreign-Multinational Exports and Number of Parents, by Size of the Group's Global Network"), f"net_t_{t}",
                  f"Number and share of parents, and share of foreign-MNE {sw}export value, by the number of affiliates the group has worldwide."))
    L.append(sub("Concentration within Products"))
    L.append(fig2(sc, "fig_wp0_fig6_hhi", cap(sc, "Export Concentration within Products: Firms and Groups"), f"hhi_{t}",
                  "Mean Herfindahl index of exporters within each HS6 product, weighted by export value, counting each affiliate separately or grouping affiliates by parent within or across countries. Right panel: products where MNEs account for at least half of exports.", 0.9))
    L.append(tab2(sc, "Tables", "tab_wp0_fig6_hhi.tex", cap(sc, "Export Concentration within Products: Firms and Groups"), f"hhi_t_{t}",
                  "Means across HS6 products, weighted by export value. Firm level: each affiliate counted separately. Groups: affiliates grouped by ultimate parent within each exporting country or across countries."))
    L.append(sub("Groups and Affiliates"))
    L.append(tab2(sc, "Tables", "tab_wp1e_groups_vs_affiliates.tex", cap(sc, "Multinational Affiliates and Groups in Origin--Destination--Product--Year Cells"), f"grp_{t}",
                  "Cells with at least one MNE. Group: ultimate parent in Orbis or Dun \\& Bradstreet (parent name when the identifier is missing)."))
    L.append(tab2(sc, "Regressions", "reg_wp1e_groups.tex", cap(sc, "Multinational Presence and Exports: Affiliates and Groups"), f"grp_r_{t}",
                  f"{cells} {dep_t1} Regressors: $\\ln$ number of MNE affiliates or $\\ln$ number of MNE groups (distinct ultimate parents). {cl}"))

    # ---------------- Fact 5
    L.append(sec("Fact 5: Multinational Presence Is Associated with Higher Exports", f"f5_{t}"))
    L.append(tab2(sc, "Regressions", "reg_wp0_table1_repro.tex", cap(sc, "Multinational Presence and Exports"), f"t1_{t}",
                  f"{cells} {dep_t1} Intensive margin: $\\ln$ number of MNEs, cells with at least one MNE. Extensive margin: indicator for at least one MNE. {cl}"))
    L.append(tab2(sc, "Tables", "tab_wp1e_presence_shares.tex", cap(sc, "Multinational Exports by Exporting Country and Destination Type"), f"pres_{t}",
                  f"MNE and foreign-MNE {sw}export value by country, and the split of foreign-MNE value by destination. Parent country: exports to the country of the ultimate parent. Other: all remaining destinations; in parentheses, destinations where the group has another affiliate. {N_USD}"))
    L.append(tab2(sc, "Regressions", "reg_wp1e_counts.tex", cap(sc, "Multinational Presence and Exports: Intensive Margin, by Type of Multinational"), f"cnt_{t}",
                  f"{cells} {dep_t1} Regressors: $\\ln$ number of MNEs of each type. Columns (5)--(6) split foreign MNEs by whether the destination is the parent's country. {cl}"))
    L.append(tab2(sc, "Regressions", "reg_wp1e_extensive.tex", cap(sc, "Multinational Presence and Exports: Extensive Margin, by Type of Multinational"), f"ext_{t}",
                  f"{cells} {dep_t1} Regressors: indicators for at least one MNE of each type. Columns (5)--(6) split foreign MNEs by whether the destination is the parent's country. {cl}"))
    if sc == "all":
        L.append(tab2("sectors", "Tables", "tab_wp3_fact5_summary.tex", "Multinational Presence and Exports by Sector: Intensive Margin", "f5sum",
                      f"{cells} {dep_t1} Specification of columns (3)--(4) of Table~\\ref{{tab:cnt_all}}, estimated by sector. Blank: too few observations. {cl}"))

    # ---------------- Fact 6
    L.append(sec("Fact 6: Distance Is a Weaker Barrier for Multinationals", f"f6_{t}"))
    L.append(tab2(sc, "Regressions", "reg_wp0_table2_repro.tex", cap(sc, "Distance and Firm Exports: Multinationals by Presence at the Destination"), f"t2_{t}",
                  f"{firms} Dependent variable: $\\ln$ exports. Non-MNE firms are the omitted group. Present: the group has an affiliate in the destination or the destination is the parent's country. {cl}"))
    L.append(tab2(sc, "Regressions", "reg_wp1e_distance_hq.tex", cap(sc, "Distance and Firm Exports: Foreign and Domestic Multinationals"), f"dist_{t}",
                  f"{firms} Dependent variable: $\\ln$ exports. Non-MNE firms are the omitted group. Columns (3)--(4) split foreign MNEs by whether the destination is the parent's country. {cl}"))
    if sc == "all":
        L.append(tab2("sectors", "Tables", "tab_wp3_fact6_summary.tex", "Distance and Firm Exports, by Sector", "f6sum",
                      f"{firms} Dependent variable: $\\ln$ exports. Specification of columns (1)--(2) of Table~\\ref{{tab:dist_all}}, estimated by sector. {cl}"))

    # ---------------- Products
    L.append(sec("Products", f"hs6_{t}"))
    L.append(fig2(sc, "fig_wp1f_top20_hs6_stacked", cap(sc, "Ownership of the Twenty Largest Export Products"), f"hs_st_{t}",
                  "Shares of each product's export value. Twenty largest HS6 products by export value.", 1.0))
    L.append(fig2(sc, "fig_wp1f_top20_hs6_by_parent", cap(sc, "Ownership of the Twenty Largest Export Products, by Parent Country"), f"hs_par_{t}",
                  "Shares of each product's export value. Foreign-MNE share split by country of the ultimate parent; the unfilled part of each bar is local firms.", 1.0))
    L.append(fig2(sc, "fig_wp1f_foreign_share_distribution", cap(sc, "Distribution of Export Value by Product-Level Foreign-Multinational Share"), f"hs_dist_{t}",
                  f"Share of {sw}export value and MNE share of exporting firms, by the foreign-MNE share of each HS6 product's export value.", 0.85))
    L.append(tab2(sc, "Tables", "tab_wp1f_foreign_share_distribution.tex", cap(sc, "Distribution of Export Value by Product-Level Foreign-Multinational Share"), f"hs_dist_t_{t}",
                  f"Share of {sw}export value and MNE share of exporting firms, by the foreign-MNE share of each HS6 product's export value. MNE share of exporting firms: MNE firm--destination--product--year observations over all observations in the bin."))
    L.append(fig2(sc, "fig_wp1f_lorenz_foreign", cap(sc, "Concentration of Exports across Products"), f"hs_lor_{t}",
                  "Cumulative share of export value against the cumulative share of HS6 products, ranked by value, for foreign-MNE exports and for all exports.", 0.6))
    L.append(tab2(sc, "Tables", "tab_wp1f_hs_sections.tex", cap(sc, "Exports and Multinational Shares, by HS Section"), f"hs_sec_{t}",
                  f"Foreign, domestic and local: percent of each section's export value. Leading parent: largest parent country and its share of the section's foreign-MNE exports. {N_USD}", size=r"\footnotesize"))
    for stem, title, note in (("by_value", "Thirty Largest Export Products", "Thirty largest HS6 products by export value."),
                              ("by_foreign_value", "Thirty Largest Export Products of Foreign Multinationals", "Thirty largest HS6 products by foreign-MNE export value."),
                              ("by_foreign_share", "Products with the Highest Foreign-Multinational Share", "HS6 products with exports of at least US\\$500 million over the period, ranked by foreign-MNE share."),
                              ("by_domestic_share", "Products with the Highest Domestic-Multinational Share", "HS6 products with exports of at least US\\$500 million over the period, ranked by domestic-MNE share.")):
        L.append(tab2(sc, "Tables", f"tab_wp1f_top_hs6_{stem}.tex", cap(sc, title), f"hs_{stem}_{t}",
                      f"{note} Foreign, domestic and local: percent of the product's export value. Leading parent: largest parent country and its share of the product's foreign-MNE exports. {N_USD}", size=r"\footnotesize"))


def destination_side(sc: str, L: list, tag: str, sw: str) -> None:
    """Fact 3 seen from the destination: who carries the exports that reach each main market."""
    if not exists(sc, "Tables", "tab_wp3_dest_carriers.tex") and not exists(sc, "Tables", "tab_wp3_to_usa_carriers.tex"):
        return
    t = tag
    L.append(sub("Destination Markets"))
    if sc == "all":
        L.append(fig2("sectors", "fig_wp3_to_usa_carriers_total_manuf", "Exports to the United States, by Type of Exporter and Exporting Country", "to_usa_tm",
                      "Percent of each country's exports to the United States, by type of exporter. Left: all goods. Right: manufacturing.", 1.0))
        L.append(tab2("sectors", "Tables", "tab_wp3_to_usa_carriers_by_sector.tex", "Exports to the United States, by Type of Exporter and Sector", "to_usa_sec",
                      f"Percent of each sector's exports to the United States, by type of exporter. {N_USD}"))
    else:
        L.append(fig2(sc, "fig_wp3_to_usa_carriers", cap(sc, "Exports to the United States, by Type of Exporter and Exporting Country"), f"to_usa_f_{t}",
                      f"Percent of each country's {sw}exports to the United States, by type of exporter.", 0.9))
    L.append(tab2(sc, "Tables", "tab_wp3_to_usa_carriers.tex", cap(sc, "Exports to the United States, by Type of Exporter and Exporting Country"), f"to_usa_{t}",
                  f"Percent of each country's {sw}exports to the United States, by type of exporter. {N_USD}"))
    L.append(fig2(sc, "fig_wp3_dest_carriers", cap(sc, "Ownership of Exports to the Main Destination Markets"), f"dest_f_{t}",
                  "Percent of the export value reaching each destination, by type of exporter. The first segment is exports by MNEs whose parent is located in that destination. EU-27 member states are pooled.", 0.95))
    L.append(tab2(sc, "Tables", "tab_wp3_dest_carriers.tex", cap(sc, "Ownership of Exports to the Main Destination Markets"), f"dest_{t}",
                  f"Percent of the export value reaching each destination, by type of exporter. EU-27 member states are pooled. {N_USD}", size=r"\footnotesize"))
    L.append(tab2(sc, "Tables", "tab_wp3_us_home_products.tex", cap(sc, "Main Products Shipped by US-Parent Multinationals to the United States"), f"us_home_{t}",
                  f"Fifteen HS6 products with the largest exports by US-parent MNEs to the United States. {N_USD}", size=r"\footnotesize"))
    L.append(fig2(sc, "fig_wp3_us_home_products", cap(sc, "US-Parent Share of Exports to the United States, Main Products Shipped by US-Parent Multinationals"), f"us_home_f_{t}",
                  "Percent of the nine countries' exports of each product to the United States shipped by US-parent MNEs; the fifteen products with the largest US-parent exports to the United States.", 0.95))
    L.append(tab2(sc, "Tables", "tab_wp3_to_usa_top_products.tex", cap(sc, "Largest Export Products to the United States, by Type of Exporter"), f"to_usa_prod_{t}",
                  f"Fifteen largest HS6 products exported to the United States; percent of each product's exports to the United States by type of exporter. {N_USD}", size=r"\footnotesize"))


def fact2_body(sc: str, L: list, tag: str, cells: str) -> None:
    t = tag
    sh = shr(sc)
    L.append(sub("Product Complexity and Technology"))
    L.append(fig2(sc, "fig_wp0_fig2_pci", cap(sc, "Multinational Share of Export Value, by Product Complexity Quintile"), f"pci_{t}",
                  f"{sh} {N_PCI}", 0.78))
    L.append(fig2(sc, "fig_wp0_fig3_lall", cap(sc, "Multinational Share of Export Value, by Technology Class"), f"lall_{t}",
                  f"{sh} {N_LALL}", 0.78))
    L.append(sub("By Parent Country"))
    L.append(fig2(sc, "fig_wp1a_pci_by_parent", cap(sc, "Multinational Share of Export Value, by Product Complexity Quintile and Parent Country"), f"pci_p_{t}",
                  f"{sh} Foreign MNEs split by country of the ultimate parent. {N_PCI}", 0.92))
    L.append(tab2(sc, "Tables", "tab_wp1a_pci_by_parent.tex", cap(sc, "Multinational Share of Export Value, by Product Complexity Quintile and Parent Country"), f"pci_pn_{t}",
                  f"{sh} Other: all remaining foreign parents. {N_USD}"))
    L.append(fig2(sc, "fig_wp1a_lall_by_parent", cap(sc, "Multinational Share of Export Value, by Technology Class and Parent Country"), f"lall_p_{t}",
                  f"{sh} Foreign MNEs split by country of the ultimate parent. {N_LALL}", 0.92))
    L.append(tab2(sc, "Tables", "tab_wp1a_lall_by_parent.tex", cap(sc, "Multinational Share of Export Value, by Technology Class and Parent Country"), f"lall_pn_{t}",
                  f"{sh} Other: all remaining foreign parents. {N_USD}"))
    L.append(fig2(sc, "fig_wp1a_pci_lall_by_oecd", cap(sc, "Multinational Share of Export Value, by Product Sophistication and Location of the Parent"), f"oecd_{t}",
                  f"{sh} Foreign MNEs are split by whether the ultimate parent is in an OECD member country. Panel A: {N_PCI} Panel B: {N_LALL}", 1.0))
    L.append(sub("Other Measures of Product Sophistication"))
    six = (r"The six measures are the Product Complexity Index, the absolute import-demand elasticity of Fontagn\'e, "
           r"Guimbard and Orefice (2022), the elasticity of substitution of Broda and Weinstein, upstreamness, the quality "
           r"ladder and the revealed human-capital intensity of UNCTAD.")
    L.append(fig2(sc, "fig_wp1b_panel_quintiles", cap(sc, "Multinational Share of Export Value, by Quintile of Six Sophistication Measures"), f"six_q_{t}",
                  f"{sh} Quintiles computed over HS6 products. {six}", 1.0))
    L.append(fig2(sc, "fig_wp1b_sigma_fgo_abs_quintile", cap(sc, "Multinational Share of Export Value, by Quintile of the Import-Demand Elasticity"), f"fgo_q_{t}",
                  f"{sh} Quintiles of the absolute import-demand elasticity of Fontagn\\'e, Guimbard and Orefice (2022) across HS6 products; higher quintiles are more substitutable products.", 0.78))
    L.append(fig2(sc, "fig_wp1b_panel_hist", cap(sc, "Distribution of Export Value across Six Sophistication Measures"), f"six_h_{t}",
                  f"Bars: {SC_DESC[sc]} in each bin, by type of exporter. Line (right axis): foreign-MNE share of each bin. {six}", 1.0))
    L.append(fig2(sc, "fig_wp1b_hist_sigma_fgo_abs", cap(sc, "Distribution of Export Value across the Import-Demand Elasticity"), f"fgo_h_{t}",
                  "Left: export value in each bin, by type of exporter, and the foreign-MNE share of each bin. Right: number of HS6 products in each bin.", 1.0))
    L.append(fig2(sc, "fig_wp1b_hist_complexity", cap(sc, "Distribution of Export Value across the Product Complexity Index"), f"pci_h_{t}",
                  "Left: export value in each bin, by type of exporter, and the foreign-MNE share of each bin. Right: number of HS6 products in each bin.", 1.0))
    L.append(tab2(sc, "Tables", "tab_wp1b_quintile_shares.tex", cap(sc, "Multinational Share of Export Value, by Quintile of Six Sophistication Measures"), f"six_t_{t}",
                  f"{sh} Quintiles computed over HS6 products. --: fewer than 30 HS6 products carry the measure."))
    L.append(tab2(sc, "Tables", "tab_wp1b_measure_corr.tex", cap(sc, "Correlations between Sophistication Measures"), f"corr_{t}",
                  "Correlations across HS6 products, weighted by export value."))
    L.append(sub("Rauch Classes and End Use"))
    L.append(tab2(sc, "Tables", "tab_wp1b_rauch.tex", cap(sc, "Multinational Share of Export Value, by Rauch Product Class"), f"rauch_{t}",
                  f"{sh} {N_RAUCH} {N_USD}"))
    L.append(fig2(sc, "fig_wp1b_rauch", cap(sc, "Multinational Share of Export Value, by Rauch Product Class"), f"rauch_f_{t}",
                  f"{sh} {N_RAUCH}", 0.7))
    L.append(tab2(sc, "Tables", "tab_wp1b_rauch2.tex", cap(sc, "Multinational Share of Export Value: Differentiated and Other Products"), f"rauch2_{t}",
                  f"{sh} Rauch (1999) conservative classification; other products are reference-priced and homogeneous goods. {N_USD}"))
    L.append(fig2(sc, "fig_wp1b_rauch2", cap(sc, "Multinational Share of Export Value: Differentiated and Other Products"), f"rauch2_f_{t}",
                  f"{sh} Rauch (1999) conservative classification; other products are reference-priced and homogeneous goods.", 0.7))
    L.append(tab2(sc, "Tables", "tab_wp1b_bec.tex", cap(sc, "Multinational Share of Export Value, by End Use"), f"bec_{t}",
                  f"{sh} End use from BEC Rev.\\,4; HS6 products without a BEC correspondence are excluded. {N_USD}"))
    L.append(sub("Regressions"))
    L.append(tab2(sc, "Regressions", "reg_wp1b_odpy_fgo.tex", cap(sc, "Product Characteristics and Multinational Shares"), f"fgo_r_{t}",
                  f"{cells} Dependent variable: share of the cell's export value shipped by each type of MNE. The import-demand elasticity is standardized (mean 0, standard deviation 1). Regressions weighted by the cell's export value. Robust standard errors in parentheses. {D2_STARS}"))
    L.append(tab2(sc, "Regressions", "reg_wp1b_odpy_measures.tex", cap(sc, "Product Sophistication and Multinational Shares"), f"meas_r_{t}",
                  f"{cells} Dependent variable: share of the cell's export value shipped by each type of MNE. Omitted categories: primary and resource-based products (Lall) and homogeneous products (Rauch). Robust standard errors in parentheses. {D2_STARS}", size=r"\footnotesize"))


def subclass_block(sc: str, L: list, tag: str) -> None:
    t = tag
    sname = SC_NAME[sc]
    L.append(sec("Product Groups within the Sector", f"sub_{t}"))
    SPLITS = [("hs_section", "HS Section"), ("bec_enduse", "End Use"), ("bec4", "BEC Category"),
              ("sitc2", "SITC Division"), ("naics3", "NAICS Industry"), ("lall2000_category", "Technology Class")]
    if sc == "agro":
        SPLITS.append(("inputs", "Inputs and Other Products"))
    SRCNOTE = {"hs_section": "HS sections.", "bec_enduse": "End use from BEC Rev.\\,4.", "bec4": "Categories of BEC Rev.\\,4.",
               "sitc2": "SITC Rev.\\,3 divisions; HS6 products without an SITC correspondence are excluded.",
               "naics3": "NAICS 3-digit industries assigned to HS6 products.", "lall2000_category": "Lall (2000) technology classes.",
               "inputs": "Inputs: seeds, animal feed and live animals."}
    for stem, title in SPLITS:
        if not exists(sc, "Tables", f"tab_wp2_{stem}.tex"):
            continue
        k = SRCNOTE[stem]
        L.append(sub(f"By {title}"))
        L.append(tab2(sc, "Tables", f"tab_wp2_{stem}.tex", f"{sname}: Exports and Multinational Shares, by {title}", f"sc_{stem}_{t}",
                      f"{k} Foreign and domestic: percent of the group's export value. {N_LEAD} {N_USD}", size=r"\footnotesize"))
        L.append(fig2(sc, f"fig_wp2_{stem}", f"{sname}: Multinational Share of Export Value, by {title}", f"sc_{stem}_f_{t}",
                      f"{shr(sc)} {k}", 0.9))
        L.append(fig2(sc, f"fig_wp2_origin_x_{stem}", f"{sname}: Foreign-Multinational Share of Export Value, by Exporting Country and {title}", f"sc_{stem}_hm_{t}",
                      f"Percent of each group's export value in each country shipped by foreign MNEs. {k}", 0.95))
        L.append(tab2(sc, "Tables", f"tab_wp2_origin_x_{stem}.tex", f"{sname}: Exports by Exporting Country and {title}", f"sc_{stem}_ht_{t}",
                      f"Panel A: composition of each country's exports in the sector (rows add to 100). Panel B: percent of each cell's export value shipped by foreign MNEs. {k}", size=r"\footnotesize"))
        L.append(tab2(sc, "Tables", f"tab_wp2_{stem}_by_parent.tex", f"{sname}: Exports by {title} and Parent Country", f"sc_{stem}_par_{t}",
                      f"Percent of each group's export value, by country of the ultimate parent of foreign MNEs; domestic MNEs shown for comparison. {k}", size=r"\footnotesize"))
        if stem == "inputs":
            L.append(tab2(sc, "Tables", "tab_wp2_top_inputs_hs6.tex", f"{sname}: Largest Input Products", f"sc_topin_{t}",
                          f"HS6 input products with the largest export value. Foreign and domestic: percent of the product's export value. {N_USD}", size=r"\footnotesize"))
    L.append(sub("HS Section and End Use"))
    L.append(tab2(sc, "Tables", "tab_wp2_section_x_enduse_value.tex", f"{sname}: Exports by HS Section and End Use", f"sxe_v_{t}",
                  f"Export value by HS section and BEC Rev.\\,4 end use. {N_USD}"))
    L.append(tab2(sc, "Tables", "tab_wp2_section_x_enduse_foreignshare.tex", f"{sname}: Foreign-Multinational Share of Exports by HS Section and End Use", f"sxe_f_{t}",
                  "Percent of each cell's export value shipped by foreign MNEs."))


def four_sectors(L: list) -> None:
    L.append(tab2("sectors", "Tables", "tab_wp2_four_sectors.tex", "Exports and Multinational Shares, by Sector", "four",
                  f"Foreign and domestic: percent of the sector's export value. Other goods: HS 98--99 and unclassified codes. {N_LEAD} {N_USD}"))
    L.append(fig2("sectors", "fig_wp2_four_sectors", "Multinational Share of Export Value, by Sector", "four_f",
                  f"{N_SHARES} Agriculture: HS 01--24. Mining and fuels: HS 25--27 and 71. Manufacturing: HS 28--97 excluding 71.", 0.8))
    L.append(fig2("sectors", "fig_wp2_origin_x_sector", "Foreign-Multinational Share of Export Value, by Exporting Country and Sector", "ox_f",
                  "Percent of each country's export value in each sector shipped by foreign MNEs.", 0.8))
    L.append(tab2("sectors", "Tables", "tab_wp2_origin_x_sector.tex", "Exports by Exporting Country and Sector", "ox_t",
                  "Panel A: composition of each country's exports by sector (rows add to 100). Panel B: percent of each cell's export value shipped by foreign MNEs."))
    L.append(tab2("sectors", "Tables", "memo_wp2_services.tex", "Industry of Matched Exporting Affiliates", "services",
                  "Percent of matched export value, by NAICS sector of the exporting affiliate. Services are not observed in customs records; the table shows how much of goods exports is shipped by affiliates classified in service industries."))


def build_total() -> Path:
    L = [preamble("Multinational Firms and Trade in Latin America", "Stylized Facts: All Tables and Figures, All Goods",
                  datestr=date.today().strftime("%B %Y"))]
    L.append(data_block())
    fact_block("all", L, "all")
    L.append(sec("Sectors", "sectors"))
    four_sectors(L)
    L.append(tab2("sectors", "Tables", "tab_wp2_sector_x_destregion_foreign.tex", "Foreign-Multinational Exports by Sector and Destination Region", "sdr",
                  f"Percent of each sector's foreign-MNE exports, by destination region (rows add to 100). Last column: foreign-MNE exports. {N_USD}"))
    L.append(r"\end{document}" + "\n")
    return write_main(L)


def build_sectors() -> Path:
    L = [preamble("Multinational Firms and Trade in Latin America", "Stylized Facts by Sector: All Tables and Figures",
                  datestr=date.today().strftime("%B %Y"))]
    L.append(data_block(r"""Each part of this document repeats the exhibits within one sector: agriculture, manufacturing,
mining and fuels, and other goods (HS 98--99 and unclassified codes). Quintiles, rankings and top
lists are computed within the sector."""))
    L.append(sec("The Four Sectors", "sectors"))
    four_sectors(L)
    L.append(fig2("sectors", "fig_wp3_us_share_origin_sector", "Exports by US-Parent Multinationals, by Exporting Country and Sector", "us_ox_sector",
                  "Percent of each country's exports in each sector shipped by US-parent MNEs, to all destinations.", 1.0))
    L.append(tab2("sectors", "Tables", "tab_wp3_us_share_origin_sector.tex", "Exports by US-Parent Multinationals, by Exporting Country and Sector", "us_ox_sector_t",
                  f"Left panel: percent of each country's exports in the sector shipped by US-parent MNEs. Right panel: exports by US-parent MNEs. {N_USD}"))
    L.append(fig2("sectors", "fig_wp3_home_share_by_parent_sectors", "Share of Foreign-Multinational Exports Shipped to the Parent Country, by Sector", "home_sectors",
                  "Percent of each parent country's exports shipped to that same country, by sector. Hatched bars: the parent country's exports in the sector are below US\\$1 billion over the period.", 0.95))
    L.append(tab2("sectors", "Tables", "tab_wp3_home_share_by_parent_sectors.tex", "Share of Foreign-Multinational Exports Shipped to the Parent Country, by Sector", "home_sectors_t",
                  f"Left panel: percent of each parent country's exports shipped to that same country. Right panel: the parent country's exports. {N_USD}", size=r"\footnotesize"))
    L.append(fig2("sectors", "fig_wp3_to_usa_carriers_total_manuf", "Exports to the United States, by Type of Exporter and Exporting Country", "to_usa_tm",
                  "Percent of each country's exports to the United States, by type of exporter. Left: all goods. Right: manufacturing.", 1.0))
    L.append(tab2("sectors", "Tables", "tab_wp3_to_usa_carriers_by_sector.tex", "Exports to the United States, by Type of Exporter and Sector", "to_usa_sec",
                  f"Percent of each sector's exports to the United States, by type of exporter. {N_USD}"))
    cl = r"Standard errors clustered by origin--destination pair in parentheses. " + D2_STARS
    L.append(tab2("sectors", "Tables", "tab_wp3_fact5_summary.tex", "Multinational Presence and Exports by Sector: Intensive Margin", "f5sum",
                  f"Observations are origin--destination--HS6--year cells. {N_DEP_T1} Regressors: $\\ln$ number of foreign and of domestic MNEs; cells with at least one of each. Blank: too few observations. {cl}"))
    L.append(tab2("sectors", "Tables", "tab_wp3_fact6_summary.tex", "Distance and Firm Exports, by Sector", "f6sum",
                  f"Observations are firm--destination--HS6--year cells. Dependent variable: $\\ln$ exports. Non-MNE firms are the omitted group. {cl}"))
    for sc in SECTOR_SCOPES:
        L.append(r"\clearpage\part{" + SC_NAME[sc] + "}\n")
        fact_block(sc, L, sc)
        subclass_block(sc, L, sc)
    L.append(r"\end{document}" + "\n")
    return write_main(L)


def build_countries() -> Path:
    L = [preamble("Multinational Firms and Trade in Latin America", "Stylized Facts by Exporting Country: All Tables and Figures",
                  datestr=date.today().strftime("%B %Y"))]
    L.append(data_block(r"""Each section of this document reports, for one exporting country, where the exports of its
multinational affiliates go by parent region and parent country, how much of each parent's exports
goes to the parent's own country, and the largest export products, for all goods and by sector."""))
    for o in ORIGINS:
        name = COUNTRY_NAME[o]
        L.append(sec(name, f"c_{o}"))
        L.append(sub("Parents and Destinations"))
        L.append(tab2("all", "Tables", f"tab_wp1c_byorigin_{o}.tex", f"{name}: Multinational Exports by Parent Region and Destination Region", f"c_reg_{o}",
                      f"Percent of each group's exports from {name}, by destination region (rows add to 100). Last column: the group's exports. {N_USD}"))
        L.append(fig2("all", f"fig_wp1d_heatmap_country_cellpct_{o}", f"{name}: Foreign-Multinational Exports by Parent Country and Destination", f"c_hm_{o}",
                      f"Percent of the foreign-MNE export value of {name} in each parent country and destination pair; fifteen largest parent countries and destinations.", 1.0))
        L.append(fig2("all", f"fig_wp1d_home_share_by_parent_{o}", f"{name}: Share of Foreign-Multinational Exports Shipped to the Parent Country", f"c_home_{o}",
                      f"Percent of each parent country's exports from {name} shipped to that same country; ten largest parent countries.", 0.85))
        for sc in SECTOR_SCOPES:
            if exists(sc, "Tables", f"tab_wp1c_byorigin_{o}.tex"):
                L.append(tab2(sc, "Tables", f"tab_wp1c_byorigin_{o}.tex", f"{name}, {SC_NAME[sc]}: Multinational Exports by Parent Region and Destination Region", f"c_reg_{o}_{sc}",
                              f"Percent of each group's {scope_word(sc)}exports from {name}, by destination region (rows add to 100). Last column: the group's exports. {N_USD}"))
        L.append(sub("Products"))
        top_note = "Foreign, domestic and local: percent of the product's export value. Leading parent: largest parent country and its share of the product's foreign-MNE exports."
        L.append(tab2("all", "Tables", f"tab_wp1f_top_hs6_{o}.tex", f"{name}: Fifteen Largest Export Products", f"c_hs6_{o}",
                      f"Fifteen largest HS6 products exported by {name}. {top_note} {N_USD}", size=r"\footnotesize"))
        for sc in SECTOR_SCOPES:
            if exists(sc, "Tables", f"tab_wp1f_top_hs6_{o}.tex"):
                L.append(tab2(sc, "Tables", f"tab_wp1f_top_hs6_{o}.tex", f"{name}, {SC_NAME[sc]}: Fifteen Largest Export Products", f"c_hs6_{o}_{sc}",
                              f"Fifteen largest {scope_word(sc)}HS6 products exported by {name}. {top_note} {N_USD}", size=r"\footnotesize"))
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
#   rev. 2026-09-23: same exhibit conventions as WP_draft2 (titles, short notes with a plain
#   description and a separate Source line, relabelled fragments, main/appendix split), and a
#   plainer text throughout.
# =====================================================================

PAPER_ABSTRACT = r"""
We match the customs export records of nine Latin American countries to the ownership records of
Orbis and Dun \& Bradstreet and classify every exporter as a foreign multinational affiliate, a
domestic multinational affiliate or a local firm. Multinational affiliates account for 61 percent
of the region's exports, most of it foreign owned. Foreign affiliates concentrate in complex and
differentiated products, domestic ones in primary goods. The parents come from a few countries,
and a small number of large groups accounts for most of the value. Product--destination pairs with
more multinationals export more, and distance reduces the exports of multinationals less than
those of other firms. US groups are the only large investors that ship a sizeable share of their
affiliates' exports to their own country: 22 percent, against less than 3 percent for British,
Dutch or Swiss groups.
"""

AGRO_ABSTRACT = r"""
We match the customs export records of nine Latin American countries to the ownership records of
Orbis and Dun \& Bradstreet and describe who owns the region's agricultural exporters. Multinational
affiliates account for 48 percent of agricultural exports (HS 01--24), 38 percent foreign owned and
10 percent domestically owned. The share ranges from 29 percent in El Salvador to 66 percent in
Paraguay. The parents come from a few countries, and a small number of large groups accounts for
half of foreign-affiliate exports. Unlike in the region's exports as a whole, foreign affiliates in
agriculture are not concentrated in more complex or more differentiated products.
Product--destination pairs with more multinationals export more, and distance reduces the exports
of multinationals less than those of other firms.
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
Customs records show what a country exports and where, but not who owns the exporter. In Latin
America many exporters are affiliates of groups headquartered abroad, so this is a large gap.
Foreign direct investment statistics do not fill it: they show where capital goes, not which
firms export which products to which markets.

In this paper we match the customs export records of nine countries (Argentina, Chile, Colombia,
Costa Rica, the Dominican Republic, El Salvador, Paraguay, Peru and Uruguay) to the ownership
records of Orbis and Dun \& Bradstreet. Every exporter is classified as a foreign multinational
affiliate, a domestic multinational affiliate or a local firm, and the exports of foreign
affiliates can be traced to the country of their parent.

The data show six facts. First, multinational affiliates account for 61 percent of the region's
exports, from 47 percent in Peru to 74 percent in Colombia, and most of it is foreign owned.
Second, foreign affiliates concentrate in complex and differentiated products and domestic
multinationals in primary goods, especially within manufacturing. Third, the parents come from a
few countries: the United States, the United Kingdom and Canada account for half of
foreign-affiliate exports. Fourth, parents with more than 100 affiliates worldwide are 9 percent of
all parents and account for 56 percent of foreign-affiliate exports. Fifth, product--destination
pairs with more multinationals export more, and the relationship is about three times stronger for
foreign than for domestic affiliates, also for the exports of local firms. Sixth, distance reduces
the exports of multinationals less than those of other firms.

The United States deserves separate attention because it is both the largest parent country and
the largest destination. Affiliates of US groups account for 10.8 percent of the exports of the
nine countries, the United States buys 18.4 percent of them, and the two overlap in 2.5 percent.
US groups are the only large investors that ship a sizeable share of their affiliates' exports to
their own country: 22.3 percent, against 0.6 percent for British groups, 2.2 percent for Dutch
groups and almost none for Swiss or Liechtenstein groups. These shipments are concentrated in
Central America and the Caribbean, where US-parent affiliates account for 41 percent of El
Salvador's exports to the United States, 40 percent of Costa Rica's and 26 percent of the
Dominican Republic's. Groups from other countries follow different patterns. British and
Liechtenstein groups, mostly in mining, sell to Asia, and German and Japanese groups export from
Argentina to Brazil.

\tbw{Contribution to the literature: to be written.}

Section~\ref{sec:lit} reviews the literature, Section~\ref{sec:data} describes the data and
Section~\ref{sec:facts} presents the six facts. Section~\ref{sec:products} looks at products,
Section~\ref{sec:model} outlines the model and Section~\ref{sec:concl} concludes.
"""

AGRO_INTRO = r"""
Customs records show what a country exports and where, but not who owns the exporter. In
agriculture this matters because a large part of Latin America's exports is handled by traders,
processors and food companies headquartered abroad. Foreign direct investment statistics show
where capital goes, not which firms export which products to which markets.

In this paper we match the customs export records of nine countries (Argentina, Chile, Colombia,
Costa Rica, the Dominican Republic, El Salvador, Paraguay, Peru and Uruguay) to the ownership
records of Orbis and Dun \& Bradstreet, classify every exporter as a foreign multinational
affiliate, a domestic multinational affiliate or a local firm, and focus on agricultural exports
(HS chapters 01--24). These amount to US\$78.9 billion a year, a third of the nine countries'
exports. All results are for the nine countries together.

Multinational affiliates account for 48 percent of agricultural exports, 38 percent foreign owned
and 10 percent domestically owned, with shares that range from 29 percent in El Salvador to 66
percent in Paraguay. Parents come from a few countries, and groups with more than 100 affiliates
worldwide, 12 percent of all parents, account for half of foreign-affiliate exports. Among the five largest
product groups, the foreign share is highest in oil seeds (62 percent) and cereals (49 percent). Two patterns found in the region's exports as a whole do not hold in
agriculture: foreign affiliates are not concentrated in more complex products or in differentiated
products. The other results do hold. Product--destination pairs with more multinationals export
more, and distance reduces the exports of multinationals less than those of other firms.

\tbw{Contribution to the literature: to be written.}

Section~\ref{sec:lit} reviews the literature, Section~\ref{sec:data} describes the data and
Section~\ref{sec:facts} presents the facts. Section~\ref{sec:sub} looks at product groups within
agriculture, Section~\ref{sec:model} outlines the model and Section~\ref{sec:concl} concludes.
"""


def data_section(agro: bool = False) -> str:
    scope = (r"""
Agricultural exports are HS chapters 01--24: live animals, meat, fish, dairy, vegetables, fruit,
cereals, oil seeds, fats and oils, prepared foods, beverages and tobacco. All results in this paper
are for these products and for the nine countries together.
""" if agro else "")
    return r"""
\subsection{Customs data}

The export records come from the customs authorities of the nine countries. Each record gives the
value exported (FOB, US dollars) by a firm, of an HS6 product (2007 revision), to a destination, in
a year. Firms are identified by their tax number and name. The records cover all merchandise
exports in the years available for each country: Argentina 2011--2019, Chile 2009--2022, Colombia
2010--2021, Costa Rica 2010--2019, the Dominican Republic 2012--2019, El Salvador 2006--2018,
Paraguay 2012--2020, Peru 2010--2019 and Uruguay 2010--2019.
""" + scope + r"""
\subsection{Ownership data and matching}

Ownership comes from Orbis (Bureau van Dijk) and Dun \& Bradstreet, which report for each company
its global ultimate owner and the owner's country. We combine the two sources into one file with
the group, the country of the parent and the number of affiliates the group has worldwide.

Exporters are matched to this file in four steps: by tax number where the corporate records
report it; by company name within each country, using a character-based similarity measure,
with each candidate pair reviewed by a large language model; by company name across all countries; and, for the 500
largest unmatched exporters of each country, by hand, using company websites and business
registries. The tax number delivers about 60 percent of matched export value. After matching, the
parent's country is known for 92.5 percent of the export value of foreign affiliates.

\subsection{Definitions}

An exporter found in Orbis or Dun \& Bradstreet is a multinational affiliate (MNE). It is a
\emph{domestic} MNE when its ultimate parent is located in the exporting country and a
\emph{foreign} MNE otherwise; matched exporters without a recorded parent country are counted as
foreign. Exporters not found in either database are \emph{local} firms. Because the match relies
on ownership links, a group's head company exporting from its own country cannot be identified
and appears among local firms.

Products are classified with the Product Complexity Index of Hausmann and Hidalgo, the technology
classes of Lall (2000), the Rauch (1999) classification, and the end-use classes of BEC Rev.\,4.
Sectors are defined on HS chapters: agriculture 01--24, mining and fuels 25--27 and 71,
manufacturing 28--97 excluding 71. Distance comes from the CEPII gravity database.

\subsection{Sample}
"""


PAPER_SAMPLE_TEXT = r"""
Table~\ref{tab:p_sample} describes the sample by country and Table~\ref{tab:p_counts} summarizes
it. The nine countries have 165,543 exporters, of which 31,350 are matched to a corporate record.
They export 5,930 HS6 products to 253 destinations. The matched exporters belong to 17,094 groups
with parents in 165 countries.
"""

AGRO_SAMPLE_TEXT = r"""
Table~\ref{tab:p_sample} describes the agricultural sample by country and Table~\ref{tab:p_counts}
summarizes it. The nine countries have 38,832 agricultural exporters, of which 7,993 are matched to
a corporate record, and export 1,023 HS6 products to 245 destinations.
"""


PAPER_FACT_TEXT = {
1: r"""
Figure~\ref{fig:p_f1} shows the share of each country's exports accounted for by multinational
affiliates. It ranges from 47 percent in Peru to 74 percent in Colombia and is 61 percent for the
nine countries together. Foreign affiliates account for 46 percent of total exports and domestic
multinationals for 14 percent. Foreign affiliates export more than domestic multinationals in every
country except Colombia, where the state oil company and its subsidiaries are domestic
multinationals. Chile, with copper and pulp, is the other country with a large domestic share.

Figures~\ref{fig:p_us3_total} and~\ref{fig:p_us3_origin} and Table~\ref{tab:p_us3_tab} separate
the two roles of the United States. The United States buys 18.4 percent of the region's exports
and US-parent affiliates ship 10.8 percent, but only 2.5 percent is both. US-parent affiliates
account for 13.6 percent of the region's exports to the United States, and for much more in El
Salvador, Costa Rica and the Dominican Republic.
""",
2: r"""
Figure~\ref{fig:p_f2f3} sorts products by sophistication. The foreign share is 0.46 in the least
complex quintile of the Product Complexity Index and 0.65 in the most complex one, and it is highest
in high- and medium-technology manufactures. Domestic multinationals are concentrated in primary
and resource-based products. The Rauch classification gives the same ordering
(Table~\ref{tab:p_rauch} and Figure~\ref{fig:p_rauch_fig}): foreign affiliates account for 56
percent of exports of differentiated products and 34 percent of homogeneous products, while the
domestic shares are 6 and 23 percent. By end use, the foreign share is 65 percent in capital goods,
48 percent in intermediate goods and 44 percent in consumption goods (Table~\ref{tab:p_bec}).
Table~\ref{tab:p_ladder} shows the same patterns in regressions at the origin--destination--product--year
level. The pattern is clearest within manufacturing (Figure~\ref{fig:p_rauch_manuf}); it is weak
within agriculture and absent within mining.
""",
3: r"""
Figure~\ref{fig:p_f4} ranks parent countries by their share of foreign-affiliate exports. The
United States (23 percent), the United Kingdom (19 percent) and Canada (8 percent) account for
half, and the ten largest parent countries for more than three quarters.
Table~\ref{tab:p_pxp} shows where the affiliates of each of the ten largest parent countries sell;
its diagonal is the share shipped to the parent's own country. The share is 22.3 percent for US
groups, 19.5 percent for Canadian groups and 18.6 percent for Brazilian groups, but less than 3
percent for British, Dutch or Swiss groups. Figure~\ref{fig:p_dest} shows the same pattern from the
side of the main destination markets.
""",
4: r"""
Figure~\ref{fig:p_f5} groups parents by the number of affiliates their group has worldwide. Almost
half of the parents have a single affiliate, but the 9 percent with more than 100 affiliates
account for 56 percent of foreign-affiliate exports.
""",
5: r"""
Table~\ref{tab:p_t1} relates the exports of an origin--destination--product--year cell to the
number of multinationals exporting in it (intensive margin) and to whether any does (extensive
margin). Both relationships are positive and large, also for the exports of the local firms in the
same cell (Panel~B). Table~\ref{tab:p_f5counts} splits the intensive margin by type of
multinational. The coefficient is 1.21 for foreign affiliates and 0.44 for domestic ones in
Panel~A, and 1.13 and 0.47 in Panel~B. On the extensive margin the two coefficients are almost
equal (Table~\ref{tab:a_ext}).
""",
6: r"""
Table~\ref{tab:p_t2} estimates how firm exports fall with distance. The elasticity is $-0.16$ for
local firms and about 0.05 smaller in absolute value for multinationals. Table~\ref{tab:p_dist}
shows that the difference is larger for foreign affiliates (0.049) than for domestic ones (0.032),
and largest for foreign affiliates exporting to their parent's country (0.064).
""",
}

AGRO_FACT_TEXT = {
1: r"""
Figure~\ref{fig:p_f1} shows the share of each country's agricultural exports accounted for by
multinational affiliates. It is 48 percent for the nine countries together, 38 percent foreign
owned and 10 percent domestically owned. It ranges from 66 percent in Paraguay and 62 percent in
Uruguay to 37 percent in Peru and 29 percent in El Salvador. Foreign affiliates export more than
domestic multinationals in every country; the gap is smallest in Chile (30 against 19 percent).
""",
2: r"""
In the region's exports as a whole, the foreign share rises with product complexity and is higher
for differentiated products. Neither pattern holds in agriculture. Across quintiles of the Product
Complexity Index the foreign share is 0.29, 0.49, 0.38, 0.42 and 0.55 (Figure~\ref{fig:p_f2f3}).
By Rauch class it is 41 percent for differentiated products, 32 percent for reference-priced
products and 41 percent for homogeneous products, and the domestic share is about 9 percent in all
three (Table~\ref{tab:p_rauch} and Figure~\ref{fig:p_rauch_fig}). By end use, the foreign share is
41 percent for intermediate goods and 35 percent for consumption goods (Table~\ref{tab:p_bec}).
""",
3: r"""
Figure~\ref{fig:p_f4} ranks parent countries by their share of foreign-affiliate agricultural
exports. The ten largest parent countries account for more than 70 percent. The list reflects the
grain trade and the jurisdictions where trading groups hold their assets: Switzerland (11 percent),
the Netherlands (9.5 percent) and Liechtenstein (7.6 percent) rank high, together with the United
States (24 percent). The destination of each parent country's exports is in
Tables~\ref{tab:ap_pxd} and~\ref{tab:ap_pxp} in the appendix.
""",
4: r"""
Figure~\ref{fig:p_f5} groups parents by the number of affiliates their group has worldwide. In
agriculture 45 percent of parents have a single affiliate, but the 12 percent with more than 100
affiliates account for half of foreign-affiliate exports.
""",
5: r"""
Table~\ref{tab:p_t1} relates the agricultural exports of an origin--destination--product--year cell
to the number of multinationals exporting in it and to whether any does. The results are similar
to those for all exports, including for the exports of local firms in the same cell (Panel~B).
Table~\ref{tab:p_f5counts} splits the intensive margin by type of multinational: the coefficient is
1.30 for foreign affiliates and 0.52 for domestic ones.
""",
6: r"""
Table~\ref{tab:p_t2} estimates how firm agricultural exports fall with distance. The elasticity is
$-0.21$ for local firms, larger in absolute value than for all exports. Table~\ref{tab:p_dist} shows
that it is 0.037 smaller in absolute value for foreign affiliates and 0.019 smaller for domestic
ones.
""",
}

PAPER_PRODUCTS_TEXT = r"""
Figure~\ref{fig:p_hs6} shows the twenty largest export products and who exports them. Crude
petroleum is mostly exported by domestic multinationals and copper concentrates by foreign ones.
Figure~\ref{fig:p_hs6_parent} splits the foreign share by parent country: British groups in copper
and coal, Canadian groups in gold, US groups in soybeans, maize and apparel, German groups in
trucks. Table~\ref{tab:p_sections} gives the same information by HS section, and
Tables~\ref{tab:a_agro_sitc} to~\ref{tab:a_mining_bec} in the appendix break down agriculture,
manufacturing and mining.
"""

AGRO_SUB_TEXT = r"""
Table~\ref{tab:a_sitc} and Figure~\ref{fig:a_sitc} split agricultural exports by SITC division.
The largest divisions are animal feed (US\$13.8 billion a year), vegetables and fruit (10.6),
cereals (10.3), oil seeds (6.7) and vegetable oils (6.0). The foreign share is highest in miscellaneous
edible products (71 percent), oil seeds (62 percent) and tobacco (55 percent), and lowest in coffee,
tea and cocoa (30 percent), beverages (29 percent) and sugar (19 percent). Domestic multinationals are largest in
dairy (20 percent), coffee (16 percent) and sugar (15 percent). Figure~\ref{fig:a_inputs} compares
agricultural inputs with other agricultural products, and Figure~\ref{fig:a_hs6} shows the twenty
largest agricultural export products. Other breakdowns are in the appendix.
"""

PAPER_TAIL = {
"lit": r"""
\tbw{To be written. Three strands: firm-level evidence on multinational production and trade;
ownership, market power and trade policy; and evidence on multinational firms in Latin America.}
""",
"model": r"""
\tbw{To be written. The model is developed in the companion theory paper.}
""",
"concl": r"""
\tbw{To be written.}
""",
}

REFS_BLOCK = r"""
\tbw{To be completed.}
\begin{list}{}{\leftmargin=1.5em \itemindent=-1.5em \itemsep=2pt \topsep=4pt}
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

# shared note fragments (same wording as WP_draft2)
N_SHARES = r"Shares of export value, all available years pooled."
N_USD = r"Values are annual averages in US\$ billion."
N_LEAD = r"Leading parents: the three largest parent countries and their share of the row's foreign-MNE exports."
N_RAUCH = (r"Rauch (1999) conservative classification: homogeneous goods are traded on organized exchanges, "
           r"reference-priced goods have a price quoted in trade publications, and differentiated goods have neither.")
N_LALL = r"Lall (2000) technology classes: primary and resource-based products, and low-, medium- and high-technology manufactures."
N_PCI = r"Quintiles of the Hausmann--Hidalgo Product Complexity Index across HS6 products (Q1 = least complex)."
N_CELLS = r"Observations are origin--destination--HS6--year cells."
N_FIRMS = r"Observations are firm--destination--HS6--year cells."
N_DEP_T1 = r"Dependent variable: $\ln$ exports of the cell (Panel A) and of the non-MNE firms in the cell (Panel B)."


def n_cl() -> str:
    return r"Standard errors clustered by origin--destination pair in parentheses. " + D2_STARS


def build_paper() -> Path:
    """The working paper for the coauthors, with the exhibit conventions of WP_draft2."""
    L = [paper_preamble("Multinational Firms and Trade in Latin America",
                        "Six Stylized Facts on Ownership and Exports",
                        PAPER_ABSTRACT, PAPER_KEYWORDS, PAPER_JEL)]
    A, M, MI, S = "all", "manufacturing", "mining", "sectors"
    cl = n_cl()

    L.append(sec("Introduction", "intro")); L.append(par(PAPER_INTRO))
    L.append(sec("Related Literature", "lit")); L.append(par(PAPER_TAIL["lit"]))

    L.append(sec("Data", "data"))
    L.append(par(data_section(agro=False)))
    L.append(par(PAPER_SAMPLE_TEXT))
    L.append(tab2(A, "Tables", "tab_paper_sample.tex", "Sample Coverage, by Exporting Country", "p_sample",
                  f"Exporters are distinct tax identifiers within each country; matched exporters are those found in Orbis or Dun \\& Bradstreet. Records are firm--destination--HS6--year observations. {N_USD}", size=r"\footnotesize"))
    L.append(tab2(A, "Tables", "tab_paper_sample_counts.tex", "Sample Summary", "p_counts",
                  "Nine countries, all available years pooled. Shares are percent of total export value."))

    L.append(sec("Six Stylized Facts", "facts"))

    L.append(sub("Fact 1: Multinationals Account for a Large Share of Exports"))
    L.append(par(PAPER_FACT_TEXT[1]))
    L.append(fig2(A, "fig_wp0_fig1_origin", "Multinational Share of Export Value, by Exporting Country", "p_f1",
                  f"{N_SHARES} The figure at the end of each bar is the total MNE share.", 0.8))
    L.append(fig2(A, "fig_wp3_us_three_shares_total", "Exports to the United States and Exports by US-Parent Multinationals", "p_us3_total",
                  "Shares of the total exports of the nine countries. The third bar is exports by US-parent MNEs shipped to the United States.", 0.6))
    L.append(fig2(A, "fig_wp3_us_three_shares_origin", "Exports to the United States and Exports by US-Parent Multinationals, by Exporting Country", "p_us3_origin",
                  "Shares of each country's total exports.", 1.0))
    L.append(tab2(A, "Tables", "tab_wp3_us_three_shares.tex", "Exports to the United States and Exports by US-Parent Multinationals, by Exporting Country", "p_us3_tab",
                  f"Columns (1)--(3): percent of each country's total exports. Column (4): percent of exports to the United States shipped by US-parent MNEs. Countries sorted by column (3). {N_USD}"))

    L.append(sub("Fact 2: Foreign Multinationals Specialize in Complex Products, Domestic Multinationals in Primary Goods"))
    L.append(par(PAPER_FACT_TEXT[2]))
    L.append(panel_fig2([(A, "fig_wp0_fig2_pci", "Product Complexity Index quintile"), (A, "fig_wp0_fig3_lall", "Lall (2000) technology class")],
                        "Multinational Share of Export Value, by Product Sophistication", "p_f2f3",
                        f"{N_SHARES} Panel A: {N_PCI} Panel B: {N_LALL}"))
    L.append(tab2(A, "Tables", "tab_wp1b_rauch.tex", "Multinational Share of Export Value, by Rauch Product Class", "p_rauch",
                  f"{N_SHARES} {N_RAUCH} {N_USD}"))
    L.append(fig2(A, "fig_wp1b_rauch", "Multinational Share of Export Value, by Rauch Product Class", "p_rauch_fig",
                  f"{N_SHARES} {N_RAUCH}", 0.7))
    L.append(tab2(A, "Tables", "tab_wp1b_bec.tex", "Multinational Share of Export Value, by End Use", "p_bec",
                  f"{N_SHARES} End use from BEC Rev.\\,4; HS6 products without a BEC correspondence are excluded. {N_USD}"))
    L.append(tab2(A, "Regressions", "reg_wp1b_odpy_measures.tex", "Product Sophistication and Multinational Shares", "p_ladder",
                  f"{N_CELLS} Dependent variable: share of the cell's export value shipped by each type of MNE. Omitted categories: primary and resource-based products (Lall) and homogeneous products (Rauch). Robust standard errors in parentheses. {D2_STARS}", size=r"\footnotesize"))
    L.append(fig2(M, "fig_wp1b_rauch", "Manufacturing: Multinational Share of Export Value, by Rauch Product Class", "p_rauch_manuf",
                  f"Shares of manufacturing export value (HS 28--97 excluding 71), all available years pooled. {N_RAUCH}", 0.7))

    L.append(sub("Fact 3: Multinationals from a Small Set of Countries Dominate Exports"))
    L.append(par(PAPER_FACT_TEXT[3]))
    L.append(fig2(A, "fig_wp1a_parent_share", "Foreign-Multinational Exports, by Parent Country", "p_f4",
                  "Percent of foreign-MNE export value, by country of the ultimate parent.", 0.78))
    L.append(tab2(A, "Tables", "tab_wp1c_parent_x_parentdest_rowpct.tex", "Foreign-Multinational Exports to the Parent Countries, by Parent Country", "p_pxp",
                  "Percent of each parent country's exports, by destination (rows add to 100). Destinations are the ten largest parent countries; the diagonal is the share shipped to the parent's own country."))
    L.append(fig2(A, "fig_wp3_dest_carriers", "Ownership of Exports to the Main Destination Markets", "p_dest",
                  "Percent of the export value reaching each destination, by type of exporter. The first segment is exports by MNEs whose parent is located in that destination. EU-27 member states are pooled.", 1.0))

    L.append(sub("Fact 4: A Small Set of Large Multinational Groups Accounts for Most Exports"))
    L.append(par(PAPER_FACT_TEXT[4]))
    L.append(fig2(A, "fig_wp0_fig5_network", "Foreign-Multinational Exports and Number of Parents, by Size of the Group's Global Network", "p_f5",
                  "Shares of foreign-MNE export value and of parents, by the number of affiliates the group has worldwide.", 0.7))

    L.append(sub("Fact 5: Multinational Presence Is Associated with Higher Exports"))
    L.append(par(PAPER_FACT_TEXT[5]))
    L.append(tab2(A, "Regressions", "reg_wp0_table1_repro.tex", "Multinational Presence and Exports", "p_t1",
                  f"{N_CELLS} {N_DEP_T1} Intensive margin: $\\ln$ number of MNEs, cells with at least one MNE. Extensive margin: indicator for at least one MNE. {cl}"))
    L.append(tab2(A, "Regressions", "reg_wp1e_counts.tex", "Multinational Presence and Exports: Intensive Margin, by Type of Multinational", "p_f5counts",
                  f"{N_CELLS} {N_DEP_T1} Regressors: $\\ln$ number of MNEs of each type. Columns (5)--(6) split foreign MNEs by whether the destination is the parent's country. {cl}"))

    L.append(sub("Fact 6: Distance Is a Weaker Barrier for Multinationals"))
    L.append(par(PAPER_FACT_TEXT[6]))
    L.append(tab2(A, "Regressions", "reg_wp0_table2_repro.tex", "Distance and Firm Exports: Multinationals by Presence at the Destination", "p_t2",
                  f"{N_FIRMS} Dependent variable: $\\ln$ exports. Non-MNE firms are the omitted group. Present: the group has an affiliate in the destination or the destination is the parent's country. {cl}"))
    L.append(tab2(A, "Regressions", "reg_wp1e_distance_hq.tex", "Distance and Firm Exports: Foreign and Domestic Multinationals", "p_dist",
                  f"{N_FIRMS} Dependent variable: $\\ln$ exports. Non-MNE firms are the omitted group. Columns (3)--(4) split foreign MNEs by whether the destination is the parent's country. {cl}"))

    L.append(sec("Products", "products"))
    L.append(par(PAPER_PRODUCTS_TEXT))
    L.append(fig2(A, "fig_wp1f_top20_hs6_stacked", "Ownership of the Twenty Largest Export Products", "p_hs6",
                  "Shares of each product's export value. Twenty largest HS6 products by export value.", 1.0))
    L.append(fig2(A, "fig_wp1f_top20_hs6_by_parent", "Ownership of the Twenty Largest Export Products, by Parent Country", "p_hs6_parent",
                  "Shares of each product's export value. Foreign-MNE share split by country of the ultimate parent; the unfilled part of each bar is local firms.", 1.0))
    L.append(tab2(A, "Tables", "tab_wp1f_hs_sections.tex", "Exports and Multinational Shares, by HS Section", "p_sections",
                  f"Foreign, domestic and local: percent of each section's export value. Leading parent: largest parent country and its share of the section's foreign-MNE exports. {N_USD}", size=r"\footnotesize"))

    L.append(sec("Theoretical Framework", "model")); L.append(par(PAPER_TAIL["model"]))
    L.append(sec("Concluding Remarks", "concl")); L.append(par(PAPER_TAIL["concl"]))
    L.append(REFS_HEAD); L.append(par(REFS_BLOCK))

    # ---------------- appendix: same set and order as WP_draft2
    L.append(APPENDIX_OPEN)
    L.append(sec("Additional Tables and Figures", "app"))
    L.append(usub("Fact 1"))
    L.append(tab2(A, "Tables", "tab_wp0_fig1_origin.tex", "Multinational Share of Export Value, by Exporting Country", "a_f1n",
                  f"Shares of each country's export value, all available years pooled. {N_USD}"))
    L.append(fig2(A, "fig_wp1a_origin_by_parent", "Multinational Share of Export Value, by Exporting Country and Parent Country", "a_f1_parent",
                  "Shares of each country's export value. Foreign MNEs split by country of the ultimate parent; the ten largest parent countries are shown separately.", 0.92))
    L.append(tab2(A, "Tables", "tab_wp1a_origin_by_parent.tex", "Multinational Share of Export Value, by Exporting Country and Parent Country", "a_f1pn",
                  f"Shares of each country's export value. Other: all remaining foreign parents. {N_USD}"))
    L.append(fig2(S, "fig_wp3_fig1_by_sector_panels", "Multinational Share of Export Value, by Exporting Country and Sector", "a_f1_sectors",
                  "Shares of each country's export value in the sector. Panel A: agriculture (HS 01--24). Panel B: manufacturing (HS 28--97 excluding 71). Panel C: mining and fuels (HS 25--27 and 71).", 1.0))
    L.append(tab2(S, "Tables", "tab_wp2_four_sectors.tex", "Exports and Multinational Shares, by Sector", "a_sectors",
                  f"Foreign and domestic: percent of the sector's export value. Rest: HS 98--99 and unclassified codes. {N_LEAD} {N_USD}"))

    L.append(usub("Fact 2"))
    L.append(fig2(A, "fig_wp1a_pci_lall_by_oecd", "Multinational Share of Export Value, by Product Sophistication and Location of the Parent", "a_f2_oecd",
                  f"{N_SHARES} Foreign MNEs are split by whether the ultimate parent is in an OECD member country. Panel A: {N_PCI} Panel B: {N_LALL}", 1.0))
    L.append(fig2(M, "fig_wp0_fig2_pci", "Manufacturing: Multinational Share of Export Value, by Product Complexity Quintile", "a_f2_manuf",
                  "Shares of manufacturing export value, all available years pooled. Quintiles computed over manufacturing HS6 products.", 0.78))

    L.append(usub("Fact 3"))
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
                  f"Percent of each sector's exports to the United States, by type of exporter. {N_USD}"))
    L.append(tab2(A, "Tables", "tab_wp3_us_home_products.tex", "Main Products Shipped by US-Parent Multinationals to the United States", "a_us_prod",
                  f"Fifteen HS6 products with the largest exports by US-parent MNEs to the United States. {N_USD}", size=r"\footnotesize"))

    L.append(usub("Fact 4"))
    L.append(tab2(A, "Tables", "tab_wp0_fig5_network.tex", "Foreign-Multinational Exports and Number of Parents, by Size of the Group's Global Network", "a_f5_tab",
                  "Number and share of parents, and share of foreign-MNE export value, by the number of affiliates the group has worldwide. Parents with a network record in Orbis or Dun \\& Bradstreet: 98 percent of parents and 97 percent of foreign-MNE export value."))

    L.append(usub("Fact 5"))
    L.append(tab2(A, "Regressions", "reg_wp1e_extensive.tex", "Multinational Presence and Exports: Extensive Margin, by Type of Multinational", "a_ext",
                  f"{N_CELLS} {N_DEP_T1} Regressors: indicators for at least one MNE of each type. Columns (5)--(6) split foreign MNEs by whether the destination is the parent's country. {cl}"))
    L.append(tab2(A, "Tables", "tab_wp1e_presence_shares.tex", "Multinational Exports by Exporting Country and Destination Type", "a_pres",
                  f"MNE and foreign-MNE export value by country, and the split of foreign-MNE value by destination. Parent country: exports to the country of the ultimate parent. Other: all remaining destinations; in parentheses, destinations where the group has another affiliate. {N_USD}"))
    L.append(tab2(S, "Tables", "tab_wp3_fact5_summary.tex", "Multinational Presence and Exports by Sector: Intensive Margin", "a_f5sum",
                  f"{N_CELLS} {N_DEP_T1} Specification of columns (3)--(4) of Table~\\ref{{tab:p_f5counts}}, estimated by sector. Blank: too few observations. {cl}"))
    L.append(tab2(S, "Tables", "tab_wp3_fact5ext_summary.tex", "Multinational Presence and Exports by Sector: Extensive Margin", "a_f5extsum",
                  f"{N_CELLS} {N_DEP_T1} Specification of columns (3)--(4) of Table~\\ref{{tab:a_ext}}, estimated by sector. {cl}"))

    L.append(usub("Fact 6"))
    L.append(tab2(S, "Tables", "tab_wp3_fact6_summary.tex", "Distance and Firm Exports, by Sector", "a_f6sum",
                  f"{N_FIRMS} Dependent variable: $\\ln$ exports. Specification of columns (1)--(2) of Table~\\ref{{tab:p_dist}}, estimated by sector. {cl}"))

    L.append(usub("Products"))
    L.append(fig2(A, "fig_wp1f_foreign_share_distribution", "Distribution of Export Value by Product-Level Foreign-Multinational Share", "a_dist",
                  "Share of total export value and MNE share of exporting firms, by the foreign-MNE share of each HS6 product's export value.", 0.85))
    L.append(tab2(A, "Tables", "tab_wp1f_foreign_share_distribution.tex", "Distribution of Export Value by Product-Level Foreign-Multinational Share", "a_dist_tab",
                  "Share of total export value and MNE share of exporting firms, by the foreign-MNE share of each HS6 product's export value. MNE share of exporting firms: MNE firm--destination--product--year observations over all observations in the bin."))
    L.append(tab2("agro", "Tables", "tab_wp2_sitc2.tex", "Agriculture: Exports and Multinational Shares, by SITC Division", "a_agro_sitc",
                  f"Agriculture: HS 01--24. Foreign and domestic: percent of the division's export value. HS6 products without an SITC correspondence (US\$6.0 billion a year) are excluded. {N_LEAD} {N_USD}", size=r"\footnotesize"))
    L.append(tab2(M, "Tables", "tab_wp2_hs_section.tex", "Manufacturing: Exports and Multinational Shares, by HS Section", "a_manuf_hs",
                  f"Manufacturing: HS 28--97 excluding 71. Foreign and domestic: percent of the section's export value. {N_LEAD} {N_USD}", size=r"\footnotesize"))
    L.append(tab2(M, "Tables", "tab_wp2_bec_enduse.tex", "Manufacturing: Exports and Multinational Shares, by End Use", "a_manuf_bec",
                  f"End use from BEC Rev.\\,4. Foreign and domestic: percent of the category's export value. {N_LEAD} {N_USD}", size=r"\footnotesize"))
    L.append(tab2(MI, "Tables", "tab_wp2_bec_enduse.tex", "Mining and Fuels: Exports and Multinational Shares, by End Use", "a_mining_bec",
                  f"Mining and fuels: HS 25--27 and 71. End use from BEC Rev.\\,4. Foreign and domestic: percent of the category's export value. {N_LEAD} {N_USD}", size=r"\footnotesize"))

    L.append(r"\end{document}" + "\n")
    return write_main(L)


def build_paper_agro() -> Path:
    """The agriculture-only companion (HS 01--24, nine origins pooled), with the exhibit
    conventions of WP_draft2. No United States section and no US-specific exhibits."""
    G = "agro"
    L = [paper_preamble("Multinational Firms and Agricultural Trade in Latin America",
                        "Ownership and Exports in Agriculture",
                        AGRO_ABSTRACT, AGRO_KEYWORDS, AGRO_JEL)]
    cl = n_cl()
    sh = r"Shares of agricultural export value (HS 01--24), all available years pooled."

    L.append(sec("Introduction", "intro")); L.append(par(AGRO_INTRO))
    L.append(sec("Related Literature", "lit")); L.append(par(PAGE_LIT_AGRO))

    L.append(sec("Data", "data"))
    L.append(par(data_section(agro=True)))
    L.append(par(AGRO_SAMPLE_TEXT))
    L.append(tab2(G, "Tables", "tab_paper_sample.tex", "Agricultural Sample Coverage, by Exporting Country", "p_sample",
                  f"Agricultural exports: HS 01--24. Exporters are distinct tax identifiers within each country; matched exporters are those found in Orbis or Dun \\& Bradstreet. Records are firm--destination--HS6--year observations. {N_USD}", size=r"\footnotesize"))
    L.append(tab2(G, "Tables", "tab_paper_sample_counts.tex", "Agricultural Sample Summary", "p_counts",
                  "Agricultural exports of the nine countries, all available years pooled. Shares are percent of agricultural export value."))

    L.append(sec("Stylized Facts in Agriculture", "facts"))

    L.append(sub("Fact 1: Multinationals Account for a Large Share of Agricultural Exports"))
    L.append(par(AGRO_FACT_TEXT[1]))
    L.append(fig2(G, "fig_wp0_fig1_origin", "Multinational Share of Agricultural Export Value, by Exporting Country", "p_f1",
                  f"{sh} The figure at the end of each bar is the total MNE share.", 0.8))

    L.append(sub("Fact 2: Product Sophistication Does Not Sort Owners in Agriculture"))
    L.append(par(AGRO_FACT_TEXT[2]))
    L.append(panel_fig2([(G, "fig_wp0_fig2_pci", "Product Complexity Index quintile"), (G, "fig_wp0_fig3_lall", "Lall (2000) technology class")],
                        "Multinational Share of Agricultural Export Value, by Product Sophistication", "p_f2f3",
                        f"{sh} Panel A: {N_PCI} Panel B: {N_LALL}"))
    L.append(tab2(G, "Tables", "tab_wp1b_rauch.tex", "Multinational Share of Agricultural Export Value, by Rauch Product Class", "p_rauch",
                  f"{sh} {N_RAUCH} {N_USD}"))
    L.append(fig2(G, "fig_wp1b_rauch", "Multinational Share of Agricultural Export Value, by Rauch Product Class", "p_rauch_fig",
                  f"{sh} {N_RAUCH}", 0.7))
    L.append(tab2(G, "Tables", "tab_wp1b_bec.tex", "Multinational Share of Agricultural Export Value, by End Use", "p_bec",
                  f"{sh} End use from BEC Rev.\\,4; HS6 products without a BEC correspondence are excluded. {N_USD}"))
    L.append(tab2(G, "Regressions", "reg_wp1b_odpy_measures.tex", "Product Sophistication and Multinational Shares in Agriculture", "p_ladder",
                  f"{N_CELLS} Agricultural products only. Dependent variable: share of the cell's export value shipped by each type of MNE. Omitted categories: primary and resource-based products (Lall) and homogeneous products (Rauch). Robust standard errors in parentheses. {D2_STARS}", size=r"\footnotesize"))

    L.append(sub("Fact 3: Multinationals from a Small Set of Countries Dominate Exports"))
    L.append(par(AGRO_FACT_TEXT[3]))
    L.append(fig2(G, "fig_wp1a_parent_share", "Foreign-Multinational Agricultural Exports, by Parent Country", "p_f4",
                  "Percent of foreign-MNE agricultural export value, by country of the ultimate parent.", 0.78))

    L.append(sub("Fact 4: A Small Set of Large Multinational Groups Accounts for Most Exports"))
    L.append(par(AGRO_FACT_TEXT[4]))
    L.append(fig2(G, "fig_wp0_fig5_network", "Foreign-Multinational Agricultural Exports and Number of Parents, by Size of the Group's Global Network", "p_f5",
                  "Shares of foreign-MNE agricultural export value and of parents, by the number of affiliates the group has worldwide.", 0.7))

    L.append(sub("Fact 5: Multinational Presence Is Associated with Higher Exports"))
    L.append(par(AGRO_FACT_TEXT[5]))
    L.append(tab2(G, "Regressions", "reg_wp0_table1_repro.tex", "Multinational Presence and Agricultural Exports", "p_t1",
                  f"{N_CELLS} Agricultural products only. {N_DEP_T1} Intensive margin: $\\ln$ number of MNEs, cells with at least one MNE. Extensive margin: indicator for at least one MNE. {cl}"))
    L.append(tab2(G, "Regressions", "reg_wp1e_counts.tex", "Multinational Presence and Agricultural Exports: Intensive Margin, by Type of Multinational", "p_f5counts",
                  f"{N_CELLS} Agricultural products only. {N_DEP_T1} Regressors: $\\ln$ number of MNEs of each type. Columns (5)--(6) split foreign MNEs by whether the destination is the parent's country. {cl}"))

    L.append(sub("Fact 6: Distance Is a Weaker Barrier for Multinationals"))
    L.append(par(AGRO_FACT_TEXT[6]))
    L.append(tab2(G, "Regressions", "reg_wp0_table2_repro.tex", "Distance and Firm Agricultural Exports: Multinationals by Presence at the Destination", "p_t2",
                  f"{N_FIRMS} Agricultural products only. Dependent variable: $\\ln$ exports. Non-MNE firms are the omitted group. Present: the group has an affiliate in the destination or the destination is the parent's country. {cl}"))
    L.append(tab2(G, "Regressions", "reg_wp1e_distance_hq.tex", "Distance and Firm Agricultural Exports: Foreign and Domestic Multinationals", "p_dist",
                  f"{N_FIRMS} Agricultural products only. Dependent variable: $\\ln$ exports. Non-MNE firms are the omitted group. Columns (3)--(4) split foreign MNEs by whether the destination is the parent's country. {cl}"))

    L.append(sec("Product Groups within Agriculture", "sub"))
    L.append(par(AGRO_SUB_TEXT))
    L.append(tab2(G, "Tables", "tab_wp2_sitc2.tex", "Agricultural Exports and Multinational Shares, by SITC Division", "a_sitc",
                  f"Foreign and domestic: percent of the division's export value. HS6 products without an SITC correspondence (US\$6.0 billion a year) are excluded. {N_LEAD} {N_USD}", size=r"\footnotesize"))
    L.append(fig2(G, "fig_wp2_sitc2", "Multinational Share of Agricultural Export Value, by SITC Division", "a_sitc",
                  "Shares of each division's export value, all available years pooled. Divisions ordered by export value.", 0.9))
    L.append(fig2(G, "fig_wp2_inputs", "Multinational Share of Agricultural Export Value: Inputs and Other Products", "a_inputs",
                  "Shares of export value, all available years pooled. Inputs: seeds, animal feed and live animals.", 0.7))
    L.append(fig2(G, "fig_wp1f_top20_hs6_stacked", "Ownership of the Twenty Largest Agricultural Export Products", "a_hs6",
                  "Shares of each product's export value. Twenty largest agricultural HS6 products by export value.", 1.0))

    L.append(sec("Theoretical Framework", "model")); L.append(par(PAPER_TAIL["model"]))
    L.append(sec("Concluding Remarks", "concl")); L.append(par(PAPER_TAIL["concl"]))
    L.append(REFS_HEAD); L.append(par(REFS_BLOCK))

    L.append(APPENDIX_OPEN)
    L.append(sec("Additional Tables and Figures", "app"))
    L.append(usub("Fact 1"))
    L.append(tab2(G, "Tables", "tab_wp0_fig1_origin.tex", "Multinational Share of Agricultural Export Value, by Exporting Country", "ap_f1n",
                  f"Shares of each country's agricultural export value, all available years pooled. {N_USD}"))
    L.append(fig2(G, "fig_wp1a_origin_by_parent", "Multinational Share of Agricultural Export Value, by Exporting Country and Parent Country", "ap_f1_parent",
                  "Shares of each country's agricultural export value. Foreign MNEs split by country of the ultimate parent; the ten largest parent countries are shown separately.", 0.92))
    L.append(tab2(G, "Tables", "tab_wp1a_origin_by_parent.tex", "Multinational Share of Agricultural Export Value, by Exporting Country and Parent Country", "ap_f1pn",
                  f"Shares of each country's agricultural export value. Other: all remaining foreign parents. {N_USD}"))

    L.append(usub("Fact 2"))
    L.append(tab2(G, "Tables", "tab_wp1b_quintile_shares.tex", "Multinational Share of Agricultural Export Value, by Quintile of Each Sophistication Measure", "ap_quint",
                  "Shares of export value within each quintile of HS6 products. --: fewer than 30 HS6 products carry the measure.", size=r"\footnotesize"))

    L.append(usub("Fact 3"))
    L.append(tab2(G, "Tables", "tab_wp1a_parent_share.tex", "Foreign-Multinational Agricultural Exports, by Parent Country", "ap_f4n",
                  f"Percent of foreign-MNE agricultural export value, by country of the ultimate parent. {N_USD}"))
    L.append(tab2(G, "Tables", "tab_wp1c_country_rowpct.tex", "Destination of Foreign-Multinational Agricultural Exports, by Parent Country", "ap_pxd",
                  "Percent of each parent country's agricultural exports, by destination (rows add to 100). Ten largest parent countries and ten largest destinations."))
    L.append(tab2(G, "Tables", "tab_wp1c_parent_x_parentdest_rowpct.tex", "Foreign-Multinational Agricultural Exports to the Parent Countries, by Parent Country", "ap_pxp",
                  "Percent of each parent country's agricultural exports, by destination (rows add to 100). Destinations are the ten largest parent countries; the diagonal is the share shipped to the parent's own country."))
    L.append(tab2(G, "Tables", "tab_wp1c_region_rowpct.tex", "Destination of Multinational Agricultural Exports, by Parent Region", "ap_reg",
                  "Percent of each group's agricultural exports, by destination region (rows add to 100). Domestic MNEs and local firms are shown for comparison."))
    L.append(fig2(G, "fig_wp1d_heatmap_country_rowpct", "Destination of Foreign-Multinational Agricultural Exports: Fifteen Largest Parent Countries and Destinations", "ap_hm",
                  "Percent of each parent country's agricultural exports going to each destination (rows add to 100 including other destinations).", 1.0))
    L.append(fig2(G, "fig_wp1d_home_share_by_parent", "Share of Foreign-Multinational Agricultural Exports Shipped to the Parent Country", "ap_home",
                  "Percent of each parent country's agricultural exports shipped to that same country.", 0.85))

    L.append(usub("Fact 4"))
    L.append(tab2(G, "Tables", "tab_wp0_fig5_network.tex", "Foreign-Multinational Agricultural Exports and Number of Parents, by Size of the Group's Global Network", "ap_f5_tab",
                  "Number and share of parents, and share of foreign-MNE agricultural export value, by the number of affiliates the group has worldwide."))

    L.append(usub("Fact 5"))
    L.append(tab2(G, "Regressions", "reg_wp1e_extensive.tex", "Multinational Presence and Agricultural Exports: Extensive Margin, by Type of Multinational", "ap_ext",
                  f"{N_CELLS} Agricultural products only. {N_DEP_T1} Regressors: indicators for at least one MNE of each type. Columns (5)--(6) split foreign MNEs by whether the destination is the parent's country. {cl}"))
    L.append(tab2(G, "Tables", "tab_wp1e_presence_shares.tex", "Multinational Agricultural Exports by Exporting Country and Destination Type", "ap_pres",
                  f"MNE and foreign-MNE agricultural export value by country, and the split of foreign-MNE value by destination. Parent country: exports to the country of the ultimate parent. Other: all remaining destinations; in parentheses, destinations where the group has another affiliate. {N_USD}"))

    L.append(usub("Product groups"))
    L.append(tab2(G, "Tables", "tab_wp2_hs_section.tex", "Agricultural Exports and Multinational Shares, by HS Section", "ap_hssection",
                  f"Foreign and domestic: percent of the section's export value. {N_LEAD} {N_USD}", size=r"\footnotesize"))
    L.append(fig2(G, "fig_wp2_hs_section", "Multinational Share of Agricultural Export Value, by HS Section", "ap_hssection",
                  "Shares of each section's export value, all available years pooled.", 0.9))
    L.append(tab2(G, "Tables", "tab_wp2_bec_enduse.tex", "Agricultural Exports and Multinational Shares, by End Use", "ap_bec",
                  f"End use from BEC Rev.\\,4. Foreign and domestic: percent of the category's export value. {N_LEAD} {N_USD}", size=r"\footnotesize"))
    L.append(tab2(G, "Tables", "tab_wp2_inputs.tex", "Agricultural Exports and Multinational Shares: Inputs and Other Products", "ap_inputs",
                  f"Foreign and domestic: percent of the group's export value. {N_LEAD} {N_USD}", size=r"\footnotesize"))
    L.append(tab2(G, "Tables", "tab_wp2_top_inputs_hs6.tex", "Largest Agricultural Input Products", "ap_topinputs",
                  f"HS6 input products with the largest export value. Foreign and domestic: percent of the product's export value. {N_USD}", size=r"\footnotesize"))
    L.append(fig2(G, "fig_wp1f_top20_hs6_by_parent", "Ownership of the Twenty Largest Agricultural Export Products, by Parent Country", "ap_hs6_parent",
                  "Shares of each product's export value. Foreign-MNE share split by country of the ultimate parent; the unfilled part of each bar is local firms.", 1.0))
    L.append(fig2(G, "fig_wp2_origin_x_sitc2", "Foreign-Multinational Share of Agricultural Export Value, by Exporting Country and SITC Division", "ap_oxs",
                  "Percent of each division's export value in each country shipped by foreign MNEs.", 1.0))
    L.append(tab2(G, "Tables", "tab_wp2_origin_x_sitc2.tex", "Foreign-Multinational Share of Agricultural Export Value, by Exporting Country and SITC Division", "ap_oxs_tab",
                  "Percent of each division's export value in each country shipped by foreign MNEs.", size=r"\footnotesize"))
    L.append(tab2(G, "Tables", "tab_wp2_sitc2_by_parent.tex", "Foreign-Multinational Agricultural Exports by SITC Division and Parent Country", "ap_sitc_par",
                  "Shares of each division's export value, by country of the ultimate parent of foreign MNEs; domestic MNEs shown for comparison.", size=r"\footnotesize"))
    L.append(fig2(G, "fig_wp1f_foreign_share_distribution", "Distribution of Agricultural Export Value by Product-Level Foreign-Multinational Share", "ap_dist",
                  "Share of agricultural export value and MNE share of exporting firms, by the foreign-MNE share of each HS6 product's export value.", 0.85))

    L.append(r"\end{document}" + "\n")
    return write_main(L)


PAGE_LIT_AGRO = r"""
\tbw{To be written. Three strands: firm-level evidence on multinational production and trade;
multinationals in agricultural and food trade; and evidence on multinational firms in Latin
America.}
"""


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
    (r"The working sample & \\", r"Statistic & Value \\"),
    (r"Export value, pooled (\$bn)", r"Export value, all years (US\$ billion)"),
(r"& \$bn/yr & For. & Dom. & Local & Lead parent", r"& US\$bn/yr & Foreign (\%) & Domestic (\%) & Local (\%) & Leading parent"),
    (r"foreign-MNE share of export value within the cell, \%", r"foreign-MNE share of export value, \%"),
    (r" in the scope,", r","),
    (r"& Naive & Within country & Across countries", r"& Firm level & Groups within country & Groups across countries"),
    (r"OxYr + DxYr + P FE", r"Origin $\times$ year, destination $\times$ year, product FE"),
    (r"ODP + ODY FE", r"Origin $\times$ dest. $\times$ product, origin $\times$ dest. $\times$ year FE"),
    (r"All LAC exports of the line", r"All exports of the product"),
    (r"US-parent share of LAC exports of the line", r"US-parent share of exports of the product"),
    (r"US-parent exports of the line", r"US-parent exports of the product"),
    (r"LAC exports to the USA", r"Exports to the USA"),
    (r"the parent's LAC exports shipped to the parent's own country", r"the parent's exports shipped to the parent's country"),
    (r"Parent's LAC exports", r"Parent's exports"),
    (r"Affiliates per group, value-weighted mean", r"Affiliates per group, mean weighted by export value"),
    (r"[later HS revision; HS 2007 line", r"[HS 2007 line"),
    (r"\% of scope", r"\% of sector"),
    (r"Value (\$bn)", r"Value (US\$bn)"),
    (r"Lead parent", r"Leading parent"),
    (r"& \$bn/yr & For. & Domestic & Local & Leading parent", r"& US\$bn/yr & Foreign (\%) & Domestic (\%) & Local (\%) & Leading parent"),
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
                  f"Agriculture: HS 01--24. Foreign and domestic: percent of the division's export value. HS6 products without an SITC correspondence (US\$6.0 billion a year) are excluded. {lead} {usd}", size=r"\footnotesize"))
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
