"""
wp1e_hq_affiliates.py  --  Volpe item 1e
========================================

"What about the multinationals' HEADQUARTERS, not only their affiliates -- for the
affiliate regressions. Try MNE counts."

What the data can and cannot say (checked on the full base, 2026-09-07):
  * Every matched exporter is an AFFILIATE by construction: the match runs through the
    Orbis ownership links and the D&B global-ultimate field, so a matched firm always has a
    global ultimate owner different from itself (subsidiarybvdid == guo25 or DUNS ==
    global-ultimate DUNS never holds; 0 of 5.45 M rows). A LAC-headquartered group's HEAD
    company exporting from home is therefore in the UNMATCHED pool unless a corporate record
    lists it with a parent. "HQ exporters" cannot be separated from local firms with this
    base; the domestic-MNE category (parent in the exporting country) is the closest object:
    domestic affiliates of LAC-headquartered groups.
  * What IS identifiable is how the multinational is PRESENT AT THE DESTINATION: through
    its headquarters (the affiliate ships to the parent's country) or through another
    affiliate (Orbis/D&B roster: `has_aff_in_dest`), or not at all. The document's Table
    A.9 splits the distance regression this way; here the split is carried into the Fact-5
    presence regressions with COUNTS by presence type, and promoted to the main text.
  * "MNE cantidad": presence measured by the number of MULTINATIONAL GROUPS (distinct
    parents) in the market, not the number of affiliates -- one group often exports through
    several affiliates (the document's Figure 6 point). Both counts are reported.

Part A -- ODPY cells from the parent cube (scope all and agro):
  Tables/tab_wp1e_presence_shares.tex     foreign-MNE value by presence type, by origin
  Tables/tab_wp1e_groups_vs_affiliates.tex affiliates per group in the market cells
  Regressions/reg_wp1e_counts.tex         Fact-5 table, intensive margin by presence-type counts
  Regressions/reg_wp1e_groups.tex         Fact-5 table, ln(# groups) vs ln(# affiliates)

Part B -- firm-level distance regressions (Fact 6, Table 2 geometry), scope all:
  Regressions/reg_wp1e_distance_hq.tex    ln dist x {foreign: HQ-present / affiliate-present /
                                          not present} and {domestic: affiliate-present / not}

Same estimator (pyfixest), FE ladders, clustering (origin-destination) and table layout as
sf4_presence.py / sf5_distance.py.
"""
from __future__ import annotations

import gc
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyfixest as pf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_common as W  # noqa: E402

SCOPES = ["all", "agro"]
RUN_PART_B = True


