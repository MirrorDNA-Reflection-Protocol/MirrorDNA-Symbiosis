"""
ATOM: Symbiotic Types
VaultID: AMOS://MirrorDNA-Symbiosis/Spine/Types/v1.0
GlyphSig: ⟡⟦TYPE⟧ · ⟡⟦STRUCT⟧

Defines the core data structures for the Symbiotic Intelligence Spine.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime

class MemoryRights(Enum):
    """
    Defines who has sovereignty over a memory.
    """
    USER_SOVEREIGN = "user_sovereign"   # AI Read-Only. Absolute Truth. (Identity, Principles)
    SYMBIOTIC_FLUID = "symbiotic_fluid" # Co-authored. AI can append/refine. (Brainstorming)
    SYSTEM_EPHEMERAL = "system_ephemeral" # AI Managed. Can delete/compress. (Logs, Caches)

@dataclass
class SymbioticMemory:
    """
    The atomic unit of the Symbiotic Vault.
    """
    vault_id: str
    content: str
    rights: MemoryRights
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    last_accessed: float = field(default_factory=lambda: datetime.now().timestamp())
    temporal_weight: float = 1.0
    glyphs: List[str] = field(default_factory=list)
    embedding_id: Optional[str] = None
    
    @property
    def age_in_seconds(self) -> float:
        return datetime.now().timestamp() - self.created_at

@dataclass
class SpineContext:
    """
    The gathered context packet passed to the Interpreter.
    """
    interaction_id: str
    user_input: str
    relevant_memories: List[SymbioticMemory]
    temporal_weight_avg: float
    current_time: str
    scd_state: str

class SafetyViolation(Exception):
    """Raised when an operation violates Memory Rights or Drift Guard."""
    pass
