"""
wp_agro_v6_answers.py  --  V6-01 of especificaciones_estimaciones_v6_2026-11-25.md: answers to the sixteen definition questions
==============================================================================================================================

Read by wp_agro_v6_workbook.py (sheet 10.1 Definitions and answers). Each answer cites the script and line that supports it
(line numbers as of commit e8f4b2f, 2026-11-25). Counts were computed on 2026-11-27 from the v5 panels.
"""

ANSWERS = [
    (1, "Rule 'two years with exports before t0' (g_ps)",
     "Any two years before t0, not necessarily the two immediately preceding ones. Exports of all firms (X > 0), not only local "
     "firms. npre counts the years before t0 with X > 0; the treated need npre >= 2; each never treated cell needs two years with "
     "X > 0 before its pseudo t0.",
     "wp_agro_v5_events.py lines 125-134 (npre), 146 (g_ps)"),
    (2, "Cohort 2013 and cells with an MNE in 2012",
     "Cells with the first MNE in 2012 are excluded from every sample (neither treated nor never treated). Cohort 2013 is treated "
     "by definition (t0 >= 2013) but cannot meet the two-year rule (only 2012 is before it), so it drops out of g_v4, g_ps and "
     "g_pre3; it enters only in g_nc (no rule). With Callaway and Sant'Anna 'not yet treated', later cohorts of the same sample "
     "serve as controls until they are treated; cells with an MNE in 2012 never do.",
     "wp_agro_v5_events.py lines 136-147"),
    (3, "Pseudo-year of the controls",
     "Confirmed: the pseudo-year only filters. In the estimation every control has gvar = 0 and is compared with every cohort, in "
     "every estimator, in the stacked regression (each stack takes all controls) and in the rows by cohort (gvar == c | gvar == 0). "
     "Controls lost by the draw: 746 -> 509 in product cells (237, 32 percent); 13,648 -> 8,747 in destination cells (4,901). "
     "Only seed 20261124 was used; no other seed was tried.",
     "wp_agro_v5_events.py lines 139-146; wp_agro_v5_event.do lines 48-66 (setev), 155 (stacks), 497 (cohorts)"),
    (4, "csdid control groups, origin x year, pre-period coefficients",
     "Row 'Callaway and Sant'Anna' = csdid option notyet (not yet treated plus never treated); row 'never treated' = option never "
     "(rerun as block csnev because csdid 2.0.3 ignores the default). Origin x year: csdid has no fixed effects and no covariates "
     "here, so it does NOT control for origin x year (the label 'Cell and origin x year' was wrong for it). Sun and Abraham absorbs "
     "cell and origin x year; BJS uses fe(cell origin-year); dCDH uses trends_nonparam(origin), i.e. origin-specific year effects. "
     "csdid pre-period coefficients use its default varying base: period-to-period differences, not long differences to -1.",
     "wp_agro_v5_event.do lines 186-189 (csdid), 219 (SA), 251 (BJS), 276 (dCDH)"),
    (5, "Stacked estimator of v5",
     "The cell and origin x year fixed effects are interacted with the stack (a#stack). Each stack has the treated of its cohort and "
     "the never treated only (gvar == g | gvar == 0); not yet treated cells do not enter as controls. Window g - 4 to g + 4.",
     "wp_agro_v5_event.do lines 145-170"),
    (6, "Definition of new, exiting and surviving local exporters",
     "NEWL: local firms whose first year with exports in the cell is t, looking back to 2012 (the first observed year); missing in "
     "2012. In destination cells the cell is origin x destination x product, so 'new' means new in the destination for that product. "
     "EXITL: local firms that export in the cell in t - 1 and not in t. SURVL = 1 - EXITL / NL(t - 1), only when NL(t - 1) > 0.",
     "wp_agro_v5_events.py lines 64-77, 105"),
    (7, "Cells E",
     "Universe: odp cells with positive exports in at least one year 2012-2018 (the B panel), whose op cell is in g_ps. Kept only if "
     "local exports are zero in every year before t0 of the op cell (controls: before the pseudo t0). Controls: odp cells of never "
     "treated op cells under g_ps. The 1,289 treated cells belong to 345 op cells; the 438 controls to 209.",
     "wp_agro_v5_events.py lines 201-213"),
    (8, "'MNE still there next year' in the 2018 cohort",
     "The 2018 cohort is excluded from the treated (t0 <= 2017); controls are unchanged.", "wp_agro_v5_events.py line 164"),
    (9, "'First foreign MNE' with the main rule",
     "Yes: the controls of g_forps are the g_ps controls, cells with no MNE at all (509 in product cells).",
     "wp_agro_v5_event.do lines 503-508"),
    (10, "Conversion to HS 2017",
     "Each row is read in the HS revision of its origin and year. A code that UNSD links to one HS 2017 code takes it. A code split "
     "into several HS 2017 codes keeps the same code number when it is among them, otherwise takes the HS 2017 code with the largest "
     "exports among origins that report in HS 2017. Several old codes that merge all take the common HS 2017 code. The reported "
     "code is kept (hs_reported) and the rule applied to each code is in hs2017_map (column how), but no indicator was stored in the "
     "panels; v6 adds hs_n1 (non-one-to-one HS 2017 <-> HS 2012).",
     "wp_common.py lines 505-554"),
    (11, "Exporter class (foreign MNE, domestic MNE, local)",
     "Fixed over time. The class comes from the firm-level match (Tax_ID to Orbis or D&B) and the parent country, with no "
     "acquisition date: no firm changes class across years (0 of the firms in the agricultural rows).",
     "wp_agro_v4 sector cache (column ot); checked 2026-11-27"),
    (12, "Universe for defining a new exporter",
     "The whole customs data of the base can be looked at: the firm rows cover all HS chapters (01 to 98), not only 01 to 24. "
     "NEWL_denovo in v6 uses all chapters, 2012 onward.", "data/intermediate/wp/v4/sector.parquet (hs2 0 to 98)"),
    (13, "Activity code of the MNEs",
     "The match keeps NAICS and US SIC codes from Orbis (naics_aff_6, ussic_aff_4, and the parent's) and the D&B primary NAICS, "
     "not NACE. In the working-paper extract only the Orbis affiliate NAICS (2 digits) is kept: it covers 32.6 percent of the value "
     "exported by MNEs (37.2 percent of rows), 2012-2018. Coverage including the D&B code needs one pass over the base (about 30 "
     "minutes); it is only needed if V6-28 (second tier) is reached.",
     "data/intermediate/wp/fdpy_base.parquet; base columns listed in CLAUDE.md section 2"),
    (14, "Quantities in the customs data",
     "Yes. The raw customs file (Customs/exp_fdpt_10c_names_180625.dta) has kilograms and value per kilogram for all ten origins; "
     "kilograms are positive for 97 to 100 percent of rows (90 to 100 percent of value) in every origin, over each origin's years "
     "(ARG 2011-19, CHL 2009-22, COL 2010-21, CRI 2010-19, DOM 2012-19, ECU 2010-19, PER 2010-19, PRY 2012-20, SLV 2006-18, URY "
     "2010-19). They were not carried into the matched base. No estimation with quantities in v6.",
     "Customs/exp_fdpt_10c_names_180625.dta, columns kilograms, mean_value_per_kg"),
    (15, "Six-digit PCI: source",
     "The Atlas of Economic Complexity (Harvard Growth Lab Dataverse) publishes PCI only at four digits (HS 1992 and HS 2012); its "
     "six-digit files have trade but no PCI. The Observatory of Economic Complexity (OEC) publishes PCI at six digits in HS 1992, "
     "1996, 2002, 2007, 2012, 2017 and 2022, and at four digits in the same revisions, through its public API (tesseract cubes "
     "complexity_pci_a_hs17_hs6, _hs17_hs4, _hs12_hs6, _hs12_hs4). HS 2017: years 2018 to 2024. HS 2012: years 2012 to 2024. The "
     "OEC does not publish ubiquity, but its BACI trade cube in HS 2017 (trade_i_baci_a_17) allows computing it (countries with RCA "
     ">= 1). All downloaded 2026-11-27. V6-03 therefore uses the main rule (PCI6_hs17).",
     "data/raw/external/v6_downloads/oec/"),
    (16, "Section 4.3 of Note_v4 on 2026-11-24",
     "First sentence. Before: 'The stronger association is not matched by a larger presence of multinationals in capital intensive "
     "products.' After: 'Multinationals export products with both high and low capital intensity, and they are not more present in "
     "the former.' Last sentence, added: 'Thus, what differs with capital intensity is not where multinationals are present but how "
     "much their presence is associated with exports.' Nothing else changed.",
     "git show e1c9165 -- docs/notes/Note_v4_source.tex"),
]
