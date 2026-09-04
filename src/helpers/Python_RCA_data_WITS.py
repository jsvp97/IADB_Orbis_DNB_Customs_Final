"""
WITS RCA Downloader — reporter × product × year
===============================================
Downloads Revealed Comparative Advantage (RCA / Balassa index) from the
World Bank WITS TradeStats API at the reporter-country × product × year level,
against the World (WLD) as partner.

Requirements:
    pip install requests pandas tqdm

Usage:
    python download_wits_rca.py

Output:
    wits_rca_hs6.csv  —  columns: reporter, year, product_code, rca

Notes:
    - The API does NOT allow ALL reporters + ALL products in one call.
      This script loops over reporters (countries) one at a time.
    - Each call fetches ALL available product groups for one country across ALL available years.
      (The TradeStats API product dimension is product *groups*; it is not HS6.)
    - Rate-limiting: a small sleep is added between calls to avoid 429 errors.
    - If a run is interrupted, the script resumes from where it left off
      (already-downloaded countries are skipped).
    - Typical full run: ~2-4 hours depending on connection speed.
"""

import requests
import pandas as pd
import time
import os
import json
import xml.etree.ElementTree as ET
from typing import Optional
from tqdm import tqdm

# ── Configuration ──────────────────────────────────────────────────────────────
BASE_URL   = "https://wits.worldbank.org/API/V1/SDMX/V21/rest/data/DF_WITS_TradeStats_Trade"
PARTNER    = "WLD"          # World = global RCA
INDICATOR  = "RCA"          # Balassa Revealed Comparative Advantage
OUTPUT_CSV = "wits_rca_hs6.csv"
TEMP_DIR   = "wits_rca_temp"  # folder for per-country temp files (for resuming)
SLEEP_SEC  = 1.5             # pause between requests (be polite to the server)
MAX_RETRIES = 3              # retries on HTTP errors
START_YEAR = 2006
END_YEAR   = 2022

# If True, keep only numeric 6-digit product codes.
# NOTE: For DF_WITS_TradeStats_Trade, product codes are typically product-group labels
# (e.g., "01-05_Animal"), not HS6. Leaving this True will likely filter everything out.
KEEP_ONLY_6DIGIT_NUMERIC_PRODUCTS = False

os.makedirs(TEMP_DIR, exist_ok=True)

# ── Step 1: Get list of all reporter countries ──────────────────────────────────
def get_reporters():
    """
    Fetch all available reporter ISO3 country codes.

    The original WITS metadata endpoint for reporters sometimes returns HTTP 405
    ("Method Not Allowed"), so instead we use the World Bank country metadata
    API, which exposes the same ISO3 codes.
    """
    url = "https://api.worldbank.org/v2/country?per_page=400&format=json"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()

    # data[1] is the list of countries; each has an 'id' that is the ISO3 code.
    countries = data[1]
    reporters = [
        c["id"]
        for c in countries
        if c.get("id") and c["id"] not in ("WLD", "all")
    ]
    print(f"Found {len(reporters)} reporter countries.")
    return reporters


