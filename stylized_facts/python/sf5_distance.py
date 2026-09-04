"""
sf4_distance.py
===============

Stylized Fact 5 — distance elasticity of exports by multinational status and
destination network presence. Firm-level FDPY (firm x origin x destination x
product x year), following Sebastian's 30_part2_effects.do network decomposition.

Full-interaction progression, one table, four increasingly granular columns
(each group gets its OWN distance slope; non-MNE is a group, not an omitted base;
level main effects are included):
    (1) MNE              vs non-MNE
    (2) foreign / domestic MNE                 vs non-MNE
    (3) MNE present / not-present / domestic    vs non-MNE        (D1)
    (4) MNE HQ / affiliate / not-present / dom  vs non-MNE        (D2)

Dependent variable: ln_exports = ln(value_fob) at the firm-dest-product-year cell.
Fixed effects: OxYear + DxYear + Product (HS6). SE clustered at origin-destination.
Estimated with pyfixest. Definitions mirror 10_part0_build.do.
"""

from __future__ import annotations

import sys
import shutil
import time
import gc
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat
import pyfixest as pf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    INT, BASE_FILE, MNE_PRESENCE_FILE, GRAVITY, REGS, OVERLEAF_SF,
    EXCLUDED_ORIGINS, ensure_dir, parquet_chunks,
)

R_SF5 = REGS / "SF5_Distance"
OL_R_SF5 = OVERLEAF_SF / "Regressions" / "SF5_Distance"
for d in (R_SF5, OL_R_SF5):
    ensure_dir(d)

FDPY_CACHE = INT / "sf4_fdpy.parquet"
AFF_CACHE = INT / "sf4_aff_pairs_matched.parquet"   # affiliate pairs for foreign + domestic MNE IDs
RAW = BASE_FILE
MNE_PRESENCE = MNE_PRESENCE_FILE


# ---------------------------------------------------------------------
# Step 1: build firm x orig x dest x product x year (FDPY) from raw
# ---------------------------------------------------------------------
def build_fdpy() -> pd.DataFrame:
    print(f">>> Building FDPY from {RAW}")
    t0 = time.time()
    cols = ["country_orig", "country_dest", "hs07_6d", "year", "value_fob",
            "Tax_ID", "_merge_DNB_Orbis", "iso3_parent", "guo25",
            "dunsnumber", "_merge_DNB"]
    keys = ["country_orig", "Tax_ID", "country_dest", "hs07_6d", "year"]
    parts = []
    for i, ch in enumerate(parquet_chunks(RAW, cols, 1_000_000), 1):
        ch = ch[~ch["country_orig"].isin(EXCLUDED_ORIGINS)].copy()
        ch = ch[ch["country_dest"].notna() & ch["Tax_ID"].notna() & ch["hs07_6d"].notna()]
        ch["value_fob"] = ch["value_fob"].abs()
        ch = ch[ch["value_fob"] > 0]
        ch["matched"] = (ch["_merge_DNB_Orbis"] == 3).astype("int8")
        ch["parent"] = ch["iso3_parent"].astype("string").str.strip()
        idv = ch["guo25"].astype("string").str.strip()
        duns = ch["dunsnumber"].astype("string").str.strip()
        idv = idv.where(ch["_merge_DNB"] != 2, duns)
        ch["ID_Orbis_DNB"] = idv.replace({"": pd.NA})
        g = (ch.groupby(keys, as_index=False, dropna=False)
               .agg(value=("value_fob", "sum"), matched=("matched", "max"),
                    parent=("parent", "first"), ID_Orbis_DNB=("ID_Orbis_DNB", "first")))
        parts.append(g)
        print(f"    chunk {i}: {time.time()-t0:.0f}s")

    fdpy = (pd.concat(parts, ignore_index=True)
              .groupby(keys, as_index=False, dropna=False)
              .agg(value=("value", "sum"), matched=("matched", "max"),
                   parent=("parent", "first"), ID_Orbis_DNB=("ID_Orbis_DNB", "first")))
    firm = (fdpy.groupby(["country_orig", "Tax_ID"], as_index=False, dropna=False)
                .agg(f_matched=("matched", "max"), f_parent=("parent", "first"),
                     f_ID=("ID_Orbis_DNB", "first")))
    fdpy = fdpy.merge(firm, on=["country_orig", "Tax_ID"], how="left")
    fdpy["matched"] = fdpy["f_matched"]; fdpy["parent"] = fdpy["f_parent"]
    fdpy["ID_Orbis_DNB"] = fdpy["f_ID"]
    fdpy = fdpy.drop(columns=["f_matched", "f_parent", "f_ID"])
    fdpy.to_parquet(FDPY_CACHE, index=False)
    print(f"  FDPY rows: {len(fdpy):,} ({time.time()-t0:.0f}s)")
    return fdpy


