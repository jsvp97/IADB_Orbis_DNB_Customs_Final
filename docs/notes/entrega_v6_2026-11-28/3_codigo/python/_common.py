"""
Common helpers for the MNCustoms stylized-facts Python pipeline.

Paths, output-directory wiring, matplotlib defaults, and small utilities
shared by all SF scripts. Matches the on-disk layout already established
by the Stata pipeline so existing Overleaf \\input{} paths keep working.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Iterable

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

# ---------------------------------------------------------------------
# Paths (mirror 01_setup.do)
# ---------------------------------------------------------------------
ROOT     = Path(r"D:\MNEs_Trade")
INPUT    = ROOT / "1_Input"
CUSTOMS  = INPUT / "Customs"
GRAVITY  = INPUT / "Gravity"
PRODUCT  = INPUT / "Product"
COUNTRY  = INPUT / "Country"
INT      = INPUT / "Intermediate"
SEBASTIAN = INPUT / "Sebastian_Orbis_DNB_Customs"

# Canonical large inputs — migrated from Stata .dta to parquet (2026-07-01),
# lossless (row/col/value verified; Stata labels in _stata_labels_metadata.json).
# The old 1_Input\Customs\*.dta base was deleted after conversion. Read these
# with parquet_chunks(); they are supersets of the April base (107 vs 90 cols).
BASE_FILE         = SEBASTIAN / "Base_final_Customs_DNB_Orbis_product_complete.parquet"
MNE_PRESENCE_FILE = SEBASTIAN / "intermediate_mne_presence.parquet"
MERGE_AFF_FILE    = SEBASTIAN / "Merge_DNB_Orbis_PostIA_v2.parquet"
FIRM_LEVEL_FILE   = SEBASTIAN / "firm_level_data_full.parquet"

OUTPUT   = ROOT / "2_Output"
GRAPHS   = OUTPUT / "Graphs"
TABLES   = OUTPUT / "Tables"
REGS     = OUTPUT / "Regressions"

OVERLEAF = Path(r"C:\Users\nnmar\Dropbox\Aplicaciones\Overleaf\Multinational Firms and Trade")
OVERLEAF_SF = OVERLEAF / "Stylized_Facts"

# Project-wide exclusion (mirror $excluded_origins)
EXCLUDED_ORIGINS = ("ECU",)

# ---------------------------------------------------------------------
# Plot style
# ---------------------------------------------------------------------
# Palette (revised 2026-06-01, user request):
#   foreign  (ext) -> navy blue
#   domestic (dom) -> light gray
# C_MNE_TOT kept only for legacy/parked exhibits; current minimal figure
# set (SF1 stacked bar, SF2 ext+dom bars) does not draw an MNE-total series.
C_MNE_EXT   = "#1f3864"   # navy blue (foreign MNE)
C_MNE_DOM   = "#bfbfbf"   # light gray (domestic MNE)
C_MNE_TOT   = "#2e7d32"   # green (legacy; unused in current minimal set)

mpl.rcParams.update({
    "font.family":          "serif",
    "font.serif":           ["Times New Roman", "DejaVu Serif"],
    "font.size":            11,
    "axes.titlesize":       12,
    "axes.labelsize":       11,
    "axes.spines.top":      False,
    "axes.spines.right":    False,
    "axes.edgecolor":       "black",
    "axes.linewidth":       0.8,
    "axes.grid":            False,
    "figure.facecolor":     "white",
    "axes.facecolor":       "white",
    "savefig.facecolor":    "white",
    "savefig.bbox":         "tight",
    "savefig.dpi":          200,
    "pdf.fonttype":         42,  # TrueType
    "ps.fonttype":          42,
})


# ---------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------

def ensure_dir(path: Path) -> Path:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def parquet_chunks(path, columns=None, chunksize: int = 1_000_000):
    """Yield pandas DataFrame chunks from a parquet file, reading only `columns`.

    Drop-in replacement for the old
        pyreadstat.read_file_in_chunks(pyreadstat.read_dta, str(raw), ...)
    loop: iterate `for ch in parquet_chunks(path, cols):` (no (df, meta) tuple).
    """
    pf = pq.ParquetFile(path)
    for batch in pf.iter_batches(batch_size=chunksize, columns=columns):
        yield batch.to_pandas()


def save_figure(fig, name: str, local_dir: Path, overleaf_dir: Path | None = None,
                exts: Iterable[str] = ("pdf", "png", "eps")) -> None:
    """Save figure to local_dir (and mirror to overleaf_dir) in given formats."""
    local_dir = ensure_dir(local_dir)
    for ext in exts:
        fig.savefig(local_dir / f"{name}.{ext}")
    if overleaf_dir is not None:
        overleaf_dir = ensure_dir(overleaf_dir)
        for ext in exts:
            shutil.copy2(local_dir / f"{name}.{ext}", overleaf_dir / f"{name}.{ext}")
    plt.close(fig)


# ---------------------------------------------------------------------
# Table writing helpers
# ---------------------------------------------------------------------

def stars(p: float) -> str:
    if p < 0.01:  return "***"
    if p < 0.05:  return "**"
    if p < 0.10:  return "*"
    return ""


def write_country_share_table(df: pd.DataFrame, share_col: str, label: str,
                              out_path: Path, *, overleaf_path: Path | None = None,
                              with_gdppc: bool = True) -> None:
    """
    df: cross-section with columns [country_orig, <share_col>, ln_gdpcap_o]
    Writes a 3-column or 2-column tabular fragment sorted by share_col desc.
    """
    df = df.sort_values(share_col, ascending=False).reset_index(drop=True)
    lines = []
    if with_gdppc:
        lines.append(r"\begin{tabular}{lcc}")
        lines.append(r"\toprule")
        lines.append(rf" & {label} share & $\ln \text{{GDPpc}}$ \\")
        lines.append(r"Country & (value, pooled) & (origin, mean) \\")
        lines.append(r"\midrule")
        for _, r in df.iterrows():
            lines.append(f"{r['country_orig']} & {r[share_col]:.3f} & {r['ln_gdpcap_o']:5.2f} \\\\")
    else:
        lines.append(r"\begin{tabular}{lc}")
        lines.append(r"\toprule")
        lines.append(rf" & {label} share \\")
        lines.append(r"Country & (value, pooled) \\")
        lines.append(r"\midrule")
        for _, r in df.iterrows():
            lines.append(f"{r['country_orig']} & {r[share_col]:.3f} \\\\")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")

    out_path = Path(out_path)
    ensure_dir(out_path.parent)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if overleaf_path is not None:
        overleaf_path = Path(overleaf_path)
        ensure_dir(overleaf_path.parent)
        shutil.copy2(out_path, overleaf_path)


def write_combined_share_table(df: pd.DataFrame, out_path: Path,
                               overleaf_path: Path | None = None) -> None:
    """
    df has columns country_orig, sh_total, sh_ext, sh_dom, ln_gdpcap_o.
    Sorted by sh_total desc.
    """
    df = df.sort_values("sh_total", ascending=False).reset_index(drop=True)
    lines = [
        r"\begin{tabular}{lcccc}",
        r"\toprule",
        r" & MNE$_{\text{total}}$ & MNE$_{\text{ext}}$ & MNE$_{\text{dom}}$ & $\ln \text{GDPpc}$ \\",
        r"Country & share (value) & share (value) & share (value) & (origin, mean) \\",
        r"\midrule",
    ]
    for _, r in df.iterrows():
        lines.append(
            f"{r['country_orig']} & {r['sh_total']:.3f} & {r['sh_ext']:.3f} & "
            f"{r['sh_dom']:.3f} & {r['ln_gdpcap_o']:5.2f} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}"]

    out_path = Path(out_path)
    ensure_dir(out_path.parent)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if overleaf_path is not None:
        overleaf_path = Path(overleaf_path)
        ensure_dir(overleaf_path.parent)
        shutil.copy2(out_path, overleaf_path)


def write_regression_table(specs: list[dict], out_path: Path,
                            overleaf_path: Path | None = None,
                            dep_label: str = "Dep. var.") -> None:
    """
    specs: list of dicts, one per column. Each dict has:
        title:        column title (e.g. "OLS")
        coefs:        list of (label, beta, se, pval) -- in order shown in rows
        n:            integer
        r2:           float
        addtext:      list of (label, value) rows (e.g. ('Year FE', 'No'))

    All specs must have the same set of coefs and addtext keys in the same order.
    Writes an outreg2-style fragment.
    """
    if not specs:
        raise ValueError("specs is empty")
    ncols = len(specs)

    # Collect coef labels in display order (from the first spec)
    coef_labels = [c[0] for c in specs[0]["coefs"]]
    addtext_labels = [a[0] for a in specs[0]["addtext"]]

    lines = []
    lines.append(rf"\begin{{tabular}}{{l{'c'*ncols}}} \hline")
    lines.append(" & " + " & ".join(f"({i+1})" for i in range(ncols)) + r" \\")
    lines.append("VARIABLES & " + " & ".join(s["title"] for s in specs) + r" \\ \hline")
    lines.append(" & " + " & ".join(" " for _ in specs) + r" \\")

    for ci, clabel in enumerate(coef_labels):
        # Coefficient row
        cells = []
        for s in specs:
            _, b, se, p = s["coefs"][ci]
            if b is None:
                cells.append("")
            else:
                cells.append(f"{b:.4f}{stars(p)}")
        lines.append(f"{clabel} & " + " & ".join(cells) + r" \\")
        # SE row
        cells = []
        for s in specs:
            _, b, se, p = s["coefs"][ci]
            if b is None:
                cells.append("")
            else:
                cells.append(f"({se:.4f})")
        lines.append(" & " + " & ".join(cells) + r" \\")

    lines.append(" & " + " & ".join(" " for _ in specs) + r" \\")
    lines.append("Observations & " + " & ".join(f"{s['n']}" for s in specs) + r" \\")
    lines.append("R-squared & " + " & ".join(f"{s['r2']:.4f}" for s in specs) + r" \\")
    for ai, alabel in enumerate(addtext_labels):
        vals = " & ".join(str(s["addtext"][ai][1]) for s in specs)
        lines.append(f"{alabel} & " + vals + r" \\")
    lines.append(r"\hline")
    lines.append(rf"\multicolumn{{{ncols+1}}}{{c}}{{ Robust standard errors in parentheses}} \\")
    lines.append(rf"\multicolumn{{{ncols+1}}}{{c}}{{ *** p$<$0.01, ** p$<$0.05, * p$<$0.1}} \\")
    lines.append(r"\end{tabular}")

    out_path = Path(out_path)
    ensure_dir(out_path.parent)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if overleaf_path is not None:
        overleaf_path = Path(overleaf_path)
        ensure_dir(overleaf_path.parent)
        shutil.copy2(out_path, overleaf_path)


# ---------------------------------------------------------------------
# Regression helper (statsmodels OLS with HC1 robust SE)
# ---------------------------------------------------------------------

def ols_robust(df: pd.DataFrame, y: str, X: list[str], year_fe: bool = False):
    """
    Fit OLS y ~ X (+ year dummies if year_fe). Returns the fitted model
    with HC1 robust covariance. Drops year-FE singletons to match reghdfe.
    """
    data = df[[y] + X + (["year"] if year_fe else [])].dropna().copy()
    if year_fe:
        # Drop singleton year groups (analogous to reghdfe singleton drop)
        counts = data.groupby("year").size()
        keep_years = counts[counts > 1].index
        data = data[data["year"].isin(keep_years)].copy()
        dummies = pd.get_dummies(data["year"].astype(int), prefix="yr", drop_first=True).astype(float)
        Xmat = pd.concat([data[X], dummies], axis=1)
    else:
        Xmat = data[X].copy()

    import statsmodels.api as sm
    Xmat = sm.add_constant(Xmat)
    Xmat = Xmat.astype(float)
    yvec = data[y].astype(float)
    model = sm.OLS(yvec, Xmat).fit(cov_type="HC1")
    return model
