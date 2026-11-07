import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from config.settings import settings

class CropRetriever:
    """Context-aware retriever for crop agronomic knowledge with Qdrant and local fallback."""

    def __init__(self):
        self.qdrant = QdrantClient(url=settings.qdrant_url)
        self.collection = "crop_knowledge"
        self._embedding_model = None
        self._local_dataset_path = Path(__file__).resolve().parent.parent / "crop_data" / "verified_crop_knowledge.json"

    @property
    def embedding_model(self):
        if self._embedding_model is None:
            try:
                from fastembed import TextEmbedding
                self._embedding_model = TextEmbedding(model_name="BAAI/bge-large-en-v1.5")
            except Exception as e:
                print(f"[WARN] Failed to load local fastembed model: {e}")
                self._embedding_model = None
        return self._embedding_model

    def embed(self, text: str) -> Optional[List[float]]:
        if self.embedding_model:
            try:
                vecs = list(self.embedding_model.embed([text]))
                return vecs[0].tolist()
            except Exception as e:
                print(f"[WARN] Crop embedding generation failed: {e}")
        return None

    def retrieve_crop_context(
        self,
        crop_name: str,
        user_question: Optional[str] = None,
        soil_ph: Optional[float] = None,
        rainfall_level: Optional[str] = None,
        specific_focus: Optional[str] = None,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Retrieve context-aware chunks for a specific crop from Qdrant,
        falling back to verified local knowledge if unavailable.
        """
        normalized_crop = crop_name.lower().replace("-", "").replace(" ", "")
        chunks = []

        # Build context-aware query
        query_parts = [crop_name, "cultivation", "agronomy"]
        if user_question:
            query_parts.append(user_question)
        if specific_focus:
            query_parts.append(specific_focus)
        if soil_ph is not None:
            query_parts.append(f"pH {soil_ph}")
        if rainfall_level:
            query_parts.append(f"rainfall {rainfall_level}")
        query_text = " ".join(query_parts)

        # 1. Attempt Qdrant vector retrieval
        try:
            vector = self.embed(query_text)
            crop_filter = Filter(must=[FieldCondition(key="crop", match=MatchValue(value=normalized_crop))])
            
            if vector:
                results = self.qdrant.query_points(
                    collection_name=self.collection,
                    query=vector,
                    query_filter=crop_filter,
                    limit=limit
                ).points
                chunks = [p.payload for p in results]
            else:
                # If embedding unavailable, scroll by exact crop filter
                points, _ = self.qdrant.scroll(
                    collection_name=self.collection,
                    scroll_filter=crop_filter,
                    limit=limit
                )
                chunks = [p.payload for p in points]
        except Exception as e:
            print(f"[RETRIEVER] Crop Qdrant search failed ({e}). Falling back to local verified knowledge.")
            chunks = []

        # 2. Deterministic Fallback: verified_crop_knowledge.json
        if not chunks and self._local_dataset_path.exists():
            try:
                with open(self._local_dataset_path, "r", encoding="utf-8") as f:
                    all_data = json.load(f)
                
                # Match crop
                matched = [
                    item for item in all_data
                    if item.get("crop", "").lower().replace("-", "").replace(" ", "") == normalized_crop
                ]
                
                # Rank matched chunks by keyword overlap if user asked a specific question
                if user_question and matched:
                    keywords = set(user_question.lower().split())
                    def score_chunk(item):
                        txt = (item.get("text") or "").lower()
                        return sum(1 for kw in keywords if kw in txt)
                    matched.sort(key=score_chunk, reverse=True)
                else:
                    matched.sort(key=lambda x: x.get("chunk_id", 0))

                chunks = matched[:limit]
            except Exception as e:
                print(f"[RETRIEVER] Crop local fallback failed: {e}")

        return {
            "status": "success",
            "crop": crop_name,
            "data": {
                "chunks": chunks
            }
        }

    def build_crop_context(self, retrieval_result: Dict[str, Any]) -> str:
        """Build structured context string with standardized citations."""
        chunks = retrieval_result.get("data", {}).get("chunks", [])
        if not chunks:
            return ""

        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            source = chunk.get("source", "Verified ICAR/Horticulture Guide")
            crop = chunk.get("crop", "General").title()
            text = chunk.get("page_content") or chunk.get("text") or ""
            
            citation_header = f"[Ref: {source} | Crop: {crop}]"
            context_parts.append(f"{citation_header}\n{text.strip()}")

        return "\n\n".join(context_parts)

crop_retriever = CropRetriever()
