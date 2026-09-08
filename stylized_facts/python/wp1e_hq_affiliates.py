"""
wp1e_hq_affiliates.py  --  Volpe item 1e (revision 3, 2026-09-08)
==================================================================

Facts 5 and 6 with the multinational categories decomposed in the order the coauthors asked
for: first FOREIGN vs DOMESTIC multinationals; then foreign MNEs split into those PRESENT AT
THE DESTINATION THROUGH THEIR HEADQUARTERS (the affiliate ships to the parent's country) and
those NOT present through their headquarters.

What the data can and cannot say: every matched exporter is an affiliate (a firm with a global
ultimate owner different from itself), so "the exporter is the HQ" is not identifiable; presence
of the group at the destination is. "MNE cantidad": counts of groups vs counts of affiliates.

Logs are plain logs: ln(count) is missing when the count is zero and the cell drops out of
that column (no ln(1+x)).

Part A -- origin x destination x HS6 x year cells (every scope):
  Regressions/reg_wp0_table1_repro.tex   Table 1 of the note reproduced (intensive + extensive margins)
  Regressions/reg_wp1e_counts.tex        intensive margin: ln # MNE -> ln # foreign + ln # domestic
                                         -> ln # foreign through HQ + ln # foreign not through HQ + ln # domestic
  Regressions/reg_wp1e_extensive.tex     the same decomposition on the extensive margin (presence dummies)
  Regressions/reg_wp1e_groups.tex        ln # groups vs ln # affiliates
  Tables/tab_wp1e_presence_shares.tex    foreign-MNE value by presence type, by origin
  Tables/tab_wp1e_groups_vs_affiliates.tex

Part B -- firm x destination x HS6 x year distance regressions (every scope):
  Regressions/reg_wp0_table2_repro.tex   Table 2 of the note reproduced
  Regressions/reg_wp1e_distance_hq.tex   ln dist x {foreign, domestic} -> {foreign through HQ, foreign not through HQ, domestic}

Estimator: pyfixest (Rust demeaner), FE ladders and origin-destination clustering as in the note.
"""
from __future__ import annotations

import gc
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_common as W  # noqa: E402

SCOPES = W.SCOPES_ALL
RUN_PART_B = True
MIN_CELLS = 2000
MIN_OBS = 500     # a regression with fewer usable observations is left blank (the Rust demeaner aborts on degenerate designs)


def ln(x: pd.Series) -> np.ndarray:
    return np.where(x > 0, np.log(x.where(x > 0)), np.nan)


# ---------------------------------------------------------------------
# Part A: ODPY cells
# ---------------------------------------------------------------------
def odpy_cells(d: pd.DataFrame) -> pd.DataFrame:
    m = W.matched_flag(d).astype(bool)
    ext = d["owner_type"].isin(["ext", "ext_unknown"]) if W.CONVENTION == "sf" else (d["owner_type"] == "ext")
    dom = d["owner_type"] == "dom"
    d = d.assign(
        n_mne=d["n_firms"] * m, n_grp=d["n_groups"] * m, n_ext=d["n_firms"] * ext, n_dom=d["n_firms"] * dom,
        n_ext_hq=d["n_hqdest"] * ext, n_ext_aff=np.clip(d["n_affpres"] - d["n_hqdest"], 0, None) * ext,
        v_mne=d["val_total"], v_ext=d["val_ext"], v_dom=d["val_dom"],
        v_hqdest=d["v_hqdest"] * ext, v_affpres=np.clip(d["v_affpres"] - d["v_hqdest"], 0, None) * ext,
    )
    keys = ["country_orig", "country_dest", "hs07_6d", "year"]
    g = d.groupby(keys, as_index=False).agg(
        total_value=("value", "sum"), v_mne=("v_mne", "sum"), v_ext=("v_ext", "sum"), v_dom=("v_dom", "sum"),
        v_hqdest=("v_hqdest", "sum"), v_affpres=("v_affpres", "sum"),
        n_firms=("n_firms", "sum"), n_mne=("n_mne", "sum"), n_grp=("n_grp", "sum"), n_ext=("n_ext", "sum"),
        n_dom=("n_dom", "sum"), n_ext_hq=("n_ext_hq", "sum"), n_ext_aff=("n_ext_aff", "sum"))
    g["n_grp"] = np.minimum(g["n_grp"], g["n_mne"])
    g["n_ext_nothq"] = np.clip(g["n_ext"] - g["n_ext_hq"], 0, None)
    g["nonmne_value"] = np.clip(g["total_value"] - g["v_mne"], 0, None)
    g["ln_total"] = np.log(g["total_value"])
    g["ln_nonmne"] = ln(g["nonmne_value"])
    for c in ("n_mne", "n_grp", "n_ext", "n_dom", "n_ext_hq", "n_ext_nothq"):
        g[f"ln_{c}"] = ln(g[c])
        g[f"any_{c}"] = (g[c] > 0).astype(float)
    g["ln_aff_per_grp"] = np.where(g["n_grp"] > 0, np.log((g["n_mne"] / g["n_grp"].replace(0, np.nan))), np.nan)
    g["year"] = g["year"].astype(int)
    g["ot"] = g["country_orig"] + "_" + g["year"].astype(str)
    g["dt"] = g["country_dest"] + "_" + g["year"].astype(str)
    g["od"] = g["country_orig"] + "_" + g["country_dest"]
    g["odp"] = g["od"] + "_" + g["hs07_6d"]
    g["ody"] = g["od"] + "_" + g["year"].astype(str)
    return g


