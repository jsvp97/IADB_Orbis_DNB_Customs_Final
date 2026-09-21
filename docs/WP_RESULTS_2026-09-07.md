# Working-paper extensions — what was built, what came out, what to watch (2026-09-07)

Everything Christian Volpe asked for (items 1a–1f and 2 of the September agenda) was
built on top of Ignacio's stylized-facts pipeline and run on the full data. This file is
the reader's guide to the results; the exhibit files are under `output/wp/` and the code
under `stylized_facts/python/wp_*.py` (map in `stylized_facts/README.md` §3b).

**Conventions (identical to the July-2026 document):** matched = `_merge_DNB_Orbis == 3`;
domestic MNE = parent in the exporting country; foreign MNE = matched − domestic (firms
with an unknown parent count as foreign); nine origins (Ecuador excluded); value-weighted;
pooled 2006–2022; navy = foreign, light gray = domestic; Times New Roman. One switch
(`wp_common.CONVENTION = "src"`) reproduces everything under the scripts-05–14 convention.

Scopes: `all` (all goods, $2,394 bn), `agro` (HS 01–24, $788 bn), `mining` (HS 25–27 + 71,
$810 bn), `manufacturing` ($795 bn), `sectors` (the four-sector comparison).

---

## 0. Three data facts that change how the document's figures read

1. **The base now has a parent country for 92 % of foreign-MNE export value.** The July
   document (Figure 4 note) says roughly half of foreign-MNE value had no recorded parent.
   The current base (built 2026-04-21) includes the parent countries recovered by script 02
   and the AI review, and Ignacio's copy predates that. Consequences, all visible in the new
   exhibits: the parent ranking is **USA 23.3 % > GBR 19.3 % > CAN 7.8 % > LIE 5.4 % > DEU 4.3 %
   > NLD 3.9 % > CHE > JPN > PAN** (document: GBR 24.7 > USA 22.5 > CAN 10.2 > NLD > DEU > JPN);
   Liechtenstein enters the top four (foundations owning ARG/CHL exporters of copper ore,
   oil-cake and cereals — a conduit jurisdiction, to be treated like PAN/CHE/NLD); and the
   **domestic-MNE share rises** where recovered parents are the origin country (COL 0.28 →
   0.39, CHL 0.02 → 0.14, ARG 0.02 → 0.07; totals unchanged: COL 0.74, DOM 0.70, CRI 0.63…).
   Fact 1's "foreign ≫ domestic" survives everywhere except Colombia (0.35 foreign incl.
   unknown vs 0.39 domestic) and is weaker in Chile. **The working paper must say which base
   it uses; every wp exhibit uses the current one.**
