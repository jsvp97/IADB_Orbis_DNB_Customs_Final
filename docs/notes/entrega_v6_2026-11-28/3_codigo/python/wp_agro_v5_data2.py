"""
wp_agro_v5_data2.py  --  inputs of E9d, E9e and E10a (especificaciones_estimaciones_v5_2026-11-24.md)
=====================================================================================================

    WP_YEARS=2012-2018 python wp_agro_v5_data2.py   -> adds columns to data/intermediate/wp/v5/classes_v5.parquet and writes
                                                      v5/alt_measures_groups.parquet, v5/country_check.parquet

E10a  PCI_p: Product Complexity Index of the Harvard Growth Lab Atlas (Dataverse doi:10.7910/DVN/T4CHWJ, file
      hs92_product_year_4.csv, downloaded 2026-11-24 to data/raw/external/v5_downloads/atlas/). The Atlas publishes PCI for
      HS 1992 headings only, so each HS 2017 product takes the PCI of the HS 1992 heading of its HS 1992 code (UNSD
      conversion table HS 2017 to HS 1992, data/raw/unsd/), averaged over 2012-2018. high_PCI: above the export weighted
      median within agriculture (high_PCI_u: unweighted median); PCI_tercile: export weighted terciles.
E9d   alternative US measures by source group (sums over the farm types or industries of each group, as KL_p):
      farm: (land and buildings + machinery) per hired worker; machinery per acre operated; machinery per dollar of sales
      (2017 Census of Agriculture, national NAICS rows); processing: total real capital per employee; total real capital
      per dollar of value added (NBER and CES, 2012-2018 means).
E9e   country check: export weighted mean of ln KL_p of each origin's agricultural exports 2012-2018 against FAOSTAT net
      capital stock in agriculture, forestry and fishing (US$ 2015 prices) per worker in agriculture (ILO modelled
      estimates) and USDA ERS International Agricultural Productivity capital input per worker (Capital_Q / Labor_Q),
      2012-2018 means.
"""
from __future__ import annotations

import os
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("WP_HS17", "1")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_common as W  # noqa: E402
import wp_agro_v5_data as D5  # noqa: E402

V5 = W.WP_INT / "v5"
EXT = W.ROOT / "data" / "raw" / "external"
DL = EXT / "v5_downloads"
ORIGINS = ["ARG", "CHL", "COL", "CRI", "DOM", "PER", "PRY", "SLV", "URY"]


def pci() -> pd.DataFrame:
    a = pd.read_csv(DL / "atlas" / "f_13685116.csv", dtype={"product_hs92_code": str})
    a = a[a["year"].between(2012, 2018)].groupby("product_hs92_code")["pci"].mean().rename("PCI_p").reset_index()
    a = a.rename(columns={"product_hs92_code": "hs92_4"})
    x = pd.read_excel(W.UNSD / "HS2017toHS1992ConversionAndCorrelationTables.xlsx", sheet_name=None, dtype=str)
    conv = x[[s for s in x if s.startswith("Conversion")][0]].iloc[:, :2]
    conv.columns = ["hs", "hs92"]
    conv["hs92_4"] = conv["hs92"].str[:4]
    return conv.merge(a, on="hs92_4", how="left")[["hs", "hs92", "PCI_p"]]


RAUCH = {"w": "Homogeneous", "r": "Reference priced", "n": "Differentiated"}


