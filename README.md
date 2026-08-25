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

**Stages 0-3 done** — scaffolding, fetch + dedup, LLM classification, and
the digest builder + send are all working, verified with a real end-to-end
run that sent an actual example email. **Cron is deliberately not set up
yet** — that's the only remaining step before this runs unattended weekly.
See [PLAN.md](PLAN.md).

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
- Recency filtering (default 10-day window, a deliberate small overlap past
  a strict 7 days) and duplicate-prevention (a persistent seen-URL store,
  `cache/seen_store.py`) were both already built as of Stage 0/1 -- and got
  re-proven live rather than just asserted: running the real production
  path twice in immediate succession dropped from 71 new items down to just
  4 on the second run, confirming the memory genuinely blocks re-surfacing
  the same items across separate runs.
- Also fixed: a real production run with nothing to report was still
  emailing a "no new items this week" digest. Changed it to skip sending
  entirely on a quiet run instead.

A real full run (with a widened window to get a representative example --
production defaults to the last 10 days, which is often quiet) went 335 raw
items → 275 new → 31 after the keyword filter → 19 kept after
classification, grouped into Awards & Recognition, Business & Product, and
General Mentions -- and an actual digest email was sent and landed
correctly.

That same verification run also found a real bug: previewing a digest
(`--fetch-only`/`--dry-run`) was permanently marking items as "seen," so
running a preview then a real send right after would silently find nothing.
Fixed so only a real send consumes the seen-state.

## Running it

```bash
cp .env.example .env   # fill in AGENTMAIL_API_KEY, EXA_API_KEY, etc.
uv run --with agentmail --with feedparser --with requests --with python-dotenv \
  --with exa-py python3 main.py --fetch-only
```

- `--fetch-only`: fetch + dedup + keyword filter only, prints candidates,
  does not touch seen-state.
- `--dry-run`: full pipeline including classification and digest
  rendering, prints the digest instead of emailing it, does not touch
  seen-state.
- `--days-back N`: override `config.DAYS_BACK` for a backfill or a richer
  one-off example run.
- Plain `python main.py`: the real thing -- fetches, classifies, **sends the
  digest email**, and marks everything as seen for next time.

No cron job is set up yet -- runs are manual until that's wanted.
