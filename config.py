"""PressWatch configuration: what to watch for, where to look, who to tell.

Deliberately a flat config file, not a database -- see PLAN.md's "Explicit
non-goals." Add a new entity/query variant here directly if coverage misses
something; no admin UI is planned for this.
"""
import os

from dotenv import load_dotenv

load_dotenv()

# --- Recipients ---------------------------------------------------------

DIGEST_RECIPIENTS = [
    r.strip()
    for r in os.environ.get("DIGEST_RECIPIENTS", "o.kahraman.phys@gmail.com").split(",")
    if r.strip()
]

# --- Entities to watch ---------------------------------------------------
# Each entry is a search query variant fed to both Exa and Google News RSS.
# Include the diacritic-dropped transliteration too -- international/wire
# coverage frequently drops Turkish characters (ı/ş/ç/ğ/ö/ü).

ENTITY_QUERIES = [
    "ING Hubs Türkiye",
    "ING Hubs Turkiye",
    "Emre Danacı",
    "Emre Danaci",
    "ING Türkiye CEO",
]

# --- Google News RSS ------------------------------------------------------
# hl/gl/ceid = Turkish edition; a second English-language pass catches
# international coverage that a Turkish-locale search might rank lower.

GOOGLE_NEWS_EDITIONS = [
    {"hl": "tr", "gl": "TR", "ceid": "TR:tr"},
    {"hl": "en", "gl": "US", "ceid": "US:en"},
]

# --- Curated Turkish business-press feeds ---------------------------------
# Independent of the search-based methods above -- a real RSS feed doesn't
# depend on Google/Exa's ranking or indexing catching the story at all.
# Verified live and parsing cleanly as of 2026-08-25; re-check periodically,
# outlets do restructure their feeds.

CURATED_RSS_FEEDS = [
    {"name": "Dünya", "url": "https://www.dunya.com/rss?dunyaRss=ekonomi", "category": "business"},
    {"name": "Hürriyet Ekonomi", "url": "https://www.hurriyet.com.tr/rss/ekonomi", "category": "business"},
    {"name": "Fintech İstanbul", "url": "https://fintechistanbul.org/feed/", "category": "fintech"},
    {"name": "Ekonomim", "url": "https://www.ekonomim.com/rss", "category": "business"},
    {"name": "Anadolu Ajansı Ekonomi", "url": "https://www.aa.com.tr/tr/rss/default?cat=ekonomi", "category": "business"},
]

# --- Fetch window ----------------------------------------------------------
# Weekly cadence with overlap so nothing falls in a gap at a run boundary.
DAYS_BACK = 10

# --- Classification categories ---------------------------------------------
# Award/Recognition surfaces first in the digest regardless of chronological
# order -- see digest.py.
CATEGORIES = [
    "award_recognition",
    "executive_leadership",
    "business_product",
    "general_mention",
    "reputational_negative",
]
