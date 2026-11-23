"""
wp_agro_note_v3.py  --  every exhibit of Note_v3.tex (agriculture note, version 3)
==================================================================================

    WP_YEARS=2012-2018 WP_SCOPES=agro python wp_agro_note_v3.py            (everything)
    WP_YEARS=2012-2018 WP_SCOPES=agro python wp_agro_note_v3.py workbook   (workbook from the saved regressions)
    WP_YEARS=2012-2018 WP_SCOPES=agro python wp_agro_note_v3.py flatten    (Note_v3.tex from the source)

History: 2026-11-02 first version. 2026-11-03 full fixed-effect progressions, outreg2-style workbook. 2026-11-03
(evening) rewrite:
  * product groups come from wp_agro_classification.py (type of production, census capital intensity, and the
    third classification, type of production x capital intensity), one table for the note and the product workbook
  * every regression is run on ONE grid of eleven fixed-effect specifications (GRID), the same columns in every
    table of the workbook; a specification that does not apply (firm fixed effects on origin x destination x product
    x year cells) or is not identified (destination x product x year within one origin) is marked as such
  * every stylized fact has an aggregate part and a by-country part (descriptive tables, figures and regressions)
  * the 2018 figures are written as pgfplots code and every table and figure is inlined into Note_v3.tex, so the
    note compiles alone (source: docs/notes/Note_v3_source.tex, flattened by flatten())
  * the data are those of wp_common.load_fdpy after the correction of Uruguay's 2016-2018 codes
2026-11-03 (night): every product code is HS 2017 (WP_HS17=1, wp_common.to_hs2017); the descriptive exhibits,
including the product groups of Fact 5, are on 2018; the workbook shows, for each table, the grid columns that apply
to it (cells: 1 to 6, cells within one origin: 1 to 5, firms: 1 to 11), so column (k) has the same fixed effects in
every table and no column is empty.
"""
from __future__ import annotations

import gc
import json
import os
import pickle
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("WP_HS17", "1")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_common as W  # noqa: E402
import wp1e_hq_affiliates as E  # noqa: E402
import wp_agro_croptype as C  # noqa: E402

SCOPE = "agro"
OUTD = W.WP_OUT / SCOPE / "v3"
TEXD = W.ROOT / "docs" / "overleaf_projects" / "WP_paperagro" / "tables" / "v3"
XLSX = W.ROOT / "docs" / "notes" / "WP_paperagro_v3_master_estimates.xlsx"
SRC = W.ROOT / "docs" / "notes" / "Note_v3_source.tex"
NOTE = W.ROOT / "docs" / "overleaf_projects" / "WP_paperagro" / "Note_v3.tex"
PICKLE = OUTD / "v3_regressions.pkl"
FACTS_JSON = OUTD / "v3_facts.json"
AUX = OUTD / "build" / "Note_v3.aux"
CLS = W.WP_INT / "hs6_agro_classification.parquet"
for d in (OUTD, TEXD, XLSX.parent, AUX.parent):
    d.mkdir(parents=True, exist_ok=True)
COUNTRY = {"ARG": "Argentina", "CHL": "Chile", "COL": "Colombia", "CRI": "Costa Rica", "DOM": "Dominican Republic",
           "PER": "Peru", "PRY": "Paraguay", "SLV": "El Salvador", "URY": "Uruguay"}
MASTER: list[dict] = []
REGS: list[dict] = []
FACTS: dict = {}

# ---------------------------------------------------------------------
# fixed effects: one map, one grid
# ---------------------------------------------------------------------
FE_ALL = {"O": ("Origin", "country_orig"), "D": ("Destination", "country_dest"), "P": ("Product", "hs07_6d"),
          "Y": ("Year", "year"), "OY": (r"Origin $\times$ year", "ot"), "DY": (r"Destination $\times$ year", "dt"),
          "ODP": (r"Origin $\times$ destination $\times$ product", "odp"),
          "ODY": (r"Origin $\times$ destination $\times$ year", "ody"),
          "OPY": (r"Origin $\times$ product $\times$ year", "opy"),
          "DPY": (r"Destination $\times$ product $\times$ year", "dpy"),
          "F": ("Firm", "fid"), "FP": (r"Firm $\times$ product", "fp"), "FY": (r"Firm $\times$ year", "fy"),
          "FPY": (r"Firm $\times$ product $\times$ year", "fpy")}
GRID = [["O", "D", "P", "Y"], ["OY", "DY", "P"], ["ODP", "Y"], ["ODP", "ODY"], ["ODP", "ODY", "OPY"],
        ["ODP", "ODY", "OPY", "DPY"], ["OY", "DY", "P", "F"], ["OY", "DY", "FP"], ["FY", "DY", "P"], ["FPY", "DY"],
        ["FPY", "DPY"]]
CELL_G = range(0, 6)              # cells aggregate firms: no firm fixed effects
CELL_CTRY_G = range(0, 5)         # within one origin, destination x product x year is the cell itself
FIRM_G = range(0, 11)
PRES_DOC = [0, 1, 2, 3, 5]        # the columns of the presence tables of the note
DIST_DOC = [0, 1, 6, 7, 8, 9, 10]  # the columns of the distance tables (Table 11 adds the no-level column first)
CTRY_DOC = 3                      # by country: origin x destination x product and origin x destination x year
CTRY_DIST_DOC = (1, 6)            # by country, distance: without and with firm fixed effects
CLUSTER_LAB = {"od": "pair of origin and destination countries", "country_dest": "destination country"}
NA_CELL = "Not applicable: one observation per origin, destination, product and year adds up the firms"
NA_CTRY = "Not identified: within one origin, destination x product x year is one observation"
SIG = r"*** $p<0.01$, ** $p<0.05$, * $p<0.1$."


def stars(p):
    return W.stars(p)


def fit(data, dep, regs, g, table, xpanel, sample, cluster="od", tests=(), tab=None, shown="", extra=None):
    """Estimate with the fixed effects of GRID[g]; record the regression in REGS (workbook) and every coefficient in
    MASTER; return {var: (b, se, p)}, N, R2 and test p-values."""
    fe_keys = GRID[g]
    if REPLAY is not None:
        r = REPLAY[(tab, xpanel, g)]
        r.update(shown=shown, extra=extra or {}); REGS.append(r)
        return {"cells": r["cells"], "n": r["n"], "r2": r["r2"], "tests": r["tests"]}
    fe = " + ".join(FE_ALL[k][1] for k in fe_keys)
    dd = data.dropna(subset=[dep] + regs)
    t0 = time.time()
    reg = dict(tab=tab, xpanel=xpanel, xcol=g, shown=shown, status="", dep=dep, regs=list(regs), fe_keys=list(fe_keys),
               cluster=cluster, sample=sample, extra=extra or {}, cells={}, tests={}, n=0, r2=np.nan, r2w=np.nan)
    try:
        m = W.feols(f"{dep} ~ {' + '.join(regs)} | {fe}", data=dd, vcov={"CRV1": cluster})
    except Exception as e:  # noqa: BLE001
        print(f"   {table} {xpanel[:30]} ({g + 1}): FAILED {str(e)[:90]}")
        reg["status"] = "Not estimated: " + str(e)[:60]
        REGS.append(reg)
        return {"cells": {}, "n": 0, "r2": np.nan, "tests": {}}
    b, se, p = m.coef(), m.se(), m.pvalue()
    r2 = float(getattr(m, "_r2", np.nan)); r2w = float(getattr(m, "_r2_within", np.nan))
    cells = {v: (float(b[v]), float(se[v]), float(p[v])) for v in regs if v in b.index}
    tres = {}
    if tests:
        from scipy.stats import norm
        V = np.asarray(m._vcov); ix = list(b.index)
        for name, (v1, v2) in tests:
            if v1 in ix and v2 in ix:
                i, j = ix.index(v1), ix.index(v2)
                sd = float(np.sqrt(V[i, i] + V[j, j] - 2 * V[i, j]))
                tres[name] = float(2 * (1 - norm.cdf(abs((b[v1] - b[v2]) / sd)))) if sd > 0 else np.nan
    reg.update(cells=cells, tests=tres, n=int(m._N), r2=r2, r2w=r2w)
    REGS.append(reg)
    for v, (bb, ss, pp) in cells.items():
        MASTER.append(dict(tab=tab, panel=xpanel, column=g + 1, dependent=dep, regressor=v, coef=bb, se=ss, pvalue=pp))
    print(f"   {table[:24]:24s} {xpanel[:34]:34s} ({g + 1:>2}): N={int(m._N):>9,} "
          + " ".join(f"{v}:{c[0]:+.3f}{stars(c[2])}" for v, c in cells.items())
          + "".join(f" [{k} p={v:.3f}]" for k, v in tres.items()) + f" ({time.time() - t0:.0f}s)")
    out = {"cells": cells, "n": int(m._N), "r2": r2, "tests": tres}
    del m; gc.collect()
    return out


def mark(tab, xpanel, g, dep, regs, status, cluster="od", sample=""):
    """A grid column that does not apply to this regression (kept so that every table has the same columns)."""
    REGS.append(dict(tab=tab, xpanel=xpanel, xcol=g, shown="", status=status, dep=dep, regs=list(regs),
                     fe_keys=list(GRID[g]), cluster=cluster, sample=sample, extra={}, cells={}, tests={}, n=0,
                     r2=np.nan, r2w=np.nan))


def save_tex(name: str, txt: str) -> None:
    (OUTD / f"{name}.tex").write_text(txt, encoding="utf-8")
    (TEXD / f"{name}.tex").write_text(txt, encoding="utf-8")


def cellfmt(r, v):
    if v in r["cells"]:
        b, s, p = r["cells"][v]
        return f"{b:.3f}{stars(p)}", f"({s:.3f})"
    return "", ""


