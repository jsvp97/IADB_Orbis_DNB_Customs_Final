# Data Guide

This file describes every dataset the pipeline needs, where to get each one, and exactly where to put it on your machine.

None of the actual data files are included in this repository — they're either commercially licensed, restricted to researchers, or generated automatically when you run the scripts. This README is the only data-related file tracked by git.

---

## Do You Already Have the Final Dataset?

If someone on the research team gave you `Base_final_Customs_DNB_Orbis_product_complete.dta`, you're halfway there. Put it in `data/raw/` and you can skip scripts 01–04 entirely — go straight to script 05.

```
Do you have Base_final_Customs_DNB_Orbis_product_complete.dta?

  YES → Put it in data/raw/  →  Run scripts 05, 06, 07, 08
  NO  → You need all the sources listed below  →  Run everything from script 01
```

---

## Where to Put Everything

```
data/
├── raw/                             ← put ALL input files here
│   ├── Base_final_Customs_DNB_Orbis_product_complete.dta
│   ├── list_exporters_10c_ALC.dta
│   ├── Merge_DNB_Orbis_PostIA_v2.dta
│   ├── Merge_DNB_Orbis_PostIA_v4.dta
│   ├── Gravity_V202211.dta
│   ├── product_characteristics_hs6_2002.dta
│   ├── Concordance_HS_2007_2002_WITS.dta
│   ├── Unknown_countries_...dta          ← created by script 02
│   ├── RCA_WITS_orig_year.dta
│   ├── lall2000_hs2007.dta
│   ├── ALP_IPC_Patent_hs2007_6_to_ipc1.dta
│   ├── UNCTAD RHCI hs_2007_indices.dta
│   ├── tariffsPairs_88_21_vbeta1-2024-12.dta
│   ├── PTA_BIT_DTT_BID.dta
│   └── WB_Income_group.dta
│
├── intermediate/                    ← created automatically — don't edit these
│   ├── customs/
│   │   ├── exp_fdpt_10c_names_180625.dta
│   │   └── Base_revision_manual_exporters_...dta
│   ├── ia_review/                   ← AI review CSVs go here (see Section 8)
│   │   ├── Match_preIA_ARG.csv      ← script 01 creates these
│   │   ├── Match_preIA_ARG_scored.csv ← you create these (AI review)
│   │   └── ... (one pair per country, plus the final cross-country files)
│   └── regressions/
│       ├── product_characteristics_hs6_2002_adj.dta
│       └── Gravity_V202211.dta
│
└── README.md                        ← this file
```

---

## 1. The Main Analysis Dataset

**File:** `data/raw/Base_final_Customs_DNB_Orbis_product_complete.dta`

This is the end product of script 01. It combines customs trade data (who exported what, where, and when) with corporate database info (is this firm a multinational?). Scripts 05–08 all start from this file.

If someone provides this file directly, you can skip all the matching steps.

**Key columns:**

| Column | What it is |
|---|---|
| `firm_name` | Company name from customs records |
| `Tax_ID` | National tax ID (RUT, RUC, CUIT, etc.) |
| `country_orig` | Exporting country (ISO3) |
| `country_dest` | Destination country (ISO3) |
| `year` | Year of export |
| `hs07_6d` | Product code (HS 2007, 6-digit) |
| `value_fob` | Export value in USD FOB |
| `_merge_final_review` | **The key variable: 1 = domestic firm, 3 = matched as MNE** |
| `subsidiarybvdid` | Firm's ID in the Orbis database |
| `guo25` | ID of the global parent company in Orbis |
| `dunsnumber` | Firm's DUNS number (Dun & Bradstreet) |
| `iso3_parent` | Country of the parent company |
| `iso3_subsidiary` | Country of the subsidiary |
| `naics_aff_2` | 2-digit industry code of the affiliate |
| `company_name` | Matched corporate name from Orbis/DNB |

---

## 2. Orbis Corporate Database (Bureau van Dijk)

**Used by:** Script 02

Orbis is a global database of corporate ownership links — who owns whom. We use it to check whether a LAC exporter is the subsidiary of a foreign parent company.

**How to get it:** Paid licence. IDB researchers should contact the IDB Library.

**What you need:** 41 chunked text files located at:
```
[your Orbis folder]\Ownership\Txt\Chunky\Links_current_0001.txt
[your Orbis folder]\Ownership\Txt\Chunky\Links_current_0002.txt
...
[your Orbis folder]\Ownership\Txt\Chunky\Links_current_0041.txt
```

