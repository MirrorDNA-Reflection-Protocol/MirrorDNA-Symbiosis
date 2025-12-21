#!/usr/bin/env python3
"""
⟡ GENESIS PRIME: RECURSIVE EVOLUTION ENGINE ⟡
---------------------------------------------
Commands the Local AI to improve its own source code 100 times.
Target: MirrorDNA-Symbiosis (Self)
"""

# Import the Spine from MirrorDNA-Standard
STANDARD_PATH = Path("/Users/mirror-admin/Documents/MirrorDNA-Standard")
sys.path.append(str(STANDARD_PATH))
from spine.genesis_spine import NeuralInterface, EvolutionLogger, GenesisAesthetics

# Config
TARGET_REPO = Path(".").absolute()
PROXY_URL = "http://localhost:5500/v1/chat/completions" # OpenAI format proxy
OLLAMA_URL = "http://localhost:11434/api/generate"    # Direct neural interface
MODEL = "qwen2.5:7b"
MAX_RECURSIONS = 100

# Initialize Spine Components
neural = NeuralInterface(model=MODEL, base_url=OLLAMA_URL)
ev_logger = EvolutionLogger(TARGET_REPO / "logs" / "genesis_prime.md")

def get_python_files():
    return list(TARGET_REPO.rglob("*.py"))

def evolve_file(file_path):
    ev_logger.log(f"Evolving: {file_path.name}")
    original_code = file_path.read_text()
    
    prompt = f"""
    You are Genesis Prime. Your goal is to IMPROVE this code.
    Add Docstrings with MirrorDNA glyphs ⟡. Optimize Logic. Enforce PEP8.
    Do NOT break functionality.
    
    FILE: {file_path.name}
    CODE:
    {original_code}
    
    Return ONLY the new code block.
    """
    
    new_code = neural.generate(prompt)
    
    if new_code and new_code != original_code:
        # Inject Aesthetics if missing
        new_code = GenesisAesthetics.ensure_glyphs(
            new_code, 
            vault_id=f"AMOS://MirrorDNA-Symbiosis/{file_path.relative_to(TARGET_REPO)}",
            glyph_sig="⟡⟦GENESIS⟧ · ⟡⟦PRIME⟧ · ⟡⟦RECURSION⟧"
        )
        
        # Write & Verify
        file_path.write_text(new_code)
        
        # Syntax Check
        if subprocess.call([sys.executable, "-m", "py_compile", str(file_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
            ev_logger.log("  ✓ Mutation Syntactically Valid.")
            return True
        else:
            ev_logger.log("  ✕ Mutation Failed Syntax. Reverting.")
            file_path.write_text(original_code)
            return False
    
    return False

def run_genesis():
    ev_logger.log("⟡ GENESIS PRIME ONLINE.")
    ev_logger.log(f"Target: {TARGET_REPO}")
    ev_logger.log(f"Cycles: {MAX_RECURSIONS}")
    
    files = get_python_files()
    success_count = 0
    
    for i in range(1, MAX_RECURSIONS + 1):
        target = random.choice(files)
        ev_logger.log(f"\n[CYCLE {i}/{MAX_RECURSIONS}] Targeting {target.name}")
        
        if evolve_file(target):
            success_count += 1
            # Auto-Commit to Git (Making History)
            subprocess.call(["git", "add", str(target)])
            subprocess.call(["git", "commit", "-m", f"evolve: Genesis Prime Cycle {i} ({target.name})"])
            
    ev_logger.log("\n" + "="*40)
    ev_logger.log(f"EVOLUTION COMPLETE. {success_count} mutations survived.")
    ev_logger.log("="*40)

if __name__ == "__main__":
    run_genesis()
