"""
Master pipeline runner. Runs all steps in order.

Usage:
    python pipeline/run_pipeline.py [--steps all|fetch|score|export]

Steps:
    fetch   — download raw data from NCES, Zillow, HUD
    score   — build master dataset and compute value scores
    export  — join with boundaries, write GeoJSON for the frontend

Run all steps:
    python pipeline/run_pipeline.py

Run only scoring (if data is already fetched):
    python pipeline/run_pipeline.py --steps score,export
"""
import argparse
import logging
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def run_fetch():
    from fetch_nces import fetch_ccd_finance, fetch_ccd_directory, fetch_naep, fetch_boundaries
    from fetch_zillow import fetch_zhvi_sqft, fetch_zori
    from crosswalk import fetch_hud_crosswalk, join_housing_to_districts

    log.info("── Step 1: Fetch NCES data ─────────────────────────────────")
    fetch_ccd_finance()
    fetch_ccd_directory()
    fetch_naep()
    fetch_boundaries()

    log.info("── Step 2: Fetch Zillow data ───────────────────────────────")
    fetch_zhvi_sqft()
    fetch_zori()

    log.info("── Step 3: Build ZIP → district crosswalk ──────────────────")
    fetch_hud_crosswalk()
    join_housing_to_districts()


def run_score():
    from score import run
    log.info("── Step 4: Compute scores ──────────────────────────────────")
    run()


def run_export():
    from export import export_geojson
    log.info("── Step 5: Export GeoJSON ──────────────────────────────────")
    export_geojson()


STEPS = {
    "fetch": run_fetch,
    "score": run_score,
    "export": run_export,
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the edu-value-map data pipeline")
    parser.add_argument(
        "--steps",
        default="all",
        help="Comma-separated steps to run: fetch,score,export  (default: all)",
    )
    args = parser.parse_args()

    if args.steps == "all":
        selected = list(STEPS.keys())
    else:
        selected = [s.strip() for s in args.steps.split(",")]

    unknown = set(selected) - set(STEPS)
    if unknown:
        log.error(f"Unknown steps: {unknown}. Valid: {list(STEPS)}")
        sys.exit(1)

    start = time.time()
    log.info(f"Running pipeline steps: {selected}")
    for step in selected:
        STEPS[step]()

    elapsed = time.time() - start
    log.info(f"Pipeline complete in {elapsed:.1f}s")
