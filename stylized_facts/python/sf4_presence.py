"""
sf5_presence.py
===============

Stylized Fact 4 — higher multinational presence is correlated with higher
trade volumes.

Presence = MNE value share of the market cell (main measure); robustness with
number of MNE firms and an any-MNE indicator. Trade volume = log exports.
Two panels throughout: (A) all exports, (B) NON-MNE exports (the spillover /
placebo cut -- the correlation is not mechanical if it shows up in non-MNE trade).

Cells collapsed from the SF4 FDPY cache (firm x origin x dest x product x year);
MNE = matched in ORBIS/D&B (foreign + domestic). pyfixest; SE clustered as noted.
Fixed effects shown as Yes/No rows above the observation counts.
"""

from __future__ import annotations

import sys
import shutil
import gc
from pathlib import Path

import numpy as np
import pandas as pd
import pyfixest as pf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import INT, REGS, OVERLEAF_SF, ensure_dir

R_SF4 = REGS / "SF4_Presence"
OL_R_SF4 = OVERLEAF_SF / "Regressions" / "SF4_Presence"
for d in (R_SF4, OL_R_SF4):
    ensure_dir(d)


# ---------------------------------------------------------------------
# Load FDPY and collapse to market levels
# ---------------------------------------------------------------------
print(">>> Loading FDPY cache")
fdpy = pd.read_parquet(INT / "sf4_fdpy.parquet")
fdpy["firm"] = fdpy["country_orig"].astype(str) + "_" + fdpy["Tax_ID"].astype(str)
fdpy["mne"] = (fdpy["matched"] == 1)
fdpy["mne_value"] = np.where(fdpy["mne"], fdpy["value"].astype(float), 0.0)
print(f"   rows: {len(fdpy):,}")


def collapse(keys: list[str]) -> pd.DataFrame:
    base = fdpy.groupby(keys, as_index=False).agg(
        total_value=("value", "sum"),
        mne_value=("mne_value", "sum"),
        n_firms=("firm", "nunique"))
    nm = fdpy[fdpy["mne"]].groupby(keys, as_index=False).agg(n_mne=("firm", "nunique"))
    g = base.merge(nm, on=keys, how="left")
    g["n_mne"] = g["n_mne"].fillna(0).astype(float)
    g = g[g["total_value"] > 0].copy()
    g["nonmne_value"]    = (g["total_value"] - g["mne_value"]).clip(lower=0)
    g["mne_value_share"] = g["mne_value"] / g["total_value"]
    g["any_mne"]   = (g["n_mne"] > 0).astype(float)
    g["ln_total"]  = np.log(g["total_value"])
    g["ln_nonmne"] = np.where(g["nonmne_value"] > 0, np.log(g["nonmne_value"].clip(lower=1)), np.nan)
    g["ln_nmne"]   = np.where(g["n_mne"] > 0, np.log(g["n_mne"].clip(lower=1)), np.nan)
    g["year"] = g["year"].astype(int)
    return g


ODPY_C, ODY_C, OPY_C = INT / "sf5_odpy.parquet", INT / "sf5_ody.parquet", INT / "sf5_opy.parquet"
if ODPY_C.exists() and ODY_C.exists() and OPY_C.exists():
    print(">>> Loading collapse caches")
    odpy = pd.read_parquet(ODPY_C); ody = pd.read_parquet(ODY_C); opy = pd.read_parquet(OPY_C)
