"""
wp_agro_note_v3.py  --  every exhibit of Note_v3.tex (agriculture note, version 3), 2026-11-02
==============================================================================================

    WP_YEARS=2012-2018 WP_SCOPES=agro python wp_agro_note_v3.py

Builds, for agriculture (HS 01--24), nine origins, convention "sf":
  * descriptive tables for 2018 (sample by country, multinational summary, country facts, groups of products)
  * every regression with the fixed effects added progressively, from the panel specification
    (origin, destination, product and year fixed effects) to the strictest one
  * the master workbook docs/notes/WP_paperagro_v3_master_estimates.xlsx: one row per coefficient of every
    specification (coefficient, standard error, p-value, stars, observations, R-squared, fixed effects, sample),
    plus one sheet per table in the layout of the LaTeX table

LaTeX tables go to docs/overleaf_projects/WP_paperagro/tables/v3/ (and output/wp_2012_2018/agro/v3/).

Regressions
  presence (origin x destination x product x year cells; clustered by origin-destination):
    ln X_odpy = b ln N_odpy (intensive, cells with >= 1 MNE) or b 1[N_odpy > 0] (extensive) + FE
    dependent: ln exports of all firms, ln exports of local firms; on the products where MNEs operate also
    ln number of local exporters and ln exports per local exporter
  heterogeneity: ln N (or the indicator) interacted with each type of production (FAO crop groups,
    wp_agro_croptype) or with each capital-intensity group (wp_agro_capital), no main term
  distance (firm x destination x product x year): ln x = a ln D + g (MNE x ln D) [+ MNE] + FE; local firms:
    ln x = a ln D + c AnyMNE_odpy + g (AnyMNE_odpy x ln D) + FE
  by country: the presence regression origin by origin

Every regression is run with every fixed-effect set of its progression, also those the note does not show (the
products where MNEs operate and the by-country table show only some columns). The workbook (2026-11-03) is laid
out like an outreg2 export: sheet "All regressions" stacks every table, then one sheet per table of the note
("Table 5", ..., "Table A.2", numbers and titles read from the compiled note), then "Long format" (one row per
coefficient) and "Notes". The table numbers need the .aux of the compiled note:

    pdflatex -output-directory=<OUTD>/build Note_v3.tex          (twice)
    WP_YEARS=2012-2018 WP_SCOPES=agro python wp_agro_note_v3.py workbook    (rebuilds the workbook from the pickle)
"""
from __future__ import annotations

import gc
import pickle
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_common as W  # noqa: E402
import wp1e_hq_affiliates as E  # noqa: E402
import wp_agro_croptype as C  # noqa: E402
import wp_agro_capital as K  # noqa: E402

SCOPE = "agro"
OUTD = W.WP_OUT / SCOPE / "v3"
TEXD = W.ROOT / "docs" / "overleaf_projects" / "WP_paperagro" / "tables" / "v3"
XLSX = W.ROOT / "docs" / "notes" / "WP_paperagro_v3_master_estimates.xlsx"
for d in (OUTD, TEXD, XLSX.parent):
    d.mkdir(parents=True, exist_ok=True)
COUNTRY = {"ARG": "Argentina", "CHL": "Chile", "COL": "Colombia", "CRI": "Costa Rica", "DOM": "Dominican Republic",
           "PER": "Peru", "PRY": "Paraguay", "SLV": "El Salvador", "URY": "Uruguay"}
MASTER: list[dict] = []          # one dict per coefficient
REGS: list[dict] = []            # one dict per regression, with its place in the workbook layout
LAYOUTS: dict[str, pd.DataFrame] = {}
PICKLE = OUTD / "v3_regressions.pkl"
AUX = OUTD / "build" / "Note_v3.aux"
NOTE_TEX = TEXD.parent.parent / "Note_v3.tex"

# ---------------------------------------------------------------------
# fixed effects
# ---------------------------------------------------------------------
FE_CELL = {"O": ("Origin", "country_orig"), "D": ("Destination", "country_dest"), "P": ("Product", "hs07_6d"),
           "Y": ("Year", "year"), "OY": (r"Origin $\times$ year", "ot"), "DY": (r"Destination $\times$ year", "dt"),
           "ODP": (r"Origin $\times$ destination $\times$ product", "odp"),
           "ODY": (r"Origin $\times$ destination $\times$ year", "ody"),
           "OPY": (r"Origin $\times$ product $\times$ year", "opy"),
           "DPY": (r"Destination $\times$ product $\times$ year", "dpy")}
CELL_SETS = [["O", "D", "P", "Y"], ["OY", "DY", "P"], ["ODP", "Y"], ["ODP", "ODY"], ["ODP", "ODY", "OPY", "DPY"]]
FE_FIRM = {"O": ("Origin", "country_orig"), "D": ("Destination", "country_dest"), "P": ("Product", "hs07_6d"),
           "Y": ("Year", "year"), "OY": (r"Origin $\times$ year", "ot"), "DY": (r"Destination $\times$ year", "dt"),
           "F": ("Firm", "fid"), "FP": (r"Firm $\times$ product", "fp"), "FY": (r"Firm $\times$ year", "fy"),
           "FPY": (r"Firm $\times$ product $\times$ year", "fpy"), "DPY": (r"Destination $\times$ product $\times$ year", "dpy")}
FIRM_SETS = [["O", "D", "P", "Y"], ["OY", "DY", "P"], ["OY", "DY", "P", "F"], ["OY", "DY", "FP"], ["FY", "DY", "P"],
             ["FPY", "DY"], ["FPY", "DPY"]]
# by country (one origin): origin x destination x product = destination x product, and so on
FE_CTRY = {"D": ("Destination", "country_dest"), "P": ("Product", "hs07_6d"), "Y": ("Year", "year"),
           "DY": (r"Destination $\times$ year", "dt"), "DP": (r"Destination $\times$ product", "odp"),
           "PY": (r"Product $\times$ year", "opy")}
CTRY_SETS = [["D", "P", "Y"], ["DY", "P"], ["DP", "Y"], ["DP", "DY"], ["DP", "DY", "PY"]]
CTRY_SHOWN = 3                   # the note shows destination x product and destination x year FE
CLUSTER_LAB = {"od": "origin and destination pair", "country_dest": "destination country"}


def stars(p):
    return W.stars(p)


