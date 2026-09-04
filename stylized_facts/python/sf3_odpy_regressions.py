"""
sf3_odpy_regressions.py
=======================

ODPY-level regressions for the SF3 appendix. Two tables, each with three
panels (MNE-total / MNE-ext / MNE-dom share) and a three-column ladder of
increasingly saturated fixed effects:

    (1) O, D, Y          origin + destination + year   (additive one-way)
    (2) O x Y, D x Y     origin-year + destination-year
    (3) O x D x Y         origin x destination x year (fully saturated)

    Table 1: independent variables = Product Complexity Index (PCI) +
             upstreamness.
    Table 2: independent variables = technology-category dummies
             (High / Medium / Low tech manufacturing; base = primary and
             resource-based).

Dependent variable: val_<def> / total_value within each ODPY cell.
Weight: total_value (value-weighted). SE: HC1 heteroskedasticity-robust
(not clustered).

Estimation uses **pyfixest** (validated fixed-effects estimator; the project
standard for every Python regression) -- no hand-rolled absorption or SE.
pyfixest drops singleton FE groups, so N can differ across columns; N is
reported per column at the foot of each table (identical across the three
panels, which share the estimation sample).
"""

from __future__ import annotations

import sys
import shutil
import time
import warnings
from pathlib import Path

import pandas as pd
import pyreadstat
import pyfixest as pf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    INT, BASE_FILE, PRODUCT, REGS, OVERLEAF_SF, EXCLUDED_ORIGINS,
    ensure_dir, parquet_chunks,
)

warnings.filterwarnings("ignore", message=".*singleton.*")

R_SF3 = REGS / "SF3_Products"
OL_R_SF3 = OVERLEAF_SF / "Regressions" / "SF3_Products"
for d in (R_SF3, OL_R_SF3):
    ensure_dir(d)

CACHE = INT / "odpy_value_cache.parquet"


# ---------------------------------------------------------------------
# Lall (2000) 4-category recode  (copied verbatim from sf3_products.py)
# ---------------------------------------------------------------------
LALL_4 = {
    "Primary products":                                                "Primary and resource-based",
    "Resource-based manufactures: agro-based":                         "Primary and resource-based",
    "Resource-based manufactures: other":                              "Primary and resource-based",
    "Low technology manufactures: textile, garment and footwear":      "Low tech manufacturing",
    "Low technology manufactures: other products":                     "Low tech manufacturing",
    "Unclassified products":                                           "Low tech manufacturing",
    "Medium technology manufactures: automotive":                      "Medium tech manufacturing",
    "Medium technology manufactures: engineering":                     "Medium tech manufacturing",
    "Medium technology manufactures: process":                         "Medium tech manufacturing",
    "High technology manufactures: electronic and electrical":         "High tech manufacturing",
    "High technology manufactures: other":                             "High tech manufacturing",
}


# ---------------------------------------------------------------------
# Build ODPY cache (one-time)
# ---------------------------------------------------------------------
def build_cache() -> pd.DataFrame:
    raw = BASE_FILE
    print(f">>> Building ODPY cache from {raw}")
    t0 = time.time()
    cols = ["country_orig", "country_dest", "hs07_6d", "year",
            "value_fob", "_merge_DNB_Orbis", "iso3_parent"]
    accum = []
    for i, ch in enumerate(parquet_chunks(raw, cols, 1_000_000), 1):
        ch["value_fob"] = ch["value_fob"].abs()
        mne_total = (ch["_merge_DNB_Orbis"] == 3)
        mne_dom   = mne_total & (ch["iso3_parent"] == ch["country_orig"])
        ch["val_total"] = ch["value_fob"] * mne_total
        ch["val_dom"]   = ch["value_fob"] * mne_dom
        accum.append(ch.groupby(["country_orig","country_dest","hs07_6d","year"],
                                 as_index=False)
                       .agg(total_value=("value_fob","sum"),
                            val_total=("val_total","sum"),
                            val_dom=("val_dom","sum")))
        print(f"    chunk {i}: {time.time()-t0:.0f}s")
    df = (pd.concat(accum)
            .groupby(["country_orig","country_dest","hs07_6d","year"], as_index=False)
            .sum(numeric_only=True))
    df["val_ext"] = df["val_total"] - df["val_dom"]
    print(f"  collapse done, ODPY rows: {len(df):,} ({time.time()-t0:.0f}s)")

    print("  merging product characteristics...")
    pc, _ = pyreadstat.read_dta(str(PRODUCT / "product_characteristics_hs6_2002_adj.dta"),
                                usecols=["hs07_6d","upstreamness","sigma","pci","ladder"])
    pc = pc.rename(columns={"pci":"complexity","ladder":"quality_ladder"})
    df = df.merge(pc, on="hs07_6d", how="left")
    rhci, _ = pyreadstat.read_dta(str(PRODUCT / "UNCTAD RHCI hs_2007_indices.dta"),
                                  usecols=["hs07_6d","rhci"])
    df = df.merge(rhci, on="hs07_6d", how="left")

    df.to_parquet(CACHE, index=False)
    print(f"  saved {CACHE} ({len(df):,} rows, {time.time()-t0:.0f}s total)")
    return df


