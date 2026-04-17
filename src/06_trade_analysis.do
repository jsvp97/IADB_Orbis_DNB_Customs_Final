/*==============================================================================
  06_trade_analysis.do

  PURPOSE:
    Main descriptive and econometric analysis of multinational enterprise (MNE)
    participation in LAC export trade. Covers all HS sectors.

    PART 1  Determinants of MNE presence
      1.1  Across exporting countries
      1.2  Across export destination countries
      1.3  By product (HS6 level)
      1.4  By parent country of origin
      1.5  Trends over time

    PART 2  Effects of MNE presence on trade patterns
      2.1  Aggregate regressions
      2.2  Gravity regressions (PPML and OLS)
      2.3  MNE network regressions (corporate linkage effects)
      2.4  Trade concentration patterns
      2.5  Extensive margin: country-product level
      2.6  Extensive margin: firm level

    PART 3  Summary statistics tables

  MNE DEFINITIONS (all results are produced for each):
    MNE_ext   — foreign subsidiary (parent country \!= exporting country)
    MNE_dom   — domestic MNE (matched in corporate DB, parent = same country)
    MNE_total — any firm matched in the corporate database

  INPUTS:
    $raw\Base_final_Customs_DNB_Orbis_product_complete.dta  (from script 02)
    Gravity and product characteristics files in $int

  OUTPUTS:
    Publication-quality graphs  → $graphs\...
    Regression tables           → $regs\...
    Summary tables              → $tables\...
    Overleaf-ready copies       → $overleaf\...  (optional)

  AUTHOR: Sebastian Velasquez (IDB)

  LAST UPDATED: March 2026
==============================================================================*/

**********************************************************************
*
* Multinational Firms and Trade — Descriptive Analysis
*
* Author:   Sebastian Velasquez (IDB)
*
* Last Version: March 2026
*
* TABLE OF CONTENTS
* -----------------
* Part 0 : Data preparation  [commented out -- run once to build .dta files]
*   0.1  Load raw data
*   0.2  Three MNE definitions (ext / dom / total)
*   0.3  Firm identifier
*   0.4  Product variables (HS6 / HS2 / HS Section)
*   0.5  Merge product characteristics
*   0.6  Merge gravity & country characteristics
*   0.7  Destination country categories
*   0.8  MNE corporate network variables
*   0.9  Collapse to analytical samples (ODPY / ODY / OPY / OY)
*   0.10 Concentration measures
*   0.11 Extensive margin variables
*   0.12 Firm-year level aggregates
*
* Part 1 : Determinants of multinational presence in trade patterns
*   1.1  Across exporting countries
*   1.2  Across export destination countries
*   1.3  By product
*
* Part 2 : Effects of multinational presence in trade patterns
*   2.1  Aggregate regressions
*   2.2  Gravity regressions
*   2.3  MNE network regressions
*   2.4  Concentration patterns
*   2.5  Extensive margin: country-product level
*   2.6  Extensive margin: firm level
*
* Part 3 : Summary statistics
*
* MNE DEFINITIONS (all loops run over all three):
*   MNE_ext   - foreign subsidiary  (parent country != exporter country)
*   MNE_dom   - domestic MNE        (parent country == exporter country)
*   MNE_total - any matched firm    (MNE_ext OR MNE_dom)
*
**********************************************************************

clear all
set more off
graph set window fontface "Times New Roman"


**********************************************************************
* DIRECTORIES & FOLDER STRUCTURE
**********************************************************************

global root     "C:\Sebas BID\Orbis_DNB_Customs_Final"
global raw      "$root\data\raw"
global int      "$root\data\intermediate"
global reg      "$int\regressions"

* Overleaf mirror (LaTeX project root)
global overleaf "$root\overleaf"   // Optional: set to your Overleaf sync folder

* Local output roots
global output   "$root\output"
global graphs   "$output\graphs"
global tables   "$output\tables"
global regs     "$output\regressions"

* Section sub-folders: graphs
global g11  "$graphs\1_1_ExportingCountries"
global g12  "$graphs\1_2_DestinationCountries"
global g13  "$graphs\1_3_ByProduct"
global g25  "$graphs\2_5_ExtensiveMargin"

* New sub-folder graph globals (v3)
global g11_tr "$graphs\1_1_Trends"
global g11_fp "$graphs\1_1_FirmProfile"
global g14    "$graphs\1_4_ParentCountries"
global g24    "$graphs\2_4_Concentration"

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

* New sub-folder Overleaf globals (v3)
global ol_g11_tr "$overleaf\Graphs\1_1_Trends"
global ol_g11_fp "$overleaf\Graphs\1_1_FirmProfile"
global ol_g14    "$overleaf\Graphs\1_4_ParentCountries"
global ol_g24    "$overleaf\Graphs\2_4_Concentration"
global ol_t_s1  "$overleaf\Tables\S1_Determinants"
global ol_t_s2  "$overleaf\Tables\S2_Effects"
global ol_t_s3  "$overleaf\Tables\S3_Summary"
global ol_r_s1  "$overleaf\Regressions\S1_Determinants"
global ol_r_s2  "$overleaf\Regressions\S2_Effects"

* Create all directories (capture suppresses error if folder already exists)
foreach dir in ///
    "$output" "$graphs" "$tables" "$regs" ///
    "$g11" "$g12" "$g13" "$g25" "$g11_tr" "$g11_fp" "$g14" "$g24" ///
    "$t_s1" "$t_s2" "$t_s3" ///
    "$r_s1" "$r_s2" ///
    "$overleaf" ///
    "$overleaf\Graphs" "$overleaf\Tables" "$overleaf\Regressions" ///
    "$ol_g11" "$ol_g12" "$ol_g13" "$ol_g25" "$ol_g11_tr" "$ol_g11_fp" "$ol_g14" "$ol_g24" ///
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
    copy "`local_dir'\\`filename'.pdf"  "`overleaf_dir'\\`filename'.pdf",  replace
    copy "`local_dir'\\`filename'.png"  "`overleaf_dir'\\`filename'.png",  replace
    copy "`local_dir'\\`filename'.eps"  "`overleaf_dir'\\`filename'.eps",  replace
end


**********************************************************************
**********************************************************************
*
*   PART 0: DATA PREPARATION
*   Uncomment this block on the FIRST run to build all .dta files.
*   After that it can stay commented to skip straight to Part 1.
*
**********************************************************************
**********************************************************************



*----------------------------------------------------------------------
* 0.1  Load raw data
*----------------------------------------------------------------------
use "$raw\Base_final_Customs_DNB_Orbis_product_complete.dta", clear

merge m:1 country_orig company_name firm_name using "$raw\Unknown_countries_Base_final_Customs_DNB_Orbis_with_parent_country.dta", keep(1 3) nogen


*----------------------------------------------------------------------
* 0.2  Three MNE definitions
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


*----------------------------------------------------------------------
* 0.3  Firm identifier
*----------------------------------------------------------------------
egen firm_id = group(country_orig Tax_ID)
label var firm_id "Unique firm identifier (country_orig x Tax_ID)"


*----------------------------------------------------------------------
* 0.4  Product variables (HS6, HS2, HS Section)
*----------------------------------------------------------------------
gen hs6 = hs07_6d
label var hs6 "HS 2007, 6-digit"
gen hs2 = substr(hs6, 1, 2)
label var hs2 "HS 2-digit chapter"
destring hs6 hs2, replace

gen byte hs_section = .
replace hs_section = 1  if inrange(hs2, 1,  5)
replace hs_section = 2  if inrange(hs2, 6,  14)
replace hs_section = 3  if hs2 == 15
replace hs_section = 4  if inrange(hs2, 16, 24)
replace hs_section = 5  if inrange(hs2, 25, 27)
replace hs_section = 6  if inrange(hs2, 28, 38)
replace hs_section = 7  if inrange(hs2, 39, 40)
replace hs_section = 8  if inrange(hs2, 41, 43)
replace hs_section = 9  if inrange(hs2, 44, 46)
replace hs_section = 10 if inrange(hs2, 47, 49)
replace hs_section = 11 if inrange(hs2, 50, 63)
replace hs_section = 12 if inrange(hs2, 64, 67)
replace hs_section = 13 if inrange(hs2, 68, 70)
replace hs_section = 14 if hs2 == 71
replace hs_section = 15 if inrange(hs2, 72, 83)
replace hs_section = 16 if inrange(hs2, 84, 85)
replace hs_section = 17 if inrange(hs2, 86, 89)
replace hs_section = 18 if inrange(hs2, 90, 92)
replace hs_section = 19 if hs2 == 93
replace hs_section = 20 if inrange(hs2, 94, 96)
replace hs_section = 21 if hs2 == 97
label var hs_section "HS Section (I-XXI)"
label define hs_sect_lbl ///
     1 "I: Live Animals"     2 "II: Vegetable"       3 "III: Fats/Oils" ///
     4 "IV: Food/Bev."       5 "V: Minerals"         6 "VI: Chemicals" ///
     7 "VII: Plastics"       8 "VIII: Leather"        9 "IX: Wood" ///
    10 "X: Pulp/Paper"      11 "XI: Textiles"        12 "XII: Footwear" ///
    13 "XIII: Stone/Glass"  14 "XIV: Prec. Metals"   15 "XV: Base Metals" ///
    16 "XVI: Machinery"     17 "XVII: Transport"     18 "XVIII: Instruments" ///
    19 "XIX: Arms"          20 "XX: Misc. Manuf."    21 "XXI: Art/Antiques"
label values hs_section hs_sect_lbl


*----------------------------------------------------------------------
* 0.5  Merge product characteristics
*----------------------------------------------------------------------

* HS code harmonisation (map obsolete codes to current HS 2007 codes)
replace hs07_6d = "250100" if hs07_6d == "002500"
replace hs07_6d = "250100" if hs07_6d == "002501"
replace hs07_6d = "250100" if hs07_6d == "002599"
replace hs07_6d = "030110" if hs07_6d == "030111"
replace hs07_6d = "030110" if hs07_6d == "030119"
replace hs07_6d = "030211" if hs07_6d == "030213"
replace hs07_6d = "030211" if hs07_6d == "030214"
replace hs07_6d = "030311" if hs07_6d == "030312"
replace hs07_6d = "030311" if hs07_6d == "030313"
replace hs07_6d = "030311" if hs07_6d == "030314"
replace hs07_6d = "030380" if hs07_6d == "030381"
replace hs07_6d = "030380" if hs07_6d == "030382"
replace hs07_6d = "030380" if hs07_6d == "030383"
replace hs07_6d = "030380" if hs07_6d == "030384"
replace hs07_6d = "030380" if hs07_6d == "030389"
replace hs07_6d = "030411" if hs07_6d == "030410"
replace hs07_6d = "030411" if hs07_6d == "030441"
replace hs07_6d = "030411" if hs07_6d == "030442"
replace hs07_6d = "030411" if hs07_6d == "030443"
replace hs07_6d = "030411" if hs07_6d == "030444"
replace hs07_6d = "030411" if hs07_6d == "030445"
replace hs07_6d = "030411" if hs07_6d == "030446"
replace hs07_6d = "030411" if hs07_6d == "030449"
replace hs07_6d = "030411" if hs07_6d == "030451"
replace hs07_6d = "030411" if hs07_6d == "030452"
replace hs07_6d = "030411" if hs07_6d == "030453"
replace hs07_6d = "030411" if hs07_6d == "030454"
replace hs07_6d = "030411" if hs07_6d == "030456"
replace hs07_6d = "030411" if hs07_6d == "030459"
replace hs07_6d = "030411" if hs07_6d == "030461"
replace hs07_6d = "030411" if hs07_6d == "030462"
replace hs07_6d = "030411" if hs07_6d == "030469"
replace hs07_6d = "030411" if hs07_6d == "030471"
replace hs07_6d = "030411" if hs07_6d == "030474"
replace hs07_6d = "030411" if hs07_6d == "030475"
replace hs07_6d = "030411" if hs07_6d == "030479"
replace hs07_6d = "030411" if hs07_6d == "030481"
replace hs07_6d = "030411" if hs07_6d == "030482"
replace hs07_6d = "030411" if hs07_6d == "030483"
replace hs07_6d = "030411" if hs07_6d == "030484"
replace hs07_6d = "030411" if hs07_6d == "030485"
replace hs07_6d = "030411" if hs07_6d == "030487"
replace hs07_6d = "030411" if hs07_6d == "030488"
replace hs07_6d = "030411" if hs07_6d == "030489"
replace hs07_6d = "030411" if hs07_6d == "030490"
replace hs07_6d = "030411" if hs07_6d == "030493"
replace hs07_6d = "030411" if hs07_6d == "030495"
replace hs07_6d = "030411" if hs07_6d == "030496"
replace hs07_6d = "030411" if hs07_6d == "030497"
replace hs07_6d = "030611" if hs07_6d == "030615"
replace hs07_6d = "030611" if hs07_6d == "030616"
replace hs07_6d = "030611" if hs07_6d == "030617"
replace hs07_6d = "060410" if hs07_6d == "060420"
replace hs07_6d = "060410" if hs07_6d == "060490"
replace hs07_6d = "080300" if hs07_6d == "080310"
replace hs07_6d = "080300" if hs07_6d == "080390"
replace hs07_6d = "080910" if hs07_6d == "080921"
replace hs07_6d = "080910" if hs07_6d == "080929"
replace hs07_6d = "382410" if hs07_6d == "382484"
replace hs07_6d = "382410" if hs07_6d == "382485"
replace hs07_6d = "382410" if hs07_6d == "382488"
replace hs07_6d = "382410" if hs07_6d == "382491"
replace hs07_6d = "382410" if hs07_6d == "382499"
replace hs07_6d = "650510" if hs07_6d == "650500"
replace hs07_6d = "761511" if hs07_6d == "761510"
replace hs07_6d = "852340" if hs07_6d == "852341"
replace hs07_6d = "852340" if hs07_6d == "852349"

* Merge product characteristics: upstreamness, sigma, complexity, quality
merge m:1 hs07_6d using ///
    "$reg\product_characteristics_hs6_2002_adj.dta", ///
    keep(1 3) nogen
label var upstreamness  "Upstreamness (Antras-Chor)"
label var sigma         "Elasticity of Substitution (Broda-Weinstein)"
rename pci    complexity
rename ladder quality_ladder
label var complexity     "Product Complexity Index (Hausman-Hidalgo)"
label var quality_ladder "Quality Ladder (Khandelwal)"

* Revealed Comparative Advantage (WITS)
merge m:1 country_orig hs07_6d year using "$raw\RCA_WITS_orig_year.dta", keep(1 3) nogen
label var rca "Revealed Comparative Advantage"

* Technology intensity: Lall (2000)
merge m:1 hs07_6d using "$raw\lall2000_hs2007.dta", keep(1 3) nogen
rename lall2000_category lall2000
label var lall2000 "Technology Intensity (Lall 2000)"
encode lall2000, gen(tech_lall2000)

* Technology intensity: Lybbert & Zolas (IPC patent concordance)
merge m:1 hs07_6d using "$raw\ALP_IPC_Patent_hs2007_6_to_ipc1.dta", keep(1 3) nogen
label var ipc1 "Technology Intensity (Lybbert-Zolas)"
encode ipc1, gen(tech_ipc1)

* Revealed Human Capital Intensity (UNCTAD)
merge m:1 hs07_6d using "$raw\UNCTAD RHCI hs_2007_indices.dta", keep(1 3) nogen
label var rhci "Revealed Human Capital Intensity (UNCTAD)"

* Above-median dummies and deciles for continuous product characteristics
foreach v in upstreamness sigma complexity quality_ladder rca rhci {
    cap {
        qui sum `v', d
        gen byte `v'_abovemed = (`v' > r(p50)) if `v' != .
        label var `v'_abovemed "`v' above median"
        xtile `v'_decile = `v', nq(10)
        label var `v'_decile "`v' decile (1-10)"
    }
}

* Lall 2000 high-tech binary (1 = medium/high tech; 0 = low/primary)
gen byte lall2000_abovemed = .
replace lall2000_abovemed = 1 if inlist(lall2000, ///
    "High technology manufactures: electronic and electrical", ///
    "High technology manufactures: other", ///
    "Medium technology manufactures: automotive", ///
    "Medium technology manufactures: process", ///
    "Medium technology manufactures: engineering")
replace lall2000_abovemed = 0 if inlist(lall2000, ///
    "Primary products", "Resource-based manufactures: agro-based", ///
    "Resource-based manufactures: other", ///
    "Low technology manufactures: textile, garment and footwear", ///
    "Low technology manufactures: other products", "Unclassified products")
label var lall2000_abovemed "Lall 2000: 1=Med/High tech, 0=Low/Primary"

* Lybbert-Zolas high-tech binary
* FIX: was `gen`, changed to `gen byte` for type consistency
gen byte ipc1_abovemed = .
replace ipc1_abovemed = 1 if inlist(ipc1, "C:Chemistry; Metallurgy", "G:Physics", "H:Electricity")
replace ipc1_abovemed = 0 if inlist(ipc1, ///
    "A:Human Necessities", "B:Performing Operations; Transporting", ///
    "D:Textiles; Paper", "E:Fixed Constructions", ///
    "F:Mechanical Engineering; Lighting; Heating; Weapons")
label var ipc1_abovemed "Lybbert-Zolas: 1=High tech, 0=Low tech"


