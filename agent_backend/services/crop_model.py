import math
from typing import Dict, Any, List, Optional
import joblib
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field, field_validator
from config.settings import settings

# Training distribution baselines derived from Crop_recommendation.csv (2200 samples)
TRAINING_DISTRIBUTION = {
    "N": {"min": 0.0, "max": 140.0, "mean": 50.55},
    "P": {"min": 5.0, "max": 145.0, "mean": 53.36},
    "K": {"min": 5.0, "max": 205.0, "mean": 48.15},
    "temperature": {"min": 8.8, "max": 43.7, "mean": 25.62},
    "humidity": {"min": 14.3, "max": 100.0, "mean": 71.48},
    "ph": {"min": 3.5, "max": 9.9, "mean": 6.47},
    "rainfall": {"min": 20.2, "max": 298.6, "mean": 103.46},
}

class CropInputParameters(BaseModel):
    """
    Physical domain validation model for crop recommendation parameters.
    Enforces strict physical boundaries (hard reject) while capturing
    out-of-distribution values for agronomic warnings.
    """
    N: float = Field(..., description="Nitrogen availability index")
    P: float = Field(..., description="Phosphorus availability index")
    K: float = Field(..., description="Potassium availability index")
    temperature: float = Field(..., description="Temperature in Celsius")
    humidity: float = Field(..., description="Relative humidity percentage")
    ph: float = Field(..., description="Soil pH value")
    rainfall: float = Field(..., description="Rainfall in millimeters")

    @field_validator("N", "P", "K", "rainfall", mode="before")
    @classmethod
    def validate_non_negative(cls, v, info):
        try:
            val = float(v)
        except (ValueError, TypeError):
            raise ValueError(f"{info.field_name} must be a valid numeric value.")
        if math.isnan(val) or math.isinf(val):
            raise ValueError(f"{info.field_name} cannot be NaN or Infinite.")
        if val < 0.0:
            raise ValueError(f"{info.field_name} cannot be negative (physically invalid).")
        return val

    @field_validator("temperature", mode="before")
    @classmethod
    def validate_temperature(cls, v):
        try:
            val = float(v)
        except (ValueError, TypeError):
            raise ValueError("Temperature must be a valid numeric value.")
        if math.isnan(val) or math.isinf(val):
            raise ValueError("Temperature cannot be NaN or Infinite.")
        if val < -50.0 or val > 70.0:
            raise ValueError(f"Temperature {val}°C is outside plausible terrestrial agricultural limits (-50°C to 70°C).")
        return val

    @field_validator("humidity", mode="before")
    @classmethod
    def validate_humidity(cls, v):
        try:
            val = float(v)
        except (ValueError, TypeError):
            raise ValueError("Humidity must be a valid numeric value.")
        if math.isnan(val) or math.isinf(val):
            raise ValueError("Humidity cannot be NaN or Infinite.")
        if val < 0.0 or val > 100.0:
            raise ValueError(f"Relative humidity {val}% must be between 0% and 100%.")
        return val

    @field_validator("ph", mode="before")
    @classmethod
    def validate_ph(cls, v):
        try:
            val = float(v)
        except (ValueError, TypeError):
            raise ValueError("Soil pH must be a valid numeric value.")
        if math.isnan(val) or math.isinf(val):
            raise ValueError("Soil pH cannot be NaN or Infinite.")
        if val < 0.0 or val > 14.0:
            raise ValueError(f"Soil pH {val} is outside the standard chemical pH scale (0.0 to 14.0).")
        return val


