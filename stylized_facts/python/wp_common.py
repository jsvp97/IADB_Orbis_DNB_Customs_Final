"""
wp_common.py
============

Shared layer for the WORKING-PAPER extensions of the stylized facts (Volpe's agenda,
September 2026; see ../../docs/WORKPLAN_working_paper.md). It sits ON TOP of Ignacio's
`_common.py`: same palette, same matplotlib defaults, same LaTeX/figure helpers -- only
the paths and a few new helpers are added here. Ignacio's scripts are untouched.

Everything downstream reads ONE cache built by `src/15_wp_extract_fdpy.do`
(firm x origin x destination x HS6 x year, with both match flags, parent country, group
id, HQ flag and destination-presence flags) -- never the 20 GB base.

Conventions
-----------
CONVENTION = "sf"  (default) : the stylized-facts document's convention (Ignacio,
                    post-2026-05-23): matched = _merge_DNB_Orbis==3 (`m_dnb`);
                    dom = matched & parent == origin; ext = matched - dom (unknown-parent
                    matched firms count as FOREIGN); Ecuador excluded.
CONVENTION = "src" : src/05-14 convention: matched = _merge_final_review==3 (`m_fr`);
                    ext requires a known parent != origin; ten origins.
Every script calls `mne_flags(df)` so the switch is one constant.

Outputs go to  output/wp/<scope>/{Graphs,Tables,Regressions}/  where scope is
"all" (all goods), "agro" (HS 01-24), "mining", "manufacturing", or "sectors" (the
four-sector comparison). No Overleaf mirror (set OVERLEAF_WP to a folder if wanted).
"""
from __future__ import annotations

import sys
from pathlib import Path

import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

logging.getLogger("fontTools").setLevel(logging.WARNING)   # eps export is very chatty otherwise

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:  # Windows consoles default to cp1252; labels carry sigma etc.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass
sys.path.insert(0, str(HERE.parents[1] / "config"))

from _common import (  # noqa: E402  -- Ignacio's helpers, unchanged
    C_MNE_EXT, C_MNE_DOM, C_MNE_TOT, ensure_dir, save_figure, stars,
    write_regression_table,
)
from paths import (  # noqa: E402  -- config/paths.py
    ROOT, RAW, INT, OUTPUT, F_PRODCHAR, F_LALL, F_IPC1, F_RHCI, F_GRAVITY, F_INCOME,
    F_HS2SITC, F_HS2NAICS, F_HSDESC, EXCLUDED_ORIGINS_SF,
)

# ---------------------------------------------------------------------
# Switches
# ---------------------------------------------------------------------
CONVENTION = "sf"            # "sf" (document) or "src" (scripts 05-14) -- see module docstring
MINING_INCLUDES_HS71 = True  # put HS 71 (precious metals/stones: gold, silver) with mining & fuels
OVERLEAF_WP: Path | None = None

# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------
WP_INT   = INT / "wp"
FDPY_DTA = WP_INT / "fdpy_base.dta"          # written by src/15_wp_extract_fdpy.do
FDPY_PQ  = WP_INT / "fdpy_base.parquet"      # pandas cache of the same
CUBE_PQ  = WP_INT / "odpy_parent_cube.parquet"
CLASS_PQ = WP_INT / "hs6_classifications.parquet"
WP_OUT   = OUTPUT / "wp"
F_FGO    = RAW / "ProTEE_0_1.csv"                              # CEPII, Fontagne-Guimbard-Orefice (2022), HS6 rev. 2007
F_BEC    = RAW / "UNSD_HS-SITC-BEC_Correlations_2022.xlsx"     # UNSD: HS92..HS22 x BEC4/BEC5 x SITC1-4
for _d in (WP_INT, WP_OUT):
    ensure_dir(_d)


def outdirs(scope: str) -> tuple[Path, Path, Path]:
    """(Graphs, Tables, Regressions) folders for a scope; created on demand."""
    base = WP_OUT / scope
    g, t, r = base / "Graphs", base / "Tables", base / "Regressions"
    for d in (g, t, r):
        ensure_dir(d)
    return g, t, r


def savefig(fig, name: str, gdir: Path) -> None:
    save_figure(fig, name, gdir, OVERLEAF_WP)


def write_tex(lines: list[str], path: Path) -> None:
    ensure_dir(path.parent)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def tex_escape(s: str) -> str:
    s = str(s)
    if s.startswith("$") or "\\" in s:   # already TeX
        return s
    return (str(s).replace("\\", r"\textbackslash{}").replace("&", r"\&").replace("%", r"\%")
            .replace("$", r"\$").replace("#", r"\#").replace("_", r"\_"))


