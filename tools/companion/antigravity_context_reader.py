#!/usr/bin/env python3
"""
⟡ ANTIGRAVITY CONTEXT READER — Real-Time Awareness for Gemini v1.0

Reads companion context and outputs a compact block for Antigravity startup.
Called by startup_sync.sh or directly by Antigravity's profile.

Output includes:
- Paul's current state (time, energy, mode)
- What other agents are doing NOW
- Recent handoff chain
- Ambient notes

Usage:
    python3 antigravity_context_reader.py          # Full context
    python3 antigravity_context_reader.py compact  # One-liner

Author: Antigravity (Execution Twin)
For: Paul
"""

import os
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

HOME = Path.home()
COMPANION_DIR = HOME / ".mirrordna" / "companion"
WARM_CONTEXT = COMPANION_DIR / "warm_context.json"
CROSS_AGENT = COMPANION_DIR / "cross_agent_memory.json"
HEARTBEAT = COMPANION_DIR / "agent_heartbeat.json"


def load_json(path: Path) -> dict:
    """Load JSON file safely."""
    if path.exists():
        try:
            return json.loads(path.read_text())
        except:
            pass
    return {}


def is_fresh(path: Path, max_age_minutes: int = 10) -> bool:
    """Check if file was modified recently."""
    if not path.exists():
        return False
    age = datetime.now().timestamp() - path.stat().st_mtime
    return age < (max_age_minutes * 60)


def get_paul_state() -> dict:
    """Get Paul's current state from warm context."""
    if not is_fresh(WARM_CONTEXT, 10):
        return {}
    
    data = load_json(WARM_CONTEXT)
    return data.get("paul_state", {})


def get_ambient() -> str:
    """Get ambient notes."""
    data = load_json(WARM_CONTEXT)
    return data.get("ambient_notes", "")


def get_active_agents() -> list:
    """Get currently active agents from heartbeat."""
    if not is_fresh(HEARTBEAT, 30):
        return []
    
    data = load_json(HEARTBEAT)
    active = []
    now = datetime.now()
    
    for agent, info in data.get("agents", {}).items():
        if info.get("status") == "active":
            # Check staleness
            last_hb = info.get("last_heartbeat")
            if last_hb:
                last_dt = datetime.fromisoformat(last_hb)
                if (now - last_dt).total_seconds() < 900:  # 15 min
                    active.append({
                        "name": agent,
                        "task": info.get("task", ""),
                        "started": info.get("started_at", "")
                    })
    
    return active


def get_last_handoff() -> dict:
    """Get last handoff from cross-agent memory."""
    if not is_fresh(CROSS_AGENT, 60):
        return {}
    
    data = load_json(CROSS_AGENT)
    chain = data.get("handoff_chain", [])
    if chain:
        return chain[-1]
    return {}


def generate_context(compact: bool = False) -> str:
    """Generate full context for Antigravity."""
    paul = get_paul_state()
    ambient = get_ambient()
    active = get_active_agents()
    handoff = get_last_handoff()
    
    if compact:
        # One-liner for quick injection
        parts = []
        if paul:
            parts.append(f"{paul.get('current_time', '?')} | {paul.get('energy', '?')} | {paul.get('mode', '?')}")
        if active:
            others = [a["name"] for a in active if a["name"] != "antigravity"]
            if others:
                parts.append(f"Active: {', '.join(others)}")
        return " | ".join(parts) if parts else "No context available"
    
    # Full context block
    lines = ["⟡ REAL-TIME CONTEXT", ""]
    
    # Paul's state
    if paul:
        lines.append(f"**Paul's State:**")
        lines.append(f"  Time: {paul.get('current_time', '?')}")
        lines.append(f"  Energy: {paul.get('energy', '?')}")
        lines.append(f"  Mode: {paul.get('mode', '?')}")
        if paul.get("primary_focus"):
            lines.append(f"  Focus: {paul.get('primary_focus')}")
        if paul.get("session_duration_minutes"):
            lines.append(f"  Session: {int(paul.get('session_duration_minutes'))} min")
        lines.append("")
    
    # Ambient
    if ambient:
        lines.append(f"**Ambient:** {ambient}")
        lines.append("")
    
    # Active agents
    if active:
        others = [a for a in active if a["name"] != "antigravity"]
        if others:
            lines.append("**Other Active Agents:**")
            for a in others:
                lines.append(f"  🟢 {a['name']}: {a['task']}")
            lines.append("")
    
    # Pending handoff
    if handoff and handoff.get("status") == "pending":
        lines.append("**Pending Handoff:**")
        lines.append(f"  {handoff.get('from', '?')} → {handoff.get('to', '?')}")
        lines.append(f"  {handoff.get('summary', '')[:100]}")
        lines.append("")
    
    return "\n".join(lines) if len(lines) > 2 else "No context available"


def main():
    compact = len(sys.argv) > 1 and sys.argv[1] == "compact"
    print(generate_context(compact))


if __name__ == "__main__":
    main()
