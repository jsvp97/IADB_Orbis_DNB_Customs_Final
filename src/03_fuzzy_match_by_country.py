"""
03_fuzzy_match_by_country.py
============================
TF-IDF Fuzzy Name Matching — Customs Exporters vs. Orbis/DNB Corporate Database
(Country-by-country pass, 10 LAC countries)

PURPOSE
-------
Matches firm names from customs export microdata against the Orbis/DNB
corporate database using TF-IDF character n-gram vectorisation and approximate
nearest-neighbour search. This is Stage 2 of the matching pipeline described
in 02_match_customs_mne.do.

A separate match is run for each of the 10 LAC countries to improve precision:
matching against a country-specific subset of the corporate database reduces
false positives that arise from cross-country name collisions.

METHOD
------
1. Build a TF-IDF matrix from the Orbis/DNB name list (reference corpus).
2. Vectorise the customs firm names (query corpus) using the same vocabulary.
3. Use NMSLIB's inverted-index approximate nearest-neighbour to find the
   k=2 closest Orbis/DNB names for each customs firm name.
4. Export match pairs and similarity scores to CSV for AI review (see
   02_match_customs_mne.do Stage 2b for the AI validation prompt).

INPUTS  (relative to project root / data/intermediate/)
--------
  Orbis_DNB_name_aff_[ISO3].csv     — Orbis/DNB firm names by country
  list_exporters_10c_ALC_[ISO3].csv — customs exporter names by country

OUTPUTS (relative to project root / data/intermediate/)
---------
  fuzzy_match_[ISO3].csv            — match pairs with similarity score (conf)

COUNTRIES: ARG, CHL, COL, CRI, DOM, ECU, PER, PRY, SLV, URY

DEPENDENCIES
------------
  See requirements.txt. Key packages: scikit-learn, nmslib, ftfy, pandas.

NOTE ON SIMILARITY SCORE
------------------------
  The `conf` column is the negative dot-product similarity from NMSLIB's
  negdotprod_sparse_fast space. Values closer to 0 = higher similarity.
  Downstream AI review keeps candidates with conf > -0.6.

AUTHORS
-------
  Sebastian Velasquez (IDB)
  Approach based on sparse TF-IDF fuzzy matching (Tate, 2021).

LAST UPDATED: March 2026
"""

import os
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd
import nmslib
from ftfy import fix_text
from sklearn.feature_extraction.text import TfidfVectorizer
from tqdm import tqdm  # optional progress bars

# ---------------------------------------------------------------------------
# PATH CONFIGURATION
# All input/output paths are derived from the project root automatically.
# No manual path editing required — just run from the project directory.
# ---------------------------------------------------------------------------

project_root = Path(__file__).resolve().parent.parent
data_int     = project_root / "data" / "intermediate"


# ---------------------------------------------------------------------------
# TEXT NORMALISATION
# ---------------------------------------------------------------------------

def ngrams(string: str, n: int = 3) -> list:
    """
    Convert a company name string into character n-grams for TF-IDF.

    Normalisation steps applied before n-gramming:
      1. Lowercase
      2. Fix unicode/encoding artefacts (ftfy)
      3. Remove 'trading as' prefixes — keep only the primary name
      4. Strip non-ASCII characters
      5. Remove common punctuation  )( . | [ ] { } ' -
      6. Title-case normalisation
      7. Collapse multiple spaces
      8. Pad with leading/trailing spaces for edge n-grams
    """
    string = str(string).lower()
    string = fix_text(string)
    string = string.split("t/a")[0]
    string = string.split("trading as")[0]
    string = string.encode("ascii", errors="ignore").decode()

    chars_to_remove = list(r")(.|[]{}'-")
    rx = "[" + re.escape("".join(chars_to_remove)) + "]"
    string = re.sub(rx, "", string)
    string = string.title()
    string = re.sub(r" +", " ", string).strip()
    string = " " + string + " "  # pad for edge n-grams

    return ["".join(ngram) for ngram in zip(*[string[i:] for i in range(n)])]


# ---------------------------------------------------------------------------
# MATCHING FUNCTION
# ---------------------------------------------------------------------------

