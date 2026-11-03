# External data for the agriculture note (not tracked in git)

Downloaded 2026-11-02 for `stylized_facts/python/wp_agro_capital.py` (capital intensity of agricultural products).
Kept out of git: the census file is 132 MB (over GitHub's limit) and NBER-CES asks users not to redistribute it.

| File | Source | How to get it |
|---|---|---|
| `qs.census2017.txt.gz` (132 MB) | USDA NASS, Quick Stats bulk file, 2017 Census of Agriculture | https://www.nass.usda.gov/datasets/qs.census2017.txt.gz |
| `usda_census2017_national_naics.parquet` | national rows of the domain "NAICS CLASSIFICATION" from the file above | built by the extraction step in the session log (filter `AGG_LEVEL_DESC == "NATIONAL"`, `DOMAIN_DESC` contains "NAICS") |
| `usda_census2017_table75_naics.pdf` | USDA NASS, 2017 Census, Vol. 1 Ch. 1 US, Table 75 (used to check the bulk values) | https://www.nass.usda.gov/Publications/AgCensus/2017/Full_Report/Volume_1,_Chapter_1_US/st99_1_0075_0075.pdf |
| `nberces5818v1_n2012.csv` | NBER-CES Manufacturing Industry Database, 2012 NAICS, v2021a (Becker, Gray and Marvakov 2021) | https://data.nber.org/nberces/nberces5818v1/nberces5818v1_n2012.csv |
| `nberces5818v1_summary_stats.pdf` | NBER-CES variable definitions (EMP in thousands, EQUIP in real $1m) | https://data.nber.org/nberces/nberces5818v1/nberces5818v1_summary_stats.pdf |
