"""Google News RSS search -- a free, no-API-key independent recall source.

Verified working (2026-08-25) against real ENTITY_QUERIES: surfaces the
correct coverage (e.g. the Webrazzi interview with Emre Danacı) alongside
some obvious noise (unrelated people/events matching a name fragment) --
that noise is exactly what the Stage 2 classifier exists to filter out.
"""
from __future__ import annotations

from urllib.parse import quote

from .rss_common import fetch_rss


def fetch(query: str, edition: dict, days_back: int = 10) -> list[dict]:
    """One Google News RSS search for `query` in the given locale edition.

    `edition` is one of config.GOOGLE_NEWS_EDITIONS, e.g. {"hl": "tr", "gl":
    "TR", "ceid": "TR:tr"}.
    """
    url = (
        f"https://news.google.com/rss/search?q={quote(query)}"
        f"&hl={edition['hl']}&gl={edition['gl']}&ceid={edition['ceid']}"
    )
    return fetch_rss(
        url,
        source=f"google_news_{edition['hl']}",
        category="search",
        days_back=days_back,
    )
