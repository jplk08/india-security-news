"""Tests for fetchers.py — RSS and NewsAPI fetching with shared deduplication."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import fetchers


class TestSharedSeenTitles:
    """fetch_rss_articles and fetch_newsapi_articles share a seen_titles set."""

    def _make_fake_feed(self, title: str, summary: str, link: str) -> MagicMock:
        entry = {
            "title":          title,
            "summary":        summary,
            "description":    summary,
            "link":           link,
            "published_parsed": None,
            "updated_parsed":   None,
        }
        feed = MagicMock()
        feed.entries = [entry]
        return feed

    def test_rss_duplicate_across_feeds_skipped(self):
        """Second call with same seen_titles should yield no new articles."""
        seen   = set()
        title  = "India military attack border threat security"
        text   = "India security threat border military attack cyber surveillance"
        feed   = self._make_fake_feed(title, text, "https://example.com/1")

        with patch("fetchers._fetch_feed_with_timeout", return_value=feed):
            first_batch = fetchers.fetch_rss_articles(seen)

        with patch("fetchers._fetch_feed_with_timeout", return_value=feed):
            second_batch = fetchers.fetch_rss_articles(seen)

        # First batch picks up the article (if relevant); second finds nothing new
        assert len(second_batch) == 0

    def test_seen_titles_populated_after_rss_fetch(self):
        """Titles fetched via RSS are added to the shared seen_titles set."""
        seen  = set()
        title = "India cyber attack border military threat security"
        text  = "India security threat border military attack cyber surveillance"
        feed  = self._make_fake_feed(title, text, "https://example.com/2")

        with patch("fetchers._fetch_feed_with_timeout", return_value=feed):
            fetchers.fetch_rss_articles(seen)

        assert title in seen

    def test_newsapi_skips_title_already_in_seen(self):
        """NewsAPI skips articles whose title is already in seen_titles."""
        title = "India security threat border military"
        seen  = {title}  # pre-populate — as if RSS already fetched this

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "articles": [{
                "title":       title,
                "description": "India border military threat security attack",
                "source":      {"name": "Reuters"},
                "url":         "https://reuters.com/article/1",
            }]
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("fetchers.requests.get", return_value=mock_resp):
            articles = fetchers.fetch_newsapi_articles(seen)

        assert len(articles) == 0

    def test_newsapi_skipped_when_key_missing(self):
        """fetch_newsapi_articles returns [] immediately when NEWSAPI_KEY is empty."""
        seen = set()
        with patch("fetchers.NEWSAPI_KEY", ""):
            articles = fetchers.fetch_newsapi_articles(seen)
        assert articles == []
