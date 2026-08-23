from pydantic import BaseModel
from typing import List

class DiseasePredictionLabel(BaseModel):
    label: str
    confidence: float

class DiseaseAPIResponse(BaseModel):
    disease: str
    confidence: float
    top_predictions: List[DiseasePredictionLabel]
