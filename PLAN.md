# PressWatch — Implementation Plan

## Context

Weekly press-clipping tool for a fixed, narrow entity list: **ING Hubs
Türkiye** and its CEO **Emre Danacı**. Explicitly scoped to stay narrow —
Osman confirmed this is not meant to generalize into a multi-entity platform,
so this stays a lean single-purpose script (quoideneuf's shape), not a
DB-backed multi-tenant product (Curio's shape). If that ever changes, the
entity config below is already isolated enough to extend, but that's not
being designed for up front.

**Reference projects in this environment** (reuse, don't reinvent):
- `~/projects/quoideneuf` — fetch → filter → score → digest → mail shape.
  `fetchers/rss_common.py`'s `fetch_rss(feed_url, source, category, days_back)`
  is generic enough to reuse unmodified for both Google News RSS search URLs
  and curated Turkish business-press feeds. `filter.py`'s cheap keyword
  pre-pass and `scorer.py`'s per-item Claude CLI scoring pattern are both
  directly adaptable (see Stage 2/3 below for what changes).
- `~/projects/hr_tech` — the Exa-search-for-a-named-entity pattern
  (`candidate_pool/scripts/search.py`) is the same shape as "find mentions of
  a specific company/person across the web."
- `~/projects/curio` (`PLAN.md`) — the LLM provider strategy just decided
  there (Claude via the n8n multi-profile setup, OpenRouter fallback, email
  alert on first fallback) applies here too — build it once as a small shared
  module, reuse in both projects rather than duplicating.

**Established preferences to follow:**
- AgentMail for outbound email.
- `claude --print --output-format json` (not the raw subprocess-without-usage-tracking
  pattern quoideneuf's `scorer.py` currently uses) — get cost/token logging
  for free from the start.
- No database, no admin panel — a fixed entity config file is the right
  amount of infrastructure for a single-entity tool.

## Recall & precision strategy (the actual hard part here)

**Recall — cast a wide net, independently, across methods:**
- [ ] Multiple query variants per entity: `"ING Hubs Türkiye"`, `"ING Hubs
  Turkiye"` (ASCII fallback), `"Emre Danacı"`, `"Emre Danaci"` (dropped
  diacritics — common in wire/international coverage), plus a couple of
  narrower variants (`"ING Türkiye CEO"`, English-language equivalents) to
  catch coverage that doesn't use the exact name.
- [ ] At least two *independent* search methods, not just one queried
  multiple ways — a bug or blind spot in one shouldn't mean a total miss:
  - Exa neural search (same call shape as hr_tech's `search.py`)
  - Google News RSS search (`news.google.com/rss/search?q=...`) via
    `fetch_rss()` — free, no API key, good coverage of mainstream press
  - A short curated list of Turkish business-press RSS feeds (Dünya,
    Hürriyet Ekonomi, Fintech İstanbul, or similar) as a third, fully
    independent source for anything the search-based methods miss
- [ ] Weekly `days_back` window with a few days of overlap between runs
  (e.g. 9-10 days, not exactly 7) so nothing falls in a gap at a run
  boundary.

**Precision — confirm before treating a hit as real, but don't over-correct:**
- [ ] Cheap pre-filter: keyword/substring match on the entity name variants
  (mirrors `filter.py`) just to cut obvious non-candidates before the
  expensive step.
- [ ] LLM confirmation pass (mirrors `scorer.py`, but check-shaped, not
  score-shaped): for each surviving candidate, ask "is this genuinely about
  ING Hubs Türkiye / Emre Danacı, or just an incidental match (e.g. 'ING' as
  part of an unrelated word, or a different entity)?" Categorize into:
  Award/Recognition, Executive/Leadership, Business/Product, General mention,
  Reputational/negative.
  - When the model is confident either way, trust it (exclude clear
    false-positives, include and categorize real hits).
  - When it's genuinely unsure, **include it, flagged as low-confidence**,
    rather than silently drop it — a false positive costs Osman a few
    seconds of "not relevant"; a false negative means a real mention (maybe
    an award) never gets seen at all. Recall wins the tie.

## Stage 0 — Scaffolding

- [ ] Repo layout (mirrors quoideneuf): `fetchers/` (Exa search wrapper,
  Google News RSS query builder, curated Turkish press feed list — reusing
  `rss_common.fetch_rss`), `filter.py` (keyword pre-pass), `classifier.py`
  (the LLM confirm+categorize step, replacing `scorer.py`), `digest.py`,
  `mailer.py` (AgentMail, same pattern as quoideneuf), `config.py` (entity
  name variants, recipient list, RSS feed URLs), `main.py`.
- [ ] Shared LLM provider module (Claude via n8n profile, OpenRouter
  fallback, alert email) — same as Curio's plan; write it once, use from
  both repos (or factor out to a tiny shared package later if that gets
  annoying — not worth doing up front for two callers).
- [ ] `.env.example`: `AGENTMAIL_API_KEY`, `EXA_API_KEY`, `OPENROUTER_API_KEY`,
  recipient list, Claude profile name.
- [ ] `cache/` dir for a seen-URLs store (mirrors quoideneuf's dedup cache)
  so the same story doesn't get re-flagged every week it's still floating
  around.

## Stage 1 — Fetch + dedup

- [ ] Implement the three source types from the recall strategy above.
- [ ] Dedup across sources by URL, then a simple normalized-title
  near-duplicate check (same story often runs on multiple outlets with
  slightly different headlines).
- [ ] Verification: run fetch-only against the real entity config, manually
  eyeball the raw candidate list for a week or two of real news before
  wiring in the classifier — confirms the sources are actually finding
  known real coverage (spot-check against something you already know
  happened) before trusting the pipeline's judgment on top of it.

## Stage 2 — Classification (precision layer)

- [ ] Build `classifier.py` per the precision strategy above: confirm +
  categorize + low-confidence-include-don't-drop.
- [ ] Verification: deliberately feed it a few known false-positive-shaped
  inputs (generic "ING" mentions unrelated to the entity) and confirm they
  get excluded, plus a few genuine-but-ambiguous-sounding ones to confirm
  they come through flagged low-confidence rather than dropped.

## Stage 3 — Digest + delivery

- [ ] Weekly digest email: awards/recognition surfaced first regardless of
  chronological order (that's the category Osman explicitly said not to
  miss), then executive news, business news, general mentions; low-confidence
  items in their own clearly-labeled section at the bottom rather than mixed
  in.
- [ ] Send via AgentMail to Osman (and whoever else should get this —
  confirm recipient list).
- [ ] Cron: weekly.
- [ ] Verification: run one full real week end-to-end, confirm the email
  reads clearly and the categorization/ordering holds up before considering
  this live.

## Explicit non-goals

- No multi-entity configuration UI or admin panel — a config file is enough
  for a fixed, narrow entity list.
- No database — the seen-URLs cache is a flat file, matching quoideneuf's
  approach, not a reason to add SQLite.
- No real-time/immediate alerting — weekly cadence as specified; if
  same-day award/news alerting becomes a real need later, that's a
  meaningfully different (and bigger) feature, not an incremental add.
