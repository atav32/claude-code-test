"""
Fetch and clean NCES data:
  - CCD F-33: district-level per-pupil spending (fiscal)
  - CCD Directory: district enrollment, locale codes
  - NAEP API: state-level reading + math scores (grades 4 & 8)
  - NCES EDGE: district boundary shapefiles

Run:
    python pipeline/fetch_nces.py
"""
import io
import zipfile
import logging
import requests
import pandas as pd
import geopandas as gpd
from pathlib import Path

from config import (
    DATA_RAW, DATA_PROCESSED,
    CCD_FINANCE_URL, CCD_FINANCE_YEAR, CCD_FINANCE_REV,
    CCD_DIRECTORY_URL, CCD_DIRECTORY_YEAR,
    NCES_BOUNDARIES_URL,
    NAEP_API_BASE, NAEP_SUBJECTS, NAEP_GRADES, NAEP_YEAR,
    MIN_ENROLLMENT,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)


# ── helpers ──────────────────────────────────────────────────────────────────

def _download(url: str, dest: Path, desc: str) -> Path:
    """Download a file if not already cached."""
    if dest.exists():
        log.info(f"  cached  {desc}")
        return dest
    log.info(f"  downloading  {desc}")
    r = requests.get(url, timeout=120, stream=True)
    r.raise_for_status()
    dest.write_bytes(r.content)
    log.info(f"  saved → {dest}")
    return dest


def _unzip_single(zip_path: Path, suffix: str) -> pd.DataFrame:
    """Open a zip, find the first file matching suffix, return as DataFrame."""
    with zipfile.ZipFile(zip_path) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(suffix)]
        if not names:
            raise FileNotFoundError(
                f"No *{suffix} file found in {zip_path}. Contents: {zf.namelist()}"
            )
        with zf.open(names[0]) as f:
            if suffix == ".csv":
                return pd.read_csv(f, encoding="latin-1", low_memory=False)
            elif suffix in (".xlsx", ".xls"):
                return pd.read_excel(f)
    raise ValueError(f"Unsupported suffix: {suffix}")


# ── CCD Finance (F-33) ───────────────────────────────────────────────────────

def fetch_ccd_finance() -> pd.DataFrame:
    """
    Download CCD F-33 district finance data and extract:
      - LEAID (district NCES ID)
      - TOTALREV (total revenue)
      - TOTALEXP (total expenditure)
      - V33 (current expenditure per pupil in ADA) — the primary spending metric
      - MEMBERSCH (membership / enrollment used for per-pupil calc)

    Returns a DataFrame with one row per district.
    """
    url = CCD_FINANCE_URL.format(year=CCD_FINANCE_YEAR, rev=CCD_FINANCE_REV)
    dest = DATA_RAW / f"ccd_finance_{CCD_FINANCE_YEAR}.zip"
    _download(url, dest, f"CCD F-33 FY{CCD_FINANCE_YEAR}")

    df = _unzip_single(dest, ".csv")

    # Standardize column names to uppercase
    df.columns = df.columns.str.upper()

    keep = {
        "LEAID": "leaid",
        "STID": "state_agency_id",
        "TOTALREV": "total_revenue",
        "TFEDREV": "federal_revenue",
        "TSTREV": "state_revenue",
        "TLOCREV": "local_revenue",
        "TOTALEXP": "total_expenditure",
        "TCURSSVC": "current_exp_instruction",  # current exp on instruction
        "V33": "current_exp_per_pupil",          # the headline $/pupil metric
        "MEMBERSCH": "membership",
    }
    available = {k: v for k, v in keep.items() if k in df.columns}
    df = df[list(available.keys())].rename(columns=available)

    # NCES uses negative values to flag missing / not applicable
    numeric_cols = [c for c in df.columns if c != "leaid"]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
    df[numeric_cols] = df[numeric_cols].where(df[numeric_cols] >= 0)

    # Pad LEAID to 7 digits (standard NCES format)
    df["leaid"] = df["leaid"].astype(str).str.zfill(7)

    log.info(f"CCD Finance: {len(df):,} districts")
    out = DATA_PROCESSED / "ccd_finance.parquet"
    df.to_parquet(out, index=False)
    return df


# ── CCD Directory ────────────────────────────────────────────────────────────

def fetch_ccd_directory() -> pd.DataFrame:
    """
    Download CCD LEA (district) directory and extract:
      - LEAID, NAME, STATE, LOCALE code, ENROLLMENT, LAT, LON
    """
    url = CCD_DIRECTORY_URL.format(year=CCD_DIRECTORY_YEAR)
    dest = DATA_RAW / f"ccd_directory_{CCD_DIRECTORY_YEAR}.zip"
    _download(url, dest, f"CCD Directory {CCD_DIRECTORY_YEAR}")

    df = _unzip_single(dest, ".csv")
    df.columns = df.columns.str.upper()

    keep = {
        "LEAID": "leaid",
        "LEA_NAME": "district_name",
        "STABBR": "state",
        "LEANM": "lea_name_alt",
        "LOCALE": "locale_code",   # urban/suburban/rural taxonomy
        "ENROLLMENT": "enrollment",
        "LATCOD": "lat",
        "LONCOD": "lon",
        "GSLO": "grade_low",
        "GSHI": "grade_high",
    }
    available = {k: v for k, v in keep.items() if k in df.columns}
    df = df[list(available.keys())].rename(columns=available)

    df["leaid"] = df["leaid"].astype(str).str.zfill(7)
    df["enrollment"] = pd.to_numeric(df["enrollment"], errors="coerce")
    df = df[df["enrollment"] >= MIN_ENROLLMENT].copy()

    log.info(f"CCD Directory: {len(df):,} districts (enrollment ≥ {MIN_ENROLLMENT})")
    out = DATA_PROCESSED / "ccd_directory.parquet"
    df.to_parquet(out, index=False)
    return df


