# Estimation specifications for the next version of "Multinational Firms and Agricultural Trade in Latin America"

Date: 2026-11-17. Audience: the coauthor running the estimations (and any assistant working with them). Self-contained: every sample, variable, classification, specification and output is defined here. Starting point: the v3 of the paper (Overleaf `Note_v3`, 2026-11-03) and the master workbook `WP_paperagro_v3_master_estimates.xlsx`. Rule for this round: **run every variant listed; decisions about what goes in the body are taken afterwards, with all results in hand.** Nothing in the text is rewritten until then.

## 0. Common definitions

### 0.1 Sample

- Countries (origins, o): Argentina, Chile, Colombia, Costa Rica, the Dominican Republic, El Salvador, Paraguay, Peru, Uruguay.
- Years (y): 2012–2018.
- Products (p): HS 2007 six-digit codes. Agricultural products: HS chapters 01–24. For the sector comparison (E1) the whole customs universe is used.
- Destinations (d): countries with an ISO3 code; free trade zones and the exporting country itself are not destinations.
- Firm (f): exporter identified by tax identifier within the origin country.
- Exporter classes (from the Orbis / Dun & Bradstreet match): **foreign MNE** (ultimate parent outside o, or matched with no recorded parent country), **domestic MNE** (ultimate parent in o), **local firm** (not matched). "MNE" = foreign + domestic. A multinational **group** = set of affiliates with the same ultimate parent.
- Cell levels: `odpy` (origin × destination × product × year), `opy` (origin × product × year), `ody`, `fdpy` (firm-level, not used in this round).

### 0.2 Variables at the cell level

- `X_odpy`: export value, all firms (US$). `XL_odpy`: export value of local firms. `XM_odpy`: export value of MNEs.
- `N_odpy`: number of MNE exporters (distinct firms) in the cell; `NF`, `ND`: foreign and domestic MNE exporters. `NL_odpy`: number of local exporters.
- `D_odpy = 1[N_odpy ≥ 1]`: at least one MNE in the cell.
- `S_odpy = XM/X`: MNE share of the cell's exports.
- Logs: `ln X` only for positive values; where zeros matter (local exports can be zero in a cell with MNE exports) report also `asinh(X)` and, as a robustness, PPML on levels.

### 0.3 Product classifications (publish the HS6 mapping table as a sheet: one row per HS6 with every classification below)

1. **Type of production** (FAO Indicative Crop Classification, as in v3 Section 2): `field crops` (cereals, oilseeds, pulses, roots and tubers, sugar crops, fibers, with their flours, oils and meals); `horticultural and plantation crops` (fruit, vegetables, coffee, tea, cocoa, spices, flowers, tobacco, permanent oilseed crops); `livestock and fisheries`; `other processed food and beverages`. Each group includes the preparations of its products.
2. **Stage**: `farm` (primary products) vs `processing` (processed products), as used for the capital-intensity measure; `not classified` for the 26 products without a match.
3. **Capital intensity** `KL_p` (US$ thousand per worker): farm stage = machinery and equipment per hired worker from the 2017 US Census of Agriculture (USDA NASS); processing stage = equipment capital per employee from the NBER-CES Manufacturing Industry Database. Keep the current mapping. Variants to compute for every product:
   - `high_mean`: `KL_p` above the export-weighted mean of its stage (current: US$113 thousand farm, US$118 thousand processing);
   - `high_median`: above the export-weighted median of its stage (new);
   - `quintile`: export-weighted quintile of `KL_p` within stage (1 = lowest);
   - `lnKL_p` continuous.
4. **Type × capital intensity**: the eight cells of (1) × high/low (both thresholds), plus not classified.
5. **Rauch classification** (Rauch 1999, conservative and liberal versions): `homogeneous` (organized exchange), `reference priced`, `differentiated`; mapping via SITC Rev. 2 → HS 2007 concordance (the earlier note had this table; the archived fragment `tab_wp1b_rauch.tex` documents the groups used).
6. **End use** (BEC Rev. 4): `intermediate` vs `consumption` goods; and the project's `inputs` group (seeds, animal feed, live animals) vs other products (archived fragment `tab_wp2_bec_enduse.tex`).
7. **Sector** (E1 only): `agriculture` HS 01–24; `mining and fuels` HS 25–27, with `fuels` HS 27 also separately; `manufacturing` HS 28–97 (exclude HS 98–99 special codes if present).

