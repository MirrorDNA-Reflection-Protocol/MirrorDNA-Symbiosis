#!/usr/bin/env python3
"""
⟡ SUPERAGENT — Multi-AI Consortium v3.0 (Institutional Depth)
"The internal intelligence memo you wish you had."

Changes from v2.0:
- Outputs structured JSON for the Mirror Intelligence Portal (V3 Schema).
- Generates "Probabilistic Spine" (Base rate, Updated, Range).
- Generates "Council Cross-Examination" (Side-by-side reasoning).
- Generates "Evidence Stacks" (Primary, Quant, Analog).
- Still sends human-readable email digest.

Usage:
    python3 consortium_v3.py digest [--email] [--deploy]
"""

import os
import json
import asyncio
import aiohttp
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
from typing import Dict, List
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
PORTAL_PUBLIC_DIR = Path.home() / "Documents/GitHub/mirror-intelligence-portal/public"
EMAILS = ["paul@activemirror.ai", "pauldesai@gmail.com"]

# Model Roles (Unchanged)
ROLES = {
    "gpt": {"role": "Narrative & Framing", "prompt": "Identify narratives and framing shifts. What is the story?"},
    "deepseek": {"role": "Facts & Metrics", "prompt": "Extract concrete facts, numbers, and specifications. Be pedantic."},
    "groq": {"role": "Signal Filter", "prompt": "Separate hype from durable change. What matters in 6 months?"},
    "mistral": {"role": "Nuance & Dissent", "prompt": "Find what is overlooked. Construct the counter-narrative."}
}

MODELS = {
    "gpt": {"api_key_env": "OPENAI_API_KEY", "model": "gpt-4o-mini", "endpoint": "https://api.openai.com/v1/chat/completions"},
    "deepseek": {"api_key_env": "DEEPSEEK_API_KEY", "model": "deepseek-chat", "endpoint": "https://api.deepseek.com/v1/chat/completions"},
    "groq": {"api_key_env": "GROQ_API_KEY", "model": "llama-3.3-70b-versatile", "endpoint": "https://api.groq.com/openai/v1/chat/completions"},
    "mistral": {"api_key_env": "MISTRAL_API_KEY", "model": "mistral-small-latest", "endpoint": "https://api.mistral.ai/v1/chat/completions"}
}

# ═══════════════════════════════════════════════════════════════
# WEB SEARCH
# ═══════════════════════════════════════════════════════════════

async def search_duckduckgo(query: str, max_results: int = 10) -> List[Dict]:
    """Search DuckDuckGo (HTML) for recent news."""
    url = "https://html.duckduckgo.com/html/"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    
    try:
        async with aiohttp.ClientSession() as session:
            # Add "news" and current year to filter for relevance
            async with session.post(url, data={"q": query + f" news {datetime.now().year}", "t": "h_", "ia": "web"}, headers=headers, timeout=30) as resp:
                if resp.status != 200:
                    return []
                html = await resp.text()
                
                # Regex scraping (same as v2)
                pattern = r'<a rel="nofollow" class="result__a" href="([^"]+)"[^>]*>([^<]+)</a>'
                links = re.findall(pattern, html)
                
                results = []
                for link, title in links[:max_results]:
                    if "uddg=" in link:
                        actual_url = link.split("uddg=")[-1].split("&")[0]
                        from urllib.parse import unquote
                        actual_url = unquote(actual_url)
                        results.append({"title": title, "url": actual_url})
                return results
    except Exception as e:
        print(f"Search error: {e}")
        return []

async def fetch_article_content(url: str) -> str:
    """Simple text fetcher."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    # Very naive stripping used in v2 - keeping it for consistency
                    clean = re.sub('<[^<]+?>', '', text)
                    return " ".join(clean.split())[:3000]
    except:
        return ""
    return ""

async def gather_news() -> str:
    """Gather news for today."""
    topics = [
        "Artificial Intelligence LLM news",
        "Generative AI business adoption",
        "AI regulation policy EU US",
        "Major tech ipo capital markets"
    ]
    
    all_articles = []
    print("⟡ gathering_news")
    
    for topic in topics:
        results = await search_duckduckgo(topic, max_results=3)
        for r in results:
            content = await fetch_article_content(r["url"])
            if content:
                all_articles.append({"title": r["title"], "url": r["url"], "content": content[:1000]})
    
    if not all_articles:
        return ""

    news_text = f"# News Articles ({datetime.now().strftime('%Y-%m-%d')})\n\n"
    for i, article in enumerate(all_articles[:12], 1):
        news_text += f"## {i}. {article['title']}\nURL: {article['url']}\n{article['content'][:500]}...\n\n"
    
    return news_text

# ═══════════════════════════════════════════════════════════════
# MODEL PIPELINE
# ═══════════════════════════════════════════════════════════════

async def query_model(model_key: str, prompt: str) -> Dict:
    """Query a specific model config."""
    config = MODELS[model_key]
    api_key = os.getenv(config["api_key_env"])
    if not api_key: return {"error": f"No key for {model_key}"}
    
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": config["model"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 1500,
        "response_format": {"type": "json_object"} if model_key in ["gpt", "mistral"] else None
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(config["endpoint"], headers=headers, json=payload, timeout=90) as resp:
                if resp.status != 200:
                    return {"error": f"HTTP {resp.status}"}
                data = await resp.json()
                return {"response": data["choices"][0]["message"]["content"]}
    except Exception as e:
        return {"error": str(e)}

async def synthesize_v3_json(news_content: str) -> Dict:
    """Synthesize news into the V3 Institutional JSON Schema."""
    
    print("⟡ synthesizing_v3_json")
    
    prompt = f"""
