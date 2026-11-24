"""
wp_agro_v4_exhibits.py  --  regression and event-study exhibits of Note_v4.tex (imported by wp_agro_v4_paper.py)
==============================================================================================================

Every function writes one LaTeX table or pgfplots figure into tables/v4 and records, in SHOWN, the workbook cells
(sheet|panel|column, or sheet|tag|outcome|estimator for E6) that the paper prints, so the workbook can colour them red.
Numbers quoted in the text are stored in FACTS.
"""
from __future__ import annotations

import pickle

import numpy as np
import pandas as pd

import wp_agro_v4_paper as P

N = P.N
W = P.W
FE_GRID = {"FE1": ["O", "D", "P", "Y"], "FE2": ["OY", "DY", "P"], "FE3": ["ODP", "Y"], "FE4": ["ODP", "ODY"],
           "FE5": ["ODP", "ODY", "OPY"], "FE6": ["ODP", "ODY", "OPY", "DPY"]}
SIG = r"*** $p<0.01$, ** $p<0.05$, * $p<0.1$."


def load_regs() -> list[dict]:
    regs = []
    for f in sorted(P.OUT4.glob("v4_regs_*.pkl"), key=lambda p: p.stat().st_mtime):
        regs += pickle.load(open(f, "rb"))
    f = P.OUT4 / "v4_ppml.dta"
    if f.exists():
        for _, r in pd.read_stata(f).iterrows():
            if r["status"] == "ok":
                regs.append(dict(sheet="E2e", panel=f"PPML, local exports in levels, regressor {r['reg']}", col="FE4", fe="FE4", dep="XL",
                                 regs=[r["reg"]], cells={r["reg"]: (float(r["b"]), float(r["se"]), float(r["p"]))}, tests={},
                                 n=int(r["N"]), r2=float(r["pr2"]), r2w=np.nan, singletons=int(r["singletons"]), cluster="od", est="PPML"))
    seen, out = set(), []
    for r in reversed(regs):
        k = (r["sheet"], r["panel"], str(r["col"]))
        if k not in seen:
            seen.add(k); out.append(r)
    return list(reversed(out))


REGS = load_regs()


def get(sheet, panel, col):
    for r in REGS:
        if r["sheet"] == sheet and r["panel"] == panel and str(r["col"]) == str(col):
            return r
    raise KeyError((sheet, panel, col))


def show(sheet, panel, col, where):
    k = f"{sheet}|{panel}|{col}"
    old = P.SHOWN.get(k, "")
    if where not in old.split("; "):
        P.SHOWN[k] = f"{old}; {where}" if old else where


def texlab(v: str) -> str:
    base = {"lnN": r"$\ln$(number of MNEs)", "D": "At least one MNE"}
    if v in base:
        return base[v]
    simple = {"lnkl": r"$\ln$ capital per worker", "hi_mean": "High capital intensity", "hi_median": "High capital intensity (median)",
              "q2": "Quintile 2", "q3": "Quintile 3", "q4": "Quintile 4", "q5": "Quintile 5"}
    if v in simple:
        return simple[v]
    import re
    m = re.match(r"^(lnN|D)_(.*)$", v)
    r, rest = base[m.group(1)], m.group(2)
    rest = rest.replace("high_mean_", "").replace("high_median_", "")
    words = {"hi": "high capital intensity", "lo": "low capital intensity", "nc": "not classified", "tnc": "not classified",
             "farm_hi": "farm stage, high", "farm_lo": "farm stage, low", "proc_hi": "processing stage, high", "proc_lo": "processing stage, low",
             "x_lnkl": r"$\ln$ capital per worker", "x_lnkl_dm": r"$\ln$ capital per worker (within stage)",
             "type_field": "field crops", "type_horti": "horticultural and plantation crops", "type_live": "livestock and fisheries",
             "type_proc": "other processed food", "rauch_con_hom": "homogeneous", "rauch_con_ref": "reference priced",
             "rauch_con_diff": "differentiated", "rauch_con_na": "not classified", "bec2_int": "intermediate goods", "bec2_cons": "consumption goods",
             "input_inp": "inputs", "input_oth": "other products"}
    if rest in words:
        return rf"{r} $\times$ {words[rest]}"
    m2 = re.match(r"^(field|horti|live|proc)_(h|l)$", rest)
    if m2:
        ty = {"field": "field crops", "horti": "horticultural and plantation", "live": "livestock and fisheries", "proc": "other processed food"}[m2.group(1)]
        return rf"{r} $\times$ {ty}, {'high' if m2.group(2) == 'h' else 'low'}"
    return rf"{r} $\times$ {rest}"


