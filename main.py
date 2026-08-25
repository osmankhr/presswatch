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


def fetch_all(days_back: int = DAYS_BACK) -> list[dict]:
    items: list[dict] = []

    print("[fetch] Google News RSS search...")
    for query in ENTITY_QUERIES:
        for edition in GOOGLE_NEWS_EDITIONS:
            batch = google_news.fetch(query, edition, days_back=days_back)
            print(f"  {query!r} ({edition['hl']}): {len(batch)} items")
            items.extend(batch)

    print("[fetch] Exa search...")
    try:
        from fetchers import exa_search

        for query in ENTITY_QUERIES:
            batch = exa_search.fetch(query, days_back=days_back)
            print(f"  {query!r}: {len(batch)} items")
            items.extend(batch)
    except NotImplementedError:
        print("  (skipped -- Stage 1 not yet implemented)")

    print("[fetch] curated Turkish business-press feeds...")
    for feed in CURATED_RSS_FEEDS:
        batch = rss_common.fetch_rss(
            feed["url"], source=feed["name"], category=feed["category"], days_back=days_back
        )
        print(f"  {feed['name']}: {len(batch)} items")
        items.extend(batch)

    return items


def _normalize_title(title: str) -> list[str]:
    """Lowercase, strip punctuation, split into words -- catches the same
    story served from different URLs (e.g. two different CDN mirror
    subdomains for the identical article, seen for real during testing: the
    same Al Jazeera piece via two distinct *.edgeone.app hostnames)."""
    return "".join(ch for ch in title.lower() if ch.isalnum() or ch.isspace()).split()


def dedup(items: list[dict], persist: bool = True) -> list[dict]:
    """persist=False for preview modes (--fetch-only, --dry-run) -- a preview
    that permanently marks items as "seen" would mean the next *real* run
    silently skips everything you just looked at. Only a real send should
    consume the seen-state."""
    seen = load_seen()
    new_items = [item for item in items if item.get("url") and item["url"] not in seen]

    # Dedup within this run's own batch by URL *and* normalized title -- same
    # story is routinely found via multiple methods/queries at once, and
    # sometimes via different mirror URLs for byte-identical content, not
    # just across weekly runs.
    deduped: list[dict] = []
    seen_urls_this_run: set[str] = set()
    seen_titles_this_run: set[tuple] = set()
    for item in new_items:
        url = item["url"]
        title_key = tuple(_normalize_title(item.get("title", "")))
        if url in seen_urls_this_run or (title_key and title_key in seen_titles_this_run):
            continue
        seen_urls_this_run.add(url)
        if title_key:
            seen_titles_this_run.add(title_key)
        deduped.append(item)

    print(f"[dedup] {len(deduped)}/{len(items)} items are new (not seen in a prior run, and not a duplicate URL or near-duplicate title this run)")
    if persist:
        save_seen(seen | seen_urls_this_run)
    else:
        print("[dedup] preview mode -- not persisting seen-state")
    return deduped


def run(fetch_only: bool = False, dry_run: bool = False, days_back: int = DAYS_BACK) -> None:
    week_label = datetime.now(timezone.utc).strftime("Week of %B %d, %Y")
    print(f"\n=== PressWatch | {week_label} ===\n")

    raw = fetch_all(days_back=days_back)
    print(f"\n[fetch] total: {len(raw)} raw items\n")

    new_items = dedup(raw, persist=not (fetch_only or dry_run))
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

    if not sections:
        # No confirmed or low-confidence items this run -- skip sending
        # rather than emailing a "nothing new" digest every quiet week.
        print("\n[main] no items this run -- skipping send (nothing to report).")
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
    parser.add_argument(
        "--days-back",
        type=int,
        default=None,
        help="Override config.DAYS_BACK (e.g. for a backfill or a richer one-off example run)",
    )
    args = parser.parse_args()

    try:
        run(
            fetch_only=args.fetch_only,
            dry_run=args.dry_run,
            days_back=args.days_back if args.days_back is not None else DAYS_BACK,
        )
    except NotImplementedError as exc:
        print(f"\n[main] stopped at a not-yet-implemented stage: {exc}", file=sys.stderr)
        sys.exit(1)
