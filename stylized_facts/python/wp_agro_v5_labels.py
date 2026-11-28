"""
wp_agro_v5_labels.py  --  plain language labels for the v5 workbook and figures
==============================================================================

Every code used inside the estimation scripts (FE4, EV2, g_ps, lnN, D, anyXL, high_mean, ...) is translated here into words, so
that the workbook and the figures can be read without a key. Used by wp_agro_v5_workbook.py.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------------------------------------------------
# fixed effects
# ---------------------------------------------------------------------------------------------------------------------
FE_WORDS = {
    "FE1": "Origin, destination, product and year",
    "FE2": "Origin x year, destination x year and product",
    "FE3": "Origin x destination x product and year",
    "FE4": "Origin x destination x product and origin x destination x year",
    "FE5": "Origin x destination x product, origin x destination x year and origin x product x year",
    "FE6": "Origin x destination x product, origin x destination x year, origin x product x year and destination x product x year",
    "origin x year": "Origin x year",
    "origin x year + type of production": "Origin x year and type of production",
    "origin x year + HS chapter": "Origin x year and HS chapter",
    "oy": "Origin x year", "oy + type": "Origin x year and type of production", "oy + hs2": "Origin x year and HS chapter",
}
FE_WORDS_WITHIN = {"FE3": "Destination x product and year", "FE4": "Destination x product and destination x year",
                   "FE5": "Destination x product, destination x year and product x year"}
EV_FE = {
    "EV1": "Cell and year",
    "EV2": "Cell and origin x year (destination cells: also destination x year)",
    "EV3": "Product cells: adds type of production x year. Destination cells: cell and origin x destination x year",
    "EV4": "Product cells: adds HS chapter x year. Destination cells: adds product x year",
    "EV5": "Destination cells: cell and origin x product x year",
    "EV2T": "Cell and origin x year, plus a linear trend for each cell estimated on the years before entry",
    "EV2TF": "Cell and origin x year, plus a linear trend for each cell over all years",
}

# ---------------------------------------------------------------------------------------------------------------------
# variables
# ---------------------------------------------------------------------------------------------------------------------
REG = {"lnN": "ln number of MNEs", "D": "at least one MNE (0/1)", "S": "MNE share of exports", "DF": "at least one foreign MNE (0/1)",
       "DD": "at least one domestic MNE (0/1)", "logit": "at least one MNE (0/1), logit", "first entry": "first MNE enters this year (0/1)"}
EXPORTS = {"all": "exports of all firms", "local": "exports of local firms"}

# event study outcomes: name and the unit of the coefficient (used on the y axis of the figures)
OUT = {
    "anyXL": ("Local firms export (0/1)", "Change in the probability that local firms export"),
    "lnXL": ("ln exports of local firms", "Change in ln exports of local firms"),
    "lnX": ("ln exports of all firms", "Change in ln exports of all firms"),
    "lnXLpf": ("ln exports per local exporter", "Change in ln exports per local exporter"),
    "SHL": ("Local firms' share of exports (0 to 1)", "Change in the local share of exports"),
    "NL": ("Number of local exporters", "Change in the number of local exporters"),
    "lnNL": ("ln number of local exporters", "Change in ln number of local exporters"),
    "NEWL": ("New local exporters", "Change in the number of new local exporters"),
    "EXITL": ("Local exporters that stop exporting", "Change in the number of local exporters that stop"),
    "SURVL": ("Share of last year's local exporters that still export", "Change in the survival rate of local exporters"),
    "NDL": ("Destinations reached by local firms", "Change in destinations reached by local firms"),
    "NDA": ("Destinations reached by all firms", "Change in destinations reached by all firms"),
    "NEWDL": ("New destinations of local firms", "Change in new destinations of local firms"),
    "NEWDA": ("New destinations of all firms", "Change in new destinations of all firms"),
    "N": ("Number of MNEs", "Change in the number of MNEs"),
    "XL": ("Exports of local firms, levels (PPML)", "Change in exports of local firms (log points)"),
    "anyXLd": ("Local firms export (0/1), domestic MNEs counted as local", "Change in the probability that local firms export"),
    "lnXLd": ("ln exports of local firms, domestic MNEs counted as local", "Change in ln exports of local firms"),
    "NLd": ("Number of local exporters, domestic MNEs counted as local", "Change in the number of local exporters"),
    "NEWDL_go": ("New local destinations already served by the entering group from this country", "Change in new local destinations"),
    "NEWDL_xo": ("New local destinations not served by the entering group from this country", "Change in new local destinations"),
    "NEWDL_ga": ("New local destinations already served by the entering group from any country", "Change in new local destinations"),
    "NEWDL_xa": ("New local destinations not served by the entering group from any country", "Change in new local destinations"),
}


def out_name(y: str) -> str:
    return OUT.get(y, (y, y))[0]


def out_axis(y: str) -> str:
    return OUT.get(y, (y, y))[1]


# ---------------------------------------------------------------------------------------------------------------------
# event study: cells, samples, estimators, groups, terms
# ---------------------------------------------------------------------------------------------------------------------
CELLS = {"A": "product cells (origin x product, for example Chilean wine)",
         "B": "destination cells (origin x destination x product, for example Chilean wine to the United States)",
         "E": "new destination cells (origin x destination x product where local firms did not export before the MNE entered the product)"}
CELLS_SHORT = {"A": "Product cells", "B": "Destination cells", "E": "New destination cells"}
CELLS_FILE = {"A": "product", "B": "destination", "E": "new_destination"}
CLUSTER = {"A": "product cell", "B": "origin and destination pair", "E": "origin and destination pair"}

SAMPLE = {
    "g_ps": "Entered cells and comparison cells meet the same rule, the main comparison (two years with exports before the entry year; "
            "each comparison cell gets a placebo entry year drawn from the actual entry years)",
    "g_v4": "Rule of the v4 draft: entered cells need two years with exports before entry, comparison cells need two years with exports at any time",
    "g_nc": "No condition on the years with exports",
    "g_bal": "Only cells with exports in every year from 2012 to 2018",
    "g_pre3": "Three years with exports before the entry year, same rule for both groups",
    "g_for": "Event is the entry of the first foreign MNE (rule of the v4 draft)",
    "g_dom": "Event is the entry of the first domestic MNE (rule of the v4 draft)",
    "g_s10": "Event is an entry where the MNE has at least 10 percent of the cell's exports (rule of the v4 draft)",
    "g_s25": "Event is an entry where the MNE has at least 25 percent of the cell's exports (rule of the v4 draft)",
    "g_pers": "Event is an entry where the MNE is still there the next year (rule of the v4 draft)",
    "g_forps": "Event is the entry of the first foreign MNE, same rule for both groups",
    "g_domps": "Event is the entry of the first domestic MNE, same rule for both groups",
    "g_s10ps": "Event is an entry where the MNE has at least 10 percent of the cell's exports, same rule for both groups",
    "g_s25ps": "Event is an entry where the MNE has at least 25 percent of the cell's exports, same rule for both groups",
    "g_persps": "Event is an entry where the MNE is still there the next year, same rule for both groups",
    "g_be": "Destinations where local firms did not export before the MNE entered the product",
    "gpl": "Placebo: entry year moved three years earlier",
}
SAMPLE_SHORT = {
    "g_ps": "Same rule for both groups (main)", "g_v4": "Rule of the v4 draft", "g_nc": "No condition", "g_bal": "Cells exporting every year",
    "g_pre3": "Three years before entry", "g_for": "First foreign MNE (v4 rule)", "g_dom": "First domestic MNE (v4 rule)",
    "g_s10": "MNE with 10% or more (v4 rule)", "g_s25": "MNE with 25% or more (v4 rule)", "g_pers": "MNE still there next year (v4 rule)",
    "g_forps": "First foreign MNE", "g_domps": "First domestic MNE", "g_s10ps": "MNE with 10% or more of exports",
    "g_s25ps": "MNE with 25% or more of exports", "g_persps": "MNE still there next year", "g_be": "New destinations", "gpl": "Placebo",
}
SAMPLE_FILE = {"g_ps": "same_rule", "g_v4": "v4_rule", "g_nc": "no_condition", "g_bal": "exporting_every_year", "g_pre3": "three_years_before",
               "g_be": "new_destinations"}

EST = {"twfe": "OLS with fixed effects (TWFE)", "cs": "Callaway and Sant'Anna, not yet treated cells as controls",
       "csnev": "Callaway and Sant'Anna, never treated cells as controls", "sa": "Sun and Abraham", "bjs": "Borusyak, Jaravel and Spiess",
       "dcdh": "de Chaisemartin and D'Haultfoeuille", "stk": "Stacked regression by entry year", "TF": "OLS with a linear trend for each cell",
       "T": "Imputation with a linear trend for each cell", "jw": "Wooldridge, PPML", "fhs": "Freyaldenhoven, Hansen and Shapiro",
       "match": "Stacked regression with matched comparison cells (CEM)", "ppml": "PPML with fixed effects"}
EST_SHORT = {"twfe": "OLS (TWFE)", "cs": "Callaway and Sant'Anna", "csnev": "Callaway and Sant'Anna, never treated", "sa": "Sun and Abraham",
             "bjs": "Borusyak, Jaravel and Spiess", "dcdh": "de Chaisemartin and D'Haultfoeuille", "stk": "Stacked", "TF": "OLS with cell trends",
             "T": "Imputation with cell trends", "jw": "Wooldridge PPML", "fhs": "Freyaldenhoven et al.", "match": "Matched controls (CEM)",
             "ppml": "PPML"}

TERM = {"Tm4": "4 or more years before entry", "Tm3": "3 years before entry", "Tm2": "2 years before entry",
        "Tm1": "1 year before entry (reference year, shown only by BJS)", "Tp0": "Year of entry", "Tp1": "1 year after entry",
        "Tp2": "2 years after entry", "Tp3": "3 years after entry", "Tp4": "4 or more years after entry",
        "Post_avg": "Average effect, year of entry to 4 years after", "Av_tot": "Average total effect (dCDH)"}

CUT = {"high_mean": "Capital intensity (stage ratio)", "high_median": "Capital intensity (median)",
       "high_top": "Capital intensity (only the most capital intensive group is high)", "tercile_stage": "Capital intensity tercile",
       "type": "Type of production", "processing_degree": "Degree of processing", "high_PCI": "Product complexity (PCI)",
       "rauch_full_con": "Rauch class"}
TERCILE = {"1": "lowest", "1.0": "lowest", "2": "middle", "2.0": "middle", "3": "highest", "3.0": "highest"}


def group_name(g: str) -> str:
    if g == "all":
        return "All cells"
    if g.startswith("cohort"):
        return "Cells entered in " + g.split()[-1]
    if ":" in g:
        cut, v = [x.strip() for x in g.split(":", 1)]
        v = TERCILE.get(v, v) if cut == "tercile_stage" else v
        return f"{CUT.get(cut, cut)}: {v[:1].lower() + v[1:] if v in ('High', 'Low') else v}"
    return g


# ---------------------------------------------------------------------------------------------------------------------
# regression panels and columns
# ---------------------------------------------------------------------------------------------------------------------
ALT = {"KL_p (current)": "capital per worker (main measure)", "assets_pw": "farm assets per worker", "mach_per_acre": "machinery per acre",
       "mach_per_sales": "machinery per dollar of sales", "cap_pw": "capital per worker (industry capital stock)",
       "cap_per_va": "capital per dollar of value added"}


def _fe(s: str) -> str:
    return FE_WORDS.get(s, s)


def panel(p: str) -> str:
    """Panel label of a regression table in words."""
    m = re.match(r"^Location, (.*?), (D|S|lnN), FE (.*)$", p)
    if m:
        return f"Where MNEs are, by {m.group(1)}. Dependent variable: {REG[m.group(2)]}. Fixed effects: {_fe(m.group(3))}"
    m = re.match(r"^(Farm|Processing) stage, (D|S|lnN|DF|DD|logit|first entry), FE (.*)$", p)
    if m:
        return f"{m.group(1)} stage. Dependent variable: {REG[m.group(2)]}. Fixed effects: {_fe(m.group(3))}"
    m = re.match(r"^(Farm stage|Processing stage|Pooled stages), (lnN|D) x (.*), ln exports, (all|local) firms$", p)
    if m:
        st, r, cut, who = m.groups()
        return f"{st}. ln {EXPORTS[who]} on {REG[r]}, by {cut_words(cut)}"
    m = re.match(r"^(lnN|D)( and (?:lnN|D) x | x )(.*), ln exports, (all|local) firms$", p)
    if m:
        r, how, cut, who = m.groups()
        if "and" in how:
            return f"ln {EXPORTS[who]} on {REG[r]} and its interaction with {cut}"
        return f"ln {EXPORTS[who]} on {REG[r]}, by {cut_words(cut)}"
    return text(p)


def cut_words(cut: str) -> str:
    m = re.match(r"^high/low, threshold: (.*)$", cut)
    if m:
        return "high and low capital intensity, " + cutname(m.group(1))
    m = re.match(r"^high/low, export weighted median of (.*)$", cut)
    if m:
        return f"high and low {ALT.get(m.group(1), m.group(1))} (split at the median of exports)"
    cut = cut.replace("farm type or industry", "farm type (farm stage) or industry (processing stage)")
    cut = re.sub(r"(?<!PCI )terciles", "capital intensity terciles", cut)
    cut = re.sub(r"(?<!PCI )quartiles", "capital intensity quartiles", cut)
    cut = cut.replace("capital capital", "capital")
    return text(cut)


def text(s: str) -> str:
    """Token replacements for any remaining code in a label."""
    if not isinstance(s, str):
        return s
    reps = [(r"\bKL_p\b", "capital per worker"), (r"\bKL\b", "capital intensity"), (r"\bFE ([1-6])\b", r"FE\1"),
            (r"\bOY\b", "origin x year"), (r"\bODP\b", "origin x destination x product"), (r"\bODY\b", "origin x destination x year"),
            (r"\bOPY\b", "origin x product x year"), (r"\bDPY\b", "destination x product x year"), (r"\bhigh_mean\b", "capital intensity (stage ratio)"),
            (r"\bhigh_median\b", "capital intensity (median)"), (r"\bv_1218\b", "exports 2012 to 2018"), (r"\bsrc_id\b", "group"),
            (r"\bthreshold\b", "cut-off")]
    for a, b in reps:
        s = re.sub(a, b, s)
    for k, v in FE_WORDS.items():
        if k.startswith("FE"):
            s = re.sub(rf"\b{k}\b", v, s)
    return s


TEST = {"high = low": "high and low are equal", "all groups equal": "all groups are equal"}


def test_name(t: str) -> str:
    return "p value, test that " + TEST.get(t, t.replace(" = ", " and ") + " are equal" if " = " in t and not t.startswith("slope") else t)

# short names for figure files
OUT_FILE = {"anyXL": "local_firms_export", "lnXL": "local_exports", "lnX": "total_exports", "lnXLpf": "exports_per_local_exporter",
            "SHL": "local_share", "NL": "local_exporters", "lnNL": "ln_local_exporters", "NEWL": "new_local_exporters",
            "EXITL": "exiting_local_exporters", "SURVL": "survival_of_local_exporters", "NDL": "local_destinations", "NDA": "all_destinations",
            "NEWDL": "new_local_destinations", "NEWDA": "new_destinations_all_firms", "N": "number_of_MNEs", "XL": "local_exports_levels",
            "anyXLd": "local_firms_export_domestic_MNEs_as_local", "lnXLd": "local_exports_domestic_MNEs_as_local",
            "NLd": "local_exporters_domestic_MNEs_as_local", "NEWDL_go": "new_local_destinations_served_by_group_here",
            "NEWDL_xo": "new_local_destinations_not_served_by_group_here", "NEWDL_ga": "new_local_destinations_served_by_group_anywhere",
            "NEWDL_xa": "new_local_destinations_not_served_by_group_anywhere"}
CUT_FILE = {"high_mean": "capital_stage_ratio", "high_median": "capital_median", "high_top": "capital_top_group", "tercile_stage": "capital_terciles",
            "type": "type_of_production", "processing_degree": "degree_of_processing", "high_PCI": "complexity", "rauch_full_con": "rauch_class"}
EST_FILE = {"cs": "callaway_santanna", "twfe": "ols", "csnev": "callaway_santanna_never"}


def cutname(lab: str) -> str:
    """Names of the capital intensity cut-offs in words: 'gap at US$30 thousand (US$30.0 thousand)' -> 'cut-off at US$30 thousand'."""
    if not isinstance(lab, str):
        return lab
    s = re.sub(r"gap at (US\$[\d,.]+ thousand)(?: \(US\$[\d,.]+ thousand\))?", r"cut-off at \1", lab)
    for a, b in (("export weighted 75th percentile", "cut-off at the 75th percentile of exports"),
                 ("export weighted median", "cut-off at the median of exports"),
                 ("unweighted 75th percentile", "cut-off at the 75th percentile of products"),
                 ("unweighted median", "cut-off at the median product"),
                 ("aggregate ratio", "cut-off at the stage ratio, as in the v4 draft"),
                 ("pooled", "one cut-off for both stages,")):
        s = s.replace(a, b)
    return s


SAMPLE_ORDER = ["g_ps", "g_v4", "g_nc", "g_bal", "g_pre3", "g_be", "g_forps", "g_domps", "g_s10ps", "g_s25ps", "g_persps",
                "g_for", "g_dom", "g_s10", "g_s25", "g_pers"]
