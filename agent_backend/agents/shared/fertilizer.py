"""
Fertilizer & Soil Nutrient Management Advisory Module
Shared utility module for Integrated Nutrient Management (INM) and Soil Health Card interpretation.
Rejects universal fixed nutrient targets (e.g. rigid 100:40:40) and enforces ICAR agronomic guidelines.

Used by:
- General Agricultural Agent: Standalone fertilizer queries and soil nutrient management advisory.
- Crop Recommendation Agent: Post-recommendation balanced nutrient advice for the predicted crop.
"""

import re
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class NutrientStatus(BaseModel):
    nutrient: str
    value: float
    category: str  # "Low", "Medium", "High"
    interpretation: str


class FertilizerAdvisory(BaseModel):
    crop: str
    nutrient_statuses: List[NutrientStatus] = Field(default_factory=list)
    has_soil_test: bool = Field(default=True, description="True if soil test parameters (N, P, K) were supplied")
    missing_measurements: List[str] = Field(default_factory=list, description="List of unmeasured nutrients")
    measurement_prompt: Optional[str] = Field(default=None, description="Guidance prompt asking for missing soil test values")
    organic_recommendations: List[str] = Field(default_factory=list)
    inorganic_guidelines: List[str] = Field(default_factory=list)
    micronutrient_notes: List[str] = Field(default_factory=list)
    mandatory_disclaimer: str


# Reference general soil fertility rating chart (ICAR / Dept of Agriculture, India)
# In standard ratio test scales (0-140 scale used in dataset / index ratio):
# N: Low < 50, Medium 50-100, High > 100
# P: Low < 30, Medium 30-70, High > 70
# K: Low < 30, Medium 30-70, High > 70
NUTRIENT_THRESHOLDS = {
    "N": {"low": 50.0, "high": 100.0, "unit": "index ratio"},
    "P": {"low": 30.0, "high": 70.0, "unit": "index ratio"},
    "K": {"low": 30.0, "high": 70.0, "unit": "index ratio"},
}

MANDATORY_FERTILIZER_DISCLAIMER = (
    "⚠️ **Important Agronomic Notice:** Nutrient requirements vary substantially based on actual Soil Health Card "
    "laboratory analyses, crop variety (hybrid vs traditional), target yield, and irrigation management. "
    "Do not apply concentrated synthetic fertilizers without verified soil test reports. "
    "Always consult your local Krishi Vigyan Kendra (KVK) or State Agricultural University (SAU) extension officer "
    "for field-specific, package-of-practices fertilizer dosage schedules."
)

COMMON_CROPS = [
    "rice", "paddy", "wheat", "maize", "corn", "cotton", "sugarcane", "soybean",
    "chickpea", "gram", "pigeonpea", "arhar", "tur", "lentil", "groundnut", "peanut",
    "mustard", "potato", "tomato", "onion", "banana", "mango", "coffee", "tea", "jute"
]

LEGUME_PULSES = [
    "chickpea", "gram", "pigeonpea", "arhar", "tur", "lentil", "soybean", "groundnut",
    "peanut", "blackgram", "greengram", "mung", "urad", "cowpea", "pea"
]


def categorize_nutrient(nutrient: str, value: float) -> NutrientStatus:
    """Classify a soil nutrient level into Low, Medium, or High relative to standard benchmarks."""
    threshold = NUTRIENT_THRESHOLDS.get(nutrient.upper(), {"low": 30.0, "high": 70.0, "unit": "ratio"})
    low_t = threshold["low"]
    high_t = threshold["high"]

    if value < low_t:
        cat = "Low"
        interp = "Deficit condition. Baseline soil replenishment and organic enrichment strongly recommended."
    elif value <= high_t:
        cat = "Medium"
        interp = "Adequate baseline range. Maintain maintenance doses to prevent progressive depletion."
    else:
        cat = "High"
        interp = "Surplus range. Avoid excess synthetic application to prevent nutrient antagonism and runoff."

    return NutrientStatus(
        nutrient=nutrient.upper(),
        value=value,
        category=cat,
        interpretation=interp
    )


