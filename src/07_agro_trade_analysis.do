/*==============================================================================
  07_agro_trade_analysis.do

  PURPOSE:
    Descriptive and econometric analysis of MNE participation in LAC
    agricultural exports (HS2 chapters 1-24 only).

    Mirrors the structure of 06_trade_analysis.do but restricted to
    agricultural products. Adds an agricultural deep-dive section (Part 1.5)
    that disaggregates by HS agricultural section.

  INPUTS:
    $raw\Base_final_Customs_DNB_Orbis_product_complete.dta  (from script 01)
    Gravity and product characteristics files in $agro_root\Data

  OUTPUTS:
    Graphs  → $agro_root\Output\Graphs\...
    Tables  → $agro_root\Output\Tables\...
    Regs    → $agro_root\Output\Regressions\...

  AUTHOR: Sebastian Velasquez (IDB)

  LAST UPDATED: March 2026
==============================================================================*/

**********************************************************************
*
* Multinational Firms and Agricultural Trade
* Restricted to HS 2-digit chapters 1-24 (Sections I-IV)
*
* Author:   Sebastian Velasquez (IDB)
*
* Last Version: April 2026
* Based on: MNE_Trade_Analysis_corrected_v3.do
*
* AGRICULTURAL HS SECTIONS:
*   Section I   (HS 01-05) : Live Animals & Animal Products
*   Section II  (HS 06-14) : Vegetable Products
*   Section III (HS 15)    : Animal & Vegetable Fats & Oils
*   Section IV  (HS 16-24) : Prepared Foodstuffs, Beverages & Tobacco
*
* TABLE OF CONTENTS
* -----------------
* Part 0 : Data preparation (agro-filtered)
*   0.1  Load raw data
*   0.2  Three MNE definitions
*   0.3  Firm identifier
*   0.4  Product variables + AGRO FILTER (keep HS2 1-24)
*   0.5  Merge product characteristics
*   0.6  Merge gravity & country characteristics
*   0.7  Destination country categories
*   0.8  MNE corporate network variables
*   0.9  Collapse to analytical samples
*   0.10 Concentration measures
*   0.11 Extensive margin variables
*   0.12 Firm-year level aggregates
*
* Part 1 : Determinants of MNE presence
*   1.1  Across exporting countries (trends + firm profile)
*   1.2  Across destination countries
*   1.3  By product
*   1.4  Parent country analysis
*   1.5  [AGRO-NEW] Agricultural section deep-dive
*
* Part 2 : Effects of MNE presence
*   2.1  Aggregate regressions
*   2.2  Gravity regressions
*   2.3  MNE network regressions
*   2.4  Concentration patterns
*   2.5  Extensive margin: country-product
*   2.6  Extensive margin: firm level
*
* Part 3 : Summary statistics
*
**********************************************************************

clear all
set more off
graph set window fontface "Times New Roman"


**********************************************************************
* DIRECTORIES & FOLDER STRUCTURE
**********************************************************************

* Original root (for raw data only)
global root     "C:\Sebas BID\Orbis_DNB_Customs_Final"
global raw      "$root\data\raw"

* Agro-specific root — ALL output and intermediate data go here
global agro_root "$root\agro"

global agro_data "$agro_root\Data"
global int       "$agro_data\Intermediate"

* Output roots
global output   "$agro_root\Output"
global graphs   "$output\Graphs"
global tables   "$output\Tables"
global regs     "$output\Regressions"

* Graph sub-folders
global g11    "$graphs\1_1_ExportingCountries"
global g12    "$graphs\1_2_DestinationCountries"
global g13    "$graphs\1_3_ByProduct"
global g14    "$graphs\1_4_ParentCountries"
global g15    "$graphs\1_5_AgroSections"
global g25    "$graphs\2_5_ExtensiveMargin"
global g11_tr "$graphs\1_1_Trends"
global g11_fp "$graphs\1_1_FirmProfile"
global g24    "$graphs\2_4_Concentration"

* Table sub-folders
global t_s1  "$tables\S1_Determinants"
global t_s2  "$tables\S2_Effects"
global t_s3  "$tables\S3_Summary"

* Regression sub-folders
global r_s1  "$regs\S1_Determinants"
global r_s2  "$regs\S2_Effects"

* Overleaf mirror
global overleaf   "$agro_root\Overleaf"
global ol_g11     "$overleaf\Graphs\1_1_ExportingCountries"
global ol_g12     "$overleaf\Graphs\1_2_DestinationCountries"
global ol_g13     "$overleaf\Graphs\1_3_ByProduct"
global ol_g14     "$overleaf\Graphs\1_4_ParentCountries"
global ol_g15     "$overleaf\Graphs\1_5_AgroSections"
global ol_g25     "$overleaf\Graphs\2_5_ExtensiveMargin"
global ol_g11_tr  "$overleaf\Graphs\1_1_Trends"
global ol_g11_fp  "$overleaf\Graphs\1_1_FirmProfile"
global ol_g24     "$overleaf\Graphs\2_4_Concentration"
global ol_t_s1    "$overleaf\Tables\S1_Determinants"
global ol_t_s2    "$overleaf\Tables\S2_Effects"
global ol_t_s3    "$overleaf\Tables\S3_Summary"
global ol_r_s1    "$overleaf\Regressions\S1_Determinants"
global ol_r_s2    "$overleaf\Regressions\S2_Effects"

* Create all directories
foreach dir in ///
    "$agro_root" "$agro_data" "$int" ///
    "$output" "$graphs" "$tables" "$regs" ///
    "$g11" "$g12" "$g13" "$g14" "$g15" "$g25" ///
    "$g11_tr" "$g11_fp" "$g24" ///
    "$t_s1" "$t_s2" "$t_s3" ///
    "$r_s1" "$r_s2" ///
    "$overleaf" ///
    "$overleaf\Graphs" "$overleaf\Tables" "$overleaf\Regressions" ///
    "$ol_g11" "$ol_g12" "$ol_g13" "$ol_g14" "$ol_g15" "$ol_g25" ///
    "$ol_g11_tr" "$ol_g11_fp" "$ol_g24" ///
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
global c_MNEtot    "green*0.7"

* Agro section colours (muted earthy palette)
global c_s1 "brown*0.9"
global c_s2 "green*0.8"
global c_s3 "orange*0.9"
global c_s4 "blue*0.7"

global gro `"graphregion(fcolor(white) lwidth(none) lpattern(blank)) plotregion(fcolor(white) lwidth(none) lpattern(blank))"'


**********************************************************************
* FIXED-EFFECT SYSTEM
* All FE specs are globals — locals are NOT visible inside program
* definitions and would silently produce empty strings.
**********************************************************************

* ---- (A) Standard 7-spec ladder (ODY / firm-level) ----
global fe1  ""
global fe2  "year"
global fe3  "orig_id year"
global fe4  "orig_id dest_id year"
global fe5  "ot_id dt_id"
global fe6  "od_id year"
global fe7  "ot_id dt_id od_id"

global fel1 "No FE"
global fel2 "Year"
global fel3 "O + Year"
global fel4 "O + D + Year"
global fel5 "OxT + DxT"
global fel6 "OD x Year"
global fel7 "OxT + DxT + OD"

* ---- (B) OPY 8-spec ladder ----
global nfe_opy = 8

global fe_opy1  ""
global fe_opy2  "year"
global fe_opy3  "orig_id year"
global fe_opy4  "ot_id"
global fe_opy5  "pt_id"
global fe_opy6  "ot_id pt_id"
global fe_opy7  "op_id year"
global fe_opy8  "op_id ot_id"

global fel_opy1 "No FE"
global fel_opy2 "Year"
global fel_opy3 "O + Year"
global fel_opy4 "OxT"
global fel_opy5 "PxT"
global fel_opy6 "OxT + PxT"
global fel_opy7 "OP x Year"
global fel_opy8 "OP + OxT"

* ---- (C) ODPY 9-spec ladder ----
global nfe_odpy = 9

global fe_odpy1  ""
global fe_odpy2  "year"
global fe_odpy3  "orig_id year"
global fe_odpy4  "orig_id dest_id year"
global fe_odpy5  "ot_id dt_id"
global fe_odpy6  "od_id year"
global fe_odpy7  "ot_id dt_id od_id"
global fe_odpy8  "odp_id year"
global fe_odpy9  "odp_id ot_id dt_id"

global fel_odpy1 "No FE"
global fel_odpy2 "Year"
global fel_odpy3 "O + Year"
global fel_odpy4 "O + D + Year"
global fel_odpy5 "OxT + DxT"
global fel_odpy6 "OD x Year"
global fel_odpy7 "OxT + DxT + OD"
global fel_odpy8 "ODP x Year"
global fel_odpy9 "ODP + OxT + DxT"


**********************************************************************
* HELPER PROGRAMS
**********************************************************************

* ---- Graph export (PDF + PNG + EPS, local + Overleaf) ----
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
*   Filter to HS2 1-24 before all merges and collapses.
*   All intermediate .dta files saved under $int (Agro folder).
*
**********************************************************************
**********************************************************************


*----------------------------------------------------------------------
* 0.1  Load raw data
*----------------------------------------------------------------------
use "$raw\Base_final_Customs_DNB_Orbis_product_complete.dta", clear


*----------------------------------------------------------------------
* 0.2  Three MNE definitions
*----------------------------------------------------------------------

gen byte MNE_ext   = (_merge_final_review == 3) & (iso3_parent != "") ///
                   & (iso3_parent != country_orig)
gen byte DOM_ext   = 1 - MNE_ext

gen byte MNE_dom   = (_merge_final_review == 3) & (iso3_parent == country_orig)
gen byte DOM_dom   = 1 - MNE_dom

gen byte MNE_total = (_merge_final_review == 3)
gen byte DOM_total = 1 - MNE_total

gen byte MNE = MNE_ext
gen byte DOM = DOM_ext

label var MNE_ext   "=1 if foreign subsidiary (parent != exporting country)"
label var DOM_ext   "=1 if not a foreign subsidiary"
label var MNE_dom   "=1 if domestic MNE (parent = exporting country)"
label var DOM_dom   "=1 if not a domestic MNE"
label var MNE_total "=1 if any MNE (ext OR dom)"
label var DOM_total "=1 if not matched in corporate database"
label var MNE       "=1 if MNE (baseline alias = MNE_ext)"
label var DOM       "=1 if domestic (baseline alias = DOM_ext)"


*----------------------------------------------------------------------
* 0.3  Firm identifier
*----------------------------------------------------------------------
egen firm_id = group(country_orig Tax_ID)
label var firm_id "Unique firm identifier (country_orig x Tax_ID)"


*----------------------------------------------------------------------
* 0.4  Product variables + AGRO FILTER
*----------------------------------------------------------------------
gen hs6 = hs07_6d
label var hs6 "HS 2007, 6-digit"
gen hs2 = substr(hs6, 1, 2)
label var hs2 "HS 2-digit chapter"
destring hs6 hs2, replace

* === AGRO FILTER: keep only chapters 1-24 ===
keep if inrange(hs2, 1, 24)
di as text "Agro filter applied: kept HS2 chapters 1-24 only."

* Agro section classification (HS Sections I-IV)
gen byte hs_section = .
replace hs_section = 1 if inrange(hs2,  1,  5)   // I:   Live Animals & Products
replace hs_section = 2 if inrange(hs2,  6, 14)   // II:  Vegetable Products
replace hs_section = 3 if hs2 == 15               // III: Fats & Oils
replace hs_section = 4 if inrange(hs2, 16, 24)   // IV:  Food, Beverages & Tobacco
label var hs_section "Agro HS Section (I-IV)"

label define agro_sect_lbl ///
    1 "I: Live Animals" ///
    2 "II: Vegetables"  ///
    3 "III: Fats & Oils" ///
    4 "IV: Food & Bev."
label values hs_section agro_sect_lbl

* HS2 chapter labels (for chapter-level graphs)
label define hs2_lbl ///
     1 "01 Live animals"       2 "02 Meat"             3 "03 Fish" ///
     4 "04 Dairy & eggs"       5 "05 Animal prods"     6 "06 Live trees" ///
     7 "07 Vegetables"         8 "08 Fruit & nuts"     9 "09 Coffee & spices" ///
    10 "10 Cereals"           11 "11 Milling prods"   12 "12 Oil seeds" ///
    13 "13 Gums & resins"     14 "14 Veg. plaiting"   15 "15 Fats & oils" ///
    16 "16 Meat/fish prep."   17 "17 Sugars"          18 "18 Cocoa" ///
    19 "19 Cereal preps."     20 "20 Veg. preps."     21 "21 Misc. food" ///
    22 "22 Beverages"         23 "23 Feed residues"   24 "24 Tobacco"
label values hs2 hs2_lbl


*----------------------------------------------------------------------
* 0.5  Merge product characteristics
*----------------------------------------------------------------------

* HS code harmonisation (relevant codes for agro chapters only)
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

* NOTE: Copy all remaining harmonisation lines from v3 §0.5 here
* (only the subset relevant to HS2 1-24 matters; the rest will not match)

* Merge product characteristics (upstreamness, sigma, complexity, etc.)
merge m:1 hs07_6d using "$root\Data\Intermediate\product_characteristics.dta", ///
    keep(1 3) nogen

* Above-median dummies for product characteristics
foreach v in upstreamness sigma complexity quality_ladder rca rhci {
    cap {
        sum `v', detail
        gen byte `v'_abovemed = (`v' > r(p50)) if !missing(`v')
        label var `v'_abovemed "Above median `v'"
    }
}

