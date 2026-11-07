"""
Compatibility shim for agents.crop.fertilizer.
Core logic has moved to agents.shared.fertilizer.
Re-exports all symbols to preserve backward compatibility across running processes and tests.
"""
from agents.shared.fertilizer import (
    NutrientStatus,
    FertilizerAdvisory,
    NUTRIENT_THRESHOLDS,
    MANDATORY_FERTILIZER_DISCLAIMER,
    categorize_nutrient,
    extract_nutrient_measurements,
    detect_crop_name,
    generate_fertilizer_guidance,
    format_fertilizer_markdown,
)

__all__ = [
    "NutrientStatus",
    "FertilizerAdvisory",
    "NUTRIENT_THRESHOLDS",
    "MANDATORY_FERTILIZER_DISCLAIMER",
    "categorize_nutrient",
    "extract_nutrient_measurements",
    "detect_crop_name",
    "generate_fertilizer_guidance",
    "format_fertilizer_markdown",
]

