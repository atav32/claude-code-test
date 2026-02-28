"""
Export scored districts to GeoJSON for the frontend map.

Produces two files in web/public/data/:
  districts.geojson   — full national dataset (district polygons + scores)
  districts-meta.json — summary stats used by the frontend (score ranges, etc.)

The GeoJSON is pre-computed so the frontend has no backend dependency.
It can be served as a static file from Vercel, GitHub Pages, etc.

Run:
    python pipeline/export.py
"""
import json
import logging
import numpy as np
import pandas as pd
import geopandas as gpd
from pathlib import Path

from config import DATA_PROCESSED, WEB_PUBLIC

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

# Columns to include in GeoJSON properties (keep payload lean)
EXPORT_COLS = [
    "leaid",
    "district_name",
    "state",
    "metro",
    "enrollment",
    "locale_code",
    # Education
    "education_score",
    "score_test",
    "score_spending",
    "naep_composite",
    "current_exp_per_pupil",
    # Housing
    "zhvi_sqft",
    "zori_rent",
    "housing_cost_buy",
    "housing_cost_rent",
    # Value scores
    "value_score_buy",
    "value_score_rent",
    "grade_buy",
    "grade_rent",
]


def export_geojson() -> None:
    """
    Join scored districts with boundary polygons and write GeoJSON.
    Splits into state-level files to keep individual file sizes manageable.
    """
    log.info("Loading scored districts and boundary shapefiles…")
    scored = pd.read_parquet(DATA_PROCESSED / "scored_districts.parquet")
    boundaries = gpd.read_parquet(DATA_PROCESSED / "district_boundaries.parquet")

    # Keep only columns that exist in scored
    export_cols = [c for c in EXPORT_COLS if c in scored.columns]
    data = scored[export_cols].copy()

    # Join geometry
    gdf = boundaries.merge(data, on="leaid", how="inner")
    gdf = gdf[gdf.geometry.notna()]

    # Simplify geometry to reduce file size (tolerance in degrees ≈ 0.01° ≈ 1km)
    gdf["geometry"] = gdf["geometry"].simplify(tolerance=0.01, preserve_topology=True)

    # Replace NaN with None for valid JSON
    for col in gdf.columns:
        if col == "geometry":
            continue
        if gdf[col].dtype in [np.float64, np.float32]:
            gdf[col] = gdf[col].where(gdf[col].notna(), other=None)

    log.info(f"Total districts with geometry: {len(gdf):,}")

    # ── National file ─────────────────────────────────────────────────────────
    national_path = WEB_PUBLIC / "districts.geojson"
    log.info(f"  writing national GeoJSON → {national_path}")
    gdf.to_file(national_path, driver="GeoJSON")
    size_mb = national_path.stat().st_size / 1e6
    log.info(f"  size: {size_mb:.1f} MB")

    # ── Per-state files (for lazy loading) ────────────────────────────────────
    state_dir = WEB_PUBLIC / "states"
    state_dir.mkdir(exist_ok=True)

    if "state" in gdf.columns:
        for state, group in gdf.groupby("state"):
            if not state or str(state).strip() in ("", "nan"):
                continue
            out = state_dir / f"{state.upper()}.geojson"
            group.to_file(out, driver="GeoJSON")
        log.info(f"  wrote {gdf['state'].nunique()} state files → {state_dir}")

    # ── Metadata JSON ─────────────────────────────────────────────────────────
    meta = {
        "generated": pd.Timestamp.now().isoformat(),
        "district_count": len(gdf),
        "score_ranges": {
            "value_score_buy": {
                "min": float(gdf["value_score_buy"].min()) if "value_score_buy" in gdf.columns else None,
                "max": float(gdf["value_score_buy"].max()) if "value_score_buy" in gdf.columns else None,
                "mean": float(gdf["value_score_buy"].mean()) if "value_score_buy" in gdf.columns else None,
            },
            "value_score_rent": {
                "min": float(gdf["value_score_rent"].min()) if "value_score_rent" in gdf.columns else None,
                "max": float(gdf["value_score_rent"].max()) if "value_score_rent" in gdf.columns else None,
                "mean": float(gdf["value_score_rent"].mean()) if "value_score_rent" in gdf.columns else None,
            },
        },
        "states": sorted(gdf["state"].dropna().unique().tolist()) if "state" in gdf.columns else [],
        "metros": sorted(gdf["metro"].dropna().unique().tolist()) if "metro" in gdf.columns else [],
    }
    meta_path = WEB_PUBLIC / "districts-meta.json"
    meta_path.write_text(json.dumps(meta, indent=2))
    log.info(f"  metadata → {meta_path}")


if __name__ == "__main__":
    log.info("=== Exporting GeoJSON ===")
    export_geojson()
    log.info("=== Done ===")