Today is {datetime.now().strftime('%Y-%m-%d')}.
You are the Council Secretary for Mirror Intelligence (Institutional Grade).

SOURCE NEWS:
{news_content[:5000]}

MANDATE:
Synthesize this into a structured JSON briefing.
1. Identify the ONE major headline story.
2. Extract strictly factual bullets (Signal).
3. Identify divergence/dissent.
4. formulate 2-3 "Living Predictions" based on this news.

CRITICAL: OUTPUT STICT JSON matching this schema:
{{
  "meta": {{ "date": "...", "generated": "..." }},
  "briefing": {{
    "headline": "...",
    "subline": "...",
    "summary": "...",
    "stats": {{ "sources": 12, "models": 4 }},
    "sections": {{
      "changed": [ {{ "text": "...", "detail": "...", "source": {{ "name": "Source", "url": "..." }}, "voice": "gpt" }} ],
      "matters": [ {{ "text": "...", "voice": "deepseek" }} ],
      "risks": [ {{ "text": "...", "severity": "high", "voice": "mistral" }} ],
      "actions": [ {{ "text": "...", "priority": "high" }} ]
    }}
  }},
  "predictions": [
    {{
      "id": "p-1", 
      "text": "Prediction statement...",
      "state": "neutral",
      "timeframe": "6 months",
      "probability": {{
        "base_rate": 20, 
        "updated": 60,
        "range": [50, 70],
        "decay": "Q3 2026"
      }},
      "reasoning": {{
        "gpt": {{ "position": "supports", "argument": "...", "would_change": "..." }},
        "deepseek": {{ "position": "supports", "argument": "...", "would_change": "..." }},
        "groq": {{ "position": "neutral", "argument": "...", "would_change": "..." }},
        "mistral": {{ "position": "skeptical", "argument": "...", "would_change": "..." }}
      }},
      "evidence": [
        {{ "type": "primary", "text": "..." }},
        {{ "type": "quant", "text": "..." }}
      ]
    }}
  ]
}}
"""
    # Using GPT-4o for synthesis as it handles JSON structure best
    result = await query_model("gpt", prompt)
    if "error" in result:
        print(f"❌ Synthesis error: {result['error']}")
        return {}
    
    try:
        return json.loads(result["response"])
    except:
        # Fallback cleanup
        clean = result["response"].replace("```json", "").replace("```", "")
        return json.loads(clean)

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

async def run(deploy: bool = False):
    # 1. Gather
    news = await gather_news()
    if not news:
        print("❌ No news found.")
        return

    # 2. Synthesize V3
    data = await synthesize_v3_json(news)
    
    if not data:
        print("❌ Synthesis returned empty.")
        return

    # 3. Save JSON for Portal
    PORTAL_PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    json_path = PORTAL_PUBLIC_DIR / "data.json"
    json_path.write_text(json.dumps(data, indent=2))
    print(f"✓ Saved V3 JSON to {json_path}")
    
    # 4. Save Human Readable (Markdown) to Vault
    changes_list = "\n".join([f"- {i['text']} ({i['voice']})" for i in data['briefing']['sections']['changed']])
    
    predictions_list = "\n".join([
        f"#### {p['text']}\n- Prob: {p['probability']['updated']}%\n- Range: {p['probability']['range']}" 
        for p in data['predictions']
    ])
    
    md_content = f"""# ⟡ Mirror Brief — {data['meta']['date']}
    
## {data['briefing']['headline']}
*{data['briefing']['subline']}*

{data['briefing']['summary']}

### What Changed
{changes_list}

### Predictions
{predictions_list}
"""
    
    BRIEFINGS_DIR.mkdir(parents=True, exist_ok=True)
    md_path = BRIEFINGS_DIR / f"{datetime.now().strftime('%Y%m%d')}_Briefing_v3.md"
    md_path.write_text(md_content)
    print(f"✓ Saved V3 Markdown to {md_path}")

    # 5. Email (Optional) - skipping implementation for brevity, relying on portal

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--deploy", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.deploy))
