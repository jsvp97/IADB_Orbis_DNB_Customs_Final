# `stylized_facts/` — the pipeline behind *Stylized Facts on Multinational Firms and Trade* (v. 2026-07-29)

Code by **Ignacio Marra de Artiñano** (with Gabriel Scattolo, Sebastián Velásquez, Christian
Volpe). Received 2026-09-03 as `codigos Ignacio/` and moved here **byte-for-byte** (only
the folder names changed: `0_Code` → `stata/`, `0_Code_Python` → `python/`, `Old/` →
`_old/`, scratch files into `_old/`). Nothing in it has been edited; it still points at
Ignacio's machine (`D:\MNEs_Trade`) — see the last section before running anything.

The document it produces: `../docs/stylized_facts_document/Multinational_Firms_and_Trade_2026-07-29.pdf`.
Its LaTeX source lives in Ignacio's Overleaf project *Multinational Firms and Trade*
(`Stylized_Facts/` subfolder; `New_SFs_Analysis/` for the network-facts memo). Not local.

## 1. Two generations of code

| Generation | Where | Role today |
|---|---|---|
| **Stata, May 2026** — `stata/00_master.do`, `01_setup.do`, `10_part0_build.do`, `20_part1_determinants.do`, `30_part2_effects.do`, `40_part3_summary.do` | fork of Sebastián's `MNE_Trade_Analysis_corrected.do` (April 2026; the original is in `stata/_old/`), split into modules. `10_part0_build.do` builds the same cubes as `src/06` Part 0 (`collapsed_{oy,ody,opy,odpy}`, `firm_level_data(_full)`, `firm_year_level`, `firm_dest_year_level`). | **Reference for cube definitions**; not what produced the July document's exhibits. `_sf1_build_and_run.do` and `_sf_explore_dest.do` are the first SF1 / destination explorations, later rewritten in Python. |
| **Python, June–August 2026** — `python/*.py` | everything in the July-2026 PDF. pandas + pyarrow chunked reads of a **parquet** copy of the base, pyfixest for every regression, matplotlib figures, LaTeX fragments written directly (helpers in `_common.py`). | **The live pipeline.** Extend here. |

`_common.py` holds: the path block (§4 below), palette (foreign = navy `#1f3864`, domestic =
light gray `#bfbfbf`), `parquet_chunks()`, `save_figure()` (pdf+png+eps + Overleaf mirror),
LaTeX table writers, `ols_robust()`. `EXCLUDED_ORIGINS = ("ECU",)`.

## 2. Exhibit → script → cache map (the July-2026 document)

