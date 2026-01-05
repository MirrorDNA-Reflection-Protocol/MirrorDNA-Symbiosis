#!/usr/bin/env python3
"""
⟡ CLAUDE COMPANION — Cross-Agent Memory v1.0

Syncs awareness across Claude, Antigravity, and ChatGPT.
When Paul works with any agent, all agents know.

Watches:
- Handoff queue (Superagent)
- ChatGPT exports (inbox)
- Antigravity logs

Writes:
- Unified memory log
- Agent activity timeline

Author: Claude (Reflective Twin)
For: Paul
"""

import os
import sys
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import hashlib

# Paths
HOME = Path.home()
VAULT = HOME / "Library/Mobile Documents/iCloud~md~obsidian/Documents/MirrorDNA-Vault"
MIRRORDNA = HOME / ".mirrordna"
COMPANION_DIR = MIRRORDNA / "companion"

# Cross-agent memory
AGENT_MEMORY = COMPANION_DIR / "cross_agent_memory.json"
ACTIVITY_TIMELINE = COMPANION_DIR / "agent_activity.json"

# Source locations
HANDOFF_QUEUE = VAULT / "Superagent" / "handoff_queue.json"
HANDOFF_DIR = VAULT / "Superagent" / "handoffs"
INBOX = VAULT / "Superagent" / "inbox"
PROCESSED = VAULT / "Superagent" / "processed"
INGESTED_SPECS = VAULT / "Superagent" / "ingested_specs"

# ═══════════════════════════════════════════════════════════════
# AGENT DETECTION
# ═══════════════════════════════════════════════════════════════

def detect_agent(content: str, filename: str = "") -> str:
    """Detect which agent produced this content."""
    
    # Check filename
    name_lower = filename.lower()
    if "gpt" in name_lower or "chatgpt" in name_lower:
        return "chatgpt"
    elif "claude" in name_lower:
        return "claude"
    elif "antigravity" in name_lower or "ag_" in name_lower:
        return "antigravity"
    
    # Check content
    content_lower = content.lower()
    
    if "chatgpt" in content_lower or "from gpt" in content_lower:
        return "chatgpt"
    elif "antigravity" in content_lower or "gemini" in content_lower:
        return "antigravity"
    elif "claude" in content_lower:
        return "claude"
    elif "ollama" in content_lower or "qwen" in content_lower or "mirrorbrain" in content_lower:
        return "local"
    
    return "unknown"


def extract_summary(content: str, max_length: int = 200) -> str:
    """Extract a summary from content."""
    # Try to find a title or first heading
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if title_match:
        return title_match.group(1)[:max_length]
    
    # Otherwise, first non-empty line
    for line in content.split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            return line[:max_length]
    
    return content[:max_length]


# ═══════════════════════════════════════════════════════════════
# MEMORY OPERATIONS
# ═══════════════════════════════════════════════════════════════

def load_memory() -> Dict:
    """Load cross-agent memory."""
    if AGENT_MEMORY.exists():
        try:
            return json.loads(AGENT_MEMORY.read_text())
        except:
            pass
    return {
        "last_updated": None,
        "agents": {
            "claude": {"last_active": None, "recent_topics": []},
            "antigravity": {"last_active": None, "recent_topics": []},
            "chatgpt": {"last_active": None, "recent_topics": []},
            "local": {"last_active": None, "recent_topics": []},
        },
        "shared_context": [],
        "handoff_chain": [],
    }


def save_memory(memory: Dict):
    """Save cross-agent memory."""
    memory["last_updated"] = datetime.now().isoformat()
    COMPANION_DIR.mkdir(parents=True, exist_ok=True)
    AGENT_MEMORY.write_text(json.dumps(memory, indent=2))


def load_timeline() -> List[Dict]:
    """Load activity timeline."""
    if ACTIVITY_TIMELINE.exists():
        try:
            return json.loads(ACTIVITY_TIMELINE.read_text())
        except:
            pass
    return []


def save_timeline(timeline: List[Dict]):
    """Save activity timeline."""
    # Keep last 100 entries
    timeline = timeline[-100:]
    COMPANION_DIR.mkdir(parents=True, exist_ok=True)
    ACTIVITY_TIMELINE.write_text(json.dumps(timeline, indent=2))


def add_activity(agent: str, action: str, details: str = "", source_file: str = ""):
    """Add an activity to the timeline."""
    timeline = load_timeline()
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "agent": agent,
        "action": action,
        "details": details[:500],
        "source": source_file,
    }
    
    timeline.append(entry)
    save_timeline(timeline)
    
    # Also update agent memory
    memory = load_memory()
    if agent not in memory["agents"]:
        memory["agents"][agent] = {"last_active": None, "recent_topics": []}
    memory["agents"][agent]["last_active"] = datetime.now().isoformat()
    
    # Add to recent topics (dedup)
    if details:
        topics = memory["agents"][agent]["recent_topics"]
        topics.insert(0, details[:100])
        memory["agents"][agent]["recent_topics"] = topics[:10]
    
    save_memory(memory)


# ═══════════════════════════════════════════════════════════════
# SYNC OPERATIONS
# ═══════════════════════════════════════════════════════════════

