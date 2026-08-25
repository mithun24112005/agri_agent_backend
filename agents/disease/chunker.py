import uuid
from typing import List, Dict, Tuple
from agents.disease.models import NormalizedDisease, DiseaseChunk, SectionType, ContentType

def build_identity_header(disease: NormalizedDisease, topic: str) -> str:
    lines = [f"Disease: {disease.disease_name}"]
    if disease.crop:
        lines.append(f"Crop: {disease.crop.title()}")
    if disease.disease_category:
        lines.append(f"Disease Category: {disease.disease_category}")
    lines.append("")
    lines.append(f"Topic: {topic}")
    lines.append("")
    return "\n".join(lines)

def generate_semantic_chunks(disease: NormalizedDisease) -> List[DiseaseChunk]:
    chunks = []
    
    # Define mapping from attribute to (SectionType, ContentType, Title)
    sections: List[Tuple[str, SectionType, ContentType, str]] = [
        ("overview", SectionType.OVERVIEW, ContentType.OVERVIEW, "Overview"),
        ("symptoms", SectionType.SYMPTOMS, ContentType.DIAGNOSIS, "Symptoms"),
        ("causes", SectionType.CAUSES, ContentType.CAUSE_TRANSMISSION, "Causes"),
        ("organic_control", SectionType.ORGANIC_CONTROL, ContentType.TREATMENT, "Organic Control"),
        ("chemical_control", SectionType.CHEMICAL_CONTROL, ContentType.TREATMENT, "Chemical Control"),
        ("preventive_measures", SectionType.PREVENTIVE_MEASURES, ContentType.PREVENTION, "Preventive Measures")
    ]
    
    for attr, sec_type, content_type, title in sections:
        content = getattr(disease, attr)
        if content:
            header = build_identity_header(disease, title)
            text = f"{header}\n{title} for {disease.disease_name}:\n{content}"
            
            chunk_id = f"{disease.disease_id}::{sec_type.value}"
            
            chunks.append(DiseaseChunk(
                chunk_id=chunk_id,
                disease_id=disease.disease_id,
                disease_name=disease.disease_name,
                crop=disease.crop,
                host_crops=disease.host_crops,
                disease_category=disease.disease_category,
                section=sec_type,
                section_title=title,
                content_type=content_type,
                tags=disease.tags,
                text=text
            ))
            
    # Handle Environment specifically
    if disease.environment:
        env = disease.environment
        # Check if there's substantial info. If only 'season' is present, skip creating a chunk.
        meaningful_keys = [k for k, v in env.items() if k != "season" and v]
        if meaningful_keys:
            title = "Environment Conditions"
            header = build_identity_header(disease, title)
            
            env_text_parts = [f"{k.capitalize()}: {v}" for k, v in env.items() if v]
            env_text = "\n".join(env_text_parts)
            
            text = f"{header}\n{title} for {disease.disease_name}:\n{env_text}"
            chunk_id = f"{disease.disease_id}::environment"
            
            chunks.append(DiseaseChunk(
                chunk_id=chunk_id,
                disease_id=disease.disease_id,
                disease_name=disease.disease_name,
                crop=disease.crop,
                host_crops=disease.host_crops,
                disease_category=disease.disease_category,
                section=SectionType.ENVIRONMENT,
                section_title=title,
                content_type=ContentType.ENVIRONMENT,
                tags=disease.tags,
                text=text
            ))
            
    return chunks

def validate_chunk(chunk: DiseaseChunk) -> Tuple[bool, str]:
    if not chunk.disease_id:
        return False, "Missing disease_id"
    if not chunk.disease_name:
        return False, "Missing disease_name"
    if not chunk.section:
        return False, "Missing section"
    if not chunk.content_type:
        return False, "Missing content_type"
    if not chunk.text or not chunk.text.strip():
        return False, "Empty text content"
    return True, "Valid"
