from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class SectionType(str, Enum):
    OVERVIEW = "overview"
    SYMPTOMS = "symptoms"
    CAUSES = "causes"
    ORGANIC_CONTROL = "organic_control"
    CHEMICAL_CONTROL = "chemical_control"
    PREVENTIVE_MEASURES = "preventive_measures"
    ENVIRONMENT = "environment"

class ContentType(str, Enum):
    OVERVIEW = "overview"
    DIAGNOSIS = "diagnosis"
    CAUSE_TRANSMISSION = "cause_transmission"
    TREATMENT = "treatment"
    PREVENTION = "prevention"
    ENVIRONMENT = "environment"

class NormalizedDisease(BaseModel):
    disease_id: str
    disease_name: str
    crop: Optional[str] = None
    host_crops: List[str] = Field(default_factory=list)
    disease_category: Optional[str] = None
    pathogen_name: Optional[str] = None
    
    overview: Optional[str] = None
    symptoms: Optional[str] = None
    causes: Optional[str] = None
    organic_control: Optional[str] = None
    chemical_control: Optional[str] = None
    preventive_measures: Optional[str] = None
    environment: Optional[Dict[str, Any]] = None
    
    tags: List[str] = Field(default_factory=list)

class DiseaseChunk(BaseModel):
    chunk_id: str
    disease_id: str
    disease_name: str
    crop: Optional[str] = None
    host_crops: List[str] = Field(default_factory=list)
    disease_category: Optional[str] = None
    
    section: SectionType
    section_title: str
    content_type: ContentType
    
    tags: List[str] = Field(default_factory=list)
    text: str
