from langgraph.graph import StateGraph, START, END
from graph.state import CropAgentState
from services.crop_model import crop_model_service
from agents.crop.retriever import crop_retriever
from langchain_core.prompts import ChatPromptTemplate
from langchain.chat_models import init_chat_model
from langchain_core.output_parsers import StrOutputParser

llm = init_chat_model("groq:openai/gpt-oss-120b")

CROP_AGENT_PROMPT = """
You are an expert agricultural consultant specializing in crop recommendations.

Based on the provided soil and environmental parameters, a machine learning model has recommended growing: {crop}

Input Parameters:
- Nitrogen (N): {n}
- Phosphorus (P): {p}
- Potassium (K): {k}
- Temperature: {temperature} °C
- Humidity: {humidity} %
- pH: {ph}
- Rainfall: {rainfall} mm

Derived Features used by the model:
- NPK Mean: {npk_mean}
- Temperature-Humidity Index (THI): {thi}
- pH Category: {ph_category}
- Rainfall Level: {rainfall_level}

Below is detailed agronomic knowledge about {crop}:
{crop_context}

Your Task:
Explain clearly why {crop} is suitable for these conditions and provide actionable advice for the farmer based on the agronomic knowledge provided.
Format your response using Markdown, with clear headings. Keep it practical and easy to understand.
"""

def input_validation_node(state: CropAgentState):
    REQUIRED_FIELDS = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
    user_input = state["input_parameters"]
    missing = [field for field in REQUIRED_FIELDS if field not in user_input]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")
    return {"input_parameters": user_input}

def crop_prediction_node(state: CropAgentState):
    inputs = state["input_parameters"]
    prediction_result = crop_model_service.predict_crop(
        n=inputs["N"],
        p=inputs["P"],
        k=inputs["K"],
        temperature=inputs["temperature"],
        humidity=inputs["humidity"],
        ph=inputs["ph"],
        rainfall=inputs["rainfall"],
    )
    return {
        "prediction_result": prediction_result,
        "recommended_crop": prediction_result["recommended_crop"],
        "derived_features": prediction_result["derived_features"]
    }

def crop_retrieval_node(state: CropAgentState):
    retrieval_result = crop_retriever.retrieve_crop_context(state["recommended_crop"])
    return {"retrieval_result": retrieval_result}

def context_builder_node(state: CropAgentState):
    crop_context = crop_retriever.build_crop_context(state["retrieval_result"])
    return {"crop_context": crop_context}

async def crop_reasoning_node(state: CropAgentState):
    inputs = state["input_parameters"]
    derived = state["derived_features"]
    
    prompt = CROP_AGENT_PROMPT.format(
        crop=state["recommended_crop"],
        n=inputs["N"],
        p=inputs["P"],
        k=inputs["K"],
        temperature=inputs["temperature"],
        humidity=inputs["humidity"],
        ph=inputs["ph"],
        rainfall=inputs["rainfall"],
        npk_mean=derived["NPK_mean"],
        thi=derived["THI"],
        ph_category=derived["ph_category"],
        rainfall_level=derived["rainfall_level"],
        crop_context=state["crop_context"]
    )
    
    response = await llm.ainvoke(prompt)
    return {"explanation": response.content}


workflow = StateGraph(CropAgentState)

workflow.add_node("input_validation", input_validation_node)
workflow.add_node("crop_prediction", crop_prediction_node)
workflow.add_node("crop_retrieval", crop_retrieval_node)
workflow.add_node("context_builder", context_builder_node)
workflow.add_node("crop_reasoning", crop_reasoning_node)

workflow.add_edge(START, "input_validation")
workflow.add_edge("input_validation", "crop_prediction")
workflow.add_edge("crop_prediction", "crop_retrieval")
workflow.add_edge("crop_retrieval", "context_builder")
workflow.add_edge("context_builder", "crop_reasoning")
workflow.add_edge("crop_reasoning", END)

crop_graph = workflow.compile()
