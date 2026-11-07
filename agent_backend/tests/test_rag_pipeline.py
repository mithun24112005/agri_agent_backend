import unittest
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Ensure environment is loaded from agent_backend/.env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from agents.disease.retriever import disease_retriever_v2
from agents.crop.retriever import crop_retriever
from agents.disease.chunker import generate_semantic_chunks
from agents.disease.normalizer import normalize_disease


class TestRAGPipeline(unittest.TestCase):
    """Phase 4 Test Suite: RAG Anti-Contamination, Local Embeddings & Context-Aware Retrieval."""

    def test_01_local_embedding_dimensions(self):
        """Verify local fastembed produces exact 1024-dimensional vectors matching Qdrant schema."""
        vec = disease_retriever_v2.embed("What are the symptoms of apple scab?")
        self.assertIsNotNone(vec, "Local embedding failed to produce a vector!")
        self.assertEqual(len(vec), 1024, f"Vector dimension must be 1024, got {len(vec)}")

    def test_02_disease_rag_anti_contamination(self):
        """Verify disease retriever NEVER returns chunks from another pathogen."""
        # Query with disease_id="early_blight"
        ctx = disease_retriever_v2.build_context(
            question="What fungicides should I apply for early blight?",
            disease_id="early_blight",
            intents=["chemical_control"]
        )
        self.assertTrue(len(ctx) > 0, "No context returned for early_blight!")
        
        # Verify no contamination from unrelated diseases (e.g. apple scab, powdery mildew)
        self.assertNotIn("apple_scab", ctx.lower(), "Contamination: found apple_scab in early_blight query!")
        self.assertNotIn("powdery mildew", ctx.lower(), "Contamination: found powdery mildew in early_blight query!")
        self.assertIn("[Ref:", ctx, "Citation header missing from retrieved context!")

    def test_03_unindexed_disease_no_cross_contamination(self):
        """Verify an unindexed disease never leaks chunks from other diseases."""
        ctx = disease_retriever_v2.build_context(
            question="What is this mysterious pathogen?",
            disease_id="nonexistent_alien_pathogen_xyz",
            intents=["symptoms"]
        )
        # Must return empty string, NOT chunks of an arbitrary disease
        self.assertEqual(ctx, "", "Unindexed disease returned chunks from another disease!")

    def test_04_context_aware_crop_retrieval(self):
        """Verify context-aware crop retrieval retrieves crop knowledge and formats citations."""
        res = crop_retriever.retrieve_crop_context(
            crop_name="apple",
            user_question="What are the soil acidity and pH requirements for apple orchards?",
            soil_ph=5.8,
            rainfall_level="moderate",
            limit=3
        )
        self.assertEqual(res.get("status"), "success")
        chunks = res.get("data", {}).get("chunks", [])
        self.assertTrue(len(chunks) > 0, "No crop chunks returned for apple!")

        ctx_str = crop_retriever.build_crop_context(res)
        self.assertIn("[Ref:", ctx_str, "Citation header missing from crop context!")
        self.assertIn("apple", ctx_str.lower(), "Retrieved context does not mention the target crop!")

    def test_05_content_hash_chunk_deduplication(self):
        """Verify chunk generator creates deterministic content-hashed chunk IDs."""
        sample_disease_data = {
            "id": "test_blight",
            "metadata": {"title": "Test Blight", "host_crops": ["wheat"], "disease_category": "Fungal"},
            "overview": {"content": "Test blight affects wheat crops in humid weather."},
            "symptoms": {"content": "Brown spots on lower leaves with yellow halos."},
            "causes": {"content": "Fungal spores spreading through wind and splash."},
            "recommendations": {
                "organic": {"content": "Apply neem seed kernel extract."},
                "chemical": {"content": "Spray copper oxychloride 50 WP."}
            },
            "preventive_measures": {
                "items": ["Use certified disease-free seeds", "Maintain proper plant spacing"]
            }
        }
        norm = normalize_disease(sample_disease_data)
        chunks = generate_semantic_chunks(norm)
        
        self.assertTrue(len(chunks) >= 3, "Expected at least 3 chunks generated!")
        chunk_ids = [c.chunk_id for c in chunks]
        
        # Ensure all chunk IDs are unique
        self.assertEqual(len(chunk_ids), len(set(chunk_ids)), "Duplicate chunk IDs generated!")
        
        # Verify content hash presence in chunk_id format: disease_id::section::hash
        for cid in chunk_ids:
            parts = cid.split("::")
            self.assertEqual(len(parts), 3, f"Chunk ID '{cid}' does not follow 'id::sec::hash' pattern!")
            self.assertEqual(len(parts[2]), 12, f"Content hash '{parts[2]}' should be 12 characters!")


if __name__ == "__main__":
    unittest.main()
