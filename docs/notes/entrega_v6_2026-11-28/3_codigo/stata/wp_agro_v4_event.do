* =====================================================================================================================
* wp_agro_v4_event.do  --  E6 of especificaciones_estimaciones_v4_2026-11-17.md: entry of the first multinational
* =====================================================================================================================
* Inputs : data/intermediate/wp/v4/event_op.dta, event_odp.dta (stylized_facts/python/wp_agro_v4_data.py)
*          balanced cell x year panels 2012-2018, zero filled. gvar = year of the first MNE exporter in the cell
*          (2014 to 2018, at least two years with positive exports before it), 0 = never treated. Cells with an MNE in
*          2012 are dropped (always treated).
* Output : output/wp_2012_2018/agro/v4/v4_event.dta, one row per cell set x sample x outcome x estimator x term
*          (Tm4 ... Tp4, Post_avg, pre_test), read by wp_agro_v4_workbook.py
* Usage  : StataMP-64.exe /e do wp_agro_v4_event.do <part>     part = A (op cells) or B (odp cells); default both
*
* Estimators
*   twfe : reghdfe on event-time dummies (-4 binned, -3, -2, 0, 1, 2, 3, 4; base -1), cell FE and origin x year FE
*          (B adds destination x year FE). Never and not yet treated cells are the controls.
*   cs   : Callaway and Sant'Anna (csdid 2.0.3), not yet treated controls, universal base period (t0 - 1), analytical
*          standard errors, event aggregation over -4..4.
*   sa   : Sun and Abraham (eventstudyinteract), never treated controls, same dummies and FE as twfe.
*   ppml : ppmlhdfe of local exports in levels on the twfe dummies.
* Clusters: A by cell (origin x product), B by origin and destination pair.
* =====================================================================================================================
version 18
clear all
set more off
set matsize 2000
args part
if "`part'" == "" local part "A B"

global ROOT "C:\Sebas BID\Orbis_DNB_Customs_Final"
global V4   "$ROOT\data\intermediate\wp\v4"
global OUT  "$ROOT\output\wp_2012_2018\agro\v4"
cap mkdir "$OUT"

global OUTCOMES "lnXL anyXL NL lnNL lnX N"
global EV "ev_m4 ev_m3 ev_m2 ev_0 ev_1 ev_2 ev_3 ev_4"

* ---------------------------------------------------------------------------------------------
capture program drop onerun
program define onerun
    args H P tag y est cond gv
    local status "ok"
    local cnt = 0
    qui count if `cond'
    if r(N) == 0 {
        post `H' ("`P'") ("`tag'") ("`y'") ("`est'") ("none") (.) (.) (.) (0) (0) (0) ("empty sample")
        exit
    }
    qui distinct_cells `"`cond'"'
    local nc = r(nc)
    local nt = r(nt)
    if "`est'" == "twfe" | "`est'" == "ppml" {
        if "`est'" == "twfe" capture reghdfe `y' $EV if `cond', absorb($ABS) vce(cluster clus)
        if "`est'" == "ppml" capture ppmlhdfe `y' $EV if `cond', absorb($ABS) vce(cluster clus)
        if _rc {
            post `H' ("`P'") ("`tag'") ("`y'") ("`est'") ("none") (.) (.) (.) (0) (`nc') (`nt') ("error `=_rc'")
            exit
        }
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
            post `H' ("`P'") ("`tag'") ("`y'") ("`est'") ("`t'") (`bb') (`ss') (2 * normal(-abs(`bb' / `ss'))) (`N') (`nc') (`nt') ("ok")
        }
        capture test ev_m4 ev_m3 ev_m2
        local pp = cond(_rc, ., r(p))
        post `H' ("`P'") ("`tag'") ("`y'") ("`est'") ("pre_test") (.) (.) (`pp') (`N') (`nc') (`nt') ("ok")
        capture lincom (ev_0 + ev_1 + ev_2 + ev_3 + ev_4) / 5
        if _rc == 0 post `H' ("`P'") ("`tag'") ("`y'") ("`est'") ("Post_avg") (r(estimate)) (r(se)) (r(p)) (`N') (`nc') (`nt') ("ok")
    }
    if "`est'" == "cs" {
        local bal = cond(inlist("`y'", "lnXL", "lnNL", "lnX"), "bal(pair)", "")
        capture csdid `y' if `cond', ivar(cell) time(year) gvar(`gv') notyet analytical pointwise cluster(clus) `bal'
        if _rc {
            post `H' ("`P'") ("`tag'") ("`y'") ("`est'") ("none") (.) (.) (.) (0) (`nc') (`nt') ("error `=_rc'")
            exit
        }
        local N = e(N)
        capture estat event, window(-4 4) post
        if _rc {
            post `H' ("`P'") ("`tag'") ("`y'") ("`est'") ("none") (.) (.) (.) (`N') (`nc') (`nt') ("estat error `=_rc'")
            exit
        }
        local names : colnames e(b)
        foreach t of local names {
            if "`t'" == "Tm1" continue
            local bb = _b[`t']
            local ss = _se[`t']
            post `H' ("`P'") ("`tag'") ("`y'") ("`est'") ("`t'") (`bb') (`ss') (2 * normal(-abs(`bb' / `ss'))) (`N') (`nc') (`nt') ("ok")
        }
        local pre ""
        foreach t in Tm4 Tm3 Tm2 {
            if strpos(" `names' ", " `t' ") local pre "`pre' `t'"
        }
        capture test `pre'
        local pp = cond(_rc, ., r(p))
        post `H' ("`P'") ("`tag'") ("`y'") ("`est'") ("pre_test") (.) (.) (`pp') (`N') (`nc') (`nt') ("ok")
    }
    if "`est'" == "sa" {
        capture eventstudyinteract `y' $EV if `cond', cohort(cohort) control_cohort(never) absorb($ABS) vce(cluster clus)
        if _rc {
            post `H' ("`P'") ("`tag'") ("`y'") ("`est'") ("none") (.) (.) (.) (0) (`nc') (`nt') ("error `=_rc'")
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
            post `H' ("`P'") ("`tag'") ("`y'") ("`est'") ("`t'") (`bb') (`ss') (2 * normal(-abs(`bb' / `ss'))) (`N') (`nc') (`nt') ("ok")
        }
        * joint test of the three pre-period coefficients and the average of the five post-period ones
        matrix bp = B[1, 1..3]
        matrix Vp = V[1..3, 1..3]
        capture matrix W = bp * invsym(Vp) * bp'
        local pp = cond(_rc, ., chi2tail(3, W[1, 1]))
        post `H' ("`P'") ("`tag'") ("`y'") ("`est'") ("pre_test") (.) (.) (`pp') (`N') (`nc') (`nt') ("ok")
        matrix a = (0, 0, 0, 0.2, 0.2, 0.2, 0.2, 0.2)
        matrix m = B * a'
        matrix s = a * V * a'
        local bb = m[1, 1]
        local ss = sqrt(s[1, 1])
        post `H' ("`P'") ("`tag'") ("`y'") ("`est'") ("Post_avg") (`bb') (`ss') (2 * normal(-abs(`bb' / `ss'))) (`N') (`nc') (`nt') ("ok")
    }
