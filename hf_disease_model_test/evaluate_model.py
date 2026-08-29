import os
import time
import csv
from huggingface_hub import InferenceClient
from dotenv import load_dotenv

load_dotenv()

DATASET_PATH = r"D:\web-dev-projects\agri\disease_detection\dataset\New Plant Diseases Dataset(Augmented)\New Plant Diseases Dataset(Augmented)"
MODEL_ID = "linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification"
RESULTS_DIR = r"d:\agent_backend\hf_disease_model_test\results"
PREDICTIONS_FILE = os.path.join(RESULTS_DIR, "predictions.csv")

IMAGES_PER_CLASS = 10

def normalize_label(label: str) -> str:
    return label.lower().replace("___", "").replace("_", "").replace(" ", "").replace(",", "").replace("-", "").replace("(", "").replace(")", "")

def evaluate():
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("Error: HF_TOKEN not found.")
        return
        
    client = InferenceClient(token=token)
    
    valid_path = os.path.join(DATASET_PATH, "valid")
    classes = [d for d in os.listdir(valid_path) if os.path.isdir(os.path.join(valid_path, d))]
    
    # Load existing results to support resuming
    existing_results = {}
    if os.path.exists(PREDICTIONS_FILE):
        with open(PREDICTIONS_FILE, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # If there's no error, we consider it successfully processed
                if not row.get("error"):
                    existing_results[row["image_path"]] = row

    print(f"Loaded {len(existing_results)} successful existing predictions.")
    print(f"Starting/Resuming evaluation on {len(classes)} classes. Limit: {IMAGES_PER_CLASS} images per class.")
    
    # We will rewrite the file, but keep existing successful results
    # and append new ones.
    
    all_rows = []
    
    for cls in classes:
        cls_path = os.path.join(valid_path, cls)
        images = os.listdir(cls_path)[:IMAGES_PER_CLASS]
        
        print(f"Evaluating {cls}...")
        
        for img in images:
            img_path = os.path.join(cls_path, img)
            
            if img_path in existing_results:
                all_rows.append(existing_results[img_path])
                continue
                
            row = {
                "image_path": img_path,
                "ground_truth": cls,
                "predicted_label": "",
                "top1_confidence": "",
                "top2_label": "",
                "top2_confidence": "",
                "top3_label": "",
                "top3_confidence": "",
                "correct": "False",
                "latency_seconds": "",
                "error": ""
            }
            
            success = False
            retries = 3
            
            while not success and retries > 0:
                start_time = time.time()
                try:
                    result = client.image_classification(img_path, model=MODEL_ID)
                    latency = time.time() - start_time
                    row["latency_seconds"] = latency
                    
                    if result:
                        top1 = result[0]
                        row["predicted_label"] = top1.label
                        row["top1_confidence"] = top1.score
                        
                        if len(result) > 1:
                            row["top2_label"] = result[1].label
                            row["top2_confidence"] = result[1].score
                        if len(result) > 2:
                            row["top3_label"] = result[2].label
                            row["top3_confidence"] = result[2].score
                        
                        gt_norm = normalize_label(cls)
                        pred_norm = normalize_label(top1.label)
                        
                        if pred_norm in gt_norm or gt_norm in pred_norm:
                            row["correct"] = "True"
                        else:
                            pred_norm_no_crop = pred_norm
                            for crop in ["apple", "cherry", "cornmaize", "grape", "orange", "peach", "bellpepper", "potato", "raspberry", "soybean", "squash", "strawberry", "tomato"]:
                                if pred_norm_no_crop.startswith(crop):
                                    pred_norm_no_crop = pred_norm_no_crop[len(crop):]
                            if pred_norm_no_crop in gt_norm:
                                row["correct"] = "True"
                    success = True
                    row["error"] = ""
                    
                except Exception as e:
                    print(f"Error on {img}: {e}. Retrying in 5s...")
                    time.sleep(5)
                    retries -= 1
                    if retries == 0:
                        row["error"] = str(e)
            
            all_rows.append(row)
            
            # Save progressively
            with open(PREDICTIONS_FILE, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "image_path", "ground_truth", "predicted_label", "top1_confidence", 
                    "top2_label", "top2_confidence", "top3_label", "top3_confidence", 
                    "correct", "latency_seconds", "error"
                ])
                writer.writeheader()
                writer.writerows(all_rows)

if __name__ == "__main__":
    evaluate()
