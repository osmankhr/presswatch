"""Exa neural search fetcher -- one of PressWatch's independent recall
sources, alongside Google News RSS and the curated press feeds.

Same call shape as hr_tech's candidate_pool/scripts/search.py, but
category="news" instead of "people", and there's no `people` here to
dedup against an existing candidate DB -- URL-based dedup happens once,
centrally, in main.py.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from exa_py import Exa

_client: Exa | None = None


def _get_client() -> Exa:
    global _client
    if _client is None:
        api_key = os.environ.get("EXA_API_KEY")
        if not api_key:
            raise RuntimeError("EXA_API_KEY not set in environment")
        _client = Exa(api_key)
    return _client


def fetch(query: str, days_back: int = 10, num_results: int = 20) -> list[dict]:
    """Run one Exa search query and return items in the shared candidate shape
    used across all fetchers: {source, category, title, url, snippet, published}.
    """
    exa = _get_client()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

    try:
        response = exa.search(
            query=query,
            category="news",
            type="auto",
            num_results=num_results,
            start_published_date=cutoff.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            contents={"text": True},
        )
    except Exception as exc:  # network/API errors shouldn't kill the whole run
        print(f"[exa_search] query {query!r} failed: {exc}")
        return []

    items = []
    for result in response.results:
        text = getattr(result, "text", None) or ""
        items.append(
            {
                "source": "exa_search",
                "category": "search",
                "title": result.title or "",
                "url": result.url,
                "snippet": text[:800],
                "published": result.published_date or "",
            }
        )
    return items