# ---------------------------------------------------------------------
# Palette for parent countries (foreign MNE bar split by home country)
#   foreign total keeps Ignacio's navy; parents get distinct, print-safe hues;
#   domestic stays light gray; unknown parent is hatched.
# ---------------------------------------------------------------------
PARENT_COLORS = {
    "USA": "#1f3864",  # navy (same as C_MNE_EXT)
    "GBR": "#8c1d1d",
    "CAN": "#c8a24a",  # gold (Ignacio's third colour)
    "NLD": "#e07b39",
    "DEU": "#4c7a34",
    "JPN": "#6a3d9a",
    "BRA": "#2e8b9a",
    "FRA": "#a6cee3",
    "CHN": "#d62728",
    "ESP": "#b5651d",
    "CHE": "#7f7f7f",
    "ITA": "#98df8a",
    "MEX": "#ff9896",
    "PAN": "#c5b0d5",
    "AUS": "#17becf",
    "LIE": "#8c564b",
    "Other": "#9aa5b8",
    "Unknown": "#cfd6e4",
    "Domestic": C_MNE_DOM,
}
_FALLBACK = ["#393b79", "#637939", "#8c6d31", "#843c39", "#7b4173", "#3182bd", "#e6550d",
             "#31a354", "#756bb1", "#636363"]


def parent_color(code: str, i: int = 0) -> str:
    return PARENT_COLORS.get(code, _FALLBACK[i % len(_FALLBACK)])


# ---------------------------------------------------------------------
# Regions (destination and parent). Same lists as Ignacio's sf_explore_dest.py,
# extended so that every code in the data gets a region.
# ---------------------------------------------------------------------
NA_CODES = {"USA", "CAN"}
OC_CODES = {"AUS", "NZL", "PNG", "FJI"}
LAC_CODES = {"ARG", "BHS", "BRB", "BLZ", "BOL", "BRA", "CHL", "COL", "CRI", "DOM", "ECU", "SLV",
             "GTM", "GUY", "HTI", "HND", "JAM", "MEX", "NIC", "PAN", "PRY", "PER", "SUR", "TTO",
             "URY", "VEN", "CUB", "ABW", "ANT", "CUW", "ATG", "DMA", "GRD", "KNA", "LCA", "VCT",
             "BMU", "CYM", "VGB", "TCA", "PRI", "SXM", "BES", "MSR", "AIA", "GLP", "MTQ", "GUF"}
EU_CODES = {"AUT", "BEL", "BGR", "CYP", "CZE", "DNK", "EST", "FIN", "FRA", "DEU", "GRC", "HUN",
            "IRL", "ITA", "LVA", "LTU", "LUX", "MLT", "NLD", "POL", "PRT", "ROU", "SVK", "SVN",
            "ESP", "SWE", "GBR", "CHE", "NOR", "ISL", "LIE", "MCO", "AND", "SMR", "GIB", "JEY",
            "GGY", "IMN", "FRO", "ALB", "BIH", "HRV", "MKD", "MNE", "SRB", "XKX", "MDA", "BLR",
            "UKR", "RUS", "TUR", "GEO", "ARM", "AZE"}
ASIA_CODES = {"CHN", "HKG", "MAC", "TWN", "JPN", "KOR", "PRK", "MNG", "IND", "PAK", "BGD", "LKA",
              "NPL", "BTN", "MDV", "AFG", "IDN", "MYS", "PHL", "SGP", "THA", "VNM", "KHM", "LAO",
              "MMR", "BRN", "TLS", "KAZ", "KGZ", "TJK", "TKM", "UZB", "ARE", "SAU", "ISR", "IRN",
              "IRQ", "JOR", "KWT", "LBN", "OMN", "QAT", "SYR", "YEM", "BHR", "PSE"}
AFRICA_CODES = {"DZA", "AGO", "BEN", "BWA", "BFA", "BDI", "CMR", "CPV", "CAF", "TCD", "COM", "COD",
                "COG", "CIV", "DJI", "EGY", "GNQ", "ERI", "ETH", "GAB", "GMB", "GHA", "GIN", "GNB",
                "KEN", "LSO", "LBR", "LBY", "MDG", "MWI", "MLI", "MRT", "MUS", "MAR", "MOZ", "NAM",
                "NER", "NGA", "RWA", "STP", "SEN", "SYC", "SLE", "SOM", "ZAF", "SSD", "SDN", "SWZ",
                "TZA", "TGO", "TUN", "UGA", "ZMB", "ZWE", "ESH", "REU", "MYT", "SHN"}
