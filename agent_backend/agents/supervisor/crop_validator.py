"""
Deterministic Crop Input Validation Module for Supervisor Agent (Phase 1 / v2.1).
Enforces strict 7-parameter completeness verification BEFORE invoking the Crop Recommendation Agent.
Guarantees that the Crop ML prediction pipeline is NEVER invoked with missing, fallback, or default values.
"""

import re
import math
from typing import Dict, Any, Optional, List, Tuple
from pydantic import BaseModel, Field

# ==========================================
# Exact Clarification Message Required by Spec
# ==========================================

EXACT_CROP_CLARIFICATION_MESSAGE = (
    "Please provide the full set of soil and climate parameters for accurate crop recommendation: "
    "Nitrogen (N), Phosphorus (P), Potassium (K) levels (kg/ha), soil pH, average temperature (°C), "
    "humidity (%), and confirm the rainfall amount (mm)."
)

# 7 Mandatory Parameters with Required Units and Physical Bounds
REQUIRED_PARAMETERS: Dict[str, Dict[str, Any]] = {
    "N": {"name": "Nitrogen (N)", "unit": "kg/ha", "min": 0.0, "max": 300.0},
    "P": {"name": "Phosphorus (P)", "unit": "kg/ha", "min": 0.0, "max": 200.0},
    "K": {"name": "Potassium (K)", "unit": "kg/ha", "min": 0.0, "max": 300.0},
    "ph": {"name": "soil pH", "unit": "pH", "min": 0.0, "max": 14.0},
    "temperature": {"name": "average temperature", "unit": "°C", "min": -10.0, "max": 60.0},
    "humidity": {"name": "humidity", "unit": "%", "min": 0.0, "max": 100.0},
    "rainfall": {"name": "rainfall amount", "unit": "mm", "min": 0.0, "max": 5000.0},
}

class CropValidationResult(BaseModel):
    is_complete: bool = Field(description="True ONLY if all seven parameters are present and physically valid.")
    validated_parameters: Dict[str, float] = Field(default_factory=dict, description="All 7 validated parameters.")
    missing_parameters: List[str] = Field(default_factory=list, description="Keys of missing parameters.")
    invalid_parameters: Dict[str, str] = Field(default_factory=dict, description="Keys mapped to rejection reasons.")
    clarification_message: Optional[str] = Field(default=None, description="Exact clarification message if incomplete.")

def detect_context_reset(query: str) -> bool:
    """Check if the user is switching to a different farm, soil sample, or resetting parameters."""
    reset_patterns = [
        r"\b(?:new|another|different|second)\s+(?:farm|field|plot|soil|sample|land|location)\b",
        r"\b(?:reset|start\s+over|forget\s+previous|ignore\s+previous)\b",
    ]
    q_low = query.lower()
    return any(re.search(pat, q_low) for pat in reset_patterns)

def check_unit_incompatibilities(query: str) -> Dict[str, str]:
    """Detect if the user supplied values with incompatible or ambiguous units."""
    issues = {}
    q_low = query.lower()

    # Temperature in Fahrenheit
    if re.search(r"\b\d+(?:\.\d+)?\s*(?:°\s*f|f(?:ahrenheit)?)\b", q_low):
        if not re.search(r"\b\d+(?:\.\d+)?\s*(?:°\s*c|c(?:elsius)?)\b", q_low):
            issues["temperature"] = "Temperature was provided in Fahrenheit (°F). Please provide temperature in Celsius (°C)."

    # Rainfall in inches
    if re.search(r"\b\d+(?:\.\d+)?\s*(?:inches|inch|\bin\b)\b", q_low) and "rain" in q_low:
        if not re.search(r"\b\d+(?:\.\d+)?\s*mm\b", q_low):
            issues["rainfall"] = "Rainfall was provided in inches. Please confirm the rainfall amount in millimeters (mm)."

    # NPK in lbs or pounds
    if re.search(r"\b\d+(?:\.\d+)?\s*(?:lbs|pounds|lbs/acre)\b", q_low) and any(k in q_low for k in ["n", "p", "k", "nitrogen"]):
        issues["NPK"] = "Soil nutrients were provided in lbs/acre. Please provide Nitrogen, Phosphorus, Potassium levels in kg/ha."

    return issues

