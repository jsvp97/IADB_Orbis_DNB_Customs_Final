"""
wp_agro_paper_tex.py -- the script that wrote docs/overleaf_projects/WP_paperagro/main.tex (v5, 2026-10-05).
Kept for the record: main.tex is edited by hand from now on, so do NOT re-run this over a hand-edited file.
The reference list is wp_agro_paper_refs.tex (verified one by one; see docs/notes/WP_paperagro_reference_check_2026-10-05.md).
"""
from pathlib import Path

OUT = Path(r"C:\Sebas BID\Orbis_DNB_Customs_Final\docs\overleaf_projects\WP_paperagro\main.tex")
REFS = Path(__file__).with_name("wp_agro_paper_refs.tex").read_text(encoding="utf-8")

TAB = r"""% ---- Table: @CAP@
\begin{table}[H]\centering@SIZE@%
  \caption{@CAP@}%
  \label{tab:@LAB@}%
  \adjustbox{max width=\textwidth, max totalheight=0.8\textheight}{\input{tables/agro/@NAME@}}%
  \par\vspace{3pt}%
  \begin{minipage}{0.95\textwidth}\footnotesize %
  \textit{Notes:} @NOTE@\\[3pt]%
  \srcnote%
  \end{minipage}%
  \end{table}
"""
FIG = r"""% ---- Figure: @CAP@
\begin{figure}[H]\centering%
  \caption{@CAP@}%
  \label{fig:@LAB@}%
  \includegraphics[width=@W@\textwidth,height=0.8\textheight,keepaspectratio]{figures/agro/@NAME@.pdf}%
  \par\vspace{2pt}%
  \parbox{0.92\textwidth}{\footnotesize %
  \textit{Notes:} @NOTE@\\[3pt]%
  \srcnote}%
  \end{figure}
"""


def tab(name, cap, lab, note, size=r"\small"):
    return (TAB.replace("@CAP@", cap).replace("@LAB@", lab).replace("@NAME@", name)
            .replace("@NOTE@", note).replace("@SIZE@", size))


def fig(name, cap, lab, note, w="0.85"):
    return FIG.replace("@CAP@", cap).replace("@LAB@", lab).replace("@NAME@", name).replace("@NOTE@", note).replace("@W@", w)


SH = "Shares of agricultural export value (HS 01--24), 2012--2018 pooled."
USD = "Values are annual averages over 2012--2018, in US\\$ billion."
REG_ODPY = "Regression at the origin country, destination country, product and year level; agricultural products, 2012--2018."
REG_FDPY = "Regression at the firm, destination country, product and year level; agricultural products, 2012--2018."
SE = "Standard errors clustered by origin--destination pair in parentheses. *** $p<0.01$, ** $p<0.05$, * $p<0.1$."
PANELB = ("Panel B uses only the exports of non-MNE firms, so that the exports of the multinationals themselves do "
          "not enter the dependent variable.")
RAUCH = ("Rauch (1999) conservative classification: homogeneous goods are traded on organized exchanges, "
         "reference-priced goods have a price quoted in trade publications, and differentiated goods have neither.")

PRE = r"""% Multinational Firms and Agricultural Trade in Latin America -- WP_paperagro
% Version 5 (2026-10-05). Every exhibit covers 2012--2018.
% Exhibits: stylized_facts/python (WP_YEARS=2012-2018), copied here by wp_agro_refresh_overleaf.py.
% Compile with pdfLaTeX. Each figure and table below starts with a '% ----' line.
\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{mathptmx}
\usepackage[margin=2.5cm]{geometry}
\usepackage{graphicx,booktabs,amsmath,amssymb,adjustbox,float,caption,hyperref,xcolor,enumitem}
\captionsetup{font=small,skip=4pt}
\captionsetup[figure]{position=top}
\hypersetup{colorlinks,linkcolor=blue!50!black,urlcolor=blue!50!black,citecolor=blue!50!black}
\setlength{\parskip}{3pt}
\newcommand{\srcnote}{\textit{Source:} Authors' calculations based on customs data matched to Orbis and Dun \& Bradstreet.}
\title{Multinational Firms and Agricultural Trade in Latin America}
\author{Ignacio Marra de Arti\~nano\thanks{Universit\'e Libre de Bruxelles (ECARES).}
 \and Gabriel Scattolo\thanks{Inter-American Development Bank.}
 \and Sebasti\'an Vel\'asquez\thanks{Inter-American Development Bank.}
 \and Christian Volpe Martincus\thanks{Inter-American Development Bank and CESifo. The views and
interpretations in this paper are strictly those of the authors and should not be attributed to
the Inter-American Development Bank, its executive directors, or its member countries.}}
\date{This version: October 2026 \\[2pt] \small Preliminary draft, please do not circulate}
\begin{document}
\maketitle
\thispagestyle{empty}
\begin{abstract}\noindent
This paper looks at the role of multinational firms in the agricultural exports of Latin America.
We combine customs data on the exports of nine countries of the region over the period 2012--2018
with ownership data from Orbis and Dun \& Bradstreet. We find that affiliates of multinational
firms account for almost half of the region's agricultural exports, and that this share was
stable over the period. Most of these exports come from foreign affiliates, whose parents are
based in a small number of countries and belong to a few very large groups. Product--destination
pairs with more multinational firms have larger exports, including the exports of firms that do
not belong to a multinational group. Finally, distance raises the cost of exporting, including the
fixed costs of finding buyers and learning about far-away markets. These costs weigh less on
multinational firms, which can rely on their group's network abroad, and their exports fall less
with distance than those of local firms.
\end{abstract}
\vspace{4pt}
\noindent\textit{Keywords:} Multinational Firms, Agricultural Exports, Foreign Direct Investment, Firm-Level Data, Latin America \\
\noindent\textit{JEL codes:} F14, F23, Q17, L25
\clearpage
\tableofcontents
\clearpage
"""

