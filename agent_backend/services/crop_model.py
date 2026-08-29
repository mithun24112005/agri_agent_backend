import joblib
import pandas as pd
from config.settings import settings

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

    def predict_crop(self, n: float, p: float, k: float, temperature: float, humidity: float, ph: float, rainfall: float):
        prepared = self.prepare_features(n, p, k, temperature, humidity, ph, rainfall)
        features = prepared["features"]
        
        prediction = self.model.predict(features)[0]
        crop = self.target_encoder.inverse_transform([prediction])[0]

        return {
            "recommended_crop": crop,
            "input_parameters": {
                "N": n,
                "P": p,
                "K": k,
                "temperature": temperature,
                "humidity": humidity,
                "ph": ph,
                "rainfall": rainfall,
            },
            "derived_features": {
                "NPK_mean": float(features["NPK_mean"].iloc[0]),
                "THI": float(features["THI"].iloc[0]),
                "ph_category": prepared["ph_category"],
                "rainfall_level": prepared["rainfall_level"]
            }
        }

# Global singleton instance
crop_model_service = CropModelService()
