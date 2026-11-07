import unittest
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Ensure environment is loaded from agent_backend/.env
load_dotenv(backend_dir / ".env")

from agents.shared.fertilizer import generate_fertilizer_guidance, format_fertilizer_markdown, MANDATORY_FERTILIZER_DISCLAIMER
from agents.crop.comparator import build_comparison_matrix, CROP_METADATA
from agents.crop.calendar import get_crop_season_info, format_crop_calendar_markdown
from agents.general.schemes import search_schemes, format_schemes_summary
from agents.general.market import get_msp_info, format_market_guidance_markdown
from agents.general.graph import general_graph


class TestAgriculturalCapabilities(unittest.TestCase):
    """Phase 8 Test Suite: Advanced Agronomic Capabilities & Knowledge Expansion."""

    def test_01_fertilizer_guidance_and_disclaimer(self):
        """Verify soil nutrient categorization, INM advice, and mandatory KVK/SHC disclaimer."""
        advisory = generate_fertilizer_guidance(
            crop_name="rice",
            n=35.0,  # Low N
            p=55.0,  # Medium P
            k=85.0,  # High K
            ph=6.5
        )
        self.assertEqual(advisory.crop, "Rice")
        
        # Check nutrient categorization
        statuses = {s.nutrient: s.category for s in advisory.nutrient_statuses}
        self.assertEqual(statuses.get("N"), "Low")
        self.assertEqual(statuses.get("P"), "Medium")
        self.assertEqual(statuses.get("K"), "High")

        # Format markdown and verify disclaimer
        md = format_fertilizer_markdown(advisory)
        self.assertIn("Krishi Vigyan Kendra", md, "Mandatory KVK disclaimer missing!")
        self.assertIn("Soil Health Card", md, "Soil Health Card reference missing!")
        self.assertNotIn("100:40:40", md, "Prohibited universal rigid dosage formula detected!")

    def test_02_candidate_crop_comparison_matrix(self):
        """Verify side-by-side Markdown comparison matrix generation for candidate crops."""
        top_candidates = [
            {"crop": "rice", "tree_vote_share": 0.75},
            {"crop": "maize", "tree_vote_share": 0.15},
            {"crop": "jute", "tree_vote_share": 0.10}
        ]
        matrix_md = build_comparison_matrix(top_candidates)
        self.assertTrue(len(matrix_md) > 200)
        self.assertIn("Rice", matrix_md)
        self.assertIn("Maize", matrix_md)
        self.assertIn("Jute", matrix_md)
        self.assertIn("Tree-Vote Share", matrix_md)
        self.assertIn("Water Need", matrix_md)
        self.assertIn("Optimal Soil pH", matrix_md)

    def test_03_seasonal_crop_calendar(self):
        """Verify seasonal mapping for Kharif, Rabi, and Zaid crops."""
        # Kharif
        rice_cal = get_crop_season_info("rice")
        self.assertEqual(rice_cal["season_key"], "kharif")
        self.assertIn("June", rice_cal["sowing_window"])

        # Rabi
        chickpea_cal = get_crop_season_info("chickpea")
        self.assertEqual(chickpea_cal["season_key"], "rabi")
        self.assertIn("October", chickpea_cal["sowing_window"])

        # Zaid
        melon_cal = get_crop_season_info("watermelon")
        self.assertEqual(melon_cal["season_key"], "zaid")
        self.assertIn("March", melon_cal["sowing_window"])
        self.assertIn("April", melon_cal["harvesting_window"])

    def test_04_government_schemes_lookup(self):
        """Verify government schemes module returns verified official portals and benefits."""
        # 1. PM-KISAN
        pm_kisan_matches = search_schemes("PM-KISAN direct cash transfer")
        self.assertTrue(len(pm_kisan_matches) > 0)
        self.assertIn("pmkisan.gov.in", pm_kisan_matches[0]["official_portal"])
        self.assertIn("6,000", pm_kisan_matches[0]["benefits"])

        # 2. PMFBY (Crop Insurance)
        pmfby_matches = search_schemes("crop insurance calamity")
        self.assertTrue(len(pmfby_matches) > 0)
        self.assertIn("pmfby.gov.in", pmfby_matches[0]["official_portal"])

        # 3. KUSUM (Solar Pumps)
        kusum_matches = search_schemes("solar pump subsidy")
        self.assertTrue(len(kusum_matches) > 0)
        self.assertIn("pmkusum.mnre.gov.in", kusum_matches[0]["official_portal"])

    def test_05_market_msp_and_price_guidance(self):
        """Verify market guidance returns official MSP rates and Agmarknet portals."""
        # Wheat MSP
        wheat_msp = get_msp_info("wheat")
        self.assertIsNotNone(wheat_msp)
        self.assertEqual(wheat_msp["crop"], "Wheat")
        self.assertEqual(wheat_msp["msp"], 2425)

        # Paddy MSP
        paddy_msp = get_msp_info("paddy")
        self.assertIsNotNone(paddy_msp)
        self.assertEqual(paddy_msp["msp"], 2300)

        # Markdown format check
        md = format_market_guidance_markdown(commodity="wheat", mandi_name="Khanna")
        self.assertIn("agmarknet.gov.in", md)
        self.assertIn("enam.gov.in", md)
        self.assertIn("2425", md)

    def test_06_general_agent_scheme_integration(self):
        """Verify General Agent responds with structured scheme data for subsidy queries."""
        async def run_query():
            res = await general_graph.ainvoke({
                "question": "How can I register for the PM-KISAN subsidy scheme?"
            })
            return res.get("answer", "")

        answer = asyncio.run(run_query())
        self.assertTrue(len(answer) > 100)
        self.assertTrue("pmkisan" in answer.lower() or "6,000" in answer or "aadhaar" in answer.lower())


if __name__ == "__main__":
    unittest.main()
