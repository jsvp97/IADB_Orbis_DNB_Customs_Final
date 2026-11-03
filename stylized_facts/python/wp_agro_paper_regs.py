"""
wp_agro_paper_regs.py  --  regressions of the agriculture paper (2026-10-13 round, reformatted 2026-10-20)
=========================================================================================================

Agriculture (HS 01--24), nine origins, CONVENTION "sf". Run on the balanced window:

    WP_YEARS=2012-2018 WP_SCOPES=agro python wp_agro_paper_regs.py [presence] [distance]

Every table has the format of the presence table (Table 5 of the paper): one row of column numbers (1), (2), ...,
panels "Panel A. Dependent variable: ..." in italics, fixed-effect rows with check marks, observations per panel.

Outputs (output/wp_2012_2018/agro/Regressions/):
  reg_agp_presence.tex        ln exports on ln number of MNEs (1)-(3) and on an indicator for any MNE (4)-(6);
                              fixed effects: ODP + Y, ODP + ODY, ODP + ODY + OPY + DPY (the strictest set);
                              Panel A total exports, Panel B exports of non-MNE firms
  reg_agp_share.tex           the same with the MNE share of the cell's exports as the regressor: (1)-(3) cells with
                              at least one MNE, (4)-(6) all cells (share zero where no MNE exports)
  reg_agp_croptype.tex        the presence regressions with ln N (any MNE) interacted with each of the four types of
                              production (wp_agro_croptype.crop_type), no main term; ODP + ODY and the strictest set
  reg_agp_croptype_share.tex  MNE share of the cell on type-of-production dummies (unweighted and value-weighted)
  reg_agp_counts.tex,         appendix: foreign / domestic / presence-through-HQ splits of reg_wp1e_counts and
  reg_agp_extensive.tex       reg_wp1e_extensive in the standard format
  reg_agp_distance_early.tex  the distance table of earlier versions (no MNE level term), standard format
  reg_agp_distance_hq.tex     the same, foreign vs domestic and presence through HQ (appendix)
  reg_agp_distance.tex        distance with firm fixed effects and stricter sets; Panel A all firms (ln distance x
                              MNE), Panel B non-MNE firms (ln distance x any MNE from the same origin in the market)
  reg_agp_distance_pres.tex   the same columns, multinationals split by presence at the destination (appendix)

With a firm fixed effect the MNE indicator is absorbed, so the interaction compares the same firm across destinations.
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
import wp1e_hq_affiliates as E  # noqa: E402

SCOPE = "agro"
G, T, R = W.outdirs(SCOPE)

# ---------------------------------------------------------------------
# Presence regressions (origin x destination x product x year)
# ---------------------------------------------------------------------
E.FE_COMPONENTS.update({"OPY": (r"Origin $\times$ product $\times$ year FE", "opy"),
                        "DPY": (r"Destination $\times$ product $\times$ year FE", "dpy")})
E.FE_ORDER[:] = ["O", "D", "P", "Y", "OY", "DY", "ODP", "ODY", "OPY", "DPY"]
FE_SETS = [["ODP", "Y"], ["ODP", "ODY"], ["ODP", "ODY", "OPY", "DPY"]]   # 2026-10-20: (3) = strictest
NOTE = "."   # notes live in main.tex; split_note drops the fragment note
CT = {"horti": "Horticultural and plantation crops", "field": "Field crops", "live": "Livestock and fisheries",
      "proc": "Other processed food and beverages"}
CT_LAB = {"horti": "horticultural and plantation crops", "field": "field crops", "live": "livestock and fisheries",
          "proc": "other processed food"}


def numbered(regs_by_col: list[tuple[list[str], list[str]]]):
    return [(f"({i + 1})", fe, regs) for i, (fe, regs) in enumerate(regs_by_col)]


def presence() -> None:
    d = W.scope_filter(W.mne_flags(W.build_cube()), SCOPE)
    g = E.odpy_cells(d[d["value"] > 0])
    g["opy"] = g["country_orig"] + "_" + g["hs07_6d"] + "_" + g["year"].astype(str)
    g["dpy"] = g["country_dest"] + "_" + g["hs07_6d"] + "_" + g["year"].astype(str)
    print(f"cells {len(g):,}")

    # Table 5: number of MNEs and any MNE
    cols = numbered([(fe, ["ln_n_mne"]) for fe in FE_SETS] + [(fe, ["any_n_mne"]) for fe in FE_SETS])
    E.run_panel_table(g, cols, E.PANELS, [(E.LAB["ln_n_mne"], "ln_n_mne"), (E.LAB["any_n_mne"], "any_n_mne")], "od",
                      R / "reg_agp_presence.tex", NOTE)

    # Table 6: the MNE share of the cell's exports as the regressor
    g["sh_pos"] = np.where(g["n_mne"] > 0, g["v_mne"] / g["total_value"], np.nan)
    g["sh_all"] = g["v_mne"] / g["total_value"]
    E.LAB.update({"sh_pos": "MNE share of exports", "sh_all": "MNE share of exports, all observations"})
    cols = numbered([(fe, ["sh_pos"]) for fe in FE_SETS] + [(fe, ["sh_all"]) for fe in FE_SETS])
    E.run_panel_table(g, cols, E.PANELS, [(E.LAB["sh_pos"], "sh_pos"), (E.LAB["sh_all"], "sh_all")], "od",
                      R / "reg_agp_share.tex", NOTE)

    croptype(g)

    # appendix: type-of-multinational splits in the standard format (same columns as wp1e)
    DEC1, DEC2 = ["ln_n_ext", "ln_n_dom"], ["ln_n_ext_hq", "ln_n_ext_nothq", "ln_n_dom"]
    rows = [(E.LAB[v], v) for v in ("ln_n_mne", "ln_n_ext", "ln_n_ext_hq", "ln_n_ext_nothq", "ln_n_dom")]
    E.run_panel_table(g, numbered([(E.FE_A, ["ln_n_mne"]), (E.FE_B, ["ln_n_mne"]), (E.FE_A, DEC1), (E.FE_B, DEC1),
                                   (E.FE_A, DEC2), (E.FE_B, DEC2)]), E.PANELS, rows, "od", R / "reg_agp_counts.tex", NOTE)
    EX1, EX2 = ["any_n_ext", "any_n_dom"], ["any_n_ext_hq", "any_n_ext_nothq", "any_n_dom"]
    rows = [(E.LAB[v], v) for v in ("any_n_mne", "any_n_ext", "any_n_ext_hq", "any_n_ext_nothq", "any_n_dom")]
    E.run_panel_table(g, numbered([(E.FE_A, ["any_n_mne"]), (E.FE_B, ["any_n_mne"]), (E.FE_A, EX1), (E.FE_B, EX1),
                                   (E.FE_A, EX2), (E.FE_B, EX2)]), E.PANELS, rows, "od", R / "reg_agp_extensive.tex", NOTE)
    del g; gc.collect()


def croptype(g: pd.DataFrame) -> None:
    """Presence by type of production: ln N (any MNE) interacted with each of the four types, no main term."""
    import wp_agro_croptype as C
    g = g.copy()
    ct = C.crop_type(g["hs07_6d"])
    for k, lab in CT.items():
        g[k] = (ct == lab).astype(float)
        g[f"lnN_{k}"] = g["ln_n_mne"] * g[k]
        g[f"any_{k}"] = g["any_n_mne"] * g[k]
        E.LAB[f"lnN_{k}"] = rf"$\ln$(\# MNE firms) $\times$ {CT_LAB[k]}"
        E.LAB[f"any_{k}"] = rf"Any MNE present $\times$ {CT_LAB[k]}"
    INT = [f"lnN_{k}" for k in CT]
    EXT = [f"any_{k}" for k in CT]
    S1, S2 = FE_SETS[1], FE_SETS[2]
    E.run_panel_table(g, numbered([(S1, INT), (S2, INT), (S1, EXT), (S2, EXT)]), E.PANELS,
                      [(E.LAB[v], v) for v in INT + EXT], "od", R / "reg_agp_croptype.tex", NOTE)
    # equality tests, field vs horticultural crops (for the text)
    for dep in ("ln_total", "ln_nonmne"):
        for regs, fe in ((INT, S1), (INT, S2), (EXT, S1), (EXT, S2)):
            dd = g.dropna(subset=[dep] + regs)
            fes = " + ".join(E.FE_COMPONENTS[k][1] for k in fe)
            m = W.feols(f"{dep} ~ {' + '.join(regs)} | {fes}", data=dd, vcov={"CRV1": "od"})
            b = m.coef(); V = m._vcov; ix = list(b.index)
            i, j = ix.index(regs[1]), ix.index(regs[0])
            diff = b[regs[1]] - b[regs[0]]; se = float(np.sqrt(V[i, i] + V[j, j] - 2 * V[i, j]))
            print(f"   test field = horti  {dep} {regs[0][:3]} {'+'.join(fe)}: diff {diff:+.3f} (se {se:.3f}, t {diff / se:.2f})")

    # the MNE share of the cell on type-of-production dummies (appendix)
    g["sh_mne"] = g["v_mne"] / g["total_value"]; g["sh_ext"] = g["v_ext"] / g["total_value"]
    cols = [("ot + dt", None), ("ody", None), ("ot + dt", "total_value"), ("ody", "total_value")]
    lab = {k: CT[k] for k in ("field", "live", "proc")}
    res = {}
    for pi, dep in enumerate(["sh_mne", "sh_ext"]):
        for ci, (fe, w) in enumerate(cols):
            m = W.feols(f"{dep} ~ field + live + proc | {fe}", data=g, vcov={"CRV1": "od"}, weights=w)
            res[(pi, ci)] = ({v: (float(m.coef()[v]), float(m.se()[v]), float(m.pvalue()[v])) for v in lab}, int(m._N))
            print(f"   share {dep} {fe} w={w}: " + " ".join(f"{v} {res[(pi, ci)][0][v][0]:+.3f}{W.stars(res[(pi, ci)][0][v][2])}" for v in lab))
    L = [r"\begin{tabular}{lcccc} \hline", " & (1) & (2) & (3) & (4) " + r"\\ \hline"]
    for pi, plab in enumerate(["Panel A. Dependent variable: share of all MNEs", "Panel B. Dependent variable: share of foreign MNEs"]):
        if pi:
            L.append(r"\midrule")
        L.append(rf"\multicolumn{{5}}{{l}}{{\textit{{{plab}}}}} \\")
        for v, vl in lab.items():
            L.append(vl + " & " + " & ".join(f"{res[(pi, ci)][0][v][0]:.4f}{W.stars(res[(pi, ci)][0][v][2])}" for ci in range(4)) + r" \\")
            L.append(" & " + " & ".join(f"({res[(pi, ci)][0][v][1]:.4f})" for ci in range(4)) + r" \\")
    ck = r"$\checkmark$"
    L += [r"\hline", rf"Origin $\times$ year FE & {ck} & & {ck} & \\", rf"Destination $\times$ year FE & {ck} & & {ck} & \\",
          rf"Origin $\times$ dest.\ $\times$ year FE & & {ck} & & {ck} \\", rf"Weighted by export value & & & {ck} & {ck} \\",
          "Observations & " + " & ".join(f"{res[(0, ci)][1]:,}" for ci in range(4)) + r" \\", r"\hline", r"\end{tabular}"]
    W.write_tex(L, R / "reg_agp_croptype_share.tex")


# ---------------------------------------------------------------------
# Distance (firm x destination x product x year)
# ---------------------------------------------------------------------
FE_DIST = {  # key: (pyfixest FE, FE rows ticked)
    "ODYP": ("country_orig + country_dest + year + hs07_6d", {"o", "d", "y", "p"}),
    "A": ("ot + dt + hs07_6d", {"oy", "dy", "p"}),
    "B": ("ot + dt + hs07_6d + fid", {"oy", "dy", "p", "f"}),
    "C": ("fy + dt + hs07_6d", {"fy", "dy", "p"}),
    "D": ("fpy + dt", {"fpy", "dy"}),
    "E": ("fpy + dpy", {"fpy", "dpy"}),
}
FE_ROWS = [("o", "Origin FE"), ("d", "Destination FE"), ("y", "Year FE"), ("oy", r"Origin $\times$ year FE"),
           ("dy", r"Destination $\times$ year FE"), ("p", "Product FE"), ("f", "Firm FE"), ("fy", r"Firm $\times$ year FE"),
           ("fpy", r"Firm $\times$ product $\times$ year FE"), ("dpy", r"Destination $\times$ product $\times$ year FE")]
DLAB = {"ln_dist": r"$\ln$ distance", "g_mne_Xd": r"$\ln$ distance $\times$ MNE",
        "g_anypres_Xd": r"$\ln$ distance $\times$ MNE, present at destination",
        "g_anynotpres_Xd": r"$\ln$ distance $\times$ MNE, not present at destination",
        "g_ext_Xd": r"$\ln$ distance $\times$ foreign MNE", "g_dom_Xd": r"$\ln$ distance $\times$ domestic MNE",
        "g_ext_hq_Xd": r"$\ln$ distance $\times$ foreign MNE, destination is the parent's country",
        "g_ext_nothq_Xd": r"$\ln$ distance $\times$ foreign MNE, other destinations",
        "any_mne_odpy": "Any MNE in the market", "any_Xd": r"$\ln$ distance $\times$ any MNE in the market"}
FIRM_FE = ["B", "C", "D", "E"]


def firm_panel() -> pd.DataFrame:
    f = E.load_firm_panel()
    f = f[W.sector4(f["hs2"]) == W.SECTOR_OF_SCOPE[SCOPE]].copy()
    f["fid"] = f["country_orig"] + "|" + f["Tax_ID"].astype(str)
    f["fy"] = f["fid"] + "_" + f["year"].astype(str)
    f["fpy"] = f["fy"] + "_" + f["hs07_6d"]
    f["dpy"] = f["country_dest"] + "_" + f["hs07_6d"] + "_" + f["year"].astype(str)
    key = ["country_orig", "country_dest", "hs07_6d", "year"]
    f["any_mne_odpy"] = f.groupby(key)["m"].transform("max").astype(float)
    f["any_Xd"] = f["any_mne_odpy"] * f["ln_dist"]
    print(f"firm panel (agro): {len(f):,} rows; non-MNE rows {int((f['m'] == 0).sum()):,}")
    return f


def est(f: pd.DataFrame, regs: list[str], fe: str) -> dict:
    t0 = time.time()
    m = W.feols(f"ln_exports ~ {' + '.join(regs)} | {fe}", data=f, vcov={"CRV1": "od"})
    b, se, p = m.coef(), m.se(), m.pvalue()
    out = {"cells": {v: (float(b[v]), float(se[v]), float(p[v])) for v in regs if v in b.index}, "n": int(m._N)}
    print(f"   [{fe}] N={out['n']:,} " + " ".join(f"{v}:{c[0]:+.4f}{W.stars(c[2])}" for v, c in out["cells"].items())
          + f" ({time.time() - t0:.0f}s)")
    del m; gc.collect()
    return out


def write_dist(path: Path, fes: list[str], panels: list) -> None:
    """Standard format. fes: one FE key per column; panels: [(label, data, [regs per column])]."""
    n = len(fes)
    res = [[est(dat, regs[ci], FE_DIST[fes[ci]][0]) for ci in range(n)] for _, dat, regs in panels]
    L = [rf"\begin{{tabular}}{{l{'c' * n}}} \hline", " & " + " & ".join(f"({i + 1})" for i in range(n)) + r" \\ \hline"]
    for pi, (lab, _, regs) in enumerate(panels):
        if pi:
            L.append(r"\midrule")
        L.append(rf"\multicolumn{{{n + 1}}}{{l}}{{\textit{{{lab}}}}} \\")
        rows = list(dict.fromkeys(v for rr in regs for v in rr))
        for r in rows:
            rb, rs = [], []
            for c in res[pi]:
                if r in c["cells"]:
                    bb, ss, pp = c["cells"][r]; rb.append(f"{bb:.4f}{W.stars(pp)}"); rs.append(f"({ss:.4f})")
                else:
                    rb.append(""); rs.append("")
            L += [f"{DLAB[r]} & " + " & ".join(rb) + r" \\", " & " + " & ".join(rs) + r" \\"]
    L.append(r"\hline")
    for k, lab in FE_ROWS:
        if any(k in FE_DIST[fk][1] for fk in fes):
            L.append(f"{lab} & " + " & ".join(r"$\checkmark$" if k in FE_DIST[fk][1] else "" for fk in fes) + r" \\")
    for pi, (lab, _, _) in enumerate(panels):
        short = f" ({lab.split('.')[0]})" if len(panels) > 1 else ""
        L.append(f"Observations{short} & " + " & ".join(f"{c['n']:,}" for c in res[pi]) + r" \\")
    L += [r"\hline", r"\end{tabular}"]
    W.write_tex(L, path)


def distance() -> None:
    f = firm_panel()
    loc = f[f["m"] == 0]
    DV = r"Dependent variable: $\ln$ exports"
    base = ["ln_dist"]
    # earlier specification (Table 8) and its foreign / domestic split (appendix)
    write_dist(R / "reg_agp_distance_early.tex", ["ODYP", "A", "ODYP", "A"],
               [(DV, f, [base + ["g_mne_Xd"]] * 2 + [base + ["g_anypres_Xd", "g_anynotpres_Xd"]] * 2)])
    write_dist(R / "reg_agp_distance_hq.tex", ["ODYP", "A", "ODYP", "A"],
               [(DV, f, [base + ["g_ext_Xd", "g_dom_Xd"]] * 2 + [base + ["g_ext_hq_Xd", "g_ext_nothq_Xd", "g_dom_Xd"]] * 2)])
    # firm fixed effects and stricter sets (Table 9) and the presence split (appendix)
    cols = ["A"] + FIRM_FE
    write_dist(R / "reg_agp_distance.tex", cols,
               [("Panel A. " + DV + ", all firms", f, [base + ["g_mne_Xd"]] * 5),
                ("Panel B. " + DV + ", non-MNE firms", loc, [base + ["any_mne_odpy", "any_Xd"]] * 5)])
    write_dist(R / "reg_agp_distance_pres.tex", cols, [(DV, f, [base + ["g_anypres_Xd", "g_anynotpres_Xd"]] * 5)])


if __name__ == "__main__":
    assert W.YEAR_WINDOW == (2012, 2018), "run with WP_YEARS=2012-2018"
    which = sys.argv[1:] or ["presence", "distance"]
    if "presence" in which:
        presence()
    if "distance" in which:
        distance()
    print(">>> wp_agro_paper_regs done ->", R)
