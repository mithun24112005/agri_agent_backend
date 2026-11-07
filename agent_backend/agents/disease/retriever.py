import json
from pathlib import Path
from typing import List, Optional, Any
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny
from config.settings import settings

class DiseaseRetrieverV2:
    """Anti-contamination disease retriever using local ONNX embeddings and verified fallback."""

    def __init__(self):
        self.qdrant = QdrantClient(url=settings.qdrant_url)
        self.collection = settings.disease_collection_name
        self._embedding_model = None
        self.hf = None
        # Auto-detect collection name if default differs
        try:
            available = [c.name for c in self.qdrant.get_collections().collections]
            if self.collection not in available:
                for candidate in ["plant_diseases", "disease_knowledge_v2"]:
                    if candidate in available:
                        self.collection = candidate
                        break
        except Exception:
            pass
        if settings.hf_token:
            try:
                from huggingface_hub import InferenceClient
                self.hf = InferenceClient(provider="hf-inference", api_key=settings.hf_token)
            except Exception:
                self.hf = None

    @property
    def embedding_model(self):
        if self._embedding_model is None:
            try:
                from fastembed import TextEmbedding
                self._embedding_model = TextEmbedding(model_name="BAAI/bge-large-en-v1.5")
            except Exception as e:
                print(f"[WARN] Failed to load local fastembed model for disease retriever: {e}")
                self._embedding_model = None
        return self._embedding_model

    def embed(self, text: str) -> Optional[List[float]]:
        # Primary: Local 1024-d ONNX embedding
        if self.embedding_model:
            try:
                vecs = list(self.embedding_model.embed([text]))
                return vecs[0].tolist()
            except Exception as e:
                print(f"[WARN] Local disease embedding failed ({e}), attempting HF fallback...")

        # Secondary fallback: Remote HF client
        if self.hf:
            try:
                return self.hf.feature_extraction(text, model="BAAI/bge-m3")
            except Exception as e:
                print(f"[WARN] Remote HF embedding failed: {e}")

        return None

    def search(self, question: str, disease_id: Optional[str] = None, intents: Optional[List[str]] = None, limit: int = 5):
        """
        Search for disease chunks in Qdrant with STRICT anti-contamination guarantee.
        Under NO circumstances is disease_id dropped.
        """
        vector = self.embed(question)
        if not vector:
            return []

        must_conditions = []
        if disease_id:
            must_conditions.append(FieldCondition(key="disease_id", match=MatchValue(value=disease_id)))
            
        if intents:
            must_conditions.append(FieldCondition(key="section", match=MatchAny(any=intents)))
            
        filter_obj = Filter(must=must_conditions) if must_conditions else None
        
        try:
            results = self.qdrant.query_points(
                collection_name=self.collection,
                query=vector,
                query_filter=filter_obj,
                limit=limit
            ).points
        except Exception as e:
            print(f"[RETRIEVER] Vector search error: {e}")
            results = []
        
        # Fallback: If strict section filter yielded 0 results, drop section filter BUT KEEP disease_id filter!
        # NEVER drop disease_id filter as that causes cross-disease contamination.
        if len(results) == 0 and intents and disease_id:
            filter_obj = Filter(must=[FieldCondition(key="disease_id", match=MatchValue(value=disease_id))])
            try:
                results = self.qdrant.query_points(
                    collection_name=self.collection,
                    query=vector,
                    query_filter=filter_obj,
                    limit=limit
                ).points
            except Exception:
                results = []
            
        return results

    def build_context(self, question: str, disease_id: Optional[str], intents: Optional[List[str]]) -> str:
        """
        Build contextual guidance for the disease LLM prompt.
        If Qdrant returns chunks, format with citations.
        If Qdrant returns 0 chunks, fall back deterministically to local verified disease JSON dataset.
        """
        # 1. Attempt vector search via Qdrant
        if disease_id:
            try:
                results = self.search(question, disease_id, intents, limit=5)
                if results:
                    chunks = []
                    for r in results:
                        payload = r.payload or {}
                        txt = payload.get("text", "")
                        sec = payload.get("section", "General").title()
                        dis_title = payload.get("title") or disease_id.replace("_", " ").title()
                        citation = f"[Ref: PlantVillage / Plantix | Disease: {dis_title} | Section: {sec}]"
                        chunks.append(f"{citation}\n{txt}")
                    return "\n\n".join(chunks)
            except Exception as e:
                print(f"[RETRIEVER] Vector search failed ({e}). Falling back to local disease dataset.")

        # 2. Deterministic Fallback: Local curated disease dataset
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
                    dis_title = norm.disease_name or disease_id.replace("_", " ").title()
                    if intents:
                        for intent in intents:
                            if intent in intent_map and intent_map[intent][1]:
                                title, content = intent_map[intent]
                                citation = f"[Ref: Verified Plant Pathology Database | Disease: {dis_title} | Section: {title}]"
                                chunks.append(f"{citation}\n### {title}\n{content}")
                    if not chunks:
                        for title, content in [
                            ("Symptoms", norm.symptoms),
                            ("Causes", norm.causes),
                            ("Organic Control", norm.organic_control),
                            ("Chemical Control", norm.chemical_control),
                            ("Preventive Measures", norm.preventive_measures)
                        ]:
                            if content:
                                citation = f"[Ref: Verified Plant Pathology Database | Disease: {dis_title} | Section: {title}]"
                                chunks.append(f"{citation}\n### {title}\n{content}")
                    if chunks:
                        return "\n\n".join(chunks)
            except Exception as e:
                print(f"[RETRIEVER] Local JSON fallback failed: {e}")

        return ""

disease_retriever_v2 = DiseaseRetrieverV2()
disease_retriever = disease_retriever_v2  # Backward compatibility alias
