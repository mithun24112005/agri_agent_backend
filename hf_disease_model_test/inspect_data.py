import os
import json
from collections import defaultdict
from huggingface_hub import HfApi, model_info

DATASET_PATH = r"D:\web-dev-projects\agri\disease_detection\dataset\New Plant Diseases Dataset(Augmented)\New Plant Diseases Dataset(Augmented)"
MODEL_ID = "linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification"

def inspect_dataset():
    print("=== Dataset Inspection ===")
    if not os.path.exists(DATASET_PATH):
        print(f"Error: Path {DATASET_PATH} does not exist.")
        return
    
    valid_path = os.path.join(DATASET_PATH, "valid")
    if not os.path.exists(valid_path):
        print(f"Error: valid path {valid_path} does not exist.")
        return
        
    classes = [d for d in os.listdir(valid_path) if os.path.isdir(os.path.join(valid_path, d))]
    print(f"Found {len(classes)} classes in 'valid' folder.")
    
    total_images = 0
    extensions = set()
    
    for cls in classes:
        cls_path = os.path.join(valid_path, cls)
        for img in os.listdir(cls_path):
            total_images += 1
            ext = os.path.splitext(img)[1].lower()
            extensions.add(ext)
            
    print(f"Total images in 'valid': {total_images}")
    print(f"Image formats: {list(extensions)}")
    print("\nDataset structure sample:")
    print(f"dataset/")
    for cls in classes[:3]:
        print(f"    {cls}/")
    print("    ...\n")

def inspect_model():
    print("=== Model Inspection ===")
    try:
        api = HfApi()
        info = api.model_info(MODEL_ID)
        
        print(f"Model ID: {info.id}")
        print(f"Task: {info.pipeline_tag}")
        
        # We can extract config directly using requests if info.config doesn't have it
        import requests
        config_url = f"https://huggingface.co/{MODEL_ID}/resolve/main/config.json"
        resp = requests.get(config_url)
        if resp.status_code == 200:
            config = resp.json()
            id2label = config.get("id2label", {})
            print(f"Number of classes (from config): {len(id2label)}")
            print(id2label)
            
            crop_map = defaultdict(list)
            for k, v in id2label.items():
                if " with " in v:
                    crop = v.split(" with ")[0]
                elif "Healthy " in v:
                    crop = v.replace("Healthy ", "").replace(" Plant", "")
                elif "Apple" in v: crop = "Apple"
                elif "Cherry" in v: crop = "Cherry"
                elif "Corn" in v: crop = "Corn (Maize)"
                elif "Tomato" in v: crop = "Tomato"
                else: crop = v.split(" ")[0]
                crop_map[crop].append(v)
            
            print("\nCrop Summary:")
            for crop, cls_list in crop_map.items():
                print(f"{crop}: {len(cls_list)} classes")
        else:
            print("Could not fetch config.json")
            
    except Exception as e:
        print(f"Failed to fetch model info: {e}")

if __name__ == "__main__":
    inspect_dataset()
    inspect_model()
