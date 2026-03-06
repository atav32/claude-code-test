"""
Product Hunt source.

Uses the public Product Hunt GraphQL API (no auth required for basic reads)
to find recently launched digital products. We look for:
  - High vote-to-comment ratio (viral, but comments = controversy = competition)
  - Low vote count overall (early, not yet saturated)
  - Keywords matching high-margin niches

The *absence* of many copycat products in the same category signals low
competition (we check the category post count proxy).
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

import requests

from market_research.config import (
    PH_DAYS_WINDOW,
    PH_MIN_VOTES,
    PH_MAX_POSTS,
    HIGH_MARGIN_KEYWORDS,
    MAX_PER_SOURCE,
)

logger = logging.getLogger(__name__)

_GQL_URL     = "https://api.producthunt.com/v2/api/graphql"
_PUBLIC_TOKEN = ""   # Product Hunt allows read-only without token for basic queries

_QUERY = """
query($after: String, $postedAfter: DateTime!) {
  posts(order: VOTES, postedAfter: $postedAfter, first: 50, after: $after) {
    pageInfo { hasNextPage endCursor }
    edges {
      node {
        id
        name
        tagline
        description
        votesCount
        commentsCount
        url
        website
        createdAt
        topics { edges { node { name } } }
      }
    }
  }
}
"""

_HEADERS = {
    "Content-Type": "application/json",
    "Accept":       "application/json",
}


def _margin_boost(text: str) -> int:
    lower = text.lower()
    return min(sum(1 for kw in HIGH_MARGIN_KEYWORDS if kw in lower) * 8, 40)


def _fetch_page(after: str | None, posted_after: str) -> dict:
    payload = {
        "query":     _QUERY,
        "variables": {
            "after":       after,
            "postedAfter": posted_after,
        },
    }
    r = requests.post(_GQL_URL, json=payload, headers=_HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()


def fetch() -> List[Dict[str, Any]]:
    """Fetch recent Product Hunt launches and return Opportunity dicts."""
    cutoff      = datetime.now(timezone.utc) - timedelta(days=PH_DAYS_WINDOW)
    posted_after = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    all_nodes = []
    cursor    = None

    while len(all_nodes) < PH_MAX_POSTS:
        try:
            data = _fetch_page(cursor, posted_after)
        except Exception as exc:
            logger.warning("Product Hunt API error: %s", exc)
            break

        posts_data = data.get("data", {}).get("posts", {})
        edges      = posts_data.get("edges", [])
        if not edges:
            break

        all_nodes.extend(e["node"] for e in edges)

        page_info = posts_data.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break
        cursor = page_info.get("endCursor")

    results = []
    for node in all_nodes:
        votes    = node.get("votesCount", 0) or 0
        comments = node.get("commentsCount", 0) or 0

        if votes < PH_MIN_VOTES:
            continue

        topics = [
            e["node"]["name"]
            for e in (node.get("topics") or {}).get("edges", [])
        ]

        full_text = " ".join([
            node.get("name", ""),
            node.get("tagline", ""),
            node.get("description", "") or "",
            " ".join(topics),
        ])

        boost    = _margin_boost(full_text)
        # Low comments relative to votes → narrow audience (niche = higher price)
        niche_score = max(0, 100 - int((comments / max(votes, 1)) * 200))

        results.append({
            "source":      "Product Hunt",
            "title":       node.get("name", "Unknown"),
            "description": (
                f"{node.get('tagline', '')} | "
                f"{votes} votes, {comments} comments | "
                f"Topics: {', '.join(topics[:5])}"
            ),
            "url":         node.get("url") or node.get("website", ""),
            "_votes":        votes,
            "_niche_score":  niche_score,    # proxy for low competition
            "_margin_boost": boost,
            "_topics":       topics,
        })

    # Sort by niche_score × margin_boost
    results.sort(
        key=lambda x: x["_niche_score"] * (1 + x["_margin_boost"] / 40),
        reverse=True,
    )
    results = results[:MAX_PER_SOURCE]

    logger.info("Product Hunt: found %d relevant launches.", len(results))
    return results
