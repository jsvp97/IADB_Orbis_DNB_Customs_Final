"""
sf1_origin.py
=============

Stylized Fact 1 (Python rewrite of _sf1_build_and_run.do).

Inputs:
    1_Input\\Intermediate\\sf1_origin_value.dta  -- existing Stata cache

Outputs (mirror Stata pipeline so existing Overleaf includes keep working):
    2_Output\\Graphs\\SF1_OriginShare\\fig_sf1_hbar_{total,ext,dom}.{pdf,png,eps}
    2_Output\\Graphs\\SF1_OriginShare\\fig_sf1_scatter_{total,ext,dom}.{pdf,png,eps}
    2_Output\\Tables\\SF1_OriginShare\\tab_sf1_share_by_country.tex
    2_Output\\Tables\\SF1_OriginShare\\tab_sf1_share_by_country_{total,ext,dom}.tex
    2_Output\\Regressions\\SF1_OriginShare\\reg_sf1_{total,ext,dom}.tex
    + Overleaf mirror under Stylized_Facts/

MNE conventions:
    total = matched in corporate DB
    ext   = matched AND parent != exporting country  (= total - dom)
    dom   = matched AND parent == exporting country

Origin exclusions: ECU (see _common.EXCLUDED_ORIGINS).
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyreadstat
import pyfixest as pf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    INT, GRAPHS, TABLES, REGS, OVERLEAF_SF, EXCLUDED_ORIGINS,
    C_MNE_TOT, C_MNE_EXT, C_MNE_DOM,
    ensure_dir, save_figure,
    write_country_share_table, write_combined_share_table,
    write_regression_table, ols_robust,
)


# ---------------------------------------------------------------------
# Output paths
# ---------------------------------------------------------------------
G_SF1 = GRAPHS / "SF1_OriginShare"
T_SF1 = TABLES / "SF1_OriginShare"
R_SF1 = REGS   / "SF1_OriginShare"

OL_G_SF1 = OVERLEAF_SF / "Graphs"      / "SF1_OriginShare"
OL_T_SF1 = OVERLEAF_SF / "Tables"      / "SF1_OriginShare"
OL_R_SF1 = OVERLEAF_SF / "Regressions" / "SF1_OriginShare"

for d in (G_SF1, T_SF1, R_SF1, OL_G_SF1, OL_T_SF1, OL_R_SF1):
    ensure_dir(d)


# ---------------------------------------------------------------------
# Step 1: load + clean the SF1 cache
# ---------------------------------------------------------------------
CACHE = INT / "sf1_origin_value.dta"
print(f">>> Loading cache {CACHE}")
df, meta = pyreadstat.read_dta(str(CACHE))
print(f"    raw cache: {len(df):,} rows, {df.columns.tolist()}")

df = df[~df["country_orig"].isin(EXCLUDED_ORIGINS)].copy()

# Recompute MNE_ext with the new convention val_ext := val_total - val_dom.
# (The Stata-side cache already does this on save, but we re-derive here
# for safety in case the cache is older.)
df["val_ext"] = df["val_total"] - df["val_dom"]

# Year-level value shares
df["share_value_total"] = df["val_total"] / df["total_value"]
df["share_value_ext"]   = df["val_ext"]   / df["total_value"]
df["share_value_dom"]   = df["val_dom"]   / df["total_value"]

print(f"    after ECU drop: {len(df):,} origin-year obs")
print(f"    origins: {sorted(df['country_orig'].unique())}")
print(f"    years:   {int(df['year'].min())}–{int(df['year'].max())}")


# Cross-section: pool across years (value-weighted)
cross = (df.groupby("country_orig", as_index=False)
           .agg(total_value=("total_value", "sum"),
                val_total=("val_total", "sum"),
                val_dom=("val_dom", "sum"),
                ln_gdpcap_o=("ln_gdpcap_o", "mean"),
                ln_pop_o=("ln_pop_o", "mean")))
cross["val_ext"]   = cross["val_total"] - cross["val_dom"]
cross["sh_total"]  = cross["val_total"] / cross["total_value"]
cross["sh_ext"]    = cross["val_ext"]   / cross["total_value"]
cross["sh_dom"]    = cross["val_dom"]   / cross["total_value"]

lo = cross["sh_total"].min() * 100
hi = cross["sh_total"].max() * 100
cmin = cross.loc[cross["sh_total"].idxmin(), "country_orig"]
cmax = cross.loc[cross["sh_total"].idxmax(), "country_orig"]
print(f">>> SF1 caption fact: MNE_total share ranges {lo:.1f}% ({cmin}) to {hi:.1f}% ({cmax}).")


# ---------------------------------------------------------------------
# Step 2: descriptive tables (combined + one per MNE def)
# ---------------------------------------------------------------------
write_combined_share_table(
    cross[["country_orig", "sh_total", "sh_ext", "sh_dom", "ln_gdpcap_o"]],
    out_path=T_SF1 / "tab_sf1_share_by_country.tex",
    overleaf_path=OL_T_SF1 / "tab_sf1_share_by_country.tex",
)

LABELS = {
    "total": r"MNE$_{\text{total}}$",
    "ext":   r"MNE$_{\text{ext}}$",
    "dom":   r"MNE$_{\text{dom}}$",
}
for d in ("total", "ext", "dom"):
    write_country_share_table(
        cross[["country_orig", f"sh_{d}", "ln_gdpcap_o"]].rename(columns={f"sh_{d}": f"sh_{d}"}),
        share_col=f"sh_{d}",
        label=LABELS[d],
        out_path=T_SF1 / f"tab_sf1_share_by_country_{d}.tex",
        overleaf_path=OL_T_SF1 / f"tab_sf1_share_by_country_{d}.tex",
    )

print(f">>> Tables written to {T_SF1}")


# ---------------------------------------------------------------------
# Step 3: main figure -- stacked horizontal bar by origin
#   Each origin's MNE export-value share is split into:
#     foreign  (MNE_ext, navy)  + domestic (MNE_dom, light gray)
#   stacked so the full bar length = MNE_total share.
# ---------------------------------------------------------------------

def stacked_origin_bar():
    sub = cross.sort_values("sh_total", ascending=True).reset_index(drop=True)
    y = np.arange(len(sub))
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(y, sub["sh_ext"], color=C_MNE_EXT, edgecolor="white", linewidth=0.6,
            label="Foreign MNEs")
    ax.barh(y, sub["sh_dom"], left=sub["sh_ext"], color=C_MNE_DOM,
            edgecolor="white", linewidth=0.6, label="Domestic MNEs")

    for yi, r in zip(y, sub.itertuples()):
        if r.sh_ext > 0.05:
            ax.text(r.sh_ext / 2, yi, f"{r.sh_ext:.2f}", va="center", ha="center",
                    color="white", fontsize=8)
        if r.sh_dom > 0.04:
            ax.text(r.sh_ext + r.sh_dom / 2, yi, f"{r.sh_dom:.2f}", va="center",
                    ha="center", color="black", fontsize=8)
        ax.text(r.sh_total + 0.006, yi, f"{r.sh_total:.2f}", va="center", ha="left",
                fontsize=8, fontweight="bold")

    ax.set_yticks(y)
    ax.set_yticklabels(sub["country_orig"])
    ax.set_xlabel("MNE share in export value (value-weighted)")
    xmax = max(0.85, sub["sh_total"].max() * 1.12)
    ax.set_xlim(0, xmax)
    ax.set_xticks(np.arange(0, xmax + 1e-9, 0.1))
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    return fig


fig = stacked_origin_bar()
save_figure(fig, "fig_sf1_stacked_origin", G_SF1, OL_G_SF1)
print(f">>> Main figure (stacked origin bar) written to {G_SF1}")


# ---------------------------------------------------------------------
# Step 4: regressions (4 specs per MNE def)
# ---------------------------------------------------------------------
def _coef(m, name):
    """Return (beta, se, p) for `name`, or (None, None, None) if absent."""
    c, s, p = m.coef(), m.se(), m.pvalue()
    if name in c.index:
        return float(c[name]), float(s[name]), float(p[name])
    return None, None, None


def run_specs(dvar: str) -> list[dict]:
    """Origin-year panel: share on ln GDPpc (+ ln pop) (+ year FE).
    Estimated with pyfixest; HC1 robust SE (vcov='hetero')."""
    def r2(m):
        return float(getattr(m, "_r2", float("nan")))

    specs = []
    # Col 1: OLS robust
    m = pf.feols(f"{dvar} ~ ln_gdpcap_o", data=df, vcov="hetero")
    specs.append(dict(title="OLS",
                      coefs=[("Log GDP per capita (origin)", *_coef(m, "ln_gdpcap_o")),
                             ("Log population (origin)",      None, None, None),
                             ("Constant",                     *_coef(m, "Intercept"))],
                      n=int(m._N), r2=r2(m),
                      addtext=[("Year FE", "No"), ("Pop control", "No"), ("SE", "Robust")]))

    # Col 2: + ln pop
    m = pf.feols(f"{dvar} ~ ln_gdpcap_o + ln_pop_o", data=df, vcov="hetero")
    specs.append(dict(title="+ ln pop",
                      coefs=[("Log GDP per capita (origin)", *_coef(m, "ln_gdpcap_o")),
                             ("Log population (origin)",      *_coef(m, "ln_pop_o")),
                             ("Constant",                     *_coef(m, "Intercept"))],
                      n=int(m._N), r2=r2(m),
                      addtext=[("Year FE", "No"), ("Pop control", "Yes"), ("SE", "Robust")]))

    # Col 3: Year FE
    m = pf.feols(f"{dvar} ~ ln_gdpcap_o | year", data=df, vcov="hetero")
    specs.append(dict(title="Year FE",
                      coefs=[("Log GDP per capita (origin)", *_coef(m, "ln_gdpcap_o")),
                             ("Log population (origin)",      None, None, None),
                             ("Constant",                     None, None, None)],
                      n=int(m._N), r2=r2(m),
                      addtext=[("Year FE", "Yes"), ("Pop control", "No"), ("SE", "Robust")]))

    # Col 4: Year FE + pop
    m = pf.feols(f"{dvar} ~ ln_gdpcap_o + ln_pop_o | year", data=df, vcov="hetero")
    specs.append(dict(title="Year FE + pop",
                      coefs=[("Log GDP per capita (origin)", *_coef(m, "ln_gdpcap_o")),
                             ("Log population (origin)",      *_coef(m, "ln_pop_o")),
                             ("Constant",                     None, None, None)],
                      n=int(m._N), r2=r2(m),
                      addtext=[("Year FE", "Yes"), ("Pop control", "Yes"), ("SE", "Robust")]))
    return specs


for d in ("total", "ext", "dom"):
    specs = run_specs(f"share_value_{d}")
    write_regression_table(
        specs,
        out_path=R_SF1 / f"reg_sf1_{d}.tex",
        overleaf_path=OL_R_SF1 / f"reg_sf1_{d}.tex",
    )
    # Also print to console for quick sanity-check
    print(f"\n--- {d.upper()} ---")
    for i, s in enumerate(specs, 1):
        ln_gdp = s["coefs"][0]
        ln_pop = s["coefs"][1]
        print(f"  ({i}) {s['title']:14s}  ln_gdpcap_o = {ln_gdp[1]:+.4f} ({ln_gdp[2]:.4f}) "
              f"p={ln_gdp[3]:.3f}  R2={s['r2']:.3f}  N={s['n']}"
              + (f"   ln_pop_o = {ln_pop[1]:+.4f} ({ln_pop[2]:.4f}) p={ln_pop[3]:.3f}" if ln_pop[1] is not None else ""))

print(f"\n>>> Regression tables written to {R_SF1}")
print(">>> SF1 Python pipeline complete.")
