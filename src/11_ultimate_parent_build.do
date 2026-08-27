*==============================================================================
*  ucp01_cube.do   -- CONDUIT REALLOCATION, step 1 of 2
*
*  The problem (brief section 6, item 2): `iso3_parent` is the country of the
*  parent Orbis/D&B records, and for a large slice of value that parent is a
*  holding company in a conduit jurisdiction, not an economic owner. GBR is
*  17.9% of foreign-MNE export value and ships 0.9% of it home; LIE is 4.4%.
*  A paper about US tariffs cannot rest on that.
*
*  The fix: build `iso3_ucp`, the country of the ULTIMATE CONTROLLING PARENT,
*  from three sources in order of priority, and keep every ingredient so the
*  reallocation can be audited and switched off:
*
*     1  GUO50C   Orbis global ultimate owner at the 50% control threshold
*     2  GUO25C   Orbis global ultimate owner at 25%
*     3  globalultimatecountry   Dun & Bradstreet's global ultimate (a NAME)
*     4  iso3_parent             the status quo, as the fallback
*
*  Orbis codes are ISO2 and D&B gives a country name, so both are crosswalked
*  to ISO3 first. This script reads the 20.5 GB file once and saves a cube.
*==============================================================================

set more off
clear all
set linesize 200

local INFILE "C:\Sebas BID\Orbis_DNB_Customs\Base_final_Customs_DNB_Orbis_product_complete.dta"
local OUT    "C:\Sebas BID\Orbis_DNB_Customs_Final\output\tables"

*--- crosswalks --------------------------------------------------------------
import delimited using "`OUT'/iso2_to_iso3.csv", clear varnames(1) stringcols(_all)
keep iso2 iso3
rename iso3 xw_iso3
tempfile xw2
save `xw2'

import delimited using "`OUT'/cname_to_iso3.csv", clear varnames(1) stringcols(_all)
keep cname iso3
rename iso3 xwn_iso3
tempfile xwn
save `xwn'

*--- the data ----------------------------------------------------------------
display "=== reading the transaction file ==="
use country_orig country_dest year value_fob iso3_parent _merge_final_review ///
    GUO50C GUO25C globalultimatecountry                                      ///
    using "`INFILE'", clear
count

foreach v in country_orig country_dest iso3_parent {
    quietly replace `v' = upper(trim(`v'))
    quietly replace `v' = "" if inlist(`v', ".", "NA", "N/A", "-")
}
foreach v in GUO50C GUO25C {
    quietly replace `v' = upper(trim(`v'))
    quietly replace `v' = "" if inlist(`v', ".", "NA", "N/A", "-", "WW", "ZZ", "XX")
}
quietly replace globalultimatecountry = upper(trim(globalultimatecountry))

*--- crosswalk GUO50C --------------------------------------------------------
generate iso2 = GUO50C
merge m:1 iso2 using `xw2', keep(master match) nogenerate
rename xw_iso3 ucp50
drop iso2

generate iso2 = GUO25C
merge m:1 iso2 using `xw2', keep(master match) nogenerate
rename xw_iso3 ucp25
drop iso2

generate cname = globalultimatecountry
merge m:1 cname using `xwn', keep(master match) nogenerate
rename xwn_iso3 ucpdnb
drop cname

foreach v in ucp50 ucp25 ucpdnb {
    quietly replace `v' = "" if `v' == "."
}

display "=== how far does each ultimate-owner source reach? (share of MNE value) ==="
generate byte matched = (_merge_final_review == 3)
generate byte has_parent = (iso3_parent != "")
foreach v in ucp50 ucp25 ucpdnb {
    quietly summarize value_fob if has_parent & `v' != ""
    local a = r(sum)
    quietly summarize value_fob if has_parent
    display "`v' covers " %8.4f `a'/r(sum) " of value that has an iso3_parent"
}

*--- the ultimate controlling parent, and the status quo ---------------------
generate str3 iso3_ucp = ""
quietly replace iso3_ucp = ucpdnb      if ucpdnb  != ""
quietly replace iso3_ucp = ucp25       if ucp25   != ""
quietly replace iso3_ucp = ucp50       if ucp50   != ""
quietly replace iso3_ucp = iso3_parent if iso3_ucp == ""
label variable iso3_ucp "ultimate controlling parent country (GUO50 > GUO25 > D&B > parent)"

*--- MNE definitions, on BOTH the status quo and the reallocated owner -------
generate byte MNE_ext   = matched & (iso3_parent != "") & (iso3_parent != country_orig)
generate byte MNE_ucp   = matched & (iso3_ucp    != "") & (iso3_ucp    != country_orig)
generate byte to_parent = (iso3_parent != "") & (country_dest == iso3_parent)
generate byte to_ucp    = (iso3_ucp    != "") & (country_dest == iso3_ucp)

display "=== how much value changes owner country at all? ==="
generate byte moved = (iso3_ucp != iso3_parent) & has_parent
table moved, statistic(sum value_fob) nformat(%18.0fc)

display "=== headline, before and after ==="
table MNE_ext to_parent, statistic(sum value_fob) nformat(%18.0fc)
table MNE_ucp to_ucp,    statistic(sum value_fob) nformat(%18.0fc)

*--- the cube ----------------------------------------------------------------
display "=== collapsing ==="
collapse (sum) value_fob, ///
    by(country_orig country_dest year iso3_parent iso3_ucp                    ///
       ucp50 ucp25 ucpdnb                                                     ///
       MNE_ext MNE_ucp to_parent to_ucp moved matched)
compress
count
save "`OUT'/mne_ucp_cube.dta", replace
describe