def fit(data, dep, regs, fe_keys, fe_map, table, panel, col, sample, cluster="od", weights=None, tests=(),
        tab=None, xpanel=None, xcol=None, shown="", extra=None):
    """Estimate, record every coefficient in MASTER and the regression in REGS, return {var: (b, se, p)}, N, R2 and
    test p-values. tab = LaTeX label of the note's table; xpanel/xcol = panel and column of the workbook layout;
    shown = where the note reports it ("" = workbook only); extra = {row label: value} for the workbook."""
    fe = " + ".join(fe_map[k][1] for k in fe_keys)
    dd = data.dropna(subset=[dep] + regs)
    t0 = time.time()
    reg = dict(tab=tab, xpanel=xpanel if xpanel is not None else panel, xcol=xcol if xcol is not None else col, shown=shown,
               dep=dep, regs=list(regs), fe_keys=list(fe_keys), fe_map=fe_map, cluster=cluster, sample=sample,
               extra=extra or {}, cells={}, tests={}, n=0, r2=np.nan, r2w=np.nan)
    try:
        m = W.feols(f"{dep} ~ {' + '.join(regs)} | {fe}", data=dd, vcov={"CRV1": cluster}, weights=weights)
    except Exception as e:  # noqa: BLE001
        print(f"   {table} {panel} {col}: FAILED {str(e)[:90]}")
        if tab:
            REGS.append(reg)
        return {"cells": {}, "n": 0, "r2": np.nan, "tests": {}}
    b, se, p = m.coef(), m.se(), m.pvalue()
    r2 = float(getattr(m, "_r2", np.nan)); r2w = float(getattr(m, "_r2_within", np.nan))
    cells = {v: (float(b[v]), float(se[v]), float(p[v])) for v in regs if v in b.index}
    tres = {}
    if tests:
        V = np.asarray(m._vcov); ix = list(b.index)
        for name, (v1, v2) in tests:
            if v1 in ix and v2 in ix:
                i, j = ix.index(v1), ix.index(v2)
                diff = b[v1] - b[v2]; sd = float(np.sqrt(V[i, i] + V[j, j] - 2 * V[i, j]))
                from scipy.stats import norm
                tres[name] = float(2 * (1 - norm.cdf(abs(diff / sd))))
    if tab:
        reg.update(cells=cells, tests=tres, n=int(m._N), r2=r2, r2w=r2w)
        REGS.append(reg)
    for v, (bb, ss, pp) in cells.items():
        MASTER.append(dict(tab=tab, table=table, panel=panel, column=col, sample=sample, dependent=dep, regressor=v, coef=bb, se=ss,
                           pvalue=pp, stars=stars(pp), nobs=int(m._N), r2=r2, r2_within=r2w,
                           fixed_effects=" + ".join(fe_map[k][0] for k in fe_keys), cluster=cluster,
                           weights=weights or ""))
    for name, pv in tres.items():
        MASTER.append(dict(tab=tab, table=table, panel=panel, column=col, sample=sample, dependent=dep, regressor=f"test: {name}",
                           coef=np.nan, se=np.nan, pvalue=pv, stars=stars(pv), nobs=int(m._N), r2=r2, r2_within=r2w,
                           fixed_effects=" + ".join(fe_map[k][0] for k in fe_keys), cluster=cluster, weights=weights or ""))
    print(f"   {table} {panel[:28]:28s} {col}: N={int(m._N):>9,} " + " ".join(f"{v}:{c[0]:+.3f}{stars(c[2])}" for v, c in cells.items())
          + "".join(f" [{k} p={v:.3f}]" for k, v in tres.items()) + f" ({time.time() - t0:.0f}s)")
    out = {"cells": cells, "n": int(m._N), "r2": r2, "tests": tres}
    del m; gc.collect()
    return out


def write_table(name, panels, fe_sets, fe_map, labels, extra_rows=None, test_rows=None, r2=True):
    """panels: [(panel label, [result per column])]; labels: {var: row label}. Writes LaTeX + layout sheet."""
    k = len(fe_sets)
    L = [rf"\begin{{tabular}}{{l*{{{k}}}{{c}}}}", r"\toprule", " & " + " & ".join(f"({i + 1})" for i in range(k)) + r" \\", r"\midrule"]
    lay = []
    for pi, (plab, res) in enumerate(panels):
        if pi:
            L.append(r"\midrule")
        if plab:
            L.append(rf"\multicolumn{{{k + 1}}}{{l}}{{\textit{{{plab}}}}} \\")
            lay.append([plab] + [""] * k)
        rows = list(dict.fromkeys(v for r in res for v in r["cells"]))
        for v in rows:
            rb, rs = [], []
            for r in res:
                if v in r["cells"]:
                    bb, ss, pp = r["cells"][v]; rb.append(f"{bb:.3f}{stars(pp)}"); rs.append(f"({ss:.3f})")
                else:
                    rb.append(""); rs.append("")
            L += [f"{labels.get(v, v)} & " + " & ".join(rb) + r" \\", " & " + " & ".join(rs) + r" \\"]
            lay += [[labels.get(v, v)] + rb, [""] + rs]
        for tname, tlab in (test_rows or []):
            vals = [f"{r['tests'][tname]:.3f}" if tname in r["tests"] else "" for r in res]
            if any(vals):
                L.append(f"{tlab} & " + " & ".join(vals) + r" \\"); lay.append([tlab] + vals)
        nlab = "Observations" + (f" ({plab.split('.')[0]})" if plab and len(panels) > 1 else "")
        L.append(f"{nlab} & " + " & ".join(f"{r['n']:,}" if r["n"] else "" for r in res) + r" \\")
        lay.append([nlab] + [f"{r['n']:,}" for r in res])
        if r2:
            L.append(r"$R^2$ & " + " & ".join(f"{r['r2']:.3f}" if r["n"] else "" for r in res) + r" \\")
            lay.append(["R2"] + [f"{r['r2']:.3f}" for r in res])
    L.append(r"\midrule")
    keys = [kk for kk in fe_map if any(kk in s for s in fe_sets)]
    for kk in keys:
        L.append(f"{fe_map[kk][0]} FE & " + " & ".join(r"$\checkmark$" if kk in s else "" for s in fe_sets) + r" \\")
        lay.append([f"{fe_map[kk][0]} FE".replace("$\\times$", "x")] + ["Yes" if kk in s else "" for s in fe_sets])
    for lab, vals in (extra_rows or []):
        L.append(f"{lab} & " + " & ".join(vals) + r" \\"); lay.append([lab] + vals)
    L += [r"\bottomrule", r"\end{tabular}"]
    txt = "\n".join(L) + "\n"
    (OUTD / f"{name}.tex").write_text(txt, encoding="utf-8")
    (TEXD / f"{name}.tex").write_text(txt, encoding="utf-8")
    LAYOUTS[name] = pd.DataFrame(lay, columns=[""] + [f"({i + 1})" for i in range(k)])


