"""Shared seen-URL store for cross-source dedup.

quoideneuf tracks "seen" per-fetcher (cache/<source>_seen.json) since each
fetcher there is a distinct topic source that never overlaps another. Here
the same story routinely shows up via multiple independent methods (Exa +
Google News + a curated feed), so PressWatch dedups once, centrally, across
all sources for a run -- not per-source.
"""
import json
from pathlib import Path

STATE_PATH = Path(__file__).parent / "seen_urls.json"


def load_seen() -> set[str]:
    if not STATE_PATH.exists():
        return set()
    try:
        return set(json.loads(STATE_PATH.read_text()))
    except (json.JSONDecodeError, OSError):
        return set()


def save_seen(urls: set[str]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(sorted(urls), indent=2, ensure_ascii=False))
