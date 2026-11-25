# Estimation specifications for round v5 of "Multinational Firms and Agricultural Trade in Latin America"

Date: 2026-11-24. Audience: the coauthor running the estimations. Starting point: the v4 delivery (`Note_v4`, `WP_paperagro_v4_master_estimates.xlsx`, 39 sheets), which is complete against the 2026-11-17 specifications and whose numbers were checked against the workbook.

**What this document contains.** The estimations, tables and figures for round v5, in four blocks: **E9** (more definitions of capital intensity and a check of the measure), **E10** (complexity and differentiation), **E11** (event studies: outcomes by step of the story, estimators, fixed effects, trends, samples, figures) and **E12** (items pending from v4). The round covers every block, variant, table and figure listed here; section 3 gives the suggested order of work.

**How it relates to the 2026-11-17 document.** Definitions are not repeated: sample, cell variables, product classifications, the FE codes FE1–FE6, clusters and output conventions are those of sections 0.1–0.5 of the 2026-11-17 document, and blocks E2, E4, E5 and E6 of that document are the templates. Where a block below says "as in E4" or "as in E5", the 2026-11-17 specification of that block applies, with the changes stated here. Where the 2026-11-17 document and `Notes` of the v4 workbook differ (HS 2017 instead of HS 2007; `high_mean` = aggregate ratio of the stage), the v4 workbook is the reference.

## 0. Rules for this round

