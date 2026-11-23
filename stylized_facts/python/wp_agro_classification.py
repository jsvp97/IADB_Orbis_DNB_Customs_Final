"""
wp_agro_classification.py  --  one table with the classifications of the agricultural products, 2026-11-03
========================================================================================================

    WP_YEARS=2012-2018 WP_HS17=1 python wp_agro_classification.py

For every HS 2017 product of HS chapters 01--24 exported by the nine origins in 2012--2018 (the codes of the base are
converted to HS 2017 with the UNSD correlation tables, wp_common.to_hs2017):

  * type of production (wp_agro_croptype.crop_type: FAO Indicative Crop Classification groups, by HS heading)
  * capital intensity, from the census of the industry that makes the product, with two links from HS to NAICS 2017:
      UNSD    the UNSD tables HS 2017 -> CPC 2.1 -> ISIC Rev.4 -> NAICS 2017 (the last one by the US Census Bureau,
              published in the UNSD classifications registry). UNSD has no direct HS to NAICS table. The stage is that
              of the ISIC classes (01 to 03 farm, 10 to 12 processing). The chain works at the level of ISIC classes,
              so a product reaches several NAICS industries; capital per worker adds up machinery (or equipment) and
              workers over all the census farm types (or NBER and CES industries) it reaches.
      Census  the HS 2017 to NAICS 2017 concordance of the US Census Bureau (data/raw/HS6_to_NAICS_2017.dta), one
              NAICS code per HS code.
    Farm stage: the farm types of the 2017 Census of Agriculture that report machinery and hired workers, as
    published, including the combined rows "11193 & 11194 & 11199" and "1125 & 1129". Processing stage: NBER and
    CES industries (NAICS 311 and 312). High = capital per worker above the ratio of the stage as a whole (our
    threshold; the census does not rank farm types).
  * the third classification: type of production x high or low capital intensity
  * a consistency check between the FAO type and the census farm types (farm stage)

WP_NAICS ("unsd" by default, or "census") picks the link that feeds the note (columns stage, capital_intensity, kl,
type_x_capital). Writes data/intermediate/wp/hs6_agro_classification.parquet and
docs/notes/WP_paperagro_product_classification.xlsx.
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
import wp_agro_capital as K  # noqa: E402
import wp_agro_croptype as C  # noqa: E402

assert W.HS17, "run with WP_HS17=1"
OUT = W.WP_INT / "hs6_agro_classification.parquet"
XLSX = W.ROOT / "docs" / "notes" / "WP_paperagro_product_classification.xlsx"
NAICS_SOURCE = os.environ.get("WP_NAICS", "unsd").strip().lower()
OPTS = {"unsd": "UNSD tables", "census": "Census concordance"}

# census farm types that each FAO type of production can come from (farm stage)
EXPECTED = {"Field crops": {"1111", "11192", "11193 & 11194 & 11199"},
            "Horticultural and plantation crops": {"1112", "1113", "1114", "11191", "11193 & 11194 & 11199"},
            "Livestock and fisheries": {"112111", "112112", "11212", "1122", "1123", "1124", "1125 & 1129"},
            "Other processed food and beverages": set()}


def descriptions() -> pd.Series:
    """HS 2017 descriptions (WITS HS 2017 to HS 2012 concordance)."""
    w = pd.read_csv(W.ROOT / "data" / "raw" / "Concordance_HS_2017_2012_WITS.csv", dtype=str, encoding="latin1")
    w.columns = ["h17", "d17", "h12", "d12"]
    return w.drop_duplicates("h17").set_index("h17")["d17"]


def products() -> pd.DataFrame:
    """Exports 2012-2018 and 2018, MNE share 2018, and the codes of the base behind each HS 2017 code."""
    d = W.scope_filter(W.mne_flags(W.build_cube()), "agro")
    d = d[d["value"] > 0]
    y = pd.to_numeric(d["year"]) == 2018
    g = d.groupby("hs07_6d").agg(v=("value", "sum"))
    g["v18"] = d[y].groupby("hs07_6d")["value"].sum()
    g["v18_mne"] = d[y & (d["owner_type"] != "local")].groupby("hs07_6d")["value"].sum()
    g = g.fillna({"v18": 0.0, "v18_mne": 0.0})
    g["mne18"] = np.where(g["v18"] > 0, 100 * g["v18_mne"] / g["v18"].replace(0, np.nan), np.nan)
    f = W.load_fdpy()
    f = f[(f["value_fob"] > 0) & f["hs07_6d"].isin(g.index) & ~f["country_orig"].isin(W.excluded_origins())]
    yrs = pd.to_numeric(f["year"]).astype(int)
    f = f.assign(rev=[W.HS_REVISION.get(k, 2007) for k in zip(f["country_orig"], yrs)])
    rep = f[f["hs_reported"] != f["hs07_6d"]].groupby("hs07_6d").apply(
        lambda s: ", ".join(f"{c} (HS {r})" for c, r in sorted(set(zip(s["hs_reported"], s["rev"])))))
    g["reported"] = rep
    return g


def capital_tables():
    c = K.census()
    farm = c.loc[K.FARM_KL_ROWS, ["mach", "workers", "farms"]].copy()
    farm["kl"] = farm["mach"] / farm["workers"] / 1e3
    n = K.nber()
    return farm, farm["mach"].sum() / farm["workers"].sum() / 1e3, n, n["equip"].sum() / n["emp"].sum()


def nber_rows(naics: list[str], n: pd.DataFrame) -> list[str]:
    """NBER and CES industries (2012 NAICS) of a list of NAICS 2017 codes, at the finest level that exists."""
    out = []
    for nc in naics:
        for k in (6, 5, 4):
            hit = n.loc[n["naics"].str[:k] == nc[:k], "naics"]
            if len(hit):
                out += list(hit)
                break
    return sorted(set(out))


def farm_rows(naics: list[str]) -> list[str]:
    rows = []
    for nc in naics:
        if "X" in nc:                    # the Census concordance writes 11211X (112111 or 112112) or 1123XX
            pre = nc.rstrip("X")
            rows += [r for r in K.FARM_KL_ROWS if any(p.strip().startswith(pre) or pre.startswith(p.strip()) for p in r.split("&"))]
        else:
            r = K.farm_row(nc, K.FARM_KL_ROWS)
            if r:
                rows.append(r)
    return sorted(set(rows), key=K.FARM_KL_ROWS.index)


def capital(stage: str, naics: list[str], farm, fr, n, pr) -> dict:
    """Pooled capital per worker over every census farm type (or NBER industry) that the NAICS codes reach."""
    if stage == "Farm":
        rows = farm_rows(naics)
        if rows:
            kl = farm.loc[rows, "mach"].sum() / farm.loc[rows, "workers"].sum() / 1e3
            return dict(stage="Farm", source=" + ".join(rows), source_label=", ".join(K.FARM_LABEL[r] for r in rows),
                        kl=kl, ci="High" if kl > fr else "Low")
    if stage == "Processing":
        rows = nber_rows([x for x in naics if x[:3] in ("311", "312")], n)
        if rows:
            s = n[n["naics"].isin(rows)]
            kl = s["equip"].sum() / s["emp"].sum()
            return dict(stage="Processing", source=" + ".join(rows), source_label="", kl=kl, ci="High" if kl > pr else "Low")
    return dict(stage="Not classified", source="", source_label="", kl=np.nan, ci="Not classified")


def unsd_links() -> pd.DataFrame:
    """HS 2017 -> CPC 2.1 -> ISIC Rev.4 -> NAICS 2017, UNSD classifications registry."""
    U = W.UNSD
    h = pd.read_csv(U / "CPC21-HS2017.csv", dtype=str)
    h.columns = ["hs", "hsp", "cpc", "cpcp"]
    h["hs"] = h["hs"].str.replace(".", "", regex=False)
    c = pd.read_csv(U / "cpc21-isic4.txt", dtype=str)
    c.columns = ["cpc", "cpcp", "isic", "isicp"]
    n = pd.read_excel(U / "ISIC_4_to_2017_NAICS.xlsx", dtype=str)
    n.columns = ["isicp", "isic", "isic_t", "naicsp", "naics", "naics_t", "note"]
    n["isic"] = n["isic"].str.zfill(4)
    x = h[["hs", "cpc"]].merge(c[["cpc", "isic"]], on="cpc", how="left").merge(n[["isic", "naics"]], on="isic", how="left")
    x["istage"] = x["isic"].str[:2].map(lambda s: "Farm" if s in ("01", "03") else ("Processing" if s in ("10", "11", "12") else "Other")
                                        if isinstance(s, str) else "Other")
    return x


def build() -> pd.DataFrame:
    farm, fr, n, pr = capital_tables()
    ex = products()
    t = pd.DataFrame({"hs": sorted(ex.index)})
    t["description"] = t["hs"].map(descriptions())
    t["hs4"] = t["hs"].str[:4]
    t["fao_type"] = C.crop_type(t["hs"])

    # option 1: UNSD tables
    x = unsd_links()
    rows = []
    for h in t["hs"]:
        s = x[x["hs"] == h]
        st = s.drop_duplicates(["cpc", "istage"]).groupby("istage")["cpc"].nunique().drop("Other", errors="ignore")
        # stage: the one of most CPC links; products with as many farm as processing links (live or fresh and
        # frozen fish or crustaceans, for example) are farm products
        stage = "" if st.empty else ("Farm" if st.get("Farm", 0) >= st.get("Processing", 0) else "Processing")
        nc = sorted(set(s.loc[s["istage"] == stage, "naics"].dropna()))
        r = capital(stage, nc, farm, fr, n, pr)
        rows.append(dict(hs=h, u_cpc=" ".join(sorted(set(s["cpc"].dropna()))), u_isic=" ".join(sorted(set(s["isic"].dropna()))),
                         u_naics=" ".join(nc), **{f"u_{k}": v for k, v in r.items()}))
    t = t.merge(pd.DataFrame(rows), on="hs")

    # option 2: Census concordance. Its chapters 01 and 02 are listed twice: as correct codes ("020130") and as
    # 10-digit tariff codes that lost the leading zero ("201300" = 0201.30); the broken keys start with 101-106 or
    # 201-210 (210 only with NAICS 3116: "210120" is bacon 0210.12 there, not tea extracts 2101.20). They are dropped.
    m = pd.read_stata(W.ROOT / "data" / "raw" / "HS6_to_NAICS_2017.dta")
    m["hs6"] = m["hs6"].astype(str).str.zfill(6); m["naics"] = m["naics"].astype(str)
    s3 = m["hs6"].str[:3]
    m = m[~(s3.isin([f"10{k}" for k in range(1, 7)] + [f"20{k}" for k in range(1, 10)]) | ((s3 == "210") & m["naics"].str.startswith("3116")))]
    conc = m.set_index("hs6")["naics"]
    m4 = m.assign(hs4=m["hs6"].str[:4])
    rows = []
    for h in t["hs"]:
        if h in conc.index:
            nc, lab = conc[h], conc[h]
        else:                           # not in the concordance: the most common NAICS code of its HS heading
            cand = m4.loc[m4["hs4"] == h[:4], "naics"]
            nc = cand.mode().iat[0] if len(cand) else ""
            lab = f"{nc} (heading {h[:4]})" if nc else ""
        stage = "Farm" if nc[:3] in ("111", "112") else ("Processing" if nc[:3] in ("311", "312") else "")
        r = capital(stage, [nc], farm, fr, n, pr)
        rows.append(dict(hs=h, c_naics=lab, **{f"c_{k}": v for k, v in r.items()}))
    t = t.merge(pd.DataFrame(rows), on="hs")

    exp = t["fao_type"].map(EXPECTED)
    for p in ("u", "c"):
        t[f"{p}_tx"] = np.where(t[f"{p}_ci"] == "Not classified", "Not classified",
                                t["fao_type"] + ", " + t[f"{p}_ci"].str.lower() + " capital intensity")
        t[f"{p}_consistency"] = np.select(
            [t[f"{p}_stage"] != "Farm", [bool(r) and all(x in e for x in r.split(" + ")) for r, e in zip(t[f"{p}_source"], exp)]],
            ["Not applicable", "Consistent"], "Check")
    t["same"] = np.where((t["u_stage"] == t["c_stage"]) & (t["u_ci"] == t["c_ci"]), "Yes", "No")
    t = t.merge(ex, left_on="hs", right_index=True, how="left")
    # the columns read by the note
    p = "u" if NAICS_SOURCE == "unsd" else "c"
    t["hs07_6d"] = t["hs"]
    t["stage"], t["capital_intensity"], t["kl"], t["type_x_capital"] = t[f"{p}_stage"], t[f"{p}_ci"], t[f"{p}_kl"], t[f"{p}_tx"]
    t.attrs.update(farm_ratio=fr, proc_ratio=pr)
    return t


def workbook(t: pd.DataFrame) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    fr, pr = t.attrs["farm_ratio"], t.attrs["proc_ratio"]
    cols = [("hs", "HS 2017 code", 10), ("description", "Product description (HS 2017)", 60),
            ("reported", "Codes in the customs data that become this HS 2017 code", 30),
            ("fao_type", "Type of production (FAO crop groups)", 30),
            ("u_cpc", "CPC 2.1 (UNSD)", 14), ("u_isic", "ISIC Rev.4 (UNSD)", 12), ("u_naics", "NAICS 2017 (UNSD)", 30),
            ("u_stage", "Stage", 12), ("u_source", "Census farm types or NBER and CES industries", 30),
            ("u_source_label", "Census farm types, names", 40),
            ("u_kl", "Capital per worker (US$ thousand)", 14), ("u_ci", "Capital intensity", 12),
            ("u_tx", "Type of production x capital intensity", 50), ("u_consistency", "FAO type and census farm type", 14),
            ("v18", "Exports 2018 (US$ million)", 12), ("mne18", "MNE share of exports 2018 (%)", 12)]
    cols_c = [("hs", "HS 2017 code", 10), ("description", "Product description (HS 2017)", 60), ("fao_type", "Type of production (FAO crop groups)", 30),
              ("c_naics", "NAICS 2017 (Census concordance)", 16), ("c_stage", "Stage", 12), ("c_source", "Census farm type or NBER and CES industry", 22),
              ("c_source_label", "Census farm type, name", 36), ("c_kl", "Capital per worker (US$ thousand)", 14), ("c_ci", "Capital intensity", 12),
              ("c_tx", "Type of production x capital intensity", 50), ("c_consistency", "FAO type and census farm type", 14),
              ("u_stage", "Stage, UNSD tables", 12), ("u_ci", "Capital intensity, UNSD tables", 12), ("same", "Same stage and capital intensity in both", 12),
              ("v18", "Exports 2018 (US$ million)", 12)]
    wb = Workbook(); ws = wb.active; ws.title = "Products"
    yellow = PatternFill("solid", fgColor="FFF2CC")

    def sheet(ws, cc):
        ws.append([c[1] for c in cc])
        for _, r in t.sort_values("hs").iterrows():
            vals = []
            for k, _, _ in cc:
                v = r[k]
                if k == "v18":
                    v = round(v / 1e6, 3) if v > 0 else None
                elif isinstance(v, float):
                    v = None if np.isnan(v) else round(v, 1)
                vals.append(v)
            ws.append(vals)
        for j, (k, _, w) in enumerate(cc, 1):
            ws.cell(row=1, column=j).font = Font(bold=True)
            ws.cell(row=1, column=j).alignment = Alignment(wrap_text=True, vertical="top")
            ws.column_dimensions[get_column_letter(j)].width = w
            if k in ("u_consistency", "c_consistency", "same"):
                for i in range(2, ws.max_row + 1):
                    if ws.cell(row=i, column=j).value in ("Check", "No"):
                        ws.cell(row=i, column=j).fill = yellow
        ws.freeze_panes = "C2"; ws.auto_filter.ref = ws.dimensions
    sheet(ws, cols)
    sheet(wb.create_sheet("Census concordance"), cols_c)

    # census farm types, as published
    ws = wb.create_sheet("Census farm types")
    farm, _, _, _ = capital_tables()
    ws.append(["Census row (NAICS)", "Census farm type", "Machinery and equipment (US$ thousand)", "Hired workers", "Farms",
               "Capital per hired worker (US$ thousand)", "Capital intensity", "Products, UNSD", "Products, Census"])
    for rr, v in farm.iterrows():
        ws.append([rr, K.FARM_LABEL[rr], round(v["mach"] / 1e3), int(v["workers"]), int(v["farms"]), round(v["kl"], 1),
                   "High" if v["kl"] > fr else "Low",
                   int(t["u_source"].apply(lambda x, rr=rr: rr in x.split(" + ")).sum()),
                   int(t["c_source"].apply(lambda x, rr=rr: rr in x.split(" + ")).sum())])
    ws.append(["All farm types", "All farms", round(farm["mach"].sum() / 1e3), int(farm["workers"].sum()), int(farm["farms"].sum()),
               round(fr, 1), "Threshold", int((t["u_stage"] == "Farm").sum()), int((t["c_stage"] == "Farm").sum())])
    for j, w in enumerate([22, 40, 22, 14, 12, 22, 16, 14, 14], 1):
        ws.column_dimensions[get_column_letter(j)].width = w; ws.cell(row=1, column=j).font = Font(bold=True)
        ws.cell(row=1, column=j).alignment = Alignment(wrap_text=True, vertical="top")

    # the two links compared
    ws = wb.create_sheet("Comparison")
    key = {p: np.where(t[f"{p}_stage"] == "Not classified", "Not classified", t[f"{p}_stage"] + ", " + t[f"{p}_ci"].str.lower())
           for p in ("u", "c")}
    groups = ["Farm, high", "Farm, low", "Processing, high", "Processing, low", "Not classified"]
    V = t["v18"].sum()
    ws.append(["Products by capital intensity under the two links (number of products; share of 2018 exports in % in parentheses)"])
    ws.cell(row=1, column=1).font = Font(bold=True)
    ws.append(["UNSD tables (rows) x Census concordance (columns)"] + groups + ["Total"])
    for gu in groups:
        row = [gu]
        for gc in groups + ["Total"]:
            s = t[(key["u"] == gu) & ((key["c"] == gc) if gc != "Total" else True)]
            row.append(f"{len(s)} ({100 * s['v18'].sum() / V:.1f})")
        ws.append(row)
    s = t; ws.append(["Total"] + [f"{int((key['c'] == gc).sum())} ({100 * t.loc[key['c'] == gc, 'v18'].sum() / V:.1f})" for gc in groups]
                     + [f"{len(s)} (100.0)"])
    agree = t["same"] == "Yes"
    ws.append([f"Same group in both: {int(agree.sum())} of {len(t)} products, {100 * t.loc[agree, 'v18'].sum() / V:.1f}% of 2018 exports"])
    ws.append([])
    ws.append(["Third classification under the two links (share of 2018 exports and MNE share, %)"])
    ws.cell(row=ws.max_row, column=1).font = Font(bold=True)
    ws.append(["Group", "Products, UNSD", "Share of exports, UNSD", "MNE share, UNSD", "Products, Census", "Share of exports, Census", "MNE share, Census"])
    for gname in sorted(set(t["u_tx"]) | set(t["c_tx"])):
        row = [gname]
        for p in ("u", "c"):
            s = t[t[f"{p}_tx"] == gname]
            row += [len(s), round(100 * s["v18"].sum() / V, 1), round(100 * s["v18_mne"].sum() / s["v18"].sum(), 1) if s["v18"].sum() > 0 else None]
        ws.append(row)
    ws.append([])
    ws.append(["Products whose group differs, by 2018 exports"])
    ws.cell(row=ws.max_row, column=1).font = Font(bold=True)
    ws.append(["HS 2017 code", "Description", "UNSD", "Census", "UNSD farm types or industries", "Census farm type or industry", "Exports 2018 (US$ million)"])
    for _, r in t[~agree].sort_values("v18", ascending=False).iterrows():
        ws.append([r["hs"], r["description"], key["u"][r.name], key["c"][r.name], r["u_source"], r["c_source"], round(r["v18"] / 1e6, 1)])
    ws.column_dimensions["A"].width = 44
    for col in "BCDEFG":
        ws.column_dimensions[col].width = 24

    ws = wb.create_sheet("Notes")
    for row in [
        ["Notes"],
        ["Products", "Every HS 2017 product of chapters 01 to 24 exported by the nine origins between 2012 and 2018. Exports and MNE shares are those of 2018; products not exported in 2018 have no value."],
        ["HS 2017", "The customs data report HS 2007 (Argentina, Dominican Republic, Paraguay, Peru, Uruguay until 2015), HS 2012 (Chile, Colombia, Costa Rica and El Salvador until 2016, Uruguay from 2016) and HS 2017 (Chile, Colombia, Costa Rica and El Salvador in 2017 and 2018). Every code is converted to HS 2017 with the UNSD correlation tables HS 2017 to HS 2007 and HS 2017 to HS 2012. When UNSD links an old code to several HS 2017 codes, it takes the same code number if it is among them, else the one with the largest exports of the origins that report in HS 2017."],
        ["Type of production", "Groups built on the crop groups of the FAO Indicative Crop Classification (FAO, 2015), by HS heading (stylized_facts/python/wp_agro_croptype.py)."],
        ["UNSD", "UNSD publishes no table from HS to NAICS. The chain is HS 2017 to CPC 2.1 (UNSD), CPC 2.1 to ISIC Rev.4 (UNSD) and ISIC Rev.4 to NAICS 2017 (US Census Bureau, in the UNSD classifications registry). Stage: ISIC classes 01 to 03 are the farm stage and 10 to 12 the processing stage; a product with links to both takes the stage of most of its CPC links. Capital per worker adds up machinery and hired workers (or equipment and employees) over all the census farm types (or NBER and CES industries) the chain reaches."],
        ["Census", "HS 2017 to NAICS 2017 concordance of the US Census Bureau (data/raw/HS6_to_NAICS_2017.dta), one NAICS code per HS code. Codes missing from it take the most common NAICS code of their HS heading, written as (heading xxxx)."],
        ["Census farm type", "The NAICS rows of the 2017 Census of Agriculture (USDA NASS, Quick Stats, domain NAICS CLASSIFICATION) that report both the market value of machinery and equipment and the number of hired workers. These are the census's own farm types, including its combined rows 11193 & 11194 & 11199 and 1125 & 1129."],
        ["Processing", "NAICS 311 and 312 industries of the NBER and CES Manufacturing Industry Database (2012 NAICS), real equipment capital over employment, averages of 2012 to 2018, at the finest level available."],
        ["High or low", f"High when capital per worker is above the ratio of the stage as a whole: {fr:.1f} thousand US$ per hired worker for all farms of the census and {pr:.1f} thousand US$ per employee for all food and beverage industries. This threshold is the authors' choice. The census reports the inputs by farm type but does not rank them."],
        ["Consistency", "Farm stage only. Field crops are expected in census farm types 1111, 11192 and 11193 & 11194 & 11199. Horticultural and plantation crops in 1112, 1113, 1114, 11191 and 11193 & 11194 & 11199. Livestock and fisheries in 112."],
        ["Used in the note", f"{OPTS[NAICS_SOURCE]}. The sheet Products has this link and the sheet Census concordance the other one. The sheet Comparison compares them, and the sheet Regressions, both links of the master workbook compares the regressions."],
        ["Source", "stylized_facts/python/wp_agro_classification.py; UNSD tables in data/raw/unsd (downloaded 3 November 2026 from unstats.un.org)."]]:
        ws.append(row)
    ws.column_dimensions["A"].width = 22; ws.column_dimensions["B"].width = 160; ws["A1"].font = Font(bold=True)
    for i in range(2, ws.max_row + 1):
        ws.cell(row=i, column=2).alignment = Alignment(wrap_text=True, vertical="top")
    XLSX.parent.mkdir(parents=True, exist_ok=True)
    wb.save(XLSX)


def main() -> None:
    t = build()
    t.to_parquet(OUT, index=False)
    workbook(t)
    V = t["v18"].sum()
    print(f"{len(t)} products; farm ratio {t.attrs['farm_ratio']:.1f}, processing ratio {t.attrs['proc_ratio']:.1f}; note uses {NAICS_SOURCE}")
    for p in ("u", "c"):
        k = t[f"{p}_stage"] + " " + t[f"{p}_ci"]
        print(p, (t.groupby(k)["v18"].sum() / V * 100).round(1).to_dict(), t[f"{p}_consistency"].value_counts().to_dict())
    print("same:", (t["same"] == "Yes").sum(), f"{100 * t.loc[t['same'] == 'Yes', 'v18'].sum() / V:.1f}% of 2018 exports")
    print(pd.crosstab(t["fao_type"], t["u_stage"] + " " + t["u_ci"]).to_string())
    print(pd.crosstab(t["fao_type"], t["c_stage"] + " " + t["c_ci"]).to_string())
    for p in ("u", "c"):
        chk = t[t[f"{p}_consistency"] == "Check"]
        print(p, "check:\n", chk[["hs", "description", "fao_type", f"{p}_source", "v18"]].assign(v18=lambda x: (x.v18 / 1e6).round(1)).to_string()[:3000])
    print(f"-> {XLSX}")


if __name__ == "__main__":
    main()
