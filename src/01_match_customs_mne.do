/*==============================================================================
  01_match_customs_mne.do

  PURPOSE:
    Link customs exporter records to multinational enterprise (MNE) identifiers
    from the Orbis/DNB corporate database. Uses a three-stage matching strategy:

      Stage 1 — Tax ID exact match (national tax identifiers: RUT, RUC, RNC...)
      Stage 2 — Country-level fuzzy name matching (TF-IDF, 10 LAC countries)
                 followed by AI validation (see 03_fuzzy_match_by_country.py)
      Stage 3 — Post-country-pass fuzzy match on remaining unmatched firms
                 followed by AI validation (see 04_fuzzy_match_post10cou.py)

    After all matching stages, the script assembles the final analysis dataset
    (firm × product × destination × year), appends trade values from customs,
    and constructs the MNE indicator used throughout the econometric analysis.

  INPUTS (all in $int or $raw):
    list_exporters_10c_ALC.dta              — customs exporter list (10 LAC countries)
    Merge_DNB_Orbis_PostIA_v2.dta           — Orbis/DNB corporate database (post AI review)
    fuzzy_match_[ISO3].csv                  — country-level fuzzy match outputs (script 03)
    IA_review/Match_preIA_[ISO3]_scored.csv — AI review scores by country
    fuzzy_match_post10cou.csv               — cross-country fuzzy match output (script 04)
    final_match_postIA.csv                  — AI-validated final fuzzy matches
    Customs/exp_fdpt_10c_names_180625.dta   — customs trade flows (firm-product-dest-year)
    Regresion/product_characteristics_hs6_2002.dta — product-level characteristics
    Regresion/Gravity_V202211.dta           — CEPII gravity variables

  OUTPUTS:
    Base_final_Customs_DNB_Orbis_product_complete.dta  — main analysis dataset

  COUNTRIES COVERED: ARG CHL COL CRI DOM ECU PER PRY SLV URY

  AUTHOR: Sebastian Velasquez (IDB)
  LAST UPDATED: March 2026
==============================================================================*/

clear all
set more off

// ============================================================================
// PATH CONFIGURATION — set $root once; all other paths are derived
// ============================================================================

global root  "C:\Sebas BID\Orbis_DNB_Customs_Final"
global raw   "$root\data\raw"
global int   "$root\data\intermediate"
global cust  "$int\customs"
global ia    "$int\ia_review"
global reg   "$int\regressions"
global out   "$root\output"

// ============================================================================
// STAGE 1 — EXACT TAX ID MATCH
// ----------------------------------------------------------------------------
// Orbis records up to 3 national tax ID fields (nationalID_num1-3_aff).
// We loop over each and merge against the unique-Tax_ID customs list.
// ============================================================================

// Build unique-Tax_ID reference file from customs exporter list
use "$raw\list_exporters_10c_ALC.dta", clear
duplicates drop Tax_ID, force
save "$int\list_exporters_10c_ALC_uniqueTax.dta", replace

// Load the Orbis/DNB corporate database (post-AI review from script 03/04)
use "$int\Merge_DNB_Orbis_PostIA_v2.dta", clear

// --- First Tax ID field ---
rename nationalID_num1_aff Tax_ID
merge m:1 Tax_ID using "$int\list_exporters_10c_ALC_uniqueTax.dta"
rename Tax_ID nationalID_num1_aff

preserve
    keep if _merge == 3
    rename nationalID_num1_aff Tax_ID1
    keep companyname firm_name conf country_orig Tax_ID1
    save "$int\list_exporters_10c_ALC_uniqueTax_merge1.dta", replace
restore

keep if _merge == 1
drop country_orig firm_name _merge

// --- Second Tax ID field ---
rename nationalID_num2_aff Tax_ID
merge m:1 Tax_ID using "$int\list_exporters_10c_ALC_uniqueTax.dta"
rename Tax_ID nationalID_num2_aff

preserve
    keep if _merge == 3
    rename nationalID_num1_aff Tax_ID2
    keep companyname firm_name conf country_orig Tax_ID2
    save "$int\list_exporters_10c_ALC_uniqueTax_merge2.dta", replace
