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
