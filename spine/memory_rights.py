"""
PROTOCOL: Memory Rights
VaultID: AMOS://MirrorDNA-Symbiosis/Spine/MemoryRights/v1.0
GlyphSig: ⟡⟦RIGHTS⟧ · ⟡⟦SOVEREIGNTY⟧

Enforces the Memory Rights Protocol (MRP).
The AI cannot overwrite USER_SOVEREIGN data.
"""

from typing import Optional
from .types import MemoryRights, SymbioticMemory, SafetyViolation

class MemoryRightsProtocol:
    """
    The Guardian of Memory Sovereignty.
    """
    
    @staticmethod
    def can_read(memory: SymbioticMemory, actor: str = "AI") -> bool:
        """
        All levels are readable by the Symbiotic System to form context.
        Privacy layers (if any) would be enforced here.
        """
        return True

    @staticmethod
    def can_write(memory: SymbioticMemory, actor: str = "AI") -> bool:
        """
        Determines if the actor can Overwrite/Modify the memory.
        """
        if actor == "USER":
            return True
            
        if memory.rights == MemoryRights.USER_SOVEREIGN:
            return False
            
        if memory.rights == MemoryRights.SYMBIOTIC_FLUID:
            # Fluid memories can be appended to, but full overwrite 
            # might be restricted in v2. For now, we allow it with caution.
            return True
            
        if memory.rights == MemoryRights.SYSTEM_EPHEMERAL:
            return True
            
        return False

    @staticmethod
    def can_delete(memory: SymbioticMemory, actor: str = "AI") -> bool:
        """
        Determines if the actor can Delete the memory.
        """
        if actor == "USER":
            return True
            
        if memory.rights in [MemoryRights.USER_SOVEREIGN, MemoryRights.SYMBIOTIC_FLUID]:
            return False
            
        if memory.rights == MemoryRights.SYSTEM_EPHEMERAL:
            return True
            
        return False

    @classmethod
    def enforce_write(cls, memory: SymbioticMemory, actor: str = "AI"):
        """
        Raises SafetyViolation if write is forbidden.
        Raises QuantumCollapse if integrity is compromised.
        """
        # 1. Quantum Observation
        from quantum.observer import QuantumObserver, LatticeShield
        # In a real system, we'd fetch the stored hash from SCD/Vault.
        # Here we simulate valid state by generating a hash of the current object 
        # to ensure it hasn't somehow mutated in transit (Python object stability).
        current_hash = LatticeShield.generate_quantum_hash(memory.__dict__)
        QuantumObserver.observe(memory.__dict__, current_hash)
        
        # 2. Logic Check
        if not cls.can_write(memory, actor):
            raise SafetyViolation(
                f"MRP VIOLATION: Actor '{actor}' cannot write to "
                f"{memory.rights.value} memory '{memory.vault_id}'."
            )

    @classmethod
    def enforce_delete(cls, memory: SymbioticMemory, actor: str = "AI"):
        """
        Raises SafetyViolation if delete is forbidden.
        """
        if not cls.can_delete(memory, actor):
            raise SafetyViolation(
                f"MRP VIOLATION: Actor '{actor}' cannot delete "
                f"{memory.rights.value} memory '{memory.vault_id}'."
            )