# ── Step 2: Fetch RCA for one country, all HS6 products, all years ─────────────
def fetch_rca_for_country(iso3: str) -> Optional[pd.DataFrame]:
    """
    Call WITS SDMX API for a single reporter.
    Returns a DataFrame with columns: reporter, year, product_code, rca
    or None if no data is available.

    SDMX key structure:
        FREQ . REPORTER . PARTNER . PRODUCTCODE . INDICATOR
        A    . {iso3}   . WLD     . (wildcard)   . RCA

    Note:
        WITS rejects PRODUCTCODE=ALL with HTTP 400 ("Invalid Product Code").
        In SDMX REST, an empty dimension (.. between dots) is the wildcard.
    """
    key = f"A.{iso3}.{PARTNER}..{INDICATOR}"
    url = f"{BASE_URL}/{key}"
    params = {"startPeriod": str(START_YEAR), "endPeriod": str(END_YEAR)}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(url, params=params, timeout=60)
            if r.status_code == 404:
                return None   # country has no data
            if r.status_code == 429:
                wait = 30 * attempt
                print(f"  Rate limited for {iso3}, waiting {wait}s …")
                time.sleep(wait)
                continue
            r.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            if attempt == MAX_RETRIES:
                print(f"  ERROR for {iso3}: {e}")
                return None
            time.sleep(5 * attempt)

    # ── Parse SDMX GenericData XML response ─────────────────────────────────────
    # WITS currently returns SDMX-ML GenericData (XML) rather than SDMX-JSON.
    rows = []
    try:
        root = ET.fromstring(r.content)
    except ET.ParseError:
        return None

    def local(tag: str) -> str:
        return tag.rsplit("}", 1)[-1] if "}" in tag else tag

    # Iterate series; each series key includes PRODUCTCODE and observations include TIME + value
    for series in root.iter():
        if local(series.tag) != "Series":
            continue

        product_code = None
        for child in series:
            if local(child.tag) != "SeriesKey":
                continue
            for v in child:
                if local(v.tag) == "Value" and v.get("id") == "PRODUCTCODE":
                    product_code = v.get("value")
                    break
            break

        if not product_code or product_code == "TOTAL":
            continue

        for obs in series:
            if local(obs.tag) != "Obs":
                continue
            year = None
            value = None
            for part in obs:
                t = local(part.tag)
                if t == "ObsDimension":
                    year = part.get("value")
                elif t == "ObsValue":
                    value = part.get("value")
            if not year or value is None:
                continue
            try:
                y = int(year)
            except ValueError:
                continue
            if START_YEAR <= y <= END_YEAR:
                try:
                    val = float(value)
                except ValueError:
                    continue
                rows.append(
                    {"reporter": iso3, "year": y, "product_code": product_code, "rca": val}
                )

    if not rows:
        return None

    return pd.DataFrame(rows)


# ── Step 3: Main loop ──────────────────────────────────────────────────────────
def main():
    reporters = get_reporters()

    # Check which countries already have temp files (resume support)
    done = {f.replace(".parquet", "") for f in os.listdir(TEMP_DIR)
            if f.endswith(".parquet")}
    print(f"Already downloaded: {len(done)} countries. Remaining: {len(reporters)-len(done)}")

    for iso3 in tqdm(reporters, desc="Countries"):
        if iso3 in done:
            continue

        df = fetch_rca_for_country(iso3)

        if df is not None and not df.empty:
            df.to_parquet(os.path.join(TEMP_DIR, f"{iso3}.parquet"), index=False)
        else:
            # Write empty marker so we don't retry a country with no data
            pd.DataFrame(columns=["reporter","year","product_code","rca"])\
              .to_parquet(os.path.join(TEMP_DIR, f"{iso3}.parquet"), index=False)

        time.sleep(SLEEP_SEC)

    # ── Step 4: Combine all temp files into one CSV ────────────────────────────
    print("\nCombining all country files …")
    all_files = [os.path.join(TEMP_DIR, f)
                 for f in os.listdir(TEMP_DIR) if f.endswith(".parquet")]
    dfs = [pd.read_parquet(f) for f in all_files]
    non_empty = [d for d in dfs if d is not None and not d.empty]
    if not non_empty:
        pd.DataFrame(columns=["reporter", "year", "product_code", "rca"]).to_csv(
            OUTPUT_CSV, index=False
        )
        print(f"\nDone! No data returned by API. Wrote empty {OUTPUT_CSV}")
        return

    full = pd.concat(non_empty, ignore_index=True)

    if KEEP_ONLY_6DIGIT_NUMERIC_PRODUCTS:
        full = full[full["product_code"].astype(str).str.match(r"^\d{6}$", na=False)]
    full = full.sort_values(["reporter", "year", "product_code"]).reset_index(drop=True)

    full.to_csv(OUTPUT_CSV, index=False)
    print(f"\nDone! Saved {len(full):,} rows to {OUTPUT_CSV}")
    print(full.head(10).to_string())


if __name__ == "__main__":
    main()