def write_plain(name, header, rows, colspec=None, midrule_before=()):
    """A descriptive table (booktabs)."""
    k = len(header)
    L = [rf"\begin{{tabular}}{{{colspec or ('l' + 'r' * (k - 1))}}}", r"\toprule", " & ".join(header) + r" \\", r"\midrule"]
    for i, r in enumerate(rows):
        if i in midrule_before:
            L.append(r"\midrule")
        L.append(" & ".join(r) + r" \\")
    L += [r"\bottomrule", r"\end{tabular}"]
    txt = "\n".join(L) + "\n"
    (OUTD / f"{name}.tex").write_text(txt, encoding="utf-8")
    (TEXD / f"{name}.tex").write_text(txt, encoding="utf-8")
    LAYOUTS[name] = pd.DataFrame(rows, columns=header)


# ---------------------------------------------------------------------
# product groups (type of production, capital intensity) and the products where MNEs operate
# ---------------------------------------------------------------------
CT_KEYS = {"horti": "Horticultural and plantation crops", "field": "Field crops", "live": "Livestock and fisheries",
           "proc": "Other processed food and beverages"}
CT_LAB = {"horti": "horticultural and plantation crops", "field": "field crops", "live": "livestock and fisheries",
          "proc": "other processed food"}
KI_KEYS = {"farm_hi": ("Farm", 1.0), "farm_lo": ("Farm", 0.0), "proc_hi": ("Processing", 1.0), "proc_lo": ("Processing", 0.0)}
KI_LAB = {"farm_hi": "farm stage, high capital intensity", "farm_lo": "farm stage, low capital intensity",
          "proc_hi": "processing stage, high capital intensity", "proc_lo": "processing stage, low capital intensity",
          "ki_nc": "not classified"}


def product_groups(hs: pd.Series) -> pd.DataFrame:
    """crop type and capital-intensity group for each hs07_6d (HS 2007); capital groups matched on HS6, else on the
    most common group of the same HS4 heading."""
    cap = pd.read_parquet(K.OUT.with_suffix(".parquet"))
    u = pd.DataFrame({"hs07_6d": pd.Series(hs.unique())})
    u = u.merge(cap[["hs6", "stage", "ki_high", "kl"]].rename(columns={"hs6": "hs07_6d"}), on="hs07_6d", how="left")
    cap["hs4"] = cap["hs6"].str[:4]
    by4 = (cap.dropna(subset=["stage"]).groupby("hs4")
           .agg(stage4=("stage", lambda s: s.mode().iat[0]), ki4=("ki_high", lambda s: s.mode().iat[0]), kl4=("kl", "median")))
    u = u.merge(by4, left_on=u["hs07_6d"].str[:4], right_index=True, how="left")
    # 2026-11-03: the HS4 fallback only for codes absent from the concordance (HS 2007 codes split or renumbered by
    # later HS revisions, e.g. soybeans 120100 or wheat 100190); a code that is in the concordance but maps to an
    # unclassified industry (fishing 114, forestry 113, ...) stays unclassified
    miss = ~u["hs07_6d"].isin(cap["hs6"])
    u.loc[miss, "stage"] = u.loc[miss, "stage4"]; u.loc[miss, "ki_high"] = u.loc[miss, "ki4"]; u.loc[miss, "kl"] = u.loc[miss, "kl4"]
    u["crop"] = C.crop_type(u["hs07_6d"])
    u["kgroup"] = "ki_nc"
    for k, (st, hi) in KI_KEYS.items():
        u.loc[(u["stage"] == st) & (u["ki_high"] == hi), "kgroup"] = k
    return u[["hs07_6d", "crop", "stage", "ki_high", "kl", "kgroup"]]


# ---------------------------------------------------------------------
# cells
# ---------------------------------------------------------------------
def cells() -> pd.DataFrame:
    d = W.scope_filter(W.mne_flags(W.build_cube()), SCOPE)
    g = E.odpy_cells(d[d["value"] > 0])
    g["opy"] = g["country_orig"] + "_" + g["hs07_6d"] + "_" + g["year"].astype(str)
    g["dpy"] = g["country_dest"] + "_" + g["hs07_6d"] + "_" + g["year"].astype(str)
    g["n_local"] = (g["n_firms"] - g["n_mne"]).clip(lower=0)
    g["ln_nlocal"] = E.ln(g["n_local"])
    g["ln_xlocal_pf"] = E.ln(g["nonmne_value"] / g["n_local"].replace(0, np.nan))
    pg = product_groups(g["hs07_6d"])
    g = g.merge(pg, on="hs07_6d", how="left")
    op = g.groupby(["country_orig", "hs07_6d"])["n_mne"].transform("max")
    g["mne_product"] = (op > 0).astype(int)
    for k in CT_KEYS:
        ind = (g["crop"] == CT_KEYS[k]).astype(float)
        g[f"lnN_{k}"] = g["ln_n_mne"] * ind; g[f"any_{k}"] = g["any_n_mne"] * ind
    for k in list(KI_KEYS) + ["ki_nc"]:
        ind = (g["kgroup"] == k).astype(float)
        g[f"lnN_{k}"] = g["ln_n_mne"] * ind; g[f"any_{k}"] = g["any_n_mne"] * ind
    print(f"cells {len(g):,}; in MNE products {g['mne_product'].mean():.1%} of cells, "
          f"{g.loc[g['mne_product'] == 1, 'total_value'].sum() / g['total_value'].sum():.1%} of value")
    return g


LAB = {"ln_n_mne": r"$\ln$(number of MNEs)", "any_n_mne": "At least one MNE"}
for k in CT_KEYS:
    LAB[f"lnN_{k}"] = rf"$\ln$(number of MNEs) $\times$ {CT_LAB[k]}"; LAB[f"any_{k}"] = rf"At least one MNE $\times$ {CT_LAB[k]}"
for k in list(KI_KEYS) + ["ki_nc"]:
    LAB[f"lnN_{k}"] = rf"$\ln$(number of MNEs) $\times$ {KI_LAB[k]}"; LAB[f"any_{k}"] = rf"At least one MNE $\times$ {KI_LAB[k]}"
DEPLAB = {"ln_total": r"$\ln$ exports, all firms", "ln_nonmne": r"$\ln$ exports, local firms",
          "ln_nlocal": r"$\ln$ number of local exporters", "ln_xlocal_pf": r"$\ln$ exports per local exporter",
          "ln_exports": r"$\ln$ exports of the firm"}


