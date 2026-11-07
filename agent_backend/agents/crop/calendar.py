"""
Seasonal Crop Calendar Module (Phase 8)
Maps crops to Indian cropping seasons (Kharif, Rabi, Zaid) with regional sowing windows.
"""

from typing import Dict, Any, List, Optional


SEASONS = {
    "kharif": {
        "name": "Kharif (Monsoon Season)",
        "sowing": "June – July (onset of Southwest Monsoon)",
        "harvesting": "September – October",
        "description": "Crops requiring warm temperatures and abundant rainfall during vegetative growth.",
        "crops": ["rice", "maize", "pigeonpeas", "cotton", "jute", "mothbeans", "blackgram"]
    },
    "rabi": {
        "name": "Rabi (Winter Season)",
        "sowing": "October – December (post-monsoon)",
        "harvesting": "February – April",
        "description": "Crops requiring cool climate during growth and warm dry weather for seed ripening.",
        "crops": ["chickpea", "lentil", "maize", "kidneybeans"]
    },
    "zaid": {
        "name": "Zaid (Summer Season)",
        "sowing": "February – March",
        "harvesting": "April – June",
        "description": "Short-duration crops grown between Rabi harvest and Kharif sowing with assured irrigation.",
        "crops": ["watermelon", "muskmelon", "mungbean"]
    },
    "perennial": {
        "name": "Perennial & Plantation Crops",
        "sowing": "Establishment during monsoon; year-round management",
        "harvesting": "Cyclical seasonal harvests or year-round production",
        "description": "Long-lived orchards, plantations, and multi-year horticultural crops.",
        "crops": ["apple", "banana", "mango", "grapes", "orange", "pomegranate", "papaya", "coconut", "coffee"]
    }
}


def get_crop_season_info(crop_name: str) -> Dict[str, Any]:
    """Retrieve seasonal calendar information for a given crop."""
    clean_crop = crop_name.lower().replace("-", "").replace(" ", "")

    for season_key, data in SEASONS.items():
        if clean_crop in data["crops"]:
            return {
                "crop": crop_name.title(),
                "season_key": season_key,
                "season_name": data["name"],
                "sowing_window": data["sowing"],
                "harvesting_window": data["harvesting"],
                "description": data["description"]
            }

    return {
        "crop": crop_name.title(),
        "season_key": "general",
        "season_name": "General Cultivation",
        "sowing_window": "Varies by agro-climatic zone",
        "harvesting_window": "Varies by variety",
        "description": "Consult state package of practices for localized sowing calendars."
    }


def format_crop_calendar_markdown(crop_name: str) -> str:
    """Format crop seasonal calendar as Markdown."""
    info = get_crop_season_info(crop_name)
    return (
        f"#### 📅 Sowing & Seasonal Calendar for {info['crop']}\n"
        f"- **Primary Season:** {info['season_name']}\n"
        f"- **Optimal Sowing Period:** {info['sowing_window']}\n"
        f"- **Harvest Window:** {info['harvesting_window']}\n"
        f"- **Climatic Note:** {info['description']}"
    )

