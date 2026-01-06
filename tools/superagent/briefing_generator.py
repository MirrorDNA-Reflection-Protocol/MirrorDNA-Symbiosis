#!/usr/bin/env python3
"""
⟡ BRIEFING GENERATOR — Professional Newsletter Platform v1.0

Transforms raw consortium output into professional, publishable briefings with:
- Inline citations linked to sources
- Predictions section with tracking
- HTML/PDF output with beautiful design
- Distribution-ready format

Usage:
    python3 briefing_generator.py generate          # Generate from latest news
    python3 briefing_generator.py render FILE       # Render existing brief to HTML
    python3 briefing_generator.py predictions       # Show prediction accuracy

Author: Antigravity (Execution Twin)
For: Paul / Active Mirror
"""

import os
import json
import asyncio
import aiohttp
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re
import hashlib

# Paths
HOME = Path.home()
VAULT = HOME / "Library/Mobile Documents/iCloud~md~obsidian/Documents/MirrorDNA-Vault"
BRIEFINGS_DIR = VAULT / "Superagent" / "briefings"
PREDICTIONS_FILE = VAULT / "Superagent" / "predictions.json"
OUTPUT_DIR = VAULT / "Superagent" / "published"

# HTML Template
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>⟡ Daily Brief — {date}</title>
    <style>
        :root {{
            --bg: #0d1117;
            --card: #161b22;
            --border: #30363d;
            --text: #c9d1d9;
            --accent: #58a6ff;
            --gold: #f0c674;
            --green: #3fb950;
            --red: #f85149;
            --purple: #bc8cff;
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            padding: 2rem;
            max-width: 800px;
            margin: 0 auto;
        }}
        
        header {{
            text-align: center;
            margin-bottom: 3rem;
            padding: 2rem;
            background: linear-gradient(135deg, var(--card) 0%, #1a2332 100%);
            border-radius: 16px;
            border: 1px solid var(--border);
        }}
        
        .logo {{ font-size: 3rem; margin-bottom: 0.5rem; }}
        h1 {{ 
            font-size: 1.75rem; 
            font-weight: 600;
            color: var(--gold);
            margin-bottom: 0.5rem;
        }}
        .date {{ color: var(--accent); font-size: 0.9rem; }}
        .tagline {{ color: #8b949e; font-size: 0.85rem; margin-top: 1rem; }}
        
        section {{
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }}
        
        h2 {{
            font-size: 1.1rem;
            color: var(--accent);
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        h2 .icon {{ font-size: 1.2rem; }}
        
        ul {{ list-style: none; }}
        li {{
            padding: 0.75rem 0;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: flex-start;
            gap: 0.75rem;
        }}
        li:last-child {{ border-bottom: none; }}
        li::before {{ content: "→"; color: var(--accent); flex-shrink: 0; }}
        
        a {{ color: var(--accent); text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        
        .citation {{
            font-size: 0.75rem;
            background: var(--bg);
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
            margin-left: 0.5rem;
        }}
        
        .prediction {{
            background: linear-gradient(135deg, #1a2332 0%, #0d1117 100%);
            border-left: 3px solid var(--purple);
        }}
        
        .prediction h2 {{ color: var(--purple); }}
        
        .confidence {{
            font-size: 0.75rem;
            padding: 0.2rem 0.5rem;
            border-radius: 12px;
            margin-left: auto;
        }}
        .confidence.high {{ background: rgba(63, 185, 80, 0.2); color: var(--green); }}
        .confidence.medium {{ background: rgba(240, 198, 116, 0.2); color: var(--gold); }}
        .confidence.low {{ background: rgba(248, 81, 73, 0.2); color: var(--red); }}
        
        .sources {{
            margin-top: 2rem;
            padding: 1.5rem;
            background: var(--bg);
            border-radius: 8px;
            font-size: 0.85rem;
        }}
        
        .sources h3 {{ 
            font-size: 0.9rem; 
            color: #8b949e; 
            margin-bottom: 1rem; 
        }}
        
        .source-item {{
            display: flex;
            gap: 0.5rem;
            padding: 0.5rem 0;
            border-bottom: 1px solid var(--border);
        }}
        .source-item:last-child {{ border-bottom: none; }}
        .source-num {{ color: var(--accent); font-weight: 600; min-width: 2rem; }}
        .source-title {{ flex: 1; }}
        .source-domain {{ color: #8b949e; font-size: 0.8rem; }}
        
        footer {{
            text-align: center;
            margin-top: 3rem;
            padding: 1.5rem;
            color: #8b949e;
            font-size: 0.85rem;
        }}
        
        footer a {{ color: var(--gold); }}
        
        @media (max-width: 600px) {{
            body {{ padding: 1rem; }}
            header {{ padding: 1.5rem; }}
            section {{ padding: 1rem; }}
        }}
    </style>
</head>
<body>
    <header>
        <div class="logo">⟡</div>
        <h1>Daily Consortium Brief</h1>
        <div class="date">{date}</div>
        <div class="tagline">Multi-AI synthesis from GPT, DeepSeek, Groq, and Mistral</div>
    </header>
    
    {content}
    
    <div class="sources">
        <h3>📚 Sources</h3>
        {sources}
    </div>
    
    <footer>
        <p>Generated by <a href="https://activemirror.ai">Active Mirror</a></p>
        <p>⟡ Multi-AI Consortium • {date}</p>
    </footer>
</body>
</html>
"""


# ═══════════════════════════════════════════════════════════════
# CITATION SYSTEM
# ═══════════════════════════════════════════════════════════════

class CitationManager:
    """Manages source citations for briefings."""
    
    def __init__(self):
        self.sources: List[Dict] = []
        self.url_to_num: Dict[str, int] = {}
    
    def add_source(self, url: str, title: str) -> int:
        """Add a source and return its citation number."""
        if url in self.url_to_num:
            return self.url_to_num[url]
        
        num = len(self.sources) + 1
        self.sources.append({
            "num": num,
            "url": url,
            "title": title,
            "domain": self._extract_domain(url)
        })
        self.url_to_num[url] = num
        return num
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc.replace("www.", "")
        except:
            return url[:30]
    
    def get_citation_link(self, num: int) -> str:
        """Get markdown citation link."""
        if 0 < num <= len(self.sources):
            source = self.sources[num - 1]
            return f"[{num}]({source['url']})"
        return f"[{num}]"
    
    def render_sources_html(self) -> str:
        """Render sources list as HTML."""
        items = []
        for s in self.sources:
            items.append(f'''
            <div class="source-item">
                <span class="source-num">[{s["num"]}]</span>
                <a href="{s["url"]}" class="source-title">{s["title"]}</a>
                <span class="source-domain">{s["domain"]}</span>
            </div>
            ''')
        return "\n".join(items)
    
    def render_sources_markdown(self) -> str:
        """Render sources list as markdown."""
        lines = ["## Sources\n"]
        for s in self.sources:
            lines.append(f"[{s['num']}] [{s['title']}]({s['url']}) — {s['domain']}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# PREDICTION SYSTEM
# ═══════════════════════════════════════════════════════════════

class PredictionTracker:
    """Tracks predictions and their outcomes."""
    
    def __init__(self):
        self.predictions = self._load()
    
    def _load(self) -> Dict:
        """Load predictions from file."""
        if PREDICTIONS_FILE.exists():
            try:
                return json.loads(PREDICTIONS_FILE.read_text())
            except:
                pass
        return {"predictions": [], "accuracy": {"correct": 0, "wrong": 0, "pending": 0}}
    
    def _save(self):
        """Save predictions to file."""
        PREDICTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        PREDICTIONS_FILE.write_text(json.dumps(self.predictions, indent=2))
    
    def add_prediction(self, text: str, confidence: str, timeframe: str, tags: List[str] = None) -> str:
        """Add a new prediction."""
        pred_id = hashlib.md5(f"{text}{datetime.now().isoformat()}".encode()).hexdigest()[:8]
        
        self.predictions["predictions"].append({
            "id": pred_id,
            "text": text,
            "confidence": confidence,  # high, medium, low
            "timeframe": timeframe,    # "1 week", "1 month", etc.
            "tags": tags or [],
            "created_at": datetime.now().isoformat(),
            "outcome": "pending",      # pending, correct, wrong
            "resolved_at": None
        })
        self.predictions["accuracy"]["pending"] += 1
        self._save()
        return pred_id
    
    def resolve_prediction(self, pred_id: str, outcome: str):
        """Mark a prediction as resolved."""
        for p in self.predictions["predictions"]:
            if p["id"] == pred_id and p["outcome"] == "pending":
                p["outcome"] = outcome
                p["resolved_at"] = datetime.now().isoformat()
                self.predictions["accuracy"]["pending"] -= 1
                self.predictions["accuracy"][outcome] += 1
                self._save()
                return True
        return False
    
    def get_accuracy(self) -> Tuple[int, int, float]:
        """Get prediction accuracy (correct, total, percentage)."""
        acc = self.predictions["accuracy"]
        total = acc["correct"] + acc["wrong"]
        if total == 0:
            return 0, 0, 0.0
        return acc["correct"], total, (acc["correct"] / total) * 100
    
    def get_pending(self) -> List[Dict]:
        """Get pending predictions."""
        return [p for p in self.predictions["predictions"] if p["outcome"] == "pending"]


# ═══════════════════════════════════════════════════════════════
# BRIEFING GENERATION
# ═══════════════════════════════════════════════════════════════

def parse_raw_news(raw_news: str) -> List[Dict]:
    """Parse raw news markdown into structured format."""
    articles = []
    current = None
    
    for line in raw_news.split("\n"):
        if line.startswith("## "):
            if current:
                articles.append(current)
            # Extract number and title
            match = re.match(r"## (\d+)\. (.+)", line)
            if match:
                current = {"num": int(match.group(1)), "title": match.group(2), "url": "", "content": ""}
            else:
                current = {"num": len(articles) + 1, "title": line[3:], "url": "", "content": ""}
        elif current:
            if line.startswith("URL: "):
                current["url"] = line[5:].strip()
            else:
                current["content"] += line + " "
    
    if current:
        articles.append(current)
    
    return articles


def generate_predictions(brief_content: str, articles: List[Dict]) -> List[Dict]:
    """Generate predictions based on briefing content."""
    # This would ideally use an LLM, but for now we'll create placeholders
    # that the synthesis prompt will fill in
    predictions = []
    
    # These will be generated by the LLM in the enhanced synthesis
    # For now, return empty list to be filled later
    return predictions


def render_section_html(title: str, icon: str, items: List[str], section_class: str = "") -> str:
    """Render a section as HTML."""
    li_items = "\n".join([f"<li>{item}</li>" for item in items])
    return f"""
    <section class="{section_class}">
        <h2><span class="icon">{icon}</span> {title}</h2>
        <ul>
            {li_items}
        </ul>
    </section>
    """


def parse_brief_sections(brief: str) -> Dict[str, List[str]]:
    """Parse brief markdown into sections."""
    sections = {}
    current_section = None
    current_items = []
    
    for line in brief.split("\n"):
        if line.startswith("## ") or line.startswith("# ⟡"):
            if current_section:
                sections[current_section] = current_items
            current_section = line.lstrip("# ").strip()
            current_items = []
        elif line.strip().startswith("- ") or line.strip().startswith("* "):
            current_items.append(line.strip()[2:])
        elif line.strip() and current_section and not line.startswith("#"):
            # Non-bullet content
            if current_items:
                current_items[-1] += " " + line.strip()
            else:
                current_items.append(line.strip())
    
    if current_section:
        sections[current_section] = current_items
    
    return sections


def render_brief_html(brief: str, citations: CitationManager, predictions: List[Dict] = None) -> str:
    """Render full briefing as HTML."""
    sections = parse_brief_sections(brief)
    date = datetime.now().strftime("%B %d, %Y")
    
    content_parts = []
    
    # Section mapping
    section_config = {
        "1. What Changed": ("📊", "Changed"),
        "What Changed": ("📊", "Changed"),
        "2. What Matters": ("⚡", "What Matters"),
        "What Matters": ("⚡", "What Matters"),
        "3. What Can Be Ignored": ("🔇", "What Can Be Ignored"),
        "What Can Be Ignored": ("🔇", "What Can Be Ignored"),
        "4. Risks / Drift": ("⚠️", "Risks & Drift"),
        "Risks / Drift": ("⚠️", "Risks & Drift"),
        "5. Suggested Action": ("🎯", "Suggested Action"),
        "Suggested Action": ("🎯", "Suggested Action"),
        "6. Dissenting View": ("💭", "Dissenting View"),
        "Dissenting View": ("💭", "Dissenting View"),
    }
    
    for section_name, items in sections.items():
        if not items:
            continue
        
        for key, (icon, display_name) in section_config.items():
            if key in section_name:
                content_parts.append(render_section_html(display_name, icon, items))
                break
    
    # Add predictions section
    if predictions:
        pred_items = []
        for p in predictions:
            conf_class = p.get("confidence", "medium").lower()
            pred_items.append(
                f'{p["text"]} <span class="confidence {conf_class}">{p["confidence"]}</span>'
            )
        content_parts.append(render_section_html(
            "What's Next — Predictions", "🔮", pred_items, "prediction"
        ))
    
    return HTML_TEMPLATE.format(
        date=date,
        content="\n".join(content_parts),
        sources=citations.render_sources_html()
    )


# ═══════════════════════════════════════════════════════════════
# MAIN FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def process_briefing(brief_path: Path, raw_news_path: Path = None) -> Tuple[str, str]:
    """Process a briefing file and generate HTML + enhanced markdown."""
    brief = brief_path.read_text()
    
    # Initialize citation manager
    citations = CitationManager()
    
    # Parse raw news for sources
    if raw_news_path and raw_news_path.exists():
        raw_news = raw_news_path.read_text()
        articles = parse_raw_news(raw_news)
        
        for article in articles:
            if article.get("url"):
                citations.add_source(article["url"], article["title"])
    
    # Generate HTML
    html = render_brief_html(brief, citations)
    
    # Enhanced markdown with sources
    enhanced_md = brief + "\n\n---\n\n" + citations.render_sources_markdown()
    
    return html, enhanced_md


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("""
⟡ Briefing Generator v1.0

Commands:
    generate              — Generate from latest consortium output
    render FILE           — Render specific briefing to HTML
    predictions           — Show prediction accuracy
    resolve ID OUTCOME    — Resolve a prediction (correct/wrong)
""")
        return
    
    cmd = sys.argv[1]
    
    if cmd == "generate":
        # Find latest briefing and raw news
        today = datetime.now().strftime("%Y%m%d")
        brief_path = BRIEFINGS_DIR / f"{today}_Briefing.md"
        raw_news_path = BRIEFINGS_DIR / f"{today}_RawNews.md"
        
        if not brief_path.exists():
            print(f"❌ No briefing found for today: {brief_path}")
            return
        
        html, enhanced_md = process_briefing(brief_path, raw_news_path)
        
        # Save outputs
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        html_path = OUTPUT_DIR / f"{today}_Brief.html"
        html_path.write_text(html)
        print(f"✓ HTML saved: {html_path}")
        
        # Update markdown with citations
        enhanced_path = BRIEFINGS_DIR / f"{today}_Briefing_Enhanced.md"
        enhanced_path.write_text(enhanced_md)
        print(f"✓ Enhanced MD saved: {enhanced_path}")
    
    elif cmd == "render" and len(sys.argv) > 2:
        brief_path = Path(sys.argv[2])
        if not brief_path.exists():
            print(f"❌ File not found: {brief_path}")
            return
        
        # Try to find corresponding raw news
        raw_news_path = brief_path.parent / brief_path.name.replace("_Briefing", "_RawNews")
        if not raw_news_path.exists():
            raw_news_path = None
        
        html, enhanced_md = process_briefing(brief_path, raw_news_path)
        
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        html_path = OUTPUT_DIR / (brief_path.stem.replace("_Briefing", "_Brief") + ".html")
        html_path.write_text(html)
        print(f"✓ HTML saved: {html_path}")
    
    elif cmd == "predictions":
        tracker = PredictionTracker()
        correct, total, pct = tracker.get_accuracy()
        pending = tracker.get_pending()
        
        print(f"⟡ Prediction Accuracy: {correct}/{total} ({pct:.1f}%)")
        print(f"   Pending: {len(pending)}")
        
        if pending:
            print("\nPending predictions:")
            for p in pending[:10]:
                print(f"  [{p['id']}] {p['text'][:60]}... ({p['confidence']})")
    
    elif cmd == "resolve" and len(sys.argv) > 3:
        pred_id = sys.argv[2]
        outcome = sys.argv[3]
        if outcome not in ["correct", "wrong"]:
            print("❌ Outcome must be 'correct' or 'wrong'")
            return
        
        tracker = PredictionTracker()
        if tracker.resolve_prediction(pred_id, outcome):
            print(f"✓ Prediction {pred_id} marked as {outcome}")
        else:
            print(f"❌ Prediction {pred_id} not found or already resolved")
    
    else:
        print("Unknown command. Run without arguments for help.")


if __name__ == "__main__":
    main()
