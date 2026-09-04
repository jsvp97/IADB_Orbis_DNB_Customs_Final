"""
Deep analysis + figure battery for the TWO new stylized facts, written to the
Overleaf doc `New_SFs_Analysis/new_sfs_analysis.tex`.

  SF-A  Network size: foreign-MNE exports are dominated by parents with large
        global affiliate networks.
  SF-B  Cross-country shared parents: the same multinational groups dominate
        exports across LAC countries (top-K overlap).

Inputs (built by nsf_prep.py / build_network_size.py):
  nsf_parent.parquet          name-parent: export_value, n_origins, iso3_parent,
                              total_affiliates, n_countries, n_sectors, has_network
  nsf_id_country.parquet      guo25-id x country -> val (robust cross-country key)
  nsf_parent_country.parquet  name x country -> val (name-based robustness)

All figures -> 2_Output/Graphs/NewSFs + Overleaf mirror. Value-weighted.
"""
from __future__ import annotations
import sys, itertools
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (INT, GRAPHS, TABLES, REGS, OVERLEAF, C_MNE_EXT, C_MNE_DOM,
                     ensure_dir, save_figure)  # noqa: E402
import pyfixest as pf  # noqa: E402

G   = GRAPHS / "NewSFs"
T   = TABLES / "NewSFs"
R   = REGS / "NewSFs"
OLR_ROOT = OVERLEAF / "New_SFs_Analysis"
OLG = OLR_ROOT / "Graphs"
OLT = OLR_ROOT / "Tables"
OLR = OLR_ROOT / "Regressions"
for d in (G, T, R, OLG, OLT, OLR):
    ensure_dir(d)

NAVY, GRAY, GOLD = C_MNE_EXT, "#8c8c8c", "#c8a24a"

def wtable(lines, name):
    txt = "\n".join(lines) + "\n"
    (T / f"{name}.tex").write_text(txt, encoding="utf-8")
    (OLT / f"{name}.tex").write_text(txt, encoding="utf-8")

def wreg(lines, name):
    txt = "\n".join(lines) + "\n"
    (R / f"{name}.tex").write_text(txt, encoding="utf-8")
    (OLR / f"{name}.tex").write_text(txt, encoding="utf-8")

# =====================================================================
par = pd.read_parquet(INT / "nsf_parent.parquet")
idc = pd.read_parquet(INT / "nsf_id_country.parquet")
pc  = pd.read_parquet(INT / "nsf_parent_country.parquet")
COUNTRIES = sorted(idc["country_orig"].unique())
print(f"parents={len(par):,} | id-country rows={len(idc):,} | countries={COUNTRIES}")

# ---------------------------------------------------------------------
# SF-A helpers
# ---------------------------------------------------------------------
pa = par[par["has_network"]].copy()
pa["export_value"] = pa["export_value"].astype(float)
TOTV = pa["export_value"].sum()

def share_table_by_bin(df, valcol, bincol, edges, labels):
    b = pd.cut(df[bincol], bins=edges, labels=labels, right=True, include_lowest=True)
    g = df.groupby(b, observed=True).agg(npar=(valcol, "size"), val=(valcol, "sum"))
    g["share_val"] = g["val"] / g["val"].sum()
    g["share_par"] = g["npar"] / g["npar"].sum()
    return g

AFF_EDGES = [0, 1, 10, 100, np.inf]
AFF_LAB = ["1", "2--10", "11--100", "$>$100"]


def figA1():
    g = share_table_by_bin(pa, "export_value", "total_affiliates", AFF_EDGES, AFF_LAB)
    fig, ax = plt.subplots(figsize=(7, 4.2))
    x = np.arange(len(g))
    ax.bar(x - 0.2, g["share_val"], 0.4, color=NAVY, label="share of export value")
    ax.bar(x + 0.2, g["share_par"], 0.4, color=GRAY, label="share of parents")
    ax.set_xticks(x); ax.set_xticklabels(g.index)
    ax.set_xlabel("Parent global affiliate count"); ax.set_ylabel("Share")
    ax.legend(frameon=False)
    for xi, v in zip(x - 0.2, g["share_val"]):
        ax.text(xi, v + 0.01, f"{v:.0%}", ha="center", va="bottom", fontsize=8)
    save_figure(fig, "figA1_value_by_netbin", G, OLG)
    return g


