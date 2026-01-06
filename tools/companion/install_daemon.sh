#!/bin/bash
# ⟡ MirrorOS Daemon — Installation Script
#
# Installs the unified daemon as a LaunchAgent
# that starts on boot and auto-restarts on crash.
#
# Usage:
#   ./install_daemon.sh           # Install and start
#   ./install_daemon.sh --uninstall # Remove

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_NAME="ai.mirroros.daemon.plist"
PLIST_SRC="${SCRIPT_DIR}/${PLIST_NAME}"
PLIST_DST="$HOME/Library/LaunchAgents/${PLIST_NAME}"
LOG_DIR="$HOME/.mirrordna/daemon"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}✓${NC} $1"; }
log_warn() { echo -e "${YELLOW}⚠${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; }

uninstall() {
    echo "⟡ Uninstalling MirrorOS Daemon..."
    
    # Unload if running
    if launchctl list | grep -q "ai.mirroros.daemon"; then
        launchctl unload "$PLIST_DST" 2>/dev/null || true
        log_info "LaunchAgent unloaded"
    fi
    
    # Remove plist
    if [ -f "$PLIST_DST" ]; then
        rm -f "$PLIST_DST"
        log_info "Plist removed"
    fi
    
    # Remove lock file
    rm -f "$LOG_DIR/daemon.lock" 2>/dev/null || true
    
    log_info "Uninstall complete"
    exit 0
}

install() {
    echo "⟡ Installing MirrorOS Daemon v2.0..."
    echo ""
    
    # Check source exists
    if [ ! -f "$PLIST_SRC" ]; then
        log_error "Plist not found: $PLIST_SRC"
        exit 1
    fi
    
    # Check daemon script exists
    if [ ! -f "${SCRIPT_DIR}/daemon.py" ]; then
        log_error "Daemon script not found: ${SCRIPT_DIR}/daemon.py"
        exit 1
    fi
    
    # Create log directory
    mkdir -p "$LOG_DIR"
    log_info "Log directory: $LOG_DIR"
    
    # Unload existing if present
    if launchctl list | grep -q "ai.mirroros.daemon"; then
        log_warn "Existing daemon found, unloading..."
        launchctl unload "$PLIST_DST" 2>/dev/null || true
        sleep 1
    fi
    
    # Copy plist
    cp "$PLIST_SRC" "$PLIST_DST"
    log_info "Plist copied to ~/Library/LaunchAgents/"
    
    # Set permissions
    chmod 644 "$PLIST_DST"
    log_info "Permissions set (644)"
    
    # Remove stale lock
    rm -f "$LOG_DIR/daemon.lock" 2>/dev/null || true
    
    # Load agent
    launchctl load "$PLIST_DST"
    log_info "LaunchAgent loaded"
    
    # Wait and verify
    sleep 2
    
    if launchctl list | grep -q "ai.mirroros.daemon"; then
        STATUS=$(launchctl list | grep "ai.mirroros.daemon" | awk '{print $1}')
        if [ "$STATUS" = "-" ]; then
            log_info "Daemon registered (waiting to start)"
        else
            log_info "Daemon running (PID: $STATUS)"
        fi
    else
        log_error "Daemon failed to register"
        echo ""
        echo "Check logs:"
        echo "  tail -f $LOG_DIR/daemon.log"
        echo "  tail -f $LOG_DIR/daemon_error.log"
        exit 1
    fi
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⟡ MirrorOS Daemon Installed Successfully"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Commands:"
    echo "  python3 daemon.py --status   # Check status"
    echo "  python3 daemon.py --context  # View warm_context.json"
    echo "  python3 daemon.py --stop     # Stop daemon"
    echo ""
    echo "Logs:"
    echo "  tail -f $LOG_DIR/daemon.log"
    echo ""
    echo "Warm Context:"
    echo "  cat $LOG_DIR/warm_context.json"
    echo ""
}

# Main
if [ "$1" = "--uninstall" ] || [ "$1" = "-u" ]; then
    uninstall
else
    install
fi
