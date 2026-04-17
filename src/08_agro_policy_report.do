/*==============================================================================
  08_agro_policy_report.do

  PURPOSE:
    Standalone script that produces all publication-quality figures and tables
    for the agricultural policy report. Uses intermediate .dta files built by
    07_agro_trade_analysis.do. All output goes to $agro_root\PolicyReport\.

  OUTPUTS:
    Table 1  — Country snapshot (MNE share of exports by country)
    Figures 1-9 — MNE comparisons: by country, HS section, destination, parent region
    Table 2  — Agricultural section breakdown

  DEPENDS ON:
    07_agro_trade_analysis.do must have been run first to generate the
    intermediate .dta files consumed here.

  AUTHOR: Sebastian Velasquez (IDB)

  LAST UPDATED: March 2026
==============================================================================*/

**********************************************************************
*
* MNE and Agricultural Trade in Latin America
* Policy Report — Descriptive Analysis
*
* Author:   Sebastian Velasquez (IDB)
*
* Last Version: April 2026
*
* PURPOSE:
*   Standalone policy-report script. Reads intermediate .dta files
*   already built by MNE_Trade_Agro.do and produces exactly:
*     9 publication-quality figures
*     2 structured tables
*   All output goes to $agro_root\PolicyReport\
*
* PREREQUISITE:
*   Run MNE_Trade_Agro.do first (Part 0) to build $int files.
*
* OUTPUT MAP:
*   T1  Country snapshot (exports, firms, MNE shares, year range)
*   F1  MNE share in value & # firms, by country
*   F2  MNE trend: LAC aggregate + 4 heterogeneous countries
*   F3  Agro export value by section × MNE vs. domestic (LAC pooled)
*   F4  MNE value share by section × country
*   F5  MNE vs. domestic export distribution by destination type
*   F6  Firm export size: MNE vs. domestic by country (box plots)
*   F7  MNE exports by parent region — LAC pooled + by country
*   F8  US-destined agro exports: US-parented vs. other MNE vs. domestic
*   F9  EU-destined agro exports: EU-parented vs. other MNE vs. domestic
*   T2  Section breakdown: value, share, MNE presence (LAC pooled)
*
**********************************************************************

clear all
set more off
graph set window fontface "Times New Roman"


**********************************************************************
* 0. DIRECTORIES
**********************************************************************

* Agro root (same as MNE_Trade_Agro.do — intermediate data lives here)
global root     "C:\Sebas BID\Orbis_DNB_Customs_Final"
global agro_root "$root\agro"
global int       "$agro_root\Data\Intermediate"

* Policy report output (separate from full analysis outputs)
global pr        "$agro_root\PolicyReport"
global pr_fig    "$pr\Figures"
global pr_tab    "$pr\Tables"

* Overleaf mirror for the policy report
global pr_ol     "$agro_root\Overleaf\PolicyReport"
global pr_ol_fig "$pr_ol\Figures"
global pr_ol_tab "$pr_ol\Tables"

foreach dir in "$pr" "$pr_fig" "$pr_tab" "$pr_ol" "$pr_ol_fig" "$pr_ol_tab" {
    capture mkdir `"`dir'"'
}


**********************************************************************
* GRAPH SCHEME — policy-report quality
*
* Palette: two-tone MNE/domestic for all comparisons.
*          Section palette: earthy, colour-blind distinguishable.
*          Highlighted-country palette: 4 visually distinct lines.
**********************************************************************

* Core MNE / domestic
global c_mne  "227 72 54"    // coral-red  (MNE)
global c_dom  "130 130 130"  // mid-grey   (domestic)
global c_lac  "0 63 135"     // IDB navy   (LAC aggregate line)

* Agro section colours
global c_s1   "139 90 43"    // brown      (Live animals)
global c_s2   "76 153 0"     // forest     (Vegetables)
global c_s3   "255 153 0"    // amber      (Fats & oils)
global c_s4   "0 112 192"    // steel blue (Food & bev)

* 4 highlighted country colours (assigned dynamically in F2)
global c_h1   "214 39 40"    // red
global c_h2   "44 160 44"    // green
global c_h3   "255 127 14"   // orange
global c_h4   "148 103 189"  // purple

* Standard graph background: white, no frame
global gro `"graphregion(fcolor(white) lwidth(none) lpattern(blank)) plotregion(fcolor(white) lwidth(none) lpattern(blank))"'

* Font size shortcuts
global tsize  "large"        // figure titles
global lsize  "medium"       // axis labels & legend
global nsize  "small"        // notes


**********************************************************************
* HELPER: export graph to Figures + Overleaf (PDF + PNG)
**********************************************************************

capture program drop pr_export
program define pr_export
    args fname
    graph export "$pr_fig\\`fname'.pdf", replace
    graph export "$pr_fig\\`fname'.png", replace width(2400)
    copy "$pr_fig\\`fname'.pdf" "$pr_ol_fig\\`fname'.pdf", replace
    copy "$pr_fig\\`fname'.png" "$pr_ol_fig\\`fname'.png", replace
end


**********************************************************************
* HELPER: LaTeX booktabs-style table note block
*   Appends a \bottomrule + \end{tabular} to a .tex file fragment.
**********************************************************************

capture program drop pr_tab_close
program define pr_tab_close
    args fname note
    file open  fh using "$pr_tab\\`fname'.tex", write append
    file write fh "\midrule" _newline
    file write fh "\multicolumn{7}{l}{\footnotesize `note'} \\" _newline
    file write fh "\bottomrule" _newline
    file write fh "\end{tabular}" _newline
    file close fh
end


**********************************************************************
**********************************************************************
*
*   TABLE 1 — Country Snapshot
*
*   Columns: Country | Years covered | Avg annual agro exports (USD M)
*            | Avg # exporting firms | MNE share in value (%)
*            | MNE share in # firms (%)
*
*   Source: firm_level_data.dta
*
**********************************************************************
**********************************************************************

di as text _newline ">>> Building T1: Country Snapshot"

use "$int\firm_level_data.dta", clear

* Step 1: compute MNE export value at transaction level (before any collapse)
gen double mne_val_obs = value_fob * MNE_ext