*----------------------------------------------------------------------
* 0.6  Gravity & country characteristics
*----------------------------------------------------------------------

* CEPII Gravity (bilateral time-invariant)
preserve
    use "$raw\Gravity_V202211.dta", clear
    rename iso3_o country_orig
    rename iso3_d country_dest
    tempfile gravity
    save `gravity'
restore
merge m:1 country_orig country_dest year using `gravity', keep(1 3) nogen

gen ln_dist = ln(dist)
label var ln_dist "Ln bilateral distance (CEPII)"
foreach stub in o d {
    cap gen ln_gdp_`stub'    = ln(gdp_`stub')
    cap gen ln_gdpcap_`stub' = ln(gdpcap_`stub')
    cap gen ln_pop_`stub'    = ln(pop_`stub')
}

* Time-varying bilateral variables (Feodora Teti tariff database)
preserve
    use "$raw\tariffsPairs_88_21_vbeta1-2024-12.dta", clear
    rename iso1 country_orig
    rename iso2 country_dest
    tempfile bilateral_tv
    save `bilateral_tv'
restore
merge m:1 country_orig country_dest year using `bilateral_tv', keep(1 3) nogen

* PTA, BIT, DTT (IDB bilateral agreements database)
merge m:1 country_orig country_dest year using "$raw\PTA_BIT_DTT_BID.dta", keep(1 3) nogen

rename tariff       avg_tariff
rename col_dep_ever colony
label var avg_tariff "Average applied bilateral tariff"
label var PTA        "Preferential Trade Agreement"
label var BIT        "Bilateral Investment Treaty"
label var DTT        "Double Taxation Treaty"
label var colony     "Colonial tie (ever)"


*----------------------------------------------------------------------
* 0.7  Destination country categories
*----------------------------------------------------------------------

* World Bank income groups - origin
preserve
    use "$raw\WB_Income_group.dta", clear
    rename (iso3 income_group) (country_orig income_group_orig)
    tempfile wdi_o
    save `wdi_o'
restore
merge m:1 country_orig using `wdi_o', keep(1 3) nogen

* World Bank income groups - destination
preserve
    use "$raw\WB_Income_group.dta", clear
    rename (iso3 income_group) (country_dest income_group_dest)
    tempfile wdi_d
    save `wdi_d'
restore
merge m:1 country_dest using `wdi_d', keep(1 3) nogen

* Recode income groups to numeric (1=Low, 2=Lower-middle, 3=Upper-middle, 4=High)
foreach c in orig dest {
    replace income_group_`c' = "4" if income_group_`c' == "High income"
    replace income_group_`c' = "3" if income_group_`c' == "Upper middle income"
    replace income_group_`c' = "2" if income_group_`c' == "Lower middle income"
    replace income_group_`c' = "1" if income_group_`c' == "Low income"
    cap destring income_group_`c', replace
}
label define income_group ///
    1 "Low income" 2 "Lower middle income" ///
    3 "Upper middle income" 4 "High income"
label values income_group_dest income_group
label values income_group_orig income_group

* LAC destination indicator (covers all 26 LAC countries)
gen byte LAC_dest = 0
replace  LAC_dest = 1 if inlist(country_dest, "ARG","BHS","BRB","BLZ","BOL")
replace  LAC_dest = 1 if inlist(country_dest, "BRA","CHL","COL","CRI","DOM")
replace  LAC_dest = 1 if inlist(country_dest, "ECU","SLV","GTM","GUY","HTI")
replace  LAC_dest = 1 if inlist(country_dest, "HND","JAM","MEX","NIC","PAN")
replace  LAC_dest = 1 if inlist(country_dest, "PRY","PER","SUR","TTO","URY","VEN")
gen byte intra_regional = LAC_dest
gen byte extra_regional = 1 - LAC_dest
label var intra_regional "=1 if destination is LAC"

gen byte non_contig = (contig == 0) if contig != .

* Distance above/below sample median
qui sum dist, d
gen byte dist_above_med = (dist > r(p50)) if dist != .

* Broad destination region
gen dest_region = ""
replace dest_region = "Latin America" if LAC_dest == 1

replace dest_region = "North America" if inlist(country_dest,"USA","CAN")

replace dest_region = "Europe" if inlist(country_dest,"AUT","BEL","BGR","CYP","CZE")
replace dest_region = "Europe" if inlist(country_dest,"DNK","EST","FIN","FRA","DEU")
replace dest_region = "Europe" if inlist(country_dest,"GRC","HUN","IRL","ITA","LVA")
replace dest_region = "Europe" if inlist(country_dest,"LTU","LUX","MLT","NLD","POL")
replace dest_region = "Europe" if inlist(country_dest,"PRT","ROU","SVK","SVN","ESP")
replace dest_region = "Europe" if inlist(country_dest,"SWE","GBR")

replace dest_region = "Asia" if inlist(country_dest,"CHN","HKG","IND","IDN","JPN")
replace dest_region = "Asia" if inlist(country_dest,"MYS","PHL","KOR","SGP","TWN")
replace dest_region = "Asia" if inlist(country_dest,"THA")

replace dest_region = "Africa" if inlist(country_dest,"DZA","AGO","BEN","BWA","BFA")
replace dest_region = "Africa" if inlist(country_dest,"BDI","CMR","CPV","CAF","TCD")
replace dest_region = "Africa" if inlist(country_dest,"COM","COD","COG","CIV","DJI")
replace dest_region = "Africa" if inlist(country_dest,"EGY","GNQ","ERI","ETH","GAB")
replace dest_region = "Africa" if inlist(country_dest,"GMB","GHA","GIN","GNB","KEN")
replace dest_region = "Africa" if inlist(country_dest,"LSO","LBR","LBY","MDG","MWI")
replace dest_region = "Africa" if inlist(country_dest,"MLI","MRT","MUS","MAR","MOZ")
replace dest_region = "Africa" if inlist(country_dest,"NAM","NER","NGA","RWA","STP")
replace dest_region = "Africa" if inlist(country_dest,"SEN","SYC","SLE","SOM","ZAF")
replace dest_region = "Africa" if inlist(country_dest,"SSD","SDN","SWZ","TZA","TGO")
replace dest_region = "Africa" if inlist(country_dest,"TUN","UGA","ZMB","ZWE")

replace dest_region = "Rest of World" if dest_region == ""
encode dest_region, gen(dest_region_num)


* Value labels for graph axes
label define intra_lbl   0 "Extra-regional"   1 "Intra-regional (LAC)", replace
label define contig_lbl  0 "Non-Contiguous"   1 "Contiguous", replace
label define distmed_lbl 0 "Below Median"     1 "Above Median", replace
label values intra_regional intra_lbl
label values contig         contig_lbl
label values dist_above_med distmed_lbl


*----------------------------------------------------------------------
* 0.8  MNE corporate network variables
*----------------------------------------------------------------------

gen country_hq   = iso3_parent
gen home_country = iso3_parent if MNE == 1
label var home_country "Home country of MNE parent"

* Merge affiliate presence at destination (built externally from ORBIS)
merge m:1 ID_Orbis_DNB country_dest using "$int\intermediate_mne_presence.dta", ///
    keep(1 3) nogen

gen byte MNE_HQ_dest         = (MNE == 1 & country_hq == country_dest)
gen byte MNE_aff_dest        = (MNE == 1 & company_has_aff_in_dest == 1)
gen byte MNE_present_dest    = (MNE_HQ_dest == 1 | MNE_aff_dest == 1)
gen byte MNE_notpresent_dest = (MNE == 1 & MNE_present_dest == 0)
gen byte MNE_neighbor_dest   = (MNE == 1 & MNE_present_dest == 0 ///
                               & company_has_aff_in_neighbor == 1)

label var MNE_HQ_dest         "MNE: HQ is in the destination country"
label var MNE_aff_dest        "MNE: affiliate in the destination country"
label var MNE_present_dest    "MNE: any network presence in destination"
label var MNE_notpresent_dest "MNE: no network presence in destination"
label var MNE_neighbor_dest   "MNE: affiliate in contiguous country only"
drop company_has_aff_in_dest company_has_aff_in_neighbor

compress
save "$int\firm_level_data.dta", replace


*----------------------------------------------------------------------
* 0.9  Collapse to analytical samples
*----------------------------------------------------------------------

* ----- (A) ODPY: Origin-Destination-Product-Year -----
use "$int\firm_level_data.dta", clear
gen double mne_value = value_fob * MNE_ext
gen double dom_value = value_fob * DOM_ext

gcollapse ///
    (sum)     total_value=value_fob mne_value dom_value ///
    (count)   n_firms=firm_id ///
    (sum)     n_mne=MNE_ext n_dom=DOM_ext n_mne_dom=MNE_dom n_mne_total=MNE_total ///
    (firstnm) ln_dist dist contig comlang_off colony fta_wto PTA BIT DTT ///
              avg_tariff ln_gdp_o ln_gdpcap_o ln_pop_o ///
              ln_gdp_d ln_gdpcap_d ln_pop_d ///
              income_group_dest intra_regional dest_region_num ///
              dist_above_med LAC_dest non_contig ///
              upstreamness sigma complexity quality_ladder rca ///
              tech_lall2000 tech_ipc1 rhci ///
              upstreamness_abovemed sigma_abovemed complexity_abovemed ///
              quality_ladder_abovemed rca_abovemed lall2000_abovemed ///
              ipc1_abovemed rhci_abovemed ///
              upstreamness_decile sigma_decile complexity_decile ///
              quality_ladder_decile rca_decile hs2 hs_section ///
    , by(country_orig country_dest hs6 year) labelformat(#sourcelabel#)

gen share_mne_value    = mne_value / total_value
gen share_mne_nfirms   = n_mne / n_firms
gen ln_total_value     = ln(total_value)
gen share_ext_value    = mne_value / total_value
gen share_ext_nfirms   = n_mne / n_firms
gen share_dom_nfirms   = n_mne_dom / n_firms
gen share_total_nfirms = n_mne_total / n_firms
* NOTE: positive_trade = 1 for all obs in the non-squared collapsed data.
* The LaTeX plan calls for this in a squared dataset; mark as placeholder.
gen byte positive_trade = 1

label var share_mne_value    "Share MNE (ext) in exports (value)"
label var share_mne_nfirms   "Share MNE (ext) in # exporters"
label var share_ext_value    "Share MNE_ext in exports (value)"
label var share_ext_nfirms   "Share MNE_ext in # exporters"
label var share_dom_nfirms   "Share MNE_dom in # exporters"
label var share_total_nfirms "Share MNE_total in # exporters"

* Fixed-effect group identifiers
egen orig_id = group(country_orig)
egen dest_id = group(country_dest)
egen prod_id = group(hs6)
egen od_id   = group(country_orig country_dest)
egen op_id   = group(country_orig hs6)
egen ot_id   = group(country_orig year)
egen dt_id   = group(country_dest year)
egen pt_id   = group(hs6 year)
egen odt_id  = group(country_orig country_dest year)
egen odp_id  = group(country_orig country_dest hs6)

compress
save "$int\collapsed_odpy.dta", replace


* ----- (B) ODY: Origin-Destination-Year -----
use "$int\firm_level_data.dta", clear
gen double mne_value = value_fob * MNE_ext

gcollapse ///
    (sum)     total_value=value_fob mne_value ///
    (count)   n_firms=firm_id ///
    (sum)     n_mne=MNE_ext n_dom=DOM_ext n_mne_dom=MNE_dom n_mne_total=MNE_total ///
    (firstnm) ln_dist dist contig comlang_off colony fta_wto PTA BIT DTT ///
              avg_tariff ln_gdp_o ln_gdpcap_o ln_pop_o ///
              ln_gdp_d ln_gdpcap_d ln_pop_d ///
              income_group_dest intra_regional dest_region_num ///
              dist_above_med LAC_dest non_contig ///
    , by(country_orig country_dest year) labelformat(#sourcelabel#)

gen share_mne_value    = mne_value / total_value
gen share_mne_nfirms   = n_mne / n_firms
gen ln_total_value     = ln(total_value)
gen share_ext_value    = mne_value / total_value
gen share_ext_nfirms   = n_mne / n_firms
gen share_dom_nfirms   = n_mne_dom / n_firms
gen share_total_nfirms = n_mne_total / n_firms
gen byte positive_trade = 1  // see note in ODPY block above
label values income_group_dest income_group

egen orig_id = group(country_orig)
egen dest_id = group(country_dest)
egen od_id   = group(country_orig country_dest)
egen ot_id   = group(country_orig year)
egen dt_id   = group(country_dest year)

compress
save "$int\collapsed_ody.dta", replace


* ----- (C) OPY: Origin-Product-Year -----
use "$int\firm_level_data.dta", clear
gen double mne_value = value_fob * MNE_ext

gcollapse ///
    (sum)     total_value=value_fob mne_value ///
    (count)   n_firms=firm_id ///
    (sum)     n_mne=MNE_ext n_mne_dom=MNE_dom n_mne_total=MNE_total ///
    (firstnm) upstreamness sigma complexity quality_ladder rca ///
              tech_lall2000 tech_ipc1 rhci ///
              upstreamness_abovemed sigma_abovemed complexity_abovemed ///
              quality_ladder_abovemed rca_abovemed lall2000_abovemed ///
              ipc1_abovemed rhci_abovemed ///
              upstreamness_decile sigma_decile complexity_decile ///
              quality_ladder_decile rca_decile ///
              hs2 hs_section ln_gdp_o ln_gdpcap_o ln_pop_o ///
    , by(country_orig hs6 year) labelformat(#sourcelabel#)

gen share_mne_value    = mne_value / total_value
gen share_mne_nfirms   = n_mne / n_firms
gen share_ext_value    = mne_value / total_value
gen share_ext_nfirms   = n_mne / n_firms
gen share_dom_nfirms   = n_mne_dom / n_firms
gen share_total_nfirms = n_mne_total / n_firms

egen orig_id = group(country_orig)
egen prod_id = group(hs6)
egen op_id   = group(country_orig hs6)
egen ot_id   = group(country_orig year)
egen pt_id   = group(hs6 year)

compress
save "$int\collapsed_opy.dta", replace


* ----- (D) OY: Origin-Year -----
use "$int\firm_level_data.dta", clear
gen double mne_value = value_fob * MNE_ext

gcollapse ///
    (sum)     total_value=value_fob mne_value ///
    (count)   n_firms=firm_id ///
    (sum)     n_mne=MNE_ext n_mne_dom=MNE_dom n_mne_total=MNE_total ///
    (firstnm) ln_gdp_o ln_gdpcap_o ln_pop_o ///
    , by(country_orig year) labelformat(#sourcelabel#)

gen share_mne_value    = mne_value / total_value
gen share_mne_nfirms   = n_mne / n_firms
gen share_ext_nfirms   = n_mne / n_firms
gen share_dom_nfirms   = n_mne_dom / n_firms
gen share_total_nfirms = n_mne_total / n_firms

compress
save "$int\collapsed_oy.dta", replace


*----------------------------------------------------------------------
* 0.10  Concentration measures (top-k exporter shares)
*----------------------------------------------------------------------

* --- ODY level ---
use "$int\firm_level_data.dta", clear

bysort country_orig country_dest year: egen double tot_ody = total(value_fob)
gen firm_sh_ody = value_fob / tot_ody
gsort country_orig country_dest year -value_fob
bysort country_orig country_dest year: gen rank_ody = _n

* All-firm concentration
bysort country_orig country_dest year: ///
    egen share_top1_all = total(firm_sh_ody * (rank_ody == 1))
bysort country_orig country_dest year: ///
    egen share_top3_all = total(firm_sh_ody * (rank_ody <= 3))
bysort country_orig country_dest year: ///
    egen share_top5_all = total(firm_sh_ody * (rank_ody <= 5))
bysort country_orig country_dest year: gen n_exp_all = _N

* Domestic-firm concentration
bysort country_orig country_dest year: ///
    egen double tot_dom_ody = total(value_fob * DOM_ext)
gen firm_sh_dom_ody = (value_fob * DOM_ext) / tot_dom_ody if DOM_ext == 1
gsort country_orig country_dest year DOM_ext -value_fob
bysort country_orig country_dest year DOM_ext: gen rank_dom = _n if DOM_ext == 1
bysort country_orig country_dest year: ///
    egen share_top1_dom = total(firm_sh_dom_ody * (rank_dom == 1))
bysort country_orig country_dest year: ///
    egen share_top3_dom = total(firm_sh_dom_ody * (rank_dom <= 3))
bysort country_orig country_dest year: ///
    egen share_top5_dom = total(firm_sh_dom_ody * (rank_dom <= 5))
bysort country_orig country_dest year: ///
    egen n_exp_dom = total(DOM_ext)
gen ln_n_exp_all = ln(n_exp_all)
gen ln_n_exp_dom = ln(n_exp_dom) if n_exp_dom > 0

preserve
    gcollapse (firstnm) share_top1_all share_top3_all share_top5_all ///
              ln_n_exp_all share_top1_dom share_top3_dom share_top5_dom ///
              ln_n_exp_dom, by(country_orig country_dest year) labelformat(#sourcelabel#)
    tempfile conc_ody
    save `conc_ody'
restore
use "$int\collapsed_ody.dta", clear
merge 1:1 country_orig country_dest year using `conc_ody', nogen
save "$int\collapsed_ody.dta", replace


* --- ODPY level ---
use "$int\firm_level_data.dta", clear

bysort country_orig country_dest hs6 year: ///
    egen double tot_odpy = total(value_fob)
gen firm_sh_odpy = value_fob / tot_odpy
gsort country_orig country_dest hs6 year -value_fob
bysort country_orig country_dest hs6 year: gen rank_odpy = _n

bysort country_orig country_dest hs6 year: ///
    egen share_top1_all_p = total(firm_sh_odpy * (rank_odpy == 1))
bysort country_orig country_dest hs6 year: ///
    egen share_top3_all_p = total(firm_sh_odpy * (rank_odpy <= 3))
bysort country_orig country_dest hs6 year: ///
    egen share_top5_all_p = total(firm_sh_odpy * (rank_odpy <= 5))
bysort country_orig country_dest hs6 year: gen n_exp_all_p = _N

bysort country_orig country_dest hs6 year: ///
    egen double tot_dom_odpy = total(value_fob * DOM_ext)
gen firm_sh_dom_odpy = (value_fob * DOM_ext) / tot_dom_odpy if DOM_ext == 1
gsort country_orig country_dest hs6 year DOM_ext -value_fob
bysort country_orig country_dest hs6 year DOM_ext: ///
    gen rank_dom_p = _n if DOM_ext == 1
bysort country_orig country_dest hs6 year: ///
    egen share_top1_dom_p = total(firm_sh_dom_odpy * (rank_dom_p == 1))
bysort country_orig country_dest hs6 year: ///
    egen share_top3_dom_p = total(firm_sh_dom_odpy * (rank_dom_p <= 3))
bysort country_orig country_dest hs6 year: ///
    egen share_top5_dom_p = total(firm_sh_dom_odpy * (rank_dom_p <= 5))
bysort country_orig country_dest hs6 year: ///
    egen n_exp_dom_p = total(DOM_ext)
gen ln_n_exp_all_p = ln(n_exp_all_p)
gen ln_n_exp_dom_p = ln(n_exp_dom_p) if n_exp_dom_p > 0

preserve
    gcollapse (firstnm) share_top1_all_p share_top3_all_p share_top5_all_p ///
              ln_n_exp_all_p share_top1_dom_p share_top3_dom_p ///
              share_top5_dom_p ln_n_exp_dom_p, ///
              by(country_orig country_dest hs6 year) labelformat(#sourcelabel#)
    tempfile conc_odpy
    save `conc_odpy'
restore
use "$int\collapsed_odpy.dta", clear
merge 1:1 country_orig country_dest hs6 year using `conc_odpy', nogen
save "$int\collapsed_odpy.dta", replace


*----------------------------------------------------------------------
* 0.11  Extensive margin variables (new products to the export basket)
*----------------------------------------------------------------------

use "$int\firm_level_data.dta", clear

* New product at the origin level:
* a product is "new" in the year it first appears in the origin's basket
preserve
    gcollapse (count) has_exp = value_fob, by(country_orig hs6 year) labelformat(#sourcelabel#)
    bysort country_orig hs6 (year): gen first_year_op = year[1]
    gen byte new_product_orig = (year == first_year_op)
    keep country_orig hs6 year new_product_orig
    tempfile new_o
    save `new_o'
restore
merge m:1 country_orig hs6 year using `new_o', keep(1 3) nogen

* Who introduces the new product? MNE only / both / domestic only
bysort country_orig hs6 year: ///
    egen has_mne_exp = max(MNE_ext) if new_product_orig == 1
bysort country_orig hs6 year: ///
    egen has_dom_exp = max(DOM_ext) if new_product_orig == 1
gen byte new_prod_only_mne = (has_mne_exp == 1 & has_dom_exp == 0) ///
    if new_product_orig == 1
gen byte new_prod_both     = (has_mne_exp == 1 & has_dom_exp == 1) ///
    if new_product_orig == 1
gen byte new_prod_only_dom = (has_mne_exp == 0 & has_dom_exp == 1) ///
    if new_product_orig == 1

* New product at the origin-destination level
bysort country_orig country_dest hs6 (year): gen first_year_odp = year[1]
gen byte new_product_od = (year == first_year_odp)
bysort country_orig country_dest hs6 year: ///
    egen has_mne_od = max(MNE_ext) if new_product_od == 1
bysort country_orig country_dest hs6 year: ///
    egen has_dom_od = max(DOM_ext) if new_product_od == 1
gen byte new_prod_only_mne_od = (has_mne_od == 1 & has_dom_od == 0) ///
    if new_product_od == 1
gen byte new_prod_both_od     = (has_mne_od == 1 & has_dom_od == 1) ///
    if new_product_od == 1

save "$int\firm_level_data_full.dta", replace


*----------------------------------------------------------------------
* 0.12  Firm-year level aggregates
*----------------------------------------------------------------------

use "$int\firm_level_data_full.dta", clear

* ---- (A) Firm-Year level ----
preserve
    bysort firm_id year: egen n_destinations = nvals(country_dest)
    bysort firm_id year: egen n_products     = nvals(hs6)

    gcollapse ///
        (sum)     firm_total_exports = value_fob ///
        (firstnm) n_destinations n_products ///
                  MNE_ext DOM_ext MNE_dom DOM_dom MNE_total DOM_total ///
                  hs_section ///
        , by(firm_id country_orig year) labelformat(#sourcelabel#)

    * Rename to the short aliases used in Part 2.6
    rename MNE_ext   MNE
    rename DOM_ext   DOM

    gen ln_firm_exports   = ln(firm_total_exports)
    gen ln_n_destinations = ln(n_destinations)
    gen ln_n_products     = ln(n_products)
    gen ln_exp_per_dest   = ln(firm_total_exports / n_destinations)
    gen ln_exp_per_prod   = ln(firm_total_exports / n_products)

    egen orig_id   = group(country_orig)
    egen ot_id     = group(country_orig year)
    egen sector_id = group(hs_section)

    compress
    save "$int\firm_year_level.dta", replace
restore

* ---- (B) Firm-Destination-Year level ----
preserve
    gcollapse ///
        (sum)     firm_dest_exports = value_fob ///
        (firstnm) MNE_ext DOM_ext MNE_dom DOM_dom MNE_total DOM_total ///
                  ln_dist dist contig comlang_off colony ///
                  fta_wto PTA BIT DTT avg_tariff ///
                  ln_gdp_o ln_gdpcap_o ln_pop_o ///
                  ln_gdp_d ln_gdpcap_d ln_pop_d ///
                  income_group_dest ///
                  MNE_HQ_dest MNE_aff_dest MNE_present_dest ///
                  MNE_notpresent_dest MNE_neighbor_dest ///
                  upstreamness sigma complexity ///
        , by(firm_id country_orig country_dest year) labelformat(#sourcelabel#)

    rename MNE_ext MNE
    rename DOM_ext DOM

    gen ln_exports      = ln(firm_dest_exports)
    gen byte positive_trade = 1

    egen orig_id = group(country_orig)
    egen dest_id = group(country_dest)
    egen od_id   = group(country_orig country_dest)
    egen ot_id   = group(country_orig year)
    egen dt_id   = group(country_dest year)

    compress
    save "$int\firm_dest_year_level.dta", replace

    * FIX: was `gen avg_dist = mean(dist)` — mean() is an egen function
    bysort firm_id year: egen avg_dist = mean(dist)
    gen ln_avg_dist = ln(avg_dist)
    gcollapse (firstnm) ln_avg_dist, by(firm_id year) labelformat(#sourcelabel#)
    tempfile avg_d
    save `avg_d'
restore

use "$int\firm_year_level.dta", clear
merge 1:1 firm_id year using `avg_d', nogen
save "$int\firm_year_level.dta", replace

*/
*  ^^^ End of Part 0 ^^^
**********************************************************************


**********************************************************************
**********************************************************************
*
*   PART 1: DETERMINANTS OF MULTINATIONAL PRESENCE IN TRADE
*
**********************************************************************
**********************************************************************


**********************************************************************
* 1.1  ACROSS EXPORTING COUNTRIES                         [Plan §1.1]
**********************************************************************
*
* FIGURE 1.1.1  Bar: MNE share in total exports and # exporters by country
* FIGURE 1.1.2  Scatter: MNE share in exports vs. GDP per capita (origin)
* FIGURE 1.1.3  Bar: share of top-10 home countries of MNE parents
*
* Produced for each MNE definition: ext / dom / total
**********************************************************************

use "$int\collapsed_oy.dta", clear

* Collapse to one obs per country (average over years)
preserve
    gcollapse (mean) share_mne_value share_mne_nfirms ///
                     share_ext_nfirms share_dom_nfirms share_total_nfirms ///
              , by(country_orig) labelformat(#sourcelabel#)

    gsort -share_mne_value
    gen rank = _n
    labmask rank, values(country_orig)
    local N = _N

    * Combined panel: all three definitions in one chart
    twoway ///
        (bar share_ext_nfirms   rank, barwidth(0.8) fcolor($c_MNE)    lcolor($c_MNE)) ///
        (bar share_dom_nfirms   rank, barwidth(0.5) fcolor($c_MNEdom) lcolor($c_MNEdom)) ///
        (bar share_total_nfirms rank, barwidth(0.2) fcolor($c_MNEtot) lcolor($c_MNEtot)), ///
        ytitle("Share in # Exporters") xtitle("") ///
        xla(1/`N', ang(45) valuelabel noticks labsize(*0.8)) ///
        ylab(0(0.1)1, nogrid format(%9.1f)) ///
        legend(order(1 "MNE_ext" 2 "MNE_dom" 3 "MNE_total") ///
               position(6) rows(1) region(lcolor(white)) symysize(small) size(small)) ///
        $gro
    export_graph "fig_1_1_1_all_defs_nfirms" "$g11" "$ol_g11"

    * One chart per MNE definition: export value share + exporter count share
    foreach mne_def in ext total {
        if "`mne_def'" == "ext" {
            local sv "share_mne_value"
            local sn "share_ext_nfirms"
            local ll "Foreign Subsidiary (ext)"
            local bc "$c_MNE"
        }
        else if "`mne_def'" == "dom" {
            local sv "share_mne_value"
            local sn "share_dom_nfirms"
            local ll "Domestic MNE (dom)"
            local bc "$c_MNEdom"
        }
        else {
            local sv "share_mne_value"
            local sn "share_total_nfirms"
            local ll "All MNEs (total)"
            local bc "$c_MNEtot"
        }
        cap {
            twoway ///
                (bar `sv' rank, barwidth(0.6) fcolor(`bc') lcolor(`bc')) ///
                (bar `sn' rank, barwidth(0.3) fcolor(`bc') lcolor(`bc') fintensity(60)), ///
                ytitle("Share") xtitle("") ///
                xla(1/`N', ang(45) valuelabel noticks labsize(*0.8)) ///
                ylab(0(0.1)1, nogrid format(%9.1f)) ///
                title("`ll'", size(medium)) ///
                legend(on order(1 "Export Value" 2 "# Exporters") ///
                       position(6) rows(1) region(lcolor(white)) symysize(small) size(small)) ///
                $gro
            export_graph "fig_1_1_1_`mne_def'_by_country" "$g11" "$ol_g11"
        }
    }