INTRO = r"""
%======================================================================
\section{Introduction}\label{sec:intro}
%======================================================================
Multinational firms are at the center of international trade. About 80 percent of world trade is
linked to the international production networks of multinational firms (UNCTAD, 2013). Trade is
also concentrated in a few large firms: in a sample of 32 countries, the largest exporter accounts
for about 14 percent of non-oil exports and the five largest for about 30 percent (Freund and
Pierola, 2015). Agriculture is no exception. Four trading companies, known as the ABCD, control
over 70 percent of the global grain market (Murphy, Burch and Clapp, 2012; Clapp, 2015), and
multinational firms from developed countries lead the supplier, processing, trading and retail
stages of agricultural value chains (UNCTAD, 2009).

For Latin America this matters a great deal. Agriculture makes up 35 percent of the merchandise
exports of the nine countries we study, and more than half in Argentina, Paraguay and Uruguay.
However, we know little about who ships these exports. Customs records show what a country exports
and where, but not who owns the exporting firm. Statistics on foreign direct investment show where
capital goes, but not which firms export which products to which markets. As a result, there is
little systematic evidence on how much of the region's agricultural exports is shipped by
multinational firms, where these firms are based, and whether exports are different where they
are present.

In this paper, we address the following main questions: How large is the share of multinational
firms in the agricultural exports of Latin America? Where are the parents of these firms based,
and how concentrated is their ownership? Are exports larger, and is distance a smaller barrier,
where multinational firms are present?

To explore these questions, we build a new database that links the customs records of all the
exports of nine Latin American countries (Argentina, Chile, Colombia, Costa Rica, the Dominican
Republic, El Salvador, Paraguay, Peru and Uruguay) over the period 2012--2018 with ownership data
from Orbis and Dun \& Bradstreet. The customs data report, for each exporting firm, the value
exported of each product to each destination in each year. The ownership data tell us whether the
firm belongs to a multinational group, where the group's ultimate parent is based, and how many
affiliates the group has worldwide. Linking the two sources requires matching tens of thousands of
exporters to corporate records, which we do in four steps that combine tax identifiers, text
matching of company names, validation with a large language model and a manual review of the
largest exporters. We use the resulting database to classify every exporter as a foreign
multinational, a domestic multinational or a local firm.

Our main results can be summarized as follows. First, multinational firms account for 48 percent
of the agricultural exports of the nine countries, 39 percent through foreign affiliates and 9
percent through domestic ones, and this share stayed between 47 and 50 percent every year. Second,
the parents of foreign affiliates are based in a few countries. The United States accounts for 25
percent of the exports of foreign affiliates and the Netherlands for 10 percent, while groups whose
parent is recorded in Switzerland, Liechtenstein and other tax havens account for 29 percent.
Third, a few very large groups dominate: groups with more than 100 affiliates worldwide are 13
percent of all parents but ship half of the exports of foreign affiliates. Fourth,
product--destination pairs with more multinational firms export more, and so do the firms that do
not belong to a multinational group in those pairs. Fifth, distance reduces the exports of
multinational firms less than those of local firms, especially when the group has an affiliate in
the destination country. These results are correlations and do not, by themselves, show that
multinational firms cause higher exports.

Our study contributes to three strands of the literature. First, a large body of work studies how
firms take part in international trade and why some of them become multinationals (see, e.g.,
Helpman, Melitz and Yeaple, 2004; Antr\`as and Yeaple, 2014; Bernard et al., 2018). This work shows
that the most productive firms invest abroad, that a few large firms account for most trade, and
that much multinational activity does not involve shipping goods within the group: in US
multinationals, the median affiliate ships nothing to the rest of its group (Ramondo, Rappoport and
Ruhl, 2016). Most of this evidence comes from manufacturing and from high-income countries. We
provide evidence on agriculture in nine Latin American countries, using customs records that cover
every exporter.

Second, we add to the work on multinational firms in agricultural value chains. This literature
shows that, in developing countries, agrifood chains have been reorganized around large
processors, traders and retailers that coordinate production with farmers through contracts and
standards (Swinnen and Maertens, 2007; Reardon et al., 2009; UNCTAD, 2009), and that a few large
trading companies handle much of world grain trade (Murphy, Burch and Clapp, 2012; Clapp, 2015).
Most of these studies focus on specific chains or companies. We measure the share of multinational
firms in all agricultural exports, by country, product and destination, and identify the countries
where their parents are based.

Third, we relate to the work on foreign direct investment and the exports of host countries. Plants
in Mexico are more likely to export when multinational exporters are nearby (Aitken, Hanson and
Harrison, 1997), and Chinese firms are more likely to start exporting a product to a country when
nearby foreign firms already export that product to that country (Mayneris and Poncet, 2015).
Foreign investment raises the productivity of domestic firms in the industries that supply
multinationals (Javorcik, 2004), domestic firms in Costa Rica that start supplying a multinational
grow and become more productive (Alfaro-Ure\~na, Manelici and Vasquez, 2022), and in Uruguay those
that start selling to a multinational are more likely to start exporting, especially to the
countries where that multinational has its headquarters or an affiliate (Carballo et al., 2021).
Our finding that firms outside multinational groups export more in the product--destination pairs
where multinationals are present is in line with this evidence. On distance, gravity equations
consistently find that trade falls with the distance between countries (Head and Mayer, 2014). Part of
this cost is fixed, such as finding buyers and setting up distribution, and fixed costs shape which
firms export to each market (Chaney, 2008); search costs also rise with distance and matter more
for differentiated goods (Rauch, 1999). Multinational firms face these costs too: the costs of
moving knowledge within the firm make the sales of affiliates fall with distance from the parent
(Keller and Yeaple, 2013), and firms often export to a market before investing there (Conconi,
Sapir and Zanardi, 2016). We look at a different margin: how distance affects the exports of
affiliates located in Latin America, and whether it matters less when the group is already present
in the destination.

Our results are also relevant for the policy discussion on how to attract foreign investment.
Investment promotion agencies help countries attract multinational firms by reducing information
barriers (Harding and Javorcik, 2011; Volpe Martincus et al., 2021). In Costa Rica, support from the
national agency raised the probability that a multinational firm opened its first affiliate in the
country (Carballo, Marra de Arti\~nano and Volpe Martincus, 2026). Our data show how important
these firms already are for agricultural exports. They also show that a large part of foreign
ownership is recorded in tax havens, in line with evidence that a large share of global foreign
direct investment and of multinational profits is booked in such jurisdictions (Damgaard, Elkjaer
and Johannesen, 2024; T{\o}rsl{\o}v, Wier and Zucman, 2023).

The remainder of this paper is organized as follows. Section~\ref{sec:data} describes the data, the
construction of the multinational database and the main features of agricultural exports.
Section~\ref{sec:results} presents the results: first who owns these exports, and then how the
presence of multinational firms relates to export performance. Section~\ref{sec:concl} concludes
and discusses policy implications.
"""