* Decile dummies
foreach v in upstreamness sigma complexity quality_ladder rca rhci {
    cap {
        xtile `v'_decile = `v', nq(10)
        label var `v'_decile "Decile of `v'"
    }
}

* Lall 2000 and IPC patent variables (may exist as tech_lall2000 / tech_ipc1)
cap rename tech_lall2000 lall2000
cap rename tech_ipc1     ipc1
cap {
    sum lall2000, detail
    gen byte lall2000_abovemed = (lall2000 > r(p50)) if !missing(lall2000)
    sum ipc1, detail
    gen byte ipc1_abovemed = (ipc1 > r(p50)) if !missing(ipc1)
}


*----------------------------------------------------------------------
* 0.6  Merge gravity & country characteristics
*----------------------------------------------------------------------
merge m:1 country_orig country_dest year using ///
    "$root\Data\Intermediate\gravity_bilateral.dta", keep(1 3) nogen

* Log transforms
cap gen ln_gdp_o    = ln(gdp_o)
cap gen ln_gdpcap_o = ln(gdpcap_o)
cap gen ln_pop_o    = ln(pop_o)
cap gen ln_gdp_d    = ln(gdp_d)
cap gen ln_gdpcap_d = ln(gdpcap_d)
cap gen ln_pop_d    = ln(pop_d)
cap gen ln_dist     = ln(dist)

* Tariffs
cap merge m:1 country_orig country_dest hs6 year using ///
    "$root\Data\Intermediate\teti_tariffs.dta", keep(1 3) nogen
cap label var avg_tariff "Average bilateral tariff"

* Income groups
cap label define income_group 1 "Low" 2 "Lower-Mid" 3 "Upper-Mid" 4 "High", replace
cap label values income_group_dest income_group

* Distance above median
cap sum dist, detail
cap gen byte dist_above_med = (dist > r(p50)) if !missing(dist)

* PTA / BIT / DTT
foreach v in PTA BIT DTT {
    cap confirm variable `v'
    if _rc != 0 gen byte `v' = 0
}


*----------------------------------------------------------------------
* 0.7  Destination country categories
*----------------------------------------------------------------------

gen byte LAC_dest  = 0
gen byte non_contig = 1 - contig

* LAC destinations (same mapping as v3)
replace LAC_dest = 1 if inlist(country_dest,"ARG","BHS","BRB","BLZ","BOL")
replace LAC_dest = 1 if inlist(country_dest,"BRA","CHL","COL","CRI","DOM")
replace LAC_dest = 1 if inlist(country_dest,"ECU","SLV","GTM","GUY","HTI")
replace LAC_dest = 1 if inlist(country_dest,"HND","JAM","MEX","NIC","PAN")
replace LAC_dest = 1 if inlist(country_dest,"PRY","PER","SUR","TTO","URY","VEN")

gen byte intra_regional = (LAC_dest == 1)
label var intra_regional "=1 if destination is in LAC"

* Destination region (string, then encode)
gen dest_region = ""
replace dest_region = "LAC"    if LAC_dest == 1
replace dest_region = "North America" if inlist(country_dest,"USA","CAN")
replace dest_region = "Europe" if inlist(country_dest,"AUT","BEL","BGR","CYP","CZE")
replace dest_region = "Europe" if inlist(country_dest,"DNK","EST","FIN","FRA","DEU")
replace dest_region = "Europe" if inlist(country_dest,"GRC","HUN","IRL","ITA","LVA")
replace dest_region = "Europe" if inlist(country_dest,"LTU","LUX","MLT","NLD","POL")
replace dest_region = "Europe" if inlist(country_dest,"PRT","ROU","SVK","SVN","ESP")
replace dest_region = "Europe" if inlist(country_dest,"SWE","GBR","NOR","CHE")
replace dest_region = "Asia"   if inlist(country_dest,"CHN","HKG","IND","IDN","JPN")
replace dest_region = "Asia"   if inlist(country_dest,"MYS","PHL","KOR","SGP","TWN","THA","VNM")
replace dest_region = "Africa" if inlist(country_dest,"DZA","AGO","BEN","BWA","BFA")
replace dest_region = "Africa" if inlist(country_dest,"CMR","CPV","CAF","TCD","COM")
replace dest_region = "Africa" if inlist(country_dest,"COD","COG","CIV","DJI","EGY")
replace dest_region = "Africa" if inlist(country_dest,"GNQ","ERI","ETH","GAB","GMB")
replace dest_region = "Africa" if inlist(country_dest,"GHA","GIN","GNB","KEN","LSO")
replace dest_region = "Africa" if inlist(country_dest,"LBR","LBY","MDG","MWI","MLI")
replace dest_region = "Africa" if inlist(country_dest,"MRT","MUS","MAR","MOZ","NAM")
replace dest_region = "Africa" if inlist(country_dest,"NER","NGA","RWA","STP","SEN")
replace dest_region = "Africa" if inlist(country_dest,"SYC","SLE","SOM","ZAF","SSD")
replace dest_region = "Africa" if inlist(country_dest,"SDN","SWZ","TZA","TGO","TUN","UGA","ZMB","ZWE")
replace dest_region = "Rest of World" if dest_region == ""
encode dest_region, gen(dest_region_num)

label define intra_lbl  0 "Extra-regional" 1 "Intra-regional (LAC)", replace
label define contig_lbl 0 "Non-Contiguous" 1 "Contiguous", replace
label define distmed_lbl 0 "Below Median"  1 "Above Median", replace
label values intra_regional intra_lbl
label values contig         contig_lbl
label values dist_above_med distmed_lbl


*----------------------------------------------------------------------
* 0.8  MNE corporate network variables
*----------------------------------------------------------------------

gen country_hq   = iso3_parent
gen home_country = iso3_parent if MNE == 1
label var home_country "Home country of MNE parent"

merge m:1 ID_Orbis_DNB country_dest using ///
    "$root\Data\Intermediate\intermediate_mne_presence.dta", keep(1 3) nogen

gen byte MNE_HQ_dest         = (MNE == 1 & country_hq == country_dest)
gen byte MNE_aff_dest        = (MNE == 1 & company_has_aff_in_dest == 1)
gen byte MNE_present_dest    = (MNE_HQ_dest == 1 | MNE_aff_dest == 1)
gen byte MNE_notpresent_dest = (MNE == 1 & MNE_present_dest == 0)
gen byte MNE_neighbor_dest   = (MNE == 1 & MNE_present_dest == 0 ///
                               & company_has_aff_in_neighbor == 1)

label var MNE_HQ_dest         "MNE: HQ is in the destination"
label var MNE_aff_dest        "MNE: affiliate at the destination"
label var MNE_present_dest    "MNE: any network presence at destination"
label var MNE_notpresent_dest "MNE: no network presence at destination"
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
label values hs_section agro_sect_lbl
label values hs2 hs2_lbl

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
gen byte positive_trade = 1
cap label values income_group_dest income_group

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
label values hs_section agro_sect_lbl
label values hs2 hs2_lbl

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
* 0.10  Concentration measures (top-k exporter shares) — AGRO only
*----------------------------------------------------------------------

* --- ODY level ---
use "$int\firm_level_data.dta", clear

bysort country_orig country_dest year: egen double tot_ody = total(value_fob)
gen firm_sh_ody = value_fob / tot_ody
gsort country_orig country_dest year -value_fob
bysort country_orig country_dest year: gen rank_ody = _n

bysort country_orig country_dest year: ///
    egen share_top1_all = total(firm_sh_ody * (rank_ody == 1))
bysort country_orig country_dest year: ///
    egen share_top3_all = total(firm_sh_ody * (rank_ody <= 3))
bysort country_orig country_dest year: ///
    egen share_top5_all = total(firm_sh_ody * (rank_ody <= 5))
bysort country_orig country_dest year: gen n_exp_all = _N

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
* 0.11  Extensive margin variables
*----------------------------------------------------------------------

use "$int\firm_level_data.dta", clear

preserve
    gcollapse (count) has_exp = value_fob, by(country_orig hs6 year) labelformat(#sourcelabel#)
    bysort country_orig hs6 (year): gen first_year_op = year[1]
    gen byte new_product_orig = (year == first_year_op)
    keep country_orig hs6 year new_product_orig
    tempfile new_o
    save `new_o'
restore
merge m:1 country_orig hs6 year using `new_o', keep(1 3) nogen

bysort country_orig hs6 year: ///
    egen has_mne_exp = max(MNE_ext) if new_product_orig == 1
bysort country_orig hs6 year: ///
    egen has_dom_exp = max(DOM_ext) if new_product_orig == 1
gen byte new_prod_only_mne = (has_mne_exp == 1 & has_dom_exp == 0) if new_product_orig == 1
gen byte new_prod_both     = (has_mne_exp == 1 & has_dom_exp == 1) if new_product_orig == 1
gen byte new_prod_only_dom = (has_mne_exp == 0 & has_dom_exp == 1) if new_product_orig == 1

bysort country_orig country_dest hs6 (year): gen first_year_odp = year[1]
gen byte new_product_od = (year == first_year_odp)
bysort country_orig country_dest hs6 year: ///
    egen has_mne_od = max(MNE_ext) if new_product_od == 1
bysort country_orig country_dest hs6 year: ///
    egen has_dom_od = max(DOM_ext) if new_product_od == 1
gen byte new_prod_only_mne_od = (has_mne_od == 1 & has_dom_od == 0) if new_product_od == 1
gen byte new_prod_both_od     = (has_mne_od == 1 & has_dom_od == 1) if new_product_od == 1

save "$int\firm_level_data_full.dta", replace


*----------------------------------------------------------------------
* 0.12  Firm-year level aggregates
*----------------------------------------------------------------------

use "$int\firm_level_data_full.dta", clear

* ---- (A) Firm-Year ----
preserve
    bysort firm_id year: egen n_destinations = nvals(country_dest)
    bysort firm_id year: egen n_products     = nvals(hs6)

    gcollapse ///
        (sum)     firm_total_exports = value_fob ///
        (firstnm) n_destinations n_products ///
                  MNE_ext DOM_ext MNE_dom DOM_dom MNE_total DOM_total ///
                  hs_section ///
        , by(firm_id country_orig year) labelformat(#sourcelabel#)

    rename MNE_ext MNE
    rename DOM_ext DOM

    gen ln_firm_exports   = ln(firm_total_exports)
    gen ln_n_destinations = ln(n_destinations)
    gen ln_n_products     = ln(n_products)
    gen ln_exp_per_dest   = ln(firm_total_exports / n_destinations)
    gen ln_exp_per_prod   = ln(firm_total_exports / n_products)

    cap gen ln_avg_dist = .    // placeholder; merge from firm_dest_year if needed

    egen orig_id   = group(country_orig)
    egen ot_id     = group(country_orig year)
    egen sect_id   = group(hs_section)
    label values hs_section agro_sect_lbl

    compress
    save "$int\firm_year_level.dta", replace
restore

* ---- (B) Firm-Destination-Year ----
preserve
    gcollapse ///
        (sum)     firm_dest_exports = value_fob ///
        (firstnm) MNE_ext DOM_ext MNE_dom DOM_dom MNE_total DOM_total ///
                  ln_dist dist contig comlang_off colony fta_wto ///
                  ln_gdp_d ln_gdpcap_d ln_pop_d ///
                  income_group_dest intra_regional dest_region_num ///
                  MNE_HQ_dest MNE_aff_dest MNE_present_dest ///
                  MNE_notpresent_dest MNE_neighbor_dest ///
        , by(firm_id country_orig country_dest year) labelformat(#sourcelabel#)

    rename MNE_ext MNE
    rename DOM_ext DOM

    gen ln_exports = ln(firm_dest_exports) if firm_dest_exports > 0
    gen byte positive_trade = 1

    egen orig_id = group(country_orig)
    egen dest_id = group(country_dest)
    egen od_id   = group(country_orig country_dest)
    egen ot_id   = group(country_orig year)
    egen dt_id   = group(country_dest year)

    compress
    save "$int\firm_dest_year_level.dta", replace
restore


**********************************************************************
**********************************************************************
*
*   PART 1: DETERMINANTS OF MULTINATIONAL PRESENCE
*
**********************************************************************
**********************************************************************


**********************************************************************
* 1.1  ACROSS EXPORTING COUNTRIES
**********************************************************************

*===============================================================
* BLOCK A — MNE share trends over time (OY and ODY)
*===============================================================

use "$int\collapsed_oy.dta", clear

levelsof country_orig, local(countries_tr)

foreach mne_def in ext total {
    if "`mne_def'" == "ext" {
        local sv "share_mne_value"
        local sn "share_ext_nfirms"
    }
    else {
        local sv "share_mne_value"
        local sn "share_total_nfirms"
    }

    local cmd_v ""
    local cmd_n ""
    foreach c of local countries_tr {
        local cmd_v "`cmd_v' (connected `sv' year if country_orig == "`c'", lpattern(solid) lwidth(medthin))"
        local cmd_n "`cmd_n' (connected `sn' year if country_orig == "`c'", lpattern(solid) lwidth(medthin))"
    }

    twoway `cmd_v', ///
        ytitle("MNE Share in Agro Export Value", size(*.9)) xtitle("Year") ///
        ylab(0(0.1)1, nogrid format(%9.1f)) xlab(, nogrid angle(45)) ///
        legend(on rows(2) size(vsmall) region(lcolor(white)) symysize(small)) ///
        title("MNE_`mne_def': Agro Export Value Share over Time", size(medium)) $gro
    export_graph "fig_1_1_tr_mnevalue_`mne_def'" "$g11_tr" "$ol_g11_tr"

    twoway `cmd_n', ///
        ytitle("MNE Share in # Agro Exporters", size(*.9)) xtitle("Year") ///
        ylab(0(0.1)1, nogrid format(%9.1f)) xlab(, nogrid angle(45)) ///
        legend(on rows(2) size(vsmall) region(lcolor(white)) symysize(small)) ///
        title("MNE_`mne_def': Agro Exporter Count Share over Time", size(medium)) $gro
    export_graph "fig_1_1_tr_mnefirms_`mne_def'" "$g11_tr" "$ol_g11_tr"
}


*===============================================================
* BLOCK B — MNE vs. domestic firm profile
*===============================================================

use "$int\firm_year_level.dta", clear

label var ln_firm_exports   "Ln Total Agro Exports"
label var n_destinations    "# Export Destinations"
label var n_products        "# Agro Products Exported"
label var ln_avg_dist       "Ln Avg Distance"

local first_tab = 1
levelsof country_orig, local(ctry_list)

foreach c of local ctry_list {
    preserve
        keep if country_orig == "`c'"
        eststo mne_`c': quietly estpost tabstat ///
            ln_firm_exports n_destinations n_products ln_avg_dist ///
            if MNE == 1, statistics(mean sd) columns(statistics)
        eststo dom_`c': quietly estpost tabstat ///
            ln_firm_exports n_destinations n_products ln_avg_dist ///
            if MNE == 0, statistics(mean sd) columns(statistics)
        if `first_tab' == 1 {
            esttab mne_`c' dom_`c' using ///
                "$t_s3\tab_3_4_firm_profile_comparison.tex", ///
                replace cells("mean(fmt(%9.2f)) sd(fmt(%9.2f))") ///
                mtitle("MNE" "Domestic") title("`c'") label noobs
            local first_tab = 0
        }
        else {
            esttab mne_`c' dom_`c' using ///
                "$t_s3\tab_3_4_firm_profile_comparison.tex", ///
                append cells("mean(fmt(%9.2f)) sd(fmt(%9.2f))") ///
                mtitle("MNE" "Domestic") title("`c'") label noobs
        }
    restore
}
copy "$t_s3\tab_3_4_firm_profile_comparison.tex" ///
     "$ol_t_s3\tab_3_4_firm_profile_comparison.tex", replace

* Box plots: export size by MNE status
preserve
    keep if !missing(ln_firm_exports) & !missing(MNE)
    egen ctry_num = group(country_orig)
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
                over(`mne_var', label(labsize(vsmall)) relabel(1 "Dom" 2 "MNE")) ///
                over(ctry_num, label(labsize(vsmall) angle(45))) ///
                nooutsides asyvars ///
                box(1, fcolor("$c_DOM") lcolor("$c_DOM")) ///
                box(2, fcolor("$c_MNE") lcolor("$c_MNE")) ///
                ytitle("Ln Total Agro Exports") ///
                title("Agro Firm Export Distribution: MNE vs. Domestic", size(medium)) ///
                legend(on order(1 "Domestic" 2 "MNE_`mne_def'") ///
                       position(6) rows(1) size(small) region(lcolor(white))) ///
                bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
            export_graph "fig_1_1_fp_boxplot_`mne_def'" "$g11_fp" "$ol_g11_fp"
        }
    }
