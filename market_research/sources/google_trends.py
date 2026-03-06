"""
Google Trends source.

Uses pytrends to discover rising related queries for seed keywords.
Returns Opportunity dicts with trend momentum as the competition signal.
"""

import logging
import time
from typing import List, Dict, Any

from pytrends.request import TrendReq

from market_research.config import (
    TREND_SEED_KEYWORDS,
    TREND_MIN_BREAKOUT_SCORE,
    HIGH_MARGIN_KEYWORDS,
)

logger = logging.getLogger(__name__)

_PYTRENDS_TIMEFRAME = "today 3-m"   # last 3 months for rising queries
_REQUEST_DELAY_S    = 1.5           # polite delay between API calls


def _keyword_margin_boost(text: str) -> int:
    """Return 0-40 based on how many high-margin keywords appear in text."""
    lower = text.lower()
    hits  = sum(1 for kw in HIGH_MARGIN_KEYWORDS if kw in lower)
    return min(hits * 8, 40)


def _parse_rising_value(val) -> int:
    """
    pytrends returns an int (0-4950+) or the string 'Breakout' (>5000%).
    Normalise to 0-100.
    """
    if val == "Breakout":
        return 100
    try:
        return min(int(val) // 50, 100)   # 5000% → 100, 500% → 10, etc.
    except (TypeError, ValueError):
        return 0


def fetch() -> List[Dict[str, Any]]:
    """
    Iterate over seed keywords, pull rising related queries, and return a
    list of Opportunity dicts.
    """
    pytrends   = TrendReq(hl="en-US", tz=0, timeout=(10, 25))
    results    = []
    seen_terms = set()

    for seed in TREND_SEED_KEYWORDS:
        try:
            pytrends.build_payload([seed], timeframe=_PYTRENDS_TIMEFRAME)
            related = pytrends.related_queries()
            time.sleep(_REQUEST_DELAY_S)
        except Exception as exc:
            logger.warning("Google Trends error for seed '%s': %s", seed, exc)
            continue

        rising_df = related.get(seed, {}).get("rising")
        if rising_df is None or rising_df.empty:
            continue

        for _, row in rising_df.iterrows():
            term  = str(row["query"]).strip()
            value = row["value"]

            if term in seen_terms:
                continue
            seen_terms.add(term)

            trend_score  = _parse_rising_value(value)
            if trend_score < (TREND_MIN_BREAKOUT_SCORE // 50):
                continue

            margin_boost = _keyword_margin_boost(term)

            results.append({
                "source":      "Google Trends",
                "title":       term,
                "description": (
                    f"Rising Google search query (related to '{seed}'). "
                    f"Trend growth score: {value}."
                ),
                "url":         (
                    f"https://trends.google.com/trends/explore"
                    f"?q={term.replace(' ', '+')}&geo=US"
                ),
                # Raw signals — scorer.py will normalise these
                "_trend_score":  trend_score,    # 0-100 (competition proxy: lower = fresher)
                "_margin_boost": margin_boost,   # 0-40 bonus
                "_raw_value":    value,
            })

    logger.info("Google Trends: found %d rising queries.", len(results))
    return results