restore

keep if _merge == 1
drop country_orig firm_name _merge

// --- Third Tax ID field ---
rename nationalID_num3_aff Tax_ID
merge m:1 Tax_ID using "$int\list_exporters_10c_ALC_uniqueTax.dta"
rename Tax_ID nationalID_num3_aff

preserve
    keep if _merge == 3
    rename nationalID_num1_aff Tax_ID3
    keep companyname firm_name conf country_orig Tax_ID3
    save "$int\list_exporters_10c_ALC_uniqueTax_merge3.dta", replace
restore

keep if _merge == 1
drop country_orig firm_name _merge

rename Tax_ID nationalID_num3_aff

// Construct unified company name field
gen company_name = name_aff if _merge_DNB == 1
replace company_name = matched_name if _merge_DNB != 1

save "$int\Merge_DNB_Orbis_PostIA_v2_uniqueTax_pre10cou.dta", replace

// ============================================================================
// STAGE 2a — EXPORT COUNTRY-LEVEL INPUT FILES FOR FUZZY MATCHING
// ----------------------------------------------------------------------------
// Export per-country name lists for the TF-IDF fuzzy matcher (script 03).
// ============================================================================

// Orbis/DNB name lists by country
foreach x in "ARG" "CHL" "COL" "CRI" "DOM" "ECU" "PER" "PRY" "SLV" "URY" {
    preserve
        keep if iso3_subsidiary == "`x'" | iso3_aff == "`x'"
        keep company_name
        duplicates drop company_name, force
        export delimited using "$int\Orbis_DNB_name_aff_`x'.csv", replace
    restore
}

// Customs exporter name lists by country
use "$raw\list_exporters_10c_ALC.dta", clear
foreach x in "ARG" "CHL" "COL" "CRI" "DOM" "ECU" "PER" "PRY" "SLV" "URY" {
    preserve
        keep if country_orig == "`x'"
        keep firm_name
        duplicates drop firm_name, force
        export delimited using "$int\list_exporters_10c_ALC_`x'.csv", replace
    restore
}

// ============================================================================
// *** PAUSE POINT 1 OF 2 ***
// ----------------------------------------------------------------------------
// Before this script can continue, you need to:
//   1. Run the fuzzy matching script from your command line:
//          python src\03_fuzzy_match_by_country.py
//   2. Send the output CSVs to GPT-4 or Gemini for review.
//      The files to review are in: data\intermediate\ia_review\Match_preIA_*.csv
//      Save the AI-scored versions back as: Match_preIA_*_scored.csv
//      (See data\README.md for the exact AI prompt to use.)
//
// This script will check if the output files are ready.
// If they are not there yet, it will stop here with an error message.
// ============================================================================

capture confirm file "$int\fuzzy_match_ARG.csv"
if _rc != 0 {
    di as error " "
    di as error "======================================================"
    di as error "  STOP — Fuzzy match output not found."
    di as error "  Run this from the command line first:"
    di as error "    python src\03_fuzzy_match_by_country.py"
    di as error "  Then do the AI review on the CSVs in:"
    di as error "    data\intermediate\ia_review\Match_preIA_*.csv"
    di as error "  Save the scored files back as Match_preIA_*_scored.csv"
    di as error "  Then re-run 00_master.do (or re-run this script)."
    di as error "======================================================"
    exit 1
}

capture confirm file "$ia\Match_preIA_ARG_scored.csv"
if _rc != 0 {
    di as error " "
    di as error "======================================================"
    di as error "  STOP — AI-scored files not found."
    di as error "  Run the AI review on the CSVs in:"
    di as error "    data\intermediate\ia_review\Match_preIA_*.csv"
    di as error "  Save the scored files back as Match_preIA_*_scored.csv"
    di as error "  Then re-run 00_master.do (or re-run this script)."
    di as error "======================================================"
    exit 1
}

