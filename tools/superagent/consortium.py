#!/usr/bin/env python3
"""
⟡ SUPERAGENT — Multi-AI Consortium v2.0
Now with REAL web search before model analysis.

The Problem with v1.0:
- Models hallucinated news from training data
- No actual web search = no real-time info

v2.0 Flow:
1. Web search for actual news (via DuckDuckGo or NewsAPI)
2. Feed REAL articles to models
3. Models analyze with their lenses
4. Synthesize into brief

Usage:
    python3 consortium.py digest [--email]
    python3 consortium.py search "query"  # Test search
"""

import os
import json
import asyncio
import aiohttp
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import argparse
import re

# Load .env
ENV_FILE = Path(__file__).parent / ".env"
if ENV_FILE.exists():
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            if value:
                os.environ[key] = value

# Config
VAULT = Path.home() / "Library/Mobile Documents/iCloud~md~obsidian/Documents/MirrorDNA-Vault"
BRIEFINGS_DIR = VAULT / "Superagent" / "briefings"
EMAILS = ["paul@activemirror.ai", "pauldesai@gmail.com"]

# Model Roles
ROLES = {
    "gpt": {"role": "Narrative & Framing", "prompt": "Identify narratives and framing shifts in these articles."},
    "deepseek": {"role": "Facts & Metrics", "prompt": "Extract concrete facts, numbers, and specifications."},
    "groq": {"role": "Noise Filter", "prompt": "What is hype vs durable change? What will matter in 6 months?"},
    "mistral": {"role": "Nuance & Dissent", "prompt": "Find what's being overlooked. What's the counter-narrative?"}
}

MODELS = {
    "gpt": {"api_key_env": "OPENAI_API_KEY", "model": "gpt-4o-mini", "endpoint": "https://api.openai.com/v1/chat/completions"},
    "deepseek": {"api_key_env": "DEEPSEEK_API_KEY", "model": "deepseek-chat", "endpoint": "https://api.deepseek.com/v1/chat/completions"},
    "groq": {"api_key_env": "GROQ_API_KEY", "model": "llama-3.3-70b-versatile", "endpoint": "https://api.groq.com/openai/v1/chat/completions"},
    "mistral": {"api_key_env": "MISTRAL_API_KEY", "model": "mistral-small-latest", "endpoint": "https://api.mistral.ai/v1/chat/completions"}
}


# ═══════════════════════════════════════════════════════════════
# WEB SEARCH — Get REAL news
# ═══════════════════════════════════════════════════════════════

async def search_duckduckgo(query: str, max_results: int = 10) -> List[Dict]:
    """Search DuckDuckGo for recent news."""
    # Use DuckDuckGo HTML search (no API key needed)
    url = "https://html.duckduckgo.com/html/"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data={"q": query + " news 2026", "t": "h_", "ia": "news"}, headers=headers, timeout=30) as resp:
                if resp.status != 200:
                    print(f"⚠️ DuckDuckGo returned {resp.status}")
                    return []
                
                html = await resp.text()
                
                # Parse results (basic extraction)
                results = []
                # Find result blocks
                pattern = r'<a rel="nofollow" class="result__a" href="([^"]+)"[^>]*>([^<]+)</a>'
                snippet_pattern = r'<a class="result__snippet"[^>]*>([^<]+)</a>'
                
                links = re.findall(pattern, html)
                snippets = re.findall(snippet_pattern, html)
                
                for i, (link, title) in enumerate(links[:max_results]):
                    # Decode URL
                    if "uddg=" in link:
                        actual_url = link.split("uddg=")[-1].split("&")[0]
                        from urllib.parse import unquote
                        actual_url = unquote(actual_url)
                    else:
                        actual_url = link
                    
                    results.append({
                        "title": title.strip(),
                        "url": actual_url,
                        "snippet": snippets[i] if i < len(snippets) else ""
                    })
                
                return results
                
    except Exception as e:
        print(f"⚠️ Search error: {e}")
        return []


async def fetch_article_content(url: str, max_chars: int = 2000) -> str:
    """Fetch article content (basic extraction)."""
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=15) as resp:
                if resp.status != 200:
                    return ""
                
                html = await resp.text()
                
                # Basic content extraction (remove scripts, styles, extract text)
                # Remove script/style
                html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
                html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
                
                # Get text from paragraphs
                paragraphs = re.findall(r'<p[^>]*>([^<]+)</p>', html)
                text = ' '.join(paragraphs)
                
                # Clean up
                text = re.sub(r'\s+', ' ', text).strip()
                
                return text[:max_chars]
                
    except Exception as e:
        return ""


async def gather_news(topics: List[str] = None) -> str:
    """Gather real news from the web."""
    if topics is None:
        topics = [
            "AI artificial intelligence news today",
            "OpenAI Anthropic Google AI",
            "tech industry news today",
            "AI regulation policy"
        ]
    
    all_articles = []
    
    for topic in topics:
        print(f"  Searching: {topic}")
        results = await search_duckduckgo(topic, max_results=5)
        
        for r in results[:3]:  # Top 3 per topic
            content = await fetch_article_content(r["url"])
            if content:
                all_articles.append({
                    "title": r["title"],
                    "url": r["url"],
                    "content": content[:1000]  # Limit content
                })
    
    if not all_articles:
        return "No articles found. Web search may have failed."
    
    # Format for models
    news_text = f"# News Articles ({datetime.now().strftime('%Y-%m-%d')})\n\n"
    for i, article in enumerate(all_articles[:12], 1):  # Max 12 articles
        news_text += f"## {i}. {article['title']}\n"
        news_text += f"URL: {article['url']}\n"
        news_text += f"{article['content'][:500]}...\n\n"
    
    return news_text


