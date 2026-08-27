*==============================================================================
*  dest03_tables.do   -- step 2 of 2
*
*  Reads the destination cube built by dest02_cube.do and produces the
*  tabulation the model needs:
*
*   T1  coverage: how much export value is classified, and how confidently
*   T2  THE HEADLINE: share of foreign-MNE export value that goes to the
*       parent's own country -- overall, by origin, by year
*   T3  where foreign-MNE exports actually go, against where everyone else's go
*   T4  the top parent countries, and how much each one's LAC affiliates ship
*       back home
*   T5  THE OBJECT THE OPTIMAL-TARIFF CORRECTION NEEDS: for each destination,
*       the share of its imports from LAC that is produced by affiliates of its
*       OWN multinationals.  This is theta_X, market by market.
*
*  Everything is value-weighted FOB. Results go to the log and to CSVs in
*  output/tables.
*==============================================================================

set more off
clear all
set linesize 200

local OUT "C:\Sebas BID\Orbis_DNB_Customs_Final\output\tables"
use "`OUT'/mne_export_destination_cube.dta", clear
count
describe, short

*--- T1  coverage ------------------------------------------------------------
display "=============================================================="
display "T1  COVERAGE  (value FOB, whole sample)"
display "=============================================================="
quietly summarize value_fob
local TOT = r(sum)
display "total export value in the sample: " %20.0fc `TOT'

foreach g in MNE_total MNE_ext MNE_dom {
    quietly summarize value_fob if `g' == 1
    display "`g' = 1 : " %20.0fc r(sum) "   share " %6.4f r(sum)/`TOT'
}
quietly summarize value_fob if MNE_total == 1 & has_parent == 0
display "matched but NO parent country recorded : " %20.0fc r(sum)

*--- T2  the headline --------------------------------------------------------
display "=============================================================="
display "T2  SHARE OF FOREIGN-MNE EXPORT VALUE GOING TO THE PARENT'S OWN COUNTRY"
display "=============================================================="
quietly summarize value_fob if MNE_ext == 1
local MNEV = r(sum)
quietly summarize value_fob if MNE_ext == 1 & to_parent == 1
display "foreign-MNE export value          : " %20.0fc `MNEV'
display "of which to the parent country    : " %20.0fc r(sum)
display "SHARE                             : " %8.4f r(sum)/`MNEV'

display "--- by origin ---"
preserve
    keep if MNE_ext == 1
    collapse (sum) value_fob, by(country_orig to_parent)
    reshape wide value_fob, i(country_orig) j(to_parent)
    rename value_fob0 v_other
    rename value_fob1 v_home
    replace v_other = 0 if missing(v_other)
    replace v_home  = 0 if missing(v_home)
    generate double share_to_parent = v_home/(v_home + v_other)
    format v_* %18.0fc
    list country_orig v_home v_other share_to_parent, noobs
    export delimited using "`OUT'/T2_share_to_parent_by_origin.csv", replace
restore

display "--- by year ---"
preserve
    keep if MNE_ext == 1
    collapse (sum) value_fob, by(year to_parent)
    reshape wide value_fob, i(year) j(to_parent)
    rename value_fob0 v_other
    rename value_fob1 v_home
    replace v_other = 0 if missing(v_other)
    replace v_home  = 0 if missing(v_home)
    generate double share_to_parent = v_home/(v_home + v_other)
    list year share_to_parent, noobs
    export delimited using "`OUT'/T2_share_to_parent_by_year.csv", replace
restore

*--- T3  destination mix -----------------------------------------------------
display "=============================================================="
display "T3  WHERE EXPORTS GO: FOREIGN MNE AFFILIATES vs EVERYONE ELSE"
display "=============================================================="
preserve
    collapse (sum) value_fob, by(country_dest MNE_ext)
    reshape wide value_fob, i(country_dest) j(MNE_ext)
    rename value_fob0 v_nonmne
    rename value_fob1 v_mne
    replace v_nonmne = 0 if missing(v_nonmne)
    replace v_mne    = 0 if missing(v_mne)
    quietly summarize v_mne
    local SM = r(sum)
    quietly summarize v_nonmne
    local SN = r(sum)
    generate double sh_mne    = v_mne/`SM'
    generate double sh_nonmne = v_nonmne/`SN'
    gsort -sh_mne
    format v_* %18.0fc
    list country_dest v_mne sh_mne sh_nonmne in 1/25, noobs
    export delimited using "`OUT'/T3_destination_mix.csv", replace
restore

*--- T4  the top parent countries -------------------------------------------
display "=============================================================="
display "T4  TOP PARENT COUNTRIES, AND HOW MUCH THEY SHIP HOME"
display "=============================================================="
preserve
    keep if MNE_ext == 1
    collapse (sum) value_fob, by(iso3_parent to_parent)
    reshape wide value_fob, i(iso3_parent) j(to_parent)
    rename value_fob0 v_other
    rename value_fob1 v_home
    replace v_other = 0 if missing(v_other)
    replace v_home  = 0 if missing(v_home)
    generate double v_tot = v_home + v_other
    quietly summarize v_tot
    generate double sh_of_mne      = v_tot/r(sum)
    generate double share_to_home  = v_home/v_tot
    gsort -v_tot
    format v_* %18.0fc
    list iso3_parent v_tot sh_of_mne share_to_home in 1/25, noobs
    export delimited using "`OUT'/T4_parent_countries.csv", replace
restore

*--- T5  theta_X : the object the optimal-tariff correction needs ------------
display "=============================================================="
display "T5  FOR EACH DESTINATION, THE SHARE OF ITS LAC IMPORTS PRODUCED BY"
display "    AFFILIATES OF ITS OWN MULTINATIONALS  (this is theta_X)"
display "=============================================================="
preserve
    generate byte own_affiliate = (MNE_ext == 1) & (iso3_parent == country_dest)
    collapse (sum) value_fob, by(country_dest own_affiliate)
    reshape wide value_fob, i(country_dest) j(own_affiliate)
    rename value_fob0 v_other
    rename value_fob1 v_own
    replace v_other = 0 if missing(v_other)
    replace v_own   = 0 if missing(v_own)
    generate double v_tot = v_own + v_other
    generate double theta_dest = v_own/v_tot
    gsort -v_tot
    format v_* %18.0fc
    list country_dest v_tot v_own theta_dest in 1/25, noobs
    export delimited using "`OUT'/T5_theta_by_destination.csv", replace
restore

display "=== done ==="
