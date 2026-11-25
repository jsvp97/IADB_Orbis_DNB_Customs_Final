"""
wp_agro_v5_est.py  --  E9, E10 and E12.1 of especificaciones_estimaciones_v5_2026-11-24.md (E11 runs in Stata)
==============================================================================================================

    WP_YEARS=2012-2018 WP_SCOPES=agro python wp_agro_v5_est.py [e12_1 e9b e9a e9c e10c e9d e10a e10b e10d ...]

Reads data/intermediate/wp/v4/ (cells and classes of wp_agro_v4_data.py) and data/intermediate/wp/v5/classes_v5.parquet
(wp_agro_v5_data.py: source groups, threshold ladder, pooled thresholds, degree of processing, PCI, Rauch complete,
alternative US measures). Writes output/wp_2012_2018/agro/v5/v5_regs_<step>.pkl and v5_desc_<step>.pkl, read by
wp_agro_v5_workbook.py and wp_agro_v5_figures.py.

Conventions are those of v4 (wp_agro_v4_est.py): FE codes FE1 to FE6, clusters by origin and destination pair (by
product in the location regressions), ln of positive values only (no ln(1 + x), no asinh). Every variant is run and
kept, null and opposite-sign results included.
"""
from __future__ import annotations

import gc
import os
import pickle
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("WP_HS17", "1")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_common as W  # noqa: E402
import wp_agro_v4_est as E4  # noqa: E402

V4 = W.WP_INT / "v4"
V5 = W.WP_INT / "v5"
OUT = W.WP_OUT / "agro" / "v5"
OUT.mkdir(parents=True, exist_ok=True)
REGS = E4.REGS            # shared list: E4.fit appends to it
DESC: dict = {}
FE = E4.FE
FE_BODY = E4.FE_BODY
FE_FIG = ["FE4", "FE6"]
DEP = E4.DEP
REG = E4.REG
STAGES = ("Farm", "Processing")
LOC_FE = {"OYT": ("oy + type", ["oy", "type"], "origin x year + type of production"),
          "OYH": ("oy + hs2", ["oy", "hs2"], "origin x year + HS chapter"),
          "OY": ("oy", ["oy"], "origin x year")}


