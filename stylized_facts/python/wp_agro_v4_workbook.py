"""
wp_agro_v4_workbook.py  --  docs/notes/WP_paperagro_v4_master_estimates.xlsx (spec 0.5 of especificaciones_estimaciones_v4)
==========================================================================================================================

    WP_YEARS=2012-2018 WP_SCOPES=agro python wp_agro_v4_workbook.py

One sheet per table (E1a, E1b, ... E7c), in the layout of the v3 workbook (outreg2 style): column numbers, a row with the
fixed-effect code (FE1 to FE6) or the column label, one block per panel with coefficients, standard errors in
parentheses, stars, test p values, observations, R2, within R2, singletons dropped and the row "Column in the note"
(red: printed in the paper). Then "Long format" (one row per coefficient), "Classifications" (HS6 -> every product
group of spec 0.3), "Samples" and "Notes".

Reads output/wp_2012_2018/agro/v4/v4_regs_*.pkl, v4_desc_*.pkl (wp_agro_v4_est.py), v4_event_A.dta, v4_event_B.dta
(stylized_facts/stata/wp_agro_v4_event.do) and, when it exists, v4_shown.json (the cells printed in the paper, written
by wp_agro_v4_paper.py).
"""
from __future__ import annotations

import json
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

OUT = W.WP_OUT / "agro" / "v4"
V4 = W.WP_INT / "v4"
XLSX = W.ROOT / "docs" / "notes" / "WP_paperagro_v4_master_estimates.xlsx"
RED = "C00000"
FE_TXT = {"FE1": "origin + destination + product + year", "FE2": "origin x year + destination x year + product",
          "FE3": "origin x destination x product + year", "FE4": "origin x destination x product + origin x destination x year",
          "FE5": "FE4 + origin x product x year", "FE6": "FE5 + destination x product x year"}
TITLES = {
    "E1a": "Sector context, 2018: exports, exporters and multinational shares by sector and origin",
    "E1b": "Sector context, 2012 to 2018 annual averages",
    "E1c": "Multinational affiliates and groups by sector, 2018",
    "E2a": "Baseline: ln exports of all firms on ln number of MNEs",
    "E2b": "Baseline: ln exports of all firms on the indicator for at least one MNE",
    "E2c": "Local firms: ln exports of local firms on ln number of MNEs",
    "E2d": "Local firms: ln exports of local firms on the indicator for at least one MNE",
    "E2e": "Zeros of local exports: probability of positive local exports and PPML",
    "E2f": "Number of local exporters and exports per local exporter",
    "E2g": "Baseline by origin",
    "E3a": "Capital intensity quintiles within stage: products, exports and multinational shares",
    "E3b": "Product by product: capital per worker and multinational shares (figure data)",
    "E3c": "Coverage of the capital intensity measure",
    "E3d": "Type of production x high or low capital intensity, both thresholds",
    "E4a": "Heterogeneity: high and low capital intensity, stages pooled",
    "E4b": "Heterogeneity: continuous ln capital per worker",
    "E4c": "Heterogeneity: stage x high and low capital intensity",
    "E4d": "Heterogeneity: farm stage, capital intensity and type of production together",
    "E4e": "Heterogeneity: type of production x capital intensity",
    "E4f": "Heterogeneity: type of production",
    "E4g": "Heterogeneity by origin (FE4)",
    "E5a": "Location: probability that at least one MNE exports the product from the origin",
    "E5b": "Location: ln number of MNEs and MNE share",
    "E5c": "Location: foreign and domestic MNEs",
    "E5d": "Location: first entry of an MNE (discrete time hazard)",
    "E5e": "Location: capital intensity and other product characteristics",
    "E6a": "Entry of the first MNE, origin x product cells: main sample and three pre-years",
    "E6b": "Entry of the first MNE, origin x destination x product cells: main sample and three pre-years",
    "E6c": "Entry of the first MNE, origin x product cells: heterogeneity",
    "E6d": "Entry of the first MNE, origin x destination x product cells: heterogeneity",
    "E6e": "Entry of the first MNE: checks (placebo, no exit within two years, balanced cells, PPML)",
    "E6f": "Entry of the first MNE: descriptive companion",
    "E7a": "Rauch (1999) classes: multinational shares and heterogeneity",
    "E7b": "BEC end use and the inputs group: multinational shares and heterogeneity",
    "E7c": "Capital intensity x Rauch",
}
SHOWN: dict = {}


