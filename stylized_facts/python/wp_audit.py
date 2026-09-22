"""
wp_audit.py  --  cross-exhibit consistency audit (revision 8, 2026-09-21)
=========================================================================

Recomputes from the cube every share that appears in more than one exhibit of the working-paper draft and compares
it with the number written in the LaTeX fragments, and checks the identities that link exhibits with different
denominators:

  * US-parent share of TOTAL exports (10.0 %)  = USA bar of fig_wp1a_parent_share_total = column (2) of tab_wp3_us_three_shares
                                                = 'All goods / All' of tab_wp3_us_share_origin_sector
  * share of US-parent exports going HOME (22.3 %) = USA diagonal of tab_wp1c_parent_x_parentdest_rowpct
                                                = USA row of tab_wp1c_country_rowpct (USA column) = fig_wp1d_home_share_by_parent
  * column (3) = column (2) x home share / 100 (2.2 = 10.0 x 0.223) in tab_wp3_us_three_shares
  * column (4) of tab_wp3_us_three_shares = US-parent share of exports TO the USA = tab_wp3_to_usa_carriers (by origin)
                                          = 'All goods' row of tab_wp3_to_usa_carriers_by_sector = USA row of tab_wp3_dest_carriers
  * Rauch two-class table = value-weighted merge of the three-class table; BEC rows = the three classes only
  * destination-carrier rows sum to 100; EU-27 is the strict 27-member list
  * Fact 5 / 6 summaries reproduce the full regression fragments to the digit

Run after wp3:  python wp_audit.py   (step `audit` of wp_run_all.py). Exit code 1 if any check fails.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_common as W  # noqa: E402
import wp3_usa_destinations as X  # noqa: E402

OUT = W.WP_OUT
FAILS: list[str] = []


def cells(path: Path, first_col: str) -> list | None:
    """Numeric cells of the first table row whose first cell equals `first_col` (NaN for text cells)."""
    for l in path.read_text(encoding="utf-8").split("\n"):
        if l.startswith(("\\", "%")) or "&" not in l:
            continue
        parts = [c.strip() for c in re.split(r"(?<!\\)&", l.replace("\\\\", ""))]
        if parts[0] == first_col:
            out = []
            for c in parts[1:]:
                c2 = re.sub(r"\\%|\*+|\\\$", "", c).replace(",", "").strip()
                out.append(float(c2) if re.fullmatch(r"-?\d*\.?\d+", c2) else np.nan)
            return out
    return None


def frag_cell(path: Path, row: str, j: int) -> str | None:
    for l in path.read_text(encoding="utf-8").split("\n"):
        parts = [c.strip() for c in re.split(r"(?<!\\)&", l.replace("\\\\", ""))]
        if parts[0] == row and len(parts) > j + 1:
            return parts[1 + j]
    return None


def check(name: str, got, exp, tol: float = 0.06) -> None:
    ok = got is not None and ((np.isnan(got) and np.isnan(exp)) or abs(got - exp) <= tol)
    print(f"  {'OK  ' if ok else 'FAIL'} {name}: table {got if got is None else round(got, 4)} vs recomputed {exp:.4f}")
    if not ok:
        FAILS.append(name)


def main() -> int:
    cube = W.build_cube(); d = W.mne_flags(cube); d = d[d["value"] > 0].copy(); d["sector4"] = W.sector4(d["hs2"])
    cls = W.build_classifications()
    tot = d["value"].sum(); us = (d["owner_type"] == "ext") & (d["iso3_parent"] == "USA"); to_us = d["country_dest"] == "USA"
    ext = d["owner_type"].isin(["ext", "ext_unknown"]); dom = d["owner_type"] == "dom"; kn = d["owner_type"] == "ext"
    ny = d.groupby("country_orig")["year"].nunique()
    exp_yr = sum(d.loc[d["country_orig"] == o, "value"].sum() / ny[o] for o in ny.index) / 1e9
    T = lambda sc, name: OUT / sc / "Tables" / name  # noqa: E731
    print(f"== all goods: pooled ${tot / 1e9:,.1f}bn, annual average ${exp_yr:,.1f}bn/yr; years by origin {ny.to_dict()}")

    print("\n== Figure 1 numbers vs cube")
    for o in sorted(ny.index):
        c = cells(T("all", "tab_wp0_fig1_origin.tex"), o); sel = d["country_orig"] == o
        check(f"{o} foreign share", c[0], d.loc[sel & ext, "value"].sum() / d.loc[sel, "value"].sum(), 0.0006)
        check(f"{o} value $bn/yr", c[3], d.loc[sel, "value_yr"].sum() / 1e9, 0.06)
    c = cells(T("all", "tab_wp0_fig1_origin.tex"), "All")
    check("All foreign share", c[0], d.loc[ext, "value"].sum() / tot, 0.0006); check("All value $bn/yr", c[3], exp_yr, 0.06)
    c = cells(T("sectors", "tab_wp2_four_sectors.tex"), "All"); check("four sectors All $bn/yr", c[0], exp_yr, 0.06)

    print("\n== The US identities (one denominator per column)")
    t3 = T("all", "tab_wp3_us_three_shares.tex"); c3 = cells(t3, "All")
    fall = ext; scale_all = d.loc[fall, "value"].sum() / d.loc[kn, "value"].sum()                # parent rule, whole sample
    scale_usa = d.loc[fall & to_us, "value"].sum() / d.loc[kn & to_us, "value"].sum()            # parent rule, exports to the USA
    us_share_total = 100 * d.loc[us, "value"].sum() / tot * scale_all
    home_share_us = 100 * d.loc[us & to_us, "value"].sum() / d.loc[us, "value"].sum()
    check("three-shares (1) % to USA", c3[0], 100 * d.loc[to_us, "value"].sum() / tot)
    check("three-shares (2) % by US MNEs (parent rule)", c3[1], us_share_total)
    check("three-shares (4) = US-parent share of exports to USA (parent rule)", c3[3], 100 * d.loc[us & to_us, "value"].sum() / d.loc[to_us, "value"].sum() * scale_usa)
    check("identity (3) = (4) x (1)", c3[2], c3[3] * c3[0] / 100, 0.06)
    pt = cells(T("all", "tab_wp1a_parent_share_total.tex"), "USA"); check("parent-share-total USA == three-shares (2)", pt[0], c3[1], 0.06)
    f4 = cells(T("all", "tab_wp1a_parent_share.tex"), "USA"); f1 = cells(T("all", "tab_wp0_fig1_origin.tex"), "All")
    check("Figure 4 USA share x Figure 1 foreign share == three-shares (2)  [parent rule]", f4[0] * f1[0], c3[1], 0.06)   # f1[0] is a fraction
    check("Figure 4 USA share == 23.3 (Ignacio, recorded parents)", f4[0], 100 * d.loc[us, "value"].sum() / d.loc[kn, "value"].sum(), 0.06)
    ox = cells(T("sectors", "tab_wp3_us_share_origin_sector.tex"), "All"); check("origin x sector All goods == three-shares (2)", ox[0], c3[1], 0.06)
    pxp = T("all", "tab_wp1c_parent_x_parentdest_rowpct.tex")
    hdr = [l for l in pxp.read_text(encoding="utf-8").split("\n") if l.startswith("Parent / Destination")][0]
    cols_ = [c.strip() for c in hdr.replace("\\\\", "").split("&")][1:]
    diag = cells(pxp, "USA")[cols_.index("USA")]; check("parent x parent-dest USA diagonal == home share", diag, home_share_us)
    rp = T("all", "tab_wp1c_country_rowpct.tex")
    hdr2 = [l for l in rp.read_text(encoding="utf-8").split("\n") if l.startswith("Parent / Destination")][0]
    cols2 = [c.strip() for c in hdr2.replace("\\\\", "").split("&")][1:]
    check("country rowpct USA->USA == home share", cells(rp, "USA")[cols2.index("USA")], home_share_us)
    hs = cells(T("sectors", "tab_wp3_home_share_by_parent_sectors.tex"), "USA"); check("home share by sector, all goods USA == home share", hs[0], home_share_us)
    tu = cells(T("sectors", "tab_wp3_to_usa_carriers_by_sector.tex"), "All goods"); check("to-USA by sector All goods == three-shares (4)", tu[1], c3[3], 0.06)
    dc = cells(T("all", "tab_wp3_dest_carriers.tex"), "USA"); check("dest table USA 'parent in destination' == three-shares (4)", dc[1], c3[3], 0.06)
    for o in sorted(ny.index):
        a = cells(t3, o); b = cells(T("all", "tab_wp3_to_usa_carriers.tex"), o)
        if a is not None and b is not None:
            check(f"{o}: three-shares (4) == to-USA carriers US-parent", a[3], b[1], 0.06)
            check(f"{o}: (3) == (4) x (1)", a[2], a[3] * a[0] / 100, 0.06)

    print("\n== destinations: rows sum to 100, strict EU-27")
    for mk in ("USA", "CHN", "EU-27", "BRA", "CAN"):
        c = cells(T("all", "tab_wp3_dest_carriers.tex"), mk)
        if c is not None:
            check(f"{mk}: shares sum to 100", sum(x for x in c[1:] if not np.isnan(x)), 100.0, 0.25)
    assert "GBR" not in X.EU27 and len(X.EU27) == 27, "EU27 must be the strict 27-member list"
    print("  OK   EU-27 strict (27 members, GBR excluded)")

    print("\n== Rauch and BEC")
    r3, r2 = T("all", "tab_wp1b_rauch.tex"), T("all", "tab_wp1b_rauch2.tex")
    ref, hom, nd = cells(r3, "Reference-priced"), cells(r3, "Homogeneous (exchange)"), cells(r2, "Non-differentiated")
    check("Rauch non-differentiated foreign = weighted merge of ref + hom", nd[0], (ref[0] * ref[4] + hom[0] * hom[4]) / (ref[4] + hom[4]), 0.002)
    rows = [re.split(r"(?<!\\)&", l)[0].strip() for l in T("all", "tab_wp1b_bec.tex").read_text(encoding="utf-8").split("\n") if "&" in l and not l.startswith("\\")]
    ok = rows[1:] == ["Intermediate", "Consumption", "Capital"]; print(f"  {'OK  ' if ok else 'FAIL'} BEC rows = three classes: {rows[1:]}")
    if not ok: FAILS.append("BEC rows")

    print("\n== OECD split adds up to the foreign share")
    for q in ("Q1", "Q3", "Q5"):
        a = cells(T("all", "tab_wp1a_pci_by_oecd.tex"), q); b = cells(T("all", "tab_wp1a_pci_by_parent.tex"), q)
        check(f"PCI {q}: OECD + non-OECD == foreign (by-parent table)", a[0] + a[1], b[-2] - b[-3], 0.002)

    print("\n== Fact 5 / 6 summaries reproduce the full fragments")
    pairs = [("reg_wp1e_counts.tex", r"$\ln$(\# foreign MNEs)", 2, "tab_wp3_fact5_summary.tex", r"\quad Number of foreign MNEs exporting the product to the destination ($\ln$)", 0),
             ("reg_wp1e_extensive.tex", "Any foreign MNE", 2, "tab_wp3_fact5ext_summary.tex", r"\quad At least one foreign MNE exports the product to the destination (0/1)", 0),
             ("reg_wp1e_distance_hq.tex", r"$\ln$ distance $\times$ foreign MNE", 0, "tab_wp3_fact6_summary.tex", r"\quad $\ln$ distance $\times$ foreign MNE", 0)]
    for frag, row, j, summ, srow, k in pairs:
        a = frag_cell(OUT / "all" / "Regressions" / frag, row, j); b = frag_cell(T("sectors", summ), srow, k)
        ok = a is not None and a == b; print(f"  {'OK  ' if ok else 'FAIL'} {summ}: {b} == {a}")
        if not ok: FAILS.append(summ)

    print("\n==== RESULT:", "ALL CHECKS PASSED" if not FAILS else f"{len(FAILS)} FAILED -> {FAILS}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
