"""
wp_agro_v6_workbook.py  --  docs/notes/WP_paperagro_v6_master_estimates.xlsx and docs/notes/figures_v6/ (V6-18)
================================================================================================================

    WP_YEARS=2012-2018 WP_SCOPES=agro python wp_agro_v6_workbook.py

The v6 workbook is the v5 workbook (wp_agro_v5_workbook.py, run without redoing its figures) with the corrections of V6-02 and
the new sheets 10.1 to 12.7 of especificaciones_estimaciones_v6_2026-11-25.md, a Primary set table at the top of Main results,
new columns in 1.1, 1.2, 2.2 and All estimates (Request, Role, FE code, Cut variable, Group), and the figures v6_fig1 to
v6_fig7. Inputs: output/wp_2012_2018/agro/v6/ (ev6_*.dta of stata/wp_agro_v6_event.do, v6_regs_*.pkl and v6_desc_*.pkl of
wp_agro_v6_est.py, honest_v6_*.txt), data/intermediate/wp/v6/ (wp_agro_v6_data.py, wp_agro_v6_events.py).
"""
from __future__ import annotations

import os
import pickle
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("WP_HS17", "1")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_common as W  # noqa: E402
import wp_agro_v5_workbook as B  # noqa: E402
import wp_agro_v5_labels as L  # noqa: E402
import wp_agro_v6_answers as ANS  # noqa: E402

OUT6 = W.WP_OUT / "agro" / "v6"
OUT5 = W.WP_OUT / "agro" / "v5"
V6 = W.WP_INT / "v6"
FIG6 = W.ROOT / "docs" / "notes" / "figures_v6"
XLSX6 = W.ROOT / "docs" / "notes" / "WP_paperagro_v6_master_estimates.xlsx"

OUTN = dict(L.OUT)
OUTN.update({"XL_ppml": ("Exports of local firms, levels (PPML)", "Change in exports of local firms (log points)"),
             "NEWL_fw": ("New local exporters, fixed window", "Change in new local exporters"),
             "NEWL_clean": ("New local exporters without doubtful cases", "Change in new local exporters"),
             "D": ("At least one MNE (0/1)", "Change in the probability of an MNE")})
TERMS = ["Tm4", "Tm3", "Tm2", "Tm1", "Tp0", "Tp1", "Tp2", "Tp3", "Tp4"]
TLAB = {"Tm4": "4 or more years before entry (not interpreted)", "Tm3": "3 years before entry", "Tm2": "2 years before entry",
        "Tm1": "1 year before entry (base year, 0)", "Tp0": "Year of entry", "Tp1": "1 year after entry", "Tp2": "2 years after entry",
        "Tp3": "3 years after entry (not interpreted)", "Tp4": "4 or more years after entry (not interpreted)"}
ROLE = {"primary": "primary", "secondary": "secondary", "robustness": "robustness", "descriptive": "descriptive", "exploratory": "exploratory",
        "diagnostic": "diagnostic"}
EVFE = {"EV2": "EV2: cell + origin x year (by stack)", "EV3": "EV3: cell + origin x destination x year (by stack)",
        "EV4": "EV4: EV2 + HS chapter x year", "EV6": "EV6: EV3 + origin x product x year", "EV7": "EV7: EV6 + destination x product x year",
        "EV8": "EV8: EV2 + HS4 heading x year", "EV9": "EV9: EV2 + HS6 product x year", "FE4=EV3": "FE4 = EV3"}
LEV = {"A": "N1, product cells (origin x product)", "B": "N6, destination cells (origin x destination x product)", "H": "N4, heading cells"}
st = B.stars


def name(y):
    return OUTN.get(y, (y, y))[0]


def ev(level, block):
    f = OUT6 / f"ev6_{level}_{block}.dta"
    if not f.exists():
        return pd.DataFrame()
    try:
        d = pd.read_stata(f)
    except Exception:  # noqa: BLE001
        return pd.DataFrame()
    for c in ("b", "se", "p"):
        d[c] = d[c].astype(float).round(6)
    d["term"] = d["term"].replace({"p_equal_avg0": "p_equal_avg02"})
    # numeric entrant cuts: Stata stored the group as cut + 1 (1 = 0, 2 = 1)
    m = d["variant"].isin(["ent_big", "ent_incumbent"]) & d["group"].isin(["1", "2"])
    d.loc[m, "group"] = d.loc[m, "variant"] + "=" + (d.loc[m, "group"].astype(int) - 1).astype(str)
    return d


def regs(step):
    f = OUT6 / f"v6_regs_{step}.pkl"
    return pickle.load(open(f, "rb")) if f.exists() else []


def desc(step):
    f = OUT6 / f"v6_desc_{step}.pkl"
    return pickle.load(open(f, "rb")) if f.exists() else {}


def fmt(b, se, p):
    if b is None or not np.isfinite(b):
        return "", ""
    return f"{b:.3f}{st(p)}", f"({se:.3f})"


# ---------------------------------------------------------------------------------------------------------------------
# regression sheets
# ---------------------------------------------------------------------------------------------------------------------
LAB_R = {"lnN": "ln number of MNEs", "D": "At least one MNE", "RxPCI6": "x PCI6_z", "RxPCI4": "ln N x PCI4_z", "RxDEV": "ln N x PCI6_dev",
         "RxPCI12": "ln N x PCI6_hs12 (standardized)", "RxPCIp": "ln N x PCI_p (Atlas HS4)", "lnG": "ln number of MNE groups",
         "GxPCI6": "ln G x PCI6_z", "PCI6_z": "PCI6_z", "hiPCI6": "High PCI6 (low omitted)", "ncPCI6": "PCI6 not classified",
         "r_diff": "Differentiated (not differentiated omitted)", "r_nc": "Rauch not classified", "lnkl": "ln capital per worker"}


def rlabel(v, reg_of=None):
    if v in LAB_R:
        lab = LAB_R[v]
        if v == "RxPCI6" and reg_of:
            return f"{LAB_R.get(reg_of, reg_of)} x PCI6_z"
        return lab
    m = re.match(r"^(lnN|D)x(.*)$", v)
    if m:
        return f"{LAB_R[m.group(1)]} x {m.group(2).replace('o_', 'origin ')}"
    m = re.match(r"^(lnN|D)(H|R|Hom|T)_(.*)$", v)
    if m:
        return f"{LAB_R[m.group(1)]} x {m.group(3)}"
    m = re.match(r"^g(\d+)$", v)
    if m:
        return f"ln N x group {m.group(1)}"
    return v


def render_regs(recs, title, info):
    rows = [[title]] + [[x] for x in info]
    for P in dict.fromkeys(r["panel"] for r in recs):
        rr = [r for r in recs if r["panel"] == P]
        rows.append([]); rows.append([P])
        rows.append([""] + [f"({i + 1})" for i in range(len(rr))])
        rows.append(["Column"] + [str(r["col"]) for r in rr])
        rows.append(["Dependent variable"] + [{"lnX": "ln X", "lnXL": "ln XL", "lnXM": "ln XM", "lnXMpN": "ln (XM / N)"}.get(r["dep"], r["dep"]) for r in rr])
        vs = list(dict.fromkeys(v for r in rr for v in r["regs"]))
        reg0 = rr[0]["regs"][0] if rr[0]["regs"] else None
        for v in vs:
            b, s = [], []
            for r in rr:
                c = r["cells"].get(v)
                x, y = fmt(*c) if c else ("", "")
                b.append(x); s.append(y)
            rows.append([rlabel(v, reg0)] + b); rows.append([""] + s)
        for t in dict.fromkeys(t for r in rr for t in r["tests"]):
            rows.append([f"p value, test that {t.replace(' = ', ' and ')} are equal"] + [f"{r['tests'][t]:.3f}" if t in r["tests"] and np.isfinite(r["tests"][t]) else "" for r in rr])
        for t in dict.fromkeys(t for r in rr for t in r.get("contrasts", {})):
            rows.append([t] + [fmt(*r["contrasts"][t])[0] if t in r.get("contrasts", {}) else "" for r in rr])
        alts = list(dict.fromkeys(a for r in rr for a in r.get("alt", {})))
        key = next((v for v in vs if v not in ("lnN", "D")), None)
        for a in alts:
            rows.append([f"p value of {rlabel(key, reg0)} with {a}"] + [f"{r['alt'][a][key][1]:.3f}" if a in r.get("alt", {}) and key in r["alt"][a] else "" for r in rr])
        if any("permutation_p" in r for r in rr):
            rows.append(["Permutation p (1,000 reassignments of PCI6_z within stage x type)"] + [f"{r['permutation_p']:.3f}" if "permutation_p" in r else "" for r in rr])
        rows.append(["Observations"] + [f"{r['n']:,}" if r["n"] else r["status"] for r in rr])
        rows.append(["R-squared"] + [f"{r['r2']:.3f}" if np.isfinite(r["r2"]) else "" for r in rr])
        rows.append(["Within R-squared"] + [f"{r['r2w']:.3f}" if np.isfinite(r["r2w"]) else "" for r in rr])
        rows.append(["Fixed effects (code)"] + [r["fe"] for r in rr])
        rows.append(["Cluster (code)"] + [r["cluster"] for r in rr])
        rows.append(["Weights"] + [r.get("weights") or "none" for r in rr])
        rows.append(["Sample"] + [r.get("sample", "") for r in rr])
        rows.append(["Role"] + [r["role"] for r in rr])
    rows.append(["Standard errors in parentheses. *** p<0.01, ** p<0.05, * p<0.1. FE, FL, EV and cluster codes are in the Glossary."])
    return rows