REGION_ORDER = ["Latin America", "North America", "Europe", "Asia", "Africa", "Oceania", "Rest of World"]


def classify_region(code) -> str:
    code = "" if code is None or (isinstance(code, float) and np.isnan(code)) else str(code)
    if code in LAC_CODES:    return "Latin America"
    if code in NA_CODES:     return "North America"
    if code in EU_CODES:     return "Europe"
    if code in ASIA_CODES:   return "Asia"
    if code in AFRICA_CODES: return "Africa"
    if code in OC_CODES:     return "Oceania"
    return "Rest of World"


# ---------------------------------------------------------------------
# Sectors (HS 2007 chapters)
# ---------------------------------------------------------------------
SECTOR_ORDER = ["Agriculture", "Mining & fuels", "Manufacturing"]
AGRO_SECTION_LABEL = {1: "I Live animals & products (01-05)", 2: "II Vegetable products (06-14)",
                      3: "III Fats & oils (15)", 4: "IV Food, beverages, tobacco (16-24)"}


def hs2_of(hs6: pd.Series) -> pd.Series:
    return pd.to_numeric(hs6.astype(str).str.zfill(6).str[:2], errors="coerce")


def sector4(hs2: pd.Series) -> pd.Series:
    """Agriculture 01-24; Mining & fuels 25-27 (+71 if MINING_INCLUDES_HS71); Manufacturing = rest.
    Services are NOT in customs merchandise data (documented in the WORKPLAN)."""
    s = pd.Series("Manufacturing", index=hs2.index, dtype="object")
    s[hs2.between(1, 24)] = "Agriculture"
    mining = hs2.between(25, 27)
    if MINING_INCLUDES_HS71:
        mining = mining | (hs2 == 71)
    s[mining] = "Mining & fuels"
    s[hs2.isna()] = np.nan
    return s


def agro_section(hs2: pd.Series) -> pd.Series:
    s = pd.Series(np.nan, index=hs2.index, dtype="float")
    s[hs2.between(1, 5)] = 1; s[hs2.between(6, 14)] = 2; s[hs2 == 15] = 3; s[hs2.between(16, 24)] = 4
    return s


def hs_section(hs2: pd.Series) -> pd.Series:
    bins = [(1, 5), (6, 14), (15, 15), (16, 24), (25, 27), (28, 38), (39, 40), (41, 43), (44, 46), (47, 49),
            (50, 63), (64, 67), (68, 70), (71, 71), (72, 83), (84, 85), (86, 89), (90, 92), (93, 93),
            (94, 96), (97, 97)]
    s = pd.Series(np.nan, index=hs2.index, dtype="float")
    for i, (a, b) in enumerate(bins, 1):
        s[hs2.between(a, b)] = i
    return s


def scope_filter(df: pd.DataFrame, scope: str) -> pd.DataFrame:
    """Row filter by scope on a frame that carries `hs2`."""
    if scope == "all":
        return df
    sec = sector4(df["hs2"])
    return df[sec == {"agro": "Agriculture", "mining": "Mining & fuels",
                      "manufacturing": "Manufacturing"}[scope]]


# ---------------------------------------------------------------------
# BEC Rev.4 -> end use (SNA basic classes). Standard mapping used by UN/OECD:
#   capital       41, 521
#   intermediate  111, 121, 21, 22, 31, 322, 42, 53
#   consumption   112, 122, 522, 61, 62, 63
#   mixed / n.e.s. 321 (motor spirit), 51 (passenger cars), 7
# ---------------------------------------------------------------------
BEC4_ENDUSE = {
    "111": "Intermediate", "121": "Intermediate", "21": "Intermediate", "22": "Intermediate",
    "31": "Intermediate", "322": "Intermediate", "42": "Intermediate", "53": "Intermediate",
    "112": "Consumption", "122": "Consumption", "522": "Consumption", "61": "Consumption",
    "62": "Consumption", "63": "Consumption",
    "41": "Capital", "521": "Capital",
    "321": "Mixed (motor spirit)", "51": "Mixed (passenger cars)", "7": "n.e.s.",
}
BEC4_LABEL = {
    "111": "Food & bev., primary, for industry", "112": "Food & bev., primary, for households",
    "121": "Food & bev., processed, for industry", "122": "Food & bev., processed, for households",
    "21": "Industrial supplies, primary", "22": "Industrial supplies, processed",
    "31": "Fuels, primary", "321": "Motor spirit", "322": "Fuels, other processed",
    "41": "Capital goods", "42": "Parts of capital goods", "51": "Passenger cars",
    "521": "Transport equipment, industrial", "522": "Transport equipment, non-industrial",
    "53": "Parts of transport equipment", "61": "Consumer goods, durable",
    "62": "Consumer goods, semi-durable", "63": "Consumer goods, non-durable", "7": "Goods n.e.s.",
}
ENDUSE_ORDER = ["Intermediate", "Consumption", "Capital", "Mixed (motor spirit)", "Mixed (passenger cars)", "n.e.s."]

