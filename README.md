# Multinational Firms and Trade in Latin America

A Stata + Python project that figures out which companies exporting from Latin America are multinationals — and then asks what difference that makes for trade.

**Author:** Sebastian Velasquez (IDB)

**Full Code available at** https://github.com/jsvp97/IADB_Orbis_DNB_Customs_Final


---

## The Problem We're Solving

Customs data tells you *what* was exported, *where*, and *by whom* — but it doesn't tell you whether the exporter is a foreign subsidiary, a domestic conglomerate, or an independent local firm. We fix that by matching firm names and tax IDs from customs records across 10 Latin American countries to two commercial corporate databases (Orbis and Dun & Bradstreet).

Once we know which exporters are multinationals, we can answer:

- What share of LAC exports come from multinational affiliates vs. regular local firms?
- Do multinationals export to more countries and sell more types of products?
- How does being part of a corporate network affect trade flows (gravity model)?
- Are multinationals responsible for opening up new export markets and products?

There's also a separate analysis just for **agricultural exports** (HS chapters 1–24), which is relevant for IDB food security and rural development work.

---

## Countries and Data Coverage

| Country | Code | Years covered |
|---|---|---|
| Argentina | ARG | 2011–2019 |
| Chile | CHL | 2009–2022 |
| Colombia | COL | 2010–2021 |
| Costa Rica | CRI | 2010–2019 |
| Dominican Republic | DOM | 2012–2019 |
| Ecuador | ECU | 2010–2019 |
| Peru | PER | 2010–2019 |
| Paraguay | PRY | 2012–2020 |
| El Salvador | SLV | 2006–2018 |
| Uruguay | URY | 2010–2019 |

---

## What's in This Repo

```
orbis-dnb-customs-trade/
│
├── src/                              ← all scripts, run them in number order
│   ├── 00_master.do                  ← start here
│   ├── 01_match_customs_mne.do       ← the main matching script
│   ├── 02_build_orbis_database.do    ← find missing parent countries (runs after 01)
│   ├── 03_fuzzy_match_by_country.py  ← name matching, one pass per country
│   ├── 04_fuzzy_match_post10cou.py   ← name matching, final cross-country pass
│   ├── 05_descriptive_stats.do       ← summary tables
│   ├── 06_trade_analysis.do          ← main econometric analysis
│   ├── 07_agro_trade_analysis.do     ← same analysis, agriculture only
│   ├── 08_agro_policy_report.do      ← policy report charts and tables
│   ├── 09_mne_export_destinations_build.do   ← where MNE exports go: build the cube
│   ├── 10_mne_export_destinations_tables.do  ← where MNE exports go: the tables
│   ├── 11_ultimate_parent_build.do           ← conduit reallocation: build the cube
│   ├── 12_ultimate_parent_tables.do          ← conduit reallocation: the tables
│   ├── 13_fact5_dpy_fe.do                    ← Fact 5: destination×product×year FE test
│   └── 14_ownership_covariance.do            ← Cov(θ,S): the paper's headline object
│
├── data/
│   ├── README.md                     ← what data you need and where to put it
│   ├── raw/                          ← put your input files here (not in git)
│   └── intermediate/                 ← created automatically while running
│
├── output/                           ← all output files (not in git)
│
├── requirements.txt                  ← Python packages needed
├── .gitignore                        ← keeps data files out of git
└── README.md                         ← this file
```

The `data/` and `output/` folders are not tracked by git because they contain proprietary or restricted data. Only the code and documentation live here.

---

## How the Matching Works

The hard part is connecting a firm name like "EXPORT SA" in a customs spreadsheet to "Exportaciones S.A. de C.V." in a corporate database. These are the same company but a simple search won't find the match. The process has four steps:

