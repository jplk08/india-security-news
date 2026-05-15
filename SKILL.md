---
name: india-security-news
description: >
  Generates a daily India national security and threat intelligence digest by
  fetching news from multiple sources (Google News RSS × 6, BBC, Reuters, Times of
  India, The Hindu, Hindustan Times, NDTV, Indian Express, NewsAPI), filtering for
  India-relevant threat/security content from the last 7 days, summarising with
  Google Gemini AI into a clean 300-400 word executive summary, reviewing and
  improving with a Gemini editor pass, and saving as a dated A4 PDF report.
  Use this skill whenever the user asks to: fetch/generate a security news digest
  for India, build or run a daily news summariser, create a threat intelligence
  report, automate India security news collection, or mentions keywords like
  "daily news PDF", "India threat summary", "security digest", "news automation
  script", or "summarise security articles". Also trigger when the user wants to
  modify, extend, or re-run this workflow (e.g. add email delivery, change sources,
  adjust word count, change output format, add new keywords).
---

# India National Security News Summarizer

## Overview

This skill produces a daily PDF digest of India national security and threat news.
Summarisation and content review are both performed by **Google Gemini AI**
(`gemini-2.5-flash` with fallback to `gemini-2.0-flash` and `gemini-2.0-flash-lite`),
producing a high-quality, factual intelligence briefing.
News is limited to the **last 7 days** to ensure relevance.

---

## Architecture

```
[RSS Feeds × 13]  +  [NewsAPI]
        │                 │
        ▼                 ▼
fetch_rss_articles(seen)   fetch_newsapi_articles(seen)
        │                         │
        └──────────┬──────────────┘
                   │  shared seen_titles set
                   │  (cross-source deduplication)
                   ▼
         is_security_relevant()   ← keyword filter + negative filter
         date filter (last 7 days)
         threshold: ≥3 THREAT_TERMS + India context
                   │
                   ▼ (capped at MAX_CORPUS_ARTICLES = 50)
         summarize_with_gemini()  ← Gemini analyst pass
                   │                → 300-400 word draft executive summary
                   ▼
         review_with_gemini()     ← Gemini senior editor pass
                   │                → improved summary + KEY_DEVELOPMENTS bullets
                   ▼
         generate_pdf()           ← reportlab A4 PDF
                   │                sections: Key Developments, Executive Summary, Sources
                   ▼
       india_security_YYYY-MM-DD.pdf
```

If either Gemini call fails (quota, deadline, network), `main.py` catches the
exception and generates a fallback PDF listing all collected articles without
an AI summary — the pipeline never crashes without output.

---

## Module Map

| File | Responsibility |
|------|----------------|
| `config.py` | All constants and environment variables (single source of truth) |
| `models.py` | `Article` dataclass — shared data model across all modules |
| `filters.py` | `is_security_relevant()`, `clean_html()` (with html.unescape), sanitize helpers |
| `fetchers.py` | `fetch_rss_articles()`, `fetch_newsapi_articles()` — accept shared `seen_titles` set |
| `ai.py` | `_gemini_generate()`, `summarize_with_gemini()`, `review_with_gemini()` |
| `pdf_generator.py` | `build_source_list()`, `generate_pdf()` |
| `main.py` | Pipeline orchestration, logging setup, error recovery |

---

## Configuration (`config.py`)

