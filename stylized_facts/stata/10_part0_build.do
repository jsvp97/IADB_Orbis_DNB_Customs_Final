**********************************************************************
* 10_part0_build.do
*
* PART 0 -- DATA PREPARATION
*
* Builds all analytical .dta files in $int from the project's raw inputs.
* The whole block is wrapped in /* */ -- uncomment on the first run only.
* After intermediates exist, skip this file and start at 20_part1_*.do.
*
* Inputs:  $customs\Base_final_Customs_DNB_Orbis_product_complete.dta (19 GB)
*          $product\..., $gravity\..., $country\..., $int\intermediate_mne_presence.dta
* Outputs (saved to $int):
*   firm_level_data.dta, firm_level_data_full.dta,
*   firm_year_level.dta, firm_dest_year_level.dta,
*   collapsed_ody.dta, collapsed_odpy.dta, collapsed_opy.dta, collapsed_oy.dta
*
* Called by 00_master.do after 01_setup.do.
**********************************************************************
**********************************************************************
**********************************************************************
*
*   PART 0: DATA PREPARATION
*   Uncomment this block on the FIRST run to build all .dta files.
*   After that it can stay commented to skip straight to Part 1.
*
**********************************************************************
**********************************************************************

/*

*----------------------------------------------------------------------
* 0.1  Load raw data
*----------------------------------------------------------------------
use "$customs\Base_final_Customs_DNB_Orbis_product_complete.dta", clear

replace value_fob=-value_fob if value_fob<0

tostring dunsnumber, replace
gen ID_Orbis_DNB = guo25
replace ID_Orbis_DNB = dunsnumber if _merge_DNB == 2


*----------------------------------------------------------------------
* 0.2  Three MNE definitions
*----------------------------------------------------------------------

* MNE_ext: foreign subsidiary (parent country differs from exporting country)
gen byte MNE_ext   = (_merge_DNB_Orbis == 3) & (iso3_parent != "") ///
                   & (iso3_parent != country_orig)
gen byte DOM_ext   = 1 - MNE_ext

* MNE_dom: domestic MNE (matched in corporate DB, parent = exporting country)
gen byte MNE_dom   = (_merge_DNB_Orbis == 3) & (iso3_parent == country_orig)
gen byte DOM_dom   = 1 - MNE_dom

* MNE_total: any firm matched in the corporate database
gen byte MNE_total = (_merge_DNB_Orbis == 3)
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
    "$product\product_characteristics_hs6_2002_adj.dta", ///
    keep(1 3) nogen
label var upstreamness  "Upstreamness (Antras-Chor)"
label var sigma         "Elasticity of Substitution (Broda-Weinstein)"
rename pci    complexity
rename ladder quality_ladder
label var complexity     "Product Complexity Index (Hausman-Hidalgo)"
label var quality_ladder "Quality Ladder (Khandelwal)"

* Revealed Comparative Advantage (WITS)
merge m:1 country_orig hs07_6d year using "$product\RCA_WITS_orig_year.dta", keep(1 3) nogen
label var rca "Revealed Comparative Advantage"

* Technology intensity: Lall (2000)
merge m:1 hs07_6d using "$product\lall2000_hs2007.dta", keep(1 3) nogen
rename lall2000_category lall2000
label var lall2000 "Technology Intensity (Lall 2000)"
encode lall2000, gen(tech_lall2000)

* Technology intensity: Lybbert & Zolas (IPC patent concordance)
merge m:1 hs07_6d using "$product\ALP_IPC_Patent_hs2007_6_to_ipc1.dta", keep(1 3) nogen
label var ipc1 "Technology Intensity (Lybbert-Zolas)"
encode ipc1, gen(tech_ipc1)

* Revealed Human Capital Intensity (UNCTAD)
merge m:1 hs07_6d using "$product\UNCTAD RHCI hs_2007_indices.dta", keep(1 3) nogen
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
    use "$gravity\Gravity_V202211.dta", clear
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
    use "$gravity\tariffsPairs_88_21_vbeta1-2024-12.dta", clear
    rename iso1 country_orig
    rename iso2 country_dest
    tempfile bilateral_tv
    save `bilateral_tv'
restore
merge m:1 country_orig country_dest year using `bilateral_tv', keep(1 3) nogen

* PTA, BIT, DTT (IDB bilateral agreements database)
merge m:1 country_orig country_dest year using "$gravity\PTA_BIT_DTT_BID.dta", keep(1 3) nogen

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
    use "$country\WB_Income_group.dta", clear
    rename (iso3 income_group) (country_orig income_group_orig)
    tempfile wdi_o
    save `wdi_o'
restore
merge m:1 country_orig using `wdi_o', keep(1 3) nogen

* World Bank income groups - destination
preserve
    use "$country\WB_Income_group.dta", clear
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
    , by(country_orig country_dest hs6 year)

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
    , by(country_orig country_dest year)

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
    , by(country_orig hs6 year)

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
    , by(country_orig year)

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
              ln_n_exp_dom, by(country_orig country_dest year)
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
              by(country_orig country_dest hs6 year)
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
    gcollapse (count) has_exp = value_fob, by(country_orig hs6 year)
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
        , by(firm_id country_orig year)

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
        , by(firm_id country_orig country_dest year)

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

    * FIX: was `gen avg_dist = mean(dist)` â€” mean() is an egen function
    bysort firm_id year: egen avg_dist = mean(dist)
    gen ln_avg_dist = ln(avg_dist)
    gcollapse (firstnm) ln_avg_dist, by(firm_id year)
    tempfile avg_d
    save `avg_d'
restore

use "$int\firm_year_level.dta", clear
merge 1:1 firm_id year using `avg_d', nogen
save "$int\firm_year_level.dta", replace

*/
*  ^^^ End of Part 0 ^^^
**********************************************************************