def rauch_full() -> pd.DataFrame:
    """E10b: Rauch (1999) conservative and liberal class of every HS 2017 product from Rauch's SITC Rev. 2 file
    (Rauch_classification_revised.csv, econweb.ucsd.edu/~jrauch, downloaded 2026-11-24) through the UNSD HS-SITC-BEC
    correlation table (HS 2017 to SITC Rev. 2, data/raw/UNSD_HS-SITC-BEC_Correlations_2022.xlsx). When an HS 2017 code maps
    to several SITC codes, the modal class over its correlation rows wins (no trade weights exist at that level); ties go to
    the more differentiated class."""
    r = pd.read_csv(DL / "rauch" / "Rauch_classification_revised.csv", dtype=str)
    u = pd.read_excel(W.F_BEC, dtype=str, usecols=["HS17", "SITC2"]).dropna()
    u["sitc4"] = u["SITC2"].str[:4]
    m = u.merge(r, on="sitc4", how="left")
    rank = {"w": 0, "r": 1, "n": 2}
    out = []
    for hs, g in m.groupby("HS17"):
        row = {"hs": hs, "sitc2_codes": ";".join(sorted(g["sitc4"].unique())), "rauch_sitc_matched": int(g["con"].notna().sum()), "rauch_rows": len(g)}
        for c in ("con", "lib"):
            v = g[c].dropna()
            if len(v):
                cnt = v.value_counts()
                top = cnt[cnt == cnt.max()].index
                row[f"rauch_full_{c}"] = RAUCH[max(top, key=lambda k: rank[k])]
            else:
                row[f"rauch_full_{c}"] = None
        out.append(row)
    return pd.DataFrame(out)


def census_items() -> pd.DataFrame:
    d = pd.read_parquet(EXT / "usda_census2017_national_naics.parquet")
    d = d[d["DOMAIN_DESC"] == "NAICS CLASSIFICATION"].copy()
    d["code"] = d["DOMAINCAT_DESC"].str.extract(r"\((.*)\)")[0]
    d["v"] = pd.to_numeric(d["VALUE"].str.replace(",", ""), errors="coerce")
    items = {"MACHINERY TOTALS - ASSET VALUE, MEASURED IN $": "mach", "LABOR, HIRED - NUMBER OF WORKERS": "workers",
             "AG LAND, INCL BUILDINGS - ASSET VALUE, MEASURED IN $": "land", "FARM OPERATIONS - ACRES OPERATED": "acres",
             "COMMODITY TOTALS - SALES, MEASURED IN $": "sales"}
    d = d[d["SHORT_DESC"].isin(items)]
    return d.assign(item=d["SHORT_DESC"].map(items)).pivot_table(index="code", columns="item", values="v", aggfunc="first")


def nber() -> pd.DataFrame:
    n = pd.read_csv(EXT / "nberces5818v1_n2012.csv")
    n = n[n["year"].between(2012, 2018) & n["naics"].astype(str).str[:3].isin(["311", "312"])]
    n = n.groupby("naics")[["equip", "cap", "emp", "vadd"]].mean()
    n.index = n.index.astype(str)
    return n


def alt_measures(cls: pd.DataFrame) -> pd.DataFrame:
    c, n = census_items(), nber()
    g = cls[cls["stage"].isin(["Farm", "Processing"])].groupby(["stage", "src_id", "kl_source"]).agg(
        kl=("kl", "first"), v=("v_1218", "sum"), products=("hs", "size")).reset_index()
    rows = []
    for _, r in g.iterrows():
        parts = [p.strip() for p in r["kl_source"].split(" + ")]
        out = r.to_dict()
        if r["stage"] == "Farm":
            s = c.reindex(parts)[["mach", "workers", "land", "acres", "sales"]].sum(min_count=1)
            out.update(kl_check=s["mach"] / s["workers"] / 1e3, assets_pw=(s["land"] + s["mach"]) / s["workers"] / 1e3,
                       mach_per_acre=s["mach"] / s["acres"], mach_per_sales=s["mach"] / s["sales"], missing=int(c.reindex(parts)["mach"].isna().sum()))
        else:
            s = n.reindex(parts)[["equip", "cap", "emp", "vadd"]].sum(min_count=1)
            out.update(kl_check=s["equip"] / s["emp"], cap_pw=s["cap"] / s["emp"], cap_per_va=s["cap"] / s["vadd"],
                       missing=int(n.reindex(parts)["emp"].isna().sum()))
        rows.append(out)
    return pd.DataFrame(rows)