def longs_from_regs(recs, sheet, cut=""):
    out = []
    for r in recs:
        for v, c in r["cells"].items():
            out.append({"Table": sheet, "Panel": r["panel"], "Column": str(r["col"]), "Dependent variable": r["dep"], "Regressor": rlabel(v, r["regs"][0]),
                        "Coefficient": c[0], "Standard error": c[1], "p value": c[2], "Stars": st(c[2]), "Observations": r["n"], "R-squared": r["r2"],
                        "Within R-squared": r["r2w"], "Fixed effects": r["fe"], "Clustered by": r["cluster"], "Sample": r.get("sample", ""),
                        "Estimator": "OLS", "Column in the note": "Not shown", "Request": r["request"], "Role": r["role"], "FE code": r["fe"],
                        "Cut variable": cut, "Group": ""})
        for t, p in r["tests"].items():
            out.append({"Table": sheet, "Panel": r["panel"], "Column": str(r["col"]), "Dependent variable": r["dep"], "Regressor": f"Test: {t}",
                        "p value": p, "Observations": r["n"], "Fixed effects": r["fe"], "Clustered by": r["cluster"], "Request": r["request"],
                        "Role": r["role"], "FE code": r["fe"], "Cut variable": cut, "Group": ""})
    return out


# ---------------------------------------------------------------------------------------------------------------------
# event-study sheets
# ---------------------------------------------------------------------------------------------------------------------
def baseline(level, outs, cond=None):
    s = pd.read_stata(V6 / f"ev6_{level}_stk.dta")
    s = s[s["inR"] == 1]
    if cond is not None:
        s = s[cond(s)]
    pre = s[s["k"] == -1]
    rows = []
    for y in outs:
        yy = "XL" if y == "XL_ppml" else y
        if yy not in pre:
            continue
        for g, lab in ((1, "treated"), (0, "controls")):
            x = pre.loc[pre["treat"] == g, yy].dropna()
            rows.append({"Outcome": name(y), "Group": lab, "Mean in g - 1": x.mean(), "Median": x.median(), "90th percentile": x.quantile(0.9),
                         "Share of zeros": (x == 0).mean(), "Cell-stack pairs": len(x)})
    per = s[s["treat"] == 1].groupby("k")["D"].mean().rename("Share of treated cells with an MNE (D = 1)").reset_index()
    stk = s.groupby(["stack", "treat"])["cell"].nunique().unstack().rename(columns={0: "Comparison cells", 1: "Entered cells"}).reset_index()
    org = s[s["treat"] == 1].drop_duplicates(["cell", "stack"]).groupby(["country_orig", "stack"]).size().unstack(fill_value=0).reset_index()
    return pd.DataFrame(rows), per, stk, org


def v5_number(level):
    """v5 number for the same outcome: rule g_ps, Callaway and Sant'Anna, average 0 to 4 (sheets 4.1 and 5.1)."""
    e = B.load_events()
    x = e[(e["cellset"] == level) & (e["block"] == "std") & (e["sample"] == "g_ps") & (e["est"] == "cs") & (e["term"] == "Post_avg") & (e["group"] == "all")]
    return {r["outcome"]: (r["b"], r["se"], r["p"]) for _, r in x.iterrows()}


def render_ev(d, title, info, outs=None, v5=None, base=None):
    rows = [[title]] + [[x] for x in info]
    if not len(d):
        rows.append(["Not estimated (no results file)."])
        return rows
    for (var, grp), x in d.groupby(["variant", "group"], sort=False):
        ys = [y for y in (outs or list(dict.fromkeys(x["outcome"]))) if y in set(x["outcome"])]
        if not ys:
            continue
        cols = list(dict.fromkeys((y, e) for y, e in zip(x["outcome"], x["est"]) if y in ys))
        cols = sorted(cols, key=lambda c: ys.index(c[0]))
        rows.append([]); rows.append([f"Variant: {var}. Group: {grp}. Fixed effects: {EVFE.get(x['fe'].iloc[0], x['fe'].iloc[0])}. Cluster: {x['clus'].iloc[0]}."])
        rows.append(["Outcome"] + [name(y) for y, e in cols])
        rows.append(["Estimator"] + [{"ols": "OLS, aligned stacks", "ppml": "PPML, aligned stacks"}.get(e, e) for y, e in cols])

        def get(y, e, term):
            r = x[(x["outcome"] == y) & (x["est"] == e) & (x["term"] == term)]
            return r.iloc[0] if len(r) else None
        for t in TERMS:
            b, s = [], []
            for y, e in cols:
                if t == "Tm1":
                    b.append("0 (base)"); s.append(""); continue
                r = get(y, e, t)
                u, v = fmt(r["b"], r["se"], r["p"]) if r is not None else ("", "")
                b.append(u); s.append(v)
            rows += [[TLAB[t]] + b, [""] + s]
        for t, lab in (("Avg02", "Average effect, years 0 to 2 (main)"), ("Avg04", "Average effect, years 0 to 4 (continuity with v5)")):
            b, s, ci = [], [], []
            for y, e in cols:
                r = get(y, e, t)
                u, v = fmt(r["b"], r["se"], r["p"]) if r is not None else ("", "")
                b.append(u); s.append(v)
                ci.append(f"[{r['b'] - 1.96 * r['se']:.3f}, {r['b'] + 1.96 * r['se']:.3f}]" if r is not None and np.isfinite(r["b"]) else "")
            rows += [[lab] + b, [""] + s]
            if t == "Avg02":
                rows.append(["95 percent interval of the main average"] + ci)
        rows.append(["p value, no difference before entry (b-3 = b-2 = 0; for anyXL b-2 is 0 by construction, the test rests on b-3)"] +
                    [f"{get(y, e, 'pre_test')['p']:.3f}" if get(y, e, "pre_test") is not None else "" for y, e in cols])
        if base is not None:
            rows.append(["Effect as a percentage of the treated mean in g - 1"] + [
                (lambda r, m: f"{100 * r['b'] / m:.1f}" if r is not None and m and np.isfinite(m) and m != 0 else "")(
                    get(y, e, "Avg02"), base.get(y)) for y, e in cols])
        if v5 is not None:
            rows.append(["v5 number (rule g_ps, Callaway and Sant'Anna, average 0 to 4)"] + [fmt(*v5[y])[0] if y in v5 else "" for y, e in cols])
        rows.append(["Observations"] + [f"{int(get(y, e, 'cells')['N']):,}" if get(y, e, "cells") is not None else "" for y, e in cols])
        rows.append(["Entered cells"] + [f"{int(get(y, e, 'cells')['ntreat']):,}" if get(y, e, "cells") is not None else "" for y, e in cols])
        rows.append(["Comparison cells"] + [f"{int(get(y, e, 'cells')['nclus']):,}" if get(y, e, "cells") is not None else "" for y, e in cols])
        rows.append(["Clusters"] + [f"{int(get(y, e, 'clusters')['ntreat']):,}" if get(y, e, "clusters") is not None else "" for y, e in cols])
        for t in ("Tm3", "Tm2", "Tp0", "Tp1", "Tp2"):
            rows.append([f"Entered cells / clusters identifying: {TLAB[t]}"] + [
                (lambda r: f"{int(r['ntreat'])} / {int(r['nclus'])}" if r is not None and np.isfinite(r["ntreat"]) else "")(get(y, e, t)) for y, e in cols])
        bad = x[x["status"] != "ok"]
        if len(bad):
            rows.append(["Not estimated"] + ["; ".join(bad.loc[bad["outcome"] == y, "status"].unique()) for y, e in cols])
    rows.append(["Standard errors in parentheses. *** p<0.01, ** p<0.05, * p<0.1. Stacks aligned by cohort (A.7): each comparison cell enters the "
                 "stack of cohort g only if it meets R(g) in that year; fixed effects interacted with the stack."])
    return rows


