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

## Stage 0 — Scaffolding — done 2026-08-25

- [x] Repo layout (mirrors quoideneuf): `fetchers/` (`google_news.py`
  implemented and verified; `exa_search.py` stubbed for Stage 1;
  `rss_common.py` copied verbatim from quoideneuf), `filter.py` (keyword
  pre-pass, implemented — curated distinctive markers, not
  naively-tokenized entity names, since generic tokens like "Türkiye"/"Emre"
  would pass through nearly everything), `classifier.py` and `digest.py`
  (stubbed for Stage 2/3, interfaces defined), `mailer.py` (AgentMail,
  implemented), `config.py` (entity queries, curated feed list — all 5
  feeds verified live and parsing), `main.py` (orchestrator with a working
  `--fetch-only` mode).
- [x] Shared LLM provider module (`llm_provider.py`) — Claude via the
  `aiworkspacetr` n8n profile by default, OpenRouter fallback on failure,
  one-time-per-run alert email. Verified for real: a genuine Claude call
  through the profile (cost/timing logged correctly), and a genuine forced
  failure that correctly fell back and sent a real alert email via
  AgentMail end-to-end (not just unit-tested in isolation).
- [x] `.env.example`: all vars documented, including reusing hr_tech's
  existing `EXA_API_KEY` rather than provisioning a new one.
- [x] `cache/seen_store.py` — one shared seen-URL store, not per-fetcher like
  quoideneuf, since the same story routinely surfaces via multiple
  independent methods here (Exa + Google News + curated feed) and dedup
  needs to happen once across all of them, not per-source.

## Stage 1 — Fetch + dedup — partially done

- [x] Google News RSS search — implemented, verified against the real
  entity: correctly surfaces genuine coverage (a Webrazzi interview with
  Emre Danacı) and, running it for real, already turned up two concrete
  real-world precision problems worth keeping as classifier.py test
  fixtures later: (1) an unrelated person, "Ahmet Eymen Danacı," who shares
  only the surname, and (2) a batch of German amateur football fixture
  pages that Google News' looser English-locale matching surfaced with no
  actual textual connection to the query at all.
- [x] Curated Turkish business-press feeds — implemented via
  `rss_common.fetch_rss` (already generic enough to need zero changes),
  all 5 configured feeds verified live.
- [x] Cross-run + within-run dedup by URL (`cache/seen_store.py` +
  `main.py`'s `dedup()`).
- [ ] Exa search — not yet implemented (`fetchers/exa_search.py` is
  currently a stub that raises `NotImplementedError`; `main.py` catches
  that and skips it, logging that it was skipped).
- [ ] Normalized-title near-duplicate check beyond exact URL match (same
  story, different URL, across outlets) — not yet implemented.
- [ ] Full verification (a week or two of real news, manually spot-checked
  against known real coverage) — partially done via the fetch-only runs
  above, but not yet over a sustained period.

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
