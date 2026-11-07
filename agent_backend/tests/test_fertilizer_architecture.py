"""
Comprehensive Architecture Verification Test Suite for Fertilizer Implementation
Verifies all 8 requirements specified in the Fertilizer Architecture Fix:
1. Fertilizer query with crop name but no NPK values (no TypeError, no fabricated values).
2. Fertilizer query with valid NPK measurements.
3. Fertilizer query with incomplete NPK measurements (asks for missing parameters).
4. Fertilizer query routes only to General Agent.
5. Fertilizer query does not invoke Crop Recommendation Agent.
6. Compound fertilizer and incomplete crop recommendation query (both handled cleanly).
7. Shared fertilizer utility is imported successfully by both relevant agents (no duplicate logic).
8. Existing fertilizer and crop recommendation tests continue passing.
"""

import unittest
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

load_dotenv(backend_dir / ".env")

from agents.shared.fertilizer import (
    generate_fertilizer_guidance,
    format_fertilizer_markdown,
    extract_nutrient_measurements,
    detect_crop_name,
    FertilizerAdvisory,
    NutrientStatus,
    NUTRIENT_THRESHOLDS,
    MANDATORY_FERTILIZER_DISCLAIMER
)
from agents.general.graph import general_graph, information_retrieval_node
from agents.supervisor.graph import supervisor_graph
from graph.main_graph import build_main_graph
from services.crop_model import crop_model_service, CropInputParameters


