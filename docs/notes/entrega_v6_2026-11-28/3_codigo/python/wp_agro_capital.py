"""
wp_agro_capital.py  --  capital intensity of agricultural products (HS 01--24), 2026-11-02
=========================================================================================

Each HS6 product is assigned the capital intensity of the US industry that produces it (HS6 -> NAICS 2017 from
data/raw/HS6_to_NAICS_2017.dta), separately for the two stages of agricultural production:

  Farm stage (NAICS 111 crops, 112 animals): machinery and equipment on the operation (market value, $) per hired
      worker, 2017 Census of Agriculture, United States (USDA NASS, Quick Stats bulk file qs.census2017.txt.gz,
      national rows of the domain "NAICS CLASSIFICATION"). Hired workers are reported at the 4-digit level (5 or 6
      digits for tobacco, cotton, beef cattle, feedlots and dairy), so this is the finest level used. Farm scale
      (sales and acres per farm) is kept at the finest level available (up to 6 digits) for description.
  Processing stage (NAICS 311 food, 312 beverages and tobacco): real equipment capital stock per employee, NBER-CES
      Manufacturing Industry Database, 2012 NAICS version (nberces5818v1_n2012.csv), average 2012--2018.

Within each stage a product is "high capital intensity" when its industry's capital per worker is above the ratio
for the stage as a whole (total capital over total workers of all industries in the stage), and "low" otherwise.
Products of other industries (fishing 114, forestry 113, chemicals 325, ...) are not classified.

Outputs: data/intermediate/wp/hs6_capital_intensity.parquet and .csv (one row per HS6), and the industry table
output/wp_2012_2018/agro/Tables/tab_agp_capital_industries.tex (via main()).

    python wp_agro_capital.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_common as W  # noqa: E402

EXT = W.ROOT / "data" / "raw" / "external"
OUT = W.WP_INT / "hs6_capital_intensity"

# census rows that report hired workers, and which NAICS 6-digit codes they cover (prefix match, longest first)
FARM_KL_ROWS = ["112111", "112112", "11212", "11191", "11192", "11193 & 11194 & 11199", "1125 & 1129",
                "1111", "1112", "1113", "1114", "1122", "1123", "1124"]
FARM_LABEL = {"1111": "Oilseed and grain farming", "1112": "Vegetable and melon farming", "1113": "Fruit and tree nut farming",
              "1114": "Greenhouse and nursery production", "11191": "Tobacco farming", "11192": "Cotton farming",
              "11193 & 11194 & 11199": "Sugarcane, hay and other crop farming", "112111": "Beef cattle ranching",
              "112112": "Cattle feedlots", "11212": "Dairy cattle and milk production", "1122": "Hog and pig farming",
              "1123": "Poultry and egg production", "1124": "Sheep and goat farming", "1125 & 1129": "Aquaculture and other animals"}


def census() -> pd.DataFrame:
    d = pd.read_parquet(EXT / "usda_census2017_national_naics.parquet")
    d = d[d["DOMAIN_DESC"] == "NAICS CLASSIFICATION"].copy()
    d["code"] = d["DOMAINCAT_DESC"].str.extract(r"\((.*)\)")[0]
    d["v"] = pd.to_numeric(d["VALUE"].str.replace(",", ""), errors="coerce")
    items = {"MACHINERY TOTALS - ASSET VALUE, MEASURED IN $": "mach", "LABOR, HIRED - NUMBER OF WORKERS": "workers",
             "FARM OPERATIONS - NUMBER OF OPERATIONS": "farms", "FARM OPERATIONS - ACRES OPERATED": "acres",
             "COMMODITY TOTALS - SALES, MEASURED IN $": "sales"}
    d = d[d["SHORT_DESC"].isin(items)]
    return d.assign(item=d["SHORT_DESC"].map(items)).pivot_table(index="code", columns="item", values="v", aggfunc="first")


def farm_row(naics6: str, rows: list[str]) -> str | None:
    for r in rows:
        parts = [p.strip() for p in r.split("&")]
        if any(naics6.startswith(p) for p in parts):
            return r
    return None


def nber() -> pd.DataFrame:
    n = pd.read_csv(EXT / "nberces5818v1_n2012.csv")
    n = n[n["year"].between(2012, 2018) & n["naics"].astype(str).str[:3].isin(["311", "312"])]
    n = n.groupby("naics", as_index=False)[["equip", "emp", "vship"]].mean()
    n["naics"] = n["naics"].astype(str)
    return n


def build() -> pd.DataFrame:
    m = pd.read_stata(W.ROOT / "data" / "raw" / "HS6_to_NAICS_2017.dta")
    m["hs6"] = m["hs6"].astype(str).str.zfill(6)
    m["naics"] = m["naics"].astype(str)
    m = m[m["hs6"].str[:2].astype(int) <= 24].copy()

    c = census()
    kl_rows = [r for r in FARM_KL_ROWS]
    farm = c.loc[kl_rows, ["mach", "workers"]].copy()
    farm["kl"] = farm["mach"] / farm["workers"] / 1e3                     # thousand $ per hired worker
    farm_ratio = farm["mach"].sum() / farm["workers"].sum() / 1e3

    n = nber()
    n["kl"] = n["equip"] / n["emp"]                                         # $ million / thousand = thousand $ per worker
    proc_ratio = n["equip"].sum() / n["emp"].sum()

    rows = []
    for _, r in m.iterrows():
        code = r["naics"]
        out = dict(hs6=r["hs6"], naics=code, stage=None, industry=None, kl=np.nan, sales_per_farm=np.nan, acres_per_farm=np.nan)
        if code[:3] in ("111", "112"):
            fr = farm_row(code, kl_rows)
            if fr is not None:
                out.update(stage="Farm", industry=FARM_LABEL[fr], kl=farm.loc[fr, "kl"])
                for k in (6, 5, 4):                                         # scale at the finest level available
                    if code[:k] in c.index and pd.notna(c.loc[code[:k], "farms"]):
                        out.update(sales_per_farm=c.loc[code[:k], "sales"] / c.loc[code[:k], "farms"] / 1e3,
                                   acres_per_farm=c.loc[code[:k], "acres"] / c.loc[code[:k], "farms"])
                        break
        elif code[:3] in ("311", "312"):
            for k in (6, 5, 4):
                g = n[n["naics"].str[:k] == code[:k]]
                if len(g):
                    out.update(stage="Processing", industry=f"NAICS {code[:k]}", kl=g["equip"].sum() / g["emp"].sum())
                    break
        rows.append(out)
    h = pd.DataFrame(rows)
    thr = h["stage"].map({"Farm": farm_ratio, "Processing": proc_ratio})
    h["ki_high"] = np.where(h["stage"].isna(), np.nan, (h["kl"] > thr).astype(float))
    h["ki_group"] = np.select([h["stage"].isna(), h["ki_high"] == 1], ["Not classified", "High capital intensity"],
                              "Low capital intensity")
    h.attrs.update(farm_ratio=farm_ratio, proc_ratio=proc_ratio)
    print(f"farm-stage ratio {farm_ratio:,.1f} thousand $ per hired worker; processing ratio {proc_ratio:,.1f} thousand $ per employee")
    print(farm.assign(label=[FARM_LABEL[i] for i in farm.index]).round(1).to_string())
    return h


def main() -> None:
    h = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    h.to_parquet(OUT.with_suffix(".parquet"), index=False)
    h.to_csv(OUT.with_suffix(".csv"), index=False)
    print(h.groupby(["stage", "ki_group"], dropna=False).size())


if __name__ == "__main__":
    main()