2. **"HQ exporters" are not identifiable.** Every one of the 5.45 M matched rows has a
   global ultimate owner different from the exporter (Orbis `subsidiarybvdid ≠ guo25`,
   D&B `dunsnumber ≠ globalultimatedunsnumber`, no name matches). The match is built from
   ownership links, so a LAC group's head company exporting from home is in the unmatched
   pool. What IS identifiable is presence *through* the HQ (the affiliate ships to the
   parent's country) versus through another affiliate — item 1e is built on that.
3. **The two match flags differ by 357 bn of export value.** Both flags = 1,411 bn; only
   the document's flag (`_merge_DNB_Orbis`) = 90 bn; only the manual-review flag
   (`_merge_final_review`, scripts 05–14) = 267 bn; neither = 819 bn. The manual top-500
   review adds 267 bn of matched value that the document does not count. Item for the WP's
   data section.

## 1a. Figures 1–4 by parent country — `fig_wp1a_*` (four scopes)

Foreign bar split by parent (since 2026-09-08 rev. 3: the ten largest parents by value in shades of navy, then `Other foreign MNEs`
which includes matched firms with no recorded parent), domestic in gray, bold total = MNE share, exactly the
document's layout.

- **By origin** (`fig_wp1a_origin_by_parent`): US parents dominate the maquila/Central-
  American origins (CRI 0.30, PRY 0.30, SLV 0.28 of ALL exports) and are minor in the
  Andean/Southern-Cone mining and agro exporters (CHL 0.03, URY 0.05, ARG 0.08, PER 0.08).
  GBR is the largest parent in CHL (0.21) and PER (0.11); CAN in DOM (0.16, gold); LIE in
  CHL (0.06) and ARG (0.05). China is ≤ 0.04 everywhere (URY 0.04 beef).
- **By PCI quintile** (`fig_wp1a_pci_by_parent`): the rising foreign share (0.46 → 0.65) is
  carried by USA (0.11 → 0.19 in Q3–Q4), DEU (0.15 in Q5) and JPN (0.15 in Q5: vehicles);
  GBR and CAN sit in Q1 (ores, metals). Domestic MNEs: 0.18 in Q1 → 0.07 in Q5.
- **By Lall category** (`fig_wp1a_lall_by_parent`): high-tech = USA 0.22; medium-tech =
  USA 0.10 + DEU 0.07 + JPN 0.05; low-tech = CAN 0.13 (gold) + USA 0.12 (apparel); primary
  = GBR 0.13 + USA 0.09 + domestic 0.18.
- **Agriculture** (`output/wp/agro/`): parents USA 23.9 %, CHE 11.0 %, NLD 9.5 %, LIE 7.6 %,
  BRA 3.8 %, ESP 3.8 %, DEU 3.5 %, SAU 3.2 % (Almarai/SALIC in ARG/BRA grain); unknown
  parent 12 %. PRY is the outlier: USA parents = 0.35 of all agro exports (soy crushers).
- **Mining & fuels**: GBR 36 %, USA 21 %, CAN 16 %, LIE 7 %. **Manufacturing**: USA 25 %,
  GBR 14 %, DEU 9 %, JPN 7 %, PAN 5 %.

## 1b. Figure 2 with other sophistication measures — `fig_wp1b_*`, `tab_wp1b_*`, `reg_wp1b_odpy_fgo`

Fontagné–Guimbard–Orefice (2022) elasticities downloaded from CEPII (ProTEE 0.1, HS6
rev. 2007; 90 % of HS6 lines, 78 % of export value). `|σ|` = absolute import-demand
elasticity, larger = more substitutable.

| Foreign-MNE share by quintile (Q1 → Q5) | Q1 | Q2 | Q3 | Q4 | Q5 |
|---|---|---|---|---|---|
| PCI (document's Figure 2, current base) | 0.46 | 0.44 | 0.56 | 0.60 | 0.65 |
| \|σ\| FGO 2022 | 0.46 | 0.38 | 0.45 | 0.34 | 0.52 |
| σ Broda–Weinstein | 0.44 | 0.40 | 0.40 | 0.48 | 0.39 |
| Upstreamness | 0.52 | 0.41 | 0.41 | 0.47 | 0.49 |
| Quality ladder | 0.49 | 0.49 | 0.65 | 0.64 | 0.43 |
| RHCI | 0.34 | 0.59 | 0.51 | 0.49 | 0.53 |

**Volpe's hypothesis (more substitutable = less complex = less foreign) is not in the data.**
(i) The elasticity measures are essentially orthogonal to complexity: corr(PCI, |σ| FGO) =
0.08, corr(PCI, σ BW) = 0.04, corr(|σ| FGO, σ BW) = 0.09 (value-weighted, 2,809 HS6).
(ii) No monotone gradient across |σ| quintiles; Q4 is a domestic-MNE quintile (0.40 —
copper cathodes, crude oil). (iii) In the Table A.4 ladder (ODPY cells, weighted, with PCI
and upstreamness as controls) |σ| FGO enters **positive** for the foreign share (+0.034 per
s.d., +0.024 with origin×dest×year FE) and negative for the domestic share (−0.042): within
markets, foreign affiliates are relatively more present in *more* substitutable products.
PCI keeps its sign and size (+0.093 / −0.065). Only PCI and RHCI (corr 0.74) sort foreign
presence monotonically. Recommendation: report FGO as a robustness measure and keep PCI as
the headline; the correlation table (`tab_wp1b_measure_corr`) makes the point in one line.
BEC end use: foreign share 0.48 intermediate, 0.41 consumption, 0.65 capital goods.

## 1c/1d. Parent × destination — `tab_wp1c_*`, `fig_wp1d_*`

Region × region (value, row %, col %), top-10 parents × top-10 destinations (same three; heat maps 15 × 15),
one row-% table per LAC origin, and rows for domestic MNEs and local exporters as the
comparison the document lacks.

- **Only 9.1 % of known-parent foreign-MNE exports go to the parent's own country** (the
  destination fact of `src/10`, reproduced on the document's convention). By parent: USA
  0.22, CAN 0.20, JPN 0.09, DEU 0.08, NLD 0.02, GBR 0.01, CHE 0.00, LIE 0.00.
- Region row %: North-American parents ship 31 % to LAC, 24 % to North America, 23 % to
  Asia; European parents 38 % to Asia (China: copper), 28 % to LAC; Asian parents 51 % to
  LAC. Domestic MNEs: 33 % North America, 27 % Asia, 26 % LAC. Local firms are spread
  evenly (27/22/22/26).
- Country heat map (`fig_wp1d_heatmap_country_rowpct`): GBR → CHN 37 %, PAN → CHN 35 %,
  LIE → CHN 25 % / JPN 19 %, JPN → BRA 45 %, DEU → BRA 32 %, NLD → BRA 27 %, USA → USA 22 %,
  CAN → CAN 20 % / CHE 13 % (gold), ESP → USA 26 %, CHL parents → USA 21 % / BRA 16 %.
  European and Panamanian parents in LAC are China-facing commodity platforms; Japanese,
  German and Dutch parents are Brazil-facing (regional manufacturing); only US and Canadian
  parents ship home in size.
- Agriculture: 5.4 % goes home; ESP 0.26 (fruit/wine), USA 0.07; Asian parents (SAU) ship
  29 % to North America and 29 % to Asia.

## 1e. Headquarters vs affiliates; MNE counts — `tab_wp1e_*`, `reg_wp1e_*`

- **Presence type (all goods):** of foreign-MNE export value, **8.4 % is shipped to the
  parent's country (presence through HQ), 40.5 % to a destination where the group has
  another affiliate, 51.1 % to destinations where the group is not present.** Origin split
  as in the brain: SLV 41 % / DOM 29 % / CRI 26 % through HQ vs PRY 2 % / PER 4 % / CHL 4 %.
  Chile and Paraguay are the affiliate-network cases (57 % and 66 % through another
  affiliate).
- **Groups vs affiliates:** at the origin×dest×HS6×year grain a group almost never exports
  through two affiliates (1.01 affiliates per group; 1 % of cells). "MNE count" at the
  market-cell level is therefore the same whether counted as firms or as groups; the
  grouping matters at the product level (document's Figure 6), not in the Fact-5 cells.
- **Fact-5 regressions with counts by presence type** (`reg_wp1e_counts`, ODPY cells with
  ≥ 1 MNE, cluster OD). Benchmark ln(# MNE firms): Panel A (all exports) 2.07 / 0.94 / 0.82
  and Panel B (non-MNE exports) 1.34 / **0.239** / 0.132 across O+D+Y+P, ODP+ODY and
  ODP+ODY+DPY FE — the middle number reproduces the document's Table 1 (0.2391) exactly.
  Split by presence type (ln(1+count), tightest ODP+ODY+DPY column): Panel A 0.55 HQ-present
  / 0.58 affiliate-present / 0.68 not present / 0.40 domestic; Panel B 0.082 / 0.070 /
  **0.135** / 0.077, all 1 %. **The positive association between MNE presence and local
  exports is strongest for foreign MNEs that have NO presence at the destination**, and is
  weakest — but still positive — for those shipping to their own HQ country. Multinationals
  present through their headquarters do not crowd local exporters out more than the others.
- **Groups vs firms** (`reg_wp1e_groups`): ln(# MNE groups) gives 0.942 / 0.240 (Panels A/B,
  ODP+ODY) against 0.941 / 0.239 for ln(# MNE firms) — identical, as the 1.01 affiliates per
  group implies. Adding ln(affiliates per group) is positive for total exports (+0.87) and
  insignificant for non-MNE exports (+0.07): a group exporting through several affiliates
  raises its own exports, not the locals'. **"MNE cantidad" can be counted either way.**
- **Agriculture** (`output/wp/agro/Regressions/`): same pattern, somewhat larger — Panel B
  ln(# MNE firms) 0.405 (ODP+ODY) / 0.357 (+DPY); by presence type (tightest column) 0.13
  HQ-present / 0.23 affiliate-present / 0.35 not present / 0.29 domestic.
- **Distance regressions with the presence split** (`reg_wp1e_distance_hq`, 5.08 M firm ×
  dest × HS6 × year rows, OxY + DxY + product FE, cluster OD). Baseline ln distance −0.185;
  attenuation: foreign MNE +0.048, domestic MNE +0.032 (the document's A.8 had +0.046 /
  +0.054 on the older base). Split: foreign present **through HQ +0.065** ≈ through another
  affiliate +0.067 > not present +0.042; domestic MNE with a group affiliate in the destination
  **+0.104**, without +0.026. Presence at the destination — through whichever entity — is
  what flattens distance; whether the local entity is the parent or a sister affiliate makes
  no difference (A.9's conclusion, now in the main table).

## 1f. HS6 products — `tab_wp1f_*`, `fig_wp1f_*`

Top-30 tables by value, by foreign value, by foreign share and by domestic share (products
≥ $500 m), with descriptions and the leading parent; top-15 per origin; top-20 stacked
figures (owner type; parent country); distribution and Lorenz.

- Top 30 HS6 = 57 % of exports. Crude oil ($209 bn) is 75 % domestic-MNE (Ecopetrol,
  ENAP, YPF) and 21 % foreign; copper ore ($206 bn) 83 % foreign (GBR 54 % of it);
  cathodes 32 % foreign / 65 % local (Codelco unmatched); gold 40 % foreign (CAN 66 %);
  soybeans 64 % foreign (USA 51 %); coal 77 % foreign (GBR/USA); trucks 85 % foreign
  (DEU/JPN); coffee 34 % foreign (DEU 40 %); T-shirts 60 % foreign, almost all US.
- 38 % of export value is in products where foreign MNEs hold more than half; 15 HS6
  products make 50 % of foreign-MNE exports (10 in agriculture).

## 2. Agriculture and the four sectors — `output/wp/sectors/`, `output/wp/agro/`

| Sector | Value $bn | Foreign | Domestic | N HS6 | Leading parents |
|---|---|---|---|---|---|
| Agriculture (HS 01–24) | 788 | 0.38 | 0.09 | 1,023 | USA .24, CHE .11, NLD .10, LIE .08, BRA .04 |
| Mining & fuels (25–27, 71) | 810 | 0.49 | 0.25 | 208 | GBR .36, USA .21, CAN .16, LIE .07 |
| Manufacturing (rest) | 795 | 0.52 | 0.08 | 4,698 | USA .25, GBR .14, DEU .09, JPN .07, PAN .05 |

**Services cannot be done with customs data** (goods only). Memo: 17.6 % of matched export
value comes from affiliates whose own NAICS is a trade/services code (wholesale, logistics,
holdings) — that is the closest the data get; a services version needs another source.

Agriculture sub-classifications (all with foreign/domestic shares, leading parents, and an
origin × sub-sector heat map):
- HS sections: I animals 0.36 foreign (14 % of agro), II vegetable products 0.42 (43 %),
  III fats & oils 0.31 (9 %), IV food/beverages/tobacco 0.37 (34 %).
- **BEC end use** (the classification the notes call "VEC"): intermediate goods 56 % of agro
  exports, foreign share 0.41; consumption goods 44 %, foreign 0.35; capital ≈ 0. Detailed
  BEC: primary food for industry (111) 0.49 foreign — the highest — vs primary food for
  households (112) 0.32; processed for households (122) 0.37.
- **Agro inputs vs output** (own flag: fertilisers, agrochemicals, seeds for sowing, animal
  feed 2301–2309, agricultural machinery, live animals; whole soybeans counted as output):
  inputs are 17.5 % of agro exports ($138 bn, dominated by soybean oil-cake and fishmeal)
  with a foreign share of 0.36 against 0.39 for food, fibres and beverages — i.e. no input
  premium; the input exporters' parents are the Swiss/Liechtenstein/US grain traders
  (CHE 0.26, LIE 0.18, USA 0.18). Top input lines: oil-cake 2304 ($97 bn), fishmeal 2301
  ($18 bn), feed preparations 2309, maize seed 100510 (0.60 foreign), vegetable seeds
  120991 (0.67 foreign).
- SITC Rev. 3 divisions, NAICS 3-digit (311 food manufacturing 57 %, 111 crops 32 %) and
  Lall (primary 0.46 foreign, resource-based agro 0.38) tables complete the set.

## 3. Exhibit index and the Overleaf project

**Everything is assembled in THREE LaTeX documents** (since rev. 3; the single 95-page
`WP_extensions` document of 2026-09-07 is superseded and parked in `output/wp/_superseded/`):
`output/wp/overleaf_WP_{total,sectors,countries}/` (each `main.tex` + `Graphs/`, `Tables/`,
`Regressions/`), compiled locally to `docs/WP_{total,sectors,countries}_<date>.pdf` and zipped as
`output/wp/overleaf_WP_{total,sectors,countries}.zip`. To share: Overleaf → *New Project* → *Upload
Project* → pick a zip → compile (pdflatex). All three are generated by
`stylized_facts/python/wp_build_overleaf.py`, so after re-running any `wp_*` script, re-run the
builder and re-upload (or copy the changed files into the Overleaf project). The section map of
each document is its table of contents (facts 1–6 → HS6 → sectors; sectors → parts I–IV; countries
→ one section per origin).


`output/wp/<scope>/Graphs|Tables|Regressions/` — every figure as pdf + png + eps, every
table as a LaTeX fragment (`\input`-ready, booktabs). Prefixes: `wp1a` (parent splits),
`wp1b` (complexity variants), `wp1c`/`wp1d` (parent × destination), `wp1e` (HQ/presence),
`wp1f` (HS6), `wp2` (sectors, agro). Origin-specific tables carry the ISO code.

## 4. How to rerun

```
"C:\Program Files\Stata18\StataMP-64.exe" /e do src\15_wp_extract_fdpy.do      # once (45 s + presence merge)
cd stylized_facts\python && python wp_run_all.py                               # ≈ 15 min + regressions (1e ≈ 1 h)
```
Caches: `data/intermediate/wp/{fdpy_base.dta|parquet, odpy_parent_cube.parquet,
hs6_classifications.parquet}` — delete to rebuild. Logs: `output/logs/wp_*.log`.

## 5. Caveats and open points

- Base version vs the July document (§0.1): the WP needs one sentence on it, and Figure 4
  must be redrawn (it is: `fig_wp1a_parent_share`, scope `all`).
- LIE, PAN, CHE, NLD as recorded parents: the non-conduit reallocation exists (`src/12`,
  first non-conduit in the chain) and should be the robustness version of 1a/1c/1d.
- Quintiles are over HS6 products unweighted (as in the document); a handful of huge
  commodity lines dominate single quintiles (Q4 of |σ| = copper cathodes + crude oil).
- Item 1e reading (ii) is a data limitation, not a finding about HQs; say so in the text.
- 1e regressions are the slow step: ODP+ODY FE ≈ 8 min per regression on 1.0 M cells, the
  full `wp1e` run ≈ 1.5 h. The DPY columns here are on the document's convention (nine
  origins, `_merge_DNB_Orbis`); `src/13` runs the same test on the scripts-05–14 convention
  (0.087 there vs 0.132 here — the manual-review matches are part of the difference).
- `080390` and a few other codes in the customs data are HS 2012 lines; descriptions were
  added by hand (`wp_common.build_classifications`).

---

## Revision 2026-09-08 (Sebastián's six requests on the first document)

1. **Parent splits use the five largest parents + "Other foreign MNEs" + "Domestic MNEs"** in every
   figure that disaggregates by home country (Figures 1–3 by parent, the HS6 top-20 by parent, the agro
   by-parent tables). Matched firms with no recorded parent are inside "Other foreign" (no more hatched
   segment). All goods: USA, GBR, CAN, LIE, DEU; agriculture: USA, CHE, NLD, LIE, BRA; mining: GBR, USA,
   CAN, LIE, ESP; manufacturing: USA, GBR, DEU, JPN, PAN. Constant `wp_common.TOP_K_FIG`.
2. **The document now follows the skeleton of the stylized-facts note.** Each of the six facts opens
   with its ORIGINAL exhibit reproduced on the current base, then the variants: Figure 1
   (`fig_wp0_fig1_origin`), Figures 2–3 (`fig_wp0_fig2_pci`, `fig_wp0_fig3_lall`), Figure 4
   (`fig_wp1a_parent_share`), Figures 5–6 (`wp0_fact4_groups.py`: `fig_wp0_fig5_network`,
   `fig_wp0_fig6_hhi`, with network size from `src/16_wp_extract_parent_network.do`), Table 1
   (`reg_wp0_table1_repro`) and Table 2 (`reg_wp0_table2_repro`). Same-data check: Table 1 reproduces
   the note to the fourth decimal (2.0823 / 2.0685 / 0.9414; Panel B 0.2391; N 1,008,472 / 1,008,185 /
   883,545), Figure 5 gives the note's 56 % of value for >100-affiliate parents (9 % of parents) and
   5 % for single-affiliate parents, and Table 2 reproduces the pooled coefficients exactly (ln distance −0.1639 / −0.1848; ln distance × MNE 0.0461 / 0.0458). Only the present/not-present split differs slightly (0.0689/0.0393 vs the note's 0.0673/0.0405) because presence here also counts the parent's own country as a destination where the group is present; the note used the affiliate-pair file alone. The base is the same; only the
   parent-country field differs (§0.1 above), which is why Figures 1–4 move.
3. **Two-way country tables are top-10 × top-10** (`TOP_TAB = 10` in wp1cd); the heat maps stay
   15 × 15 (`TOP_MAP = 15`).
4. **HS6 tables are compact**: wrapped description column, shares in percent, one line per product;
   they now fit the text width (`write_hs6_table` in wp1f).
5. **Former Table 41** (origin × BEC end use) was a bare foreign-share matrix without composition,
   totals or the sub-sectors' weights, which read as inconsistent with the neighbouring tables. All
   origin × sub-sector tables are now two-panel: Panel A composition of the origin's exports (rows sum
   to 100), Panel B foreign-MNE share within the cell, "All" column, alphabetical origins, sub-sectors
   below 1 % omitted (`origin_heatmap` in wp2).
6. **General review**: pdflatex runs with `-halt-on-error`, all cross-references resolve, bare `%`
   and unbalanced braces in fragments are fixed at the writer (`wp_common.write_tex`), the SITC codes
   now come from the WITS text concordance (leading zeros preserved), and every exhibit in the
   document is regenerated by one command (`wp_run_all.py` then `wp_build_overleaf.py`).

Fact-4 reproduction numbers (all goods): parents with >100 affiliates = 8.9 % of parents, 56.0 % of
foreign-MNE value; single-affiliate parents 48.4 % / 5.4 %; network coverage 98 % of parents and 97 %
of value. Product HHI (value-weighted mean, 5,929 HS6): 0.192 naive → 0.209 grouped within country →
0.215 across countries; MNE-intensive products (1,887 HS6, 53 % of value): 0.234 → 0.262 → 0.270;
effective exporters 12.5 → 10.4 and 8.9 → 7.4. Agriculture: 0.088 → 0.098 and 0.111 → 0.135.

---

## Revision 3 — 2026-09-08 (fifteen requests on the second document)

The single document became **three**, all generated by `wp_build_overleaf.py` (folders and zips
`output/wp/overleaf_WP_{total,sectors,countries}*`, PDFs `docs/WP_{total,sectors,countries}_<date>.pdf`, current date 2026-09-14):

- **WP_total** — all goods: the six facts, each with its original exhibit reproduced and the variants,
  the HS6 section, the four sectors at a glance, numbers appendix.
- **WP_sectors** — the same block for Agriculture, Manufacturing, Mining & fuels and **Rest** (HS 98–99,
  chapter 00 and unclassifiable codes, $6.8 bn; services are not in customs data and the memo table
  says so), each followed by the sub-classification block (HS sections, BEC end use, BEC categories,
  SITC divisions, NAICS 3-digit, Lall, agro inputs) with heat maps, two-panel origin tables and
  parent-composition tables.
- **WP_countries** — per origin: parent region × destination region, the parent × destination heat
  map, the home-share figure and the top-15 HS6 lines (all goods and each sector).

Item by item:
1. Parent splits now show the **top-10 parents + Other foreign + Domestic** (`TOP_K_FIG = 10`), in
   every figure and in the by-parent tables.
2. **Colours**: ten shades of the document's navy for the parents (rank 1 darkest), gray-blue for
   Other foreign, the document's light gray for domestic (`wp_common.BLUE_SHADES`).
3. Parent × destination heat maps exist for every sector (wp1cd runs on all five scopes).
4. **Rest** sector added (`sector4` → Agriculture / Mining & fuels / Manufacturing / Rest).
5. **Histograms** for every sophistication measure (`fig_wp1b_hist_<measure>`, panel
   `fig_wp1b_panel_hist`): export value across bins stacked by owner type, foreign share per bin,
   number of HS6 per bin. **FGO check**: the CEPII database provides ONE import-demand elasticity
   per HS6 (rev. 2007), estimated on the universe of bilateral flows of the product and common to
   all exporters and importers; it is a product characteristic, so the same |σ| for a product
   whatever its origin is the intended use — no adjustment needed or possible. Extra
   classifications: **Rauch (1999)** conservative (from the product file's `con_34`, now in
   `tab_wp1b_rauch`); **Micro-D** (Bernini, González, Hallak, Vicondoa 2018) is defined on
   Argentina's 12-digit nomenclature from package-size attributes and cannot be carried to HS6 data
   for other countries — noted in the document, not used. Others already in: Broda–Weinstein σ,
   upstreamness, quality ladder, RHCI, Lall, BEC.
6. Per-origin versions of the cell-share heat map and of the home-share figure
   (`fig_wp1d_heatmap_country_cellpct_<ISO>`, `fig_wp1d_home_share_by_parent_<ISO>`) → WP_countries.
7. Every "Agriculture" subsection now exists for Manufacturing, Mining and Rest (WP_sectors).
8. Three documents (above).
9. **No ln(1+x)**: all count regressors are plain logs; a zero count drops the cell from that column
   (sample sizes shrink accordingly in the decomposed columns and are reported).
10. The counts table has an **extensive-margin twin** (`reg_wp1e_extensive`).
11. **Decomposition order** in Facts 5 and 6: MNE → foreign / domestic → foreign through HQ /
    foreign not through HQ (+ domestic). The "through another affiliate" split is kept only as a
    memo in the presence-shares table.
12. Former Figure 35: second series is now the **MNE share of exporting firm-cells** within the
    bin's products (not the share of HS6 products).
13. **HS sections by export value** table (`tab_wp1f_hs_sections`), same structure as the HS6 tables.
14. Sub-classification tables restructured: total exports, MNE exports, % foreign, % domestic,
    leading parents (top 3) — `write_split_table` in wp2, for every sector.
15. The appendix of repeated single-measure figures was removed; each exhibit appears once per document.

Speed: all regressions now run through `wp_common.feols`, which uses pyfixest's Rust demeaner
(identical coefficients; 72 s → 1.3 s on the ODP+ODY specifications), so the whole 1e block for
five scopes runs in minutes. Regressions with fewer than 500 usable observations are left blank.


## Revision 4 — 2026-09-11 (quality pass before the coauthors read the documents)

A page-by-page audit of the three PDFs (automatic scan for overflow, unreadable font sizes and empty
pages, plus a visual check of every page) and a full re-run of the pipeline from the cached cube.

**Replicability.** `python wp_run_all.py` (23.7 min; cube cached) followed by `python wp_build_overleaf.py`
regenerates everything. Against the 2026-09-08 run: all 34 regression tables are numerically identical
and 237 of 300 table fragments are byte-identical; the remaining 63 differ only by the format changes
listed below (checked number by number). The three documents compile with zero LaTeX errors and no
overfull boxes.

**Same-data check, stated precisely.** Table 1 Panel A and every observation count match the note to the
last digit (2.0823 / 2.0685 / 0.9414; 1.4622 / 1.4591 / 0.6818); Table 2 pooled coefficients too
(−0.1639 / −0.1848; 0.0461 / 0.0458; N 5,081,547 / 5,081,360). Table 1 Panel B and the Table 2
"present / not present" split differ in the third decimal (1.3536 vs the note's 1.3522; 0.0689 vs
0.0673) because the current base carries the affiliate/parent links of the 2026-04-21 build. The
"How to read" paragraph in the documents now says exactly this (the earlier text over-claimed).

**What was wrong and how it was fixed (all in code, nothing hand-edited):**
- *Table notes stretched narrow tables.* Every fragment ended with a `\multicolumn{n}{p{0.95\textwidth}}`
  note, which forces the tabular to text width and pushed the last column to the far right (visible in
  the quintile table and in every appendix table). The builder now strips the note from the fragment
  (`split_note`) and sets it under the table in a 0.95-textwidth minipage.
- *Origin × sub-sector tables unreadable* when the classification has many categories (SITC divisions,
  NAICS, BEC categories, Lall: shrunk to 1.5–3.5 pt). `origin_table_and_heatmap` now transposes when
  there are more than six sub-sectors: sub-sectors on the rows, the nine origins on the columns (Panel A
  columns sum to 100); the heat map is transposed the same way and long labels are wrapped instead of cut.
- *Six-panel figures* (Figure 2 for six measures; the histogram panel) were 2×3 at 15 in and became
  unreadable at text width → 3×2 at 11×13 in with larger fonts.
- *Measures with almost no coverage in a sector* (quality ladder: 18 HS6 in agriculture, 26 in mining)
  produced broken quintiles and `nan` cells. New guard `MIN_HS6_MEASURE = 30`: the panel shows a
  "not shown" note, the quintile table prints `--`, and the correlation table is now **pairwise** (each
  cell on the products carrying both measures; the note reports the N range).
- *Blank HS6 descriptions* for the 992 customs codes (3.2 % of value) that are not HS 2007 lines
  (HS 2012/2017/2022 codes such as 030617 shrimps, 030441 fillets, 961900 sanitary articles; national
  lines 0025xx, 98xxxx). New `wp_common.hs6_desc_fallback`: later-revision codes are mapped to their
  HS 2007 counterpart with the UNSD HS2022→HS2007 conversion and described as "… [later HS revision;
  HS 2007 line 030613]"; national/special lines say so; last resort is the HS4 heading.
- *Stale text*: "five largest parent countries" in the appendix notes → the constant `TOP_K_FIG` (10).
- *Formats*: N HS6 as integers (per-column formats in `write_matrix_tex`); HS6 tables use two decimals
  when the scope is small (Rest); agro-inputs table in percent with full descriptions; BEC category labels
  no longer cut at 26 characters.
- *Figures*: heat-map cells narrower with 8-pt annotations (15×15 maps legible); top-20 HS6 bar charts
  taller with 9-pt labels and the legend below the axis; foreign/domestic bar charts with the legend
  under the x-label (it collided with the value labels) and darker value labels; every figure capped at
  0.86 text height.
- *Empty exhibits*: the Rest sector has no BEC-classified value, so its HS section × BEC cross tables
  (previously two empty tables) are skipped.
- *Overflow*: file paths in the intro set with `\path`/`\url` (breakable); "/" in long species lists
  gets `\allowbreak`.
- Housekeeping: the superseded single document `overleaf_WP_extensions` moved to `output/wp/_superseded/`;
  START_HERE points to the three PDFs.

Known, accepted: the manufacturing SITC two-panel table (35 divisions × 2 panels) is set at about 5 pt to
fit one page; heat maps with 30+ rows are tall but legible; regressions with fewer than 500 usable
observations stay blank (mining and rest decompositions).


## Revision 5 — 2026-09-14 (Rauch in two classes; internal review document)

- **Rauch two classes** (`tab_wp1b_rauch2`, `fig_wp1b_rauch2`; WP_total Table 4 / Figure 13 and the sector
  versions): reference-priced + homogeneous pooled as "Non-differentiated". Foreign 0.563 (differentiated) vs
  0.426 (non-differentiated), domestic 0.058 vs 0.169 in the total; manufacturing 0.599 / 0.435 and 0.049 / 0.099;
  agriculture flat (0.413 / 0.377); mining has only 40 differentiated HS6. Cleanest single exhibit for Fact 2.
- **Internal review** `docs/WP_revision_interna_2026-09-14.docx` (Spanish, text only, ~6,700 words): for every
  exhibit of the three documents a verdict (MOSTRAR / APOYO-APÉNDICE / NO MOSTRAR) with the numbers behind it;
  an opening section on which facts hold by sector; the US-parent story (22 % of US-MNE exports go to the USA,
  41 % in manufacturing; DOM 70 %, SLV 67 %, CRI 47 %; US MNEs carry 54 % / 47 % / 31 % of CRI / SLV / DOM
  manufacturing exports to the USA; apparel, medical devices, electronics); what does not work (FGO sign flips by
  sector; groups vs affiliates is a null result); data caveats; a proposed minimal set of 12 exhibits. The "who
  carries the exports to the USA" numbers were computed ad hoc from the cube for the review (scratch script
  `usa_story*.py`; not yet a pipeline exhibit — candidate new figure).
- PDFs renamed to 2026-09-14 (36 / 174 / 55 pp.).

## Revision 6 — 2026-09-18 (the destination side of Fact 3; cross-sector summaries; review renumbered)

New script `wp3_usa_destinations.py` (step `3` of `wp_run_all.py`, after `1e`; ~2 min from the cached cube).
It turns Fact 3 around — of the value that REACHES a destination, who moves it — and collects the exhibits
that compare the four sectors side by side. Everything the internal review computed ad hoc is now in the
pipeline. WP_total numbers below (2026-09-18 build, 44 pp.); the sector versions sit in each sector's Fact 3
and in the "sectors side by side" block at the start of WP_sectors (192 pp.).

- **US-parent share of exports, origin × sector** (`fig/tab_wp3_us_share_origin_sector`; Figure 4 / Table 1,
  Fact 1): CRI 30 % of all exports (42 % of manufacturing), PRY 30 % (35 % of agriculture), SLV 28 % (40 % of
  mining, 35 % of manufacturing), DOM 17 % (26 % manufacturing), COL 12 %, ARG 8 %, PER 8 %, URY 5 %, CHL 3 %;
  pooled 10 % (agriculture 8, mining 10, manufacturing 12). Replaces three sector figures for this question.
- **Home share by parent, total and by sector** (`fig/tab_wp3_home_share_by_parent_sectors`; Figure 20 /
  Table 17, Fact 3): USA 22 % (agriculture 7, mining 12.5, manufacturing 41); CAN 20 % (mining 26); BRA 19 %
  (mining 34, manufacturing 22); DEU 8 %; JPN 9 % (agriculture 33 % on $6.9bn); GBR 0.6 %, LIE 0 %, CHE 0.3 %,
  NLD 2 %, PAN 1 %; all known-parent foreign MNEs 9 % (5 / 8 / 13). Bars on < $1bn are hatched.
- **Who carries the exports to the USA** (`fig_wp3_to_usa_carriers_total_manuf`, Figure 21; Tables 18–19):
  of $440bn, US-parent MNEs 12.1 %, other foreign MNEs 23.1 %, domestic MNEs 24.4 % (Colombian oil), local
  firms 40.4 %. Manufacturing ($156bn): 24.6 / 26.6 / 6.7 / 42.1. By origin, US-parent share (all goods →
  manufacturing): SLV 40 → 47 %, CRI 37 → 54 %, DOM 25 → 31 %, CHL 6 → 7, COL 6 → 9, PRY 6 → 1, ARG 5 → 7,
  PER 4 → 6, URY 0 → 1. Agriculture to the USA: US-parent 3.9 %, local 58 %; mining: domestic 52 %.
- **Who carries the exports to the eight largest markets** (`fig/tab_wp3_dest_carriers`; Figure 22 /
  Table 20; EU-27 pooled, strict 27-member list — `W.EU_CODES` is all of Europe and must not be used for this):
  China $332bn: parent-in-destination 0.3 %, US-parent 7.3 %, other foreign 44.2 %, domestic 14.5 %; EU-27
  $316bn: EU-parent 8.3 %, US-parent 8.6 %; Brazil $196bn: 2.8 / 9.5 / 46.2; Japan $78bn: 4.0 / 11.5 / 49.3;
  Canada $61bn: CAN-parent 25.9 %; Korea $59bn: 0.1 / 8.5 / 44.1. Only the USA and Canada buy from LAC
  through their own multinationals.
- **What US-parent MNEs ship home** (`tab_wp3_us_home_products`, `fig_wp3_us_home_products`; Table 21 /
  Figure 23): top-15 HS6 by US-parent value to the USA with (i) the share of the parent's exports of the
  line that goes to the USA and (ii) the US-parent share of everything LAC exports of the line to the USA:
  T-shirts 610910 $5.9bn (84 % home; 52 % of LAC→USA), catheters 901839 $5.1bn (73 %; 83 %), crude oil
  270900 $4.9bn (24 %; 5 %), medical instruments 901890 $3.6bn (69 %; 43 %), coal 270112 (9 %; 48 %),
  integrated circuits 854231 (28 %; 95 %), tyres 401110 (93 %; 63 %), molybdenum 261390 (99 %; 79 %),
  cotton socks 611595 (100 %; 93 %), men's underpants 610711 (87 %; 86 %), brassieres 621210 (98 %; 77 %),
  pineapples (66 %; 20 %), cigars (100 %; 16 %), copper cathodes (24 %; 3 %), leather footwear (70 %; 71 %).
  All 15 lines = $53bn = 22 % of US-parent LAC exports, 12 % of LAC→USA. Companion `tab_wp3_to_usa_top_products`
  (Table 22): the 15 largest LAC→USA lines and who carries them (crude oil $92bn: 81 % domestic, 5 % US-parent;
  gold $30bn 74 % local; copper cathodes 60 % local; coffee 53 % local; bananas 58 % local).
- **Fact 5 in one table** (`tab_wp3_fact5_summary`, Table 31) and **Fact 6 in one table**
  (`tab_wp3_fact6_summary`, Table 34): four columns (all goods, agriculture, mining, manufacturing), rows
  foreign / domestic, both FE sets, Panels A and B for Fact 5. Read from the `reg_wp1e_*` fragments of each
  scope (no re-estimation), so they match the full tables to the digit: Fact 5 foreign 1.213 / 1.295 / 1.130 /
  1.164 vs domestic 0.438 / 0.523 / 0.317 (n.s.) / 0.383; Fact 6 base −0.165 / −0.214 / −0.093 (n.s.) /
  −0.151, × foreign 0.049 / 0.037 / 0.057 / 0.052, × domestic 0.032 / 0.019 / 0.071 / 0.039.
- **Renumbering.** Every WP_total number after Figure 3 / before Table 1 shifts (figures 4–18 → +1, 19–26 → +5;
  tables 1–15 → +1, 16–23 → +7, 24–25 → +8, 26–39 → +9). The internal review (edited by Sebastián on 09-18) was
  renumbered by label with `scratch/renumber_docx.py` (56 paragraphs; only exhibit numbers changed, plus the
  numbers of the new exhibits appended where the text already described them) and saved as
  `docs/WP_revision_interna_2026-09-18.docx`; the 09-14 copy is parked in `output/wp/_superseded/`.
- PDFs renamed to 2026-09-18 (44 / 192 / 55 pp.); 2026-09-14 PDFs removed from git. Zero LaTeX errors or
  overfull boxes; no text below 5 pt in the new exhibits.
- **Second pass the same day (Sebastián's request).** (i) The review keeps ONLY the renumbering — the twelve
  appended references to the new exhibits were removed; a paragraph-by-paragraph diff against Sebastián's copy
  shows differences in exhibit numbers only, plus two factual fixes verified against the cube: the non-US
  parents carrying LAC exports to China are GBR (21.8 % of the value), LIE (4.1), PAN (3.6) and CAN (3.1) — AUS
  is ninth with 1.1 %, and PAN's shipments are 58 % pulp, so "(GBR, LIE, PAN, AUS: mineras)" became "(GBR, LIE,
  PAN, CAN: minerales de cobre y hierro, cátodos de cobre y celulosa)"; and DEU / JPN / NLD ship 32 / 45 / 27 %
  to Brazil, so "32–45 %" became "27–45 %". Every other number the review cites was recomputed
  (`scratch/verify_review.py`) and matches: US-parent $238.9bn = 23.3 % of known-parent foreign value, 10.0 %
  of all; sector leaders; HS-section home shares (textiles 27 % / 76 %, instruments 19 % / 72 %); home shares by
  origin (DOM 70.0, SLV 66.6, CRI 47.1, CHL 31.2, COL 15.4, PER 8.7, ARG 3.9, PRY 0.4, URY 0.4); Table 13 rows;
  the 92–97 % of DEU / JPN / NLD exports to Brazil that leave from Argentina; CAN home share = 94 % gold;
  presence shares; Figure-1 numbers by sector; parent shares by sector; network-size and HHI numbers; PCI
  quintiles; mining = 208 HS6 (192 with a PCI, 40 Rauch-differentiated). HKG-parent exports to China are 0.00 %,
  so "Chinese parents 0.3 %" needs no Hong Kong caveat. EU-27 = strict 27-member list (checked against
  `W.EU_CODES`, which adds 27 non-EU European codes and must not be used for the EU).
- **`WP_draft`** (`python wp_build_overleaf.py draft` → `output/wp/overleaf_WP_draft/`, `docs/WP_draft_2026-09-18.pdf`,
  40 pp.): the working-paper draft for Christian — only the exhibits the review marks MOSTRAR in the main text
  (Facts 1–6, Products, Sectors with one or two sub-classification tables each) and APOYO / APÉNDICE in the
  appendix, in the review's order; clean captions; a short "Data" paragraph instead of the reading guide; the
  fragment notes lose their "reproduction of the note's Table" phrases (`DRAFT_MODE`). No table of contents,
  no "draft for internal review" date line. The draft has its own exhibit numbering (the review's numbers are
  WP_total's).

## Revision 7 — 2026-09-21 (Volpe's review of the draft: annual averages, exhibit list, new exhibits)

Christian reviewed `WP_draft_2026-09-18` with Sebastián; the list of changes is implemented across the pipeline
and the four documents (`WP_draft` 29 pp., `WP_total` 52, `WP_sectors` 215, `WP_countries` 58; all dated
2026-09-21). Full rerun (steps 0–3, 80 min from the cached cube) plus `build_classifications(force=True)`.

- **Annual averages instead of pooled sums.** Every dollar value is now the origin's pooled value divided by
  the number of years it is observed (ARG 9, CHL 14, COL 12, CRI 10, DOM 8, PER 10, PRY 9, SLV 13, URY 10 years;
  `mne_flags` adds `value_yr`, `val_total_yr`, `val_ext_yr`, `val_dom_yr`); an aggregate is the sum of its origins'
  annual averages (all goods $224.5bn/yr instead of the pooled $2,393.8bn). Shares are still computed on the
  pooled values. Headers say `\$bn/yr` (`W.VAL_HDR`), notes carry `W.VAL_NOTE`. Figures no longer print dollar
  values (home-share figures, to-USA bars, top-20 HS6, sector bars); the network-size table lost its value column.
- **BEC in three classes** (`BEC4_ENDUSE`): motor spirit (321) and goods n.e.s. (7 — HS 27 fuels in these data)
  → intermediate; passenger cars (51) → consumption. Unclassified HS6 (6.6 % of value) excluded. Foreign / domestic:
  intermediate 0.476 / 0.155, consumption 0.438 / 0.082, capital 0.647 / 0.056.
- **New exhibits.** (i) `tab/fig_wp3_us_three_shares_{total,origin}`: with the origin's total exports as the
  denominator, 18.4 % goes to the USA, 10.0 % is carried by US-parent MNEs, 2.2 % is both (by origin: SLV 38 / 28 /
  19 %, CRI 38 / 30 / 14 %, DOM 48 / 17 / 12 %, PRY 2 / 30 / 0.1 %). Replaces the origin × sector US-share exhibit in
  the draft. (ii) `fig_wp1a_pci_lall_by_oecd` (+ tables): Figures 2–3 with the foreign bar split OECD / non-OECD
  parent; the PCI gradient is entirely the OECD parents (0.36 → 0.58; non-OECD 0.10 → 0.07). (iii)
  `reg_wp1b_odpy_measures`: PCI, Lall (4 categories, base primary) and Rauch (3 classes, base homogeneous) each
  in its own regression, two FE sets, panels total / foreign / domestic (foreign: PCI +0.039, Lall high-tech +0.033,
  Rauch differentiated +0.209; domestic: −0.039, −0.062, −0.127; all 1 %). (iv) `tab_wp1c_parent_x_parentdest_rowpct`:
  top-10 parents × the same ten countries as destinations, diagonal = home share. (v)
  `fig/tab_wp1d_home_share_by_parent_consolidated`: dependencies folded into their sovereign (GBR ← BMU, CYM, VGB,
  JEY, GGY, IMN, GIB, …; NLD ← CUW, ABW, SXM; USA ← PRI, VIR; CHN ← HKG, MAC) and stand-alone havens / conduits
  (LIE, CHE, LUX, PAN, BHS, …) pooled — USA 23.8 %, CAN 19.5 %, BRA 18.6 %, GBR 0.6 %, havens 2.4 %
  (`W.HAVEN_SOVEREIGN`, `W.HAVEN_STANDALONE`, `W.consolidate_parent`). (vi) `fig_wp3_dest_carriers` redrawn with
  US-, EU-27- and CAN-parent segments (EU-27 = strict 27 members, GBR excluded), no dollar totals; table gains the
  EU / CAN columns. (vii) `tab_wp3_us_home_products` gains the three main origins of each line. (viii)
  `tab_wp3_fact5ext_summary` (extensive-margin twin of the Fact-5 summary) and clearer row / panel titles in both.
  (ix) `fig_wp3_fig1_by_sector_panels`: Figure 1 within agriculture / manufacturing / mining as one three-panel
  figure. (x) `fig_wp1b_rauch` (three classes) used as a figure in the draft.
- **Draft structure.** The 2026-09-18 order is kept; every caption starts with `[Main text]` or `[Appendix]`
  (Volpe's assignment) and the exhibits he dropped are gone: by-parent PCI/Lall figures, four-sector bars,
  origin × sector table, parent-share table, home-share-by-sector table, destination table, US-home-products
  figure, WP_countries home-share figures, region value/colpct tables, origin × dest-region tables, cell-share heat
  map, to-USA by-origin table, top LAC→USA lines, HHI figure and table, Lorenz, top-30 lists, quintile panel and
  table. `panel_fig` builds lettered panels from existing graphs (PCI + Lall).
- **Audit.** `scratch/audit_draft.py`: 96 checks recomputed from the cube against the fragments — Figure-1
  shares and annual values, four-sector totals, the three US shares and their cross-exhibit identities (col 2 =
  US share in the origin × sector table; col 3 / col 1 = US-parent share of exports to the USA = destination table
  USA row), destination shares for EU-27 / CHN / CAN summing to 100, Rauch two-class = weighted merge of three,
  BEC rows, parent shares and diagonal, consolidated home shares, HS-section totals, presence shares, US home
  products, Fact 5 / 6 summaries = full fragments, OECD + non-OECD = foreign. All passed.
- No text below 5 pt in the draft; zero overfull boxes; 2026-09-18 PDFs removed from git.

## Revision 8 — 2026-09-21, second pass (Volpe / Sebastián: consistency of every number)

- **One share engine.** `W.flow_shares(d, by, numerators, denominator)` computes every share of the US, parent
  and destination exhibits (wp3's carrier tables, the three-share table, the parent ranking on total exports)
  from the same masks and the same pooled values; a different denominator is always a different column, never a
  different figure. `wp_audit.py` (step `audit`, run last) recomputes the shared quantities from the cube and
  checks the identities that link exhibits: US-parent share of TOTAL exports 10.0 % (parent ranking on total
  exports = three-share column (2) = origin × sector 'All'); share of US-parent exports going home 22.3 %
  (parent × parent-destination diagonal = country row % USA→USA = home-share figures); (3) = (2) × 0.223 = 2.2 %;
  column (4) = (3)/(1) = US-parent share of exports TO the USA = to-USA carriers by origin / by sector = destination
  table USA row (12.1 %). All pass.
- **The three numbers Christian flagged are three denominators, now labelled as such**: 23.3 % was the US share
  of foreign-MNE value with a known parent (kept only in WP_total); the draft's parent ranking now uses total
  exports (`fig_wp1a_parent_share_total`: USA 10.0, GBR 8.3, CAN 3.4, …, other foreign 9.5, domestic 14.1; bars
  add to the MNE share 60.5 %). 22.3 % is the share of US-parent exports that goes to the USA (Table 7 diagonal,
  Figures 14 and 16 now print one decimal). SLV 40.2 / CRI 37.2 / DOM 24.7 in the to-USA figure are column (4)
  of the three-share table, added for that purpose.
- **Rauch in three classes everywhere** in the draft (`tab/fig_wp1b_rauch`, all goods and manufacturing); the
  two-class exhibits stay in WP_total / WP_sectors only.
- **Tax-haven figure as two panels** (`fig_wp1d_home_share_haven_panels`): Panel A the ten largest non-haven
  parents with dependencies folded into their sovereign (USA 23.8, CAN 19.5, BRA 18.6, ESP 12.2, CHL 9.6, JPN 8.9,
  DEU 8.3, FRA 3.1, NLD 2.2, GBR 0.6); Panel B the ten largest haven / conduit jurisdictions as recorded (LIE 0.0,
  CHE 0.3, PAN 1.4, LUX 0.1, IRL, CYM 0.2, BMU, SGP, VGB, BHS 0.0).
- Captions: bold `[Main text]` / `[Appendix]`; no "Appendix" section — every former appendix exhibit sits next to
  the exhibit it documents (Figure-1 numbers after Figure 1, etc.); no "in the cell" wording — units spelled out
  as "the product from the origin to the destination in the year". Draft 29 pp.; WP_total 54; WP_sectors 223.
