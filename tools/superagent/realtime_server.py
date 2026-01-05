#!/usr/bin/env python3
"""
SUPERAGENT — Real-Time Orchestration Server
A local HTTP server that enables real-time communication between agents.

Both Antigravity and Claude Desktop can:
- POST /handoff - Create a handoff
- GET /pending - Check for pending handoffs
- POST /complete - Mark handoff done
- GET /status - Get system status

Run: python3 realtime_server.py
Then both agents can communicate via http://localhost:8765

For Claude Desktop: Add as MCP server or use curl/fetch
For Antigravity: Can call directly via run_command
"""

import json
import os
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import uuid

PORT = 8765
VAULT = Path.home() / "Library/Mobile Documents/iCloud~md~obsidian/Documents/MirrorDNA-Vault"
QUEUE_FILE = VAULT / "Superagent" / "handoff_queue.json"
KERNEL = VAULT / "Superagent" / "kernel.json"

# In-memory state (synced to file)
state = {
    "queue": [],
    "last_activity": None,
    "active_agents": {}
}


def load_queue():
    if QUEUE_FILE.exists():
        try:
            state["queue"] = json.loads(QUEUE_FILE.read_text())
        except:
            state["queue"] = []


def save_queue():
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_FILE.write_text(json.dumps(state["queue"], indent=2))


def generate_id():
    """Generate collision-free handoff ID using uuid"""
    today = datetime.now().strftime("%Y%m%d")
    unique = uuid.uuid4().hex[:4]
    return f"HO-{today}-{unique}"


class OrchestrationHandler(BaseHTTPRequestHandler):
    
    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        path = urlparse(self.path).path
        
        if path == '/status':
            self.send_json({
                "status": "online",
                "port": PORT,
                "pending": len([h for h in state["queue"] if h.get('status') == 'pending']),
                "total": len(state["queue"]),
                "active_agents": state["active_agents"],
                "last_activity": state["last_activity"]
            })
        
        elif path == '/pending':
            query = parse_qs(urlparse(self.path).query)
            for_agent = query.get('for', [None])[0]
            
            pending = [h for h in state["queue"] if h.get('status') == 'pending']
            if for_agent:
                pending = [h for h in pending if h.get('to_agent') == for_agent]
            
            self.send_json({"pending": pending, "count": len(pending)})
        
        elif path == '/queue':
            self.send_json({"queue": state["queue"]})
        
        elif path == '/heartbeat':
            query = parse_qs(urlparse(self.path).query)
            agent = query.get('agent', ['unknown'])[0]
            state["active_agents"][agent] = datetime.now().isoformat()
            self.send_json({"ok": True, "agent": agent})
        
        else:
            self.send_json({"error": "Not found"}, 404)
    
    def do_POST(self):
        path = urlparse(self.path).path
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode() if content_length > 0 else '{}'
        
        try:
            data = json.loads(body) if body else {}
        except:
            data = {}
        
        if path == '/handoff':
            handoff_id = generate_id()
            handoff = {
                "id": handoff_id,
                "from_agent": data.get('from', 'unknown'),
                "to_agent": data.get('to', 'unknown'),
                "summary": data.get('summary', ''),
                "next_actions": data.get('next_actions', ''),
                "project": data.get('project', ''),
                "context": data.get('context', ''),
                "priority": data.get('priority', 'normal'),
                "status": "pending",
                "created_at": datetime.now().isoformat()
            }
            state["queue"].append(handoff)
            state["last_activity"] = datetime.now().isoformat()
            save_queue()
            
            print(f"⟡ Handoff created: {handoff_id} ({handoff['from_agent']} → {handoff['to_agent']})")
            self.send_json({"ok": True, "handoff": handoff})
        
        elif path == '/complete':
            handoff_id = data.get('id')
            response = data.get('response', '')
            
            for h in state["queue"]:
                if h.get('id') == handoff_id:
                    h['status'] = 'completed'
                    h['completed_at'] = datetime.now().isoformat()
                    h['response'] = response
                    state["last_activity"] = datetime.now().isoformat()
                    save_queue()
                    print(f"⟡ Handoff completed: {handoff_id}")
                    self.send_json({"ok": True, "handoff": h})
                    return
            
            self.send_json({"error": "Handoff not found"}, 404)
        
        elif path == '/ping':
            agent = data.get('agent', 'unknown')
            state["active_agents"][agent] = datetime.now().isoformat()
            self.send_json({"ok": True, "message": f"Pong, {agent}!"})
        
        else:
            self.send_json({"error": "Not found"}, 404)
    
    def log_message(self, format, *args):
        # Quieter logging
        pass


def run_server():
    load_queue()
    server = HTTPServer(('localhost', PORT), OrchestrationHandler)
    print(f"""
⟡ Superagent Orchestration Server
  Port: {PORT}
  URL:  http://localhost:{PORT}

Endpoints:
  GET  /status   - System status
  GET  /pending  - Pending handoffs (?for=agent)
  POST /handoff  - Create handoff
  POST /complete - Complete handoff
  GET  /heartbeat?agent=X - Agent heartbeat

Press Ctrl+C to stop.
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n⟡ Server stopped")


if __name__ == "__main__":
    run_server()