def write_table(name, panels, fe_sets, labels, extra_rows=None, test_rows=None, header=None):
    """Regression table of the note: panels [(label, [result per column])], one column per specification."""
    k = len(fe_sets)
    L = [rf"\begin{{tabular}}{{l*{{{k}}}{{c}}}}", r"\toprule"]
    if header:
        L.append(header)
    L += [" & " + " & ".join(f"({i + 1})" for i in range(k)) + r" \\", r"\midrule"]
    for pi, (plab, res) in enumerate(panels):
        if pi:
            L.append(r"\midrule")
        if plab:
            L.append(rf"\multicolumn{{{k + 1}}}{{l}}{{\textit{{{plab}}}}} \\")
        for v in dict.fromkeys(v for r in res for v in r["cells"]):
            fb = [cellfmt(r, v) for r in res]
            L += [f"{labels.get(v, v)} & " + " & ".join(x[0] for x in fb) + r" \\", " & " + " & ".join(x[1] for x in fb) + r" \\"]
        for tname, tlab in (test_rows or []):
            vals = [f"{r['tests'][tname]:.3f}" if tname in r["tests"] else "" for r in res]
            if any(vals):
                L.append(f"{tlab} & " + " & ".join(vals) + r" \\")
        nlab = "Observations" + (f" ({plab.split('.')[0]})" if plab and len(panels) > 1 else "")
        L.append(f"{nlab} & " + " & ".join(f"{r['n']:,}" if r["n"] else "" for r in res) + r" \\")
        L.append(r"$R^2$ & " + " & ".join(f"{r['r2']:.3f}" if r["n"] else "" for r in res) + r" \\")
    L.append(r"\midrule")
    for kk in [kk for kk in FE_ALL if any(kk in s for s in fe_sets)]:
        L.append(f"{FE_ALL[kk][0]} FE & " + " & ".join(r"$\checkmark$" if kk in s else "" for s in fe_sets) + r" \\")
    for lab, vals in (extra_rows or []):
        L.append(f"{lab} & " + " & ".join(vals) + r" \\")
    L += [r"\bottomrule", r"\end{tabular}"]
    save_tex(name, "\n".join(L) + "\n")


# within one exporting country, the origin dimension of a fixed effect is constant
WITHIN = {"OY": "Year", "ODP": r"Destination $\times$ product", "ODY": r"Destination $\times$ year",
          "OPY": r"Product $\times$ year"}


def write_country_table(name, panels, origins, fe_keys, labels, test_rows=None):
    """By-country regression table: the same layout as write_table, one column per exporting country. The fixed
    effects are named as they work within one origin (WITHIN)."""
    k = len(origins)
    L = [rf"\begin{{tabular}}{{l*{{{k}}}{{c}}}}", r"\toprule", " & " + " & ".join(origins) + r" \\", r"\midrule"]
    for pi, (plab, res) in enumerate(panels):
        if pi:
            L.append(r"\midrule")
        L.append(rf"\multicolumn{{{k + 1}}}{{l}}{{\textit{{{plab}}}}} \\")
        for v in dict.fromkeys(v for r in res for v in r["cells"]):
            fb = [cellfmt(r, v) for r in res]
            L += [f"{labels.get(v, v)} & " + " & ".join(x[0] for x in fb) + r" \\", " & " + " & ".join(x[1] for x in fb) + r" \\"]
        for tname, tlab in (test_rows or {}).get(pi, []):
            vals = [f"{r['tests'][tname]:.3f}" if tname in r["tests"] else "" for r in res]
            if any(vals):
                L.append(f"{tlab} & " + " & ".join(vals) + r" \\")
        nlab = "Observations" + (f" ({plab.split('.')[0]})" if len(panels) > 1 else "")
        L.append(f"{nlab} & " + " & ".join(f"{r['n']:,}" if r["n"] else "" for r in res) + r" \\")
        L.append(r"$R^2$ & " + " & ".join(f"{r['r2']:.3f}" if r["n"] else "" for r in res) + r" \\")
    L.append(r"\midrule")
    fk = fe_keys if isinstance(fe_keys[0], list) else [fe_keys]          # one set, or one set per panel
    for kk in [kk for kk in FE_ALL if any(kk in s for s in fk)]:
        only = [chr(65 + i) for i, s in enumerate(fk) if kk in s]
        lab = f"{WITHIN.get(kk, FE_ALL[kk][0])} FE" + ("" if len(only) == len(fk) else f" (Panel {', '.join(only)})")
        L.append(f"{lab} & " + " & ".join(r"$\checkmark$" for _ in origins) + r" \\")
    L += [r"\bottomrule", r"\end{tabular}"]
    save_tex(name, "\n".join(L) + "\n")


def write_plain(name, header, rows, colspec=None, midrule_before=()):
    k = len(header)
    L = [rf"\begin{{tabular}}{{{colspec or ('l' + 'r' * (k - 1))}}}", r"\toprule", " & ".join(header) + r" \\", r"\midrule"]
    for i, r in enumerate(rows):
        if i in midrule_before:
            L.append(r"\midrule")
        L.append(" & ".join(r) + r" \\")
    L += [r"\bottomrule", r"\end{tabular}"]
    save_tex(name, "\n".join(L) + "\n")


# ---------------------------------------------------------------------
# product groups (wp_agro_classification.py)
# ---------------------------------------------------------------------
CT_KEYS = {"horti": "Horticultural and plantation crops", "field": "Field crops", "live": "Livestock and fisheries",
           "proc": "Other processed food and beverages"}
CT_LAB = {"horti": "horticultural and plantation crops", "field": "field crops", "live": "livestock and fisheries",
          "proc": "other processed food"}
KI_KEYS = {"farm_hi": ("Farm", "High"), "farm_lo": ("Farm", "Low"), "proc_hi": ("Processing", "High"), "proc_lo": ("Processing", "Low")}
KI_LAB = {"farm_hi": "farm stage, high capital intensity", "farm_lo": "farm stage, low capital intensity",
          "proc_hi": "processing stage, high capital intensity", "proc_lo": "processing stage, low capital intensity",
          "ki_nc": "not classified"}
TX_KEYS = {}
TX_LAB = {}
for _k, _t in CT_KEYS.items():
    for _h, _hl in (("h", "high"), ("l", "low")):
        TX_KEYS[f"{_k}_{_h}"] = f"{_t}, {_hl} capital intensity"
        TX_LAB[f"{_k}_{_h}"] = f"{CT_LAB[_k]}, {_hl}"
TX_KEYS["tx_nc"] = "Not classified"; TX_LAB["tx_nc"] = "not classified"
CT_SHORT = {"horti": "Horticultural and plantation", "field": "Field crops", "live": "Livestock and fisheries",
            "proc": "Other processed food"}
TX_SHORT = {k: (f"{CT_KEYS[k.rsplit('_', 1)[0]]}, {'high' if k.endswith('_h') else 'low'}" if k != "tx_nc" else "Not classified")
            for k in TX_KEYS}
REPLAY: dict | None = None      # (tab, panel, column) -> saved regression: rebuild the tables without estimating


NAICS_SOURCE = os.environ.get("WP_NAICS", "unsd").strip().lower()   # HS to NAICS link: "unsd" tables or "census" concordance


def classification() -> pd.DataFrame:
    t = pd.read_parquet(CLS)
    p = {"unsd": "u", "census": "c"}[NAICS_SOURCE]
    t["stage"], t["capital_intensity"], t["kl"], t["type_x_capital"] = t[f"{p}_stage"], t[f"{p}_ci"], t[f"{p}_kl"], t[f"{p}_tx"]
    t["crop"] = t["fao_type"]
    t["kgroup"] = "ki_nc"
    for k, (st, hi) in KI_KEYS.items():
        t.loc[(t["stage"] == st) & (t["capital_intensity"] == hi), "kgroup"] = k
    inv = {v: k for k, v in TX_KEYS.items()}
    t["tx"] = t["type_x_capital"].map(inv)
    assert t["tx"].notna().all(), t.loc[t["tx"].isna(), "type_x_capital"].unique()
    return t[["hs07_6d", "crop", "stage", "capital_intensity", "kl", "kgroup", "tx"]]


# ---------------------------------------------------------------------
# cells and firm panel
# ---------------------------------------------------------------------
def cells() -> pd.DataFrame:
    d = W.scope_filter(W.mne_flags(W.build_cube()), SCOPE)
    g = E.odpy_cells(d[d["value"] > 0])
    g["opy"] = g["country_orig"] + "_" + g["hs07_6d"] + "_" + g["year"].astype(str)
    g["dpy"] = g["country_dest"] + "_" + g["hs07_6d"] + "_" + g["year"].astype(str)
    g["n_local"] = (g["n_firms"] - g["n_mne"]).clip(lower=0)
    g["ln_nlocal"] = E.ln(g["n_local"])
    g["ln_xlocal_pf"] = E.ln(g["nonmne_value"] / g["n_local"].replace(0, np.nan))
    pg = classification()
    g = g.merge(pg, on="hs07_6d", how="left")
    assert g["crop"].notna().all(), "products missing from the classification: run wp_agro_classification.py"
    g["mne_product"] = (g.groupby(["country_orig", "hs07_6d"])["n_mne"].transform("max") > 0).astype(int)
    for k in CT_KEYS:
        ind = (g["crop"] == CT_KEYS[k]).astype(float); g[f"lnN_{k}"] = g["ln_n_mne"] * ind; g[f"any_{k}"] = g["any_n_mne"] * ind
    for k in list(KI_KEYS) + ["ki_nc"]:
        ind = (g["kgroup"] == k).astype(float); g[f"lnN_{k}"] = g["ln_n_mne"] * ind; g[f"any_{k}"] = g["any_n_mne"] * ind
    for k in TX_KEYS:
        ind = (g["tx"] == k).astype(float); g[f"lnN_{k}"] = g["ln_n_mne"] * ind; g[f"any_{k}"] = g["any_n_mne"] * ind
    FACTS["cells"] = len(g)
    FACTS["mne_products_cells"] = float(g["mne_product"].mean())
    FACTS["mne_products_value"] = float(g.loc[g["mne_product"] == 1, "total_value"].sum() / g["total_value"].sum())
    print(f"cells {len(g):,}; MNE products {FACTS['mne_products_cells']:.1%} of cells, {FACTS['mne_products_value']:.1%} of value")
    return g


