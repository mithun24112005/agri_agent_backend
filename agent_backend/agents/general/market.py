"""
Agricultural Market Trends & Price Discovery Module (Phase 8)
Provides structured guidance on APMC Mandi rates, MSP benchmarks, e-NAM, and post-harvest marketing.
"""

from typing import Dict, Any, List, Optional


OFFICIAL_MARKET_PORTALS = {
    "agmarknet": {
        "name": "Agmarknet (Agricultural Marketing Information Network)",
        "url": "https://agmarknet.gov.in",
        "description": "Daily real-time arrival volumes and minimum/maximum/modal wholesale prices across 3,000+ APMC mandis in India."
    },
    "enam": {
        "name": "e-NAM (National Agriculture Market)",
        "url": "https://enam.gov.in",
        "description": "Pan-India electronic trading portal integrating mandis for transparent price discovery and online payments directly to farmer bank accounts."
    },
    "cacp": {
        "name": "CACP (Commission for Agricultural Costs & Prices)",
        "url": "https://cacp.dacnet.nic.in",
        "description": "Official nodal agency announcing seasonal Minimum Support Prices (MSP) across 22 mandated Kharif and Rabi crops."
    }
}


# Key Kharif & Rabi MSP Reference Benchmarks (Govt of India 2024-25 Season in ₹/Quintal)
MSP_REFERENCE_DATA = {
    "paddy": {"crop": "Paddy (Common)", "season": "Kharif", "msp": 2300, "unit": "₹/Quintal"},
    "paddy_grade_a": {"crop": "Paddy (Grade A)", "season": "Kharif", "msp": 2320, "unit": "₹/Quintal"},
    "maize": {"crop": "Maize", "season": "Kharif", "msp": 2225, "unit": "₹/Quintal"},
    "cotton_medium": {"crop": "Cotton (Medium Staple)", "season": "Kharif", "msp": 7121, "unit": "₹/Quintal"},
    "cotton_long": {"crop": "Cotton (Long Staple)", "season": "Kharif", "msp": 7521, "unit": "₹/Quintal"},
    "wheat": {"crop": "Wheat", "season": "Rabi", "msp": 2425, "unit": "₹/Quintal"},
    "chickpea": {"crop": "Gram (Chickpea)", "season": "Rabi", "msp": 5650, "unit": "₹/Quintal"},
    "lentil": {"crop": "Lentil (Masoor)", "season": "Rabi", "msp": 6700, "unit": "₹/Quintal"},
    "mungbean": {"crop": "Moong (Mungbean)", "season": "Kharif", "msp": 8682, "unit": "₹/Quintal"},
    "blackgram": {"crop": "Urad (Blackgram)", "season": "Kharif", "msp": 7400, "unit": "₹/Quintal"},
    "pigeonpeas": {"crop": "Arhar / Tur (Pigeonpea)", "season": "Kharif", "msp": 7550, "unit": "₹/Quintal"},
    "jute": {"crop": "Raw Jute (TD-3)", "season": "Kharif", "msp": 5335, "unit": "₹/Quintal"}
}


def get_msp_info(commodity: str) -> Optional[Dict[str, Any]]:
    """Look up official MSP benchmark for a crop."""
    clean = commodity.lower().replace("-", "").replace(" ", "").replace("crop", "")
    for key, data in MSP_REFERENCE_DATA.items():
        if clean in key or key in clean:
            return data
    return None


def format_market_guidance_markdown(commodity: Optional[str] = None, mandi_name: Optional[str] = None) -> str:
    """Format market guidance with MSP references and price discovery tips."""
    lines = [
        "### 📈 Agricultural Market & APMC Price Guidance",
        "",
        "#### 🏛️ Official Real-Time Price Discovery Portals",
        f"- **Agmarknet Portal:** [{OFFICIAL_MARKET_PORTALS['agmarknet']['name']}]({OFFICIAL_MARKET_PORTALS['agmarknet']['url']}) — {OFFICIAL_MARKET_PORTALS['agmarknet']['description']}",
        f"- **e-NAM Electronic Portal:** [{OFFICIAL_MARKET_PORTALS['enam']['name']}]({OFFICIAL_MARKET_PORTALS['enam']['url']}) — {OFFICIAL_MARKET_PORTALS['enam']['description']}",
        ""
    ]

    if commodity:
        msp_data = get_msp_info(commodity)
        if msp_data:
            lines.extend([
                f"#### 🏷️ Official Minimum Support Price (MSP) Benchmark",
                f"- **Commodity:** {msp_data['crop']} ({msp_data['season']} Season)",
                f"- **Government MSP Rate:** **₹{msp_data['msp']} {msp_data['unit']}**",
                f"> 💡 *Farmer Safety Benchmark:* Use the official MSP as a baseline price floor during negotiations. Open mandi bids should not fall below this floor for Fair Average Quality (FAQ) produce.",
                ""
            ])

    lines.extend([
        "#### 💡 Strategic Marketing & Post-Harvest Advice",
        "- **Quality Grading (FAQ):** Clean, destoned, and moisture-controlled grain (typically below 12–14% moisture) commands a 10%–20% premium over uncleaned lots in APMC auctions.",
        "- **Avoid Distress Selling at Harvest Peak:** Heavy arrivals in mandis during peak harvest weeks depress modal prices. If feasible, consider storing dried grain in WDRA-accredited warehouses (e-NWR pledge financing) for 4–8 weeks when post-harvest supply tightens.",
        "- **Direct Trade via e-NAM:** Register lots on e-NAM to attract interstate buyers directly, eliminating extra handling and commission fees.",
        "",
        "> ⚠️ **Notice:** Mandi wholesale rates fluctuate on daily supply-demand dynamics and produce grade. Verify current daily modal rates on [Agmarknet](https://agmarknet.gov.in) before dispatching truckloads to the yard."
    ])

    return "\n".join(lines)

