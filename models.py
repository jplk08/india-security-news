"""Shared data models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Article:
    """A single news article fetched from any source."""
    title:     str
    url:       str
    source:    str
    published: str = field(default="")
    text:      str = field(default="")