def firm_panel() -> pd.DataFrame:
    f = E.load_firm_panel()
    f = f[W.sector4(f["hs2"]) == W.SECTOR_OF_SCOPE[SCOPE]].copy()
    f["fid"] = f["country_orig"] + "|" + f["Tax_ID"].astype(str)
    f["fp"] = f["fid"] + "_" + f["hs07_6d"]
    f["fy"] = f["fid"] + "_" + f["year"].astype(str)
    f["fpy"] = f["fy"] + "_" + f["hs07_6d"]
    f["odp"] = f["od"] + "_" + f["hs07_6d"]
    f["ody"] = f["od"] + "_" + f["year"].astype(str)
    f["opy"] = f["country_orig"] + "_" + f["hs07_6d"] + "_" + f["year"].astype(str)
    f["dpy"] = f["country_dest"] + "_" + f["hs07_6d"] + "_" + f["year"].astype(str)
    f["any_mne_odpy"] = f.groupby(["country_orig", "country_dest", "hs07_6d", "year"])["m"].transform("max").astype(float)
    f["any_Xd"] = f["any_mne_odpy"] * f["ln_dist"]
    f["mne"] = f["m"].astype(float)
    f["pres"] = f["g_anypres_Xd"].ne(0).astype(float); f["notpres"] = f["g_anynotpres_Xd"].ne(0).astype(float)
    return f


LAB = {"ln_n_mne": r"$\ln$(number of MNEs)", "any_n_mne": "At least one MNE"}
for _k in CT_KEYS:
    LAB[f"lnN_{_k}"] = rf"$\ln$(number of MNEs) $\times$ {CT_LAB[_k]}"; LAB[f"any_{_k}"] = rf"At least one MNE $\times$ {CT_LAB[_k]}"
for _k in list(KI_KEYS) + ["ki_nc"]:
    LAB[f"lnN_{_k}"] = rf"$\ln$(number of MNEs) $\times$ {KI_LAB[_k]}"; LAB[f"any_{_k}"] = rf"At least one MNE $\times$ {KI_LAB[_k]}"
for _k in TX_KEYS:
    LAB[f"lnN_{_k}"] = rf"$\ln$(number of MNEs) $\times$ {TX_LAB[_k]}"; LAB[f"any_{_k}"] = rf"At least one MNE $\times$ {TX_LAB[_k]}"
DLAB = {"ln_dist": r"$\ln$ distance", "mne": "MNE", "g_mne_Xd": r"$\ln$ distance $\times$ MNE",
        "pres": "MNE, present at destination", "notpres": "MNE, not present at destination",
        "g_anypres_Xd": r"$\ln$ distance $\times$ MNE, present", "g_anynotpres_Xd": r"$\ln$ distance $\times$ MNE, not present",
        "any_mne_odpy": "At least one MNE in the market", "any_Xd": r"$\ln$ distance $\times$ at least one MNE in the market"}
DEPLAB = {"ln_total": r"$\ln$ exports, all firms", "ln_nonmne": r"$\ln$ exports, local firms",
          "ln_nlocal": r"$\ln$ number of local exporters", "ln_xlocal_pf": r"$\ln$ exports per local exporter",
          "ln_exports": r"$\ln$ exports of the firm"}
PA, PB = "Panel A. Intensive margin: observations with at least one MNE", "Panel B. Extensive margin: all observations"


def origins_by_value(g: pd.DataFrame) -> list:
    return list(g.groupby("country_orig")["total_value"].sum().sort_values(ascending=False).index)


# ---------------------------------------------------------------------
# Fact 4: presence
# ---------------------------------------------------------------------
def presence(g: pd.DataFrame) -> None:
    for dep, name, tab in (("ln_total", "v3_presence_all", "tab:t1"), ("ln_nonmne", "v3_presence_local", "tab:t1local")):
        res = {}
        for reg, P, pl in (("ln_n_mne", PA, "Panel A"), ("any_n_mne", PB, "Panel B")):
            for gi in FIRM_G:
                if gi not in CELL_G:
                    mark(tab, P, gi, dep, [reg], NA_CELL); continue
                c = PRES_DOC.index(gi) + 1 if gi in PRES_DOC else None
                res[(reg, gi)] = fit(g, dep, [reg], gi, "Presence", P, "all observations", tab=tab, shown=f"{pl}, column ({c})" if c else "")
        write_table(name, [(PA, [res[("ln_n_mne", gi)] for gi in PRES_DOC]), (PB, [res[("any_n_mne", gi)] for gi in PRES_DOC])],
                    [GRID[gi] for gi in PRES_DOC], LAB)
    # products where MNEs operate: four dependent variables; the note shows grid columns 4 and 6 for each
    sub = g[g["mne_product"] == 1]
    deps = ("ln_total", "ln_nonmne", "ln_nlocal", "ln_xlocal_pf")
    SHOWN = (3, 5)
    res = {}
    for d, dep in enumerate(deps):
        for reg, P0, pl in (("ln_n_mne", PA, "Panel A"), ("any_n_mne", PB, "Panel B")):
            P = f"{P0.split('.')[0]}. {DEPLAB[dep]}, {P0.split(': ')[0].split('. ')[1].lower()}"
            for gi in FIRM_G:
                if gi not in CELL_G:
                    mark("tab:mneprod", P, gi, dep, [reg], NA_CELL); continue
                c = 2 * d + SHOWN.index(gi) + 1 if gi in SHOWN else None
                res[(reg, dep, gi)] = fit(sub, dep, [reg], gi, "MNE products", P, "products where MNEs operate", tab="tab:mneprod",
                                          shown=f"{pl}, column ({c})" if c else "")
    cols = [(dep, gi) for dep in deps for gi in SHOWN]
    head = (r" & \multicolumn{2}{c}{$\ln$ exports,} & \multicolumn{2}{c}{$\ln$ exports,} & \multicolumn{2}{c}{$\ln$ number of} & \multicolumn{2}{c}{$\ln$ exports per} \\"
            "\n" r" & \multicolumn{2}{c}{all firms} & \multicolumn{2}{c}{local firms} & \multicolumn{2}{c}{local exporters} & \multicolumn{2}{c}{local exporter} \\"
            "\n" r"\cmidrule(lr){2-3}\cmidrule(lr){4-5}\cmidrule(lr){6-7}\cmidrule(lr){8-9}")
    write_table("v3_presence_mneprod", [(PA, [res[("ln_n_mne", dep, gi)] for dep, gi in cols]), (PB, [res[("any_n_mne", dep, gi)] for dep, gi in cols])],
                [GRID[gi] for _, gi in cols], LAB, header=head)


def presence_by_country(g: pd.DataFrame) -> None:
    order = origins_by_value(g)
    FACTS["origin_order"] = order
    for dep, name, tab, who in (("ln_total", "v3_country_presence_all", "tab:cpres_all", "all firms"),
                                ("ln_nonmne", "v3_country_presence_local", "tab:cpres_local", "local firms")):
        doc = {"ln_n_mne": [], "any_n_mne": []}
        for o in order:
            s = g[g["country_orig"] == o]
            for reg, P0, pl in (("ln_n_mne", "Intensive margin", "Panel A"), ("any_n_mne", "Extensive margin", "Panel B")):
                P = f"{COUNTRY[o]}. {P0}"
                for gi in FIRM_G:
                    if gi not in CELL_G:
                        mark(tab, P, gi, dep, [reg], NA_CELL, "country_dest"); continue
                    if gi not in CELL_CTRY_G:
                        mark(tab, P, gi, dep, [reg], NA_CTRY, "country_dest"); continue
                    r = fit(s, dep, [reg], gi, f"Presence {o}", P, f"origin {o}", cluster="country_dest", tab=tab,
                            shown=f"{pl}, column {COUNTRY[o]}" if gi == CTRY_DOC else "")
                    if gi == CTRY_DOC:
                        doc[reg].append(r)
        write_country_table(name, [(PA, doc["ln_n_mne"]), (PB, doc["any_n_mne"])], order, GRID[CTRY_DOC], LAB)


# ---------------------------------------------------------------------
# Fact 5: type of production, capital intensity, and both
# ---------------------------------------------------------------------
HSPECS = [("crop", "tab:crop", "tab:crop_ext", list(CT_KEYS), [("field = horticultural", ("field", "horti"))],
           [("field = horticultural", r"$p$ value: field crops = horticultural and plantation crops")]),
          ("capital", "tab:capital", "tab:capital_ext", list(KI_KEYS) + ["ki_nc"],
           [("farm high = farm low", ("farm_hi", "farm_lo")), ("processing high = processing low", ("proc_hi", "proc_lo"))],
           [("farm high = farm low", r"$p$ value: farm stage, high = low"), ("processing high = processing low", r"$p$ value: processing stage, high = low")]),
          ("txk", "tab:txk", "tab:txk_ext", list(TX_KEYS),
           [(f"{CT_LAB[k]} high = low", (f"{k}_h", f"{k}_l")) for k in CT_KEYS],
           [(f"{CT_LAB[k]} high = low", rf"$p$ value: {CT_LAB[k]}, high = low") for k in CT_KEYS])]


def heterogeneity(g: pd.DataFrame) -> None:
    for tag, tab_i, tab_e, keys, tests, trows in HSPECS:
        for pre, suffix, tab in (("lnN_", "int", tab_i), ("any_", "ext", tab_e)):
            regs = [pre + k for k in keys if (g["crop" if tag == "crop" else ("kgroup" if tag == "capital" else "tx")] ==
                                               (CT_KEYS.get(k) if tag == "crop" else k)).any()]
            tt = [(n, (pre + a, pre + b)) for n, (a, b) in tests]
            panels = []
            for dep, plab in (("ln_total", r"Panel A. Dependent variable: $\ln$ exports, all firms"),
                              ("ln_nonmne", r"Panel B. Dependent variable: $\ln$ exports, local firms")):
                res = {}
                for gi in FIRM_G:
                    if gi not in CELL_G:
                        mark(tab, plab, gi, dep, regs, NA_CELL); continue
                    c = PRES_DOC.index(gi) + 1 if gi in PRES_DOC else None
                    res[gi] = fit(g, dep, regs, gi, f"{tag} {suffix}", plab, "all observations", tests=tt, tab=tab,
                                  shown=f"{plab[:7]}, column ({c})" if c else "")
                panels.append((plab, [res[gi] for gi in PRES_DOC]))
            write_table(f"v3_{tag}_{suffix}", panels, [GRID[gi] for gi in PRES_DOC], LAB, test_rows=trows)


