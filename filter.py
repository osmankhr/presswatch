"""Cheap keyword pre-pass before the expensive LLM classification step
(classifier.py). Mirrors quoideneuf's filter.py's role, but for entity
mentions rather than a topic keyword list.

Deliberately NOT auto-derived from ENTITY_QUERIES by splitting into
individual words -- tokens like "Türkiye" or "Emre" are far too generic on
their own (nearly every Turkish news item mentions "Türkiye"; "Emre" is one
of the most common Turkish first names) and would pass through almost
everything, defeating the point of a cheap pre-filter. Use distinctive
multi-word phrases or the surname instead.

No MAX_CANDIDATES cap here unlike quoideneuf -- a single-entity monitor's
weekly volume is expected to be far smaller than a broad topic digest's, so
capping candidates before classification isn't a concern yet. Add one later
if real usage proves otherwise.
"""
from __future__ import annotations

_MARKERS = [
    "ing hubs",  # distinctive as a phrase even though "ing" and "hubs" alone aren't
    "danacı",  # surname, distinctive on its own
    "danaci",  # transliterated surname
]


def passes_filter(item: dict) -> bool:
    text = f"{item.get('title', '')} {item.get('snippet', '')}".lower()
    return any(marker in text for marker in _MARKERS)


def apply(items: list[dict]) -> list[dict]:
    passed = [item for item in items if passes_filter(item)]
    print(f"[filter] {len(passed)}/{len(items)} items passed keyword pre-filter")
    return passed