DATA = r"""
%======================================================================
\section{Data and Descriptive Statistics}\label{sec:data}
%======================================================================
\subsection{Data}\label{sec:data_data}

We rely on two main sources of data. The first one consists of export transactions from the
customs agencies of Argentina, Chile, Colombia, Costa Rica, the Dominican Republic, El Salvador,
Paraguay, Peru and Uruguay. For each export, these data report the tax identifier and name of the
exporting firm, the product, the country of destination, the year and the value in US dollars
(FOB). Products are defined at the six-digit level of the Harmonized System (2007 revision). The
data cover all the merchandise exports of each country. We use the period 2012--2018, the years in
which all nine countries are observed, and focus on agricultural products, defined as chapters 01
to 24 of the Harmonized System. These include live animals, meat, fish, dairy, vegetables, fruit,
cereals, oil seeds, fats and oils, prepared foods, beverages and tobacco.

The second source consists of ownership data from two corporate databases: Orbis, compiled by
Bureau van Dijk, and the 2025 release of Dun \& Bradstreet. Customs records do not identify who
owns the exporting firm, so we use these sources to build a new database of multinational firms,
which is one of the contributions of this paper. Its construction involves three stages, which we
describe in turn.

In the first stage, we assemble the ownership information. From the ownership links in Orbis, we
take for each company its global ultimate owner, that is, the shareholder at the top of its
ownership chain, as defined by Orbis with ownership thresholds of 25 and 50 percent. We keep one
ultimate owner per company and read the country of both the company and its owner from the Orbis
identifiers. For each company, we also keep its name, up to three national identifiers such as tax
numbers, its industry and its year of incorporation. The resulting file links about 17 million
companies to about 13 million ultimate owners. Dun \& Bradstreet provides, for each company, its
DUNS identifier, name, country, industry and starting year, together with the identifier, name and
country of its global ultimate parent.

In the second stage, we combine the two sources, since each of them covers firms that the other
misses. We match the names of the companies in Orbis with those in Dun \& Bradstreet using the
text-similarity method described below, and an artificial intelligence agent reviews each
candidate pair and decides whether both records refer to the same company. The outcome is a single
file in which every company has a global ultimate parent and a parent country, and from which we
count the number of affiliates that each parent has worldwide.

In the third stage, we link the exporters in the customs data to this combined file in four
sequential steps, each applied only to the exporters that remain unmatched after the previous one.
First, we match the tax identifier reported in customs (for instance, the RUT in Chile, the RUC in
Peru or the CUIT in Argentina) with the national identifiers reported in the corporate records.
Second, we compare the names of the remaining exporters with the names of the companies located in
the same country. To do so, we split each name into sequences of three characters and compute the
TF-IDF cosine similarity between them. Working with sequences of characters instead of whole words
handles abbreviations and differences in legal forms across sources, such as ``CORP EXPORT LTDA''
and ``Corporaci\'on Exportadora Limitada''. We retain the candidate pairs with a similarity of at
least 0.6, and a large language model, using web search when needed, assesses whether each pair
corresponds to the same company or to companies of the same group and assigns a confidence score.
Pairs whose names are identical after cleaning are accepted directly, and when several exporters
match the same corporate record we keep the pair with the highest similarity. Third, we repeat
this procedure for the exporters that are still unmatched, now comparing their names with those of
companies in all countries; a second review by the language model then resolves the cases in which
an exporter is matched to more than one record, by ranking the candidates and keeping the most
likely one. Finally, we review manually the 500 largest unmatched exporters in each country,
relying on company websites, LinkedIn and national business registries.

For matched firms whose parent country is missing, we recover it from the raw ownership links in
Orbis and an additional review with the language model. As a result, the country of the parent is
known for 89 percent of the agricultural exports of foreign affiliates. Combining the two
corporate databases proves important: about half of the matched agricultural export value
corresponds to firms found only in Orbis, a quarter to firms found only in Dun \& Bradstreet, and
the remaining quarter to firms found in both.

Exporters linked to the combined file are classified as affiliates of multinational firms (MNEs).
An affiliate is a \emph{domestic} MNE when its ultimate parent is located in the exporting country
and a \emph{foreign} MNE otherwise; matched exporters without a recorded parent country are treated
as foreign. Exporters that cannot be linked to the file are \emph{local} firms, which we also refer
to as non-MNE firms. Since the match relies on ownership links, the head company of a group that
exports from its own country cannot be identified and is counted as a local firm.

\subsection{Descriptive Statistics}\label{sec:data_desc}

The final sample comprises 30,858 agricultural exporters, 6,330 of which are multinational
affiliates. Together they export 981 products to 242 destinations, for an average of US\$78.2
billion a year, and about 13,000 firms export agricultural products in a given year. Agriculture
accounts for 35 percent of the merchandise exports of the nine countries, but its weight differs
widely across them, from 86 percent in Paraguay, 62 percent in Uruguay and 57 percent in Argentina
to between 15 and 23 percent in Colombia, Peru, El Salvador, Chile and the Dominican Republic.
Argentina alone ships 48 percent of the region's agricultural exports.

The first table describes the sample by country: the number of exporters and of multinational
affiliates, the number of products and destinations, the value exported per year, the weight of
agriculture in the country's exports and the share shipped by multinational firms (see
Table~\ref{tab:sample}).
"""
DATA += tab("tab_agp_sample", "Agricultural Exports, by Exporting Country", "sample",
            "Agricultural exports (HS 01--24), 2012--2018. Exporters are distinct tax identifiers within each "
            "country; MNE affiliates are exporters linked to Orbis or Dun \\& Bradstreet. Exports are annual "
            "averages in US\\$ billion. Agriculture in total exports: percent of the country's merchandise "
            "exports. MNE share: percent of the country's agricultural exports shipped by MNE affiliates.",
            r"\footnotesize")
DATA += r"""
The second table summarizes the sample for the nine countries together, including the number of
parent countries and multinational groups and the split of exports by type of exporter (see
Table~\ref{tab:summary}).
"""
DATA += tab("tab_agp_summary", "Agricultural Sample Summary", "summary",
            "Agricultural exports of the nine countries, 2012--2018. Exports per year are annual averages; "
            "shares by type of exporter are percent of agricultural export value. Exporters per year: average "
            "number of exporting firms in a year, summed over countries.")
DATA += r"""
Over the period, agricultural exports followed commodity prices, while the role of multinational
firms remained stable. The exports of the nine countries peaked at US\$82.5 billion in 2013, fell
to US\$73.6 billion in 2015 and recovered to US\$78.5 billion in 2018. In every year,
multinational firms shipped between 47 and 50 percent of the total, and foreign affiliates alone
between 37 and 41 percent (see Figure~\ref{fig:ap_trend} and Table~\ref{tab:ap_trend} in the
Appendix).

The geography of these exports changed more than their ownership. The region sells its agricultural
products to many markets: over 2012--2018, Latin America and the Caribbean took 27 percent of the
exports, Europe 24 percent, Asia without China 18 percent, the United States and Canada 15 percent,
China 10 percent and Africa 6 percent. Between 2012 and 2018, the share going to other Latin
American countries fell from 29 to 26 percent, while the share of the United States and Canada rose
from 13 to 16 percent and that of China from 9 to 10 percent (see Figure~\ref{fig:ap_trend_dest}
and Table~\ref{tab:ap_trend_dest} in the Appendix). Ownership also differs across markets. Foreign
affiliates ship 47 percent of the exports that go to other Latin American countries and 45 percent
of those that go to China, against 34 and 33 percent of those that go to North America and Europe
(see Figure~\ref{fig:ap_dest} in the Appendix).

The next table shows, for each destination region, its share of total agricultural exports and
the share shipped by each type of exporter (see Table~\ref{tab:dest}).
"""
DATA += tab("tab_agp_dest", "Agricultural Exports and Ownership, by Destination Region", "dest",
            "Column (1): percent of the agricultural exports of the nine countries going to each region. Columns "
            "(2)--(4): percent of the exports to each region shipped by each type of exporter. Exports are annual "
            "averages over 2012--2018, in US\\$ billion.")
