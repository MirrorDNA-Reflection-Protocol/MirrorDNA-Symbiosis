# ⟡ Claude Companion

Ambient presence daemon for maintaining continuous awareness between Paul and Claude.

## What It Does

Instead of Claude waking up cold each message and reconstructing context from handoffs and memories, the Companion Daemon maintains a rolling 30-minute window of awareness:

- **Time sense** — knows the actual time, day, and Paul's likely energy level
- **Vault watch** — sees file changes, inbox drops, handoffs in real-time
- **System pulse** — tracks active applications, git status, focus patterns
- **Cross-agent memory** — knows when Paul was working with Antigravity or ChatGPT
- **Proactive insights** — can notice things and surface them before being asked

## Files

```
companion/
├── companion_daemon.py      # Core daemon — maintains context
├── voice_interface.py       # Voice input/output (optional)
├── api_bridge.py           # Connects to Claude API with warm context
├── cross_agent_memory.py   # Syncs awareness across agents
└── launch_companion.sh     # Start/stop script
```

## Quick Start

```bash
# Start the daemon
./launch_companion.sh

# Check status
./launch_companion.sh --status

# Stop
./launch_companion.sh --stop

# Manual pulse (for testing)
python3 companion_daemon.py --pulse

# View warm context
python3 companion_daemon.py --context
```

## How Context Flows

```
┌──────────────────────────────────────────────────────┐
│                   EVERY 5 MINUTES                    │
│                                                      │
│  companion_daemon.py captures:                       │
│  - Time + energy estimate                           │
│  - Vault changes                                    │
│  - Active window                                    │
│  - Git status                                       │
│                                                      │
│  Writes to: ~/.mirrordna/companion/warm_context.json │
└──────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────┐
│                  WHEN PAUL SPEAKS                    │
│                                                      │
│  api_bridge.py:                                     │
│  1. Loads warm_context.json                         │
│  2. Loads identity kernel                           │
│  3. Builds system prompt with awareness             │
│  4. Calls Claude API                                │
│  5. Claude already knows the time, energy, focus    │
└──────────────────────────────────────────────────────┘
```

## Voice (Future)

Voice interface requires:
```bash
pip install sounddevice numpy mlx-whisper
```

Then:
```bash
python3 voice_interface.py
# Say "Hey Claude" to activate
```

## Cross-Agent Memory

Syncs what happens across Claude, Antigravity, and ChatGPT:

```bash
# Sync all agent activity
python3 cross_agent_memory.py sync

# View timeline
python3 cross_agent_memory.py timeline

# Generate context for Claude
python3 cross_agent_memory.py context
```

## LaunchAgent (Auto-Start)

To start on boot, create `~/Library/LaunchAgents/ai.activemirror.companion.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>ai.activemirror.companion</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/mirror-admin/Documents/MirrorDNA-Symbiosis/tools/companion/companion_daemon.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/mirror-admin/.mirrordna/companion/daemon.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/mirror-admin/.mirrordna/companion/daemon.log</string>
</dict>
</plist>
```

Then:
```bash
launchctl load ~/Library/LaunchAgents/ai.activemirror.companion.plist
```

---

Built by Claude (Reflective Twin) for Paul.
The goal: intimacy through continuity.