# Agro INPUTS (Volpe: "insumos agro") -- hand-made HS 2007 flag, cross-checked against BEC end use
AGRO_INPUT_HS2 = {31}                                         # fertilizers
AGRO_INPUT_HS4 = {"3808",                                      # pesticides, herbicides, fungicides
                  "1209", "1005", "1006", "1007",              # seeds for sowing (1005-1007 only the seed lines; refined below)
                  "2301", "2302", "2303", "2304", "2305", "2306", "2308", "2309",   # animal feed
                  "8432", "8433", "8434", "8436", "8437", "8701",                    # agricultural machinery, tractors
                  "0102", "0103", "0104", "0105", "0106", "0511",                    # live animals, semen/embryos
                  "3101", "3102", "3103", "3104", "3105"}
SEED_HS6 = {"100510", "100610", "100710", "120810", "120910", "120921", "120922", "120923",
            "120924", "120925", "120926", "120929", "120930", "120991", "120999", "070110", "071310",
            "071320", "071331", "071332", "071333", "071339", "071340", "071350", "071390"}


def agro_input_flag(hs6: pd.Series) -> pd.Series:
    h = hs6.astype(str).str.zfill(6)
    f = h.str[:2].isin({f"{c:02d}" for c in AGRO_INPUT_HS2}) | h.str[:4].isin(AGRO_INPUT_HS4) | h.isin(SEED_HS6)
    # exclude the food uses of maize/rice/soy: only the "seed" lines count (10051x, 10061x, 10071x, 1201 all)
    food_not_seed = h.str[:4].isin({"1005", "1006", "1007"}) & ~h.isin({"100510", "100610", "100710"})
    return (f & ~food_not_seed).astype("int8")


