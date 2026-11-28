"""
wp_agro_v5_workbook.py  --  docs/notes/WP_paperagro_v5_master_estimates.xlsx and docs/notes/figures_v5/
=====================================================================================================

    WP_YEARS=2012-2018 WP_SCOPES=agro python wp_agro_v5_workbook.py [--no-figures]

Builds the workbook of round v5 and its figures, written so that a reader who did not run the estimates can follow them:
every code of the scripts (FE4, EV2, g_ps, lnN, ...) is shown in words (wp_agro_v5_labels.py), sheets are named and ordered by
question, and the first sheets are Read me, Main results and Glossary.

Sheets: Read me, Main results, Glossary; 1.x where MNEs are; 2.x capital intensity; 3.x other product traits; 4.x to 6.x what
happens after an MNE enters (product cells, destination cells, new destination cells); 7.x checks of the event studies; 8.x
figure index and figure data; 9.x descriptives of the v4 draft; v4 E1a ... v4 E7c (the v4 sheets, numbers unchanged); All
estimates, one per row; Product classifications; Technical notes.
Figures: docs/notes/figures_v5/1_main_figures, 2_capital_intensity, 3_after_entry/<by_estimator|by_fixed_effects|by_sample|by_group>.
Inputs: output/wp_2012_2018/agro/v4/, output/wp_2012_2018/agro/v5/ (v5_regs_*.pkl, v5_desc_*.pkl, ev5_*.dta, ev5_match.parquet,
honest_*.txt), data/intermediate/wp/v5/.
"""
from __future__ import annotations

import json
import os
import pickle
import re
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("WP_HS17", "1")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_common as W  # noqa: E402
import wp_agro_v4_workbook as K  # noqa: E402
import wp_agro_v5_labels as L  # noqa: E402

OUT5 = W.WP_OUT / "agro" / "v5"
V5 = W.WP_INT / "v5"
XLSX = W.ROOT / "docs" / "notes" / "WP_paperagro_v5_master_estimates.xlsx"
FIGCACHE = W.WP_OUT / "agro" / "v5" / "v5_figure_tables.pkl"   # figure index and figure data of the last run with figures
# hooks used by wp_agro_v6_workbook.py (round v6): extra sheets, primary-set table, extra rows and columns of All estimates
HOOK_SHEETS = None      # callable(new, put_df, put_rows, text_sheet) -> list of dicts for All estimates
PRIMARY = None          # (title, header, rows) shown at the top of Main results
LONG_EXTRA_COLS: list = []
FIG_EXTRA = None        # (figure data capital, figure data events, figure index) added by round v6
READ_TITLE = "Multinationals and agricultural exports: all estimates, November 2026"
READ_EXTRA: list = []   # extra (label, text) rows of Read me
MAIN_TITLE = "Main results, in eight points (the numbers are in the sheets listed on the right)"
FIG = W.ROOT / "docs" / "notes" / "figures_v5"
OLD_FIG = [W.ROOT / "docs" / "notes" / "figures_E9", W.ROOT / "docs" / "notes" / "figures_E11"]
TEX4 = W.ROOT / "docs" / "overleaf_projects" / "WP_paperagro" / "tables" / "v4"

# fixed effects in words in the header row of every regression sheet
K.FE_SHORT = {k: v for k, v in L.FE_WORDS.items() if k.startswith("FE")}
K.FE_SHORT_WITHIN = dict(L.FE_WORDS_WITHIN)
K.FE_PARTS["origin x year"] = ["OY"]
K.FE_PARTS["oy"] = ["OY"]
K.COL_LAB.update({"terciles": "Terciles within stage", "quartiles": "Quartiles within stage", "quintiles": "Quintiles within stage",
                  "degree": "Degree of processing", "lnKL": "ln capital per worker", "high_PCI": "High PCI (cut at the export weighted median)",
                  "high_PCI_u": "High PCI (cut at the unweighted median)", "PCI": "PCI (continuous)", "PCI terciles": "PCI terciles",
                  "PCI and ln KL": "PCI and ln capital per worker", "KL (aggregate ratio) x PCI": "Capital intensity (stage ratio) x PCI",
                  "KL (median) x PCI": "Capital intensity (median) x PCI", "Rauch complete, conservative": "Rauch class (conservative)",
                  "Rauch complete, liberal": "Rauch class (liberal)"})
OUTS5 = {k: L.out_name(k) for k in L.OUT}
SMP5 = L.SAMPLE
EST5 = L.EST
FE5 = L.EV_FE
CELLS = L.CELLS
TERMS = ["Tm4", "Tm3", "Tm2", "Tm1", "Tp0", "Tp1", "Tp2", "Tp3", "Tp4", "Post_avg", "Av_tot"]
TLAB = L.TERM

# ---------------------------------------------------------------------------------------------------------------------
# sheet names, titles, codes of the estimation plan, how to read
# ---------------------------------------------------------------------------------------------------------------------
TITLE = {
    "E12a": "Where MNEs are: probability that at least one MNE exports the product, by stage",
    "E12b": "Where MNEs are: number of MNEs and MNE share of exports, by stage",
    "E12c": "Where MNEs are: foreign and domestic MNEs, by stage",
    "E12d": "Where MNEs are: year in which the first MNE enters, by stage",
    "E9a": "Exports and MNE presence in products with high and low capital intensity, at every cut-off, by stage",
    "E9b": "Exports and MNE presence: one coefficient for each US farm type or industry",
    "E9c": "Exports and MNE presence: high and low capital intensity with one cut-off for both stages",
    "E9d": "Exports and MNE presence: high and low capital intensity under other US measures of capital",
    "E10a": "Exports and MNE presence by product complexity (PCI), and where MNEs are by complexity",
    "E10b": "Exports and MNE presence by Rauch class, and where MNEs are by Rauch class",
    "E10c": "Exports and MNE presence by degree of processing, and where MNEs are by degree of processing",
    "E10d": "Exports and MNE presence by capital intensity and complexity together",
}
CODE = {"E12a": "E12.1, E5a by stage", "E12b": "E12.1, E5b by stage", "E12c": "E5c by stage", "E12d": "E5d by stage", "E9a": "E9a",
        "E9b": "E9b", "E9c": "E9c", "E9d": "E9d", "E10a": "E10a", "E10b": "E10b", "E10c": "E10c", "E10d": "E10d"}
HOW = {
    "loc": "How to read: each column is one regression across origin x product x year cells. A negative coefficient on capital "
           "intensity means that MNEs are less present in more capital intensive products.",
    "cut": "How to read: each column lets the link between exports and MNE presence differ for products above (high) and below (low) "
           "the cut-off named at the top. If capital intensity mattered, high would be clearly larger than low; the last p value "
           "tests whether they are equal.",
    "E9b": "How to read: one coefficient for each US farm type or industry (names and capital per worker in sheet 2.3). The slope "
           "rows say whether the coefficients rise with capital per worker across groups.",
    "trait": "How to read: the upper panels let the link between exports and MNE presence differ by the product trait in the title; "
             "the lower panels (Where MNEs are) show whether MNEs are more present in products with that trait.",
}
HOW_SHEET = {"E12a": "loc", "E12b": "loc", "E12c": "loc", "E12d": "loc", "E9a": "cut", "E9c": "cut", "E9d": "cut", "E9b": "E9b",
             "E10a": "trait", "E10b": "trait", "E10c": "trait", "E10d": "trait"}
NAME = {
    "E12 map": "1.0 Where MNEs are, summary", "E12a": "1.1 Presence by stage", "E12b": "1.2 Number and share by stage",
    "E12c": "1.3 Foreign and domestic MNEs", "E12d": "1.4 First entry by stage",
    "E9 map": "2.0 Capital intensity, summary", "E9a": "2.1 High vs low, every cut-off", "E9b": "2.2 By farm type or industry",
    "E9b groups": "2.3 Farm types and industries", "E9c": "2.4 One cut-off, both stages", "E9d": "2.5 Other capital measures",
    "E9e": "2.6 Check with country data",
    "E10 map": "3.0 Other traits, summary", "E10a": "3.1 Product complexity (PCI)", "E10b": "3.2 Rauch classes",
    "E10b classes": "3.3 Rauch classes, products", "E10c": "3.4 Degree of processing", "E10d": "3.5 Capital and complexity",
    "E11 map": "4.0 After entry, summary",
    "E11 honest": "7.1 Sensitivity to pre-trends", "E11 counts": "7.2 Number of cells",
    "fig index": "8.0 Figure index", "E9 figdata": "8.1 Figure data, capital", "E11 figdata": "8.2 Figure data, after entry",
    "D1": "9.1 Exports by country", "D2": "9.2 MNEs in exports", "D3": "9.3 Parent countries", "D4": "9.4 MNE groups",
    "Long format": "All estimates, one per row", "Classifications": "Product classifications", "Notes": "Technical notes",
}
EV_SECTION = {"A": ("4", "Product"), "B": ("5", "Destination"), "E": ("6", "New dest.")}
EV_BLOCK = [  # code, short name for the sheet, description, code of the estimation plan
    ("std", "estimators", "every estimator, under each comparison rule", "E11b, E11d.1"),
    ("fe", "fixed effects", "OLS with different fixed effects, cell trends, stacked regressions and the trend adjustment of Freyaldenhoven, Hansen and Shapiro", "E11c"),
    ("treatps", "type and size", "by type and size of the entry, same selection rule for entered and comparison cells", "E11d.2, E11d.3"),
    ("treat", "type and size, v4", "by type and size of the entry with the comparison cells of the v4 draft, and by entry year", "E11d.2 to E11d.4"),
    ("het", "by capital", "by capital intensity, type of production and degree of processing", "E11e"),
    ("het2", "by PCI and Rauch", "by product complexity (PCI) and Rauch class", "E11e with E10a, E10b"),
    ("add", "stacked and PPML", "stacked regression by entry year and Wooldridge PPML", "E11b vi, vii"),
    ("match", "matched cells", "stacked regression with matched comparison cells (CEM)", "E11b ix"),
    ("spill", "spillovers", "information spillovers: new destinations of local firms", "E11a.4"),
    ("placebo", "placebo", "placebo with the entry year moved three years earlier", "E11"),
]
V4_TITLE = {"E1a": "Exports by country", "E1b": "Exports by type of production", "E1c": "MNEs by country",
            "E5a": "Where MNEs are (v4 table)", "E6a": "Event study, product cells (v4)", "E6b": "Event study, destination cells (v4)"}


def ev_sheet_name(P, k, short):
    sec, cell = EV_SECTION[P]
    return f"{sec}.{k} {cell}, {short}"[:31]


def stars(p):
    return K.stars(p)


