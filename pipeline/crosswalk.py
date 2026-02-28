"""
Build a ZIP-to-school-district crosswalk and join Zillow housing cost data
onto school districts.

Sources:
  - HUD USPS ZIP → School District crosswalk (type 6)
    https://www.huduser.gov/portal/datasets/usps_crosswalk.html
  - Processed ZHVI sqft and ZORI rent from fetch_zillow.py

Strategy:
  A single ZIP code may overlap multiple school districts (and vice versa).
  HUD provides the fraction of residential addresses in each ZIP that fall
  within each district (RES_RATIO). We use this as a weight when aggregating
  Zillow data from ZIP → district.

Run:
    python pipeline/crosswalk.py
"""
import io
import logging
import requests
import pandas as pd
from pathlib import Path

from config import (
    DATA_RAW, DATA_PROCESSED,
    HUD_CROSSWALK_CSV_URL, HUD_CROSSWALK_YEAR,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)


# ── Fetch HUD crosswalk ───────────────────────────────────────────────────────

def fetch_hud_crosswalk() -> pd.DataFrame:
    """
    Download HUD ZIP → School District crosswalk.
    Returns DataFrame with: zip5, leaid, res_ratio (fraction of ZIP in district).

    HUD type-6 crosswalk maps each ZIP to the school districts whose
    boundaries overlap it, with RES_RATIO = share of residential addresses
    in the ZIP that fall in each district.
    """
    cache = DATA_PROCESSED / "hud_zip_to_district.parquet"
    if cache.exists():
        log.info("  cached  HUD ZIP→district crosswalk")
        return pd.read_parquet(cache)

    url = HUD_CROSSWALK_CSV_URL.format(year=HUD_CROSSWALK_YEAR)
    dest = DATA_RAW / f"hud_zip_sd_{HUD_CROSSWALK_YEAR}Q4.xlsx"

    if not dest.exists():
        log.info(f"  downloading  HUD crosswalk {HUD_CROSSWALK_YEAR}Q4")
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        dest.write_bytes(r.content)

    df = pd.read_excel(dest, dtype=str)
    df.columns = df.columns.str.upper()

    # Column names vary by year; normalize
    rename = {}
    for col in df.columns:
        if "ZIP" in col and "RES" not in col:
            rename[col] = "zip5"
        elif "SDID" in col or "SD_ID" in col or "SCHOOLDISTRICT" in col.replace("_", ""):
            rename[col] = "leaid"
        elif "RES_RATIO" in col or "RESRATIO" in col:
            rename[col] = "res_ratio"
    df = df.rename(columns=rename)

    required = {"zip5", "leaid", "res_ratio"}
    missing = required - set(df.columns)
    if missing:
        log.error(f"HUD crosswalk missing columns: {missing}. Available: {list(df.columns)}")
        # Return empty but valid DataFrame so pipeline can continue
        return pd.DataFrame(columns=["zip5", "leaid", "res_ratio"])

    df["zip5"] = df["zip5"].str.zfill(5)
    df["leaid"] = df["leaid"].str.zfill(7)
    df["res_ratio"] = pd.to_numeric(df["res_ratio"], errors="coerce").fillna(0)

    df = df[["zip5", "leaid", "res_ratio"]].dropna()
    log.info(f"HUD crosswalk: {len(df):,} ZIP-district pairs")
    df.to_parquet(cache, index=False)
    return df


# ── Join Zillow → districts ───────────────────────────────────────────────────

def join_housing_to_districts() -> pd.DataFrame:
    """
    Join Zillow ZHVI/sqft and ZORI/rent from ZIP level to district level
    using HUD RES_RATIO weights.

    For each district, the housing cost = weighted average of all ZIPs
    that overlap it, weighted by the share of residential addresses.

    Returns one row per district with: leaid, zhvi_sqft, zori_rent, metro.
    """
    cache = DATA_PROCESSED / "housing_by_district.parquet"
    if cache.exists():
        log.info("  cached  housing by district")
        return pd.read_parquet(cache)

    crosswalk = fetch_hud_crosswalk()
    zhvi = pd.read_parquet(DATA_PROCESSED / "zhvi_sqft_zip.parquet")
    zori = pd.read_parquet(DATA_PROCESSED / "zori_zip.parquet")

    # Merge Zillow data onto crosswalk
    merged = crosswalk.merge(
        zhvi[["zip5", "zhvi_sqft", "metro", "state"]],
        on="zip5", how="left",
    ).merge(
        zori[["zip5", "zori_rent"]],
        on="zip5", how="left",
    )

    def weighted_avg(group, val_col):
        """Compute res_ratio-weighted average, ignoring NaNs."""
        mask = group[val_col].notna()
        if mask.sum() == 0:
            return None
        w = group.loc[mask, "res_ratio"]
        v = group.loc[mask, val_col]
        total_w = w.sum()
        if total_w == 0:
            return v.mean()
        return (v * w).sum() / total_w

    log.info("  aggregating ZIP → district (weighted by res_ratio)…")
    result = (
        merged.groupby("leaid")
        .apply(
            lambda g: pd.Series({
                "zhvi_sqft": weighted_avg(g, "zhvi_sqft"),
                "zori_rent": weighted_avg(g, "zori_rent"),
                # Use the metro of the largest-weight ZIP
                "metro": g.sort_values("res_ratio", ascending=False)["metro"].iloc[0]
                         if "metro" in g.columns else None,
                "state": g.sort_values("res_ratio", ascending=False)["state"].iloc[0]
                         if "state" in g.columns else None,
            })
        )
        .reset_index()
    )

    log.info(
        f"Housing by district: {len(result):,} districts | "
        f"ZHVI coverage: {result['zhvi_sqft'].notna().sum():,} | "
        f"ZORI coverage: {result['zori_rent'].notna().sum():,}"
    )
    result.to_parquet(cache, index=False)
    return result


if __name__ == "__main__":
    log.info("=== Building ZIP → district crosswalk ===")
    fetch_hud_crosswalk()
    join_housing_to_districts()
    log.info("=== Done ===")
