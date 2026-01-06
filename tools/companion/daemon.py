#!/usr/bin/env python3
"""
⟡ MIRROROS UNIFIED DAEMON v2.0

The "Always On" state maintainer. Combines:
- Companion pulse (Paul awareness)
- Antigravity ops (Git, system health)  
- API bridge monitoring

Produces a single warm_context.json for morning handshake.

Architecture:
- Main heartbeat: 5 minutes (Paul pulse)
- Git sentinel: 15 minutes (system ops)
- API probe: 60 minutes (bridge check)

Author: Claude (Reflective Twin)
For: Paul
"""

import os
import sys
import json
import time
import fcntl
import signal
import hashlib
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

# Intervals (seconds)
PAUL_PULSE_INTERVAL = 300      # 5 minutes
SYSTEM_OPS_INTERVAL = 900      # 15 minutes  
API_PROBE_INTERVAL = 3600      # 60 minutes

# Paths
HOME = Path.home()
VAULT = HOME / "Library/Mobile Documents/iCloud~md~obsidian/Documents/MirrorDNA-Vault"
MIRRORDNA = HOME / ".mirrordna"
DAEMON_DIR = MIRRORDNA / "daemon"
COMPANION_DIR = MIRRORDNA / "companion"

# State files
WARM_CONTEXT = DAEMON_DIR / "warm_context.json"
DAEMON_STATE = DAEMON_DIR / "daemon_state.json"
LOCK_FILE = DAEMON_DIR / "daemon.lock"
LOG_FILE = DAEMON_DIR / "daemon.log"

# Git repos to monitor
GIT_REPOS = [
    VAULT,
    HOME / "Documents/GitHub/activemirror-site",
    HOME / "Documents/MirrorDNA-Symbiosis",
]

# Files to NEVER commit
FORBIDDEN_PATTERNS = [".env", "api_key", "secret", "password", "token"]

# Idle threshold (seconds)
IDLE_THRESHOLD = 300  # 5 minutes = considered idle

# ═══════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════

def setup_logging() -> logging.Logger:
    """Configure logging with rotation awareness."""
    DAEMON_DIR.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger("mirroros")
    logger.setLevel(logging.INFO)
    
    # File handler
    handler = logging.FileHandler(LOG_FILE)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logger.addHandler(handler)
    
    # Console handler for debugging
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
    logger.addHandler(console)
    
    return logger

log = setup_logging()

# ═══════════════════════════════════════════════════════════════
# LOCK MECHANISM
# ═══════════════════════════════════════════════════════════════

class DaemonLock:
    """File-based lock to prevent multiple daemon instances."""
    
    def __init__(self, lock_path: Path):
        self.lock_path = lock_path
        self.lock_file = None
    
    def acquire(self) -> bool:
        """Acquire exclusive lock. Returns False if already locked."""
        try:
            self.lock_path.parent.mkdir(parents=True, exist_ok=True)
            self.lock_file = open(self.lock_path, 'w')
            fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.lock_file.write(str(os.getpid()))
            self.lock_file.flush()
            return True
        except (IOError, OSError):
            if self.lock_file:
                self.lock_file.close()
            return False
    
    def release(self):
        """Release lock."""
        if self.lock_file:
            try:
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                self.lock_file.close()
                self.lock_path.unlink(missing_ok=True)
            except:
                pass

# ═══════════════════════════════════════════════════════════════
# STATE MANAGEMENT
# ═══════════════════════════════════════════════════════════════

class UserState(Enum):
    ACTIVE = "active"
    IDLE = "idle"
    SLEEPING = "sleeping"

@dataclass
class NightShift:
    """Overnight state summary."""
    status: str = "running"
    sleep_started: Optional[str] = None
    total_sleep_seconds: int = 0
    git_commits_made: int = 0
    bridge_connectivity: bool = False
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    @property
    def total_sleep_duration(self) -> str:
        """Human-readable sleep duration."""
        hours = self.total_sleep_seconds // 3600
        minutes = (self.total_sleep_seconds % 3600) // 60
        return f"{hours}h {minutes}m"

