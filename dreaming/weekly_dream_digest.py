#!/usr/bin/env python3
"""
weekly_dream_digest.py

Generates a weekly summary of The Dreaming's activity.
Runs Sunday 08:00 — drops a digest in the Vault.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

DREAM_JOURNAL = Path("/Users/mirror-admin/Documents/MirrorDNA-Symbiosis/dream_journal.json")
VAULT_DIGEST_DIR = Path("/Users/mirror-admin/Documents/MirrorDNA-Vault/Digests")
VAULT_DIGEST_DIR.mkdir(parents=True, exist_ok=True)

def load_dreams():
    if not DREAM_JOURNAL.exists():
        return []
    return json.loads(DREAM_JOURNAL.read_text())

def filter_last_week(dreams):
    cutoff = datetime.now().timestamp() - (7 * 24 * 60 * 60)
    return [d for d in dreams if d.get("timestamp", 0) > cutoff]

def generate_digest(dreams):
    now = datetime.now()
    week_start = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    week_end = now.strftime("%Y-%m-%d")
    
    lines = [
        f"# ⟡ Dream Digest — {week_start} to {week_end}",
        "",
        f"**Generated:** {now.isoformat()}",
        f"**Dreams this week:** {len(dreams)}",
        "",
        "---",
        ""
    ]
    
    if not dreams:
        lines.append("No dreams recorded this week. System was quiet.")
    else:
        lines.append("## Optimizations")
        lines.append("")
        for i, dream in enumerate(dreams, 1):
            ts = datetime.fromtimestamp(dream["timestamp"]).strftime("%Y-%m-%d %H:%M")
            original = dream.get("original_event", {})
            action = original.get("action", "Unknown")
            result_preview = str(original.get("result", ""))[:100]
            
            lines.append(f"### {i}. {ts}")
            lines.append(f"**Trigger:** {action}")
            lines.append(f"**Original:** `{result_preview}...`")
            lines.append("")
            
            optimization = dream.get("dream_optimization", "")
            if len(optimization) > 300:
                optimization = optimization[:300] + "..."
            lines.append(f"**Fix:** {optimization}")
            lines.append("")
            lines.append("---")
            lines.append("")
    
    lines.extend([
        "",
        "⟡ Prime Neuro (Llama 3.2 3B) — The Dreaming Engine"
    ])
    
    return "\n".join(lines)

def main():
    dreams = load_dreams()
    week_dreams = filter_last_week(dreams)
    digest = generate_digest(week_dreams)
    
    filename = f"DREAM_DIGEST_{datetime.now().strftime('%Y%m%d')}.md"
    output_path = VAULT_DIGEST_DIR / filename
    output_path.write_text(digest)
    
    print(f"⟡ Digest written to {output_path}")
    print(f"⟡ {len(week_dreams)} dreams summarized")

if __name__ == "__main__":
    main()