restore


*---------------------------------------------------------------
* FIGURE 1.1.2 – MNE share vs. GDP per capita (scatter)
*---------------------------------------------------------------
foreach mne_def in ext total {
    if "`mne_def'" == "ext"   local sv "share_mne_value"
    if "`mne_def'" == "dom"   local sv "share_dom_nfirms"
    if "`mne_def'" == "total" local sv "share_total_nfirms"

    preserve
        gcollapse (mean) `sv' ln_gdpcap_o, by(country_orig) labelformat(#sourcelabel#)
        cap {
            twoway ///
                (lfitci `sv' ln_gdpcap_o, clcolor(black)) ///
                (scatter `sv' ln_gdpcap_o, ///
                     mlabel(country_orig) mlabsize(6pt) mlabposition(3) ///
                     msize(4pt) mcolor($c_MNE) mlabcolor($c_MNE) ms(o)), ///
                ytitle("Share MNE_`mne_def' in Exports", margin(medsmall) size(*.9)) ///
                xtitle("Log GDP per capita (origin)", margin(medsmall) size(*.9)) ///
                ylab(, nogrid) legend(off region(lcolor(white))) $gro
            export_graph "fig_1_1_2_`mne_def'_vs_GDPpc" "$g11" "$ol_g11"
        }
    restore
}


*---------------------------------------------------------------
* FIGURE 1.1.3 – Top-10 home countries of MNE parents
*---------------------------------------------------------------
use "$int\firm_level_data.dta", clear

preserve
    keep if MNE_ext == 1
    gcollapse (sum) mne_exports = value_fob, by(home_country) labelformat(#sourcelabel#)
    egen double total_mne = total(mne_exports)
    gen share_home = mne_exports / total_mne

    gsort -share_home
    gen rank = _n
    gen country_label = home_country if rank <= 10
    replace country_label = "Rest" if rank > 10
    gcollapse (sum) share_home, by(country_label) labelformat(#sourcelabel#)
    gsort -share_home
    gen order = _n
    replace order = 11 if country_label == "Rest"
    sort order
    replace order = _n
    labmask order, values(country_label)

    graph hbar (asis) share_home, ///
        over(order, sort(order) descending label(labsize(small))) ///
        bar(1, color($c_MNE)) ///
        ytitle("Share in Total MNE Exports") ///
        ylab(, nogrid format(%9.2f)) ///
        bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
    export_graph "fig_1_1_3_top10_home_countries" "$g11" "$ol_g11"
restore

**********************************************************************
* 1.1.EXTRA  TIME TRENDS & FIRM PROFILE (Blocks A & B)
**********************************************************************

*---------------------------------------------------------------
* BLOCK A — MNE share trends over time (by country)
*   fig_1_1_tr_mnevalue_[def]  : share in exports value
*   fig_1_1_tr_mnefirms_[def]  : share in # exporters
*   Dataset: collapsed_oy.dta
*---------------------------------------------------------------

use "$int\collapsed_oy.dta", clear

foreach mne_def in ext total {
    if "`mne_def'" == "ext" {
        local sv "share_mne_value"
        local sn "share_ext_nfirms"
        local ll "Foreign Subsidiary (ext)"
    }
    else {
        local sv "share_total_nfirms"
        local sn "share_total_nfirms"
        local ll "All MNEs (total)"
    }

    * Value share trend
    cap {
        levelsof country_orig, local(countries_tr)
        local cmd_v ""
        local cmd_n ""
        foreach c of local countries_tr {
            local cmd_v "`cmd_v' (connected `sv' year if country_orig == "`c'", lpattern(solid) lwidth(medthin))"
            local cmd_n "`cmd_n' (connected `sn' year if country_orig == "`c'", lpattern(solid) lwidth(medthin))"
        }

        twoway `cmd_v', ///
            ytitle("MNE Share in Export Value", size(*.9)) xtitle("Year") ///
            ylab(0(0.1)1, nogrid format(%9.1f)) ///
            xlab(, nogrid angle(45)) ///
            legend(on rows(2) size(vsmall) region(lcolor(white)) ///
                   label(1 "`c'") symysize(small)) ///
            title("MNE_`mne_def': Export Value Share over Time", size(medium)) $gro
        export_graph "fig_1_1_tr_mnevalue_`mne_def'" "$g11_tr" "$ol_g11_tr"

        twoway `cmd_n', ///
            ytitle("MNE Share in # Exporters", size(*.9)) xtitle("Year") ///
            ylab(0(0.1)1, nogrid format(%9.1f)) ///
            xlab(, nogrid angle(45)) ///
            legend(on rows(2) size(vsmall) region(lcolor(white)) symysize(small)) ///
            title("MNE_`mne_def': Exporter Count Share over Time", size(medium)) $gro
        export_graph "fig_1_1_tr_mnefirms_`mne_def'" "$g11_tr" "$ol_g11_tr"
    }
}


*---------------------------------------------------------------
* BLOCK B — MNE vs. domestic firm profile
*   tab_3_4_firm_profile_comparison.tex  : mean table by country
*   fig_1_1_fp_boxplot_[def]             : box plots (combined, 10 countries)
*   Dataset: firm_year_level.dta
*---------------------------------------------------------------

use "$int\firm_year_level.dta", clear

* NOTE: ln_avg_dist merged in Part 0 (§0.12); if missing, we compute
*   a proxy from firm_dest_year_level here.
cap confirm variable ln_avg_dist
if _rc != 0 {
    di as text "ln_avg_dist not found in firm_year_level — adding placeholder"
    gen ln_avg_dist = .
}

* ---- Table B1: mean comparison MNE vs domestic, by country ----
    label var ln_firm_exports   "Ln Total Exports"
    label var n_destinations    "# Destinations"
    label var n_products        "# Products"
    label var ln_avg_dist       "Ln Avg Distance"

    local first_tab = 1
    levelsof country_orig, local(ctry_list)

    foreach c of local ctry_list {
        preserve
            keep if country_orig == "`c'"
            * MNE stats
            eststo mne_`c': quietly estpost tabstat ///
                ln_firm_exports n_destinations n_products ln_avg_dist ///
                if MNE == 1, statistics(mean sd) columns(statistics)
            * DOM stats
            eststo dom_`c': quietly estpost tabstat ///
                ln_firm_exports n_destinations n_products ln_avg_dist ///
                if MNE == 0, statistics(mean sd) columns(statistics)

            if `first_tab' == 1 {
                esttab mne_`c' dom_`c' using ///
                    "$t_s3\tab_3_4_firm_profile_comparison.tex", ///
                    replace cells("mean(fmt(%9.2f)) sd(fmt(%9.2f))") ///
                    mtitle("MNE" "Domestic") ///
                    title("`c'") label noobs
                local first_tab = 0
            }
            else {
                esttab mne_`c' dom_`c' using ///
                    "$t_s3\tab_3_4_firm_profile_comparison.tex", ///
                    append cells("mean(fmt(%9.2f)) sd(fmt(%9.2f))") ///
                    mtitle("MNE" "Domestic") ///
                    title("`c'") label noobs
            }
        restore
    }
    copy "$t_s3\tab_3_4_firm_profile_comparison.tex" ///
         "$ol_t_s3\tab_3_4_firm_profile_comparison.tex", replace


