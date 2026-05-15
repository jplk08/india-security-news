---
name: india-security-news
description: >
  Generates a daily India national security and threat intelligence digest by
  fetching news from multiple sources (Google News RSS, NewsAPI, BBC, Reuters,
  Times of India, The Hindu, Hindustan Times), filtering for India-relevant
  threat/security content from the last 7 days, summarizing with Claude AI into
  a clean 300-400 word executive summary, reviewing and improving with a Claude
  editor pass, and saving as a dated PDF report. Use this skill whenever the
  user asks to: fetch/generate a security news digest for India, build or run a
  daily news summarizer, create a threat intelligence report, automate India
  security news collection, or mentions keywords like "daily news PDF", "India
  threat summary", "security digest", "news automation script", or "summarize
  security articles". Also trigger when the user wants to modify, extend, or
  re-run this workflow (e.g. add email delivery, change sources, adjust word
  count, change output format).
---

# India National Security News Summarizer

## Overview

This skill produces a daily PDF digest of India national security and threat
news. Summarization and content review are both performed by Claude AI
(claude-sonnet-4-6), producing a high-quality, factual intelligence briefing.
News is limited to the **last 7 days** to ensure relevance.

---

## Architecture

```
[RSS Feeds]  +  [NewsAPI]
      │               │
      ▼               ▼
  fetch_rss_articles()   fetch_newsapi_articles()
           │
           ▼
    is_security_relevant()   ← keyword filter + negative filter (sport/entertainment)
    date filter (last 7 days)
    threshold: ≥3 THREAT_TERMS
           │
           ▼
    summarize_with_claude()  ← Claude (claude-sonnet-4-6) intelligence analyst pass
           │                    → 300-400 word draft executive summary
           ▼
    review_with_claude()     ← Claude (claude-sonnet-4-6) senior editor pass
           │                    → improved summary + KEY_DEVELOPMENTS bullet list
           ▼
    generate_pdf()           ← reportlab A4 PDF
           │                    sections: Key Developments, Executive Summary, Sources
           ▼
  india_security_YYYY-MM-DD.pdf
```

---

## Configuration (top of script)

| Variable         | Default                          | Purpose                              |
|------------------|----------------------------------|--------------------------------------|
| `NEWSAPI_KEY`    | *(your key)*                     | Free key from newsapi.org/register   |
| `ANTHROPIC_KEY`  | reads `ANTHROPIC_API_KEY` env var| Anthropic API key for Claude          |
| `OUTPUT_DIR`     | `.` (current folder)             | Where the PDF is saved               |

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
- Indian Express India

### NewsAPI (free tier — 100 req/day)
- Queries 5 of the 13 `SECURITY_KEYWORDS` per run
- Uses last 7 days as `from` date
- Skipped gracefully if key not configured

---

## Date Filtering

All articles are filtered to the **last 7 days**:
- RSS: uses `published_parsed` / `updated_parsed` from feed entries; articles without a date are included (some feeds omit it)
- NewsAPI: `from` parameter set to `today - 7 days`

---

## Filtering Logic

An article is kept only if **all** conditions are true:
1. Does **not** match any `NON_SECURITY_TERMS` (cricket, Bollywood, stock market, etc.)
2. Contains `"india"` or `"indian"` in title+summary
3. Matches **≥ 3** terms from the `THREAT_TERMS` list (covers: threat, attack,
   security, military, border, terror, cyber, nuclear, espionage, army, blast, drone, etc.)

---

## Summarization — Claude AI

`summarize_articles()` sends all article titles and snippets to
`claude-sonnet-4-6` with an intelligence-analyst prompt:

- Produces a 300-400 word flowing executive summary
- Focuses on significant threats, key actors, geographic hotspots, and implications
- Professional intelligence-briefing tone, no bullet points

---

## Review Pass — Claude AI

`review_summary()` sends the draft summary + all source headlines to
`claude-sonnet-4-6` acting as a senior intelligence editor:

- Checks accuracy against source headlines
- Flags missing major stories
- Improves clarity and professional tone
- Returns only the final improved summary (no commentary)

---

## PDF Output Structure