restore


**********************************************************************
* 1.2  ACROSS DESTINATION COUNTRIES
**********************************************************************

*===============================================================
* 1.2.A  Bar graphs — aggregate (by destination category × MNE def)
*===============================================================

use "$int\collapsed_ody.dta", clear

local cats  "income_group_dest intra_regional contig dest_region_num dist_above_med"
local fnums "1_2_1 1_2_2 1_2_3 1_2_4 1_2_5"
local n_cats : word count `cats'

foreach mne_def in ext total {
    if "`mne_def'" == "ext" {
        local sv "share_mne_value"
        local sn "share_mne_nfirms"
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
                    title("Agro MNE_`mne_def'", size(medium)) ///
                    ytitle("") bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
                export_graph "fig_`fnum'_`mne_def'_agg" "$g12" "$ol_g12"
            }
        restore
    }
}

*===============================================================
* 1.2.B  Bar graphs — by exporting country
*===============================================================

use "$int\collapsed_ody.dta", clear
levelsof country_orig, local(countries)

foreach mne_def in ext total {
    if "`mne_def'" == "ext"   local sv "share_mne_value"
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
                        title("`c' - Agro MNE_`mne_def'", size(medium)) ///
                        ytitle("MNE Share in Agro Exports") ///
                        bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
                    export_graph "fig_1_2_`mne_def'_`cat'_`c'" "$g12" "$ol_g12"
                }
            restore
        }
    }
}

*===============================================================
* 1.2.C_EXTRA  MNE share vs. average tariff (scatter)
*===============================================================