if FDPY_CACHE.exists():
    print(f">>> Loading FDPY cache {FDPY_CACHE}")
    fdpy = pd.read_parquet(FDPY_CACHE)
    print(f"   rows: {len(fdpy):,}")
else:
    fdpy = build_fdpy()


# ---------------------------------------------------------------------
# Step 2: MNE / DOM / HQ presence
# ---------------------------------------------------------------------
fdpy["MNE"] = ((fdpy["matched"] == 1) & (fdpy["parent"] != fdpy["country_orig"])).astype("int8")
fdpy["DOM"] = ((fdpy["matched"] == 1) & (fdpy["parent"] == fdpy["country_orig"])).astype("int8")
fdpy["MNE_HQ_dest"] = ((fdpy["MNE"] == 1) & (fdpy["parent"] == fdpy["country_dest"])).astype("int8")


# ---------------------------------------------------------------------
# Step 3: affiliate presence (cached pairs)
# ---------------------------------------------------------------------
if AFF_CACHE.exists():
    print(f">>> Loading affiliate-pairs cache {AFF_CACHE}")
    _ap = pd.read_parquet(AFF_CACHE)
    aff_pairs = set(zip(_ap["ID_Orbis_DNB"].tolist(), _ap["country_dest"].tolist()))
else:
    need_ids = set(fdpy.loc[(fdpy["matched"] == 1) & fdpy["ID_Orbis_DNB"].notna(), "ID_Orbis_DNB"].unique())
    print(f">>> Scanning affiliate presence for {len(need_ids):,} matched (foreign+domestic) IDs ...")
    aff_pairs = set()
    t0 = time.time()
    for i, ch in enumerate(parquet_chunks(
            MNE_PRESENCE,
            ["ID_Orbis_DNB", "country_dest", "company_has_aff_in_dest"],
            5_000_000), 1):
        ch = ch[ch["company_has_aff_in_dest"] == 1]
        ids = ch["ID_Orbis_DNB"].astype("string").str.strip()
        keep = ids.isin(need_ids)
        aff_pairs.update(zip(ids[keep].tolist(),
                             ch.loc[keep, "country_dest"].astype("string").str.strip().tolist()))
        print(f"    chunk {i}: {time.time()-t0:.0f}s  (aff pairs: {len(aff_pairs):,})")
    pd.DataFrame(list(aff_pairs), columns=["ID_Orbis_DNB", "country_dest"]).to_parquet(AFF_CACHE, index=False)

key = list(zip(fdpy["ID_Orbis_DNB"].astype("string").str.strip().tolist(),
               fdpy["country_dest"].astype("string").str.strip().tolist()))
in_aff = np.fromiter((k in aff_pairs for k in key), bool, len(fdpy))
fdpy["MNE_aff_dest"] = (((fdpy["MNE"] == 1).to_numpy()) & in_aff).astype("int8")
fdpy["DOM_aff_dest"] = (((fdpy["DOM"] == 1).to_numpy()) & in_aff).astype("int8")  # domestic: affiliate only (no HQ-in-dest)
fdpy["MNE_present_dest"]    = ((fdpy["MNE_HQ_dest"] == 1) | (fdpy["MNE_aff_dest"] == 1)).astype("int8")
fdpy["MNE_notpresent_dest"] = ((fdpy["MNE"] == 1) & (fdpy["MNE_present_dest"] == 0)).astype("int8")


# ---------------------------------------------------------------------
# Step 4: distance + logs
# ---------------------------------------------------------------------
grav, _ = pyreadstat.read_dta(str(GRAVITY / "Gravity_V202211.dta"),
                              usecols=["iso3_o", "iso3_d", "dist"])
grav = (grav.dropna(subset=["dist"]).groupby(["iso3_o", "iso3_d"], as_index=False)
            .agg(dist=("dist", "first")))
fdpy = fdpy.merge(grav, left_on=["country_orig", "country_dest"],
                  right_on=["iso3_o", "iso3_d"], how="left")
fdpy["dist"] = pd.to_numeric(fdpy["dist"], errors="coerce")
fdpy["value"] = pd.to_numeric(fdpy["value"], errors="coerce")
fdpy = fdpy[fdpy["dist"].notna() & (fdpy["dist"] > 0) & (fdpy["value"] > 0)].copy()
fdpy["ln_dist"] = np.log(fdpy["dist"].astype(float))
fdpy["ln_exports"] = np.log(fdpy["value"].astype(float))
fdpy["ot"] = fdpy["country_orig"] + "_" + fdpy["year"].astype(int).astype(str)
fdpy["dt"] = fdpy["country_dest"] + "_" + fdpy["year"].astype(int).astype(str)
fdpy["od"] = fdpy["country_orig"] + "_" + fdpy["country_dest"]


