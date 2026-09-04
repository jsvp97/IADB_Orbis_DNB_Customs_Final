**********************************************************************
*
*   00_master.do  -- MNCustoms (Multinational Firms and Trade)
*
*   Authors: Ignacio Marra de Artinano  (ULB & ECARES)
*            Gabriel Scattolo            (IDB)
*            Sebastian Velasquez         (IDB)
*            Christian Volpe Martincus   (IDB & CESifo)
*
*   Project root:   D:\MNEs_Trade
*   Code root:      $code   = D:\MNEs_Trade\0_Code
*   Input root:     $input  = D:\MNEs_Trade\1_Input   (Customs / Gravity / Product / Country / Intermediate)
*   Output root:    $output = D:\MNEs_Trade\2_Output  (Graphs / Tables / Regressions)
*
*   PIPELINE
*   --------
*     01_setup.do                 Globals, packages, graph globals, FE ladders, programs
*     10_part0_build.do           PART 0 -- Data preparation (commented out; run once on first pass)
*     20_part1_determinants.do    PART 1 -- Determinants of MNE presence in trade
*     30_part2_effects.do         PART 2 -- Effects of MNE presence in trade
*     40_part3_summary.do         PART 3 -- Summary statistics
*
*   USAGE
*   -----
*     Run this file. By default it skips Part 0 (intermediates assumed present in $int).
*     To rebuild intermediates from raw, set $run_part0 = 1 below AND uncomment the /* */
*     block inside 10_part0_build.do.
*
**********************************************************************

clear all
set more off

* ---- Pipeline switches ----
global run_part0 = 0      // 1 to rebuild Part-0 intermediates (also uncomment in 10_part0_build.do)
global run_part1 = 1
global run_part2 = 1
global run_part3 = 1

* ---- Resolve code path (so this master can be run from anywhere) ----
global code "D:\MNEs_Trade\0_Code"

* ---- 1. Setup (globals, FE ladders, helper programs) ----
do "$code\01_setup.do"

* ---- 2. Part 0: Data preparation (optional rebuild) ----
if $run_part0 == 1 {
    do "$code\10_part0_build.do"
}

* ---- 3. Part 1: Determinants ----
if $run_part1 == 1 {
    do "$code\20_part1_determinants.do"
}

* ---- 4. Part 2: Effects ----
if $run_part2 == 1 {
    do "$code\30_part2_effects.do"
}

* ---- 5. Part 3: Summary statistics ----
if $run_part3 == 1 {
    do "$code\40_part3_summary.do"
}

display _newline ">>> 00_master.do complete <<<"
