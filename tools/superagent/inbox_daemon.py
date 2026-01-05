#!/usr/bin/env python3
"""
SUPERAGENT — Autonomous Inbox Scanner v2.0
Now with: Approval Queue, Source Attribution, Conflict Locks

Features:
- Auto-executes spec_ingest and handoff tasks
- Declines execution tasks → moves to approval_queue/
- Parses source from YAML header or filename prefix
- Uses lockfiles to prevent conflicts
"""

import os
import json
import time
import subprocess
import shutil
import re
import fcntl
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import hashlib

# Config
SCAN_INTERVAL_SECONDS = 30 * 60  # 30 minutes
VAULT = Path.home() / "Library/Mobile Documents/iCloud~md~obsidian/Documents/MirrorDNA-Vault"
INBOX = VAULT / "Superagent" / "inbox"
PROCESSED = VAULT / "Superagent" / "processed"
APPROVAL_QUEUE = VAULT / "Superagent" / "approval_queue"  # NEW
LOCKS_DIR = VAULT / "Superagent" / "locks"  # NEW
OPEN_LOOPS = Path.home() / ".mirrordna" / "open_loops.md"
LOG_FILE = VAULT / "Superagent" / "daemon_log.json"
REALTIME_SERVER = "http://localhost:8765"


def ensure_dirs():
    INBOX.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    APPROVAL_QUEUE.mkdir(parents=True, exist_ok=True)
    LOCKS_DIR.mkdir(parents=True, exist_ok=True)
    OPEN_LOOPS.parent.mkdir(parents=True, exist_ok=True)


def log_event(event: str, details: str = ""):
    logs = []
    if LOG_FILE.exists():
        try:
            logs = json.loads(LOG_FILE.read_text())
        except:
            logs = []
    logs.append({
        "timestamp": datetime.now().isoformat(),
        "event": event,
        "details": details
    })
    logs = logs[-100:]
    LOG_FILE.write_text(json.dumps(logs, indent=2))
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {event}: {details}")


# ============ NEW: SOURCE ATTRIBUTION ============

def parse_source(path: Path, content: str) -> str:
    """Extract source from YAML header, filename, or content heuristics."""
    
    # 1. Check YAML frontmatter
    yaml_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if yaml_match:
        yaml_content = yaml_match.group(1)
        source_match = re.search(r'source:\s*(\w+)', yaml_content, re.IGNORECASE)
        if source_match:
            return source_match.group(1).lower()
    
    # 2. Check filename prefix
    name = path.name.upper()
    if name.startswith("GPT_") or name.startswith("CHATGPT_"):
        return "chatgpt"
    elif name.startswith("CLAUDE_"):
        return "claude"
    elif name.startswith("AG_") or name.startswith("ANTIGRAVITY_"):
        return "antigravity"
    elif name.startswith("PAUL_"):
        return "paul"
    
    # 3. Content heuristics
    content_lower = content.lower()
    if "chatgpt" in content_lower or "from gpt" in content_lower:
        return "chatgpt"
    elif "claude" in content_lower or "from claude" in content_lower:
        return "claude"
    elif "antigravity" in content_lower:
        return "antigravity"
    
    return "unknown"


def parse_priority(content: str) -> str:
    """Extract priority from YAML or content."""
    yaml_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if yaml_match:
        yaml_content = yaml_match.group(1)
        priority_match = re.search(r'priority:\s*(\w+)', yaml_content, re.IGNORECASE)
        if priority_match:
            return priority_match.group(1).lower()
    
    content_lower = content.lower()
    if "critical" in content_lower or "urgent" in content_lower:
        return "critical"
    elif "high" in content_lower:
        return "high"
    elif "low" in content_lower:
        return "low"
    
    return "medium"


# ============ NEW: CONFLICT LOCKS ============

def acquire_lock(task_name: str) -> Optional[Path]:
    """Try to acquire lock on a task. Returns lock path if successful."""
    lock_file = LOCKS_DIR / f"{hashlib.md5(task_name.encode()).hexdigest()[:8]}.lock"
    
    try:
        # Create lock file with metadata
        lock_data = {
            "task": task_name,
            "agent": "antigravity_daemon",
            "acquired_at": datetime.now().isoformat(),
            "pid": os.getpid()
        }
        
        # Check if lock exists and is stale (>1 hour old)
        if lock_file.exists():
            try:
                existing = json.loads(lock_file.read_text())
                acquired = datetime.fromisoformat(existing.get("acquired_at", "2000-01-01"))
                age_hours = (datetime.now() - acquired).total_seconds() / 3600
                if age_hours < 1:
                    log_event("lock_conflict", f"{task_name} locked by {existing.get('agent')}")
                    return None
                # Stale lock, we can take it
                log_event("lock_stale", f"Taking stale lock for {task_name}")
            except:
                pass
        
        lock_file.write_text(json.dumps(lock_data, indent=2))
        return lock_file
    except Exception as e:
        log_event("lock_error", str(e))
        return None