def figA2_lorenz():
    d = pa.sort_values("total_affiliates", ascending=False).reset_index(drop=True)
    cum_par = (np.arange(1, len(d) + 1)) / len(d)
    cum_val = d["export_value"].cumsum() / d["export_value"].sum()
    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.plot(cum_par, cum_val, color=NAVY, lw=2)
    ax.plot([0, 1], [0, 1], color=GRAY, ls="--", lw=1)
    ax.set_xlabel("Cumulative share of parents (ranked by network size, largest first)")
    ax.set_ylabel("Cumulative share of foreign-MNE export value")
    for q in (0.01, 0.05, 0.10):
        yv = cum_val.iloc[int(q * len(d)) - 1]
        ax.annotate(f"top {q:.0%}: {yv:.0%}", (q, yv), textcoords="offset points",
                    xytext=(8, -4), fontsize=8, color=NAVY)
    save_figure(fig, "figA2_lorenz_network", G, OLG)


def figA3_binscatter():
    d = pa[(pa["total_affiliates"] >= 1) & (pa["export_value"] > 0)].copy()
    d["lx"] = np.log(d["total_affiliates"].astype(float))
    d["ly"] = np.log(d["export_value"])
    q = pd.qcut(d["lx"].rank(method="first"), 20)
    b = d.groupby(q, observed=True).agg(lx=("lx", "mean"), ly=("ly", "mean"))
    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.scatter(b["lx"], b["ly"], color=NAVY, s=28)
    m, c = np.polyfit(d["lx"], d["ly"], 1)
    xs = np.array([d["lx"].min(), d["lx"].max()])
    ax.plot(xs, m * xs + c, color=GOLD, lw=2, label=f"slope = {m:.2f}")
    ax.set_xlabel("ln(parent global affiliates)"); ax.set_ylabel("ln(parent export value)")
    ax.legend(frameon=False)
    save_figure(fig, "figA3_binscatter", G, OLG)