```
┌─────────────────────────────────────────────┐
│  🇮🇳  India National Security Digest         │  ← Title (dark blue)
│  Daily Threat & Security Intelligence Summary │
│  Report Date: May 14, 2026 | Articles: 43    │
├─────────────────────────────────────────────┤
│  EXECUTIVE SUMMARY                           │  ← Section (red)
│                                             │
│  [300-400 word reviewed paragraph...]       │
│                                             │
├─────────────────────────────────────────────┤
│  NEWS SOURCES REFERENCED                    │  ← Up to 20 sources
│  1. [BBC]  India border tensions...         │
│  2. [Reuters]  Army deploys...              │
│  ...                                        │
├─────────────────────────────────────────────┤
│  Auto-generated footer                      │
└─────────────────────────────────────────────┘
```

---

## Installation & Usage

### One-time setup
```bash
pip install feedparser requests reportlab anthropic newsapi-python
```

> `sumy`, `nltk`, and `numpy` are no longer required — summarization is fully handled by Claude.

Set your Anthropic API key:
```bash
# Windows (PowerShell)
$env:ANTHROPIC_API_KEY = "sk-ant-..."

# Or paste directly into ANTHROPIC_KEY in the script
```

Get a free NewsAPI key: https://newsapi.org/register
Paste it into `NEWSAPI_KEY` in the script.

### Run manually
```bash
python india_security_news.py
```

### Automate daily

**Windows (Task Scheduler):**
- Open Task Scheduler → Create Basic Task
- Trigger: Daily at 7:00 AM
- Action: Start a program → `python.exe`
- Arguments: `C:\path\to\india_security_news.py`

---

## Pipeline Steps

```
[1/5] Fetch RSS articles        → fetch_rss_articles()
[2/5] Fetch NewsAPI articles    → fetch_newsapi_articles()
[3/5] Draft summary             → summarize_with_claude()   [Claude analyst pass]
[4/5] Review + key developments → review_with_claude()      [Claude editor pass]
[5/5] Build PDF                 → generate_pdf()
```

---

## Common Customizations

### Change output folder
```python
OUTPUT_DIR = "C:/Users/yourname/SecurityReports"
```

### Add more RSS sources
```python
RSS_FEEDS["NDTV Security"] = "https://feeds.ndtv.com/ndtv/national?pfrom=home-ndtvrss"
RSS_FEEDS["Indian Express"] = "https://indianexpress.com/section/india/feed/"
```

### Focus on a specific threat type (e.g. cyber only)
Add to `SECURITY_KEYWORDS`:
```python
"India cyber threat 2026",
"India data breach",
"India critical infrastructure attack",
```

### Add email delivery
Use Python's `smtplib` to attach and send the PDF after `generate_pdf()`.
Ask Claude: *"Add Gmail email delivery to the india_security_news.py script"*

---

## Dependencies

| Library          | Purpose                        | Install                        |
|------------------|--------------------------------|--------------------------------|
| `feedparser`     | Parse RSS/Atom feeds           | `pip install feedparser`       |
| `requests`       | HTTP calls to NewsAPI          | `pip install requests`         |
| `anthropic`      | Claude AI summarization+review | `pip install anthropic`        |
| `reportlab`      | PDF generation                 | `pip install reportlab`        |
| `newsapi-python` | NewsAPI client (optional)      | `pip install newsapi-python`   |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `0 articles found` | Too-strict filter or internet issue | Lower threshold to `2` in `is_security_relevant()` |
| NewsAPI skipped | Key not set | Register at newsapi.org and add key to `NEWSAPI_KEY` |
| `ANTHROPIC_API_KEY not set` | Missing key | Set `ANTHROPIC_API_KEY` env var or paste into `ANTHROPIC_KEY` |
| PDF not saving | Wrong `OUTPUT_DIR` | Use absolute path or `"."` for current folder |
| Summary too short | Few articles fetched | Add more RSS feeds or broaden keywords |
| Claude call fails | API quota or network | Check Anthropic dashboard for usage/errors |

---

## File Output

```
india_security_2026-05-14.pdf   ← dated, never overwrites previous days
india_security_2026-05-15.pdf
india_security_2026-05-16.pdf
...
```