| Exhibit in the PDF | Script | Cache it reads (all in Ignacio's `1_Input\Intermediate\`) | Output name |
|---|---|---|---|
| **Fact 1** — Fig. 1 MNE share of export value by origin, foreign vs domestic | `sf1_origin.py` | `sf1_origin_value.dta` (origin×year value cache built by `stata/_sf1_build_and_run.do`) | `fig_sf1_stacked_origin`, `fig_sf1_hbar_*`, `tab_sf1_share_by_country*`, `reg_sf1_*` |
| Table A.3 — origin-year panel, share on ln GDPpc | `sf1_origin.py` | same + `Gravity_V202211.dta` | `reg_sf1_{total,ext,dom}` |
| **Fact 2** — Fig. 2 share by PCI quintile; Fig. 3 by Lall technology category (4 buckets) | `sf3_products.py` | `opy_value_cache.parquet` (origin×HS6×year; built by `sf_explore_products.py`) + `product_characteristics_hs6_2002_adj.dta`, `lall2000_hs2007.dta`, `UNCTAD RHCI…`, `ALP_IPC…`, `RCA_WITS_orig_year.dta` | `fig_sf3_pci_quintile`, `fig_sf3_lall4`; appendix `fig_sf3_{sigma,upstream,quality,rhci}_quintile`, `fig_sf3_lall5`, `fig_sf3_hs_section_<def>`, `fig_sf3_ipc1_<def>`, `fig_sf3_top15_hs2_<def>`, `tab_sf3_*`, `reg_sf3_{total,ext,dom}` |
| Tables A.4, A.5 — ODPY regressions on PCI/upstreamness and Lall dummies | `sf3_odpy_regressions.py` | `odpy_value_cache.parquet` (origin×dest×HS6×year, built in the script from the base) | `reg_sf3_odpy_pci`, `reg_sf3_odpy_lall` |
| **Fact 3** — Fig. 4 foreign-MNE value by parent country, top 15 + Other | `sf2_mne_origin.py` | `sf2_mne_origin_value.parquet` (parent-level value; built from the base) | `fig_sf2_mne_origin` |
| **Fact 4** — Fig. 5 value and parent counts by global affiliate-network size; Table A.6 parent-level regression | `sf6_mne_groups.py` | `nsf_parent.parquet` (from `nsf_prep.py`) + `network_size_by_parent.parquet` (from `build_network_size.py`, which reads the affiliate-level Orbis∪D&B merge) | `fig_sf6_network`, `reg_sf6_network` |
| Fig. 6 product HHI: naive vs grouped by parent | `sf6_mne_groups.py` | `nsf_hs_conc.parquet` (from `nsf_product_conc.py`) | `fig_sf6_hhi` |
| **Fact 5** — Table 1 (intensive/extensive margins, Panels A/B), Table A.7 (value share) | `sf4_presence.py` | `sf4_fdpy.parquet` (firm×origin×dest×HS6×year) | `reg_sf4_main`, `reg_sf4_shares` |
| **Fact 6** — Table 2 distance × MNE × presence; A.8 foreign/domestic; A.9 HQ vs affiliate | `sf5_distance.py` | `sf5_{odpy,opy,ody}.parquet`, `sf4_aff_pairs_matched.parquet` (affiliate presence per (group id, dest)), `intermediate_mne_presence.parquet`, gravity | `reg_sf5_distance`, `reg_sf5_appendix_fordom`, `reg_sf5_appendix_hqaff` |
| (parked) concentration regressions OPY/ODY | `sf6_concentration.py` | `sf6_{opy,ody}.parquet` | `reg_sf6_main`, `reg_sf6_ody*`, `reg_sf6_measures` |
| (memo `New_SFs_Analysis`) network size, cross-country shared parents, Lorenz, product leaders | `nsf_figs.py`, `nsf_lorenz.py`, `nsf_product_leaders.py` | `nsf_*.parquet` | `Graphs/NewSFs/*` |
| (exploration, May 2026) destination cuts, product cuts, per-definition, heat maps origin × destination category | `sf_explore_dest.py`, `sf_explore_dest_by_origin.py`, `sf_explore_products.py`, `sf_explore_products_perdef_quintile.py`, `sf_explore_perdef.py`, `sf_explore_by_def.py` | `ody_value_cache.parquet`, `opy_value_cache.parquet` | `Graphs/Exploration_*` |

Definitions used everywhere here (post-2026-05-23 convention): matched = `_merge_DNB_Orbis == 3`;
`dom` = matched & `iso3_parent == country_orig`; **`ext` = matched − dom** (unknown-parent
firms count as foreign); ECU excluded. Fig. 4 additionally drops unknown-parent firms
(≈ half of foreign-MNE value; stated in its note). This differs from `src/05–14` — see
`../CLAUDE.md` §3.

## 3. Where Volpe's new items plug in (pointer; the plan is `../docs/WORKPLAN_working_paper.md`)

| Item | Plug into | Because |
|---|---|---|
| 1a Figures 1–3 by main parent country | `sf1_origin.py`, `sf3_products.py` | they already draw foreign/domestic bars per origin / per product bucket; they need a cache carrying `iso3_parent` (new cube, workplan §0) |
| 1b more complexity measures for Fig. 2 (σ from Fontagné–Guimbard–Orefice 2022) | `sf3_products.py` merge block (product characteristics, ~lines 90–110) and the `CHARS` list; `stata/10_part0_build.do` §0.5 for the Stata cube | `sigma` (Broda–Weinstein) is already there as an appendix quintile figure — FGO is one more column |
| 1c/1d parent × destination tables and heat map | new script (Python) reading `output/tables/mne_export_destination_cube.dta`; heat-map code to reuse: `sf_explore_dest_by_origin.py` | the cube already exists |
| 1e HQ vs affiliates; MNE counts | `sf5_distance.py` (`g_hq`, `g_aff` groups → Table A.9; promote to main text), `sf4_presence.py` (add counts of HQ-present vs affiliate-present MNEs as regressors) | the HQ/affiliate flags are built at lines 105–176 of `sf5_distance.py` |
| 1f HS6-level shares with descriptions | `sf3_products.py` (`fig_sf3_top15_hs2_<def>` is HS2 — add an HS6 table) + descriptions from `data/raw/JobID-46_Concordance_H3_to_H2.CSV` | |
| 2 agro version | add a `SECTOR` filter to `_common.py` (HS2 01–24) applied inside every chunked read, and a parallel output tree `Graphs/<sector>/…` | every script filters at read time, so one switch does it |

## 4. Running it on this machine (nothing has been run here yet)

Ignacio's environment: Python 3.14, parquet copies of the base and of the Orbis∪D&B merge
in `D:\MNEs_Trade\1_Input\Sebastian_Orbis_DNB_Customs\`, caches in
`D:\MNEs_Trade\1_Input\Intermediate\`, outputs in `D:\MNEs_Trade\2_Output\`, Overleaf
mirror in his Dropbox. **None of that exists here.** What exists here: the base as `.dta`
(20.6 GB), the small inputs in `../data/raw/`, Python 3.10 with pandas/pyarrow/pyfixest,
Stata 18.

To run the Python pipeline here you need, in order:

1. **Paths.** In `python/_common.py` replace the block `ROOT … OVERLEAF_SF` (lines ~22–45)
   so that `ROOT`/`INT`/`OUTPUT` point inside this repo and `PRODUCT`, `GRAVITY`,
   `COUNTRY` point at `../data/raw/` (flat — Ignacio had them in subfolders). The
   constants to use are in `../config/paths.py`. Set `OVERLEAF` to a local folder or make
   `save_figure(..., overleaf_dir=None)`.
2. **The base.** Either (a) convert the `.dta` once to parquet with pyreadstat →
   pyarrow (chunked; ~1–2 h; ~5 GB on disk) and keep `BASE_FILE` pointing at it, or
   (b) swap `parquet_chunks()` for a `pyreadstat.read_file_in_chunks(pyreadstat.read_dta,
   path, chunksize=1_000_000, usecols=cols)` generator (that is what the June version did;
   see `python/_old/Code_20260701_134403.zip`). Option (a) is the right one if more than
   two scripts will run.
3. **Caches.** Every `sf*.py` rebuilds its cache when the file is missing, so the first run
   of each is the slow one (a full pass over the base). Order that avoids duplicate passes:
   `sf_explore_products.py` (→ `opy_value_cache`) → `sf_explore_dest.py` (→
   `ody_value_cache`) → `sf3_odpy_regressions.py` (→ `odpy_value_cache`) →
   `sf2_mne_origin.py` → `sf4_presence.py` (→ `sf4_fdpy`) → `sf5_distance.py` →
   `build_network_size.py` + `nsf_prep.py` + `nsf_product_conc.py` → `sf6_mne_groups.py`.
   `sf1_origin.py` reads a Stata-built cache (`sf1_origin_value.dta` from
   `stata/_sf1_build_and_run.do`) — either run that do-file first or derive the same
   origin×year table from `ody_value_cache` (three lines).
4. **Stata modules** (`stata/`): edit `global root` in `01_setup.do` and `00_master.do`
   (both `D:\MNEs_Trade`), and `global overleaf`. The `$customs`, `$gravity`, `$product`,
   `$country` folders must contain the files named in `10_part0_build.do` §0.5–0.7 (all in
   `../data/raw/` here, flat) and the base.

Keep Ignacio's files unmodified except for these path blocks, so a diff against his copy
stays readable; put new analysis in NEW files (`sf7_*.py`, `wp_*.py`) that import
`_common`.