def fe_table(name, panels, cols, where, test_rows=None, header=None, extra_rows=None):
    """panels: [(panel label in the paper, sheet, workbook panel)], one column per FE code in cols."""
    out = []
    for lab, sheet, wpanel in panels:
        res = [get(sheet, wpanel, c) for c in cols]
        for i, c in enumerate(cols):
            show(sheet, wpanel, c, f"{where}, {lab.split('.')[0]}, column ({i + 1})")
        out.append((lab, res))
    labels = {v: texlab(v) for _, res in out for r in res for v in r["regs"]}
    N.write_table(name, out, [FE_GRID[c] for c in cols], labels, test_rows=test_rows, header=header, extra_rows=extra_rows)
    return out


# ---------------------------------------------------------------------
# section 4.1: baseline
# ---------------------------------------------------------------------
def baseline() -> None:
    out = fe_table("v4_base", [("Panel A. Intensive margin: cells with at least one MNE", "E2a", "Main"),
                               ("Panel B. Extensive margin: all cells", "E2b", "Main")], ["FE1", "FE2", "FE3", "FE4", "FE5", "FE6"], "Table base")
    P.FACTS["base"] = {lab[:7]: [r["cells"][r["regs"][0]][0] for r in res] for lab, res in out}
    out = fe_table("v4_base_local", [("Panel A. Intensive margin: cells with at least one MNE", "E2c", "Main"),
                                     ("Panel B. Extensive margin: all cells", "E2d", "Main")], ["FE1", "FE2", "FE3", "FE4", "FE5", "FE6"], "Table A local")
    P.FACTS["base_local"] = {lab[:7]: [r["cells"][r["regs"][0]][0] for r in res] for lab, res in out}
    # zeros and exporters
    out = fe_table("v4_zeros", [("Panel A. Positive local exports, cells with at least one MNE", "E2e", "Positive local exports, regressor lnN"),
                                ("Panel B. Positive local exports, all cells", "E2e", "Positive local exports, regressor D")],
                   ["FE3", "FE4", "FE5", "FE6"], "Table A zeros")
    P.FACTS["zeros"] = {lab[:7]: [r["cells"][r["regs"][0]][0] for r in res] for lab, res in out}
    pp = {k: get("E2e", f"PPML, local exports in levels, regressor {k}", "FE4") for k in ("lnN", "D")}
    for k in pp:
        show("E2e", f"PPML, local exports in levels, regressor {k}", "FE4", "Table A zeros, text")
    P.FACTS["ppml"] = {k: list(r["cells"][k]) + [r["n"]] for k, r in pp.items()}
    out = fe_table("v4_exporters", [(r"Panel A. $\ln$ number of local exporters", "E2f", "ln number of local exporters, regressor lnN"),
                                    (r"Panel B. $\ln$ exports per local exporter", "E2f", "ln exports per local exporter, regressor lnN"),
                                    (r"Panel C. $\ln$ number of local exporters", "E2f", "ln number of local exporters, regressor D"),
                                    (r"Panel D. $\ln$ exports per local exporter", "E2f", "ln exports per local exporter, regressor D")],
                   ["FE3", "FE4", "FE5", "FE6"], "Table A exporters")
    P.FACTS["exporters"] = {lab[:7]: [r["cells"][r["regs"][0]][0] for r in res] for lab, res in out}
    P.FACTS["exporters_p"] = {lab[:7]: [r["cells"][r["regs"][0]][2] for r in res] for lab, res in out}
    # by origin
    order = P.FACTS["origin_order"]
    for reg, nm, tab in (("lnN", "v4_country_lnN", "Table A country"), ("D", "v4_country_D", "Table A country")):
        panels, fk = [], []
        for fe, lab in (("FE3", r"Panel A. Destination $\times$ product and year FE"), ("FE4", r"Panel B. Destination $\times$ product and destination $\times$ year FE"),
                        ("FE5", r"Panel C. Panel B plus product $\times$ year FE")):
            res = [get("E2g", f"{P.COUNTRY[o]}, regressor {reg}", fe) for o in order]
            for o in order:
                show("E2g", f"{P.COUNTRY[o]}, regressor {reg}", fe, f"{tab} ({reg}), {lab.split('.')[0]}, column {o}")
            panels.append((lab, res)); fk.append(FE_GRID[fe])
        N.write_country_table(nm, panels, order, fk, {reg: texlab(reg)})
        P.FACTS[f"country_{reg}"] = {o: get("E2g", f"{P.COUNTRY[o]}, regressor {reg}", "FE4")["cells"].get(reg, [np.nan] * 3)[:3] for o in order}


