# Overleaf projects

One folder per document, ready to edit or upload to Overleaf. Each folder has:

- `main.tex`: the whole document. Each figure and table sits on several lines and starts with a `% ---- Figure:` or `% ---- Table:` comment that gives its title.
- `figures/<scope>/`: the figures `main.tex` uses.
- `tables/<scope>/`: the tables and regressions `main.tex` uses.

`<scope>` is the sample the exhibit was computed on:
- `all` covers all goods;
- `agro`, `manufacturing`, `mining` and `rest` are the four sectors;
- `sectors` holds the exhibits that compare the sectors.

| Folder | Document |
|---|---|
| `WP_paper` | the working paper |
| `WP_paperagro` | the agriculture working paper |
| `WP_draft2` | tables and figures, with the main text and the appendix as separate parts |
| `WP_total` | reference document for all goods (every exhibit) |
| `WP_sectors` | reference document for the four sectors (every exhibit) |
| `WP_countries` | reference document for the nine exporting countries (every exhibit) |

**To upload:** in Overleaf, go to New Project > Upload Project and choose `WP_<name>.zip`. Compile with pdfLaTeX, which is the default.

**To rebuild after a script changes a number or a figure,** run these from `stylized_facts/python`:

1. `python wp_build_overleaf.py <name>`
2. `python wp_export_overleaf.py <name>`

The export changes nothing in the output. A project compiled from these folders gives the same PDF as `docs/WP_<name>_<date>.pdf`: same page count and same text on every page, checked on 2026-09-24.

Once `main.tex` or a table is edited by hand, the edited copy becomes the source of the text. From then on, `wp_export_overleaf.py` refuses to overwrite that folder unless you pass `--force`. `_export_state.json` stores the checksums it uses for that check.
