# India National Security News Summarizer

An automated daily intelligence digest that fetches India national security and threat news from 14 sources, filters for relevance, summarises and reviews using **Google Gemini AI**, and saves a professional A4 PDF report.

---

## Features

- Fetches from **14 sources** — 13 RSS feeds (Google News × 6, BBC, Reuters, ToI, Hindustan Times, The Hindu, NDTV, Indian Express) + NewsAPI
- **Dual-pass AI pipeline** — Gemini drafts a 300-400 word executive summary, then a second Gemini editor pass improves accuracy and extracts 4-6 key developments
- Smart filtering — blocks non-security content (cricket, Bollywood, stocks) and requires India context + ≥3 threat-term matches
- **Cross-source deduplication** — a single shared set prevents the same story appearing twice from different feeds
- **Corpus cap** — at most 50 articles sent to Gemini, preventing token-budget overruns
- **AI deadline** — overall 120-second timeout on both Gemini calls so the pipeline never stalls indefinitely
- **Error recovery** — if AI is unavailable, a fallback PDF is generated listing all articles without a summary
- Outputs a clean **A4 PDF** with Key Developments, Executive Summary, and Sources sections

---

## Output

```
india_security_2026-05-15.pdf
```

```
┌──────────────────────────────────────────────┐
│    India National Security Digest             │
│    Daily Threat & Security Intelligence Summary│
│    Report Date: May 15, 2026 | Articles: 14  │
├──────────────────────────────────────────────┤
│  KEY DEVELOPMENTS                             │
│  • India-Pakistan border tensions escalate    │
│  • Cyber attack on critical infrastructure   │
│  • ...                                        │
├──────────────────────────────────────────────┤
│  EXECUTIVE SUMMARY                            │
│  [300-400 word AI-reviewed paragraph...]      │
├──────────────────────────────────────────────┤
│  NEWS SOURCES REFERENCED                      │
│  1. [BBC]  India border tensions...           │
│  2. [Reuters]  Army deploys...                │
└──────────────────────────────────────────────┘
```

---

## Installation

```bash
pip install -r requirements.txt
```

### Requirements

| Library | Purpose |
|---------|---------|
| `feedparser` | Parse RSS/Atom feeds |
| `requests` | HTTP calls (RSS + NewsAPI) |
| `google-genai` | Gemini AI summarisation + review |
| `reportlab` | PDF generation |
| `newsapi-python` | NewsAPI client |
| `python-dotenv` | Load `.env` secrets file |
| `pytest` | Unit + integration tests |

---

## Configuration

Copy `.env.example` to `.env` and fill in your API keys (never commit `.env`):

```
GEMINI_API_KEY=your_gemini_api_key_here
NEWSAPI_KEY=your_newsapi_key_here
OUTPUT_DIR=.
```