# ── NAEP API ─────────────────────────────────────────────────────────────────

NAEP_SUBJECT_CODES = {"reading": "NDEReadingState", "mathematics": "NDEMathState"}

def _fetch_naep_subject_grade(subject: str, grade: int, year: int) -> pd.DataFrame:
    """
    Call the NAEP Data Explorer API for one subject/grade combination.
    Returns state-level average scale scores.
    """
    # NAEP API endpoint for state average scores
    # Docs: https://www.nationsreportcard.gov/api_specification.aspx
    url = "https://www.nationsreportcard.gov/DataService/GetAdhocData/byVariables"
    params = {
        "subject": subject,
        "grade": grade,
        "subscale": "OMPCS" if subject == "mathematics" else "ORPCS",
        "variable": "TOTAL",
        "jurisdiction": "ST",   # ST = all states
        "stattype": "MN:MN",    # mean scale score
        "Year": year,
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()

    rows = []
    for item in data.get("result", []):
        rows.append({
            "state": item.get("Jurisdiction", ""),
            "subject": subject,
            "grade": grade,
            "year": year,
            "avg_score": item.get("Value"),
            "se": item.get("StandardError"),
        })
    return pd.DataFrame(rows)


def fetch_naep() -> pd.DataFrame:
    """
    Fetch NAEP scores for all subjects × grades, compute a composite
    state-level education score, and save to processed/.

    Returns one row per state with columns:
      state, naep_reading_g4, naep_math_g4, naep_reading_g8, naep_math_g8,
      naep_composite (simple average of the four scaled scores)
    """
    cache = DATA_PROCESSED / f"naep_{NAEP_YEAR}.parquet"
    if cache.exists():
        log.info("  cached  NAEP scores")
        return pd.read_parquet(cache)

    dfs = []
    for subject in NAEP_SUBJECTS:
        for grade in NAEP_GRADES:
            log.info(f"  fetching NAEP {subject} grade {grade} {NAEP_YEAR}")
            try:
                df = _fetch_naep_subject_grade(subject, grade, NAEP_YEAR)
                dfs.append(df)
            except Exception as e:
                log.warning(f"  NAEP fetch failed ({subject} g{grade}): {e}")

    if not dfs:
        log.warning("No NAEP data fetched. Creating empty placeholder.")
        return pd.DataFrame(columns=["state", "naep_composite"])

    long = pd.concat(dfs, ignore_index=True)
    long["avg_score"] = pd.to_numeric(long["avg_score"], errors="coerce")

    # Pivot to wide format: one column per subject-grade combo
    wide = long.pivot_table(
        index="state",
        columns=["subject", "grade"],
        values="avg_score",
        aggfunc="first",
    )
    wide.columns = [f"naep_{s}_g{g}" for s, g in wide.columns]
    wide = wide.reset_index()

    score_cols = [c for c in wide.columns if c.startswith("naep_")]
    wide["naep_composite"] = wide[score_cols].mean(axis=1)

    log.info(f"NAEP: {len(wide)} states/jurisdictions")
    wide.to_parquet(cache, index=False)
    return wide


# ── Boundary shapefiles ───────────────────────────────────────────────────────

def fetch_boundaries() -> gpd.GeoDataFrame:
    """
    Download NCES EDGE school district boundary shapefiles.
    Returns a GeoDataFrame with LEAID + geometry (WGS84).
    """
    dest = DATA_RAW / "nces_district_boundaries.zip"
    _download(NCES_BOUNDARIES_URL, dest, "NCES district boundaries")

    cache = DATA_PROCESSED / "district_boundaries.parquet"
    if cache.exists():
        log.info("  cached  district boundaries")
        return gpd.read_parquet(cache)

    with zipfile.ZipFile(dest) as zf:
        # Extract to a temp folder
        extract_dir = DATA_RAW / "boundaries"
        extract_dir.mkdir(exist_ok=True)
        zf.extractall(extract_dir)

    shp_files = list(extract_dir.rglob("*.shp"))
    if not shp_files:
        raise FileNotFoundError(f"No .shp file found after extracting {dest}")

    gdf = gpd.read_file(shp_files[0])
    gdf = gdf.to_crs("EPSG:4326")  # WGS84 for Leaflet

    # Normalize LEAID
    id_col = next((c for c in gdf.columns if "LEAID" in c.upper()), None)
    if id_col:
        gdf = gdf.rename(columns={id_col: "leaid"})
        gdf["leaid"] = gdf["leaid"].astype(str).str.zfill(7)

    # Keep only geometry + leaid
    gdf = gdf[["leaid", "geometry"]].copy()
    gdf.to_parquet(cache, index=False)
    log.info(f"Boundaries: {len(gdf):,} districts")
    return gdf


if __name__ == "__main__":
    log.info("=== Fetching NCES data ===")
    fetch_ccd_finance()
    fetch_ccd_directory()
    fetch_naep()
    fetch_boundaries()
    log.info("=== Done ===")
