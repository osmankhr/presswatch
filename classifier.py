"""Stage 2: LLM confirm + categorize pass -- the precision layer.

For each candidate that passed filter.py's keyword pre-pass, confirm it's
genuinely about ING Hubs Türkiye / Emre Danacı (not a coincidental match) and
categorize it into config.CATEGORIES. When genuinely unsure, include it
flagged low-confidence rather than drop it -- see PLAN.md's recall/precision
strategy.

Concrete real test case already found during Stage 0 verification (worth
using as a fixture once this gets built): a Google News hit for "Samsunlu
Ahmet Eymen Danacı dünya ikincisi oldu" -- a different person who happens to
share the surname "Danacı," not Emre Danacı. filter.py's keyword pre-pass
correctly can't tell these apart (that's not its job); this is exactly the
kind of item classifier.py must correctly exclude.
"""
from __future__ import annotations


def classify(item: dict) -> dict | None:
    """Return item annotated with {is_match, category, confidence, reasoning},
    or None if the model is confident it's not a real match at all.

    TODO (Stage 2): implement via llm_provider.call_model_text, mirroring
    quoideneuf's scorer.py / hr_tech's filter.py per-item Claude call shape.
    """
    raise NotImplementedError("Stage 2: classifier not yet implemented")


def classify_all(items: list[dict]) -> list[dict]:
    raise NotImplementedError("Stage 2: classifier not yet implemented")