Set `global orbis_raw` in `src/00_master.do` to the folder that contains the `Ownership\` subfolder. Script 02 takes care of the rest.

**Columns used:**

| Column | What it is |
|---|---|
| `subsidiarybvdid` | The firm's unique BvD identifier |
| `typeofrelation` | Ownership type (GUO25, GUO50, DUO25, etc.) |
| `Parent_ISO2` | Country code of the parent company |

---

## 3. Dun & Bradstreet Corporate Database

**Used by:** Script 01

DNB provides firm-level identifiers (DUNS numbers), tax IDs, and corporate network information. We use it mainly for the tax-ID matching step and as a source of company names for the fuzzy match.

**How to get it:** IDB licence. Contact the Trade and Integration Division.

**Files needed:**

| File | Where | What it is |
|---|---|---|
| `Merge_DNB_Orbis_PostIA_v2.dta` | `data/raw/` | The merged DNB + Orbis corporate database |
| `Merge_DNB_Orbis_PostIA_v4.dta` | `data/raw/` | Updated version used in the final merge |

**Key columns:**

| Column | What it is |
|---|---|
| `name_aff` | Affiliate company name |
| `dunsnumber` | DUNS number of the affiliate |
| `globalultimatedunsnumber` | DUNS number of the global parent |
| `nationalID_num1/2/3_aff` | National tax IDs (up to 3 per firm) |
| `naics_aff_2/4/6` | Industry codes of the affiliate |
| `iso3_aff`, `iso3_par` | Country codes (affiliate and parent) |

---

## 4. Customs Export Records

**Used by:** Script 01

These are the firm-level export records from national customs agencies across the 10 countries. They tell us who exported what, where, and how much — but they don't identify multinationals. That's what the matching process does.

**How to get it:** Restricted access. Contact the IDB Trade and Integration Division.

**Files needed:**

| File | Where | What it is |
|---|---|---|
| `list_exporters_10c_ALC.dta` | `data/raw/` | Unique exporter list (firm name + tax ID + country) |
| `exp_fdpt_10c_names_180625.dta` | `data/intermediate/customs/` | Full trade flows by firm, product, destination, year |

**Key columns:**

| Column | What it is |
|---|---|
| `firm_name` | Company name in customs records |
| `Tax_ID` | National tax identifier |
| `country_orig` | Exporting country (ISO3) |
| `country_dest` | Destination country (ISO3) |
| `year` | Year of export |
| `hs07_6d` | Product code, 6-digit HS 2007 |
| `value_fob` | Export value, USD FOB |

**Years available by country:**

| Country | Years | Notes |
|---|---|---|
| ARG | 2011–2019 | |
| CHL | 2009–2022 | |
| COL | 2010–2021 | |
| CRI | 2010–2019 | |
| DOM | 2012–2019 | |
| ECU | 2010–2019 | |
| PER | 2010–2019 | |
| PRY | 2012–2020 | |
| SLV | 2006–2018 | |
| URY | 2010–2019 | |

---

## 5. Gravity Variables

**Used by:** Scripts 06 and 07

Bilateral trade controls for the gravity model regressions (distance, common language, trade agreements, etc.).

**How to get it:** Free. Download from [cepii.fr](http://www.cepii.fr/CEPII/en/bdd_modele/bdd_modele_item.asp?id=8). Get version 2022.

**File:** `data/raw/Gravity_V202211.dta`

**Key columns used:** `gdp_o`, `gdp_d` (GDP), `gdpcap_o`, `gdpcap_d` (GDP per capita), `dist` (bilateral distance), `contig` (shared border), `comlang_ethno` (common language), `comcol` (common coloniser), `fta_wto` (free trade agreement dummy)

---

## 6. Product Characteristics

**Used by:** Scripts 06 and 07

Product-level variables merged at the HS6 code level. Used to test whether MNE effects differ depending on the type of product (e.g., more complex or differentiated goods).

**Where these come from:**
- Rauch (1999): whether a product is differentiated, reference-priced, or exchange-traded
- Antràs et al. (2012): how far upstream in the supply chain a product is
- Economic Complexity Atlas: how complex a product is to make
- Hausmann & Klinger (2006): where a product sits on the quality ladder

**Files:**

| File | Where | What it is |
|---|---|---|
| `product_characteristics_hs6_2002.dta` | `data/raw/` | Characteristics at the HS6 level (HS 2002 codes) |
| `product_characteristics_hs6_2002_adj.dta` | `data/intermediate/regressions/` | Adjusted version used in script 06 |
| `Concordance_HS_2007_2002_WITS.dta` | `data/raw/` | Translates HS 2007 codes to HS 2002 codes |

---

## 7. Manual Review File

**Used by:** Script 01 (final corrections)

For the top 500 exporters per country that couldn't be matched automatically, I went through each one manually — searching company websites, LinkedIn, and corporate registries — to verify whether it's a multinational. These are the firms that matter most for the aggregate numbers, so getting them right was worth the effort.

**File:** `data/intermediate/customs/Base_revision_manual_exporters_DNB_Orbis_manualrev_nodup.dta`

**Key columns:**

| Column | Values | What it means |
|---|---|---|
| `Manually_found` | "FOUND-YES" / "FOUND-NO" / "FOUND-PARENT" | Verification result |
| `firm_name_match` | text | Correct corporate name found manually |
| `location` | URL | Source used for verification |

---

## 8. AI Review Files

**Used by:** Script 01 (between the fuzzy matching steps)

Script 01 has two pause points where you need to run the Python name-matching scripts and then send the results to an AI model for validation. The AI checks each candidate pair (customs firm name vs. corporate database name) and says whether they're the same company.

### How the files flow

```
Script 01 (Stage 2a) generates:
  data/intermediate/ia_review/Match_preIA_ARG.csv
  data/intermediate/ia_review/Match_preIA_CHL.csv
  ... (one per country)

