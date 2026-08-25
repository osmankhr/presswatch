"""Exa neural search fetcher -- one of PressWatch's independent recall sources.

Stage 1 work. Interface sketched now so main.py's orchestration shape is
clear from Stage 0; the actual Exa call (same pattern as hr_tech's
candidate_pool/scripts/search.py) gets implemented in Stage 1.
"""
from __future__ import annotations


def fetch(query: str, days_back: int = 10) -> list[dict]:
    """Run one Exa search query and return items in the shared candidate shape
    used across all fetchers: {source, category, title, url, snippet, published}.

    TODO (Stage 1): implement using exa_py.Exa, mirroring hr_tech's
    candidate_pool/scripts/search.py call shape. Needs EXA_API_KEY.
    """
    raise NotImplementedError("Stage 1: Exa search fetcher not yet implemented")