# ---------------------------------------------------------------------
# section 4.2: capital intensity
# ---------------------------------------------------------------------
def capital_desc() -> None:
    D = {}
    for f in sorted(P.OUT4.glob("v4_desc_*.pkl"), key=lambda p: p.stat().st_mtime):
        D.update(pickle.load(open(f, "rb")))
    q = D["E3a"]
    q = q[q["Period"] == "2018"]
    rows = []
    for st in ("Farm", "Processing"):
        rows.append([rf"\textit{{{st} stage}}", "", "", "", "", ""])
        for _, r in q[q["Stage"] == st].iterrows():
            rows.append([f"Quintile {int(r['Quintile'])}", f"{int(r['Products']):,}", f"{r['Share of agricultural exports (%)']:.1f}",
                         f"{r['MNE share (%)']:.1f}", f"{r['Foreign MNE share (%)']:.1f}", f"{r['Capital per worker, mean weighted by exports (US$ thousand)']:,.0f}"])
    P.write_plain("v4_quintiles", ["", "Products", r"Share of agricultural exports (\%)", r"MNE share (\%)", r"Foreign MNE share (\%)",
                                   r"Capital per worker (US\$ thousand)"], rows, colspec="lrrrrr")
    P.FACTS["quintiles"] = {f"{r['Stage']}_{int(r['Quintile'])}": {k: (float(v) if isinstance(v, (int, float, np.floating)) else v) for k, v in r.items()}
                            for _, r in q.iterrows()}
    d3 = D["E3d"]
    P.FACTS["e3d"] = d3[d3["Period"] == "2018"].to_dict("records")
    P.FACTS["coverage"] = D["E3c"].to_dict("records")
    P.FACTS["thresholds"] = D["Thresholds"].to_dict("records")
    # figure: MNE share and capital per worker, product by product, 2018
    b = D["E3b"]
    b = b[b["stage"].isin(["Farm", "Processing"]) & (b["exports_2018"] > 0)].copy()
    vmax = b["exports_2018"].max()
    L = [r"\begin{tikzpicture}"]
    P.FACTS["kl_slope"] = {}
    for i, st in enumerate(("Farm", "Processing")):
        s = b[b["stage"] == st]
        w = s["exports_2018"].values
        X = np.c_[np.ones(len(s)), np.log(s["kl"].values)]
        beta = np.linalg.lstsq(X * np.sqrt(w)[:, None], s["mne_share_2018"].values * np.sqrt(w), rcond=None)[0]
        P.FACTS["kl_slope"][st] = float(beta[1])
        lo, hi = float(s["kl"].min()), float(s["kl"].max())
        xs = np.exp(np.linspace(np.log(lo), np.log(hi), 20))
        shift = r"xshift=8.2cm," if i else ""
        L += [rf"\begin{{axis}}[{shift} width=7.6cm, height=6.4cm, xmode=log, log basis x=10, xmin={lo * 0.8:.1f}, xmax={hi * 1.25:.1f}, ymin=-5, ymax=105,",
              r"  xlabel={Capital per worker (US\$ thousand, log scale)}, ylabel={MNE share of exports (\%)}, title={" + st + r" stage}, title style={font=\footnotesize},",
              r"  tick label style={font=\footnotesize}, label style={font=\footnotesize}, axis x line*=bottom, axis y line*=left, log ticks with fixed point,",
              r"  scatter/use mapped color={draw=none, fill=" + N.C_EXT + r", fill opacity=0.35}]",
              r"\addplot[scatter, only marks, mark=*, visualization depends on={\thisrow{s} \as \ps}, scatter/@pre marker code/.append style={/tikz/mark size=\ps}]",
              r"  table[x=x, y=y, meta=y, row sep=\\] {x y s \\ " + " ".join(f"{k:.2f} {m:.1f} {0.6 + 4.4 * np.sqrt(v / vmax):.2f} \\\\"
                                                                          for k, m, v in zip(s["kl"], s["mne_share_2018"], s["exports_2018"])) + "};",
              r"\addplot[thick, color={rgb,255:red,191;green,144;blue,0}, no marks] coordinates {" + " ".join(f"({x:.2f},{beta[0] + beta[1] * np.log(x):.2f})" for x in xs) + "};",
              r"\end{axis}"]
    L.append(r"\end{tikzpicture}")
    P.save_tex("v4_fig_kl", "\n".join(L) + "\n")


