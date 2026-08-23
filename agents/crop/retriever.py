from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from config.settings import settings
from typing import List, Dict, Any

class CropRetriever:
    def __init__(self):
        self.qdrant = QdrantClient(url=settings.qdrant_url)
        self.collection = "crop_knowledge"

    def retrieve_crop_context(self, crop_name: str, limit: int = 20) -> Dict[str, Any]:
        """
        Retrieve chunks related to the specific crop from Qdrant.
        We fetch all relevant chunks by exact crop name.
        """
        # Crop names are saved in lowercase without hyphens (e.g., "rice", "kidneybeans")
        normalized_crop = crop_name.lower().replace("-", "").replace(" ", "")
        
        points, _ = self.qdrant.scroll(
            collection_name=self.collection,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="crop",
                        match=MatchValue(value=normalized_crop),
                    )
                ]
            ),
            limit=limit,
        )
        
        return {
            "status": "success",
            "data": {
                "chunks": [p.payload for p in points]
            }
        }

    def build_crop_context(self, retrieval_result: Dict[str, Any]) -> str:
        """
        Build a string context from the retrieved chunks.
        """
        chunks = retrieval_result.get("data", {}).get("chunks", [])
        
        # Sort chunks if they have a chunk_id for sequential flow
        chunks.sort(key=lambda x: x.get("chunk_id", 0))
        
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            text = chunk.get("page_content") or chunk.get("text") or ""
            context_parts.append(f"--- Document Chunk {i} ---\n{text.strip()}")
            
        return "\n\n".join(context_parts)

crop_retriever = CropRetriever()
