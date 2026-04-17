/*==============================================================================
  02_build_orbis_database.do

  PURPOSE:
    After script 01 builds the matched dataset, some firms have a BvD ID but
    a missing parent country — the regular matching process couldn't find it.
    This script goes back to the raw Orbis ownership files, looks up those
    specific firms by BvD ID, and recovers their parent country information.

    The output is a small lookup file that scripts 06 and 07 merge in to fill
    those gaps before running regressions.

    Run this script AFTER script 01, not before.

  WHEN TO RUN:
    After 01_match_customs_mne.do has finished and produced:
      data\raw\Base_final_Customs_DNB_Orbis_product_complete.dta

  INPUTS:
    $raw\Base_final_Customs_DNB_Orbis_product_complete.dta  (from script 01)
    $orbis_raw\Ownership\Txt\Chunky\Links_current_000X.txt  (Orbis raw files,
                                                             chunks 01-41)

  OUTPUTS:
    $orbis_int\Links_current_000X.dta   — intermediate per-chunk files
    $orbis_int\Links_current_v1.dta     — full ownership lookup table
    $raw\Unknown_countries_Base_final_Customs_DNB_Orbis_with_parent_country.dta
                                        — parent country info for previously
                                          unknown firms (used by scripts 06/07)

  KEY VARIABLES IN OUTPUT:
    subsidiarybvdid  — BvD ID of the subsidiary firm
    iso2_subsidiary  — ISO2 country code of the subsidiary
    iso2_parent      — ISO2 country code of the parent (from GUO25 BvD ID prefix)
    same_cou         — 1 if subsidiary and parent are in the same country
    Parent_ISO2_1-4  — up to 4 unique parent country codes

  NOTES:
    - Orbis raw data comes in 41 text files (around 5 million rows each).
    - The same subsidiary can appear in multiple chunks — duplicates are
      removed after everything is appended together.
    - Ownership type codes need cleaning: "GUO 25" becomes "GUO25", etc.
    - You need a Bureau van Dijk Orbis licence to access the raw files.

  AUTHOR: Sebastian Velasquez (IDB)
  LAST UPDATED: March 2026
==============================================================================*/

clear all
set more off

// ============================================================================
// PATH CONFIGURATION
// ----------------------------------------------------------------------------
// Set the two globals below to match your local Orbis data location.
// All other paths are derived automatically.
// ============================================================================

* Root folder for raw Orbis text files (chunked .txt ownership links)
global orbis_raw  "D:\BID\Orbis\FINAL"

* Root folder for processed .dta output files
global orbis_out  "D:\BID\Orbis\FINAL\Ownership\Dta"

* Derived paths (no need to change)
global orbis_txt  "$orbis_raw\Ownership\Txt\Chunky"
global orbis_int  "$orbis_out\entity_information\intermediate"

// ============================================================================
// PART 1 — IMPORT CHUNKED RAW FILES AND EXTRACT OWNERSHIP LINKS
// ----------------------------------------------------------------------------
// Loop over all 41 chunks. For each chunk:
//   1. Import the delimited text file
//   2. Extract the subsidiary's ISO2 country from the BvD ID prefix
//   3. Keep only the columns needed for the ownership network
//   4. Drop exact duplicates within the chunk
// ============================================================================

* Chunks 01-09 (zero-padded to 4 digits)
forvalues i = 1(1)9 {
    import delimited "$orbis_txt\Links_current_000`i'.txt", clear

    // Check ownership type distribution
    tab typeofrelation

    // ISO2 country code is embedded in the first 2 characters of the BvD ID
    gen Country_ISO2 = substr(subsidiarybvdid, 1, 2)

    keep subsidiarybvdid typeofrelation Country_ISO2 Parent_ISO2
    duplicates drop subsidiarybvdid typeofrelation Country_ISO2 Parent_ISO2, force

    save "$orbis_int\Links_current_000`i'.dta", replace
}

