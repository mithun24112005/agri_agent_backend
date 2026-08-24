from langgraph.graph import StateGraph, START, END
from graph.state import DiseaseState
from agents.disease.mapper import disease_mapper
from agents.disease.classifier import classifier_chain, disease_qa_chain
from agents.disease.retriever import disease_retriever
from services.disease_api import predict_disease_from_path
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
    """If image_path is present, get prediction from disease API."""
    if state.get("image_path"):
        try:
            result = await predict_disease_from_path(state["image_path"])
            return {"prediction": result.disease}
        except Exception as e:
            print(f"Disease prediction failed: {e}")
            return {"prediction": None}
    return {}

def mapper_node(state: DiseaseState):
    """Map prediction to disease ID and crop."""
    if state.get("prediction"):
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
    
    # If we have a specific disease_id, use exact match retrieval
    if disease_id and disease_mapper.exists(disease_id):
        context = disease_retriever.build_context(disease_id, intents)
        if not context.strip():
            # Fallback if no sections matched
            context = "No detailed information found for the requested sections."
    else:
        # Fallback to semantic search on the question
        results = disease_retriever.search(state["question"], limit=3)
        context = "\n\n".join(r.payload.get("text", "") for r in results)
        
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
