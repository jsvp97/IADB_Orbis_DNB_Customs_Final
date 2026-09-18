"""
wp3_usa_destinations.py  --  revision 6 (2026-09-18): the US-parent story seen from the DESTINATION,
and the cross-sector summaries the internal review asked for
=====================================================================================================

Who carries the exports that reach each destination? Fact 3 and its variants look at the parent's
country from the ORIGIN side (where does each parent ship). This script turns the table around: of
what the nine origins export TO the United States (to China, to the EU-27, ...), how much is moved by
multinationals whose parent sits in that destination, by US-parent MNEs, by other foreign MNEs, by
domestic MNEs and by local firms. It also collects the exhibits that compare the four sectors side by
side (US-parent share by origin x sector; home share by parent x sector; Facts 5 and 6 in one table).

Per scope (output/wp/<scope>/ for all, agro, mining, manufacturing, rest):
  Tables/tab_wp3_to_usa_carriers.tex      exports to the USA by origin: who carries them (%)
  Graphs/fig_wp3_to_usa_carriers          the same as stacked bars
  Tables/tab_wp3_dest_carriers.tex        exports to the main destinations: who carries them (%)
  Graphs/fig_wp3_dest_carriers            the same as stacked bars
  Tables/tab_wp3_us_home_products.tex     top HS6 lines US-parent MNEs ship to the USA, with the US-parent
                                          share of everything LAC exports of the line to the USA
  Graphs/fig_wp3_us_home_products         the last column as bars
  Tables/tab_wp3_to_usa_top_products.tex  top HS6 lines LAC exports to the USA: who carries them (%)

Cross-sector (output/wp/sectors/):
  Tables/tab_wp3_to_usa_carriers_by_sector.tex     who carries exports to the USA, by sector
  Graphs/fig_wp3_to_usa_carriers_total_manuf       two panels: all goods | manufacturing, by origin
  Tables/tab_wp3_us_share_origin_sector.tex        US-parent MNE share of exports, origin x sector
  Graphs/fig_wp3_us_share_origin_sector            grouped bars
  Tables/tab_wp3_home_share_by_parent_sectors.tex  share of each parent's exports shipped home, total and by sector
  Graphs/fig_wp3_home_share_by_parent_sectors      grouped bars (top-10 parents of all goods)
  Tables/tab_wp3_fact5_summary.tex                 Fact 5: ln(# foreign) / ln(# domestic) coefficients, four columns
  Tables/tab_wp3_fact6_summary.tex                 Fact 6: ln distance x foreign / domestic, four columns

The two summary tables are READ from the regression fragments written by wp1e (reg_wp1e_counts.tex,
reg_wp1e_distance_hq.tex) in each scope, so they match the full tables to the last digit; wp1e must
have run first. Conventions: CONVENTION="sf" (nine origins, foreign = matched - domestic); "US-parent
MNE" = matched firm whose recorded ultimate parent is in the USA; "other foreign MNE" includes matched
firms with no recorded parent. Pooled 2006--2022, value-weighted.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_common as W  # noqa: E402

SCOPES = W.SCOPES_ALL
SECTOR_COLS = [("all", "All goods"), ("agro", "Agriculture"), ("mining", "Mining \\& fuels"), ("manufacturing", "Manufacturing")]
SECTOR_OF_COL = {"all": None, "agro": "Agriculture", "mining": "Mining & fuels", "manufacturing": "Manufacturing"}
N_DEST = 8            # destinations in the "who carries" figure (EU-27 pooled as one market)
EU27 = {"AUT", "BEL", "BGR", "HRV", "CYP", "CZE", "DNK", "EST", "FIN", "FRA", "DEU", "GRC", "HUN", "IRL", "ITA", "LVA", "LTU",
        "LUX", "MLT", "NLD", "POL", "PRT", "ROU", "SVK", "SVN", "ESP", "SWE"}   # strict EU-27 (W.EU_CODES is all of Europe)
N_PROD = 15           # HS6 lines in the product tables
MIN_TO_USA_BN = 0.5   # skip the to-USA exhibits in a scope with less than this to the USA (USD bn)
MIN_PARENT_SECTOR_BN = 1.0   # home-share bars drawn hatched when the parent exports less than this in the sector

C_HOME = W.C_MNE_EXT             # MNE whose parent sits in the destination (for the USA: US-parent MNEs)
C_US = W.BLUE_SHADES[4]          # US-parent MNEs when the destination is not the USA
C_OTHER = W.C_OTHER_FOREIGN
C_DOM = W.C_MNE_DOM
C_LOCAL = "#e8e8e8"
SECTOR_COLORS = {"all": W.BLUE_SHADES[0], "agro": W.BLUE_SHADES[3], "mining": W.BLUE_SHADES[6], "manufacturing": W.BLUE_SHADES[9]}
NOTE_BASE = ("Pooled 2006--2022, nine LAC origins (Ecuador excluded), value-weighted. US-parent MNE = matched exporter "
             "whose recorded ultimate parent is in the United States; other foreign MNE = every other matched exporter "
             "with a parent abroad or with no recorded parent; domestic MNE = parent in the exporting country; local = unmatched.")


def _b(s: pd.Series) -> np.ndarray:
    return s.to_numpy(dtype=bool, na_value=False)


def carrier(d: pd.DataFrame, home_parents) -> pd.Series:
    """Five carrier groups for exports to a destination whose parents are `home_parents`."""
    ot = d["owner_type"].astype(str); par = d["iso3_parent"].astype(str)
    is_ext = _b(ot == "ext")
    home = is_ext & _b(par.isin(list(home_parents)))
    us = is_ext & _b(par == "USA") & ~home
    lab = np.select([home, us, _b(ot.isin(["ext", "ext_unknown"])), _b(ot == "dom")],
                    ["home", "us", "other", "dom"], "local")
    return pd.Series(lab, index=d.index)


def shares_table(t: pd.DataFrame, by: str, order=None) -> pd.DataFrame:
    m = t.pivot_table(index=by, columns="grp", values="value", aggfunc="sum", fill_value=0.0)
    for c in ("home", "us", "other", "dom", "local"):
        if c not in m.columns:
            m[c] = 0.0
    m = m[["home", "us", "other", "dom", "local"]]
    tot = m.sum(axis=1)
    sh = 100 * m.div(tot, axis=0); sh["total_bn"] = tot / 1e9
    if order is not None:
        sh = sh.reindex([o for o in order if o in sh.index])
    return sh


# ---------------------------------------------------------------------
# Exports TO the USA: who carries them, by origin
# ---------------------------------------------------------------------
def to_usa_by_origin(d: pd.DataFrame) -> pd.DataFrame:
    tu = d[d["country_dest"] == "USA"].copy()
    if tu["value"].sum() < MIN_TO_USA_BN * 1e9:
        return pd.DataFrame()
    tu["grp"] = carrier(tu, ["USA"])
    sh = shares_table(tu, "country_orig").sort_values("home", ascending=False)
    allrow = shares_table(tu.assign(country_orig="All"), "country_orig")
    return pd.concat([sh, allrow])


def write_to_usa_table(sh: pd.DataFrame, path: Path, first_col: str, note: str) -> None:
    lines = [r"\begin{tabular}{lrrrrr}", r"\toprule",
             f"{first_col} & Exports to the USA (\\$bn) & US-parent MNEs (\\%) & Other foreign MNEs (\\%) & Domestic MNEs (\\%) & Local firms (\\%) \\\\", r"\midrule"]
    for idx, r in sh.iterrows():
        if idx == "All":
            lines.append(r"\midrule")
        lines.append(f"{W.tex_escape(idx)} & {r['total_bn']:,.1f} & {r['home']:.1f} & {r['other']:.1f} & {r['dom']:.1f} & {r['local']:.1f} \\\\")
    lines += [r"\bottomrule", rf"\multicolumn{{6}}{{p{{0.95\textwidth}}}}{{\footnotesize {note}}} \\", r"\end{tabular}"]
    W.write_tex(lines, path)


def draw_carriers(ax, sh: pd.DataFrame, labels, title: str = "", home_label="US-parent MNEs", us_label=None, fontsize=8):
    """Stacked horizontal bars: home / (US) / other foreign / domestic / local, rows in `sh` order (top to bottom)."""
    n = len(sh); y = np.arange(n)[::-1]
    segs = [("home", C_HOME, home_label)]
    if us_label and sh["us"].sum() > 0:
        segs.append(("us", C_US, us_label))
    segs += [("other", C_OTHER, "Other foreign MNEs"), ("dom", C_DOM, "Domestic MNEs"), ("local", C_LOCAL, "Local firms (unmatched)")]
    left = np.zeros(n)
    for col, color, lab in segs:
        v = sh[col].to_numpy()
        ax.barh(y, v, left=left, color=color, edgecolor="white", linewidth=0.6, label=lab)
        for k in range(n):
            if v[k] >= 4.5:
                ax.text(left[k] + v[k] / 2, y[k], f"{v[k]:.0f}", va="center", ha="center", fontsize=fontsize - 1,
                        color="white" if color in (C_HOME, C_US) else "#222222")
        left = left + v
    for k in range(n):
        ax.text(101, y[k], f"${sh['total_bn'].iloc[k]:,.1f}bn", va="center", ha="left", fontsize=fontsize - 1, color="#333333")
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=fontsize + 1)
    ax.set_xlim(0, 118); ax.set_xticks(np.arange(0, 101, 20))
    ax.set_xlabel("% of the export value reaching the destination; right margin = value", fontsize=fontsize + 1)
    if title:
        ax.set_title(title, fontsize=fontsize + 2)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def fig_to_usa(sh: pd.DataFrame, fname: str, G: Path, title: str = "") -> None:
    fig, ax = plt.subplots(figsize=(8.5, 0.5 * len(sh) + 1.9))
    draw_carriers(ax, sh, list(sh.index), title, fontsize=9)
    h, l = ax.get_legend_handles_labels()
    fig.legend(h, l, frameon=False, fontsize=8, loc="lower center", ncol=4, bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(rect=(0, 0.55 / fig.get_figheight(), 1, 1))
    W.savefig(fig, fname, G)


# ---------------------------------------------------------------------
# Exports to the main destinations: who carries them
# ---------------------------------------------------------------------
def dest_markets(d: pd.DataFrame) -> tuple[pd.Series, dict]:
    """Destination market label: EU-27 pooled, everything else by country. Returns (label series, home-parent sets)."""
    eu = d["country_dest"].isin(EU27)
    mk = d["country_dest"].where(~eu, "EU-27")
    homes = {"EU-27": EU27}
    return mk, homes


def dest_carriers(d: pd.DataFrame) -> pd.DataFrame:
    mk, homes = dest_markets(d)
    d = d.assign(market=mk)
    top = d.groupby("market")["value"].sum().sort_values(ascending=False).index[:N_DEST]
    out = []
    for m in top:
        t = d[d["market"] == m].copy()
        t["grp"] = carrier(t, homes.get(m, {m}))
        sh = shares_table(t.assign(market=m), "market")
        out.append(sh)
    return pd.concat(out)


def write_dest_table(sh: pd.DataFrame, path: Path, note: str) -> None:
    lines = [r"\begin{tabular}{lrrrrrr}", r"\toprule",
             r"Destination & " + " & ".join([r"\multicolumn{1}{p{1.6cm}}{\raggedright Exports (\$bn)}", r"\multicolumn{1}{p{2.6cm}}{\raggedright MNEs with parent in the destination (\%)}", r"\multicolumn{1}{p{1.8cm}}{\raggedright US-parent MNEs (\%)}", r"\multicolumn{1}{p{1.8cm}}{\raggedright Other foreign MNEs (\%)}", r"\multicolumn{1}{p{1.8cm}}{\raggedright Domestic MNEs (\%)}", r"\multicolumn{1}{p{1.8cm}}{\raggedright Local firms (\%)}"]) + r" \\", r"\midrule"]
    for idx, r in sh.iterrows():
        us = "--" if idx == "USA" else f"{r['us']:.1f}"
        lines.append(f"{W.tex_escape(idx)} & {r['total_bn']:,.1f} & {r['home']:.1f} & {us} & {r['other']:.1f} & {r['dom']:.1f} & {r['local']:.1f} \\\\")
    lines += [r"\bottomrule", rf"\multicolumn{{7}}{{p{{0.95\textwidth}}}}{{\footnotesize {note}}} \\", r"\end{tabular}"]
    W.write_tex(lines, path)


def fig_dest(sh: pd.DataFrame, fname: str, G: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 0.5 * len(sh) + 2.1))
    draw_carriers(ax, sh, list(sh.index), home_label="MNEs with parent in the destination", us_label="US-parent MNEs (destination $\\neq$ USA)", fontsize=9)
    h, l = ax.get_legend_handles_labels()
    fig.legend(h, l, frameon=False, fontsize=8, loc="lower center", ncol=3, bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(rect=(0, 0.75 / fig.get_figheight(), 1, 1))
    W.savefig(fig, fname, G)


# ---------------------------------------------------------------------
# Products: what US-parent MNEs ship home, and who carries the top LAC -> USA lines
# ---------------------------------------------------------------------
def _desc(codes: pd.Index, width: int = 46) -> dict:
    s = W.hs6_desc_fallback(pd.Series(list(codes)))
    out = {}
    for c, t in zip(codes, s):
        t = str(t) if pd.notna(t) else ""
        t = re.sub(r"\s+", " ", t).strip().replace("BrassiFres", "Brassieres")
        out[c] = (t[: width - 1] + "\u2026") if len(t) > width else t
    return out


def us_home_products(d: pd.DataFrame, T: Path, G: Path) -> None:
    tu = d[d["country_dest"] == "USA"].copy()
    tu["grp"] = carrier(tu, ["USA"])
    us_all = d[(d["owner_type"] == "ext") & (d["iso3_parent"] == "USA")]
    us_home = us_all[us_all["country_dest"] == "USA"]
    if us_home["value"].sum() < MIN_TO_USA_BN * 1e9 or us_home["hs07_6d"].nunique() < N_PROD:
        print("   US home products: too little value or too few lines; skipped"); return
    ph = us_home.groupby("hs07_6d")["value"].sum().sort_values(ascending=False)
    pall = us_all.groupby("hs07_6d")["value"].sum()                    # US-parent exports of the line, all destinations
    lac_usa = tu.groupby("hs07_6d")["value"].sum()                      # everything LAC ships of the line to the USA
    top = ph.index[:N_PROD]
    desc = _desc(top)
    rows = pd.DataFrame({"v_home": ph.loc[top] / 1e9, "sh_of_us_home": 100 * ph.loc[top] / ph.sum(),
                         "home_share": 100 * ph.loc[top] / pall.reindex(top), "lac_usa": lac_usa.reindex(top) / 1e9,
                         "us_share_of_lac_usa": 100 * ph.loc[top] / lac_usa.reindex(top)})
    lines = [r"\begin{tabular}{llrrrrr}", r"\toprule",
             r"HS6 & Description & " + " & ".join([r"\multicolumn{1}{p{2.0cm}}{\raggedright US-parent exports to the USA (\$bn)}", r"\multicolumn{1}{p{2.0cm}}{\raggedright \% of all US-parent exports to the USA}", r"\multicolumn{1}{p{2.4cm}}{\raggedright \% of US-parent exports of the line going to the USA}", r"\multicolumn{1}{p{2.2cm}}{\raggedright All LAC exports of the line to the USA (\$bn)}", r"\multicolumn{1}{p{2.6cm}}{\raggedright US-parent share of LAC exports of the line to the USA (\%)}"]) + r" \\", r"\midrule"]
    for h, r in rows.iterrows():
        lines.append(f"{h} & {W.tex_escape(desc[h])} & {r['v_home']:.2f} & {r['sh_of_us_home']:.1f} & {r['home_share']:.0f} & {r['lac_usa']:.2f} & {r['us_share_of_lac_usa']:.0f} \\\\")
    lines += [r"\midrule", f"All lines & & {ph.sum() / 1e9:,.1f} & 100.0 & {100 * ph.sum() / pall.sum():.0f} & {lac_usa.sum() / 1e9:,.1f} & {100 * ph.sum() / lac_usa.sum():.0f} \\\\", r"\bottomrule",
              rf"\multicolumn{{7}}{{p{{0.95\textwidth}}}}{{\footnotesize Top {N_PROD} HS6 lines by the value US-parent multinationals export from the nine origins to the United States. "
              r"Column 5 = of what US-parent MNEs export of the line from LAC (all destinations), the share shipped to the USA; column 7 = of what all firms in the nine origins export of the line to the USA, the share moved by US-parent MNEs. " + NOTE_BASE + "} \\\\", r"\end{tabular}"]
    W.write_tex(lines, T / "tab_wp3_us_home_products.tex")
    # figure: US-parent share of LAC -> USA exports of the line
    fig, ax = plt.subplots(figsize=(9, 0.42 * len(rows) + 1.8))
    y = np.arange(len(rows))[::-1]
    ax.barh(y, rows["us_share_of_lac_usa"], color=C_HOME)
    for yi, (h, r) in zip(y, rows.iterrows()):
        ax.text(r["us_share_of_lac_usa"] + 1, yi, f"{r['us_share_of_lac_usa']:.0f}%  (US-parent to USA \${r['v_home']:.1f}bn of \${r['lac_usa']:.1f}bn)", va="center", fontsize=7.5)
    ax.set_yticks(y); ax.set_yticklabels([f"{h} {desc[h][:44]}" for h in rows.index], fontsize=8)
    ax.set_xlim(0, 135); ax.set_xticks(np.arange(0, 101, 20))
    ax.set_xlabel("US-parent MNEs' share of everything the nine origins export of the line to the USA (%)", fontsize=9)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    W.savefig(fig, "fig_wp3_us_home_products", G)
    print("   US-parent lines shipped home (US share of LAC->USA): " + ", ".join(f"{h} {r['us_share_of_lac_usa']:.0f}%" for h, r in rows.head(8).iterrows()))

    # who carries the top LAC -> USA lines
    top2 = lac_usa.sort_values(ascending=False).index[:N_PROD]
    desc2 = _desc(top2)
    m = tu[tu["hs07_6d"].isin(top2)].pivot_table(index="hs07_6d", columns="grp", values="value", aggfunc="sum", fill_value=0.0)
    for c in ("home", "other", "dom", "local"):
        if c not in m.columns:
            m[c] = 0.0
    m = m.reindex(top2); tot = m.sum(axis=1); sh = 100 * m.div(tot, axis=0)
    lines = [r"\begin{tabular}{llrrrrr}", r"\toprule",
             r"HS6 & Description & " + " & ".join([r"\multicolumn{1}{p{2.0cm}}{\raggedright LAC exports to the USA (\$bn)}", r"\multicolumn{1}{p{1.8cm}}{\raggedright US-parent MNEs (\%)}", r"\multicolumn{1}{p{1.8cm}}{\raggedright Other foreign MNEs (\%)}", r"\multicolumn{1}{p{1.8cm}}{\raggedright Domestic MNEs (\%)}", r"\multicolumn{1}{p{1.8cm}}{\raggedright Local firms (\%)}"]) + r" \\", r"\midrule"]
    for h in top2:
        lines.append(f"{h} & {W.tex_escape(desc2[h])} & {tot[h] / 1e9:,.2f} & {sh.loc[h, 'home']:.0f} & {sh.loc[h, 'other']:.0f} & {sh.loc[h, 'dom']:.0f} & {sh.loc[h, 'local']:.0f} \\\\")
    lines += [r"\bottomrule", rf"\multicolumn{{7}}{{p{{0.95\textwidth}}}}{{\footnotesize Top {N_PROD} HS6 lines by the value the nine origins export to the United States, and the share of each line moved by each type of exporter. " + NOTE_BASE + "} \\\\", r"\end{tabular}"]
    W.write_tex(lines, T / "tab_wp3_to_usa_top_products.tex")


# ---------------------------------------------------------------------
# Per-scope driver
# ---------------------------------------------------------------------
def run_scope(cube: pd.DataFrame, scope: str) -> None:
    G, T, R = W.outdirs(scope)
    d = W.scope_filter(W.mne_flags(cube), scope)
    d = d[d["value"] > 0].copy()
    S = W.SCOPE_LABEL[scope].replace("\\\\&", "\\&")
    print(f"\n=== scope {scope}: ${d['value'].sum() / 1e9:,.1f} bn")
    sh = to_usa_by_origin(d)
    if len(sh):
        write_to_usa_table(sh, T / "tab_wp3_to_usa_carriers.tex", "Origin", f"{S}. Exports from each origin to the United States and the share of that value moved by each type of exporter; origins sorted by the US-parent share. " + NOTE_BASE)
        fig_to_usa(sh, "fig_wp3_to_usa_carriers", G)
        a = sh.loc["All"]
        print(f"   to USA ${a['total_bn']:,.1f}bn: US-parent {a['home']:.1f}%, other foreign {a['other']:.1f}%, domestic {a['dom']:.1f}%, local {a['local']:.1f}%")
        print("   US-parent share by origin: " + ", ".join(f"{o} {r['home']:.0f}%" for o, r in sh.drop("All").iterrows()))
    else:
        print("   too little exported to the USA; to-USA exhibits skipped")
    if d["value"].sum() >= 5e9:
        sd = dest_carriers(d)
        write_dest_table(sd, T / "tab_wp3_dest_carriers.tex", f"{S}. The {N_DEST} largest destination markets (EU-27 pooled) and the share of the value reaching each one moved by each type of exporter. `Parent in the destination': the exporter's ultimate parent is in the destination country (for the EU-27, in any member state); for the USA this group is the US-parent MNEs and the US-parent column is left blank. " + NOTE_BASE)
        fig_dest(sd, "fig_wp3_dest_carriers", G)
        print("   destinations: " + "; ".join(f"{m} ${r['total_bn']:,.0f}bn home {r['home']:.0f}% US {r['us']:.0f}% other {r['other']:.0f}% dom {r['dom']:.0f}%" for m, r in sd.iterrows()))
    us_home_products(d, T, G)


# ---------------------------------------------------------------------
# Cross-sector exhibits (scope "sectors")
# ---------------------------------------------------------------------
def cross_sector(cube: pd.DataFrame) -> None:
    G, T, R = W.outdirs("sectors")
    d = W.mne_flags(cube); d = d[d["value"] > 0].copy()
    d["sector4"] = W.sector4(d["hs2"])
    us = (d["owner_type"] == "ext") & (d["iso3_parent"] == "USA")

    # (a) who carries exports to the USA, by sector ------------------------------------------------
    tu = d[d["country_dest"] == "USA"].copy(); tu["grp"] = carrier(tu, ["USA"])
    rows = [shares_table(tu.assign(k="All goods"), "k")] + [shares_table(tu[tu["sector4"] == s].assign(k=s), "k") for s in W.SECTOR_ORDER if (tu["sector4"] == s).any()]
    sh_sec = pd.concat(rows)
    write_to_usa_table(sh_sec, T / "tab_wp3_to_usa_carriers_by_sector.tex", "Sector", "Exports from the nine origins to the United States by sector, and the share of that value moved by each type of exporter. " + NOTE_BASE)
    print("\n=== to the USA by sector:\n" + sh_sec.round(1).to_string())
    # two-panel figure: all goods | manufacturing, by origin
    sh_all = to_usa_by_origin(d); sh_man = to_usa_by_origin(d[d["sector4"] == "Manufacturing"])
    fig, axes = plt.subplots(1, 2, figsize=(12, 0.62 * len(sh_all) + 2.3))
    draw_carriers(axes[0], sh_all, list(sh_all.index), "All goods", fontsize=10.5)
    sh_man = sh_man.reindex(sh_all.index)
    draw_carriers(axes[1], sh_man, list(sh_man.index), "Manufacturing (HS 28--97 excl. 71)".replace("--", "\u2013"), fontsize=10.5)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, frameon=False, fontsize=10.5, loc="lower center", ncol=4, bbox_to_anchor=(0.5, 0.0))
    fig.tight_layout(rect=(0, 0.7 / fig.get_figheight(), 1, 1))
    W.savefig(fig, "fig_wp3_to_usa_carriers_total_manuf", G)

    # (b) US-parent share of exports, origin x sector -----------------------------------------------
    cols = [c for c, _ in SECTOR_COLS]
    tot = d.groupby(["country_orig", "sector4"])["value"].sum().unstack("sector4")
    usv = d[us].groupby(["country_orig", "sector4"])["value"].sum().unstack("sector4").reindex(tot.index).fillna(0.0)
    tot["All goods"] = tot.sum(axis=1); usv["All goods"] = usv.sum(axis=1)
    tot.loc["All"] = tot.sum(axis=0); usv.loc["All"] = usv.sum(axis=0)
    lab = {"all": "All goods", "agro": "Agriculture", "mining": "Mining & fuels", "manufacturing": "Manufacturing"}
    share = pd.DataFrame({c: 100 * usv[lab[c]] / tot[lab[c]] for c in cols})
    value = pd.DataFrame({c: usv[lab[c]] / 1e9 for c in cols})
    order = list(share.drop("All").sort_values("all", ascending=False).index) + ["All"]
    share, value = share.reindex(order), value.reindex(order)
    lines = [r"\begin{tabular}{lrrrrrrrr}", r"\toprule",
             r" & \multicolumn{4}{c}{US-parent MNE share of the cell's exports (\%)} & \multicolumn{4}{c}{US-parent MNE exports (\$bn)} \\",
             "Origin & " + " & ".join(l for _, l in SECTOR_COLS) + " & " + " & ".join(l for _, l in SECTOR_COLS) + r" \\", r"\midrule"]
    for o in order:
        if o == "All":
            lines.append(r"\midrule")
        lines.append(f"{o} & " + " & ".join(f"{share.loc[o, c]:.1f}" if tot.loc[o, lab[c]] > 0 else "--" for c in cols) + " & " + " & ".join(f"{value.loc[o, c]:,.1f}" for c in cols) + r" \\")
    lines += [r"\bottomrule", r"\multicolumn{9}{p{0.95\textwidth}}{\footnotesize Share of each origin's export value (all destinations) moved by multinationals whose recorded ultimate parent is in the United States, all goods and by sector; origins sorted by the all-goods share. Sectors as in the conventions (rest not shown, included in all goods). " + NOTE_BASE + r"} \\", r"\end{tabular}"]
    W.write_tex(lines, T / "tab_wp3_us_share_origin_sector.tex")
    n = len(order); x = np.arange(n); bw = 0.2
    fig, ax = plt.subplots(figsize=(11, 5.6))
    for i, (c, l) in enumerate(SECTOR_COLS):
        v = share[c].to_numpy()
        ax.bar(x + (i - 1.5) * bw, v, bw, color=SECTOR_COLORS[c], edgecolor="#1f3864" if c == "manufacturing" else "none", linewidth=0.5, label=l.replace("\\&", "&"))
        for xi, vi in zip(x, v):
            if np.isfinite(vi):
                ax.text(xi + (i - 1.5) * bw, vi + 0.6, f"{vi:.0f}", ha="center", fontsize=8.5)
    ax.set_xticks(x); ax.set_xticklabels(order, fontsize=12); ax.tick_params(axis="y", labelsize=11)
    ax.set_ylabel("US-parent MNE share of the origin's export value (%)", fontsize=11)
    ax.set_ylim(0, max(10, float(np.nanmax(share.to_numpy())) * 1.18))
    ax.axvline(n - 1.5, color="#999999", linewidth=0.6, linestyle=":")
    ax.legend(frameon=False, fontsize=11, ncol=4, loc="upper right")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    W.savefig(fig, "fig_wp3_us_share_origin_sector", G)
    print("\n=== US-parent share, origin x sector (%):\n" + share.round(1).to_string())

    # (c) home share by parent, total and by sector --------------------------------------------------
    ext = d[d["owner_type"] == "ext"].copy()
    ext["home"] = (ext["country_dest"] == ext["iso3_parent"]).astype(float) * ext["value"]
    top = W.top_parents(d, W.TOP_K_FIG)
    hs, hv = {}, {}
    for c in cols:
        e = ext if c == "all" else ext[ext["sector4"] == SECTOR_OF_COL[c]]
        g = e.groupby("iso3_parent").agg(value=("value", "sum"), home=("home", "sum")).reindex(top)
        hs[c] = 100 * g["home"] / g["value"]; hv[c] = g["value"] / 1e9
        allk = e.groupby("iso3_parent").agg(value=("value", "sum"), home=("home", "sum")).sum()
        hs[c]["All known-parent foreign MNEs"] = 100 * allk["home"] / allk["value"]; hv[c]["All known-parent foreign MNEs"] = allk["value"] / 1e9
    hs, hv = pd.DataFrame(hs), pd.DataFrame(hv)
    lines = [r"\begin{tabular}{lrrrrrrrr}", r"\toprule",
             r" & \multicolumn{4}{c}{\% of the parent's LAC exports shipped to the parent's own country} & \multicolumn{4}{c}{Parent's LAC exports (\$bn)} \\",
             "Parent & " + " & ".join(l for _, l in SECTOR_COLS) + " & " + " & ".join(l for _, l in SECTOR_COLS) + r" \\", r"\midrule"]
    for p in hs.index:
        if p == "All known-parent foreign MNEs":
            lines.append(r"\midrule")
        lines.append(f"{W.tex_escape(p)} & " + " & ".join("--" if not np.isfinite(hs.loc[p, c]) else f"{hs.loc[p, c]:.1f}" for c in cols) + " & " + " & ".join("--" if not np.isfinite(hv.loc[p, c]) else f"{hv.loc[p, c]:,.1f}" for c in cols) + r" \\")
    lines += [r"\bottomrule", rf"\multicolumn{{9}}{{p{{0.95\textwidth}}}}{{\footnotesize Top-{W.TOP_K_FIG} parent countries by foreign-MNE export value (all goods). Home share = value the parent's affiliates export from the nine origins to the parent's country, over everything they export from the nine origins, all goods and within each sector. Shares computed on less than \${MIN_PARENT_SECTOR_BN:.0f}bn of exports are fragile (see the value columns). Pooled 2006--2022; foreign MNEs with a recorded parent country.}} \\", r"\end{tabular}"]
    W.write_tex(lines, T / "tab_wp3_home_share_by_parent_sectors.tex")
    parents = list(hs.index); n = len(parents); y = np.arange(n)[::-1]; bh = 0.2
    fig, ax = plt.subplots(figsize=(9, 0.95 * n + 1.6))
    for i, (c, l) in enumerate(SECTOR_COLS):
        v = hs[c].to_numpy(); small = hv[c].to_numpy() < MIN_PARENT_SECTOR_BN
        yy = y + (1.5 - i) * bh
        ax.barh(yy, np.nan_to_num(v), bh, color=SECTOR_COLORS[c], edgecolor="#1f3864", linewidth=0.4, label=l.replace("\\&", "&"))
        ax.barh(yy[small], np.nan_to_num(v)[small], bh, color="white", edgecolor="#1f3864", linewidth=0.4, hatch="////")
        for yi, vi, vv in zip(yy, v, hv[c].to_numpy()):
            if np.isfinite(vi):
                ax.text(vi + 0.6, yi, f"{vi:.0f}%  (${vv:,.1f}bn)", va="center", fontsize=8, color="#333333")
    ax.set_yticks(y); ax.set_yticklabels([p.replace("All known-parent foreign MNEs", "All foreign MNEs\n(known parent)") for p in parents], fontsize=11); ax.tick_params(axis="x", labelsize=10)
    ax.set_xlim(0, max(30, float(np.nanmax(hs.to_numpy())) * 1.45)); ax.set_xlabel("% of the parent's export value from LAC shipped to the parent's own country; in parentheses the parent's exports in the scope", fontsize=8.5)
    ax.axhline(0.5, color="#999999", linewidth=0.6, linestyle=":")
    h, l = ax.get_legend_handles_labels()
    from matplotlib.patches import Patch
    h.append(Patch(facecolor="white", edgecolor="#1f3864", hatch="////")); l.append(f"< ${MIN_PARENT_SECTOR_BN:.0f}bn in the sector (fragile)")
    fig.legend(h, l, frameon=False, fontsize=9.5, loc="lower center", ncol=5, bbox_to_anchor=(0.5, 0.0))
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout(rect=(0, 0.55 / fig.get_figheight(), 1, 1))
    W.savefig(fig, "fig_wp3_home_share_by_parent_sectors", G)
    print("\n=== home share by parent x sector (%):\n" + hs.round(1).to_string())

    # (d) Facts 5 and 6: one table each, four columns ------------------------------------------------
    fact5_summary(T); fact6_summary(T)


# ---------------------------------------------------------------------
# Summary tables read from the wp1e fragments
# ---------------------------------------------------------------------
def parse_fragment(path: Path) -> tuple[dict, dict]:
    """Return ({row label: [cells]}, {row label: [se cells]}) for the coefficient rows of a wp1e table, and the
    observation rows under their own labels. A coefficient row is followed by a row whose label is empty."""
    coef, se = {}, {}
    if not path.exists():
        return coef, se
    raw = [l.strip() for l in path.read_text(encoding="utf-8").split("\n")]
    panel = ""
    i = 0
    # track the panel from the \multicolumn{..}{l}{\textit{Panel X}} lines
    lines_with_panels = []
    for l in raw:
        m = re.match(r"\\multicolumn\{\d+\}\{l\}\{\\textit\{(Panel [AB])", l)
        if m:
            panel = m.group(1); continue
        if l.endswith("\\\\") and "&" in l and not l.startswith("\\multicolumn"):
            lines_with_panels.append((panel, [c.strip() for c in l[:-2].split("&")]))
    while i < len(lines_with_panels):
        pnl, cells = lines_with_panels[i]
        lab = cells[0]
        if lab and i + 1 < len(lines_with_panels) and lines_with_panels[i + 1][1][0] == "" and any(c.startswith("(") for c in lines_with_panels[i + 1][1][1:]):
            key = (pnl, lab)
            coef[key] = cells[1:]; se[key] = lines_with_panels[i + 1][1][1:]; i += 2
        else:
            coef[(pnl, lab)] = cells[1:]; i += 1
    return coef, se


def _cell(coef, se, key, j):
    c = coef.get(key)
    if c is None or j >= len(c) or c[j] == "":
        return "", ""
    s = se.get(key, [])
    return c[j], (s[j] if j < len(s) else "")


def fact5_summary(T: Path) -> None:
    frags = {c: parse_fragment(W.WP_OUT / c / "Regressions" / "reg_wp1e_counts.tex") for c, _ in SECTOR_COLS}
    ROWS = [(r"$\ln$(\# foreign MNEs)", "Foreign MNEs"), (r"$\ln$(\# domestic MNEs)", "Domestic MNEs")]
    SPECS = [(2, r"Origin $\times$ year, destination $\times$ year and product FE (column (3) of the full table)"),
             (3, r"Origin $\times$ destination $\times$ product and origin $\times$ destination $\times$ year FE (column (4))")]
    ncol = len(SECTOR_COLS)
    lines = [rf"\begin{{tabular}}{{l{'c' * ncol}}} \hline", " & " + " & ".join(l for _, l in SECTOR_COLS) + r" \\ \hline"]
    for pnl, ptitle in (("Panel A", r"Panel A: all exports of the cell ($\ln$)"), ("Panel B", r"Panel B: exports of the cell's non-MNE firms ($\ln$)")):
        lines.append(rf"\multicolumn{{{ncol + 1}}}{{l}}{{\textit{{{ptitle}}}}} \\")
        for j, stitle in SPECS:
            lines.append(rf"\multicolumn{{{ncol + 1}}}{{l}}{{\footnotesize {stitle}}} \\")
            for lab, short in ROWS:
                b = [_cell(*frags[c], (pnl, lab), j) for c, _ in SECTOR_COLS]
                lines.append(f"\\quad $\\ln$(\\# {short[0].lower() + short[1:]}) & " + " & ".join(x[0] for x in b) + r" \\")
                lines.append(" & " + " & ".join(x[1] for x in b) + r" \\")
            key = "Observations (all exports)" if pnl == "Panel A" else "Observations (non-MNE exports)"
            obs = [_cell(*frags[c], ("Panel B", key), j)[0] or _cell(*frags[c], ("Panel A", key), j)[0] or _cell(*frags[c], ("", key), j)[0] for c, _ in SECTOR_COLS]
            lines.append("\\quad Observations & " + " & ".join(obs) + r" \\")
        if pnl == "Panel A":
            lines.append(r"\midrule")
    lines += [r"\hline", rf"\multicolumn{{{ncol + 1}}}{{p{{0.95\textwidth}}}}{{\footnotesize Fact 5 in one table: the coefficients of $\ln$(\# foreign MNEs) and $\ln$(\# domestic MNEs) from the intensive-margin decomposition (columns (3) and (4) of the full table in each scope), all goods and within each sector. Origin--destination--product--year cells with at least one foreign and one domestic MNE; plain logs; dep.\ var.\ $\ln$ exports of the cell (Panel A) or of its non-MNE exporters (Panel B). A blank cell was not estimated (too few observations). SE clustered at origin--destination in parentheses. *** p$<$0.01, ** p$<$0.05, * p$<$0.1}} \\", r"\end{tabular}"]
    W.write_tex(lines, T / "tab_wp3_fact5_summary.tex")
    print("\n=== Fact 5 summary (col. 3): " + "; ".join(f"{l}: F {_cell(*frags[c], ('Panel A', ROWS[0][0]), 2)[0]} / D {_cell(*frags[c], ('Panel A', ROWS[1][0]), 2)[0]}" for c, l in SECTOR_COLS))


def fact6_summary(T: Path) -> None:
    frags = {c: parse_fragment(W.WP_OUT / c / "Regressions" / "reg_wp1e_distance_hq.tex") for c, _ in SECTOR_COLS}
    ROWS = [(r"$\ln$ distance", r"$\ln$ distance"), (r"$\ln$ distance $\times$ foreign MNE", r"$\ln$ distance $\times$ foreign MNE"),
            (r"$\ln$ distance $\times$ domestic MNE", r"$\ln$ distance $\times$ domestic MNE")]
    SPECS = [(0, r"Origin, destination, year and product FE (column (1) of the full table)"), (1, r"Origin $\times$ year, destination $\times$ year and product FE (column (2))")]
    ncol = len(SECTOR_COLS)
    lines = [rf"\begin{{tabular}}{{l{'c' * ncol}}} \hline", r"Dep.\ var.: $\ln$ firm exports & " + " & ".join(l for _, l in SECTOR_COLS) + r" \\ \hline"]
    for k, (j, stitle) in enumerate(SPECS):
        if k:
            lines.append(r"\midrule")
        lines.append(rf"\multicolumn{{{ncol + 1}}}{{l}}{{\footnotesize {stitle}}} \\")
        for lab, short in ROWS:
            b = [_cell(*frags[c], ("", lab), j) for c, _ in SECTOR_COLS]
            lines.append(f"\\quad {short} & " + " & ".join(x[0] for x in b) + r" \\")
            lines.append(" & " + " & ".join(x[1] for x in b) + r" \\")
        obs = [_cell(*frags[c], ("", "Observations"), j)[0] for c, _ in SECTOR_COLS]
        lines.append("\\quad Observations & " + " & ".join(obs) + r" \\")
    lines += [r"\hline", rf"\multicolumn{{{ncol + 1}}}{{p{{0.95\textwidth}}}}{{\footnotesize Fact 6 in one table: the distance elasticity of firm exports and its attenuation for foreign and for domestic multinationals (columns (1) and (2) of the full table in each scope), all goods and within each sector. Firm $\times$ origin $\times$ destination $\times$ product $\times$ year; non-MNE flows are the omitted base, so the interaction is the difference from the base elasticity. SE clustered at origin--destination in parentheses. *** p$<$0.01, ** p$<$0.05, * p$<$0.1}} \\", r"\end{tabular}"]
    W.write_tex(lines, T / "tab_wp3_fact6_summary.tex")
    print("=== Fact 6 summary (col. 1): " + "; ".join(f"{l}: base {_cell(*frags[c], ('', ROWS[0][0]), 0)[0]} F {_cell(*frags[c], ('', ROWS[1][0]), 0)[0]} / D {_cell(*frags[c], ('', ROWS[2][0]), 0)[0]}" for c, l in SECTOR_COLS))


def main():
    cube = W.build_cube()
    for scope in SCOPES:
        run_scope(cube, scope)
    cross_sector(cube)
    print("\n>>> wp3 done")


if __name__ == "__main__":
    main()