def ev_longs(d, sheet, request, role_fn, level):
    out = []
    for _, r in d[d["term"].isin(TERMS + ["Avg02", "Avg04", "pre_test"]) | d["term"].str.contains("_c20|AvgW|Avg02_c|p_equal", regex=True)].iterrows():
        out.append({"Table": sheet, "Panel": f"{LEV.get(level, level)}; {r['variant']}; {r['group']}", "Column": f"{name(r['outcome'])}, {r['est']}",
                    "Dependent variable": name(r["outcome"]), "Regressor": TLAB.get(r["term"], r["term"]), "Coefficient": r["b"], "Standard error": r["se"],
                    "p value": r["p"], "Stars": st(r["p"]), "Observations": r["N"], "Fixed effects": EVFE.get(r["fe"], r["fe"]), "Clustered by": r["clus"],
                    "Sample": "aligned stacks, R(g)", "Estimator": r["est"], "Column in the note": "Not shown", "Request": request,
                    "Role": role_fn(r), "FE code": r["fe"], "Cut variable": r["variant"] if r["block"] in ("het", "hetplc") else "", "Group": r["group"]})
    return out


# ---------------------------------------------------------------------------------------------------------------------
def honest_v6():
    rows = []
    for f in OUT6.glob("honest_v6_*.txt"):
        t = f.read_text(errors="ignore")
        m = re.match(r"honest_v6_(\w)_(\w+?)_(\w+)\.txt", f.name)
        if not m:
            continue
        lev, tag, y = m.groups()
        for kind in ("RM", "SD"):
            blk = t.split(f"HONEST {kind}")[1] if f"HONEST {kind}" in t else ""
            blk = blk.split("HONEST")[0]
            tab = re.findall(r"\|\s*([\d.]+|\.)\s*\|\s*(-?[\d.]+)\s*\|\s*(-?[\d.]+)\s*\|", blk)
            orig = [r for r in tab if r[0] == "."]
            grid = [(float(a), float(b), float(c)) for a, b, c in tab if a != "."]
            brk = next((M for M, lb, ub in grid if lb <= 0 <= ub), np.nan)
            rows.append({"Level": lev, "Sample": tag, "Outcome": name(y),
                         "Restriction": "relative magnitudes (Mbar)" if kind == "RM" else "linear trend, smoothness (M)",
                         "95 percent interval of the average 0 to 2, no violation": f"[{orig[0][1]}, {orig[0][2]}]" if orig else "",
                         "Breakdown value (smallest M at which the interval includes 0)": brk,
                         "Interval at each M": "; ".join(f"{M:g}: [{lb:.3f}, {ub:.3f}]" for M, lb, ub in grid[:12])})
    return pd.DataFrame(rows)


def chk_table(d):
    rows = []
    for (var, y, e, fe, cl), x in d.groupby(["variant", "outcome", "est", "fe", "clus"], sort=False):
        t = x.set_index("term")
        if "support" in var:
            for k in ("support_EV8", "support_EV9"):
                if k in t.index:
                    rows.append({"Row": k.replace("support_", "Support of "), "Outcome": "", "Average 0 to 2": None,
                                 "Note": f"{int(t.loc[k, 'ntreat'])} of {int(t.loc[k, 'nclus'])} entered cells have a comparison cell of the same "
                                         + ("heading" if k.endswith("8") else "product in another origin") + " in their stack"})
            continue
        a = t.loc["Avg02"] if "Avg02" in t.index else None
        rows.append({"Row": var, "Outcome": name(y), "Estimator": e, "FE code": fe, "Cluster": cl,
                     "Average 0 to 2": a["b"] if a is not None else None, "SE": a["se"] if a is not None else None, "p": a["p"] if a is not None else None,
                     "Stars": st(a["p"]) if a is not None else "", "95 percent interval": f"[{a['b'] - 1.96 * a['se']:.3f}, {a['b'] + 1.96 * a['se']:.3f}]" if a is not None else "",
                     "Pre-trend p": t.loc["pre_test", "p"] if "pre_test" in t.index else None,
                     "Entered cells": t.loc["cells", "ntreat"] if "cells" in t.index else None,
                     "Role": "secondary (S2)" if (var == "EV9" and y == "NEWL") else "robustness",
                     "Note": "; ".join(x.loc[x["status"] != "ok", "status"].unique())})
    return pd.DataFrame(rows)


def bridge_table(level, br, main, regsb, v5ref):
    outs = ["lnX", "lnXL", "lnNL", "anyXL", "NEWL"]
    rows = []
    for y in outs:
        x = br[br["outcome"] == y]

        def g(var, term):
            r = x[(x["variant"] == var) & (x["term"] == term)]
            return r.iloc[0] if len(r) else None
        p2a = next((r for r in regsb if r["panel"].startswith(f"Level {level},") and r["dep"] == y), None)
        m = main[(main["outcome"] == y) & (main["est"] == "ols") & (main["variant"] == "main")]
        a02 = m[m["term"] == "Avg02"]; a04 = m[m["term"] == "Avg04"]
        p3, fsd, fsn = g("P3", "Post"), g("P3", "FS_D"), g("P3", "FS_N")
        ratio = p3["b"] / fsd["b"] if p3 is not None and fsd is not None and fsd["b"] else np.nan
        row = {"Level": level, "Outcome": name(y)}
        for lab, r in (("P0", g("P0", "D")), ("P1", g("P1", "D")), ("P2 (event panel)", g("P2b", "D")), ("P3 (Post)", p3),
                       ("First stage of D on Post", fsd), ("First stage of N on Post", fsn), ("P4 (Post x Treat, stacks)", g("P4", "PostxTreat"))):
            row[lab] = r["b"] if r is not None else np.nan
            row[f"{lab} SE"] = r["se"] if r is not None else np.nan
        row["P2 (regression code)"] = p2a["cells"]["D"][0] if p2a and "D" in p2a["cells"] else np.nan
        row["P2 (regression code) SE"] = p2a["cells"]["D"][1] if p2a and "D" in p2a["cells"] else np.nan
        row["P3 / first stage of D"] = ratio
        row["P5 (average 0 to 2)"] = a02["b"].iloc[0] if len(a02) else np.nan
        row["P5 SE"] = a02["se"].iloc[0] if len(a02) else np.nan
        row["P5 (average 0 to 4)"] = a04["b"].iloc[0] if len(a04) else np.nan
        row["v5 reference (destination cells, EV3, OLS, average 0 to 4)"] = v5ref.get(y, np.nan)
        rows.append(row)
    return pd.DataFrame(rows)


def dg_verdict(bt):
    """DG: the two versions of P2 coincide; P3 / first stage within the 95 percent interval of P2; P4 within the interval of P5."""
    out = []
    for _, r in bt.iterrows():
        if r["Outcome"] not in (name("lnX"), name("lnXL")):
            continue
        p2, s2 = r["P2 (event panel)"], r["P2 (event panel) SE"]
        c1 = np.isfinite(r["P2 (regression code)"]) and abs(r["P2 (regression code)"] - p2) < 1e-6 + 1e-3 * abs(p2)
        c2 = np.isfinite(r["P3 / first stage of D"]) and (p2 - 1.96 * s2 <= r["P3 / first stage of D"] <= p2 + 1.96 * s2)
        c3 = np.isfinite(r["P4 (Post x Treat, stacks)"]) and (r["P5 (average 0 to 2)"] - 1.96 * r["P5 SE"] <= r["P4 (Post x Treat, stacks)"] <= r["P5 (average 0 to 2)"] + 1.96 * r["P5 SE"])
        out.append({"Level": r["Level"], "Outcome": r["Outcome"], "P2 versions coincide": c1, "P3 / first stage within the 95% interval of P2": c2,
                    "P4 within the 95% interval of P5": c3, "DG met": bool(c1 and c2 and c3)})
    return pd.DataFrame(out)


def who_table():
    f = pd.read_parquet(V6 / "ev6_A_newfirms.parquet")
    s = pd.read_stata(V6 / "ev6_A_stk.dta", columns=["cell", "stack", "year", "k", "treat", "inR", "high_PCI6", "type"])
    s = s[(s["inR"] == 1) & s["k"].between(0, 2)]
    m = s.merge(f, on=["cell", "year"], how="inner")
    rows = []
    for (tr, k), x in m.groupby(["treat", "k"]):
        r = {"Group": "entered cells" if tr == 1 else "comparison cells", "Event time": k, "New local exporters (firm x stack)": len(x)}
        for p in ("NEWL_denovo", "NEWL_div_hs4", "NEWL_div_other"):
            r[f"{p}, share"] = (x["prov"] == p).mean()
        r["persist (exports again in t + 1), share"] = x["persist"].mean()
        r["samedest, share"] = x["samedest"].mean() if tr == 1 else np.nan
        r["dest_subset, share"] = x["dest_subset"].mean() if tr == 1 else np.nan
        r["big, share"] = x["big"].mean()
        r["Median relative size (first-year exports / cell median)"] = x["relsize"].median()
        rows.append(r)
    t1 = pd.DataFrame(rows)
    t2 = m.groupby(["treat", "high_PCI6"]).size().unstack(fill_value=0).reset_index()
    t3 = m.groupby(["treat", "type"]).size().unstack(fill_value=0).reset_index()
    val = pd.DataFrame([{"Check": "exporter class fixed over time (question 11)", "Result": "yes: the class comes from the firm match, no acquisition date"},
                        {"Check": "share of big among new exporters, entered cells", "Result": f"{m.loc[m['treat'] == 1, 'big'].mean():.3f}"},
                        {"Check": "share of big among new exporters, comparison cells", "Result": f"{m.loc[m['treat'] == 0, 'big'].mean():.3f}"},
                        {"Check": "share of dest_subset among new exporters, entered cells", "Result": f"{m.loc[m['treat'] == 1, 'dest_subset'].mean():.3f}"},
                        {"Check": "row 11 of 12.2 (NEWL without big or dest_subset)", "Result": "see sheet 12.2"}])
    return t1, t2, t3, val


