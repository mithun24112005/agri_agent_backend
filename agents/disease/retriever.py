from typing import List, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from huggingface_hub import InferenceClient
from config.settings import settings

class DiseaseRetriever:
    def __init__(self):
        self.qdrant = QdrantClient(url=settings.qdrant_url)
        self.hf = InferenceClient(provider="hf-inference", api_key=settings.hf_token)
        self.model = "BAAI/bge-m3"
        self.collection = "plant_diseases"

        # Order used when building context
        self.section_order = {
            "overview": 1,
            "symptoms": 2,
            "causes": 3,
            "organic_control": 4,
            "chemical_control": 5,
            "preventive_measures": 6,
            "environment": 7,
        }

    def embed(self, text: str):
        return self.hf.feature_extraction(text, model=self.model)

    def search(self, query: str, limit: int = 5):
        vector = self.embed(query)
        results = self.qdrant.query_points(
            collection_name=self.collection,
            query=vector,
            limit=limit,
        )
        return results.points

    def get_disease(self, disease_id: str):
        points, _ = self.qdrant.scroll(
            collection_name=self.collection,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="disease_id",
                        match=MatchValue(value=disease_id),
                    )
                ]
            ),
            limit=50,
        )
        points.sort(
            key=lambda p: self.section_order.get(
                p.payload.get("section", ""), 999
            )
        )
        return points

    def get_section(self, disease_id: str, section: str):
        section = section.lower().replace(" ", "_").replace("-", "_")
        points, _ = self.qdrant.scroll(
            collection_name=self.collection,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="disease_id",
                        match=MatchValue(value=disease_id),
                    ),
                    FieldCondition(
                        key="section",
                        match=MatchValue(value=section),
                    ),
                ]
            ),
            limit=1,
        )
        if len(points) == 0:
            return None
        return points[0]

    def build_context(self, disease_id: str, sections: Optional[List[str]] = None) -> str:
        chunks = self.get_disease(disease_id)
        if sections:
            sections_set = {
                s.lower().replace(" ", "_").replace("-", "_")
                for s in sections
            }
            chunks = [
                chunk for chunk in chunks
                if chunk.payload.get("section") in sections_set
            ]

        return "\n\n".join(
            chunk.payload.get("text", "")
            for chunk in chunks
        )

disease_retriever = DiseaseRetriever()

class DiseaseRetrieverV2:
    def __init__(self):
        self.qdrant = QdrantClient(url=settings.qdrant_url)
        self.hf = InferenceClient(provider="hf-inference", api_key=settings.hf_token)
        self.model = "BAAI/bge-m3"
        self.collection = settings.disease_collection_name

    def embed(self, text: str):
        return self.hf.feature_extraction(text, model=self.model)

    def search(self, question: str, disease_id: Optional[str] = None, intents: Optional[List[str]] = None, limit: int = 5):
        vector = self.embed(question)
        
        must_conditions = []
        if disease_id:
            must_conditions.append(FieldCondition(key="disease_id", match=MatchValue(value=disease_id)))
            
        if intents:
            from qdrant_client.models import MatchAny
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
        results = self.search(question, disease_id, intents, limit=5)
        return "\n\n".join(r.payload.get("text", "") for r in results)

    def debug_search(self, question: str, disease_id: Optional[str] = None, intents: Optional[List[str]] = None, limit: int = 5):
        results = self.search(question, disease_id, intents, limit=limit)
        debug_info = []
        for r in results:
            debug_info.append({
                "score": round(r.score, 4) if hasattr(r, 'score') else None,
                "disease": r.payload.get("disease_name"),
                "section": r.payload.get("section"),
                "content_type": r.payload.get("content_type"),
                "chunk_id": r.payload.get("chunk_id"),
                "text_snippet": r.payload.get("text", "")[:100].replace("\n", " ") + "..."
            })
        return debug_info

disease_retriever_v2 = DiseaseRetrieverV2()