# ---------------------------------------------------------------------
# Part A: ODPY cells with counts by presence type and by group
# ---------------------------------------------------------------------
def odpy_cells(d: pd.DataFrame) -> pd.DataFrame:
    m = W.matched_flag(d).astype(bool)
    ext = d["owner_type"].isin(["ext", "ext_unknown"]) if W.CONVENTION == "sf" else (d["owner_type"] == "ext")
    d = d.assign(
        n_mne=d["n_firms"] * m, n_grp=d["n_groups"] * m,
        n_ext=d["n_firms"] * ext, n_dom=d["n_firms"] * (d["owner_type"] == "dom"),
        n_hq_present=d["n_hqdest"] * ext,
        n_aff_present=np.clip(d["n_affpres"] - d["n_hqdest"], 0, None) * ext,
        n_dom_present=d["n_affpres"] * (d["owner_type"] == "dom"),
        v_mne=d["val_total"], v_ext=d["val_ext"], v_dom=d["val_dom"],
        v_hqdest=d["v_hqdest"] * ext, v_affpres=np.clip(d["v_affpres"] - d["v_hqdest"], 0, None) * ext,
    )
    keys = ["country_orig", "country_dest", "hs07_6d", "year"]
    g = d.groupby(keys, as_index=False).agg(
        total_value=("value", "sum"), v_mne=("v_mne", "sum"), v_ext=("v_ext", "sum"), v_dom=("v_dom", "sum"),
        v_hqdest=("v_hqdest", "sum"), v_affpres=("v_affpres", "sum"),
        n_firms=("n_firms", "sum"), n_mne=("n_mne", "sum"), n_grp=("n_grp", "sum"), n_ext=("n_ext", "sum"),
        n_dom=("n_dom", "sum"), n_hq_present=("n_hq_present", "sum"), n_aff_present=("n_aff_present", "sum"),
        n_dom_present=("n_dom_present", "sum"))
    # n_grp summed over parent rows over-counts a group present under two parent codes only in
    # pathological cases (same group id, different iso3_parent); cap at n_mne.
    g["n_grp"] = np.minimum(g["n_grp"], g["n_mne"])
    g["n_not_present"] = np.clip(g["n_ext"] - g["n_hq_present"] - g["n_aff_present"], 0, None)
    g["nonmne_value"] = np.clip(g["total_value"] - g["v_mne"], 0, None)
    g["ln_total"] = np.log(g["total_value"])
    g["ln_nonmne"] = np.where(g["nonmne_value"] > 0, np.log(g["nonmne_value"].clip(lower=1)), np.nan)
    g["ln_nmne"] = np.where(g["n_mne"] > 0, np.log(g["n_mne"].clip(lower=1)), np.nan)
    g["ln_ngrp"] = np.where(g["n_grp"] > 0, np.log(g["n_grp"].clip(lower=1)), np.nan)
    g["ln_aff_per_grp"] = np.where(g["n_grp"] > 0, np.log((g["n_mne"] / g["n_grp"].clip(lower=1)).clip(lower=1)), np.nan)
    for c in ("n_hq_present", "n_aff_present", "n_not_present", "n_dom"):
        g[f"l1_{c}"] = np.log1p(g[c])
    g["any_mne"] = (g["n_mne"] > 0).astype(float)
    g["year"] = g["year"].astype(int)
    g["ot"] = g["country_orig"] + "_" + g["year"].astype(str)
    g["dt"] = g["country_dest"] + "_" + g["year"].astype(str)
    g["od"] = g["country_orig"] + "_" + g["country_dest"]
    g["odp"] = g["od"] + "_" + g["hs07_6d"]
    g["ody"] = g["od"] + "_" + g["year"].astype(str)
    g["dpy"] = g["country_dest"] + "_" + g["hs07_6d"] + "_" + g["year"].astype(str)
    return g


FE_COMPONENTS = {
    "O": ("Origin FE", "country_orig"), "D": ("Destination FE", "country_dest"), "P": ("Product FE", "hs07_6d"),
    "Y": ("Year FE", "year"), "OY": (r"Origin $\times$ year FE", "ot"), "DY": (r"Destination $\times$ year FE", "dt"),
    "ODP": (r"Origin $\times$ dest.\ $\times$ product FE", "odp"), "ODY": (r"Origin $\times$ dest.\ $\times$ year FE", "ody"),
    "DPY": (r"Dest.\ $\times$ product $\times$ year FE", "dpy"),
}
FE_ORDER = ["O", "D", "P", "Y", "OY", "DY", "ODP", "ODY", "DPY"]


def run_panel_table(df, columns, panels, coef_rows, cluster, out: Path, note: str, col_groups=None):
    """Same logic as sf4_presence.run_panel_table (pyfixest, CRV1 cluster, FE as tick rows)."""
    res = {}
    for pi, (plab, dep) in enumerate(panels):
        for ci, (tag, fe_keys, regs) in enumerate(columns):
            fe = " + ".join(FE_COMPONENTS[k][1] for k in fe_keys)
            dd = df.dropna(subset=[dep] + regs)
            t0 = time.time()
            m = pf.feols(f"{dep} ~ {' + '.join(regs)}" + (f" | {fe}" if fe else ""), data=dd, vcov={"CRV1": cluster})
            b, se, p = m.coef(), m.se(), m.pvalue()
            res[(pi, ci)] = {"cells": {v: (float(b[v]), float(se[v]), float(p[v])) for v in regs if v in b.index}, "n": int(m._N)}
            print(f"   {plab[:8]:8s} {tag} N={int(m._N):>9,} " + "  ".join(f"{v}:{float(b[v]):+.3f}{W.stars(float(p[v]))}" for v in regs if v in b.index)
                  + f"  ({time.time() - t0:.0f}s)")
            del m, b, se, p; gc.collect()
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
                    bb, ss, pp = res[(pi, ci)]["cells"][v]
                    rb.append(f"{bb:.4f}{W.stars(pp)}"); rse.append(f"({ss:.4f})")
                else:
                    rb.append(""); rse.append("")
            lines.append(f"{rlab} & " + " & ".join(rb) + r" \\"); lines.append(" & " + " & ".join(rse) + r" \\")
    lines.append(r"\hline")
    for k in fe_used:
        lines.append(f"{FE_COMPONENTS[k][0]} & " + " & ".join(r"$\checkmark$" if k in columns[ci][1] else "" for ci in range(ncols)) + r" \\")
    for pi, (plab, dep) in enumerate(panels):
        short = plab.split(":")[1].split("(")[0].strip() if ":" in plab else plab
        lines.append(f"Observations ({short}) & " + " & ".join(f"{res[(pi, ci)]['n']:,}" for ci in range(ncols)) + r" \\")
    lines += [r"\hline", rf"\multicolumn{{{ncols + 1}}}{{p{{0.92\textwidth}}}}{{\footnotesize {note} SE clustered at origin-destination. *** p$<$0.01, ** p$<$0.05, * p$<$0.1}} \\", r"\end{tabular}"]
    W.write_tex(lines, out)
    return res


