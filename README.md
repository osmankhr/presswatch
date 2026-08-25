# PressWatch

Weekly media monitoring for a fixed set of entities — right now: **ING Hubs
Türkiye** and its CEO **Emre Danacı**. Screens for any mention, with a
deliberate emphasis on not missing awards/recognition, and flags each hit by
category in a weekly digest email.

## What this is

A narrowly-scoped press-clipping tool, not a platform: one fixed entity list
(no admin panel, no multi-tenant subscriber management), built to run weekly
and email a digest. Deliberately reuses
[quoideneuf](https://github.com/osmankhr/quoideneuf)'s fetch → filter →
score → digest → mail shape, since that pattern already fits this problem
well — the main difference is *what* gets fetched (targeted entity search
instead of fixed topic RSS feeds) and *how* the LLM pass is used (confirm
"is this genuinely about the entity" + categorize, instead of score relevance
and novelty).

## Goal: high recall AND high precision

- **Recall** (don't miss a mention): cast a wide net across independent
  search methods (see PLAN.md) and multiple name-variant queries, including
  the common transliteration that drops Turkish diacritics.
- **Precision** (don't drown in noise): "ING" is a common substring in
  unrelated text, so every candidate hit goes through an LLM confirmation
  pass before it's treated as a real mention — but when the model is
  genuinely unsure, the default is to *include it flagged as low-confidence*
  rather than silently drop it, so recall never gets traded away to buy
  precision.

## Status

**Stage 0 (scaffolding) and Stage 1 (fetch + dedup) done.** Working today:
Google News RSS search, Exa neural search, curated Turkish business-press
feeds, cross-run + within-run dedup (by URL and normalized title), the
keyword pre-filter, and the Claude/OpenRouter LLM provider (with
real-fallback + real-alert-email verified end-to-end). Not yet implemented:
the LLM classify/categorize step (Stage 2) and the digest builder (Stage 3)
— see [PLAN.md](PLAN.md).

Real end-to-end verification already run against the live entity, and it's
already doing its job finding real precision problems to solve rather than
hypothetical ones:
- Search correctly surfaces genuine coverage (a Webrazzi interview with
  Emre Danacı).
- The keyword filter correctly rejects real noise: unrelated people who
  happen to share the surname "Danacı" (found three so far — Ahmet Eymen,
  Uğur, Onur), German amateur football fixture pages, and Exa's
  recency-constrained search broadening to generic "ING Bank" content
  (branch listings, SWIFT codes) for an "ING Hubs Türkiye" query.
- Title-based dedup correctly collapsed a real duplicate: the identical Al
  Jazeera article served from two different CDN mirror subdomains, which
  URL-only dedup would have treated as two separate stories.

A full run (207 raw items across all three sources → 71 new after dedup →
5 after the keyword filter) shows the funnel working as designed: cheap
methods cut obvious volume, and everything that survives is a genuinely
hard case — real surname collisions — that only Stage 2's LLM
classification can resolve.

## Running it

```bash
cp .env.example .env   # fill in AGENTMAIL_API_KEY, EXA_API_KEY, etc.
uv run --with agentmail --with feedparser --with requests --with python-dotenv \
  --with jinja2 --with exa-py python3 main.py --fetch-only
```

`--fetch-only` runs everything implemented so far (fetch, dedup, keyword
filter) and prints the surviving candidates — useful for checking real
coverage before Stage 2/3 land. Plain `python main.py` will currently stop
with a clear "not yet implemented" error at the classification step.