* ---- Figure B1: Box plots — ln_firm_exports by MNE status, all countries ----
* Combined chart: 10 pairs of boxes (one pair per country)
* Use a country-rank numeric variable for the x-axis

preserve
    keep if !missing(ln_firm_exports) & !missing(MNE)
    * Create numeric country rank (sorted alphabetically)
    egen ctry_num = group(country_orig)
    label define ctry_num_lbl 1 "C1" 2 "C2" 3 "C3" 4 "C4" 5 "C5" ///
                               6 "C6" 7 "C7" 8 "C8" 9 "C9" 10 "C10", replace
    * Override with actual ISO3
    levelsof country_orig, local(cl)
    local k = 1
    foreach c of local cl {
        label define ctry_num_lbl `k' "`c'", modify
        local k = `k' + 1
    }
    label values ctry_num ctry_num_lbl

    foreach mne_def in ext total {
        if "`mne_def'" == "ext"   local mne_var "MNE"
        if "`mne_def'" == "total" local mne_var "MNE_total"

        cap confirm variable `mne_var'
        if _rc != 0 continue

        cap {
            graph box ln_firm_exports, ///
                over(`mne_var', label(labsize(vsmall)) ///
                    relabel(1 "Dom" 2 "Ext")) ///
                over(ctry_num, label(labsize(vsmall) angle(45))) ///
                nooutsides asyvars ///
                box(1, fcolor("$c_DOM") lcolor("$c_DOM")) ///
                box(2, fcolor("$c_MNE") lcolor("$c_MNE")) ///
                ytitle("Ln Total Exports") ///
                title("Firm Export Distribution: External vs Domestic", size(medium)) ///
                legend(on order(1 "Domestic" 2 "MNE_`mne_def'") ///
                       position(6) rows(1) size(small) region(lcolor(white))) ///
                bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
            export_graph "fig_1_1_fp_boxplot_`mne_def'" "$g11_fp" "$ol_g11_fp"
        }
    }
restore



**********************************************************************
* 1.2  ACROSS EXPORT DESTINATION COUNTRIES               [Plan §1.2]
**********************************************************************

*===============================================================
* 1.2.A  Bar graphs — aggregate (one per category × MNE def)
*===============================================================

use "$int\collapsed_ody.dta", clear

* Category list and corresponding figure numbers (aligned with LaTeX plan)
local cats  "income_group_dest intra_regional contig dest_region_num dist_above_med"
local fnums "1_2_1 1_2_2 1_2_3 1_2_4 1_2_5"
local n_cats : word count `cats'

foreach mne_def in ext total {
    if "`mne_def'" == "ext" {
        local sv "share_mne_value"
        local sn "share_mne_nfirms"
    }
    else if "`mne_def'" == "dom" {
        local sv "share_mne_value"
        local sn "share_dom_nfirms"
    }
    else {
        local sv "share_mne_value"
        local sn "share_total_nfirms"
    }
    forvalues k = 1/`n_cats' {
        local cat  : word `k' of `cats'
        local fnum : word `k' of `fnums'
        preserve
            drop if `cat' == .
            gcollapse (mean) `sv' `sn' [aw = total_value], by(`cat') labelformat(#sourcelabel#)
            cap {
                graph hbar (asis) `sv' `sn', ///
                    over(`cat', label(labsize(small))) ///
                    bar(1, color($c_MNE)) bar(2, color($c_DOM)) ///
                    legend(on order(1 "Share in Value" 2 "Share in # Exporters") ///
                           position(6) rows(1) region(lcolor(white)) size(small)) ///
                    title("MNE_`mne_def'", size(medium)) ///
                    ytitle("") bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
                export_graph "fig_`fnum'_`mne_def'_agg" "$g12" "$ol_g12"
            }
        restore
    }
}


*===============================================================
* 1.2.B  Bar graphs — by exporting country × category × MNE def
*===============================================================

use "$int\collapsed_ody.dta", clear
levelsof country_orig, local(countries)

foreach mne_def in ext total {
    if "`mne_def'" == "ext"   local sv "share_mne_value"
    if "`mne_def'" == "dom"   local sv "share_dom_nfirms"
    if "`mne_def'" == "total" local sv "share_total_nfirms"

    foreach cat in income_group_dest intra_regional contig dest_region_num dist_above_med {
        foreach c of local countries {
            preserve
                keep if country_orig == "`c'"
                drop if `cat' == .
                cap {
                    gcollapse (mean) `sv' [aw = total_value], by(`cat') labelformat(#sourcelabel#)
                    graph hbar (asis) `sv', ///
                        over(`cat', label(labsize(small))) ///
                        bar(1, color($c_MNE)) ///
                        title("`c' - MNE_`mne_def'", size(medium)) ///
                        ytitle("MNE Share") ///
                        bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
                    export_graph "fig_1_2_`mne_def'_`cat'_`c'" "$g12" "$ol_g12"
                }
            restore
        }
    }
}


*===============================================================
* 1.2.C_EXTRA  BLOCK C — MNE share vs. average tariff (scatter)
*   fig_1_2_6_[def]_tariff_scatter
*   Dataset: collapsed_ody.dta
*===============================================================
* NOTE: Shows the raw MNE-tariff relationship *before* the regression
*   interactions in §2.1. Non-obvious result: MNE presence may be
*   high in both very low and very high tariff markets (tariff-jumping
*   vs. supply-chain integration).

use "$int\collapsed_ody.dta", clear