def part_a(cube: pd.DataFrame, scope: str) -> None:
    G, T, R = W.outdirs(scope)
    d = W.scope_filter(W.mne_flags(cube), scope)
    d = d[d["value"] > 0]
    g = odpy_cells(d)
    print(f"\n=== Part A, scope {scope}: {len(g):,} ODPY cells; any MNE {g['any_mne'].mean():.0%}")

    # descriptive: foreign-MNE value by presence type, by origin ------------------------------------
    by_o = g.groupby("country_orig").agg(v_ext=("v_ext", "sum"), v_hq=("v_hqdest", "sum"), v_aff=("v_affpres", "sum"), v_mne=("v_mne", "sum"))
    tot = by_o.sum(); tot.name = "All"; by_o = pd.concat([by_o, tot.to_frame().T])
    lines = [r"\begin{tabular}{lrrrr}", r"\toprule",
             r"Origin & Foreign-MNE value (\$bn) & \multicolumn{3}{c}{\% of foreign-MNE export value by the group's presence at the destination} \\",
             r" & & through headquarters & through another affiliate & not present \\", r"\midrule"]
    for o, r in by_o.iterrows():
        v = r["v_ext"]; hq = 100 * r["v_hq"] / v if v else np.nan; af = 100 * r["v_aff"] / v if v else np.nan
        if o == "All": lines.append(r"\midrule")
        lines.append(f"{o} & {v / 1e9:,.1f} & {hq:.1f} & {af:.1f} & {100 - hq - af:.1f} \\\\")
    lines += [r"\bottomrule",
              r"\multicolumn{5}{p{0.95\textwidth}}{\footnotesize `Through headquarters': the affiliate ships to its parent's country. `Through another affiliate': the group has an affiliate in the destination (Orbis/D\&B roster) that is not the parent. Pooled 2006--2022. Every matched exporter is itself an affiliate (see the script header), so an `exporter is the HQ' split is not available in this base.}} \\",
              r"\end{tabular}"]
    W.write_tex(lines, T / "tab_wp1e_presence_shares.tex")
    a = by_o.loc["All"]
    print(f"   foreign-MNE value: {100 * a['v_hq'] / a['v_ext']:.1f}% shipped to the HQ country, {100 * a['v_aff'] / a['v_ext']:.1f}% to destinations with another affiliate, "
          f"{100 - 100 * (a['v_hq'] + a['v_aff']) / a['v_ext']:.1f}% not present")

    # groups vs affiliates in the market cells ------------------------------------------------------
    sub = g[g["n_mne"] > 0]
    ratio = sub["n_mne"].sum() / sub["n_grp"].sum()
    dist = (sub["n_mne"] / sub["n_grp"]).describe(percentiles=[.5, .75, .9, .99])
    multi = (sub["n_mne"] > sub["n_grp"]).mean()
    vw = np.average(sub["n_mne"] / sub["n_grp"], weights=sub["total_value"])
    lines = [r"\begin{tabular}{lr}", r"\toprule", r"Origin-destination-product-year cells with $\geq 1$ MNE & \\", r"\midrule",
             f"Cells & {len(sub):,} \\\\", f"MNE affiliates per cell (mean) & {sub['n_mne'].mean():.2f} \\\\",
             f"MNE groups per cell (mean) & {sub['n_grp'].mean():.2f} \\\\", f"Affiliates per group, pooled & {ratio:.2f} \\\\",
             f"Affiliates per group, value-weighted mean & {vw:.2f} \\\\", f"Cells where one group exports through $>1$ affiliate (\\%) & {100 * multi:.1f} \\\\",
             f"Affiliates per group, p90 / p99 & {dist['90%']:.1f} / {dist['99%']:.1f} \\\\", r"\bottomrule",
             r"\multicolumn{2}{p{0.8\textwidth}}{\footnotesize Group = ultimate parent (Orbis GUO id or D\&B global ultimate; parent name when the id is missing).}} \\", r"\end{tabular}"]
    W.write_tex(lines, T / "tab_wp1e_groups_vs_affiliates.tex")
    print(f"   affiliates per group in MNE cells: {ratio:.2f} pooled, {vw:.2f} value-weighted; {100 * multi:.1f}% of cells have a multi-affiliate group")

    # Fact-5 regressions ---------------------------------------------------------------------------------
    PANELS = [(r"Panel A: all exports ($\ln$)", "ln_total"), (r"Panel B: non-MNE exports ($\ln$)", "ln_nonmne")]
    # (0) the document's Table 1, reproduced on the current base: intensive (ln # MNE firms) + extensive (any MNE)
    run_panel_table(g,
                    [("(1)", ["O", "D", "Y", "P"], ["ln_nmne"]), ("(2)", ["OY", "DY", "P"], ["ln_nmne"]), ("(3)", ["ODP", "ODY"], ["ln_nmne"]),
                     ("(1)", ["O", "D", "Y", "P"], ["any_mne"]), ("(2)", ["OY", "DY", "P"], ["any_mne"]), ("(3)", ["ODP", "ODY"], ["any_mne"])],
                    PANELS, [(r"$\ln$(\# MNE firms)", "ln_nmne"), ("Any MNE present", "any_mne")], "od", R / "reg_wp0_table1_repro.tex",
                    "Origin-destination-product-year cells; dep.\\ var.\\ $\\ln$ exports. Intensive margin: $\\ln$ number of MNE firms (cells with $\\geq 1$ MNE); "
                    "extensive margin: indicator for any MNE present. Reproduction of the document's Table 1 on the current base.",
                    col_groups=[(r"Intensive: $\ln$(\# MNE firms)", 3), ("Extensive: any MNE present", 3)])
    ROWS = [(r"$\ln$(\# MNE firms)", "ln_nmne"),
            (r"$\ln$(1 + \# foreign MNEs present through HQ)", "l1_n_hq_present"),
            (r"$\ln$(1 + \# foreign MNEs present through another affiliate)", "l1_n_aff_present"),
            (r"$\ln$(1 + \# foreign MNEs not present)", "l1_n_not_present"),
            (r"$\ln$(1 + \# domestic MNEs)", "l1_n_dom")]
    BY_TYPE = ["l1_n_hq_present", "l1_n_aff_present", "l1_n_not_present", "l1_n_dom"]
    run_panel_table(sub,
                    [("(1)", ["OY", "DY", "P"], ["ln_nmne"]), ("(2)", ["ODP", "ODY"], ["ln_nmne"]), ("(3)", ["ODP", "ODY", "DPY"], ["ln_nmne"]),
                     ("(4)", ["OY", "DY", "P"], BY_TYPE), ("(5)", ["ODP", "ODY"], BY_TYPE), ("(6)", ["ODP", "ODY", "DPY"], BY_TYPE)],
                    PANELS, ROWS, "od", R / "reg_wp1e_counts.tex",
                    "Origin-destination-product-year cells with at least one MNE; dep.\\ var.\\ $\\ln$ exports. Columns (1)--(3) reproduce the document's intensive margin (the third adds destination $\\times$ product $\\times$ year FE); (4)--(6) split the count of foreign multinationals by how the group is present at the destination (through its headquarters, through another affiliate, not present), plus domestic MNEs.",
                    col_groups=[(r"$\ln$(\# MNE firms)", 3), ("Counts by presence type", 3)])
    ROWS2 = [(r"$\ln$(\# MNE firms)", "ln_nmne"), (r"$\ln$(\# MNE groups)", "ln_ngrp"), (r"$\ln$(affiliates per group)", "ln_aff_per_grp")]
    run_panel_table(sub,
                    [("(1)", ["ODP", "ODY"], ["ln_nmne"]), ("(2)", ["ODP", "ODY"], ["ln_ngrp"]), ("(3)", ["ODP", "ODY"], ["ln_ngrp", "ln_aff_per_grp"]),
                     ("(4)", ["ODP", "ODY", "DPY"], ["ln_nmne"]), ("(5)", ["ODP", "ODY", "DPY"], ["ln_ngrp"]), ("(6)", ["ODP", "ODY", "DPY"], ["ln_ngrp", "ln_aff_per_grp"])],
                    PANELS, ROWS2, "od", R / "reg_wp1e_groups.tex",
                    "Origin-destination-product-year cells with at least one MNE; dep.\\ var.\\ $\\ln$ exports. `MNE firms' counts matched exporting affiliates; `MNE groups' counts distinct ultimate parents; `affiliates per group' = firms/groups.",
                    col_groups=[(r"ODP + ODY FE", 3), (r"+ DPY FE", 3)])


