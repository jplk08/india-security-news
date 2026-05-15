"""India National Security News Summarizer — pipeline entry point."""

from __future__ import annotations

import logging
import os
import sys
import time
from datetime import date

# config must be imported first so .env is loaded before anything else reads env vars
import config
from ai import review_with_gemini, summarize_with_gemini
from fetchers import fetch_newsapi_articles, fetch_rss_articles
from pdf_generator import build_source_list, generate_pdf

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-20s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def _validate_environment() -> None:
    if not os.path.isdir(config.OUTPUT_DIR):
        logger.warning(
            "OUTPUT_DIR '%s' does not exist — falling back to current directory",
            config.OUTPUT_DIR,
        )
        config.OUTPUT_DIR = "."

    if not config.GEMINI_KEY:
        logger.error("GEMINI_API_KEY is not set. Add it to your .env file.")
        sys.exit(1)


def main() -> None:
    _validate_environment()

    logger.info("=" * 55)
    logger.info("  India National Security News Summarizer")
    logger.info("  Date: %s", date.today().strftime("%B %d, %Y"))
    logger.info("=" * 55)

    # Shared seen_titles set — prevents duplicates across RSS and NewsAPI
    seen_titles: set[str] = set()

    logger.info("[1/5] Fetching RSS feed articles...")
    rss_articles = fetch_rss_articles(seen_titles)
    logger.info("[1/5] Found %d relevant RSS articles", len(rss_articles))

    logger.info("[2/5] Fetching NewsAPI articles...")
    api_articles = fetch_newsapi_articles(seen_titles)
    logger.info("[2/5] Found %d relevant NewsAPI articles", len(api_articles))

    all_articles = rss_articles + api_articles
    logger.info("      Total articles for analysis: %d", len(all_articles))

    if not all_articles:
        logger.warning("No articles found — check internet connection or broaden keyword filters")
        pdf_path = generate_pdf(
            "No security articles were found for this run. "
            "Check your internet connection or broaden the keyword filters in config.py.",
            [],
            [],
            0,
        )
        logger.info("Fallback PDF saved: %s", pdf_path)
        return

    # Single deadline spanning both Gemini calls (issue #9)
    ai_deadline = time.monotonic() + config.GEMINI_DEADLINE_SECS

    try:
        logger.info("[3/5] Drafting executive summary with Gemini AI...")
        draft = summarize_with_gemini(all_articles, ai_deadline)
        logger.info("[3/5] Draft: %d words", len(draft.split()))

        logger.info("[4/5] Reviewing and extracting key developments with Gemini AI...")
        summary, key_devs = review_with_gemini(draft, all_articles, ai_deadline)
        logger.info(
            "[4/5] Final summary: %d words | Key developments: %d",
            len(summary.split()), len(key_devs),
        )
    except Exception as e:
        logger.warning(
            "[AI] Gemini pipeline failed (%s) — generating fallback PDF without AI summary",
            e,
        )
        summary  = (
            "AI summarisation unavailable for this run. "
            "Please review the source articles listed below."
        )
        key_devs = []

    logger.info("[5/5] Building PDF report...")
    sources  = build_source_list(all_articles)
    pdf_path = generate_pdf(summary, key_devs, sources, len(all_articles))
    logger.info("[5/5] PDF saved: %s", pdf_path)

    logger.info("=" * 55)
    logger.info("[Done] Open the PDF to read today's security digest.")
    logger.info("=" * 55)


if __name__ == "__main__":
    main()
