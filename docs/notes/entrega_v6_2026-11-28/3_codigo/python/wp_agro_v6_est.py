"""
wp_agro_v6_est.py  --  regressions of round v6 (V6-05 to V6-09) and the regression side of the bridge table (V6-16)
====================================================================================================================

    WP_YEARS=2012-2018 WP_SCOPES=agro python wp_agro_v6_est.py [step ...]
    steps: pci (V6-05, sheet 11.1), rauch (V6-06, 11.2), race (V6-07, 11.3), loc (V6-08, 11.4), cap (V6-09), bridge (V6-16 P2a)

Templates (A.6 of especificaciones_estimaciones_v6_2026-11-25.md):
  ASOC  cells odpy; ln X (X > 0) and ln XL (XL > 0); regressor ln N (N >= 1) or D (all cells with X > 0); by groups (R x one
        dummy per group, no main effect, p of equality) or continuous (R and R x standardized trait); FE3 to FE6; cluster CL2 =
        two-way origin-destination pair and HS4 heading.
  LOC   cells opy with X > 0; D, ln N (N >= 1), S; FL1 origin x year + type, FL2 origin x year + HS chapter, FL3 origin x year;
        cluster HS6 product; variants weighted by X_opy and S conditional on N >= 1.
Every row carries Request (V6-xx) and Role (A.9). Output: output/wp_2012_2018/agro/v6/v6_regs_<step>.pkl, v6_desc_<step>.pkl
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
import pyfixest as pf  # noqa: E402
from scipy.stats import norm  # noqa: E402

V4 = W.WP_INT / "v4"
V6 = W.WP_INT / "v6"
OUT = W.WP_OUT / "agro" / "v6"
FE = {"FE3": "odp + year", "FE4": "odp + ody", "FE5": "odp + ody + opy", "FE6": "odp + ody + opy + dpy"}
FL = {"FL1": "oy + type", "FL2": "oy + hs2", "FL3": "oy"}
CL = {"CL2": "od+hs4", "CL-od": "od", "CL2-hs6": "od+hs", "CL-hs6": "hs", "CL-hs4": "hs4", "CL-op": "op", "CL-B": "od+op"}
REGS: list[dict] = []
DESC: dict = {}


def fit(d, dep, regs, fe, sheet, panel, col, request, role, cl="CL2", tests=(), w=None, alt_cl=(), sample="", contrasts=None):
    """One OLS regression with pyfixest. tests = [(name, v1, v2)]; contrasts = [(name, {var: weight})] linear combinations."""
    fe_str = FE.get(fe, FL.get(fe, fe))
    clus = CL.get(cl, cl)
    cols = [dep] + list(regs) + [c.strip() for c in fe_str.split("+") if c.strip()] + [c for c in clus.split("+")] + ([w] if w else [])
    for a in alt_cl:
        cols += CL[a].split("+")
    dd = d.dropna(subset=list(dict.fromkeys(cols)))
    rec = dict(sheet=sheet, panel=panel, col=col, fe=fe, cluster=cl, dep=dep, regs=list(regs), request=request, role=role, sample=sample,
               weights=w or "", cells={}, tests={}, alt={}, n=0, r2=np.nan, r2w=np.nan, status="ok", contrasts={})
    t0 = time.time()
    try:
        m = pf.feols(f"{dep} ~ {' + '.join(regs)} | {fe_str}", data=dd, vcov={"CRV1": clus}, weights=w)
    except Exception as e:  # noqa: BLE001
        rec["status"] = "Not estimated: " + str(e)[:100]
        REGS.append(rec)
        print(f"   {sheet} {panel[:50]} {col}: FAILED {str(e)[:100]}")
        return rec
    b, se, p = m.coef(), m.se(), m.pvalue()
    rec["cells"] = {v: (float(b[v]), float(se[v]), float(p[v])) for v in regs if v in b.index}
    V = np.asarray(m._vcov); ix = list(b.index)
    for name, v1, v2 in tests:
        if v1 in ix and v2 in ix:
            i, j = ix.index(v1), ix.index(v2)
            sd = float(np.sqrt(V[i, i] + V[j, j] - 2 * V[i, j]))
            rec["tests"][name] = float(2 * norm.sf(abs((b[v1] - b[v2]) / sd))) if sd > 0 else np.nan
    for name, wts in (contrasts or []):
        a = np.array([wts.get(v, 0.0) for v in ix])
        est = float(a @ b.values); s = float(np.sqrt(a @ V @ a))
        rec["contrasts"][name] = (est, s, float(2 * norm.sf(abs(est / s))) if s > 0 else np.nan)
    for a in alt_cl:
        try:
            m2 = pf.feols(f"{dep} ~ {' + '.join(regs)} | {fe_str}", data=dd, vcov={"CRV1": CL[a]}, weights=w)
            rec["alt"][a] = {v: (float(m2.se()[v]), float(m2.pvalue()[v])) for v in regs if v in m2.coef().index}
        except Exception as e:  # noqa: BLE001
            rec["alt"][a] = {"error": str(e)[:80]}
    rec.update(n=int(m._N), r2=float(getattr(m, "_r2", np.nan)), r2w=float(getattr(m, "_r2_within", np.nan)))
    REGS.append(rec)
    print(f"   {sheet:5s} {panel[:48]:48s} {str(col):>6s} N={rec['n']:>7,} " + " ".join(f"{v}:{c[0]:+.3f}({c[2]:.3f})" for v, c in list(rec["cells"].items())[:3])
          + f" [{time.time() - t0:.0f}s]")
    del m; gc.collect()
    return rec


def groups_interact(d, reg, col, prefix):
    names = []
    for g in sorted(d[col].dropna().unique()):
        v = f"{prefix}_{''.join(ch for ch in str(g) if ch.isalnum())[:12]}"
        d[v] = d[reg] * (d[col] == g)
        names.append((g, v))
    return names


def load_od() -> pd.DataFrame:
    cls = pd.read_parquet(V6 / "classes_v6.parquet")
    od = pd.read_parquet(V4 / "odpy.parquet").merge(cls, on="hs", how="left")
    od["od"] = od["country_orig"] + "_" + od["country_dest"]
    od["odp"] = od["od"] + "_" + od["hs"]
    od["ody"] = od["od"] + "_" + od["year"].astype(str)
    od["opy"] = od["country_orig"] + "_" + od["hs"] + "_" + od["year"].astype(str)
    od["dpy"] = od["country_dest"] + "_" + od["hs"] + "_" + od["year"].astype(str)
    od["op"] = od["country_orig"] + "_" + od["hs"]
    # groups (G) and MNE exports per firm from the firm rows
    s = pd.read_parquet(V4 / "sector.parquet").rename(columns={"hs07_6d": "hs", "dest": "country_dest"})
    s = s[s["hs2"].between(1, 24) & (s["ot"] != "local")]
    s["grp"] = s["parent_key"].fillna("").astype(str)
    s.loc[s["grp"] == "", "grp"] = s["ID_Orbis_DNB"].fillna("").astype(str)
    s.loc[s["grp"] == "", "grp"] = s["firm"].astype(str)
    G = s.groupby(["country_orig", "country_dest", "hs", "year"])["grp"].nunique().rename("G").reset_index()
    od = od.merge(G, on=["country_orig", "country_dest", "hs", "year"], how="left")
    od["G"] = od["G"].fillna(0)
    od["lnG"] = np.where(od["G"] > 0, np.log(od["G"].where(od["G"] > 0)), np.nan)
    od["lnXM"] = np.where(od["XM"] > 0, np.log(od["XM"].where(od["XM"] > 0)), np.nan)
    od["lnXMpN"] = np.where((od["XM"] > 0) & (od["N"] > 0), np.log((od["XM"] / od["N"].where(od["N"] > 0)).where(od["XM"] > 0)), np.nan)
    od["wodp"] = od.groupby("odp")["X"].transform("mean")
    return od


def load_op() -> pd.DataFrame:
    cls = pd.read_parquet(V6 / "classes_v6.parquet")
    op = pd.read_parquet(V4 / "opy.parquet").merge(cls, on="hs", how="left")
    op["oy"] = op["country_orig"] + "_" + op["year"].astype(str)
    op["hs2"] = op["hs"].str[:2]
    op["hs4"] = op["hs"].str[:4]
    return op


DEPS = {"lnX": "ln X", "lnXL": "ln XL"}


def asoc_sample(od, reg, dep):
    s = od[od["N"] >= 1] if reg == "lnN" else od
    return s[s[dep].notna()].copy()


# ---------------------------------------------------------------------------------------------------------------------
def step_pci(od):
    req = "V6-05"
    for reg in ("lnN", "D"):
        for dep in DEPS:
            d = asoc_sample(od, reg, dep)
            d = d[d["PCI6_z"].notna()].copy()
            d["RxPCI6"] = d[reg] * d["PCI6_z"]
            for fe in FE:
                prim = reg == "lnN" and fe == "FE4" and dep in ("lnX", "lnXL")
                role = "primary" if prim else "robustness"
                alt = ("CL-od", "CL2-hs6") if (reg == "lnN" and fe in ("FE4", "FE5", "FE6")) else ()
                tag = {"lnXL": "T2", "lnX": "T3"}[dep] if prim else ""
                fit(d, dep, [reg, "RxPCI6"], fe, "11.1", f"A. Continuous: {DEPS[dep]} on {reg} and {reg} x PCI6_z", fe, req, role,
                    alt_cl=alt, sample=f"odpy cells, {'N >= 1' if reg == 'lnN' else 'X > 0'}, products with PCI6; {tag}".strip("; "))
            # B. two groups
            d2 = asoc_sample(od, reg, dep)
            g = groups_interact(d2, reg, "high_PCI6", reg + "H")
            names = [v for _, v in g]
            hv = dict(g)
            for fe in FE:
                fit(d2, dep, names, fe, "11.1", f"B. Two groups: {DEPS[dep]} on {reg} x high_PCI6", fe, req, "robustness",
                    tests=[("High = Low", hv.get("High"), hv.get("Low"))], sample="odpy cells")
            del d, d2; gc.collect()
    for dep in DEPS:
        d = asoc_sample(od, "lnN", dep)
        # C. between headings and within the heading
        c = d[d["PCI4_z"].notna() & d["PCI6_dev"].notna()].copy()
        c["RxPCI4"] = c["lnN"] * c["PCI4_z"]; c["RxDEV"] = c["lnN"] * c["PCI6_dev"]
        for fe in ("FE4", "FE6"):
            fit(c, dep, ["lnN", "RxPCI4", "RxDEV"], fe, "11.1", f"C. Between and within heading: {DEPS[dep]} on ln N, ln N x PCI4_z, ln N x PCI6_dev", fe, req, "exploratory")
        # D. another revision
        c = d[d["PCI6_hs12_z"].notna()].copy(); c["RxPCI12"] = c["lnN"] * c["PCI6_hs12_z"]
        for fe in ("FE4", "FE6"):
            fit(c, dep, ["lnN", "RxPCI12"], fe, "11.1", f"D. Another revision: {DEPS[dep]} on ln N and ln N x PCI6_hs12 (standardized)", fe, req, "robustness")
        # E. v5 with the new cluster
        c = d.copy(); c["RxPCIp"] = c["lnN"] * c["PCI_p"]
        g = groups_interact(c, "lnN", "type", "lnNT")
        for fe in ("FE4", "FE6"):
            fit(c, dep, ["lnN", "RxPCIp"], fe, "11.1", f"E. v5 with CL2: {DEPS[dep]} on ln N and ln N x PCI_p (Atlas, HS4)", fe, req, "robustness")
            gv = dict(g)
            fit(c, dep, [v for _, v in g], fe, "11.1", f"E. v5 with CL2: {DEPS[dep]} on ln N x type of production", fe, req, "robustness",
                tests=[("Field crops = Horticultural and plantation crops", gv.get("Field crops"), gv.get("Horticultural and plantation crops"))])
        del c, d; gc.collect()
    # F. margin of the MNEs
    for dep in ("lnXM", "lnXMpN"):
        d = od[(od["N"] >= 1) & od[dep].notna() & od["PCI6_z"].notna()].copy(); d["RxPCI6"] = d["lnN"] * d["PCI6_z"]
        for fe in ("FE4", "FE6"):
            fit(d, dep, ["lnN", "RxPCI6"], fe, "11.1", f"F. Margin of the MNEs: {'ln XM' if dep == 'lnXM' else 'ln (XM / N)'} on ln N and ln N x PCI6_z", fe, req, "exploratory")
    # G. groups instead of firms
    for dep in DEPS:
        d = od[(od["G"] >= 1) & od[dep].notna() & od["PCI6_z"].notna()].copy(); d["GxPCI6"] = d["lnG"] * d["PCI6_z"]
        fit(d, dep, ["lnG", "GxPCI6"], "FE4", "11.1", f"G. Groups: {DEPS[dep]} on ln G and ln G x PCI6_z", "FE4", req, "robustness")
    # H. weighted
    d = od[(od["N"] >= 1) & od["lnX"].notna() & od["PCI6_z"].notna()].copy(); d["RxPCI6"] = d["lnN"] * d["PCI6_z"]
    fit(d, "lnX", ["lnN", "RxPCI6"], "FE4", "11.1", "H. Weighted by the average exports of the odp cell: ln X on ln N and ln N x PCI6_z", "FE4", req,
        "descriptive", w="wodp")


def permutation_p(od, dep, B=1000, seed=20261127):
    """1,000 reassignments of PCI6_z across products within stage x type; p of |t| (FE4, CL2)."""
    d = asoc_sample(od, "lnN", dep)
    d = d[d["PCI6_z"].notna()].copy()
    prod = d[["hs", "stage", "type", "PCI6_z"]].drop_duplicates("hs")
    rng = np.random.default_rng(seed)
    d["RxPCI6"] = d["lnN"] * d["PCI6_z"]
    m = pf.feols(f"{dep} ~ lnN + RxPCI6 | odp + ody", data=d, vcov={"CRV1": "od+hs4"})
    t_obs = float(m.tstat()["RxPCI6"])
    ts = []
    for _ in range(B):
        perm = prod.copy()
        perm["PCI6_p"] = perm.groupby(["stage", "type"])["PCI6_z"].transform(lambda s: rng.permutation(s.values))
        x = d.merge(perm[["hs", "PCI6_p"]], on="hs")
        x["RxP"] = x["lnN"] * x["PCI6_p"]
        mm = pf.feols(f"{dep} ~ lnN + RxP | odp + ody", data=x, vcov={"CRV1": "od+hs4"})
        ts.append(float(mm.tstat()["RxP"]))
    ts = np.array(ts)
    return t_obs, float((np.abs(ts) >= abs(t_obs)).mean())


def step_rauch(od, op):
    req = "V6-06"
    for col, panel in (("rauch_bin_con", "A"), ("rauch_bin_lib", "B"), ("rauch_full_con", "C")):
        for reg in ("lnN", "D"):
            for dep in DEPS:
                d = asoc_sample(od, reg, dep)
                d[col] = d[col].fillna("Not classified")
                g = dict(groups_interact(d, reg, col, reg + "R"))
                if col == "rauch_full_con":
                    tests = [("Homogeneous = Reference priced", g.get("Homogeneous"), g.get("Reference priced")),
                             ("Homogeneous = Differentiated", g.get("Homogeneous"), g.get("Differentiated")),
                             ("Reference priced = Differentiated", g.get("Reference priced"), g.get("Differentiated"))]
                else:
                    tests = [("Differentiated = Not differentiated", g.get("Differentiated"), g.get("Not differentiated"))]
                for fe in FE:
                    role = "secondary" if (col == "rauch_bin_con" and reg == "lnN" and dep == "lnXL" and fe == "FE4") else "exploratory"
                    fit(d, dep, list(g.values()), fe, "11.2", f"{panel}. {DEPS[dep]} on {reg} x {col}", fe, req, role, tests=tests,
                        sample="S1" if role == "secondary" else "")
                del d; gc.collect()
    for dep in DEPS:
        d = asoc_sample(od, "lnN", dep)
        g = dict(groups_interact(d, "lnN", "rauch_hom_con", "lnNHom"))
        for fe in FE:
            fit(d, dep, list(g.values()), fe, "11.2", f"D. {DEPS[dep]} on ln N x rauch_hom_con", fe, req, "descriptive",
                tests=[("Homogeneous = Not homogeneous", g.get("Homogeneous"), g.get("Not homogeneous"))])
    # E. LOC
    for col in ("rauch_bin_con", "rauch_bin_lib"):
        o = op.copy()
        o["r_diff"] = (o[col] == "Differentiated").astype(float)
        o["r_nc"] = (o[col] == "Not classified").astype(float)
        loc_block(o, ["r_diff", "r_nc"], "11.2", f"E. Location by {col} (not differentiated omitted)", req, "exploratory",
                  weighted=(col == "rauch_bin_con"), conditional=(col == "rauch_bin_con"))


def loc_block(o, regs, sheet, label, req, role, weighted=False, conditional=False, primary_row=None):
    for dep, sub in (("D", o), ("lnN", o[o["N"] >= 1]), ("S", o)):
        for fk in FL:
            r = role
            if primary_row and (dep, fk) == primary_row:
                r = "primary"
            fit(sub, dep, regs, fk, sheet, f"{label}: {dep}", fk, req, r, cl="CL-hs6", sample="opy cells with X > 0" + ("; T1" if r == "primary" else ""))
            if weighted:
                fit(sub, dep, regs, fk, sheet, f"{label}, weighted by X_opy: {dep}", fk, req, "robustness", cl="CL-hs6", w="X")
    if conditional:
        for fk in FL:
            fit(o[o["N"] >= 1], "S", regs, fk, sheet, f"{label}, conditional on N >= 1: S", fk, req, "robustness", cl="CL-hs6")


def step_race(od):
    req = "V6-07"
    base = od[(od["N"] >= 1) & od["PCI6_z"].notna() & od["rauch_bin_con"].isin(["Differentiated", "Not differentiated"])
              & od["stage"].isin(["Farm", "Processing"])].copy()
    base["DIFF"] = (base["rauch_bin_con"] == "Differentiated").astype(float)
    base["FIELD"] = (base["type"] == "Field crops").astype(float)
    base["PROC"] = (base["stage"] == "Processing").astype(float)
    origins = sorted(base["country_orig"].unique())
    cols = {1: ["PCI6_z"], 2: ["DIFF"], 3: ["FIELD"], 4: ["PROC"], 5: ["ubiq_z"], 6: ["PCI6_z", "DIFF"], 7: ["PCI6_z", "FIELD"],
            8: ["PCI6_z", "PROC"], 9: ["PCI6_z", "ubiq_z"], 10: ["PCI6_z", "DIFF", "FIELD", "PROC"], 11: ["PCI6_z", "DIFF", "FIELD", "PROC", "ubiq_z"],
            12: ["PCI6_z", "DIFF", "FIELD", "PROC"] + [f"o_{o}" for o in origins[1:]]}
    for reg, deps in (("lnN", ["lnX", "lnXL"]), ("D", ["lnXL"])):
        for dep in deps:
            if reg == "lnN":
                d = base[base[dep].notna()].copy()
            else:
                d = od[od["XL"] > 0].copy()
                d = d[d["PCI6_z"].notna() & d["rauch_bin_con"].isin(["Differentiated", "Not differentiated"]) & d["stage"].isin(["Farm", "Processing"])]
                d["DIFF"] = (d["rauch_bin_con"] == "Differentiated").astype(float)
                d["FIELD"] = (d["type"] == "Field crops").astype(float)
                d["PROC"] = (d["stage"] == "Processing").astype(float)
            for o in origins[1:]:
                d[f"o_{o}"] = (d["country_orig"] == o).astype(float)
            for k, terms in cols.items():
                x = d if not any(t == "ubiq_z" for t in terms) else d[d["ubiq_z"].notna()]
                regs = [reg] + [f"{reg}x{t}" for t in terms]
                for t in terms:
                    x[f"{reg}x{t}"] = x[reg] * x[t]
                for fe in ("FE4", "FE6"):
                    prim = reg == "lnN" and k == 10 and fe == "FE4"
                    fit(x, dep, regs, fe, "11.3", f"{DEPS[dep]} on {reg} and {reg} x traits, column ({k})", f"({k}) {fe}", req,
                        "primary" if prim else "robustness", sample="common sample: N >= 1, PCI6, Rauch class, stage" + ("; T4" if prim else ""))
            del d; gc.collect()
    # leave-one-out
    top = od.groupby("hs")["X"].sum().sort_values(ascending=False).head(10).index.tolist()
    rows = []
    for dep in DEPS:
        d = asoc_sample(od, "lnN", dep)
        d = d[d["PCI6_z"].notna()].copy(); d["RxPCI6"] = d["lnN"] * d["PCI6_z"]
        for kind, vals, colname in (("product", top, "hs"), ("origin", sorted(d["country_orig"].unique()), "country_orig")):
            for v in vals:
                r = fit(d[d[colname] != v], dep, ["lnN", "RxPCI6"], "FE4", "11.3", f"Leave one out: {DEPS[dep]}, without {kind} {v}", "FE4", req, "robustness")
                c = r["cells"].get("RxPCI6", (np.nan,) * 3)
                rows.append({"Dependent variable": DEPS[dep], "Excluded": f"{kind} {v}", "Coefficient of ln N x PCI6_z": c[0], "SE (CL2)": c[1], "p": c[2], "N": r["n"]})
    DESC["leave_one_out"] = pd.DataFrame(rows)


def step_loc(op):
    req = "V6-08"
    o = op[op["PCI6_z"].notna()].copy()
    loc_block(o, ["PCI6_z"], "11.4", "A. Location on PCI6_z", req, "robustness", weighted=True, conditional=True, primary_row=("S", "FL1"))
    o = op.copy()
    o["hiPCI6"] = (o["high_PCI6"] == "High").astype(float)
    o["ncPCI6"] = (o["high_PCI6"] == "Not classified").astype(float)
    loc_block(o, ["hiPCI6", "ncPCI6"], "11.4", "A. Location on high_PCI6 (Low omitted)", req, "robustness", weighted=True, conditional=True)
    # D. concentration
    s = pd.read_parquet(V4 / "sector.parquet").rename(columns={"hs07_6d": "hs"})
    s = s[s["hs2"].between(1, 24) & s["year"].between(2012, 2018)]
    s["grp"] = s["parent_key"].fillna("").astype(str)
    s.loc[s["grp"] == "", "grp"] = s["ID_Orbis_DNB"].fillna("").astype(str)
    s.loc[s["grp"] == "", "grp"] = s["firm"].astype(str)
    fx = s[s["ot"] == "ext"].groupby("grp")["value_fob"].sum().sort_values(ascending=False)
    top20 = set(fx.head(20).index)
    s["top20"] = s["grp"].isin(top20) & (s["ot"] == "ext")
    fv = s.groupby(["country_orig", "hs", "year", "firm"])["value_fob"].sum().rename("v").reset_index()
    tot = fv.groupby(["country_orig", "hs", "year"])["v"].transform("sum")
    fv["sh"] = fv["v"] / tot
    cc = fv.groupby(["country_orig", "hs", "year"]).agg(HHI=("sh", lambda x: float((x ** 2).sum())), maxsh=("sh", "max")).reset_index()
    G = s[s["ot"] != "local"].groupby(["country_orig", "hs", "year"])["grp"].nunique().rename("G").reset_index()
    t20 = s[s["top20"]].groupby(["country_orig", "hs", "year"])["value_fob"].sum().rename("X20").reset_index()
    o = op.merge(cc, on=["country_orig", "hs", "year"], how="left").merge(G, on=["country_orig", "hs", "year"], how="left").merge(
        t20, on=["country_orig", "hs", "year"], how="left")
    o[["G", "X20"]] = o[["G", "X20"]].fillna(0)
    rows = []
    for col in ("high_PCI6", "rauch_full_con", "rauch_bin_con", "type"):
        oo = o.copy(); oo[col] = oo[col].fillna("Not classified")
        for g, y in oo.groupby(col):
            m = y[y["N"] >= 1]
            rows.append({"Cut": col, "Group": g, "Products": y["hs"].nunique(), "opy cells with X > 0": len(y),
                         "Share with N >= 1 (%)": 100 * (y["N"] >= 1).mean(), "Mean N (cells with N >= 1)": m["N"].mean(),
                         "Mean G (cells with N >= 1)": m["G"].mean(), "MNE share of value 2012-2018 (%)": 100 * y["XM"].sum() / y["X"].sum(),
                         "Share of top20 groups in MNE exports (%)": 100 * y["X20"].sum() / max(y["XM"].sum(), 1),
                         "Mean HHI of the cell": y["HHI"].mean(), "Mean share of the largest exporter": y["maxsh"].mean()})
    DESC["concentration"] = pd.DataFrame(rows)
    DESC["top20_groups"] = pd.DataFrame({"group key": list(fx.head(20).index), "agricultural exports of foreign affiliates 2012-2018 (US$ million)": (fx.head(20).values / 1e6)})


def step_cap(op, od):
    req = "V6-09"
    for st in ("Farm", "Processing"):
        d = op[(op["stage"] == st) & op["lnkl"].notna()]
        for dep, sheet in (("D", "1.1"), ("S", "1.2")):
            fit(d, dep, ["lnkl"], "FL1", sheet, f"{st} stage, {dep} on ln capital per worker, weighted by X_opy", "FL1 weighted", req, "descriptive",
                cl="CL-hs6", w="X")
    # 2.2 slopes without the group that generates them
    cls = pd.read_parquet(V6 / "classes_v6.parquet")
    kl = cls.dropna(subset=["src_id"]).groupby("src_id").agg(lnkl=("lnkl", "first"), v=("v_1218", "sum"), st=("stage", "first"))
    rows = []
    for st, drop in (("Farm", 21), ("Processing", 45)):
        for dep in DEPS:
            d = asoc_sample(od, "lnN", dep)
            d = d[(d["stage"] == st) & d["src_id"].notna()].copy()
            ids = sorted(d["src_id"].unique())
            names = []
            for i in ids:
                v = f"g{int(i)}"; d[v] = d["lnN"] * (d["src_id"] == i); names.append(v)
            m = pf.feols(f"{dep} ~ {' + '.join(names)} | odp + ody", data=d, vcov={"CRV1": "od"})
            b = m.coef(); V = pd.DataFrame(np.asarray(m._vcov), index=b.index, columns=b.index)
            keep = [v for v in b.index if int(v[1:]) != drop and np.isfinite(b[v]) and V.loc[v, v] > 0]
            x = np.array([kl.loc[int(v[1:]), "lnkl"] for v in keep]); bb = b[keep].values; VV = V.loc[keep, keep].values
            for wlab, w in (("export weighted", np.array([kl.loc[int(v[1:]), "v"] for v in keep])), ("unweighted", np.ones(len(keep)))):
                X = np.c_[np.ones(len(keep)), x]; Wm = np.diag(w / w.sum())
                A = np.linalg.solve(X.T @ Wm @ X, X.T @ Wm)[1]
                est = float(A @ bb); se = float(np.sqrt(A @ VV @ A))
                rows.append({"Stage": st, "Dependent variable": DEPS[dep], "Excluded group": drop, "Groups": len(keep), "Slope": wlab,
                             "Slope on ln capital per worker": est, "SE": se, "p": float(2 * norm.sf(abs(est / se)))})
    DESC["slopes_2_2"] = pd.DataFrame(rows)


def step_bridge(od, op):
    """P2a: the regression code restricted to the event-study sample (logs on positive cells), levels B and A."""
    req = "V6-16"
    for lev in ("B", "A"):
        pan = pd.read_parquet(V6 / f"ev6_{lev}_panel.parquet")
        c = pd.read_parquet(V6 / f"ev6_cells_{lev}.parquet")
        ins = set()
        for g in range(2014, 2019):
            ins |= set(c.index[((c["t0"] == g) | (c["status"] == "Never treated")) & (c[f"R_{g}"] == 1)])
        keys = ["country_orig", "dest", "hs"] if lev == "B" else ["country_orig", "hs"]
        cells = pan.drop_duplicates("cell").set_index("cell")[keys]
        cells = cells[cells.index.isin(ins)]
        if lev == "B":
            d = od.merge(cells.rename(columns={"dest": "country_dest"}), on=["country_orig", "country_dest", "hs"], how="inner")
            fe, cl = "odp + ody", "od+op"
        else:
            d = op.merge(cells, on=["country_orig", "hs"], how="inner")
            d["op"] = d["country_orig"] + "_" + d["hs"]
            fe, cl = "op + oy", "op"
        for dep in ("lnX", "lnXL", "lnNL"):
            fit(d, dep, ["D"], fe, "12.4", f"Level {lev}, P2 from the regression code: {dep} on D", "P2a", req, "diagnostic", cl=cl)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    steps = [a for a in sys.argv[1:] if not a.startswith("-")] or ["pci", "rauch", "race", "loc", "cap", "bridge"]
    od, op = load_od(), load_op()
    for st in steps:
        REGS.clear(); DESC.clear()
        t0 = time.time()
        {"pci": lambda: step_pci(od), "rauch": lambda: step_rauch(od, op), "race": lambda: step_race(od), "loc": lambda: step_loc(op),
         "cap": lambda: step_cap(op, od), "bridge": lambda: step_bridge(od, op)}[st]()
        if st == "pci":
            for r in REGS:
                if r["role"] == "primary":
                    p2 = r["cells"].get("RxPCI6", (np.nan, np.nan, np.nan))[2]
                    if 0.01 <= p2 <= 0.10:
                        t, pp = permutation_p(od, r["dep"])
                        r["permutation_p"] = pp
                        print(f"   permutation p for {r['dep']}: {pp:.3f} (t {t:.2f})")
        pickle.dump(REGS.copy(), open(OUT / f"v6_regs_{st}.pkl", "wb"))
        pickle.dump(DESC.copy(), open(OUT / f"v6_desc_{st}.pkl", "wb"))
        print(f"== {st}: {len(REGS)} regressions ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