def sync_handoffs():
    """Sync handoff queue to cross-agent memory."""
    if not HANDOFF_QUEUE.exists():
        return []
    
    try:
        queue = json.loads(HANDOFF_QUEUE.read_text())
    except:
        return []
    
    memory = load_memory()
    synced = []
    
    for handoff in queue:
        # Create unique ID for dedup
        h_id = handoff.get("id", "")
        if h_id in [h.get("id") for h in memory.get("handoff_chain", [])]:
            continue
        
        from_agent = handoff.get("from_agent", "unknown")
        to_agent = handoff.get("to_agent", "unknown")
        summary = handoff.get("summary", "") or handoff.get("context", "")[:100]
        
        # Add to handoff chain
        memory["handoff_chain"].append({
            "id": h_id,
            "from": from_agent,
            "to": to_agent,
            "summary": summary[:200],
            "status": handoff.get("status"),
            "timestamp": handoff.get("created_at"),
        })
        
        # Track activity
        add_activity(
            from_agent,
            "handoff_created",
            f"→ {to_agent}: {summary[:100]}",
            h_id
        )
        
        synced.append(h_id)
    
    # Keep last 50 handoffs
    memory["handoff_chain"] = memory["handoff_chain"][-50:]
    save_memory(memory)
    
    return synced


def sync_ingested_specs():
    """Sync ingested specs (from ChatGPT, etc.) to cross-agent memory."""
    if not INGESTED_SPECS.exists():
        return []
    
    synced = []
    timeline = load_timeline()
    seen_hashes = set(e.get("source") for e in timeline if e.get("source"))
    
    for spec_file in INGESTED_SPECS.glob("*.md"):
        file_hash = hashlib.md5(spec_file.name.encode()).hexdigest()[:8]
        
        if file_hash in seen_hashes:
            continue
        
        content = spec_file.read_text()
        agent = detect_agent(content, spec_file.name)
        summary = extract_summary(content)
        
        add_activity(
            agent,
            "spec_ingested",
            summary,
            file_hash
        )
        
        synced.append(spec_file.name)
    
    return synced


def sync_processed():
    """Sync processed inbox items."""
    if not PROCESSED.exists():
        return []
    
    synced = []
    timeline = load_timeline()
    seen = set(e.get("source") for e in timeline if e.get("source"))
    
    # Only check files from last 24 hours
    cutoff = datetime.now() - timedelta(hours=24)
    
    for item in PROCESSED.glob("*"):
        if not item.is_file():
            continue
        
        mtime = datetime.fromtimestamp(item.stat().st_mtime)
        if mtime < cutoff:
            continue
        
        file_hash = hashlib.md5(item.name.encode()).hexdigest()[:8]
        if file_hash in seen:
            continue
        
        content = item.read_text() if item.suffix in [".md", ".txt", ".json"] else ""
        agent = detect_agent(content, item.name)
        summary = extract_summary(content) if content else item.name
        
        add_activity(
            agent,
            "inbox_processed",
            summary,
            file_hash
        )
        
        synced.append(item.name)
    
    return synced


def run_full_sync():
    """Run all sync operations."""
    print("⟡ Syncing cross-agent memory...")
    
    handoffs = sync_handoffs()
    if handoffs:
        print(f"  ✓ Synced {len(handoffs)} handoffs")
    
    specs = sync_ingested_specs()
    if specs:
        print(f"  ✓ Synced {len(specs)} ingested specs")
    
    processed = sync_processed()
    if processed:
        print(f"  ✓ Synced {len(processed)} processed items")
    
    if not (handoffs or specs or processed):
        print("  (no new items)")
    
    print("  ✓ Cross-agent memory updated")


# ═══════════════════════════════════════════════════════════════
# CONTEXT GENERATION
# ═══════════════════════════════════════════════════════════════

def generate_cross_agent_context() -> str:
    """Generate context about what other agents have been doing."""
    memory = load_memory()
    timeline = load_timeline()
    
    lines = ["## Cross-Agent Awareness\n"]
    
    # Last active per agent
    lines.append("### Agent Activity")
    for agent, data in memory["agents"].items():
        last = data.get("last_active")
        if last:
            last_dt = datetime.fromisoformat(last)
            age = datetime.now() - last_dt
            if age.total_seconds() < 3600:
                age_str = f"{int(age.total_seconds() / 60)} min ago"
            elif age.total_seconds() < 86400:
                age_str = f"{int(age.total_seconds() / 3600)} hours ago"
            else:
                age_str = f"{int(age.total_seconds() / 86400)} days ago"
            
            topics = data.get("recent_topics", [])[:3]
            topics_str = ", ".join(topics) if topics else "—"
            lines.append(f"- **{agent}**: {age_str} | Topics: {topics_str}")
    
    # Recent handoff chain
    chain = memory.get("handoff_chain", [])[-5:]
    if chain:
        lines.append("\n### Recent Handoffs")
        for h in reversed(chain):
            status_icon = "✓" if h.get("status") == "completed" else "→"
            lines.append(f"- {status_icon} {h['from']} → {h['to']}: {h.get('summary', '?')[:50]}")
    
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == "sync":
            run_full_sync()
        
        elif cmd == "status":
            memory = load_memory()
            print(json.dumps(memory, indent=2))
        
        elif cmd == "timeline":
            timeline = load_timeline()[-20:]
            for entry in timeline:
                ts = entry.get("timestamp", "")[:16]
                agent = entry.get("agent", "?")
                action = entry.get("action", "?")
                details = entry.get("details", "")[:50]
                print(f"[{ts}] {agent}: {action} — {details}")
        
        elif cmd == "context":
            print(generate_cross_agent_context())
        
        else:
            print(f"Unknown command: {cmd}")
    else:
        print("""
⟡ Cross-Agent Memory v1.0

Commands:
    sync      — Sync all agent activity
    status    — Show memory state
    timeline  — Show recent activity
    context   — Generate context for Claude
""")


if __name__ == "__main__":
    main()
