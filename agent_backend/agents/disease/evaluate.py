import argparse
import asyncio
from typing import List, Dict, Any
from agents.disease.retriever import disease_retriever, disease_retriever_v2
from config.settings import settings

GOLD_DATASET = [
    # Apple Scab
    {"query": "What are the symptoms of Apple Scab?", "expected_disease_id": "apple_scab", "expected_sections": ["symptoms"], "expected_content_type": "diagnosis"},
    {"query": "How does Apple Scab affect the leaves?", "expected_disease_id": "apple_scab", "expected_sections": ["symptoms"], "expected_content_type": "diagnosis"},
    {"query": "What does Apple Scab look like?", "expected_disease_id": "apple_scab", "expected_sections": ["symptoms"], "expected_content_type": "diagnosis"},
    {"query": "How can I control Apple Scab organically?", "expected_disease_id": "apple_scab", "expected_sections": ["organic_control"], "expected_content_type": "treatment"},
    {"query": "What organic treatment is available for Apple Scab?", "expected_disease_id": "apple_scab", "expected_sections": ["organic_control"], "expected_content_type": "treatment"},
    {"query": "What can I use against Apple Scab without relying on conventional chemical treatment?", "expected_disease_id": "apple_scab", "expected_sections": ["organic_control"], "expected_content_type": "treatment"},
    {"query": "What chemical treatment is recommended for Apple Scab?", "expected_disease_id": "apple_scab", "expected_sections": ["chemical_control"], "expected_content_type": "treatment"},
    {"query": "Which fungicides can control Apple Scab?", "expected_disease_id": "apple_scab", "expected_sections": ["chemical_control"], "expected_content_type": "treatment"},
    {"query": "How can Apple Scab be chemically controlled?", "expected_disease_id": "apple_scab", "expected_sections": ["chemical_control"], "expected_content_type": "treatment"},
    {"query": "How can I prevent Apple Scab?", "expected_disease_id": "apple_scab", "expected_sections": ["preventive_measures"], "expected_content_type": "prevention"},
    {"query": "What preventive measures should I take for Apple Scab?", "expected_disease_id": "apple_scab", "expected_sections": ["preventive_measures"], "expected_content_type": "prevention"},
    {"query": "What causes Apple Scab?", "expected_disease_id": "apple_scab", "expected_sections": ["causes"], "expected_content_type": "cause_transmission"},
    {"query": "How does Apple Scab spread?", "expected_disease_id": "apple_scab", "expected_sections": ["causes"], "expected_content_type": "cause_transmission"},

    # Bacterial Leaf Streak
    {"query": "What are the symptoms of Bacterial Leaf Streak?", "expected_disease_id": "bacterial_leaf_streak", "expected_sections": ["symptoms"], "expected_content_type": "diagnosis"},
    {"query": "How do I identify Bacterial Leaf Streak?", "expected_disease_id": "bacterial_leaf_streak", "expected_sections": ["symptoms"], "expected_content_type": "diagnosis"},
    {"query": "What causes Bacterial Leaf Streak?", "expected_disease_id": "bacterial_leaf_streak", "expected_sections": ["causes"], "expected_content_type": "cause_transmission"},
    {"query": "Is there an organic treatment for Bacterial Leaf Streak?", "expected_disease_id": "bacterial_leaf_streak", "expected_sections": ["organic_control"], "expected_content_type": "treatment"},
    {"query": "What chemical options are available for Bacterial Leaf Streak?", "expected_disease_id": "bacterial_leaf_streak", "expected_sections": ["chemical_control"], "expected_content_type": "treatment"},
    {"query": "How do I prevent Bacterial Leaf Streak?", "expected_disease_id": "bacterial_leaf_streak", "expected_sections": ["preventive_measures"], "expected_content_type": "prevention"},

    # Tomato Spotted Wilt Virus
    {"query": "How can Tomato Spotted Wilt Virus be controlled organically?", "expected_disease_id": "tomato_spotted_wilt_virus", "expected_sections": ["organic_control"], "expected_content_type": "treatment"},
    {"query": "Chemical treatments for Tomato Spotted Wilt Virus", "expected_disease_id": "tomato_spotted_wilt_virus", "expected_sections": ["chemical_control"], "expected_content_type": "treatment"},
    {"query": "TSWV symptoms on leaves and fruit", "expected_disease_id": "tomato_spotted_wilt_virus", "expected_sections": ["symptoms"], "expected_content_type": "diagnosis"},
    {"query": "What is Tomato Spotted Wilt Virus in a nutshell?", "expected_disease_id": "tomato_spotted_wilt_virus", "expected_sections": ["overview"], "expected_content_type": "overview"},
    {"query": "How to prevent Tomato Spotted Wilt Virus?", "expected_disease_id": "tomato_spotted_wilt_virus", "expected_sections": ["preventive_measures"], "expected_content_type": "prevention"},
    {"query": "How is TSWV transmitted?", "expected_disease_id": "tomato_spotted_wilt_virus", "expected_sections": ["causes"], "expected_content_type": "cause_transmission"},

    # Blast of Rice
    {"query": "What are the symptoms of rice blast?", "expected_disease_id": "blast_of_rice", "expected_sections": ["symptoms"], "expected_content_type": "diagnosis"},
    {"query": "How to cure blast of rice organically?", "expected_disease_id": "blast_of_rice", "expected_sections": ["organic_control"], "expected_content_type": "treatment"},
    {"query": "Chemical fungicide for rice blast", "expected_disease_id": "blast_of_rice", "expected_sections": ["chemical_control"], "expected_content_type": "treatment"},
    {"query": "Conditions that favor rice blast", "expected_disease_id": "blast_of_rice", "expected_sections": ["causes", "environment"], "expected_content_type": "cause_transmission"},
    {"query": "Preventing blast of rice", "expected_disease_id": "blast_of_rice", "expected_sections": ["preventive_measures"], "expected_content_type": "prevention"},

    # Powdery Mildew (Mango)
    {"query": "Symptoms of powdery mildew on mango", "expected_disease_id": "powdery_mildew_of_mango", "expected_sections": ["symptoms"], "expected_content_type": "diagnosis"},
    {"query": "Organic remedy for powdery mildew of mango", "expected_disease_id": "powdery_mildew_of_mango", "expected_sections": ["organic_control"], "expected_content_type": "treatment"},
    {"query": "Chemical control of mango powdery mildew", "expected_disease_id": "powdery_mildew_of_mango", "expected_sections": ["chemical_control"], "expected_content_type": "treatment"},

    # General pests/diseases
    {"query": "Aphids overview", "expected_disease_id": "aphids", "expected_sections": ["overview"], "expected_content_type": "overview"},
    {"query": "How to get rid of aphids naturally", "expected_disease_id": "aphids", "expected_sections": ["organic_control"], "expected_content_type": "treatment"},
    {"query": "Chemical pesticides for aphids", "expected_disease_id": "aphids", "expected_sections": ["chemical_control"], "expected_content_type": "treatment"},
    {"query": "What do aphids look like?", "expected_disease_id": "aphids", "expected_sections": ["symptoms"], "expected_content_type": "diagnosis"},
    {"query": "Preventing aphids in the garden", "expected_disease_id": "aphids", "expected_sections": ["preventive_measures"], "expected_content_type": "prevention"},
    {"query": "Stem borer symptoms on maize", "expected_disease_id": "spotted_stemborer", "expected_sections": ["symptoms"], "expected_content_type": "diagnosis"},
    {"query": "Chemical treatment for spotted stemborer", "expected_disease_id": "spotted_stemborer", "expected_sections": ["chemical_control"], "expected_content_type": "treatment"},
    
    # Ambiguous/Broad (we test fallback behavior)
    {"query": "What is the best way to handle apple scab?", "expected_disease_id": "apple_scab", "expected_sections": ["organic_control", "chemical_control", "preventive_measures"], "expected_content_type": "treatment"},
    {"query": "How to deal with bacterial leaf streak", "expected_disease_id": "bacterial_leaf_streak", "expected_sections": ["organic_control", "chemical_control", "preventive_measures"], "expected_content_type": "treatment"},
    {"query": "Tell me about TSWV", "expected_disease_id": "tomato_spotted_wilt_virus", "expected_sections": ["overview", "symptoms"], "expected_content_type": "overview"},

    # Additional Diseases for diversity (Citrus Canker)
    {"query": "What are the symptoms of Citrus Canker?", "expected_disease_id": "citrus_canker", "expected_sections": ["symptoms"], "expected_content_type": "diagnosis"},
    {"query": "How do I identify Citrus Canker?", "expected_disease_id": "citrus_canker", "expected_sections": ["symptoms"], "expected_content_type": "diagnosis"},
    {"query": "What causes Citrus Canker?", "expected_disease_id": "citrus_canker", "expected_sections": ["causes"], "expected_content_type": "cause_transmission"},
    {"query": "Organic remedies for Citrus Canker", "expected_disease_id": "citrus_canker", "expected_sections": ["organic_control"], "expected_content_type": "treatment"},
    {"query": "Chemical treatment options for Citrus Canker", "expected_disease_id": "citrus_canker", "expected_sections": ["chemical_control"], "expected_content_type": "treatment"},
    {"query": "Preventing Citrus Canker outbreaks", "expected_disease_id": "citrus_canker", "expected_sections": ["preventive_measures"], "expected_content_type": "prevention"},

    # Potato Late Blight
    {"query": "Symptoms of Potato Late Blight", "expected_disease_id": "potato_late_blight", "expected_sections": ["symptoms"], "expected_content_type": "diagnosis"},
    {"query": "What does Late Blight look like on potatoes?", "expected_disease_id": "potato_late_blight", "expected_sections": ["symptoms"], "expected_content_type": "diagnosis"},
    {"query": "How is Late Blight transmitted?", "expected_disease_id": "potato_late_blight", "expected_sections": ["causes"], "expected_content_type": "cause_transmission"},
    {"query": "Organic control for Potato Late Blight", "expected_disease_id": "potato_late_blight", "expected_sections": ["organic_control"], "expected_content_type": "treatment"},
    {"query": "Fungicides for Late Blight on Potato", "expected_disease_id": "potato_late_blight", "expected_sections": ["chemical_control"], "expected_content_type": "treatment"},
    {"query": "How to prevent Late Blight in potatoes", "expected_disease_id": "potato_late_blight", "expected_sections": ["preventive_measures"], "expected_content_type": "prevention"},

    # Fall Armyworm
    {"query": "Overview of Fall Armyworm", "expected_disease_id": "fall_armyworm", "expected_sections": ["overview"], "expected_content_type": "overview"},
    {"query": "Identifying Fall Armyworm damage", "expected_disease_id": "fall_armyworm", "expected_sections": ["symptoms"], "expected_content_type": "diagnosis"},
    {"query": "Non-chemical control of Fall Armyworm", "expected_disease_id": "fall_armyworm", "expected_sections": ["organic_control"], "expected_content_type": "treatment"},
    {"query": "Pesticides for Fall Armyworm", "expected_disease_id": "fall_armyworm", "expected_sections": ["chemical_control"], "expected_content_type": "treatment"},
    {"query": "How to stop Fall Armyworm from spreading", "expected_disease_id": "fall_armyworm", "expected_sections": ["preventive_measures"], "expected_content_type": "prevention"},
    {"query": "Fall armyworm causes and lifecycle", "expected_disease_id": "fall_armyworm", "expected_sections": ["causes"], "expected_content_type": "cause_transmission"},

    # Black Spot
    {"query": "What is black spot disease?", "expected_disease_id": "black_spot", "expected_sections": ["overview"], "expected_content_type": "overview"},
    {"query": "Signs of black spot on leaves", "expected_disease_id": "black_spot", "expected_sections": ["symptoms"], "expected_content_type": "diagnosis"},
    {"query": "Organic fungicide for black spot", "expected_disease_id": "black_spot", "expected_sections": ["organic_control"], "expected_content_type": "treatment"},
    {"query": "Chemical spray for black spot", "expected_disease_id": "black_spot", "expected_sections": ["chemical_control"], "expected_content_type": "treatment"},
    {"query": "Black spot prevention tips", "expected_disease_id": "black_spot", "expected_sections": ["preventive_measures"], "expected_content_type": "prevention"},

]

