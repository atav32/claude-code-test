"""
Deduplication.

Removes near-duplicate opportunities across sources using simple
token-overlap (Jaccard similarity) on normalised titles.
"""

from __future__ import annotations

import re
from typing import List, Dict, Any

_SIMILARITY_THRESHOLD = 0.55   # Jaccard similarity above this = duplicate


def _tokenise(text: str) -> set[str]:
    """Lowercase, strip punctuation, split into word tokens."""
    cleaned = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    return set(cleaned.split())


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def deduplicate(opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Return a de-duplicated list.  Keeps the higher-scoring item when two
    opportunities are similar.  Assumes input is already sorted descending
    by composite_score.
    """
    kept: List[Dict[str, Any]] = []
    kept_tokens: List[set]     = []

    for opp in opportunities:
        tokens = _tokenise(opp["title"])
        is_dup = any(
            _jaccard(tokens, kt) >= _SIMILARITY_THRESHOLD
            for kt in kept_tokens
        )
        if not is_dup:
            kept.append(opp)
            kept_tokens.append(tokens)

    return kept
