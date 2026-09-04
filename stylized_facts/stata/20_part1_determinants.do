**********************************************************************
* 20_part1_determinants.do
*
* PART 1 -- DETERMINANTS OF MULTINATIONAL PRESENCE IN TRADE
*   1.1  Across exporting countries           [graphs + regressions]
*   1.2  Across export destination countries  [graphs + regressions]
*   1.3  By product                           [graphs + regressions]
*
* All three MNE definitions (ext / dom / total) used in every loop.
*
* Inputs:  $int\collapsed_oy.dta, $int\collapsed_ody.dta,
*          $int\collapsed_opy.dta, $int\collapsed_odpy.dta,
*          $int\firm_level_data.dta
* Outputs: $g11, $g12, $g13, $t_s1, $r_s1 (+ Overleaf mirrors)
*
* Called by 00_master.do after 01_setup.do (and 10_part0_build.do on first run).
**********************************************************************


**********************************************************************
**********************************************************************
*
*   PART 1: DETERMINANTS OF MULTINATIONAL PRESENCE IN TRADE
*
**********************************************************************
**********************************************************************


**********************************************************************
* 1.1  ACROSS EXPORTING COUNTRIES                         [Plan Â§1.1]
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
              , by(country_orig)

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
    foreach mne_def in ext dom total {
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
* FIGURE 1.1.2 â€“ MNE share vs. GDP per capita (scatter)
*---------------------------------------------------------------
foreach mne_def in ext dom total {
    if "`mne_def'" == "ext"   local sv "share_mne_value"
    if "`mne_def'" == "dom"   local sv "share_dom_nfirms"
    if "`mne_def'" == "total" local sv "share_total_nfirms"

    preserve
        gcollapse (mean) `sv' ln_gdpcap_o, by(country_orig)
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
* FIGURE 1.1.3 â€“ Top-10 home countries of MNE parents
*---------------------------------------------------------------
use "$int\firm_level_data.dta", clear

preserve
    keep if MNE_ext == 1
    gcollapse (sum) mne_exports = value_fob, by(home_country)
    egen double total_mne = total(mne_exports)
    gen share_home = mne_exports / total_mne

    gsort -share_home
    gen rank = _n
    gen country_label = home_country if rank <= 10
    replace country_label = "Rest" if rank > 10
    gcollapse (sum) share_home, by(country_label)
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
* 1.2  ACROSS EXPORT DESTINATION COUNTRIES               [Plan Â§1.2]
**********************************************************************

*===============================================================
* 1.2.A  Bar graphs â€” aggregate (one per category Ã— MNE def)
*===============================================================

use "$int\collapsed_ody.dta", clear

* Category list and corresponding figure numbers (aligned with LaTeX plan)
local cats  "income_group_dest intra_regional contig dest_region_num dist_above_med"
local fnums "1_2_1 1_2_2 1_2_3 1_2_4 1_2_5"
local n_cats : word count `cats'

foreach mne_def in ext dom total {
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
            gcollapse (mean) `sv' `sn' [aw = total_value], by(`cat')
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
* 1.2.B  Bar graphs â€” by exporting country Ã— category Ã— MNE def
*===============================================================

use "$int\collapsed_ody.dta", clear
levelsof country_orig, local(countries)

foreach mne_def in ext dom total {
    if "`mne_def'" == "ext"   local sv "share_mne_value"
    if "`mne_def'" == "dom"   local sv "share_dom_nfirms"
    if "`mne_def'" == "total" local sv "share_total_nfirms"

    foreach cat in income_group_dest intra_regional contig dest_region_num dist_above_med {
        foreach c of local countries {
            preserve
                keep if country_orig == "`c'"
                drop if `cat' == .
                cap {
                    gcollapse (mean) `sv' [aw = total_value], by(`cat')
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
* 1.2.C  Regressions â€” origin and destination characteristics
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

foreach mne_def in ext dom total {
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

foreach mne_def in ext dom total {
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
* 1.3  BY PRODUCT                                         [Plan Â§1.3]
**********************************************************************

*===============================================================
* 1.3.A  Bar graphs â€” aggregate (by product characteristic Ã— MNE def)
*===============================================================

use "$int\collapsed_opy.dta", clear

foreach mne_def in ext dom total {
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
            gcollapse (mean) `sv' `sn' [aw = total_value], by(`v'_abovemed)
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
        gcollapse (mean) `sv' `sn' [aw = total_value], by(hs_section)
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
        gcollapse (mean) `sv' [aw = total_value], by(hs2)
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
* 1.3.B  Bar graphs â€” by exporting country Ã— product category
*===============================================================

use "$int\collapsed_opy.dta", clear
levelsof country_orig, local(countries)

foreach mne_def in ext dom total {
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
                    gcollapse (mean) `sv' [aw = total_value], by(`cat')
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
* 1.3.C  Regressions â€” product characteristics
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

foreach mne_def in ext dom total {
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

foreach mne_def in ext dom total {
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


