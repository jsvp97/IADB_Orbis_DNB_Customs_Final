# Estimation specifications for round v6 of "Multinational Firms and Agricultural Trade in Latin America"

Date: 2026-11-25. Audience: the coauthor running the estimations. Starting point: the v5 delivery (`results.v5`) and its workbook, `WP_paperagro_v5_master_estimates.xlsx`. The figures quoted here come from that workbook and carry their sheet; where a figure is our calculation from the numbers of a sheet, the text says so.

**What this document contains.** The requests for round v6: a one-page **Summary**; **Part A**, the rules of the round and the common definitions (cells, variables, outcomes, fixed-effect and cluster codes, regression templates, cohort-aligned stacks, what is always reported, roles); **Part B**, the 18 core requests (V6-01 to V6-18: definition questions, corrections to the v5 workbook, new classifications, regressions, event studies by level of aggregation, the bridge table, the new local exporters and the delivery format); **Part C**, the primary set of six tests and one diagnostic, and how the team will read it; **Part D**, the second tier (V6-19 to V6-31); **Part E**, what is not in this round; and the suggested order of work.

**How it relates to the 2026-11-17 and 2026-11-24 documents.** The definitions of the sample, of the cell variables and of the fixed-effect codes FE1 to FE6 in those documents still apply. Everything new in this round is defined here, in Part A, so this document is self-contained for everything new.

## Summary

- **Size.** The core is 18 requests (V6-01 to V6-18): 14 new sheets, new columns in five existing sheets and specific corrections to the v5 workbook. On the order of 2,500 to 3,500 new rows in `All estimates` if every event-time coefficient is stored (our rough count; a second count gave 1,500 to 2,000), against 43,585 in v5. Everything else goes to a second tier of 13 requests (V6-19 to V6-31), which is run only if the core has already been delivered.
- **Before estimating.** Sixteen questions that are answered without running anything (V6-01) and a table of universe and support (V6-10). The heading level, the source of the PCI, the definition of "new exporter" and the reading of the 2017 cohort depend on the answers.
- **New classifications.** Six-digit PCI merged in the same HS revision as the data (HS 2017), with the four-digit PCI and the ubiquity from the same source (V6-03). Binary Rauch, differentiated against not differentiated, next to the three classes (V6-04).
- **Regressions.** The complexity gradient is estimated again with PCI6 and with errors clustered by product as well: today they are clustered by origin–destination pair and the cut varies by product. What belongs to the MNEs is separated from what belongs to local firms, a horse race is run between complexity, differentiation, field crops, stage and ubiquity, and location is also estimated weighted by value and conditional on an MNE being present (V6-05 to V6-09).
- **Event studies at different levels of aggregation.** The table of levels is in B.5.1. In v6 four are run: origin × product, the same product across origins, origin × HS4 heading and origin × destination × product, all with cohort-aligned stacks (V6-11 to V6-15). Reason: in v5 each control is compared with every cohort although its condition of prior exports was evaluated against another year, and that generates mechanical pre-trends.
- **Bridge table.** Six columns that go from each regression to its event study changing one thing per column, in destination cells (where the fixed effects coincide) and in product cells (where there is no regression today) (V6-16).
- **The only clean result is tested and described.** New local exporters with product × year, without the 2017 cohort and without the HS codes with a non-one-to-one correspondence (V6-12); and a table of who they are, with the validation of the "local" class (V6-17).
- **Primary set.** Six tests and one diagnostic fixed in writing before running, with the way each outcome will be read fixed in advance (Part C). Everything else carries its label in a `Role` column.
- **What changes relative to v5.** (i) Comparison rule: from `g_ps` (drawn pseudo-year) to `R(g)`, evaluated in the year of each cohort, with no draw. (ii) Window: −3 to +2 are shown and 0 to 2 are averaged (before, −4 to +4 and 0 to 4). (iii) A single main estimator, the aligned stacked estimator; Callaway and Sant'Anna, Sun and Abraham, BJS, dCDH with absorbing treatment, cell trends, Freyaldenhoven and CEM are not run again. (iv) Heterogeneity of the event studies by interaction in a single estimation, with an equality test, instead of split samples. (v) Destination cells with the event split and the fixed effects of the regressions. (vi) Two-way clustering in every regression with product traits. (vii) Cells E, the capital-per-worker blocks and the split-sample sheets are not redone.
- **Text.** Still frozen at v4 (rule 1 of A.1).
- **Code.** The delivery includes the scripts of rounds v4, v5 and v6: code only, with no data and no intermediate files (B.8, point 14).

## Part A. Rules and common definitions

Each object is defined once, here, and is then cited by its name. If a request seems to contradict this part, this part prevails.

### A.1 Rules

1. **Frozen text.** `Note_v4` is not touched until the team decides on the story. The only new item admitted is the answer to question 16.
2. **Order.** First the sheets `10.1` and `10.2`, which require no estimation. Then, in parallel, the regressions (`10.3`, `11.1` to `11.4`) and the event studies (`12.1` to `12.5`). Last, `12.6` and `12.7`. The second tier starts when the core has been delivered.
3. **Run what is written.** Everything requested is reported, including nulls and opposite signs. No cuts, estimators, samples or windows are added beyond those in this document; if something is missing, it is proposed separately.
4. **One cut, one column.** Each product cut is a named column of `Product classifications`. Each sheet states in its header the cut column, the sample, the FE or EV code, the cluster code and the `Role`.
5. **Logs and zeros.** Logs only of positive values; zeros enter through a 0/1 indicator (linear probability model) or through PPML in levels. Never ln(1 + x) or asinh (rule in force, `Technical notes`).
6. **External data.** Downloads (PCI, ubiquity, classification lists) are documented with source, version, HS revision, years and download date in `Technical notes`. No project data are sent to external services.
7. **Role declared before running.** The role of each estimation (A.9) is the one in this document and does not change after the results are seen.

### A.2 Sample, cells and variables

- **Sample:** that of v5. Nine origins, 2012 to 2018, six-digit HS 2017 products of chapters 01 to 24 (860 products), real destinations.
- **Indices:** `o` origin, `d` destination, `p` HS6 product, `h` HS4 heading, `t` year, `u` generic cell, `g` cohort (year of the first entry), `k = t − g` event time.
- **Regression cells:** `odpy` (association) and `opy` (location), as in the 2026-11-17 specifications.
- **Event-study cells:** A = `op` (origin × product); B = `odp` (origin × destination × product); H = `oh` (origin × HS4 heading, new). The universe of each level is the set of cells with positive exports in at least one year from 2012 to 2018. The cells E of v5 are not used.
- **Cell variables** (2026-11-17 specifications, 0.2): `X` exports of all firms; `XL` of local firms; `XM` of MNEs; `N` number of MNEs (firms); `NF`, `ND` foreign and domestic; `NL` number of local exporters; `D = 1[N ≥ 1]`; `S = XM / X`.
- **New variables:**
  - `G`: number of distinct multinational groups (same ultimate parent) with exports in the cell.
  - `Dotros_odpt`: 1 if some MNE exports product `p` from `o` to another destination, different from `d`, in `t`.
  - `t0_u`: year of the first entry (A.7). `Post_ut = 1[t ≥ t0_u]` for cells with a first entry and 0 for never-treated cells. Unlike `D`, it does not return to zero if the MNE leaves.
  - `Treat_ug`: 1 if cell `u` is treated in stack `g` (A.7).

### A.3 Outcomes of the event studies

The names of the v5 workbook are used (`4.0`, column `Outcome`) and, in this document, the short code.

| Code | Name in the workbook | Definition | Panel |
|---|---|---|---|
| `anyXL` | Local firms export (0/1) | `1[XL_ut > 0]` | rectangular, with zeros |
| `lnXL` | ln exports of local firms | `ln XL_ut` | `XL > 0` only |
| `XL_ppml` | Exports of local firms, levels (PPML) | `XL_ut` in levels, PPML | rectangular |
| `lnX` | ln exports of all firms | `ln X_ut` | `X > 0` only |
| `NL` | Number of local exporters | count | rectangular |
| `lnNL` | ln number of local exporters | `ln NL_ut` | `NL > 0` only |
| `NEWL` | New local exporters | local firms that export in the cell in `t` and did not export in the cell in any earlier observed year (since 2012); no value in 2012. This is the v5 definition, to be confirmed (question 6) | rectangular |
| `NEWL_fw` | New local exporters, fixed window (new) | local firms that export in the cell in `t` and not in `t − 1` or in `t − 2`; defined from 2014. Robustness only | rectangular |
| `EXITL` | Local exporters that stop exporting | v5 definition, to be confirmed (question 6) | rectangular |
| `SURVL` | Share of last year's local exporters that still export | share of the local exporters of `t − 1` that export in `t` | cells with `NL > 0` in `t − 1` |
| `N` | Number of MNEs | first stage | rectangular |
| `D` | At least one MNE (0/1) (new as an outcome) | first stage | rectangular |

- **Full list:** the twelve rows, except `NEWL_fw`. For `NL` and `NEWL` the level is reported and, next to it, the PPML.
- **Short list:** `lnX`, `lnXL`, `lnNL`, `anyXL`, `NEWL`, plus the first stage (`N` and `D`).
- "New" always means new in the cell of the level: in A, in the product; in B, in the destination; in H, in the heading (the firm did not export any HS6 of the heading from the origin in earlier years).

### A.4 Fixed effects: FE codes (regressions) and EV codes (event studies)

FE1 to FE6 are those of the 2026-11-17 specifications and do not change. FE3 to FE6 are used.

| Code | Fixed effects (cells `odpy`) |
|---|---|
| FE3 | origin × destination × product + year |
| FE4 | origin × destination × product + origin × destination × year |
| FE5 | FE4 + origin × product × year |
| FE6 | FE5 + destination × product × year |