def extract_explicit_parameters(text: str) -> Dict[str, float]:
    """
    Extract explicitly mentioned agricultural parameters from text using robust regex.
    Does NOT invent, default, or infer values.
    """
    extracted: Dict[str, float] = {}

    # 1. NPK composite patterns (e.g. 'NPK: 80, 40, 30', 'NPK of 80:40:30', 'NPK values are 80, 40, 30')
    npk_match = re.search(
        r"\bnpk\b[^\d]*?(\d+(?:\.\d+)?)\s*[,:\s/]\s*(\d+(?:\.\d+)?)\s*[,:\s/]\s*(\d+(?:\.\d+)?)",
        text,
        re.IGNORECASE
    )
    if npk_match:
        try:
            extracted["N"] = float(npk_match.group(1))
            extracted["P"] = float(npk_match.group(2))
            extracted["K"] = float(npk_match.group(3))
        except (ValueError, IndexError):
            pass

    # 2. Individual Nitrogen (N)
    if "N" not in extracted:
        n_match = re.search(
            r"\b(?:n|nitrogen)\b\s*(?:level|value|content|ratio)?\s*(?:is|of|[:=])?\s*(\d+(?:\.\d+)?)\s*(?:kg/ha|kg\s*/\s*ha)?\b",
            text,
            re.IGNORECASE
        )
        if n_match:
            try:
                extracted["N"] = float(n_match.group(1))
            except ValueError:
                pass

    # 3. Individual Phosphorus (P)
    if "P" not in extracted:
        p_match = re.search(
            r"\b(?:p|phosphorus|phosphate)\b\s*(?:level|value|content|ratio)?\s*(?:is|of|[:=])?\s*(\d+(?:\.\d+)?)\s*(?:kg/ha|kg\s*/\s*ha)?\b",
            text,
            re.IGNORECASE
        )
        if p_match:
            try:
                extracted["P"] = float(p_match.group(1))
            except ValueError:
                pass

    # 4. Individual Potassium (K)
    if "K" not in extracted:
        k_match = re.search(
            r"\b(?:k|potassium|potash)\b\s*(?:level|value|content|ratio)?\s*(?:is|of|[:=])?\s*(\d+(?:\.\d+)?)\s*(?:kg/ha|kg\s*/\s*ha)?\b",
            text,
            re.IGNORECASE
        )
        if k_match:
            try:
                extracted["K"] = float(k_match.group(1))
            except ValueError:
                pass

    # 5. Soil pH
    ph_match = re.search(
        r"\b(?:soil\s+)?ph\b\s*(?:level|value)?\s*(?:is|of|[:=])?\s*(\d+(?:\.\d+)?)\b",
        text,
        re.IGNORECASE
    )
    if ph_match:
        try:
            extracted["ph"] = float(ph_match.group(1))
        except ValueError:
            pass

    # 6. Temperature (°C)
    temp_match = re.search(
        r"\b(?:temp(?:erature)?)\b\s*(?:is|of|[:=])?\s*(\d+(?:\.\d+)?)\s*(?:°\s*c|c(?:elsius)?)?\b",
        text,
        re.IGNORECASE
    )
    if temp_match:
        try:
            extracted["temperature"] = float(temp_match.group(1))
        except ValueError:
            pass

    # 7. Humidity (%)
    hum_match = re.search(
        r"\b(?:humidity)\b\s*(?:is|of|[:=])?\s*(\d+(?:\.\d+)?)\s*%?\b",
        text,
        re.IGNORECASE
    )
    if hum_match:
        try:
            extracted["humidity"] = float(hum_match.group(1))
        except ValueError:
            pass

    # 8. Rainfall (mm)
    rain_match = re.search(
        r"\b(?:rain(?:fall)?)\b\s*(?:amount|level|value)?\s*(?:is|of|[:=])?\s*(\d+(?:\.\d+)?)\s*(?:mm)?\b",
        text,
        re.IGNORECASE
    )
    if rain_match:
        try:
            extracted["rainfall"] = float(rain_match.group(1))
        except ValueError:
            pass

    return extracted