def country_check(cls: pd.DataFrame) -> pd.DataFrame:
    od = pd.read_parquet(W.WP_INT / "v4" / "odpy.parquet")[["country_orig", "hs", "X"]]
    od = od.merge(cls[["hs", "lnkl", "stage"]], on="hs")
    rows = []
    for o, x in od[od["lnkl"].notna()].groupby("country_orig"):
        r = {"iso3": o, "lnKL_export_weighted": np.average(x["lnkl"], weights=x["X"])}
        for st in ("Farm", "Processing"):
            y = x[x["stage"] == st]
            r[f"lnKL_export_weighted_{st.lower()}"] = np.average(y["lnkl"], weights=y["X"]) if len(y) else np.nan
        rows.append(r)
    out = pd.DataFrame(rows)
    z = zipfile.ZipFile(DL / "faostat" / "Investment_CapitalStock_E_All_Data_(Normalized).zip")
    f = pd.read_csv(z.open("Investment_CapitalStock_E_All_Data_(Normalized).csv"), encoding="latin1")
    f = f[f["Item"].str.startswith("Net Capital Stocks (Agriculture, Forestry and Fishing)") & (f["Element"] == "Value US$, 2015 prices")
          & f["Year"].between(2012, 2018)]
    z2 = zipfile.ZipFile(DL / "faostat" / "Employment_Indicators_Agriculture_E_All_Data_(Normalized).zip")
    e = pd.read_csv(z2.open("Employment_Indicators_Agriculture_E_All_Data_(Normalized).csv"), encoding="latin1")
    e = e[(e["Indicator"] == "Employment in agriculture - ILO modelled estimates") & (e["Sex"] == "Total") & e["Year"].between(2012, 2018)]
    m49 = pd.read_csv(z.open("Investment_CapitalStock_E_AreaCodes.csv"), encoding="latin1")
    fao_iso = {"Argentina": "ARG", "Chile": "CHL", "Colombia": "COL", "Costa Rica": "CRI", "Dominican Republic": "DOM",
               "Peru": "PER", "Paraguay": "PRY", "El Salvador": "SLV", "Uruguay": "URY", "United States of America": "USA"}
    k = f.assign(iso3=f["Area"].map(fao_iso)).dropna(subset=["iso3"]).groupby("iso3")["Value"].mean().rename("fao_netK_musd2015")
    l = e.assign(iso3=e["Area"].map(fao_iso)).dropna(subset=["iso3"]).groupby("iso3")["Value"].mean().rename("ilo_ag_emp_thousand")
    ers = pd.read_excel(DL / "ers" / "AgTFPInternational2022_long.xlsx", sheet_name="Wide format data")
    ers = ers[ers["ISO3"].isin(ORIGINS + ["USA"]) & ers["Year"].between(2012, 2018)].groupby("ISO3")[["Capital_Q", "Labor_Q"]].mean()
    ers["ers_capital_per_worker"] = ers["Capital_Q"] / ers["Labor_Q"]
    out = out.merge(k, left_on="iso3", right_index=True, how="left").merge(l, left_on="iso3", right_index=True, how="left")
    out = out.merge(ers[["ers_capital_per_worker"]], left_on="iso3", right_index=True, how="left")
    out["fao_capital_per_worker_usd2015"] = out["fao_netK_musd2015"] * 1e6 / (out["ilo_ag_emp_thousand"] * 1e3)
    out.attrs["m49"] = len(m49)
    return out


