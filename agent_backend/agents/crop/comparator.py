"""
Candidate Crop Comparison Matrix Module (Phase 8)
Generates side-by-side agronomic comparison tables for top ranked candidate crops.
"""

from typing import List, Dict, Any, Optional

# Curated reference table for the 22 supported crops
CROP_METADATA = {
    "rice": {
        "duration_days": "110–140",
        "water_req": "High (1200–2000 mm)",
        "ph_range": "5.5–7.0",
        "economic_value": "High (Major Staple / MSP Protected)",
        "season": "Kharif (Monsoon)",
        "key_risk": "Requires dependable irrigation; vulnerable to drought"
    },
    "maize": {
        "duration_days": "90–110",
        "water_req": "Moderate (500–800 mm)",
        "ph_range": "5.5–7.5",
        "economic_value": "High (Industrial Starch, Poultry Feed, MSP)",
        "season": "Kharif / Rabi / Spring",
        "key_risk": "Sensitive to waterlogging at early stages"
    },
    "chickpea": {
        "duration_days": "95–110",
        "water_req": "Low (250–400 mm)",
        "ph_range": "6.0–8.0",
        "economic_value": "High (Major Pulse, High Protein, MSP)",
        "season": "Rabi (Winter)",
        "key_risk": "Excess rainfall promotes wilt/root rot"
    },
    "kidneybeans": {
        "duration_days": "80–100",
        "water_req": "Moderate (400–600 mm)",
        "ph_range": "5.5–6.5",
        "economic_value": "High (Premium Pulse Market)",
        "season": "Kharif / Rabi (Hills)",
        "key_risk": "Susceptible to high temperatures during flowering"
    },
    "pigeonpeas": {
        "duration_days": "140–180",
        "water_req": "Low to Moderate (600–700 mm)",
        "ph_range": "6.0–7.5",
        "economic_value": "Very High (Arhar/Tur Dal - Prime Demand)",
        "season": "Kharif",
        "key_risk": "Long duration, sensitive to frost and waterlogging"
    },
    "mothbeans": {
        "duration_days": "65–75",
        "water_req": "Very Low (200–350 mm)",
        "ph_range": "6.5–8.0",
        "economic_value": "Moderate (Namkeen/Flour Industry)",
        "season": "Kharif (Arid)",
        "key_risk": "Cannot tolerate standing water"
    },
    "mungbean": {
        "duration_days": "60–70",
        "water_req": "Low (300–450 mm)",
        "ph_range": "6.2–7.5",
        "economic_value": "High (Quick Catch Crop, High MSP)",
        "season": "Zaid (Summer) / Kharif",
        "key_risk": "Rain during pod maturity impairs grain quality"
    },
    "blackgram": {
        "duration_days": "70–85",
        "water_req": "Low to Moderate (400–500 mm)",
        "ph_range": "6.0–7.5",
        "economic_value": "High (Urad Dal - High Domestic Demand)",
        "season": "Kharif / Rabi (South India)",
        "key_risk": "Susceptible to Yellow Mosaic Virus"
    },
    "lentil": {
        "duration_days": "100–120",
        "water_req": "Low (200–350 mm)",
        "ph_range": "6.0–7.5",
        "economic_value": "High (Masoor Dal, Export Potential)",
        "season": "Rabi (Winter)",
        "key_risk": "Damp cloudy weather promotes rust and blight"
    },
    "pomegranate": {
        "duration_days": "Perennial (Harvest in 150d from flowering)",
        "water_req": "Moderate (Drip: 400–600 mm)",
        "ph_range": "6.5–7.5",
        "economic_value": "Very High (Commercial Horticulture)",
        "season": "Ambe/Mrig/Hasta Bahar",
        "key_risk": "Bacterial blight and fruit cracking risk"
    },
    "banana": {
        "duration_days": "11–13 months",
        "water_req": "Very High (1500–2200 mm)",
        "ph_range": "6.0–7.5",
        "economic_value": "Very High (Continuous Cash Flow)",
        "season": "Year-round (Tropical)",
        "key_risk": "High capital input, wind damage, Panama wilt"
    },
    "mango": {
        "duration_days": "Perennial (Harvest 90–120d from fruit set)",
        "water_req": "Moderate (Drip in establishment)",
        "ph_range": "5.5–7.5",
        "economic_value": "Very High (King of Fruits, Export)",
        "season": "Summer (April–July)",
        "key_risk": "Alternate bearing, fruit fly damage"
    },
    "grapes": {
        "duration_days": "Perennial (110–130d pruning to harvest)",
        "water_req": "Moderate (Drip: 500–700 mm)",
        "ph_range": "6.5–7.5",
        "economic_value": "Very High (Table & Wine Grapes)",
        "season": "October pruning / March harvest",
        "key_risk": "Unseasonal rains cause berry cracking and downy mildew"
    },
    "watermelon": {
        "duration_days": "80–95",
        "water_req": "Moderate (400–550 mm)",
        "ph_range": "6.0–7.0",
        "economic_value": "High (Summer Cash Crop)",
        "season": "Zaid (Summer)",
        "key_risk": "Fruit rot in excessive wet conditions"
    },
    "muskmelon": {
        "duration_days": "75–90",
        "water_req": "Moderate (350–500 mm)",
        "ph_range": "6.0–7.5",
        "economic_value": "High (Quick Summer Returns)",
        "season": "Zaid (Summer)",
        "key_risk": "Powdery mildew, fruit fly"
    },
    "apple": {
        "duration_days": "Perennial (120–150d blossom to harvest)",
        "water_req": "Moderate to High (1000–1250 mm)",
        "ph_range": "5.5–6.8",
        "economic_value": "Very High (Temperate Cash Crop)",
        "season": "Temperate Winter-Summer",
        "key_risk": "Requires mandatory chilling hours; hail/scab risk"
    },
    "orange": {
        "duration_days": "Perennial (Harvest in 240d)",
        "water_req": "Moderate (800–1100 mm)",
        "ph_range": "6.0–7.5",
        "economic_value": "High (Nagpur / Kinnow Markets)",
        "season": "Ambe/Mrig Bahar",
        "key_risk": "Die-back, citrus canker, fruit drop"
    },
    "papaya": {
        "duration_days": "9–10 months to first harvest",
        "water_req": "Moderate (1000–1200 mm)",
        "ph_range": "6.0–6.8",
        "economic_value": "High (Fast-growing fruit crop)",
        "season": "Tropical Year-round",
        "key_risk": "Zero tolerance for waterlogging; Papaya Ringspot Virus"
    },
    "coconut": {
        "duration_days": "Perennial (Year-round harvests)",
        "water_req": "High (1300–2000 mm)",
        "ph_range": "5.2–8.0",
        "economic_value": "Very High (Copra, Tender Water, Oil)",
        "season": "Coastal / Tropical Year-round",
        "key_risk": "Slow initial gestation (4–5 years to yield)"
    },
    "cotton": {
        "duration_days": "150–180",
        "water_req": "Moderate (600–900 mm)",
        "ph_range": "6.0–8.0",
        "economic_value": "High (White Gold / Commercial Fibre)",
        "season": "Kharif",
        "key_risk": "Pink bollworm, high pesticide sensitivity"
    },
    "jute": {
        "duration_days": "120–135",
        "water_req": "High (1200–1600 mm)",
        "ph_range": "6.0–7.0",
        "economic_value": "Moderate to High (Eco-friendly packaging)",
        "season": "Early Kharif (March–July)",
        "key_risk": "Requires clean slow-moving water bodies for retting"
    },
    "coffee": {
        "duration_days": "Perennial (Harvest in Nov–Feb)",
        "water_req": "High (1500–2000 mm)",
        "ph_range": "5.5–6.5",
        "economic_value": "Very High (Export Commodity)",
        "season": "Shaded Plantation",
        "key_risk": "White stem borer, coffee berry borer"
    }
}


