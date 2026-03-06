"""
Reddit source.

Searches TARGET_SUBREDDITS for posts containing DEMAND_PHRASES —
"is there a tool for X", "looking for software that does Y", etc.
These indicate unmet demand (low competition) in a specific niche.
"""

import logging
import re
from typing import List, Dict, Any

import praw

from market_research.config import (
    REDDIT_CLIENT_ID,
    REDDIT_CLIENT_SECRET,
    REDDIT_USER_AGENT,
    TARGET_SUBREDDITS,
    DEMAND_PHRASES,
    HIGH_MARGIN_KEYWORDS,
    MAX_PER_SOURCE,
)

logger = logging.getLogger(__name__)

_POSTS_PER_SUBREDDIT = 100   # how many hot/new posts to scan per subreddit


def _build_reddit() -> praw.Reddit:
    return praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
        read_only=True,
    )


def _contains_demand_phrase(text: str) -> str | None:
    """Return the matched demand phrase, or None."""
    lower = text.lower()
    for phrase in DEMAND_PHRASES:
        if phrase in lower:
            return phrase
    return None


def _margin_keywords_hit(text: str) -> int:
    lower = text.lower()
    return sum(1 for kw in HIGH_MARGIN_KEYWORDS if kw in lower)


def _score_post(post: praw.models.Submission) -> Dict[str, Any] | None:
    """Return an Opportunity dict if the post signals unmet demand, else None."""
    full_text = f"{post.title} {post.selftext}"
    phrase    = _contains_demand_phrase(full_text)
    if not phrase:
        return None

    kw_hits      = _margin_keywords_hit(full_text)
    upvote_ratio = post.upvote_ratio or 0.5
    score        = post.score or 0

    # Engagement signal: highly upvoted demand = many people have same pain
    engagement = min(score * upvote_ratio / 10, 100)

    # Shorten selftext for description
    snippet = re.sub(r"\s+", " ", post.selftext[:300]).strip()
    if not snippet:
        snippet = post.title

    return {
        "source":      "Reddit",
        "title":       post.title,
        "description": (
            f"r/{post.subreddit.display_name} · {score} upvotes · "
            f"Matched phrase: \"{phrase}\"\n{snippet}"
        ),
        "url":         f"https://www.reddit.com{post.permalink}",
        "_engagement":   engagement,    # 0-100
        "_margin_boost": min(kw_hits * 8, 40),
        "_demand_phrase": phrase,
        "_subreddit":  post.subreddit.display_name,
    }


def fetch() -> List[Dict[str, Any]]:
    """Scan subreddits for unmet-demand posts and return Opportunity dicts."""
    if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
        logger.warning("Reddit credentials not set — skipping Reddit source.")
        return []

    reddit  = _build_reddit()
    results = []
    seen    = set()

    for sub_name in TARGET_SUBREDDITS:
        try:
            sub   = reddit.subreddit(sub_name)
            posts = list(sub.new(limit=_POSTS_PER_SUBREDDIT // 2)) + \
                    list(sub.hot(limit=_POSTS_PER_SUBREDDIT // 2))
        except Exception as exc:
            logger.warning("Reddit error for r/%s: %s", sub_name, exc)
            continue

        for post in posts:
            if post.id in seen:
                continue
            seen.add(post.id)

            opp = _score_post(post)
            if opp:
                results.append(opp)

    # Sort by engagement descending, cap at MAX_PER_SOURCE
    results.sort(key=lambda x: x["_engagement"], reverse=True)
    results = results[:MAX_PER_SOURCE]

    logger.info("Reddit: found %d demand-signal posts.", len(results))
    return results