```
Customs records  (firm name + tax ID)
       │
       ▼
  Step 1 — Match on tax ID
  ─────────────────────────────────────────────────────────
  Every country has a national tax number (RUT in Chile,
  RUC in Peru, CUIT in Argentina, etc.). We match those
  directly against the corporate databases.
  This gets us about 60% of matched export value.
       │
       │ firms still unmatched
       ▼
  Step 2 — Fuzzy name matching, per country
  ─────────────────────────────────────────────────────────
  For each of the 10 countries separately, we compare firm
  names character by character (not word by word) using a
  method called TF-IDF trigrams. This handles abbreviations
  and missing words much better than standard text search.
  An AI model (GPT-4 or Gemini) then checks each candidate
  pair and says yes/no.
       │
       │ firms still unmatched
       ▼
  Step 3 — Fuzzy name matching, all countries together
  ─────────────────────────────────────────────────────────
  One more pass across all countries for firms that didn't
  match in step 2. Same method, one more AI review.
       │
       │ top exporters
       ▼
  Step 4 — Manual review of the top 500 exporters per country
  ─────────────────────────────────────────────────────────
  For the largest exporters in each country that still
  couldn't be matched automatically, I went through each
  one by hand — checking company websites, LinkedIn, and
  national corporate registries — to confirm whether it is
  a multinational. These accounts for a big share of total
  export value even though there are relatively few of them.
  Results are stored in a separate file and merged at the
  end of script 01.
       │
       ▼
  Final dataset: firm × product × destination × year
  _merge_final_review = 1  →  domestic firm (no match found)
  _merge_final_review = 3  →  confirmed multinational
```

**Why compare character by character instead of word by word?**
Because "CORP EXPORT LTDA" and "Corporacion Exportadora Limitada" share no words but share a lot of the same character sequences. The trigram method handles the way Latin American company names get abbreviated in official records.

**Why do the manual review at all?**
The automated methods — tax ID match, fuzzy name match, AI validation — work well across the board but are not perfect for the very largest firms. The top 500 exporters per country often account for a large share of total export value, so getting them right matters a lot for the aggregate numbers. The manual review is the final quality check that makes the dataset reliable for research.

---

## Three Definitions of "Multinational"

All results are produced for three different definitions so you can choose what fits your question:

| Variable | What it means |
|---|---|
| `MNE_ext` | A subsidiary whose parent company is in a different country |
| `MNE_dom` | A firm matched to a corporate database with a parent in the same country |
| `MNE_total` | Any firm matched to the corporate database (either of the above) |

---

## What Each Script Does

**`00_master.do`** — the only file you need to open. Set two paths and run it. It handles everything else, including stopping at the right moments to let you run the Python scripts and AI review steps.

**`01_match_customs_mne.do`** — the main event. This script runs the full matching process and builds the final dataset. It has two built-in pause points where it stops and tells you to run a Python script and do an AI review before continuing. At the end it also merges in the manual review results for the top 500 exporters per country.

**`02_build_orbis_database.do`** — runs after script 01. Some matched firms have a corporate database ID but no parent country info. This script goes into the raw Orbis files and finds those missing countries. It needs to run after 01 because it uses the matched dataset to know which firms to look up.

**`03_fuzzy_match_by_country.py`** — does the name matching for step 2 above. Runs from the command line. All file paths are detected automatically.

**`04_fuzzy_match_post10cou.py`** — same as script 03 but for step 3 (cross-country final pass).

**`05_descriptive_stats.do`** — summary tables. Run this first after the dataset is built — it's a good sanity check that the matching worked before you run the bigger analysis.

**`06_trade_analysis.do`** — the main paper (~3,300 lines). Three parts:
- What determines whether a firm is an MNE exporter (by country, destination, product, parent country, trend over time)
- How MNE presence affects trade (gravity regressions, trade concentration, new markets and products)
- Summary statistics for the paper

**`07_agro_trade_analysis.do`** — same as 06 but restricted to food and agriculture (HS chapters 1–24). Results go to the `agro/` folder so they don't mix with the main analysis.

