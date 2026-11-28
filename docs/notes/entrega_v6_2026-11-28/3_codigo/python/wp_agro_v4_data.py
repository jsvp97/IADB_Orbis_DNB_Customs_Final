"""
wp_agro_v4_data.py  --  data for the estimations of especificaciones_estimaciones_v4_2026-11-17.md (agriculture paper v4)
=====================================================================================================================

    WP_YEARS=2012-2018 WP_SCOPES=agro python wp_agro_v4_data.py

Builds, under data/intermediate/wp/v4/:
  classes.parquet      one row per HS 2017 agricultural product with every classification of spec 0.3: type of production,
                       stage, capital per worker (UNSD link, wp_agro_classification.py), high_mean (the threshold of the
                       note: the aggregate ratio of the stage, US$112.9 and 118.2 thousand), high_median (export weighted
                       median of the stage), quintile (export weighted, within stage), lnKL, type x capital for both
                       thresholds, Rauch (1999) conservative and liberal, BEC Rev.4 end use and the inputs group.
  odpy.parquet         origin x destination x product x year cells (positive exports), spec 0.2 variables
  opy.parquet          origin x product x year cells, MNE counts from the firm data (a firm counts once per cell)
  sector.parquet       firm x origin x product x year rows of all products, for the sector context (E1)
  event_op.dta         balanced origin x product panel 2012-2018 with the entry of the first MNE (E6, cell A)
  event_odp.dta        balanced origin x destination x product panel (E6, cell B)

Destinations are real countries (wp_agro_paper.real_dest): free trade zones and the exporting country are dropped
(spec 0.1). Product codes are HS 2017 (WP_HS17=1, wp_common.to_hs2017), as in the paper since 3 November 2026.
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
import wp_agro_paper as A  # noqa: E402

assert W.HS17 and W.YEAR_WINDOW == (2012, 2018), "run with WP_YEARS=2012-2018 (WP_HS17=1 is set by default)"
V4 = W.WP_INT / "v4"
V4.mkdir(parents=True, exist_ok=True)
CLS_AGRO = W.WP_INT / "hs6_agro_classification.parquet"
YEARS = list(range(2012, 2019))
RAUCH = {"w": "Homogeneous", "r": "Reference priced", "n": "Differentiated"}


# ---------------------------------------------------------------------
# product classifications
# ---------------------------------------------------------------------
def weighted_quantile_groups(kl: pd.Series, w: pd.Series, q: int) -> pd.Series:
    """Export weighted quantile group of each product (1 = lowest). Products with the same capital per worker (the same
    census farm type or industry) fall in the same group: each distinct value is placed by the midpoint of its block
    of cumulative export share."""
    d = pd.DataFrame({"kl": kl, "w": w.fillna(0)}).dropna(subset=["kl"])
    b = d.groupby("kl")["w"].sum().sort_index()
    cum = b.cumsum() / b.sum()
    mid = cum - b / b.sum() / 2
    grp = np.minimum(q, np.floor(mid * q).astype(int) + 1)
    return kl.map(grp)


def weighted_median(kl: pd.Series, w: pd.Series) -> float:
    d = pd.DataFrame({"kl": kl, "w": w.fillna(0)}).dropna().sort_values("kl")
    c = d["w"].cumsum() / d["w"].sum()
    return float(d.loc[c >= 0.5, "kl"].iloc[0])


def rauch_hs17() -> pd.DataFrame:
    """Rauch (1999) class of each HS 2017 code: the class of its HS 2007 code in the UNSD conversion table HS 2017 to
    HS 2007. Conservative: con_34 of the product file. Liberal: the class with the largest liberal trade weight
    (lib_org_exch, lib_ref_price, lib_diff), available for fewer codes."""
    x = pd.read_excel(W.UNSD / "HS2017toHS2007ConversionAndCorrelationTables.xlsx", sheet_name=None, dtype=str)
    conv = x[[s for s in x if s.startswith("Conversion")][0]]
    conv.columns = ["hs", "hs07"]
    pc = pd.read_stata(W.F_PRODCHAR, columns=["hs07_6d", "con_34", "lib_org_exch", "lib_ref_price", "lib_diff"])
    pc["hs07"] = pc["hs07_6d"].astype(str).str.zfill(6)
    pc["rauch_con"] = pc["con_34"].map(RAUCH)
    lw = pc[["lib_org_exch", "lib_ref_price", "lib_diff"]]
    pc["rauch_lib"] = np.where(lw.notna().any(axis=1), np.array(["w", "r", "n"])[lw.fillna(-1).values.argmax(1)], None)
    pc["rauch_lib"] = pc["rauch_lib"].map(RAUCH)
    return conv.merge(pc[["hs07", "rauch_con", "rauch_lib"]].drop_duplicates("hs07"), on="hs07", how="left")[["hs", "rauch_con", "rauch_lib"]]


def bec_hs17() -> pd.DataFrame:
    u = pd.read_excel(W.F_BEC, dtype=str, usecols=["HS17", "BEC4"]).dropna()
    m = u.groupby(["HS17", "BEC4"]).size().reset_index(name="n").sort_values(["HS17", "n"], ascending=[True, False]).drop_duplicates("HS17")
    m = m.rename(columns={"HS17": "hs", "BEC4": "bec4"})[["hs", "bec4"]]
    m["bec_enduse"] = m["bec4"].map(W.BEC4_ENDUSE)
    return m


def classes() -> pd.DataFrame:
    t = pd.read_parquet(CLS_AGRO)
    c = pd.DataFrame({"hs": t["hs"], "description": t["description"], "hs2": t["hs"].str[:2], "hs4": t["hs4"],
                      "type": t["fao_type"], "stage": t["u_stage"], "kl": t["u_kl"], "kl_source": t["u_source"],
                      "high_mean": t["u_ci"], "v_1218": t["v"], "v_2018": t["v18"]})
    c["lnkl"] = np.log(c["kl"])
    thr_mean = {"Farm": 112.9, "Processing": 118.2}          # the thresholds of wp_agro_classification (rounded here only)
    c["thr_median"] = np.nan
    c["quintile"] = np.nan
    for st in ("Farm", "Processing"):
        s = c["stage"] == st
        med = weighted_median(c.loc[s, "kl"], c.loc[s, "v_1218"])
        c.loc[s, "thr_median"] = med
        c.loc[s, "quintile"] = weighted_quantile_groups(c.loc[s, "kl"], c.loc[s, "v_1218"], 5)
        # the export weighted mean, reported in the Samples sheet next to the threshold that is used
        c.loc[s, "kl_wmean_stage"] = np.average(c.loc[s, "kl"], weights=c.loc[s, "v_1218"])
        c.loc[s, "thr_mean"] = thr_mean[st]
    c["high_median"] = np.select([c["stage"] == "Not classified", c["kl"] > c["thr_median"]], ["Not classified", "High"], "Low")
    for k in ("mean", "median"):
        c[f"tx_{k}"] = np.where(c[f"high_{k}"] == "Not classified", "Not classified", c["type"] + ", " + c[f"high_{k}"].str.lower())
    c["lnkl_dm"] = c["lnkl"] - c.groupby("stage")["lnkl"].transform("mean")
    c = c.merge(rauch_hs17(), on="hs", how="left").merge(bec_hs17(), on="hs", how="left")
    c["input"] = W.agro_input_flag(c["hs"]).map({1: "Inputs", 0: "Other products"})
    return c


# ---------------------------------------------------------------------
# cells
# ---------------------------------------------------------------------
def firm_rows(scope: str = "agro") -> pd.DataFrame:
    f = W.load_fdpy()
    f = f[~f["country_orig"].isin(W.excluded_origins()) & (f["value_fob"] > 0)].copy()
    f["hs2"] = W.hs2_of(f["hs07_6d"])
    if scope != "all":
        f = W.scope_filter(f, scope)
    f["dest"] = A.real_dest(f["country_dest"], f["country_orig"])
    f = f[f["dest"].notna()].copy()
    f["ot"] = W.owner_type(f).replace({"ext_unknown": "ext"})
    f["firm"] = f["country_orig"] + "|" + f["Tax_ID"].astype(str)
    f["year"] = pd.to_numeric(f["year"]).astype(int)
    return f


def odpy_cells(f: pd.DataFrame) -> pd.DataFrame:
    k = ["country_orig", "dest", "hs07_6d", "year"]
    f = f.assign(vl=f["value_fob"] * (f["ot"] == "local"), vm=f["value_fob"] * (f["ot"] != "local"))
    g = f.groupby(k, as_index=False).agg(X=("value_fob", "sum"), XL=("vl", "sum"), XM=("vm", "sum"))
    for lab, sel in (("N", f["ot"] != "local"), ("NF", f["ot"] == "ext"), ("ND", f["ot"] == "dom"), ("NL", f["ot"] == "local")):
        n = f[sel].groupby(k)["firm"].nunique().rename(lab)
        g = g.merge(n, left_on=k, right_index=True, how="left")
    g[["N", "NF", "ND", "NL"]] = g[["N", "NF", "ND", "NL"]].fillna(0).astype(int)
    return g.rename(columns={"dest": "country_dest", "hs07_6d": "hs"})


def opy_cells(f: pd.DataFrame) -> pd.DataFrame:
    k = ["country_orig", "hs07_6d", "year"]
    f = f.assign(vl=f["value_fob"] * (f["ot"] == "local"), vm=f["value_fob"] * (f["ot"] != "local"))
    g = f.groupby(k, as_index=False).agg(X=("value_fob", "sum"), XL=("vl", "sum"), XM=("vm", "sum"))
    for lab, sel in (("N", f["ot"] != "local"), ("NF", f["ot"] == "ext"), ("ND", f["ot"] == "dom"), ("NL", f["ot"] == "local")):
        n = f[sel].groupby(k)["firm"].nunique().rename(lab)
        g = g.merge(n, left_on=k, right_index=True, how="left")
    g[["N", "NF", "ND", "NL"]] = g[["N", "NF", "ND", "NL"]].fillna(0).astype(int)
    return g.rename(columns={"hs07_6d": "hs"})


def add_vars(g: pd.DataFrame) -> pd.DataFrame:
    g["D"] = (g["N"] >= 1).astype(float)
    g["DF"] = (g["NF"] >= 1).astype(float)
    g["DD"] = (g["ND"] >= 1).astype(float)
    g["S"] = g["XM"] / g["X"]
    for v in ("X", "XL", "N", "NF", "ND", "NL"):
        g[f"ln{v}"] = np.where(g[v] > 0, np.log(g[v].where(g[v] > 0)), np.nan)
    g["anyXL"] = (g["XL"] > 0).astype(float)
    g["lnXLpf"] = np.where(g["NL"] > 0, np.log((g["XL"] / g["NL"].replace(0, np.nan)).where(g["XL"] > 0)), np.nan)
    return g


# ---------------------------------------------------------------------
# event panels (E6)
# ---------------------------------------------------------------------
def event_panel(cells: pd.DataFrame, keys: list[str], cls: pd.DataFrame) -> pd.DataFrame:
    """Balanced cell x year panel 2012-2018, zero filled, with the entry of the first MNE.
    t0: first year with an MNE exporter. Always treated: an MNE in 2012. Treated: t0 >= 2013 with at least two years
    with positive exports before t0 (pre2); pre3 marks three. Never treated: no MNE in any year, positive exports in at
    least two years."""
    c = cells[keys + ["year", "X", "XL", "N", "NF", "ND", "NL"]].copy()
    ids = c[keys].drop_duplicates().reset_index(drop=True)
    ids["cell"] = np.arange(1, len(ids) + 1)
    c = c.merge(ids, on=keys)
    full = pd.MultiIndex.from_product([ids["cell"], YEARS], names=["cell", "year"]).to_frame(index=False)
    p = full.merge(c.drop(columns=keys), on=["cell", "year"], how="left").fillna(0)
    p = p.merge(ids, on="cell")
    p["obs"] = (p["X"] > 0).astype(int)
    first = p[p["N"] >= 1].groupby("cell")["year"].min().rename("t0")
    p = p.merge(first, left_on="cell", right_index=True, how="left")
    pre = p[p["year"] < p["t0"]].groupby("cell")["obs"].sum().rename("npre")
    nobs = p.groupby("cell")["obs"].sum().rename("nobs")
    p = p.merge(pre, left_on="cell", right_index=True, how="left").merge(nobs, left_on="cell", right_index=True, how="left")
    p["npre"] = p["npre"].fillna(0)
    p["status"] = np.select([p["t0"].isna() & (p["nobs"] >= 2), p["t0"] == 2012, (p["t0"] >= 2013) & (p["npre"] >= 2)],
                            ["never", "always", "treated"], "excluded")
    p = p[p["status"].isin(["never", "treated"])].copy()
    p["gvar"] = np.where(p["status"] == "treated", p["t0"], 0).astype(int)
    p["pre3"] = ((p["status"] == "never") & (p["nobs"] >= 3) | (p["status"] == "treated") & (p["npre"] >= 3)).astype(int)
    # entrant type: foreign when a foreign MNE enters in t0
    nf0 = p[p["year"] == p["t0"]].set_index("cell")["NF"]
    p["entrant"] = p["cell"].map(pd.Series(np.where(nf0 > 0, "foreign", "domestic"), index=nf0.index)).fillna("")
    # exit of the MNE within two years of entry
    after = p[(p["year"] > p["t0"]) & (p["year"] <= p["t0"] + 2)]
    ex = after.groupby("cell")["N"].min().eq(0)
    p["exit2"] = p["cell"].map(ex).fillna(False).astype(int)
    p["balanced"] = (p["nobs"] == len(YEARS)).astype(int)
    # logs only where the variable is positive (no ln(1 + x), no asinh): zero years drop from the log outcomes
    for v in ("XL", "X", "NL"):
        p[f"ln{v}"] = np.where(p[v] > 0, np.log(p[v].where(p[v] > 0)), np.nan)
    p["anyXL"] = (p["XL"] > 0).astype(int)
    p = p.merge(cls[["hs", "type", "stage", "high_mean", "high_median"]], on="hs", how="left")
    return p


def events_only() -> None:
    cls = pd.read_parquet(V4 / "classes.parquet")
    events(pd.read_parquet(V4 / "opy.parquet"), pd.read_parquet(V4 / "odpy.parquet"), cls)


def main() -> None:
    if sys.argv[1:] == ["events"]:
        events_only(); return
    cls = classes()
    cls.to_parquet(V4 / "classes.parquet", index=False)
    print(f"classes: {len(cls)} products; median thresholds",
          cls.groupby("stage")["thr_median"].first().round(1).to_dict(), "export weighted means",
          cls.groupby("stage")["kl_wmean_stage"].first().round(1).to_dict())
    print(pd.crosstab(cls["stage"], cls["quintile"]))
    print("Rauch con", cls["rauch_con"].value_counts(dropna=False).to_dict(), "lib", cls["rauch_lib"].value_counts(dropna=False).to_dict())
    print("BEC", cls["bec_enduse"].value_counts(dropna=False).to_dict(), "inputs", cls["input"].value_counts().to_dict())

    f = firm_rows("agro")
    od = add_vars(odpy_cells(f))
    od.to_parquet(V4 / "odpy.parquet", index=False)
    op = add_vars(opy_cells(f))
    op.to_parquet(V4 / "opy.parquet", index=False)
    print(f"odpy {len(od):,} cells, opy {len(op):,} cells, firms {f['firm'].nunique():,}")
    keep = ["country_orig", "dest", "hs07_6d", "hs2", "year", "value_fob", "ot", "firm", "parent_key", "ID_Orbis_DNB", "iso3_parent"]
    fa = firm_rows("all")
    fa[keep].to_parquet(V4 / "sector.parquet", index=False)
    print(f"sector rows {len(fa):,}")
    del fa, f

    events(op, od, cls)


def events(op: pd.DataFrame, od: pd.DataFrame, cls: pd.DataFrame) -> None:
    for name, cells, keys in (("op", op, ["country_orig", "hs"]), ("odp", od, ["country_orig", "country_dest", "hs"])):
        p = event_panel(cells, keys, cls)
        p["orig"] = p["country_orig"]
        if name == "odp":
            p["od"] = p["country_orig"] + "_" + p["country_dest"]
        p.to_parquet(V4 / f"event_{name}.parquet", index=False)
        st = p.drop_duplicates("cell")
        print(f"event {name}: {st['cell'].nunique():,} cells, {len(p):,} rows; status", st["status"].value_counts().to_dict(),
              "cohorts", st.loc[st["status"] == "treated", "gvar"].value_counts().sort_index().to_dict())
        s = p.drop(columns=["status"])
        for col in s.columns:
            if str(s[col].dtype) in ("string", "object"):
                s[col] = s[col].astype(str).replace({"<NA>": "", "nan": "", "None": ""}).astype(object)
        s.to_stata(V4 / f"event_{name}.dta", write_index=False, version=118)
        p[[c_ for c_ in ("cell", "country_orig", "country_dest", "hs", "type", "stage", "high_mean", "high_median", "entrant")
           if c_ in p]].drop_duplicates("cell").to_parquet(V4 / f"event_{name}_labels.parquet", index=False)


if __name__ == "__main__":
    main()