| Constant | Default | Purpose |
|----------|---------|---------|
| `GEMINI_KEY` | `$GEMINI_API_KEY` env | Google Gemini API key |
| `NEWSAPI_KEY` | `$NEWSAPI_KEY` env | NewsAPI key (optional) |
| `OUTPUT_DIR` | `$OUTPUT_DIR` env / `.` | Folder where PDF is saved |
| `GEMINI_MODELS` | `[gemini-2.5-flash, 2.0-flash, 2.0-flash-lite]` | Tried in order on error |
| `GEMINI_DEADLINE_SECS` | `120` | Max seconds for summarise + review combined |
| `GEMINI_MAX_RETRIES` | `3` | Retry attempts per model on 429/503 |
| `GEMINI_RETRY_DELAY_SECS` | `20` | Base delay (multiplied by attempt number) |
| `MAX_CORPUS_ARTICLES` | `50` | Articles sent to Gemini (capped to control token budget) |
| `LOOKBACK_DAYS` | `7` | How far back articles are accepted |
| `MAX_SOURCES_IN_PDF` | `25` | Source entries in the PDF footer section |
| `RSS_TIMEOUT_SECS` | `10` | Per-feed HTTP timeout |
| `MAX_RSS_BYTES` | `2 MB` | Per-feed response size cap |
| `REQUEST_TIMEOUT_SECS` | `10` | NewsAPI HTTP timeout |

All keys are read from a `.env` file via `python-dotenv`. Never hardcode secrets.

---

## News Sources

### RSS Feeds (no key needed)
- Google News — India Security, Military, Terror, Cyber, Pakistan, China (6 targeted queries)
- BBC India
- Reuters India Top News
- Times of India Top Stories
- Hindustan Times India News
- The Hindu National
- NDTV India
- Indian Express

### NewsAPI (free tier — 100 req/day)
- Queries up to `MAX_NEWSAPI_KEYWORDS = 5` of the 13 `SECURITY_KEYWORDS` per run
- Uses last 7 days as `from` date
- Skipped gracefully if `NEWSAPI_KEY` not set

---

## Filtering Logic (`filters.py`)

An article is kept only if **all** conditions are true:
1. Does **not** match any `NON_SECURITY_TERMS` (cricket, Bollywood, stock market, etc.)
2. Contains `"india"` or `"indian"` in title + summary
3. Matches **≥3** terms from `THREAT_TERMS`
   (covers: threat, attack, security, military, border, terror, cyber, nuclear,
   espionage, army, blast, drone, etc.)

`clean_html()` strips tags, decodes HTML entities (including numeric `&#39;` and hex
`&#x2019;` forms via `html.unescape`), and normalises whitespace.

---

## Deduplication (`fetchers.py`)

Both `fetch_rss_articles` and `fetch_newsapi_articles` accept a single `seen_titles: set[str]`
argument passed from `main.py`. A title added by the RSS fetcher will not be added again
by the NewsAPI fetcher, preventing the same story from appearing twice in the corpus or PDF.

---

## AI Pipeline (`ai.py`)

### `_gemini_generate(prompt, deadline_end)`
- Tries each model in `GEMINI_MODELS` in order
- On `429 RESOURCE_EXHAUSTED` or `503 UNAVAILABLE`: sleeps and retries (up to `GEMINI_MAX_RETRIES` per model), then re-checks the deadline
- On `403 PERMISSION_DENIED` / leaked key: raises immediately with an actionable message
- `deadline_end` (from `time.monotonic()`) is checked before each attempt AND after each sleep, so the deadline is honoured even during backoff waits

### `summarize_with_gemini(articles, deadline_end)`
- Slices `articles[:MAX_CORPUS_ARTICLES]` before building the prompt corpus
- Instructs Gemini to write a 300-400 word flowing executive summary (no bullet points)

### `review_with_gemini(draft, articles, deadline_end)`
- Provides the draft + source headlines to a "senior editor" prompt
- Expects strict format: `SUMMARY:\n...\n\nKEY_DEVELOPMENTS:\n• ...\n• ...`
- `_parse_review_response()` logs a `WARNING` if the expected format is not found before falling back to the raw draft

---

## PDF Output (`pdf_generator.py`)

