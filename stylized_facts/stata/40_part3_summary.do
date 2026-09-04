**********************************************************************
* 40_part3_summary.do
*
* PART 3 -- SUMMARY STATISTICS
*
* Inputs:  $int\firm_level_data.dta, $int\collapsed_ody.dta, $int\collapsed_odpy.dta
* Outputs: $t_s3 (+ Overleaf mirror)
*
* Called by 00_master.do after 01_setup.do.
**********************************************************************
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
        by(country_orig year)
    * Average over years, then tabulate by country
    gcollapse (mean) total_value n_obs n_mne n_dom n_mne_dom n_mne_total, ///
        by(country_orig)
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
di as text "==========================================================="
