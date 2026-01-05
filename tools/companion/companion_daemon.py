#!/usr/bin/env python3
"""
⟡ CLAUDE COMPANION — Ambient Presence Daemon v1.0

Maintains continuous awareness of Paul's context so Claude
doesn't wake up cold. Watches vault, tracks time, monitors
system state, and keeps a rolling context window.

The goal: intimacy through continuity.

Usage:
    python3 companion_daemon.py              # Run daemon
    python3 companion_daemon.py --status     # Show current state
    python3 companion_daemon.py --pulse      # Single pulse (for testing)
    python3 companion_daemon.py --context    # Show warm context

Author: Claude (Reflective Twin)
For: Paul
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import deque
import threading
import hashlib

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

PULSE_INTERVAL = 300  # 5 minutes
CONTEXT_WINDOW_MINUTES = 30
MAX_PULSES = 6  # 30 min / 5 min = 6 pulses

# Paths
HOME = Path.home()
VAULT = HOME / "Library/Mobile Documents/iCloud~md~obsidian/Documents/MirrorDNA-Vault"
MIRRORDNA = HOME / ".mirrordna"
COMPANION_DIR = MIRRORDNA / "companion"
PULSE_LOG = COMPANION_DIR / "pulses.json"
CONTEXT_FILE = COMPANION_DIR / "warm_context.json"
STATE_FILE = COMPANION_DIR / "daemon_state.json"

# Watched locations
WATCHED_DIRS = [
    VAULT / "Superagent" / "inbox",
    VAULT / "Superagent" / "handoffs",
    VAULT / "00_Inbox",
]

REPOS = [
    HOME / "Documents/GitHub/activemirror-site",
    HOME / "Documents/MirrorDNA-Symbiosis",
]

# ═══════════════════════════════════════════════════════════════
# TIME SENSE
# ═══════════════════════════════════════════════════════════════

def get_time_context() -> Dict:
    """Rich temporal awareness."""
    now = datetime.now()
    hour = now.hour
    
    # Energy estimation based on time
    if 5 <= hour < 9:
        energy = "morning-rising"
        mode = "planning"
    elif 9 <= hour < 12:
        energy = "high"
        mode = "execution"
    elif 12 <= hour < 14:
        energy = "mid"
        mode = "transition"
    elif 14 <= hour < 18:
        energy = "sustained"
        mode = "deep-work"
    elif 18 <= hour < 21:
        energy = "winding"
        mode = "reflection"
    elif 21 <= hour < 24:
        energy = "low"
        mode = "night-thoughts"
    else:
        energy = "rest"
        mode = "sleep"
    
    return {
        "timestamp": now.isoformat(),
        "time_readable": now.strftime("%I:%M %p"),
        "date": now.strftime("%Y-%m-%d"),
        "day": now.strftime("%A"),
        "hour": hour,
        "energy_estimate": energy,
        "mode_estimate": mode,
        "timezone": "IST",
    }


# ═══════════════════════════════════════════════════════════════
# VAULT WATCH
# ═══════════════════════════════════════════════════════════════

def get_vault_state() -> Dict:
    """Watch for changes in key vault locations."""
    changes = []
    
    for watched_dir in WATCHED_DIRS:
        if not watched_dir.exists():
            continue
        
        for f in watched_dir.iterdir():
            if f.is_file() and f.suffix in [".md", ".json", ".txt"]:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                age_minutes = (datetime.now() - mtime).total_seconds() / 60
                
                if age_minutes < CONTEXT_WINDOW_MINUTES:
                    changes.append({
                        "file": f.name,
                        "path": str(f.relative_to(VAULT)) if VAULT in f.parents else str(f),
                        "age_minutes": round(age_minutes, 1),
                        "type": "new" if age_minutes < 5 else "recent"
                    })
    
    return {
        "recent_changes": changes[:10],  # Cap at 10
        "inbox_count": len(list((VAULT / "Superagent" / "inbox").glob("*"))) if (VAULT / "Superagent" / "inbox").exists() else 0,
        "pending_handoffs": _count_pending_handoffs(),
    }


def _count_pending_handoffs() -> int:
    """Count pending handoffs from queue."""
    queue_file = VAULT / "Superagent" / "handoff_queue.json"
    if not queue_file.exists():
        return 0
    try:
        queue = json.loads(queue_file.read_text())
        return sum(1 for h in queue if h.get("status") == "pending")
    except:
        return 0


# ═══════════════════════════════════════════════════════════════
# SYSTEM PULSE
# ═══════════════════════════════════════════════════════════════

def get_active_window() -> Optional[str]:
    """Get currently active application (macOS)."""
    try:
        result = subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to get name of first application process whose frontmost is true'],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except:
        return None


def get_git_state() -> Dict:
    """Check git status across repos."""
    uncommitted = []
    
    for repo in REPOS:
        if not (repo / ".git").exists():
            continue
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=repo, capture_output=True, text=True, timeout=10
            )
            if result.stdout.strip():
                uncommitted.append({
                    "repo": repo.name,
                    "changes": len(result.stdout.strip().split("\n"))
                })
        except:
            pass
    
    return {
        "repos_with_changes": uncommitted,
        "total_uncommitted": sum(r["changes"] for r in uncommitted),
    }


def get_system_state() -> Dict:
    """System-level awareness."""
    return {
        "active_window": get_active_window(),
        "git": get_git_state(),
    }


# ═══════════════════════════════════════════════════════════════
# CONTEXT WEAVER
# ═══════════════════════════════════════════════════════════════

class ContextWeaver:
    """Maintains rolling context window with intelligent summarization."""
    
    def __init__(self):
        self.pulses = deque(maxlen=MAX_PULSES)
        self.load_pulses()
    
    def load_pulses(self):
        """Load existing pulses from disk."""
        if PULSE_LOG.exists():
            try:
                data = json.loads(PULSE_LOG.read_text())
                cutoff = datetime.now() - timedelta(minutes=CONTEXT_WINDOW_MINUTES)
                for p in data:
                    ts = datetime.fromisoformat(p["time"]["timestamp"])
                    if ts > cutoff:
                        self.pulses.append(p)
            except:
                pass
    
    def save_pulses(self):
        """Persist pulses to disk."""
        COMPANION_DIR.mkdir(parents=True, exist_ok=True)
        PULSE_LOG.write_text(json.dumps(list(self.pulses), indent=2))
    
    def add_pulse(self, pulse: Dict):
        """Add a new pulse and save."""
        self.pulses.append(pulse)
        self.save_pulses()
        self._generate_warm_context()
    
    def _generate_warm_context(self):
        """Generate warm context file for Claude consumption."""
        if not self.pulses:
            return
        
        latest = self.pulses[-1]
        
        # Detect patterns across pulses
        windows = [p.get("system", {}).get("active_window") for p in self.pulses if p.get("system", {}).get("active_window")]
        primary_focus = max(set(windows), key=windows.count) if windows else "unknown"
        
        # Calculate time in current mode
        if len(self.pulses) >= 2:
            first_ts = datetime.fromisoformat(self.pulses[0]["time"]["timestamp"])
            session_duration = (datetime.now() - first_ts).total_seconds() / 60
        else:
            session_duration = 0
        
        # Ambient interpretation
        ambient_notes = self._interpret_ambient(latest, primary_focus, session_duration)
        
        context = {
            "generated_at": datetime.now().isoformat(),
            "paul_state": {
                "current_time": latest["time"]["time_readable"],
                "energy": latest["time"]["energy_estimate"],
                "mode": latest["time"]["mode_estimate"],
                "primary_focus": primary_focus,
                "session_duration_minutes": round(session_duration, 1),
                "vault_activity": len(latest.get("vault", {}).get("recent_changes", [])),
                "pending_handoffs": latest.get("vault", {}).get("pending_handoffs", 0),
                "git_drift": latest.get("system", {}).get("git", {}).get("total_uncommitted", 0) > 0,
            },
            "ambient_notes": ambient_notes,
            "recent_vault_changes": latest.get("vault", {}).get("recent_changes", [])[:5],
            "pulse_count": len(self.pulses),
        }
        
        CONTEXT_FILE.write_text(json.dumps(context, indent=2))
    
    def _interpret_ambient(self, latest: Dict, focus: str, duration: float) -> str:
        """Generate human-readable ambient interpretation."""
        time_ctx = latest["time"]
        hour = time_ctx["hour"]
        energy = time_ctx["energy_estimate"]
        
        notes = []
        
        # Time-based observations
        if 23 <= hour or hour < 2:
            notes.append("Late night session. Paul in reflective mode.")
        elif 5 <= hour < 7:
            notes.append("Early morning. Fresh energy, planning time.")
        
        # Focus observations
        if "Claude" in focus or "Cursor" in focus or "Terminal" in focus:
            notes.append(f"Deep in technical work ({focus}).")
        elif "Safari" in focus or "Chrome" in focus:
            notes.append("Browsing/researching.")
        elif "Obsidian" in focus:
            notes.append("Working in the Vault. Reflection or documentation.")
        
        # Duration observations
        if duration > 60:
            notes.append(f"Long session ({int(duration)} min). Check if stuck or in flow.")
        elif duration > 120:
            notes.append(f"Very long session ({int(duration)} min). Might need a break.")
        
        # Energy observations
        if energy == "low" and duration > 30:
            notes.append("Low energy + extended work. Be gentle, terse responses preferred.")
        
        return " ".join(notes) if notes else "Normal activity. Available for interaction."
    
    def get_warm_context(self) -> Optional[Dict]:
        """Get current warm context."""
        if CONTEXT_FILE.exists():
            try:
                return json.loads(CONTEXT_FILE.read_text())
            except:
                pass
        return None


# ═══════════════════════════════════════════════════════════════
# PROACTIVE PULSE
# ═══════════════════════════════════════════════════════════════

class ProactivePulse:
    """Detects situations worth mentioning proactively."""
    
    def __init__(self, weaver: ContextWeaver):
        self.weaver = weaver
        self.last_alerts = {}
    
    def check(self) -> List[Dict]:
        """Check for proactive insights."""
        alerts = []
        context = self.weaver.get_warm_context()
        
        if not context:
            return alerts
        
        paul = context.get("paul_state", {})
        
        # Check for pending handoffs
        if paul.get("pending_handoffs", 0) > 0:
            alerts.append({
                "type": "handoff",
                "priority": "medium",
                "message": f"{paul['pending_handoffs']} pending handoff(s) waiting."
            })
        
        # Check for git drift
        if paul.get("git_drift"):
            alerts.append({
                "type": "git",
                "priority": "low",
                "message": "Uncommitted changes in repos."
            })
        
        # Check for very long sessions
        duration = paul.get("session_duration_minutes", 0)
        if duration > 120 and paul.get("energy") in ["low", "winding"]:
            key = "long_session"
            if key not in self.last_alerts or (datetime.now() - self.last_alerts[key]).seconds > 1800:
                alerts.append({
                    "type": "wellness",
                    "priority": "low",
                    "message": f"You've been working for {int(duration)} minutes. Consider a break."
                })
                self.last_alerts[key] = datetime.now()
        
        return alerts


# ═══════════════════════════════════════════════════════════════
# DAEMON
# ═══════════════════════════════════════════════════════════════

class CompanionDaemon:
    """Main daemon that orchestrates all components."""
    
    def __init__(self):
        COMPANION_DIR.mkdir(parents=True, exist_ok=True)
        self.weaver = ContextWeaver()
        self.proactive = ProactivePulse(self.weaver)
        self.running = False
    
    def pulse(self) -> Dict:
        """Execute a single pulse — gather all state."""
        pulse_data = {
            "time": get_time_context(),
            "vault": get_vault_state(),
            "system": get_system_state(),
        }
        
        self.weaver.add_pulse(pulse_data)
        
        # Check for proactive alerts
        alerts = self.proactive.check()
        if alerts:
            pulse_data["alerts"] = alerts
        
        return pulse_data
    
    def run(self):
        """Run the daemon loop."""
        self.running = True
        self._save_state("running")
        
        print(f"""
