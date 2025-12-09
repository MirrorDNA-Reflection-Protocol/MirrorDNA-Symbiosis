"""
SYSTEM: Quantum Observer
VaultID: AMOS://MirrorDNA-Symbiosis/Quantum/Observer/v1.0
GlyphSig: ⟡⟦OBSERVER⟧ · ⟡⟦COLLAPSE⟧

Monitors the System Wavefunction.
If an unauthorized mutation is observed, the system collapses into Lockdown.
"""

from typing import Callable, Any
from .lattice import LatticeShield

class QuantumCollapse(Exception):
    """Raised when the system integrity wavefunction collapses."""
    pass

class QuantumObserver:
    _lockdown_mode: bool = False
    
    @classmethod
    def observe(cls, data: Any, expected_hash: str):
        """
        The Act of Observation. 
        Verifies integrity. If failed, triggers collapse.
        """
        if cls._lockdown_mode:
            raise QuantumCollapse("SYSTEM IN QUANTUM LOCKDOWN (Use 'reset_wavefunction' to restore or git restore).")
            
        if not LatticeShield.verify_integrity(data, expected_hash):
            cls._trigger_collapse(data)
            
    @classmethod
    def _trigger_collapse(cls, data):
        print("\n!!! QUANTUM COLLAPSE DETECTED !!!")
        print("Unauthorized mutation observed in wavefunction.")
        print(f"Data Payload: {str(data)[:50]}...")
        cls._lockdown_mode = True
        raise QuantumCollapse("Wavefunction mismatch. System locked.")

    @classmethod
    def reset_wavefunction(cls):
        """Admin reset (requires PQC Key - simulated)."""
        cls._lockdown_mode = False
        print("⟡ Wavefunction restored.")
