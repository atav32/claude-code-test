"""
Fetch Zillow Research bulk CSV files (no API key required):
  - ZHVI (Zillow Home Value Index) $/sqft by ZIP — for-sale proxy
  - ZORI (Zillow Observed Rent Index) median rent by ZIP

Zillow updates these monthly. Re-run this script to refresh.

Run:
    python pipeline/fetch_zillow.py
"""
import logging
import requests
import pandas as pd
from pathlib import Path

from config import (
    DATA_RAW, DATA_PROCESSED,
    ZHVI_SQFT_ZIP_URL,
    ZORI_ZIP_URL,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)


def _download_zillow_csv(url: str, dest: Path, desc: str) -> pd.DataFrame:
    """Download a Zillow CSV (or use cache) and return as DataFrame."""
    if dest.exists():
        log.info(f"  cached  {desc}")
    else:
        log.info(f"  downloading  {desc}")
        r = requests.get(url, timeout=120, stream=True)
        r.raise_for_status()
        dest.write_bytes(r.content)
        log.info(f"  saved → {dest}")
    return pd.read_csv(dest, dtype={"RegionName": str})


def _latest_monthly_value(df: pd.DataFrame, id_cols: list[str]) -> pd.DataFrame:
    """
    Zillow CSVs are wide format: one column per month (YYYY-MM-DD).
    Melt to long, then keep only the single most-recent non-null value per row.
    Returns df with id_cols + 'latest_value' + 'latest_date'.
    """
    date_cols = [c for c in df.columns if c[:4].isdigit() and "-" in c]
    if not date_cols:
        raise ValueError("No date columns found in Zillow CSV")

    # Sort date columns chronologically and take the most recent non-null
    date_cols_sorted = sorted(date_cols)

    result = df[id_cols].copy()
    values = df[date_cols_sorted].copy()

    # Walk backwards to find latest non-null
    result["latest_value"] = values.apply(
        lambda row: next((row[c] for c in reversed(date_cols_sorted) if pd.notna(row[c])), None),
        axis=1,
    )
    result["latest_date"] = values.apply(
        lambda row: next((c for c in reversed(date_cols_sorted) if pd.notna(row[c])), None),
        axis=1,
    )
    return result


def fetch_zhvi_sqft() -> pd.DataFrame:
    """
    Download Zillow ZHVI $/sqft (all homes, middle tier) at ZIP level.
    Returns one row per ZIP with: zip5, state, metro, zhvi_sqft, zhvi_date.
    """
    dest = DATA_RAW / "zhvi_sqft_zip.csv"
    df = _download_zillow_csv(ZHVI_SQFT_ZIP_URL, dest, "Zillow ZHVI $/sqft by ZIP")

    id_cols = ["RegionName", "State", "Metro", "CountyName", "SizeRank"]
    id_cols = [c for c in id_cols if c in df.columns]

    result = _latest_monthly_value(df, id_cols)
    result = result.rename(columns={
        "RegionName": "zip5",
        "State": "state",
        "Metro": "metro",
        "CountyName": "county",
        "SizeRank": "size_rank",
        "latest_value": "zhvi_sqft",
        "latest_date": "zhvi_date",
    })

    result["zip5"] = result["zip5"].astype(str).str.zfill(5)
    result["zhvi_sqft"] = pd.to_numeric(result["zhvi_sqft"], errors="coerce")
    result = result.dropna(subset=["zhvi_sqft"])

    log.info(f"ZHVI sqft: {len(result):,} ZIPs, latest date: {result['zhvi_date'].max()}")
    out = DATA_PROCESSED / "zhvi_sqft_zip.parquet"
    result.to_parquet(out, index=False)
    return result


def fetch_zori() -> pd.DataFrame:
    """
    Download Zillow ZORI (observed rent index) at ZIP level.
    Returns one row per ZIP with: zip5, state, metro, zori_rent, zori_date.
    """
    dest = DATA_RAW / "zori_zip.csv"
    df = _download_zillow_csv(ZORI_ZIP_URL, dest, "Zillow ZORI rent by ZIP")

    id_cols = ["RegionName", "State", "Metro", "CountyName", "SizeRank"]
    id_cols = [c for c in id_cols if c in df.columns]

    result = _latest_monthly_value(df, id_cols)
    result = result.rename(columns={
        "RegionName": "zip5",
        "State": "state",
        "Metro": "metro",
        "CountyName": "county",
        "SizeRank": "size_rank",
        "latest_value": "zori_rent",
        "latest_date": "zori_date",
    })

    result["zip5"] = result["zip5"].astype(str).str.zfill(5)
    result["zori_rent"] = pd.to_numeric(result["zori_rent"], errors="coerce")
    result = result.dropna(subset=["zori_rent"])

    log.info(f"ZORI rent: {len(result):,} ZIPs, latest date: {result['zori_date'].max()}")
    out = DATA_PROCESSED / "zori_zip.parquet"
    result.to_parquet(out, index=False)
    return result


if __name__ == "__main__":
    log.info("=== Fetching Zillow data ===")
    fetch_zhvi_sqft()
    fetch_zori()
    log.info("=== Done ===")