else:
    print(">>> Collapsing to ODPY / ODY / OPY ...")
    odpy = collapse(["country_orig", "country_dest", "hs07_6d", "year"])
    ody  = collapse(["country_orig", "country_dest", "year"])
    opy  = collapse(["country_orig", "hs07_6d", "year"])
    for d in (odpy, ody, opy):
        d["ot"] = d["country_orig"] + "_" + d["year"].astype(str)
    for d in (odpy, ody):
        d["dt"] = d["country_dest"] + "_" + d["year"].astype(str)
        d["od"] = d["country_orig"] + "_" + d["country_dest"]
    for d in (opy,):
        d["pt"] = d["hs07_6d"] + "_" + d["year"].astype(str)
        d["op"] = d["country_orig"] + "_" + d["hs07_6d"]
    odpy["odp"]    = odpy["country_orig"] + "_" + odpy["country_dest"] + "_" + odpy["hs07_6d"]
    odpy["ody_fe"] = odpy["country_orig"] + "_" + odpy["country_dest"] + "_" + odpy["year"].astype(str)
    odpy.to_parquet(ODPY_C); ody.to_parquet(ODY_C); opy.to_parquet(OPY_C)
for nm, d in [("ODPY", odpy), ("ODY", ody), ("OPY", opy)]:
    print(f"   {nm}: {len(d):,} cells | any MNE {d['any_mne'].mean():.0%}")


def stars(p):
    if p < 0.01: return "***"
    if p < 0.05: return "**"
    if p < 0.10: return "*"
    return ""


# Fixed-effect components: key -> (row label, formula term)
FE_COMPONENTS = {
    "O":   ("Origin FE",                                  "country_orig"),
    "D":   ("Destination FE",                             "country_dest"),
    "P":   ("Product FE",                                 "hs07_6d"),
    "Y":   ("Year FE",                                    "year"),
    "OY":  ("Origin $\\times$ year FE",                   "ot"),
    "DY":  ("Destination $\\times$ year FE",              "dt"),
    "PY":  ("Product $\\times$ year FE",                  "pt"),
    "ODP": ("Origin $\\times$ dest. $\\times$ product FE", "odp"),
    "ODY": ("Origin $\\times$ dest. $\\times$ year FE",    "ody_fe"),
}
FE_ORDER = ["O", "D", "P", "Y", "OY", "DY", "PY", "ODP", "ODY"]


def run_panel_table(df, columns, panels, coef_rows, cluster, fname, note, col_groups=None):
    """columns: (tag, [fe_keys], [regressors]). panels: (panel_label, dep_var).
    coef_rows: (row_label, varname). FE shown as Yes/No rows above Observations.
    col_groups: optional [(label, span), ...] header row spanning column groups."""
    print(f"\n>>> {fname} ...")
    res = {}
    for pi, (plab, dep) in enumerate(panels):
        for ci, (tag, fe_keys, regs) in enumerate(columns):
            fe = " + ".join(FE_COMPONENTS[k][1] for k in fe_keys)
            d = df.dropna(subset=[dep] + regs)
            m = pf.feols(f"{dep} ~ {' + '.join(regs)}" + (f" | {fe}" if fe else ""),
                         data=d, vcov={"CRV1": cluster})
            b, se, p = m.coef(), m.se(), m.pvalue()
            res[(pi, ci)] = {"cells": {v: (float(b[v]), float(se[v]), float(p[v]))
                                       for v in regs if v in b.index}, "n": int(m._N)}
            print(f"   {plab[:7]:7s} {tag} N={int(m._N):>9,}  "
                  + "  ".join(f"{v}:{float(b[v]):+.3f}{stars(float(p[v]))}" for v in regs if v in b.index))
            del m, b, se, p; gc.collect()
    ncols = len(columns)
    fe_set = set()
    for tag, fe_keys, regs in columns:
        fe_set.update(fe_keys)
    fe_used = [k for k in FE_ORDER if k in fe_set]

    lines = [rf"\begin{{tabular}}{{l{'c'*ncols}}} \hline"]
    if col_groups:
        lines.append(" & " + " & ".join(rf"\multicolumn{{{n}}}{{c}}{{{lab}}}" for lab, n in col_groups) + r" \\")
    lines.append(" & " + " & ".join(c[0] for c in columns) + r" \\ \hline")
    for pi, (plab, dep) in enumerate(panels):
        if pi > 0:
            lines.append(r"\midrule")
        lines.append(rf"\multicolumn{{{ncols+1}}}{{l}}{{\textit{{{plab}}}}} \\")
        for rlab, v in coef_rows:
            if not any(v in res[(pi, ci)]["cells"] for ci in range(ncols)):
                continue
            rb, rse = [], []
            for ci in range(ncols):
                if v in res[(pi, ci)]["cells"]:
                    bb, ss, pp = res[(pi, ci)]["cells"][v]
                    rb.append(f"{bb:.4f}{stars(pp)}"); rse.append(f"({ss:.4f})")
                else:
                    rb.append(""); rse.append("")
            lines.append(f"{rlab} & " + " & ".join(rb) + r" \\")
            lines.append(" & " + " & ".join(rse) + r" \\")
    lines.append(r"\hline")
    for k in fe_used:
        vals = [r"$\checkmark$" if k in columns[ci][1] else "" for ci in range(ncols)]
        lines.append(f"{FE_COMPONENTS[k][0]} & " + " & ".join(vals) + r" \\")
    for pi, (plab, dep) in enumerate(panels):
        short = plab.split(":")[1].split("(")[0].strip() if ":" in plab else plab
        lines.append(f"Observations ({short}) & "
                     + " & ".join(f"{res[(pi, ci)]['n']:,}" for ci in range(ncols)) + r" \\")
    lines.append(r"\hline")
    lines.append(rf"\multicolumn{{{ncols+1}}}{{p{{0.9\textwidth}}}}{{\footnotesize {note} "
                 r"SE clustered as noted. *** p$<$0.01, ** p$<$0.05, * p$<$0.1}} \\")
    lines.append(r"\end{tabular}")
    out = R_SF4 / f"{fname}.tex"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    shutil.copy2(out, OL_R_SF4 / f"{fname}.tex")
    print(f"   -> {out.name}")


