import argparse
import json
import logging
import uuid
import asyncio
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, 
    PayloadSchemaType
)
from huggingface_hub import AsyncInferenceClient

from config.settings import settings
from agents.disease.normalizer import normalize_disease
from agents.disease.chunker import generate_semantic_chunks, validate_chunk

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def generate_uuid_from_id(chunk_id: str) -> str:
    """Generate deterministic UUID5 from string."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"disease:{chunk_id}"))

async def embed_texts_batch(hf_client: AsyncInferenceClient, texts: list[str], batch_size: int = 20) -> list[list[float]]:
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        try:
            # The hf inference client feature_extraction returns a list of floats for a single string,
            # but if we pass a list of strings, it might return a list of lists.
            # BAAI/bge-m3 works well with feature_extraction.
            # We'll do it concurrently for the batch to be safe.
            tasks = [hf_client.feature_extraction(t, model="BAAI/bge-m3") for t in batch]
            results = await asyncio.gather(*tasks)
            # The result for each is a list of floats or numpy array
            all_embeddings.extend([list(r) for r in results])
        except Exception as e:
            logger.error(f"Error during embedding batch: {e}")
            raise
    return all_embeddings

async def main():
    parser = argparse.ArgumentParser(description="Ingest disease data into Qdrant.")
    parser.add_argument("--dry-run", action="store_true", help="Run without inserting into Qdrant.")
    args = parser.parse_args()

    dataset_path = settings.disease_dataset_path
    if not dataset_path.exists():
        logger.error(f"Dataset path not found: {dataset_path}")
        return

    json_files = list(dataset_path.glob("*.json"))
    logger.info(f"Discovered {len(json_files)} JSON files in {dataset_path}")

    diseases_normalized = 0
    chunks_generated = 0
    chunks_skipped = 0
    chunks_rejected = 0
    
    all_chunks = []

    for file_path in json_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                raw_json = json.load(f)
            
            disease = normalize_disease(raw_json)
            diseases_normalized += 1
            
            chunks = generate_semantic_chunks(disease)
            
            for chunk in chunks:
                is_valid, reason = validate_chunk(chunk)
                if not is_valid:
                    chunks_rejected += 1
                    logger.warning(f"Rejected chunk {chunk.chunk_id}: {reason}")
                    continue
                
                chunks_generated += 1
                all_chunks.append(chunk)
                
        except Exception as e:
            logger.error(f"Error processing {file_path.name}: {e}")
            continue

    logger.info(f"Diseases normalized: {diseases_normalized}")
    logger.info(f"Chunks generated: {chunks_generated}")
    logger.info(f"Chunks rejected: {chunks_rejected}")
    
    if args.dry_run:
        logger.info("DRY RUN COMPLETE. Skipping Qdrant ingestion.")
        if all_chunks:
            logger.info("Sample chunk payload:")
            sample = all_chunks[0]
            print(json.dumps(sample.model_dump(), indent=2))
        return

    logger.info("Initializing Qdrant and Embedding clients...")
    qdrant = QdrantClient(url=settings.qdrant_url)
    hf_client = AsyncInferenceClient(provider="hf-inference", api_key=settings.hf_token)
    
    collection_name = settings.disease_collection_name
    
    # Create collection if it doesn't exist
    existing_collections = [c.name for c in qdrant.get_collections().collections]
    if collection_name not in existing_collections:
        logger.info(f"Creating collection '{collection_name}'...")
        qdrant.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE)
        )
        
        # Create payload indexes
        indexes = ["disease_id", "section", "content_type", "disease_category", "crop"]
        for idx in indexes:
            qdrant.create_payload_index(
                collection_name=collection_name,
                field_name=idx,
                field_schema=PayloadSchemaType.KEYWORD
            )
        logger.info("Payload indexes created.")
    else:
        logger.info(f"Collection '{collection_name}' already exists.")

    logger.info("Embedding and uploading chunks in batches...")
    
    BATCH_SIZE = 50
    for i in range(0, len(all_chunks), BATCH_SIZE):
        batch = all_chunks[i:i+BATCH_SIZE]
        texts = [c.text for c in batch]
        
        try:
            embeddings = await embed_texts_batch(hf_client, texts)
            
            points = []
            for chunk, emb in zip(batch, embeddings):
                point_id = generate_uuid_from_id(chunk.chunk_id)
                payload = chunk.model_dump()
                points.append(PointStruct(id=point_id, vector=emb, payload=payload))
                
            qdrant.upsert(collection_name=collection_name, points=points)
            logger.info(f"Upserted batch {i//BATCH_SIZE + 1} ({len(points)} points)")
            
        except Exception as e:
            logger.error(f"Failed to upsert batch {i//BATCH_SIZE + 1}: {e}")
            
    # Verify post-ingestion
    info = qdrant.get_collection(collection_name)
    logger.info("\n--- Post-Ingestion Verification ---")
    logger.info(f"Collection: {collection_name}")
    logger.info(f"Points count: {info.points_count}")
    logger.info(f"Vector size: {info.config.params.vectors.size}")
    logger.info(f"Distance: {info.config.params.vectors.distance}")
    logger.info(f"Payload schema keys: {list(info.payload_schema.keys())}")

if __name__ == "__main__":
    asyncio.run(main())
