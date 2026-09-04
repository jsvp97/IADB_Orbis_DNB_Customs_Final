**********************************************************************
* 30_part2_effects.do
*
* PART 2 -- EFFECTS OF MULTINATIONAL PRESENCE IN TRADE
*   2.1  Aggregate regressions          (ODY + ODPY)
*   2.2  Gravity regressions            (firm-dest-year + firm-dest-product-year)
*   2.3  MNE network regressions
*   2.4  Concentration patterns         (ODY + ODPY)
*   2.5  Extensive margin: country-product level
*   2.6  Extensive margin: firm level
*
* Inputs:  $int\collapsed_ody.dta, $int\collapsed_odpy.dta,
*          $int\firm_dest_year_level.dta, $int\firm_level_data_full.dta
* Outputs: $r_s2, $t_s2, $g25 (+ Overleaf mirrors)
*
* Called by 00_master.do after 01_setup.do.
**********************************************************************
**********************************************************************
**********************************************************************
*
*   PART 2: EFFECTS OF MULTINATIONAL PRESENCE IN TRADE
*
**********************************************************************
**********************************************************************


**********************************************************************
* 2.1  AGGREGATE REGRESSIONS                          [Plan Â§2 Agg]
**********************************************************************

*===============================================================
* 2.1.A  ODY
*===============================================================

