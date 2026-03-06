"""
Market Research Tool – main entry point.

Usage:
  # Run once immediately:
  python -m market_research.main

  # Run on a daily schedule (blocks forever):
  python -m market_research.main --schedule

Options:
  --schedule          Run daily at the configured time (default 07:00 local)
  --time HH:MM        Schedule time (24h format, default 07:00)
  --no-email          Print digest to stdout instead of sending email
  --save PATH         Save JSON results to file (default: last_run.json)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import schedule

from market_research.sources import google_trends, reddit, product_hunt, hackernews
from market_research.analysis.scorer       import score_and_filter
from market_research.analysis.deduplicator import deduplicate
from market_research.reporting.email_digest import send_email, build_html

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

_DEFAULT_SAVE_PATH = Path(__file__).parent / "last_run.json"


# ── Core pipeline ─────────────────────────────────────────────────────────────

def run_pipeline(no_email: bool = False, save_path: Path = _DEFAULT_SAVE_PATH) -> List[Dict[str, Any]]:
    """
    Full pipeline: fetch → score → deduplicate → report.
    Returns the final ranked list.
    """
    logger.info("=== Market Research Tool — %s ===", datetime.now().strftime("%Y-%m-%d %H:%M"))

    # 1. Fetch from all sources (errors are caught inside each module)
    logger.info("Fetching from Google Trends…")
    trends_opps = google_trends.fetch()

    logger.info("Fetching from Reddit…")
    reddit_opps = reddit.fetch()

    logger.info("Fetching from Product Hunt…")
    ph_opps = product_hunt.fetch()

    logger.info("Fetching from Hacker News…")
    hn_opps = hackernews.fetch()

    all_opps = trends_opps + reddit_opps + ph_opps + hn_opps
    logger.info("Total raw opportunities: %d", len(all_opps))

    # 2. Score and filter
    scored = score_and_filter(all_opps)
    logger.info("After scoring/filtering (threshold): %d", len(scored))

    # 3. Deduplicate
    final = deduplicate(scored)
    logger.info("After deduplication: %d", len(final))

    if not final:
        logger.warning("No opportunities passed the threshold today.")
        return []

    # 4. Save JSON snapshot
    _save_json(final, save_path)

    # 5. Report
    if no_email:
        _print_digest(final)
    else:
        send_email(final)

    return final


# ── Helpers ───────────────────────────────────────────────────────────────────

def _save_json(opportunities: List[Dict[str, Any]], path: Path) -> None:
    """Save a clean (no private "_" keys) snapshot to JSON."""
    clean = [
        {k: v for k, v in opp.items() if not k.startswith("_")}
        for opp in opportunities
    ]
    path.write_text(json.dumps(clean, indent=2, ensure_ascii=False))
    logger.info("Results saved to %s", path)


def _print_digest(opportunities: List[Dict[str, Any]]) -> None:
    """Print a plain-text summary to stdout."""
    print(f"\n{'='*60}")
    print(f"  MARKET RESEARCH DIGEST — {datetime.now().strftime('%Y-%m-%d')}")
    print(f"  {len(opportunities)} opportunities found")
    print(f"{'='*60}\n")
    for i, opp in enumerate(opportunities, 1):
        print(
            f"#{i:2d} [{opp['composite_score']:3d}] "
            f"[{opp['source']:<15s}] "
            f"M:{opp['margin_score']:3d} C:{opp['competition_score']:3d}  "
            f"{opp['title']}"
        )
        print(f"      {opp['url']}")
        print()


# ── CLI / scheduler ───────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Daily market research tool — finds high-margin, low-competition niches."
    )
    parser.add_argument(
        "--schedule", action="store_true",
        help="Keep running and execute daily at --time.",
    )
    parser.add_argument(
        "--time", default="07:00", metavar="HH:MM",
        help="Daily run time in 24h format (default: 07:00).",
    )
    parser.add_argument(
        "--no-email", action="store_true",
        help="Print results to stdout instead of sending an email.",
    )
    parser.add_argument(
        "--save", default=str(_DEFAULT_SAVE_PATH), metavar="PATH",
        help=f"Path to save JSON results (default: {_DEFAULT_SAVE_PATH}).",
    )
    return parser.parse_args()


def main() -> None:
    args      = _parse_args()
    save_path = Path(args.save)

    def _job():
        try:
            run_pipeline(no_email=args.no_email, save_path=save_path)
        except Exception as exc:
            logger.exception("Pipeline failed: %s", exc)

    if args.schedule:
        logger.info("Scheduling daily run at %s.", args.time)
        schedule.every().day.at(args.time).do(_job)
        # Run immediately on first start, then follow the schedule
        _job()
        while True:
            schedule.run_pending()
            time.sleep(30)
    else:
        _job()


if __name__ == "__main__":
    main()
