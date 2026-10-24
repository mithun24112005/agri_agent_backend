"""
Exceptions for disease detection services.
"""

class DiseaseDetectionError(Exception):
    """Base exception for all disease detection failures."""
    pass

class LocalAPIUnavailableError(DiseaseDetectionError):
    """Raised when the local FastAPI disease prediction service (e.g. http://localhost:8000) is unreachable."""
    pass

class LocalAPITimeoutError(DiseaseDetectionError):
    """Raised when the local disease prediction service request times out."""
    pass

class LocalAPIResponseError(DiseaseDetectionError):
    """Raised when the local disease prediction API returns an unexpected error code or malformed JSON."""
    pass

class InvalidImageError(DiseaseDetectionError):
    """Raised when the provided image is corrupted, unreadable, or has an unsupported format."""
    pass

class EmptyPredictionError(DiseaseDetectionError):
    """Raised when the prediction service returns an empty list or missing prediction."""
    pass

# Retain HF-specific exceptions for backward compatibility with existing tests/handlers
class HFNetworkError(LocalAPIUnavailableError):
    pass

class HFTimeoutError(LocalAPITimeoutError):
    pass

class HFAuthenticationError(DiseaseDetectionError):
    pass

class HFServiceError(LocalAPIResponseError):
    pass