* Collapse to one obs per ODY cell averaged over years for cleaner scatter
preserve
    gcollapse (mean) share_mne_value share_ext_nfirms share_total_nfirms ///
              avg_tariff ln_dist income_group_dest, ///
              by(country_orig country_dest) labelformat(#sourcelabel#)

    drop if missing(avg_tariff)

    * Income-group colour: 1=Low 2=LowMid 3=UpMid 4=High
    cap label define inc_lbl 1 "Low" 2 "Lower-Mid" 3 "Upper-Mid" 4 "High", replace

    foreach mne_def in ext total {
        if "`mne_def'" == "ext"   local sv "share_mne_value"
        if "`mne_def'" == "total" local sv "share_total_nfirms"

        cap {
            twoway ///
                (scatter `sv' avg_tariff if income_group_dest == 1, ///
                    mcolor("navy")   ms(o) msize(small)) ///
                (scatter `sv' avg_tariff if income_group_dest == 2, ///
                    mcolor("blue")   ms(d) msize(small)) ///
                (scatter `sv' avg_tariff if income_group_dest == 3, ///
                    mcolor("orange") ms(t) msize(small)) ///
                (scatter `sv' avg_tariff if income_group_dest == 4, ///
                    mcolor("red")    ms(s) msize(small)) ///
                (lfit `sv' avg_tariff, lcolor(black) lwidth(medthin)), ///
                ytitle("MNE_`mne_def' Share in Exports", size(*.9)) ///
                xtitle("Average Bilateral Tariff", size(*.9)) ///
                legend(on order(1 "Low Income" 2 "Lower-Mid" 3 "Upper-Mid" 4 "High Income") ///
                       position(6) rows(1) size(vsmall) region(lcolor(white))) ///
                ylab(, nogrid) $gro
            export_graph "fig_1_2_6_`mne_def'_tariff_scatter" "$g12" "$ol_g12"
        }
    }
restore


*===============================================================
* 1.2.C  Regressions — origin and destination characteristics
*===============================================================

* run_trade_spec: loops over the standard 7-spec FE ladder
* FIX: changed `local fe "`fe`f''"` to `local fe "${fe`f'}"` so the
*   globals fe1..fe7 (defined at the top) are accessible inside the program.
capture program drop run_trade_spec
program define run_trade_spec
    args dv controls filename cluster_id cluster_lbl

    * Column 1: no FE, robust SE
    reg `dv' `controls', robust
    outreg2 using "`filename'", ///
        replace tex(frag) label ctitle("No FE") ///
        addtext(FE, "None", SE Cluster, "`cluster_lbl'") ///
        dec(4) nocons

    * Columns 2-7: reghdfe with progressively richer FE
    forval f = 2/7 {
        local fe "${fe`f'}"   // FIX: was `fe`f'' (local), now accesses global
        local fl "${fel`f'}"  // FIX: idem

        reghdfe `dv' `controls', absorb(`fe') vce(cluster `cluster_id')

        outreg2 using "`filename'", ///
            append tex(frag) label ctitle("`fl'") ///
            addtext(FE, "`fl'", SE Cluster, "`cluster_lbl'") ///
            dec(4) nocons
    }

    * Extra column for ODPY: absorb origin-destination-time
    if "`cluster_id'" == "odp_id" {
        reghdfe `dv' `controls', absorb(odt_id) vce(cluster `cluster_id')
        outreg2 using "`filename'", ///
            append tex(frag) label ctitle("ODxT") ///
            addtext(FE, "ODxT", SE Cluster, "`cluster_lbl'") ///
            dec(4) nocons
    }
end


local controls "ln_gdpcap_o ln_pop_o ln_gdpcap_d ln_pop_d ln_dist contig comlang_off colony fta_wto BIT DTT avg_tariff"

* --- ODY ---
use "$int\collapsed_ody.dta", clear

foreach mne_def in ext total {
    if "`mne_def'" == "ext" {
        local dvars "share_mne_value share_mne_nfirms"
    }
    else {
        local dvars "share_`mne_def'_nfirms"
    }
    foreach dv of local dvars {
        run_trade_spec ///
            `dv' "`controls'" ///
            "$r_s1\reg_1_2_ody_`mne_def'_`dv'.tex" ///
            "od_id" "Origin-Destination"
        copy "$r_s1\reg_1_2_ody_`mne_def'_`dv'.tex" ///
             "$ol_r_s1\reg_1_2_ody_`mne_def'_`dv'.tex", replace
    }
}

* --- ODPY ---
use "$int\collapsed_odpy.dta", clear

foreach mne_def in ext total {
    if "`mne_def'" == "ext" {
        local dvars "share_mne_value share_mne_nfirms"
    }
    else {
        local dvars "share_`mne_def'_nfirms"
    }
    foreach dv of local dvars {
        run_trade_spec ///
            `dv' "`controls'" ///
            "$r_s1\reg_1_2_odpy_`mne_def'_`dv'.tex" ///
            "odp_id" "Origin-Destination-Product"
        copy "$r_s1\reg_1_2_odpy_`mne_def'_`dv'.tex" ///
             "$ol_r_s1\reg_1_2_odpy_`mne_def'_`dv'.tex", replace
    }
}


**********************************************************************
* 1.3  BY PRODUCT                                         [Plan §1.3]
**********************************************************************

*===============================================================
* 1.3.A  Bar graphs — aggregate (by product characteristic × MNE def)
*===============================================================

use "$int\collapsed_opy.dta", clear

foreach mne_def in ext total {
    if "`mne_def'" == "ext" {
        local sv "share_mne_value"
        local sn "share_mne_nfirms"
    }
    else if "`mne_def'" == "dom" {
        local sv "share_mne_value"
        local sn "share_dom_nfirms"
    }
    else {
        local sv "share_mne_value"
        local sn "share_total_nfirms"
    }

    * (i) Above / below median for each product characteristic
    foreach v in upstreamness sigma complexity quality_ladder rca rhci lall2000 ipc1 {
        cap confirm variable `v'_abovemed
        if _rc != 0 continue
        preserve
            drop if `v'_abovemed == .
            gcollapse (mean) `sv' `sn' [aw = total_value], by(`v'_abovemed) labelformat(#sourcelabel#)
            label define med_lbl 0 "Below Median" 1 "Above Median", replace
            label values `v'_abovemed med_lbl
            cap {
                graph hbar (asis) `sv' `sn', ///
                    over(`v'_abovemed, label(labsize(small))) ///
                    bar(1, color($c_MNE)) bar(2, color($c_DOM)) ///
                    legend(on order(1 "Value" 2 "# Firms") ///
                           position(6) rows(1) region(lcolor(white)) size(small)) ///
                    title("MNE_`mne_def' - `v'", size(medium)) ///
                    ytitle("") bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
                export_graph "fig_1_3_`mne_def'_`v'_median" "$g13" "$ol_g13"
            }
        restore
    }

    * (ii) By decile (numeric characteristics only; lall2000/ipc1 safely skipped)
    foreach v in upstreamness sigma complexity quality_ladder rca rhci {
        cap confirm variable `v'_decile
        if _rc != 0 continue
        preserve
            drop if `v'_decile == .
            gcollapse (mean) `sv' [aw = total_value], by(`v'_decile)
            cap {
                twoway (bar `sv' `v'_decile, barwidth(0.8) fcolor($c_MNE) lcolor($c_MNE)), ///
                    xtitle("`v' Decile") ytitle("MNE_`mne_def' Share (value)") ///
                    xlab(1(1)10) ylab(, nogrid) $gro ///
                    title("MNE_`mne_def' - `v' Decile", size(medium))
                export_graph "fig_1_3_`mne_def'_`v'_decile" "$g13" "$ol_g13"
            }
        restore
    }

    * HS Sections
    preserve
        gcollapse (mean) `sv' `sn' [aw = total_value], by(hs_section) labelformat(#sourcelabel#)
        cap {
            graph hbar (asis) `sv' `sn', ///
                over(hs_section, sort(`sv') descending label(labsize(vsmall))) ///
                bar(1, color($c_MNE)) bar(2, color($c_DOM)) ///
                legend(on order(1 "Value" 2 "# Firms") position(6) rows(1) ///
                       region(lcolor(white)) size(small)) ///
                title("MNE_`mne_def' by HS Section", size(medium)) ///
                ytitle("") bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white)) ///
                ysize(6)
            export_graph "fig_1_3_`mne_def'_hs_sections" "$g13" "$ol_g13"
        }
    restore

    * Top 10 / Bottom 10 HS2 chapters by MNE share
    preserve
        gcollapse (mean) `sv' [aw = total_value], by(hs2) labelformat(#sourcelabel#)
        tempfile hs2_coll
        save `hs2_coll'

        gsort -`sv'
        keep if _n <= 10
        gen order = _n
        tostring hs2, gen(hs2_str)
        labmask order, values(hs2_str)
        local N = _N
        cap {
            twoway (bar `sv' order, barwidth(0.6) fcolor($c_MNE) lcolor($c_MNE)), ///
                xtitle("HS Chapter") ytitle("MNE_`mne_def' Share (value)") ///
                xla(1/`N', valuelabel ang(45) noticks labsize(*0.8)) ylab(, nogrid) $gro ///
                title("Top 10 HS Chapters - MNE_`mne_def'", size(medium))
            export_graph "fig_1_3_`mne_def'_top10_hs2" "$g13" "$ol_g13"
        }

        use `hs2_coll', clear
        gsort `sv'
        keep if _n <= 10
        gen order = _n
        tostring hs2, gen(hs2_str)
        labmask order, values(hs2_str)
        local N = _N
        cap {
            twoway (bar `sv' order, barwidth(0.6) fcolor($c_DOM) lcolor($c_DOM)), ///
                xtitle("HS Chapter") ytitle("MNE_`mne_def' Share (value)") ///
                xla(1/`N', valuelabel ang(45) noticks labsize(*0.8)) ylab(, nogrid) $gro ///
                title("Bottom 10 HS Chapters - MNE_`mne_def'", size(medium))
            export_graph "fig_1_3_`mne_def'_bot10_hs2" "$g13" "$ol_g13"
        }
    restore
}


*===============================================================
* 1.3.B  Bar graphs — by exporting country × product category
*===============================================================

use "$int\collapsed_opy.dta", clear
levelsof country_orig, local(countries)

foreach mne_def in ext total {
    if "`mne_def'" == "ext"   local sv "share_mne_value"
    if "`mne_def'" == "dom"   local sv "share_dom_nfirms"
    if "`mne_def'" == "total" local sv "share_total_nfirms"

    foreach cat in upstreamness_abovemed hs_section {
        foreach c of local countries {
            preserve
                keep if country_orig == "`c'"
                drop if `cat' == .
                * Apply labels only when variable matches
                cap label define med_lbl 0 "Below Median" 1 "Above Median", replace
                cap label values upstreamness_abovemed med_lbl
                cap {
                    gcollapse (mean) `sv' [aw = total_value], by(`cat') labelformat(#sourcelabel#)
                    graph hbar (asis) `sv', ///
                        over(`cat', label(labsize(small))) ///
                        bar(1, color($c_MNE)) ///
                        title("`c' - MNE_`mne_def'", size(medium)) ///
                        ytitle("MNE Share") ///
                        bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
                    export_graph "fig_1_3_`mne_def'_`cat'_`c'" "$g13" "$ol_g13"
                }
            restore
        }
    }
}


*===============================================================
* 1.3.C  Regressions — product characteristics
*===============================================================

* run_spec_iv: loops over either the OPY or ODPY FE ladder.
* FIX: replaced the broken fe_list/fel_list string-parsing approach
*   with a clean indexed-global approach.
*   Pass the ladder prefix ("opy" or "odpy") as 4th argument.
*   The program reads ${nfe_opy}, ${fe_opy1}, ${fel_opy1}, etc.
capture program drop run_spec_iv
program define run_spec_iv
    args dv iv filename ladder cluster_id cluster_lbl

    local nfe = ${nfe_`ladder'}   // number of FE specs for this ladder

    forval i = 1/`nfe' {
        local fe "${fe_`ladder'`i'}"    // e.g. ${fe_opy3}
        local fl "${fel_`ladder'`i'}"   // e.g. ${fel_opy3}

        if `i' == 1 {
            if "`fe'" == "" {
                reg `dv' `iv', robust
            }
            else {
                reghdfe `dv' `iv', absorb(`fe') vce(cluster `cluster_id')
            }
            outreg2 using "`filename'", ///
                replace tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", SE Cluster, "`cluster_lbl'") ///
                dec(4) nocons
        }
        else {
            if "`fe'" == "" {
                reg `dv' `iv', robust
            }
            else {
                reghdfe `dv' `iv', absorb(`fe') vce(cluster `cluster_id')
            }
            outreg2 using "`filename'", ///
                append tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", SE Cluster, "`cluster_lbl'") ///
                dec(4) nocons
        }
    }
end


* --- OPY regressions ---
use "$int\collapsed_opy.dta", clear

foreach mne_def in ext total {
    if "`mne_def'" == "ext" {
        local dvars "share_mne_value share_mne_nfirms"
    }
    else {
        local dvars "share_`mne_def'_nfirms"
    }
    foreach dv of local dvars {
        foreach iv in upstreamness sigma complexity quality_ladder rca rhci lall2000 ipc1 {
            cap confirm variable `iv'
            if _rc != 0 continue

            run_spec_iv ///
                `dv' `iv' ///
                "$r_s1\reg_1_3_opy_`mne_def'_`dv'_`iv'.tex" ///
                "opy" "op_id" "Origin-Product"

            * Extra column: HS section dummies as explanatory variable
            reghdfe `dv' i.hs_section, absorb(ot_id) vce(cluster op_id)
            outreg2 using "$r_s1\reg_1_3_opy_`mne_def'_`dv'_`iv'.tex", ///
                append tex(frag) label ctitle("HS Sections") ///
                addtext(FE, "OxT", SE Cluster, "Origin-Product") ///
                dec(4) nocons

            copy "$r_s1\reg_1_3_opy_`mne_def'_`dv'_`iv'.tex" ///
                 "$ol_r_s1\reg_1_3_opy_`mne_def'_`dv'_`iv'.tex", replace
        }
    }
}

* --- ODPY regressions ---
use "$int\collapsed_odpy.dta", clear

foreach mne_def in ext total {
    if "`mne_def'" == "ext" {
        local dvars "share_mne_value share_mne_nfirms"
    }
    else {
        local dvars "share_`mne_def'_nfirms"
    }
    foreach dv of local dvars {
        foreach iv in upstreamness sigma complexity quality_ladder rca rhci lall2000 ipc1 {
            cap confirm variable `iv'
            if _rc != 0 continue

            run_spec_iv ///
                `dv' `iv' ///
                "$r_s1\reg_1_3_odpy_`mne_def'_`dv'_`iv'.tex" ///
                "odpy" "odp_id" "Orig-Dest-Prod"

            copy "$r_s1\reg_1_3_odpy_`mne_def'_`dv'_`iv'.tex" ///
                 "$ol_r_s1\reg_1_3_odpy_`mne_def'_`dv'_`iv'.tex", replace
        }
    }
}


**********************************************************************
**********************************************************************
*
*   PART 1.4: PARENT COUNTRY ANALYSIS (Block D)
*
* FIGURE 1.4.1  Pooled bar: MNE export share by parent region
* FIGURE 1.4.2  Grouped bar: parent region breakdown by exporting country
* FIGURE 1.4.3  Bar: parent-destination match for US-destined exports
* FIGURE 1.4.4  Bar: parent-destination match for EU-destined exports
*
* Dataset: firm_level_data.dta
**********************************************************************
**********************************************************************

use "$int\firm_level_data.dta", clear

* Keep only MNE_ext observations (iso3_parent != country_orig)
keep if MNE_ext == 1

* ---- Classify parent company region ----
* Use dest_region variable logic: EU defined by European region code.

* Build parent_region using iso3_parent:
* - "USA"   : iso3_parent == "USA"
* - "EU"    : iso3_parent is an EU27 country (use dest_region equivalent for parent)
* - "LatAm" : iso3_parent is in Latin America (includes the 10 origin countries
*             AND other LatAm) — intra-regional MNE investing in LatAm
* - "Asia"  : iso3_parent is in Asia
* - "Other" : everything else (Canada, Australia, etc.)
*
* We use a ISO3-to-region mapping derived from the CEPII data already
* in the dataset. We merge briefly to get the region of iso3_parent.

* Step 1: build a lookup table: iso3 -> region from any obs in the data
*   We exploit that dest_region is already coded for country_dest.
*   We build the same coding for iso3_parent by joining on iso3_parent.


gen parent_region = ""
replace parent_region = "USA"   if iso3_parent == "USA"
replace parent_region = "Europe"  if inlist(iso3_parent,"AUT","BEL","BGR","CYP","CZE")
replace parent_region = "Europe"  if inlist(iso3_parent,"DNK","EST","FIN","FRA","DEU")
replace parent_region = "Europe"  if inlist(iso3_parent,"GRC","HUN","IRL","ITA","LVA")
replace parent_region = "Europe"  if inlist(iso3_parent,"LTU","LUX","MLT","NLD","POL")
replace parent_region = "Europe"  if inlist(iso3_parent,"PRT","ROU","SVK","SVN","ESP")
replace parent_region = "Europe"  if inlist(iso3_parent,"SWE","GBR")

replace parent_region = "LAC" if inlist(iso3_parent, "ARG","BHS","BRB","BLZ","BOL")
replace parent_region = "LAC" if inlist(iso3_parent, "BRA","CHL","COL","CRI","DOM")
replace parent_region = "LAC" if inlist(iso3_parent, "ECU","SLV","GTM","GUY","HTI")
replace parent_region = "LAC" if inlist(iso3_parent, "HND","JAM","MEX","NIC","PAN")
replace parent_region = "LAC" if inlist(iso3_parent, "PRY","PER","SUR","TTO","URY","VEN")

replace parent_region = "Asia" if inlist(iso3_parent,"CHN","HKG","IND","IDN","JPN")
replace parent_region = "Asia" if inlist(iso3_parent,"MYS","PHL","KOR","SGP","TWN")
replace parent_region = "Asia" if inlist(iso3_parent,"THA")

replace parent_region = "ROW" if parent_region == ""


* ---- FIGURE D1: Pooled bar — MNE export share by parent region ----
preserve
    gcollapse (sum) mne_exp = value_fob, by(parent_region) labelformat(#sourcelabel#)
    egen double tot = total(mne_exp)
    gen share_pr = mne_exp / tot
    gsort -share_pr
    gen order = _n
    labmask order, values(parent_region)
    local N = _N
    cap {
        graph hbar (asis) share_pr, ///
            over(order, sort(order) label(labsize(small))) ///
            bar(1, color($c_MNE)) ///
            ytitle("Share in Total MNE Exports") ///
            ylab(, nogrid format(%9.2f)) ///
            title("MNE Exports by Parent Region (Pooled)", size(medium)) ///
            bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
        export_graph "fig_1_4_1_parent_region_pool" "$g14" "$ol_g14"
    }
restore

* ---- FIGURE D2: Grouped bar — parent region by exporting country ----
preserve
    gcollapse (sum) mne_exp = value_fob, ///
        by(country_orig parent_region) labelformat(#sourcelabel#)
    bysort country_orig: egen double tot_ctry = total(mne_exp)
    gen share_pr = mne_exp / tot_ctry
	
    * Pivot-style: reshape to wide on parent_region
    keep country_orig parent_region share_pr
    reshape wide share_pr, i(country_orig) j(parent_region) string

    * Sort by USA share descending
    cap gsort -share_prUSA
    gen order = _n
    labmask order, values(country_orig)
    local N = _N

    cap {
        graph hbar (asis) share_prUSA share_prEurope share_prLAC share_prAsia share_prROW, ///
            over(order, sort(order) label(labsize(small))) ///
            bar(1, color("red*1.2"))   bar(2, color("blue*0.8")) ///
            bar(3, color("green*0.8")) bar(4, color("orange*0.9")) ///
            bar(5, color("gray*0.6")) ///
            stack ///
            legend(on order(1 "USA" 2 "EU" 3 "LatAm" 4 "Asia" 5 "Other") ///
                   position(6) rows(1) size(vsmall) region(lcolor(white))) ///
            ytitle("Share in Country's MNE Exports") ///
            title("Parent Region by Exporting Country", size(medium)) ///
            bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
        export_graph "fig_1_4_2_parent_region_by_origin" "$g14" "$ol_g14"
    }
restore

* ---- FIGURE D3: Parent region breakdown for US-destined vs. other exports ----
preserve
    gen dest_grp = cond(country_dest == "USA", "US Destinations", "Non-US Destinations")
    gcollapse (sum) mne_exp = value_fob, ///
        by(dest_grp parent_region) labelformat(#sourcelabel#)
    bysort dest_grp: egen double tot_dg = total(mne_exp)
    gen share_pr = mne_exp / tot_dg
	
    keep dest_grp parent_region share_pr
    reshape wide share_pr, i(dest_grp) j(parent_region)  string
    gen order = (_n == 1)  // "US Destinations" first
    sort order
    replace order = _n
    labmask order, values(dest_grp)

    cap {
        graph hbar (asis) share_prUSA share_prEurope share_prLAC share_prAsia share_prROW, ///
            over(order, label(labsize(small))) ///
            bar(1, color("red*1.2"))   bar(2, color("blue*0.8")) ///
            bar(3, color("green*0.8")) bar(4, color("orange*0.9")) ///
            bar(5, color("gray*0.6")) ///
            stack ///
            legend(on order(1 "USA Parent" 2 "EU Parent" 3 "LatAm Parent" 4 "Asia Parent" 5 "Other") ///
                   position(6) rows(1) size(vsmall) region(lcolor(white))) ///
            ytitle("Share in MNE Exports") ///
            title("Who Exports to the US? (by Parent Region)", size(medium)) ///
            bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
        export_graph "fig_1_4_3_parent_dest_match_usa" "$g14" "$ol_g14"
    }
restore

* ---- FIGURE D4: Parent region breakdown for EU-destined vs. other exports ----
preserve
    gen dest_grp = cond(dest_region == "Europe", "EU Destinations", "Non-EU Destinations")
    drop if missing(dest_grp)
    gcollapse (sum) mne_exp = value_fob, ///
        by(dest_grp parent_region) labelformat(#sourcelabel#)
    bysort dest_grp: egen double tot_dg = total(mne_exp)
    gen share_pr = mne_exp / tot_dg
		

    keep dest_grp parent_region share_pr
    reshape wide share_pr, i(dest_grp) j(parent_region)  string
    gen order = (dest_grp == "EU Destinations")
    gsort -order
    replace order = _n
    labmask order, values(dest_grp)

    cap {
        graph hbar (asis) share_prUSA share_prEurope share_prLAC share_prAsia share_prROW, ///
            over(order, label(labsize(small))) ///
            bar(1, color("red*1.2"))   bar(2, color("blue*0.8")) ///
            bar(3, color("green*0.8")) bar(4, color("orange*0.9")) ///
            bar(5, color("gray*0.6")) ///
            stack ///
            legend(on order(1 "USA Parent" 2 "EU Parent" 3 "LatAm Parent" 4 "Asia Parent" 5 "Other") ///
                   position(6) rows(1) size(vsmall) region(lcolor(white))) ///
            ytitle("Share in MNE Exports") ///
            title("Who Exports to the EU? (by Parent Region)", size(medium)) ///
            bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
        export_graph "fig_1_4_4_parent_dest_match_eu" "$g14" "$ol_g14"
    }
restore


**********************************************************************
**********************************************************************
*
*   PART 2: EFFECTS OF MULTINATIONAL PRESENCE IN TRADE
*
**********************************************************************
**********************************************************************


**********************************************************************
* 2.1  AGGREGATE REGRESSIONS                          [Plan §2 Agg]
**********************************************************************

*===============================================================
* 2.1.A  ODY
*===============================================================

* run_agg_spec: baseline/dest/bilat split for max 10 columns
* args: dv mv filename_base cluster_id cluster_lbl
capture program drop run_agg_spec
program define run_agg_spec
    args dv mv filename_base cluster_id cluster_lbl

    * --- Baseline (FE 1-7) - 7 cols ---
    forval f = 1/7 {
        local fe "${fe`f'}"
        local fl "${fel`f'}"
        if `f' == 1 reg `dv' `mv', robust
        else reghdfe `dv' `mv', absorb(`fe') vce(cluster `cluster_id')
        if `f' == 1 {
            outreg2 using "`filename_base'_baseline.tex", replace tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", Spec, "Baseline", SE Cluster, "`cluster_lbl'") dec(4) nocons
        }
        else {
            outreg2 using "`filename_base'_baseline.tex", append tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", Spec, "Baseline", SE Cluster, "`cluster_lbl'") dec(4) nocons
        }
    }

    * --- Destination interactions (FE 5-7) - 3 cols ---
    forval f = 5/7 {
        local fe "${fe`f'}"
        local fl "${fel`f'}"
        local ivd "`mv' `mv'_X_lngdppc_d `mv'_X_lnpop_d ln_gdpcap_d ln_pop_d"
        reghdfe `dv' `ivd', absorb(`fe') vce(cluster `cluster_id')
        if `f' == 5 {
            outreg2 using "`filename_base'_dest_int.tex", replace tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", Spec, "Dest Int", SE Cluster, "`cluster_lbl'") dec(4) nocons
        }
        else {
            outreg2 using "`filename_base'_dest_int.tex", append tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", Spec, "Dest Int", SE Cluster, "`cluster_lbl'") dec(4) nocons
        }
    }

    * --- Bilateral interactions (FE 5-7) - 3 cols ---
    forval f = 5/7 {
        local fe "${fe`f'}"
        local fl "${fel`f'}"
        local ivb "`mv' `mv'_X_lndist `mv'_X_contig `mv'_X_fta_wto ln_dist contig fta_wto"
        reghdfe `dv' `ivb', absorb(`fe') vce(cluster `cluster_id')
        if `f' == 5 {
            outreg2 using "`filename_base'_bilat_int.tex", replace tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", Spec, "Bilat Int", SE Cluster, "`cluster_lbl'") dec(4) nocons
        }
        else {
            outreg2 using "`filename_base'_bilat_int.tex", append tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", Spec, "Bilat Int", SE Cluster, "`cluster_lbl'") dec(4) nocons
        }
    }
end


use "$int\collapsed_ody.dta", clear

* Generate all interactions between MNE share variables and gravity variables
foreach mv in share_mne_value share_mne_nfirms share_ext_nfirms ///
              share_dom_nfirms share_total_nfirms {
    cap {
        gen `mv'_X_lngdppc_d = `mv' * ln_gdpcap_d
        gen `mv'_X_lnpop_d   = `mv' * ln_pop_d
        gen `mv'_X_lndist    = `mv' * ln_dist
        gen `mv'_X_contig    = `mv' * contig
        gen `mv'_X_fta_wto   = `mv' * fta_wto
    }
}

foreach mne_def in ext total {
    if "`mne_def'" == "ext" {
        local mv_list "share_mne_value share_mne_nfirms"
    }
    else {
        local mv_list "share_total_nfirms"
    }
    foreach mv of local mv_list {
        foreach dv in ln_total_value positive_trade total_value {
            run_agg_spec ///
                `dv' `mv' ///
                "$r_s2\reg_2_1_ody_`mne_def'_`mv'_`dv'" ///
                "od_id" "Origin-Destination"
            foreach suf in baseline dest_int bilat_int {
                copy "$r_s2\reg_2_1_ody_`mne_def'_`mv'_`dv'_`suf'.tex" ///
                     "$ol_r_s2\reg_2_1_ody_`mne_def'_`mv'_`dv'_`suf'.tex", replace
            }
        }
    }
}


*===============================================================
* 2.1.B  ODPY
*===============================================================

* run_agg_spec_odpy: baseline across ODPY ladder + product interactions
* FIX: uses indexed globals ${nfe_odpy}, ${fe_odpy`i'}, ${fel_odpy`i'}
*   instead of the undefined `fe_list_odpy' / `fel_list_odpy' locals.
capture program drop run_agg_spec_odpy
program define run_agg_spec_odpy
    args dv mv filename_base cluster_id cluster_lbl

    local nfe = ${nfe_odpy}
    
    * --- Baseline (ODPY 9-spec) - 9 cols ---
    forval i = 1/`nfe' {
        local fe "${fe_odpy`i'}"
        local fl "${fel_odpy`i'}"
        if "`fe'" == "" reg `dv' `mv', robust
        else reghdfe `dv' `mv', absorb(`fe') vce(cluster `cluster_id')
        if `i' == 1 {
            outreg2 using "`filename_base'_baseline.tex", replace tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", Spec, "Baseline", SE Cluster, "`cluster_lbl'") dec(4) nocons
        }
        else {
            outreg2 using "`filename_base'_baseline.tex", append tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", Spec, "Baseline", SE Cluster, "`cluster_lbl'") dec(4) nocons
        }
    }

    * --- Product interactions - 3 cols ---
    local first = 1
    foreach fe in "ot_id dt_id" "od_id year" "ot_id dt_id od_id" {
        if "`fe'" == "ot_id dt_id"       local fl "OxT + DxT"
        if "`fe'" == "od_id year"        local fl "OD x Year"
        if "`fe'" == "ot_id dt_id od_id" local fl "OxT + DxT + OD"
        local ivp "`mv' `mv'_X_upstream `mv'_X_sigma `mv'_X_complex upstreamness sigma complexity"
        reghdfe `dv' `ivp', absorb(`fe') vce(cluster `cluster_id')
        if `first' == 1 {
            outreg2 using "`filename_base'_prod_int.tex", replace tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", Spec, "Product Int", SE Cluster, "`cluster_lbl'") dec(4) nocons
            local first = 0
        }
        else {
            outreg2 using "`filename_base'_prod_int.tex", append tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", Spec, "Product Int", SE Cluster, "`cluster_lbl'") dec(4) nocons
        }
    }
end


use "$int\collapsed_odpy.dta", clear

* Generate interactions for ODPY regressions
foreach mv in share_mne_value share_mne_nfirms share_ext_nfirms ///
              share_dom_nfirms share_total_nfirms {
    cap {
        gen `mv'_X_lndist    = `mv' * ln_dist
        gen `mv'_X_fta_wto   = `mv' * fta_wto
        gen `mv'_X_lngdppc_d = `mv' * ln_gdpcap_d
        gen `mv'_X_upstream  = `mv' * upstreamness
        gen `mv'_X_sigma     = `mv' * sigma
        gen `mv'_X_complex   = `mv' * complexity
    }
}

foreach mne_def in ext total {
    if "`mne_def'" == "ext" {
        local mv_list "share_mne_value share_mne_nfirms"
    }
    else {
        local mv_list "share_total_nfirms"
    }
    foreach mv of local mv_list {
        foreach dv in ln_total_value positive_trade total_value {
            run_agg_spec_odpy ///
                `dv' `mv' ///
                "$r_s2\reg_2_1_odpy_`mne_def'_`mv'_`dv'" ///
                "odp_id" "Orig-Dest-Prod"
            foreach suf in baseline prod_int {
                copy "$r_s2\reg_2_1_odpy_`mne_def'_`mv'_`dv'_`suf'.tex" ///
                     "$ol_r_s2\reg_2_1_odpy_`mne_def'_`mv'_`dv'_`suf'.tex", replace
            }
        }
    }
}


**********************************************************************
* 2.2  GRAVITY REGRESSIONS                        [Plan §2 Gravity]
**********************************************************************

*===============================================================
* 2.2.A  Firm-Destination-Year
*===============================================================

* run_gravity_fdy: baseline 7-spec FE + destination interactions
capture program drop run_gravity_fdy
program define run_gravity_fdy
    args dv gvars mv dv2 filename cluster_id cluster_lbl

    local est "reghdfe"
    if "`dv'" == "firm_dest_exports" local est "reghdfe"

    * --- Baseline (FE 1-7) ---
    forval f = 1/7 {
        local fe "${fe`f'}"
        local fl "${fel`f'}"

        if "`est'" == "reghdfe" {
            if `f' == 1 reg `dv' `gvars', robust
            else        reghdfe `dv' `gvars', absorb(`fe') vce(cluster `cluster_id')
        }
        else {
            if `f' == 1 reghdfe `dv' `gvars', noabsorb
            else        reghdfe `dv' `gvars', absorb(`fe')
        }

        if `f' == 1 {
            outreg2 using "`filename'", replace tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", Spec, "Baseline", SE Cluster, "`cluster_lbl'") ///
                dec(4) nocons
        }
        else {
            outreg2 using "`filename'", append tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", Spec, "Baseline", SE Cluster, "`cluster_lbl'") ///
                dec(4) nocons
        }
    }

    * --- Destination interactions (FE 5, 7) ---
    foreach f in 5 7 {
        local fe "${fe`f'}"
        local fl "${fel`f'}"
        local ivd "`mv'_X_lndist `dv2'_X_lndist `mv'_X_lngdppc_d `dv2'_X_lngdppc_d `mv'_X_lnpop_d `dv2'_X_lnpop_d `mv'"

        if "`est'" == "reghdfe" reghdfe `dv' `ivd', absorb(`fe')
        else reghdfe `dv' `ivd', absorb(`fe') vce(cluster `cluster_id')

        outreg2 using "`filename'", append tex(frag) label ctitle("`fl'") ///
            addtext(FE, "`fl'", Spec, "Dest Interactions", SE Cluster, "`cluster_lbl'") ///
            dec(4) nocons
    }
end


use "$int\firm_dest_year_level.dta", clear

* Generate all interaction terms before the regression loop
foreach mv_pair in "MNE DOM" "MNE_dom DOM_dom" "MNE_total DOM_total" {
    local mv  : word 1 of `mv_pair'
    local dv2 : word 2 of `mv_pair'
    cap {
        gen `mv'_X_lndist     = `mv' * ln_dist
        gen `dv2'_X_lndist    = `dv2' * ln_dist
        gen `mv'_X_contig     = `mv' * contig
        gen `dv2'_X_contig    = `dv2' * contig
        gen `mv'_X_comlang    = `mv' * comlang_off
        gen `dv2'_X_comlang   = `dv2' * comlang_off
        gen `mv'_X_colony     = `mv' * colony
        gen `dv2'_X_colony    = `dv2' * colony
        gen `mv'_X_fta_wto    = `mv' * fta_wto
        gen `dv2'_X_fta_wto   = `dv2' * fta_wto
        gen `mv'_X_lngdppc_d  = `mv' * ln_gdpcap_d
        gen `dv2'_X_lngdppc_d = `dv2' * ln_gdpcap_d
        gen `mv'_X_lnpop_d    = `mv' * ln_pop_d
        gen `dv2'_X_lnpop_d   = `dv2' * ln_pop_d
    }
}

* FIX: braces added so BOTH mv and dv2 are always set before the call.
*   Without braces, the `if` only executes `local mv`, and `;` is NOT
*   a command separator in Stata — so `dv2` was never assigned, causing
*   a shifted args list and the "file dv2.txt could not be opened" error.
foreach mne_def in ext total {

    if "`mne_def'" == "ext" {
        local mv  "MNE"
        local dv2 "DOM"
    }
    else if "`mne_def'" == "dom" {
        local mv  "MNE_dom"
        local dv2 "DOM_dom"
    }
    else {
        local mv  "MNE_total"
        local dv2 "DOM_total"
    }

    * Gravity vars: each bilateral characteristic interacted with MNE and DOM
    local gvars "`mv'_X_lndist `dv2'_X_lndist `mv'_X_contig `dv2'_X_contig `mv'_X_comlang `dv2'_X_comlang `mv'_X_colony `dv2'_X_colony `mv'_X_fta_wto `dv2'_X_fta_wto `mv'"

    foreach dv in ln_exports positive_trade firm_dest_exports {
        run_gravity_fdy ///
            `dv' "`gvars'" `mv' `dv2' ///
            "$r_s2\reg_2_2_grav_fdy_`mne_def'_`dv'.tex" ///
            "od_id" "Origin-Destination"
        copy "$r_s2\reg_2_2_grav_fdy_`mne_def'_`dv'.tex" ///
             "$ol_r_s2\reg_2_2_grav_fdy_`mne_def'_`dv'.tex", replace
    }
}

*===============================================================
* 2.2.B  Firm-Destination-Product-Year
*===============================================================

capture program drop run_gravity_fdpy
program define run_gravity_fdpy
    args dv gvars mv dv2 filename_base cluster_id cluster_lbl

    local nfe = ${nfe_odpy}
    
    * --- Baseline (ODPY 9-spec) - 9 cols ---
    forval i = 1/`nfe' {
        local fe "${fe_odpy`i'}"
        local fl "${fel_odpy`i'}"
        if "`fe'" == "" reg `dv' `gvars', robust
        else reghdfe `dv' `gvars', absorb(`fe') vce(cluster `cluster_id')
        if `i' == 1 {
            outreg2 using "`filename_base'_baseline.tex", replace tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", Spec, "Baseline", SE Cluster, "`cluster_lbl'") dec(4) nocons
        }
        else {
            outreg2 using "`filename_base'_baseline.tex", append tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", Spec, "Baseline", SE Cluster, "`cluster_lbl'") dec(4) nocons
        }
    }

    * --- Product interactions - 2 cols ---
    local first = 1
    foreach fe in "ot_id dt_id" "ot_id dt_id od_id" {
        if "`fe'" == "ot_id dt_id"       local fl "OxT + DxT"
        if "`fe'" == "ot_id dt_id od_id" local fl "OxT + DxT + OD"
        local ivp "`mv'_X_lndist `dv2'_X_lndist `mv'_X_upstream `dv2'_X_upstream `mv'_X_sigma `dv2'_X_sigma `mv'_X_complex `dv2'_X_complex `mv'"
        reghdfe `dv' `ivp', absorb(`fe') vce(cluster `cluster_id')
        if `first' == 1 {
            outreg2 using "`filename_base'_prod_int.tex", replace tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", Spec, "Product Int", SE Cluster, "`cluster_lbl'") dec(4) nocons
            local first = 0
        }
        else {
            outreg2 using "`filename_base'_prod_int.tex", append tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", Spec, "Product Int", SE Cluster, "`cluster_lbl'") dec(4) nocons
        }
    }