# ---------------------------------------------------------------------------------------------------------------------
# figures
# ---------------------------------------------------------------------------------------------------------------------
def figures(evs, v5ev, loo, figdata, index):
    FIG6.mkdir(parents=True, exist_ok=True)
    B.FIG = FIG6  # relative folders in the index
    A = evs["A_main"]; Bm = evs["B_main"]
    # fig1: NEWL and anyXL, -3 to +2, with v5
    panels = []
    for y in ("NEWL", "anyXL"):
        a = A[(A["outcome"] == y) & (A["est"] == "ols") & (A["variant"] == "main") & A["term"].isin(["Tm3", "Tm2", "Tp0", "Tp1", "Tp2"])].assign(series="v6")
        v = v5ev[(v5ev["cellset"] == "A") & (v5ev["block"] == "std") & (v5ev["sample"] == "g_ps") & (v5ev["est"] == "cs") & (v5ev["outcome"] == y)
                 & (v5ev["group"] == "all") & v5ev["term"].isin(["Tm3", "Tm2", "Tp0", "Tp1", "Tp2"])].assign(series="v5")
        panels.append((pd.concat([a, v]), "series", lambda k: {"v6": "v6: aligned stacks, OLS", "v5": "v5: rule g_ps, Callaway and Sant'Anna"}[k], name(y), OUTN[y][1]))
    B.grid_fig(panels, 2, FIG6, "v6_fig1_product_cells_new_exporters_and_local_exports", "Product cells: new local exporters and local exports, v6 against v5",
               "Aligned stacks: each comparison cell enters the stack of cohort g only if it has exports in g - 1 and g - 2. Fixed effects: cell and "
               "origin x year, by stack. Standard errors clustered by product cell. Bars are 95 percent confidence intervals.", index, figdata,
               "V6-11. NEWL (T5) and anyXL (T6), coefficients -3 to +2, with the v5 series.", size=(12, 5))
    # fig2: NEWL by cohort
    c = evs["A_cohort"]
    c = c[(c["outcome"] == "NEWL") & c["term"].str.match(r"^T[mp]\d_c20\d\d$")].copy()
    c["series"] = c["term"].str[-4:]; c["term"] = c["term"].str[:3]
    B.event_fig(c, "series", lambda k: f"cohort {k}", FIG6, "v6_fig2_new_exporters_by_cohort", "Product cells: new local exporters by entry cohort",
                OUTN["NEWL"][1], "One estimation with Treat x event time x cohort. Aligned stacks, fixed effects cell and origin x year by stack, clusters by "
                "product cell. 2017 is the year HS 2017 enters into force.", index, figdata, "V6-11. NEWL by cohort.")
    # fig3: destination cells, panels C and D
    f = evs["B_fe"]
    panels = []
    for var, lab in (("panel C, event (i), pure controls, EV3", "Event (i): MNE new to the product, pure controls"),
                     ("panel D, event (ii), all controls, EV6", "Event (ii): expansion of destinations, EV6")):
        for y in ("lnXL", "anyXL"):
            x = f[(f["variant"] == var) & (f["outcome"] == y)].assign(series="b")
            panels.append((x, "series", lambda k: "", f"{lab}\n{name(y)}", OUTN[y][1]))
    B.grid_fig(panels, 2, FIG6, "v6_fig3_destination_cells_split_event", "Destination cells: the two kinds of first entry",
               "Aligned stacks in origin x destination x product cells. Clusters: origin and destination pair and origin x product (two-way). Bars are "
               "95 percent confidence intervals.", index, figdata, "V6-13. lnXL and anyXL, panels C and D.", size=(12, 8))
    # fig4: bridge P6
    panels = []
    for lev, d in (("B", Bm), ("A", A)):
        for y in ("lnX", "lnXL", "lnNL", "anyXL", "NEWL"):
            x = d[(d["outcome"] == y) & (d["est"] == "ols") & (d["variant"] == "main") & d["term"].isin(["Tm3", "Tm2", "Tp0", "Tp1", "Tp2"])].assign(series="b")
            panels.append((x, "series", lambda k: "", f"{'Destination' if lev == 'B' else 'Product'} cells: {name(y)}", ""))
    B.grid_fig(panels, 5, FIG6, "v6_fig4_bridge_event_paths", "Bridge to the regressions: event paths of the five outcomes (P6)",
               "Coefficients from -3 to +2 of the aligned stacked event studies (destination cells EV3, product cells EV2). Bars are 95 percent "
               "confidence intervals.", index, figdata, "V6-16, column P6.", size=(18, 7))
    # fig5: leave one out
    plt = B._plt()
    if loo is not None and len(loo):
        fig, ax = plt.subplots(1, 2, figsize=(12, 5.5))
        for a, dep in zip(ax, ("ln X", "ln XL")):
            x = loo[loo["Dependent variable"] == dep].reset_index(drop=True)
            a.errorbar(x["Coefficient of ln N x PCI6_z"], range(len(x)), xerr=1.96 * x["SE (CL2)"], fmt="o", color="#1f4e79", ms=4, capsize=2)
            a.set_yticks(range(len(x))); a.set_yticklabels([e.replace("product ", "without HS ").replace("origin ", "without ") for e in x["Excluded"]], fontsize=7)
            a.axvline(0, color="grey", ls="--", lw=0.6); a.set_title(f"{dep} on ln N and ln N x PCI6_z, FE4", fontsize=9)
            a.set_xlabel("Coefficient of ln N x PCI6_z (95 percent interval, CL2)")
            for i, rr in x.iterrows():
                figdata.append({"Figure file": "v6_fig5_leave_one_out", "Panel": dep, "Series": rr["Excluded"], "Coefficient": rr["Coefficient of ln N x PCI6_z"],
                                "Lower 95": rr["Coefficient of ln N x PCI6_z"] - 1.96 * rr["SE (CL2)"], "Upper 95": rr["Coefficient of ln N x PCI6_z"] + 1.96 * rr["SE (CL2)"]})
        fig.suptitle("Leave one out: the ten largest products and the nine origins, one at a time", fontsize=11)
        fig.tight_layout(rect=(0, 0, 1, 0.95))
        B.save(fig, FIG6, "v6_fig5_leave_one_out", index, "Leave one out of the complexity interaction", "V6-07. 19 coefficients per dependent variable.")
        plt.close(fig)
    index.append({"Folder": "figures_v6", "File": "v6_fig6 (not produced)", "Title": "Heading cells (HS4)",
                  "What it shows": "Not estimable: 86 entered headings with R(g), below the threshold of 150 (sheet 10.2)."})
    # fig7: heterogeneity, average 0 to 2 by group
    h = evs["A_het"]
    h = h[(h["term"] == "Avg02") & (h["clus"] == "CL-op") & h["variant"].isin(["high_PCI6", "rauch_bin_con", "rauch_full_con", "type"]) & h["outcome"].isin(["NEWL", "anyXL"])]
    if len(h):
        fig, ax = plt.subplots(2, 4, figsize=(16, 7.5))
        for i, y in enumerate(("NEWL", "anyXL")):
            for j, cut in enumerate(("high_PCI6", "rauch_bin_con", "rauch_full_con", "type")):
                a = ax[i, j]; x = h[(h["outcome"] == y) & (h["variant"] == cut)].reset_index(drop=True)
                a.errorbar(range(len(x)), x["b"], yerr=1.96 * x["se"], fmt="o", color="#1f4e79", capsize=3)
                a.set_xticks(range(len(x))); a.set_xticklabels([g[:22] for g in x["group"]], fontsize=6.5, rotation=20)
                a.axhline(0, color="grey", ls="--", lw=0.6); a.set_title(f"{name(y)} by {cut}", fontsize=8.5)
                for _, rr in x.iterrows():
                    figdata.append({"Figure file": "v6_fig7_heterogeneity", "Panel": f"{y} by {cut}", "Series": rr["group"], "Coefficient": rr["b"],
                                    "Lower 95": rr["b"] - 1.96 * rr["se"], "Upper 95": rr["b"] + 1.96 * rr["se"]})
        fig.suptitle("Product cells: average effect of years 0 to 2 by group (one estimation per cut, Treat x event time x group)", fontsize=11)
        fig.tight_layout(rect=(0, 0, 1, 0.95))
        B.save(fig, FIG6, "v6_fig7_heterogeneity", index, "Heterogeneity in product cells", "V6-14. NEWL and anyXL by group, four product cuts.")
        plt.close(fig)


