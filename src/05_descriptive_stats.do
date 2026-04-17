/*==============================================================================
  05_descriptive_stats.do

  PURPOSE:
    Produce descriptive statistics tables comparing MNE types (foreign MNE,
    domestic MNE, unknown parent, non-MNE) across years and exporting countries.
    Output is an Excel workbook with both raw and wide-format (reshaped) sheets.

  MNE DEFINITIONS:
    MNE_ext   (=1) — foreign subsidiary: parent country != exporting country
    MNE_dom   (=1) — domestic MNE: parent country = exporting country
    MNE_total (=1) — any firm matched in the corporate database
    Non-MNE   (=0 for all above)

  INPUTS:
    $raw\Base_final_Customs_DNB_Orbis_product_complete.dta  (from script 02)

  OUTPUTS:
    $tables\MNE_Descriptive_Stats.xlsx
      T1_Overall_Raw   — firm counts, trade values, destinations, products by year
      T1_Overall_Adj   — same, reshaped wide by MNE category
      T2_ByCountry_Raw — same breakdown by exporting country
      T2_ByCountry_Adj — same, reshaped wide

  AUTHOR: Sebastian Velasquez (IDB)
  LAST UPDATED: March 2026
==============================================================================*/

clear all
set more off
set matsize 11000

// ============================================================================
// PATH CONFIGURATION — set $root once; all other paths are derived
// ============================================================================

global root    "C:\Sebas BID\Orbis_DNB_Customs_Final"
global raw     "$root\data\raw"
global int     "$root\data\intermediate"
global output  "$root\output"
global graphs  "$output\graphs"
global tables  "$output\tables"
global regs    "$output\regressions"

// Create output folders if they do not yet exist
capture mkdir "$output"
capture mkdir "$tables"

// ============================================================================
// LOAD DATA
// ============================================================================

use "$raw\Base_final_Customs_DNB_Orbis_product_complete.dta", clear

*----------------------------------------------------------------------
* 0  Three MNE definitions
*----------------------------------------------------------------------

* MNE_ext: foreign subsidiary (parent country differs from exporting country)
gen byte MNE_ext   = (_merge_final_review == 3) & (iso3_parent != "") ///
                   & (iso3_parent != country_orig)
gen byte DOM_ext   = 1 - MNE_ext

* MNE_dom: domestic MNE (matched in corporate DB, parent = exporting country)
gen byte MNE_dom   = (_merge_final_review == 3) & (iso3_parent == country_orig)
gen byte DOM_dom   = 1 - MNE_dom

* MNE_total: any firm matched in the corporate database
gen byte MNE_total = (_merge_final_review == 3)
gen byte DOM_total = 1 - MNE_total

* Convenience aliases (MNE = MNE_ext baseline used in network section)
gen byte MNE = MNE_ext
gen byte DOM = DOM_ext

label var MNE_ext    "=1 if foreign subsidiary (parent != exporting country)"
label var DOM_ext    "=1 if not a foreign subsidiary"
label var MNE_dom    "=1 if domestic MNE (matched, parent = exporting country)"
label var DOM_dom    "=1 if not a domestic MNE"
label var MNE_total  "=1 if any MNE (ext OR dom)"
label var DOM_total  "=1 if not matched in corporate database"
label var MNE        "=1 if MNE (baseline alias = MNE_ext)"
label var DOM        "=1 if domestic (baseline alias = DOM_ext)"




// ============================================================================
// CREATE MUTUALLY EXCLUSIVE MNE CATEGORIES
// ============================================================================

gen byte mne_category = .
label define mne_cat 1 "Foreign MNE" 2 "Domestic MNE" 3 "Unknown Parent" 4 "Non-MNE"

// Foreign MNE: MNE_ext = 1 (parent from different country, identified)
replace mne_category = 1 if MNE_ext == 1

// Domestic MNE: MNE_dom = 1 (parent from same country)
replace mne_category = 2 if MNE_dom == 1

// Unknown Parent: MNE_total=1 but iso3_parent is missing/empty
replace mne_category = 3 if MNE_total == 1 & iso3_parent == "" & mne_category == .

// Non-MNE: everything else
replace mne_category = 4 if mne_category == .

label values mne_category mne_cat

// Verify counts
di "Verification of MNE categories:"
tabulate mne_category

// ============================================================================
// TABLE 1: OVERALL BREAKDOWN BY YEAR AND MNE CATEGORY
// ============================================================================

di "Creating Table 1: Overall by Year and MNE Category..."


preserve

	bysort mne_category firm_name year: gen n_firms=_n
	replace n_firms=0 if n_firms!=1

	bysort mne_category country_dest year: gen n_destinations=_n
	replace n_destinations=0 if n_destinations!=1

	bysort mne_category hs07_6d year: gen n_products=_n
	replace n_products=0 if n_products!=1

	collapse (count) n_obs=value_fob ///
			 (sum) total_value=value_fob n_firms n_destinations n_products ///
			 (mean) mean_value=value_fob ///
			 (median) median_value=value_fob, ///
			 by(year mne_category)

	rename mne_category mne_cat

	// Save raw version
	save "$tables\MNE_DescStats_Table1_Raw.dta", replace
	export excel year mne_cat n_obs total_value mean_value median_value ///
		n_firms n_destinations n_products ///
		using "$tables\MNE_Descriptive_Stats.xlsx", ///
		sheet("T1_Overall_Raw") replace  firstrow(variables)
		
	reshape	wide n_obs total_value n_firms n_destinations n_products mean_value median_value, i(year) j(mne_cat)
	
	order year n_obs* total_value* n_firms* n_dest* n_prod* mean_value* median_value*
	
	export excel using "$tables\MNE_Descriptive_Stats.xlsx", ///
		sheet("T1_Overall_Adj") firstrow(variables)
	
	di "Table 1 raw saved"

restore

// ============================================================================
// TABLE 2: BREAKDOWN BY EXPORTING COUNTRY, YEAR, AND MNE CATEGORY
// ============================================================================

di "Creating Table 2: By Exporting Country, Year, and MNE Category..."

preserve

	bysort mne_category firm_name country_orig year: gen n_firms=_n
	replace n_firms=0 if n_firms!=1

	bysort mne_category country_dest country_orig year: gen n_destinations=_n
	replace n_destinations=0 if n_destinations!=1

	bysort mne_category hs07_6d country_orig year: gen n_products=_n
	replace n_products=0 if n_products!=1

	collapse (count) n_obs=value_fob ///
			 (sum) total_value=value_fob n_firms n_destinations n_products ///
			 (mean) mean_value=value_fob ///
			 (median) median_value=value_fob, ///
			 by(country_orig year mne_category)

	rename mne_category mne_cat

	save "$tables\MNE_DescStats_Table2_Raw.dta", replace
	export excel country_orig year mne_cat n_obs total_value mean_value median_value ///
		n_firms n_destinations n_products ///
		using "$tables\MNE_Descriptive_Stats.xlsx", ///
		sheet("T2_ByCountry_Raw") firstrow(variables)

	reshape	wide n_obs total_value n_firms n_destinations n_products mean_value median_value, i(year country_orig) j(mne_cat)
	
	order country_orig year n_obs* total_value* n_firms* n_dest* n_prod* mean_value* median_value*
	
	sort country_orig year
	
	export excel using "$tables\MNE_Descriptive_Stats.xlsx", ///
		sheet("T2_ByCountry_Adj") firstrow(variables)
		
	di "Table 2 raw saved"

restore



