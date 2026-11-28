"""
wp_agro_v4_paper.py  --  the exhibits of Note_v4.tex (agriculture paper, version 4) and the cells it prints
=========================================================================================================

    WP_YEARS=2012-2018 WP_SCOPES=agro python wp_agro_v4_paper.py desc      2018 descriptive exhibits
    WP_YEARS=2012-2018 WP_SCOPES=agro python wp_agro_v4_paper.py regs      regression and event-study exhibits
    WP_YEARS=2012-2018 WP_SCOPES=agro python wp_agro_v4_paper.py flatten   Note_v4.tex from docs/notes/Note_v4_source.tex

Tables and pgfplots figures go to docs/overleaf_projects/WP_paperagro/tables/v4 (and output/wp_2012_2018/agro/v4).
Numbers quoted in the text are in v4_facts.json. The cells printed in the paper are listed in v4_shown.json, which
wp_agro_v4_workbook.py reads to colour them red. The 2018 descriptive tables reuse the code of wp_agro_note_v3.py,
restricted to real destinations (spec 0.1: free trade zones and the exporting country are not destinations).
"""
from __future__ import annotations

import json
import os
import pickle
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("WP_HS17", "1")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_common as W  # noqa: E402
import wp_agro_note_v3 as N  # noqa: E402

OUT4 = W.WP_OUT / "agro" / "v4"
TEX4 = W.ROOT / "docs" / "overleaf_projects" / "WP_paperagro" / "tables" / "v4"
SRC = W.ROOT / "docs" / "notes" / "Note_v4_source.tex"
NOTE = W.ROOT / "docs" / "overleaf_projects" / "WP_paperagro" / "Note_v4.tex"
V4 = W.WP_INT / "v4"
for d in (OUT4, TEX4):
    d.mkdir(parents=True, exist_ok=True)
FACTS_JSON = OUT4 / "v4_facts.json"
SHOWN_JSON = OUT4 / "v4_shown.json"
COUNTRY = N.COUNTRY
FACTS: dict = json.load(open(FACTS_JSON)) if FACTS_JSON.exists() else {}
SHOWN: dict = json.load(open(SHOWN_JSON)) if SHOWN_JSON.exists() else {}


def save_tex(name: str, txt: str) -> None:
    name = name.replace("v3_", "v4_")
    (OUT4 / f"{name}.tex").write_text(txt, encoding="utf-8")
    (TEX4 / f"{name}.tex").write_text(txt, encoding="utf-8")


# the v3 writers now write here, under v4 names
N.save_tex = save_tex
N.OUTD = OUT4
N.TEXD = TEX4
_load_2018 = N.load_2018


def load_2018_real():
    a, tot_all = _load_2018()
    return a[a["dest_real"].notna()].copy(), tot_all


N.load_2018 = load_2018_real


