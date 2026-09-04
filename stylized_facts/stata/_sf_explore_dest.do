**********************************************************************
* _sf_explore_dest.do
*
* EXPLORATION (not yet SF2): MNE_total value share across destination
* country cuts.
*
*   Cuts:
*     1. by destination income group (WB classification)
*     2. by destination region (LAC / NAM / Europe / Asia / Africa / RoW)
*     3. intra-regional (LAC dest) vs extra-regional
*     4. contiguous vs non-contiguous
*     5. by bilateral distance quintile
*     6. FTA member vs not
*     7. scatter: MNE_total share vs ln GDPpc_d (one point per destination)
*     8. top-20 destinations by total trade -- MNE_total share for each
*
* Builds (one-time) and reuses: $int\ody_value_cache.dta
*
* Outputs (local only, no Overleaf mirror yet):
*   2_Output\Graphs\Exploration_Dest\expl_dest_<cut>.{pdf,png,eps}
*   2_Output\Tables\Exploration_Dest\expl_dest_<cut>.tex
**********************************************************************

clear all
set more off

do "D:\MNEs_Trade\0_Code\01_setup.do"

global g_expdest "$graphs\Exploration_Dest"
global t_expdest "$tables\Exploration_Dest"
foreach dir in "$g_expdest" "$t_expdest" {
    cap mkdir `"`dir'"'
}


**********************************************************************
* STEP 1 -- Build (or refresh) the ODY value cache
**********************************************************************

local cache "$int\ody_value_cache.dta"

cap confirm file "`cache'"
if _rc != 0 {

    di as text _newline ">>> Building ODY cache from raw 19 GB customs file..."

    use country_orig country_dest year value_fob _merge_DNB_Orbis iso3_parent ///
        using "$customs\Base_final_Customs_DNB_Orbis_product_complete.dta", clear

    replace value_fob = -value_fob if value_fob < 0

    * Three MNE flags (using NEW MNE_ext convention)
    gen byte MNE_dom   = (_merge_DNB_Orbis == 3) & (iso3_parent == country_orig)
    gen byte MNE_total = (_merge_DNB_Orbis == 3)

    gen double val_total = value_fob * MNE_total
    gen double val_dom   = value_fob * MNE_dom
    gen double val_ext   = val_total - val_dom

    gcollapse (sum) total_value=value_fob val_ext val_dom val_total, ///
              by(country_orig country_dest year)

    * ---- Merge CEPII bilateral gravity ----
    preserve
        use "$gravity\Gravity_V202211.dta", clear
        rename iso3_o country_orig
        rename iso3_d country_dest
        keep country_orig country_dest year ///
             dist contig comlang_off fta_wto ///
             pop_d gdp_d gdpcap_d pop_o gdp_o gdpcap_o
        bysort country_orig country_dest year: keep if _n == 1
        gen ln_dist     = ln(dist)
        gen ln_gdpcap_d = ln(gdpcap_d)
        gen ln_pop_d    = ln(pop_d)
        gen ln_gdp_d    = ln(gdp_d)
        gen ln_gdpcap_o = ln(gdpcap_o)
        tempfile gravity
        save `gravity'
    restore
    merge m:1 country_orig country_dest year using `gravity', keep(1 3) nogen

    * ---- Merge WB income group (destination) ----
    preserve
        use "$country\WB_Income_group.dta", clear
        rename (iso3 income_group) (country_dest income_group_dest_str)
        tempfile wdi
        save `wdi'
    restore
    merge m:1 country_dest using `wdi', keep(1 3) nogen

    gen byte income_group_dest = .
    replace income_group_dest = 1 if income_group_dest_str == "Low income"
    replace income_group_dest = 2 if income_group_dest_str == "Lower middle income"
    replace income_group_dest = 3 if income_group_dest_str == "Upper middle income"
    replace income_group_dest = 4 if income_group_dest_str == "High income"
    label define income_lbl ///
        1 "Low" 2 "Lower-middle" 3 "Upper-middle" 4 "High", replace
    label values income_group_dest income_lbl
    drop income_group_dest_str

    * ---- LAC destination indicator + intra/extra regional ----
    gen byte LAC_dest = 0
    replace LAC_dest = 1 if inlist(country_dest, "ARG","BHS","BRB","BLZ","BOL")
    replace LAC_dest = 1 if inlist(country_dest, "BRA","CHL","COL","CRI","DOM")
    replace LAC_dest = 1 if inlist(country_dest, "ECU","SLV","GTM","GUY","HTI")
    replace LAC_dest = 1 if inlist(country_dest, "HND","JAM","MEX","NIC","PAN")
    replace LAC_dest = 1 if inlist(country_dest, "PRY","PER","SUR","TTO","URY","VEN")
    gen byte intra_regional = LAC_dest
    label define intra_lbl 0 "Extra-regional" 1 "Intra-regional (LAC)", replace
    label values intra_regional intra_lbl

    * ---- Destination region (coarse) ----
    *   inlist() with many string args hits "expression too long"; using
    *   foreach over local code-lists is more robust.
    gen dest_region = ""
    replace dest_region = "Latin America" if LAC_dest == 1

    local na_codes  "USA CAN"
    local oc_codes  "AUS NZL"
    local eu_codes  "AUT BEL BGR CYP CZE DNK EST FIN FRA DEU GRC HUN IRL ITA LVA LTU LUX MLT NLD POL PRT ROU SVK SVN ESP SWE GBR CHE NOR ISL UKR RUS TUR"
    local as_codes  "CHN HKG IND IDN JPN MYS PHL KOR SGP TWN THA VNM PAK BGD KAZ ARE SAU ISR LKA MMR"
    local af_codes  "DZA AGO BEN BWA BFA BDI CMR CPV CAF TCD COM COD COG CIV DJI EGY GNQ ERI ETH GAB GMB GHA GIN GNB KEN LSO LBR LBY MDG MWI MLI MRT MUS MAR MOZ NAM NER NGA RWA STP SEN SYC SLE SOM ZAF SSD SDN SWZ TZA TGO TUN UGA ZMB ZWE"

    foreach c of local na_codes { replace dest_region = "North America" if country_dest == "`c'" }
    foreach c of local oc_codes { replace dest_region = "Oceania"       if country_dest == "`c'" }
    foreach c of local eu_codes { replace dest_region = "Europe"        if country_dest == "`c'" }
    foreach c of local as_codes { replace dest_region = "Asia"          if country_dest == "`c'" }
    foreach c of local af_codes { replace dest_region = "Africa"        if country_dest == "`c'" }

    replace dest_region = "Rest of World" if dest_region == ""

    * ---- Distance categories ----
    qui sum dist, d
    gen byte dist_above_med = dist > r(p50) if !missing(dist)
    xtile dist_quintile = dist, nq(5)

    label define dmed_lbl 0 "Distance below median" 1 "Distance above median", replace
    label values dist_above_med dmed_lbl

    label var ln_gdpcap_d "Log GDP per capita (destination)"
    label var ln_pop_d    "Log population (destination)"
    label var ln_dist     "Log bilateral distance"
    label var fta_wto     "FTA / WTO member"

    compress
    save "`cache'", replace
    di as text ">>> Cache saved to `cache'"
}


