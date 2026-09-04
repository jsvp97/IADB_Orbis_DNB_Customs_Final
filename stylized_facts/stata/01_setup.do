**********************************************************************
* 01_setup.do
*
* Globals, packages, graph styling, FE ladders, helper programs.
* Called once from 00_master.do before any analysis do-file.
*
* MNE DEFINITIONS (all loops run over all three):
*   MNE_ext   - foreign subsidiary  (parent country != exporter country)
*   MNE_dom   - domestic MNE        (parent country == exporter country)
*   MNE_total - any matched firm    (MNE_ext OR MNE_dom)
**********************************************************************

clear all
set more off
graph set window fontface "Times New Roman"


**********************************************************************
* SAMPLE EXCLUSIONS
*
* Origins explicitly dropped from the analysis (all stylized facts,
* all tables, all figures, all regressions). Apply at use-site via:
*   drop if inlist(country_orig, $excluded_origins)
* Filter is kept at use-site (not in the upstream cache) so the
* decision remains reversible.
**********************************************************************

global excluded_origins `""ECU""'   // dropped 2026-05-23 -- see CLAUDE.md / memory


**********************************************************************
* DIRECTORIES & FOLDER STRUCTURE
**********************************************************************

global root     "D:\MNEs_Trade"

* Code
global code     "$root\0_Code"

* Inputs (1_Input organized by data source)
global input    "$root\1_Input"
global customs  "$input\Customs"            // Base_final_Customs_DNB_Orbis_product_complete.dta
global gravity  "$input\Gravity"            // Gravity_V202211, tariffsPairs, PTA_BIT_DTT_BID
global product  "$input\Product"            // RCA_WITS, lall2000, ALP_IPC, UNCTAD RHCI, product_characteristics
global country  "$input\Country"            // WB_Income_group
global int      "$input\Intermediate"       // Part-0 outputs + intermediate_mne_presence

* Output roots
global output   "$root\2_Output"
global graphs   "$output\Graphs"
global tables   "$output\Tables"
global regs     "$output\Regressions"

* Overleaf mirror (LaTeX project root)
global overleaf "C:\Users\nnmar\Dropbox\Aplicaciones\Overleaf\Multinational Firms and Trade"

* Section sub-folders: graphs
global g11  "$graphs\1_1_ExportingCountries"
global g12  "$graphs\1_2_DestinationCountries"
global g13  "$graphs\1_3_ByProduct"
global g25  "$graphs\2_5_ExtensiveMargin"

* Section sub-folders: tables
global t_s1  "$tables\S1_Determinants"
global t_s2  "$tables\S2_Effects"
global t_s3  "$tables\S3_Summary"

* Section sub-folders: regressions
global r_s1  "$regs\S1_Determinants"
global r_s2  "$regs\S2_Effects"

* Overleaf mirrors
global ol_g11   "$overleaf\Graphs\1_1_ExportingCountries"
global ol_g12   "$overleaf\Graphs\1_2_DestinationCountries"
global ol_g13   "$overleaf\Graphs\1_3_ByProduct"
global ol_g25   "$overleaf\Graphs\2_5_ExtensiveMargin"
global ol_t_s1  "$overleaf\Tables\S1_Determinants"
global ol_t_s2  "$overleaf\Tables\S2_Effects"
global ol_t_s3  "$overleaf\Tables\S3_Summary"
global ol_r_s1  "$overleaf\Regressions\S1_Determinants"
global ol_r_s2  "$overleaf\Regressions\S2_Effects"

* Create all output directories (capture suppresses error if folder exists)
foreach dir in ///
    "$output" "$graphs" "$tables" "$regs" ///
    "$g11" "$g12" "$g13" "$g25" ///
    "$t_s1" "$t_s2" "$t_s3" ///
    "$r_s1" "$r_s2" ///
    "$int" ///
    "$overleaf" ///
    "$overleaf\Graphs" "$overleaf\Tables" "$overleaf\Regressions" ///
    "$ol_g11" "$ol_g12" "$ol_g13" "$ol_g25" ///
    "$ol_t_s1" "$ol_t_s2" "$ol_t_s3" ///
    "$ol_r_s1" "$ol_r_s2" {
    capture mkdir `"`dir'"'
}


**********************************************************************
* PACKAGES (uncomment on first run)
**********************************************************************
/*
ssc install reghdfe,  replace
ssc install ppmlhdfe, replace
ssc install outreg2,  replace
ssc install ftools,   replace
ssc install labutil,  replace
ssc install estout,   replace
ssc install gtools,   replace
ssc install distinct, replace
*/