# ---------------------------------------------------------------------
# estimation with joint tests and slopes across groups
# ---------------------------------------------------------------------
def fit(data, dep, regs, fe, sheet, panel, col, sample, cluster="od", tests=(), joint=None, slope=None, est="OLS", fe_code=None):
    """As wp_agro_v4_est.fit, plus
       joint: list of regressors whose coefficients are tested jointly equal (Wald chi2, p value in tests)
       slope: {regressor: x} -> weighted least squares slope of the coefficients on x across regressors, with the
              standard error from the full covariance matrix (tests 'slope on ln KL' and 'slope SE' in rec['slope'])."""
    fe_str = FE.get(fe, fe)
    cols = [dep] + list(regs) + [c.strip() for c in fe_str.split("+") if c.strip()] + [cluster]
    dd = data.dropna(subset=list(dict.fromkeys(cols)))
    rec = dict(sheet=sheet, panel=panel, col=col, label=fe if fe in FE else "", fe=fe_code or (fe if fe in FE else fe_str),
               dep=dep, regs=list(regs), cluster=cluster, sample=sample, est=est, cells={}, tests={}, n=0, r2=np.nan,
               r2w=np.nan, singletons=0, status="", slope=None)
    t0 = time.time()
    try:
        m = W.feols(f"{dep} ~ {' + '.join(regs)} | {fe_str}", data=dd, vcov={"CRV1": cluster})
    except Exception as e:  # noqa: BLE001
        rec["status"] = "Not estimated: " + str(e)[:80]
        REGS.append(rec)
        print(f"   {sheet} {panel[:40]} {col}: FAILED {str(e)[:100]}")
        return rec
    from scipy.stats import chi2, norm
    b, se, p = m.coef(), m.se(), m.pvalue()
    V = pd.DataFrame(np.asarray(m._vcov), index=b.index, columns=b.index)
    rec["cells"] = {v: (float(b[v]), float(se[v]), float(p[v])) for v in regs if v in b.index and np.isfinite(se[v]) and se[v] > 0}
    for name, (v1, v2) in tests:
        if v1 in rec["cells"] and v2 in rec["cells"]:
            sd = float(np.sqrt(V.loc[v1, v1] + V.loc[v2, v2] - 2 * V.loc[v1, v2]))
            rec["tests"][name] = float(2 * (1 - norm.cdf(abs((b[v1] - b[v2]) / sd)))) if sd > 0 else np.nan
    if joint:
        jv = [v for v in joint if v in rec["cells"]]
        if len(jv) >= 2:
            R = np.zeros((len(jv) - 1, len(jv)))
            for i in range(len(jv) - 1):
                R[i, i], R[i, i + 1] = 1, -1
            bb = b[jv].values; VV = V.loc[jv, jv].values
            try:
                w = float((R @ bb) @ np.linalg.pinv(R @ VV @ R.T) @ (R @ bb))
                rec["tests"]["all groups equal"] = float(chi2.sf(w, len(jv) - 1))
            except Exception:  # noqa: BLE001
                pass
    if slope:
        # slope of the group coefficients on ln KL across groups: weighted by the exports of each group (the marker size
        # of the figure) and unweighted; standard errors from the full covariance matrix of the group coefficients
        sv = [v for v in slope if v in rec["cells"]]
        if len(sv) >= 3:
            x = np.array([slope[v][0] for v in sv]); w = np.array([slope[v][1] for v in sv]); bb = b[sv].values; VV = V.loc[sv, sv].values
            Z = np.column_stack([np.ones(len(sv)), x])
            rec["slope"] = {}
            for k, ww in (("export weighted", w / w.sum()), ("unweighted", np.ones(len(sv)))):
                Wt = np.diag(ww)
                A = np.linalg.pinv(Z.T @ Wt @ Z) @ Z.T @ Wt
                g = A @ bb; Vg = A @ VV @ A.T
                s = float(np.sqrt(max(Vg[1, 1], 0)))
                rec["slope"][k] = (float(g[1]), s, float(2 * (1 - norm.cdf(abs(g[1] / s)))) if s > 0 else np.nan, len(sv))
                rec["tests"][f"slope of the coefficients on ln KL = 0, {k}"] = rec["slope"][k][2]
    rec.update(n=int(m._N), r2=float(getattr(m, "_r2", np.nan)), r2w=float(getattr(m, "_r2_within", np.nan)),
               singletons=int(len(getattr(m, "_na_index", []))))
    REGS.append(rec)
    print(f"   {sheet:6s} {panel[:50]:50s} {str(col):>8s}: N={rec['n']:>8,} "
          + " ".join(f"{v[-14:]}:{c[0]:+.3f}" for v, c in list(rec["cells"].items())[:3]) + f" ({time.time() - t0:.0f}s)")
    del m; gc.collect()
    return rec


def load():
    import json
    cls = pd.read_parquet(V5 / "classes_v5.parquet")
    cls.attrs.update(json.load(open(V5 / "classes_v5_cuts.json", encoding="utf-8")))
    cls.attrs["pooled"] = [tuple(x) for x in cls.attrs["pooled"]]
    od, op, _ = E4.load_cells()
    new = [c for c in cls.columns if c not in od.columns or c == "hs"]
    od = od.merge(cls[new], on="hs", how="left")
    op = op.merge(cls[[c for c in cls.columns if c not in op.columns or c == "hs"]], on="hs", how="left")
    return od, op, cls


def ladder_cuts(cls: pd.DataFrame, stage: str) -> list[tuple[str, str]]:
    """(column, label) of every two-group cut of E9a for one stage, in the order of the ladder."""
    return [(c, cls.attrs["labels"][f"{stage}|{c}"]) for c in cls.attrs["ladder"][stage]]


def composition(cls: pd.DataFrame, col: str, stage: str | None, cut: str) -> list[dict]:
    """Products, export share and type of production of each group of a cut (spec rule: say what a cut coincides with)."""
    x = cls[cls["stage"] == stage] if stage else cls[cls["stage"].isin(STAGES)]
    V = x["v_1218"].sum()
    rows = []
    for g, y in x.groupby(col):
        r = {"Cut": cut, "Stage": stage or "Pooled", "Group": g, "Products": len(y), "Share of stage exports (%)": 100 * y["v_1218"].sum() / V,
             "Capital per worker, min": y["kl"].min(), "Capital per worker, max": y["kl"].max()}
        for ty in E4.TYPES.values():
            r[f"{ty}, % of group exports"] = 100 * y.loc[y["type"] == ty, "v_1218"].sum() / max(y["v_1218"].sum(), 1)
        if col not in ("high_mean", "high_median"):
            r["high_mean High, % of products"] = 100 * (y["high_mean"] == "High").mean()
            r["high_median High, % of products"] = 100 * (y["high_median"] == "High").mean()
        if stage is None:
            r["Farm, % of products"] = 100 * (y["stage"] == "Farm").mean()
        rows.append(r)
    return rows