def extract_nutrient_measurements(text: str) -> Dict[str, Optional[float]]:
    """
    Extract any explicitly mentioned soil nutrient measurements (N, P, K, pH) from text.
    Returns dict with keys 'N', 'P', 'K', 'ph' (float values or None).
    Never fabricates values or substitutes arbitrary defaults.
    """
    res: Dict[str, Optional[float]] = {"N": None, "P": None, "K": None, "ph": None}
    if not text:
        return res

    # N: e.g. "N=40", "N: 40", "nitrogen 40", "nitrogen = 40"
    n_match = re.search(r'\b(?:N|nitrogen)\s*(?:=|:|\blevel\s*(?:is|=|:)?|\bis\s*)?\s*([0-9]+(?:\.[0-9]+)?)\b', text, re.IGNORECASE)
    if n_match:
        try:
            val = float(n_match.group(1))
            if 0 <= val <= 500:
                res["N"] = val
        except ValueError:
            pass

    # P: e.g. "P=20", "P: 20", "phosphorus 20", "phosphorus = 20"
    p_match = re.search(r'\b(?:P|phosphorus)\s*(?:=|:|\blevel\s*(?:is|=|:)?|\bis\s*)?\s*([0-9]+(?:\.[0-9]+)?)\b', text, re.IGNORECASE)
    if p_match:
        try:
            val = float(p_match.group(1))
            if 0 <= val <= 500:
                res["P"] = val
        except ValueError:
            pass

    # K: e.g. "K=25", "K: 25", "potassium 25", "potash = 25"
    k_match = re.search(r'\b(?:K|potassium|potash)\s*(?:=|:|\blevel\s*(?:is|=|:)?|\bis\s*)?\s*([0-9]+(?:\.[0-9]+)?)\b', text, re.IGNORECASE)
    if k_match:
        try:
            val = float(k_match.group(1))
            if 0 <= val <= 500:
                res["K"] = val
        except ValueError:
            pass

    # pH: e.g. "pH=6.5", "pH 6.5", "pH of 6.5"
    ph_match = re.search(r'\bph\s*(?:=|:|\bof\s*)?\s*([0-9]+(?:\.[0-9]+)?)\b', text, re.IGNORECASE)
    if ph_match:
        try:
            val = float(ph_match.group(1))
            if 0 <= val <= 14:
                res["ph"] = val
        except ValueError:
            pass

    return res


def detect_crop_name(text: str) -> str:
    """Extract mentioned crop name from text or default to 'general crop'."""
    text_low = text.lower()
    for crop in COMMON_CROPS:
        if re.search(r'\b' + re.escape(crop) + r'\b', text_low):
            if crop in ["paddy", "rice"]:
                return "rice"
            if crop in ["corn", "maize"]:
                return "maize"
            if crop in ["gram", "chickpea"]:
                return "chickpea"
            if crop in ["arhar", "tur", "pigeonpea"]:
                return "pigeonpea"
            if crop in ["groundnut", "peanut"]:
                return "groundnut"
            return crop
    return "general crop"


