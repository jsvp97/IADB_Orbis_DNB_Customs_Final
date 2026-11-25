* =====================================================================================================================
* wp_agro_v5_event.do  --  E11 of especificaciones_estimaciones_v5_2026-11-24.md: entry of the first multinational
* =====================================================================================================================
* Inputs : data/intermediate/wp/v5/ev5_A.dta, ev5_B.dta, ev5_Bentry.dta (stylized_facts/python/wp_agro_v5_events.py)
* Output : output/wp_2012_2018/agro/v5/ev5_<part>_<block>.dta, one row per cell set x block x sample x group x outcome x
*          estimator x FE code x term (Tm4 ... Tp4, Post_avg, pre_test, Av_tot), read by wp_agro_v5_workbook.py
* Usage  : StataMP-64.exe /e do wp_agro_v5_event.do <part> <block>
*          part  = A (origin x product), B (origin x destination x product), E (B entry panel: odp cells with no local
*                  exports before the op entry)
*          block = std (E11b standard set x E11d.1 samples), fe (E11c), treat (E11d.2-4), het (E11e), add (E11b vi-viii:
*                  stacked, jwdid PPML, honestdid), spill (E11a.4), placebo
*
* Estimators (E11b)
*   twfe  : reghdfe on event-time dummies (-4 binned, -3, -2, 0, 1, 2, 3, 4 binned; base -1); FE code EV*
*   cs    : Callaway and Sant'Anna (csdid), not yet treated controls (csnev: never treated only); bal(pair) when the
*           outcome has missing years
*   sa    : Sun and Abraham (eventstudyinteract), never treated controls, EV2 fixed effects
*   bjs   : Borusyak, Jaravel and Spiess (did_imputation), fe(EV2), horizons 0-4, pretrends(3): its pre-period
*           coefficients are relative to the periods before -3, not to -1
*   dcdh  : de Chaisemartin and D'Haultfoeuille (did_multiplegt_dyn), effects(5) placebo(3), trends_nonparam(origin);
*           placebo l compares t0 - 1 - l with t0 - 1 (stored as Tm2, Tm3, Tm4)
*   stk   : stacked regression by cohort (Cengiz et al. 2019): one stack per t0 with its never treated controls, FE
*           cell x stack and the EV code x stack
*   jw    : Wooldridge extended TWFE, PPML on local exports in levels (jwdid, never), event effects on the log scale
*   hd    : Rambachan and Roth (honestdid) bounds for the average of event times 0-4 after twfe EV2 (text log)
*   T     : EV2-T, cell linear trends estimated on untreated observations and extrapolated (did_imputation with
*           unitcontrols(year)); TF: EV2 + cell linear trends over the full window (reghdfe)
* Clusters: A by cell (origin x product), B and E by origin and destination pair.
* Logs only on positive values (no ln(1 + x), no asinh).
* =====================================================================================================================
version 18
clear all
set more off
set matsize 5000
args part block only
if "`part'" == "" local part "A"
if "`block'" == "" local block "std"

global ROOT "C:\Sebas BID\Orbis_DNB_Customs_Final"
global V5   "$ROOT\data\intermediate\wp\v5"
global OUT  "$ROOT\output\wp_2012_2018\agro\v5"
cap mkdir "$OUT"
global EV "ev_m4 ev_m3 ev_m2 ev_0 ev_1 ev_2 ev_3 ev_4"

* ---------------------------------------------------------------------------------------------
capture program drop setev
program define setev
    * event-time variables for the treatment definition in `1' (a g_* variable) and the sample condition `2'
    args g cond
    cap drop gvar rel ev_* D Ei insmp cohort never
    gen gvar = `g'
    gen byte insmp = gvar < . & (`cond')
    gen rel = year - gvar if gvar > 0 & gvar < .
    gen ev_m4 = rel <= -4 & gvar > 0 & gvar < .
    gen ev_m3 = rel == -3
    gen ev_m2 = rel == -2
    forvalues k = 0/3 {
        gen ev_`k' = rel == `k'
    }
    gen ev_4 = rel >= 4 & gvar > 0 & gvar < .
    gen D = gvar > 0 & gvar < . & year >= gvar
    gen Ei = gvar if gvar > 0 & gvar < .
    gen cohort = gvar if gvar > 0 & gvar < .
    gen never = gvar == 0
end

