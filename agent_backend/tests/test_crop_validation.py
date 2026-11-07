"""
Unit tests for Crop Model Service:
- Physical rejection bounds (negative values, out-of-scale pH, non-numeric, NaNs).
- Out-of-Distribution (OOD) acceptance with warnings.
- Probability estimation via predict_proba() top-k ranking.
"""
import unittest
import math
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from pydantic import ValidationError
from services.crop_model import crop_model_service, CropInputParameters

class TestCropModelValidation(unittest.TestCase):

    def test_physical_validation_rejections(self):
        """Physically impossible agricultural inputs must raise ValidationError."""
        # 1. Negative Nitrogen
        with self.assertRaises(ValidationError):
            CropInputParameters(N=-10.0, P=50.0, K=50.0, temperature=25.0, humidity=60.0, ph=6.5, rainfall=100.0)

        # 2. Negative Rainfall
        with self.assertRaises(ValidationError):
            CropInputParameters(N=50.0, P=50.0, K=50.0, temperature=25.0, humidity=60.0, ph=6.5, rainfall=-5.0)

        # 3. Humidity > 100%
        with self.assertRaises(ValidationError):
            CropInputParameters(N=50.0, P=50.0, K=50.0, temperature=25.0, humidity=120.0, ph=6.5, rainfall=100.0)

        # 4. pH > 14.0 or < 0.0
        with self.assertRaises(ValidationError):
            CropInputParameters(N=50.0, P=50.0, K=50.0, temperature=25.0, humidity=60.0, ph=15.0, rainfall=100.0)

        # 5. NaN or Infinity
        with self.assertRaises(ValidationError):
            CropInputParameters(N=float("nan"), P=50.0, K=50.0, temperature=25.0, humidity=60.0, ph=6.5, rainfall=100.0)

    def test_out_of_distribution_warning_handling(self):
        """Values exceeding training distribution but physically valid must be accepted with an OOD warning."""
        # N=180.0 is physically valid (heavy fertilization) but exceeds training max (140.0)
        res = crop_model_service.predict_crop(
            n=180.0, p=50.0, k=50.0,
            temperature=25.0, humidity=60.0, ph=6.5, rainfall=100.0
        )
        self.assertIn("recommended_crop", res)
        self.assertTrue(res["is_out_of_distribution"])
        self.assertGreater(len(res["ood_warnings"]), 0)
        self.assertTrue(any("N value (180.0) is higher" in w for w in res["ood_warnings"]))

    def test_in_distribution_prediction(self):
        """Standard in-distribution values should produce 0 OOD warnings."""
        res = crop_model_service.predict_crop(
            n=90.0, p=42.0, k=43.0,
            temperature=21.0, humidity=82.0, ph=6.5, rainfall=200.0
        )
        self.assertEqual(res["recommended_crop"], "rice")
        self.assertFalse(res["is_out_of_distribution"])
        self.assertEqual(len(res["ood_warnings"]), 0)

    def test_predict_proba_top_candidates(self):
        """Top-k candidates must be ranked with tree-vote probabilities."""
        res = crop_model_service.predict_crop(
            n=90.0, p=42.0, k=43.0,
            temperature=21.0, humidity=82.0, ph=6.5, rainfall=200.0,
            top_k=3
        )
        top_candidates = res["top_candidates"]
        self.assertEqual(len(top_candidates), 3)
        self.assertEqual(top_candidates[0]["rank"], 1)
        self.assertEqual(top_candidates[0]["crop"], "rice")
        
        # Probabilities must be descending
        self.assertGreaterEqual(top_candidates[0]["probability"], top_candidates[1]["probability"])
        self.assertGreaterEqual(top_candidates[1]["probability"], top_candidates[2]["probability"])
        
        # All individual probabilities must be in [0, 1]
        for c in top_candidates:
            self.assertGreaterEqual(c["probability"], 0.0)
            self.assertLessEqual(c["probability"], 1.0)
            self.assertFalse(c["is_calibrated"])

if __name__ == "__main__":
    unittest.main()