### 0.4 Fixed-effect sets (same names everywhere; these are the six of the master workbook)

| Code | Fixed effects |
|---|---|
| FE1 | origin + destination + product + year |
| FE2 | origin×year + destination×year + product |
| FE3 | origin×destination×product + year |
| FE4 | origin×destination×product + origin×destination×year |
| FE5 | FE4 + origin×product×year |
| FE6 | FE5 + destination×product×year |

Standard errors clustered by origin–destination pair unless stated. Report observations, R², within-R² and the number of singletons dropped for every column. Columns 3–6 are the candidates for the body; 1–2 are context.

### 0.5 Outputs

- The master workbook with one sheet per table (named `E1a`, `E1b`, …), each with the layout of the current sheets (header row with FE codes; rows: coefficient, standard error in parentheses, stars, tests, observations, R², within-R²; a "Column in the note" row).
- The "Long format" sheet updated with every new estimate (one row per coefficient: table, panel, column, dependent variable, regressor, coefficient, SE, p, stars, N, R², within-R², FE code, cluster, sample).
- A "Classifications" sheet (HS6 → all items of 0.3) and a "Samples" sheet (number of cells, exporters and export value by sample definition).
- Significance: *** 1%, ** 5%, * 10%.

## E1. Sector context (descriptive)

Universe: all exports of the nine countries, 2012–2018.

- **E1a.** By origin and for the nine together, 2018: export value (US$ billion), number of exporters, share of exports shipped by MNEs (total, foreign, domestic), for `agriculture`, `mining and fuels` (with `fuels` as a separate row), `manufacturing`, and total. Add the share of each sector in total exports and in MNE exports.
- **E1b.** Same table with 2012–2018 annual averages.
- **E1c.** Number of MNE affiliates (foreign, domestic) and of multinational groups active in each sector, 2018.
- Optional figure: stacked bars by country, MNE share by sector.

## E2. Baseline: multinational presence and exports

Cell `odpy`, agricultural products, 2012–2018.

- **E2a.** Dependent variable `ln X_odpy` (all firms). Regressor `ln N_odpy`. Sample: cells with `N ≥ 1`. Columns FE1–FE6.
- **E2b.** Dependent variable `ln X_odpy`. Regressor `D_odpy`. Sample: all cells with positive exports. Columns FE1–FE6.
- **E2c, E2d.** Same as a and b with `ln XL_odpy` (local firms; sample: cells with positive local exports) — annex.
- **E2e.** Same as a and b with `asinh(XL_odpy)` including cells with zero local exports; and PPML on `XL` levels with FE4 — robustness for zeros.
- **E2f.** Dependent variables `ln NL_odpy` (number of local exporters) and `ln(XL/NL)` (exports per local exporter), regressors `ln N` and `D`, FE3–FE6 — annex (current Table 10).
- **E2g.** E2a and E2b estimated separately by origin, FE3–FE6, clustered by destination — annex (current Tables 11–12).

## E3. Capital intensity, descriptive

Agricultural products, by stage.

- **E3a.** By `quintile` of `KL_p` within stage (farm; processing), 2018 and 2012–2018 average: number of products, share of exports, MNE share, foreign-MNE share, number of MNE exporters, mean `KL`.
- **E3b.** Figure data: one row per HS6 product: `lnKL_p`, MNE share, foreign share, export value, stage, type. (Figure: MNE share vs `lnKL`, marker size = exports, one panel per stage, with a fitted line.)
- **E3c.** Coverage: exports and products covered by the capital-intensity measure, by stage and type; list of the not-classified products.
- **E3d.** Cross-tabulation type × high/low (both thresholds): number of products, share of exports, MNE share, mean `KL` (current Table 13, extended with `high_median`).

## E4. Heterogeneity by capital intensity

All on the baselines of E2a (`ln N`) and E2b (`D`), FE3–FE6, two panels (all firms; local firms), with the p-value of the equality tests in every column.