def heterogeneity() -> None:
    T = [("high = low", r"$p$ value: high = low")]
    out = fe_table("v4_het", [("Panel A. Stages pooled, threshold: aggregate ratio of the stage", "E4a", "lnN x high/low (aggregate ratio), ln exports, all firms"),
                              ("Panel B. Stages pooled, threshold: export weighted median of the stage", "E4a", "lnN x high/low (median), ln exports, all firms"),
                              ("Panel C. By stage, threshold: aggregate ratio of the stage", "E4c", "lnN x stage x high/low (aggregate ratio), ln exports, all firms")],
                   ["FE3", "FE4", "FE5", "FE6"], "Table het",
                   test_rows=T + [("farm high = farm low", r"$p$ value: farm stage, high = low"), ("processing high = processing low", r"$p$ value: processing stage, high = low")])
    P.FACTS["het"] = {lab[:7]: [{"cells": r["cells"], "tests": r["tests"]} for r in res] for lab, res in out}
    TT_ = [("field crops, high = low", r"$p$ value: field crops, high = low"),
           ("horticultural and plantation crops, high = low", r"$p$ value: horticultural, high = low"),
           ("livestock and fisheries, high = low", r"$p$ value: livestock, high = low"),
           ("other processed food and beverages, high = low", r"$p$ value: other processed food, high = low")]
    out = fe_table("v4_het_med", [("Panel A. By stage", "E4c", "lnN x stage x high/low (median), ln exports, all firms"),
                                  ("Panel B. By type of production", "E4e", "lnN x type x high/low (median), ln exports, all firms")],
                   ["FE3", "FE4", "FE5", "FE6"], "Table A het median",
                   test_rows=[("farm high = farm low", r"$p$ value: farm stage, high = low"),
                              ("processing high = processing low", r"$p$ value: processing stage, high = low")] + TT_)
    P.FACTS["het_med"] = {lab[:7]: [{"cells": r["cells"], "tests": r["tests"]} for r in res] for lab, res in out}
    out = fe_table("v4_farm", [(r"Panel A. High and low capital intensity and type of production", "E4d", "Farm stage: lnN x high/low (aggregate ratio) and x type, ln exports, all firms"),
                               (r"Panel B. $\ln$ capital per worker and type of production", "E4d", "Farm stage: lnN x ln capital per worker and x type, ln exports, all firms")],
                   ["FE3", "FE4", "FE5", "FE6"], "Table farm", test_rows=T)
    P.FACTS["farm"] = {lab[:7]: [{"cells": r["cells"], "tests": r["tests"]} for r in res] for lab, res in out}
    out = fe_table("v4_cont", [(r"Panel A. $\ln$ capital per worker", "E4b", "lnN and lnN x ln capital per worker, ln exports, all firms"),
                               (r"Panel B. $\ln$ capital per worker, deviation from the mean of the stage", "E4b",
                                "lnN and lnN x ln capital per worker, demeaned within stage, ln exports, all firms")],
                   ["FE3", "FE4", "FE5", "FE6"], "Table A continuous")
    P.FACTS["cont"] = {lab[:7]: [{"cells": r["cells"]} for r in res] for lab, res in out}
    # annex: local firms, alternative regressor, type of production, Rauch and BEC
    out = fe_table("v4_het_local", [("Panel A. Stages pooled, aggregate ratio", "E4a", "lnN x high/low (aggregate ratio), ln exports, local firms"),
                                    ("Panel B. Stages pooled, median", "E4a", "lnN x high/low (median), ln exports, local firms"),
                                    ("Panel C. By stage, aggregate ratio", "E4c", "lnN x stage x high/low (aggregate ratio), ln exports, local firms")],
                   ["FE3", "FE4", "FE5", "FE6"], "Table A het local",
                   test_rows=T + [("farm high = farm low", r"$p$ value: farm stage, high = low"), ("processing high = processing low", r"$p$ value: processing stage, high = low")])
    P.FACTS["het_local"] = {lab[:7]: [{"cells": r["cells"], "tests": r["tests"]} for r in res] for lab, res in out}
    out = fe_table("v4_het_D", [("Panel A. Stages pooled, aggregate ratio", "E4a", "D x high/low (aggregate ratio), ln exports, all firms"),
                                ("Panel B. Stages pooled, median", "E4a", "D x high/low (median), ln exports, all firms"),
                                ("Panel C. By stage, aggregate ratio", "E4c", "D x stage x high/low (aggregate ratio), ln exports, all firms")],
                   ["FE3", "FE4", "FE5", "FE6"], "Table A het D",
                   test_rows=T + [("farm high = farm low", r"$p$ value: farm stage, high = low"), ("processing high = processing low", r"$p$ value: processing stage, high = low")])
    P.FACTS["het_D"] = {lab[:7]: [{"cells": r["cells"], "tests": r["tests"]} for r in res] for lab, res in out}
    TT = [("field crops, high = low", r"$p$ value: field crops, high = low"),
          ("horticultural and plantation crops, high = low", r"$p$ value: horticultural, high = low"),
          ("livestock and fisheries, high = low", r"$p$ value: livestock, high = low"),
          ("other processed food and beverages, high = low", r"$p$ value: other processed food, high = low")]
    out = fe_table("v4_type", [("Panel A. Type of production", "E4f", "lnN x type of production, ln exports, all firms"),
                               ("Panel B. Type of production and capital intensity (aggregate ratio)", "E4e", "lnN x type x high/low (aggregate ratio), ln exports, all firms")],
                   ["FE3", "FE4", "FE5", "FE6"], "Table A type", test_rows=[("field = horticultural", r"$p$ value: field crops = horticultural")] + TT)
    P.FACTS["type"] = {lab[:7]: [{"cells": r["cells"], "tests": r["tests"]} for r in res] for lab, res in out}
    out = fe_table("v4_cross", [("Panel A. Rauch (1999), conservative classification", "E7a", "lnN x Rauch, conservative, ln exports, all firms"),
                                ("Panel B. BEC end use", "E7b", "lnN x BEC end use, ln exports, all firms"),
                                ("Panel C. Inputs", "E7b", "lnN x Inputs, ln exports, all firms")],
                   ["FE3", "FE4", "FE5", "FE6"], "Table A cross",
                   test_rows=[("homogeneous = differentiated", r"$p$ value: homogeneous = differentiated"),
                              ("intermediate = consumption", r"$p$ value: intermediate = consumption"), ("inputs = other", r"$p$ value: inputs = other")])
    P.FACTS["cross"] = {lab[:7]: [{"cells": r["cells"], "tests": r["tests"]} for r in res] for lab, res in out}
    # by origin (E4g, pooled, aggregate ratio and median)
    order = P.FACTS["origin_order"]
    panels = []
    for thr, lab in (("aggregate ratio", "Panel A. Threshold: aggregate ratio of the stage"), ("median", "Panel B. Threshold: export weighted median")):
        wp = f"Pooled stages, lnN x high/low ({thr}), ln exports, all firms"
        res = [get("E4g", wp, P.COUNTRY[o]) for o in order]
        for o in order:
            show("E4g", wp, P.COUNTRY[o], f"Table A het country, {lab.split('.')[0]}, column {o}")
        panels.append((lab, res))
    labels = {v: texlab(v) for _, res in panels for r in res for v in r["regs"]}
    N.write_country_table("v4_het_country", panels, order, FE_GRID["FE4"], labels,
                          test_rows={0: [("high = low", r"$p$ value: high = low")], 1: [("high = low", r"$p$ value: high = low")]})
    P.FACTS["het_country"] = {o: {"agg": get("E4g", "Pooled stages, lnN x high/low (aggregate ratio), ln exports, all firms", P.COUNTRY[o])["tests"].get("high = low"),
                                  "med": get("E4g", "Pooled stages, lnN x high/low (median), ln exports, all firms", P.COUNTRY[o])["tests"].get("high = low")}
                              for o in order}


