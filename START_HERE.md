# START HERE — Multinational Firms and Trade in Latin America (empirics)

**Folder:** `C:\Sebas BID\Orbis_DNB_Customs_Final\` — git repo, remote `github.com/jsvp97/IADB_Orbis_DNB_Customs_Final` (private).
**Owner:** Sebastián Velásquez Palacios (IDB). Coauthors: Christian Volpe Martincus (IDB), Ignacio Marra de Artiñano (ULB & ECARES), Gabriel Scattolo (IDB).
**Set up for continued work on:** 2026-09-03.

This is the ONE folder to work from for the empirical side of the project. The old
working folder `C:\Sebas BID\Orbis_DNB_Customs\` now only matters for the big data files
(20–48 GB each) that cannot live in a repo; everything else useful was brought here.

---

## What this project is

Ten Latin American customs datasets (firm × HS6 product × destination × year, 2006–2022)
matched to Orbis and Dun & Bradstreet so that every exporter is classified as a foreign
multinational affiliate, a domestic multinational, or an independent local firm. On top of
that match sit (a) a set of **stylized facts** about multinationals and trade and (b) a
**theory paper** (separate folder, `..\Orbis_DNB_Customs_Model\`).

## What we are doing next

A **working paper on the stylized facts**, built from the July-2026 document
`docs/stylized_facts_document/Multinational_Firms_and_Trade_2026-07-29.pdf`, extended
along Christian Volpe's agenda (parent-country breakdowns, more product-complexity
measures, parent × destination tables and heat maps, headquarters vs affiliates,
HS6-level shares) **and an agriculture-focused version**. The full plan, item by item,
with the script and data each item needs, is in **`docs/WORKPLAN_working_paper.md`**.

## Read in this order

| # | File | Why |
|---|---|---|
| 1 | this file | orientation |
| 2 | `docs/WORKPLAN_working_paper.md` | the agenda, mapped to code and data |
| 3 | `CLAUDE.md` | technical spec: every script, every input, every column that matters, the traps |
| 4 | `stylized_facts/README.md` | the stylized-facts pipeline (Ignacio's code): figure → script → cache |
| 5 | `docs/stylized_facts_document/Multinational_Firms_and_Trade_2026-07-29.pdf` | the document the WP starts from |
| 6 | `README.md` + `data/README.md` | the matching pipeline (scripts 01–08) and the data guide, written for GitHub readers |
| 7 | `C:\Sebas BID\_Brain\P3_MNE_Trade_Model.md` | project brain: status, decisions, dead results. Authoritative on STATUS. |

## Folder map

```
Orbis_DNB_Customs_Final/
├── START_HERE.md                ← you are here
├── CLAUDE.md                    ← technical spec for this folder (scripts, inputs, columns, traps)
├── README.md                    ← GitHub-facing description of the matching + analysis pipeline
├── config/
│   ├── paths.do                 ← EVERY machine-specific path for Stata, in one place
│   └── paths.py                 ← the same for Python
├── src/                         ← Sebastián's pipeline, numbered in run order
│   ├── 00–04   matching (Stata + Python fuzzy match + AI review)
│   ├── 05–08   descriptive stats, main analysis, agro analysis, agro policy report
│   ├── 09–14   destination of MNE exports, conduit/ultimate parent, Fact-5 FE test, Cov(θ,S)
│   └── helpers/  small utilities (WITS RCA download). NB: never name a folder `aux`, `con`, `nul`, `prn` — Windows reserved names, git cannot open them
├── stylized_facts/              ← Ignacio's pipeline behind the July-2026 document
│   ├── README.md                ← figure/table → script → inputs → outputs; how to run it HERE
│   ├── stata/                   ← 00_master, 01_setup, 10–40 (Part-0 build, determinants, effects, summary)
│   └── python/                  ← sf1…sf6 (the six facts), nsf_* (network facts), sf_explore_* (exploration)
├── docs/
│   ├── WORKPLAN_working_paper.md        ← Volpe's agenda → where to add code
│   ├── stylized_facts_document/         ← the July-2026 PDF (source .tex lives in Ignacio's Overleaf)
│   ├── exploration_2026-05/             ← Sebastián's May-2026 exploration document (.tex)
│   └── agro/                            ← March-2026 agro results PDF
├── data/
│   ├── README.md                ← data guide (+ §10 "where the files live on this machine")
│   ├── raw/                     ← the SMALL inputs, copied here (product characteristics, gravity, concordances…)
│   └── intermediate/v4_cubes/   ← the four aggregate cubes collapsed_{oy,ody,opy,odpy}.dta (456 MB, copied);
│                                   the firm-level cubes (13 GB each) stay in ..\Orbis_DNB_Customs\Claude\Data\Intermediate_v4
├── output/                      ← not in git
│   ├── tables/                  ← cubes + CSVs produced by scripts 09–14 (see CLAUDE.md §4.3)
│   ├── legacy_v4_2026-05/       ← Sebastián's May-2026 figures/regressions (the exploration document's exhibits)
│   ├── agro_legacy/             ← March-2026 agro figures, tables, policy-report exhibits
│   └── logs/
└── archive/                     ← not in git; nothing here is needed to run anything
    ├── README.md                ← manifest: what each legacy file is and where its logic lives now
    ├── legacy_dofiles/          ← the pre-repo .do/.py files from ..\Orbis_DNB_Customs
    ├── legacy_outputs/          ← two descriptive-stats workbooks
    └── Github_nested_clone_redundant_2026-09-03/   ← see "Git" below; safe to delete