def main() -> None:
    import json
    cls = pd.read_parquet(V5 / "classes_v5.parquet")
    meta = json.load(open(V5 / "classes_v5_cuts.json", encoding="utf-8"))
    cls = cls.drop(columns=[c for c in ("hs92", "PCI_p", "high_PCI", "high_PCI_u", "PCI_tercile") if c in cls])
    p = pci()
    cls = cls.merge(p, on="hs", how="left")
    ok = cls["PCI_p"].notna()
    wmed = D5.wquantile(cls.loc[ok, "PCI_p"], cls.loc[ok, "v_1218"], 0.5)
    umed = float(cls.loc[ok, "PCI_p"].median())
    cls["high_PCI"] = np.where(~ok, "Not classified", np.where(cls["PCI_p"] > wmed, "High", "Low"))
    cls["high_PCI_u"] = np.where(~ok, "Not classified", np.where(cls["PCI_p"] > umed, "High", "Low"))
    cuts = [D5.wquantile(cls.loc[ok, "PCI_p"], cls.loc[ok, "v_1218"], q) for q in (1 / 3, 2 / 3)]
    cls["PCI_tercile"] = D5.group_by_cuts(cls["PCI_p"], cuts)
    meta["labels"]["high_PCI"] = f"PCI above the export weighted median ({wmed:.3f})"
    meta["labels"]["high_PCI_u"] = f"PCI above the unweighted median ({umed:.3f})"
    print(f"PCI: {ok.sum()} of {len(cls)} products, {100 * cls.loc[ok, 'v_1218'].sum() / cls['v_1218'].sum():.1f}% of exports; "
          f"weighted median {wmed:.3f}, unweighted {umed:.3f}")
    print(pd.crosstab(cls["high_PCI"], cls["type"]))
    # group labels: component names ordered by their own capital per worker (the component that drives the group first)
    c_, n_ = census_items(), nber()
    def comp_kl(code, st):
        if st == "Farm":
            return (c_.loc[code, "mach"] / c_.loc[code, "workers"]) if code in c_.index else 0
        return (n_.loc[code, "equip"] / n_.loc[code, "emp"]) if code in n_.index else 0
    def label(row):
        parts = [x.strip() for x in str(row["kl_source"]).split(" + ")]
        parts = sorted(parts, key=lambda x: -comp_kl(x, row["stage"]))
        names = [D5.NAICS.get(x, x) for x in parts]
        return names[0] if len(names) == 1 else " + ".join(names[:2]) + (f" + {len(names) - 2} more" if len(names) > 2 else "")
    m = cls["stage"].isin(["Farm", "Processing"])
    cls.loc[m, "src_label"] = cls[m].apply(label, axis=1)
    cls = cls.drop(columns=[c for c in ("rauch_full_con", "rauch_full_lib", "sitc2_codes", "rauch_sitc_matched", "rauch_rows") if c in cls])
    cls = cls.merge(rauch_full(), on="hs", how="left")
    print("Rauch complete:", cls["rauch_full_con"].value_counts(dropna=False).to_dict(), cls["rauch_full_lib"].value_counts(dropna=False).to_dict())
    print(pd.crosstab(cls["rauch_full_con"].fillna("NA"), cls["rauch_full_lib"].fillna("NA")))
    print(pd.crosstab(cls["rauch_con"].fillna("NA"), cls["rauch_full_con"].fillna("NA")))
    a = alt_measures(cls)
    a.to_parquet(V5 / "alt_measures_groups.parquet", index=False)
    print(a.round(3).to_string(max_colwidth=40))
    # product columns for E9d: the alternative measure of each product's group and High / Low at the export weighted median
    alt_cols = {"Farm": ["assets_pw", "mach_per_acre", "mach_per_sales"], "Processing": ["cap_pw", "cap_per_va"]}
    for st, cols in alt_cols.items():
        g = a[a["stage"] == st].set_index("src_id")
        m = cls["stage"] == st
        for col in cols:
            cls.loc[m, f"alt_{col}"] = cls.loc[m, "src_id"].map(g[col])
            thr = D5.wquantile(cls.loc[m, f"alt_{col}"], cls.loc[m, "v_1218"], 0.5)
            cls.loc[m, f"high_alt_{col}"] = np.where(cls.loc[m, f"alt_{col}"] > thr, "High", "Low")
            meta["labels"][f"{st}|high_alt_{col}"] = f"{col} above the export weighted median of the stage ({thr:.4g})"
    meta["alt"] = alt_cols
    cls.to_parquet(V5 / "classes_v5.parquet", index=False)
    json.dump(meta, open(V5 / "classes_v5_cuts.json", "w", encoding="utf-8"), indent=1)
    cc = country_check(cls)
    cc.to_parquet(V5 / "country_check.parquet", index=False)
    print(cc.round(3).to_string())
    from scipy.stats import spearmanr
    for col in ("fao_capital_per_worker_usd2015", "ers_capital_per_worker"):
        x = cc.dropna(subset=[col])
        print(col, "rank correlation with lnKL_export_weighted:", round(spearmanr(x["lnKL_export_weighted"], x[col]).correlation, 3), len(x))


if __name__ == "__main__":
    main()
