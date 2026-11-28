"""
wp_agro_v6_data.py  --  V6-03, V6-04 and hs_n1 of especificaciones_estimaciones_v6_2026-11-25.md
=================================================================================================

    WP_YEARS=2012-2018 python wp_agro_v6_data.py   -> data/intermediate/wp/v6/classes_v6.parquet, classes_v6_desc.pkl

New product columns (HS 2017 six-digit agricultural products of classes_v5.parquet):
  PCI6_hs17   OEC, PCI HS6 rev. 2017, mean of the available years 2018-2024 (cube complexity_pci_a_hs17_hs6), merged code by
              code with no conversion table.
  PCI4_hs17   OEC, PCI HS4 rev. 2017, same years (complexity_pci_a_hs17_hs4); each HS6 takes the value of its heading.
  ubiq_hs17   number of countries with RCA >= 1 in the product, computed from the OEC BACI trade cube in HS 2017
              (trade_i_baci_a_17), mean of 2018-2024. RCA_cp = (x_cp / X_c) / (x_p / X_w), X_c the country's total exports
              of all goods, x_p the world exports of the product, X_w world exports of all goods.
  PCI6_hs12   OEC, PCI HS6 rev. 2012, mean 2012-2016, taken to HS 2017 with the UNSD correlation table HS 2017 x HS 2012
              (simple average when one HS 2017 code links to several HS 2012 codes; all HS 2017 codes inherit when they share one).
  derived     PCI6_z, high_PCI6 (above the export weighted median of PCI6_hs17, as high_PCI), PCI4_z (PCI4_hs17 on the scale of
              PCI6_hs17), PCI6_dev = PCI6_z - PCI4_z, ubiq_z, PCI6_hs12_z.
  rauch_bin_con, rauch_bin_lib, rauch_hom_con   binary Rauch from rauch_full_con / rauch_full_lib.
  hs_n1       1 if the HS 2017 code has no one-to-one correspondence with HS 2012 in the UNSD table.
Downloads in data/raw/external/v6_downloads/oec/ (2026-11-27). Missing values stay missing (no fill from another revision).
"""
from __future__ import annotations

import json
import os
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("WP_HS17", "1")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_common as W  # noqa: E402

V5 = W.WP_INT / "v5"
V6 = W.WP_INT / "v6"
OEC = W.ROOT / "data" / "raw" / "external" / "v6_downloads" / "oec"


def wquantile(x: pd.Series, w: pd.Series, q: float) -> float:
    o = np.argsort(x.values)
    k, ww = x.values[o], w.values[o]
    c = np.cumsum(ww) / ww.sum()
    return float(k[np.searchsorted(c, q)])


def oec_pci(cube: str, digits: int, years: range) -> pd.Series:
    d = pd.DataFrame(json.load(open(OEC / f"{cube}.json"))["data"])
    idc = f"HS{digits} ID"
    d["code"] = (d[idc].astype(int) % (10 ** digits)).astype(str).str.zfill(digits)
    d = d[d["Year"].isin(list(years))]
    return d.groupby("code")["PCI"].mean()


def ubiquity() -> tuple[pd.Series, pd.DataFrame]:
    per = []
    for y in range(2018, 2025):
        a = pd.DataFrame(json.load(open(OEC / f"baci17_agri_{y}.json"))["data"])
        t = pd.DataFrame(json.load(open(OEC / f"baci17_tot_{y}.json"))["data"])
        a["hs"] = (a["HS6 ID"].astype(int) % 1_000_000).astype(str).str.zfill(6)
        Xc = t.set_index("Exporter Country ID")["Trade Value"]
        Xw = Xc.sum()
        xp = a.groupby("hs")["Trade Value"].sum()
        a["rca"] = (a["Trade Value"] / a["Exporter Country ID"].map(Xc)) / (a["hs"].map(xp) / Xw)
        u = a[a["rca"] >= 1].groupby("hs")["Exporter Country ID"].nunique().rename(y)
        per.append(u)
    U = pd.concat(per, axis=1)
    return U.mean(axis=1), U


