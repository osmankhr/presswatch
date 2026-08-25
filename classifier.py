"""Stage 2: LLM confirm + categorize pass -- the precision layer.

For each candidate that survived filter.py's keyword pre-pass, confirm it's
genuinely about ING Hubs Türkiye / Emre Danacı (not a coincidental match --
Stage 1 testing found real cases of this: unrelated people who happen to
share the surname "Danacı", e.g. "Uğur Danacı" and "Onur Danacı") and
categorize it into config.CATEGORIES.

Decision policy (see PLAN.md's recall/precision strategy) -- deliberately
asymmetric, because a missed award costs more than an extra "not relevant":
  - model confident it's NOT a match (confidence high/medium, is_match=False)
    -> excluded.
  - model confident it IS a match -> included, normal confidence.
  - model NOT confident either way (confidence=low) -> included regardless
    of is_match, flagged low-confidence. Never silently dropped.
"""
from __future__ import annotations

import json
import re

from config import CATEGORIES
from llm_provider import call_model_text


def _extract_json(text: str) -> dict | None:
    """Best-effort JSON extraction -- strip markdown fences if present, fall
    back to the first {...} block, since models sometimes add these despite
    being told not to."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fence.group(1) if fence else text
    if not fence:
        brace = re.search(r"\{.*\}", text, re.DOTALL)
        candidate = brace.group(0) if brace else text
    try:
        obj = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None

SYSTEM_PROMPT = """\
You screen news/web items for a press-monitoring tool watching two specific \
entities: the company "ING Hubs Türkiye" (a technology/shared-services \
subsidiary of ING Bank, NOT ING Bank itself or its retail banking business) \
and its CEO "Emre Danacı" (a specific named individual).

Be careful about false positives from name/word collisions:
- "ING" alone is a common substring (e.g. "ING Bank" retail/branch content, \
"banking", generic ING Bank commentary) -- that is NOT a match unless the \
item is specifically about ING Hubs Türkiye.
- "Danacı" is a real Turkish surname other people also have -- an item about \
a different person who happens to be named e.g. "Uğur Danacı" or \
"Onur Danacı" is NOT a match.
Only count it as a match if the item is genuinely, specifically about \
ING Hubs Türkiye (the company) or Emre Danacı (this specific CEO).

If you are not confident either way from the given text, say so honestly \
via low confidence rather than guessing -- do not force a decision the \
text doesn't support.

Respond ONLY with a valid JSON object -- no markdown fences, no preamble.
"""

ITEM_PROMPT = """\
Title: {title}
Source: {source}
Text: {snippet}

Categories, use exactly one of these (or null if is_match is false):
{categories}

JSON only:
{{"is_match": <true|false>, "confidence": "<high|medium|low>", "category": <one of the categories above, or null>, "reasoning": "<one sentence>"}}
"""


def classify(item: dict) -> dict | None:
    """Return item annotated with classification fields, or None only when
    the model is confidently negative (a clear false positive). Everything
    else -- confirmed matches and genuinely-uncertain items alike -- is kept.
    """
    prompt = ITEM_PROMPT.format(
        title=item.get("title", ""),
        source=item.get("source", ""),
        snippet=(item.get("snippet") or "")[:600] or "(no text available -- title only)",
        categories=", ".join(CATEGORIES),
    )

    raw = call_model_text(prompt=prompt, system=SYSTEM_PROMPT, timeout=60)
    if raw is None:
        # Model call failed entirely (both Claude and OpenRouter down) --
        # can't confirm OR reject, so keep it, unconfirmed, rather than lose
        # it. This is the same recall-over-precision tie-break as a genuine
        # low-confidence classification, just from an infrastructure failure
        # instead of model uncertainty.
        return {
            **item,
            "is_match": True,
            "confidence": "low",
            "category": None,
            "reasoning": "Classification call failed -- kept unconfirmed rather than dropped.",
        }

    parsed = _extract_json(raw)
    if parsed is None:
        return {
            **item,
            "is_match": True,
            "confidence": "low",
            "category": None,
            "reasoning": "Classifier response was not valid JSON -- kept unconfirmed rather than dropped.",
        }

    is_match = bool(parsed.get("is_match"))
    confidence = str(parsed.get("confidence") or "low").lower()
    if confidence not in {"high", "medium", "low"}:
        confidence = "low"

    # Confident negative -> excluded. Everything else (confident positive,
    # or genuinely uncertain in either direction) is kept.
    if confidence != "low" and not is_match:
        return None

    category = parsed.get("category")
    if category not in CATEGORIES:
        category = None

    return {
        **item,
        "is_match": is_match,
        "confidence": confidence,
        "category": category,
        "reasoning": str(parsed.get("reasoning") or ""),
    }


def classify_all(items: list[dict]) -> list[dict]:
    classified: list[dict] = []
    for i, item in enumerate(items, 1):
        print(f"[classifier] {i}/{len(items)}: {item.get('title', '')[:60]}")
        result = classify(item)
        if result is not None:
            classified.append(result)
    excluded = len(items) - len(classified)
    print(f"[classifier] {len(classified)}/{len(items)} kept ({excluded} confidently excluded)")
    return classified