def heterogeneity_by_country(g: pd.DataFrame) -> None:
    order = FACTS["origin_order"]
    tab = "tab:chet"
    doc = {tag: [] for tag, *_ in HSPECS}
    trows = {}
    for pi, (tag, _, _, keys, tests, tr) in enumerate(HSPECS):
        trows[pi] = tr
        col = {"crop": "crop", "capital": "kgroup", "txk": "tx"}[tag]
        for o in order:
            s = g[g["country_orig"] == o]
            present = set(s.loc[s["n_mne"] > 0, col])
            regs = [f"lnN_{k}" for k in keys if (CT_KEYS.get(k) if tag == "crop" else k) in present]
            tt = [(n, (f"lnN_{a}", f"lnN_{b}")) for n, (a, b) in tests]
            P = f"{COUNTRY[o]}. {['Type of production', 'Capital intensity', 'Type of production x capital intensity'][pi]}"
            for gi in FIRM_G:
                if gi not in CELL_G:
                    mark(tab, P, gi, "ln_total", regs, NA_CELL, "country_dest"); continue
                if gi not in CELL_CTRY_G:
                    mark(tab, P, gi, "ln_total", regs, NA_CTRY, "country_dest"); continue
                r = fit(s, "ln_total", regs, gi, f"Hetero {o}", P, f"origin {o}", cluster="country_dest", tests=tt, tab=tab,
                        shown=f"Panel {'ABC'[pi]}, column {COUNTRY[o]}" if gi == CTRY_DOC else "")
                if gi == CTRY_DOC:
                    doc[tag].append(r)
    write_country_table("v3_country_hetero", [("Panel A. Type of production", doc["crop"]), ("Panel B. Capital intensity", doc["capital"]),
                                              (r"Panel C. Type of production $\times$ capital intensity", doc["txk"])],
                        order, GRID[CTRY_DOC], LAB, test_rows=trows)


# ---------------------------------------------------------------------
# Fact 6: distance
# ---------------------------------------------------------------------
ABSORB_POOLED = {"ODP", "ODY"}
ABSORB_COUNTRY = {"D", "DY", "ODP", "ODY", "DPY"}
FIRM_FE = {"F", "FP", "FY", "FPY"}


def distance(f: pd.DataFrame) -> None:
    tab = "tab:dist"
    A, A0 = "Panel A. All multinationals", "Panel A, without the MNE level term"
    B, B0 = "Panel B. Multinationals by presence at the destination", "Panel B, without the MNE level terms"
    res = {}
    for P, inter, lvl, use_lvl in ((A, ["g_mne_Xd"], ["mne"], True), (A0, ["g_mne_Xd"], ["mne"], False),
                                   (B, ["g_anypres_Xd", "g_anynotpres_Xd"], ["pres", "notpres"], True),
                                   (B0, ["g_anypres_Xd", "g_anynotpres_Xd"], ["pres", "notpres"], False)):
        for gi in FIRM_G:
            fe = set(GRID[gi]); firm = bool(FIRM_FE & fe)
            regs = ([] if ABSORB_POOLED & fe else ["ln_dist"]) + inter + (lvl if use_lvl and not firm else [])
            lev = "Not included" if not use_lvl else ("Absorbed by the firm FE" if firm else "Included")
            if P in (A, B):
                c = DIST_DOC.index(gi) + 2 if gi in DIST_DOC else None
            else:
                c = 1 if gi == 0 else None
            pl = P[:7]
            res[(P, gi)] = fit(f, "ln_exports", regs, gi, "Distance", P, "all firm flows", tab=tab,
                               shown=f"{pl}, column ({c})" if c else "", extra={"MNE level term": lev})
    lvl_row = [("MNE level term included", [""] + [("absorbed" if FIRM_FE & set(GRID[gi]) else "Yes") for gi in DIST_DOC])]
    write_table("v3_distance_all", [(A, [res[(A0, 0)]] + [res[(A, gi)] for gi in DIST_DOC]),
                                    (B, [res[(B0, 0)]] + [res[(B, gi)] for gi in DIST_DOC])],
                [GRID[0]] + [GRID[gi] for gi in DIST_DOC], DLAB, extra_rows=lvl_row)
    loc = f[f["m"] == 0]
    resl = {}
    for gi in FIRM_G:
        fe = set(GRID[gi])
        regs = ([] if ABSORB_POOLED & fe else ["ln_dist"]) + ["any_mne_odpy", "any_Xd"]
        c = DIST_DOC.index(gi) + 1 if gi in DIST_DOC else None
        resl[gi] = fit(loc, "ln_exports", regs, gi, "Distance local", "Local firms only", "local firm flows", tab="tab:dist_local",
                       shown=f"Column ({c})" if c else "")
    write_table("v3_distance_local", [("", [resl[gi] for gi in DIST_DOC])], [GRID[gi] for gi in DIST_DOC], DLAB)


def distance_by_country(f: pd.DataFrame) -> None:
    order = FACTS["origin_order"]
    tab = "tab:cdist"
    doc = {1: [], 6: []}
    for o in order:
        s = f[f["country_orig"] == o]
        P = f"{COUNTRY[o]}. All multinationals"
        for gi in FIRM_G:
            fe = set(GRID[gi]); firm = bool(FIRM_FE & fe)
            regs = ["g_mne_Xd"] + ([] if firm else ["mne"])
            r = fit(s, "ln_exports", regs, gi, f"Distance {o}", P, f"origin {o}", cluster="country_dest", tab=tab,
                    shown=f"Panel {'A' if gi == 1 else 'B'}, column {COUNTRY[o]}" if gi in CTRY_DIST_DOC else "",
                    extra={"MNE level term": "Absorbed by the firm FE" if firm else "Included"})
            if gi in doc:
                doc[gi].append(r)
    write_country_table("v3_country_distance", [(r"Panel A. Origin $\times$ year, destination $\times$ year and product FE", doc[1]),
                                                (r"Panel B. Panel A plus firm FE", doc[6])], order, [GRID[1], GRID[6]], DLAB)


# ---------------------------------------------------------------------
# descriptive exhibits (2018) and pgfplots figures
# ---------------------------------------------------------------------
def tex(s: str) -> str:
    return s.replace("&", r"\&").replace("%", r"\%")


def pct(x: float, d: int = 1) -> str:
    return f"{100 * x:.{d}f}"


def fig_hbar_stacked(name, labels, series, colors, legend, totals=True, xmax=None, width=r"0.92\linewidth", height=None,
                     xlabel="Share of export value", legend_cols=2, gap_after=None, percent=False):
    """Horizontal stacked bars as pgfplots code. labels top to bottom; series [(values in 0..1)]. percent=True shows
    the values in percent with one decimal (one series, no legend)."""
    n = len(labels)
    ys = list(range(1, n + 1))
    if gap_after is not None:
        ys = [y + (0.6 if i > gap_after else 0) for i, y in enumerate(ys)]
    tot = np.sum(np.array(series), axis=0)
    xmax = xmax or min(1.0, float(np.ceil((tot.max() + 0.08) * 10) / 10))
    step = 0.05 if xmax <= 0.35 else 0.1
    ticks = [round(i * step, 2) for i in range(int(round(xmax / step)) + 1)]
    tlab = [f"{100 * x:.0f}" if percent else (f"{x:.2f}".rstrip("0").rstrip(".") if x else "0") for x in ticks]
    height = height or f"{0.55 * n + 1.6:.1f}cm"
    L = [r"\begin{tikzpicture}", r"\begin{axis}[", r"  xbar stacked, bar width=8pt, y dir=reverse,",
         f"  width={width}, height={height}, xmin=0, xmax={xmax:.2f}, ymin={ys[0] - 0.7}, ymax={ys[-1] + 0.7},",
         "  ytick={" + ",".join(f"{y:g}" for y in ys) + "}, yticklabels={" + ",".join("{" + tex(l) + "}" for l in labels) + "},",
         "  xtick={" + ",".join(f"{x:g}" for x in ticks) + "}, xticklabels={" + ",".join(tlab) + "},",
         r"  tick label style={font=\footnotesize}, xlabel={" + xlabel + r"}, xlabel style={font=\footnotesize},",
         r"  axis x line*=bottom, axis y line*=left, ytick style={draw=none},",
         r"  area legend, legend image post style={draw=none}, legend cell align=left, legend style={at={(0.5,0)}, anchor=north, yshift=-1.25cm, draw=none, font=\footnotesize, legend columns=" + str(legend_cols)
         + r", /tikz/every even column/.append style={column sep=6pt}}]"]
    for vals, col in zip(series, colors):
        L.append(r"\addplot[fill=" + col + r", draw=white, line width=0.3pt] coordinates {" + " ".join(f"({v:.4f},{y:g})" for v, y in zip(vals, ys)) + "};")
    if not percent:
        L.append(r"\legend{" + ",".join("{" + tex(x) + "}" for x in legend) + "}")
    if totals:
        for t_, y in zip(tot, ys):
            lab = f"{100 * t_:.1f}" if percent else f"{t_:.2f}"
            L.append(r"\node[anchor=west, font=\scriptsize] at (axis cs:" + f"{t_:.4f},{y:g}) {{{lab}}};")
    if gap_after is not None:
        yy = (ys[gap_after] + ys[gap_after + 1]) / 2
        L.append(r"\draw[gray, dashed, line width=0.3pt] (axis cs:" + f"0,{yy:g}) -- (axis cs:{xmax:.2f},{yy:g});")
    L += [r"\end{axis}", r"\end{tikzpicture}"]
    save_tex(name, "\n".join(L) + "\n")