# ---------------------------------------------------------------------
# Part B: firm-level distance regressions with the presence splits
# ---------------------------------------------------------------------
def part_b() -> None:
    G, T, R = W.outdirs("all")
    f = W.load_fdpy()
    f = f[(~f["country_orig"].isin(W.excluded_origins())) & (f["value_fob"] > 0)].copy()
    keys = ["country_orig", "Tax_ID", "country_dest", "hs07_6d", "year"]
    mcol = "m_dnb" if W.CONVENTION == "sf" else "m_fr"
    f = f.groupby(keys, as_index=False, dropna=False).agg(
        value=("value_fob", "sum"), m=(mcol, "max"), parent=("iso3_parent", "first"), aff=("has_aff_in_dest", "max"))
    print(f"\n=== Part B: {len(f):,} firm-dest-product-year rows")
    grav = W.load_gravity(("iso3_o", "iso3_d", "dist")).dropna(subset=["dist"]).groupby(["iso3_o", "iso3_d"], as_index=False).agg(dist=("dist", "first"))
    f = f.merge(grav, left_on=["country_orig", "country_dest"], right_on=["iso3_o", "iso3_d"], how="left")
    f = f[f["dist"].notna() & (f["dist"] > 0)].copy()
    f["ln_dist"] = np.log(f["dist"].astype(float)); f["ln_exports"] = np.log(f["value"].astype(float))
    f["year"] = f["year"].astype(int)
    f["ot"] = f["country_orig"] + "_" + f["year"].astype(str); f["dt"] = f["country_dest"] + "_" + f["year"].astype(str)
    f["od"] = f["country_orig"] + "_" + f["country_dest"]
    m = f["m"].astype(bool); par = f["parent"].fillna("")
    dom = m & (par == f["country_orig"])
    ext = (m & ~dom) if W.CONVENTION == "sf" else (m & (par != "") & (par != f["country_orig"]))
    hq_pres = ext & (par == f["country_dest"])
    aff_pres = ext & ~hq_pres & (f["aff"] == 1)
    anypres = m & ((f["aff"] == 1) | (par == f["country_dest"]))
    groups = {"g_mne": m, "g_anypres": anypres, "g_anynotpres": m & ~anypres,
              "g_ext": ext, "g_dom": dom,
              "g_ext_hqpres": hq_pres, "g_ext_affpres": aff_pres, "g_ext_notpres": ext & ~hq_pres & ~aff_pres,
              "g_dom_pres": dom & (f["aff"] == 1), "g_dom_notpres": dom & (f["aff"] == 0)}
    GLAB = {"g_mne": "MNE", "g_anypres": "MNE, present", "g_anynotpres": "MNE, not present",
            "g_ext": "foreign MNE", "g_dom": "domestic MNE", "g_ext_hqpres": "foreign MNE, present through HQ",
            "g_ext_affpres": "foreign MNE, present through another affiliate", "g_ext_notpres": "foreign MNE, not present",
            "g_dom_pres": "domestic MNE, group present in destination", "g_dom_notpres": "domestic MNE, not present"}
    for k, s in groups.items():
        f[k + "_Xd"] = s.astype(float) * f["ln_dist"]
    print("   group value shares: " + ", ".join(f"{k}={f.loc[s, 'value'].sum() / f['value'].sum():.3f}" for k, s in groups.items()))
    FE = {"ODYP": ("O + D + Yr + P", "country_orig + country_dest + year + hs07_6d", {"Origin FE", "Destination FE", "Year FE", "Product FE"}),
          "OYDYP": ("OxYr + DxYr + P", "ot + dt + hs07_6d", {r"Origin $\times$ year FE", r"Destination $\times$ year FE", "Product FE"})}
    FE_ORDER_B = ["Origin FE", "Destination FE", "Year FE", r"Origin $\times$ year FE", r"Destination $\times$ year FE", "Product FE"]
    TABLES = [
        ("reg_wp0_table2_repro.tex",
         [("(1)", "ODYP", ["g_mne"]), ("(2)", "OYDYP", ["g_mne"]),
          ("(3)", "ODYP", ["g_anypres", "g_anynotpres"]), ("(4)", "OYDYP", ["g_anypres", "g_anynotpres"])],
         ["g_mne", "g_anypres", "g_anynotpres"],
         "Reproduction of the document's Table 2 on the current base: multinationals (foreign or domestic) split by presence at the "
         "destination (the group has an affiliate there, or the destination is the parent's country)."),
        ("reg_wp1e_distance_hq.tex",
         [("(1)", "ODYP", ["g_ext", "g_dom"]), ("(2)", "OYDYP", ["g_ext", "g_dom"]),
          ("(3)", "ODYP", ["g_ext_hqpres", "g_ext_affpres", "g_ext_notpres", "g_dom_pres", "g_dom_notpres"]),
          ("(4)", "OYDYP", ["g_ext_hqpres", "g_ext_affpres", "g_ext_notpres", "g_dom_pres", "g_dom_notpres"])],
         ["g_ext", "g_ext_hqpres", "g_ext_affpres", "g_ext_notpres", "g_dom", "g_dom_pres", "g_dom_notpres"],
         "Foreign MNEs split by how the group is present at the destination: through its headquarters (the parent's country), "
         "through another affiliate, or not present; domestic MNEs by whether the group has an affiliate in the destination."),
    ]
    for out_name, columns, row_order, tnote in TABLES:
        distance_table(f, FE, FE_ORDER_B, GLAB, columns, row_order, R / out_name, tnote)