FE_COMPONENTS = {
    "O": ("Origin FE", "country_orig"), "D": ("Destination FE", "country_dest"), "P": ("Product FE", "hs07_6d"),
    "Y": ("Year FE", "year"), "OY": (r"Origin $\times$ year FE", "ot"), "DY": (r"Destination $\times$ year FE", "dt"),
    "ODP": (r"Origin $\times$ dest.\ $\times$ product FE", "odp"), "ODY": (r"Origin $\times$ dest.\ $\times$ year FE", "ody"),
}
FE_ORDER = ["O", "D", "P", "Y", "OY", "DY", "ODP", "ODY"]
PANELS = [(r"Panel A: all exports ($\ln$)", "ln_total"), (r"Panel B: non-MNE exports ($\ln$)", "ln_nonmne")]
LAB = {
    "ln_n_mne": r"$\ln$(\# MNE firms)", "ln_n_ext": r"$\ln$(\# foreign MNEs)", "ln_n_dom": r"$\ln$(\# domestic MNEs)",
    "ln_n_ext_hq": r"$\ln$(\# foreign MNEs present through HQ)", "ln_n_ext_nothq": r"$\ln$(\# foreign MNEs not present through HQ)",
    "any_n_mne": "Any MNE present", "any_n_ext": "Any foreign MNE", "any_n_dom": "Any domestic MNE",
    "any_n_ext_hq": "Any foreign MNE present through HQ", "any_n_ext_nothq": "Any foreign MNE not present through HQ",
    "ln_n_grp": r"$\ln$(\# MNE groups)", "ln_aff_per_grp": r"$\ln$(affiliates per group)",
}
FE_A, FE_B = ["OY", "DY", "P"], ["ODP", "ODY"]