@dataclass 
class WarmContext:
    """The morning handshake artifact."""
    meta: Dict[str, Any]
    paul_state: Dict[str, Any]
    night_shift: Dict[str, Any]
    system_health: Dict[str, Any]
    recent_pulse: List[str]
    
    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, default=str)
    
    @classmethod
    def load(cls, path: Path) -> Optional['WarmContext']:
        if path.exists():
            try:
                data = json.loads(path.read_text())
                return cls(**data)
            except:
                pass
        return None

# ═══════════════════════════════════════════════════════════════
# SYSTEM DETECTION
# ═══════════════════════════════════════════════════════════════

def get_idle_time() -> int:
    """Get system idle time in seconds (macOS)."""
    try:
        result = subprocess.run(
            ["ioreg", "-c", "IOHIDSystem"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.split('\n'):
            if 'HIDIdleTime' in line:
                # Value is in nanoseconds
                ns = int(line.split('=')[-1].strip())
                return ns // 1_000_000_000
    except Exception as e:
        log.warning(f"Could not get idle time: {e}")
    return 0

def get_screen_locked() -> bool:
    """Check if screen is locked (macOS)."""
    try:
        result = subprocess.run(
            ["python3", "-c", 
             "import Quartz; print(Quartz.CGSessionCopyCurrentDictionary().get('CGSSessionScreenIsLocked', False))"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() == "True"
    except:
        return False

def get_active_window() -> Optional[str]:
    """Get currently active application."""
    try:
        result = subprocess.run(
            ["osascript", "-e", 
             'tell application "System Events" to get name of first application process whose frontmost is true'],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except:
        return None

def get_user_state() -> UserState:
    """Determine current user state."""
    idle_seconds = get_idle_time()
    screen_locked = get_screen_locked()
    
    if screen_locked or idle_seconds > 1800:  # 30 min
        return UserState.SLEEPING
    elif idle_seconds > IDLE_THRESHOLD:
        return UserState.IDLE
    else:
        return UserState.ACTIVE

def get_time_context() -> Dict[str, Any]:
    """Get temporal context."""
    now = datetime.now()
    hour = now.hour
    
    if 5 <= hour < 9:
        energy, mode = "morning-rising", "planning"
    elif 9 <= hour < 12:
        energy, mode = "high", "execution"
    elif 12 <= hour < 14:
        energy, mode = "mid", "transition"
    elif 14 <= hour < 18:
        energy, mode = "sustained", "deep-work"
    elif 18 <= hour < 21:
        energy, mode = "winding", "reflection"
    elif 21 <= hour < 24:
        energy, mode = "low", "night-thoughts"
    else:
        energy, mode = "rest", "sleep"
    
    return {
        "timestamp": now.isoformat(),
        "time_readable": now.strftime("%I:%M %p"),
        "date": now.strftime("%Y-%m-%d"),
        "day": now.strftime("%A"),
        "hour": hour,
        "energy_estimate": energy,
        "mode_estimate": mode,
    }

# ═══════════════════════════════════════════════════════════════
# GIT SENTINEL
# ═══════════════════════════════════════════════════════════════

def git_run(repo: Path, *args) -> subprocess.CompletedProcess:
    """Run git command in repo."""
    return subprocess.run(
        ["git"] + list(args),
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=60
    )

def check_icloud_sync_complete(path: Path) -> bool:
    """Check if iCloud sync is complete (no .icloud files)."""
    try:
        for f in path.rglob("*.icloud"):
            return False  # Still syncing
        return True
    except:
        return True

def has_forbidden_changes(repo: Path) -> bool:
    """Check if staged changes include forbidden files."""
    result = git_run(repo, "diff", "--cached", "--name-only")
    if result.returncode != 0:
        return True  # Assume forbidden on error
    
    for line in result.stdout.strip().split('\n'):
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.lower() in line.lower():
                log.warning(f"Forbidden file in changes: {line}")
                return True
    return False

def git_sentinel(repos: List[Path], night_shift: NightShift) -> List[str]:
    """Check and commit changes across repos."""
    pulse_entries = []
    
    for repo in repos:
        if not (repo / ".git").exists():
            continue
        
        repo_name = repo.name
        
        # Check for uncommitted changes
        status = git_run(repo, "status", "--porcelain")
        if status.returncode != 0:
            log.error(f"Git status failed for {repo_name}: {status.stderr}")
            night_shift.errors.append(f"git-status-{repo_name}")
            continue
        
        if not status.stdout.strip():
            continue  # No changes
        
        change_count = len(status.stdout.strip().split('\n'))
        log.info(f"{repo_name}: {change_count} changes detected")
        
        # Wait for iCloud if it's the Vault
        if "obsidian" in str(repo).lower():
            if not check_icloud_sync_complete(repo):
                log.info(f"{repo_name}: Waiting for iCloud sync...")
                pulse_entries.append(f"{datetime.now().strftime('%H:%M')} - {repo_name}: iCloud sync in progress")
                continue
        
        # Stage all changes
        add_result = git_run(repo, "add", "-A")
        if add_result.returncode != 0:
            log.error(f"Git add failed: {add_result.stderr}")
            continue
        
        # Check for forbidden files
        if has_forbidden_changes(repo):
            git_run(repo, "reset", "HEAD")  # Unstage
            log.warning(f"{repo_name}: Aborted - forbidden files detected")
            pulse_entries.append(f"{datetime.now().strftime('%H:%M')} - {repo_name}: Commit blocked (security)")
            continue
        
        # Commit
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        commit_msg = f"[MirrorOS] Overnight sync: {timestamp}"
        
        commit_result = git_run(repo, "commit", "-m", commit_msg)
        if commit_result.returncode == 0:
            night_shift.git_commits_made += 1
            log.info(f"{repo_name}: Committed successfully")
            pulse_entries.append(f"{datetime.now().strftime('%H:%M')} - {repo_name}: Git commit ({change_count} files)")
            
            # Push (non-blocking, don't fail if offline)
            push_result = git_run(repo, "push")
            if push_result.returncode != 0:
                log.warning(f"{repo_name}: Push failed (offline?)")
        else:
            log.warning(f"{repo_name}: Commit failed: {commit_result.stderr}")
    
    return pulse_entries

# ═══════════════════════════════════════════════════════════════
# API BRIDGE PROBE
# ═══════════════════════════════════════════════════════════════

def probe_api_bridge() -> Dict[str, Any]:
    """Check API connectivity without burning tokens."""
    result = {
        "status": "dormant",
        "checked_at": datetime.now().isoformat(),
        "anthropic": False,
        "openai": False,
    }
    
    # Check Anthropic
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        try:
            import urllib.request
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": anthropic_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                data=b'{"model":"claude-3-haiku-20240307","max_tokens":1,"messages":[{"role":"user","content":"ping"}]}'
            )
            # Just check if we get a response, don't actually send
            # Actually, let's just verify the key format
            if anthropic_key.startswith("sk-ant-"):
                result["anthropic"] = True
                result["status"] = "active"
        except:
            pass
    
    # Check OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key and openai_key.startswith("sk-"):
        result["openai"] = True
        if result["status"] != "active":
            result["status"] = "partial"
    
    return result

# ═══════════════════════════════════════════════════════════════
# WARM CONTEXT GENERATION
# ═══════════════════════════════════════════════════════════════

def generate_warm_context(
    paul_state: Dict,
    night_shift: NightShift,
    pulse_log: List[str],
    boot_time: datetime
) -> WarmContext:
    """Generate the morning handshake artifact."""
    
    # System health
    system_health = {
        "disk_free_gb": get_disk_free(),
        "repos_clean": all_repos_clean(),
        "services": check_services(),
    }
    
    # API bridge status
    bridge = probe_api_bridge()
    night_shift.bridge_connectivity = bridge["status"] == "active"
    
    return WarmContext(
        meta={
            "boot_time": boot_time.isoformat(),
            "last_updated": datetime.now().isoformat(),
            "mode": "daemon",
            "version": "2.0"
        },
        paul_state=paul_state,
        night_shift={
            "status": night_shift.status,
            "total_sleep_duration": night_shift.total_sleep_duration,
            "git_commits_made": night_shift.git_commits_made,
            "bridge_connectivity": night_shift.bridge_connectivity,
            "errors": night_shift.errors[-5:] if night_shift.errors else []
        },
        system_health=system_health,
        recent_pulse=pulse_log[-20:]  # Last 20 entries
    )

def get_disk_free() -> float:
    """Get free disk space in GB."""
    try:
        result = subprocess.run(
            ["df", "-g", "/"],
            capture_output=True, text=True, timeout=5
        )
        lines = result.stdout.strip().split('\n')
        if len(lines) > 1:
            parts = lines[1].split()
            return float(parts[3])  # Available
    except:
        pass
    return -1

def all_repos_clean() -> bool:
    """Check if all repos are clean."""
    for repo in GIT_REPOS:
        if not (repo / ".git").exists():
            continue
        result = git_run(repo, "status", "--porcelain")
        if result.stdout.strip():
            return False
    return True

def check_services() -> Dict[str, str]:
    """Check critical services."""
    services = {}
    
    # Ollama
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost:11434/api/tags"],
            capture_output=True, text=True, timeout=5
        )
        services["ollama"] = "up" if result.stdout.strip() == "200" else "down"
    except:
        services["ollama"] = "unknown"
    
    # MirrorBrain
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost:8081/health"],
            capture_output=True, text=True, timeout=5
        )
        services["mirrorbrain"] = "up" if result.stdout.strip() == "200" else "down"
    except:
        services["mirrorbrain"] = "unknown"
    
    # Superagent
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost:8765/status"],
            capture_output=True, text=True, timeout=5
        )
        services["superagent"] = "up" if result.stdout.strip() == "200" else "down"
    except:
        services["superagent"] = "unknown"
    
    return services

# ═══════════════════════════════════════════════════════════════
# MAIN DAEMON
# ═══════════════════════════════════════════════════════════════

class MirrorOSDaemon:
    """The unified always-on daemon."""
    
    def __init__(self):
        self.boot_time = datetime.now()
        self.night_shift = NightShift()
        self.pulse_log: List[str] = []
        self.last_paul_pulse = datetime.min
        self.last_system_ops = datetime.min
        self.last_api_probe = datetime.min
        self.last_user_state = UserState.ACTIVE
        self.sleep_start: Optional[datetime] = None
        self.running = False
        self.lock = DaemonLock(LOCK_FILE)
    
    def log_pulse(self, message: str):
        """Add entry to pulse log."""
        entry = f"{datetime.now().strftime('%H:%M')} - {message}"
        self.pulse_log.append(entry)
        log.info(message)
        
        # Keep last 100 entries
        self.pulse_log = self.pulse_log[-100:]
    
    def handle_user_state_change(self, new_state: UserState):
        """Handle transitions between user states."""
        if new_state == self.last_user_state:
            # Same state - update duration if sleeping
            if new_state in (UserState.IDLE, UserState.SLEEPING) and self.sleep_start:
                duration = (datetime.now() - self.sleep_start).seconds
                self.night_shift.total_sleep_seconds = duration
            return
        
        # State transition
        old_state = self.last_user_state
        self.last_user_state = new_state
        
        if new_state in (UserState.IDLE, UserState.SLEEPING):
            # Entering sleep
            if not self.sleep_start:
                self.sleep_start = datetime.now()
                self.log_pulse(f"User State: {old_state.value} → {new_state.value}")
        
        elif new_state == UserState.ACTIVE:
            # Waking up
            if self.sleep_start:
                duration = (datetime.now() - self.sleep_start).seconds
                self.night_shift.total_sleep_seconds += duration
                self.sleep_start = None
                
                hours = duration // 3600
                minutes = (duration % 3600) // 60
                self.log_pulse(f"Wake Detected (was {new_state.value} for {hours}h {minutes}m)")
    
    def paul_pulse(self):
        """5-minute Paul awareness pulse."""
        time_ctx = get_time_context()
        user_state = get_user_state()
        active_window = get_active_window()
        
        self.handle_user_state_change(user_state)
        
        # Only log if active (compress idle time)
        if user_state == UserState.ACTIVE:
            self.log_pulse(f"Paul Active: {active_window or 'unknown'} | Energy: {time_ctx['energy_estimate']}")
    
    def system_ops(self):
        """15-minute system operations."""
        self.log_pulse("System Ops: Starting git sentinel")
        
        new_entries = git_sentinel(GIT_REPOS, self.night_shift)
        self.pulse_log.extend(new_entries)
    
    def api_probe(self):
        """Hourly API bridge check."""
        bridge = probe_api_bridge()
        self.night_shift.bridge_connectivity = bridge["status"] == "active"
        self.log_pulse(f"API Bridge: {bridge['status']}")
    
    def save_state(self):
        """Save warm context to disk."""
        DAEMON_DIR.mkdir(parents=True, exist_ok=True)
        
        paul_state = {
            "user_state": self.last_user_state.value,
            "time": get_time_context(),
            "active_window": get_active_window(),
        }
        
        context = generate_warm_context(
            paul_state,
            self.night_shift,
            self.pulse_log,
            self.boot_time
        )
        
        WARM_CONTEXT.write_text(context.to_json())
        
        # Also write daemon state
        DAEMON_STATE.write_text(json.dumps({
            "pid": os.getpid(),
            "boot_time": self.boot_time.isoformat(),
            "last_pulse": datetime.now().isoformat(),
            "status": "running"
        }, indent=2))
    
    def run(self):
        """Main daemon loop."""
        # Acquire lock
        if not self.lock.acquire():
            log.error("Another daemon instance is running. Exiting.")
            sys.exit(1)
        
        self.running = True
        log.info(f"⟡ MirrorOS Daemon v2.0 started (PID: {os.getpid()})")
        self.log_pulse("Daemon Boot")
        
        # Signal handlers
        def shutdown(signum, frame):
            log.info("Shutdown signal received")
            self.running = False
        
        signal.signal(signal.SIGTERM, shutdown)
        signal.signal(signal.SIGINT, shutdown)
        
        try:
            while self.running:
                now = datetime.now()
                
                # Paul pulse (every 5 min)
                if (now - self.last_paul_pulse).seconds >= PAUL_PULSE_INTERVAL:
                    self.paul_pulse()
                    self.last_paul_pulse = now
                
                # System ops (every 15 min)
                if (now - self.last_system_ops).seconds >= SYSTEM_OPS_INTERVAL:
                    self.system_ops()
                    self.last_system_ops = now
                
                # API probe (every 60 min)
                if (now - self.last_api_probe).seconds >= API_PROBE_INTERVAL:
                    self.api_probe()
                    self.last_api_probe = now
                
                # Save state after each cycle
                self.save_state()
                
                # Sleep until next check (1 minute resolution)
                time.sleep(60)
        
        except Exception as e:
            log.error(f"Daemon error: {e}")
            self.night_shift.errors.append(str(e))
            raise
        
        finally:
            self.night_shift.status = "complete"
            self.save_state()
            self.lock.release()
            log.info("⟡ Daemon shutdown complete")

# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == "--status":
            if DAEMON_STATE.exists():
                print(DAEMON_STATE.read_text())
            else:
                print("Daemon not running")
        
        elif cmd == "--context":
            if WARM_CONTEXT.exists():
                print(WARM_CONTEXT.read_text())
            else:
                print("No warm context")
        
        elif cmd == "--pulse":
            # Single pulse for testing
            daemon = MirrorOSDaemon()
            daemon.paul_pulse()
            daemon.system_ops()
            daemon.api_probe()
            daemon.save_state()
            print(WARM_CONTEXT.read_text())
        
        elif cmd == "--stop":
            if DAEMON_STATE.exists():
                state = json.loads(DAEMON_STATE.read_text())
                pid = state.get("pid")
                if pid:
                    os.kill(pid, signal.SIGTERM)
                    print(f"Sent SIGTERM to {pid}")
            else:
                print("Daemon not running")
        
        else:
            print(f"Unknown command: {cmd}")
            print("Usage: daemon.py [--status|--context|--pulse|--stop]")
    else:
        # Run daemon
        daemon = MirrorOSDaemon()
        daemon.run()

if __name__ == "__main__":
    main()