**********************************************************************
* STEP 2 -- Load cache, apply exclusions, drop missing destinations
**********************************************************************

use "`cache'", clear

* Apply project-wide origin exclusions (ECU)
drop if inlist(country_orig, $excluded_origins)

* Filter out junk rows
drop if missing(country_dest) | total_value <= 0

qui count
di as text _newline ">>> ODY cache loaded (post-exclusions): " r(N) " origin-dest-year obs"
qui levelsof country_orig, local(cs) clean
di as text ">>> Origins kept: `cs'"
qui distinct country_dest
di as text ">>> Distinct destinations: " r(ndistinct)


**********************************************************************
* Helper: write a small share-by-category table as a tex fragment
**********************************************************************

cap program drop write_cut_table
program define write_cut_table
    args var label filename
    preserve
        gcollapse (sum) total_value val_total, by(`var')
        gen double share_total = val_total / total_value
        gsort `var'
        file open fh using "$t_expdest/`filename'.tex", write replace
        file write fh "\begin{tabular}{lcr}" _n
        file write fh "\toprule" _n
        * Compound quotes around the header so Stata doesn't try to expand
        * `$_{` as a global reference.
        file write fh `"`label' & MNE$_{\text{total}}$ share & Total value (\$bn) \\"' _n
        file write fh "\midrule" _n
        forvalues i = 1/`=_N' {
            local cat : label (`var') `=`var'[`i']'
            if "`cat'" == "" local cat = `var'[`i']
            local s : di %5.3f share_total[`i']
            local v : di %7.2f total_value[`i']/1e9
            file write fh "`cat' & `s' & `v' \\" _n
        }
        file write fh "\bottomrule" _n
        file write fh "\end{tabular}" _n
        file close fh
    restore
end


**********************************************************************
* STEP 3 -- Cut 1: by destination income group
**********************************************************************

preserve
    drop if missing(income_group_dest)
    gcollapse (sum) total_value val_total, by(income_group_dest)
    gen double share_total = val_total / total_value
    graph hbar (asis) share_total, ///
        over(income_group_dest, sort(income_group_dest) descending label(labsize(medium))) ///
        bar(1, color($c_MNEtot) lcolor($c_MNEtot)) ///
        ytitle("MNE-total share in export value", size(medsmall)) ///
        ylab(0(0.1)0.8, nogrid format(%9.1f)) ///
        blabel(bar, position(outside) format(%4.2f) size(small)) ///
        bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
    export_graph "expl_dest_income_group" "$g_expdest" "$g_expdest"
restore
write_cut_table income_group_dest "Destination income group" "expl_dest_income_group"


**********************************************************************
* STEP 4 -- Cut 2: by destination region
**********************************************************************

preserve
    encode dest_region, gen(dest_region_n)
    drop if missing(dest_region_n)
    gcollapse (sum) total_value val_total, by(dest_region_n)
    gen double share_total = val_total / total_value
    graph hbar (asis) share_total, ///
        over(dest_region_n, sort(share_total) descending label(labsize(medium))) ///
        bar(1, color($c_MNEtot) lcolor($c_MNEtot)) ///
        ytitle("MNE-total share in export value", size(medsmall)) ///
        ylab(0(0.1)0.8, nogrid format(%9.1f)) ///
        blabel(bar, position(outside) format(%4.2f) size(small)) ///
        bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
    export_graph "expl_dest_region" "$g_expdest" "$g_expdest"
restore
preserve
    encode dest_region, gen(dest_region_n)
    write_cut_table dest_region_n "Destination region" "expl_dest_region"
restore


**********************************************************************
* STEP 5 -- Cut 3: intra-regional (LAC dest) vs extra-regional
**********************************************************************

preserve
    drop if missing(intra_regional)
    gcollapse (sum) total_value val_total, by(intra_regional)
    gen double share_total = val_total / total_value
    graph hbar (asis) share_total, ///
        over(intra_regional, sort(share_total) descending label(labsize(medium))) ///
        bar(1, color($c_MNEtot) lcolor($c_MNEtot)) ///
        ytitle("MNE-total share in export value", size(medsmall)) ///
        ylab(0(0.1)0.8, nogrid format(%9.1f)) ///
        blabel(bar, position(outside) format(%4.2f) size(small)) ///
        bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
    export_graph "expl_dest_intra_regional" "$g_expdest" "$g_expdest"
restore
write_cut_table intra_regional "Intra/Extra-regional" "expl_dest_intra_regional"


**********************************************************************
* STEP 6 -- Cut 4: contiguous vs non-contiguous
**********************************************************************

preserve
    drop if missing(contig)
    gcollapse (sum) total_value val_total, by(contig)
    gen double share_total = val_total / total_value
    label define contig_lbl 0 "Non-contiguous" 1 "Contiguous", replace
    label values contig contig_lbl
    graph hbar (asis) share_total, ///
        over(contig, sort(share_total) descending label(labsize(medium))) ///
        bar(1, color($c_MNEtot) lcolor($c_MNEtot)) ///
        ytitle("MNE-total share in export value", size(medsmall)) ///
        ylab(0(0.1)0.8, nogrid format(%9.1f)) ///
        blabel(bar, position(outside) format(%4.2f) size(small)) ///
        bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
    export_graph "expl_dest_contig" "$g_expdest" "$g_expdest"
restore
preserve
    label define contig_lbl 0 "Non-contiguous" 1 "Contiguous", replace
    label values contig contig_lbl
    write_cut_table contig "Border-sharing" "expl_dest_contig"
restore


**********************************************************************
* STEP 7 -- Cut 5: by bilateral distance quintile
**********************************************************************

preserve
    drop if missing(dist_quintile)
    gcollapse (sum) total_value val_total, by(dist_quintile)
    gen double share_total = val_total / total_value
    graph hbar (asis) share_total, ///
        over(dist_quintile, sort(dist_quintile) label(labsize(medium))) ///
        bar(1, color($c_MNEtot) lcolor($c_MNEtot)) ///
        ytitle("MNE-total share in export value", size(medsmall)) ///
        b1title("Bilateral distance quintile (1 = closest)") ///
        ylab(0(0.1)0.8, nogrid format(%9.1f)) ///
        blabel(bar, position(outside) format(%4.2f) size(small)) ///
        bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
    export_graph "expl_dest_dist_quintile" "$g_expdest" "$g_expdest"
restore
write_cut_table dist_quintile "Distance quintile" "expl_dest_dist_quintile"


**********************************************************************
* STEP 8 -- Cut 6: FTA / WTO membership
**********************************************************************

preserve
    drop if missing(fta_wto)
    gcollapse (sum) total_value val_total, by(fta_wto)
    gen double share_total = val_total / total_value
    label define fta_lbl 0 "No FTA / WTO link" 1 "FTA / WTO member", replace
    label values fta_wto fta_lbl
    graph hbar (asis) share_total, ///
        over(fta_wto, sort(share_total) descending label(labsize(medium))) ///
        bar(1, color($c_MNEtot) lcolor($c_MNEtot)) ///
        ytitle("MNE-total share in export value", size(medsmall)) ///
        ylab(0(0.1)0.8, nogrid format(%9.1f)) ///
        blabel(bar, position(outside) format(%4.2f) size(small)) ///
        bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
    export_graph "expl_dest_fta" "$g_expdest" "$g_expdest"
restore
preserve
    label define fta_lbl 0 "No FTA / WTO link" 1 "FTA / WTO member", replace
    label values fta_wto fta_lbl
    write_cut_table fta_wto "FTA / WTO" "expl_dest_fta"
restore


**********************************************************************
* STEP 9 -- Cut 7: scatter MNE_total share vs ln GDPpc_d
*           (one point per destination, sized by total trade)
**********************************************************************

preserve
    * Collapse to destination level
    gcollapse (sum) total_value val_total ///
              (mean) ln_gdpcap_d, by(country_dest)
    gen double share_total = val_total / total_value
    drop if missing(ln_gdpcap_d) | total_value <= 0
    gen double weight = total_value / 1e9
    twoway ///
        (lfit share_total ln_gdpcap_d, lcolor(black)) ///
        (scatter share_total ln_gdpcap_d [aw=weight], ///
            mcolor($c_MNEtot) msymbol(O) mfcolor($c_MNEtot%50)), ///
        ytitle("MNE-total share in export value") ///
        xtitle("Log GDP per capita (destination)") ///
        ylab(0(0.2)1, nogrid format(%9.1f)) ///
        legend(off) $gro ///
        note("Marker size: total LAC9 export value to that destination", size(*0.7))
    export_graph "expl_dest_scatter_gdppc" "$g_expdest" "$g_expdest"
restore


**********************************************************************
* STEP 10 -- Cut 8: Top 20 destinations by total LAC9 export value
*            (MNE_total share for each)
**********************************************************************

preserve
    gcollapse (sum) total_value val_total, by(country_dest)
    gen double share_total = val_total / total_value
    gsort -total_value
    keep if _n <= 20
    graph hbar (asis) share_total, ///
        over(country_dest, sort(total_value) descending label(labsize(small))) ///
        bar(1, color($c_MNEtot) lcolor($c_MNEtot)) ///
        ytitle("MNE-total share in export value", size(medsmall)) ///
        b1title("Top 20 destinations by total LAC9 export value (descending)") ///
        ylab(0(0.1)1, nogrid format(%9.1f)) ///
        blabel(bar, position(outside) format(%4.2f) size(vsmall)) ///
        bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white)) ///
        ysize(7)
    export_graph "expl_dest_top20" "$g_expdest" "$g_expdest"

    * Save the top-20 list as a tex table
    file open fh using "$t_expdest/expl_dest_top20.tex", write replace
    file write fh "\begin{tabular}{lcc}" _n
    file write fh "\toprule" _n
    file write fh `"Destination & MNE$_{\text{total}}$ share & Total value (\$bn) \\"' _n
    file write fh "\midrule" _n
    forvalues i = 1/`=_N' {
        local cc = country_dest[`i']
        local s : di %5.3f share_total[`i']
        local v : di %7.2f total_value[`i']/1e9
        file write fh "`cc' & `s' & `v' \\" _n
    }
    file write fh "\bottomrule" _n
    file write fh "\end{tabular}" _n
    file close fh
restore


**********************************************************************
* DONE
**********************************************************************

di as text ""
di as text "==========================================================="
di as text "  Exploration outputs written:"
di as text "    Graphs -> $g_expdest"
di as text "    Tables -> $t_expdest"
di as text "==========================================================="