* Chunks 10-41
forvalues i = 10(1)41 {
    import delimited "$orbis_txt\Links_current_00`i'.txt", clear

    tab typeofrelation

    gen Country_ISO2 = substr(subsidiarybvdid, 1, 2)

    keep subsidiarybvdid typeofrelation Country_ISO2 Parent_ISO2
    duplicates drop subsidiarybvdid typeofrelation Country_ISO2 Parent_ISO2, force

    save "$orbis_int\Links_current_00`i'.dta", replace
}

// ============================================================================
// PART 2 — STANDARDISE OWNERSHIP TYPE CODES AND RESHAPE TO WIDE FORMAT
// ----------------------------------------------------------------------------
// Ownership types arrive with spaces ("GUO 25") but Stata requires no spaces
// in variable name suffixes for reshape. Standardise to "GUO25", etc.
// Then reshape so each subsidiary has one row, with parent countries in
// separate columns (Parent_ISO2_1 through Parent_ISO2_4 for unique parents).
// ============================================================================

* Process chunks 01-09
forvalues j = 1(1)9 {
    use "$orbis_int\Links_current_000`j'.dta", clear

    drop guo25   // Dropped here; GUO25 is reconstructed after reshape

    keep subsidiarybvdid typeofrelation Country_ISO2 Parent_ISO2
    duplicates drop subsidiarybvdid typeofrelation Country_ISO2 Parent_ISO2, force

    // Standardise ownership type codes (remove spaces)
    replace typeofrelation = "DUO25"  if typeofrelation == "DUO 25"
    replace typeofrelation = "DUO25C" if typeofrelation == "DUO 25C"
    replace typeofrelation = "DUO50"  if typeofrelation == "DUO 50"
    replace typeofrelation = "DUO50C" if typeofrelation == "DUO 50C"
    replace typeofrelation = "GUO25"  if typeofrelation == "GUO 25"
    replace typeofrelation = "GUO25C" if typeofrelation == "GUO 25C"
    replace typeofrelation = "GUO50"  if typeofrelation == "GUO 50"
    replace typeofrelation = "GUO50C" if typeofrelation == "GUO 50C"

    // Number each type-of-relation occurrence within a subsidiary to create
    // unique column names for the reshape (e.g., GUO251, GUO252)
    bysort subsidiarybvdid typeofrelation: gen num = _n
    tostring num, replace
    gen typerelation = typeofrelation + num
    drop num typeofrelation

    reshape wide Parent_ISO2, i(subsidiarybvdid) j(typerelation) string

    // Identify all source parent-country columns (excludes subsidiary ID and ISO2)
    unab allvars : _all
    local source_vars ""
    foreach var of local allvars {
        if "`var'" != "subsidiarybvdid" & "`var'" != "Country_ISO2" {
            local source_vars `source_vars' `var'
        }
    }

    keep subsidiarybvdid `source_vars'

    // Create up to 4 unique parent country variables (de-duplicated, ordered
    // by first appearance across all ownership-type columns)
    forvalues i = 1/4 {
        gen Parent_ISO2_`i' = ""
    }

    local n = _N
    forvalues obs = 1/`n' {
        local unique_countries ""

        foreach var of local source_vars {
            local val = `var'[`obs']
            if "`val'" != "" {
                local found = 0
                foreach country of local unique_countries {
                    if "`country'" == "`val'" {
                        local found = 1
                    }
                }
                if `found' == 0 {
                    local unique_countries `unique_countries' `val'
                }
            }
        }

        local count = 1
        foreach country of local unique_countries {
            if `count' <= 4 {
                replace Parent_ISO2_`count' = "`country'" in `obs'
                local count = `count' + 1
            }
        }
    }

    keep subsidiarybvdid Country_ISO2 Parent_ISO2GUO251 Parent_ISO2GUO252 Parent_ISO2_1-Parent_ISO2_4

    save "$orbis_int\Links_current_000`j'.dta", replace
}

