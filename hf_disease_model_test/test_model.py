import os
import json
from huggingface_hub import InferenceClient
from dotenv import load_dotenv

load_dotenv()

MODEL_ID = "linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification"
# Find an image to test with
DATASET_PATH = r"D:\web-dev-projects\agri\disease_detection\dataset\New Plant Diseases Dataset(Augmented)\New Plant Diseases Dataset(Augmented)"

def test_api():
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("HF_TOKEN not found in environment!")
        return

    client = InferenceClient(token=token)
    
    # Get first image from the first class
    valid_path = os.path.join(DATASET_PATH, "valid")
    first_class = os.listdir(valid_path)[0]
    img_path = os.path.join(valid_path, first_class, os.listdir(os.path.join(valid_path, first_class))[0])
    
    print(f"Testing inference with image: {img_path}")
    print(f"Class folder: {first_class}")
    
    try:
        # Requesting top_k doesn't seem to be a direct param in the new InferenceClient.image_classification signature, 
        # but typically HF Vision APIs return top 5 by default or accept top_k.
        result = client.image_classification(
            img_path,
            model=MODEL_ID
        )
        print("\nRAW RESPONSE")
        print("--------------------------------")
        print(f"type: {type(result)}")
        for i, pred in enumerate(result, 1):
            print(f"prediction {i}:")
            print(f"    label: {pred.label}")
            print(f"    score: {pred.score}")
            
    except Exception as e:
        print(f"Inference failed: {e}")

if __name__ == "__main__":
    test_api()
