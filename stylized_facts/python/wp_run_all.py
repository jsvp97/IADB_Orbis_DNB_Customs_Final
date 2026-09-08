"""
wp_run_all.py -- run the working-paper extensions in order.

Prerequisite (once): Stata  src/15_wp_extract_fdpy.do  ->  data/intermediate/wp/fdpy_base.dta
Then:  python wp_run_all.py            (all steps)
       python wp_run_all.py 1a 1cd     (a subset)

Steps: cube (parent cube + HS6 classifications) · 0 (Fact-4 reproductions) · 1a · 1b · 1cd · 1e · 1f · 2
Every step writes to output/wp/<scope>/ and prints the headline numbers to the console;
the console log is kept in output/logs/wp_run_all.log by the caller.
"""
from __future__ import annotations

import runpy
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
STEPS = {
    "cube": None,
    "0": "wp0_fact4_groups.py",
    "1a": "wp1a_figures_by_parent.py",
    "1b": "wp1b_complexity_variants.py",
    "1cd": "wp1cd_parent_destination.py",
    "1e": "wp1e_hq_affiliates.py",
    "1f": "wp1f_hs6_products.py",
    "2": "wp2_agro_sectors.py",
}

if __name__ == "__main__":
    want = sys.argv[1:] or list(STEPS)
    sys.path.insert(0, str(HERE))
    import wp_common as W
    t0 = time.time()
    if "cube" in want:
        W.build_classifications(); W.build_cube()
        print(f"[cube] done ({time.time() - t0:.0f}s)")
    for k in want:
        if k == "cube" or k not in STEPS:
            continue
        t1 = time.time()
        print(f"\n################ step {k}: {STEPS[k]} ################")
        runpy.run_path(str(HERE / STEPS[k]), run_name="__main__")
        print(f"[{k}] done ({time.time() - t1:.0f}s)")
    print(f"\n>>> all requested steps done ({(time.time() - t0) / 60:.1f} min)")
