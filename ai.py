"""Gemini AI integration: summarise and review security news articles."""

from __future__ import annotations

import logging
import time
from typing import Optional

from google import genai
from google.genai import errors as genai_errors

from config import (
    GEMINI_DEADLINE_SECS,
    GEMINI_KEY,
    GEMINI_MAX_RETRIES,
    GEMINI_MODELS,
    GEMINI_RETRY_DELAY_SECS,
    MAX_CORPUS_ARTICLES,
)
from models import Article

logger = logging.getLogger(__name__)

_gemini_client = genai.Client(api_key=GEMINI_KEY)


def _gemini_generate(prompt: str, deadline_end: Optional[float] = None) -> str:
    """Call Gemini with model fallback, retry on transient errors, and optional deadline."""
    for model in GEMINI_MODELS:
        for attempt in range(GEMINI_MAX_RETRIES):
            if deadline_end is not None and time.monotonic() >= deadline_end:
                raise RuntimeError("Gemini overall deadline exceeded.")
            try:
                response = _gemini_client.models.generate_content(
                    model=model, contents=prompt
                )
                return response.text.strip()
            except (genai_errors.ClientError, genai_errors.ServerError) as e:
                err = str(e)
                if "403" in err or "PERMISSION_DENIED" in err or "leaked" in err.lower():
                    raise RuntimeError(
                        "Gemini API key is invalid or flagged as leaked. "
                        "Generate a new key at aistudio.google.com."
                    )
                if any(x in err for x in ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE")):
                    wait = GEMINI_RETRY_DELAY_SECS * (attempt + 1)
                    logger.warning(
                        "_gemini_generate: transient error on %s, retrying in %ds "
                        "(attempt %d/%d)",
                        model, wait, attempt + 1, GEMINI_MAX_RETRIES,
                    )
                    time.sleep(wait)
                    if deadline_end is not None and time.monotonic() >= deadline_end:
                        raise RuntimeError("Gemini overall deadline exceeded.")
                else:
                    logger.warning(
                        "_gemini_generate: non-retryable error on %s (%s) — trying next model",
                        model, type(e).__name__,
                    )
                    break
    raise RuntimeError("All Gemini models exhausted. Check your API key and quota.")


def _build_corpus(articles: list[Article]) -> str:
    lines: list[str] = []
    for i, a in enumerate(articles, 1):
        lines.append(f"{i}. [{a.source}] {a.title}")
        if a.text:
            lines.append(f"   {a.text[:400]}")
        lines.append("")
    return "\n".join(lines)


def _parse_review_response(raw: str, fallback: str) -> tuple[str, list[str]]:
    summary  = fallback
    key_devs: list[str] = []

    try:
        if "SUMMARY:" in raw and "KEY_DEVELOPMENTS:" in raw:
            parts    = raw.split("KEY_DEVELOPMENTS:")
            summary  = parts[0].replace("SUMMARY:", "").strip()
            key_devs = [
                line.lstrip("•-– ").strip()
                for line in parts[1].splitlines()
                if line.strip()
            ]
        elif "SUMMARY:" in raw:
            summary = raw.replace("SUMMARY:", "").strip()
        else:
            logger.warning(
                "_parse_review_response: expected format not found — using fallback. "
                "Raw response (first 200 chars): %.200s",
                raw,
            )
    except Exception as e:
        logger.warning("_parse_review_response: parse error (%s) — using fallback", e)

    return summary, key_devs


def summarize_with_gemini(
    articles: list[Article],
    deadline_end: Optional[float] = None,
) -> str:
    """Draft a 300-400 word intelligence executive summary using Gemini."""
    if deadline_end is None:
        deadline_end = time.monotonic() + GEMINI_DEADLINE_SECS

    corpus = _build_corpus(articles[:MAX_CORPUS_ARTICLES])

    prompt = (
        "You are a senior intelligence analyst producing a daily classified briefing.\n\n"
        "Based on the following news articles about India's national security, write a "
        "300-400 word executive summary. Cover: significant threats, key actors, "
        "geographic hotspots (borders, conflict zones), military/defense developments, "
        "cyber incidents, and strategic implications. Use a professional "
        "intelligence-briefing tone — flowing paragraphs only, no bullet points, no headers.\n\n"
        f"ARTICLES:\n{corpus}\n\n"
        "Write the executive summary now:"
    )

    return _gemini_generate(prompt, deadline_end)


def review_with_gemini(
    draft: str,
    articles: list[Article],
    deadline_end: Optional[float] = None,
) -> tuple[str, list[str]]:
    """Senior editor pass: improve the draft and extract key developments.

    Returns (improved_summary, key_developments).
    """
    if deadline_end is None:
        deadline_end = time.monotonic() + GEMINI_DEADLINE_SECS

    headlines = "\n".join(
        f"- [{a.source}] {a.title}" for a in articles[:MAX_CORPUS_ARTICLES]
    )

    prompt = (
        "You are a senior intelligence editor reviewing a draft security briefing.\n\n"
        f"DRAFT SUMMARY:\n{draft}\n\n"
        f"SOURCE HEADLINES (verify coverage against these):\n{headlines}\n\n"
        "Your tasks:\n"
        "1. Improve clarity, factual accuracy, and professional intelligence tone\n"
        "2. Ensure all major stories from the headlines are reflected\n"
        "3. Keep the final summary 300-400 words\n"
        "4. After the summary, extract 4-6 KEY DEVELOPMENTS as concise bullet points "
        "(most significant events only — one line each)\n\n"
        "Respond in EXACTLY this format and nothing else:\n"
        "SUMMARY:\n"
        "[improved summary text]\n\n"
        "KEY_DEVELOPMENTS:\n"
        "• [development 1]\n"
        "• [development 2]\n"
        "• [development 3]\n"
        "• [development 4]\n"
        "• [development 5]"
    )

    return _parse_review_response(_gemini_generate(prompt, deadline_end), draft)