class TestFertilizerArchitecture(unittest.TestCase):
    """Rigorous verification of the refactored fertilizer architecture."""

    @classmethod
    def setUpClass(cls):
        cls.main_graph = build_main_graph()

    # -------------------------------------------------------------------------
    # 1. Fertilizer query with crop name but no NPK values
    # -------------------------------------------------------------------------
    def test_01_fertilizer_query_with_crop_name_no_npk(self):
        """No TypeError, no arbitrary defaults, no fabricated soil measurements."""
        # A. Unit test pure function
        advisory = generate_fertilizer_guidance(crop_name="wheat")
        self.assertEqual(advisory.crop, "Wheat")
        self.assertFalse(advisory.has_soil_test, "has_soil_test should be False when no NPK provided")
        self.assertEqual(len(advisory.nutrient_statuses), 0, "No nutrient status table should be fabricated!")
        self.assertIn("Nitrogen (N)", advisory.missing_measurements)
        self.assertIn("Phosphorus (P)", advisory.missing_measurements)
        self.assertIn("Potassium (K)", advisory.missing_measurements)
        self.assertIsNotNone(advisory.measurement_prompt)
        self.assertIn("Soil Health Card", advisory.measurement_prompt)

        # Markdown formatting check
        md = format_fertilizer_markdown(advisory)
        self.assertIn("No soil test measurements were provided", md)
        self.assertIn("Soil Test Notice:", md)
        self.assertIn(MANDATORY_FERTILIZER_DISCLAIMER, md)
        self.assertNotIn("100:40:40", md, "Universal fixed ratio prohibited!")

        # B. Integration test with information_retrieval_node
        async def run_retrieval():
            return await information_retrieval_node({"question": "What fertilizer should I use for wheat?"})

        res = asyncio.run(run_retrieval())
        self.assertIn("search_results", res)
        self.assertTrue(len(res["search_results"]) > 0)
        first_title = res["search_results"][0]["title"]
        self.assertIn("ICAR Integrated Nutrient Management", first_title)
        self.assertIn("Wheat", first_title)
        first_content = res["search_results"][0]["content"]
        self.assertIn("Soil Test Notice", first_content)
        self.assertIn("Krishi Vigyan Kendra", first_content)

    # -------------------------------------------------------------------------
    # 2. Fertilizer query with valid NPK measurements
    # -------------------------------------------------------------------------
    def test_02_fertilizer_query_with_valid_npk_measurements(self):
        """Accurate ICAR categorization and structured advice when NPK is provided."""
        advisory = generate_fertilizer_guidance(
            crop_name="rice",
            n=35.0,  # Low
            p=55.0,  # Medium
            k=85.0,  # High
            ph=6.5   # Optimal
        )
        self.assertEqual(advisory.crop, "Rice")
        self.assertTrue(advisory.has_soil_test)
        self.assertEqual(len(advisory.nutrient_statuses), 3)
        self.assertEqual(len(advisory.missing_measurements), 0)
        self.assertIsNone(advisory.measurement_prompt)

        status_dict = {s.nutrient: s.category for s in advisory.nutrient_statuses}
        self.assertEqual(status_dict["N"], "Low")
        self.assertEqual(status_dict["P"], "Medium")
        self.assertEqual(status_dict["K"], "High")

        md = format_fertilizer_markdown(advisory)
        self.assertIn("| **N** | 35.0 | `Low` |", md)
        self.assertIn("| **P** | 55.0 | `Medium` |", md)
        self.assertIn("| **K** | 85.0 | `High` |", md)
        self.assertIn("Optimal Soil pH (pH 6.5)", md)
        self.assertIn(MANDATORY_FERTILIZER_DISCLAIMER, md)

        # Test regex measurement extractor
        extracted = extract_nutrient_measurements("My soil has N=45, P=25, K=30, and pH=6.8")
        self.assertEqual(extracted["N"], 45.0)
        self.assertEqual(extracted["P"], 25.0)
        self.assertEqual(extracted["K"], 30.0)
        self.assertEqual(extracted["ph"], 6.8)

    # -------------------------------------------------------------------------
    # 3. Fertilizer query with incomplete NPK measurements
    # -------------------------------------------------------------------------
    def test_03_fertilizer_query_with_incomplete_npk_measurements(self):
        """Partial NPK categorization: Evaluates available nutrients, asks for missing."""
        advisory = generate_fertilizer_guidance(
            crop_name="maize",
            n=45.0,
            p=None,
            k=None
        )
        self.assertEqual(advisory.crop, "Maize")
        self.assertTrue(advisory.has_soil_test)
        self.assertEqual(len(advisory.nutrient_statuses), 1)
        self.assertEqual(advisory.nutrient_statuses[0].nutrient, "N")
        self.assertEqual(advisory.nutrient_statuses[0].category, "Low")
        self.assertEqual(advisory.missing_measurements, ["Phosphorus (P)", "Potassium (K)"])
        self.assertIn("Phosphorus (P)", advisory.measurement_prompt)
        self.assertIn("Potassium (K)", advisory.measurement_prompt)

        md = format_fertilizer_markdown(advisory)
        self.assertIn("| **N** | 45.0 | `Low` |", md)
        self.assertIn("Phosphorus (P)", md)
        self.assertIn(MANDATORY_FERTILIZER_DISCLAIMER, md)

    # -------------------------------------------------------------------------
    # 4. Fertilizer query routes only to General Agent
    # -------------------------------------------------------------------------
    def test_04_fertilizer_query_routes_only_to_general_agent(self):
        """Supervisor maps fertilizer intent to soil_nutrient_management and selects general_agent."""
        async def run_sup(q):
            return await supervisor_graph.ainvoke({
                "user_query": q,
                "conversation_context": "",
                "has_image": False
            })

        # Test query A: specific crop fertilizer
        res_a = asyncio.run(run_sup("What fertilizer should I apply for mustard?"))
        self.assertEqual(res_a.get("selected_agents"), ["general_agent"])
        self.assertIn(res_a.get("intent"), ["soil_nutrient_management", "general_farming_advice"])

        # Test query B: synthetic chemical query
        res_b = asyncio.run(run_sup("How much urea and DAP should I apply?"))
        self.assertEqual(res_b.get("selected_agents"), ["general_agent"])
        self.assertEqual(res_b.get("intent"), "soil_nutrient_management")

    # -------------------------------------------------------------------------
    # 5. Fertilizer query does not invoke Crop Recommendation Agent
    # -------------------------------------------------------------------------
    def test_05_fertilizer_query_does_not_invoke_crop_agent(self):
        """End-to-end execution of a fertilizer query never invokes crop_agent or ML model."""
        async def run_main():
            return await self.main_graph.ainvoke({
                "user_query": "What fertilizer schedule should I follow for wheat?",
                "has_image": False,
                "messages": []
            }, config={"configurable": {"thread_id": "fert_no_crop"}})

        res = asyncio.run(run_main())
        selected = res.get("selected_agents", [])
        self.assertIn("general_agent", selected)
        self.assertNotIn("crop_agent", selected)

        agent_responses = res.get("agent_responses", {})
        self.assertIn("general_agent", agent_responses)
        self.assertNotIn("crop_agent", agent_responses)
        self.assertIsNone(res.get("crop_result"))
        self.assertFalse(res.get("requires_clarification", False))

    # -------------------------------------------------------------------------
    # 6. Compound fertilizer and incomplete crop recommendation query
    # -------------------------------------------------------------------------
    def test_06_compound_fertilizer_and_incomplete_crop_recommendation(self):
        """
        Compound query: User asks for fertilizer and crop recommendation.
        General Agent executes to answer fertilizer; Crop Agent is withheld with clarification.
        """
        async def run_compound():
            return await self.main_graph.ainvoke({
                "user_query": "Explain fertilizer requirements for wheat and also recommend what crop I should plant on my farm.",
                "has_image": False,
                "messages": []
            }, config={"configurable": {"thread_id": "compound_fert_crop"}})

        res = asyncio.run(run_compound())
        agent_responses = res.get("agent_responses", {})
        
        # General Agent executed
        self.assertIn("general_agent", agent_responses)
        
        # Crop Agent withheld with canonical clarification message
        self.assertIn("crop_agent", agent_responses)
        crop_resp = agent_responses["crop_agent"]
        self.assertIn("Please provide the full set of soil and climate parameters", crop_resp)
        self.assertTrue(res.get("requires_clarification", False))
        
        # Final merged response contains both general advice and clarification
        final_resp = res.get("final_response", "")
        self.assertTrue(len(final_resp) > 100)
        self.assertIn("soil", final_resp.lower())

    # -------------------------------------------------------------------------
    # 7. Shared fertilizer utility is imported successfully by both relevant agents
    # -------------------------------------------------------------------------
    def test_07_shared_fertilizer_utility_imported_by_both_agents(self):
        """Both Crop and General agents import from agents.shared.fertilizer without error."""
        # 1. Test importing in General Agent
        import agents.general.graph as general_module
        with open(general_module.__file__, "r", encoding="utf-8") as f:
            gen_src = f.read()
        self.assertIn("from agents.shared.fertilizer import", gen_src)
        self.assertNotIn("from agents.crop.fertilizer import", gen_src)

        # 2. Test importing in Crop Agent
        import agents.crop.graph as crop_module
        with open(crop_module.__file__, "r", encoding="utf-8") as f:
            crop_src = f.read()
        self.assertIn("from agents.shared.fertilizer import", crop_src)
        self.assertNotIn("from agents.crop.fertilizer import", crop_src)

        # 3. Confirm backward-compatibility shim in agents/crop/fertilizer.py delegates to agents.shared.fertilizer
        old_path = backend_dir / "agents" / "crop" / "fertilizer.py"
        self.assertTrue(old_path.exists(), "Backward-compatibility shim should exist!")
        with open(old_path, "r", encoding="utf-8") as f:
            shim_src = f.read()
        self.assertIn("from agents.shared.fertilizer import", shim_src)

    # -------------------------------------------------------------------------
    # 8. Existing fertilizer and crop recommendation tests continue passing
    # -------------------------------------------------------------------------
    def test_08_crop_recommendation_ml_model_preserved(self):
        """Crop recommendation model continues requiring all 7 parameters and predicting accurately."""
        pred = crop_model_service.predict_crop(
            n=90.0,
            p=42.0,
            k=43.0,
            temperature=20.87,
            humidity=82.0,
            ph=6.5,
            rainfall=202.93
        )
        self.assertEqual(pred["recommended_crop"].lower(), "rice")
        self.assertTrue(len(pred["top_candidates"]) >= 3)
        self.assertTrue(pred["top_candidates"][0]["probability"] > 0.0)


if __name__ == "__main__":
    unittest.main()
