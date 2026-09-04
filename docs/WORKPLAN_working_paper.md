# Work plan — working paper on the stylized facts (+ agriculture version)

**Source of the agenda:** Christian Volpe's comments, September 2026 (transcribed by
Sebastián). **Starting document:** `stylized_facts_document/Multinational_Firms_and_Trade_2026-07-29.pdf`
(six facts, 15 pp). **Status of every item below: NOT STARTED (2026-09-03).** This file
says, for each item, what it means, which data it needs, which script it plugs into, and
what must be decided. Update the status column as work lands; move decisions to the brain
(`C:\Sebas BID\_Brain\P3_MNE_Trade_Model.md`, decision log).

Numbering follows Volpe's note: **1** = the WP on the stylized facts, items 1a–1f;
**2** = the agriculture focus.

---

## 0. Do this first — ONE new cube that serves 1a, 1c, 1d, 1f and 2

Every exhibit in the document is a collapse of a small cache built by one pass over the
20.6 GB base. The new items all need the **parent country** next to origin, destination
and product, which no existing cube has (`collapsed_odpy` has no parent;
`mne_export_destination_cube` has no product). Build once:

```
odpy_parent_cube :  country_orig × country_dest × hs07_6d × year × owner_iso3 × owner_type
                    value_fob (sum), n_firms (distinct Tax_ID), n_rows
  owner_iso3 :  iso3_parent  (as recorded)  — keep a second column with the first-NON-conduit
                ultimate owner from src/11-12 logic (ucp) so item 1c/1d can be shown both ways
  owner_type :  "local" (unmatched) | "dom" (parent == origin) | "ext" (parent != origin, known)
                | "ext_unknown" (matched, no parent country)  → lets EITHER MNE convention be
                recomposed downstream (CLAUDE.md §3)
```

Expected size: a few million rows (ODPY alone is 1.5 M; parents add < ×3), well under 1 GB.
Templates: Stata `src/09_mne_export_destinations_build.do` (add `hs07_6d` and the
Tax_ID count; ~40 min) or Python `stylized_facts/python/sf3_odpy_regressions.py` lines
~80–100 (chunked accumulate; needs the base as parquet or a pyreadstat chunk reader — see
`stylized_facts/README.md` §4). Write it as `src/15_odpy_parent_cube_build.do` (or
`stylized_facts/python/wp0_build_odpy_parent_cube.py`) and save to
`data/intermediate/odpy_parent_cube.dta/.parquet`. Every item below then reads it.

Also decide up front (one line in the brain when decided):

- **Which MNE convention the WP uses** — `src/` (unknown-parent firms are neither foreign
  nor domestic; ten origins) or Ignacio's (unknown-parent = foreign; nine origins, ECU
  out). The document is on Ignacio's. Recommendation: keep the document's convention for
  continuity, but report the unknown-parent mass explicitly in every parent-country
  exhibit and add a robustness footnote on the alternative.
- **Whether parent = recorded `iso3_parent` or the first-non-conduit ultimate owner**
  (src/12 concept 3). Headline shares barely move (θ_USA 0.134 → 0.136; GBR → AUS is the
  one big reallocation, 52.5 bn). Recommendation: recorded parent in the main text,
  non-conduit in a robustness table, and never the naive GUO chain.

## 1. The working paper on the stylized facts

### 1a. Figures by main parent countries (USA, China, …) — "look at everything through the origin-share figure"

| | |
|---|---|
| Meaning | Redo Figure 1 (share by origin), Figure 2 (by PCI quintile), Figure 3 (by Lall category) — and optionally 5/6 — with the foreign-MNE bar **split by the parent's country**: USA, GBR, CAN, NLD, DEU, JPN, BRA, CHN, ESP, FRA, Other (top of Figure 4; check whether CHN is even in the top 15 — it was not in July). |
| Data | the §0 cube. Interim (origin level only): `output/tables/mne_export_destination_cube.dta` already gives Figure 1 by parent. |
| Code | `stylized_facts/python/sf1_origin.py` (stacked bars per origin) and `sf3_products.py` (bars per bucket) — add a `by_parent=True` variant that stacks `owner_iso3` groups instead of {ext, dom}. Palette: one colour per top parent, gray for Other, hatched for unknown-parent. |
| Decide | how many parents (5? 8?); whether unknown-parent is its own segment (recommended: yes, hatched) or dropped as in Figure 4. |
| Status | not started |

### 1b. Figure 2 — other product-complexity variants; substitution elasticities (Fontagné, Guimbard & Orefice 2022, JIE 137)

