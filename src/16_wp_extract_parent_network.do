/*==============================================================================
  16_wp_extract_parent_network.do -- parent-level global network size, for the
  reproduction of the stylized-facts document's Figure 5 (Fact 4) on the current base.

  Input : $legacy_raw\Merge_DNB_Orbis_parent_total_PostIA_v2.dta  (5.4 GB, affiliate rows
          carrying the parent's totals; built 2026-06-18 by the parents dofile)
  Output: $int\wp\parent_network_size.dta  -- one row per name_parent_adj:
          total_affiliates total_affiliates_lac n_countries n_countries_lac iso3_parent
  Key   : name_parent_adj = upper(trim(coalesce(ent_name_par, globalultimatebusinessname)))
          -- the same key as parent_key in fdpy_base.dta (src/15).
==============================================================================*/
clear all
set more off
do "C:\Sebas BID\Orbis_DNB_Customs_Final\config\paths.do"
capture log close
log using "$logs\16_wp_extract_parent_network_stata.log", replace text
timer on 1
use name_parent_adj iso3_parent total_affiliates total_affiliates_lac n_countries n_countries_lac ///
    using "$legacy_raw\Merge_DNB_Orbis_parent_total_PostIA_v2.dta", clear
timer off 1
timer list 1
count
replace name_parent_adj = upper(strtrim(name_parent_adj))
drop if name_parent_adj == ""
* one row per parent: keep the maximum network size recorded for the name
collapse (max) total_affiliates total_affiliates_lac n_countries n_countries_lac (firstnm) iso3_parent, by(name_parent_adj)
count
summarize total_affiliates n_countries, detail
compress
save "$int\wp\parent_network_size.dta", replace
log close
