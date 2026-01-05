#!/usr/bin/env python3
"""
SUPERAGENT — Reflection Ingest Tool
Syncs specs created in external AI sessions (ChatGPT, Gemini, etc.) back to the kernel.

Usage:
    python ingest_spec.py "paste your spec here" --project mirrorgate --version 6.0
    python ingest_spec.py --file /path/to/spec.md --project mirrorgate
"""

import os
import re
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import argparse

# Paths
KERNEL_PATH = Path.home() / "Documents/GitHub/active-mirror-identity/ami_active-mirror.json"
VAULT_PATH = Path.home() / "Library/Mobile Documents/iCloud~md~obsidian/Documents/MirrorDNA-Vault"
INGEST_LOG = VAULT_PATH / "Superagent/ingest_log.json"
SPECS_DIR = VAULT_PATH / "Superagent/ingested_specs"


def ensure_dirs():
    """Create necessary directories."""
    SPECS_DIR.mkdir(parents=True, exist_ok=True)
    INGEST_LOG.parent.mkdir(parents=True, exist_ok=True)


def detect_version(content: str) -> Optional[str]:
    """Extract version from spec content."""
    patterns = [
        r'v(\d+\.?\d*\.?\d*)',
        r'version[:\s]+(\d+\.?\d*\.?\d*)',
        r'Version[:\s]+(\d+\.?\d*\.?\d*)',
    ]
    for p in patterns:
        match = re.search(p, content)
        if match:
            return match.group(1)
    return None


def detect_project(content: str) -> Optional[str]:
    """Guess project from content."""
    content_lower = content.lower()
    if 'mirrorgate' in content_lower:
        return 'mirrorgate'
    if 'mirrorbrain' in content_lower:
        return 'mirrorbrain'
    if 'spine' in content_lower:
        return 'spine'
    if 'scd' in content_lower:
        return 'scd'
    return 'unknown'


def compute_hash(content: str) -> str:
    """SHA256 of content for dedup."""
    return hashlib.sha256(content.encode()).hexdigest()[:12]


def load_ingest_log() -> list:
    """Load existing ingest log."""
    if INGEST_LOG.exists():
        try:
            return json.loads(INGEST_LOG.read_text())
        except:
            return []
    return []


def save_ingest_log(log: list):
    """Save ingest log."""
    INGEST_LOG.write_text(json.dumps(log, indent=2))


def append_to_kernel(entry: Dict[str, Any]) -> bool:
    """Append ingestion record to kernel's memory chain."""
    if not KERNEL_PATH.exists():
        print(f"⚠️  Kernel not found at {KERNEL_PATH}")
        return False
    
    try:
        kernel = json.loads(KERNEL_PATH.read_text())
        
        # Add to memory chain
        if 'memory_chain' not in kernel:
            kernel['memory_chain'] = []
        
        kernel['memory_chain'].append({
            "timestamp": datetime.now().isoformat(),
            "entry_type": "spec_ingest",
            "source": "Superagent_Ingest",
            "content": f"Ingested {entry['project']} spec v{entry['version']} from external AI session",
            "metadata": {
                "project": entry['project'],
                "version": entry['version'],
                "hash": entry['hash'],
                "file": entry['saved_path']
            },
            "writer": "superagent"
        })
        
        KERNEL_PATH.write_text(json.dumps(kernel, indent=2))
        return True
    except Exception as e:
        print(f"⚠️  Failed to update kernel: {e}")
        return False


def ingest_spec(
    content: str,
    project: Optional[str] = None,
    version: Optional[str] = None,
    source_ai: str = "unknown"
) -> Dict[str, Any]:
    """
    Ingest a spec from external AI session.
    
    Returns record of ingestion.
    """
    ensure_dirs()
    
    # Auto-detect if not provided
    project = project or detect_project(content)
    version = version or detect_version(content) or "0.0"
    content_hash = compute_hash(content)
    
    # Check for duplicates
    log = load_ingest_log()
    for entry in log:
        if entry.get('hash') == content_hash:
            print(f"⚠️  Duplicate detected: already ingested as {entry['saved_path']}")
            return {"status": "duplicate", "existing": entry}
    
    # Save spec file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{project}_v{version}_{timestamp}.md"
    spec_path = SPECS_DIR / filename
    spec_path.write_text(content)
    
    # Create entry
    entry = {
        "timestamp": datetime.now().isoformat(),
        "project": project,
        "version": version,
        "source_ai": source_ai,
        "hash": content_hash,
        "saved_path": str(spec_path),
        "lines": len(content.split('\n')),
        "synced_to_kernel": False
    }
    
    # Update kernel
    if append_to_kernel(entry):
        entry['synced_to_kernel'] = True
        print(f"✅ Synced to kernel")
    
    # Update log
    log.append(entry)
    save_ingest_log(log)
    
    print(f"✅ Ingested: {project} v{version}")
    print(f"   Saved to: {spec_path}")
    print(f"   Hash: {content_hash}")
    
    return {"status": "ingested", "entry": entry}


def main():
    parser = argparse.ArgumentParser(description="Ingest specs from external AI sessions")
    parser.add_argument("content", nargs="?", help="Spec content (or use --file)")
    parser.add_argument("--file", "-f", help="Path to spec file")
    parser.add_argument("--project", "-p", help="Project name (auto-detected if not provided)")
    parser.add_argument("--version", "-v", help="Version (auto-detected if not provided)")
    parser.add_argument("--source", "-s", default="chatgpt", help="Source AI (chatgpt, gemini, etc)")
    parser.add_argument("--list", "-l", action="store_true", help="List ingested specs")
    
    args = parser.parse_args()
    
    if args.list:
        log = load_ingest_log()
        print(f"\n⟡ Ingested Specs ({len(log)} total)\n")
        for entry in log[-10:]:  # Last 10
            synced = "✅" if entry.get('synced_to_kernel') else "❌"
            print(f"  {synced} {entry['project']} v{entry['version']} - {entry['source_ai']} - {entry['timestamp'][:10]}")
        return
    
    if args.file:
        content = Path(args.file).read_text()
    elif args.content:
        content = args.content
    else:
        print("❌ Provide spec content or --file path")
        return
    
    ingest_spec(content, args.project, args.version, args.source)


if __name__ == "__main__":
    main()
