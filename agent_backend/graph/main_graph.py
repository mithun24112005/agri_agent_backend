from langgraph.graph import StateGraph, START, END
from graph.state import MainAgentState
from langchain_core.runnables import RunnableConfig
from agents.supervisor.graph import supervisor_graph
from agents.disease.graph import disease_graph
from agents.crop.graph import crop_graph
from agents.general.graph import general_graph
from agents.response.graph import response_node
from services.disease_detection.exceptions import DiseaseDetectionError
from services.crop_model import CropInputParameters

from agents.supervisor.crop_validator import (
    validate_crop_inputs,
    EXACT_CROP_CLARIFICATION_MESSAGE,
    CropValidationResult
)
from config.llm_resilience import invoke_resiliently

from langchain_core.prompts import ChatPromptTemplate
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import traceback
import os
import asyncio

llm_model_name = os.getenv("MAIN_LLM_MODEL", "groq:openai/gpt-oss-120b")
llm = init_chat_model(llm_model_name)

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
                print(f"[RETRY] Main graph attempt {attempt + 1}/{retries} failed: {error_str[:100]}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                raise

class CropParamsExtraction(BaseModel):
    """Extraction schema without silent zero defaults."""
    N: Optional[float] = Field(default=None, description="Nitrogen ratio in soil if explicitly mentioned")
    P: Optional[float] = Field(default=None, description="Phosphorus ratio in soil if explicitly mentioned")
    K: Optional[float] = Field(default=None, description="Potassium ratio in soil if explicitly mentioned")
    temperature: Optional[float] = Field(default=None, description="Temperature in Celsius if explicitly mentioned")
    humidity: Optional[float] = Field(default=None, description="Relative humidity in % if explicitly mentioned")
    ph: Optional[float] = Field(default=None, description="Soil pH value if explicitly mentioned")
    rainfall: Optional[float] = Field(default=None, description="Rainfall in mm if explicitly mentioned")

# ==========================================
# Nodes
# ==========================================

async def classify_and_route(state: MainAgentState):
    """Invoke the supervisor sub-graph to classify intent, select agents, and enforce crop input validation."""
    messages = state.get("messages", [])
    
    # Format recent messages into a context string (excluding current query)
    context = ""
    if len(messages) > 1:
        recent = messages[-7:-1]
        context_parts = []
        for msg in recent:
            role = getattr(msg, "type", msg.get("role", "unknown") if isinstance(msg, dict) else "unknown")
            content = getattr(msg, "content", msg.get("content", "") if isinstance(msg, dict) else "")
            context_parts.append(f"{role.capitalize()}: {content}")
        context = "\n".join(context_parts)
    
    sup_input = {
        "user_query": state["user_query"],
        "conversation_context": context,
        "has_image": state.get("has_image", False)
    }
    sup_result = await supervisor_graph.ainvoke(sup_input)
    
    selected = list(sup_result.get("selected_agents", []))
    is_valid = sup_result.get("is_valid", True)
    requires_clarification = sup_result.get("requires_clarification", False)
    clarification_prompt = sup_result.get("clarification_prompt")
    missing_parameters = sup_result.get("missing_parameters", [])
    agent_responses_init: Dict[str, Any] = {}
    validated_crop_parameters: Optional[Dict[str, float]] = None
    
    agri_ctx = dict(state.get("agricultural_context") or {})

    # =========================================================================
    # DETERMINISTIC SUPERVISOR CROP INPUT VALIDATION GATE
    # Strictly enforce 7-parameter completeness BEFORE invoking crop_agent.
    # Never apply this validation to fertilizer or general queries!
    # =========================================================================
    if "crop_agent" in selected:
        prior_soil_params = agri_ctx.get("soil_parameters")
        crop_val = validate_crop_inputs(
            query=state["user_query"],
            conversation_context=context,
            prior_parameters=prior_soil_params
        )
        
        if not crop_val.is_complete:
            # INCOMPLETE: Do NOT invoke Crop Recommendation Agent or ML pipeline!
            print(f"[SUPERVISOR CROP GATE] Crop parameters incomplete. Missing: {crop_val.missing_parameters}. Withholding crop ML execution.")
            requires_clarification = True
            clarification_prompt = crop_val.clarification_message
            missing_parameters = crop_val.missing_parameters
            agent_responses_init["crop_agent"] = crop_val.clarification_message
            
            # Save partially extracted valid parameters in context for multi-turn collection
            if crop_val.validated_parameters:
                agri_ctx["soil_parameters"] = crop_val.validated_parameters
                
            # Remove crop_agent from selected so crop_node is NEVER invoked
            selected = [ag for ag in selected if ag != "crop_agent"]
        else:
            # COMPLETE: All 7 parameters verified!
            print(f"[SUPERVISOR CROP GATE] All 7 parameters verified: {crop_val.validated_parameters}. Approving crop recommendation routing.")
            validated_crop_parameters = crop_val.validated_parameters
            agri_ctx["soil_parameters"] = crop_val.validated_parameters
            if selected == ["crop_agent"]:
                requires_clarification = False
                clarification_prompt = None
                missing_parameters = []
    
    print(f"[SUPERVISOR] is_valid={is_valid}, intent={sup_result.get('intent')}, agents_to_run={selected}, requires_clarification={requires_clarification}")
    
    return {
        "sanitized_query": sup_result.get("sanitized_query"),
        "is_valid": is_valid,
        "guardrail_reason": sup_result.get("guardrail_reason"),
        "intent": sup_result.get("intent"),
        "tasks": sup_result.get("tasks", []),
        "selected_agents": selected,
        "confidence": sup_result.get("confidence", 1.0),
        "requires_image": sup_result.get("requires_image", False),
        "requires_structured_input": sup_result.get("requires_structured_input", False),
        "missing_parameters": missing_parameters,
        "requires_clarification": requires_clarification,
        "clarification_prompt": clarification_prompt,
        "validated_crop_parameters": validated_crop_parameters,
        "agricultural_context": agri_ctx,
        "agent_responses": agent_responses_init,
        "final_response": None
    }

def route_after_classify(state: MainAgentState) -> List[str]:
    """Conditional routing: Fan-out to selected agent nodes or route directly to format."""
    # 1. Guardrail rejection -> format directly
    if not state.get("is_valid", True):
        return ["format"]
    
    selected = state.get("selected_agents", [])
    if not selected:
        return ["format"]
        
    targets = []
    if "disease_agent" in selected:
        targets.append("disease_node")
    if "crop_agent" in selected:
        targets.append("crop_node")
    if "general_agent" in selected:
        targets.append("general_node")
        
    return targets if targets else ["format"]

async def disease_node(state: MainAgentState, config: RunnableConfig):
    """Execute the Plant Disease Detection Agent with timeout and isolated error handling."""
    configurable = config.get("configurable", {})
    image_path = configurable.get("image_path")
    query = state.get("sanitized_query") or state.get("user_query")
    
    disease_input = {
        "question": query,
        "image_path": image_path
    }
    
    # Pass prior agricultural context if no new image was provided
    agri_ctx = state.get("agricultural_context") or {}
    prior_disease = state.get("disease_result") or agri_ctx.get("disease")
    if not image_path and prior_disease and "prediction" in prior_disease:
        disease_input["prediction"] = prior_disease["prediction"]
        
    print(f"[EXECUTOR] Running disease_node with input: {disease_input}")
    try:
        res = await asyncio.wait_for(disease_graph.ainvoke(disease_input), timeout=15.0)
        resp_text = res.get("response", "Disease agent did not return a response.")
        
        updates = {"agent_responses": {"disease_agent": resp_text}}
        if res.get("prediction"):
            disease_meta = {
                "prediction": res.get("prediction"),
                "disease_id": res.get("disease_id"),
                "crop": res.get("crop"),
                "is_healthy": res.get("is_healthy", False)
            }
            updates["disease_result"] = disease_meta
            existing_ctx = dict(agri_ctx)
            existing_ctx["disease"] = disease_meta
            updates["agricultural_context"] = existing_ctx
            
        return updates
    except asyncio.TimeoutError:
        print("[TIMEOUT] disease_node timed out after 15s")
        return {"agent_responses": {"disease_agent": "The plant disease analysis service timed out after 15 seconds. Please try again or provide a clearer image."}}
    except DiseaseDetectionError as e:
        print(f"[ERROR] disease_node detection error: {e}")
        return {"agent_responses": {"disease_agent": f"Unable to analyze plant image: {str(e)}"}}
    except Exception as e:
        print(f"[ERROR] disease_node exception: {e}")
        traceback.print_exc()
        return {"agent_responses": {"disease_agent": f"An unexpected error occurred during plant disease analysis: {str(e)}"}}

async def crop_node(state: MainAgentState, config: RunnableConfig):
    """Execute the Crop Recommendation Agent with 7 validated parameters and 15s timeout."""
    validated_params = state.get("validated_crop_parameters")
    
    # Defense-in-depth: Never allow crop ML to execute without all 7 validated parameters
    if not validated_params or len(validated_params) < 7:
        agri_ctx = state.get("agricultural_context") or {}
        crop_val = validate_crop_inputs(
            query=state.get("sanitized_query") or state.get("user_query"),
            prior_parameters=agri_ctx.get("soil_parameters")
        )
        if not crop_val.is_complete:
            print("[FAILSAFE] crop_node blocked execution: inputs incomplete.")
            return {"agent_responses": {"crop_agent": crop_val.clarification_message}}
        validated_params = crop_val.validated_parameters

    crop_input = {"input_parameters": validated_params}
    print(f"[EXECUTOR] Running crop_node ML pipeline with 7 validated parameters: {crop_input}")
    
    try:
        res = await asyncio.wait_for(crop_graph.ainvoke(crop_input), timeout=15.0)
        explanation = res.get("explanation", "Crop agent did not return a response.")
        
        updates = {"agent_responses": {"crop_agent": explanation}}
        if res.get("recommended_crop"):
            crop_meta = {
                "recommended_crop": res.get("recommended_crop"),
                "derived_features": res.get("derived_features")
            }
            updates["crop_result"] = crop_meta
            existing_ctx = dict(state.get("agricultural_context") or {})
            existing_ctx["recommended_crop"] = res.get("recommended_crop")
            existing_ctx["soil_parameters"] = validated_params
            updates["agricultural_context"] = existing_ctx
            
        return updates
    except asyncio.TimeoutError:
        print("[TIMEOUT] crop_node timed out after 15s")
        return {"agent_responses": {"crop_agent": "The crop recommendation service timed out after 15 seconds. Please try again."}}
    except Exception as e:
        print(f"[ERROR] crop_node exception: {e}")
        traceback.print_exc()
        return {"agent_responses": {"crop_agent": f"An error occurred while calculating crop recommendations: {str(e)}"}}

async def general_node(state: MainAgentState, config: RunnableConfig):
    """Execute the General Agricultural Information Agent with 15s timeout."""
    query = state.get("sanitized_query") or state.get("user_query")
    general_input = {"question": query}
    
    print(f"[EXECUTOR] Running general_node with input: {general_input}")
    try:
        res = await asyncio.wait_for(general_graph.ainvoke(general_input), timeout=15.0)
        answer = res.get("answer", "General agent did not return a response.")
        return {
            "agent_responses": {"general_agent": answer},
            "general_result": {"answer": answer}
        }
    except asyncio.TimeoutError:
        print("[TIMEOUT] general_node timed out after 15s")
        return {"agent_responses": {"general_agent": "The agricultural knowledge search timed out after 15 seconds. Please rephrase or try again."}}
    except Exception as e:
        print(f"[ERROR] general_node exception: {e}")
        traceback.print_exc()
        return {"agent_responses": {"general_agent": f"An error occurred while fetching agricultural advice: {str(e)}"}}

async def format_node(state: MainAgentState):
    """Merge outputs via conflict-resolving response_node."""
    return await response_node(state)

# ==========================================
# Main Orchestration Graph
# ==========================================

builder = StateGraph(MainAgentState)

# Add nodes
builder.add_node("classify", classify_and_route)
builder.add_node("disease_node", disease_node)
builder.add_node("crop_node", crop_node)
builder.add_node("general_node", general_node)
builder.add_node("format", format_node)

# Add edges: Start -> Classify
builder.add_edge(START, "classify")

# Conditional Fan-Out from Classify to sub-agents or directly to format
builder.add_conditional_edges(
    "classify",
    route_after_classify,
    ["disease_node", "crop_node", "general_node", "format"]
)

# Fan-In from sub-agents to Format
builder.add_edge("disease_node", "format")
builder.add_edge("crop_node", "format")
builder.add_edge("general_node", "format")

# Format to End
builder.add_edge("format", END)

def build_main_graph(checkpointer=None):
    return builder.compile(checkpointer=checkpointer)