def stars(p):
    return "" if p is None or not np.isfinite(p) else ("***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else "")


def label(v: str) -> str:
    """Readable regressor names."""
    base = {"lnN": "ln(number of MNEs)", "D": "At least one MNE"}
    if v in base:
        return base[v]
    if v in ("lnkl",):
        return "ln capital per worker"
    simple = {"hi_mean": "High capital intensity (aggregate ratio)", "hi_median": "High capital intensity (median)",
              "q2": "Quintile 2", "q3": "Quintile 3", "q4": "Quintile 4", "q5": "Quintile 5 (highest)",
              "rauch_ref": "Reference priced (conservative)", "rauch_diff": "Differentiated (conservative)",
              "rauch_lib_ref": "Reference priced (liberal)", "rauch_lib_diff": "Differentiated (liberal)",
              "consumption": "Consumption good (BEC)", "inputs": "Inputs group"}
    if v in simple:
        return simple[v]
    m = re.match(r"^(lnN|D)_(.*)$", v)
    if not m:
        return v
    r, rest = base[m.group(1)], m.group(2)
    rest = rest.replace("high_mean_", "").replace("high_median_", "")
    words = {"hi": "high capital intensity", "lo": "low capital intensity", "nc": "not classified", "tnc": "not classified",
             "farm_hi": "farm stage, high", "farm_lo": "farm stage, low", "proc_hi": "processing stage, high", "proc_lo": "processing stage, low",
             "x_lnkl": "ln capital per worker", "x_lnkl_dm": "ln capital per worker, demeaned within stage",
             "type_field": "field crops", "type_horti": "horticultural and plantation crops", "type_live": "livestock and fisheries",
             "type_proc": "other processed food", "kr_other": "not classified (capital or Rauch)"}
    if rest in words:
        return f"{r} x {words[rest]}"
    m2 = re.match(r"^(field|horti|live|proc)_(h|l)$", rest)
    if m2:
        ty = {"field": "field crops", "horti": "horticultural and plantation crops", "live": "livestock and fisheries", "proc": "other processed food"}[m2.group(1)]
        return f"{r} x {ty}, {'high' if m2.group(2) == 'h' else 'low'}"
    m3 = re.match(r"^kr_(hi|lo)_(diff|nd)$", rest)
    if m3:
        return f"{r} x {'high' if m3.group(1) == 'hi' else 'low'} capital intensity, {'differentiated' if m3.group(2) == 'diff' else 'not differentiated'}"
    for col, lab in (("rauch_con", "Rauch conservative"), ("rauch_lib", "Rauch liberal"), ("bec2", "BEC"), ("input", "")):
        if rest.startswith(col + "_"):
            k = rest[len(col) + 1:]
            kk = {"hom": "homogeneous", "ref": "reference priced", "diff": "differentiated", "int": "intermediate", "cons": "consumption",
                  "inp": "inputs", "oth": "other products", "na": "not classified"}.get(k, k)
            return f"{r} x {kk}" + (f" ({lab})" if lab else "")
    return f"{r} x {rest}"


DEPS = {"lnX": "ln exports, all firms", "lnXL": "ln exports, local firms", "anyXL": "positive local exports (0/1)",
        "XL": "exports of local firms (levels)", "lnNL": "ln number of local exporters", "lnXLpf": "ln exports per local exporter",
        "D": "at least one MNE", "lnN": "ln number of MNEs", "S": "MNE share of exports", "DF": "at least one foreign MNE",
        "DD": "at least one domestic MNE"}


def load():
    regs, desc = [], {}
    for f in sorted(OUT.glob("v4_regs_*.pkl"), key=lambda p: p.stat().st_mtime):
        regs += pickle.load(open(f, "rb"))
    for f in sorted(OUT.glob("v4_desc_*.pkl"), key=lambda p: p.stat().st_mtime):
        desc.update(pickle.load(open(f, "rb")))
    # E2e PPML: pyfixest's fepois did not converge with FE4, the estimates come from ppmlhdfe (wp_agro_v4_ppml.do)
    f = OUT / "v4_ppml.dta"
    if f.exists():
        for _, r in pd.read_stata(f).iterrows():
            ok = r["status"] == "ok"
            regs.append(dict(sheet="E2e", panel=f"PPML, local exports in levels, regressor {r['reg']}", col="FE4", label="FE4", fe="FE4",
                             dep="XL", regs=[r["reg"]], cluster="od", est="PPML (ppmlhdfe)",
                             sample=("N >= 1" if r["reg"] == "lnN" else "all cells with positive exports") + ", zeros of local exports included",
                             cells={r["reg"]: (float(r["b"]), float(r["se"]), float(r["p"]))} if ok else {}, tests={},
                             n=int(r["N"]) if ok else 0, r2=float(r["pr2"]) if ok else np.nan, r2w=np.nan,
                             singletons=int(r["singletons"]) if ok else 0, status="" if ok else r["status"]))
    # the latest run of a cell wins
    seen, out = set(), []
    for r in reversed(regs):
        k = (r["sheet"], r["panel"], str(r["col"]))
        if k not in seen:
            seen.add(k); out.append(r)
    return list(reversed(out)), desc


def reg_block(sheet: str, regs: list[dict]):
    """Rows of one regression sheet; red marks (row range, column) for the cells printed in the paper."""
    rr = [r for r in regs if r["sheet"] == sheet]
    cols = list(dict.fromkeys(str(r["col"]) for r in rr))
    panels = list(dict.fromkeys(r["panel"] for r in rr))
    cell = {(r["panel"], str(r["col"])): r for r in rr}
    rows = [[f"{sheet}. {TITLES.get(sheet, '')}"], [""] + [f"({i + 1})" for i in range(len(cols))], ["Column"] + cols]
    red, long = [], []
    for P in panels:
        start = len(rows)
        rows.append([P])
        line = [cell.get((P, c)) for c in cols]
        rows.append(["Dependent variable"] + [DEPS.get(r["dep"], r["dep"]) if r else "" for r in line])
        rows.append(["Fixed effects"] + [(r["fe"] if r else "") for r in line])
        for v in dict.fromkeys(v for r in line if r for v in r["regs"]):
            b, s = [], []
            for r in line:
                if r and v in r["cells"]:
                    bb, ss, pp = r["cells"][v]; b.append(f"{bb:.3f}{stars(pp)}"); s.append(f"({ss:.3f})")
                elif r and r["n"]:
                    b.append("Not identified" if v in r["regs"] else ""); s.append("")
                else:
                    b.append(""); s.append("")
            rows += [[label(v)] + b, [""] + s]
        for t in dict.fromkeys(t for r in line if r for t in r["tests"]):
            rows.append([f"p value of the test: {t}"] + [f"{r['tests'][t]:.3f}" if r and t in r["tests"] and np.isfinite(r["tests"][t]) else "" for r in line])
        rows.append(["Observations"] + [f"{r['n']:,}" if r and r["n"] else (r["status"] if r else "") for r in line])
        rows.append(["R-squared" if not any(r and r["est"] != "OLS" for r in line) else "R-squared (pseudo for PPML and logit)"]
                    + [f"{r['r2']:.3f}" if r and r["n"] and np.isfinite(r["r2"]) else "" for r in line])
        rows.append(["Within R-squared"] + [f"{r['r2w']:.3f}" if r and r["n"] and np.isfinite(r["r2w"]) else "" for r in line])
        rows.append(["Singletons dropped"] + [f"{r['singletons']:,}" if r and r["n"] else "" for r in line])
        rows.append(["Estimator"] + [r["est"] if r else "" for r in line])
        rows.append(["Clustered by"] + [{"od": "origin and destination pair", "country_dest": "destination", "hs": "product"}.get(r["cluster"], r["cluster"]) if r else "" for r in line])
        rows.append(["Sample"] + [r["sample"] if r else "" for r in line])
        shown = [SHOWN.get(f"{sheet}|{P}|{c}", "") for c in cols]
        rows.append(["Column in the note"] + [s or "Not shown" for s in shown])
        for j, s in enumerate(shown):
            if s:
                red.append((start, len(rows) - 1, j + 1))
        for c, r in zip(cols, line):
            if not r or not r["n"]:
                continue
            for v in r["regs"]:
                if v in r["cells"]:
                    bb, ss, pp = r["cells"][v]
                    long.append({"Table": sheet, "Panel": P, "Column": c, "Dependent variable": DEPS.get(r["dep"], r["dep"]), "Regressor": label(v),
                                 "Coefficient": bb, "Standard error": ss, "p value": pp, "Stars": stars(pp), "Observations": r["n"],
                                 "R-squared": r["r2"], "Within R-squared": r["r2w"], "Singletons dropped": r["singletons"],
                                 "Fixed effects": r["fe"], "Clustered by": r["cluster"], "Sample": r["sample"], "Estimator": r["est"],
                                 "Column in the note": SHOWN.get(f"{sheet}|{P}|{c}", "Not shown")})
            for t, pv in r["tests"].items():
                long.append({"Table": sheet, "Panel": P, "Column": c, "Dependent variable": DEPS.get(r["dep"], r["dep"]), "Regressor": f"Test: {t}",
                             "p value": pv, "Observations": r["n"], "Fixed effects": r["fe"], "Clustered by": r["cluster"], "Sample": r["sample"],
                             "Estimator": r["est"], "Column in the note": SHOWN.get(f"{sheet}|{P}|{c}", "Not shown")})
    rows.append(["*** p<0.01, ** p<0.05, * p<0.1. Standard errors in parentheses. FE codes: "
                 + "; ".join(f"{k} {v}" for k, v in FE_TXT.items()) + ". Red: printed in the paper."])
    return rows, red, long


# ---------------------------------------------------------------------
# E6
# ---------------------------------------------------------------------
TAGS = {"main": "Main sample (two observed years before entry)", "pre3": "Three observed years before entry",
        "noexit": "Excluding cells where the MNE exits within two years", "balanced": "Cells with exports in every year",
        "placebo": "Placebo: event three years earlier, 2012 to 2016", "hm_hi": "High capital intensity (aggregate ratio)",
        "hm_lo": "Low capital intensity (aggregate ratio)", "hd_hi": "High capital intensity (median)", "hd_lo": "Low capital intensity (median)",
        "t_field": "Field crops", "t_horti": "Horticultural and plantation crops", "t_live": "Livestock and fisheries",
        "t_proc": "Other processed food and beverages", "st_farm": "Farm stage", "st_proc": "Processing stage",
        "en_for": "Entrant is a foreign MNE", "en_dom": "Entrant is a domestic MNE"}
for _o, _n in {"ARG": "Argentina", "CHL": "Chile", "COL": "Colombia", "CRI": "Costa Rica", "DOM": "Dominican Republic", "PER": "Peru",
               "PRY": "Paraguay", "SLV": "El Salvador", "URY": "Uruguay"}.items():
    TAGS[f"o_{_o}"] = f"Origin: {_n}"
OUTS = {"lnXL": "ln local exports", "NL": "local exporters", "lnNL": "ln local exporters",
        "lnX": "ln total exports", "N": "number of MNEs", "anyXL": "positive local exports", "XL": "local exports, levels (PPML)"}
ESTS = {"twfe": "Event study (TWFE)", "cs": "Callaway and Sant'Anna", "sa": "Sun and Abraham", "ppml": "PPML event study"}
TERMS = ["Tm4", "Tm3", "Tm2", "Tp0", "Tp1", "Tp2", "Tp3", "Tp4", "Post_avg"]
TERM_LAB = {"Tm4": "Event time -4 or earlier", "Tm3": "Event time -3", "Tm2": "Event time -2", "Tp0": "Event time 0 (entry year)",
            "Tp1": "Event time 1", "Tp2": "Event time 2", "Tp3": "Event time 3", "Tp4": "Event time 4", "Post_avg": "Average of event times 0 to 4"}


def event_results() -> pd.DataFrame:
    out = []
    for P in ("A", "B"):
        f = OUT / f"v4_event_{P}.dta"
        if f.exists():
            out.append(pd.read_stata(f))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def event_block(sheet, ev, cellset, tags, ests_main=("twfe", "cs", "sa")):
    e = ev[(ev["cellset"] == cellset) & ev["tag"].isin(tags)]
    rows = [[f"{sheet}. {TITLES.get(sheet, '')}"]]
    red, long = [], []
    for tag in tags:
        x = e[e["tag"] == tag]
        if not len(x):
            continue
        combos = [(o, s) for o in OUTS for s in ESTS if len(x[(x["outcome"] == o) & (x["est"] == s)])]
        rows.append([TAGS.get(tag, tag)])
        rows.append(["Outcome"] + [OUTS[o] for o, s in combos])
        rows.append(["Estimator"] + [ESTS[s] for o, s in combos])
        start = len(rows) - 3
        for t in TERMS:
            b, s_ = [], []
            for o, s in combos:
                r = x[(x["outcome"] == o) & (x["est"] == s) & (x["term"] == t)]
                if len(r) and np.isfinite(r["b"].iloc[0]):
                    b.append(f"{r['b'].iloc[0]:.3f}{stars(r['p'].iloc[0])}"); s_.append(f"({r['se'].iloc[0]:.3f})")
                else:
                    b.append(""); s_.append("")
            rows += [[TERM_LAB[t]] + b, [""] + s_]
        for lab, term, fld, fmt in (("p value, joint test of the pre-period coefficients", "pre_test", "p", "{:.3f}"),):
            rows.append([lab] + [fmt.format(x[(x["outcome"] == o) & (x["est"] == s) & (x["term"] == term)][fld].iloc[0])
                                 if len(x[(x["outcome"] == o) & (x["est"] == s) & (x["term"] == term)]) and np.isfinite(x[(x["outcome"] == o) & (x["est"] == s) & (x["term"] == term)][fld].iloc[0]) else ""
                                 for o, s in combos])
        for lab, fld in (("Observations", "N"), ("Cells", "ncells"), ("Treated cells", "ntreat")):
            vals = []
            for o, s in combos:
                r = x[(x["outcome"] == o) & (x["est"] == s)]
                v = r[fld].max() if len(r) else np.nan
                vals.append(f"{int(v):,}" if np.isfinite(v) and v > 0 else "")
            rows.append([lab] + vals)
        rows.append(["Status"] + [", ".join(sorted(set(x[(x["outcome"] == o) & (x["est"] == s)]["status"]) - {"ok"})) or "ok" for o, s in combos])
        shown = [SHOWN.get(f"{sheet}|{tag}|{o}|{s}", "") for o, s in combos]
        rows.append(["Column in the note"] + [s or "Not shown" for s in shown])
        for j, s in enumerate(shown):
            if s:
                red.append((start, len(rows) - 1, j + 1))
        for _, r in x.iterrows():
            if r["term"] in TERMS or r["term"] == "pre_test":
                long.append({"Table": sheet, "Panel": TAGS.get(tag, tag), "Column": f"{OUTS.get(r['outcome'], r['outcome'])}, {ESTS.get(r['est'], r['est'])}",
                             "Dependent variable": OUTS.get(r["outcome"], r["outcome"]), "Regressor": TERM_LAB.get(r["term"], "Test: pre-period coefficients jointly zero"),
                             "Coefficient": r["b"], "Standard error": r["se"], "p value": r["p"], "Stars": stars(r["p"]), "Observations": r["N"],
                             "Fixed effects": "cell + origin x year" + (" + destination x year" if cellset == "B" else ""),
                             "Clustered by": "origin x product" if cellset == "A" else "origin and destination pair", "Sample": TAGS.get(tag, tag),
                             "Estimator": ESTS.get(r["est"], r["est"]), "Column in the note": SHOWN.get(f"{sheet}|{tag}|{r['outcome']}|{r['est']}", "Not shown")})
    rows.append(["*** p<0.01, ** p<0.05, * p<0.1. Standard errors in parentheses. Base period: event time -1. TWFE and Sun and Abraham: cell FE and "
                 "origin x year FE (destination x year FE added for origin x destination x product cells), event time -4 binned with earlier years. "
                 "Callaway and Sant'Anna: not yet treated controls, base period t0 - 1, event times before -4 not shown. Red: printed in the paper."])
    return rows, red, long


def event_desc() -> dict:
    out = {}
    for P, name in (("A", "op"), ("B", "odp")):
        e = pd.read_parquet(V4 / f"event_{name}.parquet")
        c = e.drop_duplicates("cell")
        tr = c[c["gvar"] > 0]
        out[f"{name}: entry events by year"] = tr.groupby("gvar").size().rename("Entry events").reset_index().rename(columns={"gvar": "Year of entry"})
        out[f"{name}: entry events by origin"] = tr.groupby("country_orig").size().rename("Entry events").reset_index()
        out[f"{name}: entry events by type"] = tr.groupby("type").size().rename("Entry events").reset_index()
        out[f"{name}: entry events by capital intensity"] = tr.groupby(["stage", "high_mean"]).size().rename("Entry events").reset_index()
        out[f"{name}: entry events by entrant"] = tr.groupby("entrant").size().rename("Entry events").reset_index()
        x = e[e["gvar"] > 0]
        out[f"{name}: local share of exports in treated cells"] = (x.assign(rel=x["year"] - x["gvar"]).groupby("rel")
                                                                     .apply(lambda d: 100 * d["XL"].sum() / d["X"].sum() if d["X"].sum() else np.nan)
                                                                     .rename("Local firms' share of exports (%)").reset_index().rename(columns={"rel": "Event time"}))
    return out


# ---------------------------------------------------------------------
# writer
# ---------------------------------------------------------------------
def main() -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, Side
    from openpyxl.utils import get_column_letter
    global SHOWN
    sh = OUT / "v4_shown.json"
    SHOWN = json.load(open(sh)) if sh.exists() else {}
    regs, desc = load()
    ev = event_results()
    wb = Workbook(); thin = Side(style="thin")
    first = True

    def new(name):
        nonlocal first
        if first:
            ws = wb.active; ws.title = name; first = False
        else:
            ws = wb.create_sheet(name)
        return ws

    def put_rows(ws, rows, red):
        for i, row in enumerate(rows):
            for j, v in enumerate(row):
                c = ws.cell(row=i + 1, column=j + 1, value=v)
                if j:
                    c.alignment = Alignment(horizontal="center", wrap_text=False)
        ws.cell(row=1, column=1).font = Font(bold=True)
        for (a, b, j) in red:
            for i in range(a, b + 1):
                ws.cell(row=i + 1, column=j + 1).font = Font(color=RED)
        ws.column_dimensions["A"].width = 64
        for j in range(2, 40):
            ws.column_dimensions[get_column_letter(j)].width = 18
        ws.freeze_panes = "B4"

    def put_df(ws, title, frames):
        ws.append([title]); ws["A1"].font = Font(bold=True)
        for name, df in frames:
            ws.append([])
            if name:
                ws.append([name]); ws.cell(row=ws.max_row, column=1).font = Font(italic=True)
            if isinstance(df, pd.Series):
                df = df.rename("Count").reset_index()
            df = df.copy()
            ws.append(list(df.columns))
            for j in range(1, len(df.columns) + 1):
                ws.cell(row=ws.max_row, column=j).font = Font(bold=True)
            for _, r in df.iterrows():
                ws.append([(None if (isinstance(v, float) and not np.isfinite(v)) else (round(v, 3) if isinstance(v, float) else v)) for v in r.tolist()])
        ws.column_dimensions["A"].width = 30
        for j in range(2, 16):
            ws.column_dimensions[get_column_letter(j)].width = 18

    longs = []
    order = ["E1a", "E1b", "E1c", "E2a", "E2b", "E2c", "E2d", "E2e", "E2f", "E2g", "E3a", "E3b", "E3c", "E3d",
             "E4a", "E4b", "E4c", "E4d", "E4e", "E4f", "E4g", "E5a", "E5b", "E5c", "E5d", "E5e",
             "E6a", "E6b", "E6c", "E6d", "E6e", "E6f", "E7a", "E7b", "E7c"]
    het = ["hm_hi", "hm_lo", "hd_hi", "hd_lo", "t_field", "t_horti", "t_live", "t_proc", "st_farm", "st_proc", "en_for", "en_dom"] + \
          [f"o_{o}" for o in ("ARG", "CHL", "COL", "CRI", "DOM", "PER", "PRY", "SLV", "URY")]
    for s in order:
        if s in ("E1a", "E1b", "E1c", "E3a", "E3b", "E3c", "E3d"):
            if s in desc:
                frames = [("", desc[s])]
                if s == "E3c" and "E3c_list" in desc:
                    frames.append(("Products without a capital intensity measure", desc["E3c_list"]))
                put_df(new(s), f"{s}. {TITLES[s]}", frames)
            continue
        if s == "E6f":
            put_df(new(s), f"{s}. {TITLES[s]}", list(event_desc().items()))
            continue
        if s in ("E6a", "E6b", "E6c", "E6d", "E6e"):
            if not len(ev):
                continue
            cs = "A" if s in ("E6a", "E6c") else "B"
            if s in ("E6a", "E6b"):
                rows, red, lg = event_block(s, ev, cs, ["main", "pre3"])
            elif s in ("E6c", "E6d"):
                rows, red, lg = event_block(s, ev, cs, het)
            else:
                rows, red, lg = [], [], []
                for c_ in ("A", "B"):
                    r_, d_, l_ = event_block(s, ev, c_, ["placebo", "noexit", "balanced", "main"] if True else [])
                    off = len(rows)
                    rows += ([[f"Cells: {'origin x product' if c_ == 'A' else 'origin x destination x product'}"]] + r_[1:])
                    red += [(a + off, b + off, j) for a, b, j in d_]; lg += l_
                rows = [[f"{s}. {TITLES[s]}"]] + rows
                red = [(a_ + 1, b_ + 1, j_) for a_, b_, j_ in red]
                # keep only the PPML rows of the main sample in this sheet's main block: the other main results are in E6a and E6b
            put_rows(new(s), rows, red); longs += lg
            continue
        rows, red, lg = reg_block(s, regs)
        extra = []
        if s == "E5d" and "E5d_counts" in desc:
            extra = list(desc["E5d_counts"].items())
        if s in ("E7a", "E7b") and "E7_shares" in desc:
            sub = desc["E7_shares"]
            sub = sub[sub["Classification"].str.startswith("Rauch")] if s == "E7a" else sub[~sub["Classification"].str.startswith("Rauch")]
            extra = [("Multinational shares", sub)]
        if len(rows) > 2:
            ws = new(s); put_rows(ws, rows, red); longs += lg
            if extra:
                r0 = ws.max_row + 2
                for name, df in extra:
                    if isinstance(df, pd.Series):
                        df = df.rename("Count").reset_index()
                    ws.cell(row=r0, column=1, value=name).font = Font(italic=True); r0 += 1
                    for j, c in enumerate(df.columns):
                        ws.cell(row=r0, column=j + 1, value=str(c)).font = Font(bold=True)
                    for _, r in df.iterrows():
                        r0 += 1
                        for j, v in enumerate(r.tolist()):
                            ws.cell(row=r0, column=j + 1, value=round(v, 3) if isinstance(v, float) else (int(v) if isinstance(v, (np.integer,)) else v))
                    r0 += 2
    # long format
    ws = new("Long format")
    cols = ["Table", "Panel", "Column", "Column in the note", "Dependent variable", "Regressor", "Coefficient", "Standard error", "p value", "Stars",
            "Observations", "R-squared", "Within R-squared", "Singletons dropped", "Fixed effects", "Clustered by", "Sample", "Estimator"]
    ws.append(cols)
    for r in longs:
        ws.append([None if (isinstance(r.get(c), float) and not np.isfinite(r.get(c))) else r.get(c) for c in cols])
    ws.freeze_panes = "A2"
    for j, w in enumerate([8, 50, 18, 22, 30, 60, 12, 12, 10, 6, 12, 10, 12, 10, 40, 22, 50, 26]):
        ws.column_dimensions[get_column_letter(j + 1)].width = w
    # classifications
    cls = pd.read_parquet(V4 / "classes.parquet")
    cl = cls[["hs", "description", "hs2", "hs4", "type", "stage", "kl", "lnkl", "kl_source", "high_mean", "thr_mean", "high_median", "thr_median",
              "quintile", "tx_mean", "tx_median", "rauch_con", "rauch_lib", "bec4", "bec_enduse", "input", "v_1218", "v_2018"]].copy()
    cl["v_1218"] = cl["v_1218"] / 1e6; cl["v_2018"] = cl["v_2018"] / 1e6
    cl.columns = ["HS 2017 code", "Description", "HS chapter", "HS heading", "Type of production (FAO)", "Stage", "Capital per worker (US$ thousand)",
                  "ln capital per worker", "Census farm types or NBER and CES industries", "High or low: aggregate ratio of the stage",
                  "Threshold used (US$ thousand)", "High or low: export weighted median of the stage", "Median threshold (US$ thousand)",
                  "Quintile within stage (export weighted)", "Type x capital (aggregate ratio)", "Type x capital (median)", "Rauch, conservative",
                  "Rauch, liberal", "BEC Rev.4", "BEC end use", "Inputs group", "Exports 2012 to 2018 (US$ million)", "Exports 2018 (US$ million)"]
    put_df(new("Classifications"), "Classifications: one row per HS 2017 agricultural product (spec 0.3)", [("", cl)])
    frames = [("", desc.get("Samples", pd.DataFrame())), ("Capital intensity thresholds by stage (US$ thousand per worker)", desc.get("Thresholds", pd.DataFrame()))]
    put_df(new("Samples"), "Samples: cells, exporters and export value by sample definition", frames)
    ws = new("Notes")
    notes = [
        ["Notes"],
        ["Source", "stylized_facts/python/wp_agro_v4_data.py, wp_agro_v4_est.py, wp_agro_v4_workbook.py and stylized_facts/stata/wp_agro_v4_event.do. Specification: especificaciones_estimaciones_v4_2026-11-17.md."],
        ["Sample", "Nine origins (ECU excluded), 2012 to 2018, agricultural products HS chapters 01 to 24. Destinations are real countries: free trade zones and the exporting country are dropped."],
        ["Product codes", "HS 2017 at six digits (the paper's codes since 3 November 2026, converted with the UNSD correlation tables). The specification says HS 2007: this is the one deviation, chosen earlier by the authors."],
        ["Exporter classes", "Foreign MNE: matched to Orbis or Dun & Bradstreet with the parent abroad or no recorded parent country. Domestic MNE: parent in the origin. Local: not matched. Counts of MNEs are distinct firms in the cell."],
        ["Fixed effects", "; ".join(f"{k}: {v}" for k, v in FE_TXT.items()) + ". Within one origin FE6 leaves one observation per fixed effect and is not estimated (E2g)."],
        ["Clusters", "Origin and destination pair, by destination within one origin, by product in the location regressions (E5), by origin x product (E6, cells A) and by origin and destination pair (E6, cells B)."],
        ["Capital intensity", "Capital per worker of the US farm types (2017 Census of Agriculture, machinery and equipment per hired worker) or food and beverage industries (NBER and CES, equipment capital per employee) linked to each product with the UNSD tables HS 2017, CPC 2.1, ISIC Rev.4 and NAICS 2017."],
        ["high_mean", "Above the threshold used in the paper: the aggregate capital per worker of the stage (US$112.9 thousand farm, US$118.2 thousand processing). The specification calls it an export weighted mean. The export weighted mean of the products would be higher (Samples sheet), so the paper's threshold is kept and named aggregate ratio of the stage."],
        ["high_median, quintile", "Export weighted median and quintiles of capital per worker within each stage, weights: exports 2012 to 2018. Products linked to the same farm types or industries share one value, so quintiles have unequal sizes (farm stage quintile 5 has one product)."],
        ["Not classified", "Products linked to no farm type or food or beverage industry (26 products, 1 percent of exports). They keep their own interaction in E4 so the sample equals the baseline, and are dropped where ln capital per worker is needed (E4b, E5)."],
        ["Rauch", "Rauch (1999) via the HS 2007 code that the UNSD conversion table assigns to each HS 2017 code. Conservative from the product file (con_34). Liberal: the class with the largest liberal trade weight in the product file, available for 385 of 860 products."],
        ["BEC", "BEC Rev.4 of each HS 2017 code (UNSD HS SITC BEC correlations, modal code). End use: intermediate or consumption. The 4 capital goods are grouped with intermediate goods in E7b. Inputs group: seeds, animal feed, live animals (wp_common.agro_input_flag)."],
        ["Location (E5)", "Cells origin x product x year with positive exports, classified products. Linear probability model, logit average marginal effects as robustness. MNE counts from the firm data (a firm counts once per cell)."],
        ["Event studies (E6)", "First year with an MNE exporter in the cell, no MNE in any earlier year, at least two years with positive exports before (three in the variant). Cells with an MNE in 2012 are always treated and excluded. Controls: never treated cells (no MNE in 2012 to 2018, at least two years with exports) and not yet treated cells. Event window -4 to 4, base -1."],
        ["Stars", "*** p<0.01, ** p<0.05, * p<0.1"]]
    for r in notes:
        ws.append(r)
    ws.column_dimensions["A"].width = 22; ws.column_dimensions["B"].width = 170; ws["A1"].font = Font(bold=True)
    for i in range(2, ws.max_row + 1):
        ws.cell(row=i, column=2).alignment = Alignment(wrap_text=True, vertical="top")
    XLSX.parent.mkdir(parents=True, exist_ok=True)
    wb.save(XLSX)
    print(f"workbook -> {XLSX}: {len(wb.sheetnames)} sheets, {sum(1 for r in regs if r['n'])} regressions, {len(ev)} event rows, {len(longs):,} long rows")


if __name__ == "__main__":
    main()
