"""
SF-B reframed as export concentration (Lorenz), under three unit definitions:
  (1) naive        : each TIN is its own firm (pooled across LAC)
  (2) within-country: affiliates of the same parent in the SAME country grouped
  (3) cross-country : affiliates of the same parent grouped ACROSS LAC countries
Shows how correctly accounting for multinational ownership raises measured
concentration. Non-matched (non-MNE) firms stay as their own TIN in all three.

Also: top-100 cross-country overlap (companion to the top-50 heatmap).

Inputs: base (BASE_FILE). Cache: nsf_firm_level.parquet (country,Tax_ID -> value,
matched, parent group). Overlap uses nsf_parent_country.parquet.
"""
from __future__ import annotations
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (BASE_FILE, INT, GRAPHS, TABLES, OVERLEAF, EXCLUDED_ORIGINS,
                     C_MNE_EXT, ensure_dir, save_figure, parquet_chunks)  # noqa: E402

G = GRAPHS / "NewSFs"; T = TABLES / "NewSFs"
OL = OVERLEAF / "New_SFs_Analysis"; OLG = OL / "Graphs"; OLT = OL / "Tables"
for d in (G, T, OLG, OLT): ensure_dir(d)
NAVY, GRAY, GOLD = C_MNE_EXT, "#8c8c8c", "#c8a24a"
FIRM = INT / "nsf_firm_level.parquet"

def clean(s): return s.astype("string").str.strip().replace({"": pd.NA, ".": pd.NA})

# ---- firm-level cache: (country, Tax_ID) -> value, matched, parent ----
if FIRM.exists():
    print(">>> loading firm-level cache"); firm = pd.read_parquet(FIRM)
else:
    t0 = time.time(); parts = []
    cols = ["country_orig", "Tax_ID", "value_fob", "_merge_DNB_Orbis",
            "ent_name_par", "globalultimatebusinessname"]
    for i, ch in enumerate(parquet_chunks(BASE_FILE, cols, 1_000_000), 1):
        ch = ch[~ch.country_orig.isin(EXCLUDED_ORIGINS)]
        ch = ch[ch.Tax_ID.notna()]
        ch["v"] = ch["value_fob"].abs()
        ch = ch[ch.v > 0]
        ch["matched"] = (ch["_merge_DNB_Orbis"] == 3).astype("int8")
        par = clean(ch.ent_name_par).fillna(clean(ch.globalultimatebusinessname)).str.upper().str.strip()
        ch["parent"] = par.where(ch.matched == 1)
        parts.append(ch.groupby(["country_orig", "Tax_ID"], as_index=False)
                       .agg(value=("v", "sum"), matched=("matched", "max"),
                            parent=("parent", "first")))
        print(f"    chunk {i}: {time.time()-t0:.0f}s")
    firm = (pd.concat(parts, ignore_index=True)
              .groupby(["country_orig", "Tax_ID"], as_index=False)
              .agg(value=("value", "sum"), matched=("matched", "max"),
                   parent=("parent", "first")))
    firm.to_parquet(FIRM, index=False)
    print(f"  firms: {len(firm):,} ({time.time()-t0:.0f}s)")

firm["value"] = firm["value"].astype(float)
has_par = firm["parent"].notna() & (firm["matched"] == 1)
print(f"firms={len(firm):,} | matched-with-parent={has_par.sum():,} | "
      f"total value ${firm.value.sum()/1e9:.0f}bn")

# ---- three unit keys ----
tin_key = firm["country_orig"].astype(str) + "|TIN|" + firm["Tax_ID"].astype(str)
firm["u_naive"]  = tin_key
firm["u_within"] = np.where(has_par, firm["country_orig"].astype(str) + "|P|" + firm["parent"].astype(str), tin_key)
firm["u_cross"]  = np.where(has_par, "P|" + firm["parent"].astype(str), tin_key)

def unit_values(col):
    return firm.groupby(col)["value"].sum().sort_values().to_numpy()

def gini(v):
    v = np.sort(v); n = len(v); c = np.cumsum(v)
    return (n + 1 - 2 * (c.sum() / c[-1])) / n

def top_share(v, k):
    v = np.sort(v)[::-1]; return v[:k].sum() / v.sum()