class CropModelService:
    def __init__(self):
        print("Loading Crop Recommendation Model...")
        self.model = joblib.load(settings.crop_model_path)
        self.target_encoder = joblib.load(settings.target_encoder_path)
        print("[SUCCESS] Random Forest Model Loaded")
        print("[SUCCESS] Target Encoder Loaded")
        
        self.PH_CATEGORY_MAP = {
            "Acidic": 0,
            "Alkaline": 1,
            "Neutral": 2
        }

        self.RAINFALL_LEVEL_MAP = {
            "High": 0,
            "Low": 1,
            "Medium": 2,
            "Very High": 3
        }

    def detect_ood_warnings(self, params: Dict[str, float]) -> List[str]:
        """
        Detect parameters that are physically valid but fall outside the model's
        empirical training distribution, generating transparent agricultural warnings.
        """
        warnings = []
        for key, bounds in TRAINING_DISTRIBUTION.items():
            val = params.get(key)
            if val is not None:
                if val < bounds["min"]:
                    warnings.append(
                        f"{key} value ({val}) is lower than the model's training range "
                        f"({bounds['min']} - {bounds['max']}). Recommendation fidelity may be reduced."
                    )
                elif val > bounds["max"]:
                    warnings.append(
                        f"{key} value ({val}) is higher than the model's training range "
                        f"({bounds['min']} - {bounds['max']}). Recommendation fidelity may be reduced."
                    )
        return warnings

    def classify_ph(self, ph: float) -> str:
        if ph < 5.5:
            return "Acidic"
        elif ph <= 7.5:
            return "Neutral"
        else:
            return "Alkaline"
            
    def classify_rainfall(self, rainfall: float) -> str:
        if rainfall <= 50:
            return "Low"
        elif rainfall <= 100:
            return "Medium"
        elif rainfall <= 200:
            return "High"
        else:
            return "Very High"
            
    def prepare_features(self, n: float, p: float, k: float, temperature: float, humidity: float, ph: float, rainfall: float):
        ph_category = self.classify_ph(ph)
        rainfall_level = self.classify_rainfall(rainfall)

        features = pd.DataFrame([{
            "N": n,
            "P": p,
            "K": k,
            "temperature": temperature,
            "humidity": humidity,
            "ph": ph,
            "rainfall": rainfall,
            "NPK_mean": (n + p + k) / 3,
            "THI": (temperature * humidity) / 100,
            "ph_category": self.PH_CATEGORY_MAP[ph_category],
            "rainfall_level": self.RAINFALL_LEVEL_MAP[rainfall_level],
        }])

        return {
            "features": features,
            "ph_category": ph_category,
            "rainfall_level": rainfall_level,
        }

    def predict_crop(self, n: float, p: float, k: float, temperature: float, humidity: float, ph: float, rainfall: float, top_k: int = 3) -> Dict[str, Any]:
        """
        Validates inputs, predicts primary recommended crop and top-k candidate crops
        using Random Forest probability estimates, and flags out-of-distribution values.
        """
        # 1. Enforce strict physical validation
        validated = CropInputParameters(
            N=n, P=p, K=k,
            temperature=temperature,
            humidity=humidity,
            ph=ph,
            rainfall=rainfall
        )

        # 2. Check for out-of-distribution conditions
        input_dict = validated.model_dump()
        ood_warnings = self.detect_ood_warnings(input_dict)

        # 3. Feature preparation matching training pipeline
        prepared = self.prepare_features(
            validated.N, validated.P, validated.K,
            validated.temperature, validated.humidity,
            validated.ph, validated.rainfall
        )
        features = prepared["features"]
        
        # 4. Model inference
        prediction = self.model.predict(features)[0]
        primary_crop = self.target_encoder.inverse_transform([prediction])[0]

        # 5. Extract top-k candidates using predict_proba where available
        top_candidates = []
        if hasattr(self.model, "predict_proba"):
            probs = self.model.predict_proba(features)[0]
            # Order indices descending by probability
            top_indices = np.argsort(probs)[::-1][:top_k]
            for rank, idx in enumerate(top_indices, start=1):
                crop_name = self.target_encoder.inverse_transform([idx])[0]
                prob_val = float(probs[idx])
                top_candidates.append({
                    "crop": crop_name,
                    "rank": rank,
                    "tree_vote_share": round(prob_val, 4),
                    "probability": round(prob_val, 4),
                    "is_calibrated": False
                })
        else:
            top_candidates.append({
                "crop": primary_crop,
                "rank": 1,
                "tree_vote_share": 1.0,
                "probability": 1.0,
                "is_calibrated": False
            })

        return {
            "recommended_crop": primary_crop,
            "top_candidates": top_candidates,
            "ood_warnings": ood_warnings,
            "is_out_of_distribution": len(ood_warnings) > 0,
            "probability_type": "tree_vote_share",
            "is_calibrated_confidence": False,
            "input_parameters": input_dict,
            "derived_features": {
                "NPK_mean": float(features["NPK_mean"].iloc[0]),
                "THI": float(features["THI"].iloc[0]),
                "ph_category": prepared["ph_category"],
                "rainfall_level": prepared["rainfall_level"]
            }
        }

# Global singleton instance
crop_model_service = CropModelService()
