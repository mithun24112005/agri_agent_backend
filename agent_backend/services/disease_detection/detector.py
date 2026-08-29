from abc import ABC, abstractmethod
from typing import Union
from pathlib import Path
from services.disease_detection.schemas import DiseaseDetectionResult

class DiseaseDetector(ABC):
    """
    Abstract interface for disease detection.
    This abstraction allows swapping the detection model (e.g. Hugging Face vs Local)
    without affecting the core agent or API logic.
    """
    
    @abstractmethod
    async def predict(self, image_input: Union[str, Path, bytes]) -> DiseaseDetectionResult:
        """
        Takes an image input (file path or bytes) and returns a strongly typed detection result.
        Must handle its own retries and raise specific `DiseaseDetectionError` exceptions on failure.
        """
        pass
