"""
sf6_concentration.py
====================

Stylized Fact 6 — concentration patterns: where multinationals are present,
trade is more concentrated (top firms account for a larger share) and served
by fewer exporters.

Market unit: MAIN = origin x product x year (OPY, product markets); ROBUSTNESS
= origin x destination x year (ODY, destination markets). ODPY is too granular
(<=5 firms/cell -> top-5 share ~ 1), so it is not used.

Outcomes: top-5 firm value share, top-1 share, HHI (concentration); ln(# exporters).
Presence measures: any-MNE (extensive), ln(# MNE firms) (intensive), MNE value
share. pyfixest; cluster at the bilateral/product pair; FE as Yes/No rows.
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

R_SF6 = REGS / "SF6_Concentration"
OL_R_SF6 = OVERLEAF_SF / "Regressions" / "SF6_Concentration"
for d in (R_SF6, OL_R_SF6):
    ensure_dir(d)


def compute_conc(keys: list[str]) -> pd.DataFrame:
    """Per cell: total value, n firms, HHI, top-1/top-5 share, MNE measures.
    Firm value within a cell is summed across the collapsed dimension."""
    fv = fdpy.groupby(keys + ["firm"], as_index=False).agg(
        fval=("value", "sum"), mne=("mne", "max"))
    fv["total"] = fv.groupby(keys)["fval"].transform("sum")
    fv["sh2"] = (fv["fval"] / fv["total"]) ** 2
    fv = fv.sort_values(keys + ["fval"], ascending=[True] * len(keys) + [False])
    fv["rk"] = fv.groupby(keys).cumcount()
    g = fv.groupby(keys, as_index=False).agg(
        total_value=("fval", "sum"), n_firms=("firm", "size"),
        hhi=("sh2", "sum"), n_mne=("mne", "sum"))
    mv = fv[fv["mne"]].groupby(keys, as_index=False).agg(mne_value=("fval", "sum"))
    t1 = fv[fv["rk"] == 0].groupby(keys, as_index=False).agg(t1=("fval", "sum"))
    t5 = fv[fv["rk"] < 5].groupby(keys, as_index=False).agg(t5=("fval", "sum"))
    g = g.merge(mv, on=keys, how="left").merge(t1, on=keys, how="left").merge(t5, on=keys, how="left")
    g["mne_value"] = g["mne_value"].fillna(0.0)
    g["n_mne"] = g["n_mne"].fillna(0).astype(float)
    g["top1_share"] = (g["t1"] / g["total_value"]).clip(upper=1.0)
    g["top5_share"] = (g["t5"] / g["total_value"]).clip(upper=1.0)
    g["mne_value_share"] = g["mne_value"] / g["total_value"]
    g["any_mne"] = (g["n_mne"] > 0).astype(float)
    g["ln_nfirms"] = np.log(g["n_firms"])
    g["ln_nmne"] = np.where(g["n_mne"] > 0, np.log(g["n_mne"].clip(lower=1)), np.nan)
    g["year"] = g["year"].astype(int)
    return g


print(">>> Loading FDPY cache")
fdpy = pd.read_parquet(INT / "sf4_fdpy.parquet")
fdpy["firm"] = fdpy["country_orig"].astype(str) + "_" + fdpy["Tax_ID"].astype(str)
fdpy["mne"] = (fdpy["matched"] == 1)

OPY_C, ODY_C = INT / "sf6_opy.parquet", INT / "sf6_ody.parquet"
if OPY_C.exists() and ODY_C.exists():
    print(">>> Loading concentration caches")
    opy = pd.read_parquet(OPY_C); ody = pd.read_parquet(ODY_C)
else:
    print(">>> Computing OPY / ODY concentration ...")
    opy = compute_conc(["country_orig", "hs07_6d", "year"])
    ody = compute_conc(["country_orig", "country_dest", "year"])
    opy["ot"] = opy["country_orig"] + "_" + opy["year"].astype(str)
    opy["pt"] = opy["hs07_6d"] + "_" + opy["year"].astype(str)
    opy["op"] = opy["country_orig"] + "_" + opy["hs07_6d"]
    ody["ot"] = ody["country_orig"] + "_" + ody["year"].astype(str)
    ody["dt"] = ody["country_dest"] + "_" + ody["year"].astype(str)
    ody["od"] = ody["country_orig"] + "_" + ody["country_dest"]
    opy.to_parquet(OPY_C); ody.to_parquet(ODY_C)
for nm, d in [("OPY", opy), ("ODY", ody)]:
    print(f"   {nm}: {len(d):,} cells | mean #firms {d['n_firms'].mean():.0f} | "
          f"mean top5 {d['top5_share'].mean():.2f} | mean HHI {d['hhi'].mean():.2f} | any MNE {d['any_mne'].mean():.0%}")


def stars(p):
    if p < 0.01: return "***"
    if p < 0.05: return "**"
    if p < 0.10: return "*"
    return ""


FE_COMPONENTS = {
    "O":  ("Origin FE",                      "country_orig"),
    "D":  ("Destination FE",                 "country_dest"),
    "P":  ("Product FE",                     "hs07_6d"),
    "Y":  ("Year FE",                        "year"),
    "OY": ("Origin $\\times$ year FE",       "ot"),
    "DY": ("Destination $\\times$ year FE",  "dt"),
    "PY": ("Product $\\times$ year FE",      "pt"),
    "OP": ("Origin $\\times$ product FE",    "op"),
    "OD": ("Origin $\\times$ destination FE", "od"),
}
FE_ORDER = ["O", "D", "P", "Y", "OY", "DY", "PY", "OP", "OD"]


def run_panel_table(df, columns, panels, coef_rows, cluster, fname, note, col_groups=None):
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
            print(f"   {plab[:9]:9s} {tag} N={int(m._N):>8,}  "
                  + "  ".join(f"{v}:{float(b[v]):+.4f}{stars(float(p[v]))}" for v in regs if v in b.index))
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
        lines.append(f"{FE_COMPONENTS[k][0]} & "
                     + " & ".join("Yes" if k in columns[ci][1] else "No" for ci in range(ncols)) + r" \\")
    for pi, (plab, dep) in enumerate(panels):
        short = plab.split(":")[1].split("(")[0].strip() if ":" in plab else plab
        lines.append(f"Observations ({short}) & "
                     + " & ".join(f"{res[(pi, ci)]['n']:,}" for ci in range(ncols)) + r" \\")
    lines.append(r"\hline")
    lines.append(rf"\multicolumn{{{ncols+1}}}{{p{{0.9\textwidth}}}}{{\footnotesize {note} "
                 r"SE clustered as noted. *** p$<$0.01, ** p$<$0.05, * p$<$0.1}} \\")
    lines.append(r"\end{tabular}")
    out = R_SF6 / f"{fname}.tex"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    shutil.copy2(out, OL_R_SF6 / f"{fname}.tex")
    print(f"   -> {out.name}")


def cols(fe3, measure):
    return [(t, fk, [measure]) for t, fk in fe3]


OPY_FE = [("(1)", ["O", "P", "Y"]), ("(2)", ["OY", "PY"]), ("(3)", ["OP", "Y"])]
ODY_FE = [("(1)", ["O", "D", "Y"]), ("(2)", ["OY", "DY"]), ("(3)", ["OD", "Y"])]
CONC_FIRMS = [("Panel A: top-5 firm share", "top5_share"), ("Panel B: $\\ln$(\\# exporters)", "ln_nfirms")]
EXT_INT_GROUPS = [("Extensive: any MNE", 3), ("Intensive: $\\ln$(\\# MNE firms)", 3)]

# --- MAIN: OPY, extensive + intensive, top-5 share + # exporters ---
run_panel_table(opy,
    cols(OPY_FE, "any_mne") + cols(OPY_FE, "ln_nmne"), CONC_FIRMS,
    [("Any MNE present", "any_mne"), ("$\\ln$(\\# MNE firms)", "ln_nmne")],
    "op", "reg_sf6_main",
    "Origin-product-year markets; cluster origin$\\times$product. Panel~A: top-5 firm "
    "value share; Panel~B: $\\ln$ number of exporters.",
    col_groups=EXT_INT_GROUPS)

# --- OPY, MNE value share ---
run_panel_table(opy, cols(OPY_FE, "mne_value_share"), CONC_FIRMS,
    [("MNE value share", "mne_value_share")], "op", "reg_sf6_share",
    "Origin-product-year markets; cluster origin$\\times$product; presence $=$ MNE value share.")

# --- OPY, alternative concentration measures ---
run_panel_table(opy, cols(OPY_FE, "any_mne"),
    [("Panel A: top-1 firm share", "top1_share"), ("Panel B: HHI", "hhi")],
    [("Any MNE present", "any_mne")], "op", "reg_sf6_measures",
    "Origin-product-year markets; cluster origin$\\times$product. Alternative concentration "
    "outcomes (top-1 firm share; Herfindahl index).")

# --- ROBUSTNESS: ODY (destination markets) ---
run_panel_table(ody,
    cols(ODY_FE, "any_mne") + cols(ODY_FE, "ln_nmne"), CONC_FIRMS,
    [("Any MNE present", "any_mne"), ("$\\ln$(\\# MNE firms)", "ln_nmne")],
    "od", "reg_sf6_ody",
    "Origin-destination-year markets; cluster OD. Panel~A: top-5 firm value share; "
    "Panel~B: $\\ln$ number of exporters.",
    col_groups=EXT_INT_GROUPS)

run_panel_table(ody, cols(ODY_FE, "mne_value_share"), CONC_FIRMS,
    [("MNE value share", "mne_value_share")], "od", "reg_sf6_ody_share",
    "Origin-destination-year markets; cluster OD; presence $=$ MNE value share.")

print("\n>>> SF6: OPY main + alternatives + ODY robustness written.")
