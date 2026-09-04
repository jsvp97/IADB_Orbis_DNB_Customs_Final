"""
sf2_mne_origin.py
=================

Stylized Fact 2 (new): distribution of foreign-MNE export value by the
multinational's country of origin (the parent country, `iso3_parent`).

For each export transaction matched to the corporate database
(`_merge_DNB_Orbis == 3`) whose parent country is (i) known and
(ii) different from the exporting country -- i.e. a genuine foreign
multinational (MNE_ext) -- we sum FOB trade value by parent country and
express each as a share of total foreign-MNE export value.

Foreign MNEs with no recorded parent country (`iso3_parent` empty) are
DROPPED for this fact (we cannot attribute them to an origin country).
This differs from the project-wide MNE_ext definition, which keeps them.

Figure: horizontal bars, top-15 parent countries in descending order plus
an "Other" category for the remainder. Value-weighted, pooled across all
exporting origins (ECU excluded), destinations, products and years
2006--2022.

Outputs:
    1_Input/Intermediate/sf2_mne_origin_value.parquet   (parent-level value cache)
    2_Output/Graphs/SF2_MNEOrigin/fig_sf2_mne_origin.{pdf,png,eps} (+ Overleaf mirror)
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyreadstat

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    INT, BASE_FILE, GRAPHS, OVERLEAF_SF, EXCLUDED_ORIGINS,
    C_MNE_EXT, ensure_dir, save_figure, parquet_chunks,
)

G_SF2 = GRAPHS / "SF2_MNEOrigin"
OL_G_SF2 = OVERLEAF_SF / "Graphs" / "SF2_MNEOrigin"
for d in (G_SF2, OL_G_SF2):
    ensure_dir(d)

CACHE = INT / "sf2_mne_origin_value.parquet"
TOP_N = 15


# ---------------------------------------------------------------------
# Build parent-country value cache from the raw customs panel
# ---------------------------------------------------------------------
def build_cache() -> pd.DataFrame:
    raw = BASE_FILE
    print(f">>> Building parent-country cache from {raw}")
    t0 = time.time()
    cols = ["country_orig", "iso3_parent", "_merge_DNB_Orbis", "value_fob"]
    by_parent = {}          # known-parent foreign-MNE value
    v_ext_known = 0.0        # matched, parent known, parent != origin
    v_ext_unknown = 0.0      # matched, parent empty (dropped here; still MNE_ext project-wide)
    for i, ch in enumerate(parquet_chunks(raw, cols, 1_000_000), 1):
        ch = ch[ch["_merge_DNB_Orbis"] == 3]
        ch = ch[~ch["country_orig"].isin(EXCLUDED_ORIGINS)]
        if ch.empty:
            continue
        parent = ch["iso3_parent"].astype(str).str.strip()
        val = ch["value_fob"].abs()
        is_ext = parent != ch["country_orig"]          # foreign (parent != origin); "" counts as ext
        known = is_ext & (parent != "")
        unknown = is_ext & (parent == "")
        v_ext_known   += float(val[known].sum())
        v_ext_unknown += float(val[unknown].sum())
        g = val[known].groupby(parent[known]).sum()
        for k, v in g.items():
            by_parent[k] = by_parent.get(k, 0.0) + float(v)
        print(f"    chunk {i}: {time.time()-t0:.0f}s")

    df = (pd.Series(by_parent, name="value")
            .rename_axis("iso3_parent").reset_index()
            .sort_values("value", ascending=False).reset_index(drop=True))
    df.to_parquet(CACHE, index=False)
    frac_known = v_ext_known / (v_ext_known + v_ext_unknown)
    print(f"  parents: {len(df):,} | foreign-MNE value with known parent: "
          f"${v_ext_known/1e9:.1f}bn ({frac_known:.1%} of all foreign-MNE value; "
          f"${v_ext_unknown/1e9:.1f}bn dropped for missing parent)")
    return df


if CACHE.exists():
    print(f">>> Loading parent-country cache from {CACHE}")
    df = pd.read_parquet(CACHE)
else:
    df = build_cache()


# ---------------------------------------------------------------------
# Shares: top-15 + Other
# ---------------------------------------------------------------------
total = df["value"].sum()
df["share"] = df["value"] / total
top = df.head(TOP_N).copy()
other_share = df["share"].iloc[TOP_N:].sum()
n_other = len(df) - TOP_N

print(f"\n>>> Foreign-MNE export value by parent country (top {TOP_N} of {len(df)}):")
for _, r in top.iterrows():
    print(f"    {r['iso3_parent']:5s} {r['share']*100:6.2f}%   (${r['value']/1e9:7.2f}bn)")
print(f"    Other ({n_other} countries) {other_share*100:6.2f}%")


# ---------------------------------------------------------------------
# Figure: descending horizontal bars, top-15 + Other
# ---------------------------------------------------------------------
labels = top["iso3_parent"].tolist() + ["Other"]
shares = top["share"].tolist() + [other_share]

fig, ax = plt.subplots(figsize=(8, 6))
y = np.arange(len(labels))[::-1]          # rank 1 at the top, Other at the bottom
ax.barh(y, shares, color=C_MNE_EXT, edgecolor=C_MNE_EXT)
for yi, s in zip(y, shares):
    ax.text(s + max(shares) * 0.01, yi, f"{s*100:.1f}%", va="center", fontsize=9)
ax.set_yticks(y)
ax.set_yticklabels(labels)
ax.set_xlim(0, max(shares) * 1.12)
ax.set_xlabel("Share of foreign-MNE export value")
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v*100:.0f}%"))
save_figure(fig, "fig_sf2_mne_origin", G_SF2, OL_G_SF2)
print(f"\n>>> Figure written to {G_SF2}")