```
┌─────────────────────────────────────────────┐
│    India National Security Digest            │  ← Title (dark blue #1a237e)
│    Daily Threat & Security Intelligence      │
│    Summary Report Date: May 15, 2026         │
├─────────────────────────────────────────────┤
│  KEY DEVELOPMENTS             (red header)   │
│  • Development 1                             │
│  • Development 2 ... (4-6 items)             │
├─────────────────────────────────────────────┤
│  EXECUTIVE SUMMARY            (red header)   │
│                                              │
│  [300-400 word justified paragraph...]       │
│                                              │
├─────────────────────────────────────────────┤
│  NEWS SOURCES REFERENCED      (red header)   │
│  1. [BBC]  India border tensions...          │
│  2. [Reuters]  Army deploys...               │
│  ... up to 25 sources                        │
├─────────────────────────────────────────────┤
│  Auto-generated footer (grey)                │
└─────────────────────────────────────────────┘
```

---

## Installation & Usage

### One-time setup
```bash
pip install -r requirements.txt
```

Create `.env` in the project root:
```
GEMINI_API_KEY=your_gemini_key    # aistudio.google.com → Get API Key
NEWSAPI_KEY=your_newsapi_key      # newsapi.org/register (optional)
```

### Run manually
```bash
python main.py
```

### Run tests
```bash
python -m pytest tests/ -v
```

### Automate daily (Windows Task Scheduler)
- Trigger: Daily at 7:00 AM
- Program: `python.exe`
- Arguments: `C:\path\to\news-agent\main.py`
- Start in: `C:\path\to\news-agent\`

---

## Pipeline Steps

```
[1/5] Fetch RSS articles         → fetch_rss_articles(seen_titles)
[2/5] Fetch NewsAPI articles     → fetch_newsapi_articles(seen_titles)
[3/5] Draft summary              → summarize_with_gemini(articles, deadline)
[4/5] Review + key developments  → review_with_gemini(draft, articles, deadline)
[5/5] Build PDF                  → generate_pdf(summary, key_devs, sources, count)
```

---

## Common Customisations

### Change output folder
Set in `.env`:
```
OUTPUT_DIR=C:/Users/yourname/SecurityReports
```

### Add more RSS sources
In `config.py`:
```python
RSS_FEEDS["Dawn Pakistan"] = "https://www.dawn.com/feeds/home"
```

### Focus on a specific threat type
Add to `SECURITY_KEYWORDS` in `config.py`:
```python
"India data breach",
"India critical infrastructure attack",
```

### Raise the article corpus cap
In `config.py`:
```python
MAX_CORPUS_ARTICLES = 80
```

### Add email delivery
Use Python's `smtplib` to attach and send the PDF after `generate_pdf()` returns.

---

## Dependencies

| Library | Purpose |
|---------|---------|
| `feedparser` | Parse RSS/Atom feeds |
| `requests` | HTTP calls to RSS feeds and NewsAPI |
| `google-genai` | Google Gemini AI summarisation + review |
| `reportlab` | A4 PDF generation |
| `newsapi-python` | NewsAPI REST client |
| `python-dotenv` | Load `.env` secrets at startup |
| `pytest` | Unit and integration tests |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `0 articles found` | Strict filter or network issue | Lower threshold in `is_security_relevant()` to `>= 2` |
| NewsAPI skipped | Key not set | Add `NEWSAPI_KEY` to `.env` |
| `GEMINI_API_KEY is not set` | Missing `.env` | Create `.env` with a valid Gemini key |
| `403 PERMISSION_DENIED / leaked` | Key was exposed in git history | Generate a new key at aistudio.google.com |
| `Gemini deadline exceeded` | Slow network or heavy rate-limiting | Increase `GEMINI_DEADLINE_SECS` in `config.py` |
| `RESOURCE_EXHAUSTED` | Free tier daily quota | Wait until midnight (Pacific) or use a new key |
| PDF not saving | Wrong `OUTPUT_DIR` | Set to absolute path in `.env` |

---

## File Output

```
india_security_2026-05-14.pdf   ← dated, never overwrites previous days
india_security_2026-05-15.pdf
india_security_2026-05-16.pdf
...
```
