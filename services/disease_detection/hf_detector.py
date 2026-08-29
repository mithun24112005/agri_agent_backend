import asyncio
from typing import Union
from pathlib import Path
from huggingface_hub import AsyncInferenceClient
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

from config.settings import settings
from services.disease_detection.detector import DiseaseDetector
from services.disease_detection.schemas import DiseaseDetectionResult, TopPrediction
from services.disease_detection.label_mapper import LabelMapper
from services.disease_detection.exceptions import (
    HFNetworkError,
    HFTimeoutError,
    HFAuthenticationError,
    HFServiceError,
    InvalidImageError,
    EmptyPredictionError
)

class HFInferenceDetector(DiseaseDetector):
    def __init__(self):
        if not settings.hf_token:
            raise HFAuthenticationError("HF_TOKEN is missing from configuration.")
            
        self.model_id = settings.hf_disease_model
        self.client = AsyncInferenceClient(token=settings.hf_token)
        self.threshold = settings.disease_confidence_threshold
        
    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(settings.hf_max_retries),
        retry=retry_if_exception_type((HFNetworkError, HFTimeoutError, HFServiceError)),
        reraise=True
    )
    async def _predict_with_retry(self, image_input: Union[str, Path, bytes]):
        try:
            # InferenceClient automatically handles file paths, bytes, etc.
            # but we use asyncio to not block the main thread if there's any sync IO underneath.
            # AsyncInferenceClient handles it asynchronously.
            result = await self.client.image_classification(
                image_input, 
                model=self.model_id,
            )
            return result
        except Exception as e:
            error_str = str(e).lower()
            if "unauthorized" in error_str or "invalid token" in error_str:
                raise HFAuthenticationError("Invalid or unauthorized Hugging Face token.") from e
            elif "timeout" in error_str:
                raise HFTimeoutError("Hugging Face Inference API request timed out.") from e
            elif "500" in error_str or "502" in error_str or "503" in error_str:
                raise HFServiceError(f"Hugging Face Inference API service error: {e}") from e
            elif "getaddrinfo" in error_str or "connection" in error_str or "network" in error_str:
                raise HFNetworkError(f"Network error communicating with Hugging Face: {e}") from e
            elif "unsupported" in error_str or "invalid" in error_str:
                raise InvalidImageError(f"Invalid or unsupported image format: {e}") from e
            else:
                # Fallback mapping
                raise HFServiceError(f"Unexpected error during HF inference: {e}") from e

    async def predict(self, image_input: Union[str, Path, bytes]) -> DiseaseDetectionResult:
        
        # Verify file exists if it's a path
        if isinstance(image_input, (str, Path)):
            path = Path(image_input)
            if not path.exists():
                raise InvalidImageError(f"Image file not found: {image_input}")
            
        raw_predictions = await self._predict_with_retry(image_input)
        
        if not raw_predictions:
            raise EmptyPredictionError("Hugging Face model returned an empty prediction list.")
            
        top1 = raw_predictions[0]
        
        parsed = LabelMapper.parse_label(top1.label)
        
        top_k = []
        for p in raw_predictions[:3]:
            top_k.append(TopPrediction(label=p.label, confidence=p.score))
            
        return DiseaseDetectionResult(
            crop=parsed["crop"],
            disease=parsed["disease"],
            raw_label=top1.label,
            confidence=top1.score,
            is_confident=top1.score >= self.threshold,
            is_supported_crop=parsed["is_supported_crop"],
            is_healthy=parsed["is_healthy"],
            top_predictions=top_k
        )