* Step 2: collapse to country-year level
*   - total agro export value
*   - total MNE export value (correct value share denominator)
*   - number of DISTINCT exporting firms (nvals = nunique firm_id)
*   - number of distinct MNE firms
*   - year range
bysort country_orig year: egen n_firms_yr    = nvals(firm_id)
bysort country_orig year: egen n_mne_firms_yr = total(MNE_ext == 1 & !missing(firm_id))
* n_mne_firms_yr overcounts (one row per transaction); correct to distinct MNE firms
* Use a firm-year indicator: 1 for first transaction of each MNE firm in year
bysort country_orig year firm_id (MNE_ext): gen byte first_mne_obs = (_n == 1 & MNE_ext == 1)

gcollapse ///
    (sum)    agro_value  = value_fob ///
    (sum)    mne_value   = mne_val_obs ///
    (firstnm) n_firms_yr ///
    (sum)    n_mne_firms = first_mne_obs ///
    , by(country_orig year) labelformat(#sourcelabel#)

* Step 3: year coverage
bysort country_orig (year): gen yr_min = year[1]
bysort country_orig (year): gen yr_max = year[_N]

* Step 4: average over years within country
gcollapse ///
    (mean)   agro_value mne_value n_firms_yr n_mne_firms ///
    (firstnm) yr_min yr_max ///
    , by(country_orig) labelformat(#sourcelabel#)

* Step 5: derived statistics
gen mne_val_pct  = (mne_value   / agro_value)  * 100   // MNE share in export VALUE
gen mne_firm_pct = (n_mne_firms / n_firms_yr)  * 100   // MNE share in # firms
gen agro_value_m = agro_value / 1e6                     // USD millions

* Sort by total agro exports descending
gsort -agro_value_m

* Write LaTeX table
* FIX: 6 columns (lccccc), \specialcell instead of \makecell
file open fh using "$pr_tab\T1_country_snapshot.tex", write replace
file write fh "\begin{tabular}{lccccc}" _newline
file write fh "\toprule" _newline
file write fh "Country & Years" ///
    " & \specialcell{Agro Exports \\ (avg, USD M)}" ///
    " & \specialcell{\# Exporting \\ Firms (avg)}" ///
    " & \specialcell{MNE Share \\ in Value (\%)}" ///
    " & \specialcell{MNE Share \\ in \# Firms (\%)} \\" _newline
file write fh "\midrule" _newline

local N = _N
forval i = 1/`N' {
    local co  = country_orig[`i']
    local ym  = yr_min[`i']
    local yM  = yr_max[`i']
    local val : di %9.0fc agro_value_m[`i']
    local nf  : di %9.0fc n_firms_yr[`i']
    local sv  : di %5.1f  mne_val_pct[`i']
    local sf  : di %5.1f  mne_firm_pct[`i']
    file write fh "`co' & `ym'--`yM' & `val' & `nf' & `sv' & `sf' \\" _newline
}

file write fh "\midrule" _newline
file write fh "\multicolumn{6}{l}{\footnotesize \textit{Notes:} Averages computed over available years per country. Agro exports cover HS2 chapters 1--24 (Sections I--IV).} \\" _newline
file write fh "\multicolumn{6}{l}{\footnotesize MNE\textsubscript{ext} = foreign-parented exporter. Value and firm-count shares are annual averages.} \\" _newline
file write fh "\bottomrule" _newline
file write fh "\end{tabular}" _newline
file close fh

copy "$pr_tab\T1_country_snapshot.tex" "$pr_ol_tab\T1_country_snapshot.tex", replace
di as text "    T1 saved."


**********************************************************************
**********************************************************************
*
*   FIGURE 1 — MNE Share in Value and # Firms, by Country
*
*   Horizontal grouped bar. Two bars per country:
*     bar 1 (red)  = MNE share in total agro export value
*     bar 2 (grey) = MNE share in # exporting firms
*   Countries sorted by MNE value share descending.
*   Source: collapsed_oy.dta
*
**********************************************************************
**********************************************************************

di as text _newline ">>> Building F1: MNE share by country"

use "$int\collapsed_oy.dta", clear

* Average over years for each country
gcollapse ///
    (mean) share_mne_value share_ext_nfirms ///
    [aw = total_value] ///
    , by(country_orig) labelformat(#sourcelabel#)

* Sort descending by value share
gsort -share_mne_value
gen order = _N + 1 - _n       // reverse so highest is at top of hbar
labmask order, values(country_orig)

* Scale to %
replace share_mne_value  = share_mne_value  * 100
replace share_ext_nfirms = share_ext_nfirms * 100

graph hbar (asis) share_mne_value share_ext_nfirms, ///
    over(order, sort(order) descending ///
         label(labsize(`lsize') angle(0))) ///
    bar(1, fcolor("$c_mne") lcolor("$c_mne")) ///
    bar(2, fcolor("$c_dom") lcolor("$c_dom")) ///
    legend(on ///
           order(1 "Share in Export Value" 2 "Share in # Exporters") ///
           position(6) rows(1) size(`lsize') region(lcolor(white)) symysize(small)) ///
    ytitle("MNE Share (%)", size(`lsize')) ///
    ylab(0(5)40, nogrid labsize(`lsize')) ///
    title("MNE Presence in Agricultural Exports, by Country", ///
          size(`tsize') color(black)) ///
    note("Note: Value-weighted average over available years (2006–2022). MNE = foreign-parented exporter (MNE{subscript:ext}).", ///
         size(`nsize')) ///
    $gro

pr_export "F1_mne_share_by_country"
di as text "    F1 saved."


**********************************************************************
**********************************************************************
*
*   FIGURE 2 — MNE Trend: LAC Aggregate + 4 Highlighted Countries
*
*   Selection of 4 countries is fully automatic:
*     c_high : highest average MNE value share
*     c_low  : lowest average MNE value share
*     c_up   : steepest upward trend (OLS slope, excl. above)
*     c_flat : flattest / most declining trend (excl. above)
*
*   Remaining 6 countries: thin light-grey lines in background.
*   LAC aggregate: thick navy line.
*   Source: collapsed_oy.dta
*
**********************************************************************
**********************************************************************

di as text _newline ">>> Building F2: MNE trend (auto-select 4 countries)"

use "$int\collapsed_oy.dta", clear

*------------------------------------------------------------------
* Step 1: identify the 4 heterogeneous countries
*------------------------------------------------------------------

* Average share per country
preserve
    gcollapse (mean) avg_share = share_mne_value, by(country_orig)
    tempfile avg_sh
    save `avg_sh'
restore

* OLS slope of share_mne_value on year, per country
preserve
    * Standardise year so slopes are comparable
    sum year
    gen yr_c = year - r(min)
    levelsof country_orig, local(all_c)
    gen slope = .
    foreach c of local all_c {
        cap {
            reg share_mne_value yr_c if country_orig == "`c'"
            replace slope = _b[yr_c] if country_orig == "`c'"
        }
    }
    gcollapse (firstnm) slope, by(country_orig)
    merge 1:1 country_orig using `avg_sh', nogen
    tempfile slopes
    save `slopes'
restore

* Load slopes dataset and extract the 4 countries
use `slopes', clear

* 1. Highest average share
gsort -avg_share
local c_high = country_orig[1]

* 2. Lowest average share
gsort avg_share
local c_low = country_orig[1]

* 3. Steepest upward trend (exclude already selected)
gsort -slope
local k = 1
local c_up ""
while "`c_up'" == "" & `k' <= _N {
    local cand = country_orig[`k']
    if "`cand'" != "`c_high'" & "`cand'" != "`c_low'" {
        local c_up "`cand'"
    }
    local k = `k' + 1
}

* 4. Flattest / most declining (exclude already selected)
gsort slope
local k = 1
local c_flat ""
while "`c_flat'" == "" & `k' <= _N {
    local cand = country_orig[`k']
    if "`cand'" != "`c_high'" & "`cand'" != "`c_low'" & "`cand'" != "`c_up'" {
        local c_flat "`cand'"
    }
    local k = `k' + 1
}

di as text "    Selected countries:"
di as text "      High MNE share:  `c_high'"
di as text "      Low MNE share:   `c_low'"
di as text "      Upward trend:    `c_up'"
di as text "      Flat/declining:  `c_flat'"

local highlighted "`c_high' `c_low' `c_up' `c_flat'"

*------------------------------------------------------------------
* Step 2: build LAC aggregate (value-weighted mean over countries)
*------------------------------------------------------------------

use "$int\collapsed_oy.dta", clear

* LAC aggregate: weighted sum (total MNE value / total value)
gcollapse ///
    (sum) tot_mne_val = mne_value tot_val = total_value ///
    , by(year) labelformat(#sourcelabel#)
gen lac_share = (tot_mne_val / tot_val) * 100
tempfile lac_agg
save `lac_agg'

*------------------------------------------------------------------
* Step 3: country-year series (as %)
*------------------------------------------------------------------

use "$int\collapsed_oy.dta", clear
gen share_pct = share_mne_value * 100
keep country_orig year share_pct

*------------------------------------------------------------------
* Step 4: build the twoway command dynamically
*------------------------------------------------------------------

* Count countries and determine plot-position offsets for legend
levelsof country_orig, local(all_c)
local n_all : word count `all_c'
local n_bg = `n_all' - 4          // number of grey background lines
local lo1 = `n_bg' + 1            // legend position: c_high
local lo2 = `n_bg' + 2            //                  c_low
local lo3 = `n_bg' + 3            //                  c_up
local lo4 = `n_bg' + 4            //                  c_flat
local lo5 = `n_bg' + 5            //                  LAC aggregate

* All countries → thin grey background lines (plotted first)
local bg_cmd ""
local bg_n = 0
foreach c of local all_c {
    local is_hl = 0
    foreach h of local highlighted {
        if "`c'" == "`h'" local is_hl = 1
    }
    if `is_hl' == 0 {
        local bg_cmd "`bg_cmd' (line share_pct year if country_orig == "`c'", lcolor(gs14) lwidth(vthin) lpattern(solid))"
        local bg_n = `bg_n' + 1
    }
}

* Highlighted countries (coloured, drawn on top of grey)
local hl_cmd ""
local hl_colors `""$c_h1" "$c_h2" "$c_h3" "$c_h4""'
local hi = 1
foreach h of local highlighted {
    local hcol : word `hi' of `hl_colors'
    local hl_cmd "`hl_cmd' (line share_pct year if country_orig == "`h'", lcolor(`hcol') lwidth(medthick) lpattern(solid))"
    local hi = `hi' + 1
}

* LAC aggregate — drawn last so it sits on top of everything
merge m:1 year using `lac_agg', nogen
local lac_cmd "(line lac_share year, lcolor("$c_lac") lwidth(thick) lpattern(solid))"

* Combine and plot
twoway `bg_cmd' `hl_cmd' `lac_cmd', ///
    ytitle("MNE Share in Agro Export Value (%)", size(`lsize')) ///
    xtitle("") ///
    ylab(, nogrid labsize(`lsize') format(%4.0f)) ///
    xlab(, nogrid angle(45) labsize(`lsize')) ///
    legend(on ///
           order(`lo1' "High MNE: `c_high'" ///
                 `lo2' "Low MNE: `c_low'"   ///
                 `lo3' "Trend up: `c_up'"   ///
                 `lo4' "Flat: `c_flat'"     ///
                 `lo5' "LAC Aggregate")     ///
           position(6) rows(2) size(`lsize') region(lcolor(white)) symysize(small)) ///
    title("MNE Participation in Agricultural Exports over Time", ///
          size(`tsize') color(black)) ///
    note("Note: Grey lines = remaining sample countries. LAC aggregate = value-weighted mean across all 10 countries.", ///
         size(`nsize')) ///
    $gro

pr_export "F2_mne_trend_lac_highlighted"
di as text "    F2 saved."


**********************************************************************
**********************************************************************
*
*   FIGURE 3 — Export Value by Agro Section × MNE vs. Domestic
*              LAC Pooled, Stacked Bar
*
*   Each section bar = total value, split MNE (red) / domestic (grey).
*   Absolute values (USD billions), pooled over all years.
*   Source: collapsed_opy.dta
*
**********************************************************************
**********************************************************************

di as text _newline ">>> Building F3: Value by section x MNE/DOM"

use "$int\collapsed_opy.dta", clear

* Reconstruct mne_value and dom_value (not stored in OPY — recompute)
* mne_value = share_mne_value * total_value at ODPY level
* At OPY level: mne_value = n_mne_value would be more direct
* Use: share_mne_value * total_value as a close proxy at OPY
gen mne_val  = share_mne_value * total_value
gen dom_val  = total_value - mne_val

preserve
    drop if hs_section == .

    gcollapse ///
        (sum) mne_val dom_val total_value ///
        , by(hs_section) labelformat(#sourcelabel#)

    * Scale to USD billions for readability
    foreach v in mne_val dom_val total_value {
        replace `v' = `v' / 1e9
    }

    label values hs_section agro_sect_lbl

    * Sort sections I→IV
    sort hs_section

    * Encode order for over()
    gen order = hs_section
    label define sect_short 1 "I: Live Animals" 2 "II: Vegetables" ///
                            3 "III: Fats & Oils" 4 "IV: Food & Bev.", replace
    label values order sect_short

    graph hbar (asis) mne_val dom_val, ///
        over(order, label(labsize(`lsize') angle(0))) ///
        bar(1, fcolor("$c_mne") lcolor("$c_mne")) ///
        bar(2, fcolor("$c_dom") lcolor("$c_dom")) ///
        stack ///
        legend(on ///
               order(1 "MNE (foreign-parented)" 2 "Domestic") ///
               position(6) rows(1) size(`lsize') region(lcolor(white)) symysize(small)) ///
        ytitle("Total Agro Exports (USD billions)", size(`lsize')) ///
        ylab(, nogrid labsize(`lsize') format(%9.1f)) ///
        title("Agricultural Export Value by Section and Firm Type", ///
              size(`tsize') color(black)) ///
        note("Note: Pooled over all years and countries. HS2 chapters 1–24.", ///
             size(`nsize')) ///
        $gro

    pr_export "F3_value_by_section_mne_dom"
restore
di as text "    F3 saved."


**********************************************************************
**********************************************************************
*
*   FIGURE 4 — MNE Value Share by Section × Country
*
*   Grouped bar: one group per country, 4 bars (one per section).
*   Allows direct comparison of which countries have high/low MNE
*   penetration in each segment of the agro value chain.
*   Source: collapsed_opy.dta
*
**********************************************************************
**********************************************************************

di as text _newline ">>> Building F4: MNE share by section x country"

use "$int\collapsed_opy.dta", clear

preserve
    drop if hs_section == .

    gcollapse ///
        (mean) share_mne_value ///
        [aw = total_value] ///
        , by(country_orig hs_section) labelformat(#sourcelabel#)

    replace share_mne_value = share_mne_value * 100

    * Reshape wide: one column per section
    keep country_orig hs_section share_mne_value
    reshape wide share_mne_value, i(country_orig) j(hs_section)

    * Fill missing sections with 0 (country had no exports in that section)
    foreach v in share_mne_value1 share_mne_value2 share_mne_value3 share_mne_value4 {
        replace `v' = 0 if missing(`v')
    }

    * Sort by overall MNE share (simple average across sections)
    egen avg_mne = rowmean(share_mne_value1 share_mne_value2 share_mne_value3 share_mne_value4)
    gsort -avg_mne
    gen order = _n
    labmask order, values(country_orig)

    graph hbar (asis) share_mne_value1 share_mne_value2 share_mne_value3 share_mne_value4, ///
        over(order, sort(order) label(labsize(`lsize') angle(0))) ///
        bar(1, fcolor("$c_s1") lcolor("$c_s1")) ///
        bar(2, fcolor("$c_s2") lcolor("$c_s2")) ///
        bar(3, fcolor("$c_s3") lcolor("$c_s3")) ///
        bar(4, fcolor("$c_s4") lcolor("$c_s4")) ///
        legend(on ///
               order(1 "I: Live Animals" 2 "II: Vegetables" ///
                     3 "III: Fats & Oils" 4 "IV: Food & Bev.") ///
               position(6) rows(2) size(`lsize') region(lcolor(white)) symysize(small)) ///
        ytitle("MNE Share in Value (%)", size(`lsize')) ///
        ylab(0(10)60, nogrid labsize(`lsize') format(%4.0f)) ///
        title("MNE Share in Agricultural Exports by Section and Country", ///
              size(`tsize') color(black)) ///
        note("Note: Value-weighted average over available years. Countries sorted by mean MNE share across sections.", ///
             size(`nsize')) ///
        $gro

    pr_export "F4_mne_share_section_country"
restore
di as text "    F4 saved."


**********************************************************************
**********************************************************************
*
*   FIGURE 5 — Destination Profile: MNE vs. Domestic Exporters
*
*   Two-panel horizontal bar.
*   Panel A: Among MNE exports, % going to each destination type.
*   Panel B: Among domestic exports, % going to each destination type.
*   Destination types: income group (Low/LMid/UMid/High) and
*                      region (LAC / North America / Europe / Asia / Other)
*   Source: collapsed_ody.dta
*
**********************************************************************
**********************************************************************

di as text _newline ">>> Building F5: Destination profile MNE vs DOM"

use "$int\collapsed_ody.dta", clear

* Reconstruct mne and dom values
gen mne_val = share_mne_value * total_value
gen dom_val = total_value - mne_val

*------------------------------------------------------
* Panel A: by income group
*------------------------------------------------------

preserve
    drop if income_group_dest == .

    gcollapse (sum) mne_val dom_val, by(income_group_dest)

    * Shares of total MNE / total DOM exports across income groups
    egen tot_mne = total(mne_val)
    egen tot_dom = total(dom_val)
    gen sh_mne = (mne_val / tot_mne) * 100
    gen sh_dom = (dom_val / tot_dom) * 100

    cap label define inc_lbl 1 "Low Income" 2 "Lower-Middle" ///
                             3 "Upper-Middle" 4 "High Income", replace
    label values income_group_dest inc_lbl
    label var sh_mne "MNE exports (%)"
    label var sh_dom "Domestic exports (%)"

    graph hbar (asis) sh_mne sh_dom, ///
        over(income_group_dest, label(labsize(`lsize') angle(0))) ///
        bar(1, fcolor("$c_mne") lcolor("$c_mne")) ///
        bar(2, fcolor("$c_dom") lcolor("$c_dom")) ///
        legend(on ///
               order(1 "MNE exports" 2 "Domestic exports") ///
               position(6) rows(1) size(`lsize') region(lcolor(white)) symysize(small)) ///
        ytitle("Share of Total Exports (%)", size(`lsize')) ///
        ylab(0(10)60, nogrid labsize(`lsize') format(%4.0f)) ///
        title("Agricultural Exports by Destination Income Group", ///
              size(`tsize') color(black)) ///
        note("Note: Each bar shows the % of that firm type's total exports going to each income group.", ///
             size(`nsize')) ///
        $gro

    pr_export "F5a_destination_income_group"
restore

*------------------------------------------------------
* Panel B: by destination region
*------------------------------------------------------

preserve
    drop if dest_region_num == .

    gcollapse (sum) mne_val dom_val, by(dest_region_num)

    egen tot_mne = total(mne_val)
    egen tot_dom = total(dom_val)
    gen sh_mne = (mne_val / tot_mne) * 100
    gen sh_dom = (dom_val / tot_dom) * 100

    label var sh_mne "MNE exports (%)"
    label var sh_dom "Domestic exports (%)"

    * Sort by MNE share descending
    gsort -sh_mne
    gen order = _n
    labmask order, values(dest_region_num)

    graph hbar (asis) sh_mne sh_dom, ///
        over(order, sort(order) label(labsize(`lsize') angle(0))) ///
        bar(1, fcolor("$c_mne") lcolor("$c_mne")) ///
        bar(2, fcolor("$c_dom") lcolor("$c_dom")) ///
        legend(on ///
               order(1 "MNE exports" 2 "Domestic exports") ///
               position(6) rows(1) size(`lsize') region(lcolor(white)) symysize(small)) ///
        ytitle("Share of Total Exports (%)", size(`lsize')) ///
        ylab(0(10)60, nogrid labsize(`lsize') format(%4.0f)) ///
        title("Agricultural Exports by Destination Region", ///
              size(`tsize') color(black)) ///
        note("Note: Each bar shows the % of that firm type's total exports going to each region.", ///
             size(`nsize')) ///
        $gro

    pr_export "F5b_destination_region"
restore

di as text "    F5a and F5b saved."


**********************************************************************
**********************************************************************
*
*   FIGURE 6 — Firm Export Size: MNE vs. Domestic, by Country
*
*   Box plot of ln(total agro exports per firm-year).
*   One pair of boxes per country (MNE = red, domestic = grey).
*   Countries on x-axis, sorted alphabetically.
*   Source: firm_year_level.dta
*
**********************************************************************
**********************************************************************

di as text _newline ">>> Building F6: Firm size box plots"

use "$int\firm_year_level.dta", clear

keep if !missing(ln_firm_exports) & !missing(MNE)

* Numeric country identifier with ISO3 labels
egen ctry_num = group(country_orig)
levelsof country_orig, local(cl)
local k = 1
foreach c of local cl {
    label define ctry_num_lbl `k' "`c'", modify
    local k = `k' + 1
}
label values ctry_num ctry_num_lbl

graph box ln_firm_exports, ///
    over(MNE, label(labsize(vsmall)) relabel(1 "Domestic" 2 "MNE")) ///
    over(ctry_num, label(labsize(`lsize') angle(45))) ///
    nooutsides ///
    asyvars ///
    box(1, fcolor("$c_dom") lcolor("$c_dom")) ///
    box(2, fcolor("$c_mne") lcolor("$c_mne")) ///
    medtype(line) medlcolor(white) medlwidth(medthick) ///
    ytitle("Ln Total Agro Exports per Firm (USD)", size(`lsize')) ///
    legend(on ///
           order(1 "Domestic" 2 "MNE (foreign-parented)") ///
           position(6) rows(1) size(`lsize') region(lcolor(white))) ///
    title("Agricultural Exporter Size: MNE vs. Domestic Firms", ///
          size(`tsize') color(black)) ///
    note("Note: Each box covers the interquartile range. Outliers excluded for clarity.", ///
         size(`nsize')) ///
    bgcolor(white) graphregion(fcolor(white)) plotregion(fcolor(white))

pr_export "F6_firm_size_boxplot"
di as text "    F6 saved."


**********************************************************************
**********************************************************************
*
*   FIGURE 7 — Parent Region of MNE Agro Exporters
*
*   Panel A (pooled): stacked horizontal bar — share of MNE agro
*     exports by parent region (LAC aggregate).
*   Panel B (by country): stacked bar — same, broken out per
*     exporting country (sorted by share from largest to smallest).
*
*   Source: firm_level_data.dta (MNE_ext == 1 only)
*
**********************************************************************
**********************************************************************

di as text _newline ">>> Building F7: Parent region"

use "$int\firm_level_data.dta", clear
keep if MNE_ext == 1

* Build parent region classification
gen parent_region = ""
replace parent_region = "USA"    if iso3_parent == "USA"
replace parent_region = "Europe" if inlist(iso3_parent,"AUT","BEL","BGR","CYP","CZE", ///
                                            "DNK","EST","FIN","FRA","DEU","GRC","HUN", ///
                                            "IRL","ITA","LVA","LTU","LUX","MLT","NLD", ///
                                            "POL","PRT","ROU","SVK","SVN","ESP","SWE","GBR")
replace parent_region = "LAC"    if inlist(iso3_parent,"ARG","BHS","BRB","BLZ","BOL", ///
                                            "BRA","CHL","COL","CRI","DOM","ECU","SLV", ///
                                            "GTM","GUY","HTI","HND","JAM","MEX","NIC", ///
                                            "PAN","PRY","PER","SUR","TTO","URY","VEN")
replace parent_region = "Asia"   if inlist(iso3_parent,"CHN","HKG","IND","IDN","JPN", ///
                                            "MYS","PHL","KOR","SGP","TWN","THA")
replace parent_region = "Other"  if parent_region == ""

*------------------------------------------------------
* Panel A: LAC pooled
*------------------------------------------------------

preserve
    gcollapse (sum) mne_exp = value_fob, by(parent_region)
    egen tot = total(mne_exp)
    gen share = (mne_exp / tot) * 100
    gsort -share
    gen order = _n
    labmask order, values(parent_region)
    local N = _N

    graph hbar (asis) share, ///
        over(order, sort(order) label(labsize(`lsize') angle(0))) ///
        bar(1, fcolor("$c_mne") lcolor("$c_mne")) ///
        ytitle("Share of MNE Agro Exports (%)", size(`lsize')) ///
        ylab(0(10)50, nogrid labsize(`lsize') format(%4.0f)) ///
        title("Origin of Foreign Ownership in Agricultural Exports (LAC)", ///
              size(`tsize') color(black)) ///
        note("Note: Pooled over all countries and years. MNE = foreign-parented exporters only.", ///
             size(`nsize')) ///
        $gro

    pr_export "F7a_parent_region_pooled"
restore

*------------------------------------------------------
* Panel B: by exporting country (stacked)
*------------------------------------------------------

preserve
    gcollapse (sum) mne_exp = value_fob, by(country_orig parent_region)
    bysort country_orig: egen tot_c = total(mne_exp)
    gen share = (mne_exp / tot_c) * 100
    keep country_orig parent_region share
    reshape wide share, i(country_orig) j(parent_region) string

    * Fill missings with 0
    foreach v in shareUSA shareEurope shareLAC shareAsia shareOther {
        replace `v' = 0 if missing(`v')
    }

    * Sort by share from USA descending
    cap gsort -shareUSA
    gen order = _n
    labmask order, values(country_orig)

    graph hbar (asis) shareUSA shareEurope shareLAC shareAsia shareOther, ///
        over(order, sort(order) label(labsize(`lsize') angle(0))) ///
        bar(1, fcolor("214 39 40")  lcolor("214 39 40"))  ///   USA: red
        bar(2, fcolor("31 119 180") lcolor("31 119 180")) ///   Europe: blue
        bar(3, fcolor("44 160 44")  lcolor("44 160 44"))  ///   LAC: green
        bar(4, fcolor("255 127 14") lcolor("255 127 14")) ///   Asia: orange
        bar(5, fcolor("150 150 150") lcolor("150 150 150")) ///  Other: grey
        stack ///
        legend(on ///
               order(1 "USA" 2 "Europe" 3 "LAC" 4 "Asia" 5 "Other") ///
               position(6) rows(1) size(`lsize') region(lcolor(white)) symysize(small)) ///
        ytitle("Share of Country's MNE Agro Exports (%)", size(`lsize')) ///
        ylab(0(25)100, nogrid labsize(`lsize') format(%4.0f)) ///
        title("Parent Region Composition by Exporting Country", ///
              size(`tsize') color(black)) ///
        note("Note: Pooled over available years. Each bar sums to 100% within country.", ///
             size(`nsize')) ///
        $gro

    pr_export "F7b_parent_region_by_country"
restore

di as text "    F7a and F7b saved."


**********************************************************************
**********************************************************************
*
*   FIGURE 8 — US-Destined Agro Exports: Who Exports?
*
*   Three categories of exporter:
*     (1) US-parented MNE (affiliate of a US parent selling to US)
*     (2) Other MNE (non-US parent, selling to US)
*     (3) Domestic firm
*
*   Two sub-panels:
*     A: LAC pooled — share of total agro exports to USA by category
*     B: Same by exporting country
*
*   Source: firm_level_data.dta, country_dest == "USA"
*
**********************************************************************
**********************************************************************

di as text _newline ">>> Building F8: US-destined exports by parent type"

use "$int\firm_level_data.dta", clear
keep if country_dest == "USA"

* Use short codes — spaces and hyphens create invalid Stata varnames after reshape
* type_order drives the graph bars; type_code drives reshape
gen type_code = ""
replace type_code = "usmne" if MNE_ext == 1 & iso3_parent == "USA"
replace type_code = "omne"  if MNE_ext == 1 & iso3_parent != "USA"
replace type_code = "dom"   if DOM_ext == 1

gen type_order = .
replace type_order = 3 if type_code == "usmne"
replace type_order = 2 if type_code == "omne"
replace type_order = 1 if type_code == "dom"

label define type_lbl 1 "Domestic" 2 "Other MNE" 3 "US-Parented MNE", replace
label values type_order type_lbl

*------------------------------------------------------
* Panel A: LAC pooled
*------------------------------------------------------

preserve
    gcollapse (sum) value_fob, by(type_code type_order)
    egen tot = total(value_fob)
    gen share = (value_fob / tot) * 100
    sort type_order

    graph hbar (asis) share, ///
        over(type_order, sort(type_order) label(labsize(`lsize') angle(0))) ///
        bar(1, fcolor("$c_dom") lcolor("$c_dom"))         ///  Domestic: grey
        bar(2, fcolor("255 127 14") lcolor("255 127 14")) ///  Other MNE: orange
        bar(3, fcolor("214 39 40") lcolor("214 39 40"))   ///  US MNE: red
        ytitle("Share of Agro Exports to the US (%)", size(`lsize')) ///
        ylab(0(10)60, nogrid labsize(`lsize') format(%4.0f)) ///
        title("Who Exports LAC Agricultural Products to the United States?", ///
              size(`tsize') color(black)) ///
        note("Note: Pooled over all countries and years. US-Parented MNE = foreign affiliate of a US-headquartered firm.", ///
             size(`nsize')) ///
        $gro

    pr_export "F8a_us_destination_pooled"
restore

*------------------------------------------------------
* Panel B: by exporting country
*------------------------------------------------------

preserve
    gcollapse (sum) value_fob, by(country_orig type_code)
    bysort country_orig: egen tot_c = total(value_fob)
    gen share = (value_fob / tot_c) * 100
    keep country_orig type_code share
    reshape wide share, i(country_orig) j(type_code) string
    * Variables created: sharedom, shareomne, shareusmne — all valid names

    foreach v in sharedom shareomne shareusmne {
        replace `v' = 0 if missing(`v')
    }
    local sh_dom   "sharedom"
    local sh_omne  "shareomne"
    local sh_usmne "shareusmne"

    * Sort by US-parented share descending
    cap gsort -sh_usmne
    gen order = _n
    labmask order, values(country_orig)

    cap {
        graph hbar (asis) `sh_usmne' `sh_omne' `sh_dom', ///
            over(order, sort(order) label(labsize(`lsize') angle(0))) ///
            bar(1, fcolor("214 39 40") lcolor("214 39 40"))   ///  US-MNE: red
            bar(2, fcolor("255 127 14") lcolor("255 127 14")) ///  Other MNE: orange
            bar(3, fcolor("$c_dom") lcolor("$c_dom"))         ///  Domestic: grey
            stack ///
            legend(on ///
                   order(1 "US-Parented MNE" 2 "Other MNE" 3 "Domestic") ///
                   position(6) rows(1) size(`lsize') region(lcolor(white)) symysize(small)) ///
            ytitle("Share of Agro Exports to US (%)", size(`lsize')) ///
            ylab(0(25)100, nogrid labsize(`lsize') format(%4.0f)) ///
            title("US-Bound Agricultural Exports by Firm Type and Country", ///
                  size(`tsize') color(black)) ///
            note("Note: Each bar sums to 100% within country. Countries sorted by US-parented MNE share.", ///
                 size(`nsize')) ///
            $gro
        pr_export "F8b_us_destination_by_country"
    }
restore

di as text "    F8a and F8b saved."


**********************************************************************
**********************************************************************
*
*   FIGURE 9 — EU-Destined Agro Exports: Who Exports?
*
*   Same structure as F8, for EU destinations.
*   EU defined as European region in dest_region variable.
*
*   Source: firm_level_data.dta, dest_region == "Europe"
*
**********************************************************************
**********************************************************************

di as text _newline ">>> Building F9: EU-destined exports by parent type"

use "$int\firm_level_data.dta", clear

* Keep EU destinations (dest_region coded as string before encode)
* If dest_region was encoded, use the encoded value; if string, use directly.
* Attempt string first, fall back to encoded
cap keep if dest_region == "Europe"
if _rc != 0 {
    * dest_region was encoded — find the code for "Europe"
    levelsof dest_region_num, local(reg_vals)
    local eu_code = .
    foreach rv of local reg_vals {
        local rlbl : label (dest_region_num) `rv'
        if "`rlbl'" == "Europe" local eu_code = `rv'
    }
    if `eu_code' != . keep if dest_region_num == `eu_code'
    else {
        di as error "Could not find Europe in dest_region. Check label."
        error 1
    }
}

gen type_code = ""
replace type_code = "eumne" if MNE_ext == 1 & ///
    inlist(iso3_parent,"AUT","BEL","BGR","CYP","CZE","DNK","EST","FIN","FRA","DEU", ///
                        "GRC","HUN","IRL","ITA","LVA","LTU","LUX","MLT","NLD","POL", ///
                        "PRT","ROU","SVK","SVN","ESP","SWE","GBR")
replace type_code = "omne"  if MNE_ext == 1 & type_code == ""
replace type_code = "dom"   if DOM_ext == 1

gen type_order = .
replace type_order = 3 if type_code == "eumne"
replace type_order = 2 if type_code == "omne"
replace type_order = 1 if type_code == "dom"

label define eu_type_lbl 1 "Domestic" 2 "Other MNE" 3 "EU-Parented MNE", replace
label values type_order eu_type_lbl

*------------------------------------------------------
* Panel A: LAC pooled
*------------------------------------------------------

preserve
    gcollapse (sum) value_fob, by(type_code type_order)
    egen tot = total(value_fob)
    gen share = (value_fob / tot) * 100
    sort type_order

    graph hbar (asis) share, ///
        over(type_order, sort(type_order) label(labsize(`lsize') angle(0))) ///
        bar(1, fcolor("$c_dom") lcolor("$c_dom"))         ///  Domestic: grey
        bar(2, fcolor("255 127 14") lcolor("255 127 14")) ///  Other MNE: orange
        bar(3, fcolor("31 119 180") lcolor("31 119 180")) ///  EU MNE: blue
        ytitle("Share of Agro Exports to Europe (%)", size(`lsize')) ///
        ylab(0(10)60, nogrid labsize(`lsize') format(%4.0f)) ///
        title("Who Exports LAC Agricultural Products to Europe?", ///
              size(`tsize') color(black)) ///
        note("Note: Pooled over all countries and years. EU-Parented MNE = foreign affiliate of a European-headquartered firm.", ///
             size(`nsize')) ///
        $gro

    pr_export "F9a_eu_destination_pooled"
restore

*------------------------------------------------------
* Panel B: by exporting country
*------------------------------------------------------

preserve
    gcollapse (sum) value_fob, by(country_orig type_code)
    bysort country_orig: egen tot_c = total(value_fob)
    gen share = (value_fob / tot_c) * 100
    keep country_orig type_code share
    reshape wide share, i(country_orig) j(type_code) string
    * Variables created: sharedom, shareomne, shareeumne — all valid names

    foreach v in sharedom shareomne shareeumne {
        replace `v' = 0 if missing(`v')
    }
    local sh_dom   "sharedom"
    local sh_omne  "shareomne"
    local sh_eumne "shareeumne"

    cap gsort -`sh_eumne'
    gen order = _n
    labmask order, values(country_orig)

    cap {
        graph hbar (asis) `sh_eumne' `sh_omne' `sh_dom', ///
            over(order, sort(order) label(labsize(`lsize') angle(0))) ///
            bar(1, fcolor("31 119 180") lcolor("31 119 180")) ///  EU-MNE: blue
            bar(2, fcolor("255 127 14") lcolor("255 127 14")) ///  Other MNE: orange
            bar(3, fcolor("$c_dom") lcolor("$c_dom"))          ///  Domestic: grey
            stack ///
            legend(on ///
                   order(1 "EU-Parented MNE" 2 "Other MNE" 3 "Domestic") ///
                   position(6) rows(1) size(`lsize') region(lcolor(white)) symysize(small)) ///
            ytitle("Share of Agro Exports to Europe (%)", size(`lsize')) ///
            ylab(0(25)100, nogrid labsize(`lsize') format(%4.0f)) ///
            title("Europe-Bound Agricultural Exports by Firm Type and Country", ///
                  size(`tsize') color(black)) ///
            note("Note: Each bar sums to 100% within country. Countries sorted by EU-parented MNE share.", ///
                 size(`nsize')) ///
            $gro
        pr_export "F9b_eu_destination_by_country"
    }
restore

di as text "    F9a and F9b saved."


**********************************************************************
**********************************************************************
*
*   TABLE 2 — Agricultural Section Breakdown (LAC Pooled)
*
*   Columns: Section | Total Value (USD bn) | % of Agro Exports
*            | # Firms (avg annual) | MNE Share Value (%) | MNE Share Firms (%)
*            | Top HS2 Chapter by Value
*
*   Source: firm_level_data.dta + collapsed_opy.dta
*
**********************************************************************
**********************************************************************

di as text _newline ">>> Building T2: Section breakdown"

* ---- Step 1: section totals from firm_level_data ----
use "$int\firm_level_data.dta", clear

gen double mne_val = value_fob * MNE_ext

* Distinct firms per section: flag first appearance of each firm in the section
bysort hs_section firm_id (year): gen byte first_firm_sect = (_n == 1)
bysort hs_section firm_id (year): gen byte first_mne_sect  = (_n == 1 & MNE_ext == 1)

gcollapse ///
    (sum)   total_value = value_fob ///
    (sum)   mne_val                  ///
    (sum)   n_firms     = first_firm_sect ///
    (sum)   n_mne       = first_mne_sect  ///
    , by(hs_section) labelformat(#sourcelabel#)

drop if hs_section == .

gen mne_val_share  = (mne_val    / total_value) * 100
gen mne_firm_share = (n_mne      / n_firms)     * 100
gen total_val_bn   = total_value / 1e9

* Compute % of total agro exports
egen double grand_total = total(total_value)
gen pct_of_agro = (total_value / grand_total) * 100

* ---- Step 2: top HS2 chapter per section (separate collapse, then merge) ----
preserve
    use "$int\firm_level_data.dta", clear
    gcollapse (sum) val_hs2 = value_fob, by(hs_section hs2) labelformat(#sourcelabel#)
    drop if hs_section == .
    bysort hs_section (val_hs2): keep if _n == _N    // keep row with highest value
    keep hs_section hs2
    rename hs2 top_hs2
    tempfile top_hs2_file
    save `top_hs2_file'
restore

merge 1:1 hs_section using `top_hs2_file', nogen

sort hs_section
label values hs_section agro_sect_lbl

* ---- Step 3: write LaTeX table ----
* FIX: 7 columns (lrrrrrr), \specialcell instead of \makecell,
*      firm count instead of transaction count, clear column labels
file open fh using "$pr_tab\T2_section_breakdown.tex", write replace
file write fh "\begin{tabular}{lrrrrrr}" _newline
file write fh "\toprule" _newline
file write fh "Section" ///
    " & \specialcell{Total Value \\ (USD bn)}" ///
    " & \specialcell{\% Agro \\ Exports}" ///
    " & \specialcell{\# Unique \\ Firms}" ///
    " & \specialcell{MNE Value \\ Share (\%)}" ///
    " & \specialcell{MNE Firm \\ Share (\%)}" ///
    " & \specialcell{Top \\ HS2} \\" _newline
file write fh "\midrule" _newline

local N = _N
forval i = 1/`N' {
    local slbl : label agro_sect_lbl `= hs_section[`i']'
    local vbn  : di %6.1f  total_val_bn[`i']
    local pct  : di %5.1f  pct_of_agro[`i']
    local nf   : di %9.0fc n_firms[`i']
    local msv  : di %5.1f  mne_val_share[`i']
    local msf  : di %5.1f  mne_firm_share[`i']
    local tch  : di %02.0f top_hs2[`i']
    file write fh "`slbl' & `vbn' & `pct' & `nf' & `msv' & `msf' & HS~`tch' \\" _newline
}

file write fh "\midrule" _newline
file write fh "\multicolumn{7}{l}{\footnotesize \textit{Notes:} Pooled over all countries and available years (2006--2022). Value in USD billions.} \\" _newline
file write fh "\multicolumn{7}{l}{\footnotesize MNE\textsubscript{ext} = foreign-parented exporter. \# Unique Firms = distinct exporters ever active in section. MNE Value Share = section exports by MNE firms.} \\" _newline
file write fh "\bottomrule" _newline
file write fh "\end{tabular}" _newline
file close fh

copy "$pr_tab\T2_section_breakdown.tex" "$pr_ol_tab\T2_section_breakdown.tex", replace
di as text "    T2 saved."


**********************************************************************
* COMPLETION
**********************************************************************

di as text ""
di as text "============================================================"
di as text "  POLICY REPORT — COMPLETED"
di as text "============================================================"
di as text ""
di as text "  Output folder: $pr"
di as text "  Overleaf copy: $pr_ol"
di as text ""
di as text "  TABLES (2)"
di as text "  T1  T1_country_snapshot.tex"
di as text "  T2  T2_section_breakdown.tex"
di as text ""
di as text "  FIGURES (11 files across 9 concepts)"
di as text "  F1  F1_mne_share_by_country"
di as text "  F2  F2_mne_trend_lac_highlighted"
di as text "  F3  F3_value_by_section_mne_dom"
di as text "  F4  F4_mne_share_section_country"
di as text "  F5a F5a_destination_income_group"
di as text "  F5b F5b_destination_region"
di as text "  F6  F6_firm_size_boxplot"
di as text "  F7a F7a_parent_region_pooled"
di as text "  F7b F7b_parent_region_by_country"
di as text "  F8a F8a_us_destination_pooled"
di as text "  F8b F8b_us_destination_by_country"
di as text "  F9a F9a_eu_destination_pooled"
di as text "  F9b F9b_eu_destination_by_country"
di as text ""
di as text "  SUGGESTED REPORT LAYOUT (6 pages):"
di as text "  p.1  T1 + intro text"
di as text "  p.2  F1 + F2 (side by side)"
di as text "  p.3  F3 + F4 (side by side)"
di as text "  p.4  F5a + F5b (side by side)"
di as text "  p.5  F7b + F6 (side by side)"
di as text "  p.6  F8a + F9a + T2 (section data)"
di as text "  Appendix: F7a, F8b, F9b"
di as text "============================================================"