# ---------------------------------------------------------------------------------------------------------------------
def build_hook(state):
    def hook(new, put_df, put_rows, text_sheet, wb):
        longs = []
        evs, v5A, v5B = state["evs"], state["v5A"], state["v5B"]
        # 10.1
        put_df(new("10.1 Definitions and answers", "Answers to the sixteen definition questions", "V6-01"), "Definitions and answers (V6-01). Role: no estimations.",
               [("", pd.DataFrame(ANS.ANSWERS, columns=["Question", "Topic", "Answer", "Script and line"]))])
        # 10.2
        U = pickle.load(open(V6 / "ev6_universe.pkl", "rb"))
        put_df(new("10.2 Universe and support", "Cells by status and level, who enters, HS codes, alternative events", "V6-10"),
               "Universe and support (V6-10). Role: descriptive. Cells with positive exports in at least one year 2012-2018.",
               [("1. Cells by status, levels A (op), B (odp), H (oh); R(g) = exports in g - 1 and g - 2", U["status"]),
                ("1. Cells by status and origin", U["status_by_origin"]),
                ("2. Decision for the heading level (N4): threshold 150 entered headings with R(g)", U["heading_threshold"]),
                ("3. Who enters: activity of the entrant group from the origin in g - 1 (product cells)", U["who_enters"]),
                ("4. HS codes without a one-to-one correspondence with HS 2012 (hs_n1): first entries by cohort", U["hs_n1_entries"]),
                ("4. New local exporters at k = 0 in entered cells, and the part in hs_n1 codes, by cohort", U["hs_n1_newl_k0"]),
                ("4. New local exporters by year (all product cells) and the part in hs_n1 codes", U["hs_n1_newl_by_year"]),
                ("5. Alternative events, counts only (threshold for the second tier: 300 in A)", U["alt_events"]),
                ("5. Destination cells: type of first entry and of comparison cell", U["B_event_types"])],
               "Origin x chapter, origin x type of production and origin-destination pair are not counted separately: at the heading level already "
               "99 percent of exports are in cells with an MNE since 2012, so coarser levels have almost no first entries.")
        # 10.3
        D = pickle.load(open(V6 / "classes_v6_desc.pkl", "rb"))
        put_df(new("10.3 New classifications", "Construction, coverage and correlations of PCI6, PCI4, ubiquity, binary Rauch and hs_n1", "V6-03, V6-04"),
               "New classifications (V6-03, V6-04). Source: Observatory of Economic Complexity (OEC), public API, downloaded 2026-11-27.",
               [("(a, b) Source and coverage", D["coverage"]), ("(b) PCI6_hs12: HS 2017 products that average or inherit HS 2012 codes", D["hs12_mapping"]),
                ("(c) Spearman correlations", D["spearman"]), ("(d) high_PCI6 against high_PCI of v5", D["high_PCI6_x_high_PCI"]),
                ("(e) Composition of high_PCI6 by type, stage and binary Rauch", D["high_PCI6_composition"]),
                ("Binary Rauch: products and export shares", D["rauch_bin_counts"]), ("Binary Rauch by type of production", D["rauch_bin_x_type"]),
                ("Binary Rauch by stage", D["rauch_bin_x_stage"]), ("hs_n1", D["hs_n1_counts"]),
                ("Ubiquity by year (countries with RCA >= 1)", D["ubiquity_by_year"]),
                ("Cut and scale", pd.DataFrame([D["meta"]]))])
        # 11.x
        info = lambda req, cut, smp, fe, cl, role: [f"Request: {req}. Cut column: {cut}. Sample: {smp}. Fixed effects: {fe}. Cluster: {cl}. Role: {role}."]
        for step, sheet, title, what, req, cut in (
                ("pci", "11.1 Complexity, PCI6", "Association by complexity with six-digit PCI (T2 and T3 in panel A)", "Association by complexity (T2, T3), panels A to H", "V6-05", "PCI6_z, high_PCI6"),
                ("rauch", "11.2 Rauch binary", "Association and location by binary Rauch and by the three classes (S1 in panel A)", "Association and location by binary Rauch (S1)", "V6-06", "rauch_bin_con, rauch_bin_lib, rauch_full_con, rauch_hom_con"),
                ("race", "11.3 Product traits together", "Horse race between product traits (T4 in column 10, FE4) and leave one out", "Horse race (T4) and leave one out", "V6-07", "PCI6_z, DIFF, FIELD, PROC, ubiq_z"),
                ("loc", "11.4 Location, PCI6", "Location by complexity: unweighted (T1), weighted, conditional; concentration", "Location (T1), concentration", "V6-08", "PCI6_z, high_PCI6")):
            rr = regs(step)
            ws = new(sheet, what, req)
            put_rows(ws, render_regs(rr, f"{title} (estimation plan: {req})",
                                     info(req, cut, "odpy cells (association) or opy cells (location)", "FE3 to FE6; FL1 to FL3", "CL2 (association), CL-hs6 (location)",
                                          "primary in the rows marked T1 to T4; the others as stated in the Role row")))
            dd = desc(step)
            r0 = ws.max_row + 2
            for k, df in dd.items():
                ws.cell(row=r0, column=1, value={"leave_one_out": "Leave one out (FE4, CL2)", "concentration": "D. Concentration by group (descriptive)",
                                                 "top20_groups": "The twenty groups with the largest agricultural exports of foreign affiliates (top20)"}.get(k, k))
                r0 += 1
                ws.cell(row=r0, column=1, value=None)
                for j, cn in enumerate(df.columns):
                    ws.cell(row=r0, column=j + 1, value=str(cn))
                for _, row in df.iterrows():
                    r0 += 1
                    for j, v in enumerate(row.tolist()):
                        ws.cell(row=r0, column=j + 1, value=(None if isinstance(v, float) and not np.isfinite(v) else (round(v, 4) if isinstance(v, float) else (str(v) if not isinstance(v, (int, float, str)) else v))))
                r0 += 2
            longs += longs_from_regs(rr, sheet, cut)
        # V6-09: new columns in 1.1, 1.2, 2.2 (appended blocks)
        cap = regs("cap"); dcap = desc("cap")
        for sheet, dep in (("1.1 Presence by stage", "D"), ("1.2 Number and share by stage", "S")):
            ws = wb[sheet]; r0 = ws.max_row + 2
            ws.cell(row=r0, column=1, value=f"Added in v6 (V6-09, descriptive): {dep} on ln capital per worker weighted by X_opy, FL1, cluster HS6")
            for r in [x for x in cap if x["dep"] == dep]:
                r0 += 1
                c = r["cells"]["lnkl"]
                ws.cell(row=r0, column=1, value=r["panel"]); ws.cell(row=r0, column=2, value=f"{c[0]:.3f}{st(c[2])} ({c[1]:.3f})"); ws.cell(row=r0, column=3, value=f"N = {r['n']:,}")
        ws = wb["2.2 By farm type or industry"]; r0 = ws.max_row + 2
        ws.cell(row=r0, column=1, value="Added in v6 (V6-09, descriptive): slope of the group coefficients on ln capital per worker without group 21 (farm) and group 45 (processing), ln N, FE4")
        sl = dcap.get("slopes_2_2", pd.DataFrame())
        r0 += 1
        for j, cn in enumerate(sl.columns):
            ws.cell(row=r0, column=j + 1, value=str(cn))
        for _, row in sl.iterrows():
            r0 += 1
            for j, v in enumerate(row.tolist()):
                ws.cell(row=r0, column=j + 1, value=round(v, 4) if isinstance(v, float) else v)
        longs += longs_from_regs(cap, "1.1 / 1.2 (V6-09)")
        # 12.1
        bA, per, stk, org = baseline("A", ["anyXL", "lnXL", "XL_ppml", "lnX", "NL", "lnNL", "NEWL", "EXITL", "SURVL", "N", "D"])
        bmean = {r["Outcome"]: r["Mean in g - 1"] for _, r in bA[bA["Group"] == "treated"].iterrows()}
        bmean = {y: bmean.get(name(y)) for y in OUTN}
        main = evs["A_main"]
        ws = new("12.1 Product cells, aligned", "Level N1 (T5 and T6), by cohort, placebo, first stage, baseline means", "V6-11")
        put_rows(ws, render_ev(main, "Product cells, cohort-aligned stacks (V6-11): what happens to local firms after the first MNE enters",
                               ["Request: V6-11. Cut column: none. Sample: cohort-aligned stacks, R(g). Fixed effects: EV2. Cluster: CL-op. Role: primary for "
                                "NEWL average 0 to 2 (T5) and anyXL average 0 to 2 (T6); exploratory for the rest."], v5=v5A, base=bmean))
        put_df(new("12.1b Product cells, details", "Baseline means, persistence, stacks, cohorts, placebo, HonestDiD of level N1", "V6-11"),
               "Product cells (V6-11): what is always reported (A.8)",
               [("1. Outcome in g - 1, entered and comparison cells", bA), ("Persistence: share of entered cells with an MNE, by event time", per),
                ("4. Entered and comparison cells by stack", stk), ("4. Entered cells by origin and cohort", org),
                ("Weighting check: coefficients and averages by cohort (A.7 point 9)", evs["A_cohort"][["outcome", "term", "b", "se", "p", "N", "ntreat", "nclus"]].rename(
                    columns={"ntreat": "entered cells of the cohort", "nclus": "post coefficients averaged"})),
                ("5. Placebo: event moved to g - 3 (cohorts 2017 and 2018), years before g", evs["A_placebo"][["variant", "outcome", "est", "term", "b", "se", "p", "N", "ntreat", "nclus", "status"]]),
                ("HonestDiD on the aligned stacked estimator (average of 0 to 2)", honest_v6())])
        longs += ev_longs(main, "12.1 Product cells, aligned", "V6-11",
                          lambda r: "primary" if (r["outcome"] in ("NEWL", "anyXL") and r["term"] == "Avg02" and r["variant"] == "main" and r["est"] == "ols") else "exploratory", "A")
        longs += ev_longs(evs["A_cohort"], "12.1b Product cells, details", "V6-11", lambda r: "robustness", "A")
        longs += ev_longs(evs["A_placebo"], "12.1b Product cells, details", "V6-11", lambda r: "robustness", "A")
        # 12.2
        ct = chk_table(evs["A_chk"])
        put_df(new("12.2 New exporters, checks", "Robustness of T5 (S2 with EV9) and rows of T6", "V6-12"),
               "Robustness of new local exporters (V6-12), product cells, aligned stacks: one row per variant (average 0 to 2)",
               [("", ct), ("HonestDiD", honest_v6())],
               "Request: V6-12. Each row changes one thing relative to 12.1 (EV2, R(g), CL-op). Role: robustness; the row EV9 for NEWL is secondary (S2).")
        longs += ev_longs(evs["A_chk"], "12.2 New exporters, checks", "V6-12", lambda r: "secondary" if (r["variant"] == "EV9" and r["outcome"] == "NEWL") else "robustness", "A")
        # 12.3
        bB, perB, stkB, orgB = baseline("B", ["anyXL", "lnXL", "lnX", "NL", "lnNL", "NEWL", "N", "D"])
        bmB = {y: dict(zip(bB.loc[bB["Group"] == "treated", "Outcome"], bB.loc[bB["Group"] == "treated", "Mean in g - 1"])).get(name(y)) for y in OUTN}
        ws = new("12.3 Destination cells, aligned", "Level N6, panels A to D", "V6-13")
        allB = pd.concat([evs["B_main"].assign(variant=lambda d: d["variant"].replace({"main": "panel A, all events, all controls, EV3"})), evs["B_fe"]])
        put_rows(ws, render_ev(allB, "Destination cells, cohort-aligned stacks (V6-13), panels A to D",
                               ["Request: V6-13. Sample: aligned stacks of odp cells, R(g) evaluated with the odp exports. Fixed effects: EV3 (panel A, C), EV6, EV7. "
                                "Cluster: CL-B (two-way origin-destination pair and op cell). Role: exploratory."], v5=v5B, base=bmB))
        put_df(new("12.3b Destination cells, details", "Baseline means, stacks and placebo of level N6", "V6-13"), "Destination cells (V6-13): what is always reported (A.8)",
               [("Outcome in g - 1", bB), ("Persistence", perB), ("Cells by stack", stkB), ("Entered cells by origin and cohort", orgB),
                ("By cohort", evs["B_cohort"][["outcome", "term", "b", "se", "p", "N", "ntreat", "nclus"]]),
                ("Placebo", evs["B_placebo"][["variant", "outcome", "est", "term", "b", "se", "p", "N", "ntreat", "nclus", "status"]])])
        for k in ("B_main", "B_fe", "B_cohort", "B_placebo"):
            longs += ev_longs(evs[k], "12.3 Destination cells, aligned", "V6-13", lambda r: "exploratory", "B")
        # 12.4 bridge
        regsb = regs("bridge")
        v5ref = state["v5Bstk"]
        btB = bridge_table("B", evs["B_bridge"], evs["B_main"], regsb, v5ref)
        btA = bridge_table("A", evs["A_bridge"], evs["A_main"], regsb, {})
        state["dg"] = dg_verdict(pd.concat([btB, btA]))
        br = pd.concat([evs["B_bridge"], evs["A_bridge"]])
        extra = br[br["variant"].isin(["Dotros", "dCDH on D", "gradient at the op level"]) | br["variant"].str.contains("high_PCI6")]
        put_df(new("12.4 Bridge to regressions", "Bridge table in B and A (DG), Dotros, gradient at the op level, dCDH on D", "V6-16"),
               "Bridge between the regressions and the event studies (V6-16). Role: diagnostic (DG).",
               [("Destination cells (FE4 = EV3, cluster CL-B)", btB), ("Product cells (EV2, cluster CL-op)", btA), ("DG: reading rule of Part C", state["dg"]),
                ("Completing estimations and the high_PCI6 version", extra[["level", "variant", "outcome", "est", "term", "b", "se", "p", "N", "status"]])],
               "P0 all cells; P1 without cells with an MNE in 2012 or 2013; P2 the cells of the stacks, each once, 2012-2018 (computed from the event "
               "panel and from the regression code: they must coincide for the logs); P3 Post instead of D; P4 static Post x Treat in the stacks; P5 "
               "average of the event study. Figure v6_fig4 has P6.")
        longs += ev_longs(br, "12.4 Bridge to regressions", "V6-16", lambda r: "diagnostic", "B")
        longs += longs_from_regs(regsb, "12.4 Bridge to regressions")
        # 12.5
        het = pd.concat([evs["A_het"].assign(level="A"), evs["B_het"].assign(level="B")])
        hp = pd.concat([evs["A_hetplc"].assign(level="A"), evs["B_hetplc"].assign(level="B")])
        tab = het[het["term"].isin(["Avg02", "p_equal_avg02", "p_equal_avg0", "p_equal_pre"])][["level", "variant", "clus", "outcome", "group", "term", "b", "se", "p", "N", "ntreat", "status"]]
        tabp = hp[hp["term"].isin(["Avg02", "p_equal_avg02", "p_equal_avg0"])][["level", "variant", "outcome", "group", "term", "b", "se", "p", "N", "ntreat"]]
        put_df(new("12.5 Heterogeneity", "Interactions by four product cuts and two entrant cuts (S3)", "V6-14"),
               "Heterogeneity by interaction (V6-14): one estimation per cut and outcome, Treat x event time x group, common fixed effects",
               [("Average 0 to 2 by group and equality tests (A = product cells, B = destination cells, event (i) with pure controls)", tab),
                ("Placebo by group", tabp), ("Event-time coefficients by group", het[het["term"].isin(TERMS)][["level", "variant", "clus", "outcome", "group", "term", "b", "se", "p"]])],
               "Reading rule: a cut whose groups have different pre-period coefficients (p of equality below 0.10) is not interpreted. Role: exploratory; "
               "S3 = anyXL in product cells for ent_big = 1 and its p of equality.")
        longs += ev_longs(het, "12.5 Heterogeneity", "V6-14",
                          lambda r: "secondary" if (r["variant"] == "ent_big" and r["outcome"] == "anyXL" and r.get("level", "A") == "A" and r["clus"] == "CL-op") else "exploratory", "A")
        # 12.6
        put_df(new("12.6 Heading cells (HS4)", "Level N4: not estimable, counts only", "V6-15"), "Heading cells (V6-15)",
               [("Not estimable: too few entered cells", U["heading_threshold"]), ("Cells by status at the heading level", U["status"][U["status"]["Level"] == "H"])])
        # 12.7
        t1, t2, t3, val = who_table()
        put_df(new("12.7 Who the new exporters are", "Table of new local exporters and validation of the local class", "V6-17"),
               "Who the new local exporters are (V6-17), product cells, stacks of V6-11, years 0 to 2 (entered) and the same calendar years (comparison)",
               [("Provenance and flags", t1), ("Counts by high_PCI6 (0 = comparison, 1 = entered)", t2), ("Counts by type of production", t3), ("Validation of the local class", val)])
        return longs
    return hook