| | |
|---|---|
| Meaning | Volpe's hypothesis: more substitutable (higher σ) = less complex; the foreign-MNE share should fall with σ. Show Figure 2 with alternative sophistication measures. |
| Already available | `sf3_products.py` produces appendix quintile figures for `sigma` (Broda–Weinstein, in `product_characteristics_hs6_2002_adj.dta`), `upstreamness`, `quality_ladder`, `rhci`; `sf3_odpy_regressions.py` runs PCI + upstreamness. |
| To add | FGO (2022) HS6 tariff-based elasticities — **download** from CEPII ("Product-Level Trade Elasticities" database; HS6, check the HS revision on download and map to HS2007 with `data/raw/Concordance_HS_2007_2002_WITS.dta` if needed) → `data/raw/FGO2022_trade_elasticities_hs6.dta` (`$f_fgo` in `config/paths.do`). Merge in `sf3_products.py` (characteristics block, ~lines 90–110; add to `CHARS`) and in `stata/10_part0_build.do` §0.5. Produce `fig_sf3_fgo_quintile` and add `sigma_fgo` as a column in the A.4 ladder. Interpretation: a negative gradient in σ mirrors the positive one in PCI. |
| Status | not started; data not on disk |

### 1c. Two-way tables: parent country × export destination (value and % of value), region level then country level

| | |
|---|---|
| Meaning | Beyond the regressions, Volpe wants to SEE the matrix: rows = parent country (or region) of the MNE, columns = destination country (or region); cells = export value and share (row %, column %, and share of total — decide which; recommendation: all three as separate panels or an appendix). |
| Data | `output/tables/mne_export_destination_cube.dta` (origin × dest × year × iso3_parent, 201,847 rows) — sufficient; use `mne_ucp_cube.dta` for the non-conduit variant. Region maps: destination regions in `src/06` §0.7 (`dest_region_num`: LAC / NAM / EU / Asia / …) and in `stylized_facts/python/sf_explore_dest.py`; parent regions in `src/08` (Figure 7) and `src/06` §1.4. |
| Code | new `src/15_parent_by_destination_tables.do` or `stylized_facts/python/wp1_parent_x_destination.py`. Outputs: `tab_wp_parent_x_dest_region_{value,rowpct,colpct}.tex`, `…_country_top20x20…`. Pooled over origins and years; also one panel per LAC origin (Volpe reads origin splits — SLV/DOM/CRI ship home, ARG/CHL/PER do not; brain §2). |
| Status | not started |

### 1d. Heat map: main parent countries × main destinations