```

## Tools on this machine (verified 2026-09-03)

- Stata 18 MP at `C:\Program Files\Stata18\StataMP-64.exe` (batch mode: `/e do script.do`).
- Python 3.10.11 with pandas 2.1.4, pyarrow 23, pyreadstat, statsmodels 0.14.6, matplotlib 3.10, **pyfixest 0.50.1**.
- MiKTeX (pdflatex) installed.
- Disk C: had 103 GB free. The two largest inputs (20 GB base, 48 GB Orbis/D&B merge) stay where they are.

## Git — state after the 2026-09-03 reorganisation

- The outer folder's `main` now **is** GitHub's `main` (commit `249c6e4`) and tracks `origin/main`.
  The previous local-only, diverged history is preserved under the tag
  `archive-outer-local-history-2026-09-03` (same file contents, different commits).
- The nested `Github/` clone that used to be the "true" repo is redundant and was moved to
  `archive/Github_nested_clone_redundant_2026-09-03/`. Delete it when convenient.
- Everything added on 2026-09-03 (`stylized_facts/`, `config/`, `docs/`, `CLAUDE.md`,
  this file, the README structure block, the `.gitignore` additions) was committed and
  pushed the same day. Data files are gitignored by extension, so a plain `git add -A`
  picks up code and documentation only. Commit and push from THIS folder.

## The three traps a newcomer hits first

1. **Two MNE conventions coexist.** `src/05–14` count a matched firm with no recorded
   parent country as *neither* foreign nor domestic (it is only in `MNE_total`).
   The stylized-facts pipeline (post-2026-05-23) counts it as **foreign**
   (`MNE_ext = MNE_total − MNE_dom`) and **drops Ecuador** (nine origins). Numbers from
   the two pipelines are not directly comparable. Details in `CLAUDE.md` §3.
2. **Ignacio's code points at his machine** (`D:\MNEs_Trade`, parquet copies of the
   base, an Overleaf folder in his Dropbox). Nothing in `stylized_facts/` runs here until
   the paths in `stata/01_setup.do` and `python/_common.py` are redirected — see
   `stylized_facts/README.md` §4. Do not edit his files blindly; the plan there says
   exactly which lines.
3. **Read the 20 GB base once, keep a cube.** Every fact in the document is computed
   from a small cube built in one chunked pass over the base. Volpe's new items (parent ×
   destination × product) need ONE new cube — `docs/WORKPLAN_working_paper.md` §0
   specifies it. Do not write six scripts that each re-read 20 GB.
