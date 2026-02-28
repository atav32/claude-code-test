"""
Central configuration for data sources, paths, and scoring weights.
Edit this file to tune the scoring model or swap data sources.
"""
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
WEB_PUBLIC = ROOT / "web" / "public" / "data"

# Ensure directories exist
for d in [DATA_RAW, DATA_PROCESSED, WEB_PUBLIC]:
    d.mkdir(parents=True, exist_ok=True)

# ── NCES / CCD ──────────────────────────────────────────────────────────────
# Most recent available fiscal year for F-33 finance data
CCD_FISCAL_YEAR = 2022  # FY2022 = school year 2021-22

# Common Core of Data: district-level finance (F-33)
# https://nces.ed.gov/ccd/f33agency.asp
CCD_FINANCE_URL = (
    "https://nces.ed.gov/ccd/data/zip/f33fy{year}rv{rev}_dist_dat_1_0.zip"
)
CCD_FINANCE_YEAR = 2022
CCD_FINANCE_REV = "1a"  # revision suffix (update when NCES releases new revision)

# Common Core of Data: district directory (enrollment, locale, etc.)
# https://nces.ed.gov/ccd/ccddata.asp
CCD_DIRECTORY_URL = (
    "https://nces.ed.gov/ccd/data/zip/ccd_lea_{year}_l_1a_083023.zip"
)
CCD_DIRECTORY_YEAR = 2022

# NCES district boundary shapefiles (EDGE program)
# https://nces.ed.gov/programs/edge/Geographic/DistrictBoundaries
NCES_BOUNDARIES_URL = (
    "https://nces.ed.gov/programs/edge/data/EDGESCHOOLDISTRICT_TL23_SY2223.zip"
)

# ── NAEP ────────────────────────────────────────────────────────────────────
# NAEP Data Explorer API (state-level reading + math, grades 4 & 8)
# https://www.nationsreportcard.gov/api_specification.aspx
NAEP_API_BASE = "https://www.nationsreportcard.gov/DataService/GetAdhocData/byVariables"

# Subjects and grades we pull
NAEP_SUBJECTS = ["reading", "mathematics"]
NAEP_GRADES = [4, 8]
NAEP_YEAR = 2022  # Most recent NAEP assessment year

# ── Zillow ───────────────────────────────────────────────────────────────────
# Zillow Research bulk CSV downloads (no API key required)
# https://www.zillow.com/research/data/
ZILLOW_BASE = "https://files.zillowstatic.com/research/public_csvs"

# Zillow Home Value Index — $/sqft, all homes, ZIP level, monthly
ZHVI_SQFT_ZIP_URL = f"{ZILLOW_BASE}/zillow_home_value_index/Zip_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"

# Zillow Observed Rent Index — median rent, ZIP level, monthly
ZORI_ZIP_URL = f"{ZILLOW_BASE}/zori/Zip_zori_uc_sfrcondomfr_sm_month.csv"

# ── HUD ZIP ↔ School District crosswalk ──────────────────────────────────────
# https://www.huduser.gov/portal/datasets/usps_crosswalk.html
# Q4 of most recent calendar year
HUD_CROSSWALK_URL = (
    "https://www.huduser.gov/hudapi/public/usps?type=6&query=All"
)
# Fallback: direct CSV download (type 6 = ZIP → school district)
HUD_CROSSWALK_CSV_URL = (
    "https://www.huduser.gov/portal/datasets/usps/ZIP_SD_{year}Q4.xlsx"
)
HUD_CROSSWALK_YEAR = 2023

# ── Scoring weights ──────────────────────────────────────────────────────────
SCORE_WEIGHTS = {
    # Education quality sub-components (must sum to 1.0)
    "test_scores": 0.70,
    "per_pupil_spending": 0.30,
}

# Housing cost normalization: "metro" normalizes within each metro area,
# "national" normalizes against the full US distribution.
HOUSING_NORMALIZATION = "metro"

# Per-pupil spending: apply log transform to reduce outsized influence
# of very high-spending districts (true = log scale, false = linear)
SPENDING_LOG_SCALE = True

# Minimum number of students in a district to include in output
# (avoids noisy scores for tiny districts)
MIN_ENROLLMENT = 100