Location regressions (cells `opy`), with the three sets of `3.1`: **FL1** = origin × year + type of production (main); **FL2** = origin × year + HS chapter; **FL3** = origin × year.

EV1 to EV5 are those of v5. EV6 and EV7 are new and complete the map with the regressions. EV8 and EV9 are new and exist only for cells A.

| Code | Cells A (`op`) and H (`oh`) | Cells B (`odp`) | Regression with the same FE |
|---|---|---|---|
| EV1 | cell + year | cell + year | FE3 (B) |
| EV2 | cell + origin × year | cell + origin × year + destination × year | none |
| EV3 | EV2 + type of production × year | cell + origin × destination × year | **FE4** (B) |
| EV4 | EV2 + HS chapter × year | EV3 + product × year | none |
| EV5 | does not exist | cell + origin × product × year | none |
| EV6 | does not exist | EV3 + origin × product × year | **FE5** |
| EV7 | does not exist | EV6 + destination × product × year | **FE6** |
| EV8 | EV2 + HS4 heading × year | does not exist | none |
| EV9 | EV2 + HS6 product × year | does not exist | none |

Main specification in v6: EV2 in A and in H; EV3 in B. In the aligned design all fixed effects are interacted with the stack `g` (A.7). EV1 and EV5 are not used in v6.

### A.5 Cluster

| Code | Clustering | Where it is used |
|---|---|---|
| CL-od | origin–destination pair | the one of v5; kept as a reference |
| **CL2** | two-way: origin–destination pair and HS4 heading | **standard** for every `odpy` regression with an interaction by product trait |
| CL2-hs6 | two-way: origin–destination pair and HS6 product | variant, only in the primary tests T2 and T3 |
| CL-hs6 | HS6 product | location (as in v5) |
| CL-hs4 | HS4 heading | regression at the `op` level with a product trait; second p of the equality tests between product groups in cells A |
| CL-op | origin × product cell | event studies in A |
| CL-B | two-way: origin–destination pair and `op` cell | event studies and bridge in B |
| CL-oh | origin × HS4 heading | event studies in H and ring |

Standard: errors are clustered at the level at which the regressor of interest varies. A cut by product requires the product (or its heading) to be in the cluster. Errors are not clustered by origin (there are nine): origin × year FE and the exclusion of one origin at a time are used.

### A.6 Regression templates

- **ASOC** (as E4 of the 2026-11-17 specifications). Cell `odpy`. Dependent variables: `ln X` (cells with `X > 0`) and `ln XL` (cells with `XL > 0`). Regressor `R`: `ln N` (cells with `N ≥ 1`) or `D` (all cells with `X > 0`). Two forms: **by groups**, `R ×` one dummy per group, with no main effect, with the p of equality between groups; **continuous**, `R` and `R ×` standardized trait. FE3 to FE6. Cluster CL2. "Full ASOC" = the two dependent variables, the two regressors and the four FE sets (16 regressions per cut).
- **LOC** (as `3.1`). Cell `opy` with `X > 0`. Dependent variables: `D_opy`, `ln N_opy` (cells with `N ≥ 1`) and `S_opy`. Regressor: the trait, continuous or in group dummies. FL1, FL2 and FL3. Linear model. Cluster CL-hs6. Variants: **weighted** by `X_opy`; **conditional**, `S_opy` only in cells with `N_opy ≥ 1`. "Full LOC" = the three dependent variables and the three FE sets (9 regressions per cut).
- In all: observations, R², within R² and singletons, as in v5.

### A.7 Cohort-aligned stacks (programmable definition)

It applies to any level `u` (A, B or H). It replaces the `g_ps` rule and its pseudo-year: there is no draw and no seed.