// ============================================================================
// STAGE 2b — PROCESS COUNTRY-LEVEL FUZZY MATCH RESULTS + AI VALIDATION
// ----------------------------------------------------------------------------
// After running script 03 (fuzzy match) and the AI review, filter matches:
//   conf > -0.6 drops low-similarity candidates before AI review
//   q1 == "Yes" keeps AI-confirmed matches
//   duplicates resolved by keeping highest fuzzy score per Orbis name
//
// NOTE on the AI validation prompt used (passed to GPT-4 / Gemini):
//   The model receives two firm names and returns:
//     Q1: Yes/Non  — whether the firms are the same or share a parent
//     Q2: 1–10     — confidence score
//   Identical names (post normalisation) are auto-validated with Q1=Yes.
//   The model uses web search to verify ownership relationships.
// ============================================================================

// Filter fuzzy match results to candidates for AI review
foreach x in "ARG" "CHL" "COL" "CRI" "DOM" "ECU" "PER" "PRY" "SLV" "URY" {
    import delimited "$int\fuzzy_match_`x'.csv", clear
    gen company_name = matched_name
    drop if conf > -0.6
    keep company_name firm_name
    export delimited using "$ia\Match_preIA_`x'.csv", replace
}

// Load AI-reviewed results and build post-AI match files by country
foreach x in "ARG" "CHL" "COL" "CRI" "DOM" "ECU" "PER" "PRY" "SLV" "URY" {
    import delimited "$ia\Match_preIA_`x'_scored.csv", clear
    save "$ia\Match_preIA_`x'_scored.dta", replace
}

foreach x in "ARG" "CHL" "COL" "CRI" "DOM" "ECU" "PER" "PRY" "SLV" "URY" {
    import delimited "$int\fuzzy_match_`x'.csv", clear
    gen company_name = matched_name
    gen firm_name_ = firm_name
    drop firm_name
    rename firm_name_ firm_name
    drop if conf > -0.6
    keep company_name firm_name conf

    merge 1:1 company_name firm_name using "$ia\Match_preIA_`x'_scored.dta"
    keep if q1 == "Yes"

    // Keep best (lowest-conf) match per Orbis company name when duplicates exist
    duplicates tag company_name, gen(du)
    sort company_name conf
    bysort company_name: gen duplicates = _n
    keep if duplicates == 1

    keep firm_name company_name conf
    order firm_name company_name conf
    save "$ia\Match_postIA_`x'.dta", replace
}

// ============================================================================
// STAGE 2c — IDENTIFY FIRMS NOT MATCHED IN COUNTRY PASSES
// ----------------------------------------------------------------------------
// Remove already-matched firms from both sides before the cross-country pass.
// ============================================================================

use "$int\Merge_DNB_Orbis_PostIA_v2_uniqueTax_pre10cou.dta", clear
foreach x in "ARG" "CHL" "COL" "CRI" "DOM" "ECU" "PER" "PRY" "SLV" "URY" {
    merge m:1 company_name using "$ia\Match_postIA_`x'.dta"
    drop firm_name
    keep if _merge == 1
    drop _merge
}
save "$int\Merge_DNB_Orbis_PostIA_v2_uniqueTax_post10cou.dta", replace

keep subsidiarybvdid guo25 company_name
export delimited using "$int\Merge_DNB_Orbis_for_fuzzy_post10cou.csv", replace

use "$raw\list_exporters_10c_ALC.dta", clear
foreach x in "ARG" "CHL" "COL" "CRI" "DOM" "ECU" "PER" "PRY" "SLV" "URY" {
    merge m:1 firm_name using "$ia\Match_postIA_`x'.dta"
    keep if _merge == 1
    drop _merge
}
export delimited using "$int\list_exporters_10c_ALC_for_fuzzy_post10cou.csv", replace

// ============================================================================
// *** PAUSE POINT 2 OF 2 ***
// ----------------------------------------------------------------------------
// Before this script can continue, you need to:
//   1. Run the cross-country fuzzy matching script from your command line:
//          python src\04_fuzzy_match_post10cou.py
//   2. Send the output CSV to GPT-4 or Gemini for review.
//      The file to review is: data\intermediate\ia_review\final_match_preIA.csv
//      Save the AI-scored version back as: final_match_postIA.csv
//      (Same AI prompt as before — see data\README.md.)
//
// This script will check if the output files are ready.
// ============================================================================

