#!/usr/bin/env python3
"""PressWatch -- weekly press-clipping for ING Hubs Türkiye / Emre Danacı.

Usage:
    python main.py               # full run: fetch -> filter -> classify -> digest -> mail
    python main.py --fetch-only  # fetch + dedup + keyword pre-filter only, print results
                                  # (works today; classify/digest are Stage 2/3)
    python main.py --dry-run     # full pipeline, print the digest instead of emailing it
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from cache.seen_store import load_seen, save_seen
from config import CURATED_RSS_FEEDS, DAYS_BACK, ENTITY_QUERIES, GOOGLE_NEWS_EDITIONS
from fetchers import google_news, rss_common
from filter import apply as apply_filter


def fetch_all() -> list[dict]:
    items: list[dict] = []

    print("[fetch] Google News RSS search...")
    for query in ENTITY_QUERIES:
        for edition in GOOGLE_NEWS_EDITIONS:
            batch = google_news.fetch(query, edition, days_back=DAYS_BACK)
            print(f"  {query!r} ({edition['hl']}): {len(batch)} items")
            items.extend(batch)

    print("[fetch] Exa search...")
    try:
        from fetchers import exa_search

        for query in ENTITY_QUERIES:
            batch = exa_search.fetch(query, days_back=DAYS_BACK)
            print(f"  {query!r}: {len(batch)} items")
            items.extend(batch)
    except NotImplementedError:
        print("  (skipped -- Stage 1 not yet implemented)")

    print("[fetch] curated Turkish business-press feeds...")
    for feed in CURATED_RSS_FEEDS:
        batch = rss_common.fetch_rss(
            feed["url"], source=feed["name"], category=feed["category"], days_back=DAYS_BACK
        )
        print(f"  {feed['name']}: {len(batch)} items")
        items.extend(batch)

    return items


def dedup(items: list[dict]) -> list[dict]:
    seen = load_seen()
    new_items = [item for item in items if item.get("url") and item["url"] not in seen]

    # Also dedup within this run's own batch (same story often found via
    # multiple methods/queries at once, not just across weekly runs).
    deduped: list[dict] = []
    seen_this_run: set[str] = set()
    for item in new_items:
        url = item["url"]
        if url in seen_this_run:
            continue
        seen_this_run.add(url)
        deduped.append(item)

    print(f"[dedup] {len(deduped)}/{len(items)} items are new (not seen in a prior run or duplicated this run)")
    save_seen(seen | seen_this_run)
    return deduped


def run(fetch_only: bool = False, dry_run: bool = False) -> None:
    week_label = datetime.now(timezone.utc).strftime("Week of %B %d, %Y")
    print(f"\n=== PressWatch | {week_label} ===\n")

    raw = fetch_all()
    print(f"\n[fetch] total: {len(raw)} raw items\n")

    new_items = dedup(raw)
    candidates = apply_filter(new_items)

    if fetch_only:
        print("\n[fetch-only] candidates after keyword pre-filter:")
        for item in candidates:
            print(f"  - {item['title'][:90]}  ({item['source']})")
        return

    from classifier import classify_all
    from digest import build_sections, render_html, render_text

    classified = classify_all(candidates)
    sections = build_sections(classified)
    html = render_html(sections, week_label)
    text = render_text(sections)

    if dry_run:
        print(text)
        print("\n[dry-run] email not sent.")
        return

    from config import DIGEST_RECIPIENTS
    from mailer import send

    send(
        subject=f"PressWatch — {week_label}",
        html_body=html,
        text_body=text,
        recipients=DIGEST_RECIPIENTS,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        run(fetch_only=args.fetch_only, dry_run=args.dry_run)
    except NotImplementedError as exc:
        print(f"\n[main] stopped at a not-yet-implemented stage: {exc}", file=sys.stderr)
        sys.exit(1)