You send these to AI → get back:
  data/intermediate/ia_review/Match_preIA_ARG_scored.csv
  data/intermediate/ia_review/Match_preIA_CHL_scored.csv
  ... (same, with AI scores added)

Script 01 (Stage 2c) then generates:
  data/intermediate/ia_review/final_match_preIA.csv

You send this to AI → get back:
  data/intermediate/final_match_postIA.csv
```

### AI prompt to use (for all review steps)

Paste this into GPT-4 or Gemini, then give it the rows from each CSV file:

```
You are a research assistant specialized in identifying companies.
I will give you two company names: one is the original company name
(firm_name), and the other is the result of a previous database
match (company_name).

Your task: Determine whether firm_name and company_name refer to
the same company or companies belonging to the same parent company.

Output format (always in this structure, no explanations):
Q1: Yes/Non || Q2: <score from 1 to 10>

Q1: "Yes" if same company or shared parent — "Non" otherwise
Q2: 1 = very low certainty, 10 = very high certainty

Additional rules:
- Auto-mark identical names (post normalisation) as Yes/10
- Use web search to verify ownership when uncertain
- Count parent-subsidiary ties as Yes
- Consider both English and Spanish names
- Ignore generic terms (health, logistics, services) when comparing
```

### For the duplicate ranking step (Stage 5 in script 01)

Same prompt as above, but add this output column:
```
Q3: <rank from 1 to n>   (1 = most probable match among duplicates)
```
This is needed when one customs firm matched multiple corporate database entries.

### Columns the scored CSV files must have

| Column | Type | Meaning |
|---|---|---|
| `Q1` | text | "Yes" or "Non" |
| `Q2` | number | Confidence 1–10 |
| `Q3` | number | Rank among duplicates (Stage 5 only) |

---

## 9. Supplementary Input Files for Scripts 06 and 07

These smaller datasets are merged in during the data preparation section of scripts 06 and 07. Put them all in `data/raw/`.

| File | What it is | Source |
|---|---|---|
| `RCA_WITS_orig_year.dta` | Revealed comparative advantage by country, product, year | WITS |
| `lall2000_hs2007.dta` | Technology classification (Lall 2000) mapped to HS 2007 | Author |
| `ALP_IPC_Patent_hs2007_6_to_ipc1.dta` | Patent intensity by product | Author |
| `UNCTAD RHCI hs_2007_indices.dta` | UNCTAD human capital intensity index | UNCTAD |
| `tariffsPairs_88_21_vbeta1-2024-12.dta` | Bilateral tariffs 1988–2021 | MAcMap/IDB |
| `PTA_BIT_DTT_BID.dta` | Trade agreements, investment treaties, tax treaties | IDB |
| `WB_Income_group.dta` | World Bank country income group | World Bank |
| `Unknown_countries_...dta` | Parent country info for firms missing it (output of script 02) | Script 02 |

---

## What's Not in This Repo

Git is configured (via `.gitignore`) to never track:
- Any `.dta` files
- Any `.csv` output files
- Everything in `output/` and `agro/Output/`
- The Orbis and DNB source files

If you need the processed datasets, reach out to the author (jsvp97@gmail.com).
