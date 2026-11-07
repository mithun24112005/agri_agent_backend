"""
Unit tests for Disease RAG Anti-Contamination:
Verifies that disease_id filters are strictly maintained under all conditions
and never dropped on empty/missing results.
"""
import unittest
from unittest.mock import MagicMock, patch
from agents.disease.retriever import disease_retriever_v2

class TestRAGAntiContamination(unittest.TestCase):

    def test_search_never_drops_disease_id_filter(self):
        """When query returns 0 points, search should NEVER query without disease_id filter."""
        with patch.object(disease_retriever_v2, "embed", return_value=[0.1] * 1024):
            mock_qdrant = MagicMock()
            # Simulate 0 results returned on first query and second query
            mock_empty_points = MagicMock()
            mock_empty_points.points = []
            mock_qdrant.query_points.return_value = mock_empty_points
            
            with patch.object(disease_retriever_v2, "qdrant", mock_qdrant):
                results = disease_retriever_v2.search(
                    question="How to cure early blight?",
                    disease_id="early_blight",
                    intents=["organic_control"]
                )
                
                # Check all calls made to query_points
                self.assertEqual(len(results), 0)
                for call in mock_qdrant.query_points.call_args_list:
                    filter_arg = call.kwargs.get("query_filter")
                    self.assertIsNotNone(filter_arg, "query_filter must never be None when disease_id is provided!")
                    # Check must conditions contain disease_id
                    disease_conditions = [
                        c for c in filter_arg.must if getattr(c, "key", "") == "disease_id"
                    ]
                    self.assertGreater(len(disease_conditions), 0, "disease_id condition was illegally dropped!")

    def test_unindexed_disease_returns_empty_context(self):
        """Unindexed diseases must return empty context rather than chunks from other diseases."""
        context = disease_retriever_v2.build_context(
            question="What is the cure?",
            disease_id="non_existent_alien_pathogen_xyz",
            intents=["chemical_control"]
        )
        self.assertEqual(context.strip(), "")

if __name__ == "__main__":
    unittest.main()

