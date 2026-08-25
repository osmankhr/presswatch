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

**Stages 0-2 done** (scaffolding, fetch + dedup, LLM classification). Only
Stage 3 (the digest builder + weekly send) remains — see
[PLAN.md](PLAN.md).

Every stage was verified against real data, not synthetic examples, and
real testing kept surfacing precision problems harder than originally
anticipated — which the classifier now handles correctly:
- Search correctly surfaces genuine coverage (a Webrazzi interview with
  Emre Danacı).
- Beyond simple surname collisions (three different unrelated "Danacı"s
  found), real testing turned up a genuine full-name collision: a
  different person, also named "Emre Danacı," with no ING connection
  anywhere in the item — correctly excluded. A second case that *looked*
  like the same kind of collision (an "Emre DANACI, Retail Banking
  Analytics Tribe Lead at ING" LinkedIn post) turned out to be the *same*
  Emre Danacı after all — he holds multiple roles within ING beyond CEO of
  ING Hubs Türkiye. That was corrected in the classifier's rules after
  Osman flagged it, and re-verified it doesn't cause the real collisions
  above to regress.
- Also correctly excluded "ING Hubs Spain" (a different country's
  subsidiary) and correctly tagged two genuine items as `award_recognition`
  — the exact category Osman said not to miss.
- Title-based dedup correctly collapsed a real duplicate: the identical Al
  Jazeera article served from two different CDN mirror subdomains.

A full run (207 raw items across all three sources → dedup → keyword
filter → classifier) shows the funnel working end to end as designed: cheap
methods cut obvious volume, and the LLM classification step resolves the
genuinely hard remaining cases correctly.

## Running it

```bash
cp .env.example .env   # fill in AGENTMAIL_API_KEY, EXA_API_KEY, etc.
uv run --with agentmail --with feedparser --with requests --with python-dotenv \
  --with jinja2 --with exa-py python3 main.py --fetch-only
```

`--fetch-only` runs fetch + dedup + keyword filter only and prints the
surviving candidates. `--dry-run` runs the full pipeline including
classification and stops with a clear "not yet implemented" error at the
digest-building step (Stage 3) instead of emailing anything. Plain `python
main.py` will do the same until Stage 3 lands, since it can't build or send
a digest yet.
