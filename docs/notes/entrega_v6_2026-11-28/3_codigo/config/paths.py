"""
config/paths.py -- EVERY machine-specific path, in one place (Python).

Mirror of config/paths.do. Import from any script in this repo with

    import sys; from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "config"))   # adjust depth
    from paths import *

Ignacio's stylized_facts/python/_common.py has its OWN path block pointing at
D:\\MNEs_Trade (his machine). Redirect it to these constants when running here --
see stylized_facts/README.md, section "Running it on this machine".

Verified on Sebastian's laptop, 2026-09-03.
"""
from pathlib import Path

# ---- this repository ---------------------------------------------------------
ROOT      = Path(r"C:\Sebas BID\Orbis_DNB_Customs_Final")
SRC       = ROOT / "src"
SF_PY     = ROOT / "stylized_facts" / "python"
RAW       = ROOT / "data" / "raw"             # small inputs
INT       = ROOT / "data" / "intermediate"    # new caches/cubes built from now on
CUBES     = INT / "v4_cubes"                  # collapsed_{oy,ody,opy,odpy}.dta (copied from INT_V4, 2026-09-03)
OUTPUT    = ROOT / "output"
TABLES    = OUTPUT / "tables"
GRAPHS    = OUTPUT / "graphs"
REGS      = OUTPUT / "regressions"
LOGS      = OUTPUT / "logs"
OVERLEAF  = OUTPUT / "overleaf_mirror"        # local stand-in for the Overleaf sync folder

# ---- the big files that stay in the old working folder ----------------------
LEGACY     = Path(r"C:\Sebas BID\Orbis_DNB_Customs")
BASE_DTA   = LEGACY / "Base_final_Customs_DNB_Orbis_product_complete.dta"   # 20.6 GB; read in chunks (pyreadstat) -- no parquet copy exists here
INT_V4     = LEGACY / "Claude" / "Data" / "Intermediate_v4"                # originals of collapsed_*; firm_*_level.dta, firm_level_data(_full).dta (13 GB), intermediate_mne_presence.dta (2 GB)
LEGACY_RAW = LEGACY / "Claude" / "Data" / "Raw"                            # Merge_DNB_Orbis_{affiliates,parent,total}_total_PostIA_v2.dta

# ---- Orbis / D&B corporate databases -----------------------------------------
ORBIS_DNB  = Path(r"C:\Sebas BID\Orbis_DNB")
MERGE_V2   = ORBIS_DNB / "IA review" / "Merge_DNB_Orbis_PostIA_v2.dta"       # 38 GB affiliate level (Ignacio's MERGE_AFF_FILE, as .dta)
MERGE_PAR  = ORBIS_DNB / "IA review" / "Merge_DNB_Orbis_par_PostIA_v2.dta"   # 10.9 GB parent level
MERGE_V4   = LEGACY / "Merge_DNB_Orbis_PostIA_v4.dta"                        # 47.9 GB

# ---- small inputs, by name ---------------------------------------------------
F_PRODCHAR = RAW / "product_characteristics_hs6_2002_adj.dta"
F_LALL     = RAW / "lall2000_hs2007.dta"
F_IPC1     = RAW / "ALP_IPC_Patent_hs2007_6_to_ipc1.dta"
F_RHCI     = RAW / "UNCTAD RHCI hs_2007_indices.dta"
F_RCA      = RAW / "RCA_WITS_orig_year.dta"
F_GRAVITY  = RAW / "Gravity_V202211.dta"
F_TARIFFS  = RAW / "tariffsPairs_88_21_vbeta1-2024-12.dta"
F_PTA      = RAW / "PTA_BIT_DTT_BID.dta"
F_INCOME   = RAW / "WB_Income_group.dta"
F_HS2SITC  = RAW / "HS_2007_to_SITC3.dta"
F_HS2NAICS = RAW / "HS6_to_NAICS_2017.dta"
F_HSDESC   = RAW / "JobID-46_Concordance_H3_to_H2.CSV"    # "HS 2007 Product Code", "HS 2007 Product Description"
F_FGO      = RAW / "FGO2022_trade_elasticities_hs6.dta"    # NOT on disk yet (workplan item 1b)
F_BEC      = RAW / "HS2007_to_BEC.dta"                     # NOT on disk yet (workplan item 2)

# ---- cubes already built by src/09-14 (output/tables) ------------------------
CUBE_DEST  = TABLES / "mne_export_destination_cube.dta"    # origin x dest x year x iso3_parent x MNE flags (201,847 rows)
CUBE_UCP   = TABLES / "mne_ucp_cube.dta"                   # + ultimate-owner concepts (277,690 rows)
CUBE_OWNCOV= TABLES / "ownership_cov_bymarket.dta"         # dest x hs6 x year x group (5.4 M rows)

# ---- project-wide conventions ------------------------------------------------
EXCLUDED_ORIGINS_SF = ("ECU",)   # the stylized-facts document uses nine origins; src/05-14 use ten
CONDUITS = ("PAN", "BMU", "IRL", "NLD", "CHE", "LUX", "CYM", "VGB", "HKG", "SGP", "JEY", "GGY", "MLT", "MUS", "BHS", "CUW")

STATA_EXE = r"C:\Program Files\Stata18\StataMP-64.exe"

for _d in (INT, OUTPUT, TABLES, GRAPHS, REGS, LOGS, OVERLEAF):
    _d.mkdir(parents=True, exist_ok=True)