capture program drop counts
program define counts, rclass
    tempvar t
    qui egen `t' = tag(cell) if insmp
    qui count if `t' == 1 & gvar > 0
    return scalar nt = r(N)
    qui count if `t' == 1 & gvar == 0
    return scalar nc = r(N)
end

capture program drop putrow
program define putrow
    args H term b se p N
    post $HH ("$P") ("$BLK") ("$SMP") ("$GRP") ("$Y") ("$EST") ("$FEC") ("`term'") (`b') (`se') (`p') (`N') ($NT) ($NC) ("ok")
end

capture program drop putfail
program define putfail
    args msg
    post $HH ("$P") ("$BLK") ("$SMP") ("$GRP") ("$Y") ("$EST") ("$FEC") ("none") (.) (.) (.) (0) ($NT) ($NC) ("`msg'")
end

capture program drop post_ev
program define post_ev
    * after reghdfe/ppmlhdfe with $EV
    local N = e(N)
    foreach v of global EV {
        local t = cond("`v'" == "ev_m4", "Tm4", cond("`v'" == "ev_m3", "Tm3", cond("`v'" == "ev_m2", "Tm2", "Tp" + substr("`v'", 4, 1))))
        capture local bb = _b[`v']
        if _rc local bb = .
        capture local ss = _se[`v']
        if _rc local ss = .
        if `ss' == 0 | `ss' >= . {
            local bb = .
            local ss = .
        }
        putrow $HH `t' `bb' `ss' (2*normal(-abs(`bb'/`ss'))) `N'
    }
    capture test ev_m4 ev_m3 ev_m2
    local pp = cond(_rc, ., r(p))
    putrow $HH pre_test . . `pp' `N'
    capture lincom (ev_0 + ev_1 + ev_2 + ev_3 + ev_4) / 5
    if _rc == 0 putrow $HH Post_avg `r(estimate)' `r(se)' `r(p)' `N'
end

capture program drop onerun
program define onerun
    * globals in: HH P BLK SMP GRP Y EST FEC; ABS_<FEC>; local y, est, fe code
    args y est fec
    global Y "`y'"
    global EST "`est'"
    global FEC "`fec'"
    qui count if insmp & `y' < .
    if r(N) == 0 {
        global NT 0
        global NC 0
        putfail "empty sample"
        exit
    }
    qui counts
    global NT = r(nt)
    global NC = r(nc)
    if $NT == 0 {
        putfail "no treated cell"
        exit
    }
    local miss 0
    qui count if insmp & `y' >= .
    if r(N) > 0 local miss 1
    if inlist("`est'", "twfe", "ppml") {
        local A "${ABS_`fec'}"
        if "`est'" == "twfe" capture reghdfe `y' $EV if insmp, absorb(`A') vce(cluster clus)
        if "`est'" == "ppml" capture ppmlhdfe `y' $EV if insmp, absorb(`A') vce(cluster clus)
        if _rc {
            putfail "error `=_rc'"
            exit
        }
        post_ev
    }
    if "`est'" == "stk" {
        preserve
        qui keep if insmp
        tempfile base S
        qui save `base'
        qui levelsof gvar if gvar > 0, local(gs)
        local first 1
        foreach g of local gs {
            qui use `base', clear
            qui keep if (gvar == `g' | gvar == 0) & year >= `g' - 4 & year <= `g' + 4
            qui gen stack = `g'
            if !`first' qui append using `S'
            qui save `S', replace
            local first 0
        }
        qui use `S', clear
        local A ""
        foreach a of global ABS_`fec' {
            local A "`A' `a'#stack"
        }
        capture reghdfe `y' $EV, absorb(`A') vce(cluster clus)
        if _rc {
            restore
            putfail "error `=_rc'"
            exit
        }
        post_ev
        restore
    }
    if "`est'" == "TF" {
        capture reghdfe `y' $EV if insmp, absorb(cell##c.year ${ABS_EV2x}) vce(cluster clus)
        if _rc {
            putfail "error `=_rc'"
            exit
        }
        post_ev
    }
    if inlist("`est'", "cs", "csnev") {
        local bal = cond(`miss', "bal(pair)", "")
        * csdid 2.0.3: not yet treated is the default; never treated needs the option never
        local ny = cond("`est'" == "cs", "notyet", "never")
        capture csdid `y' if insmp, ivar(cell) time(year) gvar(gvar) `ny' analytical pointwise cluster(clus) `bal'
        if _rc {
            putfail "error `=_rc'"
            exit
        }
        local N = e(N)
        capture estat event, window(-4 4) post
        if _rc {
            putfail "estat error `=_rc'"
            exit
        }
        local names : colnames e(b)
        foreach t of local names {
            if "`t'" == "Tm1" | substr("`t'", 1, 1) != "T" continue
            putrow $HH `t' `=_b[`t']' `=_se[`t']' (2*normal(-abs(_b[`t']/_se[`t']))) `N'
        }
        local pre ""
        local post ""
        foreach t in Tm4 Tm3 Tm2 {
            if strpos(" `names' ", " `t' ") local pre "`pre' `t'"
        }
        capture test `pre'
        local pp = cond(_rc, ., r(p))
        putrow $HH pre_test . . `pp' `N'
        foreach t in Tp0 Tp1 Tp2 Tp3 Tp4 {
            if strpos(" `names' ", " `t' ") local post "`post' + `t'"
        }
        local k = wordcount(subinstr("`post'", "+", "", .))
        capture lincom (0 `post') / `k'
        if _rc == 0 putrow $HH Post_avg `r(estimate)' `r(se)' `r(p)' `N'
    }
    if "`est'" == "sa" {
        capture eventstudyinteract `y' $EV if insmp, cohort(cohort) control_cohort(never) absorb(${ABS_EV2}) vce(cluster clus)
        if _rc {
            putfail "error `=_rc'"
            exit
        }
        local N = e(N)
        matrix B = e(b_iw)
        matrix V = e(V_iw)
        local i = 0
        foreach v of global EV {
            local ++i
            local t = cond("`v'" == "ev_m4", "Tm4", cond("`v'" == "ev_m3", "Tm3", cond("`v'" == "ev_m2", "Tm2", "Tp" + substr("`v'", 4, 1))))
            local bb = B[1, `i']
            local ss = sqrt(V[`i', `i'])
            if `ss' == 0 | `ss' >= . {
                local bb = .
                local ss = .
            }
            putrow $HH `t' `bb' `ss' (2*normal(-abs(`bb'/`ss'))) `N'
        }
        matrix bp = B[1, 1..3]
        matrix Vp = V[1..3, 1..3]
        capture matrix W = bp * invsym(Vp) * bp'
        local pp = cond(_rc, ., chi2tail(3, W[1, 1]))
        putrow $HH pre_test . . `pp' `N'
        matrix a = (0, 0, 0, 0.2, 0.2, 0.2, 0.2, 0.2)
        matrix m = B * a'
        matrix s = a * V * a'
        putrow $HH Post_avg `=m[1,1]' `=sqrt(s[1,1])' (2*normal(-abs(m[1,1]/sqrt(s[1,1])))) `N'
    }
    if inlist("`est'", "bjs", "T") {
        local uc = cond("`est'" == "T", "unitcontrols(year)", "")
        capture did_imputation `y' cell year Ei if insmp, fe(${ABS_EV2}) horizons(0/4) pretrends(3) cluster(clus) autosample minn(0) `uc'
        if _rc {
            putfail "error `=_rc'"
            exit
        }
        local N = e(N)
        local names : colnames e(b)
        foreach k in 0 1 2 3 4 {
            if strpos(" `names' ", " tau`k' ") putrow $HH Tp`k' `=_b[tau`k']' `=_se[tau`k']' (2*normal(-abs(_b[tau`k']/_se[tau`k']))) `N'
        }
        foreach k in 1 2 3 {
            if strpos(" `names' ", " pre`k' ") putrow $HH Tm`k' `=_b[pre`k']' `=_se[pre`k']' (2*normal(-abs(_b[pre`k']/_se[pre`k']))) `N'
        }
        capture local pp = e(pre_p)
        if _rc local pp = .
        putrow $HH pre_test . . `pp' `N'
        local post ""
        foreach k in 0 1 2 3 4 {
            if strpos(" `names' ", " tau`k' ") local post "`post' + tau`k'"
        }
        local k = wordcount(subinstr("`post'", "+", "", .))
        capture lincom (0 `post') / `k'
        if _rc == 0 putrow $HH Post_avg `r(estimate)' `r(se)' `r(p)' `N'
    }
    if "`est'" == "dcdh" {
        capture did_multiplegt_dyn `y' cell year D if insmp, effects(5) placebo(3) cluster(clus) trends_nonparam(orign) graph_off
        if _rc {
            putfail "error `=_rc'"
            exit
        }
        local N = e(N_effect_1)
        forvalues k = 1/5 {
            local kk = `k' - 1
            capture local bb = e(Effect_`k')
            capture local ss = e(se_effect_`k')
            if "`bb'" != "" & "`ss'" != "" putrow $HH Tp`kk' `bb' `ss' (2*normal(-abs(`bb'/`ss'))) `N'
        }
        forvalues k = 1/3 {
            local kk = `k' + 1
            capture local bb = e(Placebo_`k')
            capture local ss = e(se_placebo_`k')
            if "`bb'" != "" & "`ss'" != "" putrow $HH Tm`kk' `bb' `ss' (2*normal(-abs(`bb'/`ss'))) `N'
        }
        capture local pp = e(p_jointplacebo)
        if _rc local pp = .
        putrow $HH pre_test . . `pp' `N'
        capture lincom (Effect_1 + Effect_2 + Effect_3 + Effect_4 + Effect_5) / 5
        if _rc == 0 putrow $HH Post_avg `r(estimate)' `r(se)' `r(p)' `N'
        capture local bb = e(Av_tot_effect)
        capture local ss = e(se_avg_total_effect)
        if "`bb'" != "" putrow $HH Av_tot `bb' `ss' (2*normal(-abs(`bb'/`ss'))) `N'
    }
    if "`est'" == "jw" {
        preserve
        qui keep if insmp
        qui replace gvar = 0 if gvar >= .
        capture jwdid `y', ivar(cell) tvar(year) gvar(gvar) method(ppmlhdfe) cluster(clus) never
        if _rc {
            restore
            putfail "error `=_rc'"
            exit
        }
        local N = e(N)
        capture estat event, window(-4 4) predict(xb) post
        if _rc {
            restore
            putfail "estat error `=_rc'"
            exit
        }
        local terms "Tm4 Tm3 Tm2 Tm1 Tp0 Tp1 Tp2 Tp3 Tp4"
        local nb = colsof(e(b))
        if `nb' == 9 {
            matrix B = e(b)
            matrix V = e(V)
            forvalues i = 1/9 {
                local t : word `i' of `terms'
                if "`t'" == "Tm1" continue
                local bb = B[1, `i']
                local ss = sqrt(V[`i', `i'])
                putrow $HH `t' `bb' `ss' (2*normal(-abs(`bb'/`ss'))) `N'
            }
            matrix a = (0, 0, 0, 0, 0.2, 0.2, 0.2, 0.2, 0.2)
            matrix m = B * a'
            matrix s = a * V * a'
            putrow $HH Post_avg `=m[1,1]' `=sqrt(s[1,1])' (2*normal(-abs(m[1,1]/sqrt(s[1,1])))) `N'
            matrix ap = (1, 0, 0, 0, 0, 0, 0, 0, 0 \ 0, 1, 0, 0, 0, 0, 0, 0, 0 \ 0, 0, 1, 0, 0, 0, 0, 0, 0)
            matrix bp = ap * B'
            matrix Vp = ap * V * ap'
            capture matrix W = bp' * invsym(Vp) * bp
            local pp = cond(_rc, ., chi2tail(3, W[1, 1]))
            putrow $HH pre_test . . `pp' `N'
        }
        else putfail "window has `nb' terms"
        restore
    }
    if "`est'" == "fhs" {
        capture xtevent `y' if insmp, panelvar(cell) timevar(year) policyvar(D) window(-4 3) trend(-4, method(ols)) cluster(clus)
        if _rc {
            putfail "error `=_rc'"
            exit
        }
        local N = e(N)
        local names : colnames e(b)
        foreach t of local names {
            local tt ""
            if "`t'" == "_k_eq_m4" local tt "Tm4"
            if "`t'" == "_k_eq_m3" local tt "Tm3"
            if "`t'" == "_k_eq_m2" local tt "Tm2"
            forvalues k = 0/3 {
                if "`t'" == "_k_eq_p`k'" local tt "Tp`k'"
            }
            if "`t'" == "_k_eq_p4" local tt "Tp4"
            if "`tt'" != "" putrow $HH `tt' `=_b[`t']' `=_se[`t']' (2*normal(-abs(_b[`t']/_se[`t']))) `N'
        }
        putrow $HH names . . . `N'
    }
