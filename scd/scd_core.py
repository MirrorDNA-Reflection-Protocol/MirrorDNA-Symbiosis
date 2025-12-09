"""
Core SCD Protocol Implementation

Provides deterministic state management with ASHA-256 checksumming.
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class SCDProtocol:
    """
    Structured Contextual Distillation Protocol
    
    Provides deterministic, verifiable state transitions for AI conversations.
    
    Features:
    - ASHA-256 checksumming (Alphabetically Sorted Hashing Algorithm)
    - Atomic state updates via supersede()
    - Drift detection
    - Cross-vendor handoff support
    
    Example:
        >>> scd = SCDProtocol()
        >>> scd.supersede({"project": "MyApp", "mode": "production"})
        >>> print(scd.get_checksum())
        ASHA-256:abc123...
    """
    
    def __init__(self, state_file: Optional[str] = None):
        """
        Initialize SCD Protocol
        
        Args:
            state_file: Path to JSON state file (optional)
        """
        self.state_file = Path(state_file) if state_file else None
        self.current_state = self._load_state()
    
    def _load_state(self) -> Dict[str, Any]:
        """Load state from file or create genesis state"""
        if self.state_file and self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    # Verify loaded state
                    if self.verify_checksum(state):
                        return state
                    else:
                        logger.warning("Loaded state failed checksum verification, using genesis")
            except Exception as e:
                logger.error(f"Failed to load state: {e}")
        
        # Genesis state
        return {
            "version": "1.0.0",
            "turn": 0,
            "state": {},
            "checksum": "GENESIS"
        }
    
    def save_state(self) -> None:
        """Persist current state to file"""
        if not self.state_file:
            return
            
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(self.current_state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def compute_checksum(self, state_dict: Dict[str, Any]) -> str:
        """
        Compute ASHA-256 checksum
        
        ASHA-256 = Alphabetically Sorted Hashing Algorithm using SHA-256
        Ensures deterministic hashing regardless of key order.
        
        Args:
            state_dict: State dictionary to hash
            
        Returns:
            Checksum string in format "ASHA-256:hexdigest"
        """
        state_json = json.dumps(state_dict, sort_keys=True).encode('utf-8')
        sha256_hash = hashlib.sha256(state_json).hexdigest()
        return f"ASHA-256:{sha256_hash}"
    
    def supersede(self, deltas: Dict[str, Any]) -> Dict[str, Any]:
        """
        Atomically apply state updates
        
        Updates are applied to a copy of current state, then checksummed.
        Setting a value to None removes that key.
        
        Args:
            deltas: Dictionary of updates {key: value}
                   value=None deletes the key
        
        Returns:
            New complete state dictionary
            
        Example:
            >>> scd.supersede({"mode": "production", "debug": None})
            # Sets mode=production, removes debug key
        """
        # Copy current inner state
        prev_inner_state = self.current_state.get("state", {})
        new_inner_state = prev_inner_state.copy()
        
        # Apply deltas
        for key, value in deltas.items():
            if value is None:
                new_inner_state.pop(key, None)
            else:
                new_inner_state[key] = value
        
        # Compute new checksum
        new_checksum = self.compute_checksum(new_inner_state)
        
        # Build new full state
        new_full_state = {
            "version": self.current_state.get("version", "1.0.0"),
            "turn": self.current_state.get("turn", 0) + 1,
            "state": new_inner_state,
            "checksum": new_checksum
        }
        
        self.current_state = new_full_state
        self.save_state()
        
        return new_full_state
    
    def get_state(self) -> Dict[str, Any]:
        """Get current complete state"""
        return self.current_state.copy()
    
    def get_checksum(self) -> str:
        """Get current state checksum"""
        return self.current_state.get("checksum", "GENESIS")
    
    def get_turn(self) -> int:
        """Get current turn number"""
        return self.current_state.get("turn", 0)
    
    def get_context_string(self) -> str:
        """
        Format state for LLM context injection
        
        Returns formatted string suitable for including in system prompts.
        
        Example output:
            [SCD STATE]
            Turn: 5
            Checksum: ASHA-256:abc123...
            State: {"project": "MyApp"}
        """
        s = self.current_state
        state_str = json.dumps(s.get("state", {}), indent=2)
        return f"""[SCD STATE]
Turn: {s.get('turn', 0)}
Checksum: {s.get('checksum', 'GENESIS')}
State: {state_str}
"""
    
    @staticmethod
    def verify_checksum(state: Dict[str, Any]) -> bool:
        """
        Verify state checksum is valid
        
        Recomputes checksum from state and compares to stored checksum.
        Detects drift/tampering.
        
        Args:
            state: Complete state dictionary
            
        Returns:
            True if checksum matches, False otherwise
        """
        if state.get("checksum") == "GENESIS":
            return True  # Genesis state has no computed checksum
            
        inner_state = state.get("state", {})
        expected_checksum = SCDProtocol._compute_checksum_static(inner_state)
        actual_checksum = state.get("checksum", "")
        
        return expected_checksum == actual_checksum
    
    @staticmethod
    def _compute_checksum_static(state_dict: Dict[str, Any]) -> str:
        """Static version of compute_checksum for verification"""
        state_json = json.dumps(state_dict, sort_keys=True).encode('utf-8')
        sha256_hash = hashlib.sha256(state_json).hexdigest()
        return f"ASHA-256:{sha256_hash}"
    
    def export_state(self) -> str:
        """
        Export state as JSON string for cross-vendor handoff
        
        Returns:
            JSON string representation of current state
        """
        return json.dumps(self.current_state, indent=2)
    
    def import_state(self, state_json: str) -> bool:
        """
        Import state from JSON string (cross-vendor handoff)
        
        Verifies checksum before accepting state.
        
        Args:
            state_json: JSON string containing state
            
        Returns:
            True if import successful, False if verification failed
        """
        try:
            state = json.loads(state_json)
            if self.verify_checksum(state):
                self.current_state = state
                self.save_state()
                return True
            else:
                logger.error("Import failed: checksum verification failed")
                return False
        except Exception as e:
            logger.error(f"Import failed: {e}")
            return False
