"""
wp_agro_delivery.py  --  arma la carpeta de entrega de una ronda del paper agro (2026-11-28)
==========================================================================================

    python wp_agro_delivery.py            (ronda v6)

Copia en docs/notes/entrega_v6_2026-11-28/ el workbook, el registro de resultados, las figuras y el codigo de las
rondas v4, v5 y v6 (solo scripts: ningun dato, archivo intermedio ni salida), y deja un zip con todo al lado.
Los textos LEEME.md y 3_codigo/README.md se escriben a mano en la carpeta y este script no los toca.
El codigo se copia plano (python/, stata/, config/) para que corra igual que en stylized_facts/: los scripts se
importan entre si y wp_common.py busca config/paths.py una carpeta arriba.
"""
from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = ROOT / "stylized_facts" / "python"
DO = ROOT / "stylized_facts" / "stata"
NOTES = ROOT / "docs" / "notes"
OUT = NOTES / "entrega_v6_2026-11-28"

RESULTS = [NOTES / "WP_paperagro_v6_master_estimates.xlsx", NOTES / "RESULTS_v6_2026-11-27.md"]
FIGURES = NOTES / "figures_v6"

# en el orden en que se corren (el README de 3_codigo explica cada uno)
PY_FILES = [
    "_common.py", "wp_common.py",
    "wp_agro_croptype.py", "wp_agro_capital.py", "wp_agro_classification.py", "wp_agro_paper.py", "wp_agro_note_v3.py",
    "wp_agro_v4_data.py", "wp_agro_v4_est.py", "wp_agro_v4_workbook.py", "wp_agro_v4_exhibits.py", "wp_agro_v4_paper.py",
    "wp_agro_v5_data.py", "wp_agro_v5_data2.py", "wp_agro_v5_est.py", "wp_agro_v5_est2.py", "wp_agro_v5_events.py",
    "wp_agro_v5_match.py", "wp_agro_v5_labels.py", "wp_agro_v5_workbook.py",
    "wp_agro_v6_answers.py", "wp_agro_v6_data.py", "wp_agro_v6_events.py", "wp_agro_v6_est.py", "wp_agro_v6_workbook.py",
]
DO_FILES = ["wp_agro_v4_event.do", "wp_agro_v4_ppml.do", "wp_agro_v5_event.do", "wp_agro_v6_event.do"]
CONFIG = [ROOT / "config" / "paths.py"]

HANDWRITTEN = {OUT / "LEEME.md", OUT / "3_codigo" / "README.md"}


def copy(src: Path, dst_dir: Path) -> None:
    dst_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst_dir / src.name)


def build() -> None:
    for sub in ["1_resultados", "2_figuras", "3_codigo/python", "3_codigo/stata", "3_codigo/config"]:
        d = OUT / sub
        if d.exists():                       # copias de una corrida anterior: se rehacen
            for f in d.iterdir():
                if f.is_file() and f not in HANDWRITTEN:
                    f.unlink()
    for f in RESULTS:
        copy(f, OUT / "1_resultados")
    for f in sorted(FIGURES.iterdir()):
        if f.suffix in (".pdf", ".png"):
            copy(f, OUT / "2_figuras")
    for name in PY_FILES:
        copy(PY / name, OUT / "3_codigo" / "python")
    for name in DO_FILES:
        copy(DO / name, OUT / "3_codigo" / "stata")
    for f in CONFIG:
        copy(f, OUT / "3_codigo" / "config")
    missing = [p for p in HANDWRITTEN if not p.exists()]
    if missing:
        print("faltan los textos escritos a mano:", *missing, sep="\n  ")

    z = OUT.with_suffix(".zip")
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(OUT.rglob("*")):
            if f.is_file():
                zf.write(f, Path(OUT.name) / f.relative_to(OUT))
    n = sum(1 for f in OUT.rglob("*") if f.is_file())
    print(f"{OUT}: {n} archivos; {z.name}: {z.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    build()