end

capture program drop honest
program define honest
    * Rambachan and Roth bounds for the average of event times 0-4 after reghdfe EV2, relative magnitudes and smoothness
    args y tag
    capture reghdfe `y' $EV if insmp, absorb(${ABS_EV2}) vce(cluster clus)
    if _rc exit
    matrix lv = (0.2 \ 0.2 \ 0.2 \ 0.2 \ 0.2)
    log using "$OUT\honest_${P}_`tag'_`y'.txt", text replace name(hd)
    di "HONEST RM `y' `tag'"
    capture noisily honestdid, pre(1/3) post(4/8) mvec(0(0.1)2) l_vec(lv)
    di "HONEST SD `y' `tag'"
    capture noisily honestdid, pre(1/3) post(4/8) mvec(0(0.02)0.3) l_vec(lv) delta(sd)
    log close hd
end

* ---------------------------------------------------------------------------------------------
* optional third argument: one sample only (used to split the slow cell set B across Stata instances)
local SFX ""
if "`only'" != "" local SFX "_`only'"
tempname HH
global HH "`HH'"
global P "`part'"
global BLK "`block'"
postfile `HH' str6 cellset str8 block str12 sample str40 group str10 outcome str6 est str6 fe str9 term ///
    double b se p N ntreat ncontrol str80 status using "$OUT\ev5_`part'_`block'`SFX'.dta", replace

if "`part'" == "A" use "$V5\ev5_A.dta", clear
if "`part'" == "B" use "$V5\ev5_B.dta", clear
if "`part'" == "E" use "$V5\ev5_Bentry.dta", clear
egen oyear = group(country_orig year)
egen orign = group(country_orig)
egen tyear = group(type year)
gen hs2s = substr(hs, 1, 2)
egen h2year = group(hs2s year)
if "`part'" == "A" {
    global ABS_EV1 "cell year"
    global ABS_EV2 "cell oyear"
    global ABS_EV2x "oyear"
    global ABS_EV3 "cell oyear tyear"
    global ABS_EV4 "cell oyear h2year"
    global FES "EV1 EV2 EV3 EV4"
    global O_STD "anyXL lnXL lnX lnXLpf SHL NL lnNL NEWL EXITL SURVL NDL NDA NEWDL NEWDA N"
    global O_PREF "anyXL lnXL NL NEWL EXITL SURVL NEWDL"
}
else {
    egen dyear = group(dest year)
    egen odyear = group(country_orig dest year)
    egen pyear = group(hs year)
    egen opyear = group(country_orig hs year)
    global ABS_EV1 "cell year"
    global ABS_EV2 "cell oyear dyear"
    global ABS_EV2x "oyear dyear"
    global ABS_EV3 "cell odyear"
    global ABS_EV4 "cell odyear pyear"
    global ABS_EV5 "cell opyear"
    global FES "EV1 EV2 EV3 EV4 EV5"
    global O_STD "anyXL lnXL lnX lnXLpf SHL NL lnNL NEWL EXITL SURVL N"
    global O_PREF "anyXL lnXL NL NEWL EXITL SURVL"
}
if "`part'" == "E" {
    global O_STD "anyXL lnXL NL"
    global O_PREF "anyXL"
}
local SAMPLES "g_v4 g_nc g_ps g_bal g_pre3"
if "`part'" == "E" local SAMPLES "g_be"
local GS "g_v4 g_ps"
if "`only'" != "" {
    local SAMPLES "`only'"
    local GS "`only'"
}
global GRP "all"

