/*==============================================================================
  15_wp_extract_fdpy.do -- ONE pass over the 20.6 GB base for the working paper

  Extracts the columns every WP exhibit needs (firm x origin x destination x HS6 x
  year grain, ~5 M rows), builds the flags both MNE conventions need, merges the
  group-level destination-presence file, and saves a compact cache that the Python
  scripts in stylized_facts/python/wp_*.py read. Everything downstream (cubes,
  figures, tables, regressions) is built from this cache -- never from the base.

  Inputs : $base                          (config/paths.do)
           $int_v4\intermediate_mne_presence.dta   (ID_Orbis_DNB x country_dest: has affiliate in dest / neighbour)
  Output : $int\wp\fdpy_base.dta

  Columns written:
    country_orig country_dest hs07_6d year value_fob (>=0)
    Tax_ID                       firm id within origin
    m_dnb  = (_merge_DNB_Orbis == 3)     matched flag, stylized-facts convention (Ignacio)
    m_fr   = (_merge_final_review == 3)  matched flag, src/05-14 convention (after manual review)
    iso3_parent                  parent country as recorded ("" = unknown)
    ID_Orbis_DNB                 group id (guo25, or dunsnumber if D&B-only)
    parent_key                   upper(trim(coalesce(ent_name_par, globalultimatebusinessname)))
    exporter_is_hq               exporter is itself the global ultimate (Orbis: subsidiarybvdid==guo25;
                                 D&B: dunsnumber==globalultimatedunsnumber)
    has_aff_in_dest, has_aff_in_neighbor   from intermediate_mne_presence (0 if no record)
    naics_aff_2                  affiliate 2-digit NAICS (for the services question)

  Run:  "C:\Program Files\Stata18\StataMP-64.exe" /e do src\15_wp_extract_fdpy.do
==============================================================================*/

clear all
set more off
set linesize 160
do "C:\Sebas BID\Orbis_DNB_Customs_Final\config\paths.do"
capture mkdir "$int\wp"
capture log close
log using "$logs\15_wp_extract_fdpy_stata.log", replace text

timer clear 1
timer on 1
display as text ">>> reading the base: $base"
use country_orig Tax_ID country_dest hs07_6d year value_fob ///
    _merge_DNB_Orbis _merge_final_review iso3_parent ID_Orbis_DNB ///
    guo25 subsidiarybvdid dunsnumber globalultimatedunsnumber naics_aff_2 ///
    ent_name_par globalultimatebusinessname ///
    using "$base", clear
timer off 1
timer list 1
count
describe, short

*--- housekeeping ------------------------------------------------------------
replace value_fob = -value_fob if value_fob < 0
foreach v in country_orig country_dest iso3_parent {
    quietly replace `v' = upper(trim(`v'))
    quietly replace `v' = "" if inlist(`v', ".", "NA", "N/A", "-")
}
capture confirm string variable hs07_6d
if _rc != 0 tostring hs07_6d, replace format(%06.0f)
quietly replace hs07_6d = trim(hs07_6d)
capture confirm string variable Tax_ID
if _rc != 0 tostring Tax_ID, replace format(%20.0f)
capture confirm string variable naics_aff_2
if _rc != 0 tostring naics_aff_2, replace

*--- the two match flags -----------------------------------------------------
generate byte m_dnb = (_merge_DNB_Orbis == 3)
generate byte m_fr  = (_merge_final_review == 3)
label variable m_dnb "matched to Orbis/D&B (stylized-facts convention: _merge_DNB_Orbis==3)"
label variable m_fr  "matched after manual review (src convention: _merge_final_review==3)"
tabulate m_dnb m_fr
table m_dnb m_fr, statistic(sum value_fob) nformat(%18.0fc)

*--- exporter is itself the headquarters -------------------------------------
capture confirm string variable dunsnumber
if _rc != 0 tostring dunsnumber, replace format(%20.0f)
capture confirm string variable globalultimatedunsnumber
if _rc != 0 tostring globalultimatedunsnumber, replace format(%20.0f)
foreach v in guo25 subsidiarybvdid dunsnumber globalultimatedunsnumber {
    quietly replace `v' = trim(`v')
    quietly replace `v' = "" if inlist(`v', ".", "NA")
}
generate byte exporter_is_hq = (guo25 != "" & subsidiarybvdid == guo25) ///
                             | (dunsnumber != "" & dunsnumber == globalultimatedunsnumber)
label variable exporter_is_hq "exporter is the group's global ultimate owner (HQ)"
tabulate exporter_is_hq m_dnb

*--- parent group key (same as build_network_size.py / parents dofile) -------
generate parent_key = upper(strtrim(ent_name_par))
replace  parent_key = upper(strtrim(globalultimatebusinessname)) if parent_key == ""
drop ent_name_par globalultimatebusinessname guo25 subsidiarybvdid dunsnumber globalultimatedunsnumber
drop _merge_DNB_Orbis _merge_final_review

*--- destination presence of the group ---------------------------------------
display as text ">>> merging destination presence"
merge m:1 ID_Orbis_DNB country_dest using "$int_v4\intermediate_mne_presence.dta", ///
    keep(master match) keepusing(company_has_aff_in_dest company_has_aff_in_neighbor)
tabulate _merge m_dnb
rename company_has_aff_in_dest     has_aff_in_dest
rename company_has_aff_in_neighbor has_aff_in_neighbor
replace has_aff_in_dest     = 0 if missing(has_aff_in_dest)
replace has_aff_in_neighbor = 0 if missing(has_aff_in_neighbor)
drop _merge

compress
describe
count
save "$int\wp\fdpy_base.dta", replace
display as text ">>> saved $int\wp\fdpy_base.dta"
log close
