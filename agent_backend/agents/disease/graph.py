import asyncio
from typing import List
from langgraph.graph import StateGraph, START, END
from graph.state import DiseaseState
from agents.disease.mapper import disease_mapper
from agents.disease.classifier import classifier_chain, disease_qa_chain
from agents.disease.retriever import disease_retriever, disease_retriever_v2
from services.disease_detection import detector
from services.disease_detection.exceptions import DiseaseDetectionError

MAX_RETRIES = 3

def extract_fallback_intents(question: str) -> List[str]:
    """Deterministic keyword-based intent fallback when LLM is unreachable."""
    q = question.lower()
    intents = []
    if any(w in q for w in ["symptom", "sign", "look like", "spot", "leaf"]):
        intents.append("symptoms")
    if any(w in q for w in ["cause", "why", "pathogen", "fungus", "bacteria"]):
        intents.append("causes")
    if any(w in q for w in ["organic", "natural", "bio", "home remedy", "neem"]):
        intents.append("organic_control")
    if any(w in q for w in ["chemical", "spray", "fungicide", "pesticide", "cure", "treat", "medicine"]):
        intents.append("chemical_control")
    if any(w in q for w in ["prevent", "avoid", "stop", "protect", "hygiene"]):
        intents.append("preventive_measures")
    if any(w in q for w in ["environment", "weather", "temp", "humidity", "rain"]):
        intents.append("environment")
    if not intents:
        intents = ["overview", "symptoms", "organic_control", "chemical_control", "preventive_measures"]
    return intents

