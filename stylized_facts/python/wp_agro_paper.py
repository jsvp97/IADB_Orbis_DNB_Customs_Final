"""
wp_agro_paper.py  --  new exhibits for the agriculture working paper (2026-10-01)
================================================================================

The agriculture paper was restructured after comments (Data and Descriptive Statistics; who owns agricultural
exports; multinationals and export performance). This script writes the exhibits that restructuring needs and
that no other wp_* script produces. Everything is agriculture (HS 01--24), nine origins, CONVENTION "sf".

Outputs (output/wp/agro/):
  Tables/tab_agp_sample.tex           coverage by exporting country (products, destinations, exporters,
                                      MNE affiliates, exports per year, agriculture in total exports)
  Tables/tab_agp_summary.tex          the sample in figures, values as annual averages
  Tables/tab_agp_firms.tex            exporter characteristics by type of owner (firm-year means and medians)
  Graphs/fig_agp_trend + table        exports per year by type of owner, 2012--2018 (all nine countries observed)
  Graphs/fig_agp_dest + table         destination regions: share of exports and ownership of each region's imports
  Graphs/fig_agp_trend_dest + table   destination composition per year, 2012--2018
  Graphs/fig_agp_origin_lac9          Figure 1 with a LAC9 bar for the nine countries together
  Graphs/fig_agp_parent_panels + tab  parent countries: Panel A regular countries, Panel B tax havens / conduits

    python wp_agro_paper.py
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
BAL = (2012, 2018)          # the years in which all nine countries are observed
G, T, _ = W.outdirs(SCOPE)
C_LOCAL = "#e8e8e8"
PERIOD = "2006--2022" if W.YEAR_WINDOW is None else f"{W.YEAR_WINDOW[0]}--{W.YEAR_WINDOW[1]}"
COUNTRY = {"ARG": "Argentina", "CHL": "Chile", "COL": "Colombia", "CRI": "Costa Rica", "DOM": "Dominican Republic",
           "PER": "Peru", "PRY": "Paraguay", "SLV": "El Salvador", "URY": "Uruguay"}
DEST_ORDER = ["Latin America and the Caribbean", "United States and Canada", "Europe", "China", "Rest of Asia",
              "Africa", "Other"]


def dest_region(code: pd.Series) -> pd.Series:
    r = code.map(W.classify_region)
    r = r.replace({"Latin America": "Latin America and the Caribbean", "North America": "United States and Canada",
                   "Asia": "Rest of Asia", "Oceania": "Other", "Rest of World": "Other"})
    return r.where(~code.isin({"CHN", "HKG", "MAC"}), "China")


def note_line(n: int, text: str) -> str:
    return rf"\multicolumn{{{n}}}{{p{{0.95\textwidth}}}}{{\footnotesize {text}}} \\"


# ---------------------------------------------------------------------
# Firm-level frame (agriculture) and the all-goods totals by origin
# ---------------------------------------------------------------------
def load():
    df = W.load_fdpy()
    df = df[~df["country_orig"].isin(W.excluded_origins()) & (df["value_fob"] > 0)].copy()
    df["hs2"] = W.hs2_of(df["hs07_6d"])
    tot_all = df.groupby("country_orig")["value_fob"].sum()
    a = W.scope_filter(df, SCOPE).copy()
    a["otype"] = W.owner_type(a).replace({"ext_unknown": "ext"})      # sf convention: unknown parent = foreign
    a["fid"] = a["country_orig"] + "|" + a["Tax_ID"]
    a["matched"] = W.matched_flag(a).astype(bool)
    return a, tot_all


def sample_tables(a: pd.DataFrame, tot_all: pd.Series) -> None:
    rows = []
    ny = a.groupby("country_orig")["year"].nunique()
    for o, d in a.groupby("country_orig"):
        rows.append(dict(o=o, exp=d["fid"].nunique(),
                         mne=d.loc[d["matched"], "fid"].nunique(), prod=d["hs07_6d"].nunique(),
                         dest=d["country_dest"].nunique(), val=d["value_fob"].sum() / ny[o] / 1e9,
                         agsh=100 * d["value_fob"].sum() / tot_all[o],
                         mnesh=100 * d.loc[d["matched"], "value_fob"].sum() / d["value_fob"].sum()))
    t = pd.DataFrame(rows).sort_values("val", ascending=False)
    L = [r"\begin{tabular}{lrrrrrrr}", r"\toprule",
         r"Country & Exporters & MNE affiliates & Products & Destinations & Exports (US\$bn/yr) & "
         r"Agriculture in total exports (\%) & MNE share (\%) \\", r"\midrule"]
    for r in t.itertuples():
        L.append(f"{COUNTRY[r.o]} & {r.exp:,} & {r.mne:,} & {r.prod:,} & {r.dest:,} & {r.val:,.1f} & "
                 f"{r.agsh:.1f} & {r.mnesh:.1f} \\\\")
    all_ag = (a.groupby("country_orig")["value_fob"].sum()).sum()
    L += [r"\midrule",
          f"LAC9 & {a['fid'].nunique():,} & {a.loc[a['matched'], 'fid'].nunique():,} & "
          f"{a['hs07_6d'].nunique():,} & {a['country_dest'].nunique():,} & {t['val'].sum():,.1f} & "
          f"{100 * all_ag / tot_all.sum():.1f} & {100 * a.loc[a['matched'], 'value_fob'].sum() / all_ag:.1f} \\\\",
          r"\bottomrule", r"\end{tabular}"]
    W.write_tex(L, T / "tab_agp_sample.tex")

    # the sample in figures, values per year
    nyr = a["country_orig"].map(ny).astype(float)
    a["v_yr"] = a["value_fob"] / nyr
    v = a["v_yr"].sum()
    ext, dom = a["otype"] == "ext", a["otype"] == "dom"
    known = a.loc[ext & (a["iso3_parent"] != ""), "value_fob"].sum() / a.loc[ext, "value_fob"].sum()
    fy = a.groupby(["country_orig", "year"])["fid"].nunique().groupby("country_orig").mean().sum()
    L = [r"\begin{tabular}{lr}", r"\toprule", r"Statistic & Value \\", r"\midrule",
         r"Exporting countries & 9 \\",
         f"Years & {PERIOD} \\\\",
         f"Products & {a['hs07_6d'].nunique():,} \\\\",
         f"Destination markets & {a['country_dest'].nunique():,} \\\\",
         f"Exporters & {a['fid'].nunique():,} \\\\",
         f"\\quad of which multinational affiliates & {a.loc[a['matched'], 'fid'].nunique():,} \\\\",
         f"Exporters per year & {fy:,.0f} \\\\",
         f"Parent countries of foreign multinationals & {a.loc[ext & (a['iso3_parent'] != ''), 'iso3_parent'].nunique():,} \\\\",
         f"Multinational groups & {a.loc[a['matched'], 'parent_key'].replace('', pd.NA).nunique():,} \\\\",
         r"\midrule",
         f"Exports per year (US\\$bn) & {v / 1e9:,.1f} \\\\",
         f"\\quad foreign multinationals (\\%) & {100 * a.loc[ext, 'value_fob'].sum() / a['value_fob'].sum():.1f} \\\\",
         f"\\quad domestic multinationals (\\%) & {100 * a.loc[dom, 'value_fob'].sum() / a['value_fob'].sum():.1f} \\\\",
         f"\\quad local firms (\\%) & {100 * a.loc[a['otype'] == 'local', 'value_fob'].sum() / a['value_fob'].sum():.1f} \\\\",
         f"Foreign-MNE exports with a recorded parent country (\\%) & {100 * known:.1f} \\\\",
         r"\bottomrule", r"\end{tabular}"]
    W.write_tex(L, T / "tab_agp_summary.tex")
    print(t.to_string(index=False))


def firm_table(a: pd.DataFrame) -> None:
    fy = a.groupby(["fid", "year"]).agg(v=("value_fob", "sum"), npr=("hs07_6d", "nunique"),
                                        nde=("country_dest", "nunique")).reset_index()
    # owner type of the firm: the type of its largest flow (constant within firm in practice)
    ot = a.sort_values("value_fob").groupby("fid")["otype"].last()
    fy["otype"] = fy["fid"].map(ot)
    lab = {"ext": "Foreign MNEs", "dom": "Domestic MNEs", "local": "Local firms"}
    tot_v = a["value_fob"].sum()
    cols = []
    for k in ("ext", "dom", "local", "all"):
        f = fy if k == "all" else fy[fy["otype"] == k]
        n = len(ot) if k == "all" else int((ot == k).sum())
        sv = 100.0 if k == "all" else 100 * a.loc[a["otype"] == k, "value_fob"].sum() / tot_v
        cols.append(dict(name="All exporters" if k == "all" else lab[k], n=n, nsh=100 * n / len(ot), vsh=sv,
                         vmean=f["v"].mean() / 1e6, vmed=f["v"].median() / 1e6,
                         pmean=f["npr"].mean(), pmed=f["npr"].median(), dmean=f["nde"].mean(), dmed=f["nde"].median()))
    c = pd.DataFrame(cols).set_index("name")
    rows = [("Number of exporters", "n", "{:,.0f}"), ("Share of exporters (\\%)", "nsh", "{:.1f}"),
            ("Share of export value (\\%)", "vsh", "{:.1f}"),
            ("Exports per firm and year, mean (US\\$ million)", "vmean", "{:.2f}"),
            ("Exports per firm and year, median (US\\$ million)", "vmed", "{:.3f}"),
            ("Products per firm and year, mean", "pmean", "{:.1f}"), ("Products per firm and year, median", "pmed", "{:.0f}"),
            ("Destinations per firm and year, mean", "dmean", "{:.1f}"),
            ("Destinations per firm and year, median", "dmed", "{:.0f}")]
    L = [r"\begin{tabular}{lrrrr}", r"\toprule", " & " + " & ".join(c.index) + r" \\", r"\midrule"]
    for txt, col, fmt in rows:
        L.append(txt + " & " + " & ".join(fmt.format(v) for v in c[col]) + r" \\")
    L += [r"\bottomrule", r"\end{tabular}"]
    W.write_tex(L, T / "tab_agp_firms.tex")
    print(c.round(2).T.to_string())


# ---------------------------------------------------------------------
# Evolution 2012-2018 and destinations
# ---------------------------------------------------------------------
def trend(a: pd.DataFrame) -> None:
    b = a[a["year"].between(*BAL)]
    p = b.pivot_table(index="year", columns="otype", values="value_fob", aggfunc="sum").fillna(0) / 1e9
    p = p[["ext", "dom", "local"]]
    p.index = p.index.astype(int)
    sh = 100 * (p["ext"] + p["dom"]) / p.sum(axis=1)
    fig, ax = plt.subplots(figsize=(8, 4.6))
    x = np.arange(len(p))
    bottom = np.zeros(len(p))
    for col, c, lab in (("ext", W.C_MNE_EXT, "Foreign MNEs"), ("dom", W.C_MNE_DOM, "Domestic MNEs"),
                        ("local", C_LOCAL, "Local firms")):
        ax.bar(x, p[col], bottom=bottom, color=c, edgecolor="white", linewidth=0.6, label=lab, width=0.7)
        bottom += p[col].values
    ax.set_xticks(x); ax.set_xticklabels(p.index)
    ax.set_ylabel("Agricultural exports (US$ billion)")
    ax.set_ylim(0, bottom.max() * 1.25)
    ax2 = ax.twinx()
    ax2.plot(x, sh, color="black", marker="o", ms=4, lw=1.2, label="MNE share (right axis)")
    ax2.set_ylim(0, 100); ax2.set_ylabel("MNE share of exports (%)")
    for s in ("top",):
        ax.spines[s].set_visible(False); ax2.spines[s].set_visible(False)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, frameon=False, fontsize=9, loc="upper left", ncol=2)
    W.savefig(fig, "fig_agp_trend", G)
    L = [r"\begin{tabular}{lrrrrr}", r"\toprule",
         r"Year & Exports (US\$bn) & Foreign MNEs (\%) & Domestic MNEs (\%) & Local firms (\%) & MNE share (\%) \\",
         r"\midrule"]
    for y, r in p.iterrows():
        t = r.sum()
        L.append(f"{y} & {t:,.1f} & {100 * r['ext'] / t:.1f} & {100 * r['dom'] / t:.1f} & {100 * r['local'] / t:.1f} & "
                 f"{100 * (r['ext'] + r['dom']) / t:.1f} \\\\")
    L += [r"\bottomrule", r"\end{tabular}"]
    W.write_tex(L, T / "tab_agp_trend.tex")
    print(pd.concat([p.sum(axis=1).rename("total"), sh.rename("mne_sh")], axis=1).round(1).to_string())

    # destination composition per year
    b = b.assign(reg=dest_region(b["country_dest"]))
    q = b.pivot_table(index="year", columns="reg", values="value_fob", aggfunc="sum").fillna(0)
    q = 100 * q.div(q.sum(axis=1), axis=0)
    q = q[[c for c in DEST_ORDER if c in q.columns]]
    q.index = q.index.astype(int)
    shades = [W.BLUE_SHADES[i] for i in (0, 2, 4, 6, 8)] + ["#bdbdbd", C_LOCAL]
    fig, ax = plt.subplots(figsize=(8, 4.8))
    bottom = np.zeros(len(q))
    for col, c in zip(q.columns, shades):
        ax.bar(np.arange(len(q)), q[col], bottom=bottom, color=c, edgecolor="white", linewidth=0.6, label=col, width=0.7)
        bottom += q[col].values
    ax.set_xticks(np.arange(len(q))); ax.set_xticklabels(q.index)
    ax.set_ylabel("Share of agricultural exports (%)"); ax.set_ylim(0, 100)
    ax.legend(frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=4)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    W.savefig(fig, "fig_agp_trend_dest", G)
    L = [r"\begin{tabular}{l" + "r" * len(q.columns) + "}", r"\toprule",
         "Year & " + " & ".join(q.columns) + r" \\", r"\midrule"]
    for y, r in q.iterrows():
        L.append(f"{y} & " + " & ".join(f"{v:.1f}" for v in r) + r" \\")
    L += [r"\bottomrule", r"\end{tabular}"]
    W.write_tex(L, T / "tab_agp_trend_dest.tex")
    print(q.round(1).to_string())


def destinations(a: pd.DataFrame) -> None:
    ny = a.groupby("country_orig")["year"].nunique()
    a = a.assign(reg=dest_region(a["country_dest"]), v_yr=a["value_fob"] / a["country_orig"].map(ny))
    g = a.pivot_table(index="reg", columns="otype", values="value_fob", aggfunc="sum").fillna(0)
    tot = g.sum(axis=1)
    out = pd.DataFrame({"share": 100 * tot / tot.sum(), "ext": 100 * g["ext"] / tot, "dom": 100 * g["dom"] / tot,
                        "local": 100 * g["local"] / tot, "bn": a.groupby("reg")["v_yr"].sum() / 1e9})
    out = out.reindex([c for c in DEST_ORDER if c in out.index])
    # foreign-MNE share by destination for the three largest parent countries is in the appendix tables; here ownership only
    fig, ax = plt.subplots(figsize=(8, 4.4))
    y = np.arange(len(out))[::-1]
    ax.barh(y, out["ext"] / 100, color=W.C_MNE_EXT, edgecolor="white", linewidth=0.6, label="Foreign MNEs")
    ax.barh(y, out["dom"] / 100, left=out["ext"] / 100, color=W.C_MNE_DOM, edgecolor="white", linewidth=0.6,
            label="Domestic MNEs")
    for yi, r in zip(y, out.itertuples()):
        ax.text((r.ext + r.dom) / 100 + 0.006, yi, f"{(r.ext + r.dom) / 100:.2f}", va="center", fontsize=8,
                fontweight="bold")
    ax.set_yticks(y); ax.set_yticklabels([f"{i} ({r.share:.0f}%)" for i, r in out.iterrows()], fontsize=9)
    ax.set_xlabel("Share of export value"); ax.set_xlim(0, 0.85)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    W.savefig(fig, "fig_agp_dest", G)
    L = [r"\begin{tabular}{lrrrrr}", r"\toprule",
         r"Destination & Share of exports (\%) & Foreign MNEs (\%) & Domestic MNEs (\%) & Local firms (\%) & Exports (US\$bn/yr) \\",
         r"\midrule"]
    for i, r in out.iterrows():
        L.append(f"{i} & {r['share']:.1f} & {r['ext']:.1f} & {r['dom']:.1f} & {r['local']:.1f} & {r['bn']:,.1f} \\\\")
    L += [r"\midrule", f"All destinations & 100.0 & {100 * g['ext'].sum() / tot.sum():.1f} & {100 * g['dom'].sum() / tot.sum():.1f} & "
          f"{100 * g['local'].sum() / tot.sum():.1f} & {out['bn'].sum():,.1f} \\\\", r"\bottomrule", r"\end{tabular}"]
    W.write_tex(L, T / "tab_agp_dest.tex")
    print(out.round(1).to_string())


# ---------------------------------------------------------------------
# Figure 1 with LAC9, and the parent countries split into regular countries and tax havens
# ---------------------------------------------------------------------
def origin_lac9(d: pd.DataFrame) -> None:
    cross = d.groupby("country_orig").agg(v=("value", "sum"), e=("val_ext", "sum"), m=("val_dom", "sum"))
    cross.loc["LAC9"] = cross.sum()
    cross["sh_ext"] = cross["e"] / cross["v"]; cross["sh_dom"] = cross["m"] / cross["v"]
    cross["sh_total"] = cross["sh_ext"] + cross["sh_dom"]
    sub = cross.drop("LAC9").sort_values("sh_total", ascending=True)
    sub = pd.concat([cross.loc[["LAC9"]], sub])          # LAC9 at the bottom
    y = np.arange(len(sub)).astype(float); y[1:] += 0.6   # a gap above LAC9
    fig, ax = plt.subplots(figsize=(8, 5.4))
    ax.barh(y, sub["sh_ext"], color=W.C_MNE_EXT, edgecolor="white", linewidth=0.6, label="Foreign MNEs")
    ax.barh(y, sub["sh_dom"], left=sub["sh_ext"], color=W.C_MNE_DOM, edgecolor="white", linewidth=0.6, label="Domestic MNEs")
    for yi, r in zip(y, sub.itertuples()):
        if r.sh_ext > 0.05:
            ax.text(r.sh_ext / 2, yi, f"{r.sh_ext:.2f}", va="center", ha="center", color="white", fontsize=8)
        if r.sh_dom > 0.04:
            ax.text(r.sh_ext + r.sh_dom / 2, yi, f"{r.sh_dom:.2f}", va="center", ha="center", color="black", fontsize=8)
        ax.text(r.sh_total + 0.006, yi, f"{r.sh_total:.2f}", va="center", ha="left", fontsize=8, fontweight="bold")
    ax.axhline((y[0] + y[1]) / 2, color="#9e9e9e", lw=0.6, ls="--")
    ax.set_yticks(y); ax.set_yticklabels(sub.index)
    ax.get_yticklabels()[0].set_fontweight("bold")
    ax.set_xlabel("Share of export value"); ax.set_xlim(0, 0.85); ax.set_xticks(np.arange(0, 0.851, 0.1))
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    W.savefig(fig, "fig_agp_origin_lac9", G)
    print("   LAC9: foreign %.3f domestic %.3f total %.3f" % tuple(cross.loc["LAC9", ["sh_ext", "sh_dom", "sh_total"]]))


def parent_panels(d: pd.DataFrame, k: int = 10) -> None:
    ext = d[d["owner_type"] == "ext"].copy()
    tot = ext["value"].sum()
    is_haven = ext["iso3_parent"].isin(W.HAVEN_STANDALONE) | ext["iso3_parent"].isin(W.HAVEN_SOVEREIGN)
    a = ext[~is_haven].groupby("iso3_parent")["value"].sum().div(tot).mul(100).sort_values(ascending=False)
    b = ext[is_haven].groupby("iso3_parent")["value"].sum().div(tot).mul(100).sort_values(ascending=False)
    ta, tb = a.head(k), b.head(k)
    fig, axes = plt.subplots(2, 1, figsize=(8, 8.2))
    xmax = max(ta.max(), tb.max()) * 1.15
    for ax, s, title, rest in ((axes[0], ta, "Panel A. Parent countries other than tax havens", a.iloc[k:].sum()),
                               (axes[1], tb, "Panel B. Tax havens and conduit jurisdictions", b.iloc[k:].sum())):
        yy = np.arange(len(s))[::-1]
        ax.barh(yy, s.values, color=W.C_MNE_EXT, height=0.7)
        for yi, v in zip(yy, s.values):
            ax.text(v + xmax * 0.01, yi, f"{v:.1f}%", va="center", fontsize=9)
        ax.set_yticks(yy); ax.set_yticklabels(s.index)
        ax.set_xlim(0, xmax); ax.set_title(title, fontsize=11)
        ax.set_xlabel("Share of foreign-MNE agricultural exports (%)")
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    fig.tight_layout(h_pad=2.0)
    W.savefig(fig, "fig_agp_parent_panels", G)
    L = [r"\begin{tabular}{lrlr}", r"\toprule",
         r"\multicolumn{2}{c}{Panel A. Other parent countries} & \multicolumn{2}{c}{Panel B. Tax havens and conduits} \\",
         r"\cmidrule(lr){1-2}\cmidrule(lr){3-4}", r"Parent country & Share (\%) & Jurisdiction & Share (\%) \\", r"\midrule"]
    for i in range(k):
        la = f"{ta.index[i]} & {ta.iloc[i]:.1f}" if i < len(ta) else " & "
        lb = f"{tb.index[i]} & {tb.iloc[i]:.1f}" if i < len(tb) else " & "
        L.append(f"{la} & {lb} \\\\")
    L += [f"Other & {a.iloc[k:].sum():.1f} & Other & {b.iloc[k:].sum():.1f} \\\\", r"\midrule",
          f"Total & {a.sum():.1f} & Total & {b.sum():.1f} \\\\", r"\bottomrule", r"\end{tabular}"]
    W.write_tex(L, T / "tab_agp_parent_panels.tex")
    print("   panel A: " + ", ".join(f"{i} {v:.1f}" for i, v in ta.items()) + f" | total {a.sum():.1f}")
    print("   panel B: " + ", ".join(f"{i} {v:.1f}" for i, v in tb.items()) + f" | total {b.sum():.1f}")


def main():
    a, tot_all = load()
    print(f"agro rows {len(a):,}, value {a['value_fob'].sum() / 1e9:,.0f} bn pooled")
    sample_tables(a, tot_all)
    firm_table(a)
    trend(a)
    destinations(a)
    d = W.scope_filter(W.mne_flags(W.build_cube()), SCOPE)
    d = d[d["value"] > 0]
    origin_lac9(d)
    parent_panels(d)
    print(">>> wp_agro_paper done ->", G.parent)


if __name__ == "__main__":
    main()