PAL12 = ["{rgb,255:red,31;green,56;blue,100}", "{rgb,255:red,46;green,84;blue,150}", "{rgb,255:red,68;green,114;blue,196}",
         "{rgb,255:red,99;green,140;blue,210}", "{rgb,255:red,132;green,165;blue,222}", "{rgb,255:red,166;green,191;blue,233}",
         "{rgb,255:red,84;green,130;blue,53}", "{rgb,255:red,112;green,173;blue,71}", "{rgb,255:red,169;green,208;blue,142}",
         "{rgb,255:red,191;green,144;blue,0}", "{rgb,255:red,159;green,176;blue,200}", "{rgb,255:red,191;green,191;blue,191}"]
C_EXT, C_DOM = "{rgb,255:red,31;green,56;blue,100}", "{rgb,255:red,191;green,191;blue,191}"


def load_2018() -> tuple[pd.DataFrame, pd.Series]:
    import wp_agro_paper as A
    fd = W.load_fdpy()
    fd = fd[~fd["country_orig"].isin(W.excluded_origins()) & (fd["value_fob"] > 0) & (pd.to_numeric(fd["year"]) == 2018)].copy()
    fd["hs2"] = W.hs2_of(fd["hs07_6d"])
    tot_all = fd.groupby("country_orig")["value_fob"].sum()
    a = W.scope_filter(fd, SCOPE).copy()
    a["otype"] = W.owner_type(a).replace({"ext_unknown": "ext"})
    a["fid"] = a["country_orig"] + "|" + a["Tax_ID"]
    a["matched"] = W.matched_flag(a).astype(bool)
    a["dest_real"] = A.real_dest(a["country_dest"], a["country_orig"])
    a["region"] = A.dest_region(a["country_dest"])
    a["parent"] = a["iso3_parent"].fillna("").astype(str)
    return a, tot_all