SNAME = {"Differentiat": "differentiated", "Notdifferent": "not differentiated", "Notclassifie": "not classified"}


def primary_rows(state):
    rows = []

    def regrow(step, pred):
        return next((r for r in regs(step) if pred(r)), None)
    t1 = regrow("loc", lambda r: r["role"] == "primary")
    t1w = regrow("loc", lambda r: r["panel"] == "A. Location on PCI6_z, weighted by X_opy: S" and r["col"] == "FL1")
    t1c = regrow("loc", lambda r: r["panel"] == "A. Location on PCI6_z, conditional on N >= 1: S" and r["col"] == "FL1")
    if t1:
        b, s, p = t1["cells"]["PCI6_z"]
        ok = b > 0 and p < 0.05 and t1w and t1w["cells"]["PCI6_z"][0] > 0 and t1c and t1c["cells"]["PCI6_z"][0] > 0
        rows.append(("T1", "Presence: S_opy on PCI6_z, FL1, CL-hs6, unweighted (11.4 A)", round(b, 4), round(s, 4), f"[{b - 1.96 * s:.4f}, {b + 1.96 * s:.4f}]", round(p, 4),
                     "positive, p < 0.05; same sign weighted and conditional", "yes" if ok else "no",
                     f"weighted {t1w['cells']['PCI6_z'][0]:+.4f} (p {t1w['cells']['PCI6_z'][2]:.2f}); conditional {t1c['cells']['PCI6_z'][0]:+.4f} (p {t1c['cells']['PCI6_z'][2]:.3f})"))
    for tag, dep, fe2 in (("T2", "lnXL", "FE5"), ("T3", "lnX", "FE6")):
        r = regrow("pci", lambda r: r["role"] == "primary" and r["dep"] == dep)
        r2 = regrow("pci", lambda r, d=dep, f=fe2: r["panel"].startswith("A. Continuous") and r["dep"] == d and r["regs"][0] == "lnN" and r["col"] == f)
        if r:
            b, s, p = r["cells"]["RxPCI6"]
            ok = b < 0 and p < 0.05 and r2 and r2["cells"]["RxPCI6"][0] < 0
            extra = f"{fe2}: {r2['cells']['RxPCI6'][0]:+.3f} (p {r2['cells']['RxPCI6'][2]:.3f})" if r2 else ""
            if "permutation_p" in r:
                extra += f"; permutation p {r['permutation_p']:.3f}"
            alt = r.get("alt", {})
            extra += "; p with CL-od " + (f"{alt['CL-od']['RxPCI6'][1]:.3f}" if "CL-od" in alt and "RxPCI6" in alt["CL-od"] else "") + ", CL2-hs6 " + (
                f"{alt['CL2-hs6']['RxPCI6'][1]:.3f}" if "CL2-hs6" in alt and "RxPCI6" in alt["CL2-hs6"] else "")
            rows.append((tag, f"Association, {'local firms' if dep == 'lnXL' else 'all firms'}: {dep} on ln N and ln N x PCI6_z, FE4, CL2 (11.1 A)",
                         round(b, 4), round(s, 4), f"[{b - 1.96 * s:.4f}, {b + 1.96 * s:.4f}]", round(p, 4), f"negative, p < 0.05; same sign with {fe2}", "yes" if ok else "no", extra))
    t4 = [r for r in regs("race") if r["role"] == "primary"]
    if t4:
        cs = [(r["dep"], r["cells"].get("lnNxPCI6_z")) for r in t4]
        txt = "; ".join(f"{d}: {c[0]:+.3f} (p {c[2]:.3f})" for d, c in cs if c)
        ok = all(c and c[0] < 0 for d, c in cs) and any(c and c[2] < 0.10 for d, c in cs)
        rows.append(("T4", "Horse race: ln N x PCI6_z in column (10) with DIFF, FIELD, PROC, FE4 (11.3)", "", "", "", "", "keeps its sign, p < 0.10 in at least one", "yes" if ok else "no", txt))
    A = state["evs"]["A_main"]; chk = state["evs"]["A_chk"]
    for tag, y in (("T5", "NEWL"), ("T6", "anyXL")):
        x = A[(A["outcome"] == y) & (A["est"] == "ols") & (A["variant"] == "main")].set_index("term")
        if "Avg02" not in x.index:
            continue
        b, s, p = x.loc["Avg02", ["b", "se", "p"]]
        pre = x.loc["pre_test", "p"] if "pre_test" in x.index else np.nan
        if tag == "T5":
            sub = {v: chk[(chk["variant"] == v) & (chk["outcome"] == "NEWL") & (chk["term"] == "Avg02")]["b"] for v in ("EV8", "without the 2017 cohort", "without products with hs_n1 = 1")}
            same = all(len(v) and v.iloc[0] > 0 for v in sub.values())
            ok = b > 0 and p < 0.05 and pre >= 0.10 and same
            txt = f"pre-trend p {pre:.3f}; " + "; ".join(f"{k}: {v.iloc[0]:+.3f}" if len(v) else f"{k}: not available" for k, v in sub.items())
            rows.append((tag, "Entry of local firms: NEWL, product cells, average 0 to 2, EV2, CL-op (12.1)", round(b, 4), round(s, 4), f"[{b - 1.96 * s:.4f}, {b + 1.96 * s:.4f}]",
                         round(p, 4), "positive, p < 0.05; pre-trend p >= 0.10; same sign with EV8, without 2017, without hs_n1", "yes" if ok else "no", txt))
        else:
            ok = b - 1.96 * s > -0.05
            rows.append((tag, "No displacement: anyXL, product cells, average 0 to 2, EV2, CL-op (12.1)", round(b, 4), round(s, 4), f"[{b - 1.96 * s:.4f}, {b + 1.96 * s:.4f}]",
                         round(p, 4), "lower bound of the 95 percent interval above -0.05", "yes" if ok else "no", f"pre-trend p {pre:.3f}"))
    dg = state.get("dg")
    if dg is not None and len(dg):
        rows.append(("DG", "Bridge table, levels B and A, lnX and lnXL (12.4)", "", "", "", "", "P2 versions coincide; P3 / first stage within the interval of P2; P4 within the interval of P5",
                     "yes" if dg["DG met"].all() else "no", "; ".join(f"{r['Level']} {r['Outcome']}: " + ("met" if r["DG met"] else "not met") for _, r in dg.iterrows())))
    s1 = regrow("rauch", lambda r: r["role"] == "secondary")
    if s1:
        p = s1["tests"].get("Differentiated = Not differentiated", np.nan)
        rows.append(("S1", "ln XL on ln N by rauch_bin_con, FE4, p of equality (11.2 A)", "", "", "", round(p, 4), "secondary, read with its p", "",
                     "; ".join(f"{SNAME.get(k[5:], k[5:])}: {v[0]:.3f} (SE {v[1]:.3f})" for k, v in s1["cells"].items())))
    s2 = chk[(chk["variant"] == "EV9") & (chk["outcome"] == "NEWL") & (chk["term"] == "Avg02")]
    if len(s2):
        b, s, p = s2.iloc[0][["b", "se", "p"]]
        rows.append(("S2", "T5 with EV9 (product x year), if there is support (12.2 row 1)", round(b, 4), round(s, 4), f"[{b - 1.96 * s:.4f}, {b + 1.96 * s:.4f}]", round(p, 4), "secondary", "", ""))
    h = state["evs"]["A_het"]
    s3 = h[(h["variant"] == "ent_big") & (h["outcome"] == "anyXL") & (h["clus"] == "CL-op")]
    if len(s3):
        g1 = s3[(s3["term"] == "Avg02") & s3["group"].str.endswith("=1")]
        pe = s3[s3["term"].str.startswith("p_equal_avg")]
        if len(g1):
            b, s, p = g1.iloc[0][["b", "se", "p"]]
            rows.append(("S3", "anyXL in product cells for ent_big = 1 and its p of equality (12.5)", round(b, 4), round(s, 4), f"[{b - 1.96 * s:.4f}, {b + 1.96 * s:.4f}]", round(p, 4),
                         "secondary", "", f"p of equality with ent_big = 0: {pe.iloc[0]['p']:.3f}" if len(pe) else ""))
    return ("Primary set (fixed before running, Part C of the v6 plan): six tests, one diagnostic and three secondaries",
            ("Test", "Exact row", "Estimate", "SE", "95 percent interval", "p", "Criterion", "Met", "Notes"), rows)


