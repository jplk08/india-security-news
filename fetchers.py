"""Article fetchers: RSS feeds and NewsAPI."""

from __future__ import annotations

import logging
from datetime import datetime, date, timedelta, timezone
from io import BytesIO

import feedparser
import requests

from config import (
    LOOKBACK_DAYS,
    MAX_NEWSAPI_KEYWORDS,
    MAX_NEWSAPI_PAGE_SIZE,
    MAX_RSS_BYTES,
    MAX_RSS_ENTRIES_PER_FEED,
    NEWSAPI_KEY,
    REQUEST_TIMEOUT_SECS,
    RSS_FEEDS,
    RSS_TIMEOUT_SECS,
    SECURITY_KEYWORDS,
)
from filters import clean_html, is_security_relevant, sanitize_text, sanitize_url
from models import Article

logger = logging.getLogger(__name__)


def _fetch_feed_with_timeout(url: str) -> feedparser.FeedParserDict:
    """Fetch an RSS feed via requests (with timeout + size cap) then parse."""
    resp = requests.get(
        url,
        timeout=RSS_TIMEOUT_SECS,
        headers={"User-Agent": "IndiaSecurityNewsBot/1.0"},
        stream=True,
    )
    resp.raise_for_status()
    raw = resp.raw.read(MAX_RSS_BYTES)
    return feedparser.parse(BytesIO(raw))


def fetch_rss_articles(seen_titles: set[str]) -> list[Article]:
    """Fetch articles from all RSS feeds published in the last LOOKBACK_DAYS days.

    seen_titles is shared with fetch_newsapi_articles to deduplicate across sources.
    """
    articles: list[Article] = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)

    for source_name, url in RSS_FEEDS.items():
        try:
            feed = _fetch_feed_with_timeout(url)
            for entry in feed.entries[:MAX_RSS_ENTRIES_PER_FEED]:
                title   = entry.get("title", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()
                link    = entry.get("link", "")

                if not title or title in seen_titles:
                    continue

                pub = entry.get("published_parsed") or entry.get("updated_parsed")
                if pub:
                    pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
                    if pub_dt < cutoff:
                        continue

                combined = (title + " " + summary).lower()
                if is_security_relevant(combined):
                    seen_titles.add(title)
                    articles.append(Article(
                        source    = source_name,
                        title     = sanitize_text(title),
                        text      = sanitize_text(clean_html(summary)),
                        url       = sanitize_url(link),
                        published = "",
                    ))
        except requests.exceptions.Timeout:
            logger.error("fetch_rss_articles: %s — request timed out", source_name)
        except requests.exceptions.RequestException as e:
            logger.error("fetch_rss_articles: %s — %s", source_name, e)
        except Exception as e:
            logger.error("fetch_rss_articles: %s — parse error: %s", source_name, e)

    return articles


def fetch_newsapi_articles(seen_titles: set[str]) -> list[Article]:
    """Fetch articles from NewsAPI free tier.

    seen_titles is shared with fetch_rss_articles to deduplicate across sources.
    """
    if not NEWSAPI_KEY:
        logger.warning("fetch_newsapi_articles: NEWSAPI_KEY not set — skipping")
        return []

    articles: list[Article] = []
    seven_days_ago = (date.today() - timedelta(days=LOOKBACK_DAYS)).isoformat()

    for keyword in SECURITY_KEYWORDS[:MAX_NEWSAPI_KEYWORDS]:
        try:
            resp = requests.get(
                "https://newsapi.org/v2/everything",
                headers={"X-Api-Key": NEWSAPI_KEY},
                params={
                    "q":        keyword,
                    "from":     seven_days_ago,
                    "sortBy":   "publishedAt",
                    "language": "en",
                    "pageSize": MAX_NEWSAPI_PAGE_SIZE,
                },
                timeout=REQUEST_TIMEOUT_SECS,
            )
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("articles", []):
                title   = (item.get("title") or "").strip()
                content = (item.get("description") or item.get("content") or "").strip()
                source  = item.get("source", {}).get("name", "NewsAPI")
                link    = item.get("url", "")

                if not title or title in seen_titles:
                    continue

                combined = (title + " " + content).lower()
                if is_security_relevant(combined):
                    seen_titles.add(title)
                    articles.append(Article(
                        source    = sanitize_text(source),
                        title     = sanitize_text(title),
                        text      = sanitize_text(clean_html(content)),
                        url       = sanitize_url(link),
                        published = "",
                    ))
        except requests.exceptions.RequestException as e:
            logger.error("fetch_newsapi_articles: keyword '%s' — %s", keyword, e)
        except (KeyError, ValueError) as e:
            logger.error("fetch_newsapi_articles: keyword '%s' — parse error: %s", keyword, e)

    return articles