DATA += r"""
Behind these aggregates are firms of very different size. Multinational affiliates are a fifth of
agricultural exporters, but they are larger and sell to more markets than local firms. Foreign
affiliates are 17 percent of exporters and ship 39 percent of the value, while local firms are 80
percent of exporters and ship 52 percent. In an average year, a foreign or a domestic affiliate
exports about US\$11.5 million, almost three times as much as a local firm (US\$4.2 million).
Affiliates also reach more destinations, 5.3 for foreign and 6.0 for domestic affiliates on
average against 3.8 for local firms, while the number of products per firm is similar in the
three groups (see Table~\ref{tab:ap_firms} in the Appendix). This is what we would expect if
belonging to a group makes it cheaper to find buyers in additional markets.

The products these firms export are concentrated in a few groups. Animal feed (US\$14.1 billion a
year, mostly soybean meal), vegetables and fruit (10.4), cereals (10.3), oil seeds (7.1) and
vegetable oils (5.8) are the largest, and soybean meal, soybeans and crude soybean oil alone amount
to US\$21.8 billion a year, 28 percent of the total (see Table~\ref{tab:ap_sitc} and
Figure~\ref{fig:ap_hs6} in the Appendix). Foreign ownership varies across these groups. The
foreign share is highest in miscellaneous food products (71 percent), oil seeds (61 percent),
tobacco (55 percent) and cereals (48 percent), and lowest in sugar (21 percent) and in coffee,
beverages and dairy (about 30 percent each), while domestic multinationals are most present in
dairy (23 percent), sugar (18 percent) and coffee (16 percent) (see Figure~\ref{fig:ap_sitc}). The
leading parent countries also change from one group to another: US groups lead in oil seeds (54
percent of the exports of foreign affiliates) and cereals (33 percent), Swiss and Liechtenstein
groups in animal feed (28 and 19 percent), German groups in coffee (42 percent), Saudi and
Brazilian groups in meat, and Spanish groups in fish and in vegetables and fruit. Agricultural
inputs (seeds, animal feed and live animals) and the remaining agricultural products have similar
foreign shares, 36 and 40 percent (see Table~\ref{tab:ap_inputs}). Other breakdowns, by section of
the Harmonized System, by end use, by exporting country and by parent country, are reported in the
Appendix (Tables~\ref{tab:ap_topinputs} to \ref{tab:ap_sitc_par} and Figures~\ref{fig:ap_inputs}
to \ref{fig:ap_dist}).

Finally, the presence of multinationals does not follow a clear pattern with product
sophistication. The foreign share rises and falls across groups of products ranked by the Product
Complexity Index, and it is similar for differentiated goods and for goods traded on organized
exchanges (43 and 41 percent). By end use, it is 42 percent for intermediate goods and 36 percent
for consumer goods (see Appendix~\ref{sec:ap_soph}).
"""

RES = r"""
%======================================================================
\section{Results}\label{sec:results}
%======================================================================
\subsection{Who Owns Agricultural Exports}\label{sec:owners}

\subsubsection{Multinationals Ship Almost Half of Agricultural Exports}

Multinational firms ship 48 percent of the agricultural exports of the nine countries, 39 percent
through foreign affiliates and 9 percent through domestic ones (see Figure~\ref{fig:f1}). The share
is highest in Paraguay (66 percent) and Uruguay (63 percent), the two countries where agriculture
weighs most in exports, and lowest in Peru (38 percent) and El Salvador (30 percent). Foreign
affiliates ship more than domestic ones in every country. The gap is smallest in Chile (30 against
18 percent) and Colombia (28 against 15 percent), where domestic groups are larger.

The next figure shows the share of each country's agricultural exports shipped by foreign and
domestic multinationals. The last bar, LAC9, is the nine countries together (see
Figure~\ref{fig:f1}).
"""
RES += fig("fig_agp_origin_lac9", "Multinational Share of Agricultural Exports, by Exporting Country", "f1",
           SH + " LAC9: the nine countries together. The number at the end of each bar is the total MNE share.", "0.8")
RES += r"""
\subsubsection{Parents Are Based in a Few Countries}

The parents of foreign affiliates are based in a few countries, and more than a quarter of foreign
ownership is recorded in tax havens. Among the countries that are not tax havens, the United States
accounts for 25 percent of the exports of foreign affiliates and the Netherlands for 10 percent; no
other country reaches 5 percent (see Figure~\ref{fig:parents}, Panel A). Tax havens and similar
jurisdictions account for 29 percent together, led by Switzerland (11 percent), Liechtenstein (8
percent), Luxembourg (3 percent) and Panama (2 percent) (Panel B). Almost all of the Swiss and
Liechtenstein shares come from exporters in Argentina. Groups often hold their foreign affiliates
through companies in these jurisdictions, so the recorded parent country does not always show
where the group's activity is (Damgaard, Elkjaer and Johannesen, 2024). Where the exports of each
parent country go is shown in Tables~\ref{tab:ap_pxd} and~\ref{tab:ap_pxp} in the Appendix.

The next figure ranks parent countries by their share of the agricultural exports of foreign
affiliates. Panel A shows countries that are not tax havens and Panel B shows tax havens (see
Figure~\ref{fig:parents}).
"""
RES += fig("fig_agp_parent_panels", "Foreign-Multinational Agricultural Exports, by Parent Country", "parents",
           "Percent of the agricultural exports of foreign MNEs with a recorded parent country (89 percent of the "
           "total), by country of the ultimate parent, 2012--2018. The ten largest in each panel. Panel A: parent "
           "countries that are not tax havens. Panel B: tax havens and conduit jurisdictions (Switzerland, "
           "Liechtenstein, Luxembourg, Panama, Ireland, Singapore, the United Arab Emirates, small island economies "
           "and dependent territories such as Bermuda, the Cayman Islands and Hong Kong).", "0.8")