def release_lock(lock_file: Path):
    """Release a lock."""
    try:
        if lock_file.exists():
            lock_file.unlink()
    except Exception as e:
        log_event("lock_release_error", str(e))


# ============ ENHANCED TASK PARSING ============

def parse_task_file(path: Path) -> Optional[Dict]:
    """Parse task with source and priority."""
    try:
        content = path.read_text()
        
        task = {
            "file": path.name,
            "path": str(path),
            "content": content,
            "type": "unknown",
            "executable": False,
            "source": parse_source(path, content),  # NEW
            "priority": parse_priority(content)      # NEW
        }
        
        content_lower = content.lower()
        if "spec" in content_lower or "design" in content_lower:
            task["type"] = "spec_ingest"
            task["executable"] = True
        elif "handoff" in content_lower:
            task["type"] = "handoff"
            task["executable"] = True
        elif "review" in content_lower:
            task["type"] = "review_request"
            task["executable"] = False
        elif "execute" in content_lower or "run" in content_lower or "implement" in content_lower:
            task["type"] = "execution"
            task["executable"] = False  # Needs approval
        
        return task
    except Exception as e:
        log_event("parse_error", f"{path.name}: {e}")
        return None


def execute_task(task: Dict) -> Dict:
    result = {
        "task": task["file"],
        "type": task["type"],
        "source": task.get("source", "unknown"),
        "executed": False,
        "reason": "",
        "output": ""
    }
    
    if not task["executable"]:
        result["reason"] = f"Task type '{task['type']}' requires approval"
        # 6. Consortium Briefing (Auto-Publish)
        # Note: The original snippet had `task_name` and `file_path` which are not defined in this scope.
        # Assuming `task["file"]` for `task_name` and `Path(task["path"])` for `file_path`.
        # Also, `PROCESSED_DIR` is replaced with `PROCESSED`, and `DestActions` is removed as it's undefined.
        # The `result` variable in the snippet was overwriting the `result` dictionary,
        # so it's renamed to `publish_result_code` to avoid conflict.
        task_name = task["file"]
        file_path = Path(task["path"])
        if "Briefing" in task_name and file_path.suffix == ".md":
            try:
                log_event("exec_start", f"Auto-publishing briefing: {task_name}")
                cmd = f"/usr/bin/python3 /Users/mirror-admin/Documents/MirrorDNA-Symbiosis/tools/superagent/consortium.py publish '{file_path}'"
                publish_result_code = os.system(cmd)
                
                if publish_result_code == 0:
                    log_event("exec_complete", f"Published {task_name} to activemirror.ai")
                    # Move to processed
                    dest = PROCESSED / file_path.name
                    shutil.move(file_path, dest)
                    result["executed"] = True # Mark as executed if published
                    result["reason"] = "Auto-published briefing"
                    return result # Return early if briefing is handled
                else:
                    log_event("exec_fail", f"Publish failed code {publish_result_code}")
                    result["reason"] = f"Briefing publish failed (code {publish_result_code})"
                    return result # Return early if briefing is handled
            except Exception as e:
                log_event("exec_error", str(e))
                result["reason"] = f"Briefing publish error: {e}"
                return result # Return early if briefing is handled
        
        return result # Original return for non-executable tasks
    
    try:
        if task["type"] == "spec_ingest":
            cmd = [
                "python3",
                str(Path.home() / "Documents/MirrorDNA-Symbiosis/tools/superagent/ingest_spec.py"),
                "--file", task["path"],
                "--source", task.get("source", "inbox")
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            result["executed"] = proc.returncode == 0
            result["output"] = proc.stdout or proc.stderr
            result["reason"] = "Ingested via ingest_spec.py"
        
        elif task["type"] == "handoff":
            import urllib.request
            data = json.dumps({
                "from": task.get("source", "inbox_daemon"),
                "to": "antigravity",
                "summary": f"Inbox task: {task['file']}",
                "priority": task.get("priority", "normal")
            }).encode()
            req = urllib.request.Request(
                f"{REALTIME_SERVER}/handoff",
                data=data,
                headers={"Content-Type": "application/json"}
            )
            try:
                urllib.request.urlopen(req, timeout=5)
                result["executed"] = True
                result["reason"] = "Created handoff via API"
            except:
                result["reason"] = "API unreachable"
        
    except Exception as e:
        result["reason"] = f"Error: {e}"
    
    return result


# ============ NEW: APPROVAL QUEUE ============

def move_to_approval_queue(path: Path, task: Dict, reason: str):
    """Move declined task to approval queue instead of processed."""
    try:
        # Add approval metadata
        approval_meta = f"""
---
needs_approval: true
declined_at: {datetime.now().isoformat()}
declined_reason: {reason}
source: {task.get('source', 'unknown')}
priority: {task.get('priority', 'medium')}
---

"""
        content = path.read_text()
        if not content.startswith("---"):
            content = approval_meta + content
        
        dest = APPROVAL_QUEUE / path.name
        dest.write_text(content)
        path.unlink()
        
        log_event("queued_for_approval", f"{path.name} → approval_queue/")
    except Exception as e:
        log_event("approval_queue_error", str(e))


def update_open_loops(task: Dict, result: Dict):
    try:
        content = OPEN_LOOPS.read_text() if OPEN_LOOPS.exists() else "# Open Loops\n\n"
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        status = "✅" if result["executed"] else "⏸️"
        source = task.get("source", "?")
        entry = f"- [{status[0]}] [{source}] {task['file']} ({task['type']}) - {result['reason']} [{timestamp}]\n"
        
        if "## Auto-Processed" not in content:
            content += "\n## Auto-Processed (Inbox Daemon)\n\n"
        
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if "## Auto-Processed" in line:
                lines.insert(i + 2, entry)
                break
        
        OPEN_LOOPS.write_text("\n".join(lines))
    except Exception as e:
        log_event("open_loops_error", str(e))


def move_to_processed(path: Path):
    try:
        dest = PROCESSED / f"{datetime.now().strftime('%Y%m%d_%H%M')}_{path.name}"
        path.rename(dest)
    except Exception as e:
        log_event("move_error", str(e))


def scan_inbox() -> List[Dict]:
    tasks = []
    for file in INBOX.iterdir():
        if file.is_file() and file.suffix in [".md", ".txt", ".json"]:
            task = parse_task_file(file)
            if task:
                tasks.append(task)
    return tasks


def run_scan_cycle():
    log_event("scan_start", f"Scanning {INBOX}")
    
    tasks = scan_inbox()
    
    if not tasks:
        log_event("scan_complete", "No tasks in inbox")
        return
    
    log_event("tasks_found", f"{len(tasks)} task(s)")
    
    for task in tasks:
        # Try to acquire lock
        lock = acquire_lock(task["file"])
        if not lock:
            log_event("skipped", f"{task['file']} - locked by another agent")
            continue
        
        try:
            log_event("processing", f"{task['file']} (source: {task.get('source', '?')})")
            
            result = execute_task(task)
            
            if result["executed"]:
                log_event("executed", f"{task['file']}: {result['reason']}")
                update_open_loops(task, result)
                move_to_processed(Path(task["path"]))
            else:
                log_event("declined", f"{task['file']}: {result['reason']}")
                move_to_approval_queue(Path(task["path"]), task, result["reason"])
                update_open_loops(task, result)
        finally:
            release_lock(lock)
    
    log_event("scan_complete", f"Processed {len(tasks)} task(s)")


def list_approval_queue():
    """List tasks waiting for approval."""
    print("\n⟡ Approval Queue\n")
    tasks = list(APPROVAL_QUEUE.glob("*.md"))
    if not tasks:
        print("  (empty)")
        return
    for t in tasks:
        print(f"  - {t.name}")
    print(f"\nApprove with: python3 inbox_daemon.py --approve '{tasks[0].name}'")


def approve_task(filename: str):
    """Approve a task and move it back to inbox for execution."""
    task_path = APPROVAL_QUEUE / filename
    if not task_path.exists():
        print(f"❌ Not found: {filename}")
        return
    
    # Move to inbox with execution allowed
    content = task_path.read_text()
    # Mark as pre-approved
    if "---" in content:
        content = content.replace("needs_approval: true", "needs_approval: false\napproved: true")
    
    dest = INBOX / filename
    dest.write_text(content)
    task_path.unlink()
    print(f"✅ Approved: {filename} → moved to inbox for execution")


def daemon_loop():
    ensure_dirs()
    log_event("daemon_start", f"Interval: {SCAN_INTERVAL_SECONDS}s")
    
    while True:
        try:
            run_scan_cycle()
        except Exception as e:
            log_event("error", str(e))
        time.sleep(SCAN_INTERVAL_SECONDS)


def run_once():
    ensure_dirs()
    run_scan_cycle()


if __name__ == "__main__":
    import sys
    
    if "--once" in sys.argv:
        print("⟡ Running single scan...")
        run_once()
    elif "--daemon" in sys.argv:
        print("⟡ Starting daemon mode...")
        daemon_loop()
    elif "--queue" in sys.argv:
        ensure_dirs()
        list_approval_queue()
    elif "--approve" in sys.argv:
        idx = sys.argv.index("--approve")
        if idx + 1 < len(sys.argv):
            approve_task(sys.argv[idx + 1])
        else:
            print("Usage: --approve <filename>")
    else:
        print("""
⟡ Superagent Inbox Daemon v2.0

Usage:
    python3 inbox_daemon.py --once       # Single scan
    python3 inbox_daemon.py --daemon     # Continuous (every 30 min)
    python3 inbox_daemon.py --queue      # List approval queue
    python3 inbox_daemon.py --approve X  # Approve task X

Features:
    ✓ Source attribution (YAML header, filename prefix, heuristics)
    ✓ Approval queue (declined tasks wait for approval)
    ✓ Conflict locks (prevents two agents working same task)
""")
