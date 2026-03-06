"""
Scoring engine.

Takes raw Opportunity dicts from any source and normalises them into a
unified 0-100 composite score with two sub-scores:

  margin_score       — estimated profit margin potential (higher = better)
  competition_score  — estimated lack of competition (higher = less competition)
  composite_score    — weighted average of the two

Each source attaches private "_*" keys with its own signals.
This module reads those signals, normalises them, and adds the three score keys.
"""

from __future__ import annotations

import re
from typing import List, Dict, Any

from market_research.config import (
    WEIGHT_MARGIN_SIGNAL,
    WEIGHT_COMPETITION_SIGNAL,
    MIN_SCORE_THRESHOLD,
    HIGH_MARGIN_KEYWORDS,
)

# ── Margin scoring ────────────────────────────────────────────────────────────

# Categories that indicate high willingness-to-pay (B2B, regulated industries)
_PREMIUM_PATTERNS = re.compile(
    r"\b("
    r"b2b|enterprise|saas|api|platform|compliance|security|payroll|billing|"
    r"invoice|legal|contract|healthcare|medical|fintech|insurance|real estate|"
    r"logistics|supply chain|recruiting|hr|erp|crm|analytics|audit|gdpr|hipaa"
    r")\b",
    re.IGNORECASE,
)

# Signals that indicate commodity / low-margin space
_COMMODITY_PATTERNS = re.compile(
    r"\b("
    r"free|open.?source|cheap|budget|simple|basic|todo|notes|chat|meme|fun|"
    r"game|dating|social|photo|music|video|streaming|entertainment"
    r")\b",
    re.IGNORECASE,
)


def _base_margin_score(opp: Dict[str, Any]) -> int:
    """Return 0-60 base margin score from keyword analysis."""
    text      = f"{opp['title']} {opp['description']}"
    premium   = len(_PREMIUM_PATTERNS.findall(text))
    commodity = len(_COMMODITY_PATTERNS.findall(text))
    raw       = premium * 12 - commodity * 10
    return max(0, min(60, raw))


def _margin_score(opp: Dict[str, Any]) -> int:
    """Full 0-100 margin score combining base + source-specific boost."""
    base   = _base_margin_score(opp)
    boost  = opp.get("_margin_boost", 0)   # 0-40, set by each source
    return min(100, base + boost)


# ── Competition scoring ───────────────────────────────────────────────────────

def _competition_score(opp: Dict[str, Any]) -> int:
    """
    Return 0-100 competition score (100 = nearly zero competition).

    Logic differs by source:
      Google Trends  → fresh rising queries = low competition
      Reddit         → high engagement on demand posts = unmet need
      Product Hunt   → niche_score already computed
      Hacker News    → niche_score already computed
    """
    source = opp["source"]

    if source == "Google Trends":
        # trend_score is 0-100 where 100 = "Breakout" (>5000% growth)
        # A breakout term is VERY fresh → low competition ceiling
        trend = opp.get("_trend_score", 50)
        # Invert: a trend_score of 100 means brand-new = least competition
        return min(100, trend)

    elif source == "Reddit":
        # High engagement on a demand post = real unmet need
        engagement = opp.get("_engagement", 30)
        return min(100, int(engagement))

    elif source == "Product Hunt":
        return opp.get("_niche_score", 50)

    elif source == "Hacker News":
        return opp.get("_niche_score", 50)

    return 50   # unknown source default


# ── Composite ─────────────────────────────────────────────────────────────────

def score_opportunity(opp: Dict[str, Any]) -> Dict[str, Any]:
    """Add margin_score, competition_score, composite_score to an Opportunity."""
    m = _margin_score(opp)
    c = _competition_score(opp)
    composite = int(
        m * WEIGHT_MARGIN_SIGNAL + c * WEIGHT_COMPETITION_SIGNAL
    )
    return {
        **opp,
        "margin_score":      m,
        "competition_score": c,
        "composite_score":   composite,
    }


def score_and_filter(opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Score all opportunities, filter below threshold, sort by composite score.
    """
    scored = [score_opportunity(o) for o in opportunities]
    passed = [o for o in scored if o["composite_score"] >= MIN_SCORE_THRESHOLD]
    passed.sort(key=lambda x: x["composite_score"], reverse=True)
    return passed