defs = [("naive (each TIN)", "u_naive", NAVY),
        ("within-country (parent)", "u_within", GOLD),
        ("cross-country (parent)", "u_cross", "#b23b3b")]
print(f"\n{'definition':26s} {'n_units':>10} {'Gini':>6} {'top100 %':>9} {'top1% %':>8}")
rows = []
curves = []
for lab, col, c in defs:
    v = unit_values(col)
    g = gini(v); t100 = top_share(v, 100); t1p = top_share(v, max(1, len(v) // 100))
    print(f"{lab:26s} {len(v):>10,} {g:6.3f} {t100:9.1%} {t1p:8.1%}")
    rows.append((lab, len(v), g, t100, t1p))
    # Lorenz points (subsample)
    vs = np.sort(v); cum = np.cumsum(vs) / vs.sum(); x = np.arange(1, len(vs) + 1) / len(vs)
    idx = np.linspace(0, len(vs) - 1, 400).astype(int)
    curves.append((lab, x[idx], cum[idx], c))

# ---- Lorenz figure ----
fig, ax = plt.subplots(figsize=(6.4, 5.2))
for lab, x, y, c in curves:
    ax.plot(np.r_[0, x], np.r_[0, y], color=c, lw=2, label=lab)
ax.plot([0, 1], [0, 1], color="gray", ls="--", lw=1)
ax.set_xlabel("Cumulative share of firms (smallest first)")
ax.set_ylabel("Cumulative share of LAC exports")
ax.legend(frameon=False, loc="upper left")
save_figure(fig, "figB_lorenz_concentration", G, OLG)

# ---- concentration table ----
lines = [r"\begin{tabular}{lrrr}", r"\toprule",
         r"Unit definition & \# firms & Gini & Top-100 \% \\", r"\midrule"]
for lab, n, g, t100, _ in rows:
    lines.append(rf"{lab} & {n:,} & {g:.3f} & {t100*100:.1f} \\")
lines += [r"\bottomrule",
          r"\multicolumn{4}{p{0.8\textwidth}}{\footnotesize \emph{Notes.} All LAC "
          r"exporters (Ecuador excluded), value-weighted. Non-MNE firms remain their own "
          r"TIN in every column; only matched-MNE affiliates are grouped. Top-100 \% is "
          r"the export share of the 100 largest units.} \\", r"\end{tabular}"]
(T / "tabB_concentration.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")
(OLT / "tabB_concentration.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")

# ---- top-100 overlap (companion to top-50) ----
pc = pd.read_parquet(INT / "nsf_parent_country.parquet")
C = sorted(pc.country_orig.unique())
def overlap_matrix(df, key, k):
    sets = {c: set(g.sort_values("val", ascending=False)[key].head(k)) for c, g in df.groupby("country_orig")}
    M = np.zeros((len(C), len(C)))
    for i, a in enumerate(C):
        for j, b in enumerate(C):
            M[i, j] = len(sets[a] & sets[b])
    return M
for k in (100,):
    M = overlap_matrix(pc, "name_parent_adj", k)
    iu = M[np.triu_indices(len(C), 1)]
    print(f"\ntop-{k} overlap (name): mean={iu.mean():.1f}  max={int(iu.max())}  median={np.median(iu):.0f}  "
          f">=20 shared: {(iu>=20).mean():.0%}")
    fig, ax = plt.subplots(figsize=(6.2, 5.2))
    im = ax.imshow(np.where(np.eye(len(C), dtype=bool), np.nan, M), cmap="Blues", vmin=0)
    ax.set_xticks(range(len(C))); ax.set_xticklabels(C, rotation=45)
    ax.set_yticks(range(len(C))); ax.set_yticklabels(C)
    for i in range(len(C)):
        for j in range(len(C)):
            if i != j: ax.text(j, i, f"{int(M[i,j])}", ha="center", va="center", fontsize=8)
    ax.set_title(f"Shared groups in both top-{k} (of {k})")
    fig.colorbar(im, ax=ax, shrink=0.8)
    save_figure(fig, f"figB2_overlap_heatmap_name_k{k}", G, OLG)

print("\n>>> nsf_lorenz done.")
