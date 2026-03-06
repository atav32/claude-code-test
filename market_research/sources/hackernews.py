"""
Hacker News source.

Scans recent "Show HN" posts for new digital products/tools.
High-point Show HN posts with few comments = viral but niche = low competition.
We also flag "Ask HN" posts that match demand phrases.
"""

import logging
import re
from typing import List, Dict, Any

import requests

from market_research.config import (
    HN_MIN_POINTS,
    HN_MAX_POSTS,
    HIGH_MARGIN_KEYWORDS,
    DEMAND_PHRASES,
    MAX_PER_SOURCE,
)

logger = logging.getLogger(__name__)

_HN_SEARCH_URL  = "https://hn.algolia.com/api/v1/search_by_date"
_HN_ITEM_URL    = "https://hacker-news.firebaseio.com/v0/item/{}.json"
_REQUEST_TIMEOUT = 15


def _margin_boost(text: str) -> int:
    lower = text.lower()
    return min(sum(1 for kw in HIGH_MARGIN_KEYWORDS if kw in lower) * 8, 40)


def _demand_signal(text: str) -> bool:
    lower = text.lower()
    return any(phrase in lower for phrase in DEMAND_PHRASES)


def _fetch_show_hn(limit: int) -> List[dict]:
    """Fetch recent Show HN posts via Algolia HN API."""
    params = {
        "query":      "Show HN",
        "tags":       "story",
        "hitsPerPage": min(limit, 100),
    }
    try:
        r = requests.get(_HN_SEARCH_URL, params=params, timeout=_REQUEST_TIMEOUT)
        r.raise_for_status()
        return r.json().get("hits", [])
    except Exception as exc:
        logger.warning("HN Show HN fetch error: %s", exc)
        return []


def _fetch_ask_hn(limit: int) -> List[dict]:
    """Fetch recent Ask HN posts that express demand."""
    params = {
        "query":      "Ask HN: Is there",
        "tags":       "story",
        "hitsPerPage": min(limit, 100),
    }
    try:
        r = requests.get(_HN_SEARCH_URL, params=params, timeout=_REQUEST_TIMEOUT)
        r.raise_for_status()
        return r.json().get("hits", [])
    except Exception as exc:
        logger.warning("HN Ask HN fetch error: %s", exc)
        return []


def _hit_to_opportunity(hit: dict, post_type: str) -> Dict[str, Any] | None:
    points   = hit.get("points") or 0
    comments = hit.get("num_comments") or 0
    title    = hit.get("title", "").strip()
    story_id = hit.get("objectID", "")
    url      = hit.get("url") or f"https://news.ycombinator.com/item?id={story_id}"

    if points < HN_MIN_POINTS:
        return None

    boost = _margin_boost(title)

    if post_type == "show":
        # Low comment-to-point ratio = viral but niche
        niche_score = max(0, 100 - int((comments / max(points, 1)) * 150))
        description = (
            f"Show HN · {points} pts, {comments} comments | {title}"
        )
    else:
        # Ask HN demand post — check demand phrase
        if not _demand_signal(title):
            return None
        niche_score = 80   # unmet demand is inherently low competition
        description = (
            f"Ask HN demand signal · {points} pts, {comments} comments | {title}"
        )

    # Remove "Show HN: " prefix for cleaner title
    clean_title = re.sub(r"^(?:Show|Ask)\s+HN:\s*", "", title, flags=re.IGNORECASE)

    return {
        "source":      "Hacker News",
        "title":       clean_title or title,
        "description": description,
        "url":         url,
        "_points":       points,
        "_niche_score":  niche_score,
        "_margin_boost": boost,
        "_hn_type":      post_type,
    }


def fetch() -> List[Dict[str, Any]]:
    """Fetch Show HN and Ask HN posts, return Opportunity dicts."""
    show_hits = _fetch_show_hn(HN_MAX_POSTS)
    ask_hits  = _fetch_ask_hn(HN_MAX_POSTS // 2)

    results = []
    seen    = set()

    for hit in show_hits:
        opp = _hit_to_opportunity(hit, "show")
        if opp and opp["title"] not in seen:
            seen.add(opp["title"])
            results.append(opp)

    for hit in ask_hits:
        opp = _hit_to_opportunity(hit, "ask")
        if opp and opp["title"] not in seen:
            seen.add(opp["title"])
            results.append(opp)

    # Sort by composite signal
    results.sort(
        key=lambda x: x["_niche_score"] * (1 + x["_margin_boost"] / 40),
        reverse=True,
    )
    results = results[:MAX_PER_SOURCE]

    logger.info("Hacker News: found %d relevant posts.", len(results))
    return results