1. **At risk:** `N_u,2012 = 0` and `N_u,2013 = 0`. Cells with an MNE in 2012 or 2013 do not enter, either as treated or as controls.
2. **Cohort** `g` in {2014, ..., 2018}: `t0_u = g` if `N_ug ≥ 1` and `N_us = 0` for every `s < g`.
3. **Never treated:** `N_ut = 0` in the seven years. Cells treated later are not used as controls.
4. **Aligned rule `R(g)`:** `X_u,g−1 > 0` and `X_u,g−2 > 0`. It is evaluated at `g` for the treated cells of cohort `g` and, separately, for each control of stack `g`. Variants: `R3(g)`, which adds `X_u,g−3 > 0` (cohorts 2015 onward), and `R0`, with no rule.
5. **Stack `g`:** treated cells with `t0 = g` that satisfy `R(g)`, plus never-treated cells that satisfy `R(g)`; years from `max(2012, g − 4)` to `min(2018, g + 4)`. The same control can be in several stacks.
6. **Equation:** `Y_ugt = Σ_k b_k · 1[t − g = k] · Treat_ug + a_ug + l_g(FE) + e_ugt`, with `k` different from −1 (base year). `a_ug` is the cell × stack fixed effect and `l_g(FE)` are the other fixed effects of the EV code, interacted with the stack. With EV2 in A, `l_g(FE)` is origin × year × stack.
7. **What is shown:** the coefficients from `k = −3` to `+2`. Those of `k = −4`, `+3` and `+4` are not interpreted and stay in `All estimates`.
8. **Main average:** simple average of `b_0`, `b_1` and `b_2`, with the standard error from the full covariance matrix. Next to it, for continuity with v5, the average of `k = 0` to `4`.
9. **Weighting check:** the same equation with `Treat × k ×` cohort. The coefficients by cohort are reported, and two averages of 0 to 2: that of point 8 and the one weighted by the number of treated cells of each cohort.
10. **Pre-trend test:** joint test of `b_−3 = b_−2 = 0`. For `anyXL`, `b_−2` is zero by construction in both groups under `R(g)` (before entry `X = XL`), so the test rests on `b_−3` (cohorts 2015 onward). The header says so.
11. **Placebo:** the same estimation with the event moved to `g − 3`, using only years before `g` and the rule `R(g − 3)`. It is only possible for cohorts 2017 and 2018.
12. **Fixed composition** (variant): cohorts 2014 to 2016, window −2 to +2.
13. **PPML:** same equation and same FE, estimated by Poisson; coefficients in log points.
14. **Column "v5":** in each sheet, once only, the v5 number for the same outcome (rule `g_ps`, Callaway and Sant'Anna, average 0 to 4, from `4.1` or `5.1`).

### A.8 What is always reported

In every event-study sheet, for all cells and for each group when there are cuts:

1. Mean, median and 90th percentile of the outcome in `g − 1`, for treated and controls; share of zeros; effect as a percentage of the mean of the treated.
2. First stage: `N` and `D` by event time.
3. Number of treated cells and of clusters that identify each coefficient.
4. Treated and control cells by stack; treated cells by origin and cohort.
5. p of the pre-trend test and placebo (A.7, points 10 and 11).
6. 95 percent confidence interval of the main average, not only the stars.

In every regression sheet with cuts: products, cells and share in exports 2012 to 2018 of each group; p with CL2.

### A.9 Roles (column `Role`) and priority

| `Role` | What it is | How it is read |
|---|---|---|
| `primary` | the exact row of one of the six tests T1 to T6 (Part C) | with its p; decides |
| `diagnostic` | the bridge table (DG, Part C) | condition for reading the event studies |
| `secondary` | the three declared secondaries (Part C) | with its p; does not decide |
| `robustness` | variant of a primary test (FE, cluster, sample, weighting) | sign and stability |
| `descriptive` | tables and regressions that describe without testing | magnitudes |
| `exploratory` | everything else | with q-values, which are computed by the team from `All estimates` |

Priority of each request: **core** (delivered in any case) or **second tier** (Part D). In each request, "Role" is that of its main rows; the exceptions are stated.

## Part B. Requests

The 18 core requests. Each one states its priority, the role of its main rows (A.9), the deliverable and why it is asked.

### B.1 Definition questions

**V6-01. Definition answers.** Priority: core. Role: no estimations. Deliverable: sheet `10.1 Definitions and answers`, one row per question with the answer and, where applicable, the script and the line that support it. Why: how what has already been delivered is read, and what can be requested, depends on these answers. They are answered before estimating.

**Design of the v5 event studies (questions 1 to 10)**

1. Rule "two years with exports before t0" (`g_ps`): any two years or the two immediately preceding ones? Exports of all firms or only of local firms?
2. Cohort 2013 and cells with an MNE in 2012: are they excluded altogether or do they enter as "not yet treated" controls?
3. Pseudo-year of the controls: confirm that it only filters, that is, that each control is compared with all cohorts, also in the stacked estimator and in the rows by cohort of `4.4`. How many controls are lost because of the draw (from 746 to 509 in product cells, `7.2`) and whether another seed was tried.
4. `csdid`: which control group each of the two Callaway and Sant'Anna rows of `4.1` uses (the `.md` says that by default it uses the not yet treated and that `never` is an option). How origin × year enters in Callaway and Sant'Anna, Sun and Abraham, BJS and dCDH (`4.0` labels "Cell and origin x year" for all). Whether the pre-period coefficients of `csdid` are long differences relative to −1 or period-to-period differences.
5. Stacked estimator of v5 (`4.7`, `5.7`): are the cell and origin × year fixed effects specific to each stack? Do the not yet treated enter as controls?
6. Exact definition of `New local exporters`, `Local exporters that stop exporting` and `Share of last year's local exporters that still export`: which years it looks back at and, in destination cells, whether "new" means new in the product or in the destination.
7. Cells E: universe of destinations (only `odp` cells with some exports in 2012 to 2018?), rule for the controls and how many products (`op`) the 1,289 treated cells belong to (`7.2`).
8. Event "MNE still there next year" in the 2018 cohort, which has no following year: how it was handled.
9. Event "First foreign MNE" with the main rule (`4.3`): are the controls the same 509 cells with no MNE at all?
10. Conversion to HS 2017 of the years declared in HS 2012: what was done with the codes that split into several or merge, and whether an indicator by code exists.

**Data (questions 11 to 15)**

11. Exporter class (foreign MNE, domestic MNE, local): is it fixed over time or does it change with the acquisition date? The reading of V6-17 depends on the answer.
12. Universe for defining "new exporter": can the whole customs data be looked at (as in `v4 E1a`) or only chapters 01 to 24? `NEWL_denovo` (V6-17) depends on the answer.
13. Activity code (NACE or SIC) from Orbis or from D&B: does the match keep it? Coverage in number of MNEs and in value exported by MNEs. V6-28 depends on the answer.
14. Quantities (weight or units) in the customs data: do they exist? For which origins and years? No estimation with quantities is requested in v6 (Part E).
15. Six-digit PCI: which source publishes it, in which HS revisions, for which years and in what download form; and whether that same source publishes, in the same revision, the four-digit PCI and the ubiquity (or the comparative-advantage matrix to compute it). V6-03, which fixes the rule for each case, depends on the answer.

**Text (question 16)**

16. What changed in Section 4.3 of `Note_v4` on 2026-11-24 (first and last sentence). Nothing else is touched.

### B.2 Corrections to the v5 workbook

**V6-02. Corrections and notes.** Priority: core. Role: documentation. Deliverable: the sheets indicated in each point and a list of changes in `Technical notes`. Why: there is a calculation error that understates magnitudes and several notes that today lead to misreading.

1. **OLS average with fewer than five post-period coefficients.** In the rows by cohort and the placebo rows (`4.4`, `5.4`, `4.10`, `5.9`, `6.6`) the OLS "Average effect, years 0 to 4" divides by five even when fewer coefficients exist. Examples (our calculation from the sheets cited): cohort 2018, `New local exporters`, coefficient at t0 0.1097 and "average" 0.0219 (`4.4`); placebo in product cells, `Local firms export (0/1)`, coefficients 0.026, 0.136 and 0.173 and "average" 0.067, when the mean is 0.112 (`4.10`). Recompute as the average of the coefficients that exist, in the five sheets, in `4.0` and in `All estimates`. The p-values do not change.
2. **`Main results`, points 5 and 7.** Add the placebos of `4.10` and `5.9` with the corrected magnitudes: the number of local exporters and the exits have a significant placebo.
3. **`Main results`, point 1.** The sentence "The MNE share of exports is unrelated to capital intensity in both stages" holds across cells and unweighted; in value the share rises with capital in the farm stage (`v4 E3a`). Clarify it and refer to the columns of V6-09.
4. **`Main results`, point 2.** Add the weighted slope of `2.2` (0.19, SE 0.03) next to the unweighted one (0.12, SE 0.06).
5. **`Main results`.** Add a point with the location by complexity and by degree of processing (`3.1` and `3.4`, panels "Where MNEs are").
6. **Freyaldenhoven et al.** The columns are empty in `4.2`, `5.2` and `6.2`, and the note of `4.2` (product cells) says "not estimable on destination cells". State whether it ran on product cells and correct the note.
7. **CEM.** The `.md` of the round says "pre-trends in lnXL" and sheet `4.8` gives p 0.27 and 0.33. Correct the `.md` or explain what it refers to.
8. **`Glossary`.** Add the map FE1 to FE6 and EV1 to EV9 of A.4, which today is only in the `.md`.
9. **`Technical notes`.** Add that `v4 E2e` runs PPML only with FE4 (pending item E12.3 of the 2026-11-24 specifications).
10. **Labels.** In `3.1` the tercile panels say "by PCI capital intensity terciles" (it should say "by PCI terciles"). In `3.2` the group of products without a Rauch class appears with the internal label `kr_na` (it should say "Not classified").
11. **For when the text is reopened (not now).** The "99 percent of exports" of Section 4.3 is 98.47 percent in `9.4`.

### B.3 New classifications

The new columns are added to `Product classifications` with the names of this section. Sheet `10.3 New classifications` documents how they were built.

**V6-03. Six-digit PCI in the same HS revision as the data, with four-digit PCI and ubiquity from the same source.** Priority: core. Role: construction. Deliverable: columns in `Product classifications` and sheet `10.3`. Why: the current PCI (`PCI_p`) is four-digit HS 1992 and takes 196 values over 197 headings (`Product classifications`); it has to be seen whether the gradient depends on the level of the index, without mixing HS revisions.

Prior step: the answer to question 15. Nothing is built before it.

Revision rule:

1. The data are in six-digit HS 2017. The PCI is merged to those codes, never to the original codes of each year.
2. Each PCI column comes from **a single** HS revision, which goes in the name of the column. A column is never completed with values from another revision or with the four-digit value: what is missing stays empty and is counted in the coverage table.
3. **Main column, `PCI6_hs17`:** six-digit PCI published in HS 2017, merged code by code, with no conversion table. Average of the available years, which are stated (a series native to HS 2017 cannot cover 2012 to 2016).
4. **`PCI4_hs17`:** four-digit PCI from the same source, the same revision and the same years; each HS6 takes that of its heading (`hs4`).
5. **`ubiq_hs17`:** ubiquity of the product (number of countries with revealed comparative advantage greater than or equal to 1), same source, revision and years. If the source neither publishes it nor allows computing it, this is stated in `10.3` and the columns with ubiquity of V6-07 are not run.
6. **Robustness, `PCI6_hs12`:** six-digit PCI published in HS 2012, average 2012 to 2016, taken to HS 2017 with the UNSD correlation table HS 2017 → HS 2012 (the same family of tables that was used for the trade data). If one HS 2017 code corresponds to several HS 2012 codes, simple average; if several HS 2017 codes correspond to one HS 2012 code, all inherit it.
7. **If the source does not publish six-digit HS 2017 or it cannot be downloaded:** the main column becomes `PCI6_hs12`, with `PCI4_hs12` and `ubiq_hs12` built in the same way, and the team is told before estimating. If there is no HS 2012 either, six-digit HS 1992 is used (`PCI6_hs92`, with the UNSD table HS 2017 → HS 1992 already used, column `hs92`). In those cases the derived columns are built on whichever main column there is, and each header says which one it is.
8. `PCI_p`, `high_PCI`, `high_PCI_u` and `PCI_tercile` (v5) are kept unchanged for comparison.

Derived columns, always on the main column:

- `PCI6_z`: `PCI6_hs17` standardized (mean 0, standard deviation 1) across the agricultural products with data, unweighted.
- `high_PCI6`: "High" if `PCI6_hs17` is above the median weighted by exports 2012 to 2018 (column `exports 2012 to 2018`), "Low" otherwise. Same rule as `high_PCI`.
- `PCI4_z`: `PCI4_hs17` minus the mean of `PCI6_hs17`, divided by the standard deviation of `PCI6_hs17` (same scale as `PCI6_z`).
- `PCI6_dev`: `PCI6_z − PCI4_z`. It is the complexity of the product relative to its heading, so that `PCI6_z = PCI4_z + PCI6_dev`.
- `ubiq_z`: `ubiq_hs17` standardized across the agricultural products with data.

No terciles and no simple median of PCI6 are built.

What `10.3` documents for V6-03: (a) source, version, revision, years and download date; (b) coverage of each column: products with and without data and their share in exports 2012 to 2018 and, for `PCI6_hs12`, how many products average several codes and how many inherit; (c) Spearman correlations between `PCI6_hs17`, `PCI4_hs17`, `PCI6_hs12`, `PCI_p` and `ubiq_hs17`; (d) cross-tabulation of `high_PCI6` with `high_PCI`; (e) composition of each group of `high_PCI6` by `type`, `stage` and `rauch_bin_con`, in products and in exports, as in `3.0`.

**V6-04. Binary Rauch.** Priority: core. Role: construction. Deliverable: columns in `Product classifications` and a block in `10.3`. Why: for the exports of local firms the gap is between differentiated products and the rest (0.26 against 0.47 and 0.43, `3.2`, FE4); for those of all firms, between homogeneous products and the rest (0.89 against 0.76 and 0.78). The binary is fixed before running.

- `rauch_bin_con`: "Differentiated" if `rauch_full_con` is Differentiated; "Not differentiated" if it is Homogeneous or Reference priced; "Not classified" for the products without a class. With the columns of today: 295, 557 and 8 products.
- `rauch_bin_lib`: the same with `rauch_full_lib`: 244, 608 and 8 products.
- `rauch_hom_con`: "Homogeneous" (189), "Not homogeneous" (663), "Not classified" (8). Only for a descriptive panel (V6-06, panel D).
- The three classes (`rauch_full_con`, `rauch_full_lib`) are kept and are reported next to the binary in the regressions (V6-06, panel C) and in the event studies (V6-14).
- In `10.3`: products and share in exports of each group, and cross-tabulation with `type` and `stage`.

Other new columns of `Product classifications` in the core: `hs_n1`, which flags the HS 2017 codes with a non-one-to-one correspondence with HS 2012 (V6-10, block 4). The terms `DIFF`, `FIELD` and `PROC` of V6-07 are derived from existing columns and are not new columns.

### B.4 Regressions

All use the templates of A.6. In a cut, the "Not classified" products enter as a separate group, as in v5, and are not interpreted.

**V6-05. Association by complexity with PCI6.** Priority: core. Role: `primary` in two rows (T2 and T3); the rest according to the panel. Deliverable: sheet `11.1 Complexity, PCI6`. Why: it is the test of whether there is a complexity axis. Today it rests on a four-digit index and on errors clustered by origin–destination pair, and for local firms it is not significant in any of the four specifications with FE6 (p 0.16, 0.29, 0.48 and 0.53, `3.1`).

- **A. Continuous.** Full ASOC, continuous form, with `PCI6_z`. T2 is `ln XL` on `ln N` and `ln N × PCI6_z`, FE4; T3 is the same with `ln X`. For those two rows and their versions with FE5 and FE6, three p-values are reported: CL-od, CL2 and CL2-hs6. If the p with CL2 of T2 or of T3 falls between 0.01 and 0.10, a permutation p is added: 1,000 reassignments of `PCI6_z` across products within `stage` × `type`. The other rows of the panel are `robustness`.
- **B. Two groups.** Full ASOC, by groups, with `high_PCI6`. `robustness`.
- **C. Between headings and within the heading.** `ln X` and `ln XL` on `ln N`, `ln N × PCI4_z` and `ln N × PCI6_dev`; FE4 and FE6. If only the term of `PCI4_z` is different from zero, the gradient is between families of products; if that of `PCI6_dev` is, there is complexity within the family. `exploratory`.
- **D. Another revision.** Panel A with `ln N`, FE4 and FE6, using standardized `PCI6_hs12` instead of `PCI6_z`. `robustness`.
- **E. Results of v5 with the new cluster.** With CL2 and changing nothing else: `ln X` and `ln XL` on `ln N` and `ln N × PCI_p` (continuous panel of `3.1`), and on `ln N ×` type of production (`v4 E4f`); FE4 and FE6. It separates the effect of changing the index from that of changing the cluster, and gives the correct inference for type of production, which is the replacement axis if complexity fails (Part C). `robustness`.
- **F. Margin of the MNEs.** `ln XM` and `ln (XM / N)` on `ln N` and `ln N × PCI6_z`; FE4 and FE6; cells with `N ≥ 1`. `X` includes what the additional MNE exports: if the gradient is in `XM / N`, it speaks of the size of the marginal MNE and not of local firms. `exploratory`.
- **G. Groups instead of firms.** `ln X` and `ln XL` on `ln G` and `ln G × PCI6_z`, FE4, cells with `G ≥ 1`. A group with several affiliates counts several times in `N`. `robustness`.
- **H. Weighted.** `ln X` on `ln N` and `ln N × PCI6_z`, FE4, weighted by the average 2012 to 2018 exports of the `odp` cell. A single column. `descriptive`.

**V6-06. Association and location by binary Rauch.** Priority: core. Role: `secondary` in one row (S1); the rest `exploratory` or `descriptive`. Deliverable: sheet `11.2 Rauch binary`. Why: it is the analogous story closest to that of complexity, and the binary and the three classes have to be read with the same inference.

- **A.** Full ASOC, by groups, with `rauch_bin_con`. S1 is the row `ln XL` on `ln N`, FE4: p of equality between "Differentiated" and "Not differentiated".
- **B.** The same with `rauch_bin_lib`.
- **C. Three classes, side by side.** Full ASOC, by groups, with `rauch_full_con`, with the three pairwise p-values of equality. It is `3.2` with CL2.
- **D.** `rauch_hom_con`: `ln X` and `ln XL` on `ln N`, FE3 to FE6. `descriptive`, because the cut was chosen after seeing the three classes.
- **E.** Full LOC with `rauch_bin_con` and with `rauch_bin_lib`. For `rauch_bin_con`, in addition, the weighted and conditional variants.

**V6-07. Horse race between traits and leave-one-out.** Priority: core. Role: `primary` in two rows (T4); the rest `robustness`. Deliverable: sheet `11.3 Product traits together` and figure `v6_fig5`. Why: 83 percent of the exports of high PCI are from the processing stage (our calculation from sheet `Product classifications`). It has to be known whether the interaction with complexity survives when its neighbors enter and whether it depends on one product or on one origin.

- **Terms:** `PCI6_z`; `DIFF` = 1[`rauch_bin_con` = Differentiated]; `FIELD` = 1[`type` = Field crops]; `PROC` = 1[`stage` = Processing]; `ubiq_z`.
- **Sample common to all columns:** cells with `N ≥ 1` whose product has `PCI6_z`, a Rauch class and a classified stage. The columns with `ubiq_z` use, in addition, only products with ubiquity and state their observations.
- **Regressions:** `ln X` and `ln XL` on `ln N` and `ln N ×` the terms of each column; FE4 and FE6; CL2. Twelve columns per dependent variable and FE set: (1) to (5), each term alone; (6) to (9), `PCI6_z` with each of the other four; (10) `PCI6_z`, `DIFF`, `FIELD` and `PROC` together; (11) column (10) plus `ubiq_z`; (12) column (10) plus `ln N ×` origin dummies. T4 is the coefficient of `ln N × PCI6_z` in column (10) with FE4, for `ln X` and for `ln XL`.
- **With `D`:** the same twelve columns only for `ln XL` (cells with `XL > 0`), FE4 and FE6. For all firms it is not requested: with `D` there is no difference by complexity in medians or in terciles (0 of 12, `3.1`).
- **Leave-one-out:** `ln X` and `ln XL` on `ln N` and `ln N × PCI6_z`, FE4, CL2, excluding one at a time the ten products with the largest exports 2012 to 2018 and one at a time the nine origins. That is 19 coefficients per dependent variable, in a table and in the figure.

**V6-08. Location with PCI6 and concentration.** Priority: core. Role: `primary` in one row (T1); the rest `robustness` and `descriptive`. Deliverable: sheet `11.4 Location, PCI6`. Why: "more present in complex products" rests today on `S_opy` estimated over all cells, whether or not they have an MNE (24,911 observations, against 16,983 with `N ≥ 1`, `3.1`), so that part of the larger share is larger presence; and nothing is weighted by value.

- **A.** Full LOC with `PCI6_z` and with `high_PCI6`. T1 is `S_opy` on `PCI6_z` with FL1.
- **B.** The same, weighted by `X_opy`.
- **C.** `S_opy` conditional on `N_opy ≥ 1`, with `PCI6_z` and with `high_PCI6`, FL1 to FL3.
- **D. Concentration** (table, `descriptive`). By group of `high_PCI6`, `rauch_full_con`, `rauch_bin_con` and `type`: products; `opy` cells with `X > 0` and share with `N ≥ 1`; mean `N` and `G` in the cells with `N ≥ 1`; share of the MNEs in value (sum of `XM` over sum of `X`, 2012 to 2018); share of `top20` in MNE exports; mean `HHI_opy`, computed across all exporters of the cell; mean share of the largest exporter. `top20` are the affiliates of the twenty groups with the largest agricultural exports of foreign affiliates in the nine origins, 2012 to 2018. It is used only in static tables, never to define an event.

**V6-09. Closing capital intensity.** Priority: core. Role: `descriptive`. Deliverable: new columns in `1.1`, `1.2` and `2.2`, with no new sheets. Why: to close the capital block with the two readings, by cell and in value, and with the slope without the group that generates it.

- **`1.1` and `1.2`:** next to the columns of `D_opy` and of `S_opy` on `lnkl` with FL1, by stage, the same regression weighted by `X_opy`. That is four columns.
- **`2.2`:** slope of the coefficients by group on the log of capital per worker, weighted and unweighted, FE4, excluding in the farm stage group 21 of `2.3` (oilseeds and grains, US$261 thousand per worker, 48.6 percent of the exports of the stage) and in the processing stage group 45 (wet corn milling and oilseed processing, US$250 thousand, 38.0 percent).

### B.5 Event studies by level of aggregation

#### B.5.1 Table of levels

In v5 the event studies were run on three panels of cells: A (origin × product), B (origin × destination × product) and E (a subset of B). None at the level of heading, chapter, type of production, origin–destination pair or firm. The table says what is run now, what is left for v7 and what is not run, with the reason.

| Level | Unit | Question it answers | Decision | Reason | Where |
|---|---|---|---|---|---|
| N1 | origin × HS6 product (cells A, redone) | What changes for the local firms of the product after the first MNE? | **v6, core** | It is the right unit for the question; the panel exists and only the selection of controls changes | V6-11, V6-12, V6-14 |
| N2 | the same product across origins (N1 with product × year, EV9) | Is the jump of new local exporters in the entry year a shock to the product? | **v6, core**, with the support first | The only test against a shock common to the product; it can be left without support | V6-12 |
| N3 | ring: the other HS6 of the heading, same origin | Does entry reach the local firms of neighboring products? | **v6, second tier** | It measures spillovers and controls for reclassifications, but it needs a new panel and does not decide the story | V6-19 |
| N4 | origin × HS4 heading (cells H) | Does the result survive aggregating products? | **v6, core**, if there are 150 or more treated headings | Immune to code changes within the heading; few events, and selected ones | V6-15 |
| N5 | origin × chapter; origin × type of production | none as an event study | **Not run**; only the count | With MNEs in 47 percent of agricultural exports, almost every cell would have an MNE since 2012 and there would be no first entries; the count verifies it | V6-10 |
| N6 | origin × destination × product (cells B, redone) | Is the link specific to the destination, as the regressions measure? | **v6, core** | The only level with a corresponding regression (EV3 = FE4, EV6 = FE5, EV7 = FE6) | V6-13, V6-14, V6-16 |
| N7 | new destinations: discrete-time hazard, replacing cells E | Do local firms start exporting to new destinations? | **Not requested in this round**; v7 if the "entry into markets" step is kept | High cost, it does not admit a pre-trend test and the candidate story does not need it | Part E |
| N8 | origin × destination pair | Do MNEs open markets for the origin? | **Not run**; only the count | Rare events, in marginal markets | V6-10 |
| N9 | local firm × product | What happens to the local firms that were already exporting? | **v7** | It is the right design for the incumbents, but it is a round in itself | Part E |
| N10 | local firm, by exposure | Do the more exposed firms change their product basket? | **Not run** | Exposure is endogenous | Part E |

No event studies are run by country (405 treated cells in nine origins, `7.2`): the treated cells by origin and cohort are reported and one origin is excluded at a time (V6-12). The cells E of v5 are not redone.

#### B.5.2 Before estimating: universe and support

**V6-10. Table of universe and support.** Priority: core. Role: `descriptive`, no estimations. Deliverable: sheet `10.2 Universe and support`, in five blocks. Why: today it is not known what the 405 treated cells of the main sample represent (out of 1,254 with a first entry, `7.2`), or whether there are enough events at the other levels.

1. **Cells by status, levels A and B.** Statuses: MNE since 2012; first MNE in 2013; cohorts 2014 to 2018, one by one; never treated. For each status: number of cells with `R0` and with `R(g)` (for the never treated, how many satisfy `R(g)` in each `g`), by origin, and exports 2012 to 2018 with their share in the agricultural total.
2. **The same count at the other levels:** H (origin × HS4 heading), origin × chapter, origin × type of production and origin–destination pair. It decides N4 (threshold: 150 treated headings with `R(g)`, adding up cohorts) and documents N5 and N8.
3. **Who enters.** For each first entry in A, with `R0` and with `R(g)`: whether the group of the entrant already exported from the origin in `g − 1` another HS6 of the same heading, another heading of the same chapter, another agricultural product, or nothing; number of distinct entrant groups; cells where two or more MNEs enter in the same year; distribution of `ent_big` and `ent_incumbent` (V6-14).
4. **HS codes with a non-one-to-one correspondence.** Column `hs_n1` in `Product classifications`: 1 if the HS 2017 code has no one-to-one correspondence with HS 2012 in the UNSD table. Number of first entries (A and B) and of new local exporters (`NEWL`) that fall in those codes, by cohort. Reason: the jump of `NEWL` in the entry year is in cohorts 2014 (+0.42, p 0.03) and 2017 (+0.68, p 0.01) (our calculation from sheet `4.4`), and 2017 is the year in which HS 2017 enters into force.
5. **Alternative events, counts only,** by cohort, in A and in B: "second MNE" (exactly one MNE in `g − 1` and in `g − 2`, two or more in `g`) and "last MNE leaves" (MNE in `g − 1` and in `g − 2`, none in `g` or in `g + 1`). In B, in addition, how many first entries are of each type of V6-13 and how many controls are pure and how many exposed. It decides V6-21 and V6-30 (threshold: 300 events in A).

#### B.5.3 Design common to all levels

- **Sample, event, equation, window, average, pre-trend test and placebo:** those of A.7, without exceptions.
- **Estimators:** aligned stacked estimator by OLS; PPML for `XL_ppml`, `NL` and `NEWL`; HonestDiD redone on the aligned stacked estimator, only for `NEWL` and `anyXL` in N1. The other estimators of v5 are not run again; their numbers go in the "v5" column.
- **Reporting:** that of A.8.
- **Heterogeneity:** never by split sample. A single estimation per cut, with `Treat × k ×` group, fixed effects common to the groups and an equality test (V6-14). Product cuts allowed: `high_PCI6`, `rauch_bin_con`, `rauch_full_con` and `type`. Entrant cuts allowed: `ent_big` and `ent_incumbent`. No other.

#### B.5.4 N1: origin × product

**V6-11. Product cells with aligned stacks.** Priority: core. Role: `primary` in two rows (T5 and T6); the rest `exploratory`. Deliverable: sheet `12.1 Product cells, aligned`; figures `v6_fig1` and `v6_fig2`. Why: the `g_ps` rule is not aligned by cohort. The pre-period coefficients of `Local firms export (0/1)` (−0.19, −0.11 and −0.02, `4.1`) are those that this mechanism produces, and they disappear when the controls are aligned by entry year (CEM, p 0.26 and 0.54, `4.8`).

- **Event:** first MNE in the `op` cell (A.7). **Controls:** never treated with `R(g)`. **FE:** EV2. **Cluster:** CL-op.
- **Outcomes:** full list (A.3), all cells. T5 is `NEWL`, average 0 to 2. T6 is `anyXL`, average 0 to 2, with its 95 percent interval.
- **By cohort:** coefficients by cohort and the two averages (A.7, point 9), for the short list.
- **Persistence:** `N` and `D` by event time, and share of treated cells with `D = 1` in `k = 1` and in `k = 2`. In v5 only 171 of 405 entries are still there the following year (`7.2`): what is estimated is the effect of a first appearance, not that of sustained presence.
- **Reading caveat:** with the 0 to 2 window the clean result of v5 falls from 0.25 to 0.18 (our calculation from sheet `4.1`, without covariances). The change of window is fixed now, before running.

#### B.5.5 N2 and the robustness of the primary result

**V6-12. Robustness of new local exporters.** Priority: core. Role: `robustness`; the row with EV9 is `secondary` (S2). Deliverable: sheet `12.2 New exporters, checks`, one row per variant with the average 0 to 2, its standard error, the pre-trend p and the treated cells. Why: it is the only result that passes pre-trends and placebo in v5, with a t statistic close to 2. It jumps in the entry year and is almost zero the following year (0.28 and 0.04, `4.1`), which is what a shock common to the product would produce; and with the linear-trend restriction of HonestDiD the interval already includes zero ([−0.17, 0.52], `7.1`).

All rows are `NEWL` in N1 with the design of V6-11, changing one thing only:

1. **Fixed effects:** EV3, EV4, EV8 and EV9. For EV8 and EV9 the support is reported first: treated cells that have in their stack at least one control of the same heading (EV8) or of the same product in another origin (EV9). The row with EV9 is level N2.
2. **Rule:** `R3(g)` and `R0`, one row each.
3. **Fixed composition** (A.7, point 12).
4. **PPML.**
5. **Fixed window:** `NEWL_fw`. Cohort 2014 is left without a base year and drops out; cohort 2015 is left without pre-period coefficients. The row states it.
6. **Without large cells:** without the 1 percent of cells with the most local exporters in `g − 1`.
7. **Cluster:** by HS6 product, and by entrant group (each control cell is its own cluster).
8. **Without one origin:** nine rows, one per excluded origin.
9. **Without the 2017 cohort.**
10. **Without the products with `hs_n1 = 1`.**
11. **Without the doubtful new exporters:** `NEWL` without the firms flagged `big` or `dest_subset` (V6-17).
12. **HonestDiD** on the aligned stacked estimator: interval with the linear-trend restriction and breakdown value, as in `7.1`.

For `anyXL` (T6) only rows 2, 3 and 12 are repeated.

#### B.5.6 N6: origin × destination × product

**V6-13. Destination cells with aligned stacks, split event and the fixed effects of the regressions.** Priority: core. Role: `exploratory` (with the exception stated in Part C). Deliverable: sheet `12.3 Destination cells, aligned`; figure `v6_fig3`. Why: the event of B mixes two treatments (an MNE that arrives at the product, and one that already exported the product to other destinations and adds this one) and its controls include destinations of products that do have an MNE. With that, B fails pre-trends (p 0.000 in almost all outcomes, `5.1`). In addition, FE6 has no event study and FE5 only an approximate one (EV5).

- **Event:** first MNE in the `odp` cell (A.7 with `u = odp`; `R(g)` is evaluated with the exports of the `odp` cell). It is split into two types: **(i) MNE new to the product**, when `t0_odp = t0_op`; **(ii) expansion of destinations**, when the `op` already had an MNE in some year before `t0_odp`.
- **Controls:** never-treated `odp` cells with `R(g)`, separated into **pure** (their `op` had no MNE in any year) and **exposed** (their `op` had an MNE in some year).
- **Cluster:** CL-B.
- **Panel A. All events, all controls, EV3.** Full list. It is the aligned version of `5.1` and the base of the bridge table.
- **Panel B. Ladder of fixed effects.** Short list with EV3, EV6 and EV7, all events and all controls. With EV6 and EV7 it is reported how many treated cells remain identifying.
- **Panel C. Event (i) with pure controls, EV3.** Short list. It measures the arrival of the MNE at the product, seen in the destination.
- **Panel D. Event (ii) with EV6,** all controls. Short list. It measures the differential effect of the destination within the same product and year.

#### B.5.7 Heterogeneity

**V6-14. Heterogeneity by interaction.** Priority: core. Role: `exploratory`; one row is `secondary` (S3). Deliverable: sheet `12.5 Heterogeneity`; figure `v6_fig7`. Why: in v5 the groups are estimated by splitting the sample, with no equality test or placebo by group, and in product cells no difference by complexity can be told apart from zero (new local exporters: 0.276 with SE 0.130 in low PCI against 0.196 with SE 0.193 in high PCI, `4.0`).

- **Estimation:** a single one per cut and outcome, with `Treat × k ×` group and the main fixed effects common to the groups. Two levels: N1 (design of V6-11) and N6 in the version of panel C of V6-13.
- **Product cuts:** `high_PCI6`; `rauch_bin_con`; `rauch_full_con` (the three classes, next to the binary); `type`. **Outcomes:** `NEWL`, `anyXL` and `lnX`, plus the first stage.
- **Entrant cuts** (N1 only; outcomes `anyXL`, `NEWL` and `lnXL`): `ent_big` = 1 if the agricultural exports of the entrant group in the nine origins in `g − 1` exceed the median of the treated cells; `ent_incumbent` = 1 if the entrant group already exported another agricultural product from the same origin in `g − 1`. If several MNEs enter in `g`, the group with the largest exports in `g − 1` applies. The two traits are measured before entry and replace the "large entries" of v5, defined with the share in the entry year, which is an outcome. S3 is the effect on `anyXL` in the group `ent_big = 1` and its p of equality with the other group.
- **Reported by group:** average 0 to 2; p of equality of the average between groups; p of equality of the pre-period coefficients between groups; placebo of the group; first stage; baseline means; products, treated cells and controls, with the sum equal to the total. In N1 the p of equality is given with CL-op and with CL-hs4.
- **Reading rule:** a cut whose groups have different pre-period coefficients (p of equality below 0.10) is not interpreted. In product cells the minimum detectable difference between two groups is about 0.65 exporters (our calculation), more than twice the overall effect: there, a "no difference" is not informative.

#### B.5.8 N4: origin × heading

**V6-15. Origin × HS4 heading cells.** Priority: core, conditional on the support. Role: `exploratory`. Deliverable: sheet `12.6 Heading cells (HS4)`; figure `v6_fig6`. Why: it responds to the request to run the event studies at another level of aggregation and it is immune to code changes within the heading, which are a possible explanation of the jump of the 2017 cohort.

- **Condition:** 150 or more treated headings with `R(g)` (V6-10, block 2). With fewer, only the counts are delivered and the sheet says "not estimable: too few entered cells".
- **Cell:** `oh`; `X` and `XL` are summed over the HS6 of the heading, and `N` and `NL` count distinct firms (a firm that exports several HS6 counts once). **Event:** first MNE that exports any HS6 of the heading (A.7 with `u = oh`). **Controls:** never-treated headings with `R(g)`. **FE:** EV2; variant EV4. **Cluster:** CL-oh.
- **Outcomes:** short list, with "new" defined in the heading (A.3).

### B.6 Bridge table between regressions and event studies

**V6-16. Bridge table.** Priority: core. Role: `diagnostic` (DG). Deliverable: sheet `12.4 Bridge to regressions`; figure `v6_fig4`. Why: the regressions use contemporaneous presence (`D`) or the number of MNEs (`ln N`) in all cells; the event studies use the first appearance of an MNE in cells with prior history, and that appearance is transitory. Today it cannot be known whether the differences come from sample, margin, dynamics or implementation. In the only cross where the fixed effects already coincide (destination cells, EV3 = FE4) the regression gives 0.656 for `ln X` (`v4 E2b`) and the event study 0.421 (`4.0`, rows of `5.2`).

#### B.6.1 The corresponding regression of each event study

| Event study | Corresponding regression | Does it exist in v5? |
|---|---|---|
| N6 with EV3 | `Y_odpt` on `D_odpt` with FE4: `v4 E2b` (`ln X`), `v4 E2d` (`ln XL`), `v4 E2f` (`ln NL`), column FE4 | Yes for the logs. For `anyXL` and `NEWL` it is redone in the rectangular panel (P0) |
| N6 with EV6 and with EV7 | the same, columns FE5 and FE6 | Yes |
| N1 with EV2 | `Y_opt` on `D_opt` with fixed effects of `op` cell and origin × year | No. It is requested here (P0 of level A) |
| N4 | none | Not requested |
| none | regressions with `ln N` (`v4 E2a`, `v4 E2c`, `3.1`, V6-05): the margin where the complexity gradient lives | Its event study would be the "second MNE" event (V6-21, second tier) |

#### B.6.2 Columns

Each column changes one thing only relative to the previous one.

| Col. | Estimation | What changes | If it differs from the previous one, the difference comes from |
|---|---|---|---|
| P0 | `Y` on `D`, fixed effects of the regression, all cells | starting point | not applicable |
| P1 | P0 without the cells with an MNE in 2012 or 2013 | the always-treated cells drop out | composition: cells with an established MNE |
| P2 | P1 in the sample of the event study: treated and control cells of the stacks, each cell once, 2012 to 2018 | rule of prior history | sample rule |
| P3 | P2 with `Post` instead of `D`. Next to it: first stage (`D` and `N` on `Post`, same fixed effects and sample) and the ratio P3 / first stage of `D` | regressor | margin (first entry against presence) and persistence |
| P4 | Static difference in differences in the aligned stacked design: `Y` on `Post × Treat`, fixed effects by stack | alignment and weights | alignment by cohort and weighting |
| P5 | Average 0 to 2 of the coefficients of the stacked event study (V6-13 panel A, or V6-11). In a second row, the average 0 to 4 | from static to dynamic | dynamics and horizon |
| P6 | Coefficients from −3 to +2 | it is not a column: it is figure `v6_fig4` | shape: jump, build-up or reversal |

#### B.6.3 Levels, outcomes and sample

- **Level B:** fixed effects FE4 = EV3. Cluster CL-B in all columns. Sample of P2 to P5: the stacks of V6-13, panel A.
- **Level A:** fixed effects of `op` cell + origin × year (EV2). Cluster CL-op. P0 is a new regression on the full `op` panel. Sample of P2 to P5: the stacks of V6-11.
- **Outcomes:** `lnX`, `lnXL` and `lnNL` on positive values; `anyXL` and `NEWL` on the rectangular panel with zeros, also in P0. For each outcome the sample is the same from P2 to P5.
- **First all cells.** Then, the same columns with the regressor interacted with `high_PCI6` (High and Low).
- **Reference column:** the number of v5 (destination cells, EV3, OLS, average 0 to 4, `5.2`).
- **Implementation check:** P2 is computed twice, once starting from the code of the regressions and restricting the sample, and once starting from the panel of the event study. They must coincide. Both are reported.

#### B.6.4 Three estimations that complete the sheet

1. **`Dotros`.** `Y_odpt` on `D_odpt` and `Dotros_odpt`, FE4, all cells, the five outcomes, CL-B. If the coefficient of `Dotros` is close to zero, the association is specific to the destination and the product cells need not show what the regressions show.
2. **Gradient when aggregating destinations.** `ln X_opt` and `ln XL_opt` on `ln N_opt` and `ln N_opt × PCI6_z`, fixed effects of `op` cell + origin × year, cells with `N_opt ≥ 1`, cluster CL-hs4.
3. **Event study on `D` itself,** which switches on and off: dCDH (`did_multiplegt_dyn`) with treatment `D_odpt`, cells B, nonparametric trends by origin–destination pair, effects from 0 to 2 and placebos from −3 to −2, for `lnX` and `lnXL`. It is the direct counterpart of the regression on `D`. If it is not estimable, the sheet says so.

#### B.6.5 Reading rule

- If P0 and P2 are similar and P3 divided by the first stage is similar to P2, the event study reflects the regression and the gap between the two is the persistence of the MNE.
- If P1 differs from P0, part of the association of the regressions comes from cells with an established MNE, which no event study of first entry can see.
- If P4 differs from P3, the problem is one of alignment or of weighting. If P5 differs from P4, it is dynamics.
- If the two versions of P2 do not coincide, there is an implementation problem and no event study is read until it is resolved.
- That they coincide does not make either of the two causal: they share the selection.
- "Similar" has an operational definition in Part C (row DG).

### B.7 Who the new local exporters are and validation of the "local" class

**V6-17. Table of new local exporters.** Priority: core. Role: `descriptive`. Deliverable: sheet `12.7 Who the new exporters are`. Why: it is the only clean effect and it is not known what it is: firms that start exporting, firms that already exported other products, noise of one year, or entities linked to the entrant MNE that did not match with Orbis or with D&B. A jump in the entry year that is almost zero the following year is what the last of these would produce.

Prior steps: the answers to questions 6, 11 and 12.

- **Universe:** the stacks of V6-11. Firms counted in `NEWL` in the treated cells in `k = 0`, `1` and `2`, and in the controls of the same stack in the same calendar years.
- **Provenance of each new exporter,** three mutually exclusive categories that add up to `NEWL`, looking back over the same years as `NEWL`:
  - `NEWL_denovo`: it did not export any product from the origin (universe according to question 12).
  - `NEWL_div_hs4`: it exported another HS6 of the same heading.
  - `NEWL_div_other`: it exported only products of other headings.
- **Other flags:**
  - `persist`: it exports the product from the origin again in `t + 1` (no value in 2018).
  - `samedest` (treated cells only): at least one of its destinations in the product was already served, that year or before, by an MNE from that origin in that product.
  - `dest_subset` (treated cells only): all its destinations in the product are destinations of the entrant MNE in the cell in `g`.
  - `big`: its exports of the product in the first year exceed the 90th percentile of the exports per firm and product of the local firms of its origin in that year.
  - Relative size: exports of the first year over the median of the local firms of the cell in that year.
- **Table:** counts, shares and sizes, treated against controls, by `k`. By `high_PCI6` and by `type`, counts only.
- **Validation of "local":** the answer to question 11; the share of `big` in treated against controls; the share of `dest_subset` in treated; and row 11 of V6-12. If the effect falls without those cases, the clean result is in part a classification error.
- **Not requested:** matching by exporter name.

### B.8 Delivery format

**V6-18. Format of the workbook and of the figures, and `Role` column.** Priority: core. Role: documentation. Why: so that each number can be located, filtered and read against its role without opening twenty sheets.

1. **Same workbook.** `WP_paperagro_v6_master_estimates.xlsx` is the v5 workbook with the corrections of V6-02, the new columns and the new sheets. The other sheets of v5 are not redone.
2. **New sheets of the core (14):**

| Sheet | Request | Content |
|---|---|---|
| `10.1 Definitions and answers` | V6-01 | Answers to the sixteen questions |
| `10.2 Universe and support` | V6-10 | Cells by status and level, who enters, HS codes, alternative events |
| `10.3 New classifications` | V6-03, V6-04 | Construction, coverage and correlations of PCI6, PCI4, ubiquity and binary Rauch |
| `11.1 Complexity, PCI6` | V6-05 | Association by complexity (T2 and T3), panels A to H |
| `11.2 Rauch binary` | V6-06 | Association and location by binary Rauch and in three classes (S1) |
| `11.3 Product traits together` | V6-07 | Horse race between traits (T4) and leave-one-out |
| `11.4 Location, PCI6` | V6-08 | Location unweighted, weighted and conditional (T1); concentration |
| `12.1 Product cells, aligned` | V6-11 | Level N1 (T5 and T6), by cohort, first stage, baseline means |
| `12.2 New exporters, checks` | V6-12 | Robustness of T5, with N2 (S2); rows of T6; V6-31 if it is reached |
| `12.3 Destination cells, aligned` | V6-13 | Level N6, panels A to D |
| `12.4 Bridge to regressions` | V6-16 | Bridge table in B and in A (DG), `Dotros`, gradient at the `op` level, dCDH on `D` |
| `12.5 Heterogeneity` | V6-14 | Interactions by four product cuts and two entrant cuts (S3) |
| `12.6 Heading cells (HS4)` | V6-15 | Level N4 |
| `12.7 Who the new exporters are` | V6-17 | Table of new local exporters and validation of "local" |

3. **Sheets of the second tier:** `13.1` to `13.12`, with the names given in Part D.
4. **Existing sheets that change:** `Product classifications`, `1.1`, `1.2`, `2.2` and `All estimates` (new columns); `Main results`, `Glossary`, `Technical notes`, `Read me`, `4.0`, `4.2`, `4.4`, `5.4`, `4.10`, `5.9`, `6.6`, `3.1`, `3.2`, `8.0` and `8.2` (corrections and additions).
5. **Header of each new sheet:** request (V6-xx), cut column, sample, FE or EV code, cluster code and `Role`.
6. **`All estimates`:** one row per coefficient, as today, with five new columns: `Request` (V6-xx), `Role`, `FE code` (FE3 to FE6, FL1 to FL3, EV2 to EV9), `Cut variable` (name of the column of `Product classifications`, or `ent_big`, `ent_incumbent`) and `Group`. In the rows of v5 they stay empty.
7. **`Product classifications`:** thirteen new columns (from 88 to 101): `PCI6_hs17`, `PCI4_hs17`, `ubiq_hs17`, `PCI6_hs12`, `PCI6_z`, `high_PCI6`, `PCI4_z`, `PCI6_dev`, `ubiq_z`, `rauch_bin_con`, `rauch_bin_lib`, `rauch_hom_con` and `hs_n1`. In the second tier, `bico` and `processing_degree_v2`.
8. **`Main results`:** a new table at the top, "Primary set", with one row for each test T1 to T6 and for DG: estimate, standard error, 95 percent interval, p, criterion and whether it is met. Below it, S1 to S3. The eight points of v5 stay after it, with the corrections of V6-02.
9. **`Glossary`:** FE1 to FE6, FL1 to FL3, EV1 to EV9, the cluster codes, aligned stack, `R(g)`, `R3(g)`, `R0`, `Post`, `Dotros`, `G`, PCI6, ubiquity, binary Rauch and `Role`.
10. **`Technical notes`:** source and revision rule of the PCI (V6-03); definition of the stacks (A.7); confirmed definitions of `NEWL`, `EXITL` and `SURVL`; list of corrections to the v5 workbook.
11. **`Read me`:** the new sheets in the table of contents, with the code V6-xx in the column "Code in the estimation plan".
12. **Figures:** folder `figures_v6\`, one file per figure in PDF and PNG, with the format of v5 (95 percent intervals, base year −1, note with sample, fixed effects and cluster). The data go to `8.2` and the index to `8.0`.

| Figure | Content | Request |
|---|---|---|
| `v6_fig1` | N1: `NEWL` and `anyXL`, coefficients from −3 to +2, with the v5 series next to them | V6-11 |
| `v6_fig2` | N1: `NEWL` by cohort | V6-11 |
| `v6_fig3` | N6: `lnXL` and `anyXL`, panels C and D | V6-13 |
| `v6_fig4` | Bridge: coefficients from −3 to +2 (P6) of the five outcomes, in B and in A | V6-16 |
| `v6_fig5` | Leave-one-out: 19 coefficients of `ln N × PCI6_z` per dependent variable | V6-07 |
| `v6_fig6` | N4: `NEWL` and `anyXL` | V6-15 |
| `v6_fig7` | Heterogeneity in N1: `NEWL` and `anyXL` by group, four product cuts | V6-14 |

13. **Record of the round:** an `.md` like that of v5, with what could not be estimated and why.
14. **Code of the three rounds:** folder `code_v4_v5_v6\` (or a zip with that name) with the Python scripts and the Stata do-files of rounds v4 and v5 (those listed in the record of v5: `wp_agro_v4_*.py`, `wp_agro_v4_event.do`, `wp_agro_v5_*.py`, `wp_agro_v5_event.do`) and those of v6, plus a `README` with one line per script in the order of execution. Code only: no data, no intermediate files and no outputs. Why: today the definitions are inferred from the documentation and from the counts; with the code they are verified directly.

## Part C. Primary set and how the results will be read

The primary set is fixed now, in writing, and approved by the team before the estimations are run.

### C.1 Primary tests and diagnostic

| Test | Piece of the story | Exact row | Sheet | Criterion |
|---|---|---|---|---|
| T1 | Presence: "more present in complex products" | LOC, `S_opy` on `PCI6_z`, FL1, CL-hs6, unweighted | `11.4`, panel A | Positive, p < 0.05; same sign weighted by `X_opy` and conditional on `N ≥ 1` |
| T2 | Association, local firms | `ln XL` on `ln N` and `ln N × PCI6_z`, FE4, CL2 | `11.1`, panel A | Negative interaction, p < 0.05; same sign with FE5 |
| T3 | Association, all firms | `ln X` on `ln N` and `ln N × PCI6_z`, FE4, CL2 | `11.1`, panel A | Negative interaction, p < 0.05; same sign with FE6 |
| T4 | Horse race | T2 and T3 with `ln N × DIFF`, `ln N × FIELD` and `ln N × PROC` (column 10) | `11.3` | `ln N × PCI6_z` keeps its sign, with p < 0.10 in at least one of the two |
| T5 | Entry of local firms | N1, all cells, `NEWL`, average 0 to 2, EV2, CL-op | `12.1` | Positive, p < 0.05; pre-trend p ≥ 0.10; same sign with EV8, without the 2017 cohort and without the products with `hs_n1 = 1` (`12.2`) |
| T6 | No displacement | N1, all cells, `anyXL`, average 0 to 2, EV2, CL-op | `12.1` | Lower bound of the 95 percent interval above −0.05 |
| DG | Diagnostic | Bridge table, levels B and A, `lnX` and `lnXL`, all cells | `12.4` | The two versions of P2 coincide; P3 / first stage falls within the 95 percent interval of P2; P4 falls within the 95 percent interval of P5 |

**Declared secondaries** (they are read with their p and do not decide):

- S1: `ln XL` on `ln N` by `rauch_bin_con`, FE4, p of equality (`11.2`, panel A).
- S2: T5 with EV9, if there is support (`12.2`, row 1).
- S3: `anyXL` in N1 for `ent_big = 1` and its p of equality with `ent_big = 0` (`12.5`).

### C.2 How the team will read the primary set (fixed in advance)

1. **T2 and T3 fail:** there is no complexity axis. The axis becomes type of production (field crops against horticultural crops: 4 of 4, also with FE6, `v4 E4f`), with the inference of panel E of V6-05.
2. **T4 fails and `FIELD` or `PROC` survive:** the story is "grains and position in the chain"; complexity remains as a label with no content of its own.
3. **T3 passes and T2 does not:** the gradient belongs to the margin of the MNEs and not to local firms; panel F of V6-05 says whether it is the size of the additional MNE. It cannot be written that MNEs "are associated with lower exports of local firms".
4. **T1 fails:** "more present in complex products" falls.
5. **T5 fails:** the event-study section is left with the methodological piece (the comparison rule) and with the nulls.
6. **T6 does not meet the margin:** "they do not displace" becomes "inconclusive". With the design of v5 the lower bound is −0.07 (our calculation from sheet `4.1`), so today it would not be met.
7. **DG does not close:** there is a problem of implementation or of alignment, and no event study is read until it is resolved.

### C.3 What is labeled `exploratory`

- All heterogeneity of event studies in product cells, except S3.
- Every result in destination cells. Exception fixed in advance: if panel C of V6-13 passes pre-trends for `anyXL` (p ≥ 0.10), the interaction of `anyXL` with `high_PCI6` at that level (V6-14) becomes `secondary`.
- The heading level (V6-15) and the whole second tier.
- In the regressions: panels C and F of V6-05, and all of V6-06 except row S1 and panel D, which is `descriptive`.

## Part D. Second tier

It is run only if the core has already been delivered, in this order. The definitions of Part A apply. Everything is `exploratory`, except where indicated. That is twelve more sheets (`13.1` to `13.12`) and two rows in `12.2`.

- **V6-19. HS4 ring (level N3).** Sheet `13.1 Ring of neighbours (HS4)`. Event and controls of V6-11. Outcomes: `NL` and `NEWL` summed over the other HS6 of the same heading and the same origin, excluding the product of the event; the same calculation for the controls. EV2, CL-oh. Variant: only headings with a single treated HS6 in the window. Why: spillover or substitution toward neighboring products, and a test of independence between the cells of N1.
- **V6-20. Decomposition of `NEWL`.** Sheet `13.2 New exporters, parts`. Design of V6-11, all cells, no cuts. Three pairs of outcomes that add up to `NEWL`, with the flags of V6-17: `NEWL_denovo` and `NEWL_div` (= `NEWL_div_hs4` + `NEWL_div_other`); `NEWL_persist` and `NEWL_oneoff` (with and without the flag `persist`, years up to 2017); `NEWL_samedest` and `NEWL_otherdest` (with and without the flag `samedest`). Why: it says what the effect is made of. They are point estimates; no component will have power of its own.
- **V6-21. "Second MNE" event,** if there are 300 or more events in A (V6-10, block 5). Sheet `13.3 Second MNE`. Treated: those of the event defined in V6-10, block 5. Controls: cells with exactly one MNE in all the years of the stack. Stacks, equation, window and averages of A.7; EV2, CL-op, short list; for `lnX` and `lnXL`, in addition, the interaction with `high_PCI6`. Why: it is the event study of the `ln N` margin, where the complexity gradient lives. Its controls condition on the future.
- **V6-22. Leads and lags.** Sheet `13.4 Leads and lags`. Cell `odpy`, 2013 to 2017: `ln X` and `ln XL` on `D` in `t − 1`, `t` and `t + 1`, FE4, CL-od, with the p of the lead. And `Δ ln X` and `Δ ln XL` on `Δ ln N` in `t + 1`, `t` and `t − 1`, cells with `N ≥ 1` in the four years, fixed effects of origin × destination × year; total and with `× PCI6_z` (CL2). Why: check of anticipation in the sample of the regressions and the only dynamic check of the `ln N` margin.
- **V6-23. Destination.** Sheet `13.5 Destination traits`. `hi_d` = 1 if the destination is high income in the World Bank classification of 2012, fixed for the whole period; `lac_d` = 1 if the destination is in Latin America and the Caribbean. `ln X` and `ln XL` on `ln N`, `ln N × hi_d` and `ln N × lac_d`, each interaction alone and together with `ln N × PCI6_z`; FE4 and FE6; CL2. Why: if the gap by complexity is composition of destinations, it falls when interacted.
- **V6-24. Complexity within the stage.** Sheet `13.6 Complexity within stage`. ASOC by groups with the four groups `stage` × `high_PCI6`; `ln N`; `ln X` and `ln XL`; FE4 and FE6; p of equality within each stage. It replaces `3.5`. Why: high PCI is above all processing.
- **V6-25. Position in the chain.** Sheet `13.7 Position in the chain`. Prior step: verify the current BICO list of USDA FAS and its HS revision; if it is not in HS 2017, it is converted with the UNSD table and this is stated. New columns: `bico` (Bulk, Intermediate, Consumer oriented) and `processing_degree_v2` (the current one, with headings 2301 to 2308 and 1701 to 1703 in First processing). ASOC by groups with each one; `ln N`; `ln X` and `ln XL`; FE4 and FE6. In addition, a column (13) in `11.3`: column (10) plus `ln N ×` 1[`bico` = Bulk]. Why: analogous story, bulk against consumer products. `processing_degree_v2` was redesigned after seeing results: `descriptive`.
- **V6-26. Foreign and domestic.** Sheet `13.8 Foreign and domestic`. `ln X` and `ln XL` on `DF = 1[NF ≥ 1]` and `DD = 1[ND ≥ 1]` together, cells with `X > 0`, FE3 to FE6, CL-od. Why: to know whether domestic MNEs are associated differently with local exports.
- **V6-27. Parent market.** Sheet `13.9 Parent market`. `Dhome_odpy` = 1 if an MNE whose parent is in the destination exports in the cell; `Dothm_odpy` = 1 if another MNE exports. Table: share of MNE exports that goes to the country of the parent, by `high_PCI6`, `rauch_bin_con` and `type`. Regression: `ln X` and `ln XL` on `Dhome` and `Dothm` together, FE3 to FE6, CL-od. Why: it separates trade within the group from an information channel by destination. It replaces the test of `4.9`.
- **V6-28. Activity of the MNE,** only if the activity code covers 80 percent or more of the value exported by MNEs (question 13). Sheet `13.10 MNE activity`. `trader` = NACE Rev. 2 division 46, or SIC 50 and 51; `producer` = NACE 01 to 03 and 10 to 12, or SIC 01 to 09, 20 and 21; `other` the rest. Only the table: number of MNEs and share of each class in MNE exports, by `high_PCI6`, `rauch_bin_con` and `type`. Why: it is the only possible direct evidence of "traders in commodities, producers in processed goods". The code is that of the legal entity, not of the product: `descriptive`.
- **V6-29. Twenty groups.** Sheet `13.11 Top 20 groups`. `D20` = 1 if a `top20` affiliate (V6-08) exports in the cell; `Doth` = 1 if another MNE exports. `ln X` and `ln XL` on `D20` and `Doth` together, FE3 to FE6, total and with each regressor interacted with `high_PCI6` (CL2). LOC with a single dependent variable, `D20_opy` (1 if a `top20` affiliate exports in the `opy` cell), on `PCI6_z`, FL1 to FL3. Why: to know whether the gradient is the scale of a few groups.
- **V6-30. "Last MNE leaves" event,** if there are 300 or more events in A. Sheet `13.12 Last MNE leaves`. Treated: those of the event defined in V6-10, block 5 (cohorts 2014 to 2017, because it requires observing `g + 1`). Controls: cells with an MNE in all the years of the stack. Stacks, equation, window and averages of A.7; EV2, CL-op; `lnX`, `lnXL` and `anyXL`. Why: if the link is one of presence, exit must show the opposite sign to that of entry.
- **V6-31. Alternative inference for T5.** Two rows in `12.2`: wild cluster bootstrap (CL-op) and randomization p, permuting 1,000 times the treated status among cells of the same origin and `type`. `robustness`. Why: the primary result has a t statistic close to 2.

## Part E. Not in this round

**Postponed to v7**

| What | Reason |
|---|---|
| Local firm × product (N9) and diversification at the firm level | They are the right designs for the local firms that were already exporting, but each is a round; one is chosen after seeing V6-17 |
| New destinations with a hazard design (N7) | High cost and no pre-trend test; the "entry into markets" step is not requested in this round |
| Perishability | The keyword rule requires reviewing 860 products by hand; `FIELD` in V6-07 already captures the contrast between horticultural and field crops, so only if a residual remains there |
| Unit values | It is not known whether there are quantities; in v6 only question 14 |
| Regions of the parent | It multiplies regressors without a hypothesis that decides |

**Not requested**

| What | Reason |
|---|---|
| Event studies at chapter, type of production and origin–destination pair (N5, N8), and by country | There are no first entries or they are marginal, and 405 cells are not enough for nine origins; only counts (V6-10) and exclusion of one origin at a time (V6-12) |
| Exposure at the firm level (N10) | Exposure is endogenous |
| Cells E as they are (`6.x`) | Pre-trend by construction |
| Full template of event studies for each cut, split sample, cells that export every year (`g_bal`) | On the order of 1,700 rows (our calculation) on non-aligned rules; with 405 cells the split sample does not tell groups apart; `g_bal` requires exporting after entry |
| Cell trends and CEM as designs | The trends absorb the effect; CEM flattens the pre-trend by construction |
| More estimators or variants: Callaway and Sant'Anna, Sun and Abraham, BJS, dCDH with absorbing treatment, Freyaldenhoven, rule of v4, EV1 | They have already served their purpose and do not change the reading |
| Event study of the first foreign MNE against the first domestic one (`4.3`) | Not redone: the domestic row is not informative (SE 0.82 to 0.84) |
| Complexity measured with unit values or a quality ladder | It mixes quality, weight and brand; ubiquity replaces it (V6-03) |
| Spillover test of `4.9` with the main rule | The result has pre-trends and the design is replaced; V6-27 replaces it if it is reached |
| Proxy for traders based on the breadth of the product basket | It does not measure intermediation and does not discriminate: 3.4, 2.9 and 3.1 products per exporter (`9.2`) |
| Row of the soybean chain | Three products in few origins cannot establish "equal" |
| Two-by-two crosses by type and by Rauch; terciles and simple median of PCI6; `lnkl` in the horse race | Cuts that do not decide |
| Regressions and events by activity of the MNE; event by `top20` | Variable not validated; `top20` uses information after entry |
| Distance, agreements, sanitary list and event studies by destination; event study of the parent market | Too many paths; few events |
| Matching by exporter name | It depends on names that may not exist and that must not circulate |
| q-values and specification curves | They are computed by the team from `All estimates`; only the `Role` column is requested |
| More cuts of capital per worker | The capital block is closed with V6-09; the agricultural census tables (E9e) are not requested in this round |
| Redoing `4.5`, `4.6`, `5.5`, `5.6`, `6.3` and `6.4` with PCI6 | They are split-sample sheets; V6-14 replaces them |

## Suggested order of work

From rule 2 of A.1:

1. Sheets `10.1 Definitions and answers` (V6-01) and `10.2 Universe and support` (V6-10), which require no estimation. Nothing is built for V6-03 before the answer to question 15. The counts of `10.2` decide whether V6-15 is estimated (150 treated headings) and, in the second tier, V6-21 and V6-30 (300 events in A).
2. In parallel: the regressions (`10.3`, `11.1` to `11.4`) and the event studies (`12.1` to `12.5`).
3. Last, `12.6` and `12.7`. V6-17 (`12.7`) needs the answers to questions 6, 11 and 12.
4. The second tier (Part D, V6-19 to V6-31, in the order listed there) starts when the core has been delivered.

Everything requested is reported, including nulls and opposite signs (rule 3 of A.1).