# ---------------------------------------------------------------------
# E12.1 location by stage (and every cut of the ladder, E9a location part)
# ---------------------------------------------------------------------
def loc_regs(d: pd.DataFrame, cls: pd.DataFrame, stage: str) -> dict[str, list[str]]:
    R = {"lnKL": ["lnkl"]}
    for c, lab in ladder_cuts(cls, stage):
        d[f"hi_{c}"] = (d[c] == "High").astype(float)
        R[c] = [f"hi_{c}"]
    for c in ("tercile", "quartile", "quintile"):
        col = f"{c}_stage" if c != "quintile" else "quintile"
        vals = sorted(v for v in d[col].dropna().unique())
        for v in vals[1:]:
            d[f"{c}{int(v)}"] = (d[col] == v).astype(float)
        R[c + "s"] = [f"{c}{int(v)}" for v in vals[1:]]
    return R


def e12_1(op: pd.DataFrame, cls: pd.DataFrame) -> None:
    smp = "origin x product x year cells with positive exports, classified products"
    for st in STAGES:
        d = op[op["lnkl"].notna() & (op["stage"] == st)].copy()
        R = loc_regs(d, cls, st)
        for sheet, dep, sub, sl in (("E12a", "D", d, smp), ("E12b", "lnN", d[d["N"] >= 1], smp + ", at least one MNE"),
                                    ("E12b", "S", d, smp), ("E12c", "DF", d, smp), ("E12c", "DD", d, smp)):
            for fk, (fe, fcols, fl) in LOC_FE.items():
                for rk, regs in R.items():
                    fit(sub, dep, regs, fe, sheet, f"{st} stage, {dep}, FE {fl}", rk, sl + f", {st.lower()} stage", cluster="hs", fe_code=fl)
            if sheet == "E12a":
                for fk, (fe, fcols, fl) in LOC_FE.items():
                    for rk in ("lnKL", "high_agg", "high_wmed", "quintiles"):
                        E4.logit_ame(sub, dep, R[rk], fcols, "E12a", f"{st} stage, logit, FE {fl}", rk, sl + f", {st.lower()} stage")
        # first entry by stage (E5d by stage)
        o = op.sort_values(["country_orig", "hs", "year"]).copy()
        o["prior_mne"] = o.groupby(["country_orig", "hs"])["D"].transform(lambda s: s.shift(1).cummax()).fillna(0)
        risk = o[(o["year"] >= 2013) & (o["prior_mne"] == 0) & o["lnkl"].notna() & (o["stage"] == st)].copy()
        R2 = loc_regs(risk, cls, st)
        for fk, (fe, fcols, fl) in LOC_FE.items():
            for rk in ("lnKL", "high_agg", "high_wmed", "quintiles"):
                fit(risk, "D", R2[rk], fe, "E12d", f"{st} stage, first entry, FE {fl}", rk,
                    f"cells at risk (no MNE in any earlier year), 2013 to 2018, {st.lower()} stage", cluster="hs", fe_code=fl)
    # descriptive: MNE presence and share by stage and group (the raw pattern behind the regressions)
    rows = []
    for st in STAGES:
        d = op[op["lnkl"].notna() & (op["stage"] == st)]
        for col in ("high_mean", "high_median", "quintile"):
            for g, y in d.groupby(col):
                rows.append({"Stage": st, "Cut": col, "Group": g, "Cells": len(y), "Share of cells with an MNE (%)": 100 * y["D"].mean(),
                             "MNE share of exports (%)": 100 * y["XM"].sum() / y["X"].sum(), "Mean number of MNEs": y["N"].mean()})
    DESC["E12_desc"] = pd.DataFrame(rows)