capture confirm file "$int\fuzzy_match_post10cou.csv"
if _rc != 0 {
    di as error " "
    di as error "======================================================"
    di as error "  STOP — Cross-country fuzzy match output not found."
    di as error "  Run this from the command line first:"
    di as error "    python src\04_fuzzy_match_post10cou.py"
    di as error "  Then do the AI review on:"
    di as error "    data\intermediate\ia_review\final_match_preIA.csv"
    di as error "  Save the scored file back as: final_match_postIA.csv"
    di as error "  Then re-run 00_master.do (or re-run this script)."
    di as error "======================================================"
    exit 1
}

capture confirm file "$int\final_match_postIA.csv"
if _rc != 0 {
    di as error " "
    di as error "======================================================"
    di as error "  STOP — AI-scored cross-country match file not found."
    di as error "  Run the AI review on:"
    di as error "    data\intermediate\ia_review\final_match_preIA.csv"
    di as error "  Save the scored file back as: final_match_postIA.csv"
    di as error "  Then re-run 00_master.do (or re-run this script)."
    di as error "======================================================"
    exit 1
}

// ============================================================================
// STAGE 3 — CROSS-COUNTRY FUZZY MATCH + AI VALIDATION
// ----------------------------------------------------------------------------
// One final fuzzy pass on all remaining unmatched pairs (script 04).
// Same confidence threshold and AI filter as Stage 2.
// ============================================================================

import delimited "$int\fuzzy_match_post10cou.csv", clear
keep original_name matched_name conf_y
gen company_name = matched_name
gen firm_name = original_name
drop if conf_y > -0.6
keep company_name firm_name
export delimited using "$ia\final_match_preIA.csv", replace

// Load AI-validated final matches
import delimited "$int\final_match_postIA.csv", clear
keep if q1 == "Yes"
drop q1 q2
gen firm_name_ = firm_name
drop firm_name
rename firm_name_ firm_name
duplicates drop company_name firm_name, force
save "$int\final_match_postIA.dta", replace

// ============================================================================
// STAGE 4 — ASSEMBLE THE FINAL MATCHED EXPORTER DATABASE
// ============================================================================

// Consolidate Tax ID matches (merge the three Tax ID match files)
use "$int\list_exporters_10c_ALC_uniqueTax_merge1.dta", clear
append using "$int\list_exporters_10c_ALC_uniqueTax_merge2.dta"
append using "$int\list_exporters_10c_ALC_uniqueTax_merge3.dta"

gen Tax_ID = Tax_ID1
replace Tax_ID = Tax_ID2 if Tax_ID == ""
replace Tax_ID = Tax_ID3 if Tax_ID == ""
drop Tax_ID1 Tax_ID2 Tax_ID3

duplicates drop Tax_ID, force
rename firm_name firmname
rename conf confianza
rename country_orig country
save "$int\list_exporters_10c_ALC_uniqueTax_final_merge.dta", replace

// Append all country-level AI matches and merge against customs list
use "$int\list_exporters_10c_ALC_utf8.dta", clear

use "$ia\Match_postIA_ARG.dta", clear
gen country_orig = "ARG"
foreach x in "CHL" "COL" "CRI" "DOM" "ECU" "PER" "PRY" "SLV" "URY" {
    append using "$ia\Match_postIA_`x'.dta"
    replace country_orig = "`x'" if country_orig == ""
}

merge 1:m firm_name country_orig using "$int\list_exporters_10c_ALC_utf8.dta"
rename _merge _merge_10cou

sort firm_name company_name Tax_ID
replace Tax_ID = Tax_ID[_n+1] if Tax_ID == ""
rename company_name company

merge m:1 firm_name using "$int\final_match_postIA.dta"
drop if _merge == 2
replace company = company_name if company == ""
drop company_name
rename company company_name
rename _merge _merge_final

// Merge Orbis/DNB corporate info via Tax ID
merge m:1 Tax_ID using "$int\list_exporters_10c_ALC_uniqueTax_final_merge.dta"
drop if _merge == 2

save "$int\list_exporters_10c_ALC_FINAL.dta", replace

