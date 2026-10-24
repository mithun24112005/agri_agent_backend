"""
Disease detection service package.
Exports the shared local disease detector singleton instance.
"""
from services.disease_detection.local_client import LocalDiseaseDetector
from services.disease_detection.schemas import DiseaseDetectionResult, DiseaseAPIResponse, TopPrediction
from services.disease_detection.exceptions import (
    DiseaseDetectionError,
    LocalAPIUnavailableError,
    LocalAPITimeoutError,
    LocalAPIResponseError,
    InvalidImageError,
    EmptyPredictionError,
)

# Shared singleton instance for the local disease detection service
detector = LocalDiseaseDetector()

__all__ = [
    "detector",
    "LocalDiseaseDetector",
    "DiseaseDetectionResult",
    "DiseaseAPIResponse",
    "TopPrediction",
    "DiseaseDetectionError",
    "LocalAPIUnavailableError",
    "LocalAPITimeoutError",
    "LocalAPIResponseError",
    "InvalidImageError",
    "EmptyPredictionError",
]
