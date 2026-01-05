#!/usr/bin/env python3
"""
⟡ AGENT HEARTBEAT — Real-Time Agent Awareness v1.0

Tracks which agents are currently active.
Each agent writes on session start/end.
Other agents can see who's working NOW.

Usage:
    python3 agent_heartbeat.py start antigravity "Working on companion system"
    python3 agent_heartbeat.py pulse antigravity
    python3 agent_heartbeat.py stop antigravity
    python3 agent_heartbeat.py status

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
HEARTBEAT_FILE = COMPANION_DIR / "agent_heartbeat.json"

# Stale threshold (minutes)
STALE_THRESHOLD = 15


def load_heartbeats() -> dict:
    """Load current heartbeat state."""
    if HEARTBEAT_FILE.exists():
        try:
            return json.loads(HEARTBEAT_FILE.read_text())
        except:
            pass
    return {"agents": {}, "last_updated": None}


def save_heartbeats(data: dict):
    """Save heartbeat state."""
    data["last_updated"] = datetime.now().isoformat()
    COMPANION_DIR.mkdir(parents=True, exist_ok=True)
    HEARTBEAT_FILE.write_text(json.dumps(data, indent=2))


def start_session(agent: str, task: str = ""):
    """Mark an agent as active."""
    data = load_heartbeats()
    data["agents"][agent] = {
        "status": "active",
        "started_at": datetime.now().isoformat(),
        "task": task[:200] if task else "Working",
        "last_heartbeat": datetime.now().isoformat()
    }
    save_heartbeats(data)
    print(f"⟡ {agent} session started")


def pulse_session(agent: str, task: str = None):
    """Update heartbeat for an active session."""
    data = load_heartbeats()
    if agent in data["agents"]:
        data["agents"][agent]["last_heartbeat"] = datetime.now().isoformat()
        if task:
            data["agents"][agent]["task"] = task[:200]
        save_heartbeats(data)


def stop_session(agent: str, summary: str = ""):
    """Mark an agent as idle."""
    data = load_heartbeats()
    if agent in data["agents"]:
        data["agents"][agent]["status"] = "idle"
        data["agents"][agent]["ended_at"] = datetime.now().isoformat()
        if summary:
            data["agents"][agent]["last_task"] = summary[:200]
        del data["agents"][agent]["task"]
        save_heartbeats(data)
        print(f"⟡ {agent} session ended")


def get_status(compact: bool = False) -> str:
    """Get current agent status."""
    data = load_heartbeats()
    now = datetime.now()
    
    lines = []
    active_agents = []
    
    for agent, info in data.get("agents", {}).items():
        status = info.get("status", "unknown")
        
        if status == "active":
            # Check if stale
            last_hb = info.get("last_heartbeat")
            if last_hb:
                last_dt = datetime.fromisoformat(last_hb)
                age_min = (now - last_dt).total_seconds() / 60
                if age_min > STALE_THRESHOLD:
                    status = "stale"
                    info["status"] = "stale"
        
        if status == "active":
            task = info.get("task", "")
            started = info.get("started_at", "")[:16]
            active_agents.append(agent)
            if compact:
                lines.append(f"  🟢 {agent}: {task}")
            else:
                lines.append(f"🟢 {agent.upper()}: ACTIVE")
                lines.append(f"   Task: {task}")
                lines.append(f"   Started: {started}")
        elif status == "idle":
            last_task = info.get("last_task", "")
            ended = info.get("ended_at", "")[:16]
            if not compact:
                lines.append(f"⚪ {agent}: idle since {ended}")
                if last_task:
                    lines.append(f"   Last task: {last_task}")
        elif status == "stale":
            if not compact:
                lines.append(f"🟡 {agent}: stale (no heartbeat)")
    
    if compact:
        if active_agents:
            return "Active: " + ", ".join(active_agents) + "\n" + "\n".join(lines)
        else:
            return "No agents currently active"
    
    if not lines:
        lines.append("No agent activity recorded")
    
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("""
⟡ Agent Heartbeat v1.0

Commands:
    start <agent> [task]   — Mark agent as active
    pulse <agent> [task]   — Update heartbeat
    stop <agent> [summary] — Mark agent as idle
    status                 — Show all agents
    compact                — Compact status for startup
""")
        return
    
    cmd = sys.argv[1]
    agent = sys.argv[2] if len(sys.argv) > 2 else ""
    extra = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""
    
    if cmd == "start" and agent:
        start_session(agent, extra)
    elif cmd == "pulse" and agent:
        pulse_session(agent, extra if extra else None)
    elif cmd == "stop" and agent:
        stop_session(agent, extra)
    elif cmd == "status":
        print(get_status())
    elif cmd == "compact":
        print(get_status(compact=True))
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
