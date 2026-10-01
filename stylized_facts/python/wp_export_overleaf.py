"""
wp_export_overleaf.py -- export each working-paper document as a clean, editable Overleaf project (2026-09-24)
===============================================================================================================

wp_build_overleaf.py writes one build folder per document (output/wp/overleaf_WP_<name>/): a generated main.tex
with every exhibit on a single line, fragments under Graphs/Tables/Regressions, and the LaTeX build files. This
script turns each build into a project meant to be edited by hand:

    docs/overleaf_projects/WP_<name>/
        main.tex                 the whole document; each figure and table spread over several lines, with a
                                 comment line giving its title, so captions and notes are easy to find and edit
        figures/<scope>/*.pdf    only the figures main.tex uses
        tables/<scope>/*.tex     only the tables and regressions main.tex uses
    docs/overleaf_projects/WP_<name>.zip   the same folder zipped (Overleaf: New Project > Upload Project)

<scope> is the sample a fragment was computed on: all (all goods), agro, manufacturing, mining, rest (sectors),
sectors (cross-sector exhibits). The layout changes nothing in the typeset output: every line break inserted
inside a figure or table ends in "%", so the PDF is the same as the build.

    python wp_export_overleaf.py                    -> the six current documents
    python wp_export_overleaf.py paper draft2       -> some of them
    python wp_export_overleaf.py paper --force      -> overwrite a project folder that was edited by hand

Once a project is edited (here or in Overleaf), that copy is the source of the text. A re-export refuses to
overwrite a folder whose .tex files changed since the last export, unless --force is given.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
import zipfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wp_common as W  # noqa: E402

BUILD = W.WP_OUT
OUT = W.ROOT / "docs" / "overleaf_projects"
STATE = OUT / "_export_state.json"
DOCS = ["paper", "paperagro", "draft2", "total", "sectors", "countries"]
TITLES = {"paper": "the working paper", "paperagro": "the agriculture working paper",
          "draft2": "tables and figures, main text and appendix", "total": "reference document: all goods",
          "sectors": "reference document: the four sectors", "countries": "reference document: the nine exporting countries"}
TODAY = date.today().strftime("%Y-%m-%d")

FOLDER = {"Graphs": "figures", "Tables": "tables", "Regressions": "tables"}
BREAK_BEFORE = [r"\begin{minipage}", r"\end{minipage}", r"\includegraphics", r"\caption{", r"\label{", r"\adjustbox{",
                r"\par\vspace", r"\parbox{", r"\textit{Notes:}", r"\textit{Source:}", r"\end{figure}", r"\end{table}"]
RE_BREAK = re.compile("(?=" + "|".join(re.escape(b) for b in BREAK_BEFORE) + ")")
RE_CAPTION = re.compile(r"\\caption\{(.*?)\}\\label")
RE_REF = re.compile(r"(\\includegraphics(?:\[[^\]]*\])?\{|\\input\{)((?:Graphs|Tables|Regressions)/[^}]+)\}")


def tree_md5(folder: Path) -> str:
    h = hashlib.md5()
    for p in sorted(folder.rglob("*.tex")):
        h.update(str(p.relative_to(folder)).encode()); h.update(p.read_bytes())
    return h.hexdigest()


def spread(line: str) -> str:
    """Put a float's pieces on separate lines. Each break ends in '%' and TeX skips leading spaces, so the
    typeset output does not change."""
    parts = [p for p in RE_BREAK.split(line) if p]
    if len(parts) == 1:
        return line
    return "%\n  ".join(parts)


def pretty(tex: str) -> str:
    out = []
    for line in tex.split("\n"):
        if not line:
            out.append(line); continue
        pieces = [p for p in re.split(r"(?=\\begin\{(?:figure|table)\}\[)", line) if p]
        for i, piece in enumerate(pieces):
            if piece.startswith((r"\begin{figure}", r"\begin{table}")):
                kind = "Figure" if piece.startswith(r"\begin{figure}") else "Table"
                m = RE_CAPTION.search(piece)
                if i > 0:
                    out[-1] += "%"          # the float followed something on the same line: keep the join exact
                out.append(f"% ---- {kind}: {m.group(1) if m else ''}")
                out.append(spread(piece))
            elif piece.startswith(r"\section") and r"}\addcontentsline" in piece:
                out.append(piece.replace(r"}\addcontentsline", "}%\n" + r"\addcontentsline", 1))
            else:
                out.append(piece)
    return "\n".join(out)


def header(name: str, built: str) -> str:
    return (f"% Multinational Firms and Trade in Latin America -- WP_{name} ({TITLES[name]})\n"
            f"% Overleaf project exported {TODAY} from the build of {built} (stylized_facts/python/wp_export_overleaf.py).\n"
            "% Compile with pdfLaTeX, the Overleaf default. Figures are in figures/<scope>/ and tables in tables/<scope>/,\n"
            "% where <scope> is the sample: all = all goods; agro, manufacturing, mining, rest = the sectors;\n"
            "% sectors = exhibits that compare the sectors. Each figure and table below starts with a '% ----' line.\n")


def export(name: str, force: bool, state: dict) -> None:
    src = BUILD / f"overleaf_WP_{name}"
    dst = OUT / f"WP_{name}"
    main_src = src / "main.tex"
    if not main_src.exists():
        print(f"   WP_{name}: no build at {src}; run wp_build_overleaf.py {name} first"); return
    if dst.exists():
        if not force and state.get(name) != tree_md5(dst):
            print(f"   WP_{name}: SKIPPED, {dst} was edited since the last export (use --force to overwrite)"); return
        shutil.rmtree(dst)
    dst.mkdir(parents=True)

    tex = main_src.read_text(encoding="utf-8")
    built = date.fromtimestamp(main_src.stat().st_mtime).strftime("%Y-%m-%d")
    copied = {}

    def relink(m: re.Match) -> str:
        old = m.group(2)
        top, rest = old.split("/", 1)
        new = f"{FOLDER[top]}/{rest}"
        f_src = src / (old if old.endswith((".pdf", ".tex")) else old + ".tex")
        f_dst = dst / (new if new.endswith((".pdf", ".tex")) else new + ".tex")
        assert f_src.exists(), f"missing {f_src}"
        assert copied.get(f_dst, f_src) == f_src, f"name clash {f_dst}"
        if f_dst not in copied:
            f_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f_src, f_dst)
            if f_dst.suffix == ".tex":
                body = f_dst.read_text(encoding="utf-8")
                assert not re.search(r"\\(input|include|includegraphics)\b", body), f"nested file in {f_src}"
            copied[f_dst] = f_src
        return m.group(1) + new + "}"

    tex = RE_REF.sub(relink, tex)
    assert not re.search(r"\{(Graphs|Tables|Regressions)/", tex), "unconverted path"
    (dst / "main.tex").write_text(header(name, built) + pretty(tex), encoding="utf-8")

    zpath = OUT / f"WP_{name}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(dst.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(dst))
    state[name] = tree_md5(dst)
    nfig = sum(1 for p in copied if p.suffix == ".pdf")
    print(f"   WP_{name}: {nfig} figures, {len(copied) - nfig} tables -> {dst.relative_to(W.ROOT)}  "
          f"(zip {zpath.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    args = sys.argv[1:]
    force = "--force" in args
    want = [a for a in args if a != "--force"] or DOCS
    OUT.mkdir(parents=True, exist_ok=True)
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    for name in want:
        assert name in DOCS, f"unknown document {name}; choose from {DOCS}"
        export(name, force, state)
    STATE.write_text(json.dumps(state, indent=1))