def presence_tables(g: pd.DataFrame) -> None:
    # Fact 4: all firms and local firms, panels = margins, columns = fixed effects
    PA, PB = "Panel A. Intensive margin: observations with at least one MNE", "Panel B. Extensive margin: all observations"
    for dep, name, tid, tab in (("ln_total", "v3_presence_all", "Presence, all firms", "tab:t1"),
                                ("ln_nonmne", "v3_presence_local", "Presence, local firms", "tab:t1local")):
        pa = [fit(g, dep, ["ln_n_mne"], s, FE_CELL, tid, "Intensive margin", f"({i + 1})", "all cells",
                  tab=tab, xpanel=PA, xcol=i, shown=f"Panel A, column ({i + 1})") for i, s in enumerate(CELL_SETS)]
        pb = [fit(g, dep, ["any_n_mne"], s, FE_CELL, tid, "Extensive margin", f"({i + 1})", "all cells",
                  tab=tab, xpanel=PB, xcol=i, shown=f"Panel B, column ({i + 1})") for i, s in enumerate(CELL_SETS)]
        write_table(name, [(PA, pa), (PB, pb)], CELL_SETS, FE_CELL, LAB)
    # products where MNEs operate: four dependent variables, every fixed-effect set; the note shows the two strictest
    sub = g[g["mne_product"] == 1]
    SHOWN = (3, 4)
    deps = ("ln_total", "ln_nonmne", "ln_nlocal", "ln_xlocal_pf")
    res = {}
    for d, dep in enumerate(deps):
        for i, s in enumerate(CELL_SETS):
            for reg, mg, pl, P in (("ln_n_mne", "Intensive margin", "Panel A", PA), ("any_n_mne", "Extensive margin", "Panel B", PB)):
                c = 2 * d + SHOWN.index(i) + 1 if i in SHOWN else None
                res[(reg, dep, i)] = fit(sub, dep, [reg], s, FE_CELL, "Presence, MNE products", f"{mg}, {DEPLAB[dep]}", f"({i + 1})",
                                         "MNE products", tab="tab:mneprod", xpanel=P, xcol=(d, i),
                                         shown=f"{pl}, column ({c})" if c else "")
    cols = [(dep, i) for dep in deps for i in SHOWN]
    pa = [res[("ln_n_mne", dep, i)] for dep, i in cols]
    pb = [res[("any_n_mne", dep, i)] for dep, i in cols]
    write_table_mne(pa, pb, [CELL_SETS[i] for _, i in cols])


def write_table_mne(pa, pb, sets):
    """Products where MNEs operate: dependent variables in pairs of columns."""
    k = len(sets)
    head = (r" & \multicolumn{2}{c}{$\ln$ exports,} & \multicolumn{2}{c}{$\ln$ exports,} & \multicolumn{2}{c}{$\ln$ number of} & \multicolumn{2}{c}{$\ln$ exports per} \\"
            "\n" r" & \multicolumn{2}{c}{all firms} & \multicolumn{2}{c}{local firms} & \multicolumn{2}{c}{local exporters} & \multicolumn{2}{c}{local exporter} \\"
            "\n" r"\cmidrule(lr){2-3}\cmidrule(lr){4-5}\cmidrule(lr){6-7}\cmidrule(lr){8-9}")
    L = [rf"\begin{{tabular}}{{l*{{{k}}}{{c}}}}", r"\toprule", head, " & " + " & ".join(f"({i + 1})" for i in range(k)) + r" \\", r"\midrule"]
    lay = []
    for pi, (plab, res, v) in enumerate((("Panel A. Intensive margin: observations with at least one MNE", pa, "ln_n_mne"),
                                         ("Panel B. Extensive margin: all observations", pb, "any_n_mne"))):
        if pi:
            L.append(r"\midrule")
        L.append(rf"\multicolumn{{{k + 1}}}{{l}}{{\textit{{{plab}}}}} \\")
        rb = [f"{r['cells'][v][0]:.3f}{stars(r['cells'][v][2])}" if v in r["cells"] else "" for r in res]
        rs = [f"({r['cells'][v][1]:.3f})" if v in r["cells"] else "" for r in res]
        L += [f"{LAB[v]} & " + " & ".join(rb) + r" \\", " & " + " & ".join(rs) + r" \\",
              f"Observations ({plab.split('.')[0]}) & " + " & ".join(f"{r['n']:,}" for r in res) + r" \\",
              r"$R^2$ & " + " & ".join(f"{r['r2']:.3f}" for r in res) + r" \\"]
        lay += [[plab] + [""] * k, [LAB[v]] + rb, [""] + rs, ["Observations"] + [f"{r['n']:,}" for r in res]]
    L.append(r"\midrule")
    for kk in [kk for kk in FE_CELL if any(kk in s for s in sets)]:
        L.append(f"{FE_CELL[kk][0]} FE & " + " & ".join(r"$\checkmark$" if kk in s else "" for s in sets) + r" \\")
    L += [r"\bottomrule", r"\end{tabular}"]
    txt = "\n".join(L) + "\n"
    (OUTD / "v3_presence_mneprod.tex").write_text(txt, encoding="utf-8"); (TEXD / "v3_presence_mneprod.tex").write_text(txt, encoding="utf-8")
    LAYOUTS["v3_presence_mneprod"] = pd.DataFrame(lay, columns=[""] + [f"({i + 1})" for i in range(k)])


def heterogeneity_tables(g: pd.DataFrame) -> None:
    """By type of production and by capital-intensity group. Text: intensive margin (Panel A all firms, Panel B local
    firms). Appendix: extensive margin, same layout. Each table has no term without interaction."""
    ct = list(CT_KEYS); kg = list(KI_KEYS) + ["ki_nc"]
    specs = [("crop", "Type of production", ct, [("field = horticultural", ("field", "horti"))],
              [("field = horticultural", r"$p$ value: field crops = horticultural and plantation crops")]),
             ("capital", "Capital intensity", kg, [("farm high = farm low", ("farm_hi", "farm_lo")), ("processing high = processing low", ("proc_hi", "proc_lo"))],
              [("farm high = farm low", r"$p$ value: farm stage, high = low"), ("processing high = processing low", r"$p$ value: processing stage, high = low")])]
    TABS = {("crop", "int"): "tab:crop", ("crop", "ext"): "tab:crop_ext", ("capital", "int"): "tab:capital", ("capital", "ext"): "tab:capital_ext"}
    for tag, tlab, keys, tests, trows in specs:
        for mg, pre, suffix in (("Intensive margin", "lnN_", "int"), ("Extensive margin", "any_", "ext")):
            regs = [pre + k for k in keys]
            tt = [(n, (pre + a, pre + b)) for n, (a, b) in tests]
            panels = []
            for dep, who, plab in (("ln_total", "all firms", "Panel A. Dependent variable: $\\ln$ exports, all firms"),
                                   ("ln_nonmne", "local firms", "Panel B. Dependent variable: $\\ln$ exports, local firms")):
                res = [fit(g, dep, regs, s, FE_CELL, f"{tlab}, {mg.lower()}", who, f"({i + 1})", "all cells", tests=tt,
                           tab=TABS[(tag, suffix)], xpanel=plab, xcol=i, shown=f"{plab[:7]}, column ({i + 1})")
                       for i, s in enumerate(CELL_SETS)]
                panels.append((plab, res))
            write_table(f"v3_{tag}_{suffix}", panels, CELL_SETS, FE_CELL, LAB, test_rows=trows)