def stars(p):
    return "" if p is None or not np.isfinite(p) else ("***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else "")


def write_plain(name, header, rows, colspec=None, midrule_before=()):
    N.write_plain(name, header, rows, colspec=colspec, midrule_before=midrule_before)


# ---------------------------------------------------------------------
# 2018 descriptive exhibits
# ---------------------------------------------------------------------
def desc() -> None:
    g = N.cells()
    N.FACTS["origin_order"] = N.origins_by_value(g)
    N.descriptives(g)
    FACTS["v3desc"] = N.FACTS["desc"]
    FACTS["origin_order"] = N.FACTS["origin_order"]
    a, tot_all = load_2018_real()
    ext = a["otype"] == "ext"

    # sector context (E1a)
    D = {}
    for f in sorted(OUT4.glob("v4_desc_*.pkl"), key=lambda p: p.stat().st_mtime):
        D.update(pickle.load(open(f, "rb")))
    e1 = D["E1a"]
    order = FACTS["origin_order"]
    rows = []
    for o in [COUNTRY[c] for c in order] + ["LAC9"]:
        x = e1[e1["Origin"] == o].set_index("Sector")
        rows.append([o] + [f"{x.loc[s, 'Exports (US$ billion)']:,.1f}" for s in ("Agriculture", "Mining and fuels", "Manufacturing")]
                    + [f"{x.loc[s, 'MNE share (%)']:.1f}" for s in ("Agriculture", "Mining and fuels", "of which fuels", "Manufacturing", "Total")])
    head = (r" & \multicolumn{3}{c}{Exports (US\$ billion)} & \multicolumn{5}{c}{MNE share of exports (\%)} \\" "\n"
            r"\cmidrule(lr){2-4}\cmidrule(lr){5-9}" "\n"
            r"Country & Agriculture & Mining and fuels & Manufacturing & Agriculture & Mining and fuels & Fuels & Manufacturing & All goods")
    L = [r"\begin{tabular}{lrrrrrrrr}", r"\toprule", head + r" \\", r"\midrule"]
    for i, r in enumerate(rows):
        if i == len(rows) - 1:
            L.append(r"\midrule")
        L.append(" & ".join(r) + r" \\")
    L += [r"\bottomrule", r"\end{tabular}"]
    save_tex("v4_sector", "\n".join(L) + "\n")
    x = e1[e1["Origin"] == "LAC9"].set_index("Sector")
    FACTS["sector"] = {s: {k: float(x.loc[s, k]) for k in x.columns if k != "Origin"} for s in x.index}
    FACTS["sector_by_country"] = {o: {s: float(e1[(e1["Origin"] == o) & (e1["Sector"] == s)]["MNE share (%)"].iloc[0])
                                      for s in ("Agriculture", "Mining and fuels", "Manufacturing")} for o in e1["Origin"].unique()}

    # parent countries: countries of operation and registration jurisdictions apart, with concentration
    H = W.HAVEN_STANDALONE | set(W.HAVEN_SOVEREIGN)
    e = a[ext & (a["parent"] != "")]
    ps = (e.groupby("parent")["value_fob"].sum() / e["value_fob"].sum()).sort_values(ascending=False)
    reg = ps[ps.index.isin(H)]
    opc = ps[~ps.index.isin(H)]
    opn = opc / opc.sum()

    def conc(s):
        return {"hhi": float((s ** 2).sum() * 10000), "eq": float(1 / (s ** 2).sum()), "top1": float(100 * s.iloc[0]),
                "top3": float(100 * s.head(3).sum()), "top5": float(100 * s.head(5).sum()), "n": int((s > 0).sum())}
    FACTS["parents_all"] = conc(ps)
    FACTS["parents_operation"] = conc(opn)
    FACTS["parents_registration_share"] = float(100 * reg.sum())
    FACTS["parents_registration"] = {k: float(100 * v) for k, v in reg.head(8).items()}
    FACTS["parents_operation_top"] = {k: float(100 * v) for k, v in opc.head(12).items()}
    FACTS["parents_operation_top_renorm"] = {k: float(100 * v) for k, v in opn.head(12).items()}
    top_op = opc.head(12)
    top_reg = reg.head(6)
    labels = [N.tex(c) for c in top_op.index] + [N.tex(c) for c in top_reg.index]
    N.fig_hbar_stacked("v4_fig_parents", labels, [np.r_[top_op.values, top_reg.values]], [N.C_EXT], [],
                       xmax=float(np.ceil((ps.max() + 0.04) * 20) / 20), percent=True, gap_after=len(top_op) - 1,
                       xlabel=r"Percent of the agricultural exports of foreign MNEs with a recorded parent")
    rows = []
    for lab, k in (("Herfindahl index (0 to 10,000)", "hhi"), ("Equivalent number of countries", "eq"), (r"Largest country (\%)", "top1"),
                   (r"Three largest (\%)", "top3"), (r"Five largest (\%)", "top5"), ("Parent countries", "n")):
        f = (lambda v: f"{v:,.0f}") if k in ("hhi", "n") else (lambda v: f"{v:.1f}")
        rows.append([lab, f(FACTS["parents_all"][k]), f(FACTS["parents_operation"][k])])
    rows.append([r"Registration jurisdictions (\% of recorded parents)", f"{FACTS['parents_registration_share']:.1f}", ""])
    write_plain("v4_parent_conc", ["", "All recorded parents", "Countries of operation"], rows, colspec="lrr", midrule_before=(len(rows) - 1,))

    # groups: concentration of the exports of foreign MNEs
    a["pkey"] = a["parent_key"].fillna("").astype(str).str.upper().str.strip()
    grp = a["ID_Orbis_DNB"].fillna("").astype(str)
    a["grp"] = np.where(grp != "", grp, np.where(a["pkey"] != "", a["pkey"], a["fid"]))
    ge = a[ext].groupby("grp")["value_fob"].sum().sort_values(ascending=False)
    gs = ge / ge.sum()
    FACTS["groups_ext"] = {"n": int(len(gs)), "top1": float(100 * gs.iloc[0]), "top5": float(100 * gs.head(5).sum()),
                           "top10": float(100 * gs.head(10).sum()), "top20": float(100 * gs.head(20).sum()),
                           "top50": float(100 * gs.head(50).sum()), "hhi": float((gs ** 2).sum() * 10000)}
    gm = a[a["otype"] != "local"].groupby("grp")["value_fob"].sum().sort_values(ascending=False)
    gms = gm / a["value_fob"].sum()
    FACTS["groups_all_mne_of_agro"] = {"top5": float(100 * gms.head(5).sum()), "top10": float(100 * gms.head(10).sum()),
                                       "top20": float(100 * gms.head(20).sum())}
    rows = [[r"Largest group", f"{FACTS['groups_ext']['top1']:.1f}"], [r"Five largest groups", f"{FACTS['groups_ext']['top5']:.1f}"],
            [r"Ten largest groups", f"{FACTS['groups_ext']['top10']:.1f}"], [r"Twenty largest groups", f"{FACTS['groups_ext']['top20']:.1f}"],
            [r"Fifty largest groups", f"{FACTS['groups_ext']['top50']:.1f}"], ["Herfindahl index (0 to 10,000)", f"{FACTS['groups_ext']['hhi']:,.0f}"],
            ["Groups", f"{FACTS['groups_ext']['n']:,}"]]
    write_plain("v4_group_conc", ["", r"Share of the exports of foreign MNEs (\%)"], rows, colspec="lr", midrule_before=(5,))
    json.dump(FACTS, open(FACTS_JSON, "w"), indent=1, default=str)
    print("descriptives done:", {k: FACTS[k] for k in ("parents_all", "parents_operation", "parents_registration_share", "groups_ext")})


# ---------------------------------------------------------------------
# flatten
# ---------------------------------------------------------------------
def flatten() -> None:
    src = SRC.read_text(encoding="utf-8")

    def rep(m):
        p = TEX4.parent.parent / (m.group(1) + ".tex")
        return p.read_text(encoding="utf-8").rstrip("\n")
    out = re.sub(r"\\input\{(tables/v4/[A-Za-z0-9_]+)\}", rep, src)
    assert "\\input{" not in out and "\\includegraphics" not in out, "the note still reads external files"
    NOTE.write_text(out, encoding="utf-8")
    print(f"flattened -> {NOTE}")


def main() -> None:
    which = sys.argv[1:] or ["desc"]
    if "desc" in which:
        desc()
    if "regs" in which:
        regs_exhibits()
    if "flatten" in which:
        flatten()




def regs_exhibits() -> None:
    import wp_agro_v4_exhibits as X
    X.P.SHOWN.clear()
    X.baseline(); X.capital_desc(); X.heterogeneity(); X.location()
    if (OUT4 / "v4_event_B.dta").exists():
        X.events()
    # the exhibits module imports this file as a module: its FACTS and SHOWN are the ones filled
    json.dump(X.P.FACTS, open(FACTS_JSON, "w"), indent=1, default=str)
    json.dump(X.P.SHOWN, open(SHOWN_JSON, "w"), indent=1)
    print(f"regression exhibits done; {len(X.P.SHOWN)} workbook cells printed in the paper")


if __name__ == "__main__":
    main()