| | |
|---|---|
| Meaning | the 1c matrix as a colour map (top ~15 parents × top ~15 destinations, cell = share of that parent's exports going to that destination, annotated). |
| Code | same data as 1c; heat-map code to reuse: `stylized_facts/python/sf_explore_dest_by_origin.py` (matplotlib `imshow` + annotations). One map for recorded parent, one for non-conduit owner; one for value shares, one for the "to parent's own country" diagonal highlighted. |
| Status | not started |

### 1e. Headquarters, not only affiliates; "test MNE quantity"

| | |
|---|---|
| Meaning — two readings, confirm with Volpe | (i) In the presence regressions (Fact 6, Table 2), distinguish MNEs present at the destination **through their headquarters** from those present **through an affiliate** — Table A.9 already does this in the appendix (`sf5_distance.py`, groups `g_hq`/`g_aff`, built at lines 105–176); promote it and extend it to the Fact 5 regressions (`sf4_presence.py`). (ii) Look at the **exporter itself being an HQ** (a LAC-headquartered group exporting from home) versus an affiliate exporting: identify with `subsidiarybvdid == guo25` (Orbis) or `dunsnumber == globalultimatedunsnumber` (D&B); a domestic MNE (`MNE_dom`) is by construction HQ-or-domestic-affiliate. |
| "MNE cantidad" | use the **number** of MNEs (and separately the number of HQ-present vs affiliate-present MNEs) as the presence regressor. Table 1 already uses ln(# MNE firms) as the intensive margin; add counts by presence type. Fields: `n_mne`, `n_mne_ext`, `n_mne_dom` in `collapsed_odpy`; HQ/affiliate presence needs `intermediate_mne_presence.dta` (2 GB, `Intermediate_v4`) or Ignacio's `sf4_aff_pairs_matched.parquet` (group id × destination presence). |
| Also | the model's Fact-6 prediction is exactly here: attenuation should survive at the affiliate level and weaken at the **parent** level (cannibalisation) — brain §5. A parent-level rerun of Table 2 is cheap once the FDPY cache exists. |
| Status | not started |

### 1f. Product level: HS6 export shares, with descriptions

| | |
|---|---|
| Meaning | tables of the MNE (foreign / domestic / by parent) share of exports **by HS6 product**, with the product description, so the reader can see WHICH goods multinationals export (top-N by value; by origin; by parent). |
| Data | `data/intermediate/v4_cubes/collapsed_opy.dta` (origin × HS6 × year, has `mne_ext_value`, `mne_dom_value`, `total_value`) for the foreign/domestic split; the §0 cube for the by-parent version. Descriptions: `data/raw/JobID-46_Concordance_H3_to_H2.CSV` ("HS 2007 Product Description"), also `hs6_description` in `lall2000_hs2007.dta` and `hs2007productdescription` in `product_characteristics_hs6_2002_adj.dta`. |
| Code | `stylized_facts/python/sf3_products.py` has `fig_sf3_top15_hs2_<def>` (HS2 chapters); add `tab_wp_top_hs6_<def>` (top 30 HS6 by value with share and description) and a value-weighted distribution of the HS6-level foreign share (histogram / Lorenz: what fraction of export value sits in products where foreign MNEs hold > 50 %, > 80 %). `nsf_product_conc.py` already computes product-level HHI naive vs grouped — reuse its `(hs, country, Tax_ID)` cache. |
| Status | not started |

### Cross-cutting for the WP

- **Fact 5 must use the dest×product×year FE result** (survives at half size: 0.087 / 0.061 /
  PPML +0.229 — `src/13`, `output/tables/fact5_dpy_fe.tex`). The July document's Table 1 does
  not have that column; add it.
- **Fact 3 (Figure 4) text**: GBR > USA is largely LSE-listed miners (genuine GBR
  ownership); conduits (PAN, BMU, IRL, NLD, CHE ≈ 11 %) and the unknown-parent half must
  be stated. Non-conduit robustness from `src/12` (`V2_owner_shares_three_concepts.csv`).
- **Destination fact** (not in the July document): only 9.2 % of foreign-MNE exports go to
  the parent's country; affiliates are less US-oriented than locals (13.9 % vs 25.0 %);
  θ_USA = 0.134 with a sharp origin split (SLV 0.40, DOM 0.30, CRI 0.28 vs ARG/CHL/PER
  ≈ 0.06). Tables `T2–T5` in `output/tables/`. Natural home: right after Fact 3, and it is
  what 1c/1d visualise.
- Skeleton for the WP `.tex`: the document's six sections + the destination section +
  the agro section; appendix A.3–A.9 already exist as fragments in Ignacio's Overleaf.
  Decide whether the WP is written in Ignacio's Overleaf project or in a new one — if new,
  copy the fragments; the code writes `.tex` fragments by name (§2 of
  `stylized_facts/README.md`), so `\input{}` paths are the only coupling.

## 2. Agriculture focus — an agro-only version and a four-sector version

### 2.1 What exists

- `src/07_agro_trade_analysis.do`: `src/06` restricted to HS2 01–24, plus §1.5 "agro section
  deep-dive" (HS sections I–IV: live animals 01–05, vegetable 06–14, fats 15, prepared
  foods/beverages/tobacco 16–24). Outputs (March–April 2026) in `output/agro_legacy/`.
- `src/08_agro_policy_report.do`: 9 figures + 2 tables (country snapshot, section
  breakdown, destination profile, parent region, US- and EU-destined exports, firm size).
  Exhibits in `output/agro_legacy/PolicyReport/`. Results write-up:
  `docs/agro/MNE_Trade_Agro_Analysis_Results_2026-03.pdf`.
- Literature review on FDI/MNEs in agriculture and D&B agro-firm extracts (10 countries):
  `C:\Sebas BID\Agriculture Multinationals Exports\` (not copied; `.docx` + two `.dta`).

### 2.2 Two versions

| Version | Definition | How |
|---|---|---|
| **Agro only** | HS2 01–24 (as `src/07`) | Python: add `SECTOR = "agro"` → `hs2 in 1..24` filter inside every chunked read in `stylized_facts/python/*` (one helper in `_common.py`, applied where `hs07_6d` is read; scripts that read caches need sector-specific cache names, e.g. `opy_value_cache_agro.parquet`) and a parallel output tree. The §0 cube already carries `hs07_6d`, so all WP items 1a–1f come for free at the agro cut. |
| **Four sectors** | agriculture / mining / manufacturing / services | **Services are not in customs merchandise data** — flag this to Volpe; the only service-like information is the affiliate's NAICS (`naics_aff_2` = 5x) for firms that ALSO export goods. For goods: agriculture HS 01–24; mining & fuels HS 25–27 (decide on ores 26 and precious metals 71 — recommendation: 25–27 + 71–81 metals as "extractive" with a robustness split); manufacturing = the rest. Alternative: Lall (2000) categories (`lall2000_hs2007.dta`: primary / resource-based agro / resource-based other / low / medium / high tech), already used in Figure 3, which sidesteps the HS-range decision. |

### 2.3 Sub-classifications inside agriculture (Volpe: final-consumption goods vs agro inputs; "VEC"; SITC or NAICS)

| Classification | What it gives | On disk? | Where to merge |
|---|---|---|---|
| HS sections I–IV | 4 broad groups (already in `src/07` §1.5) | yes (from `hs2`) | — |
| **BEC** (UN Broad Economic Categories, Rev. 4/5) | **final consumption vs intermediate inputs vs capital goods** — this is what "productos de consumo final / insumos agro" describes. *"VEC" in the notes is almost certainly BEC* — confirm with Volpe. | **no** — download the HS2007↔BEC Rev.4 correspondence (UNSD classifications registry or WITS product concordances) → `data/raw/HS2007_to_BEC.dta` (`$f_bec`) | new merge in `_common.py`/`10_part0_build.do` §0.5, keyed on `hs07_6d` |
| Upstreamness (Antràs–Chor) | continuous input-vs-final position; already in `product_characteristics_hs6_2002_adj.dta` and used in A.4 | yes | already merged |
| Lall (2000) agro-based | "Resource-based manufactures: agro-based" vs "Primary products" | yes (`lall2000_hs2007.dta`) | already merged |
| **SITC Rev. 3** | sections 0 food & live animals, 1 beverages & tobacco, 2 crude materials (incl. 22 oilseeds, 26 fibres), 4 animal & vegetable oils; 3-digit groups for sub-sectors | yes: `data/raw/HS_2007_to_SITC3.dta` (5,050 HS6 → SITC3 with descriptions), `Lall_2000_SITC3.xls` | merge on `hs07_6d` |
| **NAICS** | 111 crop production, 112 animal production, 113 forestry, 114 fishing, 311 food manufacturing, 312 beverages & tobacco, 3253 fertilizers/agrochemicals (inputs) | yes: `data/raw/HS6_to_NAICS_2017.dta` (`naics`, `hs6`) — note the affiliate's own NAICS is also in the base (`naics_aff_6`) | merge on `hs07_6d` (product) or use `naics_aff_6` (firm) |
| Agro inputs vs outputs | fertilizers HS 31, pesticides 3808, agricultural machinery 8432–8436, seeds 1209, animal feed 2301–2309 | yes (HS ranges) | a hand-made `agro_input` flag; cross-check against BEC |

Recommendation: main text with BEC (consumption / intermediate / capital) × HS section;
appendix with SITC 3-digit and NAICS 3-digit; a separate "agro inputs" flag for the policy
angle (Volpe's fertiliser interest — see also `C:\Sebas BID\Agricultura fertilizantes Peru\`).

### 2.4 Order of work for the agro version

1. §0 cube (carries `hs07_6d`, so the agro cut is a filter).
2. Download BEC; build `agro_class.dta` = `hs07_6d` → {HS section, BEC, SITC3, NAICS, agro_input}.
3. Re-run the six facts at the agro cut (Python, `SECTOR="agro"`); add the sub-sector
   splits of Figures 1–4 and of Table 1.
4. Four-sector comparison table (shares, top parents, destination mix per sector).
5. Only then the agro text.

---

## 3. Housekeeping to do alongside (small, do when touching the files)

- Point `src/09–14` at `config/paths.do` instead of their hard-coded paths.
- Tabulate `_merge_DNB_Orbis` × `_merge_final_review` once (value-weighted) and record the
  result in `CLAUDE.md` §3 — it decides how comparable the two pipelines are.
- `src/06` lacks two June-2026 additions that exist only in
  `archive/legacy_dofiles/MNE_Trade_Analysis_corrected_v4_final.do`: §0.8.1 merge of parent
  network size (`total_affiliates`, `n_countries`, `n_sectors` from
  `Merge_DNB_Orbis_parent_total_PostIA_v2.dta`) and the IV-spec ladder limits. Port them if
  the network-size regressions (Table A.6) are to be reproduced in Stata; Ignacio's
  `build_network_size.py` is the Python equivalent.
- Delete `archive/Github_nested_clone_redundant_2026-09-03/` once you are sure nothing is
  missing from the outer repo (`git log` shows `249c6e4` at the top).
- `README_txt.txt` in the root is a tracked duplicate of `README.md` — drop it from git or
  say what it is for.
