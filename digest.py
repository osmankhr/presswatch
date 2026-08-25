"""Stage 3: build the weekly digest email from classified items.

Award/Recognition items surface first regardless of chronological order --
that's the category Osman explicitly said not to miss. Then
executive/leadership, business/product, general mentions, with
low-confidence items in their own clearly-labeled section at the bottom
rather than mixed in with confirmed matches.
"""
from __future__ import annotations


def build_sections(classified_items: list[dict]) -> dict[str, list[dict]]:
    """Group classified items by category, ordered per config.CATEGORIES,
    with low-confidence items pulled into a separate trailing section.

    TODO (Stage 3): implement.
    """
    raise NotImplementedError("Stage 3: digest builder not yet implemented")


def render_html(sections: dict[str, list[dict]], week_label: str) -> str:
    raise NotImplementedError("Stage 3: digest builder not yet implemented")


def render_text(sections: dict[str, list[dict]]) -> str:
    raise NotImplementedError("Stage 3: digest builder not yet implemented")
