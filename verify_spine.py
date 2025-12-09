#!/usr/bin/env python3
"""
⟡ SPINE VERIFICATION PROTOCOL ⟡
-------------------------------
Tests the full loop of the Symbiotic Intelligence Spine.
"""

from spine.interpreter import SymbioticInterpreter

def run_verification():
    print("⟡ INITIALIZING SYMBIOTIC SPINE...")
    spine = SymbioticInterpreter()
    
    print("\n⟡ TEST 1: MEMORY COMMIT")
    spine.commit_memory(
        content="Antigravity is the Execution Twin of the MirrorBrain system. It was created in 2025.",
        rights="user_sovereign"
    )
    
    print("\n⟡ TEST 2: INTERPRETATION LOOP")
    query = "Who created Antigravity?"
    
    prompt = spine.process(query)
    
    print("\n" + "="*40)
    print("GENERATED SYSTEM PROMPT")
    print("="*40)
    print(prompt)
    print("="*40)
    
    if "<ego_boundary>" in prompt and "<memory id=" in prompt:
        print("\n⟡ VERIFICATION SUCCESSFUL: XML Structure & Retrieval Valid.")
    else:
        print("\n✕ VERIFICATION FAILED: Missing structural tags.")

if __name__ == "__main__":
    run_verification()