# ---------------------------------------------------------------------
# Step 5: mutually exclusive group indicators (each partitions all flows)
# ---------------------------------------------------------------------
fdpy["g_nonmne"]  = (fdpy["matched"] == 0).astype(float)
fdpy["g_mne"]     = (fdpy["matched"] == 1).astype(float)                     # foreign + domestic
fdpy["g_ext"]     = (fdpy["MNE"] == 1).astype(float)                         # foreign
fdpy["g_dom"]     = (fdpy["DOM"] == 1).astype(float)                         # domestic
fdpy["g_pres"]    = (fdpy["MNE_present_dest"] == 1).astype(float)            # foreign, present
fdpy["g_notpres"] = (fdpy["MNE_notpresent_dest"] == 1).astype(float)        # foreign, not present
fdpy["g_hq"]      = ((fdpy["MNE"] == 1) & (fdpy["MNE_HQ_dest"] == 1)).astype(float)
fdpy["g_aff"]     = ((fdpy["MNE"] == 1) & (fdpy["MNE_aff_dest"] == 1)
                     & (fdpy["MNE_HQ_dest"] == 0)).astype(float)            # affiliate, not HQ
fdpy["g_dom_pres"]    = ((fdpy["DOM"] == 1) & (fdpy["DOM_aff_dest"] == 1)).astype(float)   # domestic, affiliate in dest
fdpy["g_dom_notpres"] = ((fdpy["DOM"] == 1) & (fdpy["DOM_aff_dest"] == 0)).astype(float)
# Any MNE (foreign or domestic) by presence at destination -- for the main table
fdpy["g_anypres"]     = ((fdpy["g_pres"] == 1) | (fdpy["g_dom_pres"] == 1)).astype(float)
fdpy["g_anynotpres"]  = ((fdpy["g_notpres"] == 1) | (fdpy["g_dom_notpres"] == 1)).astype(float)

GLAB = {
    "g_mne":          "MNE",
    "g_anypres":      "MNE, present",
    "g_anynotpres":   "MNE, not present",
    "g_ext":          "foreign MNE",
    "g_dom":          "domestic MNE",
    "g_pres":         "foreign MNE, present",
    "g_notpres":      "foreign MNE, not present",
    "g_dom_pres":     "domestic MNE, present",
    "g_dom_notpres":  "domestic MNE, not present",
    "g_hq":           "foreign MNE, present (HQ)",
    "g_aff":          "foreign MNE, present (affiliate)",
}

# Pre-build group x ln_dist columns (differentials vs the non-MNE base)
for g in GLAB:
    fdpy[g + "_Xd"] = fdpy[g] * fdpy["ln_dist"]

FE_SPECS = {
    "ODYP":  ("O + D + Yr + P",  "country_orig + country_dest + year + hs07_6d"),
    "OYDYP": ("OxYr + DxYr + P", "ot + dt + hs07_6d"),
}
# which individual FE each spec contains, for the FE-as-rows panel (ticks)
FE_ROWS = {
    "ODYP":  {"Origin FE", "Destination FE", "Year FE", "Product FE"},
    "OYDYP": {r"Origin $\times$ year FE", r"Destination $\times$ year FE", "Product FE"},
}
FE_ORDER = ["Origin FE", "Destination FE", "Year FE",
            r"Origin $\times$ year FE", r"Destination $\times$ year FE", "Product FE"]


def stars(p):
    if p < 0.01: return "***"
    if p < 0.05: return "**"
    if p < 0.10: return "*"
    return ""


