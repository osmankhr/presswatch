"""Shared fetch logic for simple single-feed RSS sources with a days_back cutoff."""

import feedparser
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime


def fetch_rss(feed_url: str, source: str, category: str, days_back: int = 7, snippet_len: int = 800) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    feed = feedparser.parse(feed_url)
    items = []
    for entry in feed.entries:
        published = entry.get("published", "")
        try:
            pub_dt = parsedate_to_datetime(published)
        except (TypeError, ValueError):
            continue
        if pub_dt.tzinfo is None:
            pub_dt = pub_dt.replace(tzinfo=timezone.utc)
        if pub_dt < cutoff:
            continue
        items.append({
            "source": source,
            "category": category,
            "title": entry.get("title", "").strip(),
            "url": entry.get("link", ""),
            "snippet": entry.get("summary", "")[:snippet_len],
            "published": published,
        })
    return items