def build_comparison_matrix(top_candidates: List[Dict[str, Any]]) -> str:
    """
    Generate a side-by-side Markdown comparison matrix for candidate crops.
    top_candidates should be a list of dicts with 'crop' and 'tree_vote_share'.
    """
    if not top_candidates:
        return ""

    crops = [c.get("crop", "").lower() for c in top_candidates if c.get("crop")]
    if not crops:
        return ""

    headers = ["Agronomic Factor"] + [c.title() for c in crops]
    rows = []

    # Row 1: Model Tree-Vote Share
    share_row = ["**Tree-Vote Share**"] + [
        f"{next((c.get('tree_vote_share', 0.0) for c in top_candidates if c.get('crop', '').lower() == crop_id), 0.0):.1%}"
        for crop_id in crops
    ]
    rows.append(share_row)

    # Row 2: Growing Duration
    dur_row = ["**Growing Duration**"] + [
        CROP_METADATA.get(c, {}).get("duration_days", "Varies by hybrid")
        for c in crops
    ]
    rows.append(dur_row)

    # Row 3: Water Requirements
    water_row = ["**Water Need**"] + [
        CROP_METADATA.get(c, {}).get("water_req", "Moderate")
        for c in crops
    ]
    rows.append(water_row)

    # Row 4: Soil pH Tolerance
    ph_row = ["**Optimal Soil pH**"] + [
        CROP_METADATA.get(c, {}).get("ph_range", "6.0–7.5")
        for c in crops
    ]
    rows.append(ph_row)

    # Row 5: Season
    season_row = ["**Sowing Season**"] + [
        CROP_METADATA.get(c, {}).get("season", "Kharif/Rabi")
        for c in crops
    ]
    rows.append(season_row)

    # Row 6: Market Value & Demand
    econ_row = ["**Market Profile**"] + [
        CROP_METADATA.get(c, {}).get("economic_value", "Commercial Market")
        for c in crops
    ]
    rows.append(econ_row)

    # Row 7: Key Management Risk
    risk_row = ["**Key Cultivation Risk**"] + [
        CROP_METADATA.get(c, {}).get("key_risk", "Monitor pests and moisture")
        for c in crops
    ]
    rows.append(risk_row)

    # Build Markdown table
    md_lines = [
        "### 📊 Candidate Crop Agronomic Comparison Matrix",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join([":---"] + [":---:"] * (len(headers) - 1)) + " |"
    ]
    for r in rows:
        md_lines.append("| " + " | ".join(r) + " |")

    md_lines.append("")
    md_lines.append(
        "> 💡 **Farmer Decision Tip:** Tree-vote share represents the proportion of decision trees in the ensemble voting "
        "for each crop under these soil and climate numbers. Choose the crop that best matches your available irrigation "
        "infrastructure and local mandi market access."
    )

    return "\n".join(md_lines)