# ---------------------------------------------------------------------
# E9a threshold ladder (heterogeneity by stage), E9c pooled thresholds
# ---------------------------------------------------------------------
def e9a(od: pd.DataFrame, cls: pd.DataFrame) -> None:
    comp = []
    for st in STAGES:
        for c, lab in ladder_cuts(cls, st):
            comp += composition(cls, c, st, lab)
        for c in ("tercile_stage", "quartile_stage"):
            comp += composition(cls, c, st, c.replace("_stage", "s"))
    DESC["E9_composition"] = pd.DataFrame(comp)
    for reg in ("lnN", "D"):
        for depk, (dep, dl) in DEP.items():
            base = E4.base_sample(od, reg, dep)
            for st in STAGES:
                d = base[base["stage"] == st].copy()
                smp = REG[reg][1] + f", {st.lower()} stage"
                for c, lab in ladder_cuts(cls, st):
                    regs = E4.interact(d, reg, c, {"hi": "High", "lo": "Low"}, f"{reg}_{c}")
                    for fe in FE_BODY:
                        fit(d, dep, regs, fe, "E9a", f"{st} stage, {reg} x high/low, threshold: {lab}, {dl}", fe, smp,
                            tests=[("high = low", (f"{reg}_{c}_hi", f"{reg}_{c}_lo"))])
                for c in ("tercile_stage", "quartile_stage"):
                    g = sorted(d[c].dropna().unique())
                    regs = E4.interact(d, reg, c, {f"g{int(v)}": v for v in g}, f"{reg}_{c}")
                    for fe in FE_BODY:
                        fit(d, dep, regs, fe, "E9a", f"{st} stage, {reg} x {c.replace('_stage', 's')}, {dl}", fe, smp,
                            tests=[(f"lowest = group {int(v)}", (regs[0], r)) for v, r in zip(g[1:], regs[1:])], joint=regs)
                del d; gc.collect()


def e9c(od: pd.DataFrame, cls: pd.DataFrame) -> None:
    comp = []
    for c, lab in cls.attrs["pooled"]:
        comp += composition(cls, c, None, lab)
    DESC["E9c_composition"] = pd.DataFrame(comp)
    for reg in ("lnN", "D"):
        for depk, (dep, dl) in DEP.items():
            d = E4.base_sample(od, reg, dep).copy()
            smp = REG[reg][1]
            for c, lab in cls.attrs["pooled"]:
                regs = E4.interact(d, reg, c, {"hi": "High", "lo": "Low", "nc": "Not classified"}, f"{reg}_{c}")
                for fe in FE_BODY:
                    fit(d, dep, regs, fe, "E9c", f"Pooled stages, {reg} x high/low, threshold: {lab}, {dl}", fe, smp,
                        tests=[("high = low", (f"{reg}_{c}_hi", f"{reg}_{c}_lo"))])
            del d; gc.collect()


# ---------------------------------------------------------------------
# E9b flexible by source group (farm type or industry)
# ---------------------------------------------------------------------
def e9b(od: pd.DataFrame, cls: pd.DataFrame) -> None:
    g = cls[cls["stage"].isin(STAGES)].groupby(["stage", "src_id"]).agg(
        label=("src_label", "first"), codes=("kl_source", "first"), kl=("kl", "first"), products=("hs", "size"), v=("v_1218", "sum"),
        field=("type", lambda s: (s == E4.TYPES["field"]).sum())).reset_index()
    g["Share of stage exports (%)"] = 100 * g["v"] / g.groupby("stage")["v"].transform("sum")
    g["lnkl"] = np.log(g["kl"])
    DESC["E9b_groups"] = g
    SUPPORT.clear()
    for reg in ("lnN", "D"):
        for depk, (dep, dl) in DEP.items():
            base = E4.base_sample(od, reg, dep)
            for st in STAGES:
                d = base[base["stage"] == st].copy()
                gg = g[g["stage"] == st]
                regs, xs = [], {}
                for _, r in gg.iterrows():
                    name = f"{reg}_src{int(r['src_id'])}"
                    d[name] = d[reg] * (d["src_id"] == r["src_id"])
                    if d[name].abs().sum() > 0:
                        regs.append(name); xs[name] = (r["lnkl"], r["v"])
                        m = d["src_id"] == r["src_id"]
                        SUPPORT.append({"stage": st, "regressor": reg, "panel": dl, "src_id": int(r["src_id"]), "cells": int(m.sum()),
                                        "origin and destination pairs (clusters)": int(d.loc[m, "od"].nunique()),
                                        "origins": int(d.loc[m, "country_orig"].nunique())})
                for fe in FE_FIG + ["FE3", "FE5"]:
                    fit(d, dep, regs, fe, "E9b", f"{st} stage, {reg} x farm type or industry, {dl}", fe, REG[reg][1] + f", {st.lower()} stage",
                        joint=regs, slope=xs)
                del d; gc.collect()
    DESC["E9b_support"] = pd.DataFrame(SUPPORT)