RES += r"""
\subsubsection{A Few Large Groups Ship Most Foreign-Affiliate Exports}

Most of the exports of foreign affiliates come from groups with very large networks. In
agriculture, 44 percent of parents have only one affiliate in the world, but the 13 percent with
more than 100 affiliates ship half of the exports of foreign affiliates (see
Figure~\ref{fig:network}). Groups with 11 to 100 affiliates ship another 30 percent, so groups with
more than ten affiliates account for 80 percent of the total. Large networks can give these groups
buyers, logistics and information in many countries at once, which may help explain why so much of
the trade goes through them.

The next figure groups parents by the number of affiliates they have worldwide. For each size
group, it shows the share of parents and the share of the exports of foreign affiliates (see
Figure~\ref{fig:network}).
"""
RES += fig("fig_wp0_fig5_network",
           "Foreign-Multinational Agricultural Exports and Number of Parents, by Size of the Group's Global Network",
           "network", "Shares of foreign-MNE agricultural export value and of parents, by the number of affiliates "
           "the group has worldwide, 2012--2018.", "0.7")
RES += r"""
\subsection{Multinationals and Export Performance}\label{sec:perf}

\subsubsection{Multinational Presence}

There are several reasons why exports could be larger where multinational firms are present. Their
affiliates bring buyers, distribution networks and knowledge of foreign standards. Other firms can
learn from them which products sell in which markets, use the same logistics, or sell to them as
suppliers. To see whether exports are larger where more multinational firms are present, we
estimate a regression at the origin country ($o$), destination country ($d$), product ($p$) and
year ($y$) level:
\begin{equation}\label{eq:presence}
\ln X_{odpy} = \beta \ln N_{odpy} + \delta_{odp} + \delta_{ody} + \varepsilon_{odpy},
\end{equation}
where $X_{odpy}$ is the value of product $p$ exported from country $o$ to country $d$ in year
$y$, and $N_{odpy}$ is the number of multinational firms that export it. We first estimate this
equation using only the observations with at least one multinational firm; this is the
\emph{intensive margin}. We then replace $\ln N_{odpy}$ with a variable equal to one if at least
one multinational firm exports the product from $o$ to $d$ in year $y$; this is the
\emph{extensive margin}. In the strictest version, $\delta_{odp}$ and $\delta_{ody}$ are fixed
effects for each origin--destination--product and each origin--destination--year. They absorb,
for example, the fact that some countries export some products to some markets every year, and
changes over time in the trade costs between two countries. Other columns use fewer fixed effects.
Standard errors are clustered by origin--destination pair.

We estimate the equation twice. In Panel A, $X_{odpy}$ is total exports. Total exports include the
exports of the multinationals themselves, so more multinationals mechanically means more exports.
In Panel B, $X_{odpy}$ is the exports of non-MNE firms only. This panel asks whether firms that do
not belong to a multinational group export more where multinationals are present. A positive
coefficient is what we would expect if multinationals help other firms, for example through
information about buyers, shared logistics or supplier links (Aitken, Hanson and Harrison, 1997;
Mayneris and Poncet, 2015; Carballo et al., 2021). A negative coefficient would point instead to
multinationals taking the place of other exporters. The regression describes correlations; it does
not separate the effect of multinational firms from their choice of where to operate.

Exports are larger where more multinational firms are present, and so are the exports of non-MNE
firms. With the strictest fixed effects, a 10 percent increase in the number of multinationals that
export a product from a country to a destination in a given year is associated with about 8 percent
higher exports, and having at least one multinational is associated with exports about 90 percent
higher (see Table~\ref{tab:t1}, column 3 of each margin). Non-MNE firms also export more where
multinationals are present: the elasticity is 0.37, and their exports are 27 percent higher when at
least one multinational is present (Panel B). The positive association for non-MNE firms suggests
that multinationals tend to help other exporters rather than take their place.

The next table reports the estimates of equation~(\ref{eq:presence}). Panel A uses total exports
and Panel B the exports of non-MNE firms only. The first three columns give the intensive margin
and the last three the extensive margin, each with three sets of fixed effects (see
Table~\ref{tab:t1}).
"""
RES += tab("reg_wp0_table1_repro", "Multinational Presence and Agricultural Exports", "t1",
           REG_ODPY + " Dependent variable: $\\ln$ exports (Panel A) and $\\ln$ exports of non-MNE firms (Panel B). "
           "Intensive margin: $\\ln$ number of MNEs, observations with at least one MNE. Extensive margin: indicator "
           "for at least one MNE. " + PANELB + " " + SE)
RES += r"""
We then split multinationals by type, in two ways (see Table~\ref{tab:ap_counts} in the Appendix).

\emph{Foreign and domestic multinationals.} The association is stronger for foreign multinationals
than for domestic ones. With the strictest fixed effects, a 10 percent increase in the number of
foreign affiliates is associated with about 4.6 percent higher exports, against 2.4 percent for
domestic affiliates (column 4, Panel A). The same holds for the exports of non-MNE firms, with
elasticities of 0.34 for foreign and 0.24 for domestic affiliates (column 4, Panel B). Foreign
groups usually have larger networks abroad, so their affiliates can reach more buyers and bring
more information about foreign markets than domestic groups.

\emph{Foreign multinationals, by destination.} We then split foreign affiliates by whether the
destination is the country of their parent. The association is stronger for foreign affiliates
that export to other countries than for those that ship to the parent's country: with the
strictest fixed effects, the elasticity is 0.37 for other destinations and 0.24 for the parent's
country (column 6, Panel A), and 0.49 against 0.35 for the exports of non-MNE firms (column 6, Panel
B). This is in line with the idea that many affiliates in the region are set up to serve third
markets rather than to ship back to their parent, what the literature calls export-platform
investment (Ekholm, Forslid and Markusen, 2007), and with evidence that most affiliates ship little
or nothing to the rest of their group (Ramondo, Rappoport and Ruhl, 2016). Only 4.5 percent of the
agricultural exports of foreign affiliates go to the parent's country (see
Table~\ref{tab:ap_pres}). These estimates use fewer observations, because they need at least one
affiliate of each type in the same origin--destination--product--year, so they are less precise.

\subsubsection{Distance}

Distance raises the cost of exporting. Transport costs rise with distance, and so do the fixed costs
of finding buyers, learning about demand and enforcing contracts in markets that are far away
(Rauch, 1999; Chaney, 2008; Head and Mayer, 2014). Multinational affiliates can lower these costs
through their connection with the headquarters and with other affiliates of the group, which
already know buyers and conditions in many markets. We therefore expect the exports of
multinationals to fall less with distance than those of local firms, especially in countries where
the group is present. To test this, we estimate a regression at the firm ($f$), destination
country ($d$), product ($p$) and year ($y$) level:
\begin{equation}\label{eq:dist}
\ln x_{fodpy} = \alpha \ln D_{od} + \gamma \left(M_{f} \times \ln D_{od}\right) + \delta_{oy} + \delta_{dy} + \delta_{p} + u_{fodpy},
\end{equation}
where $x_{fodpy}$ is the value of product $p$ exported by firm $f$, located in country $o$, to
country $d$ in year $y$. The subscript $o$ is written for clarity: each firm exports from a single
country, so the firm identifies the origin. $D_{od}$ is the distance between the two countries, from
the CEPII gravity database, and $M_f$ equals one if the firm is a multinational affiliate. The
coefficient $\alpha$ measures how exports fall with distance for local firms, and $\gamma$ shows
how much smaller this effect is for multinationals. The fixed effects $\delta_{oy}$, $\delta_{dy}$
and $\delta_p$ absorb changes over time in each origin and each destination and differences across
products; other columns use origin, destination and year fixed effects instead. We also split
multinationals by whether the group is present in the destination (it has an affiliate there, or
the destination is the parent's country) and into foreign and domestic multinationals. Standard
errors are clustered by origin--destination pair. As before, the regression describes correlations.

Distance reduces the agricultural exports of multinational firms less than those of local firms.
For a local firm, exports fall by about 0.21 to 0.22 percent for each 1 percent of distance (see
Table~\ref{tab:t2}). This effect is about 15 percent smaller for multinationals and about 40
percent smaller when the group has an affiliate in the destination or the destination is the
parent's country (columns 3 and 4). The larger gap where the group is present fits the idea that
the group's own presence in the market is what lowers the cost of reaching it.

The next table reports the estimates of equation~(\ref{eq:dist}). Columns 1 and 2 compare all
multinationals with local firms. Columns 3 and 4 split multinationals by whether the group is
present in the destination (see Table~\ref{tab:t2}).
"""
RES += tab("reg_wp0_table2_repro", "Distance and Firm Agricultural Exports: Multinationals by Presence at the Destination",
           "t2", REG_FDPY + " Dependent variable: $\\ln$ exports. Local (non-MNE) firms are the omitted group. Present: "
           "the group has an affiliate in the destination or the destination is the parent's country. " + SE)
