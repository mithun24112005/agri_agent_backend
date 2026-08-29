# Testing Guide: Disease Agent V2 RAG Pipeline

This guide will help you manually test the newly rebuilt Disease Agent using the `/api/chat` endpoint of your FastAPI backend. The updated agent uses the `disease_knowledge_v2` Qdrant collection, which features semantic section-chunking, rich metadata filtering, and confidence-aware fallbacks.

## Prerequisites
Make sure your FastAPI server is running. You mentioned it is currently running on port 8001:
```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8001
```

## 1. Verify Server Health
Before sending complex queries, verify the server and persistence checkpointer are online.

```bash
curl -X GET "http://localhost:8001/api/health"
```
**Expected Response:**
```json
{
  "status": "ok",
  "message": "Smart Agriculture Backend is healthy",
  "memory": "available"
}
```

---

## 2. Test Text-Only Queries (Direct Retrieval)

The new agent uses an LLM Intent Classifier to determine the specific sections required before retrieving data.

### Test A: Single Intent (Symptoms)
```bash
curl -X POST "http://localhost:8001/api/chat" \
  -F "query=What are the symptoms of Tomato Early Blight?" \
  -F "session_id=test_text_1"
```
**What to look for:** The agent should provide a focused answer specifically about the *symptoms* of Tomato Early Blight, drawn exclusively from the `symptoms` chunk, rather than dumping the entire disease overview.

### Test B: Multi-Intent (Causes & Organic Control)
```bash
curl -X POST "http://localhost:8001/api/chat" \
  -F "query=What causes Potato Late Blight and how can I treat it organically?" \
  -F "session_id=test_text_2"
```
**What to look for:** The LLM classifier should recognize both `cause_transmission` and `treatment` intents. The V2 Retriever will filter and retrieve only the `causes` and `organic_control` chunks for Potato Late Blight. 

### Test C: Semantic Fallback (Ambiguous Query)
```bash
curl -X POST "http://localhost:8001/api/chat" \
  -F "query=Tell me the best way to handle TSWV" \
  -F "session_id=test_text_3"
```
**What to look for:** If the agent cannot map "TSWV" to the exact `tomato_spotted_wilt_virus` ID, or if the intent is too broad, the V2 Retriever will dynamically fall back to pure semantic search and still return highly relevant Tomato Spotted Wilt Virus chunks.

---

## 3. Test Image-Based Queries (Prediction + Retrieval)

The agent supports taking an image, passing it to the disease prediction API, and then querying the RAG pipeline for that specific predicted disease.

> [!TIP]
> You will need a sample image of a diseased plant (e.g., a tomato leaf with early blight). Let's assume you have a file named `tomato_early_blight_leaf.jpg`.

### Test D: Image Upload + Query
```bash
curl -X POST "http://localhost:8001/api/chat" \
  -F "query=What is this disease and what are the recommended chemical fungicides?" \
  -F "session_id=test_image_1" \
  -F "file=@tomato_early_blight_leaf.jpg"
```
**What happens under the hood:**
1. The `decision_node` intercepts the image and hits the prediction API.
2. The prediction (e.g., `Tomato___Early_blight`) is mapped by `mapper.py` to `early_blight`.
3. The query is classified for intents (e.g., `overview` and `treatment`).
4. The V2 Retriever executes a strict metadata filter: `disease_id="early_blight"` AND `section=["overview", "chemical_control"]`.
5. The LLM formulates the final answer using those exact chunks.

---

## 4. Test Memory / Conversation Context
Because you are passing a `session_id`, the agent remembers previous interactions via the SQLite checkpointer.

### Test E: Contextual Follow-up
Run this immediately after Test A or Test B using the **same** `session_id`:
```bash
curl -X POST "http://localhost:8001/api/chat" \
  -F "query=Are there any preventive measures for it?" \
  -F "session_id=test_text_1"
```
**What to look for:** The agent should remember that "it" refers to Tomato Early Blight (from Test A), retrieve the `preventive_measures` chunk for Tomato Early Blight, and provide the answer.

---

## Troubleshooting Guide

If a retrieval seems incorrect during testing, you can manually inspect the Qdrant V2 collection logic:

**1. Check if the disease exists in V2:**
```bash
uv run python -c "from qdrant_client import QdrantClient; c = QdrantClient(url='http://localhost:6333'); res = c.scroll(collection_name='disease_knowledge_v2', scroll_filter={'must': [{'key': 'disease_id', 'match': {'value': 'early_blight'}}]}, limit=1); print(res)"
```

**2. Check the raw V2 Retriever output (Debug Search):**
You can write a quick debug script to see exactly how the retriever scores your query:
```python
# debug_rag.py
from agents.disease.retriever import disease_retriever_v2
import json

results = disease_retriever_v2.debug_search(
    question="How do I cure tomato early blight organically?", 
    disease_id="early_blight", 
    intents=["organic_control"]
)
print(json.dumps(results, indent=2))
```
This will print the `score`, `section`, and `text_snippet` of the top chunks, proving the semantic engine is prioritizing the correct section!