def main() -> None:
    evs = {f"{l}_{b}": ev(l, b) for l in ("A", "B") for b in ("main", "cohort", "placebo", "chk", "fe", "het", "hetplc", "bridge")}
    v5A, v5B = v5_number("A"), v5_number("B")
    e5 = B.load_events()
    x = e5[(e5["cellset"] == "B") & (e5["block"] == "fe") & (e5["est"] == "twfe") & (e5["fe"] == "EV3") & (e5["term"] == "Post_avg") & (e5["sample"] == "g_ps")]
    v5Bstk = {r["outcome"]: r["b"] for _, r in x.iterrows()}
    state = {"evs": evs, "v5A": v5A, "v5B": v5B, "v5Bstk": v5Bstk}
    figdata, index = [], []
    figures(evs, e5, desc("race").get("leave_one_out"), figdata, index)
    B.FIG = W.ROOT / "docs" / "notes" / "figures_v5"
    # the bridge verdict is needed by the primary table: computed inside the hook, so the table is built after a first pass
    hook = build_hook(state)
    btB = bridge_table("B", evs["B_bridge"], evs["B_main"], regs("bridge"), v5Bstk)
    btA = bridge_table("A", evs["A_bridge"], evs["A_main"], regs("bridge"), {})
    state["dg"] = dg_verdict(pd.concat([btB, btA]))
    B.PRIMARY = primary_rows(state)
    B.MAIN_TITLE = "Main results of round v5, in eight points, with the corrections of V6-02 (the numbers are in the sheets listed on the right)"
    B.MAIN_RESULTS = main_results_v6(e5)
    B.GLOSSARY = B.GLOSSARY + GLOSSARY_V6
    B.NOTES = B.NOTES + NOTES_V6
    B.READ_TITLE = "Multinationals and agricultural exports: all estimates, round v6, November 2026"
    B.READ_EXTRA = [("Round v6", "Sheets 10.1 to 12.7 are new in v6 (cohort-aligned event studies, PCI6, binary Rauch, bridge table). The Primary set at "
                     "the top of Main results was fixed before running. Every v6 row of All estimates has Request and Role. Figures v6: "
                     "docs/notes/figures_v6.")]
    B.LONG_EXTRA_COLS = ["Request", "Role", "FE code", "Cut variable", "Group"]
    B.FIG_EXTRA = ([], figdata, index)
    B.HOOK_SHEETS = hook
    B.XLSX = XLSX6
    sys.argv = [sys.argv[0], "--no-figures"]
    B.main()


