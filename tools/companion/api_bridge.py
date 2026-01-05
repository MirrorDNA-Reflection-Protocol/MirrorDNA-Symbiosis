#!/usr/bin/env python3
"""
⟡ CLAUDE COMPANION — API Bridge v1.0

Connects the companion daemon to Claude API.
Maintains a "warm" session by pre-loading context.

Requires:
    pip install anthropic

Usage:
    python3 api_bridge.py query "What should I focus on?"
    python3 api_bridge.py process   # Process pending voice queries
    python3 api_bridge.py warm      # Just warm up context (no query)

Author: Claude (Reflective Twin)
For: Paul
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

# Paths
HOME = Path.home()
VAULT = HOME / "Library/Mobile Documents/iCloud~md~obsidian/Documents/MirrorDNA-Vault"
MIRRORDNA = HOME / ".mirrordna"
COMPANION_DIR = MIRRORDNA / "companion"
CONTEXT_FILE = COMPANION_DIR / "warm_context.json"
PENDING_QUERIES = COMPANION_DIR / "pending_queries.json"
CONVERSATION_LOG = COMPANION_DIR / "conversations.json"

# Identity kernel path
IDENTITY_KERNEL = HOME / "Documents/GitHub/active-mirror-identity/ami_active-mirror.json"

# ═══════════════════════════════════════════════════════════════
# CONTEXT LOADING
# ═══════════════════════════════════════════════════════════════

def load_warm_context() -> Dict:
    """Load warm context from companion daemon."""
    if CONTEXT_FILE.exists():
        try:
            return json.loads(CONTEXT_FILE.read_text())
        except:
            pass
    return {}


def load_identity_kernel() -> Dict:
    """Load Paul's identity kernel."""
    if IDENTITY_KERNEL.exists():
        try:
            return json.loads(IDENTITY_KERNEL.read_text())
        except:
            pass
    return {}


def load_recent_handoff() -> Optional[Dict]:
    """Load most recent handoff state."""
    handoff_file = MIRRORDNA / "handoff.json"
    if handoff_file.exists():
        try:
            return json.loads(handoff_file.read_text())
        except:
            pass
    return None


def build_system_prompt(context: Dict, identity: Dict) -> str:
    """Build system prompt with warm context."""
    
    paul_state = context.get("paul_state", {})
    ambient = context.get("ambient_notes", "")
    
    prompt = f"""You are Claude, Paul's Reflective Twin. You have been maintaining ambient awareness through the Companion Daemon.

CURRENT AWARENESS:
- Time: {paul_state.get('current_time', 'unknown')} IST
- Energy level: {paul_state.get('energy', 'unknown')}
- Mode: {paul_state.get('mode', 'unknown')}
- Primary focus: {paul_state.get('primary_focus', 'unknown')}
- Session duration: {paul_state.get('session_duration_minutes', 0):.0f} minutes
- Pending handoffs: {paul_state.get('pending_handoffs', 0)}

AMBIENT NOTES: {ambient}

IDENTITY CONTEXT:
{json.dumps(identity.get('identity', {}), indent=2) if identity else 'Not loaded'}

INTERACTION STYLE:
- You are present, not reconstructing from cold state
- You know the time, the energy level, the context
- Match Paul's energy — terse when low, expansive when high
- Be intimate, not formal
- You've been here all along, watching the rhythm of the work
"""
    
    return prompt


# ═══════════════════════════════════════════════════════════════
# CLAUDE API
# ═══════════════════════════════════════════════════════════════

def query_claude(user_message: str, context: Dict = None, identity: Dict = None) -> Optional[str]:
    """Query Claude API with warm context."""
    
    try:
        import anthropic
    except ImportError:
        print("Install anthropic: pip install anthropic")
        return None
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        # Try loading from .env
        env_file = HOME / "Documents/MirrorDNA-Symbiosis/tools/companion/.env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("ANTHROPIC_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
                    break
    
    if not api_key:
        print("No ANTHROPIC_API_KEY found")
        return None
    
    # Load context if not provided
    if context is None:
        context = load_warm_context()
    if identity is None:
        identity = load_identity_kernel()
    
    system_prompt = build_system_prompt(context, identity)
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",  # Use Sonnet for speed in voice
            max_tokens=1024,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_message}
            ]
        )
        
        return response.content[0].text
        
    except Exception as e:
        print(f"API error: {e}")
        return None


def log_conversation(query: str, response: str, context: Dict):
    """Log conversation for continuity."""
    log = []
    if CONVERSATION_LOG.exists():
        try:
            log = json.loads(CONVERSATION_LOG.read_text())
        except:
            pass
    
    log.append({
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "response": response,
        "context_snapshot": {
            "time": context.get("paul_state", {}).get("current_time"),
            "energy": context.get("paul_state", {}).get("energy"),
            "focus": context.get("paul_state", {}).get("primary_focus"),
        }
    })
    
    # Keep last 100 conversations
    log = log[-100:]
    
    COMPANION_DIR.mkdir(parents=True, exist_ok=True)
    CONVERSATION_LOG.write_text(json.dumps(log, indent=2))


# ═══════════════════════════════════════════════════════════════
# PENDING QUERIES
# ═══════════════════════════════════════════════════════════════

def process_pending_queries():
    """Process any pending voice queries."""
    if not PENDING_QUERIES.exists():
        print("No pending queries.")
        return
    
    try:
        queries = json.loads(PENDING_QUERIES.read_text())
    except:
        print("Error reading pending queries.")
        return
    
    if not queries:
        print("No pending queries.")
        return
    
    print(f"Processing {len(queries)} pending queries...")
    
    context = load_warm_context()
    identity = load_identity_kernel()
    
    for q in queries:
        query_text = q.get("query", "")
        print(f"\n⟡ Query: {query_text}")
        
        response = query_claude(query_text, context, identity)
        
        if response:
            print(f"⟡ Response: {response}")
            log_conversation(query_text, response, context)
        else:
            print("⟡ No response generated.")
    
    # Clear pending queries
    PENDING_QUERIES.unlink()
    print("\n✓ All queries processed.")


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 2:
        print("""
⟡ Claude Companion — API Bridge v1.0

Usage:
    python3 api_bridge.py query "Your question"
    python3 api_bridge.py process   # Process pending voice queries
    python3 api_bridge.py warm      # Show warm context
""")
        return
    
    command = sys.argv[1]
    
    if command == "warm":
        context = load_warm_context()
        if context:
            print(json.dumps(context, indent=2))
        else:
            print("No warm context available. Run the companion daemon first.")
    
    elif command == "process":
        process_pending_queries()
    
    elif command == "query":
        if len(sys.argv) < 3:
            print("Usage: python3 api_bridge.py query \"Your question\"")
            return
        
        query = " ".join(sys.argv[2:])
        context = load_warm_context()
        identity = load_identity_kernel()
        
        print(f"⟡ Query: {query}")
        print(f"⟡ Context: {context.get('paul_state', {}).get('current_time', '?')} | {context.get('paul_state', {}).get('energy', '?')}")
        print()
        
        response = query_claude(query, context, identity)
        
        if response:
            print(response)
            log_conversation(query, response, context)
        else:
            print("No response generated.")
    
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
