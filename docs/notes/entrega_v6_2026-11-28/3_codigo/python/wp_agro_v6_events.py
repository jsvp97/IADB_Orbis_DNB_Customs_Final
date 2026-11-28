"""
wp_agro_v6_events.py  --  panels, cohort-aligned stacks and the universe table of round v6
==========================================================================================

    WP_YEARS=2012-2018 python wp_agro_v6_events.py    (about 10 minutes)

Implements A.2, A.3, A.7 and V6-10 of especificaciones_estimaciones_v6_2026-11-25.md, plus the firm-level flags of V6-17.

Levels: A = origin x HS6 product (op), B = origin x destination x HS6 product (odp), H = origin x HS4 heading (oh). Universe of
each level: cells with positive exports in at least one year 2012-2018 (agricultural rows, HS 2017, real destinations).
Outcomes (A.3): X XL XM N NF ND NL G D anyXL lnX lnXL lnNL NEWL NEWL_fw EXITL SURVL (+ NEWL_clean in A, V6-12 row 11).
"New" is new in the cell of the level (A product, B destination, H heading), looking back to 2012; NEWL_fw = exports in t and
not in t-1 or t-2 (from 2014).

Aligned stacks (A.7): at risk = no MNE in 2012 and 2013; cohort g in 2014-2018 = first year with an MNE; never treated = no MNE
in 2012-2018. R(g): X > 0 in g-1 and g-2; R3(g) adds g-3; R0 no rule. Stack g = treated of cohort g plus every never treated
cell, years max(2012, g-4) to min(2018, g+4); flags inR, inR3 say whether the cell meets the rule for that stack (R0 = all).
Placebo stacks: cohorts 2017 and 2018 with the event at p = g-3, years up to g-1, rule R(p).

Writes data/intermediate/wp/v6/: ev6_<A|B|H>_panel.parquet (cell x year), ev6_<A|B|H>_stk.dta (stacks), ev6_<A|B|H>_plc.dta
(placebo stacks), ev6_A_newfirms.parquet (V6-17), ev6_universe.pkl (V6-10 blocks), ev6_cells_<A|B|H>.parquet (cell traits).
"""
from __future__ import annotations

import os
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("WP_HS17", "1")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_common as W  # noqa: E402

V4 = W.WP_INT / "v4"
V6 = W.WP_INT / "v6"
YEARS = list(range(2012, 2019))
COH = list(range(2014, 2019))
KEYS = {"A": ["country_orig", "hs"], "B": ["country_orig", "dest", "hs"], "H": ["country_orig", "hs4"]}


def rows() -> tuple[pd.DataFrame, pd.DataFrame]:
    s = pd.read_parquet(V4 / "sector.parquet").rename(columns={"hs07_6d": "hs"})
    s["grp"] = s["parent_key"].fillna("").astype(str)
    s.loc[s["grp"] == "", "grp"] = s["ID_Orbis_DNB"].fillna("").astype(str)
    s.loc[s["grp"] == "", "grp"] = s["firm"].astype(str)
    s["hs4"] = s["hs"].str[:4]
    s["mne"] = s["ot"] != "local"
    a = s[s["hs2"].between(1, 24) & s["year"].between(2012, 2018)].copy()
    return s, a


def first_counts(r: pd.DataFrame, keys: list[str], name: str) -> pd.DataFrame:
    f = r.groupby(keys + ["firm"])["year"].min().rename("year").reset_index()
    f = f[f["year"] >= 2013]
    return f.groupby(keys + ["year"]).size().rename(name).reset_index()


