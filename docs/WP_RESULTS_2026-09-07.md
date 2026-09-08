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

Foreign bar split by parent (since 2026-09-08: the five largest parents by value, then `Other foreign MNEs`
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

**Everything is already assembled in one LaTeX document:** `output/wp/overleaf_WP_extensions/`
(`main.tex` + `Graphs/`, `Tables/`, `Regressions/`), compiled locally to 95 pages
(`docs/WP_extensions_2026-09-07.pdf`) and zipped as `output/wp/overleaf_WP_extensions.zip`
(2.5 MB). To share: Overleaf → *New Project* → *Upload Project* → pick the zip → compile
(pdflatex). Sections follow Volpe's items; appendices hold the per-origin tables. It is
generated by `stylized_facts/python/wp_build_overleaf.py`, so after re-running any `wp_*`
script, re-run the builder and re-upload (or copy the changed files into the Overleaf project).

Page map of the PDF: §1 how to read (p. 3) · §2 item 1a (pp. 3–10) · §3 item 1b (11–14) ·
§4 items 1c/1d (15–25) · §5 item 1e (26–31) · §6 item 1f (32–41) · §7 item 2 (42–57) ·
appendices A–E (58–95).


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
