# CLAUDE.md — technical spec, `Orbis_DNB_Customs_Final` (empirics of P3)

This file is the file-by-file, column-by-column reference for this folder. It wins on any
factual conflict about data and code. **Status and decisions live in the brain:**
`C:\Sebas BID\_Brain\P3_MNE_Trade_Model.md` (read it first; it is loaded automatically
by the SessionStart hook when a session starts in this folder). The theory side has its
own spec: `..\Orbis_DNB_Customs_Model\CLAUDE.md`.

Entry point for a human: `START_HERE.md`. Work plan: `docs/WORKPLAN_working_paper.md`.

Conventions in this folder: ISO-3 country codes as `iso3` strings; `year` integer; HS 2007
six-digit codes as a string `hs07_6d` (the cubes use `hs6`); values are USD FOB
(`value_fob`, negatives sign-flipped to positive at load).

---

## 1. Where the data live on this machine (2026-09-03)

All paths are centralised in `config/paths.do` (Stata) and `config/paths.py` (Python).
Scripts 09–14 still carry these paths hard-coded at their top; when touching one, switch
it to `do "config/paths.do"`.

| Object | Path | Size | Notes |
|---|---|---|---|
| **THE BASE** — firm × HS6 × dest × year, matched | `C:\Sebas BID\Orbis_DNB_Customs\Base_final_Customs_DNB_Orbis_product_complete.dta` | 20.6 GB | built 2026-04-21 by `src/01`. Byte-identical copy at `..\Orbis_DNB_Customs\Claude\Data\Raw\`. ~101 columns, listed in §2. |
| **Aggregate analysis cubes (v4)** — `collapsed_{oy,ody,opy,odpy}.dta` | **`data/intermediate/v4_cubes/` (this repo, copied 2026-09-03)** | 456 MB | built by `src/06` Part 0 §0.9 (v4 = May-2026 run). Originals in `C:\Sebas BID\Orbis_DNB_Customs\Claude\Data\Intermediate_v4\`; script 13 still reads from there. |
| Firm-level cubes (v4) | `C:\Sebas BID\Orbis_DNB_Customs\Claude\Data\Intermediate_v4\` | 23 MB – 13.8 GB | `firm_year_level` (23 MB), `firm_dest_year_level` (136 MB), `firm_level_data(_full).dta` 13–14 GB, `intermediate_mne_presence.dta` 2 GB (group id × destination presence — needed for HQ/affiliate presence, workplan 1e). Not copied. |
| Small inputs (product characteristics, gravity, concordances) | `data/raw/` (this repo) | 676 MB total | copied 2026-09-03 from `..\Orbis_DNB_Customs\Claude\Data\Raw` and `..\Regresion`. List in §5. |
| Orbis ∪ D&B corporate DB, affiliate level, post-AI | `C:\Sebas BID\Orbis_DNB\IA review\Merge_DNB_Orbis_PostIA_v2.dta` | 38 GB | input to `src/01` and to the parent-network build |
| same, parent level | `C:\Sebas BID\Orbis_DNB\IA review\Merge_DNB_Orbis_par_PostIA_v2.dta` | 10.9 GB | |
| Orbis ∪ D&B v4 (used in the final merge of `src/01`) | `C:\Sebas BID\Orbis_DNB_Customs\Merge_DNB_Orbis_PostIA_v4.dta` | 47.9 GB | |
| Parent network-size tables | `C:\Sebas BID\Orbis_DNB_Customs\Claude\Data\Raw\Merge_DNB_Orbis_{affiliates,parent,total}_total_PostIA_v2.dta` | 5–13 GB | built by `archive/legacy_dofiles/Dofile match Orbis_DNB parents.do` (2026-06-18); `parent_total` carries `total_affiliates`, `n_countries`, `n_sectors` per `name_parent` |
| Customs intermediates | `C:\Sebas BID\Orbis_DNB_Customs\Customs\` | | `exp_fdpt_10c_names_180625.dta` (raw flows with names), `Base_revision_manual_exporters_*` (manual review) |
| Matching intermediates | `C:\Sebas BID\Orbis_DNB_Customs\` root and `IA_review\` | | `list_exporters_*`, `fuzzy_match_*.csv`, `Match_preIA/postIA_*` |
| Orbis raw ownership links | `D:\BID\Orbis\FINAL\Ownership\Txt\Chunky\` (per `src/00_master.do`) | | D: was not mounted on 2026-09-03. `Orbis_DNBformat_v3.dta` (24.9 GB) is at `C:\Sebas BID\Orbis_DNB\` |
| D&B raw vintages | `C:\Sebas BID\*.TXT`, `C:\Sebas BID\DNB 2025.v1.txt` | | |
| Ignacio's copies | `D:\MNEs_Trade\` **on his machine**: `1_Input\Sebastian_Orbis_DNB_Customs\*.parquet` (the base, `intermediate_mne_presence`, `Merge_DNB_Orbis_PostIA_v2`, `firm_level_data_full` converted to parquet 2026-07-01, 107 cols), `1_Input\Intermediate\*.parquet` caches | | none of it is on this machine |
| Stylized-facts document source (.tex) | Ignacio's Overleaf project "Multinational Firms and Trade" (Dropbox of `nnmar`), subfolder `Stylized_Facts/` | | only the PDF is local: `docs/stylized_facts_document/` |

## 2. The base file — columns that matter

`Base_final_Customs_DNB_Orbis_product_complete.dta`, one row per firm × `hs07_6d` ×
`country_dest` × `year` (2006–2022; ARG 2011–19, CHL 2009–22, COL 2010–21, CRI 2010–19,
DOM 2012–19, ECU 2010–19, PER 2010–19, PRY 2012–20, SLV 2006–18, URY 2010–19).

| Column | Meaning |
|---|---|
| `country_orig`, `country_dest`, `year`, `hs07_6d`, `value_fob` | the trade cell |
| `Tax_ID`, `firm_name` | customs identity (Tax_ID is unique within `country_orig`) |
| `_merge_final_review` | **the match flag used by `src/05–14`**: 1 = no match (local firm), 3 = matched to Orbis/D&B after AI + manual review (set in `src/01` lines 554–558 from `company_name != ""`) |
| `_merge_DNB_Orbis` | the match flag **before** the manual top-500 review (`src/01` line 399). **This is what the stylized-facts pipeline uses.** Equivalence with `_merge_final_review` has NOT been tabulated — do it before mixing outputs of the two pipelines. |
| `iso3_parent`, `iso3_subsidiary` | parent and affiliate country (ISO3). `iso3_parent == ""` for roughly half of foreign-MNE export value ("unknown parent"). |
| `company_name`, `subsidiarybvdid`, `guo25` | Orbis names/ids; `guo25` = global ultimate owner BvD id at 25% |
| `dunsnumber`, `globalultimatedunsnumber`, `globalultimatebusinessname`, `globalultimatecountry` | D&B identity and global ultimate |
| `ent_name_par`, `name_par`, `ent_name_aff` | parent/affiliate names (Orbis). Parent-group key used by Ignacio and the parents dofile: `name_parent_adj = upper(trim(coalesce(ent_name_par, globalultimatebusinessname)))` |
| `ID_Orbis_DNB` | `guo25`, or `dunsnumber` when the firm is D&B-only (`_merge_DNB == 2`) — the firm/group id used in network presence |
| `naics_aff_6`, `naics_par_6`, `naics_4_c`, `primary6digitnaicscode` | affiliate/parent NAICS |
| `parent_country`, `parent_country_conf`, `parent_country_flagged` | recovered parent country NAME (script 02 / AI); `src/09` reads them into `pcountry`, `pconf`, `pflag` |
| `Manually_found`, `firm_name_match`, `location`, `ranking` | manual top-500 review fields |
| `MNE_ext`, `MNE_dom`, `MNE_total`, `MNE`, `DOM*` | present in some versions of the base (the April sample has them); scripts recompute them — never trust stored flags |

A 2.5 MB CSV sample with all columns: `C:\Sebas BID\Orbis_DNB_Customs\Example_Base_final_Customs_DNB_Orbis_product_complete.csv` (contains firm names and tax IDs — do not put it in git).

## 3. MNE definitions — TWO conventions, do not mix

| | `src/05–14` (Sebastián, Mar–Aug 2026) | `stylized_facts/` (Ignacio, post-2026-05-23) |
|---|---|---|
| matched flag | `_merge_final_review == 3` | `_merge_DNB_Orbis == 3` |
| `MNE_total` | matched | matched |
| `MNE_dom` | matched & `iso3_parent == country_orig` | same |
| `MNE_ext` | matched & `iso3_parent != ""` & `iso3_parent != country_orig` | **`MNE_total − MNE_dom`** (unknown-parent matched firms count as foreign) |
| origins | ten (ECU included) | **nine — ECU dropped** (`global excluded_origins "ECU"` in `stata/01_setup.do`, `EXCLUDED_ORIGINS` in `python/_common.py`; decided 2026-05-23) |
| where | `src/05_descriptive_stats.do` lines 59–70; copied verbatim into `src/09`, `11`, `14` | `stata/10_part0_build.do` §0.2; `stata/_sf1_build_and_run.do` header; every `python/sf*.py` |

Consequences: Figure 1 of the document (foreign+domestic bars) and Figure 4 (parent
shares, which additionally DROPS unknown-parent firms) sit on the Ignacio convention;
θ_USA = 0.134, the 9.2 % share-to-parent and Cov(θ,S) sit on the Sebastián convention.
The working paper must pick one and say so.

## 4. Scripts

### 4.1 `src/` — Sebastián's pipeline (Stata 18 + Python)

Run order is the number. `00_master.do` sets `$root` = this folder and derived globals;
01–08 read/write under `data/` and `output/` (relative). 09–14 have absolute paths at their
top (to be replaced by `config/paths.do`).

| Script | Does | Reads | Writes |
|---|---|---|---|
| `01_match_customs_mne.do` (611 l.) | tax-ID match → fuzzy (03/04 + AI review) → manual review merge → **builds the base** | customs, `list_exporters_10c_ALC`, Orbis∪D&B v2/v4, manual review, `final_match_postIA.csv` | `data/raw/Base_final_..._product_complete.dta` |
| `02_build_orbis_database.do` | recovers missing parent countries from raw Orbis links | 41 `Links_current_*.txt` | `Unknown_countries_*.dta` |
| `03_`, `04_*.py` | TF-IDF trigram fuzzy match (per country; cross-country) | name lists from 01 | candidate CSVs for AI review |
| `05_descriptive_stats.do` | MNE shares by country/year/sector | base | `output/tables/MNE_Descriptive_Stats.xlsx` |
| `06_trade_analysis.do` (3,304 l.) | Part 0 builds the v4 cubes (§0.1–0.12); Part 1 determinants (1.1 origins, 1.2 destinations, 1.3 products, 1.4 parent region, 1.5 trends); Part 2 effects (2.1 aggregate, 2.2 gravity, 2.3 network D1/D2/D3, 2.4 concentration, 2.5/2.6 extensive margin); Part 3 summary | base + `data/raw/*` | `Intermediate_v4` cubes; graphs/regs/tables (the May-2026 outputs are in `output/legacy_v4_2026-05/`) |
| `07_agro_trade_analysis.do` (2,997 l.) | 06 restricted to HS2 01–24, plus §1.5 agro-section deep-dive (HS sections I–IV) | base | `agro/` outputs (`output/agro_legacy/`) |
| `08_agro_policy_report.do` | 9 figures + 2 tables for the IDB agro policy report | 07's intermediates | `output/agro_legacy/PolicyReport/` |
| `09_mne_export_destinations_build.do` | one pass over the base → **`mne_export_destination_cube.dta`** = origin × dest × year × `iso3_parent` × pcountry × pflag × MNE flags (201,847 rows) | base | `output/tables/mne_export_destination_cube.dta` |
| `10_mne_export_destinations_tables.do` | share to parent country (T2 by origin/year), destination mix MNE vs non-MNE (T3), top parent countries (T4), θ by destination (T5) | the cube | `output/tables/T2–T5*.csv`, `mne_export_destinations.log` |
| `11_ultimate_parent_build.do` | cube with three ownership sources (Orbis GUO50/GUO25, D&B global ultimate) crosswalked to ISO3 | base, `iso2_to_iso3.csv`, `cname_to_iso3.csv` | `output/tables/mne_ucp_cube.dta` (277,690 rows) |
| `12_ultimate_parent_tables.do` | recorded / naive-GUO / first-non-conduit owner concepts; θ range | ucp cube | `V1–V3*.csv`, `U1–U3*.csv`, `ultimate_parent.log` |
| `13_fact5_dpy_fe.do` | Fact 5 with dest×product×year FE (+PPML) | `Intermediate_v4\collapsed_odpy.dta` | `fact5_dpy_fe.{csv,tex,log}` |
| `14_ownership_covariance.do` | Σθ·S² = θ̄·HHI + Cov(θ,S), market = dest×HS6×year, group = `guo25` / parent name / firm | base | `ownership_cov_bymarket.dta` (5.4 M rows: `country_dest hs07_6d year gkey owner v`), `ownership_cov_owners.csv`, log |
| `helpers/Python_RCA_data_WITS.py` | downloads WITS RCA by origin-year | WITS API | `RCA_WITS_orig_year.dta` |

Headline numbers from 09–14 (all on the Sebastián convention, ten origins): 9.2 % of
foreign-MNE export value goes to the parent's own country; θ_USA = 0.134 (range
[0.136, 0.170] after conduit reallocation); Fact 5 survives dest×product×year FE at half
size (0.087 intensive, 0.061 extensive, PPML +0.229); USA Cov(θ,S) correction +10.1 %.
Provenance and interpretation: model `CLAUDE.md` §27, §28, §33, §34.

### 4.2 `stylized_facts/` — Ignacio's pipeline

Documented in `stylized_facts/README.md`. In one line: Stata `10_part0_build.do` is a
fork of `src/06` Part 0 (same cube definitions, Ignacio convention); Python `sf1…sf6`
produce the six facts of the July-2026 document from small caches built by chunked reads
of the parquet base; `nsf_*` produce Facts 4/6 (network size, ownership-adjusted
concentration); `sf_explore_*` are the May-2026 exploration behind the fact selection.

### 4.3 Analysis cubes — what each one is for

| Cube | Grain | Rows | Key columns | Use |
|---|---|---|---|---|
| `data/intermediate/v4_cubes/collapsed_odpy.dta` | origin × dest × HS6 × year | 1,546,580 | `total_value mne_value dom_value mne_ext_value dom_ext_value mne_dom_value n_firms n_mne n_mne_ext n_mne_dom`, gravity (`ln_dist contig fta_wto PTA BIT DTT avg_tariff`), product chars (`upstreamness sigma complexity quality_ladder rca tech_lall2000 tech_ipc1 rhci` + `_abovemed`/`_decile`), `hs2 hs_section`, `income_group_dest dest_region_num intra_regional`, FE ids `orig_id dest_id prod_id od_id op_id ot_id dt_id pt_id odt_id odp_id`, top-k shares | Fact 5 (Table 1, A.7, script 13), Fact 2 regressions (A.4/A.5), concentration |
| `collapsed_ody / opy / oy` | coarser | 2.5 MB / 39 MB / 88 KB | same family | Facts 1, 2 descriptives |
| `output/tables/mne_export_destination_cube.dta` | origin × dest × year × **parent country** | 201,847 | `iso3_parent pcountry pflag MNE_ext MNE_dom MNE_total has_parent to_parent value_fob nrows` | **Volpe items 1c/1d (parent × destination tables, heat map) — already sufficient at origin×dest level** |
| `output/tables/mne_ucp_cube.dta` | as above + ultimate owner concepts | 277,690 | `ucp50 ucp25 ucpdnb iso3_ucp MNE_ucp to_ucp moved` | robustness of owner country |
| `output/tables/ownership_cov_bymarket.dta` | dest × HS6 × year × group | 5,403,889 | `gkey owner v` | product-level owner shares (item 1f, partially: no origin dimension) |
| **MISSING: origin × dest × HS6 × year × parent** | | | | needed for items 1a (Figures 1–3 by parent), 1f (HS6 by parent), and the agro split by parent. Spec in `docs/WORKPLAN_working_paper.md` §0. |

## 5. Small inputs in `data/raw/` (copied 2026-09-03)

| File | Content | Key |
|---|---|---|
| `product_characteristics_hs6_2002_adj.dta` (5,025 rows) | `pci` (complexity), `sigma` (Broda–Weinstein), `upstreamness` (Antràs–Chor), `ladder` (Khandelwal), Rauch `lib`/`con`, `hs2007productdescription`, `sitc2` | `hs07_6d` |
| `product_characteristics_hs6_2002.dta`, `Concordance_HS_2007_2002_WITS.dta`, `JobID-46_Concordance_H3_to_H2.CSV` | HS2007↔HS2002 + **HS6 descriptions** | |
| `lall2000_hs2007.dta` (5,050) | `lall2000_category` (11 Lall classes), `hs6_description`, `sitc3_3digit` | `hs07_6d` |
| `HS_2007_to_SITC3.dta`, `JobID-53_Concordance_H3_to_S3.CSV`, `Lall_2000_SITC3.xls` | HS2007 → SITC Rev.3 (+ descriptions) | |
| `HS6_to_NAICS_2017.dta`, `HS6_to_NAICS_2016.dta` | HS6 → NAICS (`naics`, `hs6`) | |
| `ALP_IPC_Patent_hs2007_6_to_ipc1.dta` / `ipc4` | Lybbert–Zolas patent/technology classes | `hs07_6d` |
| `UNCTAD RHCI hs_2007_indices.dta` | revealed human-capital intensity | |
| `RCA_WITS_orig_year.dta` (96 MB), `RCA_WITS.dta` | RCA by origin × HS6 × year | |
| `Gravity_V202211.dta` (488 MB) | CEPII gravity 2022 | `iso3_o iso3_d year` |
| `tariffsPairs_88_21_vbeta1-2024-12.dta` (72 MB) | bilateral applied tariffs | |
| `PTA_BIT_DTT_BID.dta` | PTA / BIT / DTT indicators | |
| `WB_Income_group.dta` | WB income groups | |
| `bulk_files_Sectoral_Composition_..._Export.xlsx` | Atlas bulk export used for `pci` | |

Not on disk (to download): Fontagné–Guimbard–Orefice (2022) HS6 trade elasticities
(CEPII, "Product-Level Trade Elasticities"); HS2007→BEC correspondence (UNSD/WITS).

## 6. Traps (each has already cost time)

- **`_merge_DNB_Orbis` vs `_merge_final_review`** and **ECU in/out** — §3.
- **`parent_country` is a strL** in the base; `collapse` cannot `by()` it. `src/09` recasts to `str8` first.
- **`iso3_parent` empty for ~half of foreign-MNE value.** Any parent-country exhibit must say what it does with those rows (Figure 4 drops them; `MNE_ext` in `src/` excludes them; Ignacio's `MNE_ext` includes them).
- **Conduits.** GBR/NLD/PAN/BMU/IRL/CHE/LUX as recorded parents. Use the first-NON-conduit chain (`src/12`, concept 3), never the naive GUO chain (it moves value INTO Panama/Luxembourg). GBR is mostly genuine (LSE-listed miners); the big defensible fix is GBR→AUS (52.5 bn).
- **Reading the base.** Stata: `use <varlist> using file` and collapse immediately (scripts 09/11/14 are the templates, ~20–40 min each). Python: Ignacio's chunked `parquet_chunks` needs a parquet copy that does NOT exist here; the pre-July version used `pyreadstat.read_file_in_chunks(pyreadstat.read_dta, ...)`, which works on the `.dta` directly.
- **Positive-trade cells only** in `collapsed_odpy` — the extensive margin there is conditional on the cell exporting; the published extensive margin used a squared cube.
- **Stata globals inside programs.** FE specs must be globals (`${fe`f'}`), not locals — a local silently becomes empty inside a `program` and every regression runs without FE (fixed in both pipelines; keep it that way).
- **Outreg/esttab fragments and Overleaf mirrors.** Both pipelines `copy` every exhibit to an Overleaf folder that exists only on the author's machine; `export_graph` in `src/06` uses `copy` without `cap` and will error if `$overleaf` does not exist — set `$overleaf` to a local folder (`config/paths.do` does).
- **`Github/` folder.** Until 2026-09-03 the real GitHub clone was nested inside this folder and the outer `.git` was a diverged local-only history. Fixed: outer `main` = `origin/main`; old history tagged `archive-outer-local-history-2026-09-03`; the nested clone is in `archive/` and can be deleted. **Commit from this folder.**
- **Spaces in paths.** Everything lives under `C:\Sebas BID\` — always quote paths in Stata (`"$root\..."`) and Python (`Path(r"...")`).