**********************************************************************
* GRAPH GLOBALS
**********************************************************************

global c_MNE       "red*1.3"
global c_DOM       "black*0.6"
global c_MNE_light "red*0.6"
global c_MNEdom    "blue*0.7"
global c_MNEtot    "green*0.7"

* White background, no frame (appended to every twoway call)
global gro `"graphregion(fcolor(white) lwidth(none) lpattern(blank)) plotregion(fcolor(white) lwidth(none) lpattern(blank))"'


**********************************************************************
* FIXED-EFFECT SYSTEM
*
* FIX (critical): All FE specs MUST be globals, not locals.
*   Locals defined in the main script are NOT visible inside program
*   definitions. Inside a program, `local fe "`fe`f''"` would silently
*   produce an empty string, running every regression without FE.
*   Using globals and ${fe`f'} solves this.
*
* THREE LADDERS DEFINED:
*   (A) Standard 7-spec (ODY / firm-level): fe1..fe7, fel1..fel7
*   (B) OPY 8-spec: fe_opy1..fe_opy8, fel_opy1..fel_opy8, nfe_opy
*   (C) ODPY 9-spec: fe_odpy1..fe_odpy9, fel_odpy1..fel_odpy9, nfe_odpy
**********************************************************************

* ---- (A) Standard 7-spec ladder ----
global fe1    ""
global fe2    "year"
global fe3    "orig_id year"
global fe4    "orig_id dest_id year"
global fe5    "ot_id dt_id"
global fe6    "od_id year"
global fe7    "ot_id dt_id od_id"

global fel1   "No FE"
global fel2   "Year"
global fel3   "O + Year"
global fel4   "O + D + Year"
global fel5   "OxT + DxT"
global fel6   "OD x Year"
global fel7   "OxT + DxT + OD"

* ---- (B) OPY 8-spec ladder ----
global nfe_opy = 8

global fe_opy1   ""
global fe_opy2   "year"
global fe_opy3   "orig_id year"
global fe_opy4   "ot_id"
global fe_opy5   "pt_id"
global fe_opy6   "ot_id pt_id"
global fe_opy7   "op_id year"
global fe_opy8   "op_id ot_id"

global fel_opy1  "No FE"
global fel_opy2  "Year"
global fel_opy3  "O + Year"
global fel_opy4  "OxT"
global fel_opy5  "PxT"
global fel_opy6  "OxT + PxT"
global fel_opy7  "OP x Year"
global fel_opy8  "OP + OxT"

* ---- (C) ODPY 9-spec ladder ----
global nfe_odpy = 9

global fe_odpy1   ""
global fe_odpy2   "year"
global fe_odpy3   "orig_id year"
global fe_odpy4   "orig_id dest_id year"
global fe_odpy5   "ot_id dt_id"
global fe_odpy6   "od_id year"
global fe_odpy7   "ot_id dt_id od_id"
global fe_odpy8   "odp_id year"
global fe_odpy9   "odp_id ot_id dt_id"

global fel_odpy1  "No FE"
global fel_odpy2  "Year"
global fel_odpy3  "O + Year"
global fel_odpy4  "O + D + Year"
global fel_odpy5  "OxT + DxT"
global fel_odpy6  "OD x Year"
global fel_odpy7  "OxT + DxT + OD"
global fel_odpy8  "ODP x Year"
global fel_odpy9  "ODP + OxT + DxT"


**********************************************************************
* HELPER PROGRAMS
**********************************************************************

* ---- Graph export (PDF + PNG + EPS, local + Overleaf copy) ----
* FIX: replaces four near-identical section-specific redefinitions.
*   Single program taking the filename and the two folder paths.
* Usage: export_graph "fig_name" "$g11" "$ol_g11"
capture program drop export_graph
program define export_graph
    args filename local_dir overleaf_dir
    graph export "`local_dir'\\`filename'.pdf", replace
    graph export "`local_dir'\\`filename'.png", replace width(2400)
    graph export "`local_dir'\\`filename'.eps", replace
    cap copy "`local_dir'\\`filename'.pdf"  "`overleaf_dir'\\`filename'.pdf",  replace
    cap copy "`local_dir'\\`filename'.png"  "`overleaf_dir'\\`filename'.png",  replace
    cap copy "`local_dir'\\`filename'.eps"  "`overleaf_dir'\\`filename'.eps",  replace
end