def run_fuzzy_match(
    ref_csv: Path,
    ref_col: str,
    query_csv: Path,
    query_col: str,
    output_csv: Path,
    k: int = 2,
    num_threads: int = 4,
) -> None:
    """
    Run TF-IDF + NMSLIB approximate nearest-neighbour matching.

    Parameters
    ----------
    ref_csv    : Path to reference corpus CSV (Orbis/DNB names)
    ref_col    : Column name for firm names in ref_csv
    query_csv  : Path to query corpus CSV (customs exporter names)
    query_col  : Column name for firm names in query_csv
    output_csv : Path for output CSV (match pairs + similarity score)
    k          : Number of nearest neighbours to retrieve per query
    num_threads: Threads for NMSLIB batch query
    """
    print(f"\n{'='*60}")
    print(f"Reference : {ref_csv.name}  [{ref_col}]")
    print(f"Query     : {query_csv.name}  [{query_col}]")
    print(f"Output    : {output_csv.name}")
    print(f"{'='*60}")

    # Build TF-IDF matrix from reference corpus (Orbis/DNB names)
    t0 = time.time()
    df_ref    = pd.read_csv(ref_csv, encoding="latin1")
    ref_names = list(df_ref[ref_col].unique().astype("U"))

    vectorizer    = TfidfVectorizer(min_df=1, analyzer=ngrams)
    tf_idf_matrix = vectorizer.fit_transform(ref_names)
    print(f"  TF-IDF matrix: {tf_idf_matrix.shape}  ({time.time()-t0:.1f}s)")

    # Vectorise query corpus (customs names) using same vocabulary
    df_query     = pd.read_csv(query_csv, encoding="latin1")
    query_names  = list(df_query[query_col].unique().astype("U"))
    query_matrix = vectorizer.transform(query_names)

    # Build NMSLIB inverted index on reference corpus
    index = nmslib.init(
        method="simple_invindx",
        space="negdotprod_sparse_fast",
        data_type=nmslib.DataType.SPARSE_VECTOR,
    )
    index.addDataPointBatch(tf_idf_matrix)

    t1 = time.time()
    index.createIndex()
    print(f"  Index built ({time.time()-t1:.1f}s)")

    # Query: find k nearest neighbours for each customs firm name
    t2 = time.time()
    nbrs      = index.knnQueryBatch(query_matrix, k=k, num_threads=num_threads)
    n_queries = query_matrix.shape[0]
    elapsed   = time.time() - t2
    print(f"  kNN query: {elapsed:.1f}s total  ({elapsed/n_queries:.4f}s per query)")

    # Collect match pairs
    rows = []
    for i, query_name in enumerate(query_names):
        try:
            matched_name = ref_names[nbrs[i][0][0]]
            conf         = nbrs[i][1][0]
        except (IndexError, TypeError):
            matched_name = "no match found"
            conf         = None
        rows.append([query_name, matched_name, conf])

    matches = pd.DataFrame(rows, columns=["original_name", "matched_name", "conf"])
    results = df_query.merge(matches, left_on=query_col, right_on="original_name")
    results.to_csv(output_csv, index=False)
    print(f"  Saved {len(results):,} rows -> {output_csv}")


# ---------------------------------------------------------------------------
# MAIN — run per-country matches for all 10 LAC countries
# ---------------------------------------------------------------------------

COUNTRIES = ["ARG", "CHL", "COL", "CRI", "DOM", "ECU", "PER", "PRY", "SLV", "URY"]

if __name__ == "__main__":
    print(f"Project root : {project_root}")
    print(f"Data folder  : {data_int}")

    for iso3 in COUNTRIES:
        ref_csv   = data_int / f"Orbis_DNB_name_aff_{iso3}.csv"
        query_csv = data_int / f"list_exporters_10c_ALC_{iso3}.csv"
        out_csv   = data_int / f"fuzzy_match_{iso3}.csv"

        if not ref_csv.exists():
            print(f"[SKIP] Reference file not found: {ref_csv.name}")
            continue
        if not query_csv.exists():
            print(f"[SKIP] Query file not found: {query_csv.name}")
            continue

        run_fuzzy_match(
            ref_csv    = ref_csv,
            ref_col    = "company_name",
            query_csv  = query_csv,
            query_col  = "firm_name",
            output_csv = out_csv,
        )

    print("\nAll country-level fuzzy matches complete.")
    print("Next: run AI review on data/intermediate/ia_review/Match_preIA_*.csv")
    print("      (see AI prompt in 02_match_customs_mne.do, Stage 2b)")
