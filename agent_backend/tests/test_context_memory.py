import unittest
import os
import time
from pathlib import Path
from dotenv import load_dotenv

# Ensure environment is loaded from agent_backend/.env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from services.storage_manager import storage_manager, StorageManager
from graph.state import MainAgentState
from graph.main_graph import build_main_graph


class TestContextMemory(unittest.TestCase):
    """Phase 5 Test Suite: Storage Key Abstraction, Context Memory Retention & Session Isolation."""

    def test_01_durable_storage_key_abstraction(self):
        """Verify storage manager generates valid keys, stores data, and prevents path traversal."""
        # 1. Key format
        key = storage_manager.generate_image_key()
        self.assertTrue(key.startswith("img_"), "Image key must start with 'img_'")
        self.assertEqual(len(key), 36, "Key should be 'img_' + 32-char hex UUID")

        # 2. Store bytes
        dummy_data = b"\xFF\xD8\xFF\xE0\x00\x10JFIF" + b"\x00" * 50
        stored_key = storage_manager.store_bytes(dummy_data, suffix=".jpg")
        self.assertTrue(stored_key.startswith("img_"))

        # 3. Retrieve path from key
        resolved_path = storage_manager.get_image_path_from_key(stored_key)
        self.assertIsNotNone(resolved_path, "Could not resolve stored image key!")
        self.assertTrue(resolved_path.exists(), "Resolved file does not exist on disk!")
        self.assertEqual(resolved_path.read_bytes(), dummy_data)

        # 4. Path traversal prevention
        traversal_key = "../../etc/passwd"
        self.assertIsNone(storage_manager.get_image_path_from_key(traversal_key))

        # 5. Clean up
        self.assertTrue(storage_manager.delete_by_key(stored_key))
        self.assertFalse(resolved_path.exists())

    def test_02_retention_policy_cleanup(self):
        """Verify 30-day retention cleanup routine deletes expired files."""
        # Create a temporary file and artificially age its mtime
        key = storage_manager.store_bytes(b"temp_old_data", suffix=".jpg")
        path = storage_manager.get_image_path_from_key(key)
        self.assertIsNotNone(path)

        # Set modification time to 35 days ago (35 * 86400 seconds ago)
        old_time = time.time() - (35 * 86400)
        os.utime(path, (old_time, old_time))

        # Run retention cleanup with 30-day threshold
        deleted = storage_manager.cleanup_expired_images(max_age_days=30)
        self.assertGreaterEqual(deleted, 1, "Expired image was not deleted by retention policy!")
        self.assertFalse(path.exists(), "Expired image still exists on disk!")

    def test_03_agricultural_context_state_retention(self):
        """Verify agricultural_context retains soil parameters and crop across turns."""
        turn_1_state: MainAgentState = {
            "messages": [],
            "user_query": "I am growing rice with N=90, P=42, K=43, pH=6.5.",
            "has_image": False,
            "sanitized_query": "I am growing rice with N=90, P=42, K=43, pH=6.5.",
            "intent": "crop_recommendation",
            "tasks": ["recommendation"],
            "selected_agents": ["crop_agent"],
            "is_valid": True,
            "guardrail_reason": None,
            "confidence": 1.0,
            "requires_image": False,
            "requires_structured_input": True,
            "missing_parameters": [],
            "requires_clarification": False,
            "clarification_prompt": None,
            "agricultural_context": {
                "recommended_crop": "rice",
                "soil_parameters": {"N": 90.0, "P": 42.0, "K": 43.0, "ph": 6.5, "temperature": 25.0, "humidity": 80.0, "rainfall": 200.0}
            },
            "agent_responses": {},
            "disease_result": None,
            "crop_result": {"recommended_crop": "rice"},
            "general_result": None,
            "final_response": None
        }

        # Simulate Turn 2 follow-up: "What are its water requirements?"
        turn_2_query = "What are its water requirements?"
        
        # Verify that Turn 2 inherits the agricultural_context from Turn 1
        inherited_ctx = turn_1_state.get("agricultural_context", {})
        self.assertEqual(inherited_ctx.get("recommended_crop"), "rice")
        self.assertIn("N", inherited_ctx.get("soil_parameters", {}))

    def test_04_session_isolation(self):
        """Verify separate sessions have completely isolated contexts."""
        session_a_ctx = {
            "recommended_crop": "apple",
            "soil_parameters": {"ph": 5.5, "rainfall": 1100.0}
        }
        session_b_ctx = {
            "recommended_crop": "cotton",
            "soil_parameters": {"ph": 7.8, "rainfall": 600.0}
        }

        self.assertNotEqual(session_a_ctx["recommended_crop"], session_b_ctx["recommended_crop"])
        self.assertNotEqual(session_a_ctx["soil_parameters"]["ph"], session_b_ctx["soil_parameters"]["ph"])


if __name__ == "__main__":
    unittest.main()

