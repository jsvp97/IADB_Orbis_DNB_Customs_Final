"""
wp_agro_croptype.py  --  agricultural products by type of crop / production (2026-10-13)
=========================================================================================

Groups the agricultural HS6 products (HS 01--24) by the kind of farm production behind them, to compare the
multinational share of exports across them:

  Field crops              cereals, oilseeds, pulses and sugar crops (FAO Indicative Crop Classification groups 1, 4,
                           7 and 8) and root crops (group 5), their milling and crushing products (flour, vegetable oils, oilcake and meal)
                           and fodder. Grown on large areas and harvested by machine.
  Horticultural and        fruit and nuts, vegetables, stimulant and spice crops (coffee, tea, cocoa, spices), flowers
  plantation crops         and live plants, tobacco, hops and medicinal plants (ICC groups 2, 3, 6 and part of 9), with
                           their preparations (HS 20) and wine. Fruit, vegetables and horticulture are the
                           labor-intensive crops (USDA ERS, "Hired Farmworkers a Major Input for Some U.S. Farm
                           Sectors", Amber Waves 2008: hired labor is 30--40 percent of cash expenses for these growers).
  Livestock and fisheries  live animals, meat, fish, dairy, eggs, other animal products, animal fats, their
                           preparations (HS 16) and meat or fish meal.
  Other processed food     gums and resins, plaiting materials, cereal preparations, sugar confectionery,
  and beverages            miscellaneous preparations, beverages other than wine, residues of the food industry not
                           listed above, and prepared animal feed.

The grouping is by HS heading (four digits); it is the authors' classification, built on the FAO crop groups. FAO does
not itself classify crops as mechanized or labor-intensive.

Outputs (output/wp_<window>/agro/): Tables/tab_agp_croptype.tex, Graphs/fig_agp_croptype.pdf

    WP_YEARS=2012-2018 WP_SCOPES=agro python wp_agro_croptype.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_common as W  # noqa: E402

SCOPE = "agro"
G, T, _ = W.outdirs(SCOPE)
ORDER = ["Field crops", "Horticultural and plantation crops", "Livestock and fisheries", "Other processed food and beverages"]

# 2026-11-03, after the product-by-product comparison with the Census of Agriculture farm types
# (wp_agro_classification.py): roots and tubers (FAO group 5, heading 0714) join potatoes (0701) in horticultural
# crops, as in the census (vegetable farming), except cassava (071410), which the census puts with grains; the permanent oilseed crops of FAO group 4.2 (coconut, oil palm,
# olive) and their oils are plantation crops (headings 1203, 1509, 1510, 1511, 1513, code 120710); vegetable,
# flower and other seeds for sowing (120930, 120991, 120999) and carob and fruit stones (121299) follow their crop.
PLANT4 = {"1203", "1509", "1510", "1511", "1513"}
FIELD = (({"10", "11"} | {f"12{k:02d}" for k in range(1, 10)} | {"1212", "1213", "1214", "0713"}
          | {f"15{k:02d}" for k in range(7, 19)} | {"1701", "1702", "1703"} | {f"23{k:02d}" for k in range(2, 9)}) - PLANT4)
HORTI = ({"06", "08", "09", "18", "20", "24", "1210", "1211", "2204", "2205", "2206", "1203", "1509", "1510", "1511", "1513"}
         | {f"07{k:02d}" for k in range(1, 15)} - {"0713"})
FIELD6 = {"200811", "071410"}   # cassava stays a field crop (grain farming in the census concordance)
HORTI6 = {"120710", "120930", "120991", "120999", "121292", "121299"}   # 121292: carob has its own code from HS 2012 on
LIVE = {"01", "02", "03", "04", "05", "16", "2301"} | {f"15{k:02d}" for k in range(1, 7)}


def crop_type(hs6: pd.Series) -> pd.Series:
    h2, h4 = hs6.str[:2], hs6.str[:4]

    def pick(s: set) -> pd.Series:
        return h4.isin(s) | h2.isin(s)
    out = pd.Series("Other processed food and beverages", index=hs6.index)
    out[pick(LIVE)] = "Livestock and fisheries"
    out[pick(HORTI)] = "Horticultural and plantation crops"
    out[pick(FIELD)] = "Field crops"
    out[hs6.isin(FIELD6)] = "Field crops"   # 2026-11-03: prepared groundnuts (HS 20) are an oilseed, a field crop
    out[hs6.isin(HORTI6)] = "Horticultural and plantation crops"
    return out


def main() -> None:
    d = W.scope_filter(W.mne_flags(W.build_cube()), SCOPE)
    d = d[d["value"] > 0].copy()
    d["ct"] = crop_type(d["hs07_6d"])
    g = d.groupby("ct").agg(v=("value", "sum"), vyr=("value_yr", "sum"), e=("val_ext", "sum"), m=("val_dom", "sum"),
                            n=("hs07_6d", "nunique")).reindex(ORDER)
    g["sh"] = 100 * g["v"] / g["v"].sum(); g["ext"] = 100 * g["e"] / g["v"]; g["dom"] = 100 * g["m"] / g["v"]
    tot = g.sum()
    L = [r"\begin{tabular}{lrrrrrr}", r"\toprule",
         r"Type of production & Products & Exports (US\$bn/yr) & Share of exports (\%) & Foreign MNEs (\%) & Domestic MNEs (\%) & MNE share (\%) \\",
         r"\midrule"]
    for i, r in g.iterrows():
        L.append(f"{i} & {int(r['n']):,} & {r['vyr'] / 1e9:,.1f} & {r['sh']:.1f} & {r['ext']:.1f} & {r['dom']:.1f} & {r['ext'] + r['dom']:.1f} \\\\")
    L += [r"\midrule", f"All agricultural products & {d['hs07_6d'].nunique():,} & {tot['vyr'] / 1e9:,.1f} & 100.0 & "
          f"{100 * tot['e'] / tot['v']:.1f} & {100 * tot['m'] / tot['v']:.1f} & {100 * (tot['e'] + tot['m']) / tot['v']:.1f} \\\\",
          r"\bottomrule", r"\end{tabular}"]
    W.write_tex(L, T / "tab_agp_croptype.tex")
    fig, ax = plt.subplots(figsize=(8, 3.6))
    y = np.arange(len(g))[::-1]
    ax.barh(y, g["ext"] / 100, color=W.C_MNE_EXT, edgecolor="white", label="Foreign MNEs")
    ax.barh(y, g["dom"] / 100, left=g["ext"] / 100, color=W.C_MNE_DOM, edgecolor="white", label="Domestic MNEs")
    for yi, (_, r) in zip(y, g.iterrows()):
        ax.text((r["ext"] + r["dom"]) / 100 + 0.006, yi, f"{(r['ext'] + r['dom']) / 100:.2f}", va="center", fontsize=8)
    ax.set_yticks(y); ax.set_yticklabels([f"{i} ({r['sh']:.0f}%)" for i, r in g.iterrows()], fontsize=9)
    ax.set_xlim(0, 0.85); ax.set_xlabel("Share of export value")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    W.savefig(fig, "fig_agp_croptype", G)
    print(g[["n", "sh", "ext", "dom"]].round(1).to_string())


if __name__ == "__main__":
    main()
