import re
import json
from pathlib import Path
from typing import Optional, Dict, Any
from config.settings import settings

# Canonical mapping from PlantVillage model labels to verified diseases_dataset IDs
CANONICAL_PLANTVILLAGE_MAP = {
    "apple___apple_scab": "apple_scab",
    "apple___black_rot": "black_rot",
    "apple___cedar_apple_rust": "cedar_apple_rust",  # Unrepresented in 722 dataset -> insufficient evidence
    "cherry___powdery_mildew": "powdery_mildew",
    "corn___cercospora_leaf_spot_gray_leaf_spot": "grey_leaf_spot_of_maize",
    "corn_(maize)___cercospora_leaf_spot_gray_leaf_spot": "grey_leaf_spot_of_maize",
    "corn___common_rust": "common_rust_of_maize",
    "corn_(maize)___common_rust": "common_rust_of_maize",
    "corn_(maize)___common_rust_": "common_rust_of_maize",
    "corn___northern_leaf_blight": "southern_leaf_blight_of_maize",
    "corn_(maize)___northern_leaf_blight": "southern_leaf_blight_of_maize",
    "grape___black_rot": "black_rot_of_grape",
    "grape___esca_(black_measles)": "esca",
    "grape___leaf_blight_(isariopsis_leaf_spot)": "black_rot_of_grape",
    "orange___haunglongbing_(citrus_greening)": "citrus_greening_disease",
    "peach___bacterial_spot": "bacterial_spot_on_stone_fruits",
    "pepper,_bell___bacterial_spot": "bacterial_spot_of_pepper",
    "potato___early_blight": "early_blight",
    "potato___late_blight": "potato_late_blight",
    "squash___powdery_mildew": "powdery_mildew",
    "strawberry___leaf_scorch": "angular_leaf_scorch",
    "tomato___bacterial_spot": "bacterial_spot_and_speck_of_tomato",
    "tomato___early_blight": "early_blight",
    "tomato___late_blight": "tomato_late_blight",
    "tomato___leaf_mold": "leaf_mold_of_tomato",
    "tomato___septoria_leaf_spot": "septoria_leaf_spot",
    "tomato___spider_mites_two_spotted_spider_mite": "spider_mites",
    "tomato___target_spot": "target_spot",
    "tomato___tomato_yellow_leaf_curl_virus": "tomato_yellow_leaf_curl_virus",
    "tomato___tomato_mosaic_virus": "tobacco_mosaic_virus",
}

class DiseaseMapper:
    def __init__(self, disease_folder: Optional[Path] = None):
        self.lookup: Dict[str, Dict[str, Any]] = {}
        self.alias_lookup: Dict[str, str] = {}
        folder = Path(disease_folder or settings.disease_dataset_path)
        self.load_diseases(folder)
        self._register_canonical_mappings()

    def normalize(self, text: str) -> str:
        """
        Deterministic string normalizer for labels and queries.
        Handles punctuation, repeated underscores, case differences.
        """
        if not text:
            return ""
        text = text.lower()
        text = text.replace(",", "")
        text = text.replace("(", "")
        text = text.replace(")", "")
        text = text.replace("-", "_")
        text = text.replace(" ", "_")
        text = re.sub(r"_+", "_", text)
        return text.strip("_")

    def load_diseases(self, disease_folder: Path):
        """Loads all disease definitions from JSON dataset files."""
        if not disease_folder.exists():
            return
            
        for file in disease_folder.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    disease = json.load(f)
            except Exception:
                continue

            disease_id = disease.get("id", file.stem)
            metadata = disease.get("metadata", {})
            title = metadata.get("title", disease_id)
            host_crops = metadata.get("host_crops", [])

            aliases = set()
            aliases.add(disease_id)
            aliases.add(title)
            aliases.add(title.lower())
            aliases.add(self.normalize(title))
            aliases.add(self.normalize(disease_id))

            # Crop-qualified aliases
            for crop in host_crops:
                aliases.add(f"{crop.title()}___{title.replace(' ', '_')}")
                aliases.add(f"{crop.capitalize()}___{disease_id}")
                aliases.add(self.normalize(f"{crop}_{title}"))
                aliases.add(self.normalize(f"{crop}_{disease_id}"))

            self.lookup[disease_id] = {
                "title": title,
                "aliases": list(aliases),
                "host_crops": host_crops
            }

            for alias in aliases:
                norm_alias = self.normalize(alias)
                if norm_alias:
                    self.alias_lookup[norm_alias] = disease_id

    def _register_canonical_mappings(self):
        """Registers verified PlantVillage canonical mapping overrides."""
        for pv_label, target_id in CANONICAL_PLANTVILLAGE_MAP.items():
            norm_pv = self.normalize(pv_label)
            self.alias_lookup[norm_pv] = target_id

    def map_prediction(self, prediction: str, crop: Optional[str] = None) -> Dict[str, Any]:
        """
        Maps a prediction string (e.g. 'Apple___Apple_scab') and optional crop
        to canonical metadata and knowledge base disease ID.
        """
        if not prediction:
            return {
                "canonical_label": None,
                "prediction": None,
                "crop": None,
                "disease_id": None,
                "title": None,
                "is_healthy": False
            }

        canonical_label = prediction.strip()
        norm_pred = self.normalize(canonical_label)
        is_healthy = "healthy" in norm_pred

        resolved_crop = self.normalize(crop) if crop else None
        parts = canonical_label.split("___")
        if len(parts) == 2 and not resolved_crop:
            resolved_crop = self.normalize(parts[0])

        disease_id = None
        
        # 1. Exact lookup in alias registry
        if norm_pred in self.alias_lookup:
            disease_id = self.alias_lookup[norm_pred]
        # 2. Try crop + disease combination
        elif resolved_crop and len(parts) == 2:
            combined = self.normalize(f"{resolved_crop}_{parts[1]}")
            if combined in self.alias_lookup:
                disease_id = self.alias_lookup[combined]
        # 3. Try disease suffix only
        if not disease_id and len(parts) == 2:
            suffix = self.normalize(parts[1])
            if suffix in self.alias_lookup:
                disease_id = self.alias_lookup[suffix]
            else:
                disease_id = suffix
        elif not disease_id:
            disease_id = norm_pred

        title = self.lookup.get(disease_id, {}).get("title")
        if not title:
            # Fallback human-readable title
            if len(parts) == 2:
                title = parts[1].replace("_", " ").title()
            else:
                title = canonical_label.replace("_", " ").title()

        return {
            "canonical_label": canonical_label,
            "prediction": canonical_label,
            "crop": resolved_crop,
            "disease_id": disease_id,
            "title": title,
            "is_healthy": is_healthy
        }

    def exists(self, disease_id: str) -> bool:
        """Checks if disease_id is indexed in the knowledge base."""
        return disease_id in self.lookup

disease_mapper = DiseaseMapper()
