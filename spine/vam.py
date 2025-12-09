"""
SYSTEM: Vault Attention Mechanism (VAM)
VaultID: AMOS://MirrorDNA-Symbiosis/Spine/VAM/v1.0
GlyphSig: ⟡⟦ATTENTION⟧ · ⟡⟦FOCUS⟧

The VAM determines what the System 'sees' in its context window.
It balances long-term memory (Vectors) with short-term relevance (Time).

Formula: Attention = (VectorSim * 0.5) + (TimeDecay * 0.3) + (GlyphPriority * 0.2)
"""

import time
import chromadb
from typing import List, Dict, Any
from datetime import datetime
from sentence_transformers import SentenceTransformer
from .types import SymbioticMemory, SpineContext

# Weight Config
WEIGHT_VECTOR = 0.5
WEIGHT_TIME = 0.3
WEIGHT_GLYPH = 0.2

class VaultAttentionMechanism:
    def __init__(self, vault_path: str = "./vectors", model_name: str = "all-MiniLM-L6-v2"):
        self.chroma_client = chromadb.PersistentClient(path=vault_path)
        self.collection = self.chroma_client.get_or_create_collection(name="symbiotic_spine")
        self.embedder = SentenceTransformer(model_name)
        print(f"⟡ VAM Online: {model_name} loaded.")

    def add_memory(self, memory: SymbioticMemory):
        """Index a memory into the vector spine."""
        embedding = self.embedder.encode(memory.content).tolist()
        
        # Determine active glyphs
        active_glyphs = [g for g in ["⟡", "❖", "◈"] if g in memory.content]
        
        self.collection.add(
            ids=[memory.vault_id],
            embeddings=[embedding],
            documents=[memory.content],
            metadatas=[{
                "created_at": memory.created_at,
                "rights": memory.rights.value,
                "glyphs": ",".join(active_glyphs)
            }]
        )

    def retrieve_context(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieves context using the Unified Attention Formula.
        """
        query_vec = self.embedder.encode(query).tolist()
        current_time = datetime.now().timestamp()
        
        # 1. Fetch Candidates (Broad Vector Search)
        results = self.collection.query(
            query_embeddings=[query_vec],
            n_results=top_k * 3 # Fetch extra to re-rank
        )
        
        if not results['ids']:
            return []

        candidates = []
        ids = results['ids'][0]
        distances = results['distances'][0]
        metadatas = results['metadatas'][0]
        documents = results['documents'][0]

        for i, vault_id in enumerate(ids):
            # 2. Compute Components
            # Vector Similarity (1 - distance for cosine approx)
            vector_score = 1.0 - distances[i] 
            
            # Time Decay: 1.0 at creation, decays to 0.5 over 7 days
            created_at = metadatas[i].get('created_at', current_time)
            age_seconds = current_time - created_at
            time_decay = 1.0 / (1.0 + (age_seconds / 604800)) # 7 days decay half-life
            
            # Glyph Boost
            glyphs = metadatas[i].get('glyphs', "")
            glyph_score = 1.0 if "⟡" in glyphs else 0.5
            
            # 3. Unified Score
            final_score = (vector_score * WEIGHT_VECTOR) + \
                          (time_decay * WEIGHT_TIME) + \
                          (glyph_score * WEIGHT_GLYPH)
            
            candidates.append({
                'vault_id': vault_id,
                'content': documents[i],
                'score': final_score,
                'vector_score': vector_score,
                'time_score': time_decay,
                'glyph_score': glyph_score
            })
            
        # 4. Re-Rank and Return
        candidates.sort(key=lambda x: x['score'], reverse=True)
        return candidates[:top_k]
