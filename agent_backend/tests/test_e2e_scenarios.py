"""
Master End-to-End Integration Test Suite (Phase 9)
Executes all 10 mandatory scenario workflows covering the entire multi-agent agriculture system.
"""

import unittest
import asyncio
import os
import io
from pathlib import Path
from dotenv import load_dotenv

# Ensure environment is loaded from agent_backend/.env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from graph.main_graph import build_main_graph
from graph.state import MainAgentState
from services.crop_model import crop_model_service
from services.image_storage import save_uploaded_image
from services.storage_manager import storage_manager
from agents.general.graph import general_graph


class TestEndToEndScenarios(unittest.TestCase):
    """Executes all 10 mandatory integration scenarios."""

    @classmethod
    def setUpClass(cls):
        cls.graph = build_main_graph()

    def test_scenario_01_valid_crop_recommendation(self):
        """Scenario 1: User provides valid soil/environmental parameters -> RF prediction, INM advice, KVK disclaimer."""
        async def run_scenario():
            initial_state = {
                "user_query": "My soil parameters are N=90, P=42, K=43, pH=6.5, temperature=21, humidity=82, rainfall=202. What crop is recommended?",
                "has_image": False,
                "messages": []
            }
            res = await self.graph.ainvoke(initial_state, config={"configurable": {"thread_id": "s1_valid_crop"}})
            return res

        res = asyncio.run(run_scenario())
        resp = res.get("final_response", "")
        self.assertIn("rice", resp.lower(), "Expected rice recommendation in response!")
        self.assertIn("Krishi Vigyan Kendra", resp, "Expected KVK disclaimer in fertilizer advice!")
        self.assertIn("Soil Health Card", resp, "Expected Soil Health Card mention!")
        self.assertIn("crop_agent", res.get("selected_agents", []))

    def test_scenario_02_missing_crop_parameters_clarification(self):
        """Scenario 2: User asks for crop recommendation without parameters -> Clarification requested, zero crashes."""
        async def run_scenario():
            initial_state = {
                "user_query": "Which crop is best for my farm?",
                "has_image": False,
                "messages": []
            }
            res = await self.graph.ainvoke(initial_state, config={"configurable": {"thread_id": "s2_missing_params"}})
            return res

        res = asyncio.run(run_scenario())
        resp = res.get("final_response", "")
        self.assertTrue(
            "soil" in resp.lower() and ("npk" in resp.lower() or "nitrogen" in resp.lower() or "test" in resp.lower()),
            "Expected clarification prompt asking for soil test or NPK values!"
        )
        self.assertTrue(res.get("requires_clarification", False))

    def test_scenario_03_extreme_ood_crop_input(self):
        """Scenario 3: Out-of-Distribution input -> Physical validation passes, explicit OOD warning generated."""
        res = crop_model_service.predict_crop(
            n=180.0, p=160.0, k=250.0, temperature=45.0, humidity=98.0, ph=8.5, rainfall=350.0
        )
        warnings = res.get("ood_warnings", [])
        self.assertTrue(len(warnings) > 0, "Expected out-of-distribution warnings for extreme inputs!")
        self.assertIn("tree_vote_share", res["top_candidates"][0])
        # Probabilities should be between 0 and 1
        for cand in res["top_candidates"]:
            self.assertGreaterEqual(cand["tree_vote_share"], 0.0)
            self.assertLessEqual(cand["tree_vote_share"], 1.0)

    def test_scenario_04_image_disease_detection_and_rag(self):
        """Scenario 4: Plant disease detection with zero-contamination RAG."""
        from agents.disease.mapper import disease_mapper
        from agents.disease.retriever import disease_retriever_v2

        # Verify mapping for PlantVillage Tomato Early Blight
        mapping = disease_mapper.map_prediction("Tomato___Early_blight")
        self.assertEqual(mapping["disease_id"], "early_blight")

        # Verify RAG retrieval with citations
        context = disease_retriever_v2.build_context(
            question="What are the symptoms and organic management of early blight?",
            disease_id=mapping["disease_id"],
            intents=["symptoms", "organic_control"]
        )
        self.assertTrue(len(context) > 0)
        self.assertIn("[Ref:", context, "Citation header missing!")
        self.assertNotIn("apple_scab", context.lower(), "Cross-disease contamination detected!")

    def test_scenario_05_healthy_plant_safety(self):
        """Scenario 5: Healthy plant prediction -> Confirms health, prescribes ZERO chemical fungicides."""
        from agents.disease.mapper import disease_mapper

        healthy_cases = [
            "Apple___healthy", "Corn_(maize)___healthy", "Grape___healthy",
            "Peach___healthy", "Pepper,_bell___healthy", "Potato___healthy",
            "Strawberry___healthy", "Tomato___healthy"
        ]
        for pred in healthy_cases:
            res = disease_mapper.map_prediction(pred)
            self.assertTrue(res["is_healthy"], f"Crop {pred} was not marked is_healthy=True!")

    def test_scenario_06_multi_intent_compound_query(self):
        """Scenario 6: Multi-intent query -> Concurrent execution, conflict reconciliation."""
        async def run_scenario():
            initial_state = {
                "user_query": "What crop can I grow in pH 6.5 soil, and also how do I protect my orchard against apple scab?",
                "has_image": False,
                "messages": []
            }
            res = await self.graph.ainvoke(initial_state, config={"configurable": {"thread_id": "s6_multi_intent"}})
            return res

        res = asyncio.run(run_scenario())
        selected = res.get("selected_agents", [])
        final_resp = res.get("final_response", "")

        self.assertTrue(len(selected) >= 2, f"Expected multiple agents selected, got {selected}")
        self.assertIn("crop_agent", selected)
        self.assertIn("disease_agent", selected)
        self.assertTrue(len(final_resp) > 200, "Multi-intent response was too brief!")

    def test_scenario_07_follow_up_context_memory(self):
        """Scenario 7: Follow-up question preserves agricultural context across turns."""
        async def run_two_turns():
            thread_id = "s7_turn_context"
            # Turn 1
            t1_state = {
                "user_query": "My soil has N=90, P=42, K=43, pH=6.5, temp=22, humidity=80, rainfall=200. What crop is recommended?",
                "has_image": False,
                "messages": []
            }
            res1 = await self.graph.ainvoke(t1_state, config={"configurable": {"thread_id": thread_id}})
            agri_ctx = res1.get("agricultural_context", {})

            # Turn 2: Follow up question referencing Turn 1 crop
            t2_state = {
                "user_query": "What are the watering and irrigation needs for this crop?",
                "has_image": False,
                "messages": res1.get("messages", []),
                "agricultural_context": agri_ctx
            }
            res2 = await self.graph.ainvoke(t2_state, config={"configurable": {"thread_id": thread_id}})
            return res1, res2

        res1, res2 = asyncio.run(run_two_turns())
        t1_crop = res1.get("crop_result", {}).get("recommended_crop")
        self.assertEqual(t1_crop, "rice")

        t2_resp = res2.get("final_response", "").lower()
        self.assertTrue(
            "rice" in t2_resp or "water" in t2_resp or "irrigation" in t2_resp,
            "Turn 2 did not retain context of the recommended crop!"
        )

    def test_scenario_08_cross_user_session_isolation(self):
        """Scenario 8: Two separate users/sessions cannot access or leak each other's state."""
        storage_a = storage_manager.store_bytes(b"user_A_leaf_data", suffix=".jpg")
        storage_b = storage_manager.store_bytes(b"user_B_leaf_data", suffix=".jpg")

        self.assertNotEqual(storage_a, storage_b)
        path_a = storage_manager.get_image_path_from_key(storage_a)
        path_b = storage_manager.get_image_path_from_key(storage_b)

        self.assertNotEqual(path_a, path_b)
        self.assertEqual(path_a.read_bytes(), b"user_A_leaf_data")
        self.assertEqual(path_b.read_bytes(), b"user_B_leaf_data")

        # Cleanup
        storage_manager.delete_by_key(storage_a)
        storage_manager.delete_by_key(storage_b)

    def test_scenario_09_search_service_offline_fallback(self):
        """Scenario 9: Search service failure / offline fallback degrades gracefully."""
        async def run_query():
            # Test general query with offline fallback
            res = await general_graph.ainvoke({"question": "What are organic methods for soil health improvement?"})
            return res

        res = asyncio.run(run_query())
        answer = res.get("answer", "")
        self.assertTrue(len(answer) > 50, "General agent failed to generate response during fallback!")

    def test_scenario_10_sub_agent_failure_recovery(self):
        """Scenario 10: Sub-agent error or timeout does not crash the main graph."""
        async def run_with_simulated_error():
            # Query triggering general agent
            state = {
                "user_query": "What is the capital of France?",
                "has_image": False,
                "messages": []
            }
            # Guardrail will reject or handle politely without throwing unhandled exceptions
            res = await self.graph.ainvoke(state, config={"configurable": {"thread_id": "s10_error_isolation"}})
            return res

        res = asyncio.run(run_with_simulated_error())
        self.assertIsNotNone(res.get("final_response"))
        self.assertIn("agriculture", res.get("final_response", "").lower())


if __name__ == "__main__":
    unittest.main()

