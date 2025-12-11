#!/bin/bash
# The Dreaming — Nightly Optimization Loop
# Runs at 3:15 AM after daily snapshot

cd /Users/mirror-admin/Documents/MirrorDNA-Symbiosis
source ~/.zshrc 2>/dev/null

echo "⟡ $(date): ENTERING THE DREAMING..."

# Run the dream engine
python3 dreaming/engine.py

echo "⟡ $(date): DREAM CYCLE COMPLETE"
