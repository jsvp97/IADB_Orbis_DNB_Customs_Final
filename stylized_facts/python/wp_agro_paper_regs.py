"""
wp_agro_paper_regs.py  --  regressions added to the agriculture paper in the 2026-10-13 round
==============================================================================================

Agriculture (HS 01--24), nine origins, CONVENTION "sf". Run on the balanced window:

    WP_YEARS=2012-2018 WP_SCOPES=agro python wp_agro_paper_regs.py

Outputs (output/wp_2012_2018/agro/Regressions/):
  reg_agp_presence.tex        Table 4 with a fourth fixed-effect set, the strictest one: all four three-way sets
                              (origin x destination x product, origin x destination x year, origin x product x year,
                              destination x product x year), for both margins (Panel A total, Panel B non-MNE exports)
  reg_agp_croptype.tex        presence regressions with ln N (any MNE) interacted with the type of production
                              (wp_agro_croptype.crop_type; horticultural and plantation crops the omitted group)
  reg_agp_croptype_share.tex  MNE share of the cell on type-of-production dummies (unweighted and value-weighted)
  reg_agp_share.tex           the MNE share of the cell's exports as the dependent variable (Panel A all MNEs,
                              Panel B foreign, Panel C domestic) on ln number of MNEs, same four fixed-effect sets
  reg_agp_distance.tex        Table 5 with firm fixed effects and stricter sets; Panel A all firms (ln distance x MNE),
                              Panel B non-MNE firms only (ln distance x any MNE exporting the same product from the
                              same origin to the same destination in the same year, with its level)
  reg_agp_distance_pres.tex   the same columns, multinationals split by presence at the destination

With a firm fixed effect the MNE indicator is absorbed, so the interaction compares the same firm across destinations.
Column (1) of the distance table keeps the paper's original specification (no MNE level term).
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
# Presence and share regressions (origin x destination x product x year)
# ---------------------------------------------------------------------
E.FE_COMPONENTS.update({"OPY": (r"Origin $\times$ product $\times$ year FE", "opy"),
                        "DPY": (r"Destination $\times$ product $\times$ year FE", "dpy")})
E.FE_ORDER[:] = ["O", "D", "P", "Y", "OY", "DY", "ODP", "ODY", "OPY", "DPY"]
FE_SETS = [["O", "D", "Y", "P"], ["OY", "DY", "P"], ["ODP", "ODY"], ["ODP", "ODY", "OPY", "DPY"]]   # 2026-10-14: col 4 = strictest


def presence_and_share() -> None:
    d = W.scope_filter(W.mne_flags(W.build_cube()), SCOPE)
    g = E.odpy_cells(d[d["value"] > 0])
    g["opy"] = g["country_orig"] + "_" + g["hs07_6d"] + "_" + g["year"].astype(str)
    g["dpy"] = g["country_dest"] + "_" + g["hs07_6d"] + "_" + g["year"].astype(str)
    print(f"cells {len(g):,}")
    cols = [(f"({i + 1})", fe, ["ln_n_mne"]) for i, fe in enumerate(FE_SETS)] + \
           [(f"({i + 1})", fe, ["any_n_mne"]) for i, fe in enumerate(FE_SETS)]
    E.run_panel_table(g, cols, E.PANELS, [(E.LAB["ln_n_mne"], "ln_n_mne"), (E.LAB["any_n_mne"], "any_n_mne")], "od",
                      R / "reg_agp_presence.tex", "Presence regressions with a fourth fixed-effect set.",
                      col_groups=[(r"Intensive: $\ln$(\# MNE firms)", 4), ("Extensive: any MNE present", 4)])
    sub = g[g["n_mne"] > 0].copy()
    sub["sh_mne"] = sub["v_mne"] / sub["total_value"]
    sub["sh_ext"] = sub["v_ext"] / sub["total_value"]
    sub["sh_dom"] = sub["v_dom"] / sub["total_value"]
    print(f"cells with >=1 MNE {len(sub):,}; mean MNE share {sub['sh_mne'].mean():.3f}")
    panels = [("Panel A: share of all MNEs", "sh_mne"), ("Panel B: share of foreign MNEs", "sh_ext"),
              ("Panel C: share of domestic MNEs", "sh_dom")]
    E.run_panel_table(sub, [(f"({i + 1})", fe, ["ln_n_mne"]) for i, fe in enumerate(FE_SETS)], panels,
                      [(E.LAB["ln_n_mne"], "ln_n_mne")], "od", R / "reg_agp_share.tex",
                      "MNE share of the cell's exports on ln number of MNEs; cells with at least one MNE.")
    croptype(g)
    del g, sub; gc.collect()


def croptype(g: pd.DataFrame) -> None:
    """2026-10-14: does the presence association differ by type of production? Base: horticultural and plantation crops."""
    import wp_agro_croptype as C
    g = g.copy()
    ct = C.crop_type(g["hs07_6d"])
    D = {"field": "Field crops", "live": "Livestock and fisheries", "proc": "Other processed food and beverages"}
    for k, lab in D.items():
        g[k] = (ct == lab).astype(float)
        g[f"lnN_{k}"] = g["ln_n_mne"] * g[k]
        g[f"any_{k}"] = g["any_n_mne"] * g[k]
    E.LAB.update({"lnN_field": r"$\ln$(\# MNE firms) $\times$ field crops", "lnN_live": r"$\ln$(\# MNE firms) $\times$ livestock and fisheries",
                  "lnN_proc": r"$\ln$(\# MNE firms) $\times$ other processed food",
                  "any_field": r"Any MNE present $\times$ field crops", "any_live": r"Any MNE present $\times$ livestock and fisheries",
                  "any_proc": r"Any MNE present $\times$ other processed food"})
    INT = ["ln_n_mne", "lnN_field", "lnN_live", "lnN_proc"]
    EXT = ["any_n_mne", "any_field", "any_live", "any_proc"]
    S1, S2 = FE_SETS[2], FE_SETS[3]
    E.run_panel_table(g, [("(1)", S1, INT), ("(2)", S2, INT), ("(3)", S1, EXT), ("(4)", S2, EXT)], E.PANELS,
                      [(E.LAB[v], v) for v in INT + EXT], "od", R / "reg_agp_croptype.tex",
                      "Presence regressions by type of production; horticultural and plantation crops are the omitted group.",
                      col_groups=[(r"Intensive: $\ln$(\# MNE firms)", 2), ("Extensive: any MNE present", 2)])
    # the MNE share of the cell on type-of-production dummies
    g["sh_mne"] = g["v_mne"] / g["total_value"]; g["sh_ext"] = g["v_ext"] / g["total_value"]
    cols = [("(1)", "ot + dt", None), ("(2)", "ody", None), ("(3)", "ot + dt", "total_value"), ("(4)", "ody", "total_value")]
    lab = {"field": "Field crops", "live": "Livestock and fisheries", "proc": "Other processed food and beverages"}
    res = {}
    for pi, dep in enumerate(["sh_mne", "sh_ext"]):
        for ci, (_, fe, w) in enumerate(cols):
            m = W.feols(f"{dep} ~ field + live + proc | {fe}", data=g, vcov={"CRV1": "od"}, weights=w)
            res[(pi, ci)] = ({v: (float(m.coef()[v]), float(m.se()[v]), float(m.pvalue()[v])) for v in lab}, int(m._N))
            print(f"   share {dep} {fe} w={w}: " + " ".join(f"{v} {res[(pi, ci)][0][v][0]:+.3f}{W.stars(res[(pi, ci)][0][v][2])}" for v in lab))
    L = [r"\begin{tabular}{lcccc} \hline", r" & \multicolumn{2}{c}{Unweighted} & \multicolumn{2}{c}{Weighted by export value} \\",
         " & " + " & ".join(c[0] for c in cols) + r" \\ \hline"]
    for pi, plab in enumerate(["Panel A. Dependent variable: share of all MNEs", "Panel B. Dependent variable: share of foreign MNEs"]):
        if pi:
            L.append(r"\midrule")
        L.append(rf"\multicolumn{{5}}{{l}}{{\textit{{{plab}}}}} \\")
        for v, vl in lab.items():
            L.append(vl + " & " + " & ".join(f"{res[(pi, ci)][0][v][0]:.4f}{W.stars(res[(pi, ci)][0][v][2])}" for ci in range(4)) + r" \\")
            L.append(" & " + " & ".join(f"({res[(pi, ci)][0][v][1]:.4f})" for ci in range(4)) + r" \\")
    L += [r"\hline", r"Origin $\times$ year FE & $\checkmark$ & & $\checkmark$ & \\", r"Destination $\times$ year FE & $\checkmark$ & & $\checkmark$ & \\",
          r"Origin $\times$ dest.\ $\times$ year FE & & $\checkmark$ & & $\checkmark$ \\", r"\hline",
          "Observations & " + " & ".join(f"{res[(0, ci)][1]:,}" for ci in range(4)) + r" \\", r"\hline", r"\end{tabular}"]
    W.write_tex(L, R / "reg_agp_croptype_share.tex")


# ---------------------------------------------------------------------
# Distance (firm x destination x product x year)
# ---------------------------------------------------------------------
FE_DIST = [  # (key, pyfixest FE, FE rows ticked)
    ("A", "ot + dt + hs07_6d", {"oy", "dy", "p"}),
    ("B", "ot + dt + hs07_6d + fid", {"oy", "dy", "p", "f"}),
    ("C", "fy + dt + hs07_6d", {"fy", "dy", "p"}),
    ("D", "fpy + dt", {"fpy", "dy"}),
    ("E", "fpy + dpy", {"fpy", "dpy"}),
]
FE_ROWS = [("oy", r"Origin $\times$ year FE"), ("dy", r"Destination $\times$ year FE"), ("p", "Product FE"),
           ("f", "Firm FE"), ("fy", r"Firm $\times$ year FE"), ("fpy", r"Firm $\times$ product $\times$ year FE"),
           ("dpy", r"Destination $\times$ product $\times$ year FE")]
DLAB = {"ln_dist": r"$\ln$ distance", "g_mne_Xd": r"$\ln$ distance $\times$ MNE",
        "g_anypres_Xd": r"$\ln$ distance $\times$ MNE, present at destination",
        "g_anynotpres_Xd": r"$\ln$ distance $\times$ MNE, not present at destination",
        "any_mne_odpy": "Any MNE in the market", "any_Xd": r"$\ln$ distance $\times$ any MNE in the market"}


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
    print(f"firm panel (agro): {len(f):,} rows; non-MNE rows {int((f['m'] == 0).sum()):,}; "
          f"non-MNE rows in markets with an MNE {(f.loc[f['m'] == 0, 'any_mne_odpy'] == 1).mean():.1%}")
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


def write_dist(panels: list, path: Path) -> None:
    """panels: [(label, data, regs, rows)]; one column per FE_DIST set."""
    n = len(FE_DIST)
    res = {pi: [est(dat, regs, fe) for _, fe, _ in FE_DIST] for pi, (_, dat, regs, _) in enumerate(panels)}
    L = [rf"\begin{{tabular}}{{l{'c' * n}}} \hline", r"Dep.\ var.: $\ln$ exports & " + " & ".join(f"({i + 1})" for i in range(n)) + r" \\ \hline"]
    for pi, (lab, _, _, rows) in enumerate(panels):
        if pi:
            L.append(r"\midrule")
        if len(panels) > 1:
            L.append(rf"\multicolumn{{{n + 1}}}{{l}}{{\textit{{{lab}}}}} \\")
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
        L.append(f"{lab} & " + " & ".join(r"$\checkmark$" if k in s else "" for _, _, s in FE_DIST) + r" \\")
    L.append(r"\hline")
    for pi, (lab, _, _, _) in enumerate(panels):
        short = f" ({lab.split('. ')[1]})" if len(panels) > 1 else ""
        L.append(f"Observations{short} & " + " & ".join(f"{c['n']:,}" for c in res[pi]) + r" \\")
    L += [r"\hline", r"\end{tabular}"]
    W.write_tex(L, path)


def distance() -> None:
    f = firm_panel()
    loc = f[f["m"] == 0]
    write_dist([("Panel A. All firms", f, ["ln_dist", "g_mne_Xd"], ["ln_dist", "g_mne_Xd"]),
                ("Panel B. Non-MNE firms", loc, ["ln_dist", "any_mne_odpy", "any_Xd"], ["ln_dist", "any_mne_odpy", "any_Xd"])],
               R / "reg_agp_distance.tex")
    write_dist([("All firms", f, ["ln_dist", "g_anypres_Xd", "g_anynotpres_Xd"], ["ln_dist", "g_anypres_Xd", "g_anynotpres_Xd"])],
               R / "reg_agp_distance_pres.tex")


if __name__ == "__main__":
    assert W.YEAR_WINDOW == (2012, 2018), "run with WP_YEARS=2012-2018"
    which = sys.argv[1:] or ["presence", "distance"]
    if "presence" in which:
        presence_and_share()
    if "distance" in which:
        distance()
    print(">>> wp_agro_paper_regs done ->", R)