def run_panel_table(df, columns, panels, coef_rows, cluster, out: Path, note: str, col_groups=None):
    """sf4_presence.run_panel_table logic (CRV1 cluster, FE tick rows), Rust demeaner."""
    res = {}
    for pi, (plab, dep) in enumerate(panels):
        for ci, (tag, fe_keys, regs) in enumerate(columns):
            fe = " + ".join(FE_COMPONENTS[k][1] for k in fe_keys)
            dd = df.dropna(subset=[dep] + regs)
            t0 = time.time()
            if len(dd) < MIN_OBS:
                res[(pi, ci)] = {"cells": {}, "n": len(dd)}; print(f"   {plab[:8]:8s} {tag} N={len(dd)} < {MIN_OBS}: not estimated"); continue
            try:
                m = W.feols(f"{dep} ~ {' + '.join(regs)}" + (f" | {fe}" if fe else ""), data=dd, vcov={"CRV1": cluster})
                b, se, p = m.coef(), m.se(), m.pvalue()
                res[(pi, ci)] = {"cells": {v: (float(b[v]), float(se[v]), float(p[v])) for v in regs if v in b.index}, "n": int(m._N)}
                print(f"   {plab[:8]:8s} {tag} N={int(m._N):>9,} " + "  ".join(f"{v}:{float(b[v]):+.3f}{W.stars(float(p[v]))}" for v in regs if v in b.index)
                      + f"  ({time.time() - t0:.0f}s)")
                del m, b, se, p; gc.collect()
            except Exception as e:  # noqa: BLE001  (tiny scopes)
                res[(pi, ci)] = {"cells": {}, "n": 0}; print(f"   {plab[:8]:8s} {tag} FAILED: {str(e)[:80]}")
    ncols = len(columns)
    fe_used = [k for k in FE_ORDER if any(k in c[1] for c in columns)]
    lines = [rf"\begin{{tabular}}{{l{'c' * ncols}}} \hline"]
    if col_groups:
        lines.append(" & " + " & ".join(rf"\multicolumn{{{n}}}{{c}}{{{lab}}}" for lab, n in col_groups) + r" \\")
    lines.append(" & " + " & ".join(c[0] for c in columns) + r" \\ \hline")
    for pi, (plab, dep) in enumerate(panels):
        if pi: lines.append(r"\midrule")
        lines.append(rf"\multicolumn{{{ncols + 1}}}{{l}}{{\textit{{{plab}}}}} \\")
        for rlab, v in coef_rows:
            if not any(v in res[(pi, ci)]["cells"] for ci in range(ncols)):
                continue
            rb, rse = [], []
            for ci in range(ncols):
                if v in res[(pi, ci)]["cells"]:
                    bb, ss, pp = res[(pi, ci)]["cells"][v]; rb.append(f"{bb:.4f}{W.stars(pp)}"); rse.append(f"({ss:.4f})")
                else:
                    rb.append(""); rse.append("")
            lines.append(f"{rlab} & " + " & ".join(rb) + r" \\"); lines.append(" & " + " & ".join(rse) + r" \\")
    lines.append(r"\hline")
    for k in fe_used:
        lines.append(f"{FE_COMPONENTS[k][0]} & " + " & ".join(r"$\checkmark$" if k in columns[ci][1] else "" for ci in range(ncols)) + r" \\")
    for pi, (plab, dep) in enumerate(panels):
        short = plab.split(":")[1].split("(")[0].strip() if ":" in plab else plab
        lines.append(f"Observations ({short}) & " + " & ".join(f"{res[(pi, ci)]['n']:,}" for ci in range(ncols)) + r" \\")
    lines += [r"\hline", rf"\multicolumn{{{ncols + 1}}}{{p{{0.95\textwidth}}}}{{\footnotesize {note} SE clustered at origin-destination. *** p$<$0.01, ** p$<$0.05, * p$<$0.1}} \\", r"\end{tabular}"]
    W.write_tex(lines, out)
    return res