def hs12_to_17(p12: pd.Series) -> tuple[pd.Series, pd.DataFrame]:
    c = W.hs_correlation(2012)
    c = c[c["old"].isin(p12.index)]
    c["pci"] = c["old"].map(p12)
    g = c.groupby("h17").agg(PCI6_hs12=("pci", "mean"), n_hs12=("old", "nunique"))
    share = c.groupby("old")["h17"].nunique()
    g["inherits"] = c.groupby("h17")["old"].apply(lambda s: int(any(share[o] > 1 for o in s)))
    return g["PCI6_hs12"], g


def hs_n1() -> pd.Series:
    c = W.hs_correlation(2012)
    return c.groupby("h17")["rel"].apply(lambda s: int(any(r.strip() != "1:1" for r in s)))


def build() -> tuple[pd.DataFrame, dict]:
    cls = pd.read_parquet(V5 / "classes_v5.parquet")
    desc = {}
    p6 = oec_pci("complexity_pci_a_hs17_hs6", 6, range(2018, 2025))
    p4 = oec_pci("complexity_pci_a_hs17_hs4", 4, range(2018, 2025))
    p12 = oec_pci("complexity_pci_a_hs12_hs6", 6, range(2012, 2017))
    ub, U = ubiquity()
    cls["PCI6_hs17"] = cls["hs"].map(p6)
    cls["PCI4_hs17"] = cls["hs"].str[:4].map(p4)
    cls["ubiq_hs17"] = cls["hs"].map(ub)
    p12_17, g12 = hs12_to_17(p12)
    cls["PCI6_hs12"] = cls["hs"].map(p12_17)
    ok6 = cls["PCI6_hs17"].notna()
    m6, s6 = cls.loc[ok6, "PCI6_hs17"].mean(), cls.loc[ok6, "PCI6_hs17"].std()
    cls["PCI6_z"] = (cls["PCI6_hs17"] - m6) / s6
    wmed = wquantile(cls.loc[ok6, "PCI6_hs17"], cls.loc[ok6, "v_1218"], 0.5)
    cls["high_PCI6"] = np.where(~ok6, "Not classified", np.where(cls["PCI6_hs17"] > wmed, "High", "Low"))
    cls["PCI4_z"] = (cls["PCI4_hs17"] - m6) / s6
    cls["PCI6_dev"] = cls["PCI6_z"] - cls["PCI4_z"]
    oku = cls["ubiq_hs17"].notna()
    cls["ubiq_z"] = (cls["ubiq_hs17"] - cls.loc[oku, "ubiq_hs17"].mean()) / cls.loc[oku, "ubiq_hs17"].std()
    ok12 = cls["PCI6_hs12"].notna()
    cls["PCI6_hs12_z"] = (cls["PCI6_hs12"] - cls.loc[ok12, "PCI6_hs12"].mean()) / cls.loc[ok12, "PCI6_hs12"].std()
    # binary Rauch
    for src, dst in (("rauch_full_con", "rauch_bin_con"), ("rauch_full_lib", "rauch_bin_lib")):
        cls[dst] = np.where(cls[src].isna(), "Not classified", np.where(cls[src] == "Differentiated", "Differentiated", "Not differentiated"))
    cls["rauch_hom_con"] = np.where(cls["rauch_full_con"].isna(), "Not classified",
                                    np.where(cls["rauch_full_con"] == "Homogeneous", "Homogeneous", "Not homogeneous"))
    cls["hs_n1"] = cls["hs"].map(hs_n1()).fillna(0).astype(int)
    # ---- documentation (sheet 10.3)
    V = cls["v_1218"].sum()
    cov = []
    for col, src in (("PCI6_hs17", "OEC PCI HS6 rev. 2017, mean 2018-2024"), ("PCI4_hs17", "OEC PCI HS4 rev. 2017, mean 2018-2024"),
                     ("ubiq_hs17", "computed from OEC BACI HS 2017, mean 2018-2024"), ("PCI6_hs12", "OEC PCI HS6 rev. 2012, mean 2012-2016, via UNSD"),
                     ("PCI_p", "Atlas PCI HS4 rev. 1992 (v5)")):
        okc = cls[col].notna()
        cov.append({"Column": col, "Source": src, "Products with data": int(okc.sum()), "Products without data": int((~okc).sum()),
                    "Share of exports 2012-2018 with data (%)": 100 * cls.loc[okc, "v_1218"].sum() / V})
    desc["coverage"] = pd.DataFrame(cov)
    m12 = g12.reindex(cls["hs"]).dropna(subset=["PCI6_hs12"])
    desc["hs12_mapping"] = pd.DataFrame([{"HS 2017 products with PCI6_hs12": len(m12),
                                          "that average two or more HS 2012 codes": int((m12["n_hs12"] > 1).sum()),
                                          "that inherit an HS 2012 code shared with other HS 2017 codes": int(m12["inherits"].sum())}])
    cc = ["PCI6_hs17", "PCI4_hs17", "PCI6_hs12", "PCI_p", "ubiq_hs17"]
    desc["spearman"] = cls[cc].corr(method="spearman").reset_index().rename(columns={"index": "Spearman correlation"})
    desc["high_PCI6_x_high_PCI"] = pd.crosstab(cls["high_PCI6"], cls["high_PCI"]).rename_axis(index="high_PCI6 (rows) / high_PCI of v5 (columns)").reset_index()
    comp = []
    for g, y in cls.groupby("high_PCI6"):
        vy = y["v_1218"].sum()
        r = {"high_PCI6": g, "Products": len(y), "Share of agricultural exports (%)": 100 * vy / V}
        for col in ("type", "stage", "rauch_bin_con"):
            for k, z in y.groupby(col):
                r[f"{col}: {k}, products"] = len(z)
                r[f"{col}: {k}, % of group exports"] = 100 * z["v_1218"].sum() / max(vy, 1)
        comp.append(r)
    desc["high_PCI6_composition"] = pd.DataFrame(comp)
    rb = []
    for col in ("rauch_bin_con", "rauch_bin_lib", "rauch_hom_con"):
        for g, y in cls.groupby(col):
            rb.append({"Column": col, "Group": g, "Products": len(y), "Share of agricultural exports (%)": 100 * y["v_1218"].sum() / V})
    desc["rauch_bin_counts"] = pd.DataFrame(rb)
    desc["rauch_bin_x_type"] = pd.crosstab(cls["rauch_bin_con"], cls["type"]).reset_index()
    desc["rauch_bin_x_stage"] = pd.crosstab(cls["rauch_bin_con"], cls["stage"]).reset_index()
    desc["hs_n1_counts"] = pd.DataFrame([{"Products with hs_n1 = 1": int(cls["hs_n1"].sum()), "of 860": len(cls),
                                          "Share of exports 2012-2018 (%)": 100 * cls.loc[cls["hs_n1"] == 1, "v_1218"].sum() / V}])
    desc["ubiquity_by_year"] = U.reindex(cls["hs"]).describe().T.reset_index().rename(columns={"index": "Year"})
    desc["meta"] = {"high_PCI6 cut (export weighted median of PCI6_hs17)": wmed, "PCI6_hs17 mean": m6, "PCI6_hs17 sd": s6}
    return cls, desc


def main() -> None:
    V6.mkdir(parents=True, exist_ok=True)
    cls, desc = build()
    cls.to_parquet(V6 / "classes_v6.parquet", index=False)
    pickle.dump(desc, open(V6 / "classes_v6_desc.pkl", "wb"))
    print(desc["coverage"].to_string(index=False))
    print(desc["hs12_mapping"].to_string(index=False))
    print(desc["spearman"].round(2).to_string(index=False))
    print(desc["rauch_bin_counts"].to_string(index=False))
    print(desc["hs_n1_counts"].to_string(index=False))
    print(desc["meta"])
    print(pd.crosstab(cls["high_PCI6"], cls["stage"]))


if __name__ == "__main__":
    main()
