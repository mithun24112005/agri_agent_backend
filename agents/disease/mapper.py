import re
import json
from pathlib import Path
from config.settings import settings

class DiseaseMapper:
    def __init__(self, disease_folder: str = None):
        self.lookup = {}
        self.alias_lookup = {}
        folder = disease_folder or settings.disease_folder_path
        self.load_diseases(folder)

    def load_diseases(self, disease_folder: Path):
        for file in disease_folder.glob("*.json"):
            with open(file, "r", encoding="utf-8") as f:
                disease = json.load(f)

            disease_id = disease["id"]
            metadata = disease.get("metadata", {})
            title = metadata.get("title", disease_id)
            host_crops = metadata.get("host_crops", [])

            aliases = set()
            aliases.add(disease_id)
            aliases.add(title)
            aliases.add(title.lower())
            aliases.add(title.lower().replace(" ", "_"))
            aliases.add(title.lower().replace(" ", "-"))

            # CNN aliases
            for crop in host_crops:
                aliases.add(f"{crop.title()}___{title.replace(' ', '_')}")
                aliases.add(f"{crop.capitalize()}___{disease_id}")

            aliases = list(aliases)
            self.lookup[disease_id] = {
                "title": title,
                "aliases": aliases,
                "host_crops": host_crops
            }

            for alias in aliases:
                self.alias_lookup[alias.lower()] = disease_id

    def normalize(self, text: str):
        text = text.lower()
        text = text.replace(",", "")
        text = text.replace("(", "")
        text = text.replace(")", "")
        text = text.replace("-", "_")
        text = text.replace(" ", "_")
        text = re.sub(r"_+", "_", text)
        return text.strip("_")

    def map_prediction(self, prediction: str):
        if not prediction:
            return {"prediction": None, "crop": None, "disease_id": None, "title": None}
            
        if prediction.lower() in self.alias_lookup:
            disease_id = self.alias_lookup[prediction.lower()]
        else:
            parts = prediction.split("___")
            if len(parts) == 2:
                _, disease = parts
                disease_id = self.normalize(disease)
            else:
                disease_id = self.normalize(prediction)

        parts = prediction.split("___")
        crop = self.normalize(parts[0]) if len(parts) == 2 else None

        return {
            "prediction": prediction,
            "crop": crop,
            "disease_id": disease_id,
            "title": self.lookup.get(disease_id, {}).get("title")
        }

    def exists(self, disease_id: str):
        return disease_id in self.lookup

disease_mapper = DiseaseMapper()