// Merge full Orbis/DNB information on company names
use "$int\Merge_DNB_Orbis_PostIA_v2.dta", clear
gen company_name = name_aff if _merge_DNB == 1
replace company_name = matched_name if _merge_DNB != 1
duplicates drop company_name, force
drop if company_name == ""
save "$int\Merge_DNB_Orbis_PostIA_v3.dta", replace

merge 1:m company_name using "$int\list_exporters_10c_ALC_FINAL.dta"
drop if _merge == 1
order company_name firm_name country_orig Tax_ID _merge_TaxID _merge_10cou _merge_final _merge
rename _merge _merge_DNB_Orbis
order company_name-iso2_parent iso3_subsidiary iso3_parent

save "$int\list_exporters_10c_ALC_FINAL_matched.dta"

// ============================================================================
// STAGE 5 — AI DUPLICATE REVIEW (FINAL PASS)
// ----------------------------------------------------------------------------
// For firm names that matched multiple Orbis/DNB entries, a second AI pass
// ranks duplicates by match probability (Q3=1 is the best candidate).
//
// AI PROMPT USED (Q3 ranking extension):
//   Same as Stage 2 prompt, but adds:
//     Q3: rank from 1 to n (1 = most probable match among duplicates)
//   This allows deterministic resolution of one-to-many matches.
// ============================================================================

import delimited "$int\final_match_duplicates_reviewed_final4.csv", clear
drop if q1 == "Non"
drop if q3 != 1
drop q1 q2 q3

gen company_name_ = company_name
gen firm_name_ = firm_name
drop company_name firm_name
rename company_name_ company_name
rename firm_name_ firm_name

save "$int\list_after_final_review.dta", replace

use "$int\list_exporters_10c_ALC_FINAL_matched.dta", clear
merge m:1 company_name firm_name using "$int\list_after_final_review.dta"
rename _merge _merge_final_review
replace company_name = "" if _merge_final_review == 1
save "$int\list_exporters_10c_ALC_FINAL_matched_reviewed.dta", replace

// ============================================================================
// STAGE 6 — MERGE CUSTOMS TRADE VALUES (FIRM-PRODUCT-DESTINATION-YEAR)
// ============================================================================

// Build aggregated customs file (sum of FOB values by firm × product × dest × year)
use "$cust\exp_fdpt_10c_names_180625.dta", clear

drop if Tax_ID == "." | Tax_ID == "" & firm_name == ""
drop if Tax_ID == "." | Tax_ID == "" & firm_name == "X X"

// Forward-fill firm names within Tax_ID groups to recover missing names
gsort country_orig Tax_ID -firm_name
bys country_orig Tax_ID: carryforward firm_name, gen(firm_name_aux)
replace firm_name = firm_name_aux if firm_name == "" & firm_name_aux != ""
drop firm_name_aux
replace Tax_ID = trim(Tax_ID)

collapse (sum) value_fob (mean) mean_value_fob = value_fob, ///
    by(country_orig Tax_ID country_dest year hs07_6d)

save "$cust\exp_f_10c_sum_product_complete.dta", replace

// Bring MNE attributes to the customs level (carry forward within Tax_ID)
use "$int\list_exporters_10c_ALC_FINAL_matched_reviewed.dta", clear
sort country_orig Tax_ID

local id_vars "company_name subsidiarybvdid guo25 iso2_subsidiary iso2_parent iso3_subsidiary iso3_parent name_aff name_par ussic_aff_4 naics_aff_6 ussic_par_4 naics_par_6 ussic_aff_2 naics_aff_2 ussic_par_2 naics_par_2 ussic_aff_let ussic_par_let status_aff date_incorp_aff year_incorp_aff status_par date_incorp_par year_incorp_par ent_name_aff ent_type_aff ent_name_par ent_type_par nationalID_num1_aff nationalID_num2_aff nationalID_num3_aff nationalID_num1_par nationalID_num2_par nationalID_num3_par orbis_name_1 companyname original_name match_final_1 match_final_2 match_final_3 matched_name dunsnumber cityname countryname yearstarted primary6digitnaicscode globalultimatedunsnumber globalultimatebusinessname globalultimatecityname globalultimatecountry globalultimateprimarynaicsco gobalultimateyearstarted naics_2_c naics_2_h naics_4_c naics_4_h iso3_aff iso2_aff iso3_par iso2_par _merge_DNB _merge_final_review"

