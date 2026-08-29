from typing import Dict, Any, Optional
from agents.disease.models import NormalizedDisease

def _clean_text(text: Optional[str]) -> Optional[str]:
    """Cleans text and returns None for empty or placeholder strings."""
    if not text:
        return None
    text = text.strip()
    # Treat single dots, hyphens, or 'None' as empty
    if text in [".", "-", "None", "null", ""]:
        return None
    return text

def normalize_disease(raw_json: Dict[str, Any]) -> NormalizedDisease:
    """Normalizes raw disease JSON into a clean internal representation."""
    
    disease_id = raw_json.get("id", "")
    metadata = raw_json.get("metadata", {})
    
    disease_name = metadata.get("title", disease_id)
    host_crops = metadata.get("host_crops", [])
    
    # Heuristic for primary crop
    crop = host_crops[0] if host_crops else None
    if not crop and metadata.get("scientific_name") and metadata.get("scientific_name").lower() not in ["none", "null"]:
        # We observed scientific_name often holds crop name like "Apple"
        crop = metadata.get("scientific_name").lower()
        
    disease_category = metadata.get("disease_category")
    
    # We do not use metadata["scientific_name"] as pathogen_name because inspection
    # showed it contains crop names (e.g. "Apple", "Rice").
    pathogen_name = None 

    # Overview
    overview = _clean_text(raw_json.get("overview", {}).get("content") if isinstance(raw_json.get("overview"), dict) else None)
    
    # Symptoms
    symptoms = _clean_text(raw_json.get("symptoms", {}).get("content") if isinstance(raw_json.get("symptoms"), dict) else None)
    
    # Causes
    causes = _clean_text(raw_json.get("causes", {}).get("content") if isinstance(raw_json.get("causes"), dict) else None)
    
    # Recommendations
    recs = raw_json.get("recommendations") or {}
    organic = _clean_text(recs.get("organic", {}).get("content") if isinstance(recs.get("organic"), dict) else None)
    chemical = _clean_text(recs.get("chemical", {}).get("content") if isinstance(recs.get("chemical"), dict) else None)
    
    # Preventive measures
    prev_obj = raw_json.get("preventive_measures")
    preventive_measures = None
    if isinstance(prev_obj, dict):
        items = prev_obj.get("items", [])
        if items and isinstance(items, list):
            valid_items = [_clean_text(i) for i in items if _clean_text(i)]
            if valid_items:
                preventive_measures = "\n".join(f"- {item}" for item in valid_items)
    
    # Environment
    env_obj = raw_json.get("environment") or {}
    environment = None
    if isinstance(env_obj, dict):
        cleaned_env = {}
        for k, v in env_obj.items():
            if v is not None and v != "" and v != "null":
                cleaned_env[k] = v
        if cleaned_env:
            environment = cleaned_env

    tags = raw_json.get("tags") or []
    
    return NormalizedDisease(
        disease_id=disease_id,
        disease_name=disease_name,
        crop=crop,
        host_crops=host_crops,
        disease_category=disease_category,
        pathogen_name=pathogen_name,
        overview=overview,
        symptoms=symptoms,
        causes=causes,
        organic_control=organic,
        chemical_control=chemical,
        preventive_measures=preventive_measures,
        environment=environment,
        tags=tags
    )
