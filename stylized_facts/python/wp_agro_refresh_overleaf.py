"""
wp_agro_refresh_overleaf.py  --  refresh the exhibits of the hand-edited agriculture paper (2026-10-02)
======================================================================================================

docs/overleaf_projects/WP_paperagro/ is edited by hand, so wp_build_overleaf.py no longer writes it. This script
replaces only its exhibit files: every table and figure that main.tex uses is copied again from a wp output folder
(default: output/wp_2012_2018/agro, the 2012--2018 run), with the same relabelling the builder applies
(fragment note removed, internal labels replaced by D2_RELABEL) plus the paper's own label edits below.
main.tex is never touched.

    WP_YEARS=2012-2018 python wp_run_all.py 0 1a 1b 1cd 1e 1f 2 3   (then wp_agro_paper.py)
    python wp_agro_refresh_overleaf.py [source_folder]
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_common as W  # noqa: E402
import wp_build_overleaf as B  # noqa: E402

SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else W.OUTPUT / "wp_2012_2018" / "agro"
DST = W.ROOT / "docs" / "overleaf_projects" / "WP_paperagro"

# label edits made for this paper on top of D2_RELABEL (products instead of HS6, local firms instead of non-MNE)
PAPER_RELABEL = [
    ("& HS6 products & Value", "& Products & Value"),
    (r"HS6 & Description & \$bn/yr", r"Product code & Description & US\$bn/yr"),
    ("Sub-sector &", "SITC division &"),
    (r"Panel A: composition of the origin's exports in the scope, \% (columns sum to 100)",
     "Panel A. Percent of the country's agricultural exports (columns add to 100)"),
    (r"Panel B: foreign-MNE share of export value within the cell, \%",
     r"Panel B. Foreign-MNE share of the division's exports in the country (\%)"),
    ("All sub-sectors &", "All divisions &"),
    ("ln exports, non-MNE firms", "ln exports, local firms"),
    ("$\\ln$ exports, non-MNE firms", "$\\ln$ exports, local firms"),
    ("HS6 product lines", "Products"),
    ("HS6 lines", "Products"),
]


def table_body(name: str) -> str:
    for kind in ("Tables", "Regressions"):
        p = SRC / kind / f"{name}.tex"
        if p.exists():
            body, _ = B.split_note(B.sanitize(p.read_text(encoding="utf-8")))
            body = B.d2_relabel(body)
            for a, b in PAPER_RELABEL:
                body = body.replace(a, b)
            return body
    raise FileNotFoundError(f"{name}.tex not in {SRC}")


def main() -> None:
    tex = (DST / "main.tex").read_text(encoding="utf-8")
    tabs = sorted(set(re.findall(r"\\input\{tables/agro/([^}]+)\}", tex)))
    figs = sorted(set(re.findall(r"\{figures/agro/([^}]+)\.pdf\}", tex)))
    for t in tabs:
        body = table_body(t)
        left = [w for w in ("HS6", "non-MNE", "scope") if w in body]
        (DST / "tables" / "agro" / f"{t}.tex").write_text(body, encoding="utf-8")
        if left:
            print(f"   check {t}: still contains {left}")
    for f in figs:
        shutil.copy2(SRC / "Graphs" / f"{f}.pdf", DST / "figures" / "agro" / f"{f}.pdf")
    used = {f"{t}.tex" for t in tabs} | {f"{f}.pdf" for f in figs}
    stale = [p.name for d in ("tables", "figures") for p in (DST / d / "agro").iterdir() if p.name not in used]
    print(f"   refreshed {len(tabs)} tables and {len(figs)} figures from {SRC}")
    if stale:
        print("   files not used by main.tex:", ", ".join(stale))


if __name__ == "__main__":
    main()
