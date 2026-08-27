*==============================================================================
*  ucp03_tables.do  -- CONDUIT REALLOCATION, the tables
*
*  Three owner concepts, all carried side by side so the paper can show a range
*  rather than assert one number:
*
*    A  iso3_parent  the status quo: the country of the parent as recorded
*    B  iso3_ucp     naive chain: first available of GUO50 > GUO25 > D&B > parent
*    C  iso3_ucp2    IMPROVED chain: the first NON-CONDUIT country among those
*                    four. A holding company in Panama is not an economic owner,
*                    and concept B will happily hand you one -- the flows show
*                    value moving DEU -> PAN and NLD -> LUX under B.
*
*  Whatever survives all three as a conduit is the residual the paper has to
*  disclose rather than assume away.
*==============================================================================

set more off
clear all
set linesize 200

local OUT "C:\Sebas BID\Orbis_DNB_Customs_Final\output\tables"
use "`OUT'/mne_ucp_cube.dta", clear
count

local CONDUIT "PAN BMU VGB CYM CUW ABW BHS BRB LIE LUX IRL MLT CYP JEY GGY IMN MCO AND GIB MHL LBR ANT SXM TCA VCT KNA SYC MUS BLZ"

capture program drop flagconduit
program define flagconduit
    args newvar src
    quietly generate byte `newvar' = 0
    foreach c in PAN BMU VGB CYM CUW ABW BHS BRB LIE LUX IRL MLT CYP JEY GGY ///
                 IMN MCO AND GIB MHL LBR ANT SXM TCA VCT KNA SYC MUS BLZ {
        quietly replace `newvar' = 1 if `src' == "`c'"
    }
end

foreach v in iso3_parent iso3_ucp ucp50 ucp25 ucpdnb {
    flagconduit cd_`v' `v'
    quietly replace cd_`v' = 0 if `v' == ""
}

*--- concept C: first NON-conduit in the chain -------------------------------
generate str3 iso3_ucp2 = ""
quietly replace iso3_ucp2 = iso3_parent if iso3_parent != "" & cd_iso3_parent == 0
quietly replace iso3_ucp2 = ucpdnb      if ucpdnb      != "" & cd_ucpdnb      == 0
quietly replace iso3_ucp2 = ucp25       if ucp25       != "" & cd_ucp25       == 0
quietly replace iso3_ucp2 = ucp50       if ucp50       != "" & cd_ucp50       == 0
generate byte unresolved = (iso3_ucp2 == "") & (iso3_parent != "")
quietly replace iso3_ucp2 = iso3_parent if iso3_ucp2 == ""
label variable iso3_ucp2 "first NON-conduit owner in the chain (GUO50 > GUO25 > D&B > parent)"
label variable unresolved "every link in the chain is a conduit jurisdiction"

generate byte MNE_ucp2 = matched & (iso3_ucp2 != "") & (iso3_ucp2 != country_orig)
generate byte to_ucp2  = (iso3_ucp2 != "") & (country_dest == iso3_ucp2)

display "=============================================================="
display "V0  HOW MUCH VALUE EACH CONCEPT MOVES, AND WHAT IT CANNOT MOVE"
display "=============================================================="
quietly summarize value_fob
local TOT = r(sum)
display "total export value                                : " %18.0fc `TOT'
quietly summarize value_fob if iso3_parent != ""
display "value with a recorded parent                      : " %18.0fc r(sum)
quietly summarize value_fob if iso3_ucp != iso3_parent & iso3_parent != ""
display "  concept B moves                                 : " %18.0fc r(sum)
quietly summarize value_fob if iso3_ucp2 != iso3_parent & iso3_parent != ""
display "  concept C moves                                 : " %18.0fc r(sum)
quietly summarize value_fob if cd_iso3_parent == 1
display "value whose PARENT is a conduit jurisdiction      : " %18.0fc r(sum)
quietly summarize value_fob if unresolved == 1
display "  STILL a conduit after the full chain (residual) : " %18.0fc r(sum)

display "=============================================================="
display "V1  WHERE CONCEPT C MOVES VALUE (top flows)"
display "=============================================================="
preserve
    keep if iso3_ucp2 != iso3_parent & iso3_parent != ""
    collapse (sum) value_fob, by(iso3_parent iso3_ucp2)
    gsort -value_fob
    format value_fob %18.0fc
    list iso3_parent iso3_ucp2 value_fob in 1/20, noobs
    export delimited using "`OUT'/V1_reallocation_flows_nonconduit.csv", replace
