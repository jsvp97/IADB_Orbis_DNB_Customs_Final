"""
wp_agro_v5_data.py  --  product classifications of round v5 (E9, E10, E12.5 of especificaciones_estimaciones_v5_2026-11-24.md)
===============================================================================================================================

    WP_YEARS=2012-2018 python wp_agro_v5_data.py            -> data/intermediate/wp/v5/classes_v5.parquet + classes_v5_cuts.json

Adds to the v4 classes (data/intermediate/wp/v4/classes.parquet):
  src_id, src_label          the Census farm type or NBER and CES industry group behind KL_p (one value of KL_p each:
                             22 farm groups, 26 processing groups); label = names of its NAICS codes
  thr_* / high_*             the threshold ladder of E9a, by stage: unweighted median, export weighted median (= v4
                             high_median), aggregate ratio (= v4 high_mean), unweighted and export weighted 75th
                             percentile, and the natural gaps (farm 30, 55, 90, 120, 150; processing 70, 100, 130, 150,
                             180, 240, US$ thousand per worker). High = capital per worker above the threshold.
  tercile_stage, quartile_stage   export weighted, within stage (products sharing a KL_p value fall in one group)
  pool_*                     E9c: one threshold over all classified products (export weighted median, unweighted median,
                             unweighted and export weighted 75th percentile)
  processing_degree          E10c: Primary (farm stage), First processing (processing stage, HS 02 to 15), Further
                             processing (processing stage, HS 16 to 24)
Columns of E9d (alternative US measures), E10a (PCI) and E10b (Rauch complete) are added by wp_agro_v5_data2.py.
"""
from __future__ import annotations

import json
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
V5.mkdir(parents=True, exist_ok=True)

NAICS = {
    "1111": "oilseed and grain", "1112": "vegetable and melon", "1113": "fruit and tree nut", "1114": "greenhouse and nursery",
    "11191": "tobacco", "11193 & 11194 & 11199": "sugarcane, hay and other crops", "112111": "beef cattle ranching",
    "112112": "cattle feedlots", "11212": "dairy cattle", "1122": "hogs and pigs", "1123": "poultry and eggs",
    "1124": "sheep and goats", "1125 & 1129": "aquaculture and other animals",
    "311111": "dog and cat food", "311119": "other animal food", "311211": "flour milling", "311212": "rice milling",
    "311213": "malt", "311221": "wet corn milling", "311224": "oilseed processing", "311225": "fats and oils refining",
    "311230": "breakfast cereal", "311313": "beet sugar", "311314": "cane sugar", "311340": "nonchocolate confectionery",
    "311351": "chocolate from cacao", "311352": "chocolate from purchased chocolate", "311411": "frozen fruit and vegetables",
    "311412": "frozen specialty food", "311421": "fruit and vegetable canning", "311422": "specialty canning",
    "311423": "dried and dehydrated food", "311511": "fluid milk", "311512": "butter", "311513": "cheese",
    "311514": "dry and condensed dairy", "311520": "ice cream", "311611": "animal slaughtering", "311612": "meat processing",
    "311613": "rendering", "311615": "poultry processing", "311710": "seafood", "311811": "retail bakeries",
    "311812": "commercial bakeries", "311813": "frozen cakes", "311821": "cookies and crackers", "311824": "pasta and dough",
    "311830": "tortillas", "311911": "roasted nuts", "311919": "other snack food", "311920": "coffee and tea",
    "311930": "flavoring syrup", "311941": "mayonnaise and dressings", "311942": "spices", "311991": "perishable prepared food",
    "311999": "other food", "312111": "soft drinks", "312112": "bottled water", "312120": "breweries", "312130": "wineries",
    "312140": "distilleries", "312230": "tobacco manufacturing"}
GAPS = {"Farm": [30, 55, 90, 120, 150], "Processing": [70, 100, 130, 150, 180, 240]}


def src_label(codes: str) -> str:
    parts = [p.strip() for p in str(codes).split(" + ")]
    names = [NAICS.get(p, p) for p in parts]
    return names[0] if len(names) == 1 else (" + ".join(names[:2]) + (f" + {len(names) - 2} more" if len(names) > 2 else ""))


def wquantile(kl: pd.Series, w: pd.Series, q: float) -> float:
    o = np.argsort(kl.values)
    k, ww = kl.values[o], w.values[o]
    c = np.cumsum(ww) / ww.sum()
    return float(k[np.searchsorted(c, q)])


def group_by_cuts(kl: pd.Series, cuts: list[float]) -> pd.Series:
    """1 + number of cut points strictly below kl (cuts are values of kl: a product at a cut point stays in the lower group)."""
    return kl.apply(lambda v: np.nan if pd.isna(v) else 1 + sum(v > c for c in sorted(set(cuts))))