def part_a(cube: pd.DataFrame, scope: str) -> None:
    G, T, R = W.outdirs(scope)
    d = W.scope_filter(W.mne_flags(cube), scope)
    d = d[d["value"] > 0]
    g = odpy_cells(d)
    print(f"\n=== Part A, scope {scope}: {len(g):,} ODPY cells; any MNE {g['any_n_mne'].mean():.0%}")
    if len(g) < MIN_CELLS:
        print("   too few cells; skipped"); return

    # descriptive: foreign-MNE value by presence type, by origin ------------------------------------
    by_o = g.groupby("country_orig").agg(v_ext=("v_ext", "sum"), v_hq=("v_hqdest", "sum"), v_aff=("v_affpres", "sum"), v_mne=("v_mne", "sum"), v_dom=("v_dom", "sum"))
    tot = by_o.sum(); tot.name = "All"; by_o = pd.concat([by_o, tot.to_frame().T])
    lines = [r"\begin{tabular}{lrrrrr}", r"\toprule",
             r"Origin & MNE value (\$bn) & of which domestic (\%) & Foreign-MNE value (\$bn) & \multicolumn{2}{c}{\% of foreign-MNE value: group present at destination} \\",
             r" & & & & through headquarters & not through HQ (of which via another affiliate) \\", r"\midrule"]
    for o, r in by_o.iterrows():
        v = r["v_ext"]; hq = 100 * r["v_hq"] / v if v else np.nan; af = 100 * r["v_aff"] / v if v else np.nan
        if o == "All": lines.append(r"\midrule")
        lines.append(f"{o} & {r['v_mne'] / 1e9:,.1f} & {100 * r['v_dom'] / r['v_mne']:.1f} & {v / 1e9:,.1f} & {hq:.1f} & {100 - hq:.1f} ({af:.1f}) \\\\")
    lines += [r"\bottomrule",
              r"\multicolumn{6}{p{0.95\textwidth}}{\footnotesize `Through headquarters': the affiliate ships to its parent's country. `Not through HQ': every other destination; in parentheses the part where the group has another affiliate in the destination (Orbis/D\&B roster). Pooled 2006--2022.}} \\",
              r"\end{tabular}"]
    W.write_tex(lines, T / "tab_wp1e_presence_shares.tex")
    a = by_o.loc["All"]
    print(f"   foreign-MNE value: {100 * a['v_hq'] / a['v_ext']:.1f}% through HQ; {100 * a['v_aff'] / a['v_ext']:.1f}% via another affiliate; domestic = {100 * a['v_dom'] / a['v_mne']:.1f}% of MNE value")

    sub = g[g["n_mne"] > 0]
    ratio = sub["n_mne"].sum() / sub["n_grp"].sum(); vw = np.average(sub["n_mne"] / sub["n_grp"], weights=sub["total_value"]); multi = (sub["n_mne"] > sub["n_grp"]).mean()
    lines = [r"\begin{tabular}{lr}", r"\toprule", r"Origin-destination-product-year cells with $\geq 1$ MNE & \\", r"\midrule",
             f"Cells & {len(sub):,} \\\\", f"MNE affiliates per cell (mean) & {sub['n_mne'].mean():.2f} \\\\", f"MNE groups per cell (mean) & {sub['n_grp'].mean():.2f} \\\\",
             f"Affiliates per group, pooled & {ratio:.2f} \\\\", f"Affiliates per group, value-weighted mean & {vw:.2f} \\\\",
             f"Cells where one group exports through $>1$ affiliate (\\%) & {100 * multi:.1f} \\\\", r"\bottomrule",
             r"\multicolumn{2}{p{0.8\textwidth}}{\footnotesize Group = ultimate parent (Orbis GUO id or D\&B global ultimate; parent name when the id is missing).}} \\", r"\end{tabular}"]
    W.write_tex(lines, T / "tab_wp1e_groups_vs_affiliates.tex")

    # (0) Table 1 of the note, reproduced ------------------------------------------------------------------
    run_panel_table(g, [("(1)", ["O", "D", "Y", "P"], ["ln_n_mne"]), ("(2)", FE_A, ["ln_n_mne"]), ("(3)", FE_B, ["ln_n_mne"]),
                        ("(1)", ["O", "D", "Y", "P"], ["any_n_mne"]), ("(2)", FE_A, ["any_n_mne"]), ("(3)", FE_B, ["any_n_mne"])],
                    PANELS, [(LAB["ln_n_mne"], "ln_n_mne"), (LAB["any_n_mne"], "any_n_mne")], "od", R / "reg_wp0_table1_repro.tex",
                    "Origin-destination-product-year cells; dep.\\ var.\\ $\\ln$ exports. Intensive margin: $\\ln$ number of MNE firms (cells with $\\geq 1$ MNE); extensive margin: indicator for any MNE present. Reproduction of the note's Table 1 on the current base.",
                    col_groups=[(r"Intensive: $\ln$(\# MNE firms)", 3), ("Extensive: any MNE present", 3)])

    # (1) intensive margin, decomposed --------------------------------------------------------------------
    DEC1, DEC2 = ["ln_n_ext", "ln_n_dom"], ["ln_n_ext_hq", "ln_n_ext_nothq", "ln_n_dom"]
    ROWS = [(LAB[v], v) for v in ("ln_n_mne", "ln_n_ext", "ln_n_ext_hq", "ln_n_ext_nothq", "ln_n_dom")]
    run_panel_table(g, [("(1)", FE_A, ["ln_n_mne"]), ("(2)", FE_B, ["ln_n_mne"]), ("(3)", FE_A, DEC1), ("(4)", FE_B, DEC1), ("(5)", FE_A, DEC2), ("(6)", FE_B, DEC2)],
                    PANELS, ROWS, "od", R / "reg_wp1e_counts.tex",
                    "Origin-destination-product-year cells; dep.\\ var.\\ $\\ln$ exports. Intensive margin: plain logs of the counts, so each column uses the cells where every count entering it is positive (no $\\ln(1+x)$). (1)--(2) all MNEs; (3)--(4) foreign vs domestic; (5)--(6) foreign split by whether the group is present at the destination through its headquarters (the parent's country).",
                    col_groups=[("All MNEs", 2), ("Foreign / domestic", 2), ("Foreign through HQ / not through HQ / domestic", 2)])

    # (2) extensive margin, decomposed --------------------------------------------------------------------
    EX1, EX2 = ["any_n_ext", "any_n_dom"], ["any_n_ext_hq", "any_n_ext_nothq", "any_n_dom"]
    ROWS_E = [(LAB[v], v) for v in ("any_n_mne", "any_n_ext", "any_n_ext_hq", "any_n_ext_nothq", "any_n_dom")]
    run_panel_table(g, [("(1)", FE_A, ["any_n_mne"]), ("(2)", FE_B, ["any_n_mne"]), ("(3)", FE_A, EX1), ("(4)", FE_B, EX1), ("(5)", FE_A, EX2), ("(6)", FE_B, EX2)],
                    PANELS, ROWS_E, "od", R / "reg_wp1e_extensive.tex",
                    "Origin-destination-product-year cells; dep.\\ var.\\ $\\ln$ exports. Extensive margin: indicators for the presence of at least one MNE of each type in the cell; all cells.",
                    col_groups=[("All MNEs", 2), ("Foreign / domestic", 2), ("Foreign through HQ / not through HQ / domestic", 2)])

    # (3) groups vs affiliates ---------------------------------------------------------------------------------
    run_panel_table(sub, [("(1)", FE_A, ["ln_n_mne"]), ("(2)", FE_A, ["ln_n_grp"]), ("(3)", FE_A, ["ln_n_grp", "ln_aff_per_grp"]),
                          ("(4)", FE_B, ["ln_n_mne"]), ("(5)", FE_B, ["ln_n_grp"]), ("(6)", FE_B, ["ln_n_grp", "ln_aff_per_grp"])],
                    PANELS, [(LAB["ln_n_mne"], "ln_n_mne"), (LAB["ln_n_grp"], "ln_n_grp"), (LAB["ln_aff_per_grp"], "ln_aff_per_grp")], "od", R / "reg_wp1e_groups.tex",
                    "Cells with at least one MNE; dep.\\ var.\\ $\\ln$ exports. `MNE firms' counts matched exporting affiliates; `MNE groups' counts distinct ultimate parents.",
                    col_groups=[(r"OxYr + DxYr + P FE", 3), (r"ODP + ODY FE", 3)])