if CACHE.exists():
    print(f">>> Loading ODPY cache from {CACHE}")
    df = pd.read_parquet(CACHE)
    print(f"   rows: {len(df):,}")
else:
    df = build_cache()


# ---------------------------------------------------------------------
# Merge Lall category (4-bucket) at HS6 and build dummies
# ---------------------------------------------------------------------
ll, _ = pyreadstat.read_dta(str(PRODUCT / "lall2000_hs2007.dta"),
                            usecols=["hs07_6d", "lall2000_category"])
df = df.merge(ll, on="hs07_6d", how="left")
df["lall_4"] = df["lall2000_category"].map(LALL_4)
# Category dummies (Table 2 omits one as the base; see write_panel_table call).
df["lall_high"]    = (df["lall_4"] == "High tech manufacturing").astype(float)
df["lall_med"]     = (df["lall_4"] == "Medium tech manufacturing").astype(float)
df["lall_low"]     = (df["lall_4"] == "Low tech manufacturing").astype(float)
df["lall_primary"] = (df["lall_4"] == "Primary and resource-based").astype(float)


# ---------------------------------------------------------------------
# Filter
# ---------------------------------------------------------------------
df = df[~df["country_orig"].isin(EXCLUDED_ORIGINS)]
df = df[(df["total_value"] > 0)
        & df["country_dest"].notna()
        & df["hs07_6d"].notna()].copy()
df["year"] = df["year"].astype(int)
for k in ["total", "ext", "dom"]:
    df[f"sh_{k}"] = df[f"val_{k}"] / df["total_value"]
print(f">>> Post-filter ODPY rows: {len(df):,}")
print(f"   distinct: O={df['country_orig'].nunique()}  D={df['country_dest'].nunique()}  "
      f"Y={df['year'].nunique()}  HS6={df['hs07_6d'].nunique()}")


# ---------------------------------------------------------------------
# Three-column FE ladder (pyfixest FE syntax; '^' = interacted FE)
# ---------------------------------------------------------------------
SPECS = [
    ("(1)", "country_orig + country_dest + year"),       # O, D, Y
    ("(2)", "country_orig^year + country_dest^year"),    # O x Y, D x Y
    ("(3)", "country_orig^country_dest^year"),           # O x D x Y
]
PANELS = [
    ("total", r"Panel A: $\text{MNE}_{\text{total}}$ share"),
    ("ext",   r"Panel B: $\text{MNE}_{\text{ext}}$ share"),
    ("dom",   r"Panel C: $\text{MNE}_{\text{dom}}$ share"),
]
FE_ROWS = [
    (r"Origin FE",                               [r"$\checkmark$", "", ""]),
    (r"Destination FE",                          [r"$\checkmark$", "", ""]),
    (r"Year FE",                                 [r"$\checkmark$", "", ""]),
    (r"Origin $\times$ year FE",                 ["", r"$\checkmark$", ""]),
    (r"Destination $\times$ year FE",            ["", r"$\checkmark$", ""]),
    (r"Origin $\times$ dest. $\times$ year FE",  ["", "", r"$\checkmark$"]),
]


def stars(p):
    if p < 0.01: return "***"
    if p < 0.05: return "**"
    if p < 0.10: return "*"
    return ""