RES += r"""
We also split multinationals into foreign and domestic affiliates (see Table~\ref{tab:ap_dist} in
the Appendix). Distance reduces the exports of foreign affiliates about 17 percent less than those
of local firms (an interaction of 0.038, against a base effect of $-0.21$), and those of domestic
affiliates about 9 percent less (an interaction of 0.020) (columns 1 and 2). Foreign groups
usually have more affiliates and contacts abroad than domestic ones, which can explain the larger
gap. When foreign affiliates are split by destination, the gap is largest for exports to the
parent's country (0.065) and smaller for exports to other countries (0.037) (columns 3 and 4). When
an affiliate ships to its parent's country, the group itself is the link with buyers there, which
makes distance matter less.
"""

CONCL = r"""
%======================================================================
\section{Conclusion}\label{sec:concl}
%======================================================================
In this paper, we combine customs data from nine Latin American countries with ownership data from
Orbis and Dun \& Bradstreet to study the role of multinational firms in the region's agricultural
exports over 2012--2018. Multinational firms ship almost half of these exports, 39 percent
through foreign affiliates and 9 percent through domestic ones. This share stayed between 47 and
50 percent every year, while export values went up and down with commodity prices. It is highest
in Paraguay and Uruguay and lowest in Peru and El Salvador. Multinational affiliates are only a
fifth of agricultural exporters, but they export almost three times as much as local firms and
reach more markets.

Ownership is concentrated. A few parent countries, led by the United States and the Netherlands,
and a small number of groups with more than 100 affiliates worldwide account for most of the
exports of foreign affiliates, and more than a quarter of these exports belongs to groups whose
parent is recorded in a tax haven. Exports are larger where more multinational firms are present,
and the same holds for the exports of firms outside multinational groups. Distance is also a
smaller barrier for the exports of multinational firms, especially when the group already has an
affiliate in the destination country, which is consistent with group networks lowering the fixed
costs of reaching far-away markets.

These results suggest three implications for policy, considering that they describe correlations
instead of causal effects. First, foreign investment and agricultural exports are closely linked
in the region, so policies that attract foreign investment are also export policies. Investment
promotion agencies can help countries attract multinational firms, mainly by reducing information
barriers (Harding and Javorcik, 2011; Volpe Martincus et al., 2021; Carballo, Marra de Arti\~nano
and Volpe Martincus, 2026). Second, local firms ship half of agricultural exports but are smaller
and reach fewer markets. Programs that help them sell to multinational firms could extend the
benefits of foreign presence: local firms that start supplying a multinational grow
(Alfaro-Ure\~na, Manelici and Vasquez, 2022) and are more likely to start exporting (Carballo et
al., 2021). Export promotion can also help them reach new markets and products (Volpe Martincus
and Carballo, 2008). Third, because a few large groups and several tax havens account for a large
part of agricultural exports, governments need better information on who ultimately owns their
exporters. Registries of beneficial owners and the exchange of information between tax, customs
and competition authorities would make it easier to follow these firms and their trade.

\section*{References}\addcontentsline{toc}{section}{References}\label{sec:refs}
"""

APP = r"""
\clearpage
\appendix
\setcounter{figure}{0}\renewcommand{\thefigure}{A.\arabic{figure}}
\setcounter{table}{0}\renewcommand{\thetable}{A.\arabic{table}}
\renewcommand{\thesubsection}{A.\arabic{subsection}}
\section*{Appendix}\addcontentsline{toc}{section}{Appendix}\label{sec:app}

\subsection{Descriptive Statistics}
"""
APP += fig("fig_agp_trend", "Agricultural Exports by Type of Exporter, 2012--2018", "ap_trend",
           "Agricultural exports (HS 01--24) of the nine countries. Bars: exports by type of exporter, in current "
           "US\\$ billion. Line: share of MNE affiliates in the total (right axis).")
APP += tab("tab_agp_trend", "Agricultural Exports by Type of Exporter, 2012--2018", "ap_trend",
           "Agricultural exports of the nine countries, in current US\\$ billion, and percent shipped by each type of "
           "exporter.")
APP += fig("fig_agp_trend_dest", "Destination of Agricultural Exports, 2012--2018", "ap_trend_dest",
           "Shares of the agricultural exports of the nine countries, by destination region. China includes Hong Kong "
           "and Macao. Europe includes countries outside the European Union; Rest of Asia includes the Middle East.")
APP += tab("tab_agp_trend_dest", "Destination of Agricultural Exports, 2012--2018", "ap_trend_dest",
           "Percent of the agricultural exports of the nine countries going to each destination region (rows add to "
           "100).", r"\footnotesize")