def fw_counts(r: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    p = r[keys + ["firm", "year"]].drop_duplicates()
    s = set(map(tuple, p[keys + ["firm", "year"]].values))
    lag1 = [tuple(x[:-1]) + (x[-1] - 1,) for x in p[keys + ["firm", "year"]].values]
    lag2 = [tuple(x[:-1]) + (x[-1] - 2,) for x in p[keys + ["firm", "year"]].values]
    p = p.assign(new=[(a not in s) and (b not in s) for a, b in zip(lag1, lag2)])
    p = p[(p["year"] >= 2014) & p["new"]]
    return p.groupby(keys + ["year"]).size().rename("NEWL_fw").reset_index()


def exit_counts(r: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    p = r[keys + ["firm", "year"]].drop_duplicates()
    nxt = p.assign(year=p["year"] + 1).merge(p.assign(here=1), on=keys + ["firm", "year"], how="left")
    nxt = nxt[nxt["here"].isna() & (nxt["year"] <= 2018)]
    return nxt.groupby(keys + ["year"]).size().rename("EXITL").reset_index()


def panel(a: pd.DataFrame, level: str) -> pd.DataFrame:
    keys = KEYS[level]
    k = keys + ["year"]
    a = a.assign(vl=a["value_fob"] * ~a["mne"], vm=a["value_fob"] * a["mne"])
    g = a.groupby(k, as_index=False).agg(X=("value_fob", "sum"), XL=("vl", "sum"), XM=("vm", "sum"))
    for lab, sel in (("N", a["mne"]), ("NF", a["ot"] == "ext"), ("ND", a["ot"] == "dom"), ("NL", ~a["mne"])):
        g = g.merge(a[sel].groupby(k)["firm"].nunique().rename(lab), left_on=k, right_index=True, how="left")
    g = g.merge(a[a["mne"]].groupby(k)["grp"].nunique().rename("G"), left_on=k, right_index=True, how="left")
    loc = a[~a["mne"]]
    ids = g[keys].drop_duplicates().reset_index(drop=True)
    ids["cell"] = np.arange(1, len(ids) + 1)
    p = ids.merge(pd.DataFrame({"year": YEARS}), how="cross").merge(g, on=k, how="left")
    for e in (first_counts(loc, keys, "NEWL"), fw_counts(loc, keys), exit_counts(loc, keys)):
        p = p.merge(e, on=k, how="left")
    cnt = ["X", "XL", "XM", "N", "NF", "ND", "NL", "G", "NEWL", "NEWL_fw", "EXITL"]
    p[cnt] = p[cnt].fillna(0)
    p.loc[p["year"] == 2012, ["NEWL", "EXITL"]] = np.nan
    p.loc[p["year"] < 2014, "NEWL_fw"] = np.nan
    p = p.sort_values(["cell", "year"]).reset_index(drop=True)
    lag = p.groupby("cell")["NL"].shift(1)
    p["SURVL"] = np.where(lag > 0, 1 - p["EXITL"] / lag.where(lag > 0), np.nan)
    p["D"] = (p["N"] >= 1).astype(int)
    p["anyXL"] = (p["XL"] > 0).astype(int)
    for v in ("X", "XL", "NL", "N", "G", "XM"):
        p[f"ln{v}"] = np.where(p[v] > 0, np.log(p[v].where(p[v] > 0)), np.nan)
    return p


def status(p: pd.DataFrame) -> pd.DataFrame:
    """One row per cell: t0, status, X by year (wide) and the rules R(g), R3(g) for every g."""
    w = p.pivot(index="cell", columns="year", values="X")
    n = p.pivot(index="cell", columns="year", values="N")
    c = pd.DataFrame(index=w.index)
    has = n >= 1
    c["t0"] = has.idxmax(axis=1).where(has.any(axis=1))
    c["status"] = np.select([c["t0"] == 2012, c["t0"] == 2013, c["t0"].isna()], ["MNE since 2012", "First MNE in 2013", "Never treated"],
                            c["t0"].fillna(0).astype(int).astype(str))
    for g in COH:
        c[f"R_{g}"] = ((w[g - 1] > 0) & (w[g - 2] > 0)).astype(int)
        c[f"R3_{g}"] = ((w[g - 1] > 0) & (w[g - 2] > 0) & (w[g - 3] > 0)).astype(int) if g - 3 >= 2012 else 0
    for p_ in (2014, 2015):  # placebo events (g - 3 for cohorts 2017, 2018)
        c[f"R_{p_}"] = ((w[p_ - 1] > 0) & (w[p_ - 2] > 0)).astype(int)
    c["X_1218"] = w.sum(axis=1)
    return c


def stacks(p: pd.DataFrame, c: pd.DataFrame, keep: list[str], placebo: bool = False) -> pd.DataFrame:
    out = []
    never = c.index[c["status"] == "Never treated"]
    if not placebo:
        for g in COH:
            tr = c.index[c["t0"] == g]
            cells = np.r_[tr, never]
            s = p[p["cell"].isin(cells) & p["year"].between(max(2012, g - 4), min(2018, g + 4))][keep].copy()
            s["stack"] = g
            s["treat"] = s["cell"].isin(tr).astype(int)
            s["inR"] = s["cell"].map(c[f"R_{g}"]).astype(int)
            s["inR3"] = s["cell"].map(c[f"R3_{g}"]).astype(int) if g >= 2015 else 0
            out.append(s)
    else:
        for g in (2017, 2018):
            pe = g - 3
            tr = c.index[c["t0"] == g]
            cells = np.r_[tr, never]
            s = p[p["cell"].isin(cells) & p["year"].between(max(2012, pe - 4), g - 1)][keep].copy()
            s["stack"] = pe
            s["treat"] = s["cell"].isin(tr).astype(int)
            s["inR"] = s["cell"].map(c[f"R_{pe}"]).astype(int)
            s["inR3"] = 0
            out.append(s)
    s = pd.concat(out, ignore_index=True)
    s["k"] = s["year"] - s["stack"]
    return s


def to_dta(df: pd.DataFrame, path: Path) -> None:
    s = df.copy()
    for col in s.columns:
        if str(s[col].dtype) in ("string", "object"):
            s[col] = s[col].astype(str).replace({"<NA>": "", "nan": "", "None": ""}).astype(object)
        elif str(s[col].dtype) == "bool":
            s[col] = s[col].astype(int)
    s.to_stata(path, write_index=False, version=118)


def newfirm_flags(s: pd.DataFrame, a: pd.DataFrame, pA: pd.DataFrame, cA: pd.DataFrame) -> pd.DataFrame:
    """V6-17: one row per local new exporter of an op cell (first year >= 2013) with its provenance and flags."""
    loc = a[~a["mne"]]
    first = loc.groupby(["country_orig", "hs", "firm"])["year"].min().rename("year").reset_index()
    first = first[first["year"] >= 2013]
    # provenance over all chapters, 2012 onward
    allp = s[s["year"].between(2012, 2018)][["country_orig", "firm", "hs", "hs4", "year"]].drop_duplicates()
    m = first.merge(allp.rename(columns={"hs": "hs_o", "hs4": "hs4_o", "year": "year_o"}), on=["country_orig", "firm"], how="left")
    m = m[m["year_o"] < m["year"]]
    m["hs4"] = m["hs"].str[:4]
    same4 = m[(m["hs4_o"] == m["hs4"]) & (m["hs_o"] != m["hs"])].groupby(["country_orig", "hs", "firm"]).size().rename("n4")
    anyo = m.groupby(["country_orig", "hs", "firm"]).size().rename("nany")
    f = first.merge(same4, left_on=["country_orig", "hs", "firm"], right_index=True, how="left").merge(
        anyo, left_on=["country_orig", "hs", "firm"], right_index=True, how="left")
    f["prov"] = np.select([f["nany"].isna(), f["n4"].notna()], ["NEWL_denovo", "NEWL_div_hs4"], "NEWL_div_other")
    # persist
    py = loc[["country_orig", "hs", "firm", "year"]].drop_duplicates()
    f = f.merge(py.assign(year=py["year"] - 1, persist=1), on=["country_orig", "hs", "firm", "year"], how="left")
    f["persist"] = np.where(f["year"] <= 2017, f["persist"].fillna(0), np.nan)
    # size: first-year exports of the product, origin p90 and cell median of local exporters
    fv = loc.groupby(["country_orig", "hs", "firm", "year"])["value_fob"].sum().rename("v").reset_index()
    f = f.merge(fv, on=["country_orig", "hs", "firm", "year"], how="left")
    p90 = fv.groupby(["country_orig", "year"])["v"].quantile(0.9).rename("p90")
    med = fv.groupby(["country_orig", "hs", "year"])["v"].median().rename("medcell")
    f = f.merge(p90, left_on=["country_orig", "year"], right_index=True, how="left").merge(
        med, left_on=["country_orig", "hs", "year"], right_index=True, how="left")
    f["big"] = (f["v"] > f["p90"]).astype(int)
    f["relsize"] = f["v"] / f["medcell"]
    # destinations of the new exporter in its first year
    fd = loc.groupby(["country_orig", "hs", "firm", "year"])["dest"].apply(frozenset).rename("dests").reset_index()
    f = f.merge(fd, on=["country_orig", "hs", "firm", "year"], how="left")
    # samedest: a destination already served that year or before by an MNE of the origin in the product
    mn = a[a["mne"]].groupby(["country_orig", "hs", "dest"])["year"].min().rename("ymne").reset_index()
    md = {(o, h): dict(zip(g["dest"], g["ymne"])) for (o, h), g in mn.groupby(["country_orig", "hs"])}
    f["samedest"] = [int(any(md.get((o, h), {}).get(d, 9999) <= y for d in ds)) for o, h, y, ds in zip(f["country_orig"], f["hs"], f["year"], f["dests"])]
    # dest_subset: all destinations among those of the entrant MNEs in the cell in g (treated cells only)
    cells = pA.drop_duplicates("cell")[["cell", "country_orig", "hs"]].merge(cA[["t0"]], left_on="cell", right_index=True)
    tr = cells[cells["t0"].between(2014, 2018)]
    ent = a[a["mne"]].merge(tr, on=["country_orig", "hs"])
    ent = ent[ent["year"] == ent["t0"]].groupby(["country_orig", "hs"])["dest"].apply(frozenset).rename("edests").reset_index()
    f = f.merge(ent, on=["country_orig", "hs"], how="left")
    f["dest_subset"] = [int(isinstance(e, frozenset) and ds <= e) if isinstance(e, frozenset) else np.nan for ds, e in zip(f["dests"], f["edests"])]
    f = f.merge(cells[["cell", "country_orig", "hs"]], on=["country_orig", "hs"], how="left")
    return f.drop(columns=["dests", "edests", "n4", "nany"])


def entrant_traits(a: pd.DataFrame, pA: pd.DataFrame, cA: pd.DataFrame) -> pd.DataFrame:
    """ent_big, ent_incumbent and the 'who enters' categories for every first entry of cohorts 2014-2018 in A."""
    cells = pA.drop_duplicates("cell")[["cell", "country_orig", "hs"]].merge(cA[["t0", "R_2014", "R_2015", "R_2016", "R_2017", "R_2018"]],
                                                                          left_on="cell", right_index=True)
    tr = cells[cells["t0"].between(2014, 2018)].copy()
    tr["inR"] = [r[f"R_{int(t)}"] for t, r in zip(tr["t0"], tr.to_dict("records"))]
    mne = a[a["mne"]]
    e = mne.merge(tr[["cell", "country_orig", "hs", "t0"]], on=["country_orig", "hs"])
    e = e[e["year"] == e["t0"]]
    nent = e.groupby("cell")["firm"].nunique().rename("n_entrant_firms")
    grp_x = mne.groupby(["grp", "year"])["value_fob"].sum()          # agricultural exports of the group, nine origins
    eg = e[["cell", "country_orig", "hs", "t0", "grp"]].drop_duplicates()
    eg["xg_prev"] = [grp_x.get((g, t - 1), 0.0) for g, t in zip(eg["grp"], eg["t0"])]
    eg = eg.sort_values(["cell", "xg_prev"], ascending=[True, False]).drop_duplicates("cell")
    # prior activity of the entrant group from the origin in g - 1 (all chapters for 'another agricultural product': chapters 01-24)
    act = a[a["mne"]][["grp", "country_orig", "hs", "year"]].drop_duplicates()
    act["hs4"] = act["hs"].str[:4]; act["hs2c"] = act["hs"].str[:2]
    look = {(g, o, y): grp_ for (g, o, y), grp_ in act.groupby(["grp", "country_orig", "year"])}
    who, inc = [], []
    for g, o, h, t in zip(eg["grp"], eg["country_orig"], eg["hs"], eg["t0"]):
        x = look.get((g, o, t - 1))
        if x is None or len(x) == 0:
            who.append("nothing from the origin in g - 1"); inc.append(0); continue
        x = x[x["hs"] != h]
        if len(x) == 0:
            who.append("nothing from the origin in g - 1"); inc.append(0); continue
        inc.append(1)
        if (x["hs4"] == h[:4]).any():
            who.append("another HS6 of the same heading")
        elif (x["hs2c"] == h[:2]).any():
            who.append("another heading of the same chapter")
        else:
            who.append("another agricultural product")
    eg["who_enters"] = who
    eg["ent_incumbent"] = inc
    tr = tr.merge(eg[["cell", "grp", "xg_prev", "who_enters", "ent_incumbent"]], on="cell", how="left").merge(nent, left_on="cell", right_index=True, how="left")
    med = tr.loc[tr["inR"] == 1, "xg_prev"].median()
    tr["ent_big"] = (tr["xg_prev"] > med).astype(int)
    tr["ent_big_median_usd"] = med
    return tr


def universe(levels: dict, cells_all: dict, a: pd.DataFrame, flags: pd.DataFrame, traits: pd.DataFrame, cls: pd.DataFrame) -> dict:
    U = {}
    tot = a["value_fob"].sum()
    # block 1 and 2
    b12 = []
    for lev, c in cells_all.items():
        for st, y in c.groupby("status"):
            r = {"Level": lev, "Status": st, "Cells (R0)": len(y), "Exports 2012-2018 (US$ million)": y["X_1218"].sum() / 1e6,
                 "Share of agricultural exports (%)": 100 * y["X_1218"].sum() / tot}
            if st.isdigit():
                r["Cells with R(g)"] = int(y[f"R_{st}"].sum())
            if st == "Never treated":
                for g in COH:
                    r[f"Never treated with R({g})"] = int(y[f"R_{g}"].sum())
            b12.append(r)
    U["status"] = pd.DataFrame(b12)
    b1o = []
    for lev in ("A", "B"):
        c = cells_all[lev]
        for (o, st), y in c.groupby(["country_orig", "status"]):
            r = {"Level": lev, "Origin": o, "Status": st, "Cells (R0)": len(y)}
            if st.isdigit():
                r["Cells with R(g)"] = int(y[f"R_{st}"].sum())
            b1o.append(r)
    U["status_by_origin"] = pd.DataFrame(b1o)
    th = cells_all["H"]
    nh = int(sum(th.loc[th["status"] == str(g), f"R_{g}"].sum() for g in COH))
    U["heading_threshold"] = pd.DataFrame([{"Treated headings with R(g), cohorts 2014-2018": nh, "Threshold": 150,
                                            "Estimate N4 (V6-15)": "yes" if nh >= 150 else "no"}])
    # block 3: who enters
    t = traits.copy()
    rows = []
    for lab, sub in (("R0", t), ("R(g)", t[t["inR"] == 1])):
        for w, y in sub.groupby("who_enters"):
            rows.append({"Rule": lab, "Entrant group in g - 1": w, "First entries": len(y)})
        rows.append({"Rule": lab, "Entrant group in g - 1": "distinct entrant groups", "First entries": sub["grp"].nunique()})
        rows.append({"Rule": lab, "Entrant group in g - 1": "cells where two or more MNEs enter in the same year", "First entries": int((sub["n_entrant_firms"] >= 2).sum())})
        rows.append({"Rule": lab, "Entrant group in g - 1": "ent_big = 1", "First entries": int(sub["ent_big"].sum())})
        rows.append({"Rule": lab, "Entrant group in g - 1": "ent_incumbent = 1", "First entries": int(sub["ent_incumbent"].sum())})
    U["who_enters"] = pd.DataFrame(rows)
    # block 4: hs_n1
    n1 = set(cls.loc[cls["hs_n1"] == 1, "hs"])
    b4 = []
    for lev in ("A", "B"):
        c = cells_all[lev]
        for g in COH:
            y = c[c["status"] == str(g)]
            b4.append({"Level": lev, "Cohort": g, "First entries": len(y), "of which in hs_n1 codes": int(y["hs"].isin(n1).sum()),
                       "First entries with R(g)": int(y[f"R_{g}"].sum()), "with R(g), in hs_n1 codes": int((y[f"R_{g}"].astype(bool) & y["hs"].isin(n1)).sum())})
    U["hs_n1_entries"] = pd.DataFrame(b4)
    nf = flags.copy()
    nf["n1"] = nf["hs"].isin(n1)
    U["hs_n1_newl_by_year"] = nf.groupby("year").agg(NEWL=("firm", "size"), NEWL_in_hs_n1=("n1", "sum")).reset_index()
    pA = levels["A"]
    k0 = pA[(pA["t0"].between(2014, 2018)) & (pA["year"] == pA["t0"])]
    k0 = k0.assign(n1=k0["hs"].isin(n1))
    U["hs_n1_newl_k0"] = k0.groupby("t0").apply(lambda y: pd.Series({"NEWL at k = 0, treated cells": y["NEWL"].sum(),
                                                                      "of which in hs_n1 codes": y.loc[y["n1"], "NEWL"].sum()})).reset_index().rename(columns={"t0": "Cohort"})
    # block 5: alternative events
    b5 = []
    for lev in ("A", "B"):
        p = levels[lev]
        n = p.pivot(index="cell", columns="year", values="N")
        for g in COH:
            sec = ((n[g - 1] == 1) & (n[g - 2] == 1) & (n[g] >= 2)).sum()
            last = ((n[g - 1] >= 1) & (n[g - 2] >= 1) & (n[g] == 0) & (n.get(g + 1, pd.Series(np.nan, index=n.index)) == 0)).sum() if g <= 2017 else np.nan
            b5.append({"Level": lev, "Cohort": g, "Second MNE": int(sec), "Last MNE leaves": last})
    U["alt_events"] = pd.DataFrame(b5)
    cb = cells_all["B"]
    U["B_event_types"] = pd.DataFrame([
        {"Group": "first entries, (i) MNE new to the product", "Cells": int(((cb["etype"] == 1)).sum()),
         "with R(g)": int(((cb["etype"] == 1) & (cb["Rown"] == 1)).sum())},
        {"Group": "first entries, (ii) expansion of destinations", "Cells": int((cb["etype"] == 2).sum()),
         "with R(g)": int(((cb["etype"] == 2) & (cb["Rown"] == 1)).sum())},
        {"Group": "never treated controls, pure (their op never had an MNE)", "Cells": int((cb["ctype"] == "pure").sum())},
        {"Group": "never treated controls, exposed (their op had an MNE in some year)", "Cells": int((cb["ctype"] == "exposed").sum())}])
    return U


def main() -> None:
    V6.mkdir(parents=True, exist_ok=True)
    s, a = rows()
    cls = pd.read_parquet(V6 / "classes_v6.parquet")
    lab = ["hs", "type", "stage", "high_PCI6", "PCI6_z", "rauch_bin_con", "rauch_full_con", "hs_n1"]
    levels, cells_all = {}, {}
    for lev in ("A", "B", "H"):
        p = panel(a, lev)
        c = status(p)
        c = c.join(p.drop_duplicates("cell").set_index("cell")[KEYS[lev]])
        levels[lev], cells_all[lev] = p, c
        print(f"{lev}: {p['cell'].nunique():,} cells; " + ", ".join(f"{k} {v}" for k, v in c["status"].value_counts().sort_index().items()))
    # A: new-exporter flags (V6-17) and NEWL_clean
    flags = newfirm_flags(s, a, levels["A"], cells_all["A"])
    flags.to_parquet(V6 / "ev6_A_newfirms.parquet", index=False)
    doubt = flags[(flags["big"] == 1) | (flags["dest_subset"] == 1)].groupby(["cell", "year"]).size().rename("n_doubt")
    pA = levels["A"].merge(doubt, left_on=["cell", "year"], right_index=True, how="left")
    pA["NEWL_clean"] = np.where(pA["NEWL"].notna(), pA["NEWL"] - pA["n_doubt"].fillna(0), np.nan)
    levels["A"] = pA.drop(columns="n_doubt")
    traits = entrant_traits(a, levels["A"], cells_all["A"])
    # B: event type and control type from the op history
    pB, cB = levels["B"], cells_all["B"]
    cAop = cells_all["A"][["country_orig", "hs", "t0"]].rename(columns={"t0": "t0_op"})
    cB = cB.reset_index().merge(cAop, on=["country_orig", "hs"], how="left").set_index("cell")
    cB["etype"] = np.where(cB["t0"].between(2014, 2018), np.where(cB["t0"] == cB["t0_op"], 1, np.where(cB["t0_op"] < cB["t0"], 2, 0)), 0)
    cB["ctype"] = np.where(cB["status"] == "Never treated", np.where(cB["t0_op"].isna(), "pure", "exposed"), "")
    cB["Rown"] = [r.get(f"R_{int(t)}", 0) if 2014 <= (t if t == t else 0) <= 2018 else 0 for t, r in zip(cB["t0"], cB.to_dict("records"))]
    cells_all["B"] = cB
    # Dotros: some MNE exports the product from the origin to another destination in t
    mop = a[a["mne"]].groupby(["country_orig", "hs", "year"])["dest"].nunique().rename("nd_mne_op")
    pB = pB.merge(mop, left_on=["country_orig", "hs", "year"], right_index=True, how="left")
    pB["Dotros"] = ((pB["nd_mne_op"].fillna(0) - pB["D"]) >= 1).astype(int)
    levels["B"] = pB.drop(columns="nd_mne_op")
    # cell traits and stacks
    tA = traits.set_index("cell")[["ent_big", "ent_incumbent", "who_enters", "grp"]]
    keep_common = ["cell", "year", "country_orig", "X", "XL", "N", "D", "NL", "NEWL", "NEWL_fw", "EXITL", "SURVL", "anyXL", "lnX", "lnXL", "lnNL", "G"]
    for lev in ("A", "B", "H"):
        p, c = levels[lev], cells_all[lev]
        if lev != "H":
            p = p.merge(cls[lab], on="hs", how="left")
            p["hs4"] = p["hs"].str[:4]
            p["hs2"] = p["hs"].str[:2]
        else:
            p["hs2"] = p["hs4"].str[:2]
        keep = keep_common + [x for x in ("hs", "hs4", "hs2", "dest", "type", "stage", "high_PCI6", "rauch_bin_con", "rauch_full_con", "hs_n1",
                                          "NEWL_clean", "Dotros") if x in p.columns]
        p = p.merge(c[["t0", "status"]], left_on="cell", right_index=True, how="left")
        levels[lev] = p
        p.to_parquet(V6 / f"ev6_{lev}_panel.parquet", index=False)
        # flags for the bridge table (V6-16): at risk, in the event-study sample, Post
        ins = set()
        for g in COH:
            ins |= set(c.index[((c["t0"] == g) | (c["status"] == "Never treated")) & (c[f"R_{g}"] == 1)])
        q = p.assign(atrisk=p["status"].isin([str(g) for g in COH] + ["Never treated"]).astype(int),
                     insample=p["cell"].isin(ins).astype(int),
                     Post=np.where(p["t0"].notna(), (p["year"] >= p["t0"]).astype(float), 0.0))
        to_dta(q.drop(columns=[x for x in ("status",) if x in q]), V6 / f"ev6_{lev}_panel.dta")
        c.to_parquet(V6 / f"ev6_cells_{lev}.parquet")
        for plc, suf in ((False, "stk"), (True, "plc")):
            st = stacks(p, c, keep, placebo=plc)
            if lev == "A":
                st = st.merge(tA[["ent_big", "ent_incumbent", "grp"]], left_on="cell", right_index=True, how="left")
                st["egrp"] = np.where(st["treat"] == 1, pd.factorize(st["grp"].fillna(""))[0] + 1, st["cell"] + 1_000_000)
                st = st.drop(columns="grp")
            if lev == "B":
                st = st.merge(c[["etype", "ctype"]], left_on="cell", right_index=True, how="left")
                st["op"] = pd.factorize(st["country_orig"] + "_" + st["hs"])[0] + 1
                st["od"] = pd.factorize(st["country_orig"] + "_" + st["dest"])[0] + 1
            to_dta(st, V6 / f"ev6_{lev}_{suf}.dta")
            print(f"   {lev} {suf}: {len(st):,} rows, treated cells with R(g) {st.loc[(st['treat'] == 1) & (st['inR'] == 1), 'cell'].nunique():,}, "
                  f"controls with R(g) (any stack) {st.loc[(st['treat'] == 0) & (st['inR'] == 1), 'cell'].nunique():,}")
    traits.to_parquet(V6 / "ev6_A_entrants.parquet", index=False)
    U = universe(levels, cells_all, a, flags, traits, cls)
    pickle.dump(U, open(V6 / "ev6_universe.pkl", "wb"))
    for k, v in U.items():
        print(f"--- {k}"); print(v.head(30).to_string(index=False))


if __name__ == "__main__":
    main()