def distance_table(f, FE, FE_ORDER_B, GLAB, columns, row_order, out_path, tnote):
    cols = []
    for tag, fk, gs in columns:
        t0 = time.time()
        mdl = pf.feols(f"ln_exports ~ ln_dist + {' + '.join(g + '_Xd' for g in gs)} | {FE[fk][1]}", data=f, vcov={"CRV1": "od"})
        b, se, p = mdl.coef(), mdl.se(), mdl.pvalue()
        cells = {g: (float(b[g + "_Xd"]), float(se[g + "_Xd"]), float(p[g + "_Xd"])) for g in gs}
        cells["ln_dist"] = (float(b["ln_dist"]), float(se["ln_dist"]), float(p["ln_dist"]))
        cols.append({"tag": tag, "fk": fk, "rows": set(gs) | {"ln_dist"}, "cells": cells, "n": int(mdl._N)})
        print(f"   {tag} N={int(mdl._N):,} base {cells['ln_dist'][0]:+.4f} " + " ".join(f"{GLAB[g]}: {cells[g][0]:+.4f}{W.stars(cells[g][2])}" for g in gs) + f" ({time.time() - t0:.0f}s)")
        del mdl, b, se, p; gc.collect()
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
    for fe in FE_ORDER_B:
        pres = [fe in FE[c["fk"]][2] for c in cols]
        if any(pres):
            lines.append(f"{fe} & " + " & ".join(r"$\checkmark$" if x else "" for x in pres) + r" \\")
    lines += [r"\hline", "Observations & " + " & ".join(f"{c['n']:,}" for c in cols) + r" \\", r"\hline",
              rf"\multicolumn{{{ncols + 1}}}{{p{{0.95\textwidth}}}}{{\footnotesize Distance and firm exports. Firm$\times$origin$\times$destination$\times$product$\times$year; non-MNE flows the omitted base. "
              + tnote + r" SE clustered at origin-destination. *** p$<$0.01, ** p$<$0.05, * p$<$0.1}} \\",
              r"\end{tabular}"]
    W.write_tex(lines, out_path)


def main():
    cube = W.build_cube()
    for scope in SCOPES:
        part_a(cube, scope)
    if RUN_PART_B:
        part_b()
    print("\n>>> wp1e done")


if __name__ == "__main__":
    main()
