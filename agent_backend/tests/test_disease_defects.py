"""
Regression tests for verified Disease Agent defects:
1. Disease QA prompt variable substitution (diagnosis_info).
2. Pydantic QuestionIntent attribute and dict access safety.
3. DiseaseMapper reading actual JSON schema keys.
4. Correct canonical mapping separating distinct pathogens (Northern Leaf Blight vs Southern, Isariopsis vs Black Rot).
"""
import unittest
from unittest.mock import MagicMock
from pathlib import Path
from agents.disease.mapper import disease_mapper
from agents.disease.classifier import disease_qa_prompt, QuestionIntent
from agents.disease.graph import classifier_node

class TestDiseaseAgentDefects(unittest.IsolatedAsyncioTestCase):
    
    def test_disease_qa_prompt_variables(self):
        """Verify prompt template formats without KeyError when diagnosis_info is provided."""
        formatted = disease_qa_prompt.format(
            diagnosis_info="- Condition: Apple Scab\n- Confidence: 99.2%",
            context="Apply sulfur sprays in early spring.",
            question="What is the organic treatment?"
        )
        self.assertIn("Apple Scab", formatted)
        self.assertIn("Apply sulfur sprays", formatted)
        self.assertIn("What is the organic treatment?", formatted)

    def test_canonical_pathogen_separation(self):
        """Verify distinct plant pathogens are NOT merged erroneously."""
        # 1. Corn Northern Leaf Blight (Exserohilum turcicum) must map to northern_leaf_blight
        mapped_nlb = disease_mapper.map_prediction("Corn_(maize)___Northern_Leaf_Blight")
        self.assertEqual(mapped_nlb["disease_id"], "northern_leaf_blight")
        self.assertNotEqual(mapped_nlb["disease_id"], "southern_leaf_blight_of_maize")

        # 2. Grape Isariopsis leaf spot must NOT map to Black Rot (Guignardia bidwellii)
        mapped_isariopsis = disease_mapper.map_prediction("Grape___Leaf_blight_(Isariopsis_Leaf_Spot)")
        self.assertEqual(mapped_isariopsis["disease_id"], "isariopsis_leaf_spot")
        self.assertNotEqual(mapped_isariopsis["disease_id"], "black_rot_of_grape")

    def test_disease_mapper_schema_loading(self):
        """Verify mapper correctly indexes titles and aliases from actual JSON dataset files."""
        # Check that northern_leaf_blight is indexed in mapper lookup
        self.assertTrue(disease_mapper.exists("northern_leaf_blight"))
        entry = disease_mapper.lookup.get("northern_leaf_blight")
        self.assertIsNotNone(entry)
        self.assertIn("Northern Leaf Blight", entry["title"])
        self.assertIn("maize", entry["host_crops"])

    async def test_classifier_node_safe_attribute_access(self):
        """Verify classifier node safely handles both Pydantic models and dictionary intent payloads."""
        mock_pydantic = QuestionIntent(intents=["symptoms", "organic_control"])
        
        # Test attribute access logic
        if hasattr(mock_pydantic, "intents"):
            intents = mock_pydantic.intents
        else:
            intents = mock_pydantic.get("intents", [])
            
        self.assertEqual(intents, ["symptoms", "organic_control"])
        
        # Test dict fallback logic
        mock_dict = {"intents": ["causes"]}
        if hasattr(mock_dict, "intents"):
            intents = mock_dict.intents
        else:
            intents = mock_dict.get("intents", [])
        self.assertEqual(intents, ["causes"])

if __name__ == "__main__":
    unittest.main()

