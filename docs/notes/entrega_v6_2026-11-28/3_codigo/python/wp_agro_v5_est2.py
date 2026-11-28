"""
wp_agro_v5_est2.py  --  E9d, E9e, E10a, E10b and E10d of especificaciones_estimaciones_v5_2026-11-24.md
=======================================================================================================

Loaded by wp_agro_v5_est.py (steps e9d, e9e, e10a, e10b, e10d); needs the columns of wp_agro_v5_data2.py (PCI, alternative US
measures, country check) and, for e10b, the complete Rauch classification (wp_agro_v5_rauch.py, Rauch's SITC Rev. 2 file).
"""
from __future__ import annotations

import gc

import numpy as np
import pandas as pd

import wp_common as W
import wp_agro_v4_est as E4

V5 = W.WP_INT / "v5"


def steps(od, op, cls, fit, het_generic, loc_generic, DESC):
    def comp(col, lab):
        x = cls.copy()
        V = x["v_1218"].sum()
        rows = []
        for g, y in x.groupby(col):
            r = {"Cut": lab, "Group": g, "Products": len(y), "Share of agricultural exports (%)": 100 * y["v_1218"].sum() / V}
            for ty in E4.TYPES.values():
                r[f"{ty}, % of group exports"] = 100 * y.loc[y["type"] == ty, "v_1218"].sum() / max(y["v_1218"].sum(), 1)
            for st in ("Farm", "Processing", "Not classified"):
                r[f"{st} stage, % of group exports"] = 100 * y.loc[y["stage"] == st, "v_1218"].sum() / max(y["v_1218"].sum(), 1)
            r["high_mean High, % of group exports"] = 100 * y.loc[y["high_mean"] == "High", "v_1218"].sum() / max(y["v_1218"].sum(), 1)
            rows.append(r)
        return rows

    def e10a():
        DESC["E10a_composition"] = pd.DataFrame(comp("high_PCI", "PCI, export weighted median") + comp("high_PCI_u", "PCI, unweighted median")
                                                + comp("PCI_tercile", "PCI terciles"))
        HL = {"hi": "High", "lo": "Low"}
        for col, lab in (("high_PCI", "PCI above the export weighted median"), ("high_PCI_u", "PCI above the unweighted median")):
            het_generic(od, "E10a", col, HL, lab, [("high = low", ("hi", "lo"))])
        het_generic(od, "E10a", "PCI_tercile", {"t1": 1.0, "t2": 2.0, "t3": 3.0}, "PCI terciles",
                    [("lowest = middle", ("t1", "t2")), ("lowest = highest", ("t1", "t3"))])
        for reg in ("lnN", "D"):
            for depk, (dep, dl) in E4.DEP.items():
                d = E4.base_sample(od, reg, dep).copy()
                d[f"{reg}_x_pci"] = d[reg] * d["PCI_p"]
                for fe in E4.FE_BODY:
                    fit(d, dep, [reg, f"{reg}_x_pci"], fe, "E10a", f"{reg} and {reg} x PCI (continuous), {dl}", fe, E4.REG[reg][1])
                del d; gc.collect()

        def prep(d):
            d["hi_pci"] = (d["high_PCI"] == "High").astype(float)
            d["hi_pci_u"] = (d["high_PCI_u"] == "High").astype(float)
            d["pci_t2"] = (d["PCI_tercile"] == 2).astype(float)
            d["pci_t3"] = (d["PCI_tercile"] == 3).astype(float)
        loc_generic(op, "E10a", {"PCI": ["PCI_p"], "high_PCI": ["hi_pci"], "high_PCI_u": ["hi_pci_u"], "PCI terciles": ["pci_t2", "pci_t3"],
                                 "PCI and ln KL": ["PCI_p", "lnkl"]}, prep, "PCI")

    def e9d():
        import json
        meta = json.load(open(V5 / "classes_v5_cuts.json", encoding="utf-8"))
        a = pd.read_parquet(V5 / "alt_measures_groups.parquet")
        from scipy.stats import spearmanr
        rows = []
        for st, cols in meta["alt"].items():
            g = a[a["stage"] == st]
            for col in cols:
                ok = g[col].notna()
                rows.append({"Stage": st, "Measure": col, "Groups": int(ok.sum()),
                             "Rank correlation with KL_p (Spearman, groups)": spearmanr(g.loc[ok, "kl"], g.loc[ok, col]).correlation,
                             "Correlation of logs, export weighted": np.corrcoef(np.log(g.loc[ok, "kl"]), np.log(g.loc[ok, col]))[0, 1]
                             if ok.sum() > 2 else np.nan})
        DESC["E9d_rank"] = pd.DataFrame(rows)
        DESC["E9d_groups"] = a
        for reg in ("lnN", "D"):
            for depk, (dep, dl) in E4.DEP.items():
                base = E4.base_sample(od, reg, dep)
                for st, cols in meta["alt"].items():
                    d = base[base["stage"] == st].copy()
                    for col in ["high_wmed"] + [f"high_alt_{c}" for c in cols]:
                        regs = E4.interact(d, reg, col, {"hi": "High", "lo": "Low"}, f"{reg}_{col}")
                        lab = "KL_p (current)" if col == "high_wmed" else col.replace("high_alt_", "")
                        for fe in E4.FE_BODY:
                            fit(d, dep, regs, fe, "E9d", f"{st} stage, {reg} x high/low, export weighted median of {lab}, {dl}", fe,
                                E4.REG[reg][1] + f", {st.lower()} stage", tests=[("high = low", (f"{reg}_{col}_hi", f"{reg}_{col}_lo"))])
                    del d; gc.collect()

    def e9e():
        cc = pd.read_parquet(V5 / "country_check.parquet")
        from scipy.stats import spearmanr
        rows = []
        for x in ("lnKL_export_weighted", "lnKL_export_weighted_farm", "lnKL_export_weighted_processing"):
            for y in ("fao_capital_per_worker_usd2015", "ers_capital_per_worker"):
                z = cc.dropna(subset=[x, y])
                rows.append({"Product measure (origin's export mix)": x, "Country measure": y, "Countries": len(z),
                             "Rank correlation (Spearman)": spearmanr(z[x], z[y]).correlation})
        DESC["E9e_country"] = cc
        DESC["E9e_rank"] = pd.DataFrame(rows)
        DESC["E9e_product_level"] = pd.DataFrame([
            {"Country": c, "Census": y, "What was found": "Not built in this round: the census microdata or crop tables with machinery by crop or farm type "
             "were not downloaded; the spec lists them as to be verified."}
            for c, y in (("Argentina", "CNA 2018"), ("Brazil", "Censo Agropecuario 2017"), ("Chile", "Censo 2021"), ("Colombia", "CNA 2014"),
                         ("Paraguay", "CAN 2022"), ("Uruguay", "CGA 2011"))])

    def e10d():
        x = cls.copy()
        for k in ("mean", "median"):
            x[f"kp_{k}"] = np.where((x[f"high_{k}"] == "Not classified") | (x["high_PCI"] == "Not classified"), "Not classified",
                                    "KL " + x[f"high_{k}"].str.lower() + ", PCI " + x["high_PCI"].str.lower())
        DESC["E10d_composition"] = pd.DataFrame(comp_x(x, "kp_mean", "KL (aggregate ratio) x PCI") + comp_x(x, "kp_median", "KL (median) x PCI"))
        o = od.merge(x[["hs", "kp_mean", "kp_median"]], on="hs", how="left")
        G = {"hh": "KL high, PCI high", "hl": "KL high, PCI low", "lh": "KL low, PCI high", "ll": "KL low, PCI low"}
        for k, lab in (("kp_mean", "KL (aggregate ratio) x PCI"), ("kp_median", "KL (median) x PCI")):
            het_generic(o, "E10d", k, G, lab, [("KL high = KL low, PCI high", ("hh", "lh")), ("KL high = KL low, PCI low", ("hl", "ll")),
                                               ("PCI high = PCI low, KL high", ("hh", "hl")), ("PCI high = PCI low, KL low", ("lh", "ll"))])
        p = op.merge(x[["hs", "kp_mean", "kp_median"]], on="hs", how="left")

        def prep(d):
            for k in ("kp_mean", "kp_median"):
                for g, v in (("hh", "KL high, PCI high"), ("hl", "KL high, PCI low"), ("lh", "KL low, PCI high")):
                    d[f"{k}_{g}"] = (d[k] == v).astype(float)
                d.loc[d[k] == "Not classified", [f"{k}_{g}" for g in ("hh", "hl", "lh")]] = np.nan
        loc_generic(p, "E10d", {"KL (aggregate ratio) x PCI": [f"kp_mean_{g}" for g in ("hh", "hl", "lh")],
                                "KL (median) x PCI": [f"kp_median_{g}" for g in ("hh", "hl", "lh")]}, prep, "KL x PCI (KL low, PCI low omitted)")

    def comp_x(x, col, lab):
        V = x["v_1218"].sum()
        return [{"Cut": lab, "Group": g, "Products": len(y), "Share of agricultural exports (%)": 100 * y["v_1218"].sum() / V,
                 **{f"{ty}, % of group exports": 100 * y.loc[y["type"] == ty, "v_1218"].sum() / max(y["v_1218"].sum(), 1) for ty in E4.TYPES.values()}}
                for g, y in x.groupby(col)]

    def e10b():
        if "rauch_full_con" not in cls:
            DESC["E10b_status"] = pd.DataFrame([{"Status": "Not run: the complete Rauch classification needs Rauch's SITC Rev. 2 file, "
                                                 "which was not downloaded in this round."}])
            return
        R = {"hom": "Homogeneous", "ref": "Reference priced", "diff": "Differentiated"}
        x = cls.copy()
        DESC["E10b_classes"] = pd.concat([
            pd.crosstab(x["rauch_full_con"].fillna("not classified"), x["rauch_full_lib"].fillna("not classified")).rename_axis(index="conservative (rows) / liberal (columns)").reset_index(),
            pd.crosstab(x["rauch_con"].fillna("not classified"), x["rauch_full_con"].fillna("not classified")).rename_axis(index="v4 con_34 (rows) / complete conservative (columns)").reset_index()],
            ignore_index=True)
        ch = x[(x["rauch_full_con"] != x["rauch_full_lib"]) | (x["rauch_con"] != x["rauch_full_con"])]
        DESC["E10b_changes"] = ch[["hs", "description", "type", "sitc2_codes", "rauch_con", "rauch_full_con", "rauch_full_lib", "v_1218"]].rename(
            columns={"rauch_con": "v4 conservative (con_34)", "rauch_full_con": "complete conservative", "rauch_full_lib": "complete liberal",
                     "v_1218": "exports 2012-2018"})
        # E7c rerun: capital intensity (aggregate ratio) x differentiated, complete conservative classification
        o = od.copy()
        o["kr"] = np.where((o["high_mean"] == "Not classified") | o["rauch_full_con"].isna(), "other",
                           o["high_mean"].str.lower() + "_" + np.where(o["rauch_full_con"] == "Differentiated", "diff", "nd"))
        het_generic(o, "E10b", "kr", {"hi_diff": "high_diff", "hi_nd": "high_nd", "lo_diff": "low_diff", "lo_nd": "low_nd"},
                    "capital intensity (aggregate ratio) x Rauch complete conservative",
                    [("high = low, differentiated", ("hi_diff", "lo_diff")), ("high = low, not differentiated", ("hi_nd", "lo_nd"))])
        for col, lab in (("rauch_full_con", "Rauch complete, conservative"), ("rauch_full_lib", "Rauch complete, liberal")):
            DESC.setdefault("E10b_composition", pd.DataFrame())
            DESC["E10b_composition"] = pd.concat([DESC["E10b_composition"], pd.DataFrame(comp(col, lab))])
            het_generic(od, "E10b", col, R, lab, [("homogeneous = differentiated", ("hom", "diff")), ("reference = differentiated", ("ref", "diff"))])

            def prep(d, col=col):
                d["r_ref"] = (d[col] == "Reference priced").astype(float)
                d["r_diff"] = (d[col] == "Differentiated").astype(float)
                d.loc[d[col].isna(), ["r_ref", "r_diff"]] = np.nan
            loc_generic(op, "E10b", {lab: ["r_ref", "r_diff"]}, prep, lab + " (homogeneous omitted)")

    return {"e10a": e10a, "e9d": e9d, "e9e": e9e, "e10d": e10d, "e10b": e10b}