def descriptives(g: pd.DataFrame) -> None:
    import wp_agro_paper as A
    import wp2_agro_sectors as S
    a, tot_all = load_2018()
    order = list(a.groupby("country_orig")["value_fob"].sum().sort_values(ascending=False).index)
    V = a["value_fob"].sum()
    ext, dom, loc = a["otype"] == "ext", a["otype"] == "dom", a["otype"] == "local"
    F = FACTS.setdefault("desc", {})

    # Data: the sample by country
    rows = []
    for o in order:
        s = a[a["country_orig"] == o]
        rows.append([COUNTRY[o], f"{s['fid'].nunique():,}", f"{s['hs07_6d'].nunique():,}", f"{s['dest_real'].nunique():,}",
                     f"{s['value_fob'].sum() / 1e9:,.1f}", f"{100 * s['value_fob'].sum() / tot_all[o]:.1f}"])
        F[f"agshare_{o}"] = float(100 * s["value_fob"].sum() / tot_all[o]); F[f"exports_{o}"] = float(s["value_fob"].sum() / 1e9)
    rows.append(["LAC9", f"{a['fid'].nunique():,}", f"{a['hs07_6d'].nunique():,}", f"{a['dest_real'].nunique():,}",
                 f"{V / 1e9:,.1f}", f"{100 * V / tot_all.sum():.1f}"])
    F.update(firms=int(a["fid"].nunique()), products=int(a["hs07_6d"].nunique()), dests=int(a["dest_real"].nunique()),
             exports=float(V / 1e9), agshare=float(100 * V / tot_all.sum()))
    write_plain("v3_sample", ["Country", "Exporters", "Products", "Destinations", r"Exports (US\$ billion)", r"Agriculture in total exports (\%)"],
                rows, midrule_before=(len(rows) - 1,))

    # Fact 1, aggregate: summary, destinations, SITC divisions
    fy = a.groupby("fid").agg(v=("value_fob", "sum"), nd=("dest_real", "nunique"), npd=("hs07_6d", "nunique"), ot=("otype", "first"))
    rows = [[r"Exports (US\$ billion)", f"{V / 1e9:,.1f}"] + [f"{a.loc[m_, 'value_fob'].sum() / 1e9:,.1f}" for m_ in (ext, dom, loc)],
            [r"Share of exports (\%)", "100.0"] + [f"{100 * a.loc[m_, 'value_fob'].sum() / V:.1f}" for m_ in (ext, dom, loc)],
            ["Exporters", f"{len(fy):,}"] + [f"{(fy['ot'] == t).sum():,}" for t in ("ext", "dom", "local")],
            [r"Exports per exporter (US\$ million)", f"{fy['v'].mean() / 1e6:.1f}"] + [f"{fy.loc[fy['ot'] == t, 'v'].mean() / 1e6:.1f}" for t in ("ext", "dom", "local")],
            ["Destinations per exporter", f"{fy['nd'].mean():.1f}"] + [f"{fy.loc[fy['ot'] == t, 'nd'].mean():.1f}" for t in ("ext", "dom", "local")],
            ["Products per exporter", f"{fy['npd'].mean():.1f}"] + [f"{fy.loc[fy['ot'] == t, 'npd'].mean():.1f}" for t in ("ext", "dom", "local")]]
    write_plain("v3_mne_summary", ["", "All exporters", "Foreign MNEs", "Domestic MNEs", "Local firms"], rows)
    F.update(sh_ext=float(100 * a.loc[ext, "value_fob"].sum() / V), sh_dom=float(100 * a.loc[dom, "value_fob"].sum() / V),
             n_ext=int((fy["ot"] == "ext").sum()), n_dom=int((fy["ot"] == "dom").sum()),
             groups=int(a.loc[a["matched"], "parent_key"].replace("", pd.NA).nunique()),
             parent_countries=int(a.loc[a["matched"] & (a["parent"] != ""), "parent"].nunique()),
             x_ext=float(fy.loc[fy["ot"] == "ext", "v"].mean() / 1e6), x_dom=float(fy.loc[fy["ot"] == "dom", "v"].mean() / 1e6),
             x_loc=float(fy.loc[fy["ot"] == "local", "v"].mean() / 1e6), d_ext=float(fy.loc[fy["ot"] == "ext", "nd"].mean()),
             d_dom=float(fy.loc[fy["ot"] == "dom", "nd"].mean()), d_loc=float(fy.loc[fy["ot"] == "local", "nd"].mean()))
    gr = a.pivot_table(index="region", columns="otype", values="value_fob", aggfunc="sum").fillna(0)
    tr = gr.sum(axis=1)
    rows = []
    for rg in [r for r in A.DEST_ORDER if r in gr.index]:
        rows.append([rg, pct(tr[rg] / tr.sum()), pct(gr.loc[rg, "ext"] / tr[rg]), pct(gr.loc[rg, "dom"] / tr[rg]), pct(gr.loc[rg, "local"] / tr[rg]),
                     f"{tr[rg] / 1e9:,.1f}"])
        F[f"region_ext_{rg}"] = float(100 * gr.loc[rg, "ext"] / tr[rg])
    rows.append(["All destinations", "100.0", pct(gr["ext"].sum() / tr.sum()), pct(gr["dom"].sum() / tr.sum()), pct(gr["local"].sum() / tr.sum()), f"{tr.sum() / 1e9:,.1f}"])
    write_plain("v3_dest", ["Destination", r"Share of exports (\%)", r"Foreign MNEs (\%)", r"Domestic MNEs (\%)", r"Local firms (\%)", r"Exports (US\$ billion)"],
                rows, midrule_before=(len(rows) - 1,))
    # SITC Rev.3 division of each HS 2017 code (UNSD HS-SITC-BEC correlations; the most common one when UNSD links a code
    # to several SITC items)
    u = pd.read_excel(W.F_BEC, dtype=str, usecols=["HS17", "SITC3"]).dropna()
    u["sitc2"] = u["SITC3"].str[:2]
    cls = u.groupby("HS17")["sitc2"].agg(lambda s: s.mode().iat[0]).rename_axis("hs07_6d").reset_index()
    a2 = a.merge(cls, on="hs07_6d", how="left")
    F["sitc_missing_share"] = float(a2.loc[a2["sitc2"].isna(), "value_fob"].sum() / V)
    a2["sitc_lab"] = a2["sitc2"].map(lambda c: f"{c} {S.SITC_DIV.get(c, '')}" if isinstance(c, str) else "Other")
    tot = a2.groupby("sitc_lab")["value_fob"].sum()
    small = tot[tot / tot.sum() < S.MIN_SHARE_TABLE].index
    a2.loc[a2["sitc_lab"].isin(small), "sitc_lab"] = "Other"
    s = a2.pivot_table(index="sitc_lab", columns="otype", values="value_fob", aggfunc="sum").fillna(0)
    s = s.div(s.sum(axis=1), axis=0)
    s["mne"] = s["ext"] + s["dom"]
    s = pd.concat([s.drop("Other").sort_values("mne", ascending=False), s.loc[["Other"]]])
    F["sitc"] = {k: {"ext": float(100 * r["ext"]), "dom": float(100 * r["dom"])} for k, r in s.iterrows()}
    fig_hbar_stacked("v3_fig_sitc", list(s.index), [s["ext"].values, s["dom"].values], [C_EXT, C_DOM], ["Foreign MNEs", "Domestic MNEs"])

    # Fact 1, by country: shares (figure) and exporters (table)
    cs = a.pivot_table(index="country_orig", columns="otype", values="value_fob", aggfunc="sum").fillna(0)
    cs.loc["LAC9"] = cs.sum()
    cs = cs.div(cs.sum(axis=1), axis=0)
    cs["mne"] = cs["ext"] + cs["dom"]
    sub = cs.drop("LAC9").sort_values("mne", ascending=False)
    sub = pd.concat([sub, cs.loc[["LAC9"]]])
    F["country_share"] = {o: {"ext": float(100 * r["ext"]), "dom": float(100 * r["dom"])} for o, r in sub.iterrows()}
    fig_hbar_stacked("v3_fig_country_share", [COUNTRY.get(o, o) for o in sub.index], [sub["ext"].values, sub["dom"].values], [C_EXT, C_DOM],
                     ["Foreign MNEs", "Domestic MNEs"], gap_after=len(sub) - 2)
    rows = []
    for o in order:
        s_ = a[a["country_orig"] == o]; v = s_["value_fob"].sum()
        nf = s_["fid"].nunique(); na_ = s_.loc[s_["matched"], "fid"].nunique()
        x_aff = s_[s_["matched"]].groupby("fid")["value_fob"].sum().mean() / 1e6
        x_loc = s_[~s_["matched"]].groupby("fid")["value_fob"].sum().mean() / 1e6
        dsh = s_.groupby("dest_real")["value_fob"].sum().sort_values(ascending=False)
        rows.append([COUNTRY[o], f"{v / 1e9:,.1f}", f"{nf:,}", f"{na_:,}", f"{100 * na_ / nf:.1f}", f"{x_aff:.1f}", f"{x_loc:.1f}",
                     f"{dsh.index[0]} ({100 * dsh.iloc[0] / v:.0f})"])
        F[f"aff_share_{o}"] = float(100 * na_ / nf); F[f"x_aff_{o}"] = float(x_aff); F[f"x_loc_{o}"] = float(x_loc)
        F[f"main_dest_{o}"] = [dsh.index[0], float(100 * dsh.iloc[0] / v)]
    write_plain("v3_country_exporters", ["Country", r"Exports (US\$ billion)", "Exporters", "MNE affiliates", r"Affiliates (\% of exporters)",
                                         r"Exports per affiliate (US\$ million)", r"Exports per local firm (US\$ million)", r"Main destination (\%)"],
                rows, colspec="lrrrrrrl")

    # Fact 2, aggregate: parent countries (figure) and parents by destination (table)
    e = a[ext & (a["parent"] != "")]
    F["known_parent_2018"] = float(100 * e["value_fob"].sum() / a.loc[ext, "value_fob"].sum())
    ps = (e.groupby("parent")["value_fob"].sum() / e["value_fob"].sum()).sort_values(ascending=False)
    top15 = ps.head(15)
    F["parents"] = {k: float(100 * v) for k, v in ps.head(20).items()}
    H = W.HAVEN_STANDALONE | set(W.HAVEN_SOVEREIGN)
    F["haven_share"] = float(100 * ps[ps.index.isin(H)].sum())
    fig_hbar_stacked("v3_fig_parents", list(top15.index), [top15.values], [C_EXT], [],
                     xmax=float(np.ceil((top15.max() + 0.04) * 20) / 20), percent=True,
                     xlabel=r"Percent of the agricultural exports of foreign MNEs with a recorded parent")
    top10p = list(ps.head(10).index)
    e2 = e[e["dest_real"].notna()]
    ds = e2.groupby("dest_real")["value_fob"].sum().sort_values(ascending=False)
    top10d = list(ds.head(10).index)
    pr = e2["parent"].where(e2["parent"].isin(top10p), "Other parents")
    dr = e2["dest_real"].where(e2["dest_real"].isin(top10d), "Other destinations")
    m = e2.assign(pr=pr, dr=dr).pivot_table(index="pr", columns="dr", values="value_fob", aggfunc="sum").fillna(0)
    m = m.reindex(index=top10p + ["Other parents"], columns=top10d + ["Other destinations"])
    m = 100 * m / m.sum(axis=0)
    rows = [[i] + [f"{x:.1f}" for x in r] for i, r in m.iterrows()]
    rows.append(["Total"] + ["100.0"] * m.shape[1])
    F["pxd"] = {c: {i: float(m.loc[i, c]) for i in m.index} for c in m.columns}
    F["top10p_share"] = float(100 * ps.head(10).sum()); F["top10d_share"] = float(100 * ds.head(10).sum() / ds.sum())
    F["home_share_2018"] = float(100 * e.loc[e["country_dest"] == e["parent"], "value_fob"].sum() / a.loc[ext, "value_fob"].sum())
    write_plain("v3_pxd", ["Top 10 parents / Top 10 destinations"] + top10d + ["Other destinations"], rows, midrule_before=(len(rows) - 1,))

    # Fact 2, by country: parents (figure) and the three main parents (table)
    eo = a[ext]
    tops = top10p
    shares = []
    for o in list(sub.index):
        s_ = a if o == "LAC9" else a[a["country_orig"] == o]
        v = s_["value_fob"].sum()
        row = [s_.loc[(s_["otype"] == "ext") & (s_["parent"] == p), "value_fob"].sum() / v for p in tops]
        row.append(s_.loc[(s_["otype"] == "ext") & ~s_["parent"].isin(tops), "value_fob"].sum() / v)
        row.append(s_.loc[s_["otype"] == "dom", "value_fob"].sum() / v)
        shares.append(row)
    shares = np.array(shares).T
    fig_hbar_stacked("v3_fig_country_parent", [COUNTRY.get(o, o) for o in sub.index], list(shares), PAL12[:len(tops)] + [PAL12[10], PAL12[11]],
                     tops + ["Other foreign MNEs", "Domestic MNEs"], legend_cols=4, gap_after=len(sub) - 2)
    rows = []
    for o in order:
        s_ = eo[(eo["country_orig"] == o) & (eo["parent"] != "")]
        t3 = (s_.groupby("parent")["value_fob"].sum() / s_["value_fob"].sum()).sort_values(ascending=False).head(3)
        rows.append([COUNTRY[o]] + [f"{p} ({100 * v:.0f})" for p, v in t3.items()] + [f"{100 * t3.sum():.0f}"])
        F[f"top3_{o}"] = [[p, float(100 * v)] for p, v in t3.items()]
    write_plain("v3_country_parents", ["Country", r"First parent country (\%)", r"Second (\%)", r"Third (\%)", r"Three together (\%)"],
                rows, colspec="lllll")

    # Fact 3: size of the global network of the groups, aggregate (figure) and by country (table)
    import pyreadstat
    import wp0_fact4_groups as G0
    net, _ = pyreadstat.read_dta(str(G0.NET_DTA), encoding="latin1", usecols=["name_parent_adj", "total_affiliates"])
    net["pkey"] = net["name_parent_adj"].astype(str).str.upper().str.strip()
    net = net.groupby("pkey", as_index=False).agg(total_affiliates=("total_affiliates", "max"))
    a["pkey"] = a["parent_key"].fillna("").astype(str).str.upper().str.strip()
    ex = a[ext & (a["pkey"] != "")]

    def bins(df):
        par = df.groupby("pkey", as_index=False).agg(v=("value_fob", "sum")).merge(net, on="pkey", how="left")
        cov = (par["total_affiliates"].notna().mean(), par.loc[par["total_affiliates"].notna(), "v"].sum() / par["v"].sum())
        par = par[par["total_affiliates"].notna()]
        b = pd.cut(par["total_affiliates"], G0.EDGES, labels=G0.BINLAB, right=True, include_lowest=True)
        gg = par.groupby(b, observed=False).agg(n=("v", "size"), v=("v", "sum"))
        return gg["v"] / gg["v"].sum(), gg["n"] / gg["n"].sum(), cov
    sv, sp, cov = bins(ex)
    F["network"] = {"value": {k: float(100 * v) for k, v in sv.items()}, "parents": {k: float(100 * v) for k, v in sp.items()},
                    "coverage_parents": float(100 * cov[0]), "coverage_value": float(100 * cov[1])}
    L = [r"\begin{tikzpicture}", r"\begin{axis}[ybar, bar width=14pt, width=0.8\linewidth, height=6.5cm, ymin=0, ymax=0.6, ytick={0,0.1,0.2,0.3,0.4,0.5,0.6}, yticklabels={0,0.1,0.2,0.3,0.4,0.5,0.6},",
         r"  xtick={1,2,3,4}, xticklabels={" + ",".join("{" + l + "}" for l in G0.BINLAB) + r"}, enlarge x limits=0.18,",
         r"  tick label style={font=\footnotesize}, xlabel={Number of affiliates of the group worldwide}, ylabel={Share}, label style={font=\footnotesize},",
         r"  axis x line*=bottom, axis y line*=left, nodes near coords={\pgfmathprintnumber[fixed,precision=0]{\pgfplotspointmeta}\%},",
         r"  point meta={100*y}, nodes near coords style={font=\scriptsize},",
         r"  area legend, legend image post style={draw=none}, legend cell align=left, legend style={at={(0.5,0)}, anchor=north, yshift=-1.25cm, draw=none, font=\footnotesize, legend columns=2, /tikz/every even column/.append style={column sep=8pt}}]",
         f"\\addplot[fill={C_EXT}, draw=none] coordinates {{" + " ".join(f"({i + 1},{v:.4f})" for i, v in enumerate(sv.values)) + "};",
         f"\\addplot[fill={C_DOM}, draw=none] coordinates {{" + " ".join(f"({i + 1},{v:.4f})" for i, v in enumerate(sp.values)) + "};",
         r"\legend{Share of the export value of foreign MNEs, Share of parents}", r"\end{axis}", r"\end{tikzpicture}"]
    save_tex("v3_fig_network", "\n".join(L) + "\n")
    rows = []
    for o in order:
        sv_o, sp_o, cov_o = bins(ex[ex["country_orig"] == o])
        rows.append([COUNTRY[o]] + [f"{100 * x:.1f}" for x in sv_o.values] + [f"{100 * sp_o.iloc[0]:.1f}", f"{100 * cov_o[1]:.0f}"])
        F[f"network_{o}"] = {"value": [float(100 * x) for x in sv_o.values], "one": float(100 * sp_o.iloc[0])}
    rows.append(["LAC9"] + [f"{100 * x:.1f}" for x in sv.values] + [f"{100 * sp.iloc[0]:.1f}", f"{100 * cov[1]:.0f}"])
    write_plain("v3_country_network", ["Country"] + [rf"{l} (\%)" for l in G0.BINLAB] + [r"Parents with one affiliate (\%)", r"Coverage (\%)"],
                rows, midrule_before=(len(rows) - 1,))

    # Fact 5: groups of products, aggregate and by country, 2018
    g = a.assign(v_mne=a["value_fob"] * (a["otype"] != "local"), v_ext=a["value_fob"] * (a["otype"] == "ext")).groupby(
        ["country_orig", "hs07_6d"], as_index=False).agg(total_value=("value_fob", "sum"), v_mne=("v_mne", "sum"), v_ext=("v_ext", "sum"))
    g = g.merge(classification(), on="hs07_6d", how="left")
    assert g["crop"].notna().all(), "2018 products missing from the classification"
    tot = g["total_value"].sum()
    rows = []
    for lab, col, keys, names in (("Type of production", "crop", list(CT_KEYS.values()), list(CT_KEYS.values())),
                                  ("Capital intensity", "kgroup", list(KI_KEYS) + ["ki_nc"],
                                   ["Farm stage, high", "Farm stage, low", "Processing stage, high", "Processing stage, low", "Not classified"]),
                                  (r"Type of production $\times$ capital intensity", "tx", list(TX_KEYS), [TX_SHORT[k] for k in TX_KEYS])):
        rows.append([rf"\textit{{{lab}}}", "", "", "", "", ""])
        for k, nm in zip(keys, names):
            s_ = g[g[col] == k]
            if not len(s_):
                continue
            kl = np.average(s_["kl"].fillna(0), weights=s_["total_value"]) if (col != "crop" and s_["kl"].notna().any()) else np.nan
            rows.append([nm, f"{s_['hs07_6d'].nunique():,}", f"{100 * s_['total_value'].sum() / tot:.1f}",
                         f"{100 * s_['v_mne'].sum() / s_['total_value'].sum():.1f}", f"{100 * s_['v_ext'].sum() / s_['total_value'].sum():.1f}",
                         "" if np.isnan(kl) else f"{kl:,.0f}"])
            F[f"group_{k}"] = {"share": float(100 * s_["total_value"].sum() / tot), "mne": float(100 * s_["v_mne"].sum() / s_["total_value"].sum()),
                               "n": int(s_["hs07_6d"].nunique())}
    write_plain("v3_groups", ["Group", "Products", r"Share of exports (\%)", r"MNE share (\%)", r"Foreign MNE share (\%)",
                              r"Capital per worker (US\$ thousand)"], rows, colspec="lrrrrr")
    orderg = FACTS["origin_order"]
    rows = []
    for lab, col, keys, names in (("Type of production", "crop", list(CT_KEYS.values()), [CT_SHORT[k] for k in CT_KEYS]),
                                  ("Capital intensity", "kgroup", list(KI_KEYS) + ["ki_nc"],
                                   ["Farm stage, high", "Farm stage, low", "Processing stage, high", "Processing stage, low", "Not classified"])):
        rows.append([rf"\textit{{{lab}}}"] + [""] * len(orderg))
        for k, nm in zip(keys, names):
            r = [nm]
            for o in orderg:
                s_ = g[(g["country_orig"] == o) & (g[col] == k)]
                r.append(f"{100 * s_['v_mne'].sum() / s_['total_value'].sum():.0f}" if s_["total_value"].sum() > 0 else "")
                F[f"cgroup_{o}_{k}"] = float(100 * s_["v_mne"].sum() / s_["total_value"].sum()) if s_["total_value"].sum() > 0 else None
            rows.append(r)
    rows.append([r"\textit{Share of exports (\%)}"] + [""] * len(orderg))
    for k, nm in zip(CT_KEYS.values(), [CT_SHORT[k] for k in CT_KEYS]):
        r = [nm]
        for o in orderg:
            s_ = g[g["country_orig"] == o]
            r.append(f"{100 * s_.loc[s_['crop'] == k, 'total_value'].sum() / s_['total_value'].sum():.0f}")
            F[f"cshare_{o}_{k}"] = float(100 * s_.loc[s_["crop"] == k, "total_value"].sum() / s_["total_value"].sum())
        rows.append(r)
    write_plain("v3_country_groups", ["Group"] + orderg, rows, colspec="l" + "r" * len(orderg))


