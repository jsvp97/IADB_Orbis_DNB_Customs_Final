"""
wp_paper_sample.py  --  the data section's sample table for the working paper
=============================================================================

One table describing the working sample the way a reader of the paper needs it: for each
origin, the years observed, the number of exporters and how many of them are matched to
Orbis / Dun & Bradstreet, the number of HS6 lines and destinations reached, the number of
firm x destination x HS6 x year records, and the annual-average export value.

Outputs (output/wp/all/):
  Tables/tab_paper_sample.tex          the coverage table of the data section
  Tables/tab_paper_sample_counts.tex   the same numbers in a one-column "sample in figures" list

Convention: wp_common.CONVENTION (default "sf" -- matched = _merge_DNB_Orbis == 3, domestic
MNE = parent in the exporting country, foreign MNE = matched - domestic, Ecuador excluded).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_common as W  # noqa: E402

NOTE = (
    "One record = firm $\\times$ destination $\\times$ HS6 product $\\times$ year. Exporters are counted as "
    "distinct tax identifiers within an origin; matched exporters are those found in Orbis or Dun \\& "
    "Bradstreet after the tax-identifier match, the fuzzy name match and the manual review of the largest "
    "exporters. Value is the annual average: the origin's pooled export value divided by the number of years "
    "it is observed. Ecuador is in the raw data but is excluded throughout."
)


def build(scope: str = "all") -> pd.DataFrame:
    df = W.load_fdpy()
    df = df[~df["country_orig"].isin(W.excluded_origins())].copy()
    if scope != "all":
        df["hs2"] = W.hs2_of(df["hs07_6d"])
        df = W.scope_filter(df, scope).copy()
    df["matched"] = W.matched_flag(df).astype(bool)
    df["fid"] = df["country_orig"].astype(str) + "|" + df["Tax_ID"].astype(str)
    rows = []
    for o, d in df.groupby("country_orig"):
        nyr = d["year"].nunique()
        rows.append({
            "Origin": o,
            "Years": f"{int(d['year'].min())}--{int(d['year'].max())}",
            "Exporters": d["fid"].nunique(),
            "Matched": d.loc[d["matched"], "fid"].nunique(),
            "HS6": d["hs07_6d"].nunique(),
            "Dest.": d["country_dest"].nunique(),
            "Records": len(d),
            "Value": d["value_fob"].sum() / nyr,
        })
    t = pd.DataFrame(rows).sort_values("Value", ascending=False)
    nyr_all = df.groupby("country_orig")["year"].nunique()
    val_all = df.groupby("country_orig")["value_fob"].sum().div(nyr_all).sum()
    t.loc[len(t)] = {
        "Origin": "All nine", "Years": "2006--2022", "Exporters": df["fid"].nunique(),
        "Matched": df.loc[df["matched"], "fid"].nunique(), "HS6": df["hs07_6d"].nunique(),
        "Dest.": df["country_dest"].nunique(), "Records": len(df), "Value": val_all,
    }
    return t, df


def write(t: pd.DataFrame, df: pd.DataFrame, scope: str = "all") -> None:
    _, tdir, _ = W.outdirs(scope)
    L = [r"\begin{tabular}{llrrrrrr}", r"\toprule",
         r"Origin & Years & Exporters & Matched & HS6 lines & Destinations & Records & Value (\$bn/yr) \\",
         r"\midrule"]
    for i, r in t.iterrows():
        if r["Origin"] == "All nine":
            L.append(r"\midrule")
        L.append(f"{r['Origin']} & {r['Years']} & {r['Exporters']:,} & {r['Matched']:,} & {r['HS6']:,} & "
                 f"{r['Dest.']:,} & {r['Records']:,} & {r['Value'] / 1e9:,.1f} \\\\")
    L += [r"\bottomrule",
          r"\multicolumn{8}{p{0.95\textwidth}}{\footnotesize " + NOTE + r"} \\",
          r"\end{tabular}"]
    W.write_tex(L, tdir / "tab_paper_sample.tex")

    # the same sample in a compact list, for the text
    m = df["matched"]
    dom = m & (df["iso3_parent"] == df["country_orig"])
    ext = m & ~dom
    tot = df["value_fob"].sum()
    known = df.loc[ext & (df["iso3_parent"] != ""), "value_fob"].sum()
    L = [r"\begin{tabular}{lr}", r"\toprule", r"The working sample & \\", r"\midrule",
         rf"Exporting countries & 9 \\",
         rf"Years & 2006--2022 \\",
         rf"Records (firm $\times$ destination $\times$ HS6 $\times$ year) & {len(df):,} \\",
         rf"Exporters & {df['fid'].nunique():,} \\",
         rf"\quad matched to Orbis / Dun \& Bradstreet & {df.loc[m, 'fid'].nunique():,} \\",
         rf"HS6 product lines & {df['hs07_6d'].nunique():,} \\",
         rf"Destination markets & {df['country_dest'].nunique():,} \\",
         rf"Parent countries of foreign multinationals & {df.loc[ext & (df['iso3_parent'] != ''), 'iso3_parent'].nunique():,} \\",
         rf"Multinational groups & {df.loc[m, 'parent_key'].replace('', pd.NA).nunique():,} \\",
         r"\midrule",
         rf"Export value, pooled (\$bn) & {tot / 1e9:,.0f} \\",
         rf"\quad foreign multinationals & {df.loc[ext, 'value_fob'].sum() / tot:.1%} \\",
         rf"\quad domestic multinationals & {df.loc[dom, 'value_fob'].sum() / tot:.1%} \\",
         rf"\quad local firms & {df.loc[~m, 'value_fob'].sum() / tot:.1%} \\",
         rf"Foreign-MNE value with a recorded parent country & {known / df.loc[ext, 'value_fob'].sum():.1%} \\",
         r"\bottomrule", r"\end{tabular}"]
    W.write_tex(L, tdir / "tab_paper_sample_counts.tex")
    print("   wrote tab_paper_sample.tex and tab_paper_sample_counts.tex")
    print(t.to_string(index=False))


if __name__ == "__main__":
    for sc in (sys.argv[1:] or ["all", "agro"]):
        print(f"### {sc}")
        t, df = build(sc)
        write(t, df, sc)
