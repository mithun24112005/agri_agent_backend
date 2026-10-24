import json
from pathlib import Path
from typing import List, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny
from huggingface_hub import InferenceClient
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from config.settings import settings

class DiseaseRetrieverV2:
    def __init__(self):
        self.qdrant = QdrantClient(url=settings.qdrant_url)
        self.hf = InferenceClient(provider="hf-inference", api_key=settings.hf_token)
        self.model = "BAAI/bge-m3"
        self.collection = settings.disease_collection_name

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    def embed(self, text: str):
        return self.hf.feature_extraction(text, model=self.model)

    def search(self, question: str, disease_id: Optional[str] = None, intents: Optional[List[str]] = None, limit: int = 5):
        vector = self.embed(question)
        
        must_conditions = []
        if disease_id:
            must_conditions.append(FieldCondition(key="disease_id", match=MatchValue(value=disease_id)))
            
        if intents:
            must_conditions.append(FieldCondition(key="section", match=MatchAny(any=intents)))
            
        filter_obj = Filter(must=must_conditions) if must_conditions else None
        
        results = self.qdrant.query_points(
            collection_name=self.collection,
            query=vector,
            query_filter=filter_obj,
            limit=limit
        ).points
        
        # Fallback 1: If strict filter yielded 0 results, drop section filter
        if len(results) == 0 and intents and disease_id:
            filter_obj = Filter(must=[FieldCondition(key="disease_id", match=MatchValue(value=disease_id))])
            results = self.qdrant.query_points(
                collection_name=self.collection,
                query=vector,
                query_filter=filter_obj,
                limit=limit
            ).points
            
        # Fallback 2: Drop disease filter if still 0
        if len(results) == 0 and disease_id:
            results = self.qdrant.query_points(
                collection_name=self.collection,
                query=vector,
                limit=limit
            ).points
            
        return results

    def build_context(self, question: str, disease_id: Optional[str], intents: Optional[List[str]]) -> str:
        # First attempt vector search via Qdrant & HF embeddings
        try:
            results = self.search(question, disease_id, intents, limit=5)
            if results:
                return "\n\n".join(r.payload.get("text", "") for r in results)
        except Exception as e:
            print(f"[RETRIEVER] Vector search failed ({e}). Falling back to local disease dataset.")

        # Fallback to local verified disease dataset if vector search fails or yields empty results
        if disease_id:
            try:
                from agents.disease.normalizer import normalize_disease
                json_path = settings.disease_dataset_path / f"{disease_id}.json"
                if json_path.exists():
                    with open(json_path, "r", encoding="utf-8") as f:
                        raw_data = json.load(f)
                    norm = normalize_disease(raw_data)
                    chunks = []
                    intent_map = {
                        "overview": ("Overview", norm.overview),
                        "symptoms": ("Symptoms", norm.symptoms),
                        "causes": ("Causes", norm.causes),
                        "organic_control": ("Organic Control", norm.organic_control),
                        "chemical_control": ("Chemical Control", norm.chemical_control),
                        "preventive_measures": ("Preventive Measures", norm.preventive_measures),
                    }
                    if intents:
                        for intent in intents:
                            if intent in intent_map and intent_map[intent][1]:
                                title, content = intent_map[intent]
                                chunks.append(f"### {title}\n{content}")
                    if not chunks:
                        for title, content in [
                            ("Symptoms", norm.symptoms),
                            ("Causes", norm.causes),
                            ("Organic Control", norm.organic_control),
                            ("Chemical Control", norm.chemical_control),
                            ("Preventive Measures", norm.preventive_measures)
                        ]:
                            if content:
                                chunks.append(f"### {title}\n{content}")
                    if chunks:
                        return "\n\n".join(chunks)
            except Exception as e:
                print(f"[RETRIEVER] Local JSON fallback failed: {e}")

        return ""

disease_retriever_v2 = DiseaseRetrieverV2()
disease_retriever = disease_retriever_v2  # Backward compatibility alias
