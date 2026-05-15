# 🇮🇳 India National Security News Summarizer

An automated daily intelligence digest that fetches India national security and threat news from multiple sources, summarizes and reviews using **Google Gemini AI**, and saves a professional PDF report.

---

## Features

- Fetches from **13 sources** — Google News RSS (6 targeted queries), BBC, Reuters, Times of India, Hindustan Times, The Hindu, NDTV, Indian Express + NewsAPI
- **Dual AI pipeline** — Gemini drafts a 300-400 word executive summary, then a second Gemini pass acts as a senior editor to improve accuracy and extract key developments
- Smart filtering — blocks non-security content (cricket, Bollywood, stocks) and requires ≥3 threat-term matches
- Outputs a clean **A4 PDF** with Key Developments, Executive Summary, and Sources sections
- Auto-retry with model fallback on rate limits or server errors

---

## Output

```
india_security_2026-05-15.pdf
```

```
┌──────────────────────────────────────────────┐
│  🇮🇳  India National Security Digest          │
│  Daily Threat & Security Intelligence Summary │
│  Report Date: May 15, 2026 | Articles: 14    │
├──────────────────────────────────────────────┤
│  KEY DEVELOPMENTS                            │
│  • India-Pakistan border tensions escalate   │
│  • Cyber attack on critical infrastructure  │
│  • ...                                       │
├──────────────────────────────────────────────┤
│  EXECUTIVE SUMMARY                           │
│  [300-400 word AI-reviewed paragraph...]     │
├──────────────────────────────────────────────┤
│  NEWS SOURCES REFERENCED                     │
│  1. [BBC]  India border tensions...          │
│  2. [Reuters]  Army deploys...               │
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
| `requests` | HTTP calls to NewsAPI |
| `google-generativeai` | Gemini AI summarization + review |
| `reportlab` | PDF generation |
| `newsapi-python` | NewsAPI client (optional) |

---

## Configuration

Open `india_security_news.py` and set your keys at the top:

```python
NEWSAPI_KEY = "your_newsapi_key"      # Free key from newsapi.org/register
GEMINI_KEY  = "your_gemini_api_key"   # Free key from aistudio.google.com
OUTPUT_DIR  = "."                     # Folder where PDF is saved
```

Or set via environment variables:
```bash
# Windows PowerShell
$env:GEMINI_API_KEY = "your_key_here"
```

**Getting API keys (both free):**
- **Gemini:** [aistudio.google.com](https://aistudio.google.com) → Get API Key
- **NewsAPI:** [newsapi.org/register](https://newsapi.org/register) (optional but improves coverage)

---

## Usage

```bash
python india_security_news.py
```

Output:
```
=======================================================
  India National Security News Summarizer
  Date: May 15, 2026
=======================================================

[1/5] Fetching RSS feed articles...
      Found 12 relevant RSS articles.

[2/5] Fetching NewsAPI articles...
      Found 2 relevant NewsAPI articles.

      Total articles for analysis: 14

[3/5] Drafting executive summary with Gemini AI...
      Draft: 336 words.

[4/5] Reviewing and extracting key developments with Gemini AI...
      Final summary: 328 words | Key developments: 5

[5/5] Building PDF report...
      PDF saved: ./india_security_2026-05-15.pdf

[Done] Open the PDF to read today's security digest.
=======================================================
```

---

## How It Works

```
[RSS Feeds] + [NewsAPI]
       │
       ▼
 is_security_relevant()   ← blocks sport/entertainment; requires ≥3 threat terms
 date filter (last 7 days)
       │
       ▼
 summarize_with_gemini()  ← Gemini analyst: 300-400 word executive summary draft
       │
       ▼
 review_with_gemini()     ← Gemini editor: improves accuracy + extracts key developments
       │
       ▼
 generate_pdf()           ← A4 PDF: Key Developments + Executive Summary + Sources
       │
       ▼
india_security_YYYY-MM-DD.pdf
```

### News Sources

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
| NewsAPI (5 keywords) | API |

---

## Automate Daily (Windows Task Scheduler)

1. Open **Task Scheduler** → Create Basic Task
2. **Trigger:** Daily at 7:00 AM
3. **Action:** Start a program
   - Program: `python`
   - Arguments: `C:\path\to\india_security_news.py`
   - Start in: `C:\path\to\news-agent\`

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `0 articles found` | Lower threshold to `2` in `is_security_relevant()` |
| `RESOURCE_EXHAUSTED` | Gemini free tier daily quota hit — try again tomorrow or use a new key |
| NewsAPI skipped | Add key to `NEWSAPI_KEY` in script |
| PDF not saving | Set `OUTPUT_DIR` to an absolute path |

---

## Project Structure

```
news-agent/
├── india_security_news.py   # Main script
├── requirements.txt         # Python dependencies
├── SKILL.md                 # Claude Code skill definition
└── README.md                # This file
```

---

## License

For informational and educational purposes only. News content belongs to respective publishers.
