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

Pre-implementation. See [PLAN.md](PLAN.md) for the build-out.
