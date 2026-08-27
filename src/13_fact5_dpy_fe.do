/*==============================================================================
  13_fact5_dpy_fe.do -- FACT 5, THE DECISIVE FIXED-EFFECTS TEST

  Fact 5 (stylized-facts document, Table 1 Panel B): non-MNE export value in an
  origin x destination x product x year cell RISES with MNE presence in that
  cell (intensive 0.24, extensive 0.13 in the most saturated published column).
  The model gets the OPPOSITE sign (business stealing, worse with entry), and
  the model-side conclusion (CLAUDE.md 30.5) is that the spillover knob cannot
  reconcile them at any defensible size.

  The published specification's tightest column absorbs origin x dest x product
  and origin x dest x year -- but NO column absorbs DESTINATION x PRODUCT x
  YEAR. A time-varying demand shock to a destination-product market raises
  multinational entry and local exports TOGETHER, so the published coefficient
  confounds the spillover with common demand. This script runs the missing
  specification. If the coefficient survives, Fact 5 is a real target the model
  fails; if it dies, the model's negative sign was never contradicted.

  Data: collapsed_odpy.dta (v4 cube, built by 06_trade_analysis.do Part 0.9,
  living in the predecessor project's Intermediate_v4). Only positive-trade
  cells exist in the cube, so all margins here are conditional on the cell
  exporting at all; the intensive-margin comparison to the published 0.2391 is
  the meaningful one (the published extensive margin used a squared cube).

  Columns, Panel B (DV = ln non-MNE export value, dom_ext_value):
    (1) published col 3 benchmark: absorb(odp_id odt_id)        [target 0.2391]
    (2) + dest x product x year:   absorb(odp_id odt_id dpt_id) [THE TEST]
    (3) parsimonious variant:      absorb(odp_id dpt_id)
    (4) PPML on the level with the col-2 FE (count/level outcome discipline;
        also keeps cells where non-MNE exports are zero)
  Extensive regressor (any MNE present) with the same ladder, and Panel A
  (total exports) for reference.

  Output: output/tables/fact5_dpy_fe.csv / .tex, log output/tables/
  fact5_dpy_fe.log. Run:
    "C:\Program Files\Stata18\StataMP-64.exe" /e do src\13_fact5_dpy_fe.do
==============================================================================*/

clear all
set more off
set linesize 120

global int "C:\Sebas BID\Orbis_DNB_Customs\Claude\Data\Intermediate_v4"
global out "C:\Sebas BID\Orbis_DNB_Customs_Final\output\tables"

capture log close
log using "$out\fact5_dpy_fe.log", replace text

di as text "{hline 78}"
di as text "FACT 5: does MNE presence raise NON-MNE exports once destination x"
di as text "product x year demand shocks are absorbed?"
di as text "{hline 78}"

use "$int\collapsed_odpy.dta", clear
di as text "cells loaded: " as result _N

*--- the missing fixed effect, and the regression variables ------------------
egen dpt_id = group(country_dest hs6 year)

gen double ln_dom  = ln(dom_ext_value) if dom_ext_value > 0
gen double ln_nmne = ln(n_mne_ext)     if n_mne_ext > 0
gen byte   any_mne = (n_mne_ext > 0) if !missing(n_mne_ext)
label var ln_dom  "ln non-MNE exports"
label var ln_nmne "ln # MNE firms"
label var any_mne "Any MNE present"

count if !missing(ln_dom, ln_nmne)
di as text "intensive-margin sample (>=1 MNE, non-MNE exports > 0): " as result r(N)

*==============================================================================
* PANEL B, INTENSIVE: ln non-MNE exports on ln # MNE firms
*==============================================================================
eststo clear

* (1) the published tightest column, as the benchmark
eststo B1: reghdfe ln_dom ln_nmne, absorb(odp_id odt_id) vce(cluster od_id)
scalar bench = _b[ln_nmne]
di as text "published col (3): 0.2391 (0.0178);  this cube: " as result %9.4f bench

* (2) THE TEST: add destination x product x year
eststo B2: reghdfe ln_dom ln_nmne, absorb(odp_id odt_id dpt_id) vce(cluster od_id)
scalar test = _b[ln_nmne]
di as text "with dest x product x year FE:       " as result %9.4f test

* (3) parsimonious: odp + dpt only
eststo B3: reghdfe ln_dom ln_nmne, absorb(odp_id dpt_id) vce(cluster od_id)

* (4) PPML on the level, keeping zero non-MNE cells, col-2 fixed effects
capture noisily {
    eststo B4: ppmlhdfe dom_ext_value ln_nmne, ///
        absorb(odp_id odt_id dpt_id) vce(cluster od_id) maxiter(60)
}

*==============================================================================
* PANEL B, EXTENSIVE REGRESSOR: any MNE present
*==============================================================================
eststo E1: reghdfe ln_dom any_mne, absorb(odp_id odt_id) vce(cluster od_id)
eststo E2: reghdfe ln_dom any_mne, absorb(odp_id odt_id dpt_id) vce(cluster od_id)

*==============================================================================
* PANEL A, REFERENCE: total exports
*==============================================================================
eststo A1: reghdfe ln_total_value ln_nmne, absorb(odp_id odt_id) vce(cluster od_id)
eststo A2: reghdfe ln_total_value ln_nmne, absorb(odp_id odt_id dpt_id) vce(cluster od_id)

*==============================================================================
* OUTPUT
*==============================================================================
esttab B1 B2 B3 B4 E1 E2 A1 A2 using "$out\fact5_dpy_fe.csv", replace ///
    se star(* 0.10 ** 0.05 *** 0.01) b(%9.4f) ///
    stats(N r2_within, fmt(%12.0fc %9.4f) labels("Cells" "Within R2")) ///
    mtitles("B:bench" "B:+dpt" "B:odp+dpt" "B:PPML" "Bext:bench" "Bext:+dpt" ///
            "A:bench" "A:+dpt") ///
    title("Fact 5: non-MNE exports and MNE presence, with and without destination x product x year FE")

esttab B1 B2 B3 B4 E1 E2 A1 A2 using "$out\fact5_dpy_fe.tex", replace ///
    booktabs se star(* 0.10 ** 0.05 *** 0.01) b(%9.4f) ///
    stats(N r2_within, fmt(%12.0fc %9.4f) labels("Cells" "Within \$R^2\$")) ///
    mtitles("bench" "+DPT" "ODP+DPT" "PPML" "bench" "+DPT" "bench" "+DPT")

di as text "{hline 78}"
di as text "VERDICT (computed, not asserted):"
if test > 0 & test > 0.5*bench {
    di as text "  the intensive coefficient SURVIVES the destination x product x year"
    di as text "  fixed effect (" %6.4f test " vs benchmark " %6.4f bench ")."
    di as text "  Fact 5 is a real target and the model's negative sign is a failure."
}
else if test > 0 {
    di as text "  the coefficient survives with the right sign but shrinks to " %6.4f test
    di as text "  (benchmark " %6.4f bench "): partly demand contamination, a residual"
    di as text "  positive association remains for the model to explain."
}
else {
    di as text "  the coefficient DIES (" %6.4f test "): the published positive sign was"
    di as text "  demand contamination, and the model's business-stealing sign was"
    di as text "  never contradicted by the data."
}
di as text "{hline 78}"

log close
