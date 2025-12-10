#!/usr/bin/env python3
"""
⟡ GENESIS PERFECTION: THE HUNDRED FOLD PATH ⟡
---------------------------------------------
Systematic, recursive code perfection engine.
Iterates through the codebase, applying rigor and type safety.
"""

import sys
import time
import random
import requests
import subprocess
from pathlib import Path

# Config
TARGET_REPO = Path(".").absolute()
PROXY_URL = "http://localhost:5500/v1/chat/completions" 
MODEL = "qwen2.5:7b"
MAX_CYCLES = 100

def get_target_files():
    # Exclusion list to avoid destroying the tools themselves while running
    excludes = ["genesis_prime.py", "genesis_perfection.py", "red_team_adversary.py"]
    files = [p for p in TARGET_REPO.rglob("*.py") if p.name not in excludes and "venv" not in str(p)]
    return sorted(files)

def optimize_code(file_path):
    print(f"\n⟡ OPTIMIZING: {file_path.name}")
    original_code = file_path.read_text()
    
    prompt = f"""
    You are the MirrorDNA Architect. Your goal is PERFECTION.
    Refactor the following Python code to meet these standards:
    1. STRICT TYPE HINTING (Use typing.List, typing.Dict, etc.)
    2. COMPREHENSIVE DOCSTRINGS (Google Style)
    3. ROBUST ERROR HANDLING
    4. PEP8 COMPLIANCE
    
    Do not remove functionality. Only enhance.
    
    FILE: {file_path.name}
    CODE:
    {original_code}
    
    Return ONLY the new code block enclosed in ```python ... ```.
    """
    
    try:
        resp = requests.post(PROXY_URL, json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        })
        resp.raise_for_status()
        
        content = resp.json()['choices'][0]['message']['content']
        if "```python" in content:
            # Extract code carefully
            new_code = content.split("```python")[1].split("```")[0].strip()
            
            # Validation: Check if it compiles
            try:
                compile(new_code, file_path.name, 'exec')
            except SyntaxError as e:
                print(f"  ✕ Syntax Error in Evolution: {e}")
                return False

            # Commit Change
            file_path.write_text(new_code)
            print("  ✓ Optimization Applied.")
            return True
        else:
            print("  ✕ No code block returned.")
            
    except Exception as e:
        print(f"  ✕ Evolution Error: {e}")
        return False
        
    return False

def run_perfection():
    print("⟡ GENESIS PERFECTION ONLINE.")
    print(f"Target: {TARGET_REPO}")
    print(f"Goal: {MAX_CYCLES} Recursions")
    
    targets = get_target_files()
    cycle = 0
    
    while cycle < MAX_CYCLES:
        for t in targets:
            cycle += 1
            if cycle > MAX_CYCLES: break
            
            print(f"\n[RECURSION {cycle}/{MAX_CYCLES}]")
            if optimize_code(t):
                # Auto-Commit
                subprocess.call(["git", "add", str(t)])
                subprocess.call(["git", "commit", "-m", f"perfection: Cycle {cycle} ({t.name})"])
            
            # Brief pause to let the proxy breathe
            time.sleep(1)

    print("\n" + "="*40)
    print(f"PERFECTION CYCLE COMPLETE.")
    print("="*40)

if __name__ == "__main__":
    run_perfection()