# ---------------------------------------------------------------------
# section 4.3: location
# ---------------------------------------------------------------------
def location() -> None:
    cols = ["lnKL", "high_mean", "high_median", "quintile"]
    blocks = [("Panel A. At least one MNE exports the product", "E5a", "D, FE origin x year + type of production"),
              ("Panel B. MNE share of the exports of the product", "E5b", "S, FE origin x year + type of production"),
              ("Panel C. First entry of an MNE", "E5d", "First entry, FE origin x year + type of production")]
    L = [r"\begin{tabular}{l*{4}{c}}", r"\toprule", " & (1) & (2) & (3) & (4) \\\\", r"\midrule"]
    P.FACTS["loc"] = {}
    for bi, (lab, sheet, wp) in enumerate(blocks):
        if bi:
            L.append(r"\midrule")
        L.append(rf"\multicolumn{{5}}{{l}}{{\textit{{{lab}}}}} \\")
        res = [get(sheet, wp, c) for c in cols]
        for i, c in enumerate(cols):
            show(sheet, wp, c, f"Table location, {lab.split('.')[0]}, column ({i + 1})")
        for v in ["lnkl", "hi_mean", "hi_median", "q2", "q3", "q4", "q5"]:
            b = [(f"{r['cells'][v][0]:.3f}{P.stars(r['cells'][v][2])}", f"({r['cells'][v][1]:.3f})") if v in r["cells"] else ("", "") for r in res]
            if any(x[0] for x in b):
                L += [f"{texlab(v)} & " + " & ".join(x[0] for x in b) + r" \\", " & " + " & ".join(x[1] for x in b) + r" \\"]
        L.append("Observations & " + " & ".join(f"{r['n']:,}" for r in res) + r" \\")
        L.append(r"$R^2$ & " + " & ".join(f"{r['r2']:.3f}" for r in res) + r" \\")
        P.FACTS["loc"][lab[:7]] = {c: r["cells"] for c, r in zip(cols, res)}
    L += [r"\midrule", r"Origin $\times$ year FE & $\checkmark$ & $\checkmark$ & $\checkmark$ & $\checkmark$ \\",
          r"Type of production FE & $\checkmark$ & $\checkmark$ & $\checkmark$ & $\checkmark$ \\", r"\bottomrule", r"\end{tabular}"]
    P.save_tex("v4_loc", "\n".join(L) + "\n")
    # annex: HS chapter FE and logit (one table), foreign and domestic MNEs (another)
    for name, where, alt in (
            ("v4_loc_alt", "Table A location", [("Panel A. At least one MNE, HS chapter FE", "E5a", "D, FE origin x year + HS chapter"),
                                                ("Panel B. At least one MNE, logit (average marginal effects)", "E5a", "Logit, FE origin x year + type of production")]),
            ("v4_loc_fd", "Table A location fd", [("Panel A. At least one foreign MNE", "E5c", "DF, FE origin x year + type of production"),
                                                  ("Panel B. At least one domestic MNE", "E5c", "DD, FE origin x year + type of production")])):
        L = [r"\begin{tabular}{l*{4}{c}}", r"\toprule", " & (1) & (2) & (3) & (4) \\\\", r"\midrule"]
        for bi, (lab, sheet, wp) in enumerate(alt):
            if bi:
                L.append(r"\midrule")
            L.append(rf"\multicolumn{{5}}{{l}}{{\textit{{{lab}}}}} \\")
            res = [get(sheet, wp, c) for c in cols]
            for i_, c in enumerate(cols):
                show(sheet, wp, c, f"{where}, {lab.split('.')[0]}, column ({i_ + 1})")
            for v in ["lnkl", "hi_mean", "hi_median", "q2", "q3", "q4", "q5"]:
                b = [(f"{r['cells'][v][0]:.3f}{P.stars(r['cells'][v][2])}", f"({r['cells'][v][1]:.3f})") if v in r["cells"] else ("", "") for r in res]
                if any(x_[0] for x_ in b):
                    L += [f"{texlab(v)} & " + " & ".join(x_[0] for x_ in b) + r" \\", " & " + " & ".join(x_[1] for x_ in b) + r" \\"]
            L.append("Observations & " + " & ".join(f"{r['n']:,}" for r in res) + r" \\")
        L += [r"\bottomrule", r"\end{tabular}"]
        P.save_tex(name, "\n".join(L) + "\n")
    e = get("E5e", "D, FE origin x year + type of production", "All")
    show("E5e", "D, FE origin x year + type of production", "All", "Text, location")
    P.FACTS["loc_other"] = e["cells"]



