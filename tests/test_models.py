"""Tests for models.py — Article dataclass."""

from __future__ import annotations

from models import Article


class TestArticle:
    def test_required_fields(self):
        a = Article(title="Test", url="https://example.com", source="BBC")
        assert a.title == "Test"
        assert a.url == "https://example.com"
        assert a.source == "BBC"

    def test_optional_fields_default_to_empty_string(self):
        a = Article(title="T", url="https://x.com", source="S")
        assert a.published == ""
        assert a.text == ""

    def test_optional_fields_settable(self):
        a = Article(
            title="T", url="https://x.com", source="S",
            published="2026-01-01", text="article body",
        )
        assert a.published == "2026-01-01"
        assert a.text == "article body"

    def test_equality(self):
        a1 = Article(title="T", url="https://x.com", source="S")
        a2 = Article(title="T", url="https://x.com", source="S")
        assert a1 == a2

    def test_inequality(self):
        a1 = Article(title="T1", url="https://x.com", source="S")
        a2 = Article(title="T2", url="https://x.com", source="S")
        assert a1 != a2
