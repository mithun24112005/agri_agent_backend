"""
Unit & Integration Test Suite for Supervisor-Level Crop Input Validation (v2.1).
Verifies:
1. All 7 parameters must be present before Crop Recommendation Agent or ML model is invoked.
2. Incomplete inputs return the exact spec-compliant clarification message.
3. Multi-turn parameter accumulation from the same session.
4. Parameter override uses the latest explicitly provided values.
5. Context reset for new farm/sample ignores stale parameters.
6. Incompatible units (e.g. Fahrenheit) request clarification.
7. Fertilizer queries route exclusively to General Agricultural Agent without crop validation.
8. Compound queries execute other eligible agents while withholding the crop recommendation branch.
9. Defense-in-depth: crop_node refuses to invoke ML pipeline with missing or default values.
"""

import unittest
import asyncio
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys
import os
from dotenv import load_dotenv

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
load_dotenv(backend_dir / ".env")

from agents.supervisor.crop_validator import (
    validate_crop_inputs,
    EXACT_CROP_CLARIFICATION_MESSAGE,
    REQUIRED_PARAMETERS
)
from agents.supervisor.graph import supervisor_graph
from graph.main_graph import classify_and_route, route_after_classify, crop_node
from graph.state import MainAgentState


class TestSupervisorCropValidation(unittest.IsolatedAsyncioTestCase):

    def test_01_incomplete_crop_missing_all_inputs(self):
        """Query asking for crop recommendation with no parameters must be marked incomplete."""
        res = validate_crop_inputs("Recommend a crop for my farm")
        self.assertFalse(res.is_complete)
        self.assertEqual(len(res.missing_parameters), 7)
        self.assertIn(EXACT_CROP_CLARIFICATION_MESSAGE, res.clarification_message)
        self.assertEqual(len(res.validated_parameters), 0)

    def test_02_incomplete_crop_partial_npk_only(self):
        """Query providing only NPK values must be rejected with missing weather/pH parameters."""
        res = validate_crop_inputs("My NPK values are 80, 40, 30. Which crop should I grow?")
        self.assertFalse(res.is_complete)
        self.assertEqual(res.validated_parameters.get("N"), 80.0)
        self.assertEqual(res.validated_parameters.get("P"), 40.0)
        self.assertEqual(res.validated_parameters.get("K"), 30.0)
        self.assertIn("ph", res.missing_parameters)
        self.assertIn("rainfall", res.missing_parameters)
        self.assertIn("temperature", res.missing_parameters)
        self.assertIn("humidity", res.missing_parameters)
        self.assertIn(EXACT_CROP_CLARIFICATION_MESSAGE, res.clarification_message)

    def test_03_incomplete_crop_partial_weather_only(self):
        """Query providing only weather must be rejected with missing soil nutrient parameters."""
        res = validate_crop_inputs("Temperature is 28°C and humidity is 75%. Recommend a crop.")
        self.assertFalse(res.is_complete)
        self.assertEqual(res.validated_parameters.get("temperature"), 28.0)
        self.assertEqual(res.validated_parameters.get("humidity"), 75.0)
        self.assertIn("N", res.missing_parameters)
        self.assertIn("P", res.missing_parameters)
        self.assertIn("K", res.missing_parameters)
        self.assertIn("ph", res.missing_parameters)
        self.assertIn("rainfall", res.missing_parameters)
        self.assertIn(EXACT_CROP_CLARIFICATION_MESSAGE, res.clarification_message)

    def test_04_complete_seven_parameters_accepted(self):
        """When all seven parameters are present and physically valid, validation passes."""
        query = "My soil has N=90, P=42, K=43, pH=6.5, temperature=25, humidity=80, rainfall=200. Recommend a crop."
        res = validate_crop_inputs(query)
        self.assertTrue(res.is_complete)
        self.assertEqual(len(res.missing_parameters), 0)
        self.assertIsNone(res.clarification_message)
        self.assertEqual(res.validated_parameters["N"], 90.0)
        self.assertEqual(res.validated_parameters["P"], 42.0)
        self.assertEqual(res.validated_parameters["K"], 43.0)
        self.assertEqual(res.validated_parameters["ph"], 6.5)
        self.assertEqual(res.validated_parameters["temperature"], 25.0)
        self.assertEqual(res.validated_parameters["humidity"], 80.0)
        self.assertEqual(res.validated_parameters["rainfall"], 200.0)

    def test_05_multiturn_parameter_accumulation(self):
        """Supervisor combines explicitly provided parameters across multiple turns in the same session."""
        # Turn 1: NPK only
        turn1_res = validate_crop_inputs("My NPK values are 80, 40, 30.")
        self.assertFalse(turn1_res.is_complete)
        saved_context = turn1_res.validated_parameters

        # Turn 2: pH and rainfall added
        turn2_res = validate_crop_inputs("Soil pH is 6.5 and rainfall is 180mm", prior_parameters=saved_context)
        self.assertFalse(turn2_res.is_complete)
        saved_context.update(turn2_res.validated_parameters)

        # Turn 3: temperature and humidity added -> Now complete!
        turn3_res = validate_crop_inputs("Average temperature is 24°C and humidity is 78%", prior_parameters=saved_context)
        self.assertTrue(turn3_res.is_complete)
        self.assertEqual(len(turn3_res.validated_parameters), 7)
        self.assertIsNone(turn3_res.clarification_message)

    def test_06_multiturn_parameter_override_latest_value(self):
        """When user provides an updated value for a parameter, the latest explicitly supplied value is used."""
        prior = {"N": 80.0, "P": 40.0, "K": 40.0, "ph": 6.5, "temperature": 25.0, "humidity": 70.0, "rainfall": 100.0}
        
        # User provides corrected Nitrogen value
        res = validate_crop_inputs("Actually my Nitrogen level is 95 kg/ha", prior_parameters=prior)
        self.assertTrue(res.is_complete)
        self.assertEqual(res.validated_parameters["N"], 95.0)
        self.assertEqual(res.validated_parameters["P"], 40.0)

    def test_07_multiturn_context_reset_new_farm(self):
        """When user explicitly references a new/different farm, stale parameters from prior turns are discarded."""
        prior = {"N": 80.0, "P": 40.0, "K": 40.0, "ph": 6.5, "temperature": 25.0, "humidity": 70.0, "rainfall": 100.0}
        
        # User switches to a different farm without providing new values
        res = validate_crop_inputs("Now for my second farm with sandy soil, recommend a crop.", prior_parameters=prior)
        self.assertFalse(res.is_complete)
        self.assertEqual(len(res.missing_parameters), 7)
        self.assertIn(EXACT_CROP_CLARIFICATION_MESSAGE, res.clarification_message)

    def test_08_incompatible_unit_rejection(self):
        """Incompatible units like Fahrenheit (°F) or lbs/acre must be rejected with clarification."""
        query = "Temperature is 85°F, humidity 60%, N=50, P=50, K=50, pH=6.5, rainfall=100mm. Recommend a crop."
        res = validate_crop_inputs(query)
        self.assertFalse(res.is_complete)
        self.assertIn("temperature", res.invalid_parameters)
        self.assertIn("Fahrenheit", res.invalid_parameters["temperature"])

    async def test_09_supervisor_node_fertilizer_routes_to_general_agent(self):
        """Fertilizer queries must route directly to General Agricultural Agent without crop validation."""
        state: MainAgentState = {
            "user_query": "What fertilizer should I use for my wheat crop?",
            "messages": [],
            "agricultural_context": {}
        }
        res = await classify_and_route(state)
        # Must route to general_agent
        self.assertIn("general_agent", res["selected_agents"])
        self.assertNotIn("crop_agent", res["selected_agents"])
        # Must NOT require 7-parameter crop clarification
        self.assertFalse(res.get("requires_clarification", False))

    async def test_10_supervisor_node_explain_npk_fertilizer_routes_to_general_agent(self):
        """General questions explaining NPK fertilizer route to General Agent without crop validation."""
        state: MainAgentState = {
            "user_query": "Explain NPK fertilizer.",
            "messages": [],
            "agricultural_context": {}
        }
        res = await classify_and_route(state)
        self.assertIn("general_agent", res["selected_agents"])
        self.assertNotIn("crop_agent", res["selected_agents"])
        self.assertFalse(res.get("requires_clarification", False))

    async def test_11_compound_disease_and_incomplete_crop(self):
        """
        Compound query asking for disease identification and crop recommendation:
        Disease detection agent must execute; crop agent must be skipped with clarification notice.
        """
        state: MainAgentState = {
            "user_query": "Identify this plant disease and recommend a suitable crop for my farm.",
            "messages": [],
            "agricultural_context": {}
        }
        res = await classify_and_route(state)
        # disease_agent should be scheduled to run
        self.assertIn("disease_agent", res["selected_agents"])
        # crop_agent must NOT be scheduled to run because inputs are incomplete
        self.assertNotIn("crop_agent", res["selected_agents"])
        # crop clarification message must be stored in agent_responses for response aggregator
        self.assertIn("crop_agent", res["agent_responses"])
        self.assertIn(EXACT_CROP_CLARIFICATION_MESSAGE, res["agent_responses"]["crop_agent"])
        
        # route_after_classify must schedule disease_node
        targets = route_after_classify(res)
        self.assertEqual(targets, ["disease_node"])

    async def test_12_compound_fertilizer_and_incomplete_crop(self):
        """
        Compound query asking for fertilizer requirements and crop recommendation:
        General agent handles fertilizer; crop recommendation is withheld with clarification.
        """
        state: MainAgentState = {
            "user_query": "Explain fertilizer requirements and recommend a crop.",
            "messages": [],
            "agricultural_context": {}
        }
        res = await classify_and_route(state)
        self.assertIn("general_agent", res["selected_agents"])
        self.assertNotIn("crop_agent", res["selected_agents"])
        self.assertIn("crop_agent", res["agent_responses"])
        self.assertIn(EXACT_CROP_CLARIFICATION_MESSAGE, res["agent_responses"]["crop_agent"])
        
        targets = route_after_classify(res)
        self.assertEqual(targets, ["general_node"])

    async def test_13_crop_node_defense_in_depth_failsafe(self):
        """If crop_node is somehow reached without complete validated parameters, it refuses ML execution."""
        incomplete_state: MainAgentState = {
            "user_query": "Recommend a crop for my farm",
            "sanitized_query": "Recommend a crop for my farm",
            "validated_crop_parameters": None,
            "agricultural_context": {}
        }
        res = await crop_node(incomplete_state, config={})
        self.assertIn("crop_agent", res["agent_responses"])
        self.assertIn(EXACT_CROP_CLARIFICATION_MESSAGE, res["agent_responses"]["crop_agent"])


if __name__ == "__main__":
    unittest.main()