# ---------------------------------------------------------------------
# HS6 classification table (built once, cached)
# ---------------------------------------------------------------------
def build_classifications(force: bool = False) -> pd.DataFrame:
    """hs07_6d -> descriptions, HS2/section, sector, agro section, Lall, IPC, product
    characteristics (PCI, sigma BW, upstreamness, ladder, Rauch), FGO elasticity, RHCI,
    BEC4 + end use, SITC3, NAICS, agro-input flag."""
    import pyreadstat
    if CLASS_PQ.exists() and not force:
        return pd.read_parquet(CLASS_PQ)
    print(">>> building HS6 classification table")

    def dta(p, cols=None):
        d, _ = pyreadstat.read_dta(str(p), usecols=cols, encoding="latin1")
        return d

    # descriptions (WITS H3->H2 table) -- also gives HS2002 code
    desc = pd.read_csv(F_HSDESC, dtype=str, encoding="latin1")
    desc.columns = ["hs07_6d", "hs6_desc", "hs02_6d", "hs02_desc"]
    desc["hs07_6d"] = desc["hs07_6d"].str.zfill(6)
    desc = desc.drop_duplicates("hs07_6d")[["hs07_6d", "hs6_desc"]]

    # product characteristics (Ignacio's F_PRODCHAR: pci sigma upstreamness ladder + Rauch)
    pc = dta(F_PRODCHAR, ["hs07_6d", "pci", "sigma", "upstreamness", "ladder", "lib", "con", "lib_diff",
                          "lib_ref_price", "lib_org_exch", "hs2007productdescription"])
    pc["hs07_6d"] = pc["hs07_6d"].astype(str).str.zfill(6)
    pc = pc.rename(columns={"pci": "complexity", "sigma": "sigma_bw", "ladder": "quality_ladder",
                            "hs2007productdescription": "hs6_desc_pc"})
    # Rauch (liberal): differentiated / reference-priced / organised exchange
    pc["rauch"] = np.select([pc["lib_diff"] == 1, pc["lib_ref_price"] == 1, pc["lib_org_exch"] == 1],
                            ["Differentiated", "Reference-priced", "Homogeneous (exchange)"], default=None)
    pc = pc.drop_duplicates("hs07_6d")

    lall = dta(F_LALL, ["hs07_6d", "hs6_description", "sitc3_3digit", "lall2000_category"])
    lall["hs07_6d"] = lall["hs07_6d"].astype(str).str.zfill(6)
    lall = lall.drop_duplicates("hs07_6d").rename(columns={"hs6_description": "hs6_desc_lall"})
    ipc = dta(F_IPC1, ["hs07_6d", "ipc1"]); ipc["hs07_6d"] = ipc["hs07_6d"].astype(str).str.zfill(6)
    ipc = ipc.drop_duplicates("hs07_6d")
    rhci = dta(F_RHCI, ["hs07_6d", "rhci"]); rhci["hs07_6d"] = rhci["hs07_6d"].astype(str).str.zfill(6)
    rhci = rhci.drop_duplicates("hs07_6d")

    # FGO (2022) -- sigma is the import-demand elasticity (negative); more negative = more substitutable.
    fgo = pd.read_csv(F_FGO, dtype={"HS6": str})
    fgo["hs07_6d"] = fgo["HS6"].str.zfill(6)
    fgo = fgo.rename(columns={"sigma": "sigma_fgo", "zero": "fgo_flag_zero", "positive": "fgo_flag_positive"})
    fgo["sigma_fgo_abs"] = -fgo["sigma_fgo"]           # substitutability, positive scale
    fgo = fgo[["hs07_6d", "sigma_fgo", "sigma_fgo_abs", "fgo_flag_zero", "fgo_flag_positive"]]

    # BEC4 / BEC5 / SITC3 from the UNSD table (HS07 column). One HS07 may map to several rows
    # (HS22 splits); take the modal BEC4 per HS07 (ties -> first).
    bec = pd.read_excel(F_BEC, dtype=str)
    bec = bec.rename(columns={"HS07": "hs07_6d"})[["hs07_6d", "BEC4", "BEC5", "SITC3"]].dropna(subset=["hs07_6d"])
    bec["hs07_6d"] = bec["hs07_6d"].str.zfill(6)
    bec["BEC4"] = bec["BEC4"].str.strip()
    modal = (bec.groupby(["hs07_6d", "BEC4"]).size().reset_index(name="n")
                .sort_values(["hs07_6d", "n"], ascending=[True, False]).drop_duplicates("hs07_6d"))
    bec["SITC3"] = bec["SITC3"].astype(str).str.strip()
    sitc = bec.drop_duplicates("hs07_6d")[["hs07_6d", "SITC3", "BEC5"]]
    bec4 = modal[["hs07_6d", "BEC4"]].merge(sitc, on="hs07_6d", how="left").rename(columns={"BEC4": "bec4", "SITC3": "sitc3_unsd", "BEC5": "bec5"})
    bec4["bec_enduse"] = bec4["bec4"].map(BEC4_ENDUSE).fillna("n.e.s.")
    bec4["bec4_label"] = bec4["bec4"].map(BEC4_LABEL).fillna(bec4["bec4"])

    # SITC Rev.3 from the WITS text concordance (codes are 3-5 digits with leading zeros preserved;
    # the .dta twin lost the zeros, so the CSV is the source)
    sitc_own = pd.read_csv(RAW / "JobID-53_Concordance_H3_to_S3.CSV", dtype=str, encoding="latin1")
    sitc_own.columns = ["hs07_6d", "hs6_desc_sitc", "sitc3", "sitc3_desc"]
    sitc_own["hs07_6d"] = sitc_own["hs07_6d"].str.zfill(6)
    sitc_own = sitc_own.drop_duplicates("hs07_6d")
    sitc_own["sitc3"] = sitc_own["sitc3"].astype(str).str.strip()
    sitc_own["sitc1"] = sitc_own["sitc3"].str[:1]
    sitc_own["sitc2"] = sitc_own["sitc3"].str[:2]
    sitc_own["sitc3_3d"] = sitc_own["sitc3"].str[:3]

    naics = dta(F_HS2NAICS); naics.columns = [c.lower() for c in naics.columns]
    naics["hs07_6d"] = naics["hs6"].astype(str).str.zfill(6)
    naics["naics"] = naics["naics"].astype(str).str.strip()
    naics = naics.drop_duplicates("hs07_6d")[["hs07_6d", "naics"]]
    naics["naics3"] = naics["naics"].str[:3]

    base = pd.DataFrame({"hs07_6d": sorted(set(desc["hs07_6d"]) | set(pc["hs07_6d"]) | set(lall["hs07_6d"]))})
    for t in (desc, pc, lall, ipc, rhci, fgo, bec4, sitc_own, naics):
        base = base.merge(t, on="hs07_6d", how="left")
    base["hs6_desc"] = base["hs6_desc"].fillna(base["hs6_desc_lall"]).fillna(base["hs6_desc_pc"]).fillna(base["hs6_desc_sitc"])
    # codes that appear in the customs data but are not HS 2007 lines (later revisions)
    EXTRA_DESC = {"080390": "Bananas, fresh or dried (excl. plantains) [HS2012 code]", "080310": "Plantains, fresh or dried [HS2012 code]",
                  "271012": "Light petroleum oils and preparations [HS2012 code]", "271020": "Petroleum oils containing biodiesel [HS2012 code]",
                  "440729": "Tropical wood, sawn [HS2012 code]", "030389": "Frozen fish n.e.s. [HS2012 code]"}
    for k, v in EXTRA_DESC.items():
        if k not in set(base["hs07_6d"]):
            base = pd.concat([base, pd.DataFrame({"hs07_6d": [k]})], ignore_index=True)
        base.loc[base["hs07_6d"] == k, "hs6_desc"] = base.loc[base["hs07_6d"] == k, "hs6_desc"].fillna(v)
    base = base.drop(columns=["hs6_desc_lall", "hs6_desc_pc", "hs6_desc_sitc"])
    base["hs2"] = hs2_of(base["hs07_6d"])
    base["hs4"] = base["hs07_6d"].str[:4]
    base["hs_section"] = hs_section(base["hs2"])
    base["sector4"] = sector4(base["hs2"])
    base["agro_section"] = agro_section(base["hs2"])
    base["agro_input"] = agro_input_flag(base["hs07_6d"])
    base.to_parquet(CLASS_PQ, index=False)
    print(f"    {len(base):,} HS6 rows -> {CLASS_PQ.name}; "
          f"FGO coverage {base['sigma_fgo'].notna().mean():.0%}, BEC {base['bec4'].notna().mean():.0%}, "
          f"PCI {base['complexity'].notna().mean():.0%}")
    return base