def group_table(g: pd.DataFrame) -> None:
    """Exports, MNE shares and US capital intensity by type of production and by capital-intensity group (2012-2018)."""
    cap = pd.read_parquet(K.OUT.with_suffix(".parquet"))
    tot = g["total_value"].sum()
    rows = []
    for lab, col, keys, names in (("Type of production", "crop", list(CT_KEYS.values()), list(CT_KEYS.values())),
                                  ("Capital intensity", "kgroup", list(KI_KEYS) + ["ki_nc"],
                                   ["Farm stage, high", "Farm stage, low", "Processing stage, high", "Processing stage, low", "Not classified"])):
        rows.append([rf"\textit{{{lab}}}", "", "", "", "", ""])
        for k, nm in zip(keys, names):
            s = g[g[col] == k]
            if not len(s):
                continue
            kl = np.average(s["kl"].fillna(0), weights=s["total_value"]) if s["kl"].notna().any() else np.nan
            rows.append([nm, f"{s['hs07_6d'].nunique():,}", f"{100 * s['total_value'].sum() / tot:.1f}",
                         f"{100 * s['v_mne'].sum() / s['total_value'].sum():.1f}", f"{100 * s['v_ext'].sum() / s['total_value'].sum():.1f}",
                         "" if np.isnan(kl) or col == "crop" else f"{kl:,.0f}"])
    write_plain("v3_groups", ["Group", "Products", r"Share of exports (\%)", r"MNE share (\%)", r"Foreign MNE share (\%)",
                              "Capital per worker (US\\$ thousand)"], rows, colspec="lrrrrr")


# ---------------------------------------------------------------------
# distance
# ---------------------------------------------------------------------
DLAB = {"ln_dist": r"$\ln$ distance", "mne": "MNE", "g_mne_Xd": r"$\ln$ distance $\times$ MNE",
        "pres": "MNE, present at destination", "notpres": "MNE, not present at destination",
        "g_anypres_Xd": r"$\ln$ distance $\times$ MNE, present", "g_anynotpres_Xd": r"$\ln$ distance $\times$ MNE, not present",
        "any_mne_odpy": "At least one MNE in the market", "any_Xd": r"$\ln$ distance $\times$ at least one MNE in the market"}


def firm_panel() -> pd.DataFrame:
    f = E.load_firm_panel()
    f = f[W.sector4(f["hs2"]) == W.SECTOR_OF_SCOPE[SCOPE]].copy()
    f["fid"] = f["country_orig"] + "|" + f["Tax_ID"].astype(str)
    f["fp"] = f["fid"] + "_" + f["hs07_6d"]
    f["fy"] = f["fid"] + "_" + f["year"].astype(str)
    f["fpy"] = f["fy"] + "_" + f["hs07_6d"]
    f["dpy"] = f["country_dest"] + "_" + f["hs07_6d"] + "_" + f["year"].astype(str)
    f["any_mne_odpy"] = f.groupby(["country_orig", "country_dest", "hs07_6d", "year"])["m"].transform("max").astype(float)
    f["any_Xd"] = f["any_mne_odpy"] * f["ln_dist"]
    f["mne"] = f["m"].astype(float)
    f["pres"] = f["g_anypres_Xd"].ne(0).astype(float); f["notpres"] = f["g_anynotpres_Xd"].ne(0).astype(float)
    return f


def distance_tables() -> None:
    f = firm_panel()
    loc = f[f["m"] == 0]
    firm_fe = {"F", "FP", "FY", "FPY"}
    # all firms: column (1) is the earlier specification (no MNE level term); the level enters until a firm FE absorbs it
    sets = [FIRM_SETS[0]] + FIRM_SETS
    lvl_x = ["Not included" if i == 0 else ("Included" if not firm_fe & set(s) else "Absorbed by the firm FE") for i, s in enumerate(sets)]
    PA, PB = "Panel A. All multinationals", "Panel B. Multinationals by presence at the destination"
    res = []
    for i, s in enumerate(sets):
        regs = ["ln_dist", "g_mne_Xd"] + (["mne"] if (i > 0 and not firm_fe & set(s)) else [])
        res.append(fit(f, "ln_exports", regs, s, FE_FIRM, "Distance, all firms", "MNE", f"({i + 1})", "all firm flows",
                       tab="tab:dist", xpanel=PA, xcol=i, shown=f"Panel A, column ({i + 1})", extra={"MNE level term": lvl_x[i]}))
    resp = []
    for i, s in enumerate(sets):
        regs = ["ln_dist", "g_anypres_Xd", "g_anynotpres_Xd"] + (["pres", "notpres"] if (i > 0 and not firm_fe & set(s)) else [])
        resp.append(fit(f, "ln_exports", regs, s, FE_FIRM, "Distance, all firms", "MNE by presence", f"({i + 1})", "all firm flows",
                        tab="tab:dist", xpanel=PB, xcol=i, shown=f"Panel B, column ({i + 1})", extra={"MNE level term": lvl_x[i]}))
    lvl = [("MNE level term included", [("" if i == 0 else ("Yes" if not firm_fe & set(s) else "absorbed")) for i, s in enumerate(sets)])]
    write_table("v3_distance_all", [(PA, res), (PB, resp)], sets, FE_FIRM, DLAB, extra_rows=lvl)
    resl = [fit(loc, "ln_exports", ["ln_dist", "any_mne_odpy", "any_Xd"], s, FE_FIRM, "Distance, local firms", "", f"({i + 1})", "local firm flows",
                tab="tab:dist_local", xpanel="Local firms only", xcol=i, shown=f"Column ({i + 1})")
            for i, s in enumerate(FIRM_SETS)]
    write_table("v3_distance_local", [("", resl)], FIRM_SETS, FE_FIRM, DLAB)