def figA4_altmeasures():
    meas = [("total_affiliates", "affiliates"), ("n_countries", "countries"),
            ("n_sectors", "sectors")]
    shares = []
    for col, _ in meas:
        d = pa[pa[col].notna()].sort_values(col, ascending=False)
        top10 = d.iloc[:max(1, len(d) // 10)]
        shares.append(top10["export_value"].sum() / d["export_value"].sum())
    fig, ax = plt.subplots(figsize=(6, 4))
    x = np.arange(len(meas))
    ax.bar(x, shares, color=NAVY, width=0.55)
    ax.set_xticks(x); ax.set_xticklabels([m[1] for m in meas])
    ax.set_ylabel("Export-value share of top-10% parents")
    ax.set_xlabel("Parent ranked by network breadth measure")
    for xi, v in zip(x, shares):
        ax.text(xi, v + 0.01, f"{v:.0%}", ha="center", fontsize=9)
    save_figure(fig, "figA4_altmeasures", G, OLG)


def figA6_filter():
    variants = {"all parents": pa,
                "drop $n_{countries}=0$": pa[pa["n_countries"] > 0]}
    fig, ax = plt.subplots(figsize=(7, 4.2))
    x = np.arange(len(AFF_LAB)); w = 0.38
    for k, (lab, d) in enumerate(variants.items()):
        g = share_table_by_bin(d, "export_value", "total_affiliates", AFF_EDGES, AFF_LAB)
        g = g.reindex(AFF_LAB)
        ax.bar(x + (k - 0.5) * w, g["share_val"].fillna(0), w,
               color=[NAVY, GOLD][k], label=lab)
    ax.set_xticks(x); ax.set_xticklabels(AFF_LAB)
    ax.set_xlabel("Parent global affiliate count"); ax.set_ylabel("Share of export value")
    ax.legend(frameon=False)
    save_figure(fig, "figA6_filter_robust", G, OLG)


def tabA_thresholds():
    lines = [r"\begin{tabular}{lrr}",
             r"\toprule",
             r"Parents with a network of\dots & \% of parents & \% of export value \\",
             r"\midrule"]
    for thr in [10, 50, 100]:
        m = pa["total_affiliates"] > thr
        lines.append(rf"more than {thr:,} affiliates & {m.mean()*100:.1f} & "
                     rf"{pa.loc[m,'export_value'].sum()/TOTV*100:.1f} \\")
    lines += [r"\bottomrule",
              r"\multicolumn{3}{p{0.72\textwidth}}{\footnotesize \emph{Notes.} "
              r"Foreign-MNE parents with a matched network record ($N=12{,}365$). "
              r"Columns are cumulative shares above each affiliate threshold; "
              r"value-weighted foreign-MNE exports, pooled 2006--2022.} \\",
              r"\end{tabular}"]
    wtable(lines, "tabA_thresholds")


def regA_network():
    d = pa[(pa["total_affiliates"] >= 1) & (pa["export_value"] > 0)].copy()
    d["ly"] = np.log(d["export_value"])
    d["l_aff"] = np.log(d["total_affiliates"].astype(float))
    d["l_ctry"] = np.log(d["n_countries"].astype(float) + 1)
    d["l_sect"] = np.log(d["n_sectors"].astype(float) + 1)
    d["hq"] = d["iso3_parent"].astype(str)
    specs = [
        ("l_aff", "ly ~ l_aff", None),
        ("l_aff+FE", "ly ~ l_aff | hq", None),
        ("+breadth+FE", "ly ~ l_aff + l_ctry + l_sect | hq", None),
    ]
    fits = []
    for _, f, _w in specs:
        fits.append(pf.feols(f, data=d, vcov="hetero"))
    rows = ["l_aff", "l_ctry", "l_sect"]
    lab = {"l_aff": r"$\ln$ global affiliates", "l_ctry": r"$\ln$ countries of presence",
           "l_sect": r"$\ln$ sectors of presence"}
    lines = [r"\begin{tabular}{lccc}",
             r"\toprule",
             r"& (1) & (2) & (3) \\",
             r"\cmidrule(lr){2-4}",
             r"\multicolumn{4}{l}{\textit{Dependent variable: $\ln$ parent export value}} \\",
             r"\midrule"]
    for rv in rows:
        cells, secells = [], []
        for fit in fits:
            co, se, pv = fit.coef(), fit.se(), fit.pvalue()
            if rv in co.index:
                st = "***" if pv[rv] < .01 else "**" if pv[rv] < .05 else "*" if pv[rv] < .1 else ""
                cells.append(f"{co[rv]:.3f}{st}"); secells.append(f"({se[rv]:.3f})")
            else:
                cells.append(""); secells.append("")
        lines.append(f"{lab[rv]} & " + " & ".join(cells) + r" \\")
        lines.append(" & " + " & ".join(secells) + r" \\[2pt]")
    lines += [r"\midrule",
              r"HQ-country fixed effects & No & Yes & Yes \\",
              "Observations & " + " & ".join(f"{int(f._N):,}" for f in fits) + r" \\",
              r"\bottomrule",
              r"\multicolumn{4}{p{0.82\textwidth}}{\footnotesize \emph{Notes.} Parent level; "
              r"foreign MNEs with a network record. Robust (HC1) SE in parentheses. "
              r"\sym{*}$\,p<0.1$, \sym{**}$\,p<0.05$, \sym{***}$\,p<0.01$.} \\",
              r"\end{tabular}"]
    wreg(lines, "regA_network")


# ---------------------------------------------------------------------
# SF-B helpers (cross-country overlap)
# ---------------------------------------------------------------------
def topk_sets(df, key, k):
    out = {}
    for c, g in df.groupby("country_orig"):
        out[c] = set(g.sort_values("val", ascending=False)[key].head(k).tolist())
    return out

def country_share_topk(df, key, k):
    res = {}
    for c, g in df.groupby("country_orig"):
        g = g.sort_values("val", ascending=False)
        res[c] = g["val"].head(k).sum() / g["val"].sum()
    return res


def figB1_within():
    fig, ax = plt.subplots(figsize=(8, 4.3))
    ks = [10, 25, 50]; x = np.arange(len(COUNTRIES)); w = 0.26
    for j, k in enumerate(ks):
        sh = country_share_topk(pc, "name_parent_adj", k)
        ax.bar(x + (j - 1) * w, [sh[c] for c in COUNTRIES], w,
               color=[GRAY, GOLD, NAVY][j], label=f"top {k}")
    ax.set_xticks(x); ax.set_xticklabels(COUNTRIES)
    ax.set_ylabel("Share of foreign-MNE exports from top-K groups")
    ax.legend(frameon=False, title="")
    save_figure(fig, "figB1_topk_within", G, OLG)


def _overlap_matrix(df, key, k):
    sets = topk_sets(df, key, k)
    M = np.zeros((len(COUNTRIES), len(COUNTRIES)))
    for i, a in enumerate(COUNTRIES):
        for j, b in enumerate(COUNTRIES):
            M[i, j] = len(sets[a] & sets[b])
    return M


def figB2_heatmap(df, key, tag):
    M = _overlap_matrix(df, key, 50)
    fig, ax = plt.subplots(figsize=(6.2, 5.2))
    im = ax.imshow(np.where(np.eye(len(COUNTRIES), dtype=bool), np.nan, M),
                   cmap="Blues", vmin=0)
    ax.set_xticks(range(len(COUNTRIES))); ax.set_xticklabels(COUNTRIES, rotation=45)
    ax.set_yticks(range(len(COUNTRIES))); ax.set_yticklabels(COUNTRIES)
    for i in range(len(COUNTRIES)):
        for j in range(len(COUNTRIES)):
            if i != j:
                ax.text(j, i, f"{int(M[i,j])}", ha="center", va="center",
                        fontsize=8, color="black")
    ax.set_title("Shared groups in both top-50 (of 50)")
    fig.colorbar(im, ax=ax, shrink=0.8)
    save_figure(fig, f"figB2_overlap_heatmap_{tag}", G, OLG)
    return M


def figB3_overlap_vs_k():
    ks = [10, 20, 30, 50, 75, 100]
    fig, ax = plt.subplots(figsize=(6, 4.3))
    for df, key, lab, col in [(pc, "name_parent_adj", "GUO name (primary)", NAVY),
                              (idc, "ID_Orbis_DNB", "clean id (fragments)", GOLD)]:
        ys = []
        for k in ks:
            M = _overlap_matrix(df, key, k)
            iu = M[np.triu_indices(len(COUNTRIES), 1)]
            ys.append(iu.mean() / k)
        ax.plot(ks, ys, marker="o", color=col, label=lab)
    ax.set_xlabel("K (top-K groups per country)")
    ax.set_ylabel("Avg pairwise overlap (share of K)")
    ax.legend(frameon=False)
    save_figure(fig, "figB3_overlap_vs_k", G, OLG)


def figB4_lac_topk():
    tot = pc.groupby("name_parent_adj")["val"].sum().sort_values(ascending=False)
    for k in (50,):
        topids = set(tot.head(k).index)
        res = {}
        for c, g in pc.groupby("country_orig"):
            res[c] = g[g["name_parent_adj"].isin(topids)]["val"].sum() / g["val"].sum()
        fig, ax = plt.subplots(figsize=(7.5, 4))
        ax.bar(COUNTRIES, [res[c] for c in COUNTRIES], color=NAVY, width=0.6)
        ax.set_ylabel(f"Share of exports from LAC top-{k} groups")
        for i, c in enumerate(COUNTRIES):
            ax.text(i, res[c] + 0.01, f"{res[c]:.0%}", ha="center", fontsize=8)
        save_figure(fig, "figB4_lac_topk_reliance", G, OLG)


def figB5_footprint():
    tot = pc.groupby("name_parent_adj")["val"].sum().sort_values(ascending=False)
    top = set(tot.head(50).index)
    foot = pc[pc["name_parent_adj"].isin(top)].groupby("name_parent_adj")["country_orig"].nunique()
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(foot, bins=range(1, len(COUNTRIES) + 2), color=NAVY, align="left", rwidth=0.85)
    ax.set_xlabel("Number of LAC origins the group exports from")
    ax.set_ylabel("Number of LAC top-50 groups")
    ax.set_xticks(range(1, len(COUNTRIES) + 1))
    save_figure(fig, "figB5_footprint", G, OLG)


def figB6_curves():
    fig, ax = plt.subplots(figsize=(7, 4.6))
    cmap = plt.cm.tab10(np.linspace(0, 1, len(COUNTRIES)))
    for col, c in zip(cmap, COUNTRIES):
        g = pc[pc["country_orig"] == c].sort_values("val", ascending=False)
        cs = g["val"].cumsum() / g["val"].sum()
        rank = np.arange(1, len(cs) + 1)
        ax.plot(rank[:100], cs.values[:100], color=col, lw=1.4, label=c)
    ax.set_xlabel("Number of parent groups (ranked by export value)")
    ax.set_ylabel("Cumulative share of foreign-MNE exports")
    ax.legend(frameon=False, ncol=3, fontsize=8)
    save_figure(fig, "figB6_conc_curves", G, OLG)


def tabB_overlap(M):
    iu = M[np.triu_indices(len(COUNTRIES), 1)]
    lines = [r"\begin{tabular}{lr}",
             r"\toprule",
             r"Cross-country top-50 overlap & Value \\",
             r"\midrule",
             rf"Mean shared groups per country pair & {iu.mean():.1f} \\",
             rf"Median shared & {np.median(iu):.0f} \\",
             rf"Maximum shared (any pair) & {int(iu.max())} \\",
             rf"Pairs with $\geq$10 shared (\%) & {(iu>=10).mean()*100:.0f} \\",
             r"\bottomrule",
             r"\multicolumn{2}{p{0.72\textwidth}}{\footnotesize \emph{Notes.} Overlap of "
             r"each country pair's top-50 foreign-MNE groups (by export value), keyed on "
             r"the combined ORBIS+D\&B global-ultimate name (Sebasti\'an's "
             r"\texttt{name\_parent\_adj}). Of 50 possible.} \\",
             r"\end{tabular}"]
    wtable(lines, "tabB_overlap")


# =====================================================================
def run(name, fn, *a):
    try:
        out = fn(*a)
        print(f"  ok  {name}")
        return out
    except Exception as e:
        import traceback
        print(f"  FAIL {name}: {type(e).__name__}: {e}")
        traceback.print_exc()
        return None

print("\n--- SF-A ---")
run("A1", figA1); run("A2", figA2_lorenz); run("A3", figA3_binscatter)
run("A4", figA4_altmeasures); run("A6", figA6_filter); run("tabA", tabA_thresholds)
run("regA", regA_network)
print("--- SF-B (primary key = combined ORBIS+D&B global-ultimate name) ---")
run("B1", figB1_within)
Mname = run("B2_name", figB2_heatmap, pc, "name_parent_adj", "name")
run("B2_id", figB2_heatmap, idc, "ID_Orbis_DNB", "id")   # robustness: fragmenting id
run("B3", figB3_overlap_vs_k); run("B4", figB4_lac_topk); run("B5", figB5_footprint)
run("B6", figB6_curves)
if Mname is not None:
    run("tabB", tabB_overlap, Mname)
print("\n>>> NSF figures done.")
