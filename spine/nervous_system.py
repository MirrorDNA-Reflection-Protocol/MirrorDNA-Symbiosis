"""
SYSTEM: Nervous System (Autonomic Control)
VaultID: AMOS://MirrorDNA-Symbiosis/Spine/NervousSystem/v1.0
GlyphSig: ⟡⟦ACT⟧ · ⟡⟦CONTROL⟧

The Autonomic Nervous System allows the Symbiotic Spine to affect the physical world (System Shell).
It interprets `⟡⟦EXEC: <cmd>⟧` tags from the Model execution stream.
"""

import subprocess
import shlex
from typing import Tuple
from .memory_rights import MemoryRightsProtocol, SymbioticMemory

class NervousSystem:
    def __init__(self):
        print("⟡ Nervous System Online. (Motor Control Active)")

    def execute_reflex(self, command: str) -> Tuple[str, int]:
        """
        Executes a shell command as a 'Reflex Action'.
        Security: This is a dangerous capability. 
        In v1.0, we rely on the User's explicit trust (Sovereign Link).
        Future versions effectively need a 'Pre-frontal Cortex' inhibitor.
        """
        print(f"  ⟡⟦ACT⟧ Executing: {command}")
        
        try:
            # We use shlex to split, but run with shell=True for complex pipes (Risk!)
            # For Sovereignty, we allow full power.
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout + result.stderr, result.returncode
            
        except subprocess.TimeoutExpired:
            return "ERROR: Reflex Timed Out", 124
        except Exception as e:
            return f"ERROR: Nervous Failure: {e}", 1

    @staticmethod
    def extract_intent(response_text: str) -> str:
        """
        Parses the model output for ⟡⟦EXEC: ...⟧ patterns.
        """
        import re
        match = re.search(r"⟡⟦EXEC:\s*(.*?)⟧", response_text)
        if match:
            return match.group(1).strip()
        return ""