# ---------------------------------------------------------------------
# section 4.4: entry of the first MNE
# ---------------------------------------------------------------------
EV_OUT = [("anyXL", "Any local exports"), ("lnXL", r"$\ln$ local exports"), ("lnNL", r"$\ln$ local exporters"),
          ("NL", "Local exporters"), ("lnX", r"$\ln$ total exports"), ("N", "Number of MNEs")]
EV_EST = [("twfe", "TWFE"), ("cs", "CS"), ("sa", "SA")]


def event_results() -> pd.DataFrame:
    # Sun and Abraham on the number of MNEs has a degenerate variance and is not reported (wp_agro_v4_workbook.clean_event_results)
    from wp_agro_v4_workbook import clean_event_results
    return clean_event_results(pd.concat([pd.read_stata(P.OUT4 / f"v4_event_{c}.dta") for c in ("A", "B")], ignore_index=True))


def ev_get(e, cellset, tag, y, est, term):
    r = e[(e["cellset"] == cellset) & (e["tag"] == tag) & (e["outcome"] == y) & (e["est"] == est) & (e["term"] == term)]
    return r.iloc[0] if len(r) else None


def show_ev(cellset, tag, y, est, where):
    sheet = {("A", True): "E6a", ("B", True): "E6b", ("A", False): "E6c", ("B", False): "E6d"}[(cellset, tag in ("main", "pre3"))]
    if tag in ("placebo", "noexit", "balanced") or est == "ppml":
        sheet = "E6e"
    k = f"{sheet}|{tag}|{y}|{est}"
    old = P.SHOWN.get(k, "")
    if where not in old.split("; "):
        P.SHOWN[k] = f"{old}; {where}" if old else where