def fit(dvar: str, xvars: list[str], fe: str):
    """One pyfixest WLS regression (value-weighted), HC1 heteroskedasticity-robust SE."""
    fml = f"{dvar} ~ {' + '.join(xvars)} | {fe}"
    m = pf.feols(fml, data=df, weights="total_value", vcov="hetero")
    b, se, p = m.coef(), m.se(), m.pvalue()
    return {
        "b":  {v: float(b[v])  for v in xvars},
        "se": {v: float(se[v]) for v in xvars},
        "p":  {v: float(p[v])  for v in xvars},
        "n":  int(m._N),
    }


# ---------------------------------------------------------------------
# Panel-table writer
# ---------------------------------------------------------------------
def write_panel_table(fname: str, xvars: list[str],
                      coef_labels: list[tuple[str, str]]):
    ncols = len(SPECS)
    # Estimation sample (N, clusters) is identical across panels for a given
    # column, so run it once per column for the foot; coefficients per panel.
    cells = {}
    n_by_col = []
    for ci, (ctitle, fe) in enumerate(SPECS):
        for di, (def_, _) in enumerate(PANELS):
            res = fit(f"sh_{def_}", xvars, fe)
            cells[(def_, ctitle)] = res
            if di == 0:
                n_by_col.append(res["n"])
        print(f"   {ctitle}  N={n_by_col[-1]:>9,}  "
              + " | ".join(
                  f"{def_}:" + ",".join(
                      f"{cells[(def_,ctitle)]['b'][v]:+.4f}{stars(cells[(def_,ctitle)]['p'][v])}"
                      for v, _ in [(vn, lab) for lab, vn in coef_labels])
                  for def_, _ in PANELS))

    lines = [rf"\begin{{tabular}}{{l{'c'*ncols}}} \hline",
             " & " + " & ".join(t for t, _ in SPECS) + r" \\ \hline"]
    for pi, (def_, ptitle) in enumerate(PANELS):
        if pi > 0:
            lines.append(r"\midrule")
        lines.append(rf"\multicolumn{{{ncols+1}}}{{l}}{{\textit{{{ptitle}}}}} \\")
        for lab, vname in coef_labels:
            row_b  = [f"{cells[(def_, t)]['b'][vname]:.4f}{stars(cells[(def_, t)]['p'][vname])}"
                      for t, _ in SPECS]
            row_se = [f"({cells[(def_, t)]['se'][vname]:.4f})" for t, _ in SPECS]
            lines.append(f"{lab} & " + " & ".join(row_b)  + r" \\")
            lines.append(" & "        + " & ".join(row_se) + r" \\")
    lines.append(r"\hline")
    for lab, vals in FE_ROWS:
        lines.append(f"{lab} & " + " & ".join(vals) + r" \\")
    lines.append("Observations & " + " & ".join(f"{n:,}" for n in n_by_col) + r" \\")
    lines.append(r"\hline")
    lines.append(rf"\multicolumn{{{ncols+1}}}{{c}}{{*** p$<$0.01, ** p$<$0.05, * p$<$0.1}} \\")
    lines.append(r"\end{tabular}")

    out = R_SF3 / f"{fname}.tex"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    shutil.copy2(out, OL_R_SF3 / f"{fname}.tex")
    print(f"   -> {out.name}")


# ---------------------------------------------------------------------
# Table 1: PCI + upstreamness
# ---------------------------------------------------------------------
print("\n>>> Table 1: Product Complexity Index + upstreamness ...")
write_panel_table("reg_sf3_odpy_pci", ["complexity", "upstreamness"],
                  [("Complexity (PCI)", "complexity"),
                   ("Upstreamness", "upstreamness")])

# ---------------------------------------------------------------------
# Table 2: technology-category dummies (base = low tech manufacturing)
# ---------------------------------------------------------------------
print("\n>>> Table 2: technology categories ...")
write_panel_table("reg_sf3_odpy_lall",
                  ["lall_high", "lall_med", "lall_primary"],
                  [("High tech manufacturing",     "lall_high"),
                   ("Medium tech manufacturing",   "lall_med"),
                   ("Primary and resource-based",  "lall_primary")])

print(f"\n>>> Done. Two ODPY panel tables saved to {R_SF3} (and Overleaf mirror).")