- **E4a.** Two groups, **stages pooled**: regressor × `high` / × `low`, for `high_mean` and `high_median`. Test high = low.
- **E4b.** Continuous: regressor × `lnKL_p` (and the regressor alone), so that the coefficient on the interaction is the capital-intensity "premium". Variant with `lnKL` demeaned within stage.
- **E4c.** By stage × high/low (farm high, farm low, processing high, processing low, not classified) — current Table 15, both thresholds. Tests farm high = farm low, processing high = processing low.
- **E4d.** Farm stage only: regressor × high/low **and** regressor × type of production in the same regression (types: field crops, horticultural and plantation, livestock), to separate capital intensity from "field crops". Also the same with `lnKL` continuous and type dummies.
- **E4e.** Type × capital intensity (eight cells) — current Table 16, both thresholds, with tests within each type.
- **E4f.** By type of production alone — current Table 14 (keep for the annex).
- **E4g.** E4a and E4c by origin, FE4 only, clustered by destination — annex.

## E5. Location of multinationals

Cell `opy` (origin × product × year), agricultural products; sample: products exported from o in y (positive total exports), 2012–2018.

- **E5a.** Dependent variable `D_opy = 1[N_opy ≥ 1]`. Regressors: `lnKL_p`; `high_mean`; `high_median`; `quintile` dummies. FE: origin×year and type of production (variant: origin×year and HS2 chapter). Linear probability model; logit as robustness (report average marginal effects). Cluster by product.
- **E5b.** Same with `ln N_opy` (cells with `N ≥ 1`) and with `S_opy` (MNE share).
- **E5c.** Foreign MNEs only (`NF`), and domestic only.
- **E5d.** First entry: sample of cells with no MNE in any year before y; dependent variable 1[first MNE exporter in y]; same regressors and FE (discrete-time hazard). Report also the number of first entries by year, type and capital-intensity group.
- **E5e.** Cross with 0.3.5–0.3.6: `D_opy` on `lnKL_p` plus Rauch dummies and BEC/inputs dummies, to see which product characteristic predicts presence.

## E6. Event studies: entry of multinationals

Two cell definitions, both complete: (A) `op` (origin × product), outcomes aggregated over destinations; (B) `odp` (origin × destination × product).

- **Event.** First year `t0` in which an MNE exporter appears in the cell, with no MNE exporter in any earlier observed year. Cells with an MNE already in 2012 are "always treated" and excluded from the treated group. Never-treated cells (no MNE in 2012–2018) and not-yet-treated cells are the controls. Require at least two observed years before `t0` (variant: three).
- **Outcomes.** `asinh(XL)` and `ln XL` (local exports); `NL` and `ln(1+NL)` (local exporters); `asinh(X)` (total exports); `N` (number of MNEs, to describe the entry itself); 1[XL > 0].
- **Window.** Event time −4 to +4, base period −1, endpoints binned.
- **Estimators.** (i) Event-study regression with cell FE and origin×year FE (for B also destination×year), event-time dummies interacted with treatment; (ii) Callaway–Sant'Anna with not-yet-treated controls, aggregated by event time; (iii) Sun–Abraham as a check. Cluster by origin×product (A) or origin–destination pair (B). Report the pre-trend joint test and the average post-event effect.
- **Heterogeneity.** By `high_mean` and `high_median`; by type of production; by stage; by origin (annex); by entrant type (foreign vs domestic MNE).
- **Checks.** Placebo event at `t0 − 3`; exclude cells where the MNE exits within two years; balanced panel of cells observed in every year; results in levels (PPML) for local exports.
- **Descriptive companion.** Number of entry events by year, origin, type and capital-intensity group; share of local exports in treated cells.

## E7. Other crosses for location and heterogeneity (only what shows a clear pattern enters the paper)

- **E7a.** MNE share and E4a-style heterogeneity by Rauch class (homogeneous / reference priced / differentiated), conservative and liberal.
- **E7b.** Same by BEC end use and by the `inputs` group.
- **E7c.** Capital intensity × Rauch (high/low × homogeneous/differentiated).

## E8. Consistency checklist (for the workbook and the paper)

1. One sample definition per table, stated in the sheet (cells, years, products, exporter class).
2. FE codes FE1–FE6 and cluster level stated in every sheet; no other names.
3. Every number quoted in the paper has a cell in the workbook (sheet and row).
4. The "Classifications" sheet is the only source of product groups; the paper's Section 2 describes it.
5. Report singletons dropped and the number of cells per panel; keep the "Column in the note" row.
6. For every table: all firms and local firms versions; `ln N` and `D` versions; both capital-intensity thresholds where relevant.
