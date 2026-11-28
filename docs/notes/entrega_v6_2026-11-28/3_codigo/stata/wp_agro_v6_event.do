* =====================================================================================================================
* wp_agro_v6_event.do  --  cohort-aligned stacked event studies of round v6 (especificaciones_estimaciones_v6_2026-11-25.md)
*
*   StataMP-64.exe /e do <copy of this file> <level> <block>
*     level = A (origin x product), B (origin x destination x product), H (origin x HS4 heading)
*     block = main     V6-11 / V6-13 panel A / V6-15: full or short list, EV2 (A, H) or EV3 (B), averages 0-2 and 0-4,
*                      pre-trend test (b-3 = b-2 = 0), counts of treated cells and clusters per coefficient
*             cohort   A.7 point 9: Treat x k x cohort, cohort coefficients, simple and weighted averages (short list)
*             placebo  A.7 point 11: event moved to g - 3 (cohorts 2017, 2018), years before g
*             chk      V6-12 (A only): robustness rows of NEWL (and rows 2, 3, 12 of anyXL)
*             fe       V6-13 panels B to D (B only): EV3, EV6, EV7; event (i) with pure controls; event (ii) with EV6
*             het      V6-14: interactions Treat x k x group, equality tests (A; B in the version of panel C)
*             hetplc   placebo by group for V6-14
*             bridge   V6-16 (A, B): P0 to P4 and the three completing estimations
*   Run each job from its own copy of the do-file in its own folder (Stata reads do-files line by line).
*   Output: output/wp_2012_2018/agro/v6/ev6_<level>_<block>.dta, honest_v6_*.txt
* =====================================================================================================================
version 18
clear all
set more off
set matsize 5000
args level block
global ROOT "C:\Sebas BID\Orbis_DNB_Customs_Final"
global V6   "$ROOT\data\intermediate\wp\v6"
global OUT  "$ROOT\output\wp_2012_2018\agro\v6"
cap mkdir "$OUT"
global EVV "ev_m4 ev_m3 ev_m2 ev_p0 ev_p1 ev_p2 ev_p3 ev_p4"

* ---------------------------------------------------------------------------------------------------------------------
capture program drop putrow
program define putrow
    args term b se p N nt nc
    post $HH ("$L") ("$BLK") ("$VAR") ("$GRP") ("$Y") ("$EST") ("$FEC") ("$CLC") ("`term'") (`b') (`se') (`p') (`N') (`nt') (`nc') ("ok")
end
capture program drop putfail
program define putfail
    args msg
    post $HH ("$L") ("$BLK") ("$VAR") ("$GRP") ("$Y") ("$EST") ("$FEC") ("$CLC") ("none") (.) (.) (.) (0) (0) (0) ("`msg'")
end

capture program drop mkev
program define mkev
    * event dummies on the current stacked data (treat, k)
    cap drop ev_*
    foreach j in 4 3 2 {
        qui gen byte ev_m`j' = treat * (k == -`j')
    }
    foreach j in 0 1 2 3 4 {
        qui gen byte ev_p`j' = treat * (k == `j')
    }
end

capture program drop avgpost
program define avgpost
    * averages 0-2 and 0-4 and the pre-trend test after an estimation with $EVV; args: N, prefix of terms (default ev_)
    args N
    local have ""
    foreach t of global EVV {
        capture local sx = _se[`t']
        if _rc continue
        if "`sx'" == "" continue
        if `sx' > 0 & `sx' < . local have "`have' `t'"
    }
    foreach h in 2 4 {
        local s ""
        local n 0
        forvalues j = 0/`h' {
            if strpos(" `have' ", " ev_p`j' ") {
                local s "`s' + ev_p`j'"
                local ++n
            }
        }
        if `n' > 0 {
            capture lincom (0 `s') / `n'
            if _rc == 0 putrow Avg0`h' `r(estimate)' `r(se)' `r(p)' `N' `n' .
        }
    }
    local pre ""
    foreach t in ev_m3 ev_m2 {
        if strpos(" `have' ", " `t' ") local pre "`pre' `t'"
    }
    if "`pre'" != "" {
        capture test `pre'
        if _rc == 0 putrow pre_test . . `r(p)' `N' `=wordcount("`pre'")' .
    }
