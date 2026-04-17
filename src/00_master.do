/*==============================================================================
  00_master.do

  MULTINATIONAL FIRMS AND TRADE IN LATIN AMERICA
  Master script — runs the full pipeline

  HOW TO USE THIS SCRIPT
  ──────────────────────
  1. Set the two paths at the bottom of the "USER CONFIGURATION" section below.

  2. Run this script. It will stop automatically the first time it needs you
     to do something outside of Stata (run a Python script or do an AI review).
     Follow the on-screen instructions, then re-run this script. Repeat until
     it runs all the way through.

     The full process requires three separate runs of this master script:

       Run 1 → Script 02 runs through the first matching stage, then stops.
                It will tell you to run:
                  python src\03_fuzzy_match_by_country.py
                Then send the output CSVs to GPT-4 or Gemini for review.
                (See data\README.md for the exact AI prompt to use.)

       Run 2 → Script 02 continues through the second matching stage, then stops.
                It will tell you to run:
                  python src\04_fuzzy_match_post10cou.py
                Then do the AI review again on the new output CSVs.

       Run 3 → Script 02 finishes, script 01 looks up missing parent countries,
                and scripts 05-08 run the full analysis. Done.

  3. If you already have the final matched dataset
     (Base_final_Customs_DNB_Orbis_product_complete.dta), place it in
     data\raw\ and skip straight to the analysis scripts (05-08).
     You can do this by commenting out the script 02 and script 01 calls below.

  ──────────────────────────────────────────────────────────────────────────────
  PIPELINE OVERVIEW
  ──────────────────────────────────────────────────────────────────────────────

  Script  | What it does
  ────────┼──────────────────────────────────────────────────────────────────
  01      | Matches customs exporters to MNEs using Tax IDs and firm names.
          |   → Stage 2a: exports name lists for Python fuzzy match (script 03)
          |   → [PAUSE] run 03_fuzzy_match_by_country.py + AI review
          |   → Stage 2b–2c: processes fuzzy match results, exports for script 04
          |   → [PAUSE] run 04_fuzzy_match_post10cou.py + AI review
          |   → Stages 3-8: assembles the final matched dataset
  02      | Takes the matched dataset and finds missing parent country info
          | by looking up firm BvD IDs directly in the raw Orbis files.
          | Produces: Unknown_countries_...dta (used in scripts 06 and 07)
  03 (py) | Fuzzy name matching, one pass per country  [runs inside script 01]
  04 (py) | Fuzzy name matching, final cross-country pass [runs inside script 01]
  05      | Descriptive statistics: MNE share of exports by country and sector
  06      | Main analysis: what drives MNE presence + how MNEs affect trade
  07      | Same analysis but only for agricultural exports (HS chapters 1-24)
  08      | Policy report figures and tables (agriculture)
  ────────┴──────────────────────────────────────────────────────────────────

  COUNTRIES: ARG  CHL  COL  CRI  DOM  ECU  PER  PRY  SLV  URY

  AUTHOR:
    Sebastian Velasquez (IDB)

  LAST UPDATED: March 2026
==============================================================================*/

clear all
set more off
version 17.0

// ============================================================================
// USER CONFIGURATION
// Edit these two lines, then run the script.
// ============================================================================

* Path to this repository on your machine (the folder that contains src/, data/, etc.)
global root "C:\Sebas BID\Orbis_DNB_Customs_Final"

* Path to the raw Orbis bulk-download folder (only needed for script 01).
* Set to "" if you don't have Orbis access or already have the lookup file.
global orbis_raw "D:\BID\Orbis\FINAL"

// ============================================================================
// DERIVED PATHS — no need to edit below this line
// ============================================================================

global raw    "$root\data\raw"
global int    "$root\data\intermediate"
global cust   "$int\customs"
global ia     "$int\ia_review"
global reg    "$int\regressions"
global output "$root\output"
global graphs "$output\graphs"
global tables "$output\tables"
global regs   "$output\regressions"
global agro_root "$root\agro"

global agro_data   "$agro_root\Data"
global agro_int    "$agro_data\Intermediate"
global agro_out    "$agro_root\Output"
global agro_graphs "$agro_out\Graphs"
global agro_tables "$agro_out\Tables"
global agro_regs   "$agro_out\Regressions"

* Overleaf sync folder — set to your own path, or leave as-is to ignore
global overleaf "$root\overleaf"

// ============================================================================
// CREATE FOLDER STRUCTURE
// ============================================================================

foreach dir in "$output" "$graphs" "$tables" "$regs"       ///
               "$agro_root" "$agro_out" "$agro_graphs"     ///
               "$agro_tables" "$agro_regs"                 ///
               "$int" "$cust" "$ia" "$reg" {
    capture mkdir "`dir'"
}

// ============================================================================
// GRAPH STYLE DEFAULTS
// ============================================================================

graph set window fontface "Times New Roman"
set scheme s2color

// ============================================================================
// SCRIPT 01 — Match customs exporters to MNEs
// ----------------------------------------------------------------------------
// This script runs in three sections separated by two pause points.
// It will stop automatically and tell you what to do at each pause.
// Just follow the instructions on screen and re-run this master script.
// ============================================================================

di ""
di ">>> Running 01_match_customs_mne.do ..."
do "$root\src\01_match_customs_mne.do"
di ">>> Script 01 complete."

// ============================================================================
// SCRIPT 02 — Find missing parent countries using raw Orbis files
// ----------------------------------------------------------------------------
// Runs after script 01 because it needs the matched dataset to know which
// firms are missing parent country information. It looks up those firms in
// the raw Orbis ownership files and saves the results for scripts 06 and 07.
// Set orbis_raw to "" above if you don't have the raw Orbis files.
// ============================================================================

if "$orbis_raw" != "" {
    di ""
    di ">>> Running 02_build_orbis_database.do ..."
    do "$root\src\02_build_orbis_database.do"
    di ">>> Script 02 complete."
}
else {
    di ""
    di "NOTE: orbis_raw is not set — skipping script 02."
    di "      Make sure Unknown_countries_...dta already exists in data\raw\"
    di "      if you need parent country info for scripts 06 and 07."
}

// ============================================================================
// SCRIPT 05 — Descriptive statistics
// ============================================================================

di ""
di ">>> Running 05_descriptive_stats.do ..."
do "$root\src\05_descriptive_stats.do"
di ">>> Script 05 complete."

// ============================================================================
// SCRIPT 06 — Main trade analysis (all sectors)
// ============================================================================

di ""
di ">>> Running 06_trade_analysis.do ..."
do "$root\src\06_trade_analysis.do"
di ">>> Script 06 complete."

// ============================================================================
// SCRIPT 07 — Agricultural trade analysis (HS chapters 1-24)
// ============================================================================

di ""
di ">>> Running 07_agro_trade_analysis.do ..."
do "$root\src\07_agro_trade_analysis.do"
di ">>> Script 07 complete."

// ============================================================================
// SCRIPT 08 — Agricultural policy report
// ============================================================================

di ""
di ">>> Running 08_agro_policy_report.do ..."
do "$root\src\08_agro_policy_report.do"
di ">>> Script 08 complete."

// ============================================================================

di ""
di "======================================================="
di "  All done. Outputs saved to:"
di "    Tables     : $tables"
di "    Graphs     : $graphs"
di "    Regressions: $regs"
di "    Agriculture: $agro_out"
di "======================================================="