APP += fig("fig_agp_dest", "Multinational Share of Agricultural Exports, by Destination Region", "ap_dest",
           "Shares of the agricultural exports going to each region, by type of exporter, 2012--2018 pooled. In "
           "parentheses, the region's share of total agricultural exports.")
APP += tab("tab_agp_firms", "Agricultural Exporters, by Type of Owner", "ap_firms",
           "Agricultural exporters of the nine countries, 2012--2018. Exporters are distinct tax identifiers within "
           "each country. Exports, products and destinations are computed for each firm and year and then averaged "
           "over all firm-years.")
APP += tab("tab_wp2_sitc2", "Agricultural Exports and Multinational Shares, by Product Group", "ap_sitc",
           "Agricultural exports by SITC Rev.\\,3 division, 2012--2018. Foreign and domestic: percent of the "
           "division's export value. Leading parents: the three largest parent countries and their share of the "
           "division's foreign-MNE exports. " + USD + " Products without an SITC correspondence (US\\$6.0 billion a "
           "year) are excluded.", r"\footnotesize")
APP += fig("fig_wp1f_top20_hs6_stacked", "Ownership of the Twenty Largest Agricultural Export Products", "ap_hs6",
           "Shares of each product's export value, by type of exporter, 2012--2018. The twenty largest agricultural "
           "products by export value.", "1.0")
APP += fig("fig_wp2_sitc2", "Multinational Share of Agricultural Exports, by Product Group", "ap_sitc",
           "Shares of each SITC Rev.\\,3 division's export value, 2012--2018 pooled. Divisions ordered by export "
           "value.", "0.9")
APP += tab("tab_wp2_inputs", "Agricultural Exports and Multinational Shares: Inputs and Other Products", "ap_inputs",
           "Inputs: seeds, animal feed and live animals. Foreign and domestic: percent of the group's export value, "
           "2012--2018. Leading parents: the three largest parent countries and their share of the group's "
           "foreign-MNE exports. " + USD, r"\footnotesize")
APP += fig("fig_wp2_inputs", "Multinational Share of Agricultural Exports: Inputs and Other Products", "ap_inputs",
           "Shares of export value, 2012--2018 pooled. Inputs: seeds, animal feed and live animals.", "0.7")
APP += tab("tab_wp2_top_inputs_hs6", "Largest Agricultural Input Products", "ap_topinputs",
           "Input products with the largest export value, 2012--2018. Foreign and domestic: percent of the product's "
           "export value. " + USD, r"\footnotesize")
APP += tab("tab_wp2_hs_section", "Agricultural Exports and Multinational Shares, by HS Section", "ap_hssection",
           "Foreign and domestic: percent of the section's export value, 2012--2018. Leading parents: the three "
           "largest parent countries and their share of the section's foreign-MNE exports. " + USD, r"\footnotesize")
APP += fig("fig_wp2_hs_section", "Multinational Share of Agricultural Exports, by HS Section", "ap_hssection",
           "Shares of each section's export value, 2012--2018 pooled.", "0.9")
APP += tab("tab_wp2_bec_enduse", "Agricultural Exports and Multinational Shares, by End Use", "ap_bec",
           "End use from BEC Rev.\\,4, 2012--2018. Foreign and domestic: percent of the category's export value. "
           "Leading parents: the three largest parent countries and their share of the category's foreign-MNE "
           "exports. " + USD, r"\footnotesize")
APP += fig("fig_wp1f_top20_hs6_by_parent", "Ownership of the Twenty Largest Agricultural Export Products, by Parent Country",
           "ap_hs6_parent", "Shares of each product's export value, 2012--2018. Foreign-MNE share split by country of "
           "the ultimate parent; the unfilled part of each bar is local firms.", "1.0")
APP += fig("fig_wp2_origin_x_sitc2", "Foreign-Multinational Share of Agricultural Exports, by Exporting Country and Product Group",
           "ap_oxs", "Percent of each SITC division's export value in each country shipped by foreign MNEs, 2012--2018.",
           "1.0")
APP += tab("tab_wp2_origin_x_sitc2", "Agricultural Exports and Foreign-Multinational Shares, by Exporting Country and Product Group",
           "ap_oxs_tab", "Panel A: composition of each country's agricultural exports by SITC Rev.\\,3 division. Panel "
           "B: percent of each division's exports in each country shipped by foreign MNEs. 2012--2018.", r"\footnotesize")
APP += tab("tab_wp2_sitc2_by_parent", "Foreign-Multinational Agricultural Exports by Product Group and Parent Country",
           "ap_sitc_par", "Shares of each SITC division's export value, by country of the ultimate parent of foreign "
           "MNEs, 2012--2018; domestic MNEs shown for comparison.", r"\footnotesize")
APP += fig("fig_wp1f_foreign_share_distribution", "Distribution of Agricultural Exports by Product-Level Foreign-Multinational Share",
           "ap_dist", "Share of agricultural export value and MNE share of exporting firms, by the foreign-MNE share of "
           "each product's export value, 2012--2018.")
APP += r"""
\subsection{Ownership by Exporting Country}
"""
APP += tab("tab_wp0_fig1_origin", "Multinational Share of Agricultural Exports, by Exporting Country", "ap_f1n",
           SH + " " + USD)
APP += fig("fig_wp1a_origin_by_parent", "Multinational Share of Agricultural Exports, by Exporting Country and Parent Country",
           "ap_f1_parent", "Shares of each country's agricultural export value, 2012--2018 pooled. Foreign MNEs split "
           "by country of the ultimate parent; the ten largest parent countries are shown separately.", "0.92")
APP += tab("tab_wp1a_origin_by_parent", "Multinational Share of Agricultural Exports, by Exporting Country and Parent Country",
           "ap_f1pn", "Shares of each country's agricultural export value, 2012--2018 pooled. Other: all remaining "
           "foreign parents. " + USD)
APP += r"""
\subsection{Parent Countries and Destinations}
"""
APP += tab("tab_agp_parent_panels", "Foreign-Multinational Agricultural Exports, by Parent Country: Other Countries and Tax Havens",
           "ap_panels", "Percent of foreign-MNE agricultural export value with a recorded parent country, by country "
           "of the ultimate parent, 2012--2018. The two panels add to 100.")
APP += tab("tab_wp1a_parent_share", "Foreign-Multinational Agricultural Exports, by Parent Country", "ap_f4n",
           "Percent of foreign-MNE agricultural export value, by country of the ultimate parent, 2012--2018. " + USD)
APP += tab("tab_wp1c_country_rowpct", "Destination of Foreign-Multinational Agricultural Exports, by Parent Country",
           "ap_pxd", "Percent of each parent country's agricultural exports, by destination (rows add to 100), "
           "2012--2018. Ten largest parent countries and ten largest destinations.")