def run_table(columns, row_order, fname, note):
    """Each column: (tag, fe_key, [group_keys]). Regress ln_exports on
    ln_dist + group x ln_dist differentials (non-MNE the omitted base, no level
    dummies) at the column's FE. Writes a fragment over the union of rows."""
    print(f"\n>>> {fname} ...")
    cols = []
    for tag, fe_key, groups in columns:
        fe_lbl, fe = FE_SPECS[fe_key]
        fml = f"ln_exports ~ ln_dist + {' + '.join(g + '_Xd' for g in groups)} | {fe}"
        t0 = time.time()
        m = pf.feols(fml, data=fdpy, vcov={"CRV1": "od"})
        b, se, p = m.coef(), m.se(), m.pvalue()
        cells = {g: (float(b[g + "_Xd"]), float(se[g + "_Xd"]), float(p[g + "_Xd"])) for g in groups}
        cells["ln_dist"] = (float(b["ln_dist"]), float(se["ln_dist"]), float(p["ln_dist"]))
        cols.append({"tag": tag, "fe_lbl": fe_lbl, "fe_key": fe_key,
                     "rows": set(groups) | {"ln_dist"}, "cells": cells, "n": int(m._N)})
        print(f"   {tag} {fe_lbl:14s} N={int(m._N):>9,}  base:{cells['ln_dist'][0]:+.4f}{stars(cells['ln_dist'][2])}  "
              + "  ".join(f"{GLAB[g]}:{cells[g][0]:+.4f}{stars(cells[g][2])}" for g in groups)
              + f"  ({time.time()-t0:.0f}s)")
        del m, b, se, p
        gc.collect()
    ncols = len(cols)
    ROWS = ["ln_dist"] + row_order
    ROWLAB = {"ln_dist": "$\\ln$ distance"}
    ROWLAB.update({g: f"$\\ln$ distance $\\times$ {GLAB[g]}" for g in row_order})
    lines = [rf"\begin{{tabular}}{{l{'c'*ncols}}} \hline",
             "Dep.\\ var.: $\\ln$ exports & " + " & ".join(c["tag"] for c in cols) + r" \\ \hline"]
    for r in ROWS:
        if not any(r in c["rows"] for c in cols):
            continue
        rb, rse = [], []
        for c in cols:
            if r in c["rows"]:
                bb, ss, pp = c["cells"][r]
                rb.append(f"{bb:.4f}{stars(pp)}"); rse.append(f"({ss:.4f})")
            else:
                rb.append(""); rse.append("")
        lines.append(f"{ROWLAB[r]} & " + " & ".join(rb) + r" \\")
        lines.append(" & " + " & ".join(rse) + r" \\")
    lines.append(r"\hline")
    for fe in FE_ORDER:
        present = [fe in FE_ROWS[c["fe_key"]] for c in cols]
        if not any(present):
            continue
        lines.append(f"{fe} & " + " & ".join(r"$\checkmark$" if p else "" for p in present) + r" \\")
    lines.append(r"\hline")
    lines.append("Observations & " + " & ".join(f"{c['n']:,}" for c in cols) + r" \\")
    lines.append(r"\hline")
    lines.append(rf"\multicolumn{{{ncols+1}}}{{p{{0.92\textwidth}}}}{{\footnotesize {note} "
                 r"Firm$\times$origin$\times$destination$\times$product$\times$year; non-MNE flows the "
                 r"omitted base. Fixed effects as indicated ($\checkmark$). SE clustered at "
                 r"origin-destination. *** p$<$0.01, ** p$<$0.05, * p$<$0.1}} \\")
    lines.append(r"\end{tabular}")
    out = R_SF5 / f"{fname}.tex"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    shutil.copy2(out, OL_R_SF5 / f"{fname}.tex")
    print(f"   -> {out.name}")


# Main table (body): any MNE, then split by presence at the destination
run_table(
    [("(1)", "ODYP", ["g_mne"]), ("(2)", "OYDYP", ["g_mne"]),
     ("(3)", "ODYP", ["g_anypres", "g_anynotpres"]),
     ("(4)", "OYDYP", ["g_anypres", "g_anynotpres"])],
    ["g_mne", "g_anypres", "g_anynotpres"],
    "reg_sf5_distance",
    "Distance and firm exports; multinationals split by presence at the destination.")

# Appendix A: foreign vs domestic, then each split by presence
run_table(
    [("(1)", "ODYP", ["g_ext", "g_dom"]), ("(2)", "OYDYP", ["g_ext", "g_dom"]),
     ("(3)", "ODYP", ["g_pres", "g_notpres", "g_dom_pres", "g_dom_notpres"]),
     ("(4)", "OYDYP", ["g_pres", "g_notpres", "g_dom_pres", "g_dom_notpres"])],
    ["g_ext", "g_pres", "g_notpres", "g_dom", "g_dom_pres", "g_dom_notpres"],
    "reg_sf5_appendix_fordom",
    "Foreign vs domestic multinationals, each split by presence at the destination.")

# Appendix B: as A, but foreign presence split into HQ vs affiliate
run_table(
    [("(1)", "ODYP", ["g_ext", "g_dom"]), ("(2)", "OYDYP", ["g_ext", "g_dom"]),
     ("(3)", "ODYP", ["g_hq", "g_aff", "g_notpres", "g_dom_pres", "g_dom_notpres"]),
     ("(4)", "OYDYP", ["g_hq", "g_aff", "g_notpres", "g_dom_pres", "g_dom_notpres"])],
    ["g_ext", "g_hq", "g_aff", "g_notpres", "g_dom", "g_dom_pres", "g_dom_notpres"],
    "reg_sf5_appendix_hqaff",
    "Foreign-MNE presence split into HQ vs affiliate in the destination.")

print("\n>>> SF5: main + 2 appendix tables written.")