# ---------------------------------------------------------------------
# descriptive tables for 2018 and by country
# ---------------------------------------------------------------------
def descriptives(g: pd.DataFrame) -> None:
    import wp_agro_paper as A
    fd = W.load_fdpy()
    fd = fd[~fd["country_orig"].isin(W.excluded_origins()) & (fd["value_fob"] > 0) & (fd["year"] == 2018)].copy()
    fd["hs2"] = W.hs2_of(fd["hs07_6d"])
    tot_all = fd.groupby("country_orig")["value_fob"].sum()
    a = W.scope_filter(fd, SCOPE).copy()
    a["otype"] = W.owner_type(a).replace({"ext_unknown": "ext"})
    a["fid"] = a["country_orig"] + "|" + a["Tax_ID"]
    a["matched"] = W.matched_flag(a).astype(bool)
    a["dest_real"] = A.real_dest(a["country_dest"], a["country_orig"])
    tv = a.groupby("country_orig")["value_fob"].sum().sort_values(ascending=False)

    # Table: the sample by country (no ownership)
    rows = []
    for o in tv.index:
        s = a[a["country_orig"] == o]
        rows.append([COUNTRY[o], f"{s['fid'].nunique():,}", f"{s['hs07_6d'].nunique():,}", f"{s['dest_real'].nunique():,}",
                     f"{s['value_fob'].sum() / 1e9:,.1f}", f"{100 * s['value_fob'].sum() / tot_all[o]:.1f}"])
    rows.append(["LAC9", f"{a['fid'].nunique():,}", f"{a['hs07_6d'].nunique():,}", f"{a['dest_real'].nunique():,}",
                 f"{a['value_fob'].sum() / 1e9:,.1f}", f"{100 * a['value_fob'].sum() / tot_all.sum():.1f}"])
    write_plain("v3_sample", ["Country", "Exporters", "Products", "Destinations", r"Exports (US\$ billion)", r"Agriculture in total exports (\%)"],
                rows, midrule_before=(len(rows) - 1,))

    # Table: multinationals in agricultural exports (aggregate, 2018)
    ext, dom = a["otype"] == "ext", a["otype"] == "dom"
    V = a["value_fob"].sum()
    fy = a.groupby("fid").agg(v=("value_fob", "sum"), nd=("country_dest", "nunique"), npd=("hs07_6d", "nunique"), ot=("otype", "first"))
    rows = [["Exports (US\\$ billion)", f"{V / 1e9:,.1f}", f"{a.loc[ext, 'value_fob'].sum() / 1e9:,.1f}", f"{a.loc[dom, 'value_fob'].sum() / 1e9:,.1f}", f"{a.loc[a['otype'] == 'local', 'value_fob'].sum() / 1e9:,.1f}"],
            ["Share of exports (\\%)", "100.0", f"{100 * a.loc[ext, 'value_fob'].sum() / V:.1f}", f"{100 * a.loc[dom, 'value_fob'].sum() / V:.1f}", f"{100 * a.loc[a['otype'] == 'local', 'value_fob'].sum() / V:.1f}"],
            ["Exporters", f"{len(fy):,}", f"{(fy['ot'] == 'ext').sum():,}", f"{(fy['ot'] == 'dom').sum():,}", f"{(fy['ot'] == 'local').sum():,}"],
            ["Exports per exporter (US\\$ million)", f"{fy['v'].mean() / 1e6:.1f}"] + [f"{fy.loc[fy['ot'] == t, 'v'].mean() / 1e6:.1f}" for t in ("ext", "dom", "local")],
            ["Destinations per exporter", f"{fy['nd'].mean():.1f}"] + [f"{fy.loc[fy['ot'] == t, 'nd'].mean():.1f}" for t in ("ext", "dom", "local")],
            ["Products per exporter", f"{fy['npd'].mean():.1f}"] + [f"{fy.loc[fy['ot'] == t, 'npd'].mean():.1f}" for t in ("ext", "dom", "local")]]
    write_plain("v3_mne_summary", ["", "All exporters", "Foreign MNEs", "Domestic MNEs", "Local firms"], rows)

    # Table: country facts (2018)
    cube = W.scope_filter(W.mne_flags(W.build_cube()), SCOPE)
    c18 = cube[(cube["year"] == 2018) & (cube["value"] > 0)]
    rows = []
    for o in tv.index:
        s = a[a["country_orig"] == o]; v = s["value_fob"].sum()
        e = c18[(c18["country_orig"] == o) & (c18["owner_type"] == "ext")]
        tp = e.groupby("iso3_parent")["value"].sum().sort_values(ascending=False)
        top_par = f"{tp.index[0]} ({100 * tp.iloc[0] / tp.sum():.0f})" if len(tp) else ""
        dshare = s.groupby("country_dest")["value_fob"].sum().sort_values(ascending=False)
        rows.append([COUNTRY[o], f"{v / 1e9:,.1f}", f"{s['fid'].nunique():,}", f"{s.loc[s['matched'], 'fid'].nunique():,}",
                     top_par, f"{dshare.index[0]} ({100 * dshare.iloc[0] / v:.0f})"])
    write_plain("v3_country_facts", ["Country", r"Exports (US\$ billion)", "Exporters", "MNE affiliates",
                                     r"Main parent country (\%)", r"Main destination (\%)"], rows, colspec="lrrrll")


