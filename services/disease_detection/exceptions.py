class DiseaseDetectionError(Exception):
    """Base exception for disease detection failures."""
    pass

class HFNetworkError(DiseaseDetectionError):
    """Raised when there is a network or DNS failure communicating with Hugging Face."""
    pass

class HFTimeoutError(DiseaseDetectionError):
    """Raised when the Hugging Face API times out."""
    pass

class HFAuthenticationError(DiseaseDetectionError):
    """Raised when the HF token is invalid or unauthorized."""
    pass

class HFServiceError(DiseaseDetectionError):
    """Raised when the Hugging Face Inference service returns a server error (50x)."""
    pass

class InvalidImageError(DiseaseDetectionError):
    """Raised when the uploaded image is invalid or unreadable."""
    pass

class EmptyPredictionError(DiseaseDetectionError):
    """Raised when the model returns an empty list of predictions."""
    pass
