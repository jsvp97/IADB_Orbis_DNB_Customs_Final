*==============================================================================
*  dest02_cube.do   -- step 1 of 2, second attempt
*
*  Same as dest01 but `parent_country` is a long string (strL), which collapse
*  cannot use in by(); it is recast to a fixed-width string first.
*==============================================================================

set more off
clear all
set linesize 200

local INFILE "C:\Sebas BID\Orbis_DNB_Customs\Base_final_Customs_DNB_Orbis_product_complete.dta"
local OUT    "C:\Sebas BID\Orbis_DNB_Customs_Final\output\tables"
capture mkdir "C:\Sebas BID\Orbis_DNB_Customs_Final\output"
capture mkdir "`OUT'"

use country_orig country_dest year value_fob iso3_parent _merge_final_review ///
    parent_country parent_country_conf parent_country_flagged               ///
    using "`INFILE'", clear
count
describe

*--- housekeeping ------------------------------------------------------------
foreach v in country_orig country_dest iso3_parent {
    capture confirm string variable `v'
    if _rc == 0 {
        quietly replace `v' = upper(trim(`v'))
        quietly replace `v' = "" if inlist(`v', ".", "NA", "N/A", "-")
    }
}

* parent_country may be strL; make it a plain fixed-width string
capture confirm string variable parent_country
if _rc == 0 {
    generate str8 pcountry = upper(trim(substr(parent_country, 1, 8)))
    quietly replace pcountry = "" if inlist(pcountry, ".", "NA", "N/A", "-")
    drop parent_country
}
else {
    generate str8 pcountry = ""
}

capture confirm string variable parent_country_conf
if _rc == 0 {
    generate str12 pconf = substr(parent_country_conf, 1, 12)
    drop parent_country_conf
}
else {
    generate str12 pconf = ""
}

capture confirm string variable parent_country_flagged
if _rc == 0 {
    generate str12 pflag = substr(parent_country_flagged, 1, 12)
    drop parent_country_flagged
}
else {
    rename parent_country_flagged pflagnum
    generate str12 pflag = string(pflagnum)
    drop pflagnum
}

*--- MNE definitions, verbatim from src/05_descriptive_stats.do --------------
generate byte MNE_ext   = (_merge_final_review == 3) & (iso3_parent != "") ///
                        & (iso3_parent != country_orig)
generate byte MNE_dom   = (_merge_final_review == 3) & (iso3_parent == country_orig)
generate byte MNE_total = (_merge_final_review == 3)

generate byte has_parent = (iso3_parent != "")
generate byte to_parent  = has_parent & (country_dest == iso3_parent)
label variable has_parent "exporter has a recorded parent country"
label variable to_parent  "shipment goes TO the parent's own country"

*--- diagnostics -------------------------------------------------------------
display "=== how the two parent-country variables compare ==="
display "  NOTE: parent_country holds a country NAME, iso3_parent an ISO3 code."
tabulate pcountry if has_parent, sort missing
tabulate pflag, missing

display "=== coverage ==="
table MNE_total has_parent, statistic(sum value_fob) nformat(%18.0fc)
display "=== the headline ==="
table MNE_ext to_parent, statistic(sum value_fob) nformat(%18.0fc)

*--- the cube ----------------------------------------------------------------
display "=== collapsing ==="
collapse (sum) value_fob (count) nrows = value_fob, ///
    by(country_orig country_dest year iso3_parent pcountry pflag              ///
       MNE_ext MNE_dom MNE_total has_parent to_parent)
compress
count
save "`OUT'/mne_export_destination_cube.dta", replace
display "=== cube saved ==="
describe