async def invoke_with_retry(chain, input_data, retries=MAX_RETRIES):
    """Invoke an LLM chain with exponential backoff retry for transient network and API errors."""
    for attempt in range(retries):
        try:
            return await chain.ainvoke(input_data)
        except Exception as e:
            error_str = str(e)
            is_retriable = any(term in error_str for term in [
                "Tool choice", "400", "429", "500", "502", "503", "504",
                "Connection", "getaddrinfo", "ConnectError", "timeout"
            ])
            if attempt < retries - 1 and is_retriable:
                wait_time = 2 ** attempt
                print(f"[RETRY] LLM call attempt {attempt + 1}/{retries} failed: {error_str[:120]}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                raise

async def decision_node(state: DiseaseState):
    """If image_path is present, obtain prediction from local FastAPI disease API."""
    if state.get("image_path"):
        try:
            result = await detector.predict(state["image_path"])
            return {
                "prediction": result.canonical_label,
                "detection_result": result.model_dump()
            }
        except DiseaseDetectionError as e:
            print(f"[DISEASE AGENT] Disease prediction failure: {e}")
            raise  # Let it bubble up to api/routes.py for HTTP mapping
        except Exception as e:
            print(f"[DISEASE AGENT] Disease prediction unknown failure: {e}")
            raise
    return {}

def mapper_node(state: DiseaseState):
    """Map prediction to canonical disease ID, crop, and display metadata."""
    dr = state.get("detection_result")
    raw_pred = dr.get("canonical_label") if dr else state.get("prediction")
    crop_hint = dr.get("crop") if dr else state.get("crop")

    if raw_pred:
        mapped = disease_mapper.map_prediction(raw_pred, crop=crop_hint)
        return {
            "disease_id": mapped["disease_id"],
            "crop": mapped["crop"],
            "disease_title": mapped["title"],
            "is_healthy": mapped["is_healthy"]
        }
    return {
        "disease_id": None,
        "crop": None,
        "disease_title": None,
        "is_healthy": False
    }

async def classifier_node(state: DiseaseState):
    """Classify the intents in the user's question with deterministic fallback."""
    try:
        intents_res = await invoke_with_retry(classifier_chain, {"question": state["question"]})
        intents = intents_res.intents
    except Exception as e:
        print(f"[CLASSIFIER] LLM intent classification failed ({e}). Using deterministic keyword fallback.")
        intents = extract_fallback_intents(state["question"])
    return {"intents": intents}

def retriever_node(state: DiseaseState):
    """Retrieve relevant context for the predicted disease and intents."""
    dr = state.get("detection_result")
    disease_id = state.get("disease_id")
    is_healthy = state.get("is_healthy", False)
    intents = state.get("intents", [])
    disease_title = state.get("disease_title") or disease_id or "Identified condition"

    if is_healthy:
        context = (
            f"The analyzed plant is classified as Healthy (confidence: {dr.get('confidence', 1.0) if dr else 1.0:.2%}).\n"
            "There are no active symptoms of infectious fungal, bacterial, or viral disease.\n"
            "General Maintenance Best Practices:\n"
            "- Maintain consistent soil moisture; avoid overhead watering or waterlogging.\n"
            "- Apply balanced fertilization suited to the current crop growth stage.\n"
            "- Ensure adequate plant spacing and airflow to discourage fungal spores.\n"
            "- Perform regular scouting to catch any early signs of pests or nutritional deficiencies."
        )
        return {
            "context": context,
            "rag_status": "healthy_plant",
            "sources": ["General Crop Health Guidelines"]
        }

    # If disease exists in our verified knowledge corpus
    if disease_id and disease_mapper.exists(disease_id):
        context = disease_retriever_v2.build_context(
            question=state["question"],
            disease_id=disease_id,
            intents=intents
        )
        if context.strip():
            return {
                "context": context,
                "rag_status": "success",
                "sources": [f"Knowledge Base: {disease_title}"]
            }

    # Empty retrieval or missing disease in corpus
    context = (
        f"Notice: Specific treatment and management guidelines for '{disease_title}' are not currently indexed in the local knowledge database.\n"
        "Important: Do not fabricate chemical controls, dosages, or ungrounded pesticide recommendations.\n"
        "Advise the grower to inspect for specific lesion patterns, isolate infected foliage, and consult a local agricultural extension officer."
    )
    return {
        "context": context,
        "rag_status": "insufficient_evidence",
        "sources": []
    }

async def llm_node(state: DiseaseState):
    """Generate the grounded final response."""
    dr = state.get("detection_result")
    disease_title = state.get("disease_title") or state.get("disease_id") or "Identified Disease"
    
    if dr:
        conf_pct = f"{dr.get('confidence', 0.0):.2%}"
        crop_name = dr.get("crop") or "Crop"
        canonical = dr.get("canonical_label", "")
        
        top_k_items = dr.get("top_predictions", [])
        alt_str = ", ".join(f"{p.get('label', '')} ({p.get('confidence', 0.0):.2%})" for p in top_k_items[1:]) if len(top_k_items) > 1 else "None"
        
        diagnosis_info = (
            f"- Condition: {disease_title} (Model Class: {canonical})\n"
            f"- Crop: {crop_name}\n"
            f"- Confidence Score: {conf_pct}\n"
            f"- Top Alternatives: {alt_str}\n"
            f"- Knowledge Retrieval Status: {state.get('rag_status', 'unknown')}"
        )
    else:
        diagnosis_info = "Text-only query (No image provided for visual classification)."

    response = await invoke_with_retry(disease_qa_chain, {
        "diagnosis_info": diagnosis_info,
        "context": state.get("context", ""),
        "question": state["question"]
    })
    return {"response": response}

# Build the Graph
workflow = StateGraph(DiseaseState)

workflow.add_node("decision", decision_node)
workflow.add_node("mapper", mapper_node)
workflow.add_node("classifier", classifier_node)
workflow.add_node("retriever", retriever_node)
workflow.add_node("llm", llm_node)

workflow.add_edge(START, "decision")
workflow.add_edge("decision", "mapper")
workflow.add_edge("mapper", "classifier")
workflow.add_edge("classifier", "retriever")
workflow.add_edge("retriever", "llm")
workflow.add_edge("llm", END)

disease_graph = workflow.compile()