# ---------------------------------------------------------------------
# Part B: firm-level distance regressions
# ---------------------------------------------------------------------
def load_firm_panel() -> pd.DataFrame:
    f = W.load_fdpy()
    f = f[(~f["country_orig"].isin(W.excluded_origins())) & (f["value_fob"] > 0)].copy()
    keys = ["country_orig", "Tax_ID", "country_dest", "hs07_6d", "year"]
    mcol = "m_dnb" if W.CONVENTION == "sf" else "m_fr"
    f = f.groupby(keys, as_index=False, dropna=False).agg(value=("value_fob", "sum"), m=(mcol, "max"), parent=("iso3_parent", "first"), aff=("has_aff_in_dest", "max"))
    grav = W.load_gravity(("iso3_o", "iso3_d", "dist")).dropna(subset=["dist"]).groupby(["iso3_o", "iso3_d"], as_index=False).agg(dist=("dist", "first"))
    f = f.merge(grav, left_on=["country_orig", "country_dest"], right_on=["iso3_o", "iso3_d"], how="left")
    f = f[f["dist"].notna() & (f["dist"] > 0)].copy()
    f["ln_dist"] = np.log(f["dist"].astype(float)); f["ln_exports"] = np.log(f["value"].astype(float))
    f["year"] = f["year"].astype(int); f["hs2"] = f["hs07_6d"].str[:2]
    f["ot"] = f["country_orig"] + "_" + f["year"].astype(str); f["dt"] = f["country_dest"] + "_" + f["year"].astype(str)
    f["od"] = f["country_orig"] + "_" + f["country_dest"]
    m = f["m"].astype(bool); par = f["parent"].fillna("")
    dom = m & (par == f["country_orig"])
    ext = (m & ~dom) if W.CONVENTION == "sf" else (m & (par != "") & (par != f["country_orig"]))
    hq = ext & (par == f["country_dest"])
    anypres = m & ((f["aff"] == 1) | (par == f["country_dest"]))
    groups = {"g_mne": m, "g_anypres": anypres, "g_anynotpres": m & ~anypres, "g_ext": ext, "g_dom": dom, "g_ext_hq": hq, "g_ext_nothq": ext & ~hq}
    for k, s in groups.items():
        f[k + "_Xd"] = s.astype(float) * f["ln_dist"]
    print(f"   firm panel: {len(f):,} rows; value shares: " + ", ".join(f"{k}={f.loc[s, 'value'].sum() / f['value'].sum():.3f}" for k, s in groups.items()))
    return f


