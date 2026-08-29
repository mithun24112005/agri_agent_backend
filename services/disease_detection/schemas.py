from pydantic import BaseModel, Field
from typing import List, Optional

class TopPrediction(BaseModel):
    label: str
    confidence: float

class DiseaseDetectionResult(BaseModel):
    crop: str = Field(description="The normalized crop name (e.g. 'Apple')")
    disease: str = Field(description="The normalized disease name (e.g. 'Apple Scab', or 'healthy')")
    raw_label: str = Field(description="The exact human-readable label from the model")
    confidence: float = Field(description="The confidence score of the top prediction")
    is_confident: bool = Field(description="Whether the confidence exceeds the threshold")
    is_supported_crop: bool = Field(description="Whether the crop is fully supported by the model (Apple, Maize/Corn, Grape, Orange)")
    is_healthy: bool = Field(description="Whether the plant is classified as healthy")
    top_predictions: List[TopPrediction] = Field(description="The top K predictions from the model")

class DiseaseDetectionErrorResponse(BaseModel):
    error: str
    message: str
