"""Centralised configuration: environment variables and named constants."""

from __future__ import annotations

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── API keys ──────────────────────────────────────────────────────────────────
NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY", "").strip()
GEMINI_KEY  = os.environ.get("GEMINI_API_KEY", "").strip()
OUTPUT_DIR  = os.environ.get("OUTPUT_DIR", ".")

# ── HTTP / feed limits ────────────────────────────────────────────────────────
RSS_TIMEOUT_SECS       = 10
MAX_RSS_BYTES          = 2 * 1024 * 1024   # 2 MB per feed response
REQUEST_TIMEOUT_SECS   = 10

# ── Feed / article counts ─────────────────────────────────────────────────────
LOOKBACK_DAYS              = 7
MAX_RSS_ENTRIES_PER_FEED   = 20
MAX_NEWSAPI_PAGE_SIZE      = 5
MAX_NEWSAPI_KEYWORDS       = 5
MAX_CORPUS_ARTICLES        = 50   # cap before sending to Gemini
MAX_SOURCES_IN_PDF         = 25
MAX_SOURCE_TITLE_LEN       = 110
SOURCE_DEDUP_KEY_LEN       = 80    # characters used to identify duplicate source entries
PDF_SUMMARY_CHUNK_WORDS    = 100   # words per ReportLab paragraph in the summary block

# ── Gemini ────────────────────────────────────────────────────────────────────
GEMINI_MODELS = [
    "models/gemini-2.5-flash",
    "models/gemini-2.0-flash",
    "models/gemini-2.0-flash-lite",
]
GEMINI_MAX_RETRIES      = 3
GEMINI_RETRY_DELAY_SECS = 20
GEMINI_DEADLINE_SECS    = 120   # overall cap per summarize/review call

# ── RSS feed URLs ─────────────────────────────────────────────────────────────
RSS_FEEDS: dict[str, str] = {
    "Google News - India Security": (
        "https://news.google.com/rss/search"
        "?q=India+national+security+threat&hl=en-IN&gl=IN&ceid=IN:en"
    ),
    "Google News - India Military": (
        "https://news.google.com/rss/search"
        "?q=India+military+defense+attack&hl=en-IN&gl=IN&ceid=IN:en"
    ),
    "Google News - India Terror": (
        "https://news.google.com/rss/search"
        "?q=India+terrorism+threat&hl=en-IN&gl=IN&ceid=IN:en"
    ),
    "Google News - India Cyber": (
        "https://news.google.com/rss/search"
        "?q=India+cyber+attack+hack&hl=en-IN&gl=IN&ceid=IN:en"
    ),
    "Google News - India Pakistan": (
        "https://news.google.com/rss/search"
        "?q=India+Pakistan+conflict+border&hl=en-IN&gl=IN&ceid=IN:en"
    ),
    "Google News - India China": (
        "https://news.google.com/rss/search"
        "?q=India+China+border+LAC&hl=en-IN&gl=IN&ceid=IN:en"
    ),
    "BBC India":               "https://feeds.bbci.co.uk/news/world/asia/india/rss.xml",
    "Reuters India":           "https://feeds.reuters.com/reuters/INtopNews",
    "Times of India - Nation": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    "Hindustan Times":         "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml",
    "The Hindu - National":    "https://www.thehindu.com/news/national/feeder/default.rss",
    "NDTV India":              "https://feeds.ndtv.com/ndtv/national?pfrom=home-ndtvrss",
    "Indian Express":          "https://indianexpress.com/section/india/feed/",
}

# ── NewsAPI search terms ──────────────────────────────────────────────────────
SECURITY_KEYWORDS: list[str] = [
    "India security threat",
    "India national security",
    "India military attack",
    "India border tension",
    "India terrorism",
    "India cyber attack",
    "India defense threat",
    "India nuclear",
    "India militant",
    "India insurgency",
    "Pakistan India conflict",
    "China India border",
    "India espionage",
]