def events() -> None:
    e = event_results()
    P.FACTS["event"] = {}
    # table: average of event times 0 to 4, both cell sets, three estimators
    L = [r"\begin{tabular}{l*{6}{c}}", r"\toprule",
         r" & \multicolumn{3}{c}{Origin $\times$ product cells} & \multicolumn{3}{c}{Origin $\times$ destination $\times$ product cells} \\",
         r"\cmidrule(lr){2-4}\cmidrule(lr){5-7}",
         " & " + " & ".join(lab for _ in (0, 1) for _, lab in EV_EST) + r" \\", " & " + " & ".join(f"({i})" for i in range(1, 7)) + r" \\", r"\midrule"]
    for y, ylab in EV_OUT:
        b, s, p = [], [], []
        for cs in ("A", "B"):
            for est, _ in EV_EST:
                r = ev_get(e, cs, "main", y, est, "Post_avg")
                t = ev_get(e, cs, "main", y, est, "pre_test")
                if r is not None and np.isfinite(r["b"]):
                    b.append(f"{r['b']:.3f}{P.stars(r['p'])}"); s.append(f"({r['se']:.3f})")
                    p.append(f"[{t['p']:.3f}]" if t is not None and np.isfinite(t["p"]) else "")
                    show_ev(cs, "main", y, est, f"Table event, {ylab}")
                    P.FACTS["event"][f"{cs}|{y}|{est}"] = {"b": float(r["b"]), "se": float(r["se"]), "p": float(r["p"]),
                                                           "pre_p": float(t["p"]) if t is not None and np.isfinite(t["p"]) else None}
                else:
                    b.append(""); s.append(""); p.append("")
        L += [f"{ylab} & " + " & ".join(b) + r" \\", " & " + " & ".join(s) + r" \\", " & " + " & ".join(p) + r" \\"]
    cells, tr = [], []
    for cs in ("A", "B"):
        for est, _ in EV_EST:
            r = e[(e["cellset"] == cs) & (e["tag"] == "main") & (e["outcome"] == "anyXL") & (e["est"] == est)]
            cells.append(f"{int(r['ncells'].max()):,}" if len(r) else "")
            tr.append(f"{int(r['ntreat'].max()):,}" if len(r) else "")
    L += [r"\midrule", "Cells & " + " & ".join(cells) + r" \\", "Treated cells & " + " & ".join(tr) + r" \\", r"\bottomrule", r"\end{tabular}"]
    P.save_tex("v4_event", "\n".join(L) + "\n")
    # figure: Callaway and Sant'Anna event-time coefficients with 95 percent intervals
    terms = ["Tm4", "Tm3", "Tm2", "Tm1", "Tp0", "Tp1", "Tp2", "Tp3", "Tp4"]
    xs = [-4, -3, -2, -1, 0, 1, 2, 3, 4]
    figs = [("anyXL", "Any local exports"), ("lnXL", r"$\ln$ local exports"), ("lnNL", r"$\ln$ local exporters")]
    L = [r"\begin{tikzpicture}"]
    for row, (cs, cl) in enumerate((("A", r"Origin $\times$ product"), ("B", r"Origin $\times$ dest. $\times$ product"))):
        for col, (y, ylab) in enumerate(figs):
            pts, lo, hi = [], [], []
            for t, x in zip(terms, xs):
                if t == "Tm1":
                    pts.append((x, 0.0)); lo.append((x, 0.0)); hi.append((x, 0.0)); continue
                r = ev_get(e, cs, "main", y, "cs", t)
                if r is not None and np.isfinite(r["b"]):
                    pts.append((x, r["b"])); lo.append((x, r["b"] - 1.96 * r["se"])); hi.append((x, r["b"] + 1.96 * r["se"]))
                    show_ev(cs, "main", y, "cs", "Figure event")
            ymin = min(v for _, v in lo); ymax = max(v for _, v in hi)
            pad = 0.1 * (ymax - ymin + 1e-9)
            L += [rf"\begin{{axis}}[xshift={col * 5.4:.1f}cm, yshift={-row * 5.2:.1f}cm, width=5.6cm, height=4.8cm, xmin=-4.5, xmax=4.5, ymin={ymin - pad:.3f}, ymax={ymax + pad:.3f},",
                  r"  xtick={-4,-3,-2,-1,0,1,2,3,4}, tick label style={font=\scriptsize}, title={" + ylab + "}, title style={font=\scriptsize},",
                  r"  xlabel={Years since entry}, xlabel style={font=\scriptsize}, axis x line*=bottom, axis y line*=left"
                  + (r", ylabel={" + cl + r"}, ylabel style={font=\scriptsize}" if col == 0 else "") + "]",
                  r"\addplot[draw=none, fill={rgb,255:red,166;green,191;blue,233}, fill opacity=0.6] coordinates {"
                  + " ".join(f"({x},{v:.4f})" for x, v in lo) + " " + " ".join(f"({x},{v:.4f})" for x, v in reversed(hi)) + "} -- cycle;",
                  r"\addplot[thick, mark=*, mark size=1.2pt, color=" + N.C_EXT + "] coordinates {" + " ".join(f"({x},{v:.4f})" for x, v in pts) + "};",
                  r"\draw[gray, dashed] (axis cs:-4.5,0) -- (axis cs:4.5,0);",
                  r"\end{axis}"]
    L.append(r"\end{tikzpicture}")
    P.save_tex("v4_fig_event", "\n".join(L) + "\n")
    # annex: heterogeneity and checks (average of event times 0 to 4)
    het = [("hm_hi", "High capital intensity (aggregate ratio)"), ("hm_lo", "Low capital intensity (aggregate ratio)"),
           ("hd_hi", "High capital intensity (median)"), ("hd_lo", "Low capital intensity (median)"),
           ("st_farm", "Farm stage"), ("st_proc", "Processing stage"), ("t_field", "Field crops"), ("t_horti", "Horticultural and plantation crops"),
           ("t_live", "Livestock and fisheries"), ("t_proc", "Other processed food"), ("en_for", "Entrant: foreign MNE"), ("en_dom", "Entrant: domestic MNE")]
    chk = [("main", "Main sample"), ("pre3", "Three observed years before entry"), ("noexit", "No exit of the MNE within two years"),
           ("balanced", "Cells with exports in every year"), ("placebo", "Placebo: entry three years earlier")]
    outs = [("anyXL", "Any local exp."), ("lnXL", r"$\ln$ local exp."), ("lnNL", r"$\ln$ local exporters"), ("N", "MNEs")]
    for name, rows_, est in (("v4_event_het", het, "cs"), ("v4_event_chk", chk, "cs")):
        L = [r"\begin{tabular}{l*{8}{c}}", r"\toprule",
             r" & \multicolumn{4}{c}{Origin $\times$ product cells} & \multicolumn{4}{c}{Origin $\times$ destination $\times$ product cells} \\",
             r"\cmidrule(lr){2-5}\cmidrule(lr){6-9}", " & " + " & ".join(lab for _ in (0, 1) for _, lab in outs) + r" \\", r"\midrule"]
        for tag, lab in rows_:
            b, s = [], []
            for cs in ("A", "B"):
                for y, _ in outs:
                    r = ev_get(e, cs, tag, y, est, "Post_avg")
                    if r is not None and np.isfinite(r["b"]):
                        b.append(f"{r['b']:.3f}{P.stars(r['p'])}"); s.append(f"({r['se']:.3f})")
                        show_ev(cs, tag, y, est, f"Table A {name[3:]}, {lab}")
                        P.FACTS["event"][f"{cs}|{y}|{est}|{tag}"] = {"b": float(r["b"]), "se": float(r["se"]), "p": float(r["p"])}
                    else:
                        b.append(""); s.append("")
            L += [f"{lab} & " + " & ".join(b) + r" \\", " & " + " & ".join(s) + r" \\"]
        if name == "v4_event_chk":
            b, s = [], []
            for cs in ("A", "B"):
                r = ev_get(e, cs, "main", "XL", "ppml", "Post_avg")
                b += [f"{r['b']:.3f}{P.stars(r['p'])}" if r is not None else "", "", "", ""]
                s += [f"({r['se']:.3f})" if r is not None else "", "", "", ""]
                if r is not None:
                    show_ev(cs, "main", "XL", "ppml", "Table A event checks, PPML")
                    P.FACTS["event"][f"{cs}|XL|ppml"] = {"b": float(r["b"]), "se": float(r["se"]), "p": float(r["p"])}
            L += [r"PPML, local exports in levels & " + " & ".join(b) + r" \\", " & " + " & ".join(s) + r" \\"]
        L += [r"\bottomrule", r"\end{tabular}"]
        P.save_tex(name, "\n".join(L) + "\n")
    for cs, nm in (("A", "op"), ("B", "odp")):
        p_ = pd.read_parquet(P.V4 / f"event_{nm}.parquet")
        c = p_.drop_duplicates("cell")
        P.FACTS["event"][f"{cs}|counts"] = {"treated": int((c["gvar"] > 0).sum()), "never": int((c["gvar"] == 0).sum()),
                                            "by_year": {int(k): int(v) for k, v in c[c["gvar"] > 0].groupby("gvar").size().items()},
                                            "foreign_entrant": float((c.loc[c["gvar"] > 0, "entrant"] == "foreign").mean())}
