"""
Pydantic schemas for the Disease Detection API contract and agent results.
"""
from typing import List, Optional
from pydantic import BaseModel, Field

class TopPrediction(BaseModel):
    label: str = Field(description="The predicted class label (e.g., 'Apple___Apple_scab')")
    confidence: float = Field(description="Confidence score for this prediction (0.0 to 1.0)")

class DiseaseAPIResponse(BaseModel):
    """
    Direct model matching the actual response contract of POST /disease/predict:
    {
      "disease": "Apple___Apple_scab",
      "confidence": 0.9998,
      "top_predictions": [
        {"label": "Apple___Apple_scab", "confidence": 0.9998},
        {"label": "Apple___healthy", "confidence": 0.0002},
        ...
      ]
    }
    """
    disease: str = Field(description="Primary predicted disease class")
    confidence: float = Field(description="Primary prediction confidence score")
    top_predictions: List[TopPrediction] = Field(default_factory=list, description="Top-k predictions")

class DiseaseDetectionResult(BaseModel):
    """
    Rich typed detection result used across the Disease Agent and Supervisor Graph.
    """
    canonical_label: str = Field(description="The exact canonical label from the model (e.g. 'Apple___Apple_scab')")
    raw_label: str = Field(description="Alias for canonical_label for backward compatibility")
    crop: str = Field(description="Extracted or resolved crop name (e.g. 'apple')")
    disease: str = Field(description="Clean/readable disease name (e.g. 'Apple Scab', or 'healthy')")
    confidence: float = Field(description="Confidence score of top prediction")
    is_confident: bool = Field(description="Whether confidence meets threshold")
    is_supported_crop: bool = Field(default=True, description="Whether the crop is known/supported")
    is_healthy: bool = Field(default=False, description="Whether the leaf was classified as healthy")
    top_predictions: List[TopPrediction] = Field(default_factory=list, description="Top predictions")

class DiseaseDetectionErrorResponse(BaseModel):
    error: str
    message: str
