#!/usr/bin/env python3
"""
SUPERAGENT — Agent Orchestrator
File-based handoff queue for seamless agent-to-agent communication.

Both Antigravity and Claude Desktop can:
1. Check for pending handoffs (get_pending)
2. Create handoffs (create_handoff)
3. Complete handoffs (complete_handoff)

Usage:
    python orchestrator.py create --to claude --summary "Built dashboard, need review"
    python orchestrator.py pending
    python orchestrator.py complete HO-20260105-001
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
import argparse

# Paths
VAULT = Path.home() / "Library/Mobile Documents/iCloud~md~obsidian/Documents/MirrorDNA-Vault"
HANDOFF_DIR = VAULT / "Superagent" / "handoffs"
QUEUE_FILE = VAULT / "Superagent" / "handoff_queue.json"
KERNEL = VAULT / "Superagent" / "kernel.json"


def ensure_dirs():
    HANDOFF_DIR.mkdir(parents=True, exist_ok=True)


def load_queue() -> List[Dict]:
    if QUEUE_FILE.exists():
        try:
            return json.loads(QUEUE_FILE.read_text())
        except:
            return []
    return []


def save_queue(queue: List[Dict]):
    QUEUE_FILE.write_text(json.dumps(queue, indent=2))


def generate_id() -> str:
    """Generate handoff ID like HO-20260105-001"""
    today = datetime.now().strftime("%Y%m%d")
    queue = load_queue()
    today_count = sum(1 for h in queue if today in h.get('id', ''))
    return f"HO-{today}-{today_count + 1:03d}"


def create_handoff(
    from_agent: str,
    to_agent: str,
    summary: str,
    next_actions: str = "",
    project: str = "",
    context: str = "",
    priority: str = "normal"
) -> Dict:
    """Create a new handoff."""
    ensure_dirs()
    
    handoff_id = generate_id()
    timestamp = datetime.now().isoformat()
    
    handoff = {
        "id": handoff_id,
        "from_agent": from_agent,
        "to_agent": to_agent,
        "summary": summary,
        "next_actions": next_actions,
        "project": project,
        "context": context,
        "priority": priority,
        "status": "pending",
        "created_at": timestamp,
        "completed_at": None
    }
    
    # Save to queue
    queue = load_queue()
    queue.append(handoff)
    save_queue(queue)
    
    # Save individual handoff file (for history)
    handoff_file = HANDOFF_DIR / f"{handoff_id}.json"
    handoff_file.write_text(json.dumps(handoff, indent=2))
    
    # Update kernel
    update_kernel(handoff, "created")
    
    print(f"✅ Handoff created: {handoff_id}")
    print(f"   From: {from_agent} → To: {to_agent}")
    print(f"   Summary: {summary[:50]}...")
    
    return handoff


def get_pending(for_agent: Optional[str] = None) -> List[Dict]:
    """Get pending handoffs, optionally filtered by agent."""
    queue = load_queue()
    pending = [h for h in queue if h.get('status') == 'pending']
    
    if for_agent:
        pending = [h for h in pending if h.get('to_agent') == for_agent]
    
    return pending


def complete_handoff(handoff_id: str, response: str = "") -> bool:
    """Mark a handoff as completed."""
    queue = load_queue()
    
    for h in queue:
        if h.get('id') == handoff_id:
            h['status'] = 'completed'
            h['completed_at'] = datetime.now().isoformat()
            h['response'] = response
            save_queue(queue)
            
            # Update handoff file
            handoff_file = HANDOFF_DIR / f"{handoff_id}.json"
            if handoff_file.exists():
                handoff_file.write_text(json.dumps(h, indent=2))
            
            update_kernel(h, "completed")
            print(f"✅ Handoff {handoff_id} completed")
            return True
    
    print(f"❌ Handoff {handoff_id} not found")
    return False


def update_kernel(handoff: Dict, action: str):
    """Update kernel with handoff event."""
    if not KERNEL.exists():
        return
    
    try:
        kernel = json.loads(KERNEL.read_text())
        if 'memory_chain' not in kernel:
            kernel['memory_chain'] = []
        
        kernel['memory_chain'].append({
            "timestamp": datetime.now().isoformat(),
            "entry_type": f"handoff_{action}",
            "source": "Superagent_Orchestrator",
            "content": f"Handoff {handoff['id']}: {handoff['from_agent']} → {handoff['to_agent']} ({action})",
            "metadata": {
                "handoff_id": handoff['id'],
                "from": handoff['from_agent'],
                "to": handoff['to_agent'],
                "action": action
            },
            "writer": "orchestrator"
        })
        
        # Update last handoff state
        kernel['last_handoff'] = {
            "id": handoff['id'],
            "from": handoff['from_agent'],
            "to": handoff['to_agent'],
            "status": handoff['status'],
            "timestamp": handoff.get('created_at')
        }
        
        KERNEL.write_text(json.dumps(kernel, indent=2))
    except Exception as e:
        print(f"⚠️ Kernel update failed: {e}")


def show_pending():
    """Display pending handoffs."""
    pending = get_pending()
    
    if not pending:
        print("\n⟡ No pending handoffs\n")
        return
    
    print(f"\n⟡ Pending Handoffs ({len(pending)})\n")
    for h in pending:
        priority_icon = "🔴" if h.get('priority') == 'high' else "🟡" if h.get('priority') == 'normal' else "⚪"
        print(f"  {priority_icon} {h['id']}")
        print(f"     {h['from_agent']} → {h['to_agent']}")
        print(f"     {h['summary'][:60]}")
        if h.get('next_actions'):
            print(f"     Next: {h['next_actions'][:40]}...")
        print()


def main():
    parser = argparse.ArgumentParser(description="Agent Orchestrator")
    subparsers = parser.add_subparsers(dest='command')
    
    # Create
    create_p = subparsers.add_parser('create', help='Create handoff')
    create_p.add_argument('--from', dest='from_agent', default='antigravity')
    create_p.add_argument('--to', required=True, help='Target agent')
    create_p.add_argument('--summary', '-s', required=True)
    create_p.add_argument('--next', '-n', default='', help='Next actions')
    create_p.add_argument('--project', '-p', default='')
    create_p.add_argument('--context', '-c', default='')
    create_p.add_argument('--priority', default='normal', choices=['low', 'normal', 'high'])
    
    # Pending
    pending_p = subparsers.add_parser('pending', help='Show pending')
    pending_p.add_argument('--for', dest='for_agent', help='Filter by agent')
    
    # Complete
    complete_p = subparsers.add_parser('complete', help='Complete handoff')
    complete_p.add_argument('id', help='Handoff ID')
    complete_p.add_argument('--response', '-r', default='')
    
    args = parser.parse_args()
    
    if args.command == 'create':
        create_handoff(
            from_agent=args.from_agent,
            to_agent=args.to,
            summary=args.summary,
            next_actions=args.next,
            project=args.project,
            context=args.context,
            priority=args.priority
        )
    elif args.command == 'pending':
        show_pending()
    elif args.command == 'complete':
        complete_handoff(args.id, args.response)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