**`08_agro_policy_report.do`** — makes the charts and tables for the IDB agricultural policy report. Reads from the files built by script 07.

**`09_mne_export_destinations_build.do`** — reads the full transaction file once, keeping only the columns needed to answer "where do multinational exports actually go", and collapses it to a small cube (`output/tables/mne_export_destination_cube.dta`). The MNE definitions are copied verbatim from script 05, so the numbers sit on the same classification as every other table in the project. The read is the expensive step; saving the cube means it only happens once.

**`10_mne_export_destinations_tables.do`** — the tables, from the cube. Coverage; the share of foreign-MNE export value that goes to the parent's own country, overall and by origin and year; the destination mix of MNE against non-MNE exporters; the top parent countries and how much each ships home; and, for each destination, the share of its imports from these ten origins that is produced by affiliates of its own multinationals. Writes four CSVs and a log to `output/tables/`.

Headline result: **only 9.2% of foreign-MNE export value goes to the parent's own country**, and foreign affiliates are *less* US-oriented than local exporters (13.9% of value against 25.0%). The split by origin is large — 0.40 for El Salvador, 0.30 for the Dominican Republic, 0.28 for Costa Rica, against roughly 0.06 for Argentina, Chile and Peru.

**`11_ultimate_parent_build.do`** — the recorded parent of an exporter is often a holding company in a conduit jurisdiction rather than an economic owner. This script reads the full transaction file once and builds a cube carrying three ownership sources side by side: Orbis global ultimate owner at the 50% and 25% control thresholds, and Dun & Bradstreet's global ultimate. Orbis reports ISO2 codes and D&B a country name, so both are crosswalked to ISO3 first (the two crosswalk CSVs are written by a short Python step and live in `output/tables/`).

**`12_ultimate_parent_tables.do`** — applies three owner concepts to that cube: the parent as recorded, a naive chain that takes the first available ultimate owner, and an improved chain that takes the first **non-conduit** country. The naive chain is not good enough — it moves value *into* Panama and Luxembourg — which is why the third concept exists.

Result: the correction is worth making but small. The share of foreign-MNE exports going to the owner's own country is 0.092 under all three concepts. The share of US imports from these origins produced by US-owned affiliates moves 0.134 → 0.136. The biggest single correction is 52.5 bn reassigned from the United Kingdom to Australia — the dual-listed mining groups. About 136 bn of export value cannot be resolved past a conduit and is reported as a range rather than assumed away.

**`13_fact5_dpy_fe.do`** — the decisive test of Fact 5 ("more MNE presence, more non-MNE exports"). The published Table 1's tightest column absorbs origin×dest×product and origin×dest×year but **not** destination×product×year, so a market-level demand shock raises MNE entry and local exports together. This script re-runs the Panel B regressions on `collapsed_odpy.dta` with that term added (plus a PPML column on the level). Reads the cube from the predecessor project's `Intermediate_v4`; writes `output/tables/fact5_dpy_fe.{log,csv,tex}`.

Result (2026-08-26): **the fact survives at roughly half its published size.** Intensive margin 0.166 → 0.087 (s.e. 0.017), extensive 0.117 → 0.061 (s.e. 0.011), PPML on the level with the full FE set +0.229 (s.e. 0.051), all significant at 1%. About half of the published association was common demand; the surviving half is a real fact the model must explain.

**`14_ownership_covariance.do`** — measures the theory paper's headline object: the ownership-weighted concentration decomposition Σθ·S² = θ̄·HHI + Cov(θ,S), per destination×product×year market, groups = ultimate parent firms (GUO BvD id; unmatched exporters as singleton groups), aggregated with value weights into naive + between-market + within-market terms. Reads the transaction file once; writes `output/tables/ownership_cov_bymarket.dta`, `ownership_cov_owners.csv`, and a log.