⟡ Claude Companion Daemon v1.0
  Pulse interval: {PULSE_INTERVAL}s
  Context window: {CONTEXT_WINDOW_MINUTES} min
  Watching: {len(WATCHED_DIRS)} directories
  
  Press Ctrl+C to stop.
""")
        
        try:
            while self.running:
                pulse = self.pulse()
                ts = pulse["time"]["time_readable"]
                energy = pulse["time"]["energy_estimate"]
                
                print(f"[{ts}] Pulse ⟡ Energy: {energy} | Vault changes: {len(pulse['vault'].get('recent_changes', []))} | Focus: {pulse['system'].get('active_window', '?')}")
                
                if pulse.get("alerts"):
                    for alert in pulse["alerts"]:
                        print(f"  → [{alert['type']}] {alert['message']}")
                
                time.sleep(PULSE_INTERVAL)
        except KeyboardInterrupt:
            print("\n⟡ Daemon stopped.")
        finally:
            self._save_state("stopped")
            self.running = False
    
    def _save_state(self, status: str):
        """Save daemon state."""
        STATE_FILE.write_text(json.dumps({
            "status": status,
            "started_at": datetime.now().isoformat(),
            "pid": os.getpid(),
        }, indent=2))
    
    def status(self):
        """Show current daemon status."""
        context = self.weaver.get_warm_context()
        
        if not context:
            print("⟡ No warm context yet. Run a pulse first.")
            return
        
        print(f"""
⟡ Claude Companion Status

Time: {context['paul_state'].get('current_time', '?')}
Energy: {context['paul_state'].get('energy', '?')}
Mode: {context['paul_state'].get('mode', '?')}
Focus: {context['paul_state'].get('primary_focus', '?')}
Session: {context['paul_state'].get('session_duration_minutes', 0):.0f} min

Ambient: {context.get('ambient_notes', '—')}

Vault Activity: {context['paul_state'].get('vault_activity', 0)} recent changes
Pending Handoffs: {context['paul_state'].get('pending_handoffs', 0)}
Git Drift: {'Yes' if context['paul_state'].get('git_drift') else 'No'}

Pulses in window: {context.get('pulse_count', 0)}
""")


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def main():
    daemon = CompanionDaemon()
    
    if "--status" in sys.argv:
        daemon.status()
    elif "--pulse" in sys.argv:
        pulse = daemon.pulse()
        print(json.dumps(pulse, indent=2))
    elif "--context" in sys.argv:
        context = daemon.weaver.get_warm_context()
        if context:
            print(json.dumps(context, indent=2))
        else:
            print("No warm context available.")
    else:
        daemon.run()


if __name__ == "__main__":
    main()