* Process chunks 10-41 (same logic, different zero-padding)
forvalues j = 10(1)41 {
    use "$orbis_int\Links_current_00`j'.dta", clear

    drop guo25

    keep subsidiarybvdid typeofrelation Country_ISO2 Parent_ISO2
    duplicates drop subsidiarybvdid typeofrelation Country_ISO2 Parent_ISO2, force

    replace typeofrelation = "DUO25"  if typeofrelation == "DUO 25"
    replace typeofrelation = "DUO25C" if typeofrelation == "DUO 25C"
    replace typeofrelation = "DUO50"  if typeofrelation == "DUO 50"
    replace typeofrelation = "DUO50C" if typeofrelation == "DUO 50C"
    replace typeofrelation = "GUO25"  if typeofrelation == "GUO 25"
    replace typeofrelation = "GUO25C" if typeofrelation == "GUO 25C"
    replace typeofrelation = "GUO50"  if typeofrelation == "GUO 50"
    replace typeofrelation = "GUO50C" if typeofrelation == "GUO 50C"

    bysort subsidiarybvdid typeofrelation: gen num = _n
    tostring num, replace
    gen typerelation = typeofrelation + num
    drop num typeofrelation

    reshape wide Parent_ISO2, i(subsidiarybvdid) j(typerelation) string

    unab allvars : _all
    local source_vars ""
    foreach var of local allvars {
        if "`var'" != "subsidiarybvdid" & "`var'" != "Country_ISO2" {
            local source_vars `source_vars' `var'
        }
    }

    keep subsidiarybvdid `source_vars'

    forvalues i = 1/4 {
        gen Parent_ISO2_`i' = ""
    }

    local n = _N
    forvalues obs = 1/`n' {
        local unique_countries ""

        foreach var of local source_vars {
            local val = `var'[`obs']
            if "`val'" != "" {
                local found = 0
                foreach country of local unique_countries {
                    if "`country'" == "`val'" {
                        local found = 1
                    }
                }
                if `found' == 0 {
                    local unique_countries `unique_countries' `val'
                }
            }
        }

        local count = 1
        foreach country of local unique_countries {
            if `count' <= 4 {
                replace Parent_ISO2_`count' = "`country'" in `obs'
                local count = `count' + 1
            }
        }
    }

    keep subsidiarybvdid Country_ISO2 Parent_ISO2GUO251 Parent_ISO2GUO252 Parent_ISO2_1-Parent_ISO2_4

    save "$orbis_int\Links_current_00`j'.dta", replace
}

// ============================================================================
// PART 3 — APPEND ALL CHUNKS INTO A CONSOLIDATED OWNERSHIP DATABASE
// ----------------------------------------------------------------------------
// Chunking may split one subsidiary's ownership rows across multiple files,
// so duplicates must be re-checked after appending.
// ============================================================================

use "$orbis_int\Links_current_0001.dta", clear

forvalues i = 1(1)9 {
    append using "$orbis_int\Links_current_000`i'.dta"
}

forvalues i = 10(1)41 {
    append using "$orbis_int\Links_current_00`i'.dta"
}

// Re-drop duplicates introduced by chunk boundaries
sort subsidiarybvdid guo25 informationdate
bysort subsidiarybvdid guo25: gen order = _n
drop if order != 1
drop order

duplicates report subsidiarybvdid guo25

// ============================================================================
// PART 4 — CREATE COUNTRY IDENTIFIER VARIABLES
// ============================================================================

rename Country_ISO2 iso2_subsidiary

// Parent ISO2 is the first 2 characters of the Global Ultimate Owner BvD ID
gen iso2_parent = substr(guo25, 1, 2)

// Flag domestic MNEs: subsidiary and ultimate owner in the same country
gen same_cou = 1 if iso2_subsidiary == iso2_parent
label var iso2_subsidiary "ISO2 country code of the subsidiary"
label var iso2_parent     "ISO2 country code of the GUO parent"
label var same_cou        "=1 if subsidiary and parent are in the same country"

save "$orbis_int\Links_current_v1.dta", replace

// ============================================================================
// END OF SCRIPT
// Variables in output: subsidiarybvdid, informationdate, guo25,
//                      iso2_subsidiary, iso2_parent, same_cou
// ============================================================================
