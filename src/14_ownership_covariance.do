/*==============================================================================
  14_ownership_covariance.do -- THE PAPER'S HEADLINE OBJECT, MEASURED

  Proposition P2a: country H's profit-income correction in a market is
      sum_g theta_g S_g^2  =  thetabar * HHI  +  Cov_S(theta, S),
  and aggregating over markets m with value weights w_m gives the Layer-1
  three-term decomposition

      sum_m w_m sum_g theta_g S_g^2
        = [sum_m w_m thetabar_m] * [sum_m w_m HHI_m]      (1) naive
        + Cov_w(thetabar_m, HHI_m)                        (2) BETWEEN markets
        + sum_m w_m Cov_m(theta, S)                       (3) WITHIN markets

  (1) is what country-level ownership data can produce; (1)+(2) needs market-
  level ownership shares; (3) needs firm-level global-ultimate-parent identity.
  Term (3) is the contribution. This script measures all three in the matched
  customs data.

  Objects:
    market  = destination x HS6 x year cell
    group g = the ultimate parent FIRM: guo25 (Orbis GUO BvD id) when present,
              else the parent name, else the exporting firm itself (a singleton
              group, like the model's fringe)
    S_g     = the group's share of the market's LAC-origin exports. These are
              WITHIN-SAMPLE shares -- the same object Figure 6 reports; the
              measurement-operator machinery (model CLAUDE.md section 5a) is
              what maps them into the model. Disclosed, not hidden.
    theta_g = 1{owner country = H}, owner = iso3_parent for matched firms and
              the origin country for unmatched ones (the stylized-facts
              document's own convention: unmatched = locally owned).

  Output: output/tables/ownership_cov_bymarket.dta (market x group cube),
          ownership_cov_owners.csv (the decomposition, one row per owner
          country), log ownership_cov.log.

  Run:  "C:\Program Files\Stata18\StataMP-64.exe" /e do src\14_ownership_covariance.do
==============================================================================*/

set more off
clear all
set linesize 160

local INFILE "C:\Sebas BID\Orbis_DNB_Customs\Base_final_Customs_DNB_Orbis_product_complete.dta"
global out "C:\Sebas BID\Orbis_DNB_Customs_Final\output\tables"

capture log close
log using "$out\ownership_cov.log", replace text

display "=== reading the transaction file (column subset) ==="
use country_orig country_dest year hs07_6d value_fob iso3_parent ///
    _merge_final_review guo25 name_par Tax_ID                    ///
    using "`INFILE'", clear
count

*--- housekeeping -------------------------------------------------------------
foreach v in country_orig country_dest iso3_parent {
    quietly replace `v' = upper(trim(`v'))
    quietly replace `v' = "" if inlist(`v', ".", "NA", "N/A", "-")
}
quietly replace guo25 = upper(trim(guo25))
quietly replace guo25 = "" if inlist(guo25, ".", "NA", "N/A", "-")
quietly drop if value_fob <= 0 | missing(value_fob)
quietly drop if country_dest == "" | hs07_6d == "" | missing(year)

*--- the group key and the owner country --------------------------------------
generate byte matched = (_merge_final_review == 3) & (iso3_parent != "")
generate str3 owner = iso3_parent
quietly replace owner = country_orig if !matched

* parent-FIRM identity: GUO BvD id > parent name > the exporting firm itself
generate str80 gkey = ""
quietly replace gkey = "G:" + guo25 if matched & guo25 != ""
quietly replace gkey = "N:" + upper(trim(substr(name_par, 1, 60))) ///
    if gkey == "" & matched & trim(name_par) != ""
quietly replace gkey = "F:" + country_orig + ":" + trim(Tax_ID) if gkey == ""
quietly count if gkey == "F::" | gkey == "F:" + country_orig + ":"
display "firms with no usable id at all (dropped): " r(N)
quietly drop if substr(gkey, -1, 1) == ":"