def country_regressions(g: pd.DataFrame) -> None:
    """Presence regression origin by origin, every fixed-effect set of CTRY_SETS; the note shows destination x product
    and destination x year FE (CTRY_SHOWN), the same comparison as origin x destination x product and origin x
    destination x year FE in the pooled regressions."""
    specs = (("ln_total", "ln_n_mne", "(1)"), ("ln_total", "any_n_mne", "(2)"), ("ln_nonmne", "ln_n_mne", "(3)"), ("ln_nonmne", "any_n_mne", "(4)"))
    rows, order = [], g.groupby("country_orig")["total_value"].sum().sort_values(ascending=False).index
    for o in order:
        s = g[g["country_orig"] == o]
        r = []
        for k, (dep, reg, col) in enumerate(specs):
            for j, S in enumerate(CTRY_SETS):
                rr = fit(s, dep, [reg], S, FE_CTRY, "Presence by country", f"{COUNTRY[o]}", col, "origin " + o, cluster="country_dest",
                         tab="tab:country_reg", xpanel=COUNTRY[o], xcol=(k, j), shown=f"{COUNTRY[o]}, column {col}" if j == CTRY_SHOWN else "")
                if j == CTRY_SHOWN:
                    r.append(rr)
        cells_ = []
        for rr, reg in zip(r, ("ln_n_mne", "any_n_mne", "ln_n_mne", "any_n_mne")):
            cells_.append(f"{rr['cells'][reg][0]:.3f}{stars(rr['cells'][reg][2])}" if reg in rr["cells"] else "")
        ses = [f"({rr['cells'][reg][1]:.3f})" if reg in rr["cells"] else "" for rr, reg in zip(r, ("ln_n_mne", "any_n_mne", "ln_n_mne", "any_n_mne"))]
        rows += [[COUNTRY[o]] + cells_ + [f"{r[1]['n']:,}"], [""] + ses + [""]]
    k = 5
    L = [r"\begin{tabular}{lccccr}", r"\toprule",
         r" & \multicolumn{2}{c}{$\ln$ exports, all firms} & \multicolumn{2}{c}{$\ln$ exports, local firms} & \\",
         r"\cmidrule(lr){2-3}\cmidrule(lr){4-5}",
         r" & $\ln$(number & At least & $\ln$(number & At least & Observations \\",
         r" & of MNEs) & one MNE & of MNEs) & one MNE & (all firms, (2)) \\",
         " & (1) & (2) & (3) & (4) & " + r"\\", r"\midrule"]
    L += [" & ".join(r) + r" \\" for r in rows]
    L += [r"\midrule", r"Destination $\times$ product FE & $\checkmark$ & $\checkmark$ & $\checkmark$ & $\checkmark$ & \\",
          r"Destination $\times$ year FE & $\checkmark$ & $\checkmark$ & $\checkmark$ & $\checkmark$ & \\", r"\bottomrule", r"\end{tabular}"]
    txt = "\n".join(L) + "\n"
    (OUTD / "v3_country_presence.tex").write_text(txt, encoding="utf-8"); (TEXD / "v3_country_presence.tex").write_text(txt, encoding="utf-8")
    LAYOUTS["v3_country_presence"] = pd.DataFrame(rows, columns=["Country", "(1)", "(2)", "(3)", "(4)", "Observations"])


# ---------------------------------------------------------------------
# master workbook, laid out like an outreg2 export
# ---------------------------------------------------------------------
def plain(s: str) -> str:
    """LaTeX label -> plain text for Excel."""
    for a, b in ((r"$\ln$", "ln"), (r"$\times$", "×"), (r"$R^2$", "R-squared"), (r"$p$", "p"), (r"\%", "%"), (r"\$", "$")):
        s = s.replace(a, b)
    return s.replace("$", "")


def note_tables() -> dict[str, tuple[str, str]]:
    """{LaTeX label: (table number, caption)} from the compiled note (.aux) and its source."""
    if not AUX.exists():
        raise SystemExit(f"compile the note first: pdflatex -output-directory={AUX.parent} {NOTE_TEX.name} (twice)")
    aux = AUX.read_text(encoding="utf-8", errors="replace")
    num = dict(re.findall(r"\\newlabel\{(tab:[^}]+)\}\{\{([^}]*)\}", aux))
    tex = NOTE_TEX.read_text(encoding="utf-8")
    cap = {lab: c for c, lab in re.findall(r"\\caption\{(.+?)\}\s*\n\\label\{(tab:[^}]+)\}", tex)}
    return {lab: (num[lab], cap[lab]) for lab in num if lab in cap}


def table_block(tab: str, number: str, title: str) -> tuple[list[list[str]], list[dict]]:
    """Rows of one table in outreg2 style (one column per specification, panels stacked) and its long-format rows."""
    regs = [r for r in REGS if r["tab"] == tab]
    xcols = list(dict.fromkeys(r["xcol"] for r in regs))
    panels = list(dict.fromkeys(r["xpanel"] for r in regs))
    k = len(xcols)
    cell = {(r["xpanel"], r["xcol"]): r for r in regs}
    first = {c: next(r for r in regs if r["xcol"] == c) for c in xcols}
    labels = {**LAB, **DLAB}
    rows = [[f"Table {number}. {plain(title)}"], [""] + [f"({i + 1})" for i in range(k)]]
    long = []
    for P in panels:
        rows.append([plain(P)])
        rr = [cell.get((P, c)) for c in xcols]
        rows.append(["Dependent variable"] + [plain(DEPLAB.get(r["dep"], r["dep"])) if r else "" for r in rr])
        for v in dict.fromkeys(v for r in rr if r for v in r["regs"]):
            b, s = [], []
            for r in rr:
                if r and v in r["cells"]:
                    bb, ss, pp = r["cells"][v]; b.append(f"{bb:.3f}{stars(pp)}"); s.append(f"({ss:.3f})")
                else:
                    b.append(""); s.append("")
            rows += [[plain(labels.get(v, v))] + b, [""] + s]
        for t in dict.fromkeys(t for r in rr if r for t in r["tests"]):
            rows.append([f"p value of the test: {t}"] + [f"{r['tests'][t]:.3f}" if r and t in r["tests"] else "" for r in rr])
        rows.append(["Observations"] + [f"{r['n']:,}" if r and r["n"] else ("not estimated" if r else "") for r in rr])
        rows.append(["R-squared"] + [f"{r['r2']:.3f}" if r and r["n"] else "" for r in rr])
        rows.append(["Within R-squared"] + [f"{r['r2w']:.3f}" if r and r["n"] and not np.isnan(r["r2w"]) else "" for r in rr])
        for e in dict.fromkeys(e for r in rr if r for e in r["extra"]):
            rows.append([e] + [r["extra"].get(e, "") if r else "" for r in rr])
        rows.append(["Column in the note"] + [(r["shown"] or "Not shown") if r else "" for r in rr])
        for i, r in enumerate(rr):
            if not r:
                continue
            base = dict(Table=f"Table {number}", Title=plain(title), Panel=plain(P), Column=f"({i + 1})",
                        **{"Column in the note": r["shown"] or "Not shown"},
                        **{"Dependent variable": plain(DEPLAB.get(r["dep"], r["dep"]))},
                        **{"Fixed effects": " + ".join(plain(r["fe_map"][kk][0]) for kk in r["fe_keys"])},
                        **{"Clustered by": CLUSTER_LAB.get(r["cluster"], r["cluster"]), "Sample": r["sample"],
                           "Observations": r["n"], "R-squared": r["r2"], "Within R-squared": r["r2w"]})
            for v in r["regs"]:
                if v in r["cells"]:
                    bb, ss, pp = r["cells"][v]
                    long.append({**base, "Regressor": plain(labels.get(v, v)), "Coefficient": bb, "Standard error": ss,
                                 "p value": pp, "Stars": stars(pp)})
            for t, pv in r["tests"].items():
                long.append({**base, "Regressor": f"Test: {t}", "Coefficient": np.nan, "Standard error": np.nan,
                             "p value": pv, "Stars": stars(pv)})
    fe_map = first[xcols[0]]["fe_map"]
    for kk in [kk for kk in fe_map if any(kk in first[c]["fe_keys"] for c in xcols)]:
        rows.append([f"{plain(fe_map[kk][0])} FE"] + ["Yes" if kk in first[c]["fe_keys"] else "No" for c in xcols])
    cl = {CLUSTER_LAB.get(r["cluster"], r["cluster"]) for r in regs}
    rows.append([f"Standard errors in parentheses, clustered by {' and '.join(sorted(cl))}. *** p<0.01, ** p<0.05, * p<0.1"])
    return rows, long


