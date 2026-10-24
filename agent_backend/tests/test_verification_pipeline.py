"""
Ordered verification pipeline following Requirement 10:
1. API-client unit tests
2. Mapper tests
3. RAG tests
4. Graph tests
5. Live API integration
6. Full application regression tests
"""
import os
import unittest
from unittest.mock import patch, AsyncMock, MagicMock
from pathlib import Path
import httpx

from config.settings import settings
from services.disease_detection.local_client import LocalDiseaseDetector, parse_plantvillage_label
from services.disease_detection.schemas import DiseaseDetectionResult, DiseaseAPIResponse
from services.disease_detection.exceptions import (
    LocalAPIUnavailableError,
    LocalAPITimeoutError,
    LocalAPIResponseError,
    InvalidImageError,
    EmptyPredictionError
)
from agents.disease.mapper import disease_mapper
from agents.disease.retriever import disease_retriever_v2
from agents.disease.graph import disease_graph


# ==========================================
# Group 1: API-client Unit Tests
# ==========================================
class TestGroup1APIClient(unittest.IsolatedAsyncioTestCase):
    """Group 1: Transport, multipart upload, timeout, error parsing."""

    def setUp(self):
        self.detector = LocalDiseaseDetector(
            base_url="http://127.0.0.1:8000",
            timeout=5.0,
            connect_timeout=2.0,
            confidence_threshold=0.50
        )

    async def test_successful_request_and_response_parsing(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "disease": "Apple___Apple_scab",
            "confidence": 0.9998,
            "top_predictions": [
                {"label": "Apple___Apple_scab", "confidence": 0.9998},
                {"label": "Apple___healthy", "confidence": 0.0002},
                {"label": "Tomato___Septoria_leaf_spot", "confidence": 0.0}
            ]
        }
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            res = await self.detector.predict(b"fake_bytes", filename="leaf.jpg")
            self.assertEqual(res.canonical_label, "Apple___Apple_scab")
            self.assertEqual(res.crop, "Apple")
            self.assertEqual(res.disease, "Apple Scab")
            self.assertAlmostEqual(res.confidence, 0.9998)
            # Check multipart field name 'file'
            call_kwargs = mock_post.call_args[1]
            self.assertIn("file", call_kwargs["files"])

    async def test_http_400_invalid_image(self):
        mock_response = MagicMock(status_code=400, headers={"content-type": "application/json"})
        mock_response.json.return_value = {"detail": "Unsupported file extension"}
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            with self.assertRaises(InvalidImageError):
                await self.detector.predict(b"bytes", filename="test.jpg")

    async def test_http_422_validation_error(self):
        mock_response = MagicMock(status_code=422, headers={"content-type": "application/json"})
        mock_response.text = "Missing file field"
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            with self.assertRaises(LocalAPIResponseError):
                await self.detector.predict(b"bytes", filename="test.jpg")

    async def test_http_500_server_error(self):
        mock_response = MagicMock(status_code=500, headers={"content-type": "application/json"})
        mock_response.text = "Model inference crashed"
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            with self.assertRaises(LocalAPIResponseError):
                await self.detector.predict(b"bytes", filename="test.jpg")

    async def test_connection_refused(self):
        with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("Connection refused")):
            with self.assertRaises(LocalAPIUnavailableError):
                await self.detector.predict(b"bytes", filename="test.jpg")

    async def test_timeout(self):
        with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Read timeout")):
            with self.assertRaises(LocalAPITimeoutError):
                await self.detector.predict(b"bytes", filename="test.jpg")


# ==========================================
# Group 2: Mapper Tests
# ==========================================
class TestGroup2Mapper(unittest.TestCase):
    """Group 2: Canonical label preservation, crop extraction, and verified knowledge base IDs."""

    def test_canonical_preservation_and_exact_mapping(self):
        cases = [
            ("Apple___Apple_scab", "apple_scab", "apple", True),
            ("Apple___Cedar_apple_rust", "cedar_apple_rust", "apple", False),
            ("Peach___Bacterial_spot", "bacterial_spot_on_stone_fruits", "peach", True),
            ("Tomato___Late_blight", "tomato_late_blight", "tomato", True),
            ("Grape___Esca_(Black_Measles)", "esca", "grape", True),
            ("Tomato___Spider_mites Two-spotted_spider_mite", "spider_mites", "tomato", True),
            ("Corn___Cercospora_leaf_spot Gray_leaf_spot", "grey_leaf_spot_of_maize", "corn", True),
        ]
        for canonical, expected_id, expected_crop, expected_exists in cases:
            mapped = disease_mapper.map_prediction(canonical)
            self.assertEqual(mapped["canonical_label"], canonical)
            self.assertEqual(mapped["disease_id"], expected_id)
            self.assertEqual(mapped["crop"], expected_crop)
            self.assertEqual(disease_mapper.exists(mapped["disease_id"]), expected_exists)

    def test_healthy_plants(self):
        mapped = disease_mapper.map_prediction("Apple___healthy")
        self.assertTrue(mapped["is_healthy"])
        self.assertEqual(mapped["crop"], "apple")


