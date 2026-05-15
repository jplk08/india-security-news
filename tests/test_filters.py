"""Tests for filters.py — relevance filtering and text cleaning."""

from __future__ import annotations

from filters import clean_html, is_security_relevant, sanitize_text, sanitize_url


class TestCleanHtml:
    def test_strips_tags(self):
        assert clean_html("<b>Hello</b>") == "Hello"

    def test_strips_nested_tags(self):
        assert clean_html("<p><strong>India</strong> cyber <em>attack</em></p>") == "India cyber attack"

    def test_unescape_ampersand(self):
        assert clean_html("India &amp; Pakistan") == "India & Pakistan"

    def test_unescape_lt_gt(self):
        assert clean_html("score &lt; 10 &gt; 0") == "score < 10 > 0"

    def test_normalises_whitespace(self):
        assert clean_html("  too   many   spaces  ") == "too many spaces"

    def test_unescape_numeric_entity(self):
        assert clean_html("India&#39;s security") == "India's security"

    def test_unescape_hex_entity(self):
        assert clean_html("India&#x2019;s security") == "India’s security"

    def test_empty_string(self):
        assert clean_html("") == ""


class TestIsSecurityRelevant:
    def test_positive_case(self):
        text = "india military attack border terrorism threat cyber"
        assert is_security_relevant(text) is True

    def test_blocked_by_non_security_term(self):
        # "cricket" is in NON_SECURITY_TERMS → always False
        text = "india military attack border cricket"
        assert is_security_relevant(text) is False

    def test_missing_india(self):
        text = "military attack border terrorism threat cyber"
        assert is_security_relevant(text) is False

    def test_insufficient_threat_count(self):
        # "india" counts as one threat term; needs >= 3 total
        text = "india economic growth today"
        assert is_security_relevant(text) is False

    def test_bollywood_excluded(self):
        text = "india bollywood actor military attack border threat"
        assert is_security_relevant(text) is False


class TestSanitizeText:
    def test_escapes_ampersand(self):
        assert sanitize_text("India & Pakistan") == "India &amp; Pakistan"

    def test_escapes_angle_brackets(self):
        assert sanitize_text("<script>") == "&lt;script&gt;"


class TestSanitizeUrl:
    def test_accepts_https(self):
        assert sanitize_url("https://example.com/article") == "https://example.com/article"

    def test_accepts_http(self):
        assert sanitize_url("http://example.com") == "http://example.com"

    def test_rejects_javascript(self):
        assert sanitize_url("javascript:alert(1)") == ""

    def test_rejects_empty(self):
        assert sanitize_url("") == ""

    def test_strips_leading_whitespace(self):
        assert sanitize_url("  https://example.com") == "https://example.com"