foreach var of local id_vars {
    by country_orig Tax_ID: replace `var' = `var'[_n-1] if missing(`var')
    by country_orig Tax_ID: replace `var' = `var'[_n+1] if missing(`var')
}

local merge_vars "_merge_TaxID _merge_10cou _merge_final _merge_DNB_Orbis informationdate affiliates parents parents_sect _merge_entities _merge_identifiers conf q2 match_final_1 match_final_2 match_final_3 _merge_DNB _merge_final_review"

foreach var of local merge_vars {
    by country_orig Tax_ID: egen max_`var' = max(`var')
}
foreach var of local merge_vars {
    drop `var'
    rename max_`var' `var'
}

bysort country_orig Tax_ID: keep if _n == 1
merge 1:m country_orig Tax_ID using "$cust\exp_f_10c_sum_product_complete.dta", gen(m_trade)
save "$cust\list_exporters_10c_ALC_FINAL_matched_reviewed_with_value_exp_sum_product_complete.dta", replace

// ============================================================================
// STAGE 7 — BUILD THE MAIN ANALYSIS DATASET
// ----------------------------------------------------------------------------
// Resolve any remaining duplicates, append manual review corrections,
// standardise company name encoding, and merge final Orbis/DNB attributes.
// ============================================================================

use "$cust\list_exporters_10c_ALC_FINAL_matched_reviewed_with_value_exp_sum_product_complete.dta", clear

// Normalise _merge_final_review: 0 = reviewed duplicate, 3 = confirmed match
replace _merge_final_review = 0 if _merge_final_review == 3
sort Tax_ID country_orig hs07_6d year country_dest _merge_final_review
bysort Tax_ID country_orig year country_dest hs07_6d: gen duplic = _n
replace duplic = 1 if Tax_ID == "" | Tax_ID == "."
replace duplic = 1 if _merge_final_review == 0
drop if duplic != 1
replace _merge_final_review = 1 if _merge_final_review == .
replace _merge_final_review = 3 if _merge_final_review == 0
drop if value_fob == .

// Propagate firm identifiers across product-destination rows
bysort Tax_ID country_orig hs07_6d year country_dest: ereplace subsidiarybvdid = mode(subsidiarybvdid)
bysort Tax_ID country_orig hs07_6d year country_dest: ereplace dunsnumber = mode(dunsnumber)
bysort Tax_ID country_orig hs07_6d year country_dest: ereplace ent_name_aff = mode(ent_name_aff)
bysort Tax_ID country_orig hs07_6d year country_dest: ereplace companyname = mode(companyname)

gen value_fob_sorted = -value_fob
bysort Tax_ID hs07_6d year country_dest: keep if _n == 1

// Identify source database (DNB, Orbis, or both)
gen DNB_Orbis = ""
replace DNB_Orbis = "Orbis" if subsidiarybvdid != ""
replace DNB_Orbis = "DNB"   if dunsnumber != .
replace DNB_Orbis = "Both"  if dunsnumber != . & subsidiarybvdid != ""

// Merge manual review corrections for top exporters
merge m:1 country_orig Tax_ID using "$cust\Base_revision_manual_exporters_DNB_Orbis_manualrev_nodup.dta"
replace company_name = firm_name_match if company_name == ""
replace company_name = "" if Manually_found == "FOUND-NO"

keep country_orig hs07_6d year country_dest value_fob _merge_final_review ///
     company_name firm_name Tax_ID _merge_TaxID _merge_10cou _merge_final  ///
     _merge_DNB_Orbis value_fob_sorted ranking DNB_Orbis Manually_found    ///
     firm_name_match location web