GLAB = {"g_mne": "MNE", "g_anypres": "MNE, present", "g_anynotpres": "MNE, not present", "g_ext": "foreign MNE", "g_dom": "domestic MNE",
        "g_ext_hq": "foreign MNE, present through HQ", "g_ext_nothq": "foreign MNE, not present through HQ"}
FE_D = {"ODYP": ("O + D + Yr + P", "country_orig + country_dest + year + hs07_6d", {"Origin FE", "Destination FE", "Year FE", "Product FE"}),
        "OYDYP": ("OxYr + DxYr + P", "ot + dt + hs07_6d", {r"Origin $\times$ year FE", r"Destination $\times$ year FE", "Product FE"})}
FE_ORDER_D = ["Origin FE", "Destination FE", "Year FE", r"Origin $\times$ year FE", r"Destination $\times$ year FE", "Product FE"]


def distance_table(f, columns, row_order, out_path: Path, tnote: str) -> None:
    cols = []
    for tag, fk, gs in columns:
        t0 = time.time()
        if len(f) < MIN_OBS or any(f[g + "_Xd"].ne(0).sum() < 30 for g in gs):
            cols.append({"tag": tag, "fk": fk, "rows": set(), "cells": {}, "n": len(f)}); print(f"   {tag}: too few observations in a group; not estimated"); continue
        try:
            mdl = W.feols(f"ln_exports ~ ln_dist + {' + '.join(g + '_Xd' for g in gs)} | {FE_D[fk][1]}", data=f, vcov={"CRV1": "od"})
            b, se, p = mdl.coef(), mdl.se(), mdl.pvalue()
            cells = {g: (float(b[g + "_Xd"]), float(se[g + "_Xd"]), float(p[g + "_Xd"])) for g in gs if g + "_Xd" in b.index}
            cells["ln_dist"] = (float(b["ln_dist"]), float(se["ln_dist"]), float(p["ln_dist"]))
            cols.append({"tag": tag, "fk": fk, "rows": set(cells), "cells": cells, "n": int(mdl._N)})
            print(f"   {tag} N={int(mdl._N):,} base {cells['ln_dist'][0]:+.4f} " + " ".join(f"{GLAB[g]}: {cells[g][0]:+.4f}{W.stars(cells[g][2])}" for g in gs if g in cells) + f" ({time.time() - t0:.0f}s)")
            del mdl, b, se, p; gc.collect()
        except Exception as e:  # noqa: BLE001
            cols.append({"tag": tag, "fk": fk, "rows": set(), "cells": {}, "n": 0}); print(f"   {tag} FAILED: {str(e)[:80]}")
    ncols = len(cols)
    ROWLAB = {"ln_dist": r"$\ln$ distance", **{g: rf"$\ln$ distance $\times$ {GLAB[g]}" for g in row_order}}
    lines = [rf"\begin{{tabular}}{{l{'c' * ncols}}} \hline", r"Dep.\ var.: $\ln$ exports & " + " & ".join(c["tag"] for c in cols) + r" \\ \hline"]
    for r in ["ln_dist"] + row_order:
        if not any(r in c["rows"] for c in cols):
            continue
        rb, rse = [], []
        for c in cols:
            if r in c["rows"]:
                bb, ss, pp = c["cells"][r]; rb.append(f"{bb:.4f}{W.stars(pp)}"); rse.append(f"({ss:.4f})")
            else:
                rb.append(""); rse.append("")
        lines.append(f"{ROWLAB[r]} & " + " & ".join(rb) + r" \\"); lines.append(" & " + " & ".join(rse) + r" \\")
    lines.append(r"\hline")
    for fe in FE_ORDER_D:
        pres = [fe in FE_D[c["fk"]][2] for c in cols]
        if any(pres):
            lines.append(f"{fe} & " + " & ".join(r"$\checkmark$" if x else "" for x in pres) + r" \\")
    lines += [r"\hline", "Observations & " + " & ".join(f"{c['n']:,}" for c in cols) + r" \\", r"\hline",
              rf"\multicolumn{{{ncols + 1}}}{{p{{0.95\textwidth}}}}{{\footnotesize Distance and firm exports. Firm$\times$origin$\times$destination$\times$product$\times$year; non-MNE flows the omitted base. "
              + tnote + r" SE clustered at origin-destination. *** p$<$0.01, ** p$<$0.05, * p$<$0.1}} \\", r"\end{tabular}"]
    W.write_tex(lines, out_path)


