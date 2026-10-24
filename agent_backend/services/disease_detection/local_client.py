"""
Local FastAPI Disease Detection Client.
Communicates with the local model service at POST /disease/predict.
"""
import os
import time
import logging
from pathlib import Path
from typing import Union, BinaryIO, Optional
import httpx
from pydantic import ValidationError

from config.settings import settings
from services.disease_detection.detector import DiseaseDetector
from services.disease_detection.schemas import DiseaseDetectionResult, DiseaseAPIResponse, TopPrediction
from services.disease_detection.exceptions import (
    LocalAPIUnavailableError,
    LocalAPITimeoutError,
    LocalAPIResponseError,
    InvalidImageError,
    EmptyPredictionError,
)

logger = logging.getLogger("disease_api_client")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}

def parse_plantvillage_label(canonical_label: str) -> dict:
    """
    Parses a PlantVillage-style label (e.g. 'Apple___Apple_scab' or 'Tomato___healthy')
    into crop, readable disease, is_healthy, and is_supported.
    """
    parts = canonical_label.split("___")
    if len(parts) == 2:
        crop_raw, disease_raw = parts
    else:
        crop_raw = "Unknown"
        disease_raw = canonical_label

    # Clean crop
    crop = crop_raw.replace("_(including_sour)", "").replace("_(maize)", "").replace(",_bell", "").replace("_", " ").strip().title()
    
    # Check if healthy
    is_healthy = "healthy" in disease_raw.lower()
    
    # Clean disease display name
    if is_healthy:
        disease_name = "Healthy"
    else:
        # replace underscores, normalize parentheses
        cleaned = disease_raw.replace("_", " ")
        cleaned = " ".join(cleaned.split())
        disease_name = cleaned.title()

    return {
        "crop": crop,
        "disease": disease_name,
        "is_healthy": is_healthy,
        "is_supported_crop": True
    }


class LocalDiseaseDetector(DiseaseDetector):
    """
    Shared client for the local FastAPI Disease Detection API.
    Endpoint: POST {base_url}/disease/predict
    Field: multipart/form-data 'file'
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        connect_timeout: Optional[float] = None,
        confidence_threshold: Optional[float] = None
    ):
        self.base_url = (base_url or settings.disease_api_url).rstrip("/")
        self.predict_url = f"{self.base_url}/disease/predict"
        self.timeout = timeout or getattr(settings, "disease_api_timeout_seconds", 30.0)
        self.connect_timeout = connect_timeout or getattr(settings, "disease_api_connect_timeout_seconds", 5.0)
        self.confidence_threshold = confidence_threshold or getattr(settings, "disease_confidence_threshold", 0.50)

    def _validate_file_path(self, file_path: Union[str, Path]) -> Path:
        path = Path(file_path)
        if not path.exists():
            raise InvalidImageError(f"Image file not found: {file_path}")
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            raise InvalidImageError(
                f"Unsupported file type '{path.suffix}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )
        return path

    def _determine_content_type(self, filename: str) -> str:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext in ("jpg", "jpeg"):
            return "image/jpeg"
        elif ext == "png":
            return "image/png"
        return "application/octet-stream"

    async def predict(self, image_input: Union[str, Path, bytes, BinaryIO], filename: Optional[str] = None) -> DiseaseDetectionResult:
        """
        Sends image to the local disease API and returns a validated DiseaseDetectionResult.
        """
        start_time = time.perf_counter()
        
        # Prepare file content
        file_bytes: bytes
        upload_name: str
        
        if isinstance(image_input, (str, Path)):
            path = self._validate_file_path(image_input)
            upload_name = filename or path.name
            try:
                with open(path, "rb") as f:
                    file_bytes = f.read()
            except Exception as e:
                raise InvalidImageError(f"Could not read image file '{path}': {e}") from e
        elif isinstance(image_input, bytes):
            file_bytes = image_input
            upload_name = filename or "leaf_image.jpg"
        elif hasattr(image_input, "read"):
            try:
                file_bytes = image_input.read()
                upload_name = filename or getattr(image_input, "filename", "leaf_image.jpg")
            except Exception as e:
                raise InvalidImageError(f"Failed to read file-like image object: {e}") from e
        else:
            raise InvalidImageError(f"Unsupported image input type: {type(image_input)}")

        if not file_bytes:
            raise InvalidImageError("Uploaded image file is empty (0 bytes).")

        content_type = self._determine_content_type(upload_name)
        files = {"file": (upload_name, file_bytes, content_type)}
        
        logger.info(f"Dispatching disease prediction request to {self.predict_url} (file: {upload_name}, size: {len(file_bytes)} bytes)")
        
        timeout_config = httpx.Timeout(self.timeout, connect=self.connect_timeout)
        
        try:
            async with httpx.AsyncClient(timeout=timeout_config) as client:
                response = await client.post(self.predict_url, files=files)
        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to local disease API at {self.base_url}: {e}")
            raise LocalAPIUnavailableError(
                f"The local disease prediction service is unreachable at {self.base_url}. "
                "Please verify that the local FastAPI service is running."
            ) from e
        except httpx.TimeoutException as e:
            logger.error(f"Timeout connecting to local disease API at {self.predict_url}: {e}")
            raise LocalAPITimeoutError(
                f"Request to local disease API timed out after {self.timeout}s."
            ) from e
        except httpx.RequestError as e:
            logger.error(f"Network error calling local disease API: {e}")
            raise LocalAPIUnavailableError(
                f"Network communication failure with disease API at {self.predict_url}: {e}"
            ) from e

        elapsed = time.perf_counter() - start_time
        logger.info(f"Local disease API responded with status {response.status_code} in {elapsed:.3f}s")

        if response.status_code == 400:
            detail = response.json().get("detail", response.text) if "application/json" in response.headers.get("content-type", "") else response.text
            raise InvalidImageError(f"Local disease API rejected image: {detail}")
        elif response.status_code == 422:
            raise LocalAPIResponseError(f"Local disease API validation error (422): {response.text}")
        elif response.status_code >= 500:
            raise LocalAPIResponseError(f"Local disease API server error ({response.status_code}): {response.text}")
        elif response.status_code != 200:
            raise LocalAPIResponseError(f"Unexpected status {response.status_code} from disease API: {response.text}")

        # Parse and validate JSON response
        try:
            data = response.json()
        except Exception as e:
            raise LocalAPIResponseError(f"Disease API returned non-JSON response: {response.text[:200]}") from e

        try:
            validated = DiseaseAPIResponse(**data)
        except ValidationError as e:
            raise LocalAPIResponseError(f"Invalid disease API response schema: {e}") from e

        if not validated.disease:
            raise EmptyPredictionError("Disease API returned an empty disease label.")

        # Validate confidence range
        if not (0.0 <= validated.confidence <= 1.0):
            logger.warning(f"Confidence score {validated.confidence} is outside [0, 1] range; clamping.")
            clamped_confidence = max(0.0, min(1.0, validated.confidence))
        else:
            clamped_confidence = validated.confidence

        parsed = parse_plantvillage_label(validated.disease)
        is_confident = clamped_confidence >= self.confidence_threshold

        return DiseaseDetectionResult(
            canonical_label=validated.disease,
            raw_label=validated.disease,
            crop=parsed["crop"],
            disease=parsed["disease"],
            confidence=clamped_confidence,
            is_confident=is_confident,
            is_supported_crop=parsed["is_supported_crop"],
            is_healthy=parsed["is_healthy"],
            top_predictions=validated.top_predictions
        )
