"""
verify_immune_response.py

Test script to verify that the MirrorDNA Immune System triggers
when the SCD Black Box chain is corrupted.
"""

import json
import time
from pathlib import Path
from scd.black_box import BlackBoxLogger

def main():
    print("⟡ STARTING IMMUNE RESPONSE VERIFICATION ⟡")
    
    # 1. Setup clean state
    log_path = Path("scd_black_box_test.json")
    if log_path.exists():
        log_path.unlink()
        
    logger = BlackBoxLogger(log_path=str(log_path))
    
    # 2. Create valid chain
    print("  Creating valid chain...")
    logger.log_transition({"user": "paul"}, "INITIALIZE", "SUCCESS")
    logger.log_transition({"user": "paul"}, "COMMAND", "EXECUTE_HEALER")
    logger.log_transition({"user": "paul"}, "SHUTDOWN", "OK")
    
    # Verify valid chain
    print("  Verifying valid chain...")
    if not logger.verify_chain():
        print("  ❌ Setup failed: Chain should be valid")
        return
        
    # 3. Corrupt the chain
    print("  Corrupting chain manually...")
    history = json.loads(log_path.read_text())
    # Modify T_1's checksum so T_2's prev_hash pointer is now invalid
    history[1]['checksum'] = "CORRUPTED_HASH_VALUE_000000"
    log_path.write_text(json.dumps(history))
    
    # 4. Reload and Verify - Expect Immune Trigger
    print("  Verifying corrupted chain (Expecting Immune Response)...")
    logger_corrupt = BlackBoxLogger(log_path=str(log_path))
    result = logger_corrupt.verify_chain()
    
    if not result:
        print("  ✓ Chain validation failed as expected.")
        print("  ✓ Check output above for '⟡ IMMUNE RESPONSE ⟡'")
    else:
        print("  ❌ Error: Chain verification passed (should fail)")

    # Cleanup
    if log_path.exists():
        log_path.unlink()

if __name__ == "__main__":
    main()