# ---------------------------------------------------------------------
# workbook: outreg2 layout, the same eleven columns in every table, the note's columns in red
# ---------------------------------------------------------------------
def plain(s: str) -> str:
    for a_, b_ in ((r"$\ln$", "ln"), (r"$\times$", "×"), (r"$R^2$", "R-squared"), (r"$p$", "p"), (r"\%", "%"), (r"\$", "$")):
        s = s.replace(a_, b_)
    return s.replace("$", "")


def note_tables() -> dict:
    if not AUX.exists():
        raise SystemExit(f"compile the note first into {AUX.parent}")
    aux = AUX.read_text(encoding="utf-8", errors="replace")
    num = dict(re.findall(r"\\newlabel\{(tab:[^}]+)\}\{\{([^}]*)\}", aux))
    tx = NOTE.read_text(encoding="utf-8")
    cap = {lab: c for c, lab in re.findall(r"\\caption\{(.+?)\}\s*\n\\label\{(tab:[^}]+)\}", tx)}
    return {lab: (num[lab], cap[lab]) for lab in num if lab in cap}


def table_block(tab, number, title):
    regs = [r for r in REGS if r["tab"] == tab]
    panels = list(dict.fromkeys(r["xpanel"] for r in regs))
    # the grid columns that apply to this table: those with at least one estimated regression. They are always the
    # first ones (cells 1 to 6, cells within one origin 1 to 5, firms 1 to 11), so column (k) is in the same place in
    # every table
    k = max(r["xcol"] for r in regs if r["n"]) + 1
    assert all(any(r["n"] for r in regs if r["xcol"] == i) for i in range(k)), f"{tab}: a grid column inside the table is empty"
    cell = {(r["xpanel"], r["xcol"]): r for r in regs}
    labels = {**LAB, **DLAB}
    rows, red, long = [[f"Table {number}. {plain(title)}"], [""] + [f"({i + 1})" for i in range(k)]], [], []
    rows.append(["Fixed effects"] + [" + ".join(GRID[i]) for i in range(k)])
    for P in panels:
        start = len(rows)
        rows.append([plain(P)])
        rr = [cell.get((P, i)) for i in range(k)]
        rows.append(["Dependent variable"] + [plain(DEPLAB.get(r["dep"], r["dep"])) if r else "" for r in rr])
        for v in dict.fromkeys(v for r in rr if r for v in r["regs"]):
            b, s = [], []
            for r in rr:
                if r and v in r["cells"]:
                    bb, ss, pp = r["cells"][v]; b.append(f"{bb:.3f}{stars(pp)}"); s.append(f"({ss:.3f})")
                elif r and r["n"]:     # left out because the fixed effects absorb it, or dropped as collinear
                    b.append("Absorbed by the FE" if v not in r["regs"] else "Not identified"); s.append("")
                else:
                    b.append(""); s.append("")
            rows += [[plain(labels.get(v, v))] + b, [""] + s]
        for t in dict.fromkeys(t for r in rr if r for t in r["tests"]):
            rows.append([f"p value of the test: {t}"] + [f"{r['tests'][t]:.3f}" if r and t in r["tests"] and not np.isnan(r["tests"][t]) else "" for r in rr])
        rows.append(["Observations"] + [f"{r['n']:,}" if r and r["n"] else "" for r in rr])
        rows.append(["R-squared"] + [f"{r['r2']:.3f}" if r and r["n"] else "" for r in rr])
        rows.append(["Within R-squared"] + [f"{r['r2w']:.3f}" if r and r["n"] and not np.isnan(r["r2w"]) else "" for r in rr])
        for e in dict.fromkeys(e for r in rr if r for e in r["extra"]):
            rows.append([e] + [r["extra"].get(e, "") if r else "" for r in rr])
        rows.append(["Column in the note"] + [(r["shown"] or r["status"] or "Not shown") if r else "" for r in rr])
        for i, r in enumerate(rr):
            if r and r["shown"]:
                red.append((start, len(rows) - 1, i + 1))
            if not r or not r["n"]:
                continue
            base = {"Table": f"Table {number}", "Title": plain(title), "Panel": plain(P), "Column": f"({i + 1})",
                    "Fixed effects": " + ".join(plain(FE_ALL[kk][0]) for kk in r["fe_keys"]), "Column in the note": r["shown"] or "Not shown",
                    "Dependent variable": plain(DEPLAB.get(r["dep"], r["dep"])), "Clustered by": CLUSTER_LAB.get(r["cluster"], r["cluster"]),
                    "Sample": r["sample"], "Observations": r["n"], "R-squared": r["r2"], "Within R-squared": r["r2w"]}
            for v in r["regs"]:
                if v in r["cells"]:
                    bb, ss, pp = r["cells"][v]
                    long.append({**base, "Regressor": plain(labels.get(v, v)), "Coefficient": bb, "Standard error": ss, "p value": pp, "Stars": stars(pp)})
            for t, pv in r["tests"].items():
                long.append({**base, "Regressor": f"Test: {t}", "Coefficient": None, "Standard error": None, "p value": pv, "Stars": stars(pv) if not np.isnan(pv) else ""})
    for kk in FE_ALL:
        rows.append([f"{plain(FE_ALL[kk][0])} FE"] + ["Yes" if kk in GRID[i] else "No" for i in range(k)])
    if any(r["cluster"] == "country_dest" for r in regs):
        rows.append(["Within one exporting country, origin x destination x product FE are destination x product FE, and so on."])
    cl = sorted({CLUSTER_LAB.get(r["cluster"], r["cluster"]) for r in regs})
    rows.append([f"Standard errors in parentheses, clustered by {' and '.join(cl)}. *** p<0.01, ** p<0.05, * p<0.1. "
                 "Red: the columns printed in the note."])
    return rows, red, long


