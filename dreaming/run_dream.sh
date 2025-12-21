#!/bin/bash
# The Dreaming — Nightly Optimization Loop
# Runs at 3:15 AM after daily snapshot

cd /Users/mirror-admin/Documents/MirrorDNA-Symbiosis
source ~/.zshrc 2>/dev/null

echo "⟡ $(date): ENTERING THE DREAMING..."

# 1. Run the dream engine (Internal Reflection)
python3 dreaming/engine.py

# 2. Run Project REVELATION (External Synthesis)
# Detects gaps and prepares knowledge files
python3 /Users/mirror-admin/Documents/GitHub/MirrorBrain-Setup/revelation.py

# 3. Run Project GENESIS (Weight Evolution)
# Merges new knowledge/dreams and triggers LoRA
python3 /Users/mirror-admin/Documents/GitHub/MirrorBrain-Setup/self_evolve.py

echo "⟡ $(date): DREAM CYCLE COMPLETE"