PANELS = [("Panel A: all exports ($\\ln$)", "ln_total"),
          ("Panel B: non-MNE exports ($\\ln$)", "ln_nonmne")]
SHARE = [("MNE value share", "mne_value_share")]

# 1. MAIN -- ODPY: intensive (ln # MNE firms) + extensive (any MNE) margins
run_panel_table(odpy,
    [("(1)", ["O", "D", "Y", "P"], ["ln_nmne"]),
     ("(2)", ["OY", "DY", "P"],    ["ln_nmne"]),
     ("(3)", ["ODP", "ODY"],       ["ln_nmne"]),
     ("(1)", ["O", "D", "Y", "P"], ["any_mne"]),
     ("(2)", ["OY", "DY", "P"],    ["any_mne"]),
     ("(3)", ["ODP", "ODY"],       ["any_mne"])],
    PANELS,
    [("$\\ln$(\\# MNE firms)", "ln_nmne"), ("Any MNE present", "any_mne")],
    "od", "reg_sf4_main",
    "Origin-destination-product-year cells; dep.\\ var.\\ $\\ln$ exports. Intensive "
    "margin: $\\ln$ number of MNE firms (cells with $\\ge 1$ MNE); extensive margin: "
    "indicator for any MNE present. Cluster OD.",
    col_groups=[("Intensive: $\\ln$(\\# MNE firms)", 3), ("Extensive: any MNE present", 3)])

# 2. APPENDIX -- MNE value share, all-exports panel only (share is mechanically
#    tied to the non-MNE complement, so Panel B is omitted)
run_panel_table(odpy,
    [("(1)", ["O", "D", "Y", "P"], ["mne_value_share"]),
     ("(2)", ["OY", "DY", "P"],    ["mne_value_share"]),
     ("(3)", ["ODP", "ODY"],       ["mne_value_share"])],
    [PANELS[0]], SHARE, "od", "reg_sf4_shares",
    "Origin-destination-product-year cells; dep.\\ var.\\ $\\ln$ all exports; "
    "presence $=$ MNE value share; cluster OD.")

print("\n>>> SF4: main (intensive+extensive) + shares appendix written.")