* ---------------------------------------------------------------------------------------------
if "`block'" == "std" {
    foreach g of local SAMPLES {
        global SMP "`g'"
        setev `g' "1"
        foreach y of global O_STD {
            foreach est in twfe cs sa bjs dcdh {
                onerun `y' `est' EV2
            }
        }
    }
}
if "`block'" == "fe" {
    foreach g of local GS {
        global SMP "`g'"
        setev `g' "1"
        foreach y of global O_STD {
            foreach f of global FES {
                onerun `y' twfe `f'
            }
            foreach f in EV1 EV2 EV3 EV4 {
                onerun `y' stk `f'
            }
            onerun `y' TF EV2TF
            onerun `y' T EV2T
        }
        foreach y of global O_PREF {
            onerun `y' fhs EV2
        }
    }
}
if "`block'" == "treat" {
    foreach g in g_for g_dom g_s10 g_s25 g_pers {
        global SMP "`g'"
        setev `g' "1"
        local OO "$O_PREF"
        if "`g'" == "g_for" local OO "anyXLd lnXLd NLd $O_PREF"
        foreach y of local OO {
            foreach est in twfe cs {
                onerun `y' `est' EV2
            }
        }
    }
    * E11d.4 cohorts: Callaway and Sant'Anna on each cohort against the never treated cells
    foreach g of local GS {
        global SMP "`g'"
        setev `g' "1"
        qui levelsof gvar if gvar > 0 & gvar < ., local(gs)
        foreach c of local gs {
            global GRP "cohort `c'"
            setev `g' "gvar == `c' | gvar == 0"
            foreach y of global O_PREF {
                onerun `y' csnev EV2
                onerun `y' twfe EV2
            }
        }
        global GRP "all"
    }
}
if "`block'" == "treatps" {
    * E11d.2-3 rechecked with the same selection rule for treated and controls (2026-11-24): treated cells as in each
    * definition (two years with exports before t0), controls the never treated cells of g_ps (two years with exports
    * before their pseudo t0)
    foreach g in g_for g_dom g_s10 g_s25 g_pers {
        cap drop `g'ps
        qui gen `g'ps = `g' if `g' > 0 & `g' < .
        qui replace `g'ps = 0 if g_ps == 0
        global SMP "`g'ps"
        setev `g'ps "1"
        local OO "$O_PREF"
        if "`g'" == "g_for" local OO "anyXLd lnXLd NLd $O_PREF"
        foreach y of local OO {
            foreach est in twfe cs csnev {
                onerun `y' `est' EV2
            }
        }
    }
}
if "`block'" == "het" {
    local CUTS "high_mean high_median high_top tercile_stage type processing_degree"
    foreach g of local GS {
        global SMP "`g'"
        foreach cut of local CUTS {
            capture confirm string variable `cut'
            if _rc == 0 qui levelsof `cut', local(vals)
            else qui levelsof `cut', local(vals)
            foreach v of local vals {
                capture confirm string variable `cut'
                if _rc == 0 {
                    global GRP "`cut': `v'"
                    setev `g' `"`cut' == "`v'""'
                }
                else {
                    global GRP "`cut': `v'"
                    setev `g' "`cut' == `v'"
                }
                foreach y of global O_PREF {
                    onerun `y' twfe EV2
                    onerun `y' cs EV2
                }
            }
        }
    }
    global GRP "all"
}
if "`block'" == "csnev" {
    * Callaway and Sant'Anna with never treated controls only (rerun 2026-11-24: in the std block csnev used the csdid
    * default, which is not yet treated, and repeated cs)
    foreach g of local SAMPLES {
        global SMP "`g'"
        setev `g' "1"
        foreach y of global O_STD {
            onerun `y' csnev EV2
        }
    }
}
if "`block'" == "het2" {
    * E11e for the cuts of E10a and E10b (PCI above the export weighted median, Rauch complete conservative)
    foreach g of local GS {
        global SMP "`g'"
        foreach cut in high_PCI rauch_full_con {
            qui levelsof `cut', local(vals)
            foreach v of local vals {
                global GRP "`cut': `v'"
                setev `g' `"`cut' == "`v'""'
                foreach y of global O_PREF {
                    onerun `y' twfe EV2
                    onerun `y' cs EV2
                }
            }
        }
    }
    global GRP "all"
}
if "`block'" == "add" {
    foreach g of local GS {
        global SMP "`g'"
        setev `g' "1"
        foreach y of global O_STD {
            onerun `y' stk EV2
        }
        if "`part'" != "E" onerun XL jw EV2
        foreach y of global O_PREF {
            honest `y' `g'
        }
    }
}
if "`block'" == "spill" & "`part'" == "A" {
    * treated cells only (t0 >= 2013, any history and the v4 rule): identification from the timing of entry, not yet
    * treated cells as controls; the destination sets exist only for cells with an entrant group
    foreach g in g_nc g_v4 {
        global SMP "`g'"
        setev `g' "`g' > 0"
        foreach y in NEWDL NEWDL_go NEWDL_xo NEWDL_ga NEWDL_xa {
            onerun `y' twfe EV2
            onerun `y' cs EV2
            onerun `y' bjs EV2
        }
    }
}
if "`block'" == "placebo" {
    * event three years earlier on 2012-2016 (real entries of 2017 and 2018 move to 2014 and 2015)
    foreach g of local GS {
        global SMP "`g'"
        preserve
        qui gen gpl = cond(`g' >= 2017 & `g' < ., `g' - 3, cond(`g' == 0, 0, .))
        qui keep if year <= 2016
        setev gpl "1"
        foreach y of global O_PREF {
            onerun `y' twfe EV2
            onerun `y' cs EV2
        }
        restore
    }
}
postclose `HH'