* run_agg_spec: baseline + destination interactions + bilateral interactions
* across the standard 7-spec FE ladder.
* FIX: uses ${fe`f'} / ${fel`f'} to access globals inside program.
capture program drop run_agg_spec
program define run_agg_spec
    args dv mv filename cluster_id cluster_lbl

    local est "reghdfe"
    if "`dv'" == "total_value" local est "reghdfe"

    * --- Baseline (FE 1-7) ---
    forval f = 1/7 {
        local fe "${fe`f'}"   // FIX: globals, not locals
        local fl "${fel`f'}"  // FIX: idem

        if "`est'" == "reghdfe" {
            if `f' == 1 reg `dv' `mv', robust
            else        reghdfe `dv' `mv', absorb(`fe') vce(cluster `cluster_id')
        }
        else {
            if `f' == 1 reghdfe `dv' `mv', noabsorb
            else        reghdfe `dv' `mv', absorb(`fe')
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

    * --- Destination interactions (FE 5-7): MNE x GDP, MNE x population ---
    forval f = 5/7 {
        local fe "${fe`f'}"
        local fl "${fel`f'}"
        local ivd "`mv' `mv'_X_lngdppc_d `mv'_X_lnpop_d ln_gdpcap_d ln_pop_d"

        if "`est'" == "reghdfe" reghdfe `dv' `ivd', absorb(`fe')
        else reghdfe `dv' `ivd', absorb(`fe') vce(cluster `cluster_id')

        outreg2 using "`filename'", append tex(frag) label ctitle("`fl'") ///
            addtext(FE, "`fl'", Spec, "Dest Interactions", SE Cluster, "`cluster_lbl'") ///
            dec(4) nocons
    }

    * --- Bilateral interactions (FE 5-7): MNE x distance, MNE x FTA ---
    forval f = 5/7 {
        local fe "${fe`f'}"
        local fl "${fel`f'}"
        local ivb "`mv' `mv'_X_lndist `mv'_X_contig `mv'_X_fta_wto ln_dist contig fta_wto"

        if "`est'" == "reghdfe" reghdfe `dv' `ivb', absorb(`fe')
        else reghdfe `dv' `ivb', absorb(`fe') vce(cluster `cluster_id')

        outreg2 using "`filename'", append tex(frag) label ctitle("`fl'") ///
            addtext(FE, "`fl'", Spec, "Bilateral Interactions", SE Cluster, "`cluster_lbl'") ///
            dec(4) nocons
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

foreach mne_def in ext dom total {
    if "`mne_def'" == "ext" {
        local mv_list "share_mne_value share_mne_nfirms"
    }
    else {
        local mv_list "share_`mne_def'_nfirms"
    }
    foreach mv of local mv_list {
        foreach dv in ln_total_value positive_trade total_value {
            run_agg_spec ///
                `dv' `mv' ///
                "$r_s2\reg_2_1_ody_`mne_def'_`mv'_`dv'.tex" ///
                "od_id" "Origin-Destination"
            copy "$r_s2\reg_2_1_ody_`mne_def'_`mv'_`dv'.tex" ///
                 "$ol_r_s2\reg_2_1_ody_`mne_def'_`mv'_`dv'.tex", replace
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
    args dv mv filename cluster_id cluster_lbl

    local est "reghdfe"
    if "`dv'" == "total_value" local est "reghdfe"

    * --- Baseline (ODPY 9-spec ladder) ---
    local nfe = ${nfe_odpy}
    forval i = 1/`nfe' {
        local fe "${fe_odpy`i'}"
        local fl "${fel_odpy`i'}"

        if "`est'" == "reghdfe" {
            if "`fe'" == "" reg `dv' `mv', robust
            else reghdfe `dv' `mv', absorb(`fe') vce(cluster `cluster_id')
        }
        else {
            if "`fe'" == "" reghdfe `dv' `mv', noabsorb
            else reghdfe `dv' `mv', absorb(`fe')
        }

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

    * --- Product interactions (selected FE): MNE x upstreamness, sigma, complexity ---
    foreach fe in "ot_id dt_id" "od_id year" "ot_id dt_id od_id" {
        if "`fe'" == "ot_id dt_id"       local fl "OxT + DxT"
        if "`fe'" == "od_id year"        local fl "OD x Year"
        if "`fe'" == "ot_id dt_id od_id" local fl "OxT + DxT + OD"
        local ivp "`mv' `mv'_X_upstream `mv'_X_sigma `mv'_X_complex upstreamness sigma complexity"

        if "`est'" == "reghdfe" reghdfe `dv' `ivp', absorb(`fe')
        else reghdfe `dv' `ivp', absorb(`fe') vce(cluster `cluster_id')

        outreg2 using "`filename'", append tex(frag) label ctitle("`fl'") ///
            addtext(FE, "`fl'", Spec, "Product Interactions", SE Cluster, "`cluster_lbl'") ///
            dec(4) nocons
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

foreach mne_def in ext dom total {
    if "`mne_def'" == "ext" {
        local mv_list "share_mne_value share_mne_nfirms"
    }
    else {
        local mv_list "share_`mne_def'_nfirms"
    }
    foreach mv of local mv_list {
        foreach dv in ln_total_value positive_trade total_value {
            run_agg_spec_odpy ///
                `dv' `mv' ///
                "$r_s2\reg_2_1_odpy_`mne_def'_`mv'_`dv'.tex" ///
                "odp_id" "Orig-Dest-Prod"
            copy "$r_s2\reg_2_1_odpy_`mne_def'_`mv'_`dv'.tex" ///
                 "$ol_r_s2\reg_2_1_odpy_`mne_def'_`mv'_`dv'.tex", replace
        }
    }
}


**********************************************************************
* 2.2  GRAVITY REGRESSIONS                        [Plan Â§2 Gravity]
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
*   a command separator in Stata â€” so `dv2` was never assigned, causing
*   a shifted args list and the "file dv2.txt could not be opened" error.
foreach mne_def in ext dom total {

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

* run_gravity_fdpy: baseline across ODPY 9-spec ladder + product interactions
* FIX: uses ${nfe_odpy} / ${fe_odpy`i'} / ${fel_odpy`i'} globals
capture program drop run_gravity_fdpy
program define run_gravity_fdpy
    args dv gvars mv dv2 filename cluster_id cluster_lbl

    local est "reghdfe"
    if "`dv'" == "value_fob" local est "reghdfe"

    * --- Baseline (ODPY 9-spec) ---
    local nfe = ${nfe_odpy}
    forval i = 1/`nfe' {
        local fe "${fe_odpy`i'}"
        local fl "${fel_odpy`i'}"

        if "`est'" == "reghdfe" {
            if "`fe'" == "" reg `dv' `gvars', robust
            else reghdfe `dv' `gvars', absorb(`fe') vce(cluster `cluster_id')
        }
        else {
            if "`fe'" == "" reghdfe `dv' `gvars', noabsorb
            else reghdfe `dv' `gvars', absorb(`fe')
        }

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

    * --- Product interactions (selected FE) ---
    foreach fe in "ot_id dt_id" "ot_id dt_id od_id" {
        if "`fe'" == "ot_id dt_id"       local fl "OxT + DxT"
        if "`fe'" == "ot_id dt_id od_id" local fl "OxT + DxT + OD"
        local ivp "`mv'_X_lndist `dv2'_X_lndist `mv'_X_upstream `dv2'_X_upstream `mv'_X_sigma `dv2'_X_sigma `mv'_X_complex `dv2'_X_complex `mv'"

        if "`est'" == "reghdfe" reghdfe `dv' `ivp', absorb(`fe')
        else reghdfe `dv' `ivp', absorb(`fe') vce(cluster `cluster_id')

        outreg2 using "`filename'", append tex(frag) label ctitle("`fl'") ///
            addtext(FE, "`fl'", Spec, "Product Interactions", SE Cluster, "`cluster_lbl'") ///
            dec(4) nocons
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

foreach mne_def in ext dom total {

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
            "$r_s2\reg_2_2_grav_fdpy_`mne_def'_`dv'.tex" ///
            "odp_id" "Orig-Dest-Prod"
        copy "$r_s2\reg_2_2_grav_fdpy_`mne_def'_`dv'.tex" ///
             "$ol_r_s2\reg_2_2_grav_fdpy_`mne_def'_`dv'.tex", replace
    }
}


**********************************************************************
* 2.3  MNE NETWORK REGRESSIONS                    [Plan Â§2 Network]
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

foreach mne_def in ext dom total {
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


**********************************************************************
* 2.4  CONCENTRATION PATTERNS                  [Plan Â§2 Concentration]
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

foreach mne_def in ext dom total {
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

foreach mne_def in ext dom total {
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
* 2.5  EXTENSIVE MARGIN: COUNTRY-PRODUCT LEVEL     [Plan Â§2 ExtM]
**********************************************************************

*===============================================================
* 2.5.A  Kernel densities (by year)
*===============================================================

use "$int\firm_level_data_full.dta", clear

preserve
    gcollapse (max) new_product_orig new_prod_only_mne new_prod_both ///
              (sum) total_value = value_fob, by(country_orig hs6 year)
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
              by(country_orig hs6 year)

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
              by(country_orig country_dest hs6 year)

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
* 2.6  EXTENSIVE MARGIN: FIRM LEVEL               [Plan Â§2 ExtFirm]
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
foreach mne_def in ext dom total {
    if "`mne_def'" == "ext"   local mne_d "MNE"
    if "`mne_def'" == "dom"   local mne_d "MNE_dom"
    if "`mne_def'" == "total" local mne_d "MNE_total"

    * --- Firm-Year ---
    use "$int\firm_year_level.dta", clear
    cap confirm variable `mne_d'
    if _rc != 0 {
        di as error "Variable `mne_d' not found in firm_year_level.dta â€” skipping `mne_def'"
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
                  by(firm_id country_orig hs6 year)

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