def generate_fertilizer_guidance(
    crop_name: str = "general crop",
    n: Optional[float] = None,
    p: Optional[float] = None,
    k: Optional[float] = None,
    ph: Optional[float] = None
) -> FertilizerAdvisory:
    """
    Generate balanced Integrated Nutrient Management (INM) advisory.
    Strictly avoids prescribing rigid, unverified synthetic dosages.
    
    Behavior:
    1. Complete measurements (N, P, K all provided):
       - Full ICAR categorization and deficit/surplus inorganic guidelines.
    2. Partial measurements (some provided, some None):
       - Categorizes available measurements, notes unmeasured nutrients, and prompts for missing ones.
    3. No measurements provided (N, P, K all None):
       - Does NOT fabricate numbers or insert silent defaults.
       - Provides qualified crop-specific agronomic Package of Practices (POP) baseline principles.
       - Explicitly prompts user to obtain a Soil Health Card laboratory test.
    """
    norm_crop = crop_name.lower().strip() if crop_name else "general crop"
    is_legume = any(leg in norm_crop for leg in LEGUME_PULSES)

    statuses: List[NutrientStatus] = []
    missing_measurements: List[str] = []

    # 1. Evaluate Nitrogen
    if n is not None:
        statuses.append(categorize_nutrient("N", n))
    else:
        missing_measurements.append("Nitrogen (N)")

    # 2. Evaluate Phosphorus
    if p is not None:
        statuses.append(categorize_nutrient("P", p))
    else:
        missing_measurements.append("Phosphorus (P)")

    # 3. Evaluate Potassium
    if k is not None:
        statuses.append(categorize_nutrient("K", k))
    else:
        missing_measurements.append("Potassium (K)")

    has_soil_test = len(statuses) > 0
    all_measured = len(statuses) == 3

    # Measurement prompt when measurements are missing
    measurement_prompt: Optional[str] = None
    if not has_soil_test:
        measurement_prompt = (
            "No soil test values were provided. For a customized, field-specific fertilizer prescription, "
            "please share your Soil Health Card values: Nitrogen (N), Phosphorus (P), and Potassium (K) "
            "levels (kg/ha or Low/Medium/High rating), along with soil pH if known."
        )
    elif not all_measured:
        measurement_prompt = (
            f"Partial soil measurements provided. To obtain a precision nutrient schedule, "
            f"please provide the remaining parameters: {', '.join(missing_measurements)}."
        )

    # 4. Organic & Biofertilizer Guidance (Crop-tailored)
    organic_recs = [
        "Incorporate well-decomposed Farmyard Manure (FYM) or compost (8–10 tons/ha) during primary field tillage to boost Soil Organic Carbon (SOC).",
    ]
    if is_legume:
        organic_recs.append(
            "Apply biofertilizers: Inoculate seeds with crop-specific Rhizobium culture and Phosphate Solubilizing Bacteria (PSB) before sowing to maximize biological nitrogen fixation."
        )
    else:
        organic_recs.append(
            "Apply biofertilizers: Inoculate seed or seedlings with Azotobacter / Azospirillum (nitrogen fixers) and Phosphate Solubilizing Bacteria (PSB) to mobilize fixed nutrients naturally."
        )
    organic_recs.append(
        "Consider in-situ green manuring with Sesbania (Dhaincha) or Sunn hemp before the primary sowing season to enhance soil tilth and microbial activity."
    )

    # 5. Inorganic & Agronomic Nutrient Guidelines
    inorganic_guidelines = []
    if has_soil_test:
        # Structured guidance based on actual measured nutrient categories
        for s in statuses:
            if s.nutrient == "N":
                if s.category == "Low":
                    inorganic_guidelines.append("Nitrogen Deficit: Apply split doses of nitrogen (basal + top dressings at tillering/active vegetative stages) rather than a single heavy dose to minimize leaching.")
                elif s.category == "Medium":
                    inorganic_guidelines.append("Nitrogen Adequate: Apply recommended maintenance split doses. Monitor crop canopy color to adjust subsequent top-dressings.")
                else:
                    inorganic_guidelines.append("Nitrogen Surplus: Regulate or reduce nitrogen top-dressing to prevent excessive vegetative growth, lodging, and increased pest/disease susceptibility.")
            elif s.nutrient == "P":
                if s.category == "Low":
                    inorganic_guidelines.append("Phosphorus Deficit: Apply water-soluble phosphatic fertilizer (e.g. Single Super Phosphate - SSP or DAP) strictly as a basal placement near root zones during sowing.")
                elif s.category == "Medium":
                    inorganic_guidelines.append("Phosphorus Adequate: Maintain moderate basal application; high soil phosphorus can restrict zinc and iron uptake.")
                else:
                    inorganic_guidelines.append("Phosphorus Surplus: Avoid excess phosphatic fertilization to prevent induced zinc deficiency and runoff.")
            elif s.nutrient == "K":
                if s.category == "Low":
                    inorganic_guidelines.append("Potassium Deficit: Supplement potash (Muriate of Potash - MOP or Sulfate of Potash - SOP) to enhance drought tolerance, stalk strength, and fruit/grain quality.")
                elif s.category == "Medium":
                    inorganic_guidelines.append("Potassium Adequate: Potash reserves are favorable. Minimal basal maintenance application is sufficient.")
                else:
                    inorganic_guidelines.append("Potassium Surplus: Soil potash reserves are high. Synthetic potash application can be omitted for the current season.")
        
        # If some nutrients were missing, add an advisory note
        if missing_measurements:
            inorganic_guidelines.append(
                f"Unmeasured Nutrients ({', '.join(missing_measurements)}): Maintain conservative baseline application per local package of practices pending laboratory confirmation."
            )
    else:
        # Qualified baseline Package of Practices (POP) principles when NO soil measurements exist
        inorganic_guidelines.extend([
            "Split Nitrogen Application: For field crops, apply nitrogen in 2 to 3 split doses (50% basal at sowing, 25% at active tillering/vegetative phase, and 25% at panicle initiation/flowering) to minimize leaching losses.",
            "Basal Phosphorus Placement: Apply all phosphatic fertilizers (such as DAP or Single Super Phosphate - SSP) as a basal placement directly in the root zone during sowing for optimal root development.",
            "Potash Maintenance: Apply potassium (Muriate of Potash - MOP) basally at sowing, or in two splits on light sandy soils, to enhance drought resilience and grain/stalk strength.",
            "Dosage Precaution: Do not apply rigid blanket chemical dosages. Exact synthetic quantities (kg/ha) require laboratory verification of available N, P, and K to prevent fertilizer toxicity or nutrient wastage."
        ])

    # 6. Soil pH & Micronutrient Observations
    micronutrient_notes = []
    if ph is not None:
        if ph < 5.5:
            micronutrient_notes.append(f"Strongly Acidic Soil (pH {ph:.1f}): Apply agricultural lime or dolomite as per Soil Health Card buffering recommendations to alleviate aluminum toxicity and improve phosphorus availability.")
        elif ph > 8.0:
            micronutrient_notes.append(f"Alkaline Soil (pH {ph:.1f}): Calcareous soil conditions may limit micronutrient availability (Zinc, Iron). Apply agricultural gypsum or green manure and consider foliar sprays of chelated zinc sulfate (Zn-EDTA).")
        else:
            micronutrient_notes.append(f"Optimal Soil pH (pH {ph:.1f}): Near-neutral soil reaction facilitates favorable macronutrient and micronutrient root absorption.")
    else:
        micronutrient_notes.append("Micronutrient Precaution: If crop exhibits interveinal leaf chlorosis or stunted growth, test for Zinc (Zn) and Boron (B) deficiency. Chelated foliar sprays (e.g. Zn-EDTA at 0.5-1 g/L) can rectify emergency deficits.")

    return FertilizerAdvisory(
        crop=crop_name.title(),
        nutrient_statuses=statuses,
        has_soil_test=has_soil_test,
        missing_measurements=missing_measurements,
        measurement_prompt=measurement_prompt,
        organic_recommendations=organic_recs,
        inorganic_guidelines=inorganic_guidelines,
        micronutrient_notes=micronutrient_notes,
        mandatory_disclaimer=MANDATORY_FERTILIZER_DISCLAIMER
    )


