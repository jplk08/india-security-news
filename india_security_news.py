"""
India National Security & Threat News Summarizer
=================================================
Fetches threat/security-related news about India from multiple sources,
uses Google Gemini AI to summarize and review, then saves as a dated PDF report.

Sources: Google News RSS, NewsAPI (free tier), BBC/Reuters/ToI/HT/Hindu/NDTV/IE
Output:  india_security_YYYY-MM-DD.pdf

Requirements:
    pip install feedparser requests reportlab google-genai newsapi-python python-dotenv

Setup:
    Copy .env.example to .env and fill in your API keys.
"""

import os
import re
import sys
import time
import feedparser
import requests
from io import BytesIO
from xml.sax.saxutils import escape as xml_escape
from google import genai
from google.genai import errors as genai_errors
from datetime import datetime, date, timedelta, timezone

# --- PDF Generation ---
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER

# Load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY", "")
GEMINI_KEY  = os.environ.get("GEMINI_API_KEY", "")
OUTPUT_DIR  = os.environ.get("OUTPUT_DIR", ".")

# Validate OUTPUT_DIR
if not os.path.isdir(OUTPUT_DIR):
    print(f"[!] OUTPUT_DIR '{OUTPUT_DIR}' does not exist. Using current directory.")
    OUTPUT_DIR = "."

# Validate required keys
if not GEMINI_KEY:
    print("[!] GEMINI_API_KEY is not set. Add it to your .env file or set the environment variable.")
    sys.exit(1)

# Configure Gemini client
_gemini_client = genai.Client(api_key=GEMINI_KEY)
GEMINI_MODELS  = ["models/gemini-2.5-flash", "models/gemini-2.0-flash", "models/gemini-2.0-flash-lite"]

RSS_FETCH_TIMEOUT = 15   # seconds per RSS feed request
RSS_MAX_BYTES     = 5 * 1024 * 1024  # 5 MB max per feed response


# ─────────────────────────────────────────────
# GEMINI HELPER
# ─────────────────────────────────────────────
def _gemini_generate(prompt: str) -> str:
    """Call Gemini with automatic model fallback and retry on rate-limit/overload."""
    for model in GEMINI_MODELS:
        for attempt in range(3):
            try:
                response = _gemini_client.models.generate_content(model=model, contents=prompt)
                return response.text.strip()
            except (genai_errors.ClientError, genai_errors.ServerError) as e:
                err = str(e)
                if "403" in err or "PERMISSION_DENIED" in err or "leaked" in err.lower():
                    raise RuntimeError(
                        "Gemini API key is invalid or has been flagged as leaked. "
                        "Generate a new key at aistudio.google.com."
                    )
                if any(x in err for x in ("429", "RESOURCE_EXHAUSTED", "503", "UNAVAILABLE")):
                    wait = 20 * (attempt + 1)
                    print(f"  [Gemini] Transient error on {model}, retrying in {wait}s (attempt {attempt+1}/3)...")
                    time.sleep(wait)
                else:
                    print(f"  [Gemini] Error on {model} ({type(e).__name__}). Trying next model...")
                    break  # exits attempt loop → outer loop continues to next model
    raise RuntimeError("All Gemini models exhausted. Check your API key and quota.")


# ─────────────────────────────────────────────
# SEARCH KEYWORDS
# ─────────────────────────────────────────────
SECURITY_KEYWORDS = [
    "India security threat",
    "India national security",
    "India military attack",
    "India border tension",
    "India terrorism",
    "India cyber attack",
    "India defense threat",
    "India nuclear",
    "India militant",
    "India insurgency",
    "Pakistan India conflict",
    "China India border",
    "India espionage",
]


