/*==============================================================================
  config/paths.do -- EVERY machine-specific path, in one place (Stata)

  Usage, at the top of any script:
      do "C:\Sebas BID\Orbis_DNB_Customs_Final\config\paths.do"
  or, once $root is known:
      do "$root\config\paths.do"

  Edit ONLY this file when files move or when the code runs on another machine.
  Scripts 09-14 in src/ still hard-code these paths at their top (they predate this
  file); replace those lines with `do "$root\config\paths.do"` when you touch them.

  Verified on Sebastian's laptop, 2026-09-03. Sizes in CLAUDE.md section 1.
==============================================================================*/

* ---- this repository ---------------------------------------------------------
global root       "C:\Sebas BID\Orbis_DNB_Customs_Final"
global src        "$root\src"
global sf_stata   "$root\stylized_facts\stata"
global raw        "$root\data\raw"            // small inputs (product chars, gravity, concordances)
global int        "$root\data\intermediate"   // new caches/cubes built from now on go here
global cubes      "$int\v4_cubes"             // collapsed_{oy,ody,opy,odpy}.dta (copied from $int_v4, 2026-09-03)
global output     "$root\output"
global tables     "$output\tables"
global graphs     "$output\graphs"
global regs       "$output\regressions"
global logs       "$output\logs"
global overleaf   "$output\overleaf_mirror"   // local stand-in; point at a real Overleaf sync folder if you have one

* ---- the big files that stay in the old working folder ----------------------
global legacy     "C:\Sebas BID\Orbis_DNB_Customs"
global base       "$legacy\Base_final_Customs_DNB_Orbis_product_complete.dta"   // 20.6 GB, THE base
global int_v4     "$legacy\Claude\Data\Intermediate_v4"                        // originals of the collapsed_* cubes + firm_*_level, firm_level_data(_full) (13 GB), intermediate_mne_presence (2 GB)
global legacy_raw "$legacy\Claude\Data\Raw"                                    // Merge_DNB_Orbis_{affiliates,parent,total}_total_PostIA_v2 (network size)
global customs    "$legacy\Customs"                                            // exp_fdpt_10c_names_180625.dta, manual review files
global ia_review  "$legacy\IA_review"

* ---- Orbis / D&B corporate databases -----------------------------------------
global orbis_dnb  "C:\Sebas BID\Orbis_DNB"
global merge_v2   "$orbis_dnb\IA review\Merge_DNB_Orbis_PostIA_v2.dta"        // 38 GB, affiliate level
global merge_par  "$orbis_dnb\IA review\Merge_DNB_Orbis_par_PostIA_v2.dta"    // 10.9 GB, parent level
global merge_v4   "$legacy\Merge_DNB_Orbis_PostIA_v4.dta"                     // 47.9 GB, used by src/01 final merge
global orbis_raw  "D:\BID\Orbis\FINAL"                                        // raw Orbis links (external drive; only src/02 needs it)

* ---- small inputs, by name (all in $raw) --------------------------------------
global f_prodchar "$raw\product_characteristics_hs6_2002_adj.dta"   // pci sigma upstreamness ladder rauch, hs2007 descriptions
global f_lall     "$raw\lall2000_hs2007.dta"
global f_ipc1     "$raw\ALP_IPC_Patent_hs2007_6_to_ipc1.dta"
global f_rhci     "$raw\UNCTAD RHCI hs_2007_indices.dta"
global f_rca      "$raw\RCA_WITS_orig_year.dta"
global f_gravity  "$raw\Gravity_V202211.dta"
global f_tariffs  "$raw\tariffsPairs_88_21_vbeta1-2024-12.dta"
global f_pta      "$raw\PTA_BIT_DTT_BID.dta"
global f_income   "$raw\WB_Income_group.dta"
global f_hs2sitc  "$raw\HS_2007_to_SITC3.dta"
global f_hs2naics "$raw\HS6_to_NAICS_2017.dta"
global f_hsdesc   "$raw\JobID-46_Concordance_H3_to_H2.CSV"          // HS 2007 6-digit descriptions (also in $f_prodchar and $f_lall)
* to be downloaded (see docs/WORKPLAN_working_paper.md items 1b and 2):
global f_fgo      "$raw\FGO2022_trade_elasticities_hs6.dta"          // Fontagne-Guimbard-Orefice (2022) -- NOT on disk yet
global f_bec      "$raw\HS2007_to_BEC.dta"                           // UN BEC correspondence -- NOT on disk yet

* ---- stata executable (for batch runs from a shell) --------------------------
global stata_exe  "C:\Program Files\Stata18\StataMP-64.exe"

* ---- create output folders ----------------------------------------------------
foreach d in "$int" "$output" "$tables" "$graphs" "$regs" "$logs" "$overleaf" {
    capture mkdir "`d'"
}
