"""Stage 3: build the weekly digest email from classified items.

Award/Recognition items surface first regardless of chronological order --
that's the category Osman explicitly said not to miss. Then
executive/leadership, business/product, general mentions, reputational last
(worth seeing, not worth leading with). Low-confidence items get pulled into
their own clearly-labeled section at the bottom, regardless of which
category they were tentatively assigned, rather than mixed in with confirmed
matches -- so a recruiter-style skim of the top of the email is all high
confidence, real matches.
"""
from __future__ import annotations

from config import CATEGORIES

CATEGORY_LABELS = {
    "award_recognition": "🏆 Awards & Recognition",
    "executive_leadership": "Executive & Leadership",
    "business_product": "Business & Product",
    "general_mention": "General Mentions",
    "reputational_negative": "Reputational / Negative",
}

LOW_CONFIDENCE_LABEL = "Needs Review (Low Confidence)"


def build_sections(classified_items: list[dict]) -> dict[str, list[dict]]:
    """Group items by category in CATEGORIES order, with low-confidence
    items (regardless of category) pulled into their own trailing section."""
    sections: dict[str, list[dict]] = {CATEGORY_LABELS[c]: [] for c in CATEGORIES}
    sections[LOW_CONFIDENCE_LABEL] = []

    for item in classified_items:
        if item.get("confidence") == "low":
            sections[LOW_CONFIDENCE_LABEL].append(item)
            continue
        category = item.get("category")
        label = CATEGORY_LABELS.get(category)
        if label:
            sections[label].append(item)
        else:
            # confirmed match but no/invalid category somehow -- don't lose it
            sections[CATEGORY_LABELS["general_mention"]].append(item)

    return {label: items for label, items in sections.items() if items}


def _text_item(item: dict) -> str:
    lines = [f"  {item.get('title', '(no title)')}", f"  {item.get('url', '')}"]
    if item.get("reasoning"):
        lines.append(f"  {item['reasoning']}")
    lines.append(f"  source: {item.get('source', '')}")
    return "\n".join(lines)


def render_text(sections: dict[str, list[dict]]) -> str:
    lines = ["PRESSWATCH — ING Hubs Türkiye / Emre Danacı", "=" * 50, ""]
    if not sections:
        lines.append("No new items this week.")
        return "\n".join(lines)

    for label, items in sections.items():
        lines.append(f"## {label} ({len(items)})")
        lines.append("")
        for item in items:
            lines.append(_text_item(item))
            lines.append("")
        lines.append("")
    return "\n".join(lines)


def _html_item(item: dict) -> str:
    title = item.get("title", "(no title)")
    url = item.get("url", "")
    reasoning = item.get("reasoning", "")
    source = item.get("source", "")
    return f"""<div class="item">
  <a href="{url}">{title}</a>
  <p class="reasoning">{reasoning}</p>
  <span class="meta">{source}</span>
</div>"""


def render_html(sections: dict[str, list[dict]], week_label: str) -> str:
    parts = [f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: Georgia, serif; max-width: 680px; margin: 40px auto; color: #222; line-height: 1.6; }}
  h1 {{ font-size: 1.4em; border-bottom: 2px solid #222; padding-bottom: 8px; }}
  h2 {{ font-size: 1.1em; margin-top: 2em; color: #444; text-transform: uppercase; letter-spacing: 0.05em; }}
  .item {{ margin-bottom: 1.4em; }}
  .item a {{ color: #1a0dab; font-weight: bold; text-decoration: none; }}
  .item a:hover {{ text-decoration: underline; }}
  .reasoning {{ margin: 4px 0; color: #444; }}
  .meta {{ font-size: 0.82em; color: #888; }}
  .empty {{ color: #666; }}
  hr {{ border: none; border-top: 1px solid #eee; margin: 2em 0; }}
</style>
</head>
<body>
<h1>PressWatch — {week_label}</h1>
<p style="color:#666; font-size:0.9em;">ING Hubs Türkiye / Emre Danacı — weekly press clipping.</p>
"""]

    if not sections:
        parts.append('<p class="empty">No new items this week.</p>')
    else:
        for label, items in sections.items():
            parts.append(f"<hr><h2>{label} ({len(items)})</h2>")
            for item in items:
                parts.append(_html_item(item))

    parts.append("</body></html>")
    return "\n".join(parts)
