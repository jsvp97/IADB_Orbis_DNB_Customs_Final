**********************************************************************
* _sf1_build_and_run.do
*
* STYLIZED FACT 1 -- MNE presence in international trade is large
*                    across all LAC origins.
*
* Measure: MNE share in EXPORT VALUE (pooled across years).
* Three MNE definitions (post-2026-05-23 convention -- see project memory):
*   total = matched in corporate DB (any)
*   ext   = matched AND parent != exporting country  (= total - dom)
*           (NEW: includes matched firms with empty iso3_parent)
*   dom   = matched AND parent == exporting country
*
* Origin exclusions: ECU (see 01_setup.do $excluded_origins).
*
* OUTPUTS (all to $g_sf1 / $r_sf1 / $t_sf1 + Overleaf mirror):
*   MAIN (in SF1 body):
*     fig_sf1_hbar_total            hbar MNE_total share by country, descending
*   APPENDIX (SF1 appendix):
*     fig_sf1_scatter_total         scatter MNE_total share vs ln_gdpcap_o
*     tab_sf1_share_by_country      country x (3 defs + ln GDPpc)
*     fig_sf1_hbar_ext              hbar MNE_ext share by country, descending
*     fig_sf1_scatter_ext           scatter MNE_ext share vs ln_gdpcap_o
*     reg_sf1_{ext,dom,total}.tex   share-on-lnGDPpc regs (4 specs each)
*
**********************************************************************

clear all
set more off

do "D:\MNEs_Trade\0_Code\01_setup.do"

* ---- SF1-specific output folders ----
global g_sf1     "$graphs\SF1_OriginShare"
global r_sf1     "$regs\SF1_OriginShare"
global t_sf1     "$tables\SF1_OriginShare"

global ol_sf      "$overleaf\Stylized_Facts"
global ol_g_sf1   "$ol_sf\Graphs\SF1_OriginShare"
global ol_r_sf1   "$ol_sf\Regressions\SF1_OriginShare"
global ol_t_sf1   "$ol_sf\Tables\SF1_OriginShare"

foreach dir in "$g_sf1" "$r_sf1" "$t_sf1" ///
               "$ol_sf" "$ol_sf\Graphs" "$ol_sf\Tables" "$ol_sf\Regressions" ///
               "$ol_g_sf1" "$ol_r_sf1" "$ol_t_sf1" ///
               "$ol_sf\sections" {
    cap mkdir `"`dir'"'
}


**********************************************************************
* STEP 1 -- Build / refresh the SF1 origin-year cache
*
*   On first run we build from raw 19 GB; afterwards we just patch the
*   cache to ensure val_ext follows the new MNE_ext convention
*   (val_ext = val_total - val_dom).
**********************************************************************

local cache "$int\sf1_origin_value.dta"

cap confirm file "`cache'"
if _rc != 0 {

    di as text _newline ">>> Building SF1 origin-year value cache from raw 19 GB file..."

    use country_orig year value_fob _merge_DNB_Orbis iso3_parent ///
        using "$customs\Base_final_Customs_DNB_Orbis_product_complete.dta", clear

    * Same sign correction as Part 0
    replace value_fob = -value_fob if value_fob < 0

    * MNE definitions (Part 0 sec 0.2, with NEW MNE_ext convention)
    gen byte MNE_dom   = (_merge_DNB_Orbis == 3) & (iso3_parent == country_orig)
    gen byte MNE_total = (_merge_DNB_Orbis == 3)
    gen byte MNE_ext   = MNE_total - MNE_dom   // NEW: includes empty iso3_parent

    * Value contributions
    gen double val_total = value_fob * MNE_total
    gen double val_dom   = value_fob * MNE_dom
    gen double val_ext   = value_fob * MNE_ext

    gcollapse (sum) total_value=value_fob val_ext val_dom val_total, ///
              by(country_orig year)

    * Merge in CEPII origin GDP/cap, population, GDP
    preserve
        use "$gravity\Gravity_V202211.dta", clear
        rename iso3_o country_orig
        keep country_orig year gdpcap_o pop_o gdp_o
        bysort country_orig year: keep if _n == 1
        gen ln_gdpcap_o = ln(gdpcap_o)
        gen ln_pop_o    = ln(pop_o)
        gen ln_gdp_o    = ln(gdp_o)
        tempfile gravity_o
        save `gravity_o'
    restore
    merge m:1 country_orig year using `gravity_o', keep(1 3) nogen

    egen orig_id = group(country_orig)

    label var total_value   "Total export value (origin-year)"
    label var val_total     "Export value by MNE_total"
    label var val_dom       "Export value by MNE_dom"
    label var val_ext       "Export value by MNE_ext (incl. unknown parent)"
    label var ln_gdpcap_o   "Log GDP per capita (origin)"
    label var ln_pop_o      "Log population (origin)"
    label var ln_gdp_o      "Log GDP (origin)"

    compress
    save "`cache'", replace
    di as text ">>> Cache saved to `cache'"
}
else {
    * Patch existing cache to enforce new MNE_ext = total - dom convention.
    * (Idempotent: replace is a no-op if already correct.)
    use "`cache'", clear
    cap confirm variable val_ext
    if _rc == 0 {
        qui replace val_ext = val_total - val_dom
        label var val_ext "Export value by MNE_ext (incl. unknown parent)"
        save "`cache'", replace
        di as text ">>> Patched cache: val_ext := val_total - val_dom."
    }
}


