* wp_agro_v4_ppml.do -- E2e of especificaciones_estimaciones_v4: PPML of local exports in levels, FE4
* (origin x destination x product + origin x destination x year), clustered by origin and destination pair.
* pyfixest's PPML did not converge on these fixed effects; ppmlhdfe does. Input: data/intermediate/wp/v4/odpy_ppml.dta
* (wp_agro_v4_data cells). Output: output/wp_2012_2018/agro/v4/v4_ppml.dta
version 18
clear all
global ROOT "C:\Sebas BID\Orbis_DNB_Customs_Final"
use "$ROOT\data\intermediate\wp\v4\odpy_ppml.dta", clear
tempname H
postfile `H' str6 reg double b se p N singletons pr2 str60 status using "$ROOT\output\wp_2012_2018\agro\v4\v4_ppml.dta", replace
foreach r in lnN D {
    local c = cond("`r'" == "lnN", "N >= 1", "1")
    capture ppmlhdfe XL `r' if `c', absorb(odp ody) vce(cluster od)
    if _rc {
        post `H' ("`r'") (.) (.) (.) (.) (.) (.) ("error `=_rc'")
        continue
    }
    post `H' ("`r'") (_b[`r']) (_se[`r']) (2 * normal(-abs(_b[`r'] / _se[`r']))) (e(N)) (e(num_singletons)) (e(r2_p)) ("ok")
}
postclose `H'