# ==========================================
# Group 3: RAG Tests
# ==========================================
class TestGroup3RAG(unittest.TestCase):
    """Group 3: Verified evidence retrieval, filtering, and transparent fallback."""

    def test_verified_evidence_retrieval(self):
        context = disease_retriever_v2.build_context(
            question="What are symptoms and organic treatments?",
            disease_id="apple_scab",
            intents=["symptoms", "organic_control"]
        )
        self.assertTrue(len(context) > 0)
        self.assertIn("Symptoms", context)
        self.assertIn("Organic Control", context)

    def test_unindexed_disease_returns_empty_for_fallback(self):
        context = disease_retriever_v2.build_context(
            question="What is the cure?",
            disease_id="cedar_apple_rust",  # Unindexed disease
            intents=["chemical_control"]
        )
        self.assertEqual(context.strip(), "")


# ==========================================
# Group 4: Disease Graph Workflow Tests
# ==========================================
class TestGroup4Graph(unittest.IsolatedAsyncioTestCase):
    """Group 4: Workflow orchestration, state propagation, and LLM synthesis."""

    async def test_unindexed_disease_insufficient_evidence_flow(self):
        res = await disease_graph.ainvoke({
            "question": "How to treat this disease?",
            "prediction": "Apple___Cedar_apple_rust"
        })
        self.assertEqual(res["prediction"], "Apple___Cedar_apple_rust")
        self.assertEqual(res["disease_id"], "cedar_apple_rust")
        self.assertEqual(res["rag_status"], "insufficient_evidence")
        self.assertTrue(len(res["response"]) > 0)

    async def test_healthy_plant_flow(self):
        res = await disease_graph.ainvoke({
            "question": "Is my crop sick?",
            "prediction": "Tomato___healthy"
        })
        self.assertEqual(res["rag_status"], "healthy_plant")
        self.assertTrue(res["is_healthy"])
        self.assertIn("Healthy", res["response"])


# ==========================================
# Group 5: Live API Integration Tests
# ==========================================
class TestGroup5LiveAPI(unittest.IsolatedAsyncioTestCase):
    """Group 5: Real HTTP requests against local service at port 8000 using test images."""

    async def test_live_prediction_endpoint_apple_scab(self):
        sample_img = Path("D:/major_backend/agent_backend/testdisease/Apple___Apple_scab_00075aa8-d81a-4184-8541-b692b78d398a___FREC_Scab 3335_270deg.JPG")
        if not sample_img.exists():
            self.skipTest("Sample image not found")
        detector = LocalDiseaseDetector(base_url="http://127.0.0.1:8000")
        res = await detector.predict(sample_img)
        self.assertEqual(res.canonical_label, "Apple___Apple_scab")
        self.assertGreater(res.confidence, 0.90)
        self.assertEqual(len(res.top_predictions), 3)

    async def test_live_prediction_endpoint_potato_late_blight(self):
        sample_img = Path("D:/major_backend/agent_backend/testdisease/Potato___Late_blight_00695906-210d-4a9d-822e-986a17384115___RS_LB 4026.JPG")
        if not sample_img.exists():
            self.skipTest("Sample image not found")
        detector = LocalDiseaseDetector(base_url="http://127.0.0.1:8000")
        res = await detector.predict(sample_img)
        self.assertEqual(res.canonical_label, "Potato___Late_blight")
        self.assertGreater(res.confidence, 0.90)

    async def test_live_prediction_endpoint_tomato_early_blight(self):
        sample_img = Path("D:/major_backend/agent_backend/testdisease/Tomato___Early_blight_0012b9d2-2130-4a06-a834-b1f3af34f57e___RS_Erly.B 8389.JPG")
        if not sample_img.exists():
            self.skipTest("Sample image not found")
        detector = LocalDiseaseDetector(base_url="http://127.0.0.1:8000")
        res = await detector.predict(sample_img)
        self.assertEqual(res.canonical_label, "Tomato___Early_blight")
        self.assertGreater(res.confidence, 0.50)


# ==========================================
# Group 6: Full Application Regression Tests
# ==========================================
class TestGroup6Regression(unittest.IsolatedAsyncioTestCase):
    """Group 6: Non-regression of supervisor routing, crop recommendation, and general assistance."""

    async def test_crop_agent_non_regression(self):
        from agents.crop.graph import crop_graph
        crop_input = {
            "input_parameters": {
                "N": 90, "P": 42, "K": 43,
                "temperature": 21.0, "humidity": 82.0, "ph": 6.5, "rainfall": 200.0
            }
        }
        res = await crop_graph.ainvoke(crop_input)
        self.assertIn("recommended_crop", res)
        self.assertTrue(len(res.get("explanation", "")) > 0)


if __name__ == "__main__":
    unittest.main()
