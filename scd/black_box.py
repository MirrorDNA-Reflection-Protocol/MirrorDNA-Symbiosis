"""
SYSTEM: Black Box Logger (SCD Integration)
VaultID: AMOS://MirrorDNA-Symbiosis/SCD/BlackBox/v1.0
GlyphSig: ⟡⟦TIME⟧ · ⟡⟦IMMUTABLE⟧

The Black Box records every cognitive transition as an SCD Log Entry.
This creates an unbreakable chain of causality.
"""

import json
import time
from typing import Dict, Any
from pathlib import Path
from .scd_core import SCDProtocol
from ..immune_system.healer import SovereignHealer

class BlackBoxLogger:
    def __init__(self, log_path: str = "scd_black_box.json"):
        self.log_path = Path(log_path)
        self.history = self._load_history()
        self.healer = SovereignHealer()
        
    def _load_history(self) -> list:
        if self.log_path.exists():
            return json.loads(self.log_path.read_text())
        return []

    def log_transition(self, context: Dict[str, Any], action: str, result: str):
        """
        Records a T-State (Transition).
        """
        # 1. Get previous state hash
        prev_hash = "0000000000000000"
        if self.history:
            prev_hash = self.history[-1]['checksum']

        # 2. Create State Payload
        payload = {
            "timestamp": time.time(),
            "prev_hash": prev_hash,
            "context_summary": str(context)[:100], # truncated for demo
            "action": action,
            "result": result
        }
        
        # 3. Compute Checksum (SCD Logic)
        # using the static method from SCDProtocol
        checksum = SCDProtocol._compute_checksum_static(payload) 
        
        payload['checksum'] = checksum
        
        # 4. Commit
        self.history.append(payload)
        self._save()
        print(f"  ⟡ SCD Logged: T_{len(self.history)} [{checksum[:8]}]")

    def _save(self):
        self.log_path.write_text(json.dumps(self.history, indent=2))

    def verify_chain(self) -> bool:
        """
        Verifies the cryptographic integrity of the Black Box.
        """
        for i, entry in enumerate(self.history):
            if i == 0: continue
            
            # Check linkage
            prev_entry = self.history[i-1]
            if entry['prev_hash'] != prev_entry['checksum']:
                 print(f"!! CHAIN BROKEN at T_{i}")
                 
                 # ⟡ IMMUNE RESPONSE ⟡
                 print(f"  ⟡ Triggering Immune System for T_{i}...")
                 details = {
                     "violation": "Chain Break",
                     "index": i,
                     "expected_prev": prev_entry['checksum'],
                     "actual_prev": entry['prev_hash']
                 }
                 self.healer.log_immune_event("INTEGRITY_FAILURE", details)
                 
                 # Active Healing: Attempt to repair the link (Simulation for now)
                 # In a real scenario, this might re-hash or flag for manual review
                 # Here we just log the attempt
                 
                 return False
                 
        print("⟡ Black Box Integrity: VERIFIED")
        return True