- **Results first, text later.** Christian suggested returning to the Overleaf text once the full set of results is available and there is a clear story to tell. Until then nothing in the paper is rewritten; the text stays as in v4.
- **Report everything.** Every variant below is run and reported, including null results and results with the opposite sign to the one expected. A variant that shows no pattern is information: it tells us which cuts of the data carry the pattern and which do not.
- **One summary sheet and a set of figures per block** (`E9 map`, `E10 map`, `E11 map`; folders `figures_E9\`, `figures_E11\` with the plotted numbers in `E9 figdata` and `E11 figdata`): one row per variant with the key coefficient(s), the p-value of the relevant test, N and the FE code, so that the pattern across variants is visible without opening thirty sheets; and figures wherever a pattern can be seen rather than read (event studies, threshold ladders, coefficient against capital intensity). Full tables keep the layout of the current sheets; every estimate also goes to `Long format`.
- **Say what each cut coincides with.** For every new product grouping, add to `Classifications` the column and, in the block's map sheet, a cross-tabulation against type of production, stage and the existing `high_mean` / `high_median`. The v4 results already show that in the farm stage "high capital intensity" is almost the same set as "field crops"; the same check is needed for every new cut before interpreting a coefficient.

## 1. Target structure of the results section (hypotheses to evaluate, not conclusions)

From the coauthors' discussion of 2026-11-24. The section on the effects of multinational presence and entry would follow three steps, with heterogeneity by product type across them:

1. **Probability of entering a market.** Does the arrival of an MNE in an origin × product raise the probability that the cell exports to a (new) destination, and that local firms do?
2. **Effect on exports.** Level of exports of the cell and of local firms after entry.
3. **Indirect effects on local firms.** Number of local exporters, their entry and exit, their destinations. Candidate mechanism: information spillovers (local firms learn about markets, buyers or standards from the MNE's activity).
4. **Heterogeneity by product type.** Two hypotheses, evaluated separately with the cuts of E9 and E10: (H1) MNEs tend to enter, or to be present, in capital-intensive or more complex products; (H2) the indirect effects on local firms appear in products of lower capital intensity or lower complexity. If both held, that would be the interesting result. They are hypotheses: E9–E11 are designed so that each can fail, and the results are reported either way.

Everything in E9–E11 serves this structure. The v4 blocks already cover parts of it (E2 for step 2, E5 for presence, E6 for steps 2–3); the additions fill the gaps and multiply the cuts.

## 2. What the v4 workbook already shows about the capital-intensity measure (motivation for E9)

From `Classifications` and `Samples` (v4):

- `KL_p` takes **22 distinct values in the farm stage** (298 products) and **26 in processing** (535 products): one value per Census farm type or NBER–CES industry. Products in the same farm type or industry share the value, so any threshold is in fact a partition of farm types.
- Farm stage: the farm type at US$261 thousand per worker (NAICS 1111 oilseed and grain farming with 11193–11199 other crops; 51 products, 48 of them field crops) carries 48.6 percent of farm exports 2012–2018; the next value down is US$150 thousand (6 products, 0.9 percent). **Any threshold between US$150 and US$261 thousand produces the same two groups.** The current thresholds (aggregate ratio US$112.9 thousand; export-weighted median US$133.5 thousand) differ only by a few livestock types between US$121 and US$134 thousand (9 products, 0.3 percent of farm exports).
- The farm ranking is a ranking of types of production: fruit, tree nut and greenhouse or nursery farming (NAICS 1113, 1114) at US$17 thousand (52 products, 24.5 percent of farm exports), vegetable and mixed crop farming at US$50–59 thousand (82 products, 21.8 percent), livestock types at US$42 and US$95–150 thousand (about 100 products, 4 percent), oilseed and grain farming at US$261 thousand. "High capital intensity" in the farm stage therefore means "field crops" by construction of the data, not only empirically.
- Processing stage: the industry group at US$250 thousand (NAICS 311221 wet corn milling, 311224 soybean and other oilseed processing, 311225 fats and oils refining, with 311710 seafood; 53 products, 35 of them field crops) carries 38.0 percent of processing exports; the slaughtering, meat and seafood groups at US$64–84 thousand (about 190 products) 25 percent; fruit and vegetable preserving with flour milling and other food at US$132 thousand (91 products) 8.4 percent.
- Consequence: "capital-intensive" in this data is, to a first approximation, "the grain and oilseed complex" in both stages. E9 makes this explicit and asks whether any other partition of the 22 farm types and 26 industries carries a pattern.

## E9. Capital intensity: more definitions and a check of the measure

Purpose: to know how much the capital-intensity results depend on the threshold and on the measure, whether the effects vary gradually with capital intensity or concentrate in one or two groups of products, and whether the US-based measure is plausible for the region.

All heterogeneity regressions in E9 follow E4 (baselines E2a `ln N` and E2b `D`; FE3–FE6; two panels, all firms and local firms; equality tests with p-values in every column; by stage, with the pooled version as a variant). All location regressions follow E5a–E5b (cell `opy`, LPM with logit marginal effects as robustness, FE origin×year and type of production, variant HS2, cluster by product).

- **E9a. Threshold ladder.** For each stage, define `high` with every threshold of this list and run E4c (by stage) and E5a/E5b (by stage, see E12.1) with each: (i) unweighted median of the products; (ii) export-weighted median (exists: `high_median`); (iii) aggregate ratio of the stage (exists: `high_mean`); (iv) unweighted and export-weighted 75th percentile; (v) terciles and quartiles (regressor × each group, lowest group as reference); (vi) the "natural gaps" of the distribution, i.e., thresholds that fall between farm types or industries: farm US$30 thousand (low = fruit, tree nut and greenhouse or nursery farming only), US$55 (low adds aquaculture and other animal production at US$42 and the small horticulture groups up to US$51, among them the five products at US$50.5 thousand with 13 percent of farm exports; high starts at vegetables, US$59), US$90 (low = horticulture plus aquaculture and other animal production; high = the remaining livestock types and grains), US$120 (high drops aquaculture and poultry) and US$150 (high = oilseed and grain farming, with the single product at US$350); processing US$70 (low = slaughtering and meat processing at US$64), US$100 (low adds seafood at US$84 and the other groups under US$92), US$130 (low adds confectionery and chocolate at US$118 and the mixed groups at US$120–126), US$150 (low adds fruit and vegetable preserving at US$132 and wineries at US$136–138), US$180 (low adds dairy at US$159) and US$240 (high = oilseed processing, sugar refining and tobacco manufacturing, 77 products, 42.8 percent of processing exports). Report in `E9 map` the number of products, the export share and the composition by type of production of the `high` group under each threshold. Figure: the `high` and `low` coefficients with 95 percent confidence intervals against the threshold, one panel per stage, FE4 and FE6, both regressors (files in `figures_E9\`, numbers in `E9 figdata`).
- **E9b. Flexible by source group.** Regressor × dummy for each Census farm type (22) and each NBER–CES industry (26), one regression per stage, FE4 and FE6, both regressors, both panels. Output: a sheet with one row per farm type or industry (name, `KL`, number of products, export share, coefficient, SE) and the figure itself: a scatter of the coefficient (with its 95 percent confidence interval) against `lnKL`, marker size = exports, one panel per stage, with the farm type or industry labels (files in `figures_E9\`, numbers in `E9 figdata`). This is the most transparent version of "is there a capital-intensity gradient at all": if the coefficients line up with `lnKL`, the two-group cut is a summary; if only one or two groups stand out, the story is about those groups.
- **E9c. Pooled thresholds across stages.** The farm and processing measures come from different sources (machinery and equipment per hired worker; equipment per employee) and are not strictly comparable. Still, run E4a with a single threshold over all classified products: overall export-weighted median; overall unweighted median; overall 75th percentile. Report the stage composition of `high` under each. This is the variant that a reader who wants "one capital-intensity story" will ask for.
- **E9d. Alternative US measures** (same sources, different numerators and denominators, to see whether the ranking of farm types and industries is robust): farm stage, from the 2017 Census of Agriculture by farm type: total assets (land, buildings, machinery) per hired worker; machinery and equipment per acre; machinery and equipment per dollar of sales. Processing stage, from NBER–CES: total real capital (equipment plus structures) per employee; capital per dollar of value added. For each, the rank correlation with the current `KL_p` across farm types or industries, and E4c with the export-weighted median of each measure.
- **E9e. Consistency with Latin American aggregates** (requested in the 2026-11-24 discussion). The product measure is US-based. Two checks: (i) country level: for each of the nine origins compute the export-weighted average of `lnKL_p` over its agricultural exports (2012–2018), and compare its ranking with public country-level measures of capital per agricultural worker for the same years, for example the FAOSTAT Capital Stock domain (net capital stock in agriculture, forestry and fishing, divided by agricultural employment) and the USDA ERS International Agricultural Productivity data (capital and machinery inputs per worker); report both series for the nine countries and the rank correlation (nine points: this is a plausibility check, not a test). (ii) Product level, if a Latin American source exists: national agricultural censuses report machinery or tractors by crop or farm type for some countries (Argentina 2018, Brazil 2017, Chile 2021, Colombia 2014, Paraguay 2022, Uruguay 2011; availability to be verified); where a crop-level ratio can be built, compare its ranking of field crops, horticulture and livestock with the US ranking. Report what was found and what could not be built.

## E10. Complexity and differentiation

Purpose: the same heterogeneity and location exercises with product characteristics other than capital intensity, so that "capital-intensive" can be told apart from "complex", "differentiated" or "processed".

- **E10a. Product complexity.** Product Complexity Index (PCI) from the Atlas of Economic Complexity (Harvard Growth Lab) or the Observatory of Economic Complexity, at the finest HS level available (HS 1992 four or six digits), mapped to HS 2017 with the UNSD tables; if only four-digit values exist, each HS6 takes the value of its heading. Average over 2012–2018. Add to `Classifications`: `PCI_p`, `high_PCI` (above the export-weighted median within agriculture; variant: unweighted median), `PCI_tercile`. Note that complexity indices rank agriculture low as a whole; the cuts are within agriculture. Then: E4-style heterogeneity (regressor × `high_PCI`; × terciles; × `PCI_p` continuous), E5-style location (`D_opy`, `ln N_opy`, `S_opy` on `PCI_p` and `high_PCI`), and the cross-tabulation of `high_PCI` with type, stage and `high_mean`.
- **E10b. Rauch, complete coverage.** The liberal classification is missing for 475 of 860 products (v4 `Notes`). Rebuild both Rauch versions from the full SITC Rev. 2 product file through the SITC → HS 1992 → HS 2017 concordances (modal class by trade weight when an HS6 maps to several SITC codes), so that every product has a conservative and a liberal class; document the number of products per class and the products that change class between the two versions. Then rerun E7a and E7c with the complete classification, and add the E4-style regressions with `differentiated` vs `reference priced` vs `homogeneous` (regressor × class) and the E5-style location regressions with the class dummies.
- **E10c. Degree of processing.** Three groups from the stage column and the HS chapter: primary (farm stage), first processing (processing stage in chapters 02–15: meat, fish and dairy products, milling, fats and oils), further processing (chapters 16–24: preparations, sugar confectionery, beverages, tobacco). E4-style heterogeneity and E5-style location by group. This is the cheapest proxy for complexity and is already in the data.
- **E10d. Crosses.** Capital intensity × complexity (`high_mean` or `high_median` × `high_PCI`, four cells) and capital intensity × Rauch differentiated (exists as E7c; rerun with E10b), both as E4-style heterogeneity and as location regressions. Report the cell sizes (products, export share) with the estimates.
- **E10e. Map.** `E10 map`: one row per characteristic and cut, with the heterogeneity coefficients (all firms; local firms), the equality test p-value and the location coefficient, FE4 and FE6, both regressors.

## E11. Event studies: outcomes by step of the story, estimators, fixed effects, trends, samples

Purpose: to estimate what changes in a cell after the first multinational arrives, step by step (entry into destination markets, exports, local firms), and to show how much each estimate depends on the estimator, the fixed effects, the control group and the sample, so that the team can judge which results are robust before writing.

Builds on E6 (cells A `op` and B `odp`; event = first MNE exporter in the cell; window −4..+4, base −1; pre-trend joint test, placebo, no-exit and balanced checks; `E6a`–`E6f`). Every variant is reported for both cell definitions unless the outcome only exists in one.

### E11a. Outcomes aligned with the three steps

1. **Entry into markets.** (B) Sample: `odp` cells with no local exports in any year before `t0` (and the analogous condition for controls, see E11d); outcome 1[XL > 0] in event time: probability that local firms start exporting the product to that destination after the MNE's entry in the `op` cell (note that the event is then defined at the `op` level and applied to all its destinations, including those the MNE does not serve). (A) At the `op` level: number of destinations with local exports (`ND_L`), number of *new* destinations for local firms (destinations with no local exports in any earlier year), and the same two counts for all firms.
2. **Exports.** As in E6 (`ln XL`, 1[XL > 0], PPML on `XL`), plus `ln(XL/NL)` (exports per local exporter) and `ln X` (all firms).
3. **Indirect effects on local firms.** `NL` and `ln(1 + NL)` (exist), number of *new* local exporters in the cell (firms with no exports of the product in earlier years), number of exiting local exporters, survival of incumbent local exporters (firm-level: share of the local exporters of `t0 − 1` still exporting the product at +1..+4), and the share of local exports in the cell.
4. **Information-spillover test** (mechanism of step 3). Split the new destinations of local firms in (A) into destinations that the entrant MNE's group already served *before* `t0` (from this origin, in any product, or from any of the nine origins) and other destinations; run the entry-into-markets event study on each set. If spillovers run through information about destination markets, the effect concentrates in the first set. Report the number of groups and destinations involved.

### E11b. Estimators

**Standard set, for every outcome of E11a and E6, both cell definitions and every sample variant of E11d:** (i) OLS event-study regression (TWFE; exists); (ii) Callaway–Sant'Anna with not-yet-treated controls (exists; variant with never-treated controls only); (iii) Sun–Abraham (exists); (iv) Borusyak, Jaravel and Spiess (2024) imputation estimator (`did_imputation`); (v) de Chaisemartin and D'Haultfœuille (2024) dynamic estimator (`did_multiplegt_dyn`). The five are reported together: one table per outcome with one column block per estimator (event-time coefficients −4..+4 with SEs, pre-trend joint p-value, average post effect) and one figure per outcome with the five side by side (E11f). This is the set the team reports as a matter of routine in event-study work, so that estimators that treat heterogeneous effects and the control group differently can be compared at a glance.

**Additional, for the preferred specification of each step of E11a:** (vi) stacked regression by cohort (Cengiz et al. 2019), one stack per `t0` with clean controls; (vii) Wooldridge (2021) extended TWFE (`jwdid`) as the PPML version for levels; (viii) Rambachan and Roth (2023) sensitivity bounds (`honestdid`) for the average post effect, reporting the breakdown value of the pre-trend violation; (ix) a matched-control version (controls matched on pre-event local exports and number of local exporters, e.g., coarsened exact matching or `PanelMatch`). The point of (viii)–(ix) is the result of E6a/E6e: the survival effect falls from about −15 to −4/−7 percentage points when cells are balanced, so the sensitivity to the control group has to be shown rather than argued.

### E11c. Fixed effects and trends

For the TWFE and stacked versions, estimate each outcome with the following sets and report the pre-trend test and the average post effect for each in `E11 map`:

| Code | Cells A (`op`) | Cells B (`odp`) |
|---|---|---|
| EV1 | cell + year | cell + year |
| EV2 | cell + origin×year (current) | cell + origin×year + destination×year (current) |
| EV3 | cell + origin×year + type-of-production×year | cell + origin×destination×year |
| EV4 | cell + origin×year + HS2×year | cell + origin×destination×year + product×year |
| EV5 | — | cell + origin×product×year (identified only from differences across destinations within the `op` cell) |
| EV2-T | EV2 + cell-specific linear trends estimated on the pre-period (−4..−1) and extrapolated | same |
| EV2-TF | EV2 + cell-specific linear trends over the full window | same |

Note the usual caveat for EV2-TF (the trend absorbs part of a dynamic effect); EV2-T is the version to interpret. As an additional check for the preferred outcome of each step, report the pre-trend-adjusted estimates of Freyaldenhoven, Hansen and Shapiro (2019) (`xtevent`).

### E11d. Treatment and sample definitions

1. **Same selection criterion for treated and control cells** (from the review of v4). In v4, treated cells must have at least two years with positive exports before `t0` while controls only need two years with exports in the window. Three variants, each with CS and TWFE: (i) no pre-condition on either group (cells enter with whatever history they have; the outcome 1[XL > 0] absorbs zeros); (ii) assign each control a pseudo-`t0` drawn from the cohort distribution of treated cells and impose the same condition on both; (iii) balanced cells (exists, E6e). Report the number of treated and control cells and the average post effect for survival and for `ln XL` under each, next to the v4 numbers.
2. **Entrant type.** Event = first *foreign* MNE (domestic MNEs treated as local in that variant) and event = first *domestic* MNE.
3. **Size of the entry.** Event = first year with an MNE share of the cell's exports of at least 10 percent (variant 25 percent); and event = first year of a persistent presence (MNE present in at least two consecutive years).
4. **Cohorts.** Report the CS group-time effects by cohort (`t0` 2014..2018) for the preferred outcome of each step.
5. **Minimum history.** Two (current) and three (exists) years before `t0`; and the full set of cells observed from 2012 (balanced, exists).

### E11e. Heterogeneity for the hypothesis of section 1

For each cut of E9a (at least `high_mean`, `high_median`, the US$261/US$240 thousand gaps and the terciles), E10a (`high_PCI`), E10b (differentiated vs rest) and E10c (degree of processing), and for type of production: the three steps of E11a estimated separately by group (CS and TWFE EV2), in one table per cut with the three steps as panels and the groups as columns. `E11 map` adds, for each cut, the share of entry events that fall in each group (from E6's descriptive companion) and the location coefficient of E5/E9/E10, so that the two hypotheses of section 1 can be read in one row: H1 from the entry shares and location coefficients, H2 from the local-firm effects by group.

### E11f. Reporting

- `E11 map`: one row per (outcome, cell definition, estimator, FE code, sample variant, group): pre-trend joint p-value, average post effect with SE, placebo estimate, N treated, N control.
- Event-time coefficients (−4..+4) with SEs for every variant in `Long format` (one row per event time; columns as now, plus `Estimator`, `FE code` EV*, `Sample variant`, `Group`).
- Descriptive companion extended with the new treatment definitions (E11d.2–3): number of events by year, origin, type and group.
- **Figures** (one file per figure, PDF and PNG, in a folder `figures_E11\`; the plotted numbers in a sheet `E11 figdata`: outcome, cell definition, sample variant, FE code, group, estimator, event time, coefficient, lower and upper 95 percent bounds, so that any figure can be redrawn):
  1. *Estimator comparison*, one figure per outcome × cell definition × sample variant: event time −4..+4 on the horizontal axis; at each event time the five estimators of the standard set side by side, with small horizontal offsets and one marker and shade per estimator; 95 percent confidence intervals as vertical lines; base period −1 normalized to zero; dashed horizontal line at zero and dashed vertical line between −1 and 0; legend with the estimator names; a note under the figure with the sample, the dependent variable, the fixed effects, the cluster level and "Vertical lines are 95 percent confidence intervals". `event_plot` produces this layout from the output of the five commands.
  2. *Fixed effects and trends*, one figure per outcome and cell definition (OLS only): the EV codes of E11c as series, same layout.
  3. *Sample and treatment definitions*, one figure per outcome and cell definition (Callaway–Sant'Anna): the variants of E11d as series.
  4. *Heterogeneity*, one figure per cut and step of E11e: the groups as series or as panels, Callaway–Sant'Anna and OLS.
  Same axis labels, scale within a step, marker conventions and note style throughout, so that figures can be read side by side. The figures are the first thing the team will look at; the tables back them.

## E12. Items pending from v4

Purpose: to close the gaps of the v4 workbook so that every number in the text has a cell and every sheet is self-explanatory.

1. **E5a and E5b by stage** (farm; processing), same specifications, both thresholds and `lnKL`. In v4 the pooled location regressions average opposite gradients (E3a: the MNE share rises with `KL` in the farm stage and falls in processing).
2. **Descriptive sheets for the text**: Tables 1, 3, 4 and 5 and Figures 1 and 2 of v4 (2018 descriptives), and the two numbers "68 percent of cells" and "99 percent of exports" of Section 4.3, as sheets `D1`–`D4`, so that every number in the paper has a cell in the workbook (E8.3).
3. **`Notes` additions**: `asinh` was replaced by `ln` on positive values plus 1[XL > 0] (E2e, E6); E2e runs PPML with FE4 only.
4. **FE codes in the "Fixed effects" row of every sheet** (today only in `Long format`).
5. **Classifications**: add every new column of E9–E10 (`high` under each threshold of E9a, farm type or industry id, `PCI_p`, `high_PCI`, Rauch complete, degree of processing) to the existing sheet.

## 3. Suggested order of work

All of E9–E12 is part of the round. The order below says where to start, not what to leave out; it begins with the three exercises that most reduce the uncertainty about the story:

1. E12.1 (E5a and E5b by stage).
2. E9b (flexible specification of capital intensity, by farm type or industry).
3. E11d.1 (event studies with the same selection criterion for treated and control cells).

Then: E11a.1 and E11a.3 (entry into destination markets; new and exiting local exporters) with the standard set of estimators → E11e for `high_mean`, `high_median` and type of production → E10a (PCI) → E11b additional estimators (vi)–(ix) → E9a threshold ladder and E9c → E10b–E10d → E9d–E9e → the remaining variants of E11c–E11d. Figures are prepared together with the estimations of each block. Everything is reported, including null results and results of the opposite sign.