def workbook() -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, Side
    from openpyxl.utils import get_column_letter
    meta = note_tables()
    tabs = [t for t in dict.fromkeys(r["tab"] for r in REGS)]
    missing = [t for t in tabs if t not in meta]
    assert not missing, f"tables not found in the compiled note: {missing}"

    def key(t):
        n = meta[t][0]
        return (n.startswith("A"), float(n.split(".")[-1]))
    tabs.sort(key=key)
    blocks, long = {}, []
    for t in tabs:
        rows, lg = table_block(t, *meta[t]); blocks[t] = rows; long += lg

    wb = Workbook()
    thin = Side(style="thin")

    def put(ws, rows, r0):
        """Write one block from row r0; returns the next free row."""
        for i, row in enumerate(rows):
            for j, v in enumerate(row):
                c = ws.cell(row=r0 + i, column=j + 1, value=v)
                if j:
                    c.alignment = Alignment(horizontal="center")
            if i == 0:
                ws.cell(row=r0, column=1).font = Font(bold=True)
        ncol = max(len(r) for r in rows)
        for j in range(1, ncol + 1):                       # rules as in outreg2: above and below the column numbers
            ws.cell(row=r0 + 1, column=j).border = Border(top=thin, bottom=thin)
            ws.cell(row=r0 + len(rows) - 2, column=j).border = Border(bottom=thin)
        return r0 + len(rows)

    def widths(ws, ncol):
        ws.column_dimensions["A"].width = 62
        for j in range(2, ncol + 2):
            ws.column_dimensions[get_column_letter(j)].width = 15

    ws = wb.active; ws.title = "All regressions"
    r = 1
    for t in tabs:
        r = put(ws, blocks[t], r) + 2
    widths(ws, max(len(x) for b in blocks.values() for x in b)); ws.freeze_panes = "B1"
    for t in tabs:
        ws = wb.create_sheet(f"Table {meta[t][0]}")
        put(ws, blocks[t], 1); widths(ws, max(len(x) for x in blocks[t])); ws.freeze_panes = "B3"
    ws = wb.create_sheet("Long format")
    df = pd.DataFrame(long)
    cols = ["Table", "Title", "Panel", "Column", "Column in the note", "Dependent variable", "Regressor", "Coefficient",
            "Standard error", "p value", "Stars", "Observations", "R-squared", "Within R-squared", "Fixed effects", "Clustered by", "Sample"]
    df = df[cols]
    ws.append(cols)
    for row in df.itertuples(index=False):
        ws.append([None if (isinstance(v, float) and np.isnan(v)) else v for v in row])
    for j, w in enumerate([10, 50, 45, 8, 22, 34, 50, 12, 12, 10, 6, 12, 10, 12, 60, 28, 18]):
        ws.column_dimensions[get_column_letter(j + 1)].width = w
    ws.freeze_panes = "A2"
    ws = wb.create_sheet("Notes")
    notes = [
        ["Notes"],
        ["Content", "Every regression of the note, with every fixed effect specification of its progression. Columns marked Not shown in the row Column in the note are estimated for this workbook only."],
        ["Layout", "Sheet All regressions stacks all tables. Each Table sheet has the number and title of the table in the note. One column per specification, panels as in the note, standard errors in parentheses below each coefficient."],
        ["Period and sample", "2012 to 2018, the years in which the nine origins are observed. Agricultural products, HS 2007 chapters 01 to 24."],
        ["Multinationals", "Exporters linked to Orbis or Dun & Bradstreet. Local firms are the exporters that cannot be linked."],
        ["Presence regressions", "One observation per origin, destination, product and year. Intensive margin: ln number of MNEs, observations with at least one MNE. Extensive margin: indicator for at least one MNE, all observations."],
        ["Distance regressions", "One observation per firm, destination, product and year. Distance from the CEPII gravity database."],
        ["By country", "Presence regressions estimated for each exporting country. Within one origin, destination × product FE equal origin × destination × product FE."],
        ["Stars", "*** p<0.01, ** p<0.05, * p<0.1"],
        ["Long format", "One row per coefficient and per test, with the same table and column numbers, for filtering."],
        ["Source", "stylized_facts/python/wp_agro_note_v3.py"],
    ]
    for row in notes:
        ws.append(row)
    ws.column_dimensions["A"].width = 24; ws.column_dimensions["B"].width = 140
    ws["A1"].font = Font(bold=True)
    wb.save(XLSX)
    print(f"workbook: {XLSX} ({len(tabs)} tables, {sum(1 for r in REGS if r['tab'])} regressions, {len(df):,} long rows)")


def main() -> None:
    assert W.YEAR_WINDOW == (2012, 2018), "run with WP_YEARS=2012-2018"
    which = sys.argv[1:] or ["desc", "presence", "hetero", "country", "distance"]
    if which == ["workbook"]:                   # rebuild the workbook from the saved regressions
        with open(PICKLE, "rb") as fh:
            REGS.extend(pickle.load(fh))
        workbook()
        return
    g = cells()
    if "desc" in which:
        descriptives(g); group_table(g)
    if "presence" in which:
        presence_tables(g)
    if "hetero" in which:
        heterogeneity_tables(g)
    if "country" in which:
        country_regressions(g)
    if "distance" in which:
        del g; gc.collect()
        distance_tables()
    with open(PICKLE, "wb") as fh:
        pickle.dump(REGS, fh)
    print(f"saved {len(REGS)} regressions to {PICKLE}")
    if AUX.exists():
        workbook()
    else:
        print(f"no {AUX}: compile the note, then run with the argument workbook")


if __name__ == "__main__":
    main()