Result (2026-08-27): for the **United States** (θ̄ = 0.135, independently matching script 10's 0.134), the country-level calculation **understates** the ownership-weighted concentration by **10.1%** (between +0.0032, within +0.0020, both positive: US parents are disproportionately the big players in concentrated markets). The correction is owner-specific and **sign-varying** — Colombia +24%, Chile +10%, UK −10%, Argentina −24%, Peru −30% — a pattern invisible to country-level ownership shares. Value-weighted mean market HHI 0.373 (within-LAC-sample shares), 35 groups per market.

---

## How to Run It

### What you need installed

**Stata 17+** with these packages (run once):
```stata
ssc install reghdfe
ssc install ppmlhdfe
ssc install ftools
ssc install outreg2
ssc install estout
ssc install gtools
ssc install kountry
ssc install distinct
ssc install labutil
```

**Python 3.9+** for the name matching scripts:
```bash
pip install -r requirements.txt
```

> Windows note: `nmslib` needs Visual C++ build tools. If the install fails, try:
> `pip install nmslib-metabrainz==2.1.3`

### Step by step

**1. Get the data**
Follow `data/README.md`. If you already have `Base_final_Customs_DNB_Orbis_product_complete.dta`, put it in `data/raw/` and skip to step 4.

**2. Set your paths**
Open `src/00_master.do` and change these two lines:
```stata
global root      "C:\path\to\this-folder"
global orbis_raw "D:\path\to\Orbis\FINAL"   // set to "" to skip script 02
```

**3. Run the master script**
Run `00_master.do` in Stata. The first time it runs, script 01 will stop and tell you to run a Python script. Follow the on-screen instructions. You'll need to do this twice before the full pipeline completes (see the Quick Start in `00_master.do` for details).

**4. Run the analysis**
Once the matched dataset exists, the analysis scripts (05–08) run straight through with no interruptions.

---

## Common Questions

**I don't have Orbis or DNB access. Can I still use this code?**
The matching itself requires both databases. But the name-matching code (scripts 03–04) and the analysis code (scripts 05–08) are fully readable and reusable for other projects.

**Can I adapt the name-matching method for a different country?**
Yes. Scripts 03 and 04 are general-purpose. You need a reference list of firm names from any corporate source and a query list from your administrative data. Change the `COUNTRIES` list in script 03 and the corresponding Stata import lines in script 01.

**Why does the pipeline need to stop twice for Python and AI review?**
Because the fuzzy name matching produces candidate pairs that need human-in-the-loop validation before we trust them. The AI review step filters out false matches. This is intentional — it's what makes the match quality good enough for research.

**How long does the whole thing take?**
Script 02 (Orbis processing, 41 large files): about 2 hours. Python matching (scripts 03–04): 3–6 hours. Stata analysis (05–08): 1–2 hours.

---

## Output Files

| Location | What's there |
|---|---|
| `output/tables/MNE_Descriptive_Stats.xlsx` | MNE share of exports by country, year, sector |
| `output/graphs/1_1_ExportingCountries/` | Charts: MNE presence by exporting country |
| `output/graphs/2_5_ExtensiveMargin/` | Charts: new markets and products |
| `output/regressions/S2_Effects/` | Regression output tables |
| `agro/Output/PolicyReport/Figures/` | Agricultural policy report charts |
| `agro/Output/PolicyReport/Tables/` | Agricultural policy report tables (LaTeX) |

---

## Data Sources

| Data | Where it comes from | Access |
|---|---|---|
| Corporate ownership network | Bureau van Dijk — Orbis | Paid licence |
| Firm directory + DUNS numbers | Dun & Bradstreet | IDB licence |
| Customs export records | National customs agencies, 10 LAC countries | Restricted |
| Gravity controls | CEPII Gravity Database v2022 | Free at cepii.fr |
| Product characteristics | Rauch (1999), Antràs et al. (2012), Atlas of Complexity | Free |

Full details in `data/README.md`.

---

## License

The code is available for academic and research use. The underlying data — Orbis, DNB, and the customs microdata — are not included here. They have their own licence agreements.