def part_b(f_all: pd.DataFrame, scope: str) -> None:
    G, T, R = W.outdirs(scope)
    f = f_all if scope == "all" else f_all[W.sector4(f_all["hs2"]) == W.SECTOR_OF_SCOPE[scope]]
    print(f"\n=== Part B, scope {scope}: {len(f):,} firm-dest-product-year rows")
    if len(f) < 20000:
        print("   too few rows; skipped"); return
    distance_table(f, [("(1)", "ODYP", ["g_mne"]), ("(2)", "OYDYP", ["g_mne"]), ("(3)", "ODYP", ["g_anypres", "g_anynotpres"]), ("(4)", "OYDYP", ["g_anypres", "g_anynotpres"])],
                   ["g_mne", "g_anypres", "g_anynotpres"], R / "reg_wp0_table2_repro.tex",
                   "Reproduction of the note's Table 2 on the current base: multinationals (foreign or domestic) split by presence at the destination (the group has an affiliate there, or the destination is the parent's country).")
    distance_table(f, [("(1)", "ODYP", ["g_ext", "g_dom"]), ("(2)", "OYDYP", ["g_ext", "g_dom"]), ("(3)", "ODYP", ["g_ext_hq", "g_ext_nothq", "g_dom"]), ("(4)", "OYDYP", ["g_ext_hq", "g_ext_nothq", "g_dom"])],
                   ["g_ext", "g_ext_hq", "g_ext_nothq", "g_dom"], R / "reg_wp1e_distance_hq.tex",
                   "(1)--(2) foreign vs domestic multinationals; (3)--(4) foreign MNEs split by whether the group is present at the destination through its headquarters (the parent's country) or not.")


def main():
    cube = W.build_cube()
    for scope in SCOPES:
        part_a(cube, scope)
    if RUN_PART_B:
        f = load_firm_panel()
        for scope in SCOPES:
            part_b(f, scope)
    print("\n>>> wp1e done")


if __name__ == "__main__":
    main()
