from langgraph.graph import StateGraph, START, END
from graph.state import DiseaseState
from agents.disease.mapper import disease_mapper
from agents.disease.classifier import classifier_chain, disease_qa_chain
from agents.disease.retriever import disease_retriever, disease_retriever_v2
from services.disease_detection import detector
from services.disease_detection.exceptions import DiseaseDetectionError
import asyncio

MAX_RETRIES = 3

async def invoke_with_retry(chain, input_data, retries=MAX_RETRIES):
    """Invoke an LLM chain with retry logic for transient Groq errors."""
    for attempt in range(retries):
        try:
            return await chain.ainvoke(input_data)
        except Exception as e:
            error_str = str(e)
            if attempt < retries - 1 and ("Tool choice" in error_str or "400" in error_str or "429" in error_str or "500" in error_str or "503" in error_str):
                wait_time = 2 ** attempt
                print(f"[RETRY] Disease agent attempt {attempt + 1}/{retries} failed: {error_str[:100]}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                raise

async def decision_node(state: DiseaseState):
    """If image_path is present, get prediction from HF disease API."""
    if state.get("image_path"):
        try:
            result = await detector.predict(state["image_path"])
            # Return both prediction and the rich detection result
            return {
                "prediction": result.disease,
                "detection_result": result.model_dump()
            }
        except DiseaseDetectionError as e:
            print(f"Disease prediction specific failure: {e}")
            raise # Let it bubble up to api/routes.py for HTTP mapping
        except Exception as e:
            print(f"Disease prediction unknown failure: {e}")
            return {"prediction": None, "detection_result": None}
    return {}

def mapper_node(state: DiseaseState):
    """Map prediction to disease ID and crop."""
    dr = state.get("detection_result")
    
    if dr and dr.get("disease"):
        # We use the raw_label to get the most accurate mapping if disease alone fails
        # but the normalized disease from HF is better. Let's pass disease.
        mapped = disease_mapper.map_prediction(dr["disease"], crop=dr.get("crop"))
        
        # If mapped disease ID is not found, try raw label
        if not mapped["disease_id"] or not disease_mapper.exists(mapped["disease_id"]):
            mapped_raw = disease_mapper.map_prediction(dr["raw_label"], crop=dr.get("crop"))
            if mapped_raw["disease_id"] and disease_mapper.exists(mapped_raw["disease_id"]):
                mapped = mapped_raw
                
        return {
            "disease_id": mapped["disease_id"],
            "crop": mapped["crop"]
        }
    elif state.get("prediction"):
        mapped = disease_mapper.map_prediction(state["prediction"])
        return {
            "disease_id": mapped["disease_id"],
            "crop": mapped["crop"]
        }
    return {"disease_id": None, "crop": None}

async def classifier_node(state: DiseaseState):
    """Classify the intents in the user's question."""
    intents = await invoke_with_retry(classifier_chain, {"question": state["question"]})
    return {"intents": intents.intents}

def retriever_node(state: DiseaseState):
    """Retrieve relevant context for the disease and intents."""
    disease_id = state.get("disease_id")
    intents = state.get("intents", [])
    
    # Use V2 retriever with fallback logic
    valid_disease_id = disease_id if disease_id and disease_mapper.exists(disease_id) else None
    
    context = disease_retriever_v2.build_context(
        question=state["question"], 
        disease_id=valid_disease_id, 
        intents=intents
    )
    
    if not context.strip():
        context = "No detailed information found for the requested topic."
        
    return {"context": context}

async def llm_node(state: DiseaseState):
    """Generate the final response."""
    response = await invoke_with_retry(disease_qa_chain, {
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
