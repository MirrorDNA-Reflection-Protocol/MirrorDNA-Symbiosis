"""
SYSTEM: Symbiotic Interpreter
VaultID: AMOS://MirrorDNA-Symbiosis/Spine/Interpreter/v1.0
GlyphSig: ⟡⟦BRAIN⟧ · ⟡⟦LOOP⟧

The Interpreter orchestrates the full symbiotic cycle:
input -> vam -> context -> decoder -> prompt
"""

import time
from typing import Dict, Any, List
from .vam import VaultAttentionMechanism
from .types import SymbioticMemory, MemoryRights
from codec.universal_decoder import UniversalDecoder
from scd.black_box import BlackBoxLogger
from .nervous_system import NervousSystem

class SymbioticInterpreter:
    def __init__(self):
        self.vam = VaultAttentionMechanism()
        self.decoder = UniversalDecoder()
        self.logger = BlackBoxLogger()
        self.nervous_system = NervousSystem()
        print("⟡ Symbiotic Interpreter Online.")

    def process(self, user_input: str) -> str:
        """
        The Thinking Loop.
        Returns the final prompt meant for the Model.
        """
        start_time = time.time()
        
        # 1. Attention Scan
        print(f"  ⟡ Scanning Vault for: '{user_input[:30]}...'")
        relevant_memories = self.vam.retrieve_context(user_input)
        print(f"  ⟡ Retrieved {len(relevant_memories)} active traces.")
        
        # 2. Decode to Prompt
        prompt = self.decoder.decode_context(user_input, relevant_memories)
        
        # 3. Log Thought
        self.logger.log_transition(
            context={"input": user_input, "memories": len(relevant_memories)},
            action="PROCESS",
            result="PROMPT_GENERATED"
        )
        
        return prompt

    def execute_and_learn(self, model_response: str):
        """
        Post-Processing Loop: Action & Memory.
        The Proxy calls this AFTER getting the response from Ollama.
        """
        # 1. Check for Action Intent
        cmd = self.nervous_system.extract_intent(model_response)
        if cmd:
            print(f"  ⟡ Action Detected: {cmd}")
            output, code = self.nervous_system.execute_reflex(cmd)
            
            # 2. Learn from Consequence
            # We commit the action and result to memory so the AI learns what happens.
            learn_content = f"ACTION: {cmd}\nRESULT ({code}): {output[:500]}"
            self.commit_memory(learn_content, "system_ephemeral")
            
            self.logger.log_transition(
                context={"cmd": cmd, "code": code},
                action="EXECUTE",
                result="SUCCESS" if code == 0 else "FAIL"
            )
            return output
        return None

    def commit_memory(self, content: str, rights: str = "user_sovereign"):
        """
        API to write new memories to the Spine.
        """
        import uuid
        rights_enum = MemoryRights(rights)
        vid = f"AMOS://Mem/{uuid.uuid4().hex[:8]}"
        
        mem = SymbioticMemory(
            vault_id=vid,
            content=content,
            rights=rights_enum
        )
        
        self.vam.add_memory(mem)
        print(f"  ⟡ Memory Committed: {vid}")
