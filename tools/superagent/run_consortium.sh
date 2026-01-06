#!/bin/bash
# ⟡ Consortium Daily Wrapper
# Runs consortium digest with proper environment

cd ~/Documents/MirrorDNA-Symbiosis/tools/superagent

# Load environment
export PATH="/usr/bin:/bin:/usr/sbin:/sbin"

# Run consortium
/usr/bin/python3 consortium.py digest "Critical AI developments, releases, and risks in the last 24 hours." --email >> ~/Library/Logs/consortium_daily.log 2>&1
