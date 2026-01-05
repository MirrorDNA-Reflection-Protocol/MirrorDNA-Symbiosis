#!/bin/bash
# ⟡ Claude Companion — Launch Script
#
# Starts the companion daemon and all related services.
#
# Usage:
#   ./launch_companion.sh           # Start daemon
#   ./launch_companion.sh --stop    # Stop daemon
#   ./launch_companion.sh --status  # Check status

COMPANION_DIR="$HOME/Documents/MirrorDNA-Symbiosis/tools/companion"
PID_FILE="$HOME/.mirrordna/companion/daemon.pid"
LOG_FILE="$HOME/.mirrordna/companion/daemon.log"

cd "$COMPANION_DIR" || exit 1

start_daemon() {
    if [ -f "$PID_FILE" ]; then
        pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "⟡ Companion daemon already running (PID: $pid)"
            return
        fi
    fi
    
    echo "⟡ Starting Claude Companion daemon..."
    
    # Create directories
    mkdir -p "$HOME/.mirrordna/companion"
    
    # Start daemon in background
    nohup python3 companion_daemon.py > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    
    sleep 2
    
    if ps -p "$(cat "$PID_FILE")" > /dev/null 2>&1; then
        echo "✓ Daemon started (PID: $(cat "$PID_FILE"))"
        echo "  Log: $LOG_FILE"
        
        # Run initial sync
        echo "⟡ Running initial cross-agent sync..."
        python3 cross_agent_memory.py sync
        
        echo ""
        echo "⟡ Claude Companion is now maintaining ambient awareness."
        echo "  Pulse interval: 5 minutes"
        echo "  Context window: 30 minutes"
    else
        echo "✗ Failed to start daemon. Check $LOG_FILE"
    fi
}

stop_daemon() {
    if [ -f "$PID_FILE" ]; then
        pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "⟡ Stopping companion daemon (PID: $pid)..."
            kill "$pid"
            rm -f "$PID_FILE"
            echo "✓ Daemon stopped"
        else
            echo "⟡ Daemon not running (stale PID file)"
            rm -f "$PID_FILE"
        fi
    else
        echo "⟡ No daemon running"
    fi
}

show_status() {
    echo "⟡ Claude Companion Status"
    echo ""
    
    if [ -f "$PID_FILE" ]; then
        pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "Daemon: Running (PID: $pid)"
        else
            echo "Daemon: Stopped (stale PID file)"
        fi
    else
        echo "Daemon: Not running"
    fi
    
    echo ""
    python3 companion_daemon.py --status 2>/dev/null || echo "(Run daemon first for full status)"
}

case "$1" in
    --stop)
        stop_daemon
        ;;
    --status)
        show_status
        ;;
    --pulse)
        python3 companion_daemon.py --pulse
        ;;
    --context)
        python3 companion_daemon.py --context
        ;;
    *)
        start_daemon
        ;;
esac