end


use "$int\firm_level_data_full.dta", clear

* FIX (new): firm_level_data_full.dta has no FE group IDs nor log-value variable.
* Create them here before calling run_gravity_fdpy.
* NOTE: positive_trade = 1 always in observed trade data (no zeros).
*   A squared dataset would be required for a proper extensive margin
*   estimation; this serves as a placeholder consistent with other sections.
gen ln_exports      = ln(value_fob) if value_fob > 0
gen byte positive_trade = 1
label var ln_exports  "Ln firm exports (product-destination-year)"
label var positive_trade "=1 if trade observed (placeholder, all obs = 1)"

* Fixed-effect group identifiers (not pre-existing in firm_level_data_full)
egen orig_id = group(country_orig)
egen dest_id = group(country_dest)
egen prod_id = group(hs6)
egen od_id   = group(country_orig country_dest)
egen op_id   = group(country_orig hs6)
egen ot_id   = group(country_orig year)
egen dt_id   = group(country_dest year)
egen pt_id   = group(hs6 year)
egen odt_id  = group(country_orig country_dest year)
egen odp_id  = group(country_orig country_dest hs6)

* FIX: generate all interactions needed by run_gravity_fdpy
* (these were previously missing: "prep code unchanged" with no actual code)
foreach mv_pair in "MNE DOM" "MNE_dom DOM_dom" "MNE_total DOM_total" {
    local mv  : word 1 of `mv_pair'
    local dv2 : word 2 of `mv_pair'
    cap {
        gen `mv'_X_lndist    = `mv' * ln_dist
        gen `dv2'_X_lndist   = `dv2' * ln_dist
        gen `mv'_X_contig    = `mv' * contig
        gen `dv2'_X_contig   = `dv2' * contig
        gen `mv'_X_fta_wto   = `mv' * fta_wto
        gen `dv2'_X_fta_wto  = `dv2' * fta_wto
        gen `mv'_X_upstream  = `mv' * upstreamness
        gen `dv2'_X_upstream = `dv2' * upstreamness
        gen `mv'_X_sigma     = `mv' * sigma
        gen `dv2'_X_sigma    = `dv2' * sigma
        gen `mv'_X_complex   = `mv' * complexity
        gen `dv2'_X_complex  = `dv2' * complexity
    }
}

foreach mne_def in ext total {

    if "`mne_def'" == "ext" {
        local mv  "MNE"
        local dv2 "DOM"
    }
    else if "`mne_def'" == "dom" {
        local mv  "MNE_dom"
        local dv2 "DOM_dom"
    }
    else {
        local mv  "MNE_total"
        local dv2 "DOM_total"
    }

    local gvars "`mv'_X_lndist `dv2'_X_lndist `mv'_X_contig `dv2'_X_contig `mv'_X_fta_wto `dv2'_X_fta_wto `mv'"

    foreach dv in ln_exports positive_trade value_fob {
        run_gravity_fdpy ///
            `dv' "`gvars'" `mv' `dv2' ///
            "$r_s2\reg_2_2_grav_fdpy_`mne_def'_`dv'" ///
            "odp_id" "Orig-Dest-Prod"
        foreach suf in baseline prod_int {
            copy "$r_s2\reg_2_2_grav_fdpy_`mne_def'_`dv'_`suf'.tex" ///
                 "$ol_r_s2\reg_2_2_grav_fdpy_`mne_def'_`dv'_`suf'.tex", replace
        }
    }
}


**********************************************************************
* 2.3  MNE NETWORK REGRESSIONS                    [Plan §2 Network]
**********************************************************************
*
* Three progressively richer decompositions of how MNE network
* presence at the destination interacts with distance.
*   D1: Present / NotPresent / DOM
*   D2: HQ / Affiliate / NotPresent / DOM
*   D3: HQ / Affiliate / Neighbor / NotPresent / DOM
*
* NOTE: network variables (MNE_present_dest, MNE_HQ_dest, etc.) are
*   built from MNE_ext. The loop over mne_def ext/dom/total uses the same
*   decompositions for all three to maintain comparability.
**********************************************************************