**Getting API keys (both free):**
- **Gemini:** [aistudio.google.com](https://aistudio.google.com) → Get API Key
- **NewsAPI:** [newsapi.org/register](https://newsapi.org/register) (optional — improves coverage)

All tunable constants (timeouts, article limits, model list, etc.) live in `config.py`. No need to edit any other file.

---

## Usage

```bash
python main.py
```

Sample output (structured logging):

```
2026-05-15 07:00:01  __main__   INFO  =======================================================
2026-05-15 07:00:01  __main__   INFO    India National Security News Summarizer
2026-05-15 07:00:01  __main__   INFO    Date: May 15, 2026
2026-05-15 07:00:01  __main__   INFO  =======================================================
2026-05-15 07:00:01  __main__   INFO  [1/5] Fetching RSS feed articles...
2026-05-15 07:00:08  __main__   INFO  [1/5] Found 12 relevant RSS articles
2026-05-15 07:00:08  __main__   INFO  [2/5] Fetching NewsAPI articles...
2026-05-15 07:00:09  __main__   INFO  [2/5] Found 2 relevant NewsAPI articles
2026-05-15 07:00:09  __main__   INFO        Total articles for analysis: 14
2026-05-15 07:00:09  __main__   INFO  [3/5] Drafting executive summary with Gemini AI...
2026-05-15 07:00:21  __main__   INFO  [3/5] Draft: 336 words
2026-05-15 07:00:21  __main__   INFO  [4/5] Reviewing and extracting key developments...
2026-05-15 07:00:35  __main__   INFO  [4/5] Final summary: 328 words | Key developments: 5
2026-05-15 07:00:35  __main__   INFO  [5/5] Building PDF report...
2026-05-15 07:00:35  __main__   INFO  [5/5] PDF saved: ./india_security_2026-05-15.pdf
```

---

## How It Works

```
[RSS Feeds × 13] + [NewsAPI]
          │
          ▼ (shared seen_titles set — cross-source dedup)
  is_security_relevant()   ← blocks sport/entertainment; requires India + ≥3 threat terms
  date filter (last 7 days)
          │
          ▼ (capped at MAX_CORPUS_ARTICLES = 50)
  summarize_with_gemini()  ← Gemini analyst: 300-400 word executive summary draft
          │
          ▼ (same overall ai_deadline)
  review_with_gemini()     ← Gemini editor: improves accuracy + extracts key developments
          │
          ▼
  generate_pdf()           ← A4 PDF: Key Developments + Executive Summary + Sources
          │
          ▼
india_security_YYYY-MM-DD.pdf
```

On AI failure the pipeline catches the exception and generates a fallback PDF listing all source articles without a summary, so there is always an output file.

---

## Project Structure

```
news-agent/
├── config.py          # All constants and environment variables
├── models.py          # Article dataclass
├── filters.py         # Relevance filtering and text cleaning
├── fetchers.py        # RSS and NewsAPI article fetching
├── ai.py              # Google Gemini summarise + review pipeline
├── pdf_generator.py   # A4 PDF report generation
├── main.py            # Pipeline orchestration entry point
├── conftest.py        # pytest path setup
├── tests/
│   ├── test_filters.py    # clean_html, is_security_relevant, sanitize helpers
│   ├── test_models.py     # Article dataclass
│   └── test_fetchers.py   # Deduplication and error paths
├── requirements.txt   # Python dependencies
├── .env               # API keys (gitignored — never commit)
├── SKILL.md           # Skill definition for Claude Code
└── README.md          # This file
```

---

## Running Tests

```bash
python -m pytest tests/ -v
```

---

## News Sources

| Source | Type |
|--------|------|
| Google News — India Security | RSS |
| Google News — India Military | RSS |
| Google News — India Terror | RSS |
| Google News — India Cyber | RSS |
| Google News — India Pakistan | RSS |
| Google News — India China | RSS |
| BBC India | RSS |
| Reuters India | RSS |
| Times of India | RSS |
| Hindustan Times | RSS |
| The Hindu National | RSS |
| NDTV India | RSS |
| Indian Express | RSS |
| NewsAPI (5 security keywords) | API |

---

## Automate Daily (Windows Task Scheduler)

1. Open **Task Scheduler** → Create Basic Task
2. **Trigger:** Daily at 7:00 AM
3. **Action:** Start a program
   - Program: `python`
   - Arguments: `C:\path\to\news-agent\main.py`
   - Start in: `C:\path\to\news-agent\`

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `0 articles found` | Lower threshold to `2` in `is_security_relevant()` in `filters.py` |
| `RESOURCE_EXHAUSTED` | Gemini free tier daily quota hit — try again tomorrow or rotate key |
| NewsAPI skipped | Add key to `.env` as `NEWSAPI_KEY=...` |
| PDF not saving | Set `OUTPUT_DIR` in `.env` to an absolute path |
| `GEMINI_API_KEY is not set` | Ensure `.env` exists and contains a valid key |
| `Gemini deadline exceeded` | Increase `GEMINI_DEADLINE_SECS` in `config.py` |

---

## License

For informational and educational purposes only. News content belongs to respective publishers.
