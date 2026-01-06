#!/usr/bin/env python3
"""
⟡ RSS Feed Generator — Mirror Intelligence

Generates RSS 2.0 feed from briefings for organic discovery via Feedly, Inoreader, etc.

Usage:
    python3 rss_generator.py              # Generate feed from all briefings
    python3 rss_generator.py --latest 7   # Last 7 days only

Output:
    Vault/Superagent/published/feed.xml
"""

import os
import json
from datetime import datetime, timezone
from pathlib import Path
import re
import html

# Paths
VAULT = Path.home() / "Library/Mobile Documents/iCloud~md~obsidian/Documents/MirrorDNA-Vault"
BRIEFINGS_DIR = VAULT / "Superagent" / "briefings"
OUTPUT_DIR = VAULT / "Superagent" / "published"
FEED_FILE = OUTPUT_DIR / "feed.xml"

# Config
SITE_URL = "https://brief.activemirror.ai"
FEED_TITLE = "Mirror Intelligence — Daily Briefings"
FEED_DESCRIPTION = "Multi-AI consortium synthesizing daily intelligence from GPT, DeepSeek, Groq, and Mistral"
FEED_LANGUAGE = "en-us"


def parse_briefing(filepath: Path) -> dict:
    """Parse a briefing markdown file into structured data."""
    content = filepath.read_text()
    
    # Extract date from filename (YYYYMMDD_Briefing.md)
    date_match = re.match(r"(\d{8})_Briefing", filepath.stem)
    if not date_match:
        return None
    
    date_str = date_match.group(1)
    pub_date = datetime.strptime(date_str, "%Y%m%d").replace(tzinfo=timezone.utc)
    
    # Extract title (first # line)
    title_match = re.search(r"^# (.+)$", content, re.MULTILINE)
    title = title_match.group(1) if title_match else f"Daily Brief — {date_str}"
    
    # Extract first section as description
    sections = re.split(r"^## ", content, flags=re.MULTILINE)
    description = ""
    if len(sections) > 1:
        # Get first bullet points from "What Changed" section
        first_section = sections[1] if len(sections) > 1 else ""
        bullets = re.findall(r"^- (.+)$", first_section, re.MULTILINE)
        description = " • ".join(bullets[:3]) if bullets else first_section[:300]
    
    return {
        "title": html.escape(title),
        "description": html.escape(description.strip()),
        "pub_date": pub_date.strftime("%a, %d %b %Y %H:%M:%S %z"),
        "link": f"{SITE_URL}/?date={date_str}",
        "guid": f"mirror-intel-{date_str}",
        "content": html.escape(content[:2000])  # First 2000 chars as content
    }


def generate_feed(days: int = 30) -> str:
    """Generate RSS 2.0 XML feed."""
    
    # Get briefing files
    briefings = sorted(BRIEFINGS_DIR.glob("*_Briefing.md"), reverse=True)[:days]
    
    items = []
    for filepath in briefings:
        data = parse_briefing(filepath)
        if data:
            items.append(f"""
    <item>
      <title>{data['title']}</title>
      <link>{data['link']}</link>
      <description>{data['description']}</description>
      <pubDate>{data['pub_date']}</pubDate>
      <guid isPermaLink="false">{data['guid']}</guid>
    </item>""")
    
    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{FEED_TITLE}</title>
    <link>{SITE_URL}</link>
    <description>{FEED_DESCRIPTION}</description>
    <language>{FEED_LANGUAGE}</language>
    <lastBuildDate>{datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")}</lastBuildDate>
    <atom:link href="{SITE_URL}/feed.xml" rel="self" type="application/rss+xml"/>
    <image>
      <url>{SITE_URL}/logo.png</url>
      <title>{FEED_TITLE}</title>
      <link>{SITE_URL}</link>
    </image>
{''.join(items)}
  </channel>
</rss>"""
    
    return feed


def main():
    import sys
    
    days = 30
    if "--latest" in sys.argv:
        idx = sys.argv.index("--latest")
        if idx + 1 < len(sys.argv):
            days = int(sys.argv[idx + 1])
    
    print(f"⟡ Generating RSS feed (last {days} days)...")
    
    feed = generate_feed(days)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FEED_FILE.write_text(feed)
    
    print(f"✓ Feed saved: {FEED_FILE}")
    print(f"  Items: {feed.count('<item>')}")


if __name__ == "__main__":
    main()