restore

display "=============================================================="
display "V2  OWNER SHARES UNDER ALL THREE CONCEPTS"
display "=============================================================="
preserve
    keep if matched == 1
    generate double v = value_fob
    collapse (sum) vA = v, by(iso3_parent)
    rename iso3_parent owner
    tempfile A
    save `A'
restore
preserve
    keep if matched == 1
    collapse (sum) vB = value_fob, by(iso3_ucp)
    rename iso3_ucp owner
    tempfile B
    save `B'
restore
preserve
    keep if matched == 1
    collapse (sum) vC = value_fob, by(iso3_ucp2)
    rename iso3_ucp2 owner
    merge 1:1 owner using `A', nogenerate
    merge 1:1 owner using `B', nogenerate
    foreach v in vA vB vC {
        quietly replace `v' = 0 if missing(`v')
        quietly summarize `v'
        generate double sh_`v' = `v'/r(sum)
    }
    gsort -vA
    list owner sh_vA sh_vB sh_vC in 1/22, noobs
    export delimited using "`OUT'/V2_owner_shares_three_concepts.csv", replace
restore

display "=============================================================="
display "V3  theta_X BY DESTINATION UNDER ALL THREE CONCEPTS"
display "    (share of X's imports from LAC produced by X-owned affiliates)"
display "=============================================================="
preserve
    generate double vA = value_fob*((MNE_ext ==1) & (iso3_parent == country_dest))
    generate double vB = value_fob*((MNE_ucp ==1) & (iso3_ucp    == country_dest))
    generate double vC = value_fob*((MNE_ucp2==1) & (iso3_ucp2   == country_dest))
    generate double vU = value_fob*unresolved
    collapse (sum) value_fob vA vB vC vU, by(country_dest)
    generate double thetaA = vA/value_fob
    generate double thetaB = vB/value_fob
    generate double thetaC = vC/value_fob
    generate double unres  = vU/value_fob
    gsort -value_fob
    format value_fob %18.0fc
    list country_dest value_fob thetaA thetaB thetaC unres in 1/20, noobs
    export delimited using "`OUT'/V3_theta_three_concepts.csv", replace
restore

display "=============================================================="
display "V4  SHARE SHIPPED TO THE OWNER'S OWN COUNTRY, ALL THREE CONCEPTS"
display "=============================================================="
local D = 0
quietly summarize value_fob if MNE_ext == 1
local D = r(sum)
quietly summarize value_fob if MNE_ext == 1 & to_parent == 1
display "concept A (parent as recorded) : " %8.4f r(sum)/`D'
quietly summarize value_fob if MNE_ucp == 1
local D = r(sum)
quietly summarize value_fob if MNE_ucp == 1 & to_ucp == 1
display "concept B (naive chain)        : " %8.4f r(sum)/`D'
quietly summarize value_fob if MNE_ucp2 == 1
local D = r(sum)
quietly summarize value_fob if MNE_ucp2 == 1 & to_ucp2 == 1
display "concept C (non-conduit chain)  : " %8.4f r(sum)/`D'

display "=============================================================="
display "V5  THE RANGE FOR theta_USA: none of the unresolved value is US-owned,"
display "    against all of it being US-owned"
display "=============================================================="
quietly summarize value_fob if country_dest == "USA"
local TUS = r(sum)
quietly summarize value_fob if country_dest == "USA" & MNE_ucp2 == 1 & iso3_ucp2 == "USA"
local LO = r(sum)/`TUS'
quietly summarize value_fob if country_dest == "USA" & unresolved == 1
local UP = `LO' + r(sum)/`TUS'
display "theta_USA lower bound : " %8.4f `LO'
display "theta_USA upper bound : " %8.4f `UP'

display "=== done ==="