def main_results_v6(e5):
    m = [list(r) for r in B.MAIN_RESULTS]
    pl = e5[(e5["block"] == "placebo") & (e5["term"] == "Post_avg") & (e5["est"] == "twfe") & e5["outcome"].isin(["NL", "EXITL", "NEWL", "anyXL"])]

    def plc(cs, smp="g_ps"):
        x = pl[(pl["cellset"] == cs) & (pl["sample"] == smp)]
        return "; ".join(f"{L.out_name(r['outcome']).lower()} {r['b']:+.2f}{st(r['p'])}" for _, r in x.iterrows())
    m[0][2] += (" In value the picture differs: weighted by exports, the MNE share rises with capital at the farm stage (v4 E3a); the v6 weighted "
                "regressions are in 1.1 and 1.2 (V6-09).")
    m[1][2] = m[1][2].replace("(unweighted slope 0.12, SE 0.06, farm stage;", "(farm stage: weighted slope 0.19, SE 0.03; unweighted 0.12, SE 0.06;")
    m[4][2] += f" Placebo with the entry year moved three years earlier (OLS, corrected averages, sheet 4.10): {plc('A')}; the number of local exporters and the exits have a significant placebo."
    m[6][2] += f" Placebo (OLS, corrected averages, sheet 5.9): {plc('B')}."
    m.append(["9", "Where MNEs are by complexity and degree of processing.",
              "The location panels of 3.1 and 3.4 (Where MNEs are) regress presence and the MNE share on PCI and on the degree of processing; "
              "in v6 they are redone with six-digit PCI in 11.4 (T1).", "3.1, 3.4, 11.4"])
    return [tuple(r) for r in m]


GLOSSARY_V6 = [
    ("Round v6 codes", ""),
    ("FE1 to FE6 (regressions, odpy cells)", "FE1 origin + destination + product + year; FE2 origin x year + destination x year + product; FE3 origin x "
     "destination x product + year; FE4 FE3 with origin x destination x year instead of year; FE5 FE4 + origin x product x year; FE6 FE5 + destination x product x year."),
    ("FL1 to FL3 (location, opy cells)", "FL1 origin x year + type of production (main); FL2 origin x year + HS chapter; FL3 origin x year."),
    ("EV1 to EV9 (event studies)", "EV1 cell + year; EV2 cell + origin x year (destination cells: + destination x year); EV3 product cells: EV2 + type x year, "
     "destination cells: cell + origin x destination x year (= FE4); EV4 EV2 + HS chapter x year (destination cells: EV3 + product x year); EV5 destination "
     "cells: cell + origin x product x year; EV6 EV3 + origin x product x year (= FE5); EV7 EV6 + destination x product x year (= FE6); EV8 EV2 + HS4 "
     "heading x year; EV9 EV2 + HS6 product x year. In the aligned stacks every fixed effect is interacted with the stack."),
    ("Cluster codes", "CL-od origin-destination pair; CL2 two-way origin-destination pair and HS4 heading; CL2-hs6 two-way pair and HS6 product; CL-hs6 "
     "HS6 product; CL-hs4 HS4 heading; CL-op origin x product cell; CL-B two-way pair and op cell; CL-oh origin x heading."),
    ("Aligned stack", "For each cohort g (first MNE in g, none before, no MNE in 2012 or 2013): the entered cells of g plus the never treated cells, "
     "years g - 4 to g + 4. A comparison cell enters the stack of g only if it meets the rule in that same year."),
    ("R(g), R3(g), R0", "R(g): exports in g - 1 and g - 2; R3(g): also in g - 3; R0: no rule."),
    ("Post", "1 from the year of the first MNE onward (it does not return to 0 if the MNE leaves); 0 for never treated cells."),
    ("Dotros", "1 if some MNE exports the product from the origin to another destination in the year."),
    ("G", "Number of distinct multinational groups (same ultimate parent) with exports in the cell."),
    ("PCI6, PCI4, ubiquity", "Six- and four-digit Product Complexity Index of the OEC in HS 2017 (mean 2018-2024); ubiquity = countries with revealed "
     "comparative advantage >= 1 in the product (OEC BACI HS 2017). PCI6_z standardized; high_PCI6 above the export weighted median; PCI6_dev = PCI6_z - PCI4_z."),
    ("Binary Rauch", "rauch_bin_con: differentiated against homogeneous or reference priced (conservative); rauch_bin_lib the same with the liberal classes."),
    ("Role", "primary (one of the six tests T1 to T6), diagnostic (bridge table), secondary (S1 to S3), robustness, descriptive, exploratory."),
]

NOTES_V6 = [
    ("Round v6: PCI (V6-03)", "OEC public API, cubes complexity_pci_a_hs17_hs6 and _hs17_hs4 (HS 2017, 2018-2024, merged code by code), "
     "complexity_pci_a_hs12_hs6 (HS 2012, 2012-2016, via the UNSD correlation table), and trade_i_baci_a_17 for ubiquity; downloaded 2026-11-27. The "
     "Atlas of Economic Complexity publishes PCI only at four digits. Missing values stay missing."),
    ("Round v6: stacks (A.7)", "At risk: no MNE in 2012 and 2013. Cohorts 2014 to 2018. Never treated: no MNE in 2012-2018. R(g) evaluated in g for "
     "the entered cells and for each comparison cell of the stack. Main average: years 0 to 2; also 0 to 4. Pre-trend test b-3 = b-2 = 0."),
    ("Round v6: definitions", "NEWL: local firms whose first year with exports in the cell is t (looking back to 2012). EXITL: local exporters of t - 1 "
     "that do not export in t. SURVL = 1 - EXITL / NL(t - 1). In destination cells new means new in the destination."),
    ("Round v6: corrections to the v5 workbook (V6-02)", "1. OLS, PPML and stacked averages of event times 0 to 4 with fewer than five post "
     "coefficients now average the coefficients that exist (stored value x 5 / k; p unchanged), in 4.4, 5.4, 4.10, 5.9, 6.6, 4.0 and All estimates. "
     "2-5. Main results points 1, 2, 5 and 7 completed and point 9 added. 6. Freyaldenhoven et al. did not run in any cell set in v5 (xtevent error "
     "198); the note said it ran on product cells. 7. CEM: the v5 record said 'pre-trends in lnXL'; sheet 4.8 gives pre-trend p 0.27 and 0.33, so the "
     "matched lnXL has no significant pre-trend. 8. Glossary: FE, FL, EV and cluster codes added. 9. v4 E2e runs PPML with FE4 only. 10. Labels of "
     "3.1 (PCI terciles) and 3.2 (not classified) corrected. 11. For the text, not now: the 99 percent of exports of Section 4.3 is 98.47 percent."),
    ("Round v6: Csdid in v5 (question 4)", "csdid had no fixed effects or covariates: it did not control for origin x year; the label of 4.0 was wrong for it."),
]


if __name__ == "__main__":
    main()