**********************************************************************
* STEP 2 -- Load cache, apply exclusions, build value shares
**********************************************************************

use "`cache'", clear
drop if inlist(country_orig, $excluded_origins)

* Drop any pre-existing share columns from old cache builds, then rebuild
* (so the new MNE_ext convention is reflected end-to-end)
foreach v in share_value_total share_value_ext share_value_dom share_mne_value {
    cap drop `v'
}

* Year-level value shares (new MNE_ext convention: ext = total - dom)
gen double share_value_total = val_total / total_value
gen double share_value_ext   = val_ext   / total_value
gen double share_value_dom   = val_dom   / total_value

label var share_value_total "MNE\$_{\text{total}}\$ share in export value"
label var share_value_ext   "MNE\$_{\text{ext}}\$ share in export value"
label var share_value_dom   "MNE\$_{\text{dom}}\$ share in export value"

qui count
di as text ">>> SF1 cache loaded (post-exclusions): " r(N) " origin-year obs"
qui levelsof country_orig, local(cs) clean
di as text ">>> Origins kept:   `cs'"
qui sum year
di as text ">>> Year range: " %4.0f r(min) " - " %4.0f r(max)

* Save the panel for the regressions; build a cross-section for figs/table
tempfile panel
save `panel'

* ---- Cross-section: pool across years (value-weighted) ----
gcollapse (sum) total_value val_ext val_dom val_total ///
          (mean) ln_gdpcap_o ln_pop_o ln_gdp_o, ///
          by(country_orig)

gen double sh_total = val_total / total_value
gen double sh_ext   = val_ext   / total_value
gen double sh_dom   = val_dom   / total_value

label var sh_total "MNE\$_{\text{total}}\$ share"
label var sh_ext   "MNE\$_{\text{ext}}\$ share"
label var sh_dom   "MNE\$_{\text{dom}}\$ share"

tempfile cross
save `cross'


**********************************************************************
* STEP 3 -- DESCRIPTIVE TABLE (appendix exhibit)
*
*   Country x (MNE_total, MNE_ext, MNE_dom, ln GDPpc), sorted by total.
**********************************************************************

use `cross', clear
gsort -sh_total

file open fh using "$t_sf1\tab_sf1_share_by_country.tex", write replace
file write fh "\begin{tabular}{lcccc}" _n
file write fh "\toprule" _n
file write fh " & MNE\$_{\text{total}}\$ & MNE\$_{\text{ext}}\$ & MNE\$_{\text{dom}}\$ & \$\ln \text{GDPpc}\$ \\" _n
file write fh "Country & share (value) & share (value) & share (value) & (origin, mean) \\" _n
file write fh "\midrule" _n
forvalues i = 1/`=_N' {
    local cc = country_orig[`i']
    local v1 : di %5.3f sh_total[`i']
    local v2 : di %5.3f sh_ext[`i']
    local v3 : di %5.3f sh_dom[`i']
    local v4 : di %5.2f ln_gdpcap_o[`i']
    file write fh "`cc' & `v1' & `v2' & `v3' & `v4' \\" _n
}
file write fh "\bottomrule" _n
file write fh "\end{tabular}" _n
file close fh
cap copy "$t_sf1\tab_sf1_share_by_country.tex" ///
         "$ol_t_sf1\tab_sf1_share_by_country.tex", replace


* ---- Dedicated per-def tables (country x sh_<def> x ln GDPpc),
*      one per MNE definition, sorted by that def's share descending ----

foreach def in total ext dom {
    preserve
        gsort -sh_`def'
        file open fh2 using "$t_sf1\tab_sf1_share_by_country_`def'.tex", write replace
        file write fh2 "\begin{tabular}{lcc}" _n
        file write fh2 "\toprule" _n
        * Inline the math header with compound double quotes `"..."' so
        * Stata doesn't try to expand `\$_{` as a global reference.
        file write fh2 `" & MNE$_{\text{`def'}}$ share & $\ln \text{GDPpc}$ \\"' _n
        file write fh2 "Country & (value, pooled) & (origin, mean) \\" _n
        file write fh2 "\midrule" _n
        forvalues i = 1/`=_N' {
            local cc = country_orig[`i']
            local v1 : di %5.3f sh_`def'[`i']
            local v2 : di %5.2f ln_gdpcap_o[`i']
            file write fh2 "`cc' & `v1' & `v2' \\" _n
        }
        file write fh2 "\bottomrule" _n
        file write fh2 "\end{tabular}" _n
        file close fh2
        cap copy "$t_sf1\tab_sf1_share_by_country_`def'.tex" ///
                 "$ol_t_sf1\tab_sf1_share_by_country_`def'.tex", replace
    restore
}


**********************************************************************
* STEP 4 -- Compute and announce min/max MNE_total share for the SF1 caption
**********************************************************************

qui sum sh_total
local lo : di %4.1f 100*r(min)
local hi : di %4.1f 100*r(max)
qui levelsof country_orig if sh_total == r(max), local(cmax) clean
qui levelsof country_orig if sh_total == r(min), local(cmin) clean
di as text _newline ///
    ">>> SF1 caption fact: MNE_total share ranges from " "`lo'" "% (`cmin') to " "`hi'" "% (`cmax')."


**********************************************************************
* STEP 5 -- FIGURES
**********************************************************************

* ---- 5.A  MAIN: horizontal bar of MNE_total share, descending ----

use `cross', clear
gsort -sh_total
graph hbar (asis) sh_total, ///
    over(country_orig, sort(sh_total) descending label(labsize(medium))) ///
    bar(1, color($c_MNEtot) lcolor($c_MNEtot)) ///
    ytitle("MNE share in export value", size(medsmall)) ///
    ylab(0(0.1)0.8, nogrid format(%9.1f)) ///
    blabel(bar, position(outside) format(%4.2f) size(small)) ///
    bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
export_graph "fig_sf1_hbar_total" "$g_sf1" "$ol_g_sf1"

* ---- 5.B  APPENDIX: horizontal bar of MNE_ext share, descending ----

graph hbar (asis) sh_ext, ///
    over(country_orig, sort(sh_ext) descending label(labsize(medium))) ///
    bar(1, color($c_MNE) lcolor($c_MNE)) ///
    ytitle("MNE-ext share in export value", size(medsmall)) ///
    ylab(0(0.1)0.8, nogrid format(%9.1f)) ///
    blabel(bar, position(outside) format(%4.2f) size(small)) ///
    bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
export_graph "fig_sf1_hbar_ext" "$g_sf1" "$ol_g_sf1"

* ---- 5.B'  APPENDIX: horizontal bar of MNE_dom share, descending ----

graph hbar (asis) sh_dom, ///
    over(country_orig, sort(sh_dom) descending label(labsize(medium))) ///
    bar(1, color($c_MNEdom) lcolor($c_MNEdom)) ///
    ytitle("MNE-dom share in export value", size(medsmall)) ///
    ylab(0(0.05)0.30, nogrid format(%9.2f)) ///
    blabel(bar, position(outside) format(%4.2f) size(small)) ///
    bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))
export_graph "fig_sf1_hbar_dom" "$g_sf1" "$ol_g_sf1"

* ---- 5.C  APPENDIX: scatter MNE_total share vs ln GDP/cap ----

twoway ///
    (lfitci sh_total ln_gdpcap_o, lcolor(black) acolor(gs14)) ///
    (scatter sh_total ln_gdpcap_o, mlabel(country_orig) ///
        mlabsize(2.8) mlabposition(3) ///
        msize(*1.4) mcolor($c_MNEtot) mlabcolor($c_MNEtot) ms(O)), ///
    ytitle("MNE-total share in export value") ///
    xtitle("Log GDP per capita (origin)") ///
    ylab(, nogrid) legend(off) $gro
export_graph "fig_sf1_scatter_total" "$g_sf1" "$ol_g_sf1"

* ---- 5.D  APPENDIX: scatter MNE_ext share vs ln GDP/cap ----

twoway ///
    (lfitci sh_ext ln_gdpcap_o, lcolor(black) acolor(gs14)) ///
    (scatter sh_ext ln_gdpcap_o, mlabel(country_orig) ///
        mlabsize(2.8) mlabposition(3) ///
        msize(*1.4) mcolor($c_MNE) mlabcolor($c_MNE) ms(O)), ///
    ytitle("MNE-ext share in export value") ///
    xtitle("Log GDP per capita (origin)") ///
    ylab(, nogrid) legend(off) $gro
export_graph "fig_sf1_scatter_ext" "$g_sf1" "$ol_g_sf1"

* ---- 5.E  APPENDIX: scatter MNE_dom share vs ln GDP/cap ----

twoway ///
    (lfitci sh_dom ln_gdpcap_o, lcolor(black) acolor(gs14)) ///
    (scatter sh_dom ln_gdpcap_o, mlabel(country_orig) ///
        mlabsize(2.8) mlabposition(3) ///
        msize(*1.4) mcolor($c_MNEdom) mlabcolor($c_MNEdom) ms(O)), ///
    ytitle("MNE-dom share in export value") ///
    xtitle("Log GDP per capita (origin)") ///
    ylab(, nogrid) legend(off) $gro
export_graph "fig_sf1_scatter_dom" "$g_sf1" "$ol_g_sf1"


**********************************************************************
* STEP 6 -- REGRESSIONS (country-year panel; same 4-spec ladder per def)
**********************************************************************

use `panel', clear

foreach def in ext dom total {

    local dv "share_value_`def'"
    local outfile "$r_sf1\reg_sf1_`def'.tex"

    reg `dv' ln_gdpcap_o, robust
    outreg2 using "`outfile'", replace tex(frag) label ctitle("OLS") ///
        addtext(Year FE, No, Pop control, No, SE, Robust) dec(4)

    reg `dv' ln_gdpcap_o ln_pop_o, robust
    outreg2 using "`outfile'", append tex(frag) label ctitle("+ ln pop") ///
        addtext(Year FE, No, Pop control, Yes, SE, Robust) dec(4)

    reghdfe `dv' ln_gdpcap_o, absorb(year) vce(robust)
    outreg2 using "`outfile'", append tex(frag) label ctitle("Year FE") ///
        addtext(Year FE, Yes, Pop control, No, SE, Robust) dec(4)

    reghdfe `dv' ln_gdpcap_o ln_pop_o, absorb(year) vce(robust)
    outreg2 using "`outfile'", append tex(frag) label ctitle("Year FE + pop") ///
        addtext(Year FE, Yes, Pop control, Yes, SE, Robust) dec(4)

    cap copy "`outfile'" "$ol_r_sf1\reg_sf1_`def'.tex", replace
}


**********************************************************************
* DONE
**********************************************************************
di as text ""
di as text "==========================================================="
di as text "  SF1 outputs written:"
di as text "    Graphs       -> $g_sf1"
di as text "    Tables       -> $t_sf1"
di as text "    Regressions  -> $r_sf1"
di as text "    Overleaf     -> $ol_sf"
di as text "==========================================================="