def validate_crop_inputs(
    query: str,
    conversation_context: Optional[str] = None,
    prior_parameters: Optional[Dict[str, Any]] = None
) -> CropValidationResult:
    """
    Supervisor validation gate for crop recommendation inputs.
    
    Rules:
    1. Extracts parameters explicitly provided in current query.
    2. Reuses relevant parameters from the same session unless a context reset is detected.
    3. Overwrites earlier parameters if the user provided an updated value in the current turn.
    4. Rejects ambiguous or incompatible units.
    5. Validates physical plausible ranges (no negatives, no NaNs).
    6. If incomplete, generates the exact user-facing clarification message and does NOT approve crop ML invocation.
    """
    unit_issues = check_unit_incompatibilities(query)
    
    # Check for context reset (e.g. user talking about a new or different farm)
    is_reset = detect_context_reset(query)
    
    combined_params: Dict[str, float] = {}
    
    # 1. Start with prior session parameters if available and not reset
    if not is_reset and prior_parameters and isinstance(prior_parameters, dict):
        for k in REQUIRED_PARAMETERS:
            val = prior_parameters.get(k)
            if val is not None and isinstance(val, (int, float)) and not math.isnan(val) and not math.isinf(val):
                combined_params[k] = float(val)

    # 2. Extract explicit parameters from previous conversation context if prior_parameters wasn't populated
    if not is_reset and not combined_params and conversation_context:
        ctx_extracted = extract_explicit_parameters(conversation_context)
        for k, v in ctx_extracted.items():
            if k in REQUIRED_PARAMETERS:
                combined_params[k] = v

    # 3. Extract explicit parameters from current query (latest turn overwrites prior turn values)
    current_extracted = extract_explicit_parameters(query)
    for k, v in current_extracted.items():
        if k in REQUIRED_PARAMETERS:
            combined_params[k] = v

    # 4. Validate physical bounds and validity
    invalid_params: Dict[str, str] = {}
    validated_params: Dict[str, float] = {}

    for k, v in combined_params.items():
        spec = REQUIRED_PARAMETERS[k]
        if math.isnan(v) or math.isinf(v):
            invalid_params[k] = f"{spec['name']} cannot be NaN or infinite."
        elif v < spec["min"]:
            invalid_params[k] = f"{spec['name']} cannot be negative ({v} < {spec['min']} {spec['unit']})."
        elif v > spec["max"]:
            invalid_params[k] = f"{spec['name']} ({v} {spec['unit']}) exceeds maximum physical limit ({spec['max']} {spec['unit']})."
        else:
            validated_params[k] = v

    # Add any detected unit issues
    for k, issue in unit_issues.items():
        invalid_params[k] = issue
        # Invalidate parameter if unit is wrong
        if k in validated_params:
            del validated_params[k]

    # 5. Check for missing parameters among the 7 required
    missing = [k for k in REQUIRED_PARAMETERS if k not in validated_params]

    is_complete = (len(missing) == 0 and len(invalid_params) == 0)

    clarification_msg = None
    if not is_complete:
        clarification_msg = EXACT_CROP_CLARIFICATION_MESSAGE
        
        # Format informative breakdown of missing or invalid parameters
        details = []
        if missing:
            missing_names = [f"{REQUIRED_PARAMETERS[m]['name']} ({REQUIRED_PARAMETERS[m]['unit']})" for m in missing]
            details.append(f"**Missing parameters:** {', '.join(missing_names)}")
        if invalid_params:
            invalid_details = [f"- {issue}" for issue in invalid_params.values()]
            details.append(f"**Invalid parameters:**\n" + "\n".join(invalid_details))
            
        if details:
            clarification_msg += "\n\n" + "\n\n".join(details)

    return CropValidationResult(
        is_complete=is_complete,
        validated_parameters=validated_params,
        missing_parameters=missing,
        invalid_parameters=invalid_params,
        clarification_message=clarification_msg
    )

