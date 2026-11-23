"""
wp_agro_v4_est.py  --  E1 to E5 and E7 of especificaciones_estimaciones_v4_2026-11-17.md
=========================================================================================

    WP_YEARS=2012-2018 WP_SCOPES=agro python wp_agro_v4_est.py          (everything; E6 runs in Stata, wp_agro_v4_event.do)

Reads data/intermediate/wp/v4/ (wp_agro_v4_data.py). Writes output/wp_2012_2018/agro/v4/:
  v4_regs.pkl     one dict per regression (sheet, panel, column, FE code, dependent variable, regressors, coefficients,
                  standard errors, p values, tests, N, R2, within R2, singletons, cluster, sample, estimator)
  v4_desc.pkl     the descriptive tables (E1, E3, E5d counts, E7 shares, Samples)
The workbook is written by wp_agro_v4_workbook.py.

Fixed effects (spec 0.4): FE1 O+D+P+Y, FE2 OY+DY+P, FE3 ODP+Y, FE4 ODP+ODY, FE5 FE4+OPY, FE6 FE5+DPY. Within one origin
FE6 leaves one observation per fixed effect and is not estimated. Standard errors clustered by origin and destination
pair (by destination within one origin, by product in the location regressions).
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

V4 = W.WP_INT / "v4"
OUT = W.WP_OUT / "agro" / "v4"
OUT.mkdir(parents=True, exist_ok=True)
REGS: list[dict] = []
DESC: dict = {}
COUNTRY = {"ARG": "Argentina", "CHL": "Chile", "COL": "Colombia", "CRI": "Costa Rica", "DOM": "Dominican Republic",
           "PER": "Peru", "PRY": "Paraguay", "SLV": "El Salvador", "URY": "Uruguay"}
FE = {"FE1": "country_orig + country_dest + hs + year", "FE2": "oy + dy + hs", "FE3": "odp + year", "FE4": "odp + ody",
      "FE5": "odp + ody + opy", "FE6": "odp + ody + opy + dpy"}
FE_ALL = ["FE1", "FE2", "FE3", "FE4", "FE5", "FE6"]
FE_BODY = ["FE3", "FE4", "FE5", "FE6"]
FE_CTRY = ["FE3", "FE4", "FE5"]
TYPES = {"field": "Field crops", "horti": "Horticultural and plantation crops", "live": "Livestock and fisheries",
         "proc": "Other processed food and beverages"}


# ---------------------------------------------------------------------
# estimation
# ---------------------------------------------------------------------
def fit(data, dep, regs, fe, sheet, panel, col, sample, cluster="od", tests=(), est="OLS", label=None, fe_code=None):
    """One regression; appended to REGS. fe is a pyfixest FE string or a code of FE."""
    fe_str = FE.get(fe, fe)
    cols = [dep] + [r for r in regs] + [c.strip() for c in fe_str.split("+") if c.strip()] + [cluster]
    dd = data.dropna(subset=list(dict.fromkeys(cols)))
    rec = dict(sheet=sheet, panel=panel, col=col, label=label or (fe if fe in FE else ""), fe=fe_code or (fe if fe in FE else fe_str),
               dep=dep, regs=list(regs), cluster=cluster, sample=sample, est=est, cells={}, tests={}, n=0, r2=np.nan,
               r2w=np.nan, singletons=0, status="")
    t0 = time.time()
    try:
        fml = f"{dep} ~ {' + '.join(regs)} | {fe_str}"
        if est == "PPML":
            import pyfixest as pf
            m = pf.fepois(fml, data=dd, vcov={"CRV1": cluster})
        else:
            m = W.feols(fml, data=dd, vcov={"CRV1": cluster})
    except Exception as e:  # noqa: BLE001
        rec["status"] = "Not estimated: " + str(e)[:80]
        REGS.append(rec)
        print(f"   {sheet} {panel[:40]} {col}: FAILED {str(e)[:100]}")
        return rec
    b, se, p = m.coef(), m.se(), m.pvalue()
    rec["cells"] = {v: (float(b[v]), float(se[v]), float(p[v])) for v in regs if v in b.index}
    if tests:
        from scipy.stats import norm
        V = np.asarray(m._vcov); ix = list(b.index)
        for name, (v1, v2) in tests:
            if v1 in ix and v2 in ix:
                i, j = ix.index(v1), ix.index(v2)
                sd = float(np.sqrt(V[i, i] + V[j, j] - 2 * V[i, j]))
                rec["tests"][name] = float(2 * (1 - norm.cdf(abs((b[v1] - b[v2]) / sd)))) if sd > 0 else np.nan
    rec.update(n=int(m._N), r2=float(getattr(m, "_r2", np.nan)), r2w=float(getattr(m, "_r2_within", np.nan)),
               singletons=int(len(getattr(m, "_na_index", []))))
    if est == "PPML":
        rec["r2"] = float(getattr(m, "_pseudo_r2", np.nan)) if hasattr(m, "_pseudo_r2") else np.nan
    REGS.append(rec)
    print(f"   {sheet:5s} {panel[:44]:44s} {str(col):>5s}: N={rec['n']:>8,} "
          + " ".join(f"{v}:{c[0]:+.3f}" for v, c in list(rec["cells"].items())[:4]) + f" ({time.time() - t0:.0f}s)")
    del m; gc.collect()
    return rec


def logit_ame(data, dep, regs, fe_cols, sheet, panel, col, sample):
    """Logit with origin x year and type (or HS2) dummies, average marginal effects, clustered by product."""
    import statsmodels.api as sm
    dd = data.dropna(subset=[dep] + regs + fe_cols + ["hs"]).copy()
    X = pd.get_dummies(dd[fe_cols].astype(str), drop_first=True, dtype=float)
    X = pd.concat([dd[regs].astype(float), X], axis=1)
    X = sm.add_constant(X, has_constant="add")
    rec = dict(sheet=sheet, panel=panel, col=col, label="Logit", fe=" + ".join(fe_cols), dep=dep, regs=list(regs), cluster="hs",
               sample=sample, est="Logit, average marginal effects", cells={}, tests={}, n=0, r2=np.nan, r2w=np.nan, singletons=0, status="")
    try:
        groups = pd.factorize(dd["hs"])[0]
        r = sm.Logit(dd[dep].astype(float), X).fit(disp=0, maxiter=200, cov_type="cluster", cov_kwds={"groups": groups})
        me = r.get_margeff(at="overall")
        s = me.summary_frame()
        for v in regs:
            if v in s.index:
                rec["cells"][v] = (float(s.loc[v, "dy/dx"]), float(s.loc[v, "Std. Err."]), float(s.loc[v, "Pr(>|z|)"]))
        rec.update(n=int(r.nobs), r2=float(r.prsquared))
    except Exception as e:  # noqa: BLE001
        rec["status"] = "Not estimated: " + str(e)[:80]
    REGS.append(rec)
    print(f"   {sheet:5s} {panel[:44]:44s} {str(col):>5s}: logit N={rec['n']:>8,} " + " ".join(f"{v}:{c[0]:+.3f}" for v, c in rec["cells"].items()))
    return rec


# ---------------------------------------------------------------------
# data
# ---------------------------------------------------------------------
def load_cells() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cls = pd.read_parquet(V4 / "classes.parquet")
    od = pd.read_parquet(V4 / "odpy.parquet").merge(cls, on="hs", how="left")
    assert od["type"].notna().all()
    od["ot_"] = od["country_orig"] + "_" + od["year"].astype(str)
    od["oy"] = od["ot_"]
    od["dy"] = od["country_dest"] + "_" + od["year"].astype(str)
    od["od"] = od["country_orig"] + "_" + od["country_dest"]
    od["odp"] = od["od"] + "_" + od["hs"]
    od["ody"] = od["od"] + "_" + od["year"].astype(str)
    od["opy"] = od["country_orig"] + "_" + od["hs"] + "_" + od["year"].astype(str)
    od["dpy"] = od["country_dest"] + "_" + od["hs"] + "_" + od["year"].astype(str)
    op = pd.read_parquet(V4 / "opy.parquet").merge(cls, on="hs", how="left")
    op["oy"] = op["country_orig"] + "_" + op["year"].astype(str)
    return od, op, cls


def interact(d: pd.DataFrame, reg: str, col: str, groups: dict[str, str], prefix: str) -> list[str]:
    """reg x 1[col == value] for each group; returns the new column names (only groups present)."""
    out = []
    for k, v in groups.items():
        ind = (d[col] == v).astype(float)
        if ind.sum() == 0:
            continue
        name = f"{prefix}_{k}"
        d[name] = d[reg] * ind
        out.append(name)
    return out


REG = {"lnN": ("lnN", "N >= 1"), "D": ("D", "all cells with positive exports")}
DEP = {"all": ("lnX", "ln exports, all firms"), "local": ("lnXL", "ln exports, local firms")}


def base_sample(od: pd.DataFrame, reg: str, dep: str) -> pd.DataFrame:
    s = od[od["N"] >= 1] if reg == "lnN" else od
    return s[s[dep].notna()]


# ---------------------------------------------------------------------
# E1 sector context
# ---------------------------------------------------------------------
SECTORS = [("Agriculture", lambda h: (h >= 1) & (h <= 24)), ("Mining and fuels", lambda h: (h >= 25) & (h <= 27)),
           ("of which fuels", lambda h: h == 27), ("Manufacturing", lambda h: (h >= 28) & (h <= 97))]


def e1() -> None:
    s = pd.read_parquet(V4 / "sector.parquet")
    s["h2"] = pd.to_numeric(s["hs2"], errors="coerce")
    s = s[s["h2"].between(1, 97)].copy()                       # drops HS 98-99 and invalid chapter 00 codes
    grp = s["ID_Orbis_DNB"].where(s["ID_Orbis_DNB"].fillna("") != "", s["parent_key"])
    s["group"] = grp.where(grp.fillna("") != "", s["firm"])

    def table(d: pd.DataFrame, years: int) -> pd.DataFrame:
        rows = []
        for o in [None] + sorted(d["country_orig"].unique()):
            x = d if o is None else d[d["country_orig"] == o]
            tot = x["value_fob"].sum(); tot_m = x.loc[x["ot"] != "local", "value_fob"].sum()
            for sec, f in SECTORS + [("Total", lambda h: (h >= 1) & (h <= 97))]:
                y = x[f(x["h2"])]
                v = y["value_fob"].sum()
                vm = y.loc[y["ot"] != "local", "value_fob"].sum()
                nexp = y.groupby("year")["firm"].nunique().mean()
                rows.append({"Origin": "LAC9" if o is None else COUNTRY[o], "Sector": sec, "Exports (US$ billion)": v / 1e9 / years,
                             "Exporters": nexp, "MNE share (%)": 100 * vm / v if v else np.nan,
                             "Foreign MNE share (%)": 100 * y.loc[y["ot"] == "ext", "value_fob"].sum() / v if v else np.nan,
                             "Domestic MNE share (%)": 100 * y.loc[y["ot"] == "dom", "value_fob"].sum() / v if v else np.nan,
                             "Share of total exports (%)": 100 * v / tot if tot else np.nan,
                             "Share of MNE exports (%)": 100 * vm / tot_m if tot_m else np.nan})
        return pd.DataFrame(rows)
    DESC["E1a"] = table(s[s["year"] == 2018], 1)
    DESC["E1b"] = table(s, 7)
    rows = []
    x18 = s[s["year"] == 2018]
    for o in [None] + sorted(x18["country_orig"].unique()):
        x = x18 if o is None else x18[x18["country_orig"] == o]
        for sec, f in SECTORS:
            y = x[f(x["h2"])]
            rows.append({"Origin": "LAC9" if o is None else COUNTRY[o], "Sector": sec,
                         "Foreign MNE affiliates": y.loc[y["ot"] == "ext", "firm"].nunique(),
                         "Domestic MNE affiliates": y.loc[y["ot"] == "dom", "firm"].nunique(),
                         "Multinational groups": y.loc[y["ot"] != "local", "group"].nunique(),
                         "Local exporters": y.loc[y["ot"] == "local", "firm"].nunique()})
    DESC["E1c"] = pd.DataFrame(rows)
    print(DESC["E1a"][DESC["E1a"]["Origin"] == "LAC9"].round(1).to_string())


# ---------------------------------------------------------------------
# E2 baseline
# ---------------------------------------------------------------------
def e2(od: pd.DataFrame) -> None:
    for sheet, dep, reg, fes in (("E2a", "lnX", "lnN", FE_ALL), ("E2b", "lnX", "D", FE_ALL),
                                 ("E2c", "lnXL", "lnN", FE_ALL), ("E2d", "lnXL", "D", FE_ALL)):
        d = base_sample(od, reg, dep)
        for fe in fes:
            fit(d, dep, [reg], fe, sheet, "Main", fe, REG[reg][1] + (", positive local exports" if dep == "lnXL" else ""))
    # E2e: zeros of local exports. No ln(1 + x) or asinh: the probability of positive local exports (linear probability
    # model) and PPML on levels
    for reg in ("lnN", "D"):
        d = od[od["N"] >= 1] if reg == "lnN" else od
        d = d.assign(anyXL=(d["XL"] > 0).astype(float))
        for fe in FE_ALL:
            fit(d, "anyXL", [reg], fe, "E2e", f"Positive local exports, regressor {reg}", fe, REG[reg][1] + ", zeros of local exports included")
        fit(d, "XL", [reg], "FE4", "E2e", f"PPML, local exports in levels, regressor {reg}", "FE4",
            REG[reg][1] + ", zeros of local exports included", est="PPML")
    # E2f: number of local exporters and exports per local exporter
    for dep, dl in (("lnNL", "ln number of local exporters"), ("lnXLpf", "ln exports per local exporter")):
        for reg in ("lnN", "D"):
            d = (od[od["N"] >= 1] if reg == "lnN" else od)
            for fe in FE_BODY:
                fit(d, dep, [reg], fe, "E2f", f"{dl}, regressor {reg}", fe, REG[reg][1] + ", at least one local exporter")
    # E2g: by origin
    for reg in ("lnN", "D"):
        for o in sorted(od["country_orig"].unique()):
            d = base_sample(od[od["country_orig"] == o], reg, "lnX")
            for fe in FE_CTRY:
                fit(d, "lnX", [reg], fe, "E2g", f"{COUNTRY[o]}, regressor {reg}", fe, f"origin {o}, " + REG[reg][1], cluster="country_dest")


# ---------------------------------------------------------------------
# E3 capital intensity, descriptive
# ---------------------------------------------------------------------
def e3(cls: pd.DataFrame) -> None:
    s = pd.read_parquet(V4 / "sector.parquet")
    s = s[pd.to_numeric(s["hs2"], errors="coerce").between(1, 24)].rename(columns={"hs07_6d": "hs"})
    s = s.merge(cls[["hs", "stage", "type", "kl", "quintile", "high_mean", "high_median"]], on="hs", how="left")
    rows = []
    for per, x in (("2018", s[s["year"] == 2018]), ("2012 to 2018, annual average", s)):
        ny = x["year"].nunique()
        V = x["value_fob"].sum()
        for st in ("Farm", "Processing"):
            xs = x[x["stage"] == st]
            Vs = xs["value_fob"].sum()
            for q in range(1, 6):
                y = xs[xs["quintile"] == q]
                if not len(y):
                    rows.append({"Period": per, "Stage": st, "Quintile": q, "Products": 0}); continue
                v = y["value_fob"].sum()
                hs_v = y.groupby("hs")["value_fob"].sum()
                kl = cls.set_index("hs").loc[hs_v.index, "kl"]
                rows.append({"Period": per, "Stage": st, "Quintile": q, "Products": y["hs"].nunique(),
                             "Share of agricultural exports (%)": 100 * v / V, "Share of the stage (%)": 100 * v / Vs,
                             "MNE share (%)": 100 * y.loc[y["ot"] != "local", "value_fob"].sum() / v,
                             "Foreign MNE share (%)": 100 * y.loc[y["ot"] == "ext", "value_fob"].sum() / v,
                             "MNE exporters": y[y["ot"] != "local"].groupby("year")["firm"].nunique().sum() / ny,
                             "Capital per worker, mean weighted by exports (US$ thousand)": float(np.average(kl, weights=hs_v)),
                             "Capital per worker, range (US$ thousand)": f"{kl.min():.0f} to {kl.max():.0f}"})
    DESC["E3a"] = pd.DataFrame(rows)
    # E3b: one row per product
    p = []
    for per, x in (("2018", s[s["year"] == 2018]), ("1218", s)):
        g = x.groupby("hs").agg(v=("value_fob", "sum"))
        g["mne"] = x[x["ot"] != "local"].groupby("hs")["value_fob"].sum()
        g["ext"] = x[x["ot"] == "ext"].groupby("hs")["value_fob"].sum()
        g = g.fillna(0)
        p.append(pd.DataFrame({f"exports_{per}": g["v"], f"mne_share_{per}": 100 * g["mne"] / g["v"], f"foreign_share_{per}": 100 * g["ext"] / g["v"]}))
    b = cls[["hs", "description", "stage", "type", "kl", "lnkl", "quintile", "high_mean", "high_median"]].set_index("hs").join(p[0]).join(p[1])
    DESC["E3b"] = b.reset_index()
    # E3c: coverage
    x = s
    V = x["value_fob"].sum()
    cov = x.groupby(["stage", "type"]).agg(exports=("value_fob", "sum"), products=("hs", "nunique")).reset_index()
    cov["Share of agricultural exports 2012 to 2018 (%)"] = 100 * cov["exports"] / V
    cov["exports"] = cov["exports"] / 1e9
    DESC["E3c"] = cov.rename(columns={"exports": "Exports 2012 to 2018 (US$ billion)", "products": "Products", "stage": "Stage", "type": "Type of production"})
    nc = cls[cls["stage"] == "Not classified"][["hs", "description", "type", "v_1218", "v_2018"]].copy()
    nc[["v_1218", "v_2018"]] = nc[["v_1218", "v_2018"]] / 1e6
    DESC["E3c_list"] = nc.rename(columns={"v_1218": "Exports 2012 to 2018 (US$ million)", "v_2018": "Exports 2018 (US$ million)"})
    # E3d: type x high/low, both thresholds
    rows = []
    for per, x in (("2018", s[s["year"] == 2018]), ("2012 to 2018", s)):
        V = x["value_fob"].sum()
        for thr in ("high_mean", "high_median"):
            for (ty, hl), y in x.groupby(["type", thr]):
                v = y["value_fob"].sum(); hs_v = y.groupby("hs")["value_fob"].sum()
                kl = cls.set_index("hs").loc[hs_v.index, "kl"]
                rows.append({"Period": per, "Threshold": "Aggregate ratio of the stage" if thr == "high_mean" else "Export weighted median of the stage",
                             "Type of production": ty, "Capital intensity": hl, "Products": y["hs"].nunique(), "Share of exports (%)": 100 * v / V,
                             "MNE share (%)": 100 * y.loc[y["ot"] != "local", "value_fob"].sum() / v,
                             "Foreign MNE share (%)": 100 * y.loc[y["ot"] == "ext", "value_fob"].sum() / v,
                             "Capital per worker (US$ thousand)": float(np.average(kl.fillna(0), weights=hs_v)) if kl.notna().any() else np.nan})
    DESC["E3d"] = pd.DataFrame(rows)


# ---------------------------------------------------------------------
# E4 heterogeneity by capital intensity
# ---------------------------------------------------------------------
def e4(od: pd.DataFrame) -> None:
    HL = {"hi": "High", "lo": "Low", "nc": "Not classified"}
    ST = {"farm_hi": ("Farm", "High"), "farm_lo": ("Farm", "Low"), "proc_hi": ("Processing", "High"), "proc_lo": ("Processing", "Low")}
    for reg in ("lnN", "D"):
        for depk, (dep, dl) in DEP.items():
            d = base_sample(od, reg, dep).copy()
            smp = REG[reg][1]
            # E4a pooled high/low
            for thr, tl in (("high_mean", "aggregate ratio"), ("high_median", "median")):
                regs = interact(d, reg, thr, HL, f"{reg}_{thr}")
                for fe in FE_BODY:
                    fit(d, dep, regs, fe, "E4a", f"{reg} x high/low ({tl}), {dl}", fe, smp,
                        tests=[("high = low", (f"{reg}_{thr}_hi", f"{reg}_{thr}_lo"))])
            # E4b continuous
            dc = d[d["lnkl"].notna()].copy()
            for kv, kl in (("lnkl", "ln capital per worker"), ("lnkl_dm", "ln capital per worker, demeaned within stage")):
                dc[f"{reg}_x_{kv}"] = dc[reg] * dc[kv]
                for fe in FE_BODY:
                    fit(dc, dep, [reg, f"{reg}_x_{kv}"], fe, "E4b", f"{reg} and {reg} x {kl}, {dl}", fe, smp + ", classified products")
            # E4c stage x high/low
            for thr, tl in (("high_mean", "aggregate ratio"), ("high_median", "median")):
                regs = []
                for k, (st, hl) in ST.items():
                    ind = ((d["stage"] == st) & (d[thr] == hl)).astype(float)
                    d[f"{reg}_{thr}_{k}"] = d[reg] * ind; regs.append(f"{reg}_{thr}_{k}")
                d[f"{reg}_{thr}_nc"] = d[reg] * (d["stage"] == "Not classified"); regs.append(f"{reg}_{thr}_nc")
                for fe in FE_BODY:
                    fit(d, dep, regs, fe, "E4c", f"{reg} x stage x high/low ({tl}), {dl}", fe, smp,
                        tests=[("farm high = farm low", (f"{reg}_{thr}_farm_hi", f"{reg}_{thr}_farm_lo")),
                               ("processing high = processing low", (f"{reg}_{thr}_proc_hi", f"{reg}_{thr}_proc_lo"))])
            # E4d farm stage only, capital intensity and type of production together
            df = d[(d["stage"] == "Farm") & d["type"].isin([TYPES["field"], TYPES["horti"], TYPES["live"]])].copy()
            tt = interact(df, reg, "type", {"horti": TYPES["horti"], "live": TYPES["live"]}, f"{reg}_type")
            for thr, tl in (("high_mean", "aggregate ratio"), ("high_median", "median")):
                hl = interact(df, reg, thr, {"hi": "High", "lo": "Low"}, f"{reg}_{thr}")
                for fe in FE_BODY:
                    fit(df, dep, hl + tt, fe, "E4d", f"Farm stage: {reg} x high/low ({tl}) and x type, {dl}", fe,
                        smp + ", farm stage, field, horticultural and livestock products",
                        tests=[("high = low", (f"{reg}_{thr}_hi", f"{reg}_{thr}_lo"))])
            df[f"{reg}_x_lnkl"] = df[reg] * df["lnkl"]
            for fe in FE_BODY:
                fit(df, dep, [reg, f"{reg}_x_lnkl"] + tt, fe, "E4d", f"Farm stage: {reg} x ln capital per worker and x type, {dl}", fe,
                    smp + ", farm stage, field, horticultural and livestock products")
            # E4e type x capital intensity
            for thr, tl in (("high_mean", "aggregate ratio"), ("high_median", "median")):
                regs, tests = [], []
                for k, ty in TYPES.items():
                    for h, hv in (("h", "High"), ("l", "Low")):
                        ind = ((d["type"] == ty) & (d[thr] == hv)).astype(float)
                        if ind.sum():
                            d[f"{reg}_{thr}_{k}_{h}"] = d[reg] * ind; regs.append(f"{reg}_{thr}_{k}_{h}")
                    if f"{reg}_{thr}_{k}_h" in regs and f"{reg}_{thr}_{k}_l" in regs:
                        tests.append((f"{ty.lower()}, high = low", (f"{reg}_{thr}_{k}_h", f"{reg}_{thr}_{k}_l")))
                d[f"{reg}_{thr}_tnc"] = d[reg] * (d[thr] == "Not classified"); regs.append(f"{reg}_{thr}_tnc")
                for fe in FE_BODY:
                    fit(d, dep, regs, fe, "E4e", f"{reg} x type x high/low ({tl}), {dl}", fe, smp, tests=tests)
            # E4f type alone
            regs = interact(d, reg, "type", TYPES, f"{reg}_type")
            for fe in FE_BODY:
                fit(d, dep, regs, fe, "E4f", f"{reg} x type of production, {dl}", fe, smp,
                    tests=[("field = horticultural", (f"{reg}_type_field", f"{reg}_type_horti"))])
            del d; gc.collect()
    # E4g by origin, FE4
    for reg in ("lnN", "D"):
        for depk, (dep, dl) in DEP.items():
            for o in sorted(od["country_orig"].unique()):
                d = base_sample(od[od["country_orig"] == o], reg, dep).copy()
                smp = f"origin {o}, " + REG[reg][1]
                for thr, tl in (("high_mean", "aggregate ratio"), ("high_median", "median")):
                    regs = interact(d, reg, thr, HL, f"{reg}_{thr}")
                    fit(d, dep, regs, "FE4", "E4g", f"Pooled stages, {reg} x high/low ({tl}), {dl}", COUNTRY[o], smp, cluster="country_dest",
                        tests=[("high = low", (f"{reg}_{thr}_hi", f"{reg}_{thr}_lo"))], fe_code="FE4")
                    regs = []
                    for k, (st, hl) in ST.items():
                        ind = ((d["stage"] == st) & (d[thr] == hl)).astype(float)
                        if ind.sum():
                            d[f"{reg}_{thr}_{k}"] = d[reg] * ind; regs.append(f"{reg}_{thr}_{k}")
                    if (d["stage"] == "Not classified").any():
                        d[f"{reg}_{thr}_nc"] = d[reg] * (d["stage"] == "Not classified"); regs.append(f"{reg}_{thr}_nc")
                    fit(d, dep, regs, "FE4", "E4g", f"Stage x high/low, {reg} ({tl}), {dl}", COUNTRY[o], smp, cluster="country_dest",
                        tests=[("farm high = farm low", (f"{reg}_{thr}_farm_hi", f"{reg}_{thr}_farm_lo")),
                               ("processing high = processing low", (f"{reg}_{thr}_proc_hi", f"{reg}_{thr}_proc_lo"))], fe_code="FE4")


# ---------------------------------------------------------------------
# E5 location
# ---------------------------------------------------------------------
LOC_FE = {"OYT": ("oy + type", ["oy", "type"], "origin x year + type of production"),
          "OYH": ("oy + hs2", ["oy", "hs2"], "origin x year + HS chapter")}


def kl_regs(d: pd.DataFrame) -> dict[str, list[str]]:
    d["hi_mean"] = (d["high_mean"] == "High").astype(float)
    d["hi_median"] = (d["high_median"] == "High").astype(float)
    for q in range(2, 6):
        d[f"q{q}"] = (d["quintile"] == q).astype(float)
    return {"lnKL": ["lnkl"], "high_mean": ["hi_mean"], "high_median": ["hi_median"], "quintile": [f"q{q}" for q in range(2, 6)]}


def e5(op: pd.DataFrame) -> None:
    d = op[op["lnkl"].notna()].copy()
    R = kl_regs(d)
    smp = "origin x product x year cells with positive exports, classified products"
    for sheet, dep, sub, sl in (("E5a", "D", d, smp), ("E5b", "lnN", d[d["N"] >= 1], smp + ", at least one MNE"),
                                ("E5b", "S", d, smp), ("E5c", "DF", d, smp), ("E5c", "DD", d, smp)):
        for fk, (fe, fcols, fl) in LOC_FE.items():
            for rk, regs in R.items():
                fit(sub, dep, regs, fe, sheet, f"{dep}, FE {fl}", rk, sl, cluster="hs", fe_code=fl)
            if sheet == "E5a":
                for rk, regs in R.items():
                    logit_ame(sub, dep, regs, fcols, "E5a", f"Logit, FE {fl}", rk, sl)
    # E5d first entry (discrete time hazard): cells with no MNE in any earlier year; 2012 is the first year observed
    o = op.sort_values(["country_orig", "hs", "year"]).copy()
    o["prior_mne"] = o.groupby(["country_orig", "hs"])["D"].transform(lambda s: s.shift(1).cummax()).fillna(0)
    # a cell with an MNE in any earlier observed year (2012 included) has left the risk set
    risk = o[(o["year"] >= 2013) & (o["prior_mne"] == 0)].copy()
    risk = risk[risk["lnkl"].notna()].copy()
    R = kl_regs(risk)
    for fk, (fe, fcols, fl) in LOC_FE.items():
        for rk, regs in R.items():
            fit(risk, "D", regs, fe, "E5d", f"First entry, FE {fl}", rk, "cells at risk: no MNE in any earlier year, 2013 to 2018", cluster="hs", fe_code=fl)
    rk = risk[risk["D"] == 1]
    DESC["E5d_counts"] = {"by year": rk.groupby("year").size(), "by type": rk.groupby("type").size(),
                          "by stage and capital intensity (aggregate ratio)": rk.groupby(["stage", "high_mean"]).size(),
                          "by stage and capital intensity (median)": rk.groupby(["stage", "high_median"]).size(),
                          "cells at risk by year": risk.groupby("year").size()}
    # E5e other product characteristics
    d = op[op["lnkl"].notna()].copy()
    d["rauch_ref"] = (d["rauch_con"] == "Reference priced").astype(float)
    d["rauch_diff"] = (d["rauch_con"] == "Differentiated").astype(float)
    d.loc[d["rauch_con"].isna(), ["rauch_ref", "rauch_diff"]] = np.nan
    d["consumption"] = (d["bec_enduse"] == "Consumption").astype(float)
    d.loc[d["bec_enduse"].isna(), "consumption"] = np.nan
    d["inputs"] = (d["input"] == "Inputs").astype(float)
    for fk, (fe, fcols, fl) in LOC_FE.items():
        for rk, regs in (("lnKL", ["lnkl"]), ("Rauch", ["rauch_ref", "rauch_diff"]), ("BEC and inputs", ["consumption", "inputs"]),
                         ("All", ["lnkl", "rauch_ref", "rauch_diff", "consumption", "inputs"])):
            fit(d, "D", regs, fe, "E5e", f"D, FE {fl}", rk, smp + ", Rauch (conservative) classified", cluster="hs", fe_code=fl)
        d["rauch_lib_ref"] = (d["rauch_lib"] == "Reference priced").astype(float)
        d["rauch_lib_diff"] = (d["rauch_lib"] == "Differentiated").astype(float)
        d.loc[d["rauch_lib"].isna(), ["rauch_lib_ref", "rauch_lib_diff"]] = np.nan
        fit(d, "D", ["lnkl", "rauch_lib_ref", "rauch_lib_diff", "consumption", "inputs"], fe, "E5e", f"D, FE {fl}", "All, liberal Rauch",
            smp + ", Rauch (liberal) classified", cluster="hs", fe_code=fl)


# ---------------------------------------------------------------------
# E7 other crosses
# ---------------------------------------------------------------------
def e7(od: pd.DataFrame, cls: pd.DataFrame) -> None:
    s = pd.read_parquet(V4 / "sector.parquet")
    s = s[pd.to_numeric(s["hs2"], errors="coerce").between(1, 24)].rename(columns={"hs07_6d": "hs"})
    s = s.merge(cls[["hs", "rauch_con", "rauch_lib", "bec_enduse", "input", "high_mean"]], on="hs", how="left")
    s["bec2"] = s["bec_enduse"].replace({"Capital": "Intermediate"})
    rows = []
    for per, x in (("2018", s[s["year"] == 2018]), ("2012 to 2018", s)):
        V = x["value_fob"].sum()
        for col, lab in (("rauch_con", "Rauch, conservative"), ("rauch_lib", "Rauch, liberal"), ("bec2", "BEC end use"), ("input", "Inputs")):
            for k, y in x.groupby(x[col].fillna("Not classified")):
                v = y["value_fob"].sum()
                rows.append({"Period": per, "Classification": lab, "Group": k, "Products": y["hs"].nunique(), "Share of exports (%)": 100 * v / V,
                             "MNE share (%)": 100 * y.loc[y["ot"] != "local", "value_fob"].sum() / v,
                             "Foreign MNE share (%)": 100 * y.loc[y["ot"] == "ext", "value_fob"].sum() / v})
    DESC["E7_shares"] = pd.DataFrame(rows)
    od = od.copy()
    od["bec2"] = od["bec_enduse"].replace({"Capital": "Intermediate"})
    od["rauch2"] = od["rauch_con"].map({"Differentiated": "Differentiated", "Reference priced": "Not differentiated", "Homogeneous": "Not differentiated"})
    RC = {"hom": "Homogeneous", "ref": "Reference priced", "diff": "Differentiated"}
    for reg in ("lnN", "D"):
        for depk, (dep, dl) in DEP.items():
            d = base_sample(od, reg, dep).copy()
            smp = REG[reg][1]
            for sheet, col, groups, tests, lab in (
                    ("E7a", "rauch_con", RC, [("homogeneous = differentiated", ("hom", "diff"))], "Rauch, conservative"),
                    ("E7a", "rauch_lib", RC, [("homogeneous = differentiated", ("hom", "diff"))], "Rauch, liberal"),
                    ("E7b", "bec2", {"int": "Intermediate", "cons": "Consumption"}, [("intermediate = consumption", ("int", "cons"))], "BEC end use"),
                    ("E7b", "input", {"inp": "Inputs", "oth": "Other products"}, [("inputs = other", ("inp", "oth"))], "Inputs")):
                regs = interact(d, reg, col, groups, f"{reg}_{col}")
                d[f"{reg}_{col}_na"] = d[reg] * d[col].isna(); regs.append(f"{reg}_{col}_na")
                for fe in FE_BODY:
                    fit(d, dep, regs, fe, sheet, f"{reg} x {lab}, {dl}", fe, smp,
                        tests=[(n, (f"{reg}_{col}_{a}", f"{reg}_{col}_{b}")) for n, (a, b) in tests])
            # E7c capital intensity x Rauch
            regs = []
            for h, hv in (("hi", "High"), ("lo", "Low")):
                for r, rv in (("diff", "Differentiated"), ("nd", "Not differentiated")):
                    ind = ((d["high_mean"] == hv) & (d["rauch2"] == rv)).astype(float)
                    d[f"{reg}_kr_{h}_{r}"] = d[reg] * ind; regs.append(f"{reg}_kr_{h}_{r}")
            d[f"{reg}_kr_other"] = d[reg] * ((d["high_mean"] == "Not classified") | d["rauch2"].isna()); regs.append(f"{reg}_kr_other")
            for fe in FE_BODY:
                fit(d, dep, regs, fe, "E7c", f"{reg} x capital intensity (aggregate ratio) x Rauch, {dl}", fe, smp,
                    tests=[("high = low, differentiated", (f"{reg}_kr_hi_diff", f"{reg}_kr_lo_diff")),
                           ("high = low, not differentiated", (f"{reg}_kr_hi_nd", f"{reg}_kr_lo_nd"))])
            del d; gc.collect()


# ---------------------------------------------------------------------
# samples
# ---------------------------------------------------------------------
def samples(od: pd.DataFrame, op: pd.DataFrame, cls: pd.DataFrame) -> None:
    rows = []

    def add(name, d, exporters=None):
        rows.append({"Sample": name, "Cells": len(d), "Export value 2012 to 2018 (US$ billion)": d["X"].sum() / 1e9,
                     "MNE exporters (cell sum)": int(d["N"].sum()), "Local exporters (cell sum)": int(d["NL"].sum())})
    add("odpy, all cells with positive exports (E2b, E4 with D)", od)
    add("odpy, at least one MNE (E2a, E4 with ln N)", od[od["N"] >= 1])
    add("odpy, positive local exports (E2d)", od[od["XL"] > 0])
    add("odpy, at least one MNE and positive local exports (E2c)", od[(od["N"] >= 1) & (od["XL"] > 0)])
    add("odpy, classified products (E4b)", od[od["lnkl"].notna()])
    add("odpy, farm stage, field, horticultural and livestock (E4d)", od[(od["stage"] == "Farm") & (od["type"] != TYPES["proc"])])
    add("opy, positive exports (E5)", op)
    add("opy, positive exports, classified products (E5a)", op[op["lnkl"].notna()])
    for name in ("op", "odp"):
        e = pd.read_parquet(V4 / f"event_{name}.parquet")
        c = e.drop_duplicates("cell")
        rows.append({"Sample": f"Event panel {name}: treated cells (t0 2014 to 2018, two years before t0)", "Cells": int((c["gvar"] > 0).sum()),
                     "Export value 2012 to 2018 (US$ billion)": e.loc[e["gvar"] > 0, "X"].sum() / 1e9})
        rows.append({"Sample": f"Event panel {name}: never treated cells", "Cells": int((c["gvar"] == 0).sum()),
                     "Export value 2012 to 2018 (US$ billion)": e.loc[e["gvar"] == 0, "X"].sum() / 1e9})
    DESC["Samples"] = pd.DataFrame(rows)
    th = cls.groupby("stage").agg(products=("hs", "size"), threshold_used=("thr_mean", "first"), median=("thr_median", "first"),
                                  export_weighted_mean=("kl_wmean_stage", "first")).reset_index()
    DESC["Thresholds"] = th


def main() -> None:
    which = sys.argv[1:] or ["all"]
    od, op, cls = load_cells()
    print(f"odpy {len(od):,}, opy {len(op):,}")
    steps = {"e1": lambda: e1(), "e2": lambda: e2(od), "e3": lambda: e3(cls), "e4": lambda: e4(od), "e5": lambda: e5(op),
             "e7": lambda: e7(od, cls), "samples": lambda: samples(od, op, cls)}
    for k, f in steps.items():
        if "all" in which or k in which:
            print(f"== {k}")
            f()
    tag = "_".join(which)
    with open(OUT / f"v4_regs_{tag}.pkl", "wb") as fh:
        pickle.dump(REGS, fh)
    with open(OUT / f"v4_desc_{tag}.pkl", "wb") as fh:
        pickle.dump(DESC, fh)
    print(f"saved {len(REGS)} regressions, {len(DESC)} descriptive tables -> {OUT}")


if __name__ == "__main__":
    main()
