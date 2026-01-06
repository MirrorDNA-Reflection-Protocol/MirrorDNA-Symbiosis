#!/bin/bash
# ⟡ Claude Grounding Script
# Run at session start to establish reality anchor
#
# Usage: ./ground.sh
# Or:    source ground.sh (to export variables)

echo "⟡ GROUNDING SEQUENCE"
echo "━━━━━━━━━━━━━━━━━━━━"
echo ""

# 1. Current Time
echo "TIME:"
echo "  $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "  Hour: $(date '+%H') (24h)"
echo ""

# 2. Warm Context
WARM_CONTEXT="$HOME/.mirrordna/daemon/warm_context.json"
if [ -f "$WARM_CONTEXT" ]; then
    echo "WARM CONTEXT:"
    
    # Parse key fields
    USER_STATE=$(python3 -c "import json; d=json.load(open('$WARM_CONTEXT')); print(d.get('paul_state',{}).get('user_state','unknown'))" 2>/dev/null)
    ENERGY=$(python3 -c "import json; d=json.load(open('$WARM_CONTEXT')); print(d.get('paul_state',{}).get('time',{}).get('energy_estimate','unknown'))" 2>/dev/null)
    MODE=$(python3 -c "import json; d=json.load(open('$WARM_CONTEXT')); print(d.get('paul_state',{}).get('time',{}).get('mode_estimate','unknown'))" 2>/dev/null)
    ACTIVE_WINDOW=$(python3 -c "import json; d=json.load(open('$WARM_CONTEXT')); print(d.get('paul_state',{}).get('active_window','unknown'))" 2>/dev/null)
    LAST_UPDATED=$(python3 -c "import json; d=json.load(open('$WARM_CONTEXT')); print(d.get('meta',{}).get('last_updated','unknown')[:19])" 2>/dev/null)
    
    echo "  Paul State: $USER_STATE"
    echo "  Energy: $ENERGY"
    echo "  Mode: $MODE"
    echo "  Focus: $ACTIVE_WINDOW"
    echo "  Updated: $LAST_UPDATED"
else
    echo "WARM CONTEXT: Not available"
    echo "  (Daemon may not be running)"
fi
echo ""

# 3. Handoff State
HANDOFF="$HOME/.mirrordna/handoff.json"
if [ -f "$HANDOFF" ]; then
    echo "HANDOFF:"
    LAST_ACTION=$(python3 -c "import json; d=json.load(open('$HANDOFF')); print(d.get('last_action','none')[:60])" 2>/dev/null)
    PENDING=$(python3 -c "import json; d=json.load(open('$HANDOFF')); print(d.get('pending_items','none')[:60])" 2>/dev/null)
    echo "  Last: $LAST_ACTION"
    echo "  Pending: $PENDING"
else
    echo "HANDOFF: No active handoff"
fi
echo ""

# 4. Services
echo "SERVICES:"
# Ollama
if curl -s -o /dev/null -w "%{http_code}" http://localhost:11434/api/tags 2>/dev/null | grep -q "200"; then
    echo "  Ollama: ✓ up"
else
    echo "  Ollama: ✗ down"
fi

# MirrorBrain
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8081/health 2>/dev/null | grep -q "200"; then
    echo "  MirrorBrain: ✓ up"
else
    echo "  MirrorBrain: ✗ down"
fi

# Superagent
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8765/status 2>/dev/null | grep -q "200"; then
    echo "  Superagent: ✓ up"
else
    echo "  Superagent: ✗ down"
fi
echo ""

# 5. Daemon Status
DAEMON_STATE="$HOME/.mirrordna/daemon/daemon_state.json"
if [ -f "$DAEMON_STATE" ]; then
    DAEMON_PID=$(python3 -c "import json; d=json.load(open('$DAEMON_STATE')); print(d.get('pid','?'))" 2>/dev/null)
    if ps -p "$DAEMON_PID" > /dev/null 2>&1; then
        echo "DAEMON: Running (PID: $DAEMON_PID)"
    else
        echo "DAEMON: Stopped (stale state)"
    fi
else
    echo "DAEMON: Not running"
fi
echo ""

echo "━━━━━━━━━━━━━━━━━━━━"
echo "⟡ Grounding complete"
