"""
Comprehensive test suite for the restored Local Disease Detection API,
Label Normalization, Disease RAG, and End-to-End Disease Agent Workflow.
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

class TestLocalDiseaseAPIClient(unittest.IsolatedAsyncioTestCase):
    """Unit tests for the Local Disease Detection Client using mocked HTTP transport."""

    def setUp(self):
        self.detector = LocalDiseaseDetector(
            base_url="http://127.0.0.1:8000",
            timeout=5.0,
            connect_timeout=2.0,
            confidence_threshold=0.50
        )

    def test_parse_plantvillage_label(self):
        # Normal disease
        parsed = parse_plantvillage_label("Apple___Apple_scab")
        self.assertEqual(parsed["crop"], "Apple")
        self.assertEqual(parsed["disease"], "Apple Scab")
        self.assertFalse(parsed["is_healthy"])

        # Healthy label
        parsed_healthy = parse_plantvillage_label("Tomato___healthy")
        self.assertEqual(parsed_healthy["crop"], "Tomato")
        self.assertTrue(parsed_healthy["is_healthy"])

        # Complex label with parentheses and punctuation
        parsed_complex = parse_plantvillage_label("Grape___Esca_(Black_Measles)")
        self.assertEqual(parsed_complex["crop"], "Grape")
        self.assertIn("Esca (Black Measles)", parsed_complex["disease"])

    async def test_successful_prediction_parsing(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "disease": "Apple___Apple_scab",
            "confidence": 0.9998,
            "top_predictions": [
                {"label": "Apple___Apple_scab", "confidence": 0.9998},
                {"label": "Apple___healthy", "confidence": 0.0002},
                {"label": "Tomato___Spider_mites Two-spotted_spider_mite", "confidence": 0.0}
            ]
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            fake_bytes = b"fake_image_bytes"
            result = await self.detector.predict(fake_bytes, filename="leaf.jpg")

            self.assertEqual(result.canonical_label, "Apple___Apple_scab")
            self.assertEqual(result.crop, "Apple")
            self.assertEqual(result.disease, "Apple Scab")
            self.assertAlmostEqual(result.confidence, 0.9998)
            self.assertTrue(result.is_confident)
            self.assertFalse(result.is_healthy)
            self.assertEqual(len(result.top_predictions), 3)

            # Verify multipart form field name is 'file'
            call_kwargs = mock_post.call_args[1]
            self.assertIn("files", call_kwargs)
            self.assertIn("file", call_kwargs["files"])

    async def test_http_400_invalid_image(self):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"detail": "Unsupported file type 'txt'."}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            with self.assertRaises(InvalidImageError):
                await self.detector.predict(b"not an image", filename="leaf.jpg")

    async def test_http_422_validation_error(self):
        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.headers = {"content-type": "application/json"}
        mock_response.text = "Missing multipart field"

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            with self.assertRaises(LocalAPIResponseError):
                await self.detector.predict(b"bytes", filename="leaf.jpg")

    async def test_http_500_server_error(self):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.headers = {"content-type": "application/json"}
        mock_response.text = "Internal Model Error"

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            with self.assertRaises(LocalAPIResponseError):
                await self.detector.predict(b"bytes", filename="leaf.jpg")

    async def test_connection_refused_error(self):
        with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("Connection refused")):
            with self.assertRaises(LocalAPIUnavailableError):
                await self.detector.predict(b"bytes", filename="leaf.jpg")

    async def test_timeout_error(self):
        with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Read timeout")):
            with self.assertRaises(LocalAPITimeoutError):
                await self.detector.predict(b"bytes", filename="leaf.jpg")


class TestDiseaseMapperAndNormalization(unittest.TestCase):
    """Unit tests for the canonical PlantVillage disease label registry and normalizer."""

    def test_target_benchmark_labels(self):
        # 1. Apple Scab
        m1 = disease_mapper.map_prediction("Apple___Apple_scab")
        self.assertEqual(m1["disease_id"], "apple_scab")
        self.assertTrue(disease_mapper.exists(m1["disease_id"]))

        # 2. Cedar Apple Rust (properly recognized as cedar_apple_rust with exists=False)
        m2 = disease_mapper.map_prediction("Apple___Cedar_apple_rust")
        self.assertEqual(m2["disease_id"], "cedar_apple_rust")
        self.assertFalse(disease_mapper.exists(m2["disease_id"]))

        # 3. Peach Bacterial Spot
        m3 = disease_mapper.map_prediction("Peach___Bacterial_spot")
        self.assertEqual(m3["disease_id"], "bacterial_spot_on_stone_fruits")
        self.assertTrue(disease_mapper.exists(m3["disease_id"]))

        # 4. Tomato Late Blight
        m4 = disease_mapper.map_prediction("Tomato___Late_blight")
        self.assertEqual(m4["disease_id"], "tomato_late_blight")
        self.assertTrue(disease_mapper.exists(m4["disease_id"]))

        # 5. Grape Esca (Black Measles)
        m5 = disease_mapper.map_prediction("Grape___Esca_(Black_Measles)")
        self.assertEqual(m5["disease_id"], "esca")
        self.assertTrue(disease_mapper.exists(m5["disease_id"]))

        # 6. Tomato Spider Mites
        m6 = disease_mapper.map_prediction("Tomato___Spider_mites Two-spotted_spider_mite")
        self.assertEqual(m6["disease_id"], "spider_mites")
        self.assertTrue(disease_mapper.exists(m6["disease_id"]))

        # 7. Corn Gray Leaf Spot
        m7 = disease_mapper.map_prediction("Corn___Cercospora_leaf_spot Gray_leaf_spot")
        self.assertEqual(m7["disease_id"], "grey_leaf_spot_of_maize")
        self.assertTrue(disease_mapper.exists(m7["disease_id"]))

    def test_normalization_and_case_variation(self):
        # Irregular casing and underscores
        m = disease_mapper.map_prediction("apple___apple_scab")
        self.assertEqual(m["disease_id"], "apple_scab")

        # Spaces and mixed punctuation
        m_space = disease_mapper.map_prediction("Corn (maize)___Common_rust_")
        self.assertEqual(m_space["disease_id"], "common_rust_of_maize")

    def test_healthy_classification(self):
        m = disease_mapper.map_prediction("Tomato___healthy")
        self.assertTrue(m["is_healthy"])
        self.assertEqual(m["crop"], "tomato")


class TestDiseaseRetrieverFallback(unittest.TestCase):
    """Unit tests for Disease RAG context building and offline fallback."""

    def test_local_dataset_fallback_retrieval(self):
        # When vector search returns empty / fails, local dataset must retrieve verified knowledge
        context = disease_retriever_v2.build_context(
            question="What are the symptoms and organic controls?",
            disease_id="apple_scab",
            intents=["symptoms", "organic_control"]
        )
        self.assertTrue(len(context) > 0)
        self.assertIn("Symptoms", context)
        self.assertIn("Organic Control", context)

    def test_missing_knowledge_returns_empty_context(self):
        # When disease_id is not in local dataset, return empty string for insufficient_evidence handling
        context = disease_retriever_v2.build_context(
            question="What is the cure?",
            disease_id="non_existent_fake_disease_123",
            intents=["chemical_control"]
        )
        self.assertEqual(context.strip(), "")


class TestLiveLocalAPIIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests against the live local FastAPI service on port 8000."""

    async def test_live_prediction_endpoint(self):
        test_dir = Path(r"D:/major_backend/agent_backend/testdisease")
        sample_img = test_dir / "Apple___Apple_scab_00075aa8-d81a-4184-8541-b692b78d398a___FREC_Scab 3335_270deg.JPG"
        if not sample_img.exists():
            self.skipTest(f"Test image not found at {sample_img}")

        detector = LocalDiseaseDetector(base_url="http://127.0.0.1:8000")
        try:
            res = await detector.predict(sample_img)
            self.assertEqual(res.canonical_label, "Apple___Apple_scab")
            self.assertGreater(res.confidence, 0.90)
            self.assertTrue(res.is_confident)
            self.assertEqual(len(res.top_predictions), 3)
            print(f"\n[LIVE API PASS] Predicted: {res.canonical_label} with confidence {res.confidence:.4f}")
        except LocalAPIUnavailableError:
            self.skipTest("Local API at http://127.0.0.1:8000 is not running.")


if __name__ == "__main__":
    unittest.main()