def links_sheet(wb, meta) -> None:
    """Fact 5 under the two links from HS to NAICS, grid columns 4 and 6 (columns 4 and 5 of the tables of the note). The
    UNSD tables are the regressions of this workbook, in red because the note prints them. The Census concordance comes
    from `WP_NAICS=census python wp_agro_note_v3.py alt`."""
    from openpyxl.styles import Font
    alt = OUTD / "v3_regressions_census.pkl"
    if not alt.exists():
        return
    with open(alt, "rb") as fh:
        c = pickle.load(fh)

    def cell(R, tab, panel, g, v):
        for r in R:
            if r["tab"] == tab and r["xpanel"] == panel and r["xcol"] == g:
                if v in r["cells"]:
                    b_, s_, p_ = r["cells"][v]
                    return f"{b_:.3f}{stars(p_)} ({s_:.3f})"
                if v in r["tests"]:
                    return f"{r['tests'][v]:.3f}"
        return ""
    ws = wb.create_sheet("Regressions, both links")
    ws.append(["Fact 5 under the two links from HS to NAICS. Column (4): ODP + ODY. Column (6): ODP + ODY + OPY + DPY, the strictest "
               "specification. Red: the columns printed in the note."])
    ws["A1"].font = Font(bold=True)
    ws.append(["Table", "Panel", "Regressor or test", "(4) UNSD tables", "(4) Census concordance", "(6) UNSD tables", "(6) Census concordance"])
    for j in range(1, 8):
        ws.cell(row=2, column=j).font = Font(bold=True)
    for tab in ("tab:capital", "tab:txk", "tab:capital_ext", "tab:txk_ext"):
        for P in dict.fromkeys(r["xpanel"] for r in REGS if r["tab"] == tab):
            base = [r for r in REGS if r["tab"] == tab and r["xpanel"] == P and r["xcol"] == 3][0]
            for v in list(base["regs"]) + list(base["tests"]):
                if v in base["tests"]:
                    lab = f"p value of the test: {v}"
                else:
                    lab = ("ln(number of MNEs)" if v.startswith("lnN") else "At least one MNE") + " x " + {**KI_LAB, **TX_LAB}.get(v.split("_", 1)[1], v)
                ws.append([f"Table {meta[tab][0]}", plain(P), lab] + [cell(R, tab, P, g, v) for g in (3, 5) for R in (REGS, c)])
                for j in (4, 6):
                    ws.cell(row=ws.max_row, column=j).font = Font(color="C00000")
    for col, w in zip("ABCDEFG", (11, 44, 72, 20, 22, 20, 22)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "D3"


def workbook() -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, Side
    from openpyxl.utils import get_column_letter
    meta = note_tables()
    tabs = list(dict.fromkeys(r["tab"] for r in REGS))
    miss = [t for t in tabs if t not in meta]
    assert not miss, f"tables not in the compiled note: {miss}"
    tabs.sort(key=lambda t: (meta[t][0].startswith("A"), float(meta[t][0].split(".")[-1])))
    blocks = {t: table_block(t, *meta[t]) for t in tabs}
    wb = Workbook(); thin = Side(style="thin"); RED = "C00000"

    def put(ws, block, r0):
        rows, red, _ = block
        for i, row in enumerate(rows):
            for j, v in enumerate(row):
                c = ws.cell(row=r0 + i, column=j + 1, value=v)
                if j:
                    c.alignment = Alignment(horizontal="center")
        ws.cell(row=r0, column=1).font = Font(bold=True)
        for j in range(1, len(rows[1]) + 1):
            ws.cell(row=r0 + 1, column=j).border = Border(top=thin)
            ws.cell(row=r0 + 2, column=j).border = Border(bottom=thin)
            ws.cell(row=r0 + len(rows) - 2, column=j).border = Border(bottom=thin)
        for (a_, b_, j) in red:
            for i in range(a_ + 1, b_ + 1):
                ws.cell(row=r0 + i, column=j + 1).font = Font(color=RED)
        return r0 + len(rows)

    def widths(ws):
        ws.column_dimensions["A"].width = 66
        for j in range(2, len(GRID) + 2):
            ws.column_dimensions[get_column_letter(j)].width = 17
    ws = wb.active; ws.title = "All regressions"
    r = 1
    for t in tabs:
        r = put(ws, blocks[t], r) + 2
    widths(ws); ws.freeze_panes = "B1"
    for t in tabs:
        ws = wb.create_sheet(f"Table {meta[t][0]}")
        put(ws, blocks[t], 1); widths(ws); ws.freeze_panes = "B4"
    links_sheet(wb, meta)
    ws = wb.create_sheet("Long format")
    cols = ["Table", "Title", "Panel", "Column", "Column in the note", "Dependent variable", "Regressor", "Coefficient", "Standard error",
            "p value", "Stars", "Observations", "R-squared", "Within R-squared", "Fixed effects", "Clustered by", "Sample"]
    ws.append(cols)
    nlong = 0
    for t in tabs:
        for row in blocks[t][2]:
            ws.append([None if (isinstance(row[c], float) and np.isnan(row[c])) else row[c] for c in cols]); nlong += 1
    for j, w in enumerate([10, 50, 45, 8, 24, 34, 50, 12, 12, 10, 6, 12, 10, 12, 60, 36, 22]):
        ws.column_dimensions[get_column_letter(j + 1)].width = w
    ws.freeze_panes = "A2"
    ws = wb.create_sheet("Notes")
    for row in [["Notes"],
                ["Columns", "One grid of eleven sets of fixed effects. Column (k) has the same fixed effects in every table and in every block of All regressions. The row Fixed effects at the top and the Yes/No rows at the bottom give them."],
                ["Which columns", "Regressions on origin x destination x product x year cells have columns (1) to (6): a cell adds up all the firms, so firm fixed effects, columns (7) to (11), do not apply. Cell regressions within one exporting country have columns (1) to (5): column (6) would leave one observation per fixed effect. Firm regressions (distance) have all eleven."],
                ["Red", "The cells in red are the columns printed in the note. Black cells are estimated for this workbook only."],
                ["Abbreviations", "Row Fixed effects: O origin, D destination, P product, Y year, F firm; OY origin x year, ODP origin x destination x product, FPY firm x product x year, and so on."],
                ["Absorbed by the FE", "A regressor left out because the fixed effects of the column absorb it: ln distance with origin x destination x product or origin x destination x year FE (and with any destination FE within one origin), the MNE indicator with firm FE."],
                ["By country", "Within one exporting country, origin x destination x product FE are destination x product FE, and so on."],
                ["Period and sample", "2012 to 2018, agricultural products (HS chapters 01 to 24), nine origins. Product codes are HS 2017 (UNSD correlation tables). Uruguay's codes of 2016 to 2018 are corrected (wp_common.fix_shifted_codes)."],
                ["Capital intensity", f"Link from HS to NAICS used in this workbook: {'UNSD tables' if NAICS_SOURCE == 'unsd' else 'Census concordance'}. The sheet Regressions, both links compares the two."],
                ["Stars", "*** p<0.01, ** p<0.05, * p<0.1"],
                ["Source", "stylized_facts/python/wp_agro_note_v3.py"]]:
        ws.append(row)
    ws.column_dimensions["A"].width = 20; ws.column_dimensions["B"].width = 150; ws["A1"].font = Font(bold=True)
    wb.save(XLSX)
    print(f"workbook: {XLSX} ({len(tabs)} tables, {sum(1 for r in REGS if r['n'])} regressions estimated, {nlong:,} long rows)")


# ---------------------------------------------------------------------
# the note: inline every table and figure
# ---------------------------------------------------------------------
def flatten() -> None:
    src = SRC.read_text(encoding="utf-8")

    def rep(m):
        p = TEXD.parent.parent / (m.group(1) + ".tex")
        return p.read_text(encoding="utf-8").rstrip("\n")
    out = re.sub(r"\\input\{(tables/v3/[A-Za-z0-9_]+)\}", rep, src)
    assert "\\input{" not in out and "\\includegraphics" not in out, "the note still reads external files"
    NOTE.write_text(out, encoding="utf-8")
    print(f"flattened -> {NOTE}")


def main() -> None:
    assert W.YEAR_WINDOW == (2012, 2018), "run with WP_YEARS=2012-2018"
    which = sys.argv[1:] or ["all"]
    if which == ["workbook"]:
        with open(PICKLE, "rb") as fh:
            REGS.extend(pickle.load(fh))
        workbook(); return
    if which == ["flatten"]:
        flatten(); return
    if which == ["alt"]:               # Fact 5 regressions with the Census concordance, for the comparison of the two links
        assert NAICS_SOURCE == "census", "run with WP_NAICS=census"
        globals()["save_tex"] = lambda *a_: None
        g = cells()
        FACTS["origin_order"] = origins_by_value(g)
        heterogeneity(g); heterogeneity_by_country(g)
        with open(OUTD / "v3_regressions_census.pkl", "wb") as fh:
            pickle.dump(REGS, fh)
        return
    if which == ["replay"]:            # every table and figure again, the regressions read from the pickle
        global REPLAY
        with open(PICKLE, "rb") as fh:
            REPLAY = {(r["tab"], r["xpanel"], r["xcol"]): r for r in pickle.load(fh) if r["n"] or r["status"].startswith("Not estimated")}
        which = ["all"]
    g = cells()
    FACTS["origin_order"] = origins_by_value(g)
    if "all" in which or "desc" in which:
        descriptives(g)
    if "all" in which or "presence" in which:
        presence(g); presence_by_country(g)
    if "all" in which or "hetero" in which:
        heterogeneity(g); heterogeneity_by_country(g)
    if "all" in which or "distance" in which:
        del g; gc.collect()
        f = firm_panel(); distance(f); distance_by_country(f)
    if "all" in which:
        with open(PICKLE, "wb") as fh:
            pickle.dump(REGS, fh)
        json.dump({**FACTS, "regs": [{k: v for k, v in r.items() if k != "fe_map"} for r in REGS]}, open(FACTS_JSON, "w"), default=str, indent=1)
        print(f"saved {len(REGS)} regressions -> {PICKLE}; facts -> {FACTS_JSON}")


if __name__ == "__main__":
    main()