def build() -> tuple[pd.DataFrame, dict]:
    cls = pd.read_parquet(V4 / "classes.parquet")
    st = cls["stage"].isin(["Farm", "Processing"])
    # source groups
    g = cls[st].groupby(["stage", "kl_source"])["kl"].first().reset_index().sort_values(["stage", "kl"])
    g["src_id"] = np.arange(1, len(g) + 1)
    cls = cls.merge(g[["stage", "kl_source", "src_id"]], on=["stage", "kl_source"], how="left")
    cls["src_label"] = cls["kl_source"].map(src_label)
    labels, ladder = {}, {}
    for s in ("Farm", "Processing"):
        x = cls[cls["stage"] == s]
        thr = [("umed", "unweighted median", float(x["kl"].median())),
               ("wmed", "export weighted median (v4 high_median)", float(x["thr_median"].iloc[0])),
               ("agg", "aggregate ratio of the stage (v4 high_mean)", float(x["thr_mean"].iloc[0])),
               ("up75", "unweighted 75th percentile", float(x["kl"].quantile(0.75))),
               ("wp75", "export weighted 75th percentile", wquantile(x["kl"], x["v_1218"], 0.75))]
        thr += [(f"gap{v}", f"gap at US${v} thousand", float(v)) for v in GAPS[s]]
        thr = sorted(thr, key=lambda t: t[2])
        ladder[s] = []
        for code, lab, t in thr:
            col = f"high_{code}"
            if col not in cls:
                cls[col] = "Not classified"
            m = cls["stage"] == s
            cls.loc[m, col] = np.where(cls.loc[m, "kl"] > t, "High", "Low")
            cls.loc[m, f"thr_{code}"] = t
            labels[f"{s}|{col}"] = f"{lab} (US${t:,.1f} thousand)"
            ladder[s].append(col)
        for name, qs in (("tercile_stage", [1 / 3, 2 / 3]), ("quartile_stage", [0.25, 0.5, 0.75])):
            cuts = [wquantile(x["kl"], x["v_1218"], q) for q in qs]
            cls.loc[cls["stage"] == s, name] = group_by_cuts(cls.loc[cls["stage"] == s, "kl"], cuts).values
    # pooled thresholds (E9c)
    x = cls[st]
    pooled = []
    for code, lab, t in (("pwmed", "overall export weighted median", wquantile(x["kl"], x["v_1218"], 0.5)),
                         ("pumed", "overall unweighted median", float(x["kl"].median())),
                         ("pup75", "overall unweighted 75th percentile", float(x["kl"].quantile(0.75))),
                         ("pwp75", "overall export weighted 75th percentile", wquantile(x["kl"], x["v_1218"], 0.75))):
        col = f"pool_{code}"
        cls[col] = np.where(~st, "Not classified", np.where(cls["kl"] > t, "High", "Low"))
        cls[f"thr_{code}"] = t
        pooled.append((col, f"{lab} (US${t:,.1f} thousand)"))
        labels[col] = pooled[-1][1]
    # degree of processing (E10c)
    ch = pd.to_numeric(cls["hs2"], errors="coerce")
    cls["processing_degree"] = np.select([cls["stage"] == "Farm", (cls["stage"] == "Processing") & ch.between(2, 15),
                                          (cls["stage"] == "Processing") & ch.between(16, 24)],
                                         ["Primary", "First processing", "Further processing"], "Not classified")
    meta = {"labels": labels, "ladder": ladder, "pooled": pooled}
    return cls, meta


def main() -> None:
    cls, meta = build()
    cls.to_parquet(V5 / "classes_v5.parquet", index=False)
    json.dump(meta, open(V5 / "classes_v5_cuts.json", "w", encoding="utf-8"), indent=1)
    print(f"classes_v5: {len(cls)} products, {cls['src_id'].nunique()} source groups")
    for s in ("Farm", "Processing"):
        x = cls[cls["stage"] == s]
        for c in meta["ladder"][s]:
            h = x[x[c] == "High"]
            print(f"  {s:10s} {meta['labels'][s + '|' + c][:62]:62s} high: {len(h):3d} products, {100 * h['v_1218'].sum() / x['v_1218'].sum():5.1f}% of exports, "
                  f"field crops {100 * (h['type'] == 'Field crops').mean():5.1f}% of products")
        for c in ("tercile_stage", "quartile_stage"):
            print(f"  {s:10s} {c}: " + ", ".join(f"g{int(k)} {100 * v:.1f}%" for k, v in
                                                 (x.groupby(c)['v_1218'].sum() / x['v_1218'].sum()).items()))
    for c, lab in meta["pooled"]:
        h = cls[cls[c] == "High"]
        print(f"  pooled {lab[:60]:60s} high: {len(h)} products, farm {100 * (h['stage'] == 'Farm').mean():.0f}% of products")
    print(cls["processing_degree"].value_counts().to_dict())


if __name__ == "__main__":
    main()