def format_fertilizer_markdown(advisory: FertilizerAdvisory) -> str:
    """Format the advisory into clean farmer-facing Markdown."""
    lines = [
        f"### 🧪 Soil Nutrient & Fertilizer Advisory for {advisory.crop}",
        "",
        "#### 📊 Soil Nutrient Test Status",
    ]
    if advisory.nutrient_statuses:
        lines.extend([
            "| Nutrient | Measured Value | Rating | Agronomic Interpretation |",
            "|:---|:---:|:---:|:---|",
        ])
        for s in advisory.nutrient_statuses:
            lines.append(f"| **{s.nutrient}** | {s.value:.1f} | `{s.category}` | {s.interpretation} |")
        lines.append("")
    else:
        lines.extend([
            "*No soil test measurements were provided. The guidance below reflects general agronomic best practices and Package of Practices (POP) principles. For precision dosage recommendations, obtain a laboratory Soil Health Card test.*",
            "",
        ])

    if advisory.measurement_prompt:
        lines.extend([
            f"> 💡 **Soil Test Notice:** {advisory.measurement_prompt}",
            "",
        ])

    lines.extend([
        "#### 🌿 Organic & Biofertilizer Practices",
        *[f"- {item}" for item in advisory.organic_recommendations],
        "",
        "#### ⚖️ Balanced Nutrient Management Guidelines",
        *[f"- {item}" for item in advisory.inorganic_guidelines],
    ])

    if advisory.micronutrient_notes:
        lines.extend([
            "",
            "#### 🔬 Soil Reaction & Micronutrient Observations",
            *[f"- {item}" for item in advisory.micronutrient_notes],
        ])

    lines.extend([
        "",
        advisory.mandatory_disclaimer
    ])

    return "\n".join(lines)