use "$int\collapsed_ody.dta", clear
preserve
    gcollapse (mean) share_mne_value share_ext_nfirms share_total_nfirms ///
              avg_tariff ln_dist income_group_dest, ///
              by(country_orig country_dest) labelformat(#sourcelabel#)
    drop if missing(avg_tariff)
    cap label define inc_lbl 1 "Low" 2 "Lower-Mid" 3 "Upper-Mid" 4 "High", replace

    foreach mne_def in ext total {
        if "`mne_def'" == "ext"   local sv "share_mne_value"
        if "`mne_def'" == "total" local sv "share_total_nfirms"
        cap {
            twoway ///
                (scatter `sv' avg_tariff if income_group_dest == 1, mcolor("navy")   ms(o) msize(small)) ///
                (scatter `sv' avg_tariff if income_group_dest == 2, mcolor("blue")   ms(d) msize(small)) ///
                (scatter `sv' avg_tariff if income_group_dest == 3, mcolor("orange") ms(t) msize(small)) ///
                (scatter `sv' avg_tariff if income_group_dest == 4, mcolor("red")    ms(s) msize(small)) ///
                (lfit `sv' avg_tariff, lcolor(black) lwidth(medthin)), ///
                ytitle("Agro MNE_`mne_def' Share", size(*.9)) ///
                xtitle("Average Bilateral Tariff", size(*.9)) ///
                legend(on order(1 "Low" 2 "Lower-Mid" 3 "Upper-Mid" 4 "High Income") ///
                       position(6) rows(1) size(vsmall) region(lcolor(white))) ///
                title("Agro MNE Share vs. Tariff", size(medium)) ///
                ylab(, nogrid) $gro
            export_graph "fig_1_2_6_`mne_def'_tariff_scatter" "$g12" "$ol_g12"
        }
    }
restore

*===============================================================
* 1.2.D  Regressions — destination characteristics
*===============================================================

capture program drop run_trade_spec
program define run_trade_spec
    args dv controls filename cluster_id cluster_lbl
    reg `dv' `controls', robust
    outreg2 using "`filename'", ///
        replace tex(frag) label ctitle("No FE") ///
        addtext(FE, "None", SE Cluster, "`cluster_lbl'") ///
        dec(4) nocons
    forval f = 2/7 {
        local fe "${fe`f'}"
        local fl "${fel`f'}"
        reghdfe `dv' `controls', absorb(`fe') vce(cluster `cluster_id')
        outreg2 using "`filename'", ///
            append tex(frag) label ctitle("`fl'") ///
            addtext(FE, "`fl'", SE Cluster, "`cluster_lbl'") ///
            dec(4) nocons
    }
    if "`cluster_id'" == "odp_id" {
        reghdfe `dv' `controls', absorb(odt_id) vce(cluster `cluster_id')
        outreg2 using "`filename'", ///
            append tex(frag) label ctitle("ODxT") ///
            addtext(FE, "ODxT", SE Cluster, "`cluster_lbl'") dec(4) nocons
    }
end

local controls "ln_gdpcap_o ln_pop_o ln_gdpcap_d ln_pop_d ln_dist contig comlang_off colony fta_wto BIT DTT avg_tariff"

* ODY
use "$int\collapsed_ody.dta", clear
foreach mne_def in ext total {
    if "`mne_def'" == "ext" local dvars "share_mne_value share_mne_nfirms"
    else                    local dvars "share_`mne_def'_nfirms"
    foreach dv of local dvars {
        run_trade_spec `dv' "`controls'" ///
            "$r_s1\reg_1_2_ody_`mne_def'_`dv'.tex" "od_id" "Origin-Destination"
        copy "$r_s1\reg_1_2_ody_`mne_def'_`dv'.tex" ///
             "$ol_r_s1\reg_1_2_ody_`mne_def'_`dv'.tex", replace
    }
}

* ODPY
use "$int\collapsed_odpy.dta", clear
foreach mne_def in ext total {
    if "`mne_def'" == "ext" local dvars "share_mne_value share_mne_nfirms"
    else                    local dvars "share_`mne_def'_nfirms"
    foreach dv of local dvars {
        run_trade_spec `dv' "`controls'" ///
            "$r_s1\reg_1_2_odpy_`mne_def'_`dv'.tex" "odp_id" "Orig-Dest-Product"
        copy "$r_s1\reg_1_2_odpy_`mne_def'_`dv'.tex" ///
             "$ol_r_s1\reg_1_2_odpy_`mne_def'_`dv'.tex", replace
    }
}


**********************************************************************
* 1.3  BY PRODUCT
**********************************************************************

*===============================================================
* 1.3.A  Bar graphs — by product characteristic × MNE def
*===============================================================

use "$int\collapsed_opy.dta", clear

foreach mne_def in ext total {
    if "`mne_def'" == "ext" {
        local sv "share_mne_value"
        local sn "share_mne_nfirms"
    }
    else {
        local sv "share_mne_value"
        local sn "share_total_nfirms"
    }

    * (i) Above/below median
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
                    title("Agro MNE_`mne_def' - `v'", size(medium)) ///
                    ytitle("") bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
                export_graph "fig_1_3_`mne_def'_`v'_median" "$g13" "$ol_g13"
            }
        restore
    }

    * (ii) By decile
    foreach v in upstreamness sigma complexity quality_ladder rca rhci {
        cap confirm variable `v'_decile
        if _rc != 0 continue
        preserve
            drop if `v'_decile == .
            gcollapse (mean) `sv' `sn' [aw = total_value], by(`v'_decile) labelformat(#sourcelabel#)
            cap {
                graph hbar (asis) `sv' `sn', ///
                    over(`v'_decile, label(labsize(vsmall))) ///
                    bar(1, color($c_MNE)) bar(2, color($c_DOM)) ///
                    legend(on order(1 "Value" 2 "# Firms") ///
                           position(6) rows(1) region(lcolor(white)) size(small)) ///
                    title("Agro MNE_`mne_def' - `v' (decile)", size(medium)) ///
                    ytitle("") bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
                export_graph "fig_1_3_`mne_def'_`v'_decile" "$g13" "$ol_g13"
            }
        restore
    }
}

*===============================================================
* 1.3.B  Bar graphs — product characteristic by exporting country
*===============================================================

use "$int\collapsed_opy.dta", clear
levelsof country_orig, local(countries)

foreach mne_def in ext total {
    if "`mne_def'" == "ext" local sv "share_mne_value"
    else                    local sv "share_total_nfirms"

    foreach cat in upstreamness_abovemed sigma_abovemed complexity_abovemed ///
                   quality_ladder_abovemed rca_abovemed rhci_abovemed {
        foreach c of local countries {
            preserve
                keep if country_orig == "`c'"
                drop if `cat' == .
                cap {
                    gcollapse (mean) `sv' [aw = total_value], by(`cat') labelformat(#sourcelabel#)
                    graph hbar (asis) `sv', ///
                        over(`cat', label(labsize(small))) ///
                        bar(1, color($c_MNE)) ///
                        title("`c' Agro - MNE_`mne_def'", size(medium)) ///
                        ytitle("MNE Agro Share") ///
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

capture program drop run_spec_iv
program define run_spec_iv
    args dv iv filename ladder cluster_id cluster_lbl
    local nfe = ${nfe_`ladder'}
    forval i = 1/`nfe' {
        local fe "${fe_`ladder'`i'}"
        local fl "${fel_`ladder'`i'}"
        if `i' == 1 {
            if "`fe'" == "" reg `dv' `iv', robust
            else            reghdfe `dv' `iv', absorb(`fe') vce(cluster `cluster_id')
            outreg2 using "`filename'", replace tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", SE Cluster, "`cluster_lbl'") dec(4) nocons
        }
        else {
            if "`fe'" == "" reg `dv' `iv', robust
            else            reghdfe `dv' `iv', absorb(`fe') vce(cluster `cluster_id')
            outreg2 using "`filename'", append tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", SE Cluster, "`cluster_lbl'") dec(4) nocons
        }
    }
end

* OPY
use "$int\collapsed_opy.dta", clear
foreach mne_def in ext total {
    if "`mne_def'" == "ext" local dvars "share_mne_value share_mne_nfirms"
    else                    local dvars "share_`mne_def'_nfirms"
    foreach dv of local dvars {
        foreach iv in upstreamness sigma complexity quality_ladder rca rhci lall2000 ipc1 {
            cap confirm variable `iv'
            if _rc != 0 continue
            run_spec_iv `dv' `iv' ///
                "$r_s1\reg_1_3_opy_`mne_def'_`dv'_`iv'.tex" ///
                "opy" "op_id" "Origin-Product"
            reghdfe `dv' i.hs_section, absorb(ot_id) vce(cluster op_id)
            outreg2 using "$r_s1\reg_1_3_opy_`mne_def'_`dv'_`iv'.tex", ///
                append tex(frag) label ctitle("Agro Sections") ///
                addtext(FE, "OxT", SE Cluster, "Origin-Product") dec(4) nocons
            copy "$r_s1\reg_1_3_opy_`mne_def'_`dv'_`iv'.tex" ///
                 "$ol_r_s1\reg_1_3_opy_`mne_def'_`dv'_`iv'.tex", replace
        }
    }
}

* ODPY
use "$int\collapsed_odpy.dta", clear
foreach mne_def in ext total {
    if "`mne_def'" == "ext" local dvars "share_mne_value share_mne_nfirms"
    else                    local dvars "share_`mne_def'_nfirms"
    foreach dv of local dvars {
        foreach iv in upstreamness sigma complexity quality_ladder rca rhci lall2000 ipc1 {
            cap confirm variable `iv'
            if _rc != 0 continue
            run_spec_iv `dv' `iv' ///
                "$r_s1\reg_1_3_odpy_`mne_def'_`dv'_`iv'.tex" ///
                "odpy" "odp_id" "Orig-Dest-Prod"
            copy "$r_s1\reg_1_3_odpy_`mne_def'_`dv'_`iv'.tex" ///
                 "$ol_r_s1\reg_1_3_odpy_`mne_def'_`dv'_`iv'.tex", replace
        }
    }
}


**********************************************************************
* 1.4  PARENT COUNTRY ANALYSIS
**********************************************************************

use "$int\firm_level_data.dta", clear
keep if MNE_ext == 1

gen parent_region = ""
replace parent_region = "USA"    if iso3_parent == "USA"
replace parent_region = "Europe" if inlist(iso3_parent,"AUT","BEL","BGR","CYP","CZE")
replace parent_region = "Europe" if inlist(iso3_parent,"DNK","EST","FIN","FRA","DEU")
replace parent_region = "Europe" if inlist(iso3_parent,"GRC","HUN","IRL","ITA","LVA")
replace parent_region = "Europe" if inlist(iso3_parent,"LTU","LUX","MLT","NLD","POL")
replace parent_region = "Europe" if inlist(iso3_parent,"PRT","ROU","SVK","SVN","ESP")
replace parent_region = "Europe" if inlist(iso3_parent,"SWE","GBR")
replace parent_region = "LAC"    if inlist(iso3_parent,"ARG","BHS","BRB","BLZ","BOL")
replace parent_region = "LAC"    if inlist(iso3_parent,"BRA","CHL","COL","CRI","DOM")
replace parent_region = "LAC"    if inlist(iso3_parent,"ECU","SLV","GTM","GUY","HTI")
replace parent_region = "LAC"    if inlist(iso3_parent,"HND","JAM","MEX","NIC","PAN")
replace parent_region = "LAC"    if inlist(iso3_parent,"PRY","PER","SUR","TTO","URY","VEN")
replace parent_region = "Asia"   if inlist(iso3_parent,"CHN","HKG","IND","IDN","JPN")
replace parent_region = "Asia"   if inlist(iso3_parent,"MYS","PHL","KOR","SGP","TWN","THA")
replace parent_region = "ROW"    if parent_region == ""

* Figure D1: Pooled bar
preserve
    gcollapse (sum) mne_exp = value_fob, by(parent_region) labelformat(#sourcelabel#)
    egen double tot = total(mne_exp)
    gen share_pr = mne_exp / tot
    gsort -share_pr
    gen order = _n
    labmask order, values(parent_region)
    cap {
        graph hbar (asis) share_pr, ///
            over(order, sort(order) label(labsize(small))) ///
            bar(1, color($c_MNE)) ///
            ytitle("Share in Total Agro MNE Exports") ///
            ylab(, nogrid format(%9.2f)) ///
            title("Agro MNE Exports by Parent Region (Pooled)", size(medium)) ///
            bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
        export_graph "fig_1_4_1_parent_region_pool" "$g14" "$ol_g14"
    }
restore

* Figure D2: Grouped bar by exporting country
preserve
    gcollapse (sum) mne_exp = value_fob, by(country_orig parent_region) labelformat(#sourcelabel#)
    bysort country_orig: egen double tot_ctry = total(mne_exp)
    gen share_pr = mne_exp / tot_ctry
    keep country_orig parent_region share_pr
    reshape wide share_pr, i(country_orig) j(parent_region) string
    cap gsort -share_prUSA
    gen order = _n
    labmask order, values(country_orig)
    cap {
        graph hbar (asis) share_prUSA share_prEurope share_prLAC share_prAsia share_prROW, ///
            over(order, sort(order) label(labsize(small))) stack ///
            bar(1, color("red*1.2"))   bar(2, color("blue*0.8")) ///
            bar(3, color("green*0.8")) bar(4, color("orange*0.9")) ///
            bar(5, color("gray*0.6")) ///
            legend(on order(1 "USA" 2 "Europe" 3 "LAC" 4 "Asia" 5 "ROW") ///
                   position(6) rows(1) size(vsmall) region(lcolor(white))) ///
            ytitle("Share in Country's Agro MNE Exports") ///
            title("Parent Region by Exporting Country (Agro)", size(medium)) ///
            bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
        export_graph "fig_1_4_2_parent_region_by_origin" "$g14" "$ol_g14"
    }
restore

* Figure D3: Parent region breakdown for US-destined agro exports
preserve
    gen dest_grp = cond(country_dest == "USA", "US Destinations", "Non-US Destinations")
    gcollapse (sum) mne_exp = value_fob, by(dest_grp parent_region) labelformat(#sourcelabel#)
    bysort dest_grp: egen double tot_dg = total(mne_exp)
    gen share_pr = mne_exp / tot_dg
    keep dest_grp parent_region share_pr
    reshape wide share_pr, i(dest_grp) j(parent_region) string
    gen order = (_n == 1)
    sort order
    replace order = _n
    labmask order, values(dest_grp)
    cap {
        graph hbar (asis) share_prUSA share_prEurope share_prLAC share_prAsia share_prROW, ///
            over(order, label(labsize(small))) stack ///
            bar(1, color("red*1.2"))   bar(2, color("blue*0.8")) ///
            bar(3, color("green*0.8")) bar(4, color("orange*0.9")) ///
            bar(5, color("gray*0.6")) ///
            legend(on order(1 "USA Parent" 2 "EU Parent" 3 "LAC Parent" 4 "Asia Parent" 5 "Other") ///
                   position(6) rows(1) size(vsmall) region(lcolor(white))) ///
            ytitle("Share in Agro MNE Exports") ///
            title("Agro: Who Exports to the US? (by Parent Region)", size(medium)) ///
            bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
        export_graph "fig_1_4_3_parent_dest_match_usa" "$g14" "$ol_g14"
    }
restore

* Figure D4: Parent region breakdown for EU-destined agro exports
preserve
    gen dest_grp = cond(dest_region == "Europe", "EU Destinations", "Non-EU Destinations")
    drop if missing(dest_grp)
    gcollapse (sum) mne_exp = value_fob, by(dest_grp parent_region) labelformat(#sourcelabel#)
    bysort dest_grp: egen double tot_dg = total(mne_exp)
    gen share_pr = mne_exp / tot_dg
    keep dest_grp parent_region share_pr
    reshape wide share_pr, i(dest_grp) j(parent_region) string
    gen order = (dest_grp == "EU Destinations")
    gsort -order
    replace order = _n
    labmask order, values(dest_grp)
    cap {
        graph hbar (asis) share_prUSA share_prEurope share_prLAC share_prAsia share_prROW, ///
            over(order, label(labsize(small))) stack ///
            bar(1, color("red*1.2"))   bar(2, color("blue*0.8")) ///
            bar(3, color("green*0.8")) bar(4, color("orange*0.9")) ///
            bar(5, color("gray*0.6")) ///
            legend(on order(1 "USA Parent" 2 "EU Parent" 3 "LAC Parent" 4 "Asia Parent" 5 "Other") ///
                   position(6) rows(1) size(vsmall) region(lcolor(white))) ///
            ytitle("Share in Agro MNE Exports") ///
            title("Agro: Who Exports to the EU? (by Parent Region)", size(medium)) ///
            bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
        export_graph "fig_1_4_4_parent_dest_match_eu" "$g14" "$ol_g14"
    }
restore

* Figure D5 (NEW): Parent region × Agro Section — where do foreign firms invest?
preserve
    gcollapse (sum) mne_exp = value_fob, ///
        by(parent_region hs_section) labelformat(#sourcelabel#)
    bysort parent_region: egen double tot_pr = total(mne_exp)
    gen share_sect = mne_exp / tot_pr
    label values hs_section agro_sect_lbl
    keep parent_region hs_section share_sect
    reshape wide share_sect, i(parent_region) j(hs_section)
    gen order = _n
    labmask order, values(parent_region)
    cap {
        graph hbar (asis) share_sect1 share_sect2 share_sect3 share_sect4, ///
            over(order, sort(order) label(labsize(small))) stack ///
            bar(1, color("$c_s1")) bar(2, color("$c_s2")) ///
            bar(3, color("$c_s3")) bar(4, color("$c_s4")) ///
            legend(on order(1 "I: Live Animals" 2 "II: Vegetables" ///
                            3 "III: Fats & Oils" 4 "IV: Food & Bev.") ///
                   position(6) rows(2) size(vsmall) region(lcolor(white))) ///
            ytitle("Share of Parent Region's Agro MNE Exports") ///
            title("Agro Section Mix by Parent Region", size(medium)) ///
            bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
        export_graph "fig_1_4_5_parent_agrosection" "$g14" "$ol_g14"
    }
restore


**********************************************************************
* 1.5  AGRICULTURAL SECTION DEEP-DIVE  [AGRO-NEW]
*
* Ten new figures exploring MNE presence across the 4 agro sections.
**********************************************************************

*---------------------------------------------------------------
* 1.5.A  MNE share by agro section — pooled, all years
*   fig_1_5_1_section_share_pool
*   Dataset: collapsed_opy.dta
*---------------------------------------------------------------

use "$int\collapsed_opy.dta", clear

preserve
    gcollapse (mean) share_mne_value share_mne_nfirms share_total_nfirms ///
              [aw = total_value], by(hs_section) labelformat(#sourcelabel#)
    drop if hs_section == .
    label values hs_section agro_sect_lbl

    foreach mne_def in ext total {
        if "`mne_def'" == "ext" {
            local sv "share_mne_value"
            local sn "share_mne_nfirms"
        }
        else {
            local sv "share_mne_value"
            local sn "share_total_nfirms"
        }
        cap {
            graph hbar (asis) `sv' `sn', ///
                over(hs_section, label(labsize(small) angle(0))) ///
                bar(1, color($c_MNE)) bar(2, color($c_DOM)) ///
                legend(on order(1 "Value Share" 2 "Firm Count Share") ///
                       position(6) rows(1) region(lcolor(white)) size(small)) ///
                ytitle("MNE_`mne_def' Share (value-weighted mean)") ///
                title("MNE Presence by Agricultural Section", size(medium)) ///
                note("Value-weighted across origin countries, products, and years.") ///
                bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
            export_graph "fig_1_5_1_section_share_pool_`mne_def'" "$g15" "$ol_g15"
        }
    }
restore


*---------------------------------------------------------------
* 1.5.B  MNE share by agro section over time
*   fig_1_5_2_section_trend_[def]
*   Dataset: collapsed_opy.dta
*---------------------------------------------------------------

use "$int\collapsed_opy.dta", clear

preserve
    gcollapse (mean) share_mne_value share_mne_nfirms share_total_nfirms ///
              [aw = total_value], by(hs_section year) labelformat(#sourcelabel#)
    drop if hs_section == .
    label values hs_section agro_sect_lbl

    foreach mne_def in ext total {
        if "`mne_def'" == "ext" local sv "share_mne_value"
        else                    local sv "share_total_nfirms"

        cap {
            twoway ///
                (connected `sv' year if hs_section == 1, ///
                    lcolor("$c_s1") mcolor("$c_s1") lpattern(solid) ms(o)) ///
                (connected `sv' year if hs_section == 2, ///
                    lcolor("$c_s2") mcolor("$c_s2") lpattern(dash)  ms(d)) ///
                (connected `sv' year if hs_section == 3, ///
                    lcolor("$c_s3") mcolor("$c_s3") lpattern(dot)   ms(t)) ///
                (connected `sv' year if hs_section == 4, ///
                    lcolor("$c_s4") mcolor("$c_s4") lpattern(longdash) ms(s)), ///
                ytitle("MNE_`mne_def' Share", size(*.9)) xtitle("Year") ///
                ylab(, nogrid format(%9.2f)) xlab(, nogrid angle(45)) ///
                legend(on order(1 "I: Live Animals" 2 "II: Vegetables" ///
                                3 "III: Fats & Oils" 4 "IV: Food & Bev.") ///
                       position(6) rows(2) size(small) region(lcolor(white))) ///
                title("MNE_`mne_def' Share Trends by Agro Section", size(medium)) ///
                $gro
            export_graph "fig_1_5_2_section_trend_`mne_def'" "$g15" "$ol_g15"
        }
    }
restore


*---------------------------------------------------------------
* 1.5.C  MNE share for each HS2 chapter (1-24)
*   fig_1_5_3_hs2chapter_mne_[def]
*   Dataset: collapsed_opy.dta
*---------------------------------------------------------------

use "$int\collapsed_opy.dta", clear

preserve
    gcollapse (mean) share_mne_value share_mne_nfirms share_total_nfirms ///
              (sum) total_value ///
              [aw = total_value], by(hs2) labelformat(#sourcelabel#)
    drop if hs2 == .
    label values hs2 hs2_lbl

    * Sort by MNE value share descending
    gsort -share_mne_value
    gen order = _n
    labmask order, values(hs2)

    foreach mne_def in ext total {
        if "`mne_def'" == "ext" {
            local sv "share_mne_value"
            local sn "share_mne_nfirms"
        }
        else {
            local sv "share_mne_value"
            local sn "share_total_nfirms"
        }
        cap {
            graph hbar (asis) `sv' `sn', ///
                over(order, sort(order) label(labsize(vsmall) angle(0))) ///
                bar(1, color($c_MNE)) bar(2, color($c_DOM)) ///
                legend(on order(1 "Value Share" 2 "Firm Count Share") ///
                       position(6) rows(1) region(lcolor(white)) size(small)) ///
                ytitle("MNE_`mne_def' Share") ///
                title("MNE Presence by HS2 Chapter (Sorted)", size(medium)) ///
                note("Sorted by descending MNE value share.") ///
                bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
            export_graph "fig_1_5_3_hs2chapter_mne_`mne_def'" "$g15" "$ol_g15"
        }
    }
restore


*---------------------------------------------------------------
* 1.5.D  Export value composition: section × MNE/DOM
*   fig_1_5_4_value_composition
*   Dataset: collapsed_opy.dta (collapsed further to section level)
*---------------------------------------------------------------

use "$int\collapsed_opy.dta", clear

preserve
    * Compute mne_value and dom_value at section level
    gcollapse (sum) mne_value total_value, ///
              by(hs_section year) labelformat(#sourcelabel#)
    gen dom_value = total_value - mne_value
    drop if hs_section == .
    label values hs_section agro_sect_lbl

    * Express as share of total agro exports
    egen double grand_total = total(total_value)
    gen mne_share_abs = mne_value / grand_total
    gen dom_share_abs = dom_value / grand_total

    * Collapse over years for the pooled bar
    gcollapse (mean) mne_value total_value dom_value, by(hs_section) labelformat(#sourcelabel#)
    egen double g2 = total(total_value)
    gen mne_sh = mne_value / g2
    gen dom_sh = dom_value / g2

    cap {
        graph hbar (asis) mne_sh dom_sh, ///
            over(hs_section, label(labsize(small))) ///
            bar(1, color($c_MNE)) bar(2, color($c_DOM)) ///
            stack ///
            legend(on order(1 "MNE (ext)" 2 "Domestic") ///
                   position(6) rows(1) region(lcolor(white)) size(small)) ///
            ytitle("Share of Total Agro Exports") ///
            title("Export Value Composition by Agro Section", size(medium)) ///
            note("Pooled over all years. Each bar = section's share of total agro exports.") ///
            bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
        export_graph "fig_1_5_4_value_composition" "$g15" "$ol_g15"
    }
restore


*---------------------------------------------------------------
* 1.5.E  Number of MNE vs. domestic agro exporters by section, over time
*   fig_1_5_5_nfirms_section_yr_[def]
*   Dataset: firm_level_data.dta (firm-level counts)
*---------------------------------------------------------------

use "$int\firm_level_data.dta", clear

* Count distinct firms by MNE status × section × year
preserve
    gcollapse (count) n_firms_mne = firm_id if MNE_ext == 1, ///
              by(hs_section year) labelformat(#sourcelabel#)
    rename n_firms_mne n_mne_yr
    tempfile mne_counts
    save `mne_counts'
restore

preserve
    gcollapse (count) n_firms = firm_id, by(hs_section year) labelformat(#sourcelabel#)
    merge 1:1 hs_section year using `mne_counts', nogen
    replace n_mne_yr = 0 if missing(n_mne_yr)
    gen n_dom_yr = n_firms - n_mne_yr
    drop if hs_section == .
    label values hs_section agro_sect_lbl

    forval s = 1/4 {
        cap {
            * get the section label for the title
            local slbl : label agro_sect_lbl `s'
            twoway ///
                (area n_mne_yr year if hs_section == `s', fcolor("$c_MNE") lcolor("$c_MNE") fintensity(60)) ///
                (area n_dom_yr year if hs_section == `s', fcolor("$c_DOM") lcolor("$c_DOM") fintensity(30)), ///
                ytitle("# Agro Exporters") xtitle("Year") ///
                legend(on order(1 "MNE (ext)" 2 "Domestic") ///
                       position(6) rows(1) size(small) region(lcolor(white))) ///
                title("Exporter Count: Section `s' (`slbl')", size(medium)) ///
                $gro
            export_graph "fig_1_5_5_nfirms_section`s'_yr" "$g15" "$ol_g15"
        }
    }
restore


*---------------------------------------------------------------
* 1.5.F  Country × agro section matrix (MNE share)
*   fig_1_5_6_country_section_[def]
*   Dataset: collapsed_opy.dta
*---------------------------------------------------------------

use "$int\collapsed_opy.dta", clear

preserve
    gcollapse (mean) share_mne_value share_total_nfirms ///
              [aw = total_value], ///
              by(country_orig hs_section) labelformat(#sourcelabel#)
    drop if hs_section == .
    label values hs_section agro_sect_lbl
    keep country_orig hs_section share_mne_value share_total_nfirms

    * Reshape for grouped bar: one bar group per country, 4 bars per section
    reshape wide share_mne_value share_total_nfirms, ///
        i(country_orig) j(hs_section)

    gen order = _n
    labmask order, values(country_orig)

    foreach mne_def in ext total {
        if "`mne_def'" == "ext"   local prefix "share_mne_value"
        if "`mne_def'" == "total" local prefix "share_total_nfirms"
        cap {
            graph hbar (asis) `prefix'1 `prefix'2 `prefix'3 `prefix'4, ///
                over(order, sort(order) label(labsize(small))) ///
                bar(1, color("$c_s1")) bar(2, color("$c_s2")) ///
                bar(3, color("$c_s3")) bar(4, color("$c_s4")) ///
                legend(on order(1 "I: Live Animals" 2 "II: Vegetables" ///
                                3 "III: Fats & Oils" 4 "IV: Food & Bev.") ///
                       position(6) rows(2) size(vsmall) region(lcolor(white))) ///
                ytitle("MNE_`mne_def' Share") ///
                title("MNE Share by Country and Agro Section", size(medium)) ///
                bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
            export_graph "fig_1_5_6_country_section_`mne_def'" "$g15" "$ol_g15"
        }
    }
restore


*---------------------------------------------------------------
* 1.5.G  Agro section × destination region
*   fig_1_5_7_section_dest_[def]
*   Dataset: collapsed_odpy.dta → collapse by section × dest_region
*---------------------------------------------------------------

use "$int\collapsed_odpy.dta", clear

preserve
    drop if dest_region_num == . | hs_section == .
    gcollapse (mean) share_mne_value share_total_nfirms ///
              [aw = total_value], ///
              by(hs_section dest_region_num) labelformat(#sourcelabel#)
    label values hs_section agro_sect_lbl
    keep hs_section dest_region_num share_mne_value share_total_nfirms

    foreach mne_def in ext total {
        if "`mne_def'" == "ext"   local sv "share_mne_value"
        if "`mne_def'" == "total" local sv "share_total_nfirms"
        cap {
            graph hbar (asis) `sv', ///
                over(hs_section, label(labsize(small))) ///
                over(dest_region_num, label(labsize(vsmall) angle(45))) ///
                bar(1, color($c_MNE)) ///
                ytitle("MNE_`mne_def' Share") ///
                title("Agro MNE Share: Section vs. Destination Region", size(medium)) ///
                note("Value-weighted average across origin countries and years.") ///
                bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
            export_graph "fig_1_5_7_section_dest_`mne_def'" "$g15" "$ol_g15"
        }
    }
restore


*---------------------------------------------------------------
* 1.5.H  Box plots: firm export size by section × MNE status
*   fig_1_5_8_boxplot_section_[def]
*   Dataset: firm_year_level.dta
*---------------------------------------------------------------

use "$int\firm_year_level.dta", clear

foreach mne_def in ext total {
    if "`mne_def'" == "ext"   local mne_var "MNE"
    if "`mne_def'" == "total" local mne_var "MNE_total"
    cap confirm variable `mne_var'
    if _rc != 0 continue
    cap {
        graph box ln_firm_exports, ///
            over(`mne_var', label(labsize(vsmall)) relabel(1 "Dom" 2 "MNE")) ///
            over(hs_section, label(labsize(small))) ///
            nooutsides asyvars ///
            box(1, fcolor("$c_DOM") lcolor("$c_DOM")) ///
            box(2, fcolor("$c_MNE") lcolor("$c_MNE")) ///
            ytitle("Ln Total Agro Exports") ///
            title("Firm Agro Export Size by Section and MNE Status", size(medium)) ///
            legend(on order(1 "Domestic" 2 "MNE_`mne_def'") ///
                   position(6) rows(1) size(small) region(lcolor(white))) ///
            bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
        export_graph "fig_1_5_8_boxplot_section_`mne_def'" "$g15" "$ol_g15"
    }
}


*---------------------------------------------------------------
* 1.5.I  Scatter: HS2 chapter importance vs. MNE penetration
*   (x-axis = chapter's share of total agro exports,
*    y-axis = MNE value share, label = HS2 number)
*   fig_1_5_9_hs2_value_vs_mne
*   Dataset: collapsed_opy.dta
*---------------------------------------------------------------

use "$int\collapsed_opy.dta", clear

preserve
    gcollapse (sum) total_value mne_value (count) n_firms = firm_id, ///
              by(hs2) labelformat(#sourcelabel#)
    drop if hs2 == .
    egen double grand_total = total(total_value)
    gen value_share = total_value / grand_total
    gen share_mne_value = mne_value / total_value
    label values hs2 hs2_lbl
    gen hs2_str = string(hs2, "%02.0f")

    cap {
        twoway ///
            (scatter share_mne_value value_share, ///
                ms(oh) mcolor("$c_MNE") msize(medium) ///
                mlabel(hs2_str) mlabsize(vsmall) mlabcolor(black) ///
                mlabposition(9)) ///
            (lfit share_mne_value value_share, ///
                lcolor(black) lwidth(medthin) lpattern(dash)), ///
            ytitle("MNE Value Share in Chapter") ///
            xtitle("Chapter's Share of Total Agro Exports") ///
            legend(off) ///
            title("Agro Chapter Importance vs. MNE Penetration", size(medium)) ///
            note("Each point is one HS2 chapter. Label = HS2 code.") ///
            $gro
        export_graph "fig_1_5_9_hs2_value_vs_mne" "$g15" "$ol_g15"
    }
restore


*---------------------------------------------------------------
* 1.5.J  Stacked bar: agro export value by section per country
*   fig_1_5_10_country_section_stack
*   Dataset: collapsed_opy.dta
*---------------------------------------------------------------

use "$int\collapsed_opy.dta", clear

preserve
    gcollapse (sum) total_value, by(country_orig hs_section) labelformat(#sourcelabel#)
    drop if hs_section == .
    bysort country_orig: egen double ctry_total = total(total_value)
    gen sect_share = total_value / ctry_total
    label values hs_section agro_sect_lbl
    keep country_orig hs_section sect_share
    reshape wide sect_share, i(country_orig) j(hs_section)
    gen order = _n
    labmask order, values(country_orig)
    cap {
        graph hbar (asis) sect_share1 sect_share2 sect_share3 sect_share4, ///
            over(order, sort(order) label(labsize(small))) stack ///
            bar(1, color("$c_s1")) bar(2, color("$c_s2")) ///
            bar(3, color("$c_s3")) bar(4, color("$c_s4")) ///
            legend(on order(1 "I: Live Animals" 2 "II: Vegetables" ///
                            3 "III: Fats & Oils" 4 "IV: Food & Bev.") ///
                   position(6) rows(2) size(vsmall) region(lcolor(white))) ///
            ytitle("Share of Country's Agro Exports") ///
            title("Agro Export Specialization by Country and Section", size(medium)) ///
            note("Pooled over all years.") ///
            bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
        export_graph "fig_1_5_10_country_section_stack" "$g15" "$ol_g15"
    }
restore


*---------------------------------------------------------------
* 1.5.K  MNE share over time by section AND country (faceted)
*   fig_1_5_11_section_country_trend_[def]
*   One graph per exporting country, 4 lines per section
*   Dataset: collapsed_opy.dta
*---------------------------------------------------------------

use "$int\collapsed_opy.dta", clear
levelsof country_orig, local(countries)

preserve
    gcollapse (mean) share_mne_value share_total_nfirms ///
              [aw = total_value], ///
              by(country_orig hs_section year) labelformat(#sourcelabel#)
    drop if hs_section == .
    label values hs_section agro_sect_lbl

    foreach mne_def in ext total {
        if "`mne_def'" == "ext"   local sv "share_mne_value"
        if "`mne_def'" == "total" local sv "share_total_nfirms"

        foreach c of local countries {
            cap {
                twoway ///
                    (connected `sv' year if country_orig == "`c'" & hs_section == 1, ///
                        lcolor("$c_s1") mcolor("$c_s1") lpattern(solid) ms(o)) ///
                    (connected `sv' year if country_orig == "`c'" & hs_section == 2, ///
                        lcolor("$c_s2") mcolor("$c_s2") lpattern(dash)  ms(d)) ///
                    (connected `sv' year if country_orig == "`c'" & hs_section == 3, ///
                        lcolor("$c_s3") mcolor("$c_s3") lpattern(dot)   ms(t)) ///
                    (connected `sv' year if country_orig == "`c'" & hs_section == 4, ///
                        lcolor("$c_s4") mcolor("$c_s4") lpattern(longdash) ms(s)), ///
                    ytitle("MNE_`mne_def' Share", size(*.9)) xtitle("Year") ///
                    ylab(, nogrid format(%9.2f)) xlab(, nogrid angle(45)) ///
                    legend(on order(1 "I: Live Animals" 2 "II: Vegetables" ///
                                    3 "III: Fats & Oils" 4 "IV: Food & Bev.") ///
                           position(6) rows(2) size(vsmall) region(lcolor(white))) ///
                    title("`c': MNE_`mne_def' Trends by Agro Section", size(medium)) ///
                    $gro
                export_graph "fig_1_5_11_trend_`mne_def'_`c'" "$g15" "$ol_g15"
            }
        }
    }
restore


**********************************************************************
**********************************************************************
*
*   PART 2: EFFECTS OF MULTINATIONAL PRESENCE
*
**********************************************************************
**********************************************************************


**********************************************************************
* 2.1  AGGREGATE REGRESSIONS
**********************************************************************

*===============================================================
* 2.1.A  ODY
*===============================================================

capture program drop run_agg_spec
program define run_agg_spec
    args dv mv filename_base cluster_id cluster_lbl

    * --- Baseline (7-spec) ---
    forval f = 1/7 {
        local fe "${fe`f'}"
        local fl "${fel`f'}"
        if `f' == 1 reg `dv' `mv', robust
        else        reghdfe `dv' `mv', absorb(`fe') vce(cluster `cluster_id')
        if `f' == 1 {
            outreg2 using "`filename_base'_baseline.tex", replace tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", Spec, "Baseline", SE, "`cluster_lbl'") dec(4) nocons
        }
        else {
            outreg2 using "`filename_base'_baseline.tex", append tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", Spec, "Baseline", SE, "`cluster_lbl'") dec(4) nocons
        }
    }

    * --- Destination interactions (FE 5-7) ---
    forval f = 5/7 {
        local fe "${fe`f'}"
        local fl "${fel`f'}"
        local ivd "`mv' `mv'_X_lngdppc_d `mv'_X_lnpop_d ln_gdpcap_d ln_pop_d"
        reghdfe `dv' `ivd', absorb(`fe') vce(cluster `cluster_id')
        if `f' == 5 {
            outreg2 using "`filename_base'_dest_int.tex", replace tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", Spec, "Dest Int", SE, "`cluster_lbl'") dec(4) nocons
        }
        else {
            outreg2 using "`filename_base'_dest_int.tex", append tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", Spec, "Dest Int", SE, "`cluster_lbl'") dec(4) nocons
        }
    }

    * --- Bilateral interactions (FE 5-7) ---
    forval f = 5/7 {
        local fe "${fe`f'}"
        local fl "${fel`f'}"
        local ivb "`mv' `mv'_X_lndist `mv'_X_contig `mv'_X_fta_wto ln_dist contig fta_wto"
        reghdfe `dv' `ivb', absorb(`fe') vce(cluster `cluster_id')
        if `f' == 5 {
            outreg2 using "`filename_base'_bilat_int.tex", replace tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", Spec, "Bilat Int", SE, "`cluster_lbl'") dec(4) nocons
        }
        else {
            outreg2 using "`filename_base'_bilat_int.tex", append tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", Spec, "Bilat Int", SE, "`cluster_lbl'") dec(4) nocons
        }
    }
end

use "$int\collapsed_ody.dta", clear

foreach mv in share_mne_value share_mne_nfirms share_ext_nfirms share_dom_nfirms share_total_nfirms {
    cap {
        gen `mv'_X_lngdppc_d = `mv' * ln_gdpcap_d
        gen `mv'_X_lnpop_d   = `mv' * ln_pop_d
        gen `mv'_X_lndist    = `mv' * ln_dist
        gen `mv'_X_contig    = `mv' * contig
        gen `mv'_X_fta_wto   = `mv' * fta_wto
    }
}

foreach mne_def in ext total {
    if "`mne_def'" == "ext" local mv_list "share_mne_value share_mne_nfirms"
    else                    local mv_list "share_total_nfirms"
    foreach mv of local mv_list {
        foreach dv in ln_total_value positive_trade total_value {
            run_agg_spec `dv' `mv' ///
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

capture program drop run_agg_spec_odpy
program define run_agg_spec_odpy
    args dv mv filename_base cluster_id cluster_lbl

    local nfe = ${nfe_odpy}

    * --- Baseline (9-spec) ---
    forval i = 1/`nfe' {
        local fe "${fe_odpy`i'}"
        local fl "${fel_odpy`i'}"
        if "`fe'" == "" reg `dv' `mv', robust
        else            reghdfe `dv' `mv', absorb(`fe') vce(cluster `cluster_id')
        if `i' == 1 {
            outreg2 using "`filename_base'_baseline.tex", replace tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", Spec, "Baseline", SE, "`cluster_lbl'") dec(4) nocons
        }
        else {
            outreg2 using "`filename_base'_baseline.tex", append tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", Spec, "Baseline", SE, "`cluster_lbl'") dec(4) nocons
        }
    }

    * --- Product interactions (3 FE specs) ---
    local first = 1
    foreach fe in "ot_id dt_id" "od_id year" "ot_id dt_id od_id" {
        if "`fe'" == "ot_id dt_id"       local fl "OxT + DxT"
        if "`fe'" == "od_id year"        local fl "OD x Year"
        if "`fe'" == "ot_id dt_id od_id" local fl "OxT + DxT + OD"
        local ivp "`mv' `mv'_X_upstream `mv'_X_sigma `mv'_X_complex upstreamness sigma complexity"
        reghdfe `dv' `ivp', absorb(`fe') vce(cluster `cluster_id')
        if `first' == 1 {
            outreg2 using "`filename_base'_prod_int.tex", replace tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", Spec, "Prod Int", SE, "`cluster_lbl'") dec(4) nocons
            local first = 0
        }
        else {
            outreg2 using "`filename_base'_prod_int.tex", append tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", Spec, "Prod Int", SE, "`cluster_lbl'") dec(4) nocons
        }
    }
end

use "$int\collapsed_odpy.dta", clear

foreach mv in share_mne_value share_mne_nfirms share_ext_nfirms share_dom_nfirms share_total_nfirms {
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
    if "`mne_def'" == "ext" local mv_list "share_mne_value share_mne_nfirms"
    else                    local mv_list "share_total_nfirms"
    foreach mv of local mv_list {
        foreach dv in ln_total_value positive_trade total_value {
            run_agg_spec_odpy `dv' `mv' ///
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
* 2.2  GRAVITY REGRESSIONS
**********************************************************************

*===============================================================
* 2.2.A  Firm-Destination-Year
*===============================================================

capture program drop run_gravity_fdy
program define run_gravity_fdy
    args dv gvars mv dv2 filename cluster_id cluster_lbl
    forval f = 1/7 {
        local fe "${fe`f'}"
        local fl "${fel`f'}"
        if `f' == 1 reg `dv' `gvars', robust
        else        reghdfe `dv' `gvars', absorb(`fe') vce(cluster `cluster_id')
        if `f' == 1 {
            outreg2 using "`filename'", replace tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", Spec, "Baseline", SE, "`cluster_lbl'") dec(4) nocons
        }
        else {
            outreg2 using "`filename'", append tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", Spec, "Baseline", SE, "`cluster_lbl'") dec(4) nocons
        }
    }
    foreach f in 5 7 {
        local fe "${fe`f'}"
        local fl "${fel`f'}"
        local ivd "`mv'_X_lndist `dv2'_X_lndist `mv'_X_lngdppc_d `dv2'_X_lngdppc_d `mv'_X_lnpop_d `dv2'_X_lnpop_d `mv'"
        reghdfe `dv' `ivd', absorb(`fe') vce(cluster `cluster_id')
        outreg2 using "`filename'", append tex(frag) label ctitle("`fl'") ///
            addtext(FE, "`fl'", Spec, "Dest Int", SE, "`cluster_lbl'") dec(4) nocons
    }
end

use "$int\firm_dest_year_level.dta", clear

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

foreach mne_def in ext total {
    if "`mne_def'" == "ext" {
        local mv  "MNE"
        local dv2 "DOM"
    }
    else {
        local mv  "MNE_total"
        local dv2 "DOM_total"
    }
    local gvars "`mv'_X_lndist `dv2'_X_lndist `mv'_X_contig `dv2'_X_contig `mv'_X_comlang `dv2'_X_comlang `mv'_X_colony `dv2'_X_colony `mv'_X_fta_wto `dv2'_X_fta_wto `mv'"
    foreach dv in ln_exports positive_trade firm_dest_exports {
        run_gravity_fdy `dv' "`gvars'" `mv' `dv2' ///
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
    forval i = 1/`nfe' {
        local fe "${fe_odpy`i'}"
        local fl "${fel_odpy`i'}"
        if "`fe'" == "" reg `dv' `gvars', robust
        else            reghdfe `dv' `gvars', absorb(`fe') vce(cluster `cluster_id')
        if `i' == 1 {
            outreg2 using "`filename_base'_baseline.tex", replace tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", Spec, "Baseline", SE, "`cluster_lbl'") dec(4) nocons
        }
        else {
            outreg2 using "`filename_base'_baseline.tex", append tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", Spec, "Baseline", SE, "`cluster_lbl'") dec(4) nocons
        }
    }
    local first = 1
    foreach fe in "ot_id dt_id" "ot_id dt_id od_id" {
        if "`fe'" == "ot_id dt_id"       local fl "OxT + DxT"
        if "`fe'" == "ot_id dt_id od_id" local fl "OxT + DxT + OD"
        local ivp "`mv'_X_lndist `dv2'_X_lndist `mv'_X_upstream `dv2'_X_upstream `mv'_X_sigma `dv2'_X_sigma `mv'_X_complex `dv2'_X_complex `mv'"
        reghdfe `dv' `ivp', absorb(`fe') vce(cluster `cluster_id')
        if `first' == 1 {
            outreg2 using "`filename_base'_prod_int.tex", replace tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", Spec, "Prod Int", SE, "`cluster_lbl'") dec(4) nocons
            local first = 0
        }
        else {
            outreg2 using "`filename_base'_prod_int.tex", append tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", Spec, "Prod Int", SE, "`cluster_lbl'") dec(4) nocons
        }
    }
end

use "$int\firm_level_data_full.dta", clear

gen ln_exports      = ln(value_fob) if value_fob > 0
gen byte positive_trade = 1
label var ln_exports "Ln firm agro exports (product-dest-year)"

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
    else {
        local mv  "MNE_total"
        local dv2 "DOM_total"
    }
    local gvars "`mv'_X_lndist `dv2'_X_lndist `mv'_X_contig `dv2'_X_contig `mv'_X_fta_wto `dv2'_X_fta_wto `mv'"
    foreach dv in ln_exports positive_trade value_fob {
        run_gravity_fdpy `dv' "`gvars'" `mv' `dv2' ///
            "$r_s2\reg_2_2_grav_fdpy_`mne_def'_`dv'" ///
            "odp_id" "Orig-Dest-Prod"
        foreach suf in baseline prod_int {
            copy "$r_s2\reg_2_2_grav_fdpy_`mne_def'_`dv'_`suf'.tex" ///
                 "$ol_r_s2\reg_2_2_grav_fdpy_`mne_def'_`dv'_`suf'.tex", replace
        }
    }
}


**********************************************************************
* 2.3  MNE NETWORK REGRESSIONS
**********************************************************************

capture program drop run_network_spec
program define run_network_spec
    args dv dvars filename cluster_id cluster_lbl decomp
    forval f = 1/7 {
        local fe "${fe`f'}"
        local fl "${fel`f'}"
        if `f' == 1 reg `dv' `dvars', robust
        else        reghdfe `dv' `dvars', absorb(`fe') vce(cluster `cluster_id')
        if `f' == 1 {
            outreg2 using "`filename'", replace tex(frag) label ctitle("D`decomp'") ///
                addtext(FE, "`fl'", SE, "`cluster_lbl'") dec(4) nocons
        }
        else {
            outreg2 using "`filename'", append tex(frag) label ctitle("D`decomp'") ///
                addtext(FE, "`fl'", SE, "`cluster_lbl'") dec(4) nocons
        }
    }
end

use "$int\firm_dest_year_level.dta", clear

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

gen MNE_Pres_X_dist    = MNE * MNE_present_dest    * ln_dist
gen MNE_NotPres_X_dist = MNE * MNE_notpresent_dest * ln_dist
gen DOM_X_dist         = DOM * ln_dist
gen MNE_HQ_X_dist      = MNE * MNE_HQ_dest         * ln_dist
gen MNE_Aff_X_dist     = MNE * MNE_aff_dest        * ln_dist
gen MNE_NotPr_X_dist   = MNE * MNE_notpresent_dest  * ln_dist
gen MNE_Neigh_X_dist   = MNE * MNE_neighbor_dest   * ln_dist
gen MNE_NoPr3_X_dist   = MNE * (MNE_notpresent_dest==1 & MNE_neighbor_dest==0) * ln_dist

local d1 "MNE_Pres_X_dist MNE_NotPres_X_dist DOM_X_dist"
local d2 "MNE_HQ_X_dist MNE_Aff_X_dist MNE_NotPr_X_dist DOM_X_dist"
local d3 "MNE_HQ_X_dist MNE_Aff_X_dist MNE_Neigh_X_dist MNE_NoPr3_X_dist DOM_X_dist"

foreach mne_def in ext total {
    foreach dv in ln_exports firm_dest_exports {
        forval d = 1/3 {
            run_network_spec `dv' "`d`d''" ///
                "$r_s2\reg_2_3_net_D`d'_`mne_def'_`dv'.tex" ///
                "od_id" "Origin-Destination" `d'
            copy "$r_s2\reg_2_3_net_D`d'_`mne_def'_`dv'.tex" ///
                 "$ol_r_s2\reg_2_3_net_D`d'_`mne_def'_`dv'.tex", replace
        }
    }
}


**********************************************************************
* BLOCK E — CONCENTRATION DESCRIPTIVES (before §2.4 regressions)
**********************************************************************

use "$int\collapsed_ody.dta", clear
gen byte mne_present = (share_mne_nfirms > 0) if !missing(share_mne_nfirms)
label define mne_pres_lbl 0 "No MNE" 1 "MNE Present", replace
label values mne_present mne_pres_lbl

* Figure E1: Concentration by MNE presence, per country
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
                bar(1, color($c_MNE)) bar(2, color(orange*0.8)) bar(3, color(navy*0.6)) ///
                legend(on order(1 "Top-1" 2 "Top-3" 3 "Top-5") ///
                       position(6) rows(1) size(small) region(lcolor(white))) ///
                ytitle("Mean Concentration Share") ///
                title("`c' Agro: Concentration by MNE Presence", size(medium)) ///
                bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
            export_graph "fig_2_4_conc_mne_present_`c'" "$g24" "$ol_g24"
        }
    restore
}

* Figure E2: Pooled scatter — top-1 concentration vs ln(#firms)
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
            ytitle("Top-1 Agro Exporter Share") ///
            xtitle("Ln(# Agro Exporters in Cell)") ///
            legend(on order(1 "No MNE" 2 "MNE Present") ///
                   position(6) rows(1) size(small) region(lcolor(white))) ///
            title("Agro Concentration vs. Market Size: MNE vs. No-MNE", size(medium)) ///
            $gro
        export_graph "fig_2_4_conc_over_nfirms" "$g24" "$ol_g24"
    }
restore


**********************************************************************
* 2.4  CONCENTRATION PATTERNS
**********************************************************************

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
                addtext(FE, "`fl'", SE, "`cluster_lbl'") dec(4) nocons
        }
        else {
            outreg2 using "`filename'", append tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", SE, "`cluster_lbl'") dec(4) nocons
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
            run_conc_ody `dv' `mv' ///
                "$r_s2\reg_2_4_conc_ody_`mne_def'_`mv'_`dv'.tex" ///
                "od_id" "Origin-Destination"
            copy "$r_s2\reg_2_4_conc_ody_`mne_def'_`mv'_`dv'.tex" ///
                 "$ol_r_s2\reg_2_4_conc_ody_`mne_def'_`mv'_`dv'.tex", replace
        }
    }
}

* ODPY
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
                addtext(FE, "`fl'", Spec, "Baseline", SE, "`cluster_lbl'") dec(4) nocons
        }
        else {
            outreg2 using "`filename'", append tex(frag) label ctitle("`fl'") ///
                addtext(FE, "`fl'", Spec, "Baseline", SE, "`cluster_lbl'") dec(4) nocons
        }
    }
end

capture program drop run_conc_odpy_int
program define run_conc_odpy_int
    args dv mv filename cluster_id cluster_lbl
    local first = 1
    foreach ivar in lngdppc_d lndist upstream sigma {
        reghdfe `dv' `mv' `mv'_X_`ivar', ///
            absorb(ot_id dt_id) vce(cluster `cluster_id')
        if `first' == 1 {
            outreg2 using "`filename'", replace tex(frag) label ctitle("`ivar'") ///
                addtext(FE, "OxT+DxT", Interact, "`ivar'", SE, "`cluster_lbl'") dec(4) nocons
            local first = 0
        }
        else {
            outreg2 using "`filename'", append tex(frag) label ctitle("`ivar'") ///
                addtext(FE, "OxT+DxT", Interact, "`ivar'", SE, "`cluster_lbl'") dec(4) nocons
        }
    }
end

use "$int\collapsed_odpy.dta", clear

foreach mv in share_mne_value share_mne_nfirms share_total_nfirms {
    cap {
        gen `mv'_X_lngdppc_d = `mv' * ln_gdpcap_d
        gen `mv'_X_lndist    = `mv' * ln_dist
        gen `mv'_X_upstream  = `mv' * upstreamness
        gen `mv'_X_sigma     = `mv' * sigma
    }
}

local dep_conc_p "share_top1_all_p share_top3_all_p share_top5_all_p ln_n_exp_all_p"

foreach mne_def in ext total {
    if "`mne_def'" == "ext"   local mv_list "share_mne_value share_mne_nfirms"
    else                       local mv_list "share_`mne_def'_nfirms"
    foreach mv of local mv_list {
        foreach dv of local dep_conc_p {
            run_conc_odpy `dv' `mv' ///
                "$r_s2\reg_2_4_conc_odpy_`mne_def'_`mv'_`dv'.tex" ///
                "odp_id" "Orig-Dest-Prod"
            run_conc_odpy_int `dv' `mv' ///
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
* 2.5  EXTENSIVE MARGIN: COUNTRY-PRODUCT LEVEL
**********************************************************************

* KDE plots: MNE share distribution across country-product cells
use "$int\collapsed_opy.dta", clear

preserve
    drop if missing(share_mne_value)
    levelsof year, local(years)
    foreach mne_def in ext total {
        if "`mne_def'" == "ext"   local sv "share_mne_value"
        if "`mne_def'" == "total" local sv "share_total_nfirms"
        foreach y of local years {
            cap {
                kdensity `sv' if year == `y', ///
                    kernel(epanechnikov) bwidth(0.05) ///
                    title("MNE_`mne_def' Agro Share Distribution, `y'", size(medium)) ///
                    xtitle("MNE Share") ytitle("Density") ///
                    lcolor("$c_MNE") $gro
                export_graph "fig_2_5_kdens_sh_mne_`mne_def'_`y'" "$g25" "$ol_g25"
            }
        }
    }
restore

* New product introduction regressions (OPY)
capture program drop run_newprod_opy
program define run_newprod_opy
    args keepvars filename
    reghdfe new_product_orig `keepvars', absorb(op_id year) vce(cluster op_id)
    outreg2 using "$r_s2\\`filename'.tex", replace tex(frag) label ctitle("OP + Year") ///
        keep(`keepvars') ///
        addtext(OP FE, Yes, OT FE, No, PT FE, No, Interactions, No) dec(4) nocons

    reghdfe new_product_orig `keepvars', absorb(op_id ot_id) vce(cluster op_id)
    outreg2 using "$r_s2\\`filename'.tex", append tex(frag) label ctitle("OP + OxT") ///
        keep(`keepvars') ///
        addtext(OP FE, Yes, OT FE, Yes, PT FE, No, Interactions, No) dec(4) nocons

    reghdfe new_product_orig `keepvars', absorb(op_id ot_id pt_id) vce(cluster op_id)
    outreg2 using "$r_s2\\`filename'.tex", append tex(frag) label ctitle("OP + OxT + PxT") ///
        keep(`keepvars') ///
        addtext(OP FE, Yes, OT FE, Yes, PT FE, Yes, Interactions, No) dec(4) nocons

    reghdfe new_product_orig `keepvars' only_mne_X_upsm both_X_upsm upstreamness, ///
        absorb(op_id ot_id) vce(cluster op_id)
    outreg2 using "$r_s2\\`filename'.tex", append tex(frag) label ctitle("x Upstream") ///
        keep(`keepvars' only_mne_X_upsm both_X_upsm upstreamness) ///
        addtext(OP FE, Yes, OT FE, Yes, PT FE, No, Interactions, Upstream) dec(4) nocons

    copy "$r_s2\\`filename'.tex" "$ol_r_s2\\`filename'.tex", replace
end

capture program drop run_newprod_odpy
program define run_newprod_odpy
    args keepvars filename
    reghdfe new_product_od `keepvars', absorb(odp_id year) vce(cluster odp_id)
    outreg2 using "$r_s2\\`filename'.tex", replace tex(frag) label ctitle("ODP + Year") ///
        keep(`keepvars') ///
        addtext(ODP FE, Yes, OT FE, No, DT FE, No, PT FE, No, Interactions, No) dec(4) nocons

    reghdfe new_product_od `keepvars', absorb(odp_id ot_id dt_id) vce(cluster odp_id)
    outreg2 using "$r_s2\\`filename'.tex", append tex(frag) label ctitle("ODP + OxT + DxT") ///
        keep(`keepvars') ///
        addtext(ODP FE, Yes, OT FE, Yes, DT FE, Yes, PT FE, No, Interactions, No) dec(4) nocons

    reghdfe new_product_od `keepvars', absorb(odp_id ot_id dt_id pt_id) vce(cluster odp_id)
    outreg2 using "$r_s2\\`filename'.tex", append tex(frag) label ctitle("ODP + OxT + DxT + PxT") ///
        keep(`keepvars') ///
        addtext(ODP FE, Yes, OT FE, Yes, DT FE, Yes, PT FE, Yes, Interactions, No) dec(4) nocons

    reghdfe new_product_od `keepvars' only_mne_X_lndist both_X_lndist ln_dist, ///
        absorb(odp_id ot_id dt_id) vce(cluster odp_id)
    outreg2 using "$r_s2\\`filename'.tex", append tex(frag) label ctitle("x Distance") ///
        keep(`keepvars' only_mne_X_lndist both_X_lndist ln_dist) ///
        addtext(ODP FE, Yes, OT FE, Yes, DT FE, Yes, PT FE, No, Interactions, Dist) dec(4) nocons

    reghdfe new_product_od `keepvars' only_mne_X_upsm both_X_upsm upstreamness, ///
        absorb(odp_id ot_id dt_id) vce(cluster odp_id)
    outreg2 using "$r_s2\\`filename'.tex", append tex(frag) label ctitle("x Upstream") ///
        keep(`keepvars' only_mne_X_upsm both_X_upsm upstreamness) ///
        addtext(ODP FE, Yes, OT FE, Yes, DT FE, Yes, PT FE, No, Interactions, Upstream) dec(4) nocons

    copy "$r_s2\\`filename'.tex" "$ol_r_s2\\`filename'.tex", replace
end

* OPY new-product regressions
use "$int\firm_level_data_full.dta", clear

preserve
    gcollapse (max) new_product_orig new_prod_only_mne new_prod_both ///
              (firstnm) upstreamness sigma complexity, ///
              by(country_orig hs6 year) labelformat(#sourcelabel#)
    replace new_prod_only_mne = 0 if missing(new_prod_only_mne)
    replace new_prod_both     = 0 if missing(new_prod_both)
    egen op_id = group(country_orig hs6)
    egen ot_id = group(country_orig year)
    egen pt_id = group(hs6 year)
    gen only_mne_X_upsm = new_prod_only_mne * upstreamness
    gen both_X_upsm     = new_prod_both     * upstreamness
    run_newprod_opy "new_prod_only_mne new_prod_both" "reg_2_5_newprod_opy"
restore

* ODPY new-product regressions
use "$int\firm_level_data_full.dta", clear

preserve
    gcollapse (max) new_product_od new_prod_only_mne_od new_prod_both_od ///
              (firstnm) ln_dist contig fta_wto upstreamness sigma complexity, ///
              by(country_orig country_dest hs6 year) labelformat(#sourcelabel#)
    replace new_prod_only_mne_od = 0 if missing(new_prod_only_mne_od)
    replace new_prod_both_od     = 0 if missing(new_prod_both_od)
    egen odp_id = group(country_orig country_dest hs6)
    egen ot_id  = group(country_orig year)
    egen dt_id  = group(country_dest year)
    egen pt_id  = group(hs6 year)
    gen only_mne_X_lndist = new_prod_only_mne_od * ln_dist
    gen both_X_lndist     = new_prod_both_od     * ln_dist
    gen only_mne_X_upsm   = new_prod_only_mne_od * upstreamness
    gen both_X_upsm       = new_prod_both_od     * upstreamness
    run_newprod_odpy "new_prod_only_mne_od new_prod_both_od" "reg_2_5_newprod_odpy"
restore


**********************************************************************
* 2.6  EXTENSIVE MARGIN: FIRM LEVEL
**********************************************************************

capture program drop run_firm_level
program define run_firm_level
    args mnevar filename
    local dep_firm "ln_firm_exports ln_n_destinations ln_exp_per_dest ln_n_products ln_exp_per_prod ln_avg_dist"
    local first = 1

    foreach dv of local dep_firm {
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

        reghdfe `dv' `mnevar', absorb(ot_id sect_id) vce(cluster orig_id)
        outreg2 using "$r_s2\\`filename'.tex", append tex(frag) ///
            ctitle("No Size: OxT+Sect") keep(`mnevar') dec(4) nocons

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
                absorb(ot_id sect_id) vce(cluster orig_id)
            outreg2 using "$r_s2\\`filename'.tex", append tex(frag) ///
                ctitle("+Size: OxT+Sect") keep(`mnevar' ln_firm_exports) dec(4) nocons
        }
    }
end

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

foreach mne_def in ext total {
    if "`mne_def'" == "ext"   local mne_d "MNE"
    if "`mne_def'" == "total" local mne_d "MNE_total"

    * Firm-Year
    use "$int\firm_year_level.dta", clear
    cap confirm variable `mne_d'
    if _rc != 0 {
        di as error "Variable `mne_d' not found — skipping `mne_def'"
        continue
    }
    run_firm_level "`mne_d'" "reg_2_6_firm_`mne_def'"

    * Firm-Destination-Year
    use "$int\firm_dest_year_level.dta", clear
    merge m:1 firm_id year using "$int\firm_year_level.dta", ///
        keepusing(ln_firm_exports) keep(1 3) nogen
    rename ln_firm_exports ln_total_firm_exp
    run_fmd_level "`mne_d'" "reg_2_6_fmd_`mne_def'"

    * Firm-Product-Year
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

    * Copy all to Overleaf
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

* Table 3.1: Key statistics by origin country
use "$int\firm_level_data.dta", clear

preserve
    gcollapse ///
        (sum)   total_value = value_fob ///
        (count) n_obs       = value_fob ///
        (sum)   n_mne       = MNE_ext n_dom = DOM_ext ///
                n_mne_dom   = MNE_dom  n_mne_total = MNE_total, ///
        by(country_orig year) labelformat(#sourcelabel#)
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


* Table 3.2: Summary statistics — ODY regression variables
use "$int\collapsed_ody.dta", clear

estpost sum share_mne_value share_ext_nfirms share_dom_nfirms share_total_nfirms ///
            total_value n_firms ln_total_value ln_dist contig fta_wto, d
esttab using "$t_s3\tab_3_2_sumstats_ody.tex", replace ///
    cells("mean(fmt(%9.3f)) sd(fmt(%9.3f)) p50(fmt(%9.3f)) min(fmt(%9.3f)) max(fmt(%9.3f)) count(fmt(%12.0fc))") ///
    nomtitle nonumber label
copy "$t_s3\tab_3_2_sumstats_ody.tex" "$ol_t_s3\tab_3_2_sumstats_ody.tex", replace


* Table 3.3: Summary statistics — ODPY regression variables
use "$int\collapsed_odpy.dta", clear

estpost sum share_mne_value share_ext_nfirms share_dom_nfirms share_total_nfirms ///
            total_value n_firms ln_total_value ln_dist contig fta_wto ///
            upstreamness sigma complexity quality_ladder rca, d
esttab using "$t_s3\tab_3_3_sumstats_odpy.tex", replace ///
    cells("mean(fmt(%9.3f)) sd(fmt(%9.3f)) p50(fmt(%9.3f)) min(fmt(%9.3f)) max(fmt(%9.3f)) count(fmt(%12.0fc))") ///
    nomtitle nonumber label
copy "$t_s3\tab_3_3_sumstats_odpy.tex" "$ol_t_s3\tab_3_3_sumstats_odpy.tex", replace


* Table 3.4 (NEW): Summary statistics by agro section
use "$int\collapsed_odpy.dta", clear

forval s = 1/4 {
    local slbl : label agro_sect_lbl `s'
    preserve
        keep if hs_section == `s'
        estpost sum share_mne_value share_ext_nfirms share_total_nfirms ///
                    total_value n_firms ln_total_value ln_dist contig, d
        if `s' == 1 {
            esttab using "$t_s3\tab_3_4_sumstats_by_section.tex", replace ///
                cells("mean(fmt(%9.3f)) sd(fmt(%9.3f)) p50(fmt(%9.3f)) count(fmt(%9.0fc))") ///
                nomtitle nonumber label ///
                title("Section `s': `slbl'")
        }
        else {
            esttab using "$t_s3\tab_3_4_sumstats_by_section.tex", append ///
                cells("mean(fmt(%9.3f)) sd(fmt(%9.3f)) p50(fmt(%9.3f)) count(fmt(%9.0fc))") ///
                nomtitle nonumber label ///
                title("Section `s': `slbl'")
        }
    restore
}
copy "$t_s3\tab_3_4_sumstats_by_section.tex" ///
     "$ol_t_s3\tab_3_4_sumstats_by_section.tex", replace


* Table 3.5: Correlation matrix — product characteristics × MNE share
use "$int\collapsed_opy.dta", clear

estpost pwcorr share_mne_value upstreamness sigma complexity ///
               quality_ladder rca rhci, star(0.05)
esttab using "$t_s3\tab_3_5_prodchar_corr.tex", replace ///
    cells("b(fmt(%9.3f) star)") ///
    collabels(none) nonumber nomtitle label ///
    note("* p<0.05. Correlation of MNE share and agro product characteristics.") ///
    title("Correlation: MNE Share and Product Characteristics (Agro)")
copy "$t_s3\tab_3_5_prodchar_corr.tex" "$ol_t_s3\tab_3_5_prodchar_corr.tex", replace


* Table 3.6 (NEW): MNE participation counts by section and country
use "$int\firm_level_data.dta", clear

preserve
    gcollapse ///
        (count) n_obs     = value_fob ///
        (sum)   n_mne_ext = MNE_ext   n_mne_tot = MNE_total ///
        (sum)   agro_exp  = value_fob, ///
        by(country_orig hs_section) labelformat(#sourcelabel#)
    gen mne_ext_share = n_mne_ext / n_obs
    gen mne_tot_share = n_mne_tot / n_obs
    label values hs_section agro_sect_lbl
    estpost tabstat agro_exp n_obs n_mne_ext mne_ext_share n_mne_tot mne_tot_share, ///
        statistics(mean) columns(statistics) by(hs_section)
    esttab using "$t_s3\tab_3_6_mne_by_section.tex", replace ///
        cells("mean(fmt(%9.3f))") ///
        nomtitle nonumber label ///
        title("MNE Participation by Agricultural Section")
    copy "$t_s3\tab_3_6_mne_by_section.tex" ///
         "$ol_t_s3\tab_3_6_mne_by_section.tex", replace
restore


* Table 3.7 (NEW): Firm profile comparison by MNE status × agro section
use "$int\firm_year_level.dta", clear

local first_s = 1
forval s = 1/4 {
    local slbl : label agro_sect_lbl `s'
    preserve
        keep if hs_section == `s'
        levelsof country_orig, local(ctry_list_s)
        foreach c of local ctry_list_s {
            cap {
                eststo mne_s`s'_`c': quietly estpost tabstat ///
                    ln_firm_exports n_destinations n_products ///
                    if MNE == 1 & country_orig == "`c'", ///
                    statistics(mean sd) columns(statistics)
                eststo dom_s`s'_`c': quietly estpost tabstat ///
                    ln_firm_exports n_destinations n_products ///
                    if MNE == 0 & country_orig == "`c'", ///
                    statistics(mean sd) columns(statistics)
                if `first_s' == 1 {
                    esttab mne_s`s'_`c' dom_s`s'_`c' using ///
                        "$t_s3\tab_3_7_firm_profile_by_section.tex", ///
                        replace cells("mean(fmt(%9.2f)) sd(fmt(%9.2f))") ///
                        mtitle("MNE" "Domestic") title("Sect `s': `slbl' — `c'") label noobs
                    local first_s = 0
                }
                else {
                    esttab mne_s`s'_`c' dom_s`s'_`c' using ///
                        "$t_s3\tab_3_7_firm_profile_by_section.tex", ///
                        append cells("mean(fmt(%9.2f)) sd(fmt(%9.2f))") ///
                        mtitle("MNE" "Domestic") title("Sect `s': `slbl' — `c'") label noobs
                }
            }
        }
    restore
}
copy "$t_s3\tab_3_7_firm_profile_by_section.tex" ///
     "$ol_t_s3\tab_3_7_firm_profile_by_section.tex", replace


**********************************************************************
* COMPLETION MESSAGE
**********************************************************************

di as text ""
di as text "============================================================"
di as text "  AGRO ANALYSIS COMPLETED"
di as text "  HS2 chapters 1-24 | Sections I-IV"
di as text "============================================================"
di as text "  Root           -> $agro_root"
di as text "  Intermediate   -> $int"
di as text "  Graphs (local) -> $graphs"
di as text "  Graphs (Ovlf)  -> $overleaf\Graphs"
di as text "  Tables (local) -> $tables"
di as text "  Tables (Ovlf)  -> $overleaf\Tables"
di as text "  Regs   (local) -> $regs"
di as text "  Regs   (Ovlf)  -> $overleaf\Regressions"
di as text "  Agro Sections  -> $g15 | $ol_g15"
di as text "============================================================"
di as text ""
di as text "  NEW FIGURES (Block 1.5):"
di as text "  1.5.A  fig_1_5_1  MNE share by agro section (pooled)"
di as text "  1.5.B  fig_1_5_2  MNE share by section over time"
di as text "  1.5.C  fig_1_5_3  MNE share by HS2 chapter"
di as text "  1.5.D  fig_1_5_4  Value composition by section x MNE/DOM"
di as text "  1.5.E  fig_1_5_5  Exporter counts by section x year"
di as text "  1.5.F  fig_1_5_6  Country x section MNE share matrix"
di as text "  1.5.G  fig_1_5_7  Section x destination region MNE share"
di as text "  1.5.H  fig_1_5_8  Boxplot: firm size by section x MNE"
di as text "  1.5.I  fig_1_5_9  Bubble: HS2 importance vs MNE share"
di as text "  1.5.J  fig_1_5_10 Country agro specialization stack"
di as text "  1.5.K  fig_1_5_11 Section trends by country (faceted)"
di as text "  NEW PARENT FIG: fig_1_4_5 Parent region x agro section"
di as text "  NEW TABLES: 3.4 (by section), 3.6, 3.7"
di as text "============================================================"
