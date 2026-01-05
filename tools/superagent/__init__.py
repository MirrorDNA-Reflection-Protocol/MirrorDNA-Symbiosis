#!/usr/bin/env python3
"""
SUPERAGENT — CLI Entrypoint
Unified interface for all Superagent tools.

Usage:
    superagent ingest "spec content"      # Ingest external spec
    superagent scan                        # Scan for version drift
    superagent sync                        # Sync all pending items to kernel
    superagent status                      # Show current state
"""

import sys
import subprocess
from pathlib import Path

TOOLS_DIR = Path(__file__).parent


def show_help():
    print("""
⟡ SUPERAGENT — Multi-AI Sync & Automation

Commands:
    ingest <content|--file>   Ingest spec from external AI session
    scan                       Scan for version drift across projects
    sync                       Sync pending items to kernel
    status                     Show current sync state

Examples:
    superagent ingest --file /path/to/spec.md --project mirrorgate
    superagent scan --project mirrorgate
    superagent status

For command-specific help:
    superagent ingest --help
    superagent scan --help
""")


def main():
    if len(sys.argv) < 2:
        show_help()
        return
    
    cmd = sys.argv[1]
    args = sys.argv[2:]
    
    if cmd == "ingest":
        script = TOOLS_DIR / "ingest_spec.py"
        subprocess.run(["python3", str(script)] + args)
    
    elif cmd == "scan":
        script = TOOLS_DIR / "version_scanner.py"
        subprocess.run(["python3", str(script)] + args)
    
    elif cmd == "status":
        # Quick status check
        from ingest_spec import load_ingest_log, INGEST_LOG
        log = load_ingest_log()
        synced = sum(1 for e in log if e.get('synced_to_kernel'))
        pending = len(log) - synced
        print(f"\n⟡ Superagent Status")
        print(f"   Ingested specs: {len(log)}")
        print(f"   Synced to kernel: {synced}")
        print(f"   Pending sync: {pending}")
        print(f"   Log: {INGEST_LOG}\n")
    
    elif cmd in ["help", "-h", "--help"]:
        show_help()
    
    else:
        print(f"❌ Unknown command: {cmd}")
        show_help()


if __name__ == "__main__":
    main()