def slug(s: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", s.lower())).strip("_")


def _readable_labels() -> None:
    """Readable names for the v5 regressors and columns (cuts, farm types and industries, PCI, degree of processing)."""
    meta = json.load(open(V5 / "classes_v5_cuts.json", encoding="utf-8"))
    base = {}
    for k, v in meta["labels"].items():
        col = k.split("|")[-1]
        base[col] = re.sub(r"\s*\(US\$[^)]*\)$", "", v).replace(" (v4 high_mean)", "").replace(" (v4 high_median)", "")
    for col, name in base.items():
        K.COL_LAB.setdefault(col, L.cutname(L.text(name)).capitalize() if name else name)
    cls = pd.read_parquet(V5 / "classes_v5.parquet")
    src = cls.dropna(subset=["src_id"]).groupby("src_id").agg(lab=("src_label", "first"), kl=("kl", "first"), st=("stage", "first"))
    srcname = {int(i): f"{r['st'].lower()} group {int(i)}: {r['lab']} (US${r['kl']:,.0f} thousand per worker)" for i, r in src.iterrows()}
    old = K.label
    extra = {"hi_pci": "High PCI (export weighted median)", "hi_pci_u": "High PCI (unweighted median)", "pci_t2": "PCI, middle tercile",
             "pci_t3": "PCI, highest tercile", "PCI_p": "PCI", "deg_first": "First processing (primary omitted)",
             "deg_further": "Further processing (primary omitted)", "r_ref": "Reference priced (homogeneous omitted)",
             "r_diff": "Differentiated (homogeneous omitted)", "lnkl": "ln capital per worker"}
    who = {"lnN": "ln number of MNEs", "D": "At least one MNE"}

    def label(v: str) -> str:
        if v in extra:
            return extra[v]
        if v.startswith("hi_high_") or v.startswith("hi_pool_"):
            return "High capital intensity, " + L.cutname(L.text(base.get(v[3:], v[3:])))
        m = re.match(r"^(tercile|quartile|quintile)(\d)$", v)
        if m:
            return f"{m.group(1).capitalize()} {m.group(2)} of capital intensity (first omitted)"
        m = re.match(r"^kp_(mean|median)_(hh|hl|lh)$", v)
        if m:
            return {"hh": "High capital intensity, high PCI", "hl": "High capital intensity, low PCI",
                    "lh": "Low capital intensity, high PCI"}[m.group(2)] + " (low capital intensity, low PCI omitted)"
        m = re.match(r"^(lnN|D)_(high_\w+?|pool_\w+?|high_alt_\w+?)_(hi|lo|nc)$", v)
        if m:
            return f"{who[m.group(1)]} x {dict(hi='high', lo='low', nc='not classified')[m.group(3)]}"
        m = re.match(r"^(lnN|D)_(tercile_stage|quartile_stage|PCI_tercile)_[gt](\d)$", v)
        if m:
            kind = {"tercile_stage": "capital intensity tercile", "quartile_stage": "capital intensity quartile", "PCI_tercile": "PCI tercile"}[m.group(2)]
            return f"{who[m.group(1)]} x {kind} {m.group(3)}"
        m = re.match(r"^(lnN|D)_src(\d+)$", v)
        if m:
            return f"{who[m.group(1)]} x {srcname.get(int(m.group(2)), 'group ' + m.group(2))}"
        m = re.match(r"^(lnN|D)_(high_PCI|high_PCI_u)_(hi|lo)$", v)
        if m:
            return f"{who[m.group(1)]} x {'high' if m.group(3) == 'hi' else 'low'} PCI"
        m = re.match(r"^(lnN|D)_rauch_full_(con|lib)_(hom|ref|diff|na)$", v)
        if m:
            return f"{who[m.group(1)]} x " + {"hom": "homogeneous", "ref": "reference priced", "diff": "differentiated", "na": "not classified"}[m.group(3)]
        m = re.match(r"^(lnN|D)_kr_(na|other)$", v)
        if m:
            return f"{who[m.group(1)]} x not classified (capital intensity or Rauch class)"
        m = re.match(r"^(lnN|D)_x_pci$", v)
        if m:
            return f"{who[m.group(1)]} x PCI"
        return L.text(old(v))
    K.label = label


# ---------------------------------------------------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------------------------------------------------
def load_regs():
    regs, desc = [], {}
    for f in sorted(OUT5.glob("v5_regs_*.pkl")):
        regs += pickle.load(open(f, "rb"))
    for f in sorted(OUT5.glob("v5_desc_*.pkl")):
        desc.update(pickle.load(open(f, "rb")))
    return regs, desc


def load_events() -> pd.DataFrame:
    ev = []
    for f in sorted(OUT5.glob("ev5_*_*.dta")):
        try:
            ev.append(pd.read_stata(f))
        except Exception:  # noqa: BLE001  (a block still running has an incomplete file)
            print(f"   skipped {f.name} (incomplete)")
    m = OUT5 / "ev5_match.parquet"
    if m.exists():
        ev.append(pd.read_parquet(m))
    if not ev:
        return pd.DataFrame()
    e = pd.concat(ev, ignore_index=True)
    # csnev of the std block used the csdid 2.0.3 default (not yet treated) and repeats cs: replaced by the csnev block
    e = e[~((e["block"] == "std") & (e["est"] == "csnev"))]
    e.loc[e["block"] == "csnev", "block"] = "std"
    # dCDH: when a placebo cannot be estimated the command posts no e(b) and the average of the effects is missing; it is the
    # mean of the five effects here, with a standard error that ignores their covariances
    k = ["cellset", "block", "sample", "group", "outcome", "est", "fe"]
    has = set(map(tuple, e.loc[(e["est"] == "dcdh") & (e["term"] == "Post_avg"), k].values))
    add = []
    from scipy.stats import norm
    for key, g in e[(e["est"] == "dcdh") & e["term"].isin(["Tp0", "Tp1", "Tp2", "Tp3", "Tp4"])].groupby(k):
        if key in has or len(g) < 5:
            continue
        b = g["b"].mean(); se = float(np.sqrt((g["se"] ** 2).sum()) / 5)
        add.append(dict(zip(k, key), term="Post_avg", b=b, se=se, p=float(2 * norm.sf(abs(b / se))), N=g["N"].max(),
                        ntreat=g["ntreat"].max(), ncontrol=g["ncontrol"].max(), status="ok"))
    if add:
        e = pd.concat([e, pd.DataFrame(add)], ignore_index=True)
    why = {("bjs", "error 481"): "Not estimable: the fixed effects cannot be estimated on the cells without entry",
           ("T", "error 481"): "Not estimable: the fixed effects cannot be estimated on the cells without entry",
           ("T", "error 430"): "Not estimable: the estimation did not converge",
           ("fhs", "error 198"): "Not estimable: xtevent stopped with error 198 in every cell set (product, destination and new destination cells); v5 has no Freyaldenhoven et al. estimate"}
    for (es, stt), msg in why.items():
        e.loc[(e["est"] == es) & (e["status"] == stt), "status"] = msg
    e.loc[e["status"] == "estat error 498", "status"] = "Not estimable: too few cells in this group"
    # correction V6-02 point 1 (2026-11-27): the OLS, PPML and stacked averages of event times 0 to 4 divided by five even when
    # fewer post coefficients exist (rows by cohort and placebo). The average of the coefficients that exist is the stored value
    # times 5 / k, and so is its standard error; the p value does not change.
    post = e[e["est"].isin(["twfe", "ppml", "stk"]) & e["term"].isin(["Tp0", "Tp1", "Tp2", "Tp3", "Tp4"]) & np.isfinite(e["b"]) & (e["se"] > 1e-9)]
    kk = post.groupby(k).size().rename("kpost")
    e = e.merge(kk, left_on=k, right_index=True, how="left")
    fix = e["est"].isin(["twfe", "ppml", "stk"]) & (e["term"] == "Post_avg") & (e["kpost"] < 5) & (e["kpost"] > 0)
    e.loc[fix, "b"] = e.loc[fix, "b"] * 5 / e.loc[fix, "kpost"]
    e.loc[fix, "se"] = e.loc[fix, "se"] * 5 / e.loc[fix, "kpost"]
    e = e.drop(columns="kpost")
    s = (e["est"] == "sa") & (e["outcome"] == "N")
    e.loc[s, ["b", "se", "p"]] = np.nan
    e.loc[s, "status"] = "Not reported: the variance of Sun and Abraham is degenerate here (no MNE in any comparison cell or year before entry)"
    s = (e["cellset"] == "E") & (e["est"] == "sa")
    e.loc[s, ["b", "se", "p"]] = np.nan
    e.loc[s, "status"] = "Not reported: the variance of Sun and Abraham is degenerate here (outcome zero before entry by construction)"
    s = (e["cellset"] == "E") & (e["outcome"] == "lnXL")
    e.loc[s, ["b", "se", "p"]] = np.nan
    e.loc[s, "status"] = "Not identified: these cells have no local exports before entry by construction"
    e.loc[e["status"].str.startswith("error"), "status"] = "Not estimable (" + e["status"] + ")"
    return e


def honest() -> pd.DataFrame:
    rows = []
    for f in OUT5.glob("honest_*.txt"):
        t = f.read_text(errors="ignore")
        m = re.match(r"honest_(\w)_(g_\w+?)_(\w+)\.txt", f.name)
        if not m:
            continue
        P, g, y = m.groups()
        for kind in ("RM", "SD"):
            blk = t.split(f"HONEST {kind}")[1] if f"HONEST {kind}" in t else ""
            blk = blk.split("HONEST")[0]
            tab = re.findall(r"\|\s*([\d.]+|\.)\s*\|\s*(-?[\d.]+)\s*\|\s*(-?[\d.]+)\s*\|", blk)
            orig = [r for r in tab if r[0] == "."]
            grid = [(float(a), float(b), float(c)) for a, b, c in tab if a != "."]
            brk = next((M for M, lb, ub in grid if lb <= 0 <= ub), np.nan)
            rows.append({"Cells": L.CELLS_SHORT[P], "Comparison": L.SAMPLE_SHORT.get(g, g), "Outcome": L.out_name(y),
                         "How large a violation of parallel trends is allowed":
                             "relative to the largest change before entry (Mbar)" if kind == "RM" else "change in the slope of the trend (M)",
                         "95 percent interval without violations": f"[{orig[0][1]}, {orig[0][2]}]" if orig else "",
                         "Smallest violation at which the interval includes zero": brk,
                         "Interval at each size of violation": "; ".join(f"{M:g}: [{lb:.3f}, {ub:.3f}]" for M, lb, ub in grid)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------------------------------
# summary tables (one row per variant)
# ---------------------------------------------------------------------------------------------------------------------
def e9_map(regs, desc, cls_meta) -> pd.DataFrame:
    comp = desc.get("E9_composition", pd.DataFrame())
    loc = {(r["panel"].split(" stage")[0], r["col"], r["fe"]): r for r in regs if r["sheet"] == "E12a" and r["est"] == "OLS"}
    rows = []
    for r in regs:
        if r["sheet"] not in ("E9a", "E9c", "E9d") or not r["n"]:
            continue
        m = re.match(r"(?:(Farm|Processing) stage|Pooled stages), (lnN|D) x (.*?), (ln exports, .*)$", r["panel"])
        if not m:
            continue
        st, reg, cut, dl = m.groups()
        hi = next((c for v, c in r["cells"].items() if v.endswith("_hi")), (np.nan,) * 3)
        lo = next((c for v, c in r["cells"].items() if v.endswith("_lo")), (np.nan,) * 3)
        row = {"Sheet": NAME[r["sheet"]], "Stage": st or "Both stages", "Exports of": "all firms" if "all" in dl else "local firms",
               "MNE presence measured by": L.REG[reg], "Products split by": L.cut_words(cut), "Fixed effects": L.FE_WORDS.get(r["fe"], r["fe"]),
               "Observations": r["n"], "High: coefficient": hi[0], "High: SE": hi[1], "Low: coefficient": lo[0], "Low: SE": lo[1],
               "p value, high and low are equal": r["tests"].get("high = low", np.nan)}
        if "terciles" in cut or "quartiles" in cut:
            row.update({f"Group {i + 1}: coefficient": c[0] for i, c in enumerate(r["cells"].values())})
            row["p value, all groups are equal"] = r["tests"].get("all groups equal", np.nan)
        thr = re.search(r"threshold: (.*)$", cut)
        if thr is not None and len(comp):
            c = comp[(comp["Stage"] == (st or "Pooled")) & (comp["Cut"] == thr.group(1)) & (comp["Group"] == "High")]
            if len(c):
                row.update({"High group: products": int(c["Products"].iloc[0]), "High group: % of the stage's exports": c["Share of stage exports (%)"].iloc[0],
                            "High group: % of its exports in field crops": c["Field crops, % of group exports"].iloc[0]})
            col = next((k.split("|")[1] for k, v in cls_meta["labels"].items() if v == thr.group(1) and k.startswith(f"{st}|")), None)
            for fe, lab in (("origin x year + type of production", "origin x year and type"), ("origin x year", "origin x year")):
                lr = loc.get((st, col, fe)) if col else None
                if lr is not None:
                    c = list(lr["cells"].values())[0]
                    row.update({f"Where MNEs are, high group (FE {lab}): coefficient": c[0], f"Where MNEs are (FE {lab}): SE": c[1]})
        rows.append(row)
    for r in regs:
        if r["sheet"] == "E9b" and r["n"] and r.get("slope"):
            st = r["panel"].split(" stage")[0]
            row = {"Sheet": NAME["E9b"], "Stage": st, "Exports of": "all firms" if "all firms" in r["panel"] else "local firms",
                   "MNE presence measured by": L.REG["lnN" if "lnN" in r["panel"] else "D"],
                   "Products split by": "one coefficient per farm type or industry", "Fixed effects": L.FE_WORDS.get(r["fe"], r["fe"]),
                   "Observations": r["n"], "p value, all groups are equal": r["tests"].get("all groups equal", np.nan)}
            for k, v in r["slope"].items():
                row[f"Slope across groups on ln capital per worker, {k}"] = v[0]; row[f"Slope SE, {k}"] = v[1]; row[f"Slope p value, {k}"] = v[2]
            rows.append(row)
    return pd.DataFrame(rows)


def e10_map(regs) -> pd.DataFrame:
    rows = []
    for r in regs:
        if r["sheet"] not in ("E10a", "E10b", "E10c", "E10d") or not r["n"]:
            continue
        row = {"Sheet": NAME[r["sheet"]], "Specification": L.panel(r["panel"]),
               "Column": L.FE_WORDS.get(str(r["col"]), K.COL_LAB.get(r["col"], r["col"])), "Observations": r["n"]}
        for v, c in r["cells"].items():
            row[f"{K.label(v)}: coefficient"] = c[0]; row[f"{K.label(v)}: SE"] = c[1]
        for t, p in r["tests"].items():
            row[L.test_name(t)] = p
        rows.append(row)
    return pd.DataFrame(rows)


def e12_map(regs) -> pd.DataFrame:
    rows = []
    for r in regs:
        if not r["sheet"].startswith("E12") or not r["n"]:
            continue
        m = re.match(r"(Farm|Processing) stage, (.*?), FE (.*)$", r["panel"])
        st, what, fe = m.groups() if m else ("", r["panel"], r["fe"])
        row = {"Sheet": NAME[r["sheet"]], "Stage": st, "Dependent variable": L.REG.get(what, what), "Fixed effects": L.FE_WORDS.get(fe, fe),
               "Capital intensity measured by": K.COL_LAB.get(r["col"], r["col"]), "Estimator": r["est"], "Observations": r["n"]}
        for i, (v, c) in enumerate(r["cells"].items()):
            row[f"Coefficient {i + 1}"] = f"{K.label(v)}: {c[0]:.3f}{stars(c[2])} ({c[1]:.3f})"
        rows.append(row)
    return pd.DataFrame(rows)


def e11_map(ev: pd.DataFrame, names: dict) -> pd.DataFrame:
    if not len(ev):
        return pd.DataFrame()
    k = ["cellset", "block", "sample", "group", "outcome", "est", "fe"]
    post = ev[ev["term"] == "Post_avg"].set_index(k)
    pre = ev[ev["term"] == "pre_test"].set_index(k)["p"].rename("pre")
    out = post[["b", "se", "p", "N", "ntreat", "ncontrol"]].join(pre, how="left").reset_index()
    fail = ev[ev["status"] != "ok"].drop_duplicates(k)[k + ["status"]]
    out = pd.concat([out, fail], ignore_index=True)
    pl = ev[(ev["block"] == "placebo") & (ev["term"] == "Post_avg")].set_index(["cellset", "sample", "outcome", "est"])["b"].rename("plac")
    out = out.join(pl, on=["cellset", "sample", "outcome", "est"])
    order = {b[0]: i for i, b in enumerate(EV_BLOCK)}
    so = {s: i for i, s in enumerate(L.SAMPLE_ORDER)}
    out = out.assign(_o=out["block"].map(order), _so=out["sample"].map(so).fillna(99)).sort_values(["cellset", "_o", "_so", "group", "outcome", "est"])
    res = pd.DataFrame({
        "Cells": out["cellset"].map(L.CELLS_SHORT), "Sheet": [names.get((c, b), b) for c, b in zip(out["cellset"], out["block"])],
        "Comparison": out["sample"].map(L.SAMPLE_SHORT).fillna(out["sample"]), "Group": out["group"].map(L.group_name),
        "Outcome": out["outcome"].map(L.out_name), "Estimator": out["est"].map(L.EST_SHORT).fillna(out["est"]),
        "Fixed effects": out["fe"].map(L.EV_FE).fillna(out["fe"]), "Average effect, years 0 to 4": out["b"], "SE": out["se"],
        "p value": out["p"], "Stars": out["p"].map(stars), "p value, no difference before entry": out["pre"],
        "Placebo average effect": out["plac"], "Entered cells": out["ntreat"], "Comparison cells": out["ncontrol"], "Observations": out["N"],
        "Note": out["status"].where(out["status"].notna() & (out["status"] != "ok"), "")})
    return res


def event_sheet(ev: pd.DataFrame, cellset: str, block: str, title: str) -> list[list]:
    e = ev[(ev["cellset"] == cellset) & (ev["block"] == block)]
    so = {s: i for i, s in enumerate(L.SAMPLE_ORDER)}
    e = e.assign(_so=e["sample"].map(so).fillna(99)).sort_values("_so", kind="stable")
    rows = [[title],
            ["How to read: each column compares cells where a multinational entered with comparison cells, year by year, relative to the "
             "year before entry. Rows before the year of entry show whether the two groups were already moving apart (they should be "
             "close to zero; the p value below tests that they are all zero). The average effect summarizes the year of entry and the "
             "four years after."]]
    for (smp, grp, fe), x in e.groupby(["sample", "group", "fe"], sort=False):
        combos = list(dict.fromkeys(zip(x["outcome"], x["est"])))
        rows.append([f"Comparison: {SMP5.get(smp, smp)}. Group: {L.group_name(grp)}. Fixed effects: {FE5.get(fe, fe)}."])
        rows.append(["Outcome"] + [OUTS5.get(o, o) for o, s in combos])
        rows.append(["Estimator"] + [L.EST_SHORT.get(s, s) for o, s in combos])
        for t in TERMS:
            b, s_ = [], []
            for o, s in combos:
                r = x[(x["outcome"] == o) & (x["est"] == s) & (x["term"] == t)]
                if len(r) and np.isfinite(r["b"].iloc[0]):
                    if not (r["se"].iloc[0] > 1e-9):
                        b.append("0 by construction" if abs(r["b"].iloc[0]) < 5e-4 else f"{r['b'].iloc[0]:.3f}, no variation"); s_.append("")
                    else:
                        b.append(f"{r['b'].iloc[0]:.3f}{stars(r['p'].iloc[0])}"); s_.append(f"({r['se'].iloc[0]:.3f})")
                else:
                    b.append(""); s_.append("")
            if any(b):
                rows += [[TLAB[t]] + b, [""] + s_]
        rows.append(["p value, no difference before entry (joint test)"] + [
            (lambda r: f"{r['p'].iloc[0]:.3f}" if len(r) and np.isfinite(r["p"].iloc[0]) else "")(x[(x["outcome"] == o) & (x["est"] == s) & (x["term"] == "pre_test")])
            for o, s in combos])
        for lab, fld in (("Observations", "N"), ("Entered cells", "ntreat"), ("Comparison cells", "ncontrol")):
            rows.append([lab] + [(lambda v: f"{int(v):,}" if np.isfinite(v) and v > 0 else "")(x[(x["outcome"] == o) & (x["est"] == s)][fld].max())
                                 for o, s in combos])
        rows.append(["Note"] + ["; ".join(sorted(set(x[(x["outcome"] == o) & (x["est"] == s)]["status"]) - {"ok"})) for o, s in combos])
    rows.append([f"Standard errors in parentheses, clustered by {L.CLUSTER[cellset]}. *** p<0.01, ** p<0.05, * p<0.1. Reference year: the "
                 "year before entry (Borusyak, Jaravel and Spiess: the years before 3 years before entry; de Chaisemartin and D'Haultfoeuille: "
                 "each placebo compares an earlier year with the year before entry). Logs only on positive values."])
    return rows


def friendly_rows(rows: list[list], sheet: str, v5: bool) -> tuple[list[list], int]:
    """Plain language panel labels, test labels and title in the rows of K.reg_block; returns the rows and the number of rows added
    at the top (the red marks shift by that number)."""
    out = [list(r) for r in rows]
    for i in range(len(out) - 1):
        if len(out[i]) == 1 and out[i + 1] and out[i + 1][0] == "Dependent variable":
            out[i][0] = L.panel(out[i][0])
        if out[i] and isinstance(out[i][0], str) and out[i][0].startswith("p value of the test: "):
            out[i][0] = L.text(L.test_name(out[i][0][len("p value of the test: "):]))
    for r in out:
        if r and r[0] == "Dependent variable":
            r[1:] = [L.REG.get(v, v) if isinstance(v, str) else v for v in r[1:]]
    if not v5:
        return out, 0
    out[0] = [f"{TITLE.get(sheet, sheet)} (estimation plan: {CODE.get(sheet, sheet)})"]
    out.insert(1, [HOW[HOW_SHEET[sheet]]] if sheet in HOW_SHEET else [""])
    out[-1] = [out[-1][0].replace("Red: printed in the paper.", "").strip()]
    return out, 1


# ---------------------------------------------------------------------------------------------------------------------
# figures
# ---------------------------------------------------------------------------------------------------------------------
XS = {"Tm4": -4, "Tm3": -3, "Tm2": -2, "Tm1": -1, "Tp0": 0, "Tp1": 1, "Tp2": 2, "Tp3": 3, "Tp4": 4}
XT = ["4 or more\nbefore", "3\nbefore", "2\nbefore", "1\nbefore", "Year of\nentry", "1\nafter", "2\nafter", "3\nafter", "4 or more\nafter"]
COLORS = ["#1f4e79", "#c55a11", "#548235", "#7030a0", "#bf9000", "#2e75b6", "#7f7f7f", "#c00000", "#00a3a3", "#e377c2", "#8c564b", "#000000"]
FE_FIG = {"FE4": "Fixed effects: origin x destination x product\nand origin x destination x year",
          "FE6": "Fixed effects: also origin x product x year\nand destination x product x year"}


def ev_note(P: str) -> str:
    return (f"Each point compares {L.CELLS[P].split(' (')[0]} where a multinational entered with comparison cells, relative to the year "
            "before entry (dashed line). Points before entry show whether the two groups were already moving apart. Bars are 95 percent "
            f"confidence intervals. Fixed effects: cell and origin x year{' and destination x year' if P != 'A' else ''}. Standard errors "
            f"clustered by {L.CLUSTER[P]}.")


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False})
    return plt


def draw(a, sel: pd.DataFrame, series: str, labeler, figname: str, panel: str, figdata: list) -> int:
    keys = list(dict.fromkeys(sel[series]))
    n = len(keys); drawn = 0
    for k, key in enumerate(keys):
        x = sel[(sel[series] == key) & sel["term"].isin(XS)]
        x = x[np.isfinite(x["b"]) & (x["se"] > 1e-9)]
        if not len(x):
            continue
        off = (k - (n - 1) / 2) * min(0.1, 0.6 / max(n, 1))
        xx = x["term"].map(XS).values + off; yy = x["b"].values; ee = 1.96 * x["se"].values
        if "Tm1" not in set(x["term"]):
            xx = np.r_[xx, -1 + off]; yy = np.r_[yy, 0]; ee = np.r_[ee, 0]
        lab = labeler(key)
        a.errorbar(xx, yy, yerr=ee, fmt="o", ms=3.5, lw=0.9, capsize=1.5, color=COLORS[k % len(COLORS)], label=lab)
        drawn += 1
        for _, r in x.iterrows():
            figdata.append({"Figure file": figname, "Panel": panel, "Series": lab, "Years since entry": XS[r["term"]], "Coefficient": r["b"],
                            "Lower 95": r["b"] - 1.96 * r["se"], "Upper 95": r["b"] + 1.96 * r["se"]})
    a.axhline(0, color="grey", lw=0.6, ls="--"); a.axvline(-0.5, color="grey", lw=0.6, ls="--")
    a.set_xticks(range(-4, 5)); a.set_xticklabels(XT, fontsize=6.5)
    return drawn


def save(fig, folder: Path, name: str, index: list, title: str, what: str):
    folder.mkdir(parents=True, exist_ok=True)
    fig.savefig(folder / f"{name}.pdf"); fig.savefig(folder / f"{name}.png", dpi=150)
    index.append({"Folder": str(folder.relative_to(FIG.parent)).replace("\\", "/"), "File": f"{name}.png and .pdf", "Title": title, "What it shows": what})


def event_fig(sel, series, labeler, folder, name, title, ylab, note, index, figdata, what):
    plt = _plt()
    ok = sel[sel["term"].isin(XS) & np.isfinite(sel["b"]) & (sel["se"] > 1e-9)]
    if not len(ok):
        return
    fig, a = plt.subplots(figsize=(8, 5.2))
    n = draw(a, sel, series, labeler, name, "", figdata)
    a.set_title(title, fontsize=10); a.set_ylabel(ylab, fontsize=8.5); a.set_xlabel("Years relative to the entry of the first multinational", fontsize=8.5)
    if n > 1:
        a.legend(fontsize=7, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2 if n > 3 else n)
    fig.text(0.01, 0.01, note, fontsize=6.5, wrap=True)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    save(fig, folder, name, index, title, what); plt.close(fig)


def grid_fig(panels, ncols, folder, name, title, note, index, figdata, what, size=(12, 7.5)):
    plt = _plt()
    nrows = int(np.ceil(len(panels) / ncols))
    fig, ax = plt.subplots(nrows, ncols, figsize=size, squeeze=False)
    handles = None
    for i, (sel, series, labeler, sub, ylab) in enumerate(panels):
        a = ax[i // ncols][i % ncols]
        draw(a, sel, series, labeler, name, sub, figdata)
        a.set_title(sub, fontsize=9); a.set_ylabel(ylab, fontsize=7.5)
        if handles is None:
            handles = a.get_legend_handles_labels()
    for j in range(len(panels), nrows * ncols):
        ax[j // ncols][j % ncols].axis("off")
    if handles and len(handles[0]) > 1:
        fig.legend(*handles, loc="lower center", ncol=min(4, len(handles[0])), frameon=False, fontsize=8, bbox_to_anchor=(0.5, 0.42 / size[1]))
    fig.suptitle(title, fontsize=11)
    fig.text(0.01, 0.005, note, fontsize=7, wrap=True)
    fig.tight_layout(rect=(0, 0.85 / size[1], 1, 1 - 0.3 / size[1]))
    save(fig, folder, name, index, title, what); plt.close(fig)


def fig_e9(regs, desc, cls_meta, figdata: list, index: list, folder: Path) -> dict:
    """Ladder and group figures; returns the paths of the two shown among the main figures."""
    plt = _plt()
    main = {}
    regw = {"lnN": "the number of MNEs", "D": "MNE presence"}
    regf = {"lnN": "number_of_MNEs", "D": "any_MNE"}
    ylab = {"lnN": "Coefficient of ln exports\non ln number of MNEs", "D": "Coefficient of ln exports\non at least one MNE"}
    for reg in ("lnN", "D"):
        for dl in ("ln exports, all firms", "ln exports, local firms"):
            who = "all" if "all" in dl else "local"
            fig, ax = plt.subplots(2, 2, figsize=(11, 8), sharey="row")
            for i, st in enumerate(("Farm", "Processing")):
                for j, fe in enumerate(("FE4", "FE6")):
                    a = ax[i, j]; pts = []
                    for c in cls_meta["ladder"][st]:
                        lab = cls_meta["labels"][f"{st}|{c}"]
                        t = float(re.search(r"US\$([\d,.]+) thousand\)$", lab).group(1).replace(",", ""))
                        r = next((r for r in regs if r["sheet"] == "E9a" and r["col"] == fe and r["panel"] == f"{st} stage, {reg} x high/low, threshold: {lab}, {dl}"), None)
                        if r is not None:
                            pts.append((t, r["cells"].get(f"{reg}_{c}_hi"), r["cells"].get(f"{reg}_{c}_lo")))
                    pts.sort()
                    x = np.arange(len(pts))
                    for g, col, off, k in (("High capital intensity (above the cut-off)", "#1f4e79", -0.12, 1), ("Low capital intensity (below)", "#c55a11", 0.12, 2)):
                        vals = [p[k] for p in pts]
                        a.errorbar([xi + off for xi, v in zip(x, vals) if v], [v[0] for v in vals if v], yerr=[1.96 * v[1] for v in vals if v],
                                   fmt="o", color=col, ms=4, capsize=2, label=g)
                        for (t, *_), v in zip(pts, vals):
                            if v:
                                figdata.append({"Figure file": f"capital_{regf[reg]}_{who}_firms_every_cut_off", "Panel": f"{st} stage, {fe}",
                                                "Series": g, "Cut-off (US$ thousand per worker)": t, "Coefficient": v[0],
                                                "Lower 95": v[0] - 1.96 * v[1], "Upper 95": v[0] + 1.96 * v[1]})
                    a.set_xticks(x); a.set_xticklabels([f"{p[0]:.0f}" for p in pts], fontsize=7, rotation=45)
                    a.axhline(0, color="grey", lw=0.6, ls="--")
                    a.set_title(f"{st} stage\n{FE_FIG[fe]}", fontsize=8.5)
                    a.set_xlabel("Cut-off: capital per worker (US$ thousand)", fontsize=8)
                    if j == 0:
                        a.set_ylabel(ylab[reg], fontsize=8)
            ax[0, 0].legend(fontsize=8, frameon=False)
            title = f"Exports of {who} firms and {regw[reg]}: high and low capital intensity at every cut-off"
            fig.suptitle(title, fontsize=11)
            fig.text(0.01, 0.005, "Each pair of points comes from one regression that lets the link between exports and MNEs differ between products "
                     "above and below the cut-off. Blue points above the orange ones mean a stronger link in capital intensive products. Standard "
                     "errors clustered by origin and destination pair; bars are 95 percent confidence intervals.", fontsize=7, wrap=True)
            fig.tight_layout(rect=(0, 0.04, 1, 0.96))
            name = f"capital_{regf[reg]}_{who}_firms_every_cut_off"
            save(fig, folder, name, index, title, "Sheet 2.1. High and low coefficients for every cut-off of capital per worker, by stage, "
                 "with two sets of fixed effects.")
            plt.close(fig)
            if reg == "lnN" and who == "all":
                main["ladder"] = folder / f"{name}.png"
    g = desc.get("E9b_groups")
    if g is None:
        return main
    for reg in ("lnN", "D"):
        for dl in ("ln exports, all firms", "ln exports, local firms"):
            who = "all" if "all" in dl else "local"
            fig, ax = plt.subplots(2, 2, figsize=(12, 9))
            for i, st in enumerate(("Farm", "Processing")):
                gg = g[g["stage"] == st].set_index("src_id")
                for j, fe in enumerate(("FE4", "FE6")):
                    a = ax[i, j]
                    r = next((r for r in regs if r["sheet"] == "E9b" and r["col"] == fe and r["panel"] == f"{st} stage, {reg} x farm type or industry, {dl}"), None)
                    if r is None:
                        continue
                    labeled = []
                    for v, c in r["cells"].items():
                        row = gg.loc[int(v.split("src")[1])]
                        sh = row["Share of stage exports (%)"]
                        a.errorbar(row["lnkl"], c[0], yerr=1.96 * c[1], fmt="none", ecolor="#9dc3e6", lw=0.8)
                        a.scatter(row["lnkl"], c[0], s=10 + 700 * sh / 100, color="#1f4e79", alpha=0.7, zorder=3)
                        if sh >= 5:
                            parts = row["label"].replace(" + 1 more", "").split(" + ")
                            nm = parts[0] + (f" and {parts[1]}" if len(parts) > 1 else "") + (" and others" if "more" in row["label"] else "")
                            labeled.append((row["lnkl"], c[0], nm[:1].upper() + nm[1:] + f" ({sh:.0f}%)"))
                        figdata.append({"Figure file": f"capital_{regf[reg]}_{who}_firms_by_farm_type_or_industry", "Panel": f"{st} stage, {fe}",
                                        "Series": row["label"], "Capital per worker (US$ thousand)": row["kl"], "Share of the stage's exports (%)": sh,
                                        "Products": row["products"], "Coefficient": c[0], "Lower 95": c[0] - 1.96 * c[1], "Upper 95": c[0] + 1.96 * c[1]})
                    labeled.sort(key=lambda z: (round(z[0], 1), z[1]))
                    for q, (lx, ly, nm) in enumerate(labeled if j == 0 else []):
                        a.annotate(nm, (lx, ly), fontsize=6.3, xytext=(6, 7 if q % 2 else -9), textcoords="offset points")
                    ticks = [10, 20, 50, 100, 200, 500] if st == "Farm" else [50, 100, 200, 500]
                    a.set_xticks(np.log(ticks)); a.set_xticklabels([str(z) for z in ticks])
                    sl = r.get("slope") or {}
                    s1, s2 = sl.get("export weighted"), sl.get("unweighted")
                    sub = f"{st} stage\n{FE_FIG[fe]}"
                    if s1 and s2:
                        sub += f"\nSlope across groups: {s1[0]:.2f} (SE {s1[1]:.2f}) weighted by exports, {s2[0]:.2f} (SE {s2[1]:.2f}) unweighted"
                    a.set_title(sub, fontsize=8)
                    a.axhline(0, color="grey", lw=0.6, ls="--")
                    a.set_xlabel("Capital per worker of the US farm type or industry (US$ thousand, log scale)", fontsize=8)
                    if j == 0:
                        a.set_ylabel(ylab[reg], fontsize=8)
            title = f"Exports of {who} firms and {regw[reg]}, one coefficient for each farm type and industry"
            fig.suptitle(title, fontsize=11)
            fig.text(0.01, 0.005, "Each circle is one US farm type (farm stage) or industry (processing stage); its size is its share of the stage's "
                     "exports 2012 to 2018. Labels (left panels; the groups are the same on the right) give the share for groups above 5 percent. If the link between MNEs and exports grew with "
                     "capital intensity, the circles would rise from left to right. Bars are 95 percent confidence intervals.", fontsize=7, wrap=True)
            fig.tight_layout(rect=(0, 0.04, 1, 0.96))
            name = f"capital_{regf[reg]}_{who}_firms_by_farm_type_or_industry"
            save(fig, folder, name, index, title, "Sheets 2.2 and 2.3. One coefficient per US farm type or industry against its capital per worker.")
            plt.close(fig)
            if reg == "lnN" and who == "all":
                main["groups"] = folder / f"{name}.png"
    return main


def fig_e11(ev: pd.DataFrame, figdata: list, index: list, root: Path, names: dict) -> None:
    sh = lambda P, b: names.get((P, b), "")
    of = lambda y: L.OUT_FILE.get(y, slug(y))
    std = ev[(ev["block"] == "std") & (ev["group"] == "all")]
    for (P, smp, y), x in std.groupby(["cellset", "sample", "outcome"]):
        nm = f"{L.CELLS_FILE[P]}_{of(y)}_{L.SAMPLE_FILE.get(smp, smp)}_by_estimator"
        event_fig(x, "est", lambda k: L.EST_SHORT.get(k, k), root / "by_estimator", nm,
                  f"{L.out_name(y)}, {L.CELLS_SHORT[P].lower()}: every estimator", L.out_axis(y),
                  f"Comparison: {L.SAMPLE[smp]}. " + ev_note(P) + (" Borusyak, Jaravel and Spiess measure the years before entry against "
                  "an earlier reference, so their points before entry are not comparable with the others." if "bjs" in set(x["est"]) else ""), index, figdata,
                  f"Sheet {sh(P, 'std')}. Event study of {L.out_name(y).lower()} with every estimator; comparison: {L.SAMPLE_SHORT.get(smp, smp).lower()}.")
    fe = ev[(ev["block"] == "fe") & ev["est"].isin(["twfe", "TF", "T"])]
    for (P, smp, y), x in fe.groupby(["cellset", "sample", "outcome"]):
        x = x.assign(fe=np.where(x["est"] == "TF", "EV2TF", np.where(x["est"] == "T", "EV2T", x["fe"])))
        nm = f"{L.CELLS_FILE[P]}_{of(y)}_{L.SAMPLE_FILE.get(smp, smp)}_by_fixed_effects"
        event_fig(x, "fe", lambda k: L.EV_FE.get(k, k)[:70], root / "by_fixed_effects", nm,
                  f"{L.out_name(y)}, {L.CELLS_SHORT[P].lower()}: different fixed effects (OLS)", L.out_axis(y),
                  f"Comparison: {L.SAMPLE[smp]}. " + ev_note(P).replace("Fixed effects: cell and origin x year and destination x year. ", "").replace(
                      "Fixed effects: cell and origin x year. ", ""), index, figdata,
                  f"Sheet {sh(P, 'fe')}. OLS event study of {L.out_name(y).lower()} under each set of fixed effects and with cell trends.")
    sv = ev[((ev["block"] == "std") & (ev["est"] == "cs")) | ((ev["block"] == "treatps") & (ev["est"] == "cs") & (ev["group"] == "all"))]
    for (P, y), x in sv.groupby(["cellset", "outcome"]):
        nm = f"{L.CELLS_FILE[P]}_{of(y)}_by_comparison_rule"
        event_fig(x, "sample", lambda k: L.SAMPLE_SHORT.get(k, k), root / "by_sample", nm,
                  f"{L.out_name(y)}, {L.CELLS_SHORT[P].lower()}: each comparison rule and type of entry", L.out_axis(y),
                  "Estimator: Callaway and Sant'Anna. " + ev_note(P), index, figdata,
                  f"Sheets {sh(P, 'std')} and {sh(P, 'treatps')}. The same event study under each rule for choosing entered and comparison "
                  "cells, and for large, foreign, domestic and lasting entries.")
    h = ev[ev["block"].isin(["het", "het2"])]
    for (P, smp, est, y), x in h.groupby(["cellset", "sample", "est", "outcome"]):
        for cut in sorted(set(g.split(":")[0] for g in x["group"] if ":" in g)):
            xx = x[x["group"].str.startswith(cut + ":") & ~x["group"].str.endswith("Not classified")]
            nm = f"{L.CELLS_FILE[P]}_{of(y)}_by_{L.CUT_FILE.get(cut, slug(cut))}_{L.SAMPLE_FILE.get(smp, smp)}_{L.EST_FILE.get(est, est)}"
            event_fig(xx, "group", lambda k: (lambda s: s[:1].upper() + s[1:])(L.group_name(k).split(": ", 1)[-1]), root / "by_group", nm,
                      f"{L.out_name(y)}, {L.CELLS_SHORT[P].lower()}: by {L.CUT.get(cut, cut).lower()}", L.out_axis(y),
                      f"Each series is estimated on the cells of one group. Estimator: {L.EST[est]}. Comparison: {L.SAMPLE[smp]}. " + ev_note(P),
                      index, figdata, f"Sheets {sh(P, 'het')} and {sh(P, 'het2')}. Event study by {L.CUT.get(cut, cut).lower()}.")


def fig_main(ev: pd.DataFrame, e9main: dict, figdata: list, index: list, folder: Path) -> None:
    ests = lambda k: {"cs": "Callaway and Sant'Anna", "twfe": "OLS with fixed effects (TWFE)"}.get(k, k)
    outs = ["anyXL", "NL", "NEWL", "EXITL", "lnXL", "SHL"]
    for i, P in enumerate(("A", "B")):
        x = ev[(ev["block"] == "std") & (ev["sample"] == "g_ps") & (ev["group"] == "all") & ev["est"].isin(["cs", "twfe"])]
        panels = [(x[(x["cellset"] == P) & (x["outcome"] == y)], "est", ests, L.out_name(y), L.out_axis(y)) for y in outs]
        grid_fig(panels, 3, folder, f"fig{i + 1}_{L.CELLS_FILE[P]}_cells_after_entry",
                 f"What happens to local firms after the first multinational enters: {L.CELLS_SHORT[P].lower()}",
                 "Comparison: entered and comparison cells meet the same rule (two years with exports before entry). " + ev_note(P), index, figdata,
                 f"Main figure. Six outcomes for local firms in {L.CELLS_SHORT[P].lower()}, two estimators. Numbers in sheet {EV_SECTION[P][0]}.1.")
    # 3: the comparison rule
    a = ev[(ev["cellset"] == "A") & (ev["outcome"] == "anyXL") & (ev["group"] == "all")]
    sel = pd.concat([a[(a["block"] == "std") & (a["est"] == "cs") & a["sample"].isin(["g_v4", "g_ps"])].assign(series=lambda d: d["sample"]),
                     a[(a["block"] == "match") & (a["sample"] == "g_v4")].assign(series="match")])
    lab = {"g_v4": "Rule of the v4 draft (comparison cells: any two years with exports)", "g_ps": "Same rule for both groups",
           "match": "Matched comparison cells (CEM), drawn from the cells of the v4 rule"}
    event_fig(sel, "series", lambda k: lab.get(k, k), folder, "fig3_local_exports_and_the_comparison_rule",
              "Do local firms stop exporting after entry? It depends on how comparison cells are chosen", L.out_axis("anyXL"),
              "Product cells. Callaway and Sant'Anna for the two rules; stacked regression for matched cells. In the v4 draft, entered cells needed "
              "two years with exports before entry but comparison cells only two years at any time, so comparison cells were more likely to keep "
              "exporting. " + ev_note("A"), index, figdata,
              "Main figure. The fall in the probability that local firms export (v4 draft) disappears when entered and comparison cells meet the "
              "same rule or are matched. Sheets 4.1 and 4.8.")
    # 4: size of the entry
    panels = []
    for P in ("A", "B"):
        x = ev[(ev["cellset"] == P) & (ev["outcome"] == "anyXL") & (ev["est"] == "cs") & (ev["group"] == "all")]
        sel = pd.concat([x[(x["block"] == "std") & (x["sample"] == "g_ps")], x[(x["block"] == "treatps") & x["sample"].isin(["g_s10ps", "g_s25ps"])]])
        panels.append((sel, "sample", lambda k: {"g_ps": "Every entry"}.get(k, L.SAMPLE_SHORT.get(k, k)), L.CELLS_SHORT[P], L.out_axis("anyXL")))
    grid_fig(panels, 2, folder, "fig4_large_entries", "Large entries: the probability that local firms export",
             "Every entry, and entries where the multinational has at least 10 or 25 percent of the cell's exports in the entry year. Callaway and "
             "Sant'Anna; entered and comparison cells meet the same rule. Bars are 95 percent confidence intervals.", index, figdata,
             "Main figure. Only large entries are followed by fewer cells with local exports. Sheets 4.3 and 5.3.", size=(12, 5))
    # 5: capital intensity
    x = ev[(ev["cellset"] == "A") & (ev["block"] == "het") & (ev["sample"] == "g_ps") & (ev["est"] == "cs") & ev["group"].str.startswith("high_mean:")
           & (ev["group"] != "high_mean: Not classified")]
    panels = [(x[x["outcome"] == y], "group", lambda k: L.group_name(k).split(": ", 1)[-1].capitalize() + " capital intensity", L.out_name(y), L.out_axis(y))
              for y in ("NL", "NEWL", "EXITL")]
    grid_fig(panels, 3, folder, "fig5_by_capital_intensity", "Local exporters after entry, by capital intensity of the product",
             "Product cells; high and low capital intensity split at the capital per worker of each stage as a whole. Callaway and Sant'Anna; entered "
             "and comparison cells meet the same rule. Bars are 95 percent confidence intervals.", index, figdata,
             "Main figure. New local exporters rise more in capital intensive products. Sheet 4.5.", size=(13, 4.8))
    for k, (key, nm, what) in enumerate((("groups", "fig6_exports_and_MNEs_by_farm_type_or_industry", "Main figure. The link between MNEs and exports "
                                          "does not rise with capital per worker across farm types and industries. Sheets 2.2 and 2.3."),
                                         ("ladder", "fig7_exports_and_MNEs_at_every_cut_off", "Main figure. High and low capital intensity at every "
                                          "cut-off. Sheet 2.1."))):
        if key in e9main:
            for ext in ("png", "pdf"):
                shutil.copy(e9main[key].with_suffix("." + ext), folder / f"{nm}.{ext}")
            index.append({"Folder": str(folder.relative_to(FIG.parent)).replace("\\", "/"), "File": f"{nm}.png and .pdf",
                          "Title": "Exports and MNEs " + ("by farm type and industry" if key == "groups" else "at every cut-off of capital intensity"),
                          "What it shows": what})


# ---------------------------------------------------------------------------------------------------------------------
# descriptives of the v4 draft
# ---------------------------------------------------------------------------------------------------------------------
def tex_table(name: str) -> pd.DataFrame:
    t = (TEX4 / f"{name}.tex").read_text(encoding="utf-8")
    body = re.sub(r"\\(toprule|midrule|bottomrule|hline)", "", t)
    body = re.sub(r"\\begin\{tabular\}\{[^}]*\}|\\end\{tabular\}", "", body)
    rows = []
    for line in body.split("\\\\"):
        s = re.sub(r"\\multicolumn\{\d+\}\{[^}]*\}\{([^}]*)\}", r"\1", line)
        s = re.sub(r"\\textit\{([^}]*)\}|\\textbf\{([^}]*)\}", lambda m: m.group(1) or m.group(2), s)
        s = s.replace("\\%", "%").replace("\\$", "$").replace("$", "").replace("\\times", "x").replace("\\ln", "ln").replace("\\", "").strip()
        if s:
            rows.append([c.strip() for c in s.split("&")])
    w = max(len(r) for r in rows)
    return pd.DataFrame([r + [""] * (w - len(r)) for r in rows])


def tex_fig(name: str) -> pd.DataFrame:
    t = (TEX4 / f"{name}.tex").read_text(encoding="utf-8")
    rows = []
    for k, m in enumerate(re.finditer(r"coordinates\s*\{([^}]*)\}", t)):
        for a, b in re.findall(r"\(([^,()]+),([^,()]+)\)", m.group(1)):
            rows.append({"Series": k + 1, "x": a.strip(), "y": b.strip()})
    return pd.DataFrame(rows)


def d_sheets(op: pd.DataFrame) -> dict:
    out = {}
    for name, f in (("D1", "v4_sample"), ("D2", "v4_mne_summary"), ("D3", "v4_parent_conc"), ("D4", "v4_group_conc")):
        try:
            out[name] = [("Table as printed in the v4 draft", tex_table(f))]
        except FileNotFoundError:
            out[name] = []
    for name, f in (("D3", "v4_fig_parents"), ("D4", "v4_fig_network")):
        try:
            out[name].append(("Numbers behind the figure of the v4 draft", tex_fig(f)))
        except FileNotFoundError:
            pass
    d = op[op["lnkl"].notna()]
    nums = pd.DataFrame([{"Number in Section 4.3 of the v4 draft": "Origin x product x year cells with at least one MNE (%)", "Value": 100 * d["D"].mean()},
                         {"Number in Section 4.3 of the v4 draft": "Share of agricultural exports in those cells (%)",
                          "Value": 100 * d.loc[d["D"] == 1, "X"].sum() / d["X"].sum()},
                         {"Number in Section 4.3 of the v4 draft": "Cells", "Value": len(d)}])
    out["D4"].append(("The two numbers of Section 4.3 (68 percent of cells, 99 percent of exports)", nums))
    return out


# ---------------------------------------------------------------------------------------------------------------------
# text sheets
# ---------------------------------------------------------------------------------------------------------------------
MAIN_RESULTS = [
    ("1", "Multinationals are not more present in capital intensive products.",
     "Farm stage: one more log point of capital per worker lowers the probability that at least one MNE exports the product by 4.1 points "
     "(SE 1.9; 6.1 points without type of production fixed effects). Processing stage: no relation (-1.8 points, SE 3.0). The MNE share of "
     "exports is unrelated to capital intensity in both stages.", "1.1, 1.2"),
    ("2", "The link between MNE presence and exports does not grow with capital intensity.",
     "Across 22 US farm types and 26 industries the coefficient does not rise with capital per worker (unweighted slope 0.12, SE 0.06, farm "
     "stage; -0.03, SE 0.11, processing stage). The larger coefficient of capital intensive farm products comes from one group, grains and "
     "oilseeds (48.6 percent of farm stage exports): 1.16 against 0.5 to 0.74 for the other large groups.", "2.1, 2.2, 2.3; figures 6 and 7"),
    ("3", "The link is weaker in complex and in differentiated products.",
     "Elasticity of exports to the number of MNEs: 0.72 in high PCI and 0.86 in low PCI products (equality rejected, p < 0.001); 0.78 in "
     "differentiated and 0.89 in homogeneous products (p = 0.047). For exports of local firms the gap is larger: 0.26 against 0.47.", "3.1, 3.2"),
    ("4", "After a multinational enters, the probability that local firms export does not change.",
     "With the same rule for choosing entered and comparison cells, all six estimators give between -0.01 and -0.03 (not significant) in product "
     "cells, and matched comparison cells give +0.02. The fall of 15 points in the v4 draft came from comparison cells chosen with a looser rule.",
     "4.1, 4.8; figure 3"),
    ("5", "Local exporters turn over more after entry.",
     "Product cells: local exporters rise by 0.6 to 0.8 (they were already rising before entry, so this is an association), new local exporters "
     "rise by 0.20 to 0.25 (no difference before entry), and exits rise by 0.36 to 0.43. Local firms' share of exports falls by 0.21 to 0.25.",
     "4.1; figure 1"),
    ("6", "Large entries displace local exporters.",
     "When the MNE has 25 percent or more of the cell's exports at entry, the probability that local firms export falls by 14 points in product "
     "cells (no difference before entry, p = 0.14); with the comparison cells of the v4 draft it was 28 points. The first foreign MNE, or an MNE "
     "that stays, is not followed by a fall.", "4.3, 4.4; figure 4"),
    ("7", "Destination cells point the same way, but fail the test of no difference before entry.",
     "Exports of local firms +0.14, local exporters +0.28, new local exporters +0.09, exits +0.16, with differences before entry in almost every "
     "outcome. In cells that export every year, exports of local firms rise by 0.21 with no difference before entry.", "5.1; figure 2"),
    ("8", "Effects on local firms are not larger in labor intensive products.",
     "New local exporters rise by 0.38 in capital intensive and by 0.12 in labor intensive products (product cells). By complexity, local "
     "exporters rise by 0.72 in high PCI and by 0.53 in low PCI products.", "4.5, 4.6; figure 5"),
]

GLOSSARY = [
    ("Data", ""),
    ("MNE", "Multinational firm: an exporter matched to a corporate group in Orbis or Dun & Bradstreet."),
    ("Foreign MNE / domestic MNE", "The parent of the group is in another country / in the exporting country."),
    ("Local firm", "An exporter that is not part of a multinational group."),
    ("Origin, destination, product", "Exporting country (nine Latin American countries), importing country, and six digit HS 2017 product."),
    ("Years", "2012 to 2018."),
    ("Products", ""),
    ("Farm stage / processing stage", "Products that come straight from the farm (grains, fruit, live animals) / products of food processing."),
    ("Type of production", "Field crops; horticultural and plantation crops; livestock and fisheries; other processed food and beverages."),
    ("Capital intensity, capital per worker", "Capital per worker of the US farm type (Census of Agriculture 2017, farm stage) or industry "
     "(NBER-CES, processing stage) the product comes from. All products of the same farm type or industry share its value."),
    ("High / low capital intensity", "Above / below a cut-off of capital per worker, set within each stage."),
    ("Stage ratio", "The cut-off used in the v4 draft: total capital over total workers of the whole stage."),
    ("Cut-off", "The value of capital per worker that separates high from low. Sheet 2.1 shows every cut-off tried."),
    ("Farm type or industry group", "The US farm type or industry whose capital per worker a product takes (22 at the farm stage, 26 at the "
     "processing stage, listed in sheet 2.3)."),
    ("PCI", "Product Complexity Index of the Atlas of Economic Complexity: how much know-how a product needs."),
    ("Rauch class", "Homogeneous (traded on exchanges), reference priced (prices published in trade journals) or differentiated (neither)."),
    ("Degree of processing", "Primary, first processing or further processing."),
    ("Regressions", ""),
    ("At least one MNE (0/1)", "Equals 1 when at least one MNE exports the product from the origin to the destination in the year."),
    ("ln number of MNEs", "Log of the number of MNEs that export in the cell. Its coefficient in a regression of ln exports is the elasticity of "
     "exports to the number of MNEs."),
    ("MNE share of exports", "Exports of MNEs over exports of all firms in the cell."),
    ("Fixed effects", "Dummies that absorb everything common to a group of observations. For example, origin x destination x year fixed effects "
     "absorb anything that affects all products sent from Chile to the United States in 2015. Each table lists them in words, with one Yes / No "
     "row for each."),
    ("SE, clustered", "Standard error that allows errors to be correlated within a cluster (origin and destination pair, product, or cell)."),
    ("Stars", "*** p < 0.01, ** p < 0.05, * p < 0.1."),
    ("Column in the note", "v4 sheets only: where the number is printed in the v4 draft (red = printed)."),
    ("Event studies (sheets 4 to 7)", ""),
    ("Entry", "The first year in which a multinational exports in the cell."),
    ("Entered cells / comparison cells", "Cells where a multinational enters / cells where no multinational enters in 2012 to 2018."),
    ("Product cells", "Origin x product, for example Chilean wine."),
    ("Destination cells", "Origin x destination x product, for example Chilean wine to the United States."),
    ("New destination cells", "Destination cells where local firms did not export before the multinational entered the product."),
    ("Same rule for both groups (main comparison)", "Entered cells need two years with exports before entry. Each comparison cell gets a placebo "
     "entry year, drawn from the actual entry years, and must also have two years with exports before it."),
    ("Rule of the v4 draft", "Entered cells needed two years with exports before entry; comparison cells only two years with exports at any time."),
    ("No difference before entry (p value)", "Joint test that the coefficients before the year of entry are all zero. A low p value means entered "
     "and comparison cells were already moving apart."),
    ("Average effect, years 0 to 4", "Average of the coefficients from the year of entry to four or more years after."),
    ("Placebo", "The same estimation with the entry year moved three years earlier, on years before the real entry. It should give zero."),
    ("OLS with fixed effects (TWFE)", "Event study by OLS with cell and origin x year fixed effects."),
    ("Callaway and Sant'Anna", "Compares each group of cells entered in the same year with cells not yet entered (or never entered); avoids the "
     "bias of OLS when effects change over time."),
    ("Sun and Abraham; Borusyak, Jaravel and Spiess; de Chaisemartin and D'Haultfoeuille", "Other estimators that avoid the same bias."),
    ("Stacked regression", "One small panel per entry year with its comparison cells, stacked and estimated together."),
    ("Matched comparison cells (CEM)", "Comparison cells chosen to have the same origin and similar local exports and local exporters before entry."),
    ("Wooldridge PPML", "Effects on exports in levels, so that zeros are kept."),
    ("Sensitivity to pre-trends (Rambachan and Roth)", "How large a difference in trends would have to be for the effect to stop being significant."),
]

NOTES = [
    ("Sample", "Nine origins (Argentina, Chile, Colombia, Costa Rica, Dominican Republic, El Salvador, Paraguay, Peru, Uruguay), 2012 to 2018, "
     "HS 2017 codes, real destinations only, agricultural products only."),
    ("Logs", "Logs are taken only of positive values. Zeros enter through an indicator (0/1, linear probability model) or through PPML in levels. "
     "No regression uses ln(1 + x) or the inverse hyperbolic sine."),
    ("Capital intensity", "US measures: Census of Agriculture 2017 (machinery and equipment and hired workers by farm type) and NBER-CES (capital "
     "stock and employment by industry). Because every product of a farm type or industry has the same value, a cut-off that falls on that value "
     "moves the whole group; sheet 2.0 says which products fall in the high group under each cut-off."),
    ("Where MNEs are by stage (sheets 1.x)", "Three sets of fixed effects: origin x year and type of production, origin x year and HS chapter, "
     "and origin x year alone. Within the farm stage, high capital intensity almost coincides with field crops, so type of production fixed "
     "effects absorb most of the variation."),
    ("Slopes across groups (sheet 2.2)", "Slope of the group coefficients on ln capital per worker, weighted by exports and unweighted, with "
     "standard errors from the full covariance matrix."),
    ("Other capital measures (sheet 2.5)", "Farm stage: farm assets per worker, machinery per acre and machinery per dollar of sales. "
     "Processing stage: capital stock per worker and capital per dollar of value added."),
    ("Check with country data (sheet 2.6)", "FAOSTAT net capital stock in agriculture over ILO agricultural employment, and USDA ERS "
     "capital and labor quantities, 2012 to 2018 means. With nine countries this is only a plausibility check. Census tables by crop for "
     "Latin American countries were not built."),
    ("PCI (sheet 3.1)", "Atlas of Economic Complexity, HS 1992 four digit headings, mean 2012 to 2018, mapped to HS 2017 with the UNSD "
     "conversion table."),
    ("Rauch (sheets 3.2 and 3.3)", "Rauch (1999) classification of SITC Rev. 2 products, mapped to HS 2017 with the UNSD correlation table. "
     "When an HS product maps to SITC codes of different classes, the most common class is used, and ties go to the more differentiated class."),
    ("Comparison cells (sheets 4 to 6)", "The main comparison draws one placebo entry year per comparison cell from the actual entry years "
     "(random seed 20261124) and applies the same two year condition to both groups."),
    ("Estimators", "Borusyak, Jaravel and Spiess report years before entry relative to the years before 3 years before entry. de Chaisemartin and "
     "D'Haultfoeuille: when a placebo cannot be estimated, the average effect is the mean of the five yearly effects, with a standard error "
     "that ignores their covariances. Wooldridge PPML effects are in log points. Sun and Abraham is not reported for the number of MNEs "
     "(degenerate variance). Some estimators cannot be computed on destination cells; the reason is in the Note row."),
    ("Outcomes", "New and exiting local exporters and new destinations are missing in 2012 (no earlier year). Survival is the share of last "
     "year's local exporters that still export this year."),
]


# ---------------------------------------------------------------------------------------------------------------------
def main() -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    figures = "--no-figures" not in sys.argv
    _readable_labels()
    K.SHOWN = json.load(open(K.OUT / "v4_shown.json")) if (K.OUT / "v4_shown.json").exists() else {}
    regs4, desc4 = K.load()
    ev4 = K.event_results()
    regs5, desc5 = load_regs()
    ev5 = load_events()
    cls_meta = json.load(open(V5 / "classes_v5_cuts.json", encoding="utf-8"))
    wb = Workbook(); first = [True]
    BOLD = Font(bold=True); HEAD = PatternFill("solid", fgColor="DDEBF7")
    contents = []

    def new(name, what="", code=""):
        name = name[:31]
        if first[0]:
            ws = wb.active; ws.title = name; first[0] = False
        else:
            ws = wb.create_sheet(name)
        if what:
            contents.append((name, what, code))
        return ws

    def put_rows(ws, rows, red=()):
        for i, row in enumerate(rows):
            for j, v in enumerate(row):
                c = ws.cell(row=i + 1, column=j + 1, value=v)
                if j:
                    c.alignment = Alignment(horizontal="center", wrap_text=True)
        ws.cell(row=1, column=1).font = Font(bold=True, size=12)
        if len(rows) > 1:
            ws.cell(row=2, column=1).font = Font(italic=True)
        for (a, b, j) in red:
            for i in range(a, b + 1):
                ws.cell(row=i + 1, column=j + 1).font = Font(color=K.RED)
        ws.column_dimensions["A"].width = 70
        for j in range(2, 60):
            ws.column_dimensions[get_column_letter(j)].width = 20
        ws.freeze_panes = "B5"

    def put_df(ws, title, frames, how=""):
        ws.append([title]); ws["A1"].font = Font(bold=True, size=12)
        if how:
            ws.append([how]); ws.cell(row=2, column=1).font = Font(italic=True)
        for name, df in frames:
            ws.append([])
            if name:
                ws.append([name]); ws.cell(row=ws.max_row, column=1).font = BOLD
            if df is None or not len(df):
                ws.append(["(empty)"]); continue
            df = df.copy()
            ws.append([L.text(str(c)) for c in df.columns])
            for j in range(1, len(df.columns) + 1):
                ws.cell(row=ws.max_row, column=j).font = BOLD; ws.cell(row=ws.max_row, column=j).fill = HEAD
                ws.cell(row=ws.max_row, column=j).alignment = Alignment(wrap_text=True, vertical="top")
            for _, r in df.iterrows():
                ws.append([(None if (isinstance(v, float) and not np.isfinite(v)) else (round(v, 4) if isinstance(v, float) else
                            (int(v) if isinstance(v, np.integer) else (str(v) if not isinstance(v, (int, float, str)) and v is not None else v))))
                           for v in r.tolist()])
        ws.column_dimensions["A"].width = 34
        for j in range(2, 40):
            ws.column_dimensions[get_column_letter(j)].width = 18

    def text_sheet(ws, title, rows, widths=(30, 120), header=None):
        ws.append([title]); ws["A1"].font = Font(bold=True, size=12); ws.append([])
        if header:
            ws.append(list(header))
            for j in range(1, len(header) + 1):
                ws.cell(row=ws.max_row, column=j).font = BOLD; ws.cell(row=ws.max_row, column=j).fill = HEAD
        for r in rows:
            ws.append(list(r))
            if len(r) > 1 and r[1] == "" and len(r) == 2:
                ws.cell(row=ws.max_row, column=1).font = Font(bold=True, color="1F4E79")
        for j, w in enumerate(widths):
            ws.column_dimensions[get_column_letter(j + 1)].width = w
        for row in ws.iter_rows(min_row=3):
            for c in row:
                c.alignment = Alignment(wrap_text=True, vertical="top")

    # ---- front sheets (Read me is filled at the end, once the contents are known)
    ws_read = new("Read me")
    ws_main = new("Main results")
    if PRIMARY is not None:
        ptitle, phead, prows = PRIMARY
        ws_main.append([ptitle]); ws_main["A1"].font = Font(bold=True, size=12); ws_main.append([])
        ws_main.append(list(phead))
        for j in range(1, len(phead) + 1):
            ws_main.cell(row=ws_main.max_row, column=j).font = BOLD; ws_main.cell(row=ws_main.max_row, column=j).fill = HEAD
        for r in prows:
            ws_main.append(list(r))
        ws_main.append([]); ws_main.append([MAIN_TITLE]); ws_main.cell(row=ws_main.max_row, column=1).font = Font(bold=True, size=12); ws_main.append([])
        ws_main.append(["", "Finding", "Numbers", "Sheets and figures"])
        for j in range(1, 5):
            ws_main.cell(row=ws_main.max_row, column=j).font = BOLD; ws_main.cell(row=ws_main.max_row, column=j).fill = HEAD
        for r in MAIN_RESULTS:
            ws_main.append(list(r))
        for j, w in enumerate((8, 55, 110, 24, 14, 14, 14, 50, 14)):
            ws_main.column_dimensions[get_column_letter(j + 1)].width = w
        for row in ws_main.iter_rows(min_row=3):
            for c in row:
                c.alignment = Alignment(wrap_text=True, vertical="top")
    else:
        text_sheet(ws_main, MAIN_TITLE, MAIN_RESULTS, widths=(5, 55, 110, 24), header=("", "Finding", "Numbers", "Sheets and figures"))
    text_sheet(new("Glossary"), "Glossary: every term and abbreviation used in the sheets and figures", GLOSSARY, widths=(42, 130))

    # ---- 1 where MNEs are
    longs = []

    def reg_sheet(s, regs, v5=True):
        rows, red, lg = K.reg_block(s, regs)
        if len(rows) <= 3:
            return
        rows, shift = friendly_rows(rows, s, v5)
        red = [(a + shift, b + shift, j) for a, b, j in red]
        name = NAME.get(s, f"v4 {s}")
        put_rows(new(name, TITLE.get(s, K.TITLES.get(s, "")) if v5 else f"v4 draft: {K.TITLES.get(s, '')}", CODE.get(s, s)), rows, red)
        for r in lg:
            r["Table"] = name
            r["Panel"] = L.panel(r["Panel"])
        longs.extend(lg)

    put_df(new(NAME["E12 map"], "Summary of sheets 1.1 to 1.4: one row per regression", "E12.1"),
           "Where MNEs are, summary: one row per regression", [("", e12_map(regs5)), ("Raw pattern by stage and group", desc5.get("E12_desc"))],
           "How to read: a negative coefficient on capital intensity means that MNEs are less present in more capital intensive products.")
    for s in ("E12a", "E12b", "E12c", "E12d"):
        reg_sheet(s, regs5)
    # ---- 2 capital intensity
    put_df(new(NAME["E9 map"], "Summary of sheets 2.1 to 2.5: one row per regression, with the products in the high group", "E9"),
           "Capital intensity, summary: one row per regression",
           [("High and low capital intensity under every cut-off, with what the high group contains and where MNEs are in it; slopes across "
             "farm types and industries", e9_map(regs5, desc5, cls_meta)),
            ("What each cut-off puts in the high group", desc5.get("E9_composition")), ("Cut-offs common to both stages", desc5.get("E9c_composition"))],
           HOW["cut"])
    for s in ("E9a", "E9b"):
        reg_sheet(s, regs5)
    grp = desc5.get("E9b_groups")
    if grp is not None:
        grp = grp.rename(columns={"src_id": "Group", "label": "Farm types or industries in the group", "codes": "Census or NAICS codes",
                                  "kl": "Capital per worker (US$ thousand)", "lnkl": "ln capital per worker", "products": "Products", "stage": "Stage"})
    put_df(new(NAME["E9b groups"], "The 48 US farm types and industries behind sheet 2.2", "E9b"),
           "US farm types and industries behind sheet 2.2", [("Groups", grp), ("Cells and clusters behind each group coefficient", desc5.get("E9b_support"))])
    for s in ("E9c", "E9d"):
        reg_sheet(s, regs5)
    put_df(new(NAME["E9e"], "Is the US measure consistent with Latin American data?", "E9e, E9d"),
           "Is the US measure of capital intensity consistent with Latin American data?",
           [("Capital per agricultural worker by country, 2012 to 2018 means", desc5.get("E9e_country")),
            ("Rank correlation between the origin's export weighted capital intensity and the country measures (nine countries)", desc5.get("E9e_rank")),
            ("Census tables by crop for Latin American countries", desc5.get("E9e_product_level")),
            ("Other US measures: rank correlation with capital per worker across groups", desc5.get("E9d_rank")),
            ("Other US measures by group", desc5.get("E9d_groups"))])
    # ---- 3 other traits
    put_df(new(NAME["E10 map"], "Summary of sheets 3.1 to 3.5: one row per regression", "E10"),
           "Other product traits, summary: one row per regression",
           [("", e10_map(regs5)), ("PCI groups: what they contain", desc5.get("E10a_composition")),
            ("Capital intensity x PCI groups: what they contain", desc5.get("E10d_composition")),
            ("Degree of processing: what each group contains", desc5.get("E10c_composition")),
            ("Rauch classes: what each class contains", desc5.get("E10b_composition"))], HOW["trait"])
    for s in ("E10a", "E10b"):
        reg_sheet(s, regs5)
    put_df(new(NAME["E10b classes"], "Rauch classes of every product, and the products whose class changed from the v4 draft", "E10b"),
           "Rauch classes of the products", [("Products by class (conservative and liberal versions; v4 draft against now)", desc5.get("E10b_classes")),
                                             ("Products whose class differs between versions", desc5.get("E10b_changes"))])
    for s in ("E10c", "E10d"):
        reg_sheet(s, regs5)
    # ---- 4 to 7 event studies
    names = {}
    for P in ("A", "B", "E"):
        k = 0
        for blk, short, desc, code in EV_BLOCK:
            if len(ev5[(ev5["cellset"] == P) & (ev5["block"] == blk)]):
                k += 1
                names[(P, blk)] = ev_sheet_name(P, k, short)
    e11 = e11_map(ev5, names)
    put_df(new(NAME["E11 map"], "Summary of every event study (sheets 4.1 to 6.x): one row per outcome, estimator and comparison", "E11"),
           "What happens after the first multinational enters, summary: one row per event study (average effect from the year of entry to 4 years after)",
           [("", e11)], "How to read: the average effect compares entered and comparison cells after entry. The p value of no difference "
           "before entry should be high (above 0.10) for the comparison to be credible.")
    for P in ("A", "B", "E"):
        for blk, short, desc, code in EV_BLOCK:
            if (P, blk) in names:
                put_rows(new(names[(P, blk)], f"{L.CELLS_SHORT[P]}: {desc}", code),
                         event_sheet(ev5, P, blk, f"After the first multinational enters, {L.CELLS[P]}: {desc} (estimation plan: {code})"))
    put_df(new(NAME["E11 honest"], "How large a difference in trends would overturn each effect (Rambachan and Roth)", "E11b viii"),
           "Sensitivity to differences in trends before entry (Rambachan and Roth), average effect of years 0 to 4, OLS",
           [("", honest())], "How to read: the larger the smallest violation at which the interval includes zero, the more robust the effect.")
    cnt = pd.read_parquet(V5 / "ev5_counts.parquet")
    cnt["Cells"] = cnt["Cells"].map(lambda c: L.CELLS_SHORT.get({"Bentry": "E"}.get(c, c), c))
    cnt["Treatment definition"] = cnt["Treatment definition"].map(SMP5).fillna(cnt["Treatment definition"])
    cnt = cnt.rename(columns={"Treatment definition": "Comparison rule or type of entry", "Treated cells": "Entered cells", "Control cells": "Comparison cells"})
    frames = [("Entered and comparison cells under each rule", cnt)]
    for f, lab in ((OUT5 / "ev5_match_info.parquet", "Matching of comparison cells by entry year (CEM)"),
                   (V5 / "ev5_spillover_info.parquet", "Information spillovers: groups and destinations")):
        if f.exists():
            frames.append((lab, pd.read_parquet(f).reset_index()))
    put_df(new(NAME["E11 counts"], "Number of entered and comparison cells under each rule", "E11d"), "Number of cells in each event study", frames)
    # ---- figures
    fd9, fd11, index = [], [], []
    if not figures and FIGCACHE.exists():
        fd9, fd11, index = pickle.load(open(FIGCACHE, "rb"))
    if FIG_EXTRA is not None:
        fd9, fd11, index = fd9 + FIG_EXTRA[0], fd11 + FIG_EXTRA[1], index + FIG_EXTRA[2]
    if figures:
        for d in OLD_FIG + [FIG]:
            if d.exists():
                shutil.rmtree(d)
        e9main = fig_e9(regs5, desc5, cls_meta, fd9, index, FIG / "2_capital_intensity")
        fig_main(ev5, e9main, fd11, index, FIG / "1_main_figures")
        fig_e11(ev5, fd11, index, FIG / "3_after_entry", names)
        pickle.dump((fd9, fd11, index), open(FIGCACHE, "wb"))
    put_df(new(NAME["fig index"], "List of every figure, with its folder and what it shows", ""),
           "Figure index (folder docs/notes/figures_v5)", [("", pd.DataFrame(index))],
           "1_main_figures has the seven figures behind the main results; 2_capital_intensity and 3_after_entry have every variant.")
    put_df(new(NAME["E9 figdata"], "Numbers plotted in the capital intensity figures", ""), "Numbers behind the capital intensity figures", [("", pd.DataFrame(fd9))])
    put_df(new(NAME["E11 figdata"], "Numbers plotted in the event study figures", ""), "Numbers behind the event study figures", [("", pd.DataFrame(fd11))])
    # ---- descriptives of the v4 draft
    op = pd.read_parquet(W.WP_INT / "v4" / "opy.parquet").merge(pd.read_parquet(W.WP_INT / "v4" / "classes.parquet")[["hs", "lnkl"]], on="hs")
    dt = {"D1": "Agricultural exports by exporting country, 2018 (Table 1 of the v4 draft)", "D2": "Multinationals in agricultural exports, 2018 (Table 3)",
          "D3": "Parent countries of the multinationals, 2018 (Table 4 and Figure 1)", "D4": "Multinational groups, 2018 (Table 5 and Figure 2), and the numbers of Section 4.3"}
    for name, frames in d_sheets(op).items():
        put_df(new(NAME[name], dt[name], "E12.2"), dt[name], frames)
    if HOOK_SHEETS is not None:
        longs += HOOK_SHEETS(new, put_df, put_rows, text_sheet, wb)
    # ---- v4 sheets
    order = ["E1a", "E1b", "E1c", "E2a", "E2b", "E2c", "E2d", "E2e", "E2f", "E2g", "E3a", "E3b", "E3c", "E3d",
             "E4a", "E4b", "E4c", "E4d", "E4e", "E4f", "E4g", "E5a", "E5b", "E5c", "E5d", "E5e", "E7a", "E7b", "E7c"]
    for s in order:
        if s in ("E1a", "E1b", "E1c", "E3a", "E3b", "E3c", "E3d"):
            if s in desc4:
                put_df(new(f"v4 {s}", f"v4 draft: {K.TITLES[s]}", s), f"{K.TITLES[s]} (v4 draft, sheet {s})", [("", desc4[s])])
            continue
        reg_sheet(s, regs4, v5=False)
    for s, cs, tags in (("E6a", "A", ["main", "pre3"]), ("E6b", "B", ["main", "pre3"])):
        rows, red, lg = K.event_block(s, ev4, cs, tags)
        put_rows(new(f"v4 {s}", f"v4 draft: {K.TITLES.get(s, '')}", s), rows, red); longs += lg
    # ---- all estimates, one per row
    for _, r in ev5[ev5["term"].isin(TERMS + ["pre_test"])].iterrows() if len(ev5) else []:
        longs.append({"Table": names.get((r["cellset"], r["block"]), r["block"]), "Panel": f"{L.SAMPLE_SHORT.get(r['sample'], r['sample'])}; {L.group_name(r['group'])}",
                      "Column": f"{L.out_name(r['outcome'])}, {L.EST_SHORT.get(r['est'], r['est'])}", "Dependent variable": L.out_name(r["outcome"]),
                      "Regressor": TLAB.get(r["term"], "Test: no difference before entry"), "Coefficient": r["b"], "Standard error": r["se"],
                      "p value": r["p"], "Stars": stars(r["p"]), "Observations": r["N"], "Fixed effects": L.EV_FE.get(r["fe"], r["fe"]),
                      "Estimator": L.EST.get(r["est"], r["est"]), "Sample": L.SAMPLE.get(r["sample"], r["sample"]), "Clustered by": L.CLUSTER[r["cellset"]],
                      "Column in the note": "Not shown"})
    ws = new(NAME["Long format"], "Every estimate of every sheet in one table, for filtering", "")
    cols = ["Table", "Panel", "Column", "Column in the note", "Dependent variable", "Regressor", "Coefficient", "Standard error", "p value", "Stars",
            "Observations", "R-squared", "Within R-squared", "Singletons dropped", "Fixed effects", "Clustered by", "Sample", "Estimator"] + LONG_EXTRA_COLS
    ws.append(cols)
    for j in range(1, len(cols) + 1):
        ws.cell(row=1, column=j).font = BOLD; ws.cell(row=1, column=j).fill = HEAD
    for r in longs:
        ws.append([None if (isinstance(r.get(c), float) and not np.isfinite(r.get(c))) else (L.text(r.get(c)) if c == "Fixed effects" else r.get(c)) for c in cols])
    ws.freeze_panes = "A2"
    for j, w in enumerate((26, 50, 40, 22, 30, 50, 12, 12, 10, 6, 12, 10, 10, 10, 50, 22, 40, 22)):
        ws.column_dimensions[get_column_letter(j + 1)].width = w
    # ---- classifications and notes
    cls = pd.read_parquet(V5 / "classes_v5.parquet")
    coldesc = pd.DataFrame([
        ("hs, description, hs2, hs4", "HS 2017 product code, description, chapter and heading"), ("type, stage", "Type of production and stage"),
        ("kl, lnkl, kl_source", "Capital per worker (US$ thousand) of the farm type or industry, its log, and the source"),
        ("src_id, src_label", "Farm type or industry group (sheet 2.3)"), ("high_mean, high_median", "High capital intensity in the v4 draft (stage ratio, median)"),
        ("high_gapNN, high_umed, high_wmed, high_up75, high_wp75, high_agg", "High capital intensity at each cut-off of sheet 2.1 (thr_* is the cut-off)"),
        ("tercile_stage, quartile_stage", "Capital intensity tercile and quartile within the stage, weighted by exports"),
        ("pool_*", "High capital intensity with one cut-off for both stages (sheet 2.4)"), ("processing_degree", "Degree of processing"),
        ("alt_*, high_alt_*", "Other US capital measures and the high group under each (sheet 2.5)"),
        ("PCI_p, high_PCI, PCI_tercile", "Product complexity and its groups"), ("rauch_con, rauch_lib", "Rauch class used in the v4 draft"),
        ("rauch_full_con, rauch_full_lib, sitc2_codes", "Rauch class used now (conservative, liberal) and the SITC codes behind it"),
        ("v_1218, v_2018", "Exports 2012 to 2018 and 2018 (US$ thousand)")], columns=["Columns", "Meaning"])
    put_df(new(NAME["Classifications"], "Every agricultural product with all its classifications", ""),
           "Product classifications: one row per HS 2017 agricultural product", [("What each column means", coldesc), ("Products", cls)])
    text_sheet(new(NAME["Notes"], "Data sources and details of the estimations", ""), "Technical notes", NOTES, widths=(36, 140))
    # ---- read me
    ws = ws_read
    ws.append([READ_TITLE]); ws["A1"].font = Font(bold=True, size=14)
    intro = [
        ("What this workbook answers", "1. In which agricultural products are multinationals present? 2. Is the link between multinationals and "
         "exports different in capital intensive products, or by other product traits? 3. What happens to local exporters after the first "
         "multinational enters a product?"),
        ("Where to start", "Main results (eight findings with their numbers), then the summary sheet of each section (1.0, 2.0, 3.0, 4.0)."),
        ("Words and codes", "Glossary explains every term. Technical notes give the data sources and estimation details."),
        ("How to read a regression table", "Each column is one regression. Standard errors are in parentheses below each coefficient, with stars "
         "for significance. The fixed effects of each column are named in the header row and listed below with Yes / No."),
        ("How to read an event study table", "Each column compares cells where a multinational entered with comparison cells, year by year, "
         "relative to the year before entry. The rows before entry should be close to zero; the average effect summarizes the years after."),
        ("Figures", "Folder docs/notes/figures_v5: 1_main_figures (the seven figures behind the main results), 2_capital_intensity and "
         "3_after_entry (every variant). Sheet 8.0 lists every figure and sheets 8.1 and 8.2 have the plotted numbers."),
        ("v4 sheets", "Sheets starting with v4 are the tables of the v4 draft, unchanged. Red numbers are printed in the draft."),
    ]
    intro += READ_EXTRA
    for a, b in intro:
        ws.append([a, b])
    ws.append([]); ws.append(["Contents"]); ws.cell(row=ws.max_row, column=1).font = Font(bold=True, size=12)
    ws.append(["Sheet", "What it shows", "Code in the estimation plan"])
    for j in range(1, 4):
        ws.cell(row=ws.max_row, column=j).font = BOLD; ws.cell(row=ws.max_row, column=j).fill = HEAD
    for c in contents:
        ws.append(list(c))
    ws.column_dimensions["A"].width = 34; ws.column_dimensions["B"].width = 120; ws.column_dimensions["C"].width = 26
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
        if row[0].value in dict(intro):
            row[0].font = BOLD
    wb.save(XLSX)
    print(f"workbook -> {XLSX}: {len(wb.sheetnames)} sheets, {len(regs5)} v5 regressions, {len(ev5):,} v5 event rows, {len(longs):,} long rows; "
          f"figures {len(index)}")


if __name__ == "__main__":
    main()
