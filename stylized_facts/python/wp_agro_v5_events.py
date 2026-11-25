"""
wp_agro_v5_events.py  --  event panels of E11 (especificaciones_estimaciones_v5_2026-11-24.md)
==============================================================================================

    WP_YEARS=2012-2018 python wp_agro_v5_events.py      -> data/intermediate/wp/v5/ev5_A.parquet/.dta, ev5_B.parquet/.dta,
                                                           ev5_Bentry.parquet/.dta, ev5_counts.parquet

Balanced cell x year panels 2012-2018 built from the firm rows of agricultural products (data/intermediate/wp/v4/
sector.parquet, real destinations only, HS 2017). Cells A = origin x product, B = origin x destination x product.

Outcomes (logs only on positive values, never ln(1 + x) or asinh):
  step 2  X XL lnX lnXL anyXL lnXLpf (ln exports per local exporter) SHL (local share of the cell's exports) XL (PPML)
  step 3  NL lnNL NEWL (local exporters with no exports of the product in the cell in any earlier year) EXITL (local
          exporters of t-1 that do not export in t) SURVL (share of the local exporters of t-1 still exporting in t)
  step 1  A: NDL NDA (destinations with local / any exports) NEWDL NEWDA (destinations with no local / no exports in
          any earlier year). B-entry panel: odp cells with no local exports before t0, outcome anyXL.
  step 1  information spillovers (A, treated cells): NEWDL_go / NEWDL_xo new local destinations inside / outside the
          set of destinations that the entrant MNE's group served before t0 from this origin in any product; NEWDL_ga /
          NEWDL_xa the same with the group's destinations from any of the nine origins.
  entrant type: XLd NLd anyXLd lnXLd (domestic MNEs counted with local firms, for the first foreign MNE event)
New-entry and exit counts are missing in 2012 (no earlier year observed).

Treatment definitions (gvar = year of the event, 0 = control, missing = not in that sample):
  g_v4   v4 rule: treated t0 >= 2013 with two years of positive exports before t0; controls never treated with two
         years of positive exports in 2012-2018 (the asymmetry flagged in the review of v4)
  g_nc   (i)  no pre condition: every cell with t0 >= 2013 and every never treated cell
  g_ps   (ii) pseudo t0: each never treated cell draws a pseudo t0 from the cohort distribution of the treated cells
         (seed 20261124); both groups need two years of positive exports before their (pseudo) t0
  g_bal  (iii) cells with positive exports in every year (treated under g_v4)
  g_pre3 three years before t0 (treated) and before the pseudo t0 (controls)
  g_for  first foreign MNE (domestic MNEs as local firms), v4 rule on the history
  g_dom  first domestic MNE (foreign MNEs unaffected), v4 rule
  g_s10, g_s25  first MNE entry with an MNE share of the cell's exports of at least 10 (25) percent in t0
  g_pers first MNE entry followed by an MNE in t0 + 1 (t0 <= 2017)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("WP_HS17", "1")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_common as W  # noqa: E402

V4 = W.WP_INT / "v4"
V5 = W.WP_INT / "v5"
YEARS = list(range(2012, 2019))
SEED = 20261124


def firm_rows() -> pd.DataFrame:
    s = pd.read_parquet(V4 / "sector.parquet")
    s = s.rename(columns={"hs07_6d": "hs"})
    s["grp"] = s["parent_key"].fillna("").astype(str)
    s.loc[s["grp"] == "", "grp"] = s["ID_Orbis_DNB"].fillna("").astype(str)
    s.loc[s["grp"] == "", "grp"] = s["firm"].astype(str)
    return s


def new_counts(r: pd.DataFrame, keys: list[str], unit: str, name: str) -> pd.DataFrame:
    """Number of units (firms or destinations) whose first year in the cell is t (t >= 2013)."""
    f = r.groupby(keys + [unit])["year"].min().rename("first").reset_index()
    f = f[f["first"] >= 2013]
    return f.groupby(keys + ["first"]).size().rename(name).reset_index().rename(columns={"first": "year"})


def exit_counts(r: pd.DataFrame, keys: list[str], unit: str, name: str) -> pd.DataFrame:
    """Units present in t - 1 and absent in t."""
    p = r[keys + [unit, "year"]].drop_duplicates()
    nxt = p.assign(year=p["year"] + 1)
    m = nxt.merge(p.assign(here=1), on=keys + [unit, "year"], how="left")
    m = m[(m["here"].isna()) & (m["year"] <= 2018)]
    return m.groupby(keys + ["year"]).size().rename(name).reset_index()


def cell_panel(a: pd.DataFrame, keys: list[str], level: str) -> pd.DataFrame:
    a = a.assign(vl=a["value_fob"] * (a["ot"] == "local"), vm=a["value_fob"] * (a["ot"] != "local"),
                 vd=a["value_fob"] * (a["ot"] == "dom"))
    k = keys + ["year"]
    g = a.groupby(k, as_index=False).agg(X=("value_fob", "sum"), XL=("vl", "sum"), XM=("vm", "sum"), XD=("vd", "sum"))
    for lab, sel in (("N", a["ot"] != "local"), ("NF", a["ot"] == "ext"), ("ND", a["ot"] == "dom"), ("NL", a["ot"] == "local")):
        g = g.merge(a[sel].groupby(k)["firm"].nunique().rename(lab), left_on=k, right_index=True, how="left")
    loc = a[a["ot"] == "local"]
    extra = [new_counts(loc, keys, "firm", "NEWL"), exit_counts(loc, keys, "firm", "EXITL")]
    if level == "A":
        extra += [loc.groupby(k)["dest"].nunique().rename("NDL").reset_index(), a.groupby(k)["dest"].nunique().rename("NDA").reset_index(),
                  new_counts(loc, keys, "dest", "NEWDL"), new_counts(a, keys, "dest", "NEWDA")]
    ids = g[keys].drop_duplicates().reset_index(drop=True)
    ids["cell"] = np.arange(1, len(ids) + 1)
    full = ids.merge(pd.DataFrame({"year": YEARS}), how="cross")
    p = full.merge(g, on=k, how="left")
    for e in extra:
        p = p.merge(e, on=k, how="left")
    cnt = [c for c in ("X", "XL", "XM", "XD", "N", "NF", "ND", "NL", "NEWL", "EXITL", "NDL", "NDA", "NEWDL", "NEWDA") if c in p]
    p[cnt] = p[cnt].fillna(0)
    for c in ("NEWL", "EXITL", "NEWDL", "NEWDA"):
        if c in p:
            p.loc[p["year"] == 2012, c] = np.nan
    p = p.sort_values(["cell", "year"])
    lag = p.groupby("cell")["NL"].shift(1)
    p["SURVL"] = np.where(lag > 0, 1 - p["EXITL"] / lag.where(lag > 0), np.nan)
    p["SHL"] = np.where(p["X"] > 0, p["XL"] / p["X"].where(p["X"] > 0), np.nan)
    p["XLd"] = p["XL"] + p["XD"]
    p["NLd"] = p["NL"] + p["ND"]
    for v in ("X", "XL", "NL", "XLd", "NLd"):
        p[f"ln{v}"] = np.where(p[v] > 0, np.log(p[v].where(p[v] > 0)), np.nan)
    p["anyXL"] = (p["XL"] > 0).astype(int)
    p["anyXLd"] = (p["XLd"] > 0).astype(int)
    p["lnXLpf"] = np.where((p["XL"] > 0) & (p["NL"] > 0), np.log((p["XL"] / p["NL"].replace(0, np.nan)).where(p["XL"] > 0)), np.nan)
    return p


def first_year(p: pd.DataFrame, cond: pd.Series) -> pd.Series:
    return p[cond].groupby("cell")["year"].min()


def treatments(p: pd.DataFrame, rng: np.random.Generator) -> tuple[pd.DataFrame, dict]:
    obs = (p["X"] > 0).astype(int)
    p = p.assign(obs=obs)
    nobs = p.groupby("cell")["obs"].sum()
    cells = pd.DataFrame(index=nobs.index)
    cells["nobs"] = nobs

    def npre(t0: pd.Series) -> pd.Series:
        m = p.merge(t0.rename("t0"), left_on="cell", right_index=True)
        return m[m["year"] < m["t0"]].groupby("cell")["obs"].sum().reindex(t0.index).fillna(0)

    t0 = first_year(p, p["N"] >= 1)
    cells["t0"] = t0
    cells["npre"] = npre(t0.dropna())
    never = cells["t0"].isna()
    tr = cells["t0"] >= 2013
    cells["g_v4"] = np.select([tr & (cells["npre"] >= 2), never & (cells["nobs"] >= 2)], [cells["t0"], 0], np.nan)
    cells["g_nc"] = np.select([tr, never & (cells["nobs"] >= 1)], [cells["t0"], 0], np.nan)
    # pseudo t0 for never treated cells, drawn from the cohort distribution of the treated cells of g_v4
    coh = cells.loc[cells["g_v4"] > 0, "g_v4"].value_counts(normalize=True).sort_index()
    nv = cells.index[never]
    ps = pd.Series(rng.choice(coh.index.values, size=len(nv), p=coh.values), index=nv)
    cells["pseudo_t0"] = ps
    pre_ps = npre(ps)
    cells["npre_ps"] = pre_ps
    cells["g_ps"] = np.select([tr & (cells["npre"] >= 2), never & (pre_ps.reindex(cells.index).fillna(0) >= 2)], [cells["t0"], 0], np.nan)
    cells["g_pre3"] = np.select([tr & (cells["npre"] >= 3), never & (pre_ps.reindex(cells.index).fillna(0) >= 3)], [cells["t0"], 0], np.nan)
    cells["g_bal"] = np.where(cells["nobs"] == len(YEARS), cells["g_v4"], np.nan)
    # entrant type
    for name, col in (("g_for", "NF"), ("g_dom", "ND")):
        t = first_year(p, p[col] >= 1)
        c = pd.Series(np.nan, index=cells.index); c.loc[t.index] = t
        pre = npre(t)
        cells[name] = np.select([(c >= 2013) & (pre.reindex(cells.index).fillna(0) >= 2), c.isna() & (cells["nobs"] >= 2)], [c, 0], np.nan)
    # size of the entry and persistence
    s0 = p.merge(cells["t0"].rename("t0x"), left_on="cell", right_index=True)
    at0 = s0[s0["year"] == s0["t0x"]].set_index("cell")
    share0 = (at0["XM"] / at0["X"].replace(0, np.nan)).reindex(cells.index)
    nxt = s0[s0["year"] == s0["t0x"] + 1].set_index("cell")["N"].reindex(cells.index)
    base = tr & (cells["npre"] >= 2)
    ctrl = never & (cells["nobs"] >= 2)
    for name, thr in (("g_s10", 0.10), ("g_s25", 0.25)):
        cells[name] = np.select([base & (share0 >= thr), ctrl], [cells["t0"], 0], np.nan)
    cells["g_pers"] = np.select([base & (cells["t0"] <= 2017) & (nxt >= 1), ctrl], [cells["t0"], 0], np.nan)
    cells["share_t0"] = share0
    G = [c for c in cells.columns if c.startswith("g_")]
    counts = {g: {"treated": int((cells[g] > 0).sum()), "controls": int((cells[g] == 0).sum())} for g in G}
    p = p.merge(cells[G + ["t0", "pseudo_t0", "npre", "nobs", "share_t0"]], left_on="cell", right_index=True, how="left")
    return p, counts


def spillover(p: pd.DataFrame, a: pd.DataFrame) -> pd.DataFrame:
    """A cells: new local destinations inside / outside the destinations served by the entrant group before t0."""
    tr = p.loc[p["t0"] >= 2013, ["cell", "country_orig", "hs", "t0"]].drop_duplicates("cell")
    ent = a[a["ot"] != "local"].merge(tr, on=["country_orig", "hs"])
    ent = ent[ent["year"] == ent["t0"]][["cell", "country_orig", "t0", "grp"]].drop_duplicates()
    gr = a[a["grp"].isin(ent["grp"].unique())][["grp", "country_orig", "dest", "year"]].drop_duplicates()
    m = ent.merge(gr, on="grp", suffixes=("", "_g"))
    m = m[m["year"] < m["t0"]]
    s_orig = m[m["country_orig_g"] == m["country_orig"]][["cell", "dest"]].drop_duplicates().assign(in_o=1)
    s_any = m[["cell", "dest"]].drop_duplicates().assign(in_a=1)
    loc = a[a["ot"] == "local"]
    f = loc.groupby(["country_orig", "hs", "dest"])["year"].min().rename("year").reset_index()
    f = f[f["year"] >= 2013].merge(tr[["cell", "country_orig", "hs"]], on=["country_orig", "hs"])
    f = f.merge(s_orig, on=["cell", "dest"], how="left").merge(s_any, on=["cell", "dest"], how="left").fillna({"in_o": 0, "in_a": 0})
    out = f.groupby(["cell", "year"]).agg(NEWDL_go=("in_o", "sum"), NEWDL_ga=("in_a", "sum"), n=("dest", "size")).reset_index()
    out["NEWDL_xo"] = out["n"] - out["NEWDL_go"]
    out["NEWDL_xa"] = out["n"] - out["NEWDL_ga"]
    p = p.merge(out.drop(columns="n"), on=["cell", "year"], how="left")
    trc = p["t0"] >= 2013
    for c in ("NEWDL_go", "NEWDL_ga", "NEWDL_xo", "NEWDL_xa"):
        p[c] = np.where(trc & (p["year"] >= 2013), p[c].fillna(0), np.nan)
    info = {"entrant groups": int(ent["grp"].nunique()), "treated cells with an entrant group": int(ent["cell"].nunique()),
            "cells whose group served a destination before t0 from this origin": int(s_orig["cell"].nunique()),
            "cells whose group served a destination before t0 from any origin": int(s_any["cell"].nunique()),
            "destinations in the sets, from this origin (cell x destination)": int(len(s_orig)),
            "destinations in the sets, from any origin (cell x destination)": int(len(s_any))}
    return p, info


def b_entry(pA: pd.DataFrame, pB: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """odp cells of origin x product cells: the event is the first MNE in the op cell (v4 rule at the op level), applied to
    every destination of the cell; sample: odp cells with no local exports in any year before t0 (controls: before
    their pseudo t0)."""
    ca = pA.drop_duplicates("cell")[["country_orig", "hs", "g_v4", "g_ps", "pseudo_t0"]]
    b = pB.drop(columns=[c for c in pB.columns if c.startswith("g_") or c in ("t0", "pseudo_t0", "npre", "nobs", "share_t0")])
    b = b.merge(ca, on=["country_orig", "hs"], how="inner")
    t_ref = np.where(b["g_ps"] > 0, b["g_ps"], b["pseudo_t0"])
    b["t_ref"] = t_ref
    pre_local = b[b["year"] < b["t_ref"]].groupby("cell")["XL"].sum()
    ok = pre_local.index[pre_local == 0]
    b = b[b["cell"].isin(ok) & b["g_ps"].notna()].copy()
    b["g_be"] = b["g_ps"]
    return b


def to_dta(p: pd.DataFrame, path: Path) -> None:
    s = p.copy()
    for col in s.columns:
        if str(s[col].dtype) in ("string", "object"):
            s[col] = s[col].astype(str).replace({"<NA>": "", "nan": "", "None": ""}).astype(object)
        if str(s[col].dtype) == "bool":
            s[col] = s[col].astype(int)
    s.to_stata(path, write_index=False, version=118)


def main() -> None:
    rng = np.random.default_rng(SEED)
    s = firm_rows()
    a = s[s["hs2"].between(1, 24)].copy()
    cls = pd.read_parquet(V5 / "classes_v5.parquet")
    cls["high_top"] = np.select([cls["stage"] == "Farm", cls["stage"] == "Processing"],
                                [cls["high_gap150"], cls["high_gap240"]], "Not classified")
    lab = ["hs", "type", "stage", "high_mean", "high_median", "high_top", "tercile_stage", "processing_degree"]
    for extra in ("high_PCI", "rauch_full_con", "rauch_full_lib"):
        if extra in cls:
            lab.append(extra)
    counts, info = {}, {}
    out = {}
    for P, keys in (("A", ["country_orig", "hs"]), ("B", ["country_orig", "dest", "hs"])):
        p = cell_panel(a, keys, P)
        p, counts[P] = treatments(p, rng)
        if P == "A":
            p, info = spillover(p, a)
        p = p.merge(cls[lab], on="hs", how="left")
        p["clus"] = p["cell"] if P == "A" else pd.factorize(p["country_orig"] + "_" + p["dest"])[0] + 1
        out[P] = p
        print(f"{P}: {p['cell'].nunique():,} cells, {len(p):,} rows; " + ", ".join(f"{g} {c['treated']}/{c['controls']}" for g, c in counts[P].items()))
    be = b_entry(out["A"], out["B"], rng)
    counts["Bentry"] = {"g_be": {"treated": int(be.drop_duplicates("cell")["g_be"].gt(0).sum()),
                                 "controls": int(be.drop_duplicates("cell")["g_be"].eq(0).sum())}}
    print("B entry:", counts["Bentry"], f"{len(be):,} rows")
    print("spillover:", info)
    for P, p in (("A", out["A"]), ("B", out["B"]), ("Bentry", be)):
        p.to_parquet(V5 / f"ev5_{P}.parquet", index=False)
        to_dta(p, V5 / f"ev5_{P}.dta")
    rows = [{"Cells": P, "Treatment definition": g, "Treated cells": c["treated"], "Control cells": c["controls"]}
            for P, d in counts.items() for g, c in d.items()]
    pd.DataFrame(rows).to_parquet(V5 / "ev5_counts.parquet", index=False)
    pd.Series(info).rename("value").to_frame().to_parquet(V5 / "ev5_spillover_info.parquet")


if __name__ == "__main__":
    main()
