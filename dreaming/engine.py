"""
dreaming/engine.py

The Dreaming Engine
v1.0 (Genesis)

An autonomous regenerative loop that runs during system downtime.
It replays logs, identifies entropy, and uses the Immune System to evolve.
"""
import sys
import json
import time
import logging
from pathlib import Path
from typing import List, Dict, Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from immune_system.healer import SovereignHealer
from scd.black_box import BlackBoxLogger

# Configure Logging
VAULT_LOG_DIR = Path("/Users/mirror-admin/Documents/MirrorDNA-Vault/ActiveMirrorOS/Logs")
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(VAULT_LOG_DIR / "dream_engine.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("dream_engine")

class DreamEngine:
    def __init__(self):
        self.healer = SovereignHealer()
        self.black_box = BlackBoxLogger()
        self.dream_log_path = VAULT_LOG_DIR / "dream_journal.json"

    def enter_rem_cycle(self):
        """
        The Rapid Evolution Mode (REM) Cycle.
        Triggers the nightly optimization loop.
        """
        logger.info("⟡ ENTERING THE DREAMING... ⟡")
        
        # 1. Reverie: Replay recent events
        recent_memories = self._reverie()
        if not recent_memories:
            logger.info("  No new memories to dream about. Waking up.")
            return

        # 2. Lucidity: Identify optimization targets
        targets = self._lucidity(recent_memories)
        
        # 3. Synthesis: Apply active healing/optimization
        self._synthesis(targets)
        
        logger.info("⟡ WAKING UP. DREAM CYCLE COMPLETE. ⟡")

    def _reverie(self) -> List[Dict[str, Any]]:
        """Replays logs to find context."""
        logger.info("  Phase 1: Reverie (Log Replay)")
        # We need to expose a method in BlackBox to get recent entries
        entries = self.black_box.get_recent_entries(limit=50)
        logger.info(f"  Replaying {len(entries)} events...")
        return entries

    def _lucidity(self, memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identifies entropy or inefficiencies."""
        logger.info("  Phase 2: Lucidity (Entropy Detection)")
        targets = []
        
        # Simple heuristic: Identify "Error" or "Correction" events
        for mem in memories:
            if "violation" in str(mem).lower() or "error" in str(mem).lower():
                targets.append(mem)
                
        logger.info(f"  Identified {len(targets)} optimization targets.")
        return targets

    def _synthesis(self, targets: List[Dict[str, Any]]):
        """Uses Healer to optimize."""
        logger.info("  Phase 3: Synthesis (Active Evolution)")
        
        for target in targets:
            logger.info(f"  Optimizing target T_{target.get('timestamp')}...")
            # In a real scenario, we would locate the source file and optimize it.
            # Here we simulate the dream logic.
            
            # Context for the Healer
            context = f"Optimize response to error event: {target.get('action')}"
            
            # We treat the 'result' as the content to optimize
            content_to_fix = str(target.get('result', ''))
            
            if content_to_fix:
                improved = self.healer.heal_content(content_to_fix, context)
                self._log_dream(target, improved)

    def _log_dream(self, original: Dict, improved: str):
        """Records the dream outcome."""
        entry = {
            "timestamp": time.time(),
            "original_event": original,
            "dream_optimization": improved
        }
        
        dreams = []
        if self.dream_log_path.exists():
            dreams = json.loads(self.dream_log_path.read_text())
            
        dreams.append(entry)
        self.dream_log_path.write_text(json.dumps(dreams, indent=2))
        logger.info("  Dream recorded in journal.")

if __name__ == "__main__":
    engine = DreamEngine()
    engine.enter_rem_cycle()