# ─────────────────────────────────────────────
# RSS FEEDS
# ─────────────────────────────────────────────
RSS_FEEDS = {
    "Google News - India Security": "https://news.google.com/rss/search?q=India+national+security+threat&hl=en-IN&gl=IN&ceid=IN:en",
    "Google News - India Military":  "https://news.google.com/rss/search?q=India+military+defense+attack&hl=en-IN&gl=IN&ceid=IN:en",
    "Google News - India Terror":    "https://news.google.com/rss/search?q=India+terrorism+threat&hl=en-IN&gl=IN&ceid=IN:en",
    "Google News - India Cyber":     "https://news.google.com/rss/search?q=India+cyber+attack+hack&hl=en-IN&gl=IN&ceid=IN:en",
    "Google News - India Pakistan":  "https://news.google.com/rss/search?q=India+Pakistan+conflict+border&hl=en-IN&gl=IN&ceid=IN:en",
    "Google News - India China":     "https://news.google.com/rss/search?q=India+China+border+LAC&hl=en-IN&gl=IN&ceid=IN:en",
    "BBC India":                     "https://feeds.bbci.co.uk/news/world/asia/india/rss.xml",
    "Reuters India":                 "https://feeds.reuters.com/reuters/INtopNews",
    "Times of India - Nation":       "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    "Hindustan Times":               "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml",
    "The Hindu - National":          "https://www.thehindu.com/news/national/feeder/default.rss",
    "NDTV India":                    "https://feeds.ndtv.com/ndtv/national?pfrom=home-ndtvrss",
    "Indian Express":                "https://indianexpress.com/section/india/feed/",
}


# ─────────────────────────────────────────────
# STEP 1 — FETCH ARTICLES
# ─────────────────────────────────────────────
def _fetch_feed_with_timeout(url: str) -> feedparser.FeedParserDict:
    """Fetch RSS feed via requests (with timeout + size cap) then parse."""
    resp = requests.get(
        url,
        timeout=RSS_FETCH_TIMEOUT,
        headers={"User-Agent": "IndiaSecurityNewsBot/1.0"},
        stream=True,
    )
    resp.raise_for_status()
    raw = resp.raw.read(RSS_MAX_BYTES)
    return feedparser.parse(BytesIO(raw))