end

capture program drop es
program define es
    * one stacked event study. args: y est(ols|ppml) absorb clusters. Sample: global IFC.
    args y est abs clus
    global Y "`y'"
    global EST "`est'"
    qui count if $IFC & `y' < .
    if r(N) == 0 {
        putfail "empty sample"
        exit
    }
    local A ""
    foreach a of local abs {
        local A "`A' `a'"
    }
    * first stage: N and D are zero before entry in both groups (at risk), so only the post terms are estimated
    local evs "$EVV"
    if inlist("`y'", "N", "D") local evs "ev_p0 ev_p1 ev_p2 ev_p3 ev_p4"
    if "`est'" == "ols" capture reghdfe `y' `evs' if $IFC, absorb(`A') vce(cluster `clus')
    if "`est'" == "ppml" capture ppmlhdfe `y' `evs' if $IFC, absorb(`A') vce(cluster `clus')
    if _rc {
        putfail "error `=_rc'"
        exit
    }
    local N = e(N)
    tempvar s
    qui gen byte `s' = e(sample)
    local c1 : word 1 of `clus'
    foreach t of global EVV {
        local term = cond(substr("`t'", 4, 1) == "m", "Tm" + substr("`t'", 5, 1), "Tp" + substr("`t'", 5, 1))
        local bb = .
        local ss = .
        if strpos(" `evs' ", " `t' ") {
            capture local bb = _b[`t']
            if _rc local bb = .
            capture local ss = _se[`t']
            if _rc local ss = .
        }
        if `ss' == 0 | `ss' >= . {
            local bb = .
            local ss = .
        }
        qui distinct cell if `s' & `t' == 1
        local nt = r(ndistinct)
        qui distinct `c1' if `s' & `t' == 1
        local nc = r(ndistinct)
        putrow `term' `bb' `ss' (2*normal(-abs(`bb'/`ss'))) `N' `nt' `nc'
    }
    avgpost `N'
    qui distinct cell if `s' & treat == 1
    local ntr = r(ndistinct)
    qui distinct cell if `s' & treat == 0
    local nco = r(ndistinct)
    qui distinct `c1' if `s'
    putrow cells . . . `N' `ntr' `nco'
    putrow clusters . . . `N' `r(ndistinct)' .
end

capture program drop honest6
program define honest6
    * Rambachan and Roth on the aligned stacked estimator: average of k = 0 to 2; args y abs clus tag
    args y abs clus tag
    capture reghdfe `y' $EVV if $IFC, absorb(`abs') vce(cluster `clus')
    if _rc exit
    matrix lv = (1/3 \ 1/3 \ 1/3 \ 0 \ 0)
    log using "$OUT\honest_v6_${L}_`tag'_`y'.txt", text replace name(hd)
    di "HONEST RM `y' `tag'"
    capture noisily honestdid, pre(1/3) post(4/8) mvec(0(0.1)2) l_vec(lv)
    di "HONEST SD `y' `tag'"
    capture noisily honestdid, pre(1/3) post(4/8) mvec(0(0.02)0.3) l_vec(lv) delta(sd)
    log close hd
end

* ---------------------------------------------------------------------------------------------------------------------
tempname HH
global HH "`HH'"
global L "`level'"
global BLK "`block'"
global VAR "main"
global GRP "all"
postfile `HH' str2 level str8 block str48 variant str48 group str12 outcome str5 est str6 fe str10 clus str12 term ///
    double b se p N ntreat nclus str80 status using "$OUT\ev6_`level'_`block'.dta", replace

* ---- data
if inlist("`block'", "main", "cohort", "chk", "fe", "het") use "$V6\ev6_`level'_stk.dta", clear
if inlist("`block'", "placebo", "hetplc") use "$V6\ev6_`level'_plc.dta", clear
if "`block'" != "bridge" {
    mkev
    qui gen XL_ppml = XL
    egen cs = group(cell stack)
    egen oys = group(country_orig year stack)
    if "`level'" == "B" {
        egen odys = group(country_orig dest year stack)
        egen pys = group(hs year stack)
        egen opys = group(country_orig hs year stack)
        egen dpys = group(dest hs year stack)
    }
    if "`level'" == "A" {
        egen tys = group(type year stack)
        egen h2ys = group(hs2 year stack)
        egen h4ys = group(hs4 year stack)
        egen h6ys = group(hs year stack)
        egen hs6n = group(hs)
        egen hs4n = group(hs4)
        egen orign = group(country_orig)
    }
    if "`level'" == "H" {
        egen h2ys = group(hs2 year stack)
    }
}
if "`level'" == "A" {
    global ABS "cs oys"
    global FEMAIN "EV2"
    global CL "cell"
    global CLMAIN "CL-op"
    global FULL "anyXL lnXL XL_ppml lnX NL lnNL NEWL EXITL SURVL N D"
    global SHORT "lnX lnXL lnNL anyXL NEWL N D"
}
if "`level'" == "H" {
    global ABS "cs oys"
    global FEMAIN "EV2"
    global CL "cell"
    global CLMAIN "CL-oh"
    global FULL "lnX lnXL lnNL anyXL NEWL N D"
    global SHORT "lnX lnXL lnNL anyXL NEWL N D"
}
if "`level'" == "B" {
    global ABS "cs odys"
    global FEMAIN "EV3"
    global CL "od op"
    global CLMAIN "CL-B"
    global FULL "anyXL lnXL XL_ppml lnX NL lnNL NEWL EXITL SURVL N D"
    global SHORT "lnX lnXL lnNL anyXL NEWL N D"
}
global FEC "$FEMAIN"
global CLC "$CLMAIN"

* =====================================================================================================================
if "`block'" == "main" | "`block'" == "placebo" {
    global IFC "inR == 1"
    foreach y of global FULL {
        local est = cond("`y'" == "XL_ppml", "ppml", "ols")
        es `y' `est' "$ABS" "$CL"
        if inlist("`y'", "NL", "NEWL") {
            global VAR "PPML"
            es `y' ppml "$ABS" "$CL"
            global VAR "main"
        }
    }
    if "`block'" == "main" & "`level'" == "A" {
        honest6 NEWL "$ABS" "$CL" main
        honest6 anyXL "$ABS" "$CL" main
    }
    if "`block'" == "main" & "`level'" == "H" {
        global VAR "EV4"
        global FEC "EV4"
        foreach y of global SHORT {
            es `y' ols "cs oys h2ys" "$CL"
        }
    }
}

* =====================================================================================================================
if "`block'" == "cohort" {
    global IFC "inR == 1"
    foreach y of global SHORT {
        global Y "`y'"
        global EST "ols"
        local X ""
        foreach g in 2014 2015 2016 2017 2018 {
            foreach t of global EVV {
                if inlist("`y'", "N", "D") & substr("`t'", 4, 1) == "m" continue
                cap drop `t'_`g'
                qui gen byte `t'_`g' = `t' * (stack == `g')
                qui sum `y' if `t'_`g' == 1 & $IFC
                * terms whose outcome is constant by construction (anyXL two years before entry) make the covariance singular
                if r(N) > 0 & r(sd) > 0 & r(sd) < . local X "`X' `t'_`g'"
            }
        }
        capture reghdfe `y' `X' if $IFC, absorb($ABS) vce(cluster $CL)
        if _rc {
            putfail "error `=_rc'"
            continue
        }
        local N = e(N)
        local wsum 0
        local wexp ""
        foreach g in 2014 2015 2016 2017 2018 {
            qui distinct cell if e(sample) & treat == 1 & stack == `g'
            local n`g' = r(ndistinct)
            local s ""
            local n 0
            foreach t of global EVV {
                capture local se_ = _se[`t'_`g']
                if _rc continue
                if `se_' == 0 continue
                local term = cond(substr("`t'", 4, 1) == "m", "Tm" + substr("`t'", 5, 1), "Tp" + substr("`t'", 5, 1))
                putrow `term'_c`g' `=_b[`t'_`g']' `se_' (2*normal(-abs(_b[`t'_`g']/`se_'))) `N' `n`g'' .
                if inlist("`t'", "ev_p0", "ev_p1", "ev_p2") {
                    local s "`s' + `t'_`g'"
                    local ++n
                }
            }
            if `n' > 0 {
                capture lincom (0 `s') / `n'
                if _rc == 0 putrow Avg02_c`g' `r(estimate)' `r(se)' `r(p)' `N' `n`g'' `n'
                local wexp "`wexp' + `n`g'' * (0 `s') / `n'"
                local wsum = `wsum' + `n`g''
            }
        }
        capture lincom (0 `wexp') / `wsum'
        if _rc == 0 putrow AvgW02 `r(estimate)' `r(se)' `r(p)' `N' `wsum' .
    }
}

* =====================================================================================================================
if "`block'" == "chk" & "`level'" == "A" {
    * support of EV8 and EV9: treated cells with at least one control of the same heading / the same product in another origin
    bys stack hs4: egen c4 = max(treat == 0 & inR == 1)
    bys stack hs: egen c6 = max(treat == 0 & inR == 1)
    global Y "support"
    global VAR "support"
    qui distinct cell if treat == 1 & inR == 1
    local nt = r(ndistinct)
    qui distinct cell if treat == 1 & inR == 1 & c4 == 1
    putrow support_EV8 . . . . `r(ndistinct)' `nt'
    qui distinct cell if treat == 1 & inR == 1 & c6 == 1
    putrow support_EV9 . . . . `r(ndistinct)' `nt'
    * top 1 percent of cells by local exporters in g - 1
    bys cell stack: egen nl_pre = max(NL * (k == -1))
    qui _pctile nl_pre if inR == 1 & k == -1, p(99)
    local p99 = r(r1)
    foreach y in NEWL anyXL {
        global IFC "inR == 1"
        if "`y'" == "NEWL" {
            foreach f in EV3 EV4 EV8 EV9 {
                global VAR "`f'"
                global FEC "`f'"
                if "`f'" == "EV3" local ab "cs oys tys"
                if "`f'" == "EV4" local ab "cs oys h2ys"
                if "`f'" == "EV8" local ab "cs oys h4ys"
                if "`f'" == "EV9" local ab "cs oys h6ys"
                es `y' ols "`ab'" "cell"
            }
            global FEC "EV2"
        }
        global VAR "R3"
        global IFC "inR3 == 1"
        es `y' ols "$ABS" "cell"
        global VAR "R0"
        global IFC "1"
        es `y' ols "$ABS" "cell"
        global VAR "fixed composition"
        global IFC "inR == 1 & stack <= 2016 & k >= -2 & k <= 2"
        es `y' ols "$ABS" "cell"
        if "`y'" == "NEWL" {
            global IFC "inR == 1"
            global VAR "PPML"
            es `y' ppml "$ABS" "cell"
            global VAR "fixed window (NEWL_fw)"
            es NEWL_fw ols "$ABS" "cell"
            global Y "NEWL"
            global VAR "without the top 1 percent of cells by local exporters in g - 1"
            global IFC "inR == 1 & nl_pre <= `p99'"
            es `y' ols "$ABS" "cell"
            global IFC "inR == 1"
            global VAR "cluster HS6 product"
            global CLC "CL-hs6"
            es `y' ols "$ABS" "hs6n"
            global VAR "cluster entrant group"
            global CLC "entrant group"
            es `y' ols "$ABS" "egrp"
            global CLC "CL-op"
            levelsof country_orig, local(origs)
            foreach o of local origs {
                global VAR "without `o'"
                global IFC `"inR == 1 & country_orig != "`o'""'
                es `y' ols "$ABS" "cell"
            }
            global VAR "without the 2017 cohort"
            global IFC "inR == 1 & stack != 2017"
            es `y' ols "$ABS" "cell"
            global VAR "without products with hs_n1 = 1"
            global IFC "inR == 1 & hs_n1 == 0"
            es `y' ols "$ABS" "cell"
            global VAR "without doubtful new exporters (NEWL_clean)"
            global IFC "inR == 1"
            es NEWL_clean ols "$ABS" "cell"
        }
    }
    global IFC "inR == 1 & stack <= 2016 & k >= -2 & k <= 2"
    honest6 NEWL "$ABS" "cell" fixedcomp
}

* =====================================================================================================================
if "`block'" == "fe" & "`level'" == "B" {
    global IFC "inR == 1"
    foreach f in EV6 EV7 {
        global VAR "panel B, `f'"
        global FEC "`f'"
        if "`f'" == "EV6" local ab "cs odys opys"
        if "`f'" == "EV7" local ab "cs odys opys dpys"
        foreach y of global SHORT {
            es `y' ols "`ab'" "$CL"
        }
    }
    global VAR "panel C, event (i), pure controls, EV3"
    global FEC "EV3"
    global IFC `"inR == 1 & ((treat == 1 & etype == 1) | (treat == 0 & ctype == "pure"))"'
    foreach y of global SHORT {
        es `y' ols "$ABS" "$CL"
    }
    global VAR "panel D, event (ii), all controls, EV6"
    global FEC "EV6"
    global IFC "inR == 1 & ((treat == 1 & etype == 2) | treat == 0)"
    foreach y of global SHORT {
        es `y' ols "cs odys opys" "$CL"
    }
}

* =====================================================================================================================
if "`block'" == "het" | "`block'" == "hetplc" {
    if "`level'" == "B" {
        global IFC `"inR == 1 & ((treat == 1 & etype == 1) | (treat == 0 & ctype == "pure"))"'
        local cuts "high_PCI6 rauch_bin_con rauch_full_con type"
    }
    else {
        global IFC "inR == 1"
        local cuts "high_PCI6 rauch_bin_con rauch_full_con type ent_big ent_incumbent"
    }
    foreach cut of local cuts {
        capture confirm variable `cut'
        if _rc continue
        cap drop gcut
        cap label drop gcut
        capture confirm string variable `cut'
        if _rc == 0 egen gcut = group(`cut'), label
        else {
            qui gen gcut = `cut' + 1 if treat == 1
            qui replace gcut = 0 if treat == 0
        }
        local outs "NEWL anyXL lnX N D"
        if inlist("`cut'", "ent_big", "ent_incumbent") local outs "anyXL NEWL lnXL N D"
        qui levelsof gcut if treat == 1 & $IFC, local(gs)
        foreach y of local outs {
            global Y "`y'"
            global EST "ols"
            global VAR "`cut'"
            local X ""
            foreach g of local gs {
                foreach t of global EVV {
                    cap drop `t'_g`g'
                    if inlist("`y'", "N", "D") & substr("`t'", 4, 1) == "m" continue
                    qui gen byte `t'_g`g' = `t' * (gcut == `g')
                    qui sum `y' if `t'_g`g' == 1 & $IFC
                    if r(N) > 0 & r(sd) > 0 & r(sd) < . local X "`X' `t'_g`g'"
                }
            }
            foreach clus in "$CL" "hs4n" {
                if "`clus'" == "hs4n" & "`level'" != "A" continue
                if "`clus'" == "hs4n" & inlist("`cut'", "ent_big", "ent_incumbent") continue
                global CLC = cond("`clus'" == "hs4n", "CL-hs4", "$CLMAIN")
                capture reghdfe `y' `X' if $IFC, absorb($ABS) vce(cluster `clus')
                if _rc {
                    putfail "error `=_rc'"
                    continue
                }
                local N = e(N)
                local avgs ""
                local pres ""
                local gsok ""
                foreach g of local gs {
                    capture local lab : label (gcut) `g'
                    if _rc local lab "`cut'=`=`g'-1'"
                    global GRP "`lab'"
                    qui distinct cell if e(sample) & treat == 1 & gcut == `g'
                    local ntg = r(ndistinct)
                    local s ""
                    local n 0
                    foreach t of global EVV {
                        capture local se_ = _se[`t'_g`g']
                        if _rc continue
                        if `se_' == 0 continue
                        local term = cond(substr("`t'", 4, 1) == "m", "Tm" + substr("`t'", 5, 1), "Tp" + substr("`t'", 5, 1))
                        putrow `term' `=_b[`t'_g`g']' `se_' (2*normal(-abs(_b[`t'_g`g']/`se_'))) `N' `ntg' .
                        if inlist("`t'", "ev_p0", "ev_p1", "ev_p2") {
                            local s "`s' + `t'_g`g'"
                            local ++n
                        }
                        if inlist("`t'", "ev_m3", "ev_m2") local pres "`pres' `t'_g`g'"
                    }
                    if `n' > 0 {
                        capture lincom (0 `s') / `n'
                        if _rc == 0 putrow Avg02 `r(estimate)' `r(se)' `r(p)' `N' `ntg' `n'
                        local ws : display %9.6f 1 / `n'
                        local ws = trim("`ws'")
                        local lin = subinstr("`s'", "+ ", "+`ws'*", .)
                        local lin = subinstr("`lin'", " ", "", .)
                        if strpos("`lab'", "Not classified") == 0 {
                            local avgs "`avgs' 0`lin'"
                            local gsok "`gsok' `g'"
                        }
                    }
                }
                global GRP "all groups"
                local na = wordcount("`avgs'")
                if `na' >= 2 {
                    local first : word 1 of `avgs'
                    local eqs ""
                    forvalues i = 2/`na' {
                        local w : word `i' of `avgs'
                        local eqs "`eqs' (`first'=`w')"
                    }
                    capture test `eqs'
                    if _rc == 0 putrow p_equal_avg02 . . `r(p)' `N' `na' .
                }
                if "`pres'" != "" & `na' >= 2 {
                    * equality of the pre-period coefficients across groups, by event time
                    local eq ""
                    foreach t in ev_m3 ev_m2 {
                        local first ""
                        foreach g of local gsok {
                            capture local se_ = _se[`t'_g`g']
                            if _rc continue
                            if `se_' == 0 continue
                            if "`first'" == "" local first "`t'_g`g'"
                            else local eq "`eq' (`first' = `t'_g`g')"
                        }
                    }
                    if "`eq'" != "" {
                        capture test `eq'
                        if _rc == 0 putrow p_equal_pre . . `r(p)' `N' . .
                    }
                }
                global GRP "all"
            }
        }
    }
}

* =====================================================================================================================
if "`block'" == "bridge" {
    * P0 to P4 of V6-16. Panel cell x year, 2012-2018.
    use "$V6\ev6_`level'_panel.dta", clear
    egen oy = group(country_orig year)
    if "`level'" == "B" {
        egen ody = group(country_orig dest year)
        egen odn = group(country_orig dest)
        egen opn = group(country_orig hs)
        local AB "cell ody"
        local CLB "odn opn"
        global FEC "FE4=EV3"
        global CLC "CL-B"
    }
    else {
        local AB "cell oy"
        local CLB "cell"
        global FEC "EV2"
        global CLC "CL-op"
    }
    global EST "ols"
    foreach y in lnX lnXL lnNL anyXL NEWL {
        global Y "`y'"
        foreach P in P0 P1 P2b P3 {
            global VAR "`P'"
            local reg = cond("`P'" == "P3", "Post", "D")
            local cond "1"
            if "`P'" == "P1" local cond "atrisk == 1"
            if inlist("`P'", "P2b", "P3") local cond "insample == 1"
            capture reghdfe `y' `reg' if `cond', absorb(`AB') vce(cluster `CLB')
            if _rc {
                putfail "error `=_rc'"
                continue
            }
            putrow `reg' `=_b[`reg']' `=_se[`reg']' (2*normal(-abs(_b[`reg']/_se[`reg']))) `e(N)' . .
            if "`P'" == "P3" {
                foreach fs in D N {
                    capture reghdfe `fs' Post if insample == 1 & `y' < ., absorb(`AB') vce(cluster `CLB')
                    if _rc == 0 putrow FS_`fs' `=_b[Post]' `=_se[Post]' (2*normal(-abs(_b[Post]/_se[Post]))) `e(N)' . .
                }
            }
        }
        * the same columns interacted with high_PCI6
        foreach P in P0 P2b P3 {
            global VAR "`P' x high_PCI6"
            local reg = cond("`P'" == "P3", "Post", "D")
            local cond = cond("`P'" == "P0", "1", "insample == 1")
            cap drop rH rL
            qui gen rH = `reg' * (high_PCI6 == "High")
            qui gen rL = `reg' * (high_PCI6 == "Low")
            capture reghdfe `y' rH rL if `cond' & inlist(high_PCI6, "High", "Low"), absorb(`AB') vce(cluster `CLB')
            if _rc continue
            putrow `reg'_High `=_b[rH]' `=_se[rH]' (2*normal(-abs(_b[rH]/_se[rH]))) `e(N)' . .
            putrow `reg'_Low `=_b[rL]' `=_se[rL]' (2*normal(-abs(_b[rL]/_se[rL]))) `e(N)' . .
            capture test rH = rL
            if _rc == 0 putrow p_equal . . `r(p)' `e(N)' . .
        }
    }
    if "`level'" == "B" {
        * 1. Dotros
        global VAR "Dotros"
        foreach y in lnX lnXL lnNL anyXL NEWL {
            global Y "`y'"
            capture reghdfe `y' D Dotros, absorb(`AB') vce(cluster `CLB')
            if _rc continue
            foreach v in D Dotros {
                putrow `v' `=_b[`v']' `=_se[`v']' (2*normal(-abs(_b[`v']/_se[`v']))) `e(N)' . .
            }
        }
        * 3. dCDH on D itself (switching), nonparametric trends by origin-destination pair
        global VAR "dCDH on D"
        global EST "dcdh"
        foreach y in lnX lnXL {
            global Y "`y'"
            capture did_multiplegt_dyn `y' cell year D, effects(3) placebo(2) cluster(odn) trends_nonparam(odn) graph_off
            if _rc {
                putfail "not estimable: error `=_rc'"
                continue
            }
            forvalues j = 1/3 {
                local jj = `j' - 1
                capture putrow Tp`jj' `=e(Effect_`j')' `=e(se_effect_`j')' (2*normal(-abs(e(Effect_`j')/e(se_effect_`j')))) `=e(N_effect_`j')' . .
            }
            forvalues j = 1/2 {
                local jj = `j' + 1
                capture putrow Tm`jj' `=e(Placebo_`j')' `=e(se_placebo_`j')' (2*normal(-abs(e(Placebo_`j')/e(se_placebo_`j')))) . . .
            }
        }
    }
    if "`level'" == "A" {
        * 2. gradient when aggregating destinations: ln X_opt and ln XL_opt on ln N_opt and ln N x PCI6_z, cells with N >= 1
        global VAR "gradient at the op level"
        global CLC "CL-hs4"
        egen hs4n = group(hs4)
        qui gen lnNxPCI = lnN * PCI6_z
        foreach y in lnX lnXL {
            global Y "`y'"
            capture reghdfe `y' lnN lnNxPCI if N >= 1, absorb(cell oy) vce(cluster hs4n)
            if _rc continue
            foreach v in lnN lnNxPCI {
                putrow `v' `=_b[`v']' `=_se[`v']' (2*normal(-abs(_b[`v']/_se[`v']))) `e(N)' . .
            }
        }
    }
    * P4: static difference in differences in the aligned stacks (Post x Treat), fixed effects by stack
    use "$V6\ev6_`level'_stk.dta", clear
    keep if inR == 1
    qui gen PT = treat * (k >= 0)
    egen cs = group(cell stack)
    if "`level'" == "B" {
        egen odys = group(country_orig dest year stack)
        local AS "cs odys"
        local CLS "od op"
    }
    else {
        egen oys = group(country_orig year stack)
        local AS "cs oys"
        local CLS "cell"
    }
    global VAR "P4"
    global EST "ols"
    foreach y in lnX lnXL lnNL anyXL NEWL {
        global Y "`y'"
        capture reghdfe `y' PT, absorb(`AS') vce(cluster `CLS')
        if _rc == 0 putrow PostxTreat `=_b[PT]' `=_se[PT]' (2*normal(-abs(_b[PT]/_se[PT]))) `e(N)' . .
    }
}

postclose `HH'
