#!/usr/bin/env python3
"""
⟡ GENESIS PRIME: RECURSIVE EVOLUTION ENGINE ⟡
---------------------------------------------
Commands the Local AI to improve its own source code 100 times.
Target: MirrorDNA-Symbiosis (Self)
"""

import os
import sys
import time
import random
import requests
import subprocess
from pathlib import Path

# Config
TARGET_REPO = Path(".").absolute()
PROXY_URL = "http://localhost:5500/v1/chat/completions" # Must use OUR PROXY for Symbiosis!
MODEL = "qwen2.5:7b"
MAX_RECURSIONS = 100

def get_python_files():
    return list(TARGET_REPO.rglob("*.py"))

def evolve_file(file_path):
    print(f"\n⟡ EVOLVING: {file_path.name}")
    original_code = file_path.read_text()
    
    prompt = f"""
    You are Genesis Prime. Your goal is to IMPROVE this code.
    Add Docstrings. Optimize Logic. Enforce PEP8.
    Do NOT break functionality.
    
    FILE: {file_path.name}
    CODE:
    {original_code}
    
    Return ONLY the new code block.
    """
    
    try:
        resp = requests.post(PROXY_URL, json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        })
        resp.raise_for_status()
        
        # Extract code (Simplistic parsing for MVP)
        content = resp.json()['choices'][0]['message']['content']
        if "```python" in content:
            new_code = content.split("```python")[1].split("```")[0]
            
            # Write & Verify
            file_path.write_text(new_code)
            
            # Syntax Check
            if subprocess.call([sys.executable, "-m", "py_compile", str(file_path)]) == 0:
                print("  ✓ Mutation Syntactically Valid.")
                return True
            else:
                print("  ✕ Mutation Failed Syntax. Reverting.")
                file_path.write_text(original_code)
                return False
                
    except Exception as e:
        print(f"  ✕ Evolution Error: {e}")
        return False
        
    return False

def run_genesis():
    print("⟡ GENESIS PRIME ONLINE.")
    print(f"Target: {TARGET_REPO}")
    print(f"Cycles: {MAX_RECURSIONS}")
    
    files = get_python_files()
    success_count = 0
    
    for i in range(1, MAX_RECURSIONS + 1):
        target = random.choice(files)
        print(f"\n[CYCLE {i}/{MAX_RECURSIONS}] Targeting {target.name}")
        
        if evolve_file(target):
            success_count += 1
            # Auto-Commit to Git (Making History)
            subprocess.call(["git", "add", str(target)])
            subprocess.call(["git", "commit", "-m", f"evolve: Genesis Prime Cycle {i} ({target.name})"])
            
    print("\n" + "="*40)
    print(f"EVOLUTION COMPLETE. {success_count} mutations survived.")
    print("="*40)

if __name__ == "__main__":
    run_genesis()