end

capture program drop distinct_cells
program define distinct_cells, rclass
    args cond
    tempvar t1 t2
    qui egen `t1' = tag(cell) if `cond'
    qui count if `t1' == 1
    return scalar nc = r(N)
    qui count if `t1' == 1 & gvar > 0
    return scalar nt = r(N)
end


tempname H
foreach P of local part {
    postfile `H' str2 cellset str40 tag str10 outcome str5 est str9 term double b se p N ncells ntreat str80 status ///
        using "$OUT\v4_event_`P'.dta", replace

    if "`P'" == "A" use "$V4\event_op.dta", clear
    if "`P'" == "B" use "$V4\event_odp.dta", clear
    egen oyear = group(country_orig year)
    if "`P'" == "A" {
        gen clus = cell
        global ABS "cell oyear"
    }
    else {
        egen dyear = group(country_dest year)
        egen clus = group(od)
        global ABS "cell oyear dyear"
    }
    gen rel = year - gvar if gvar > 0
    gen ev_m4 = rel <= -4 & gvar > 0
    gen ev_m3 = rel == -3
    gen ev_m2 = rel == -2
    forvalues k = 0/3 {
        gen ev_`k' = rel == `k'
    }
    gen ev_4 = rel >= 4 & gvar > 0
    gen cohort = gvar if gvar > 0
    gen never = gvar == 0
    * placebo: the event three years before the real one, on 2012-2016 only (real entries in 2017 and 2018 move to 2014
    * and 2015, cells treated before 2017 are dropped)
    gen gvar_pl = cond(gvar >= 2017, gvar - 3, cond(gvar == 0, 0, .))

    * ---------------------------------------------------------------------------------------------
    * samples
    local S_main     "1"
    local S_pre3     "pre3 == 1"
    local S_noexit   "exit2 == 0"
    local S_balanced "balanced == 1"
    local S_hm_hi    `"high_mean == "High""'
    local S_hm_lo    `"high_mean == "Low""'
    local S_hd_hi    `"high_median == "High""'
    local S_hd_lo    `"high_median == "Low""'
    local S_t_field  `"type == "Field crops""'
    local S_t_horti  `"type == "Horticultural and plantation crops""'
    local S_t_live   `"type == "Livestock and fisheries""'
    local S_t_proc   `"type == "Other processed food and beverages""'
    local S_st_farm  `"stage == "Farm""'
    local S_st_proc  `"stage == "Processing""'
    local S_en_for   `"gvar == 0 | entrant == "foreign""'
    local S_en_dom   `"gvar == 0 | entrant == "domestic""'
    foreach o in ARG CHL COL CRI DOM PER PRY SLV URY {
        local S_o_`o' `"country_orig == "`o'""'
    }

    foreach y of global OUTCOMES {
        foreach tag in main pre3 {
            foreach est in twfe cs sa {
                onerun `H' `P' `tag' `y' `est' "`S_`tag''" gvar
            }
        }
        foreach tag in noexit balanced hm_hi hm_lo hd_hi hd_lo t_field t_horti t_live t_proc st_farm st_proc en_for en_dom ///
                o_ARG o_CHL o_COL o_CRI o_DOM o_PER o_PRY o_SLV o_URY {
            foreach est in twfe cs {
                onerun `H' `P' `tag' `y' `est' `"`S_`tag''"' gvar
            }
        }
        * placebo: years 2012-2016, event moved three years earlier
        preserve
        keep if year <= 2016 & gvar_pl < .
        replace rel = year - gvar_pl if gvar_pl > 0
        replace ev_m4 = rel <= -4 & gvar_pl > 0
        replace ev_m3 = rel == -3
        replace ev_m2 = rel == -2
        forvalues k = 0/3 {
            replace ev_`k' = rel == `k'
        }
        replace ev_4 = rel >= 4 & gvar_pl > 0
        replace gvar = gvar_pl
        foreach est in twfe cs {
            onerun `H' `P' placebo `y' `est' "1" gvar
        }
        restore
    }
    onerun `H' `P' main XL ppml "1" gvar
    postclose `H'
}