SUPPORT: list = []


# ---------------------------------------------------------------------
# E10c degree of processing (and the generic E4/E5 style runs used by E10a, E10b, E10d)
# ---------------------------------------------------------------------
def het_generic(od: pd.DataFrame, sheet: str, col: str, groups: dict[str, str], lab: str, tests: list, extra_sample: str = "") -> None:
    for reg in ("lnN", "D"):
        for depk, (dep, dl) in DEP.items():
            d = E4.base_sample(od, reg, dep).copy()
            regs = E4.interact(d, reg, col, groups, f"{reg}_{col}")
            if d[col].isna().any() or (~d[col].isin(groups.values())).any():
                d[f"{reg}_{col}_na"] = d[reg] * (~d[col].isin(groups.values())); regs.append(f"{reg}_{col}_na")
            for fe in FE_BODY:
                fit(d, dep, regs, fe, sheet, f"{reg} x {lab}, {dl}", fe, REG[reg][1] + extra_sample,
                    tests=[(n, (f"{reg}_{col}_{a}", f"{reg}_{col}_{b}")) for n, (a, b) in tests], joint=regs[:len(groups)])
            del d; gc.collect()


def loc_generic(op: pd.DataFrame, sheet: str, specs: dict[str, list[str]], prep, lab: str) -> None:
    d = op.copy()
    prep(d)
    smp = "origin x product x year cells with positive exports"
    for dep, sub, sl in (("D", d, smp), ("lnN", d[d["N"] >= 1], smp + ", at least one MNE"), ("S", d, smp)):
        for fk, (fe, fcols, fl) in LOC_FE.items():
            for rk, regs in specs.items():
                fit(sub, dep, regs, fe, sheet, f"Location, {lab}, {dep}, FE {fl}", rk, sl, cluster="hs", fe_code=fl)


def e10c(od: pd.DataFrame, op: pd.DataFrame, cls: pd.DataFrame) -> None:
    G = {"prim": "Primary", "first": "First processing", "further": "Further processing"}
    DESC["E10c_composition"] = pd.DataFrame(composition(cls.assign(stage="Farm"), "processing_degree", "Farm", "degree of processing"))
    het_generic(od, "E10c", "processing_degree", G, "degree of processing",
                [("primary = first processing", ("prim", "first")), ("primary = further processing", ("prim", "further")),
                 ("first = further processing", ("first", "further"))])

    def prep(d):
        d["deg_first"] = (d["processing_degree"] == "First processing").astype(float)
        d["deg_further"] = (d["processing_degree"] == "Further processing").astype(float)
        d.loc[d["processing_degree"] == "Not classified", ["deg_first", "deg_further"]] = np.nan
    loc_generic(op, "E10c", {"degree": ["deg_first", "deg_further"]}, prep, "degree of processing (primary omitted)")


# ---------------------------------------------------------------------
def main() -> None:
    which = sys.argv[1:] or ["e12_1", "e9b", "e9a", "e9c", "e10c"]
    od, op, cls = load()
    print(f"odpy {len(od):,}, opy {len(op):,}")
    steps = {"e12_1": lambda: e12_1(op, cls), "e9b": lambda: e9b(od, cls), "e9a": lambda: e9a(od, cls), "e9c": lambda: e9c(od, cls),
             "e10c": lambda: e10c(od, op, cls)}
    extra = {}
    try:
        import wp_agro_v5_est2 as X  # E9d, E10a, E10b, E10d (need the downloaded inputs)
        extra = X.steps(od, op, cls, fit, het_generic, loc_generic, DESC)
    except ImportError:
        pass
    steps.update(extra)
    for k in which:
        print(f"== {k}")
        REGS.clear(); DESC.clear()
        steps[k]()
        with open(OUT / f"v5_regs_{k}.pkl", "wb") as fh:
            pickle.dump(list(REGS), fh)
        with open(OUT / f"v5_desc_{k}.pkl", "wb") as fh:
            pickle.dump(dict(DESC), fh)
        print(f"saved {len(REGS)} regressions, {len(DESC)} descriptive tables ({k})")


if __name__ == "__main__":
    main()