display "=== group-identity coverage, share of export value ==="
generate byte idtype = 1 + (substr(gkey,1,2) == "N:") + 2*(substr(gkey,1,2) == "F:")
label define idt 1 "GUO BvD id" 2 "parent name" 3 "own firm (singleton)"
label values idtype idt
table idtype, statistic(sum value_fob) nformat(%18.0fc)

*--- market x group cube -------------------------------------------------------
display "=== collapsing to market x group ==="
gcollapse (sum) v = value_fob, by(country_dest hs07_6d year gkey owner)
* a group occasionally carries two owner strings across shipments; keep all the
* value, label the group with its largest-value owner
bysort country_dest hs07_6d year gkey: egen double vg = total(v)
bysort country_dest hs07_6d year gkey (v): keep if _n == _N
drop v
rename vg v
compress
count
save "$out\ownership_cov_bymarket.dta", replace

*--- shares, HHI, and the per-market ownership objects -------------------------
display "=== market shares and concentration ==="
egen double Vm = total(v), by(country_dest hs07_6d year)
generate double S  = v / Vm
generate double S2 = S * S
egen double HHI = total(S2), by(country_dest hs07_6d year)
egen long   Gm  = count(1), by(country_dest hs07_6d year)

quietly summarize HHI [aw = v]
display "value-weighted mean market HHI (within-sample shares): " %8.4f r(mean)
quietly summarize Gm [aw = v]
display "value-weighted mean number of groups per market:       " %8.1f r(mean)

*--- per (market, owner): thetabar_m,H and sum_{g in H} S_g^2 -----------------
display "=== the decomposition, owner country by owner country ==="
gcollapse (sum) tbar = S sumS2 = S2 (first) Vm HHI, ///
    by(country_dest hs07_6d year owner)

* market weight: value share of the market in total exports.
* Vm repeats within a market across owners; build the true total from a market tag
egen byte mtag = tag(country_dest hs07_6d year)
quietly summarize Vm if mtag
scalar VTOT = r(sum)
generate double w = Vm / VTOT      // sums to one over MARKETS (not rows)

* value-weighted world HHI (each market counted once)
quietly summarize HHI [aw = Vm] if mtag
scalar HBAR = r(mean)
display "H_bar (value-weighted mean HHI): " %8.4f HBAR

* per owner: total = sum_m w_m sumS2 ; thetabar_agg = sum_m w_m tbar ;
* between = sum_m w_m tbar*HHI - thetabar_agg*HBAR ; within = total - sum w tbar*HHI
generate double t_total   = w * sumS2
generate double t_tbar    = w * tbar
generate double t_tbarH   = w * tbar * HHI
gcollapse (sum) total = t_total tbar_agg = t_tbar tbarH = t_tbarH, by(owner)

generate double naive   = tbar_agg * HBAR
generate double between = tbarH - naive
generate double within  = total - tbarH
generate double ratio   = total / naive
gsort -tbar_agg

display "=== the headline table: top 20 owner countries by aggregate ownership ==="
display "  total   = sum_m w_m sum_g theta S^2   (what the correction needs)"
display "  naive   = thetabar_agg * HHI_bar      (country-level data can build this)"
display "  between = Cov_w(thetabar_m, HHI_m)    (market-level ownership shares)"
display "  within  = sum_m w_m Cov_m(theta, S)   (needs FIRM-level parent identity)"
format total naive between within %12.6f
format tbar_agg %9.4f
format ratio %9.3f
list owner tbar_agg total naive between within ratio in 1/20, noobs sep(0)

display "=== the USA row, the tariff-setter of the paper ==="
list owner tbar_agg total naive between within ratio if owner == "USA", noobs

export delimited using "$out\ownership_cov_owners.csv", replace

display "=== reading ==="
display "For each owner H: total/naive > 1 means country-level data UNDERSTATE"
display "H's profit-income stake, and (between + within) is the size of the"
display "understatement -- the within term is the part only firm-level parent"
display "identity can measure. These are within-LAC-sample shares (the Figure-6"
display "measurement operator); the model's section-5a machinery maps them into"
display "destination-absorption shares."

log close