* run_network_spec: 7-spec FE ladder
* FIX: uses ${fe`f'} / ${fel`f'} globals
capture program drop run_network_spec
program define run_network_spec
    args dv dvars filename cluster_id cluster_lbl decomp

    local est "reghdfe"
    if "`dv'" == "firm_dest_exports" local est "reghdfe"

    forval f = 1/7 {
        local fe "${fe`f'}"
        local fl "${fel`f'}"

        if "`est'" == "reghdfe" {
            if `f' == 1 reg `dv' `dvars', robust
            else        reghdfe `dv' `dvars', absorb(`fe') vce(cluster `cluster_id')
        }
        else {
            if `f' == 1 reghdfe `dv' `dvars', noabsorb
            else        reghdfe `dv' `dvars', absorb(`fe')
        }

        if `f' == 1 {
            outreg2 using "`filename'", replace tex(frag) label ctitle("D`decomp'") ///
                addtext(FE, "`fl'", SE Cluster, "`cluster_lbl'") dec(4) nocons
        }
        else {
            outreg2 using "`filename'", append tex(frag) label ctitle("D`decomp'") ///
                addtext(FE, "`fl'", SE Cluster, "`cluster_lbl'") dec(4) nocons
        }
    }
end


use "$int\firm_dest_year_level.dta", clear

* NOTE: firm_dest_year_level.dta already has MNE/DOM (renamed from MNE_ext/DOM_ext
*   in Part 0), and the FE IDs orig_id, dest_id, od_id, ot_id, dt_id.
*   We re-generate the interaction terms here since this is a fresh load.
foreach mv_pair in "MNE DOM" "MNE_dom DOM_dom" "MNE_total DOM_total" {
    local mv  : word 1 of `mv_pair'
    local dv2 : word 2 of `mv_pair'
    cap {
        gen `mv'_X_lndist     = `mv' * ln_dist
        gen `dv2'_X_lndist    = `dv2' * ln_dist
        gen `mv'_X_contig     = `mv' * contig
        gen `dv2'_X_contig    = `dv2' * contig
        gen `mv'_X_comlang    = `mv' * comlang_off
        gen `dv2'_X_comlang   = `dv2' * comlang_off
        gen `mv'_X_colony     = `mv' * colony
        gen `dv2'_X_colony    = `dv2' * colony
        gen `mv'_X_fta_wto    = `mv' * fta_wto
        gen `dv2'_X_fta_wto   = `dv2' * fta_wto
        gen `mv'_X_lngdppc_d  = `mv' * ln_gdpcap_d
        gen `dv2'_X_lngdppc_d = `dv2' * ln_gdpcap_d
        gen `mv'_X_lnpop_d    = `mv' * ln_pop_d
        gen `dv2'_X_lnpop_d   = `dv2' * ln_pop_d
    }
}

* Build distance interaction terms for each network decomposition
gen MNE_Pres_X_dist    = MNE * MNE_present_dest    * ln_dist
gen MNE_NotPres_X_dist = MNE * MNE_notpresent_dest * ln_dist
gen DOM_X_dist         = DOM * ln_dist
gen MNE_HQ_X_dist      = MNE * MNE_HQ_dest         * ln_dist
gen MNE_Aff_X_dist     = MNE * MNE_aff_dest        * ln_dist
gen MNE_NotPr_X_dist   = MNE * MNE_notpresent_dest  * ln_dist
gen MNE_Neigh_X_dist   = MNE * MNE_neighbor_dest   * ln_dist
gen MNE_NoPr3_X_dist   = MNE * (MNE_notpresent_dest==1 & MNE_neighbor_dest==0) * ln_dist

* Define the three decompositions
local d1 "MNE_Pres_X_dist MNE_NotPres_X_dist DOM_X_dist"
local d2 "MNE_HQ_X_dist MNE_Aff_X_dist MNE_NotPr_X_dist DOM_X_dist"
local d3 "MNE_HQ_X_dist MNE_Aff_X_dist MNE_Neigh_X_dist MNE_NoPr3_X_dist DOM_X_dist"

foreach mne_def in ext total {
    foreach dv in ln_exports firm_dest_exports {
        forval d = 1/3 {
            run_network_spec ///
                `dv' "`d`d''" ///
                "$r_s2\reg_2_3_net_D`d'_`mne_def'_`dv'.tex" ///
                "od_id" "Origin-Destination" `d'
            copy "$r_s2\reg_2_3_net_D`d'_`mne_def'_`dv'.tex" ///
                 "$ol_r_s2\reg_2_3_net_D`d'_`mne_def'_`dv'.tex", replace
        }
    }
}


*---------------------------------------------------------------
* BLOCK E — CONCENTRATION DESCRIPTIVES (before regression §2.4)
*   fig_2_4_conc_mne_present    : Top-k concentration in cells
*                                 with vs without MNE presence
*   fig_2_4_conc_over_nfirms    : Top-1 concentration vs ln(#firms),
*                                 coloured by MNE presence
*   Dataset: collapsed_ody.dta
*---------------------------------------------------------------

use "$int\collapsed_ody.dta", clear

* Binary: at least one MNE exporter in the cell
gen byte mne_present = (share_mne_nfirms > 0) if !missing(share_mne_nfirms)
label define mne_pres_lbl 0 "No MNE" 1 "MNE Present", replace
label values mne_present mne_pres_lbl

* ---- Figure E1: Raw concentration by MNE presence, per country ----
levelsof country_orig, local(ctry_e)

foreach c of local ctry_e {
    preserve
        keep if country_orig == "`c'"
        drop if missing(mne_present)

        gcollapse (mean) share_top1_all share_top3_all share_top5_all, ///
            by(mne_present) labelformat(#sourcelabel#)

        cap {
            graph hbar (asis) share_top1_all share_top3_all share_top5_all, ///
                over(mne_present, label(labsize(small))) ///
                bar(1, color($c_MNE))   ///
                bar(2, color(orange*0.8)) ///
                bar(3, color(navy*0.6)) ///
                legend(on order(1 "Top-1" 2 "Top-3" 3 "Top-5") ///
                       position(6) rows(1) size(small) region(lcolor(white))) ///
                ytitle("Mean Concentration Share") ///
                title("`c': Export Concentration by MNE Presence", size(medium)) ///
                bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
            export_graph "fig_2_4_conc_mne_present_`c'" "$g24" "$ol_g24"
        }
    restore
}

* ---- Figure E2: Pooled scatter — top-1 concentration vs ln(#firms) ----
preserve
    drop if missing(mne_present) | missing(ln_n_exp_all) | missing(share_top1_all)

    cap {
        twoway ///
            (scatter share_top1_all ln_n_exp_all if mne_present == 0, ///
                mcolor("$c_DOM") ms(oh) msize(tiny) alpha(50)) ///
            (scatter share_top1_all ln_n_exp_all if mne_present == 1, ///
                mcolor("$c_MNE") ms(o)  msize(tiny) alpha(50)) ///
            (lfit share_top1_all ln_n_exp_all if mne_present == 0, ///
                lcolor("$c_DOM") lwidth(medthin)) ///
            (lfit share_top1_all ln_n_exp_all if mne_present == 1, ///
                lcolor("$c_MNE") lwidth(medthin)), ///
            ytitle("Top-1 Exporter Share") ///
            xtitle("Ln(# Exporters in Cell)") ///
            legend(on order(1 "No MNE" 2 "MNE Present") ///
                   position(6) rows(1) size(small) region(lcolor(white))) ///
            title("Concentration vs. Market Size: MNE vs. No-MNE Cells", size(medium)) ///
            $gro
        export_graph "fig_2_4_conc_over_nfirms" "$g24" "$ol_g24"
    }
restore


**********************************************************************
* 2.4  CONCENTRATION PATTERNS                  [Plan §2 Concentration]
**********************************************************************

*===============================================================
* 2.4.A  ODY
*===============================================================

* run_conc_ody: 7-spec FE ladder for concentration outcomes
* FIX: uses ${fe`f'} / ${fel`f'} globals
capture program drop run_conc_ody
program define run_conc_ody
    args dv mv filename cluster_id cluster_lbl

    forval f = 1/7 {
        local fe "${fe`f'}"
        local fl "${fel`f'}"

        if `f' == 1 reg `dv' `mv', robust
        else        reghdfe `dv' `mv', absorb(`fe') vce(cluster `cluster_id')

        if `f' == 1 {
            outreg2 using "`filename'", replace tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", SE Cluster, "`cluster_lbl'") dec(4) nocons
        }
        else {
            outreg2 using "`filename'", append tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", SE Cluster, "`cluster_lbl'") dec(4) nocons
        }
    }
end


use "$int\collapsed_ody.dta", clear

local dep_conc "share_top1_all share_top3_all share_top5_all ln_n_exp_all share_top1_dom share_top3_dom share_top5_dom ln_n_exp_dom"

foreach mne_def in ext total {
    if "`mne_def'" == "ext"   local mv_list "share_mne_value share_mne_nfirms"
    else                       local mv_list "share_`mne_def'_nfirms"

    foreach mv of local mv_list {
        foreach dv of local dep_conc {
            run_conc_ody ///
                `dv' `mv' ///
                "$r_s2\reg_2_4_conc_ody_`mne_def'_`mv'_`dv'.tex" ///
                "od_id" "Origin-Destination"
            copy "$r_s2\reg_2_4_conc_ody_`mne_def'_`mv'_`dv'.tex" ///
                 "$ol_r_s2\reg_2_4_conc_ody_`mne_def'_`mv'_`dv'.tex", replace
        }
    }
}


*===============================================================
* 2.4.B  ODPY
*===============================================================

* run_conc_odpy: baseline across ODPY 9-spec ladder
* FIX: uses indexed globals
capture program drop run_conc_odpy
program define run_conc_odpy
    args dv mv filename cluster_id cluster_lbl

    local nfe = ${nfe_odpy}
    forval i = 1/`nfe' {
        local fe "${fe_odpy`i'}"
        local fl "${fel_odpy`i'}"

        if "`fe'" == "" reg `dv' `mv', robust
        else            reghdfe `dv' `mv', absorb(`fe') vce(cluster `cluster_id')

        if `i' == 1 {
            outreg2 using "`filename'", replace tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", Spec, "Baseline", SE Cluster, "`cluster_lbl'") ///
                dec(4) nocons
        }
        else {
            outreg2 using "`filename'", append tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", Spec, "Baseline", SE Cluster, "`cluster_lbl'") ///
                dec(4) nocons
        }
    }
end


* run_conc_odpy_int: interactions with gravity and product vars
* FIX: first iteration must use "replace" (was always "append")
capture program drop run_conc_odpy_int
program define run_conc_odpy_int
    args dv mv filename cluster_id cluster_lbl

    local first = 1
    foreach ivar in lngdppc_d lndist upstream sigma {

        reghdfe `dv' `mv' `mv'_X_`ivar', ///
            absorb(ot_id dt_id) vce(cluster `cluster_id')

        if `first' == 1 {
            outreg2 using "`filename'", replace tex(frag) label ctitle("OxT + DxT") ///
                addtext(FE, "OxT + DxT", Spec, "x `ivar'", SE Cluster, "`cluster_lbl'") ///
                dec(4) nocons
            local first = 0
        }
        else {
            outreg2 using "`filename'", append tex(frag) label ctitle("OxT + DxT") ///
                addtext(FE, "OxT + DxT", Spec, "x `ivar'", SE Cluster, "`cluster_lbl'") ///
                dec(4) nocons
        }
    }
end


use "$int\collapsed_odpy.dta", clear

* FIX: generate interactions needed by run_conc_odpy_int
* (these were missing: marked "interaction generation unchanged" with no code)
foreach mv in share_mne_value share_mne_nfirms share_ext_nfirms ///
              share_dom_nfirms share_total_nfirms {
    cap {
        gen `mv'_X_lngdppc_d = `mv' * ln_gdpcap_d
        gen `mv'_X_lndist    = `mv' * ln_dist
        gen `mv'_X_upstream  = `mv' * upstreamness
        gen `mv'_X_sigma     = `mv' * sigma
    }
}

local dep_conc_p "share_top1_all_p share_top3_all_p share_top5_all_p ln_n_exp_all_p share_top1_dom_p share_top3_dom_p share_top5_dom_p ln_n_exp_dom_p"

foreach mne_def in ext total {
    if "`mne_def'" == "ext"   local mv_list "share_mne_value share_mne_nfirms"
    else                       local mv_list "share_`mne_def'_nfirms"

    foreach mv of local mv_list {
        foreach dv of local dep_conc_p {

            run_conc_odpy ///
                `dv' `mv' ///
                "$r_s2\reg_2_4_conc_odpy_`mne_def'_`mv'_`dv'.tex" ///
                "odp_id" "Orig-Dest-Prod"

            run_conc_odpy_int ///
                `dv' `mv' ///
                "$r_s2\reg_2_4_conc_odpy_int_`mne_def'_`mv'_`dv'.tex" ///
                "odp_id" "Orig-Dest-Prod"

            copy "$r_s2\reg_2_4_conc_odpy_`mne_def'_`mv'_`dv'.tex" ///
                 "$ol_r_s2\reg_2_4_conc_odpy_`mne_def'_`mv'_`dv'.tex", replace
            copy "$r_s2\reg_2_4_conc_odpy_int_`mne_def'_`mv'_`dv'.tex" ///
                 "$ol_r_s2\reg_2_4_conc_odpy_int_`mne_def'_`mv'_`dv'.tex", replace
        }
    }
}


**********************************************************************

*---------------------------------------------------------------
* BLOCK F — NEW PRODUCT INTRODUCTION BY FIRM TYPE (before §2.5.A)
*   fig_2_5_newprod_by_type_year    : stacked bar by year (pooled)
*   fig_2_5_newprod_by_type_country : stacked bar by year, per country
*   Dataset: firm_level_data_full.dta
*---------------------------------------------------------------

use "$int\firm_level_data_full.dta", clear

* Collapse to origin-product-year, taking max of introduction dummies
* (a product is introduced in a year if any firm did it in that year)
    gcollapse ///
        (max) new_product_orig new_prod_only_mne new_prod_both new_prod_only_dom, ///
        by(country_orig hs6 year) labelformat(#sourcelabel#)

    * Replace missing with 0 for "no MNE/dom introduced" in that year
    foreach v in new_prod_only_mne new_prod_both new_prod_only_dom {
        replace `v' = 0 if missing(`v') & new_product_orig == 1
    }

    * Restrict to new products only
    keep if new_product_orig == 1

    * ---- Pooled: aggregate across all countries ----
    preserve
        gcollapse (sum) new_prod_only_mne new_prod_both new_prod_only_dom, ///
            by(year) labelformat(#sourcelabel#)

        gen total_new = new_prod_only_mne + new_prod_both + new_prod_only_dom
        gen sh_mne_only = new_prod_only_mne / total_new
        gen sh_both     = new_prod_both     / total_new
        gen sh_dom_only = new_prod_only_dom / total_new

        cap {
            graph bar (asis) sh_mne_only sh_both sh_dom_only, ///
                over(year, label(labsize(vsmall) angle(45))) ///
                bar(1, fcolor($c_MNE)       lcolor($c_MNE)) ///
                bar(2, fcolor(orange*0.8)   lcolor(orange*0.8)) ///
                bar(3, fcolor("$c_DOM")     lcolor("$c_DOM")) ///
                stack ///
                legend(on order(1 "MNE Only" 2 "MNE & Domestic" 3 "Domestic Only") ///
                       position(6) rows(1) size(small) region(lcolor(white))) ///
                ytitle("Share of New Products Introduced") ///
                title("New Product Introduction by Firm Type (Pooled)", size(medium)) ///
                bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
            export_graph "fig_2_5_newprod_by_type_year" "$g25" "$ol_g25"
        }
    restore

    * ---- Per country ----
    levelsof country_orig, local(ctry_f)

    foreach c of local ctry_f {
        preserve
            keep if country_orig == "`c'"
            gcollapse (sum) new_prod_only_mne new_prod_both new_prod_only_dom, ///
                by(year) labelformat(#sourcelabel#)

            gen total_new = new_prod_only_mne + new_prod_both + new_prod_only_dom
            gen sh_mne_only = new_prod_only_mne / total_new
            gen sh_both     = new_prod_both     / total_new
            gen sh_dom_only = new_prod_only_dom / total_new

            cap {
                graph bar (asis) sh_mne_only sh_both sh_dom_only, ///
                    over(year, label(labsize(vsmall) angle(45))) ///
                    bar(1, fcolor($c_MNE)       lcolor($c_MNE)) ///
                    bar(2, fcolor(orange*0.8)   lcolor(orange*0.8)) ///
                    bar(3, fcolor("$c_DOM")     lcolor("$c_DOM")) ///
                    stack ///
                    legend(on order(1 "MNE Only" 2 "MNE & Domestic" 3 "Domestic Only") ///
                           position(6) rows(1) size(small) region(lcolor(white))) ///
                    ytitle("Share of New Products Introduced") ///
                    title("`c': New Product Introduction by Firm Type", size(medium)) ///
                    bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
                export_graph "fig_2_5_newprod_by_type_`c'" "$g25" "$ol_g25"
            }
        restore
    }

* 2.5  EXTENSIVE MARGIN: COUNTRY-PRODUCT LEVEL     [Plan §2 ExtM]
**********************************************************************

*===============================================================
* 2.5.A  Kernel densities (by year)
*===============================================================

use "$int\firm_level_data_full.dta", clear

preserve
    gcollapse (max) new_product_orig new_prod_only_mne new_prod_both ///
              (sum) total_value = value_fob, by(country_orig hs6 year) labelformat(#sourcelabel#)
    bysort country_orig year: egen n_new      = total(new_product_orig)
    bysort country_orig year: egen n_new_mne  = total(new_prod_only_mne)
    bysort country_orig year: egen n_new_both = total(new_prod_both)
    gen sh_new_mne = (n_new_mne + n_new_both) / n_new if n_new > 0
    gen ln_n_new   = ln(n_new) if n_new > 0
    * Collapse to one obs per country-year
    bysort country_orig year: keep if _n == 1

    levelsof year, local(yrs)
    foreach y of local yrs {
        cap {
            kdensity ln_n_new if year == `y', ///
                title("`y'") xtitle("ln(# new products)") lcolor($c_MNE) $gro
            export_graph "fig_2_5_kdens_nnewprod_`y'" "$g25" "$ol_g25"
        }
        cap {
            kdensity sh_new_mne if year == `y', ///
                title("`y'") xtitle("Share new products introduced by MNEs") ///
                lcolor($c_MNE) $gro
            export_graph "fig_2_5_kdens_sh_mne_`y'" "$g25" "$ol_g25"
        }
    }
restore


*===============================================================
* 2.5.B  Regressions: new product introduction (OPY and ODPY)
*===============================================================
*
* Dependent variable: =1 if this is the first year the product
*   appears in the exporting country's (or country-destination's) basket
* Key regressors: new_prod_only_mne (introduced by MNEs only)
*                 new_prod_both (introduced by MNEs and domestic firms)
*
* FIX: programs defined OUTSIDE preserve/restore blocks.
* FIX: removed wrong $p3_controls (is_female, is_male, is_baby, season
*   do not exist in this dataset). Product characteristics sigma and
*   complexity are used as controls instead.
**********************************************************************

* ---- Program: OPY new-product regressions ----
capture program drop run_newprod_opy
program define run_newprod_opy
    args keepvars filename

    * Col 1: OP + Year
    reghdfe new_product_orig `keepvars', absorb(op_id year) vce(cluster op_id)
    outreg2 using "$r_s2\\`filename'.tex", replace tex(frag) label ctitle("OP + Year") ///
        keep(`keepvars') ///
        addtext(OP FE, Yes, OT FE, No, PT FE, No, Interactions, No) ///
        dec(4) nocons

    * Col 2: OP + OxT
    reghdfe new_product_orig `keepvars', absorb(op_id ot_id) vce(cluster op_id)
    outreg2 using "$r_s2\\`filename'.tex", append tex(frag) label ctitle("OP + OxT") ///
        keep(`keepvars') ///
        addtext(OP FE, Yes, OT FE, Yes, PT FE, No, Interactions, No) ///
        dec(4) nocons

    * Col 3: OP + OxT + PxT
    reghdfe new_product_orig `keepvars', absorb(op_id ot_id pt_id) vce(cluster op_id)
    outreg2 using "$r_s2\\`filename'.tex", append tex(frag) label ctitle("OP + OxT + PxT") ///
        keep(`keepvars') ///
        addtext(OP FE, Yes, OT FE, Yes, PT FE, Yes, Interactions, No) ///
        dec(4) nocons

    * Col 4: OxT + upstreamness interaction
    reghdfe new_product_orig `keepvars' only_mne_X_upsm both_X_upsm upstreamness, ///
        absorb(op_id ot_id) vce(cluster op_id)
    outreg2 using "$r_s2\\`filename'.tex", append tex(frag) label ctitle("x Upstream") ///
        keep(`keepvars' only_mne_X_upsm both_X_upsm upstreamness) ///
        addtext(OP FE, Yes, OT FE, Yes, PT FE, No, Interactions, Upstream) ///
        dec(4) nocons

    copy "$r_s2\\`filename'.tex" "$ol_r_s2\\`filename'.tex", replace
end


* ---- Program: ODPY new-product regressions ----
capture program drop run_newprod_odpy
program define run_newprod_odpy
    args keepvars filename

    * Col 1: ODP + Year
    reghdfe new_product_od `keepvars', absorb(odp_id year) vce(cluster odp_id)
    outreg2 using "$r_s2\\`filename'.tex", replace tex(frag) label ctitle("ODP + Year") ///
        keep(`keepvars') ///
        addtext(ODP FE, Yes, OT FE, No, DT FE, No, PT FE, No, Interactions, No) ///
        dec(4) nocons

    * Col 2: ODP + OxT + DxT
    reghdfe new_product_od `keepvars', absorb(odp_id ot_id dt_id) vce(cluster odp_id)
    outreg2 using "$r_s2\\`filename'.tex", append tex(frag) label ctitle("ODP + OxT + DxT") ///
        keep(`keepvars') ///
        addtext(ODP FE, Yes, OT FE, Yes, DT FE, Yes, PT FE, No, Interactions, No) ///
        dec(4) nocons

    * Col 3: ODP + OxT + DxT + PxT
    reghdfe new_product_od `keepvars', absorb(odp_id ot_id dt_id pt_id) vce(cluster odp_id)
    outreg2 using "$r_s2\\`filename'.tex", append tex(frag) label ctitle("ODP + OxT + DxT + PxT") ///
        keep(`keepvars') ///
        addtext(ODP FE, Yes, OT FE, Yes, DT FE, Yes, PT FE, Yes, Interactions, No) ///
        dec(4) nocons

    * Col 4: OxT + DxT + distance interaction
    reghdfe new_product_od `keepvars' only_mne_X_lndist both_X_lndist ln_dist, ///
        absorb(odp_id ot_id dt_id) vce(cluster odp_id)
    outreg2 using "$r_s2\\`filename'.tex", append tex(frag) label ctitle("x Distance") ///
        keep(`keepvars' only_mne_X_lndist both_X_lndist ln_dist) ///
        addtext(ODP FE, Yes, OT FE, Yes, DT FE, Yes, PT FE, No, Interactions, Dist) ///
        dec(4) nocons

    * Col 5: OxT + DxT + upstreamness interaction
    reghdfe new_product_od `keepvars' only_mne_X_upsm both_X_upsm upstreamness, ///
        absorb(odp_id ot_id dt_id) vce(cluster odp_id)
    outreg2 using "$r_s2\\`filename'.tex", append tex(frag) label ctitle("x Upstream") ///
        keep(`keepvars' only_mne_X_upsm both_X_upsm upstreamness) ///
        addtext(ODP FE, Yes, OT FE, Yes, DT FE, Yes, PT FE, No, Interactions, Upstream) ///
        dec(4) nocons

    copy "$r_s2\\`filename'.tex" "$ol_r_s2\\`filename'.tex", replace
end


* --- OPY: origin-product-year new product regressions ---
use "$int\firm_level_data_full.dta", clear

preserve
    gcollapse (max) new_product_orig new_prod_only_mne new_prod_both ///
              (firstnm) upstreamness sigma complexity, ///
              by(country_orig hs6 year) labelformat(#sourcelabel#)

    replace new_prod_only_mne = 0 if missing(new_prod_only_mne)
    replace new_prod_both     = 0 if missing(new_prod_both)

    * Fixed-effect group IDs
    egen op_id = group(country_orig hs6)
    egen ot_id = group(country_orig year)
    egen pt_id = group(hs6 year)

    * Interaction terms (upstreamness interacted with MNE-introduction dummies)
    gen only_mne_X_upsm = new_prod_only_mne * upstreamness
    gen both_X_upsm     = new_prod_both     * upstreamness

    run_newprod_opy "new_prod_only_mne new_prod_both" "reg_2_5_newprod_opy"
restore


* --- ODPY: origin-destination-product-year new product regressions ---
use "$int\firm_level_data_full.dta", clear

preserve
    gcollapse (max) new_product_od new_prod_only_mne_od new_prod_both_od ///
              (firstnm) ln_dist contig fta_wto upstreamness sigma complexity, ///
              by(country_orig country_dest hs6 year) labelformat(#sourcelabel#)

    replace new_prod_only_mne_od = 0 if missing(new_prod_only_mne_od)
    replace new_prod_both_od     = 0 if missing(new_prod_both_od)

    * Fixed-effect group IDs
    egen odp_id = group(country_orig country_dest hs6)
    egen ot_id  = group(country_orig year)
    egen dt_id  = group(country_dest year)
    egen pt_id  = group(hs6 year)

    * Interaction terms
    gen only_mne_X_lndist = new_prod_only_mne_od * ln_dist
    gen both_X_lndist     = new_prod_both_od     * ln_dist
    gen only_mne_X_upsm   = new_prod_only_mne_od * upstreamness
    gen both_X_upsm       = new_prod_both_od     * upstreamness

    run_newprod_odpy "new_prod_only_mne_od new_prod_both_od" "reg_2_5_newprod_odpy"
restore


**********************************************************************
* 2.6  EXTENSIVE MARGIN: FIRM LEVEL               [Plan §2 ExtFirm]
**********************************************************************

* FIX: programs defined at the global scope (outside preserve/restore).
* FIX: all three programs reference $r_s2 directly.

* ---- Program 1: Firm-Year level ----
capture program drop run_firm_level
program define run_firm_level
    args mnevar filename

    local dep_firm "ln_firm_exports ln_n_destinations ln_exp_per_dest ln_n_products ln_exp_per_prod ln_avg_dist"
    local first = 1

    foreach dv of local dep_firm {   // FIX: foreach loop closed with }, not end

        * Without controlling for firm size
        reghdfe `dv' `mnevar', absorb(orig_id year) vce(cluster orig_id)
        if `first' == 1 {
            outreg2 using "$r_s2\\`filename'.tex", replace tex(frag) ///
                ctitle("No Size: O+T") keep(`mnevar') dec(4) nocons
            local first = 0
        }
        else {
            outreg2 using "$r_s2\\`filename'.tex", append tex(frag) ///
                ctitle("No Size: O+T") keep(`mnevar') dec(4) nocons
        }

        reghdfe `dv' `mnevar', absorb(ot_id) vce(cluster orig_id)
        outreg2 using "$r_s2\\`filename'.tex", append tex(frag) ///
            ctitle("No Size: OxT") keep(`mnevar') dec(4) nocons

        reghdfe `dv' `mnevar', absorb(ot_id sector_id) vce(cluster orig_id)
        outreg2 using "$r_s2\\`filename'.tex", append tex(frag) ///
            ctitle("No Size: OxT+Sect") keep(`mnevar') dec(4) nocons

        * With firm size control (skip when DV is firm exports itself)
        if "`dv'" != "ln_firm_exports" {
            reghdfe `dv' `mnevar' ln_firm_exports, ///
                absorb(orig_id year) vce(cluster orig_id)
            outreg2 using "$r_s2\\`filename'.tex", append tex(frag) ///
                ctitle("+Size: O+T") keep(`mnevar' ln_firm_exports) dec(4) nocons

            reghdfe `dv' `mnevar' ln_firm_exports, ///
                absorb(ot_id) vce(cluster orig_id)
            outreg2 using "$r_s2\\`filename'.tex", append tex(frag) ///
                ctitle("+Size: OxT") keep(`mnevar' ln_firm_exports) dec(4) nocons

            reghdfe `dv' `mnevar' ln_firm_exports, ///
                absorb(ot_id sector_id) vce(cluster orig_id)
            outreg2 using "$r_s2\\`filename'.tex", append tex(frag) ///
                ctitle("+Size: OxT+Sect") keep(`mnevar' ln_firm_exports) dec(4) nocons
        }
    }   // FIX: was `end` (closed program prematurely); now correctly closes foreach
end


* ---- Program 2: Firm-Destination-Year level ----
capture program drop run_fmd_level
program define run_fmd_level
    args mnevar filename

    reghdfe ln_exports `mnevar', absorb(ot_id dest_id) vce(cluster od_id)
    outreg2 using "$r_s2\\`filename'.tex", replace tex(frag) ///
        ctitle("No Size: OxT+Dest") keep(`mnevar') dec(4) nocons

    reghdfe ln_exports `mnevar' ln_total_firm_exp, ///
        absorb(ot_id dest_id) vce(cluster od_id)
    outreg2 using "$r_s2\\`filename'.tex", append tex(frag) ///
        ctitle("+Size: OxT+Dest") keep(`mnevar' ln_total_firm_exp) dec(4) nocons

    reghdfe ln_exports `mnevar', absorb(ot_id dt_id) vce(cluster od_id)
    outreg2 using "$r_s2\\`filename'.tex", append tex(frag) ///
        ctitle("No Size: OxT+DxT") keep(`mnevar') dec(4) nocons

    reghdfe ln_exports `mnevar' ln_total_firm_exp, ///
        absorb(ot_id dt_id) vce(cluster od_id)
    outreg2 using "$r_s2\\`filename'.tex", append tex(frag) ///
        ctitle("+Size: OxT+DxT") keep(`mnevar' ln_total_firm_exp) dec(4) nocons
end


* ---- Program 3: Firm-Product-Year level ----
capture program drop run_fmp_level
program define run_fmp_level
    args mnevar filename

    reghdfe ln_firm_prod_exports `mnevar', ///
        absorb(ot_id prod_id) vce(cluster ot_id)
    outreg2 using "$r_s2\\`filename'.tex", replace tex(frag) ///
        ctitle("Exports (OxT+Prod)") keep(`mnevar') dec(4) nocons

    reghdfe ln_n_destinations `mnevar', ///
        absorb(ot_id prod_id) vce(cluster ot_id)
    outreg2 using "$r_s2\\`filename'.tex", append tex(frag) ///
        ctitle("Destinations (OxT+Prod)") keep(`mnevar') dec(4) nocons
end


* ---- Main loop: run all three firm-level programs ----
foreach mne_def in ext total {
    if "`mne_def'" == "ext"   local mne_d "MNE"
    if "`mne_def'" == "dom"   local mne_d "MNE_dom"
    if "`mne_def'" == "total" local mne_d "MNE_total"

    * --- Firm-Year ---
    use "$int\firm_year_level.dta", clear
    cap confirm variable `mne_d'
    if _rc != 0 {
        di as error "Variable `mne_d' not found in firm_year_level.dta — skipping `mne_def'"
        continue
    }
    run_firm_level "`mne_d'" "reg_2_6_firm_`mne_def'"

    * --- Firm-Destination-Year ---
    use "$int\firm_dest_year_level.dta", clear
    merge m:1 firm_id year using "$int\firm_year_level.dta", ///
        keepusing(ln_firm_exports) keep(1 3) nogen
    rename ln_firm_exports ln_total_firm_exp
    run_fmd_level "`mne_d'" "reg_2_6_fmd_`mne_def'"

    * --- Firm-Product-Year ---
    use "$int\firm_level_data_full.dta", clear
    preserve
        bysort firm_id year: egen n_destinations_fp = nvals(country_dest)

        gcollapse (sum) firm_prod_exports = value_fob ///
                  (firstnm) `mne_d' hs_section n_destinations_fp, ///
                  by(firm_id country_orig hs6 year) labelformat(#sourcelabel#)

        gen ln_firm_prod_exports = ln(firm_prod_exports)
        gen ln_n_destinations    = ln(n_destinations_fp)

        egen ot_id   = group(country_orig year)
        egen prod_id = group(hs6)

        run_fmp_level "`mne_d'" "reg_2_6_fmp_`mne_def'"
    restore

    * Copy all three tables to Overleaf
    foreach stem in "reg_2_6_firm" "reg_2_6_fmd" "reg_2_6_fmp" {
        copy "$r_s2\\`stem'_`mne_def'.tex" ///
             "$ol_r_s2\\`stem'_`mne_def'.tex", replace
    }
}


**********************************************************************
**********************************************************************
*
*   PART 3: SUMMARY STATISTICS
*
**********************************************************************
**********************************************************************

* --- Table 3.1: Key statistics by origin country (averaged over years) ---
* NOTE: estpost tabstat with by() stores one row per group. esttab then
*   produces a table with one panel per country. Check estout version
*   compatibility if output is not as expected.
use "$int\firm_level_data.dta", clear

preserve
    gcollapse ///
        (sum)   total_value = value_fob ///
        (count) n_obs       = value_fob ///
        (sum)   n_mne       = MNE_ext  n_dom = DOM_ext ///
                n_mne_dom   = MNE_dom  n_mne_total = MNE_total, ///
        by(country_orig year) labelformat(#sourcelabel#)
    * Average over years, then tabulate by country
    gcollapse (mean) total_value n_obs n_mne n_dom n_mne_dom n_mne_total, ///
        by(country_orig) labelformat(#sourcelabel#)
    estpost tabstat total_value n_obs n_mne n_dom n_mne_dom n_mne_total, ///
        statistics(mean sd min max) columns(statistics)
    esttab using "$t_s3\tab_3_1_sumstats_country.tex", replace ///
        cells("mean(fmt(%12.0fc)) sd(fmt(%12.0fc)) min(fmt(%12.0fc)) max(fmt(%12.0fc))") ///
        nomtitle nonumber label
    copy "$t_s3\tab_3_1_sumstats_country.tex" ///
         "$ol_t_s3\tab_3_1_sumstats_country.tex", replace
restore


* --- Table 3.2: Summary statistics of main ODY regression variables ---
use "$int\collapsed_ody.dta", clear

estpost sum share_mne_value share_ext_nfirms share_dom_nfirms share_total_nfirms ///
            total_value n_firms ln_total_value ln_dist contig fta_wto, d
esttab using "$t_s3\tab_3_2_sumstats_ody.tex", replace ///
    cells("mean(fmt(%9.3f)) sd(fmt(%9.3f)) p50(fmt(%9.3f)) min(fmt(%9.3f)) max(fmt(%9.3f)) count(fmt(%12.0fc))") ///
    nomtitle nonumber label
copy "$t_s3\tab_3_2_sumstats_ody.tex" "$ol_t_s3\tab_3_2_sumstats_ody.tex", replace


* --- Table 3.3: Summary statistics of main ODPY regression variables ---
use "$int\collapsed_odpy.dta", clear

estpost sum share_mne_value share_ext_nfirms share_dom_nfirms share_total_nfirms ///
            total_value n_firms ln_total_value ln_dist contig fta_wto ///
            upstreamness sigma complexity quality_ladder rca, d
esttab using "$t_s3\tab_3_3_sumstats_odpy.tex", replace ///
    cells("mean(fmt(%9.3f)) sd(fmt(%9.3f)) p50(fmt(%9.3f)) min(fmt(%9.3f)) max(fmt(%9.3f)) count(fmt(%12.0fc))") ///
    nomtitle nonumber label
copy "$t_s3\tab_3_3_sumstats_odpy.tex" "$ol_t_s3\tab_3_3_sumstats_odpy.tex", replace


* --- Table 3.5: Correlation matrix — product characteristics × MNE share ---
* Motivation table for §1.3 regressions. Shows collinearity among
* product characteristics so referee understands multi-collinearity risk.

use "$int\collapsed_opy.dta", clear

* pwcorr with star significance
estpost correlate share_mne_value upstreamness sigma complexity ///
               quality_ladder rca rhci, star(0.05)
estpost correlate share_mne_value upstreamness sigma complexity ///
               quality_ladder rca rhci, matrix elabels(( ))		
esttab using "$t_s3\tab_3_5_prodchar_corr.tex", not unstack compress noobs replace ///
    note("* p<0.05. Correlation of MNE share and product characteristics.") ///
    title("Correlation: MNE Share and Product Characteristics")
   
copy "$t_s3\tab_3_5_prodchar_corr.tex" "$ol_t_s3\tab_3_5_prodchar_corr.tex", replace



**********************************************************************
* COMPLETION MESSAGE
**********************************************************************

di as text ""
di as text "==========================================================="
di as text "  ALL ANALYSES COMPLETED SUCCESSFULLY"
di as text "==========================================================="
di as text "  Graphs  (local)    -> $graphs"
di as text "  Graphs  (Overleaf) -> $overleaf\Graphs"
di as text "  Tables  (local)    -> $tables"
di as text "  Tables  (Overleaf) -> $overleaf\Tables"
di as text "  Regressions(local) -> $regs"
di as text "  Regressions(Ovlf)  -> $overleaf\Regressions"
di as text "  Parent Ctry (local)  -> $g14"
di as text "  Parent Ctry (Overleaf) -> $ol_g14"
di as text "  Concentration (local)  -> $g24"
di as text "  Concentration (Ovlf)   -> $ol_g24"
di as text "==========================================================="