def fetch_rss_articles() -> list:
    """Fetch articles from all RSS feeds published in the last 7 days."""
    articles = []
    seen_titles = set()
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    for source_name, url in RSS_FEEDS.items():
        try:
            feed = _fetch_feed_with_timeout(url)
            for entry in feed.entries[:20]:
                title   = entry.get("title", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()
                link    = entry.get("link", "")

                if not title or title in seen_titles:
                    continue

                pub = entry.get("published_parsed") or entry.get("updated_parsed")
                if pub:
                    pub_dt = datetime(*pub[:6], tzinfo=timezone.utc)
                    if pub_dt < cutoff:
                        continue

                combined = (title + " " + summary).lower()
                if is_security_relevant(combined):
                    seen_titles.add(title)
                    articles.append({
                        "source": source_name,
                        "title":  sanitize_text(title),
                        "text":   sanitize_text(clean_html(summary)),
                        "url":    sanitize_url(link),
                    })
        except requests.exceptions.Timeout:
            print(f"  [RSS] Timeout fetching {source_name} — skipping.")
        except requests.exceptions.RequestException as e:
            print(f"  [RSS] Could not fetch {source_name}: {type(e).__name__}")
        except Exception as e:
            print(f"  [RSS] Parse error for {source_name}: {type(e).__name__}")

    return articles


def fetch_newsapi_articles() -> list:
    """Fetch articles from NewsAPI free tier."""
    if not NEWSAPI_KEY:
        print("  [NewsAPI] Skipping — NEWSAPI_KEY not set in .env.")
        return []

    articles = []
    seen_titles = set()
    seven_days_ago = (date.today() - timedelta(days=7)).isoformat()

    for keyword in SECURITY_KEYWORDS[:5]:
        try:
            resp = requests.get(
                "https://newsapi.org/v2/everything",
                headers={"X-Api-Key": NEWSAPI_KEY},   # key in header, not URL
                params={
                    "q":        keyword,
                    "from":     seven_days_ago,
                    "sortBy":   "publishedAt",
                    "language": "en",
                    "pageSize": 5,
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("articles", []):
                title   = (item.get("title") or "").strip()
                content = (item.get("description") or item.get("content") or "").strip()
                source  = item.get("source", {}).get("name", "NewsAPI")
                link    = item.get("url", "")

                if not title or title in seen_titles:
                    continue

                combined = (title + " " + content).lower()
                if is_security_relevant(combined):
                    seen_titles.add(title)
                    articles.append({
                        "source": sanitize_text(source),
                        "title":  sanitize_text(title),
                        "text":   sanitize_text(clean_html(content)),
                        "url":    sanitize_url(link),
                    })
        except requests.exceptions.RequestException as e:
            print(f"  [NewsAPI] Request error for '{keyword}': {type(e).__name__}")
        except (KeyError, ValueError) as e:
            print(f"  [NewsAPI] Parse error for '{keyword}': {type(e).__name__}")

    return articles


# ─────────────────────────────────────────────
# STEP 2 — FILTER + CLEAN
# ─────────────────────────────────────────────
THREAT_TERMS = [
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

NON_SECURITY_TERMS = [
    "cricket", "ipl", "bollywood", "movies", "film", "actor", "actress",
    "wedding", "marriage", "fashion", "recipe", "weather forecast",
    "stock market", "sensex", "nifty", "share price", "mutual fund",
]


def is_security_relevant(text: str) -> bool:
    text = text.lower()
    if any(term in text for term in NON_SECURITY_TERMS):
        return False
    has_india = "india" in text or "indian" in text
    threat_count = sum(1 for t in THREAT_TERMS if t in text)
    return has_india and threat_count >= 3


def clean_html(text: str) -> str:
    """Strip HTML tags and normalize whitespace."""
    text = re.sub(r"<[^>]+>", " ", text)
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


# ─────────────────────────────────────────────
# STEP 3 — SUMMARIZE WITH GEMINI
# ─────────────────────────────────────────────
def _build_corpus(articles: list) -> str:
    lines = []
    for i, a in enumerate(articles, 1):
        lines.append(f"{i}. [{a['source']}] {a['title']}")
        if a["text"]:
            lines.append(f"   {a['text'][:400]}")
        lines.append("")
    return "\n".join(lines)


def summarize_with_gemini(articles: list) -> str:
    """Draft a 300-400 word intelligence executive summary using Gemini."""
    corpus = _build_corpus(articles)

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

    return _gemini_generate(prompt)


# ─────────────────────────────────────────────
# STEP 4 — REVIEW + STRUCTURE WITH GEMINI
# ─────────────────────────────────────────────
def review_with_gemini(draft: str, articles: list) -> tuple:
    """
    Senior editor pass: improves the draft and extracts key developments.
    Returns (improved_summary: str, key_developments: list[str]).
    """
    headlines = "\n".join(
        f"- [{a['source']}] {a['title']}" for a in articles[:40]
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

    return _parse_review_response(_gemini_generate(prompt), draft)


def _parse_review_response(raw: str, fallback: str) -> tuple:
    summary  = fallback
    key_devs = []

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
    except Exception:
        pass

    return summary, key_devs


# ─────────────────────────────────────────────
# STEP 5 — BUILD SOURCE LIST
# ─────────────────────────────────────────────
def build_source_list(articles: list) -> list:
    seen, result = set(), []
    for a in articles:
        key = a["title"][:80]
        if key not in seen:
            seen.add(key)
            result.append((a["source"], a["title"], a["url"]))
    return result[:25]


# ─────────────────────────────────────────────
# STEP 6 — GENERATE PDF
# ─────────────────────────────────────────────
def generate_pdf(summary: str, key_devs: list, sources: list, article_count: int) -> str:
    today_str    = date.today().strftime("%Y-%m-%d")
    display_date = date.today().strftime("%B %d, %Y")
    filename     = os.path.join(OUTPUT_DIR, f"india_security_{today_str}.pdf")

    doc = SimpleDocTemplate(
        filename, pagesize=A4,
        rightMargin=2.5*cm, leftMargin=2.5*cm,
        topMargin=2.5*cm,   bottomMargin=2.5*cm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("ReportTitle", parent=styles["Title"],
        fontSize=18, textColor=colors.HexColor("#1a237e"), spaceAfter=4, alignment=TA_CENTER)
    subtitle_style = ParagraphStyle("Subtitle", parent=styles["Normal"],
        fontSize=11, textColor=colors.HexColor("#455a64"), spaceAfter=2, alignment=TA_CENTER)
    meta_style = ParagraphStyle("Meta", parent=styles["Normal"],
        fontSize=9, textColor=colors.HexColor("#78909c"), spaceAfter=16, alignment=TA_CENTER)
    section_header_style = ParagraphStyle("SectionHeader", parent=styles["Heading2"],
        fontSize=12, textColor=colors.HexColor("#b71c1c"), spaceBefore=14, spaceAfter=6)
    body_style = ParagraphStyle("BodyText", parent=styles["Normal"],
        fontSize=10.5, leading=16, textColor=colors.HexColor("#212121"),
        alignment=TA_JUSTIFY, spaceAfter=10)
    bullet_style = ParagraphStyle("Bullet", parent=styles["Normal"],
        fontSize=10.5, leading=15, textColor=colors.HexColor("#212121"),
        leftIndent=15, spaceAfter=5)
    source_label_style = ParagraphStyle("SourceLabel", parent=styles["Normal"],
        fontSize=9, textColor=colors.HexColor("#37474f"), leading=13, leftIndent=10, spaceAfter=2)
    footer_style = ParagraphStyle("Footer", parent=styles["Normal"],
        fontSize=8, textColor=colors.HexColor("#9e9e9e"), alignment=TA_CENTER, spaceBefore=20)

    story = []

    story.append(Paragraph("India National Security Digest", title_style))
    story.append(Paragraph("Daily Threat &amp; Security Intelligence Summary", subtitle_style))
    story.append(Paragraph(
        f"Report Date: {display_date}  |  Articles Analyzed: {article_count}  |  "
        "AI-Reviewed by Google Gemini",
        meta_style
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a237e"), spaceAfter=10))

    if key_devs:
        story.append(Paragraph("KEY DEVELOPMENTS", section_header_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e0e0e0"), spaceAfter=8))
        for dev in key_devs:
            story.append(Paragraph(f"• {xml_escape(dev)}", bullet_style))
        story.append(Spacer(1, 0.3*cm))

    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e0e0e0"), spaceAfter=8))
    story.append(Paragraph("EXECUTIVE SUMMARY", section_header_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e0e0e0"), spaceAfter=8))

    words = summary.split()
    for i in range(0, len(words), 100):
        story.append(Paragraph(xml_escape(" ".join(words[i:i+100])), body_style))

    story.append(Spacer(1, 0.4*cm))

    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e0e0e0"), spaceAfter=8))
    story.append(Paragraph("NEWS SOURCES REFERENCED", section_header_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e0e0e0"), spaceAfter=8))
    for i, (src, title, url) in enumerate(sources, 1):
        display_title = title[:110] + ("..." if len(title) > 110 else "")
        label = f"{i}. [{xml_escape(src)}]  {xml_escape(display_title)}"
        story.append(Paragraph(label, source_label_style))

    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e0e0e0")))
    story.append(Paragraph(
        "Auto-generated by India Security News Summarizer  •  For informational purposes only  •  "
        "AI-powered by Google Gemini  •  "
        "Sources: Google News RSS, NewsAPI, BBC, Reuters, ToI, NDTV, Indian Express, The Hindu",
        footer_style
    ))

    doc.build(story)
    return filename


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  India National Security News Summarizer")
    print(f"  Date: {date.today().strftime('%B %d, %Y')}")
    print("=" * 55)

    print("\n[1/5] Fetching RSS feed articles...")
    rss_articles = fetch_rss_articles()
    print(f"      Found {len(rss_articles)} relevant RSS articles.")

    print("\n[2/5] Fetching NewsAPI articles...")
    api_articles = fetch_newsapi_articles()
    print(f"      Found {len(api_articles)} relevant NewsAPI articles.")

    all_articles = rss_articles + api_articles
    print(f"\n      Total articles for analysis: {len(all_articles)}")

    if not all_articles:
        print("\n[!] No articles found. Check your internet connection or broaden keyword filters.")
        return

    print("\n[3/5] Drafting executive summary with Gemini AI...")
    draft = summarize_with_gemini(all_articles)
    print(f"      Draft: {len(draft.split())} words.")

    print("\n[4/5] Reviewing and extracting key developments with Gemini AI...")
    summary, key_devs = review_with_gemini(draft, all_articles)
    print(f"      Final summary: {len(summary.split())} words | Key developments: {len(key_devs)}")

    print("\n[5/5] Building PDF report...")
    sources  = build_source_list(all_articles)
    pdf_path = generate_pdf(summary, key_devs, sources, len(all_articles))
    print(f"      PDF saved: {pdf_path}")

    print("\n[Done] Open the PDF to read today's security digest.")
    print("=" * 55)


if __name__ == "__main__":
    main()