def calculate_metrics(results, expected_disease_id, expected_sections):
    hit_1 = hit_3 = hit_5 = 0
    mrr = 0.0
    
    for i, res in enumerate(results):
        # res can be PointStruct or ScoredPoint, handle both Old/New formats
        payload = res.payload or {}
        
        # In old collection, disease ID was usually under 'disease_id' or 'slug'. 
        # In new collection, it's 'disease_id'
        d_id = payload.get("disease_id") or payload.get("slug")
        section = payload.get("section")
        
        if d_id == expected_disease_id and section in expected_sections:
            if i == 0: hit_1 = 1
            if i < 3: hit_3 = 1
            if i < 5: hit_5 = 1
            mrr = 1.0 / (i + 1)
            break
            
    return hit_1, hit_3, hit_5, mrr

def main():
    print(f"Evaluating {len(GOLD_DATASET)} queries...")
    
    v1_metrics = {"hit_1": 0, "hit_3": 0, "hit_5": 0, "mrr": 0.0}
    v2_metrics = {"hit_1": 0, "hit_3": 0, "hit_5": 0, "mrr": 0.0}
    
    for i, item in enumerate(GOLD_DATASET):
        q = item["query"]
        expected_d_id = item["expected_disease_id"]
        expected_sections = item["expected_sections"]
        
        # Test Old Retriever (pure semantic search)
        v1_results = disease_retriever.search(q, limit=5)
        h1, h3, h5, mrr = calculate_metrics(v1_results, expected_d_id, expected_sections)
        v1_metrics["hit_1"] += h1
        v1_metrics["hit_3"] += h3
        v1_metrics["hit_5"] += h5
        v1_metrics["mrr"] += mrr
        
        # Test New Retriever (V2) with expected disease + section intents (simulating LLM classifier)
        # Note: If intent classifier yields multiple intents, we pass them.
        v2_results = disease_retriever_v2.search(
            question=q, 
            disease_id=expected_d_id, 
            intents=expected_sections, 
            limit=5
        )
        h1_v2, h3_v2, h5_v2, mrr_v2 = calculate_metrics(v2_results, expected_d_id, expected_sections)
        v2_metrics["hit_1"] += h1_v2
        v2_metrics["hit_3"] += h3_v2
        v2_metrics["hit_5"] += h5_v2
        v2_metrics["mrr"] += mrr_v2

    n = len(GOLD_DATASET)
    
    print("\n" + "="*50)
    print("RESULTS COMPARISON")
    print("="*50)
    print(f"{'Metric':<10} | {'V1 (Old)':<15} | {'V2 (New)':<15}")
    print("-" * 50)
    print(f"{'Hit@1':<10} | {v1_metrics['hit_1']/n*100:5.1f}%          | {v2_metrics['hit_1']/n*100:5.1f}%")
    print(f"{'Hit@3':<10} | {v1_metrics['hit_3']/n*100:5.1f}%          | {v2_metrics['hit_3']/n*100:5.1f}%")
    print(f"{'Hit@5':<10} | {v1_metrics['hit_5']/n*100:5.1f}%          | {v2_metrics['hit_5']/n*100:5.1f}%")
    print(f"{'MRR':<10} | {v1_metrics['mrr']/n:5.3f}           | {v2_metrics['mrr']/n:5.3f}")
    print("="*50)

if __name__ == "__main__":
    main()
