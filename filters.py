"""Article relevance filtering and text cleaning utilities."""

from __future__ import annotations

import html
import logging
import re
from xml.sax.saxutils import escape as xml_escape

logger = logging.getLogger(__name__)

THREAT_TERMS: list[str] = [
    "india", "indian",
    "threat", "attack", "security", "military", "defense", "defence",
    "terror", "militant", "border", "conflict", "war", "weapon",
    "nuclear", "missile", "espionage", "spy", "cyber", "hack",
    "insurgent", "ceasefire", "tension", "strike", "operation",
    "pakistan", "china", "lac", "loc", "jammu", "kashmir",
    "naxal", "maoist", "infiltrat", "surveillance", "intelligence",
    "army", "navy", "air force", "paramilitary", "forces",
    "blast", "explosion", "hostage", "ied", "drone",
]

NON_SECURITY_TERMS: list[str] = [
    "cricket", "ipl", "bollywood", "movies", "film", "actor", "actress",
    "wedding", "marriage", "fashion", "recipe", "weather forecast",
    "stock market", "sensex", "nifty", "share price", "mutual fund",
]


def is_security_relevant(text: str) -> bool:
    """Return True if text is likely about India's national security."""
    text = text.lower()
    if any(term in text for term in NON_SECURITY_TERMS):
        return False
    has_india    = "india" in text or "indian" in text
    threat_count = sum(1 for t in THREAT_TERMS if t in text)
    return has_india and threat_count >= 3


def clean_html(text: str) -> str:
    """Strip HTML tags, decode HTML entities, and normalise whitespace."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def sanitize_text(text: str) -> str:
    """Escape XML/ReportLab markup characters in external content."""
    return xml_escape(text)


def sanitize_url(url: str) -> str:
    """Accept only http/https URLs; return empty string otherwise."""
    if url and re.match(r"^https?://", url.strip()):
        return url.strip()
    return ""