APP += tab("tab_wp1c_parent_x_parentdest_rowpct", "Foreign-Multinational Agricultural Exports to the Parent Countries, by Parent Country",
           "ap_pxp", "Percent of each parent country's agricultural exports, by destination (rows add to 100), "
           "2012--2018. Destinations are the ten largest parent countries; the diagonal is the share shipped to the "
           "parent's own country.")
APP += tab("tab_wp1c_region_rowpct", "Destination of Multinational Agricultural Exports, by Parent Region", "ap_reg",
           "Percent of each group's agricultural exports, by destination region (rows add to 100), 2012--2018. "
           "Domestic MNEs and local firms are shown for comparison.")
APP += fig("fig_wp1d_heatmap_country_rowpct",
           "Destination of Foreign-Multinational Agricultural Exports: Fifteen Largest Parent Countries and Destinations",
           "ap_hm", "Percent of each parent country's agricultural exports going to each destination, 2012--2018 (rows "
           "add to 100 including other destinations).", "1.0")
APP += fig("fig_wp1d_home_share_by_parent", "Share of Foreign-Multinational Agricultural Exports Shipped to the Parent Country",
           "ap_home", "Percent of each parent country's agricultural exports shipped to that same country, 2012--2018.")
APP += r"""
\subsection{Multinational Groups}
"""
APP += tab("tab_wp0_fig5_network",
           "Foreign-Multinational Agricultural Exports and Number of Parents, by Size of the Group's Global Network",
           "ap_f5_tab", "Number and share of parents, and share of foreign-MNE agricultural export value, by the number "
           "of affiliates the group has worldwide, 2012--2018.")
APP += r"""
\subsection{Multinationals and Export Performance: Additional Results}
"""
APP += tab("reg_wp1e_counts", "Multinational Presence and Agricultural Exports, by Type of Multinational", "ap_counts",
           REG_ODPY + " Dependent variable: $\\ln$ exports (Panel A) and $\\ln$ exports of non-MNE firms (Panel B). "
           "Regressors: $\\ln$ number of MNEs of each type. Columns (5)--(6) split foreign MNEs by whether the "
           "destination is the parent's country. " + PANELB + " " + SE)
APP += tab("reg_wp1e_extensive", "Multinational Presence and Agricultural Exports: Extensive Margin, by Type of Multinational",
           "ap_ext", REG_ODPY + " Dependent variable: $\\ln$ exports (Panel A) and $\\ln$ exports of non-MNE firms "
           "(Panel B). Regressors: indicators for at least one MNE of each type. Columns (5)--(6) split foreign MNEs by "
           "whether the destination is the parent's country. " + PANELB + " " + SE)
APP += tab("reg_wp1e_distance_hq", "Distance and Firm Agricultural Exports: Foreign and Domestic Multinationals", "ap_dist",
           REG_FDPY + " Dependent variable: $\\ln$ exports. Local (non-MNE) firms are the omitted group. Columns "
           "(3)--(4) split foreign MNEs by whether the destination is the parent's country. " + SE)
APP += tab("tab_wp1e_presence_shares", "Multinational Agricultural Exports by Exporting Country and Destination Type",
           "ap_pres", "MNE and foreign-MNE agricultural export value by country, and the split of foreign-MNE value by "
           "destination, 2012--2018. Parent country: exports to the country of the ultimate parent. Other: all "
           "remaining destinations; in parentheses, destinations where the group has another affiliate. " + USD)
APP += r"""
\subsection{Product Sophistication}\label{sec:ap_soph}

% ---- Figure: Multinational Share of Agricultural Exports, by Product Sophistication
\begin{figure}[H]\centering%
  \caption{Multinational Share of Agricultural Exports, by Product Sophistication}%
  \label{fig:ap_soph}%
  \begin{minipage}[t]{0.72\textwidth}\centering\textit{Panel A. Product Complexity Index quintile}\\[2pt]%
  \includegraphics[width=\linewidth,height=0.38\textheight,keepaspectratio]{figures/agro/fig_wp0_fig2_pci.pdf}%
  \end{minipage}\\[8pt]%
  \begin{minipage}[t]{0.72\textwidth}\centering\textit{Panel B. Lall (2000) technology class}\\[2pt]%
  \includegraphics[width=\linewidth,height=0.38\textheight,keepaspectratio]{figures/agro/fig_wp0_fig3_lall.pdf}%
  \end{minipage}%
  \par\vspace{2pt}%
  \parbox{0.92\textwidth}{\footnotesize %
  \textit{Notes:} Shares of agricultural export value, 2012--2018 pooled. Panel A: quintiles of the Product Complexity Index of Hausmann and Hidalgo (2011), which ranks products by how diverse and advanced the countries that export them are (Q1 = least complex). Panel B: technology classes of Lall (2000): primary products, resource-based manufactures, and low-, medium- and high-technology manufactures.\\[3pt]%
  \srcnote}%
  \end{figure}
"""
APP += tab("tab_wp1b_rauch", "Multinational Share of Agricultural Exports, by Rauch Product Class", "ap_rauch",
           "Shares of agricultural export value, 2012--2018 pooled. " + RAUCH + " " + USD)
APP += fig("fig_wp1b_rauch", "Multinational Share of Agricultural Exports, by Rauch Product Class", "ap_rauch",
           "Shares of agricultural export value, 2012--2018 pooled. " + RAUCH, "0.7")
APP += tab("tab_wp1b_bec", "Multinational Share of Agricultural Exports, by End Use and Number of Products", "ap_bec2",
           "Shares of agricultural export value, 2012--2018 pooled, by BEC Rev.\\,4 end use; products without a BEC "
           "correspondence are excluded. " + USD)
APP += tab("reg_wp1b_odpy_measures", "Product Sophistication and Multinational Shares in Agriculture", "ap_ladder",
           REG_ODPY + " Dependent variable: share of export value shipped by each type of MNE. Omitted categories: "
           "primary and resource-based products (Lall) and homogeneous products (Rauch). Robust standard errors in "
           "parentheses. *** $p<0.01$, ** $p<0.05$, * $p<0.1$.", r"\footnotesize")
APP += tab("tab_wp1b_quintile_shares", "Multinational Share of Agricultural Exports, by Quintile of Each Sophistication Measure",
           "ap_quint", "Shares of export value within each quintile of agricultural products, 2012--2018. --: fewer than "
           "30 products carry the measure.", r"\footnotesize")
APP += "\\end{document}\n"

OUT.write_text(PRE + INTRO + DATA + RES + CONCL + REFS + APP, encoding="utf-8")
print("written", OUT)