# ═══════════════════════════════════════════════════════════════
# MODEL QUERIES
# ═══════════════════════════════════════════════════════════════

async def query_model(model_key: str, news_content: str, lens_prompt: str) -> Dict:
    """Query a model with real news content."""
    config = MODELS[model_key]
    api_key = os.getenv(config["api_key_env"])
    
    if not api_key:
        return {"model": model_key, "error": "No API key"}

    full_prompt = f"""Today's date is {datetime.now().strftime('%Y-%m-%d')}.

LENS: {lens_prompt}

Here are REAL news articles from today:

{news_content}

Based ONLY on these articles, provide your analysis. Be specific and cite article numbers."""
    
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": config["model"],
        "messages": [{"role": "user", "content": full_prompt}],
        "temperature": 0.3,
        "max_tokens": 800
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(config["endpoint"], headers=headers, json=payload, timeout=60) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    return {"model": model_key, "error": f"HTTP {resp.status}: {error_text[:200]}"}
                data = await resp.json()
                content = data["choices"][0]["message"]["content"]
                return {"model": model_key, "response": content, "role": lens_prompt}
    except Exception as e:
        return {"model": model_key, "error": str(e)}


async def synthesize_brief(results: List[Dict], news_content: str) -> str:
    """Synthesize all model outputs into final brief."""
    
    synth_prompt = f"""Today is {datetime.now().strftime('%Y-%m-%d')}.

You are synthesizing analysis from 4 AI models who read today's news.

MODEL ANALYSES:
{json.dumps([r for r in results if "response" in r], indent=2)}

ORIGINAL NEWS SUMMARY:
{news_content[:2000]}

Create a strict Daily Brief in this format:

# ⟡ Daily Consortium Brief — {datetime.now().strftime('%Y-%m-%d')}

## 1. What Changed (Max 5 bullets)
[Key developments from TODAY's news only]

## 2. What Matters (Max 3 bullets)  
[Why these matter for Paul/MirrorDNA]

## 3. What Can Be Ignored (Max 3 bullets)
[Noise to filter out]

## 4. Risks / Drift
[Any concerning patterns]

## 5. Suggested Action
[Specific: "Do X" or "Monitor Y" or "No action needed"]

## 6. Dissenting View
[Counter-narrative if any]

RULES:
- ONLY cite news from TODAY ({datetime.now().strftime('%Y-%m-%d')})
- Max 15 bullets total
- Be specific with company names and facts
- If nothing notable today, say "Quiet news day"
"""
    
    result = await query_model("gpt", synth_prompt, "You are the strict synthesizer.")
    return result.get("response", "Synthesis failed")


# ═══════════════════════════════════════════════════════════════
# MAIN DIGEST
# ═══════════════════════════════════════════════════════════════

async def run_digest(topic: str = None, send_email: bool = False):
    """Run the full digest with web search."""
    print(f"⟡ Consortium v2.0 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # Step 1: Gather real news
    print("⟡ Step 1: Gathering news from the web...")
    news_content = await gather_news()
    
    if "No articles found" in news_content:
        print("❌ Web search failed. Cannot generate brief without real news.")
        return None
    
    print(f"  Found {news_content.count('##')} articles")
    
    # Step 2: Query models with real news
    print("⟡ Step 2: Querying models...")
    tasks = []
    for key, role_conf in ROLES.items():
        if os.getenv(MODELS[key]["api_key_env"]):
            tasks.append(query_model(key, news_content, role_conf["prompt"]))
    
    if not tasks:
        print("❌ No API keys configured")
        return None
    
    results = await asyncio.gather(*tasks)
    
    success_count = sum(1 for r in results if "response" in r)
    print(f"  {success_count}/{len(tasks)} models responded")
    
    # Step 3: Synthesize
    print("⟡ Step 3: Synthesizing brief...")
    brief = await synthesize_brief(results, news_content)
    
    # Save
    BRIEFINGS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{datetime.now().strftime('%Y%m%d')}_Briefing.md"
    filepath = BRIEFINGS_DIR / filename
    filepath.write_text(brief)
    print(f"✓ Saved to {filepath}")
    
    # Also save raw news for reference
    news_file = BRIEFINGS_DIR / f"{datetime.now().strftime('%Y%m%d')}_RawNews.md"
    news_file.write_text(news_content)
    
    if send_email:
        do_send_email(brief)
    
    return brief


def do_send_email(content: str):
    """Send digest via SMTP."""
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 465))
    
    if not smtp_user or not smtp_pass:
        print("⚠️ No SMTP credentials")
        return

    msg = MIMEMultipart()
    msg['From'] = f"Consortium <{smtp_user}>"
    msg['To'] = ", ".join(EMAILS)
    msg['Subject'] = f"⟡ Daily Brief — {datetime.now().strftime('%Y-%m-%d')}"
    msg.attach(MIMEText(content, 'plain'))

    try:
        server = smtplib.SMTP_SSL(smtp_host, smtp_port)
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        print(f"✓ Email sent to {EMAILS}")
    except Exception as e:
        print(f"❌ Email failed: {e}")


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["digest", "search", "test"])
    parser.add_argument("query", nargs="?", default="")
    parser.add_argument("--email", action="store_true")
    args = parser.parse_args()
    
    if args.command == "digest":
        asyncio.run(run_digest(args.query or None, args.email))
    
    elif args.command == "search":
        # Test web search
        query = args.query or "AI news today"
        print(f"⟡ Testing search: {query}")
        results = asyncio.run(search_duckduckgo(query))
        for r in results:
            print(f"  - {r['title']}")
            print(f"    {r['url']}")
    
    elif args.command == "test":
        # Test full pipeline
        print("⟡ Testing Consortium v2.0...")
        asyncio.run(run_digest(send_email=False))


if __name__ == "__main__":
    main()
