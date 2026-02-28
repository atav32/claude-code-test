"""
Composite Education Value Score

Methodology
-----------
1. Education Quality Score (0–100):
     70%  NAEP composite (state-level avg scale score, normalized nationally)
     30%  Per-pupil spending (log-transformed, normalized nationally)

   Note: NAEP is state-level for most districts. The ~27 TUDA (Trial Urban
   District Assessment) districts have their own scores — this script uses
   district-level scores where available, falls back to state average.

2. Housing Cost Index (0–100):
     For-sale: ZHVI $/sqft normalized within each metro area
     Rental:   ZORI median rent normalized within each metro area
   "Within metro" means a district with cheap housing in an expensive metro
   scores highly, while cheap housing in a cheap rural area scores average.

3. Value Score = Education Score / Housing Cost Index, scaled 0–10.
   Higher = better education for the cost.

Run:
    python pipeline/score.py
"""
import logging
import numpy as np
import pandas as pd
from pathlib import Path

from config import (
    DATA_PROCESSED,
    SCORE_WEIGHTS,
    HOUSING_NORMALIZATION,
    SPENDING_LOG_SCALE,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)


# ── Normalization helpers ─────────────────────────────────────────────────────

def normalize_percentile(series: pd.Series) -> pd.Series:
    """Map values to [0, 100] using percentile rank (robust to outliers)."""
    return series.rank(pct=True) * 100


def normalize_percentile_within_group(
    df: pd.DataFrame, value_col: str, group_col: str
) -> pd.Series:
    """Normalize within each group (e.g., within each metro)."""
    return (
        df.groupby(group_col)[value_col]
        .rank(pct=True)
        .mul(100)
    )


# ── Build master dataset ──────────────────────────────────────────────────────

def build_master() -> pd.DataFrame:
    """
    Join all processed datasets into one master DataFrame.
    One row per school district.
    """
    log.info("Loading processed data…")

    directory = pd.read_parquet(DATA_PROCESSED / "ccd_directory.parquet")
    finance = pd.read_parquet(DATA_PROCESSED / "ccd_finance.parquet")
    housing = pd.read_parquet(DATA_PROCESSED / "housing_by_district.parquet")
    naep = pd.read_parquet(DATA_PROCESSED / "naep_2022.parquet")  # state-level

    # Start from directory (defines the universe of districts)
    master = directory.merge(finance[["leaid", "current_exp_per_pupil"]], on="leaid", how="left")
    master = master.merge(housing, on="leaid", how="left")

    # Map state-level NAEP scores onto districts
    # NAEP uses full state names or abbreviations; CCD uses 2-letter abbreviations
    if "state" in naep.columns:
        # Normalize state identifier (NAEP may return abbreviations or full names)
        naep_clean = naep[["state", "naep_composite"]].copy()
        naep_clean["state"] = naep_clean["state"].str.strip()

        # Try joining on state abbreviation first
        master = master.merge(naep_clean, on="state", how="left")

    log.info(
        f"Master dataset: {len(master):,} districts | "
        f"NAEP coverage: {master['naep_composite'].notna().sum():,} | "
        f"Spending coverage: {master['current_exp_per_pupil'].notna().sum():,} | "
        f"ZHVI coverage: {master['zhvi_sqft'].notna().sum():,}"
    )
    return master


# ── Scoring ───────────────────────────────────────────────────────────────────

def compute_scores(master: pd.DataFrame) -> pd.DataFrame:
    """
    Compute education quality score, housing cost index, and value scores.
    Returns master DataFrame with added score columns.
    """
    df = master.copy()

    # ── 1. Education score ────────────────────────────────────────────────────

    # Test score component (NAEP composite, nationally normalized)
    df["score_test"] = normalize_percentile(df["naep_composite"])

    # Per-pupil spending component
    spending = df["current_exp_per_pupil"].copy()
    if SPENDING_LOG_SCALE:
        spending = np.log1p(spending)  # log(1+x) handles zeros/NaN gracefully
    df["score_spending"] = normalize_percentile(spending)

    # Weighted education quality score
    w = SCORE_WEIGHTS
    df["education_score"] = (
        w["test_scores"] * df["score_test"].fillna(50) +
        w["per_pupil_spending"] * df["score_spending"].fillna(50)
    )
    # Districts with no data at all get NaN (not 50) — mark as missing
    both_missing = df["naep_composite"].isna() & df["current_exp_per_pupil"].isna()
    df.loc[both_missing, "education_score"] = np.nan

    # ── 2. Housing cost index ─────────────────────────────────────────────────

    if HOUSING_NORMALIZATION == "metro":
        # Normalize within each metro; fall back to national for districts
        # without a metro assignment (rural districts)
        group_col = df["metro"].fillna("__national__")

        df["housing_cost_buy"] = normalize_percentile_within_group(
            df.assign(metro_group=group_col), "zhvi_sqft", "metro_group"
        ).values

        df["housing_cost_rent"] = normalize_percentile_within_group(
            df.assign(metro_group=group_col), "zori_rent", "metro_group"
        ).values
    else:
        df["housing_cost_buy"] = normalize_percentile(df["zhvi_sqft"])
        df["housing_cost_rent"] = normalize_percentile(df["zori_rent"])

    # ── 3. Value scores ───────────────────────────────────────────────────────
    # Value = education / housing cost, higher housing cost → lower value.
    # We invert cost (100 - cost) so higher value = better deal.

    def value_score(edu_score: pd.Series, cost_index: pd.Series) -> pd.Series:
        """
        Compute (education - cost) score, then scale to 0–10.
        Using difference rather than ratio avoids division instability
        near zero while preserving the relative ordering.
        """
        raw = edu_score - cost_index  # range roughly -100 to +100
        # Scale to 0–10 using percentile rank
        scaled = raw.rank(pct=True) * 10
        return scaled.round(2)

    df["value_score_buy"] = value_score(df["education_score"], df["housing_cost_buy"])
    df["value_score_rent"] = value_score(df["education_score"], df["housing_cost_rent"])

    # Round scores for output
    for col in ["education_score", "score_test", "score_spending",
                "housing_cost_buy", "housing_cost_rent"]:
        df[col] = df[col].round(1)

    log.info(
        f"Scored {df['value_score_buy'].notna().sum():,} districts (buy) | "
        f"{df['value_score_rent'].notna().sum():,} (rent)"
    )
    return df


# ── Grade labels ──────────────────────────────────────────────────────────────

def assign_grade(score: float) -> str:
    """Convert 0–10 value score to A+/A/B/C/D letter grade."""
    if pd.isna(score):
        return "N/A"
    if score >= 9.0:
        return "A+"
    if score >= 8.0:
        return "A"
    if score >= 7.0:
        return "B+"
    if score >= 6.0:
        return "B"
    if score >= 5.0:
        return "C+"
    if score >= 4.0:
        return "C"
    if score >= 3.0:
        return "D"
    return "F"


def run() -> pd.DataFrame:
    master = build_master()
    scored = compute_scores(master)
    scored["grade_buy"] = scored["value_score_buy"].apply(assign_grade)
    scored["grade_rent"] = scored["value_score_rent"].apply(assign_grade)

    out = DATA_PROCESSED / "scored_districts.parquet"
    scored.to_parquet(out, index=False)
    log.info(f"Saved scored districts → {out}")
    return scored


if __name__ == "__main__":
    log.info("=== Computing scores ===")
    run()
    log.info("=== Done ===")
