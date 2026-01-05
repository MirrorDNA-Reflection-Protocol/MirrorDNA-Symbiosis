#!/usr/bin/env python3
"""
SUPERAGENT — ChatGPT Bridge
Synced ChatGPT via API with kernel context injection.

Usage:
    python chatgpt_bridge.py "your reflection prompt"
    python chatgpt_bridge.py --interactive

The bridge:
1. Reads current kernel state
2. Injects AMI identity + project versions as system context
3. Calls OpenAI API (GPT-5-mini for cost efficiency)
4. Ingests any specs from response back to kernel

Cost: ~$0.002 per reflection (under $1/month for daily use)
"""

import os
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
import argparse

try:
    from openai import OpenAI
except ImportError:
    print("⚠️  Install openai: pip install openai")
    exit(1)

# Paths
VAULT = Path.home() / "Library/Mobile Documents/iCloud~md~obsidian/Documents/MirrorDNA-Vault"
KERNEL = VAULT / "Superagent" / "kernel.json"
AMI_KERNEL = Path.home() / "Documents/GitHub/active-mirror-identity/ami_active-mirror.json"
MIRRORGATE_VERSION = Path.home() / "Documents/GitHub/activemirror-site/MIRRORGATE_VERSION.json"
CONVERSATION_LOG = VAULT / "Superagent" / "chatgpt_sessions.json"

# Load API key from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL = "gpt-4o-mini"  # Cost-effective for reflection


def load_kernel_context() -> str:
    """Build context string from kernel and project states."""
    context_parts = []
    
    # Load AMI identity
    if AMI_KERNEL.exists():
        try:
            ami = json.loads(AMI_KERNEL.read_text())
            identity = ami.get("identity", {}).get("human", {})
            context_parts.append(f"""
IDENTITY CONTEXT:
- Human: {identity.get('name', 'Paul')} ({identity.get('role', 'Founder')})
- System: Active MirrorOS
- Philosophy: Sovereignty, Truth-State, Zero Drift
""")
        except:
            pass
    
    # Load project versions
    if MIRRORGATE_VERSION.exists():
        try:
            mg = json.loads(MIRRORGATE_VERSION.read_text())
            context_parts.append(f"""
PROJECT VERSIONS (DO NOT CONTRADICT):
- MirrorGate: v{mg.get('spec_version', '?')} (implemented), v{mg.get('next_version', '?')} (roadmap)
- Codename: {mg.get('spec_codename', 'Unknown')} → {mg.get('next_codename', 'Unknown')}
""")
        except:
            pass
    
    # Load recent handoffs
    queue_file = VAULT / "Superagent" / "handoff_queue.json"
    if queue_file.exists():
        try:
            queue = json.loads(queue_file.read_text())
            pending = [h for h in queue if h.get('status') == 'pending']
            if pending:
                context_parts.append(f"""
PENDING HANDOFFS ({len(pending)}):
""" + "\n".join([f"- {h['id']}: {h['from_agent']} → {h['to_agent']}: {h['summary'][:50]}..." for h in pending[-3:]]))
        except:
            pass
    
    # Add today's date
    context_parts.append(f"\nTODAY: {datetime.now().strftime('%Y-%m-%d')}")
    
    return "\n".join(context_parts)


def build_system_prompt() -> str:
    """Create the system prompt with kernel context."""
    context = load_kernel_context()
    
    return f"""You are Paul's reflection partner within the Active MirrorOS ecosystem.

{context}

RULES:
1. You have access to the current system state above. Stay consistent with it.
2. If you create a spec or design, clearly mark it with [SPEC] so it can be ingested.
3. Never contradict the version numbers shown above.
4. If asked to design something for MirrorGate, reference current version (v5.1) and roadmap (v6.0 Lattice).
5. End reflections with a single clarifying question.

You are synced. You are sovereign. Reflect."""


def call_chatgpt(prompt: str) -> Optional[str]:
    """Call OpenAI API with kernel context."""
    if not OPENAI_API_KEY:
        print("❌ OPENAI_API_KEY not set. Run: export OPENAI_API_KEY=sk-...")
        return None
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    system_prompt = build_system_prompt()
    
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ API Error: {e}")
        return None


def extract_and_ingest_specs(response: str):
    """Look for [SPEC] blocks and ingest them."""
    # Simple pattern: look for [SPEC] markers
    spec_matches = re.findall(r'\[SPEC\](.*?)\[/SPEC\]', response, re.DOTALL)
    
    if not spec_matches:
        # Also check for markdown code blocks that look like specs
        spec_matches = re.findall(r'```(?:yaml|json|markdown)?\s*(.*?MirrorGate.*?)```', response, re.DOTALL | re.IGNORECASE)
    
    if spec_matches:
        print(f"⟡ Found {len(spec_matches)} potential spec(s) in response")
        # Would call ingest_spec here in full implementation


def log_conversation(prompt: str, response: str):
    """Log conversation for history."""
    log = []
    if CONVERSATION_LOG.exists():
        try:
            log = json.loads(CONVERSATION_LOG.read_text())
        except:
            log = []
    
    log.append({
        "timestamp": datetime.now().isoformat(),
        "prompt": prompt[:500],  # Truncate for storage
        "response": response[:1000],
        "model": MODEL
    })
    
    # Keep last 100 conversations
    log = log[-100:]
    CONVERSATION_LOG.write_text(json.dumps(log, indent=2))


def reflect(prompt: str) -> Optional[str]:
    """Main reflection function."""
    print(f"⟡ Reflecting with synced ChatGPT ({MODEL})...\n")
    
    response = call_chatgpt(prompt)
    
    if response:
        print(response)
        print("\n" + "─" * 50)
        extract_and_ingest_specs(response)
        log_conversation(prompt, response)
        return response
    
    return None


def interactive_mode():
    """Interactive reflection session."""
    print("""
⟡ ChatGPT Bridge — Interactive Mode
  Synced with kernel. Type 'exit' to quit.
─────────────────────────────────────────
""")
    
    while True:
        try:
            prompt = input("\n⟡ You: ").strip()
            if prompt.lower() in ['exit', 'quit', 'q']:
                print("⟡ Session ended")
                break
            if not prompt:
                continue
            
            print()
            reflect(prompt)
            
        except KeyboardInterrupt:
            print("\n⟡ Session ended")
            break


def main():
    parser = argparse.ArgumentParser(description="Synced ChatGPT Bridge")
    parser.add_argument("prompt", nargs="?", help="Reflection prompt")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--context", "-c", action="store_true", help="Show current context")
    
    args = parser.parse_args()
    
    if args.context:
        print("⟡ Current Kernel Context:\n")
        print(load_kernel_context())
        return
    
    if args.interactive:
        interactive_mode()
    elif args.prompt:
        reflect(args.prompt)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