# ---------------------------------------------------------------------
# The FDPY cache and the parent cube
# ---------------------------------------------------------------------
FDPY_COLS = ["country_orig", "Tax_ID", "country_dest", "hs07_6d", "year", "value_fob", "m_dnb", "m_fr",
             "iso3_parent", "ID_Orbis_DNB", "parent_key", "exporter_is_hq", "has_aff_in_dest",
             "has_aff_in_neighbor", "naics_aff_2"]


def load_fdpy() -> pd.DataFrame:
    """Firm x origin x dest x HS6 x year rows from src/15's cache (parquet copy made on first use)."""
    if FDPY_PQ.exists():
        return pd.read_parquet(FDPY_PQ)
    import pyreadstat
    assert FDPY_DTA.exists(), f"run src/15_wp_extract_fdpy.do first -> {FDPY_DTA}"
    print(f">>> reading {FDPY_DTA} (first time; parquet cache written)")
    df, _ = pyreadstat.read_dta(str(FDPY_DTA), encoding="latin1")
    for c in ("m_dnb", "m_fr", "exporter_is_hq", "has_aff_in_dest", "has_aff_in_neighbor"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype("int8")
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df["value_fob"] = pd.to_numeric(df["value_fob"], errors="coerce").fillna(0.0).astype(float)
    for c in ("country_orig", "country_dest", "iso3_parent", "hs07_6d", "Tax_ID", "ID_Orbis_DNB", "parent_key"):
        df[c] = df[c].astype("string").str.strip().fillna("")
    df["hs07_6d"] = df["hs07_6d"].str.zfill(6)
    df.to_parquet(FDPY_PQ, index=False)
    return df


def matched_flag(df: pd.DataFrame) -> pd.Series:
    return df["m_dnb"] if CONVENTION == "sf" else df["m_fr"]


def excluded_origins() -> tuple:
    return EXCLUDED_ORIGINS_SF if CONVENTION == "sf" else tuple()


def owner_type(df: pd.DataFrame) -> pd.Series:
    """local | dom | ext | ext_unknown  (ext_unknown = matched, no parent country recorded).
    Under CONVENTION='sf', ext_unknown is FOREIGN (ext = total - dom); under 'src' it is
    neither foreign nor domestic. `mne_flags` applies that rule."""
    m = matched_flag(df).astype(bool)
    par = df["iso3_parent"].astype("string").fillna("")
    out = pd.Series("local", index=df.index, dtype="object")
    out[m & (par == df["country_orig"])] = "dom"
    out[m & (par != df["country_orig"]) & (par != "")] = "ext"
    out[m & (par == "")] = "ext_unknown"
    return out


def build_cube(force: bool = False) -> pd.DataFrame:
    """origin x dest x HS6 x year x iso3_parent x m_dnb x m_fr  ->  value, n_firms, and the
    HQ / presence sub-sums. Both conventions can be recomposed from it."""
    if CUBE_PQ.exists() and not force:
        return pd.read_parquet(CUBE_PQ)
    df = load_fdpy()
    print(f">>> building parent cube from {len(df):,} FDPY rows")
    df = df[df["value_fob"] > 0]
    keys = ["country_orig", "country_dest", "hs07_6d", "year", "iso3_parent", "m_dnb", "m_fr"]
    df = df.assign(
        v_hq=df["value_fob"] * df["exporter_is_hq"],
        v_affpres=df["value_fob"] * df["has_aff_in_dest"],
        v_hqdest=df["value_fob"] * ((df["iso3_parent"] != "") & (df["iso3_parent"] == df["country_dest"])).astype(int),
        firm=df["country_orig"] + "|" + df["Tax_ID"],
    )
    # group key: the parent's Orbis/D&B id when known, else the parent name, else the firm itself
    grp = df["ID_Orbis_DNB"].where(df["ID_Orbis_DNB"] != "", df["parent_key"])
    df["group"] = grp.where(grp != "", df["firm"])
    g = df.groupby(keys, as_index=False, dropna=False).agg(
        value=("value_fob", "sum"), n_firms=("firm", "nunique"), n_groups=("group", "nunique"),
        v_hq=("v_hq", "sum"), n_hq=("exporter_is_hq", "sum"),
        v_affpres=("v_affpres", "sum"), n_affpres=("has_aff_in_dest", "sum"),
        v_hqdest=("v_hqdest", "sum"))
    g["n_hqdest"] = np.where((g["iso3_parent"] != "") & (g["iso3_parent"] == g["country_dest"]), g["n_firms"], 0)
    g["hs2"] = hs2_of(g["hs07_6d"])
    g.to_parquet(CUBE_PQ, index=False)
    print(f"    cube: {len(g):,} rows -> {CUBE_PQ.name}")
    return g


def mne_flags(cube: pd.DataFrame) -> pd.DataFrame:
    """Add owner_type, val_total/val_dom/val_ext, parent_grp columns to a cube slice, apply the
    convention's origin exclusion. Works on any frame with the cube keys."""
    d = cube[~cube["country_orig"].isin(excluded_origins())].copy()
    d["owner_type"] = owner_type(d)
    m = matched_flag(d).astype(bool)
    d["val_total"] = d["value"] * m
    d["val_dom"] = d["value"] * (d["owner_type"] == "dom")
    if CONVENTION == "sf":
        d["val_ext"] = d["val_total"] - d["val_dom"]                    # unknown parent counts as foreign
    else:
        d["val_ext"] = d["value"] * (d["owner_type"] == "ext")
    d["val_ext_known"] = d["value"] * (d["owner_type"] == "ext")
    d["val_ext_unknown"] = d["value"] * (d["owner_type"] == "ext_unknown")
    return d


def top_parents(d: pd.DataFrame, k: int = 8, force: tuple = ("USA", "CHN")) -> list[str]:
    """Top-k parent countries by KNOWN-parent foreign-MNE value, plus forced codes if present."""
    v = d[d["owner_type"] == "ext"].groupby("iso3_parent")["value"].sum().sort_values(ascending=False)
    top = list(v.index[:k])
    for c in force:
        if c in v.index and c not in top:
            top.append(c)
    return top


def parent_group(d: pd.DataFrame, top: list[str]) -> pd.Series:
    """Label for the stacked-bar split: parent code (if in top), Other (known, not top),
    Unknown (matched, no parent), Domestic, or Local (unmatched)."""
    out = pd.Series("Local", index=d.index, dtype="object")
    out[d["owner_type"] == "dom"] = "Domestic"
    out[d["owner_type"] == "ext_unknown"] = "Unknown"
    ext = d["owner_type"] == "ext"
    out[ext] = np.where(d.loc[ext, "iso3_parent"].isin(top), d.loc[ext, "iso3_parent"], "Other")
    return out


# ---------------------------------------------------------------------
# Generic LaTeX matrix writer (two-way tables, heat-map companions)
# ---------------------------------------------------------------------
def write_matrix_tex(mat: pd.DataFrame, path: Path, *, fmt: str = "{:.1f}", corner: str = "",
                     row_total: pd.Series | None = None, col_total: pd.Series | None = None,
                     note: str | None = None, caption_cols: str | None = None) -> None:
    cols = list(mat.columns)
    ncol = len(cols) + (1 if row_total is not None else 0)
    lines = [rf"\begin{{tabular}}{{l{'r' * ncol}}}", r"\toprule"]
    if caption_cols:
        lines.append(rf" & \multicolumn{{{len(cols)}}}{{c}}{{{caption_cols}}}" + (" & " if row_total is not None else "") + r" \\")
    hdr = [tex_escape(corner)] + [tex_escape(c) for c in cols] + (["Total"] if row_total is not None else [])
    lines += [" & ".join(hdr) + r" \\", r"\midrule"]
    for idx, row in mat.iterrows():
        cells = ["--" if pd.isna(v) else fmt.format(v) for v in row.values]
        if row_total is not None:
            cells.append(fmt.format(row_total.loc[idx]))
        lines.append(tex_escape(idx) + " & " + " & ".join(cells) + r" \\")
    if col_total is not None:
        lines.append(r"\midrule")
        cells = [fmt.format(col_total.loc[c]) for c in cols] + ([fmt.format(col_total.sum() if row_total is None else row_total.sum())] if row_total is not None else [])
        lines.append("Total & " + " & ".join(cells) + r" \\")
    lines.append(r"\bottomrule")
    if note:
        lines.append(rf"\multicolumn{{{ncol + 1}}}{{p{{0.95\textwidth}}}}{{\footnotesize {note}}} \\")
    lines.append(r"\end{tabular}")
    write_tex(lines, path)


def heatmap(mat: pd.DataFrame, fname: str, gdir: Path, *, cbar_label: str, fmt: str = "{:.0f}",
            cmap: str = "Blues", vmin: float | None = None, vmax: float | None = None,
            xlabel: str = "", ylabel: str = "", annotate_thresh: float | None = None) -> None:
    """Same construction as Ignacio's sf_explore_dest_by_origin.heatmap (imshow + annotations)."""
    fig, ax = plt.subplots(figsize=(max(6, 0.62 * mat.shape[1] + 2.5), max(4, 0.42 * mat.shape[0] + 1.8)))
    vals = mat.values.astype(float)
    vmin = np.nanmin(vals) if vmin is None else vmin
    vmax = np.nanmax(vals) if vmax is None else vmax
    im = ax.imshow(vals, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_xticks(range(mat.shape[1])); ax.set_xticklabels(mat.columns, rotation=45, ha="right")
    ax.set_yticks(range(mat.shape[0])); ax.set_yticklabels(mat.index)
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            v = vals[i, j]
            if np.isnan(v):
                ax.text(j, i, "—", ha="center", va="center", fontsize=7, color="gray"); continue
            if annotate_thresh is not None and v < annotate_thresh:
                continue
            color = "white" if v > vmin + 0.6 * (vmax - vmin) else "black"
            ax.text(j, i, fmt.format(v), ha="center", va="center", fontsize=7, color=color)
    cbar = plt.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label(cbar_label, fontsize=9)
    if xlabel: ax.set_xlabel(xlabel)
    if ylabel: ax.set_ylabel(ylabel)
    savefig(fig, fname, gdir)


# ---------------------------------------------------------------------
# Gravity / income helpers
# ---------------------------------------------------------------------
def load_gravity(cols=("iso3_o", "iso3_d", "year", "dist", "contig", "comlang_off", "fta_wto",
                       "gdp_o", "gdpcap_o", "pop_o", "gdp_d", "gdpcap_d", "pop_d")) -> pd.DataFrame:
    import pyreadstat
    g, _ = pyreadstat.read_dta(str(F_GRAVITY), usecols=list(cols))
    if "year" in g.columns:
        g["year"] = pd.to_numeric(g["year"], errors="coerce").astype("Int64")
    return g


def load_income_groups() -> pd.DataFrame:
    import pyreadstat
    d, _ = pyreadstat.read_dta(str(F_INCOME))
    return d.rename(columns={"iso3": "country_dest", "income_group": "income_group_dest"})


def fmt_bn(v: float) -> str:
    return f"{v / 1e9:,.1f}"


__all__ = [n for n in dir() if not n.startswith("_")]