// Standardise UTF-8 encoding issues in company names (Windows-1252 artifacts)
replace company_name = subinstr(company_name, "ÃÂº", "ú", .)
replace company_name = subinstr(company_name, "Ãº",  "ú", .)
replace company_name = subinstr(company_name, "Ã³",  "ó", .)
replace company_name = subinstr(company_name, "Â³",  "ó", .)
replace company_name = subinstr(company_name, "ÃÂ±ÃÂ", "ñí", .)
replace company_name = subinstr(company_name, "ÃÂ",  "ñ", .)
replace company_name = subinstr(company_name, "Ã±",  "ñ", .)
replace company_name = subinstr(company_name, "Ã",   "í", .)
replace company_name = upper(company_name)
replace company_name = subinstr(company_name, "ñ", "Ñ", .)
replace company_name = subinstr(company_name, "í", "Í", .)
replace company_name = subinstr(company_name, "ó", "Ó", .)
replace company_name = subinstr(company_name, "ú", "Ú", .)
replace company_name = subinstr(company_name, "é", "É", .)
replace company_name = subinstr(company_name, "á", "Á", .)

// Manual corrections for known encoding failures
replace company_name = "GADOR PARAGUAY SA"    if company_name == "GADOR PARAGUAY SA}"
replace company_name = "METROCOLOR DE MEXICO" if company_name == "METROCOLOR DE MÉXICO"
replace company_name = "PETROQUIM S.R.L"      if company_name == "PETROQUIM S A"

// Final merge: attach full corporate attributes
merge m:1 company_name using "$int\Merge_DNB_Orbis_PostIA_v4.dta", keep(1 3)
tab _merge if company_name != ""
drop _merge

replace _merge_final_review = 3 if company_name != ""
duplicates drop country_orig year country_dest Tax_ID hs07_6d, force

replace value_fob = -value_fob if value_fob < 0
replace _merge_final_review = 1 if company_name == ""

// Construct unified firm ID across Orbis (BvD) and DNB (DUNS)
tostring dunsnumber, replace
gen ID_Orbis_DNB = guo25
replace ID_Orbis_DNB = dunsnumber if _merge_DNB == 2

// Convert ISO2 → ISO3 country codes for parent and subsidiary
drop iso3_subsidiary iso3_parent
kountry iso2_parent,    from(iso2c) to(iso3c)
rename _ISO3C_ iso3_parent
replace iso3_parent = "CUW" if iso2_parent == "CW"
replace iso3_parent = iso3_par if iso3_parent == ""

kountry iso2_subsidiary, from(iso2c) to(iso3c)
rename _ISO3C_ iso3_subsidiary
replace iso3_subsidiary = "CUW" if iso2_subsidiary == "CW"
replace iso3_subsidiary = iso3_aff if iso3_subsidiary == ""

save "$raw\Base_final_Customs_DNB_Orbis_product_complete.dta", replace

// ============================================================================
// STAGE 8 — MERGE PRODUCT CHARACTERISTICS AND GRAVITY VARIABLES
// ============================================================================

// Harmonise HS 2007 codes to HS 2002 product characteristics data
use "$reg\product_characteristics_hs6_2002.dta", clear
rename hs6_2002 hs2002productcode
merge 1:m hs2002productcode using "$reg\Concordance_HS_2007_2002_WITS.dta"
keep if _merge == 3
drop _merge
rename hs2007productcode hs07_6d
order hs07_6d hs2007productdescription hs2002productcode hs2002productdescription
save "$reg\product_characteristics_hs6_2002_adj.dta", replace

// ============================================================================
// DESCRIPTIVE CHECK — MATCH COVERAGE BY COUNTRY AND MNE STATUS
// ============================================================================

use "$raw\Base_final_Customs_DNB_Orbis_product_complete.dta", clear

di "=== Match coverage: trade value by country and MNE status ==="
table country_orig _merge_final_review, stat(sum value_fob) nformat(%17.0fc)

di "=== Match coverage: firm count by country and MNE status ==="
table country_orig _merge_final_review, stat(count value_fob) nformat(%17.0fc)

// ============================================================================
// END OF SCRIPT
// Main output: $raw\Base_final_Customs_DNB_Orbis_product_complete.dta
//   Key variables: firm_name, Tax_ID, country_orig, country_dest, year,
//                  hs07_6d, value_fob, _merge_final_review (1=domestic, 3=MNE)
//                  subsidiarybvdid, guo25, iso3_parent, iso3_subsidiary
// ============================================================================
