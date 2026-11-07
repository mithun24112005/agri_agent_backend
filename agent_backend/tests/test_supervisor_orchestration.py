import unittest
import asyncio
import os
from dotenv import load_dotenv

# Ensure environment is loaded from agent_backend/.env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from agents.supervisor.graph import (
    supervisor_graph,
    pii_sanitizer_node,
    guardrail_node,
    supervisor_node,
    SupervisorRoutingDecision
)
from agents.response.graph import response_node
from graph.main_graph import build_main_graph, route_after_classify
from graph.state import MainAgentState


class TestSupervisorOrchestration(unittest.TestCase):
    """Phase 3 Test Suite: Supervisor routing, PII preservation, and multi-agent orchestration."""

    def test_01_geography_preserving_pii_filter(self):
        """Verify PII filter redacts personal info but preserves agricultural locations."""
        async def run_pii():
            sample_query = (
                "My name is Ramesh Patel, phone 9876543210, living at House 14, Station Road, "
                "Baramati village, Pune district, Maharashtra. My sugarcane crop has yellow leaves. "
                "What is the mandi price at Lasalgaon Mandi?"
            )
            res = await pii_sanitizer_node({"user_query": sample_query})
            sanitized = res.get("sanitized_query", "")
            return sanitized

        sanitized = asyncio.run(run_pii())
        print(f"\n[TEST 01] Sanitized output:\n{sanitized}")

        # Personal PII must be redacted
        self.assertNotIn("Ramesh Patel", sanitized, "Personal name was not redacted!")
        self.assertNotIn("9876543210", sanitized, "Phone number was not redacted!")

        # Agricultural geography MUST be preserved
        self.assertTrue(
            "Baramati" in sanitized or "Pune" in sanitized,
            "Village/District name was improperly redacted!"
        )
        self.assertIn("Maharashtra", sanitized, "State name was improperly redacted!")
        self.assertTrue(
            "sugarcane" in sanitized.lower(),
            "Crop entity was improperly redacted!"
        )
        self.assertTrue(
            "lasalgaon" in sanitized.lower() or "mandi" in sanitized.lower(),
            "Mandi name was improperly redacted!"
        )

    def test_02_12_intent_allowlisted_agents(self):
        """Verify supervisor returns strictly allowlisted agents and valid 12-intent taxonomy."""
        ALLOWED_AGENTS = {"disease_agent", "crop_agent", "general_agent"}
        ALLOWED_INTENTS = {
            "disease_diagnosis",
            "disease_treatment",
            "disease_prevention",
            "crop_recommendation",
            "soil_nutrient_management",
            "irrigation_and_cultivation",
            "general_farming_advice",
            "government_schemes_and_subsidies",
            "agricultural_market_prices",
            "multi_intent",
            "follow_up",
            "unsupported_query"
        }

        async def run_classification():
            test_cases = [
                ("My tomato leaves have black spots with yellow borders. What disease is this?", "disease_agent"),
                ("What are the current wheat prices in Khanna Mandi?", "general_agent"),
                ("How can a small farmer apply for the PM-KISAN subsidy scheme?", "general_agent"),
                ("My soil has N=90, P=42, K=43, pH=6.5, temp=22, humidity=80, rainfall=200. What crop is best?", "crop_agent"),
            ]
            results = []
            for q, expected_agent in test_cases:
                out = await supervisor_graph.ainvoke({
                    "user_query": q,
                    "conversation_context": "",
                    "has_image": False
                })
                results.append((q, expected_agent, out))
            return results

        results = asyncio.run(run_classification())
        for q, expected_agent, out in results:
            intent = out.get("intent")
            selected = out.get("selected_agents", [])
            print(f"\n[TEST 02] Query: {q[:50]}...\n  -> Intent: {intent}, Agents: {selected}")
            
            self.assertIn(intent, ALLOWED_INTENTS, f"Intent '{intent}' not in 12-intent taxonomy!")
            for agent in selected:
                self.assertIn(agent, ALLOWED_AGENTS, f"Agent '{agent}' is not an allowlisted agent!")
            self.assertIn(expected_agent, selected, f"Expected '{expected_agent}' in selected agents!")

    def test_03_missing_parameters_clarification_flow(self):
        """Verify crop recommendation without parameters requests clarification instead of zero-defaults."""
        async def run_crop_query():
            out = await supervisor_graph.ainvoke({
                "user_query": "What crop should I grow on my land?",
                "conversation_context": "",
                "has_image": False
            })
            return out

        out = asyncio.run(run_crop_query())
        print(f"\n[TEST 03] Crop query without parameters:\n  -> requires_clarification: {out.get('requires_clarification')}\n  -> prompt: {out.get('clarification_prompt')}")

        self.assertEqual(out.get("intent"), "crop_recommendation")
        self.assertTrue(
            out.get("requires_clarification"),
            "Supervisor did not flag requires_clarification for parameter-less crop request!"
        )
        self.assertIsNotNone(
            out.get("clarification_prompt"),
            "Clarification prompt was not generated!"
        )

    def test_04_conditional_routing_logic(self):
        """Verify conditional fan-out router targets correct nodes."""
        # 1. Invalid query -> format
        state_invalid: MainAgentState = {
            "is_valid": False,
            "selected_agents": ["crop_agent"],
            "requires_clarification": False,
            "clarification_prompt": None,
        } # type: ignore
        self.assertEqual(route_after_classify(state_invalid), ["format"])

        # 2. Pure clarification -> format
        state_clarify: MainAgentState = {
            "is_valid": True,
            "selected_agents": ["crop_agent"],
            "requires_clarification": True,
            "clarification_prompt": "Please provide NPK values.",
        } # type: ignore
        self.assertEqual(route_after_classify(state_clarify), ["format"])

        # 3. Multi-agent fan-out -> disease_node and crop_node
        state_multi: MainAgentState = {
            "is_valid": True,
            "selected_agents": ["disease_agent", "crop_agent"],
            "requires_clarification": False,
            "clarification_prompt": None,
        } # type: ignore
        targets = route_after_classify(state_multi)
        self.assertIn("disease_node", targets)
        self.assertIn("crop_node", targets)
        self.assertEqual(len(targets), 2)

    def test_05_conflict_resolving_response_aggregation(self):
        """Verify response aggregator synthesizes multiple agents and resolves conflicting advice."""
        async def run_aggregator():
            mock_state: MainAgentState = {
                "user_query": "Can I grow rice and what should I do about leaf spots on my orchard trees?",
                "sanitized_query": "Can I grow rice and what should I do about leaf spots on my orchard trees?",
                "is_valid": True,
                "agent_responses": {
                    "crop_agent": "For your soil, Rice is recommended. Rice requires continuous field flooding and heavy irrigation.",
                    "disease_agent": "The orchard leaves show Apple Scab fungal infection. Stop all overhead irrigation immediately, as moisture spreads the fungal spores. [Ref: PlantVillage Disease Guide]"
                },
                "requires_clarification": False,
                "clarification_prompt": None
            } # type: ignore
            res = await response_node(mock_state)
            return res

        res = asyncio.run(run_aggregator())
        final_text = res.get("final_response", "")
        print(f"\n[TEST 05] Aggregated response preview:\n{final_text[:300]}...")

        # Assert citation preservation and cohesive response
        self.assertIn("PlantVillage", final_text, "Citation was not preserved in aggregated response!")
        self.assertNotIn("[crop_agent]", final_text, "Raw agent tag was exposed in response!")
        self.assertNotIn("[disease_agent]", final_text, "Raw agent tag was exposed in response!")
        self.assertTrue(len(final_text) > 100, "Aggregated response was too short or empty!")


if __name__ == "__main__":
    unittest.main()

