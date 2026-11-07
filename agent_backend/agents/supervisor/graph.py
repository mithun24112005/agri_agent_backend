from langgraph.graph import StateGraph, START, END
from graph.state import SupervisorState
from langchain_core.prompts import ChatPromptTemplate
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Dict, Any
import os
import asyncio

llm_model_name = os.getenv("SUPERVISOR_LLM_MODEL", "groq:openai/gpt-oss-120b")
llm = init_chat_model(llm_model_name)

MAX_RETRIES = 3

async def invoke_with_retry(chain, input_data, retries=MAX_RETRIES):
    """Invoke an LLM chain with retry logic for transient Groq errors."""
    for attempt in range(retries):
        try:
            return await chain.ainvoke(input_data)
        except Exception as e:
            error_str = str(e)
            # Retry on transient Groq errors (Tool choice, rate limits, etc.)
            if attempt < retries - 1 and ("Tool choice" in error_str or "400" in error_str or "429" in error_str or "500" in error_str or "503" in error_str):
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                print(f"[RETRY] Attempt {attempt + 1}/{retries} failed: {error_str[:100]}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                raise

# ==========================================
# Data Models
# ==========================================

IntentType = Literal[
    "disease_diagnosis",
    "disease_treatment",
    "disease_prevention",
    "crop_recommendation",
    "soil_nutrient_management",
    "irrigation_and_cultivation",
    "general_farming_advice",
    "government_schemes_and_subsidies",
    "agricultural_market_prices",
    "multi_intent",
    "follow_up",
    "unsupported_query"
]

AgentType = Literal["disease_agent", "crop_agent", "general_agent"]

class GuardrailDecision(BaseModel):
    is_valid: bool = Field(description="True if the query is related to agriculture, farming, crops, soils, or plant diseases.")
    reason: str = Field(description="Reason for rejection or approval.")

class SupervisorRoutingDecision(BaseModel):
    intent: IntentType = Field(description="The primary intent according to the 12-intent agricultural taxonomy.")
    tasks: List[str] = Field(description="Break down the user query into distinct tasks.")
    selected_agents: List[AgentType] = Field(description="Strictly allowlisted sub-agents: disease_agent, crop_agent, general_agent.")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Routing confidence score.")
    requires_image: bool = Field(default=False, description="True if query or diagnosis requires a visual image.")
    requires_structured_input: bool = Field(default=False, description="True if query needs structured agronomic/soil parameters (e.g. NPK, pH).")
    missing_parameters: List[str] = Field(default_factory=list, description="Missing parameters needed for accurate ML prediction (e.g. ['N', 'P', 'K', 'ph', 'rainfall']).")
    requires_clarification: bool = Field(default=False, description="True if mandatory parameters are missing and user must be asked for them before proceeding.")
    clarification_prompt: Optional[str] = Field(default=None, description="Clear, farmer-friendly question asking for the missing parameters.")
    reason: str = Field(description="Reasoning behind the routing decision and parameter check.")

# Backwards compatibility alias
SupervisorDecision = SupervisorRoutingDecision

# ==========================================
# Nodes
# ==========================================

async def pii_sanitizer_node(state: SupervisorState):
    """Sanitize any personal PII while strictly preserving agricultural geographic context."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a privacy filter for a smart agriculture advisory system.
Your job is to protect personal privacy while strictly preserving all essential agricultural context.

RULES:
1. REDACT personal identifying information (PII):
   - Personal individual names (e.g., 'Rajesh Kumar' -> '[REDACTED]')
   - Phone numbers, mobile numbers (e.g., '9876543210' -> '[REDACTED]')
   - Email addresses (e.g., 'farmer@example.com' -> '[REDACTED]')
   - Identification numbers (e.g., Aadhaar, PAN, voter ID -> '[REDACTED]')
   - Exact private house / street addresses (e.g., 'Flat 402, Green Apartments, MG Road' -> '[REDACTED]')

2. CRITICAL - PRESERVE AGRICULTURAL GEOGRAPHY AND ENTITIES:
   - NEVER redact geographic locations needed for agricultural decisions, weather, soil, or market data!
   - KEEP all Country names (e.g., India, Kenya)
   - KEEP all State / Province names (e.g., Maharashtra, Punjab, Karnataka)
   - KEEP all District names (e.g., Nashik, Ludhiana, Coimbatore)
   - KEEP all Tehsil, Taluk, Block, Mandal names
   - KEEP all Village, Town, and City names (e.g., Baramati, Khanna, Pune)
   - KEEP all APMC Mandi and market names (e.g., Azadpur Mandi, Lasalgaon Mandi)
   - KEEP all crop names, soil types, acreages, and agricultural terms.

3. Output only the sanitized text directly. If no PII exists, return the exact original query.
DO NOT answer the user's question, do not converse, do not add commentary or quotes."""),
        ("human", "{query}")
    ])
    chain = prompt | llm
    try:
        response = await invoke_with_retry(chain, {"query": state["user_query"]})
        return {"sanitized_query": response.content.strip()}
    except Exception as e:
        print(f"[PII SANITIZER FALLBACK] Error in PII sanitization: {e}. Preserving raw query.")
        return {"sanitized_query": state["user_query"]}

async def guardrail_node(state: SupervisorState):
    """Check if the query is relevant to agriculture."""
    query_to_check = state.get("sanitized_query") or state["user_query"]
    has_image = state.get("has_image", False)
    
    # If an image is attached, automatically pass the guardrail
    # since image uploads are inherently for disease detection (agriculture)
    if has_image:
        return {
            "is_valid": True,
            "guardrail_reason": "Image uploaded for plant disease analysis."
        }
    
    context = state.get("conversation_context") or ""
    
    # If there is prior conversation context, the session is already
    # agriculture-related. Any follow-up question (even vague ones like
    # "What are the causes you previously stated?") should pass.
    if context:
        return {
            "is_valid": True,
            "guardrail_reason": "Follow-up to an existing agriculture conversation."
        }
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Determine if the following query is related to agriculture, farming, crops, soils, livestock farming, or plant diseases. Return a structured decision. CRITICAL: You MUST use the provided tool/function to output your decision. DO NOT output conversational text."),
        ("human", "{query}")
    ])
    chain = prompt | llm.with_structured_output(GuardrailDecision)
    try:
        decision = await invoke_with_retry(chain, {"query": query_to_check})
        return {
            "is_valid": decision.is_valid,
            "guardrail_reason": decision.reason
        }
    except Exception as e:
        print(f"[WARN] Guardrail LLM call failed ({e}); checking fallback heuristic.")
        non_agri = ["crypto", "bitcoin", "stock market", "fifa", "movie", "netflix", "jailbreak", "shakespeare", "emperor"]
        q_low = query_to_check.lower()
        if any(term in q_low for term in non_agri):
            return {"is_valid": False, "guardrail_reason": "Query detected as non-agricultural by fallback rule."}
        return {"is_valid": True, "guardrail_reason": "Passed by fallback heuristic under high load."}

async def supervisor_node(state: SupervisorState):
    """Classify the intent into the 12-intent taxonomy and select appropriate agents."""
    query_to_check = state.get("sanitized_query") or state["user_query"]
    context = state.get("conversation_context") or "No prior context."
    has_image = state.get("has_image", False)
    image_note = "The user has uploaded an image of a plant/leaf for analysis." if has_image else "No image was uploaded."
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are the Supervisor Routing Agent for an expert smart agriculture multi-agent platform.
Your task is to analyze the user's query, determine its agricultural intent, and select the appropriate specialized sub-agents.

AVAILABLE SUB-AGENTS:
1. disease_agent: Diagnoses plant diseases, identifies fungal/bacterial/viral symptoms, and provides disease-specific treatment or prevention advice.
2. crop_agent: ML-based crop recommendation using the 7 required parameters (N, P, K, pH, temperature, humidity, rainfall). Recommends which crops to plant.
3. general_agent: Handles fertilizer queries, soil nutrient management, general farming practices, sustainable/organic methods, government schemes (PM-KISAN, subsidies, insurance), and market/mandi prices.

UNIFIED 12-INTENT TAXONOMY:
- disease_diagnosis: Identifying symptoms, leaf lesions, spots, rot, pests -> ['disease_agent']
- disease_treatment: Curatives, chemical/organic treatments, fungicides for existing plant disease -> ['disease_agent']
- disease_prevention: Prophylactic measures, sanitation, resistant varieties to prevent diseases -> ['disease_agent']
- crop_recommendation: Deciding what crops to grow based on soil nutrients, climate, or season -> ['crop_agent']
- soil_nutrient_management: Fertilizer queries, fertilizer requirements, NPK ratios, deficiency correction, organic manure -> ['general_agent']
- irrigation_and_cultivation: Sowing techniques, spacing, irrigation schedules, harvesting advice -> ['general_agent']
- general_farming_advice: General agronomy, sustainable methods, weather impact, general crop management -> ['general_agent']
- government_schemes_and_subsidies: Schemes like PM-KISAN, PMFBY, drip irrigation subsidies, government grants -> ['general_agent']
- agricultural_market_prices: APMC mandi rates, MSP, price trends, commodity selling advice -> ['general_agent']
- multi_intent: Complex query explicitly combining multiple distinct domains -> Multiple agents (e.g. ['crop_agent', 'disease_agent'])
- follow_up: Follow-up question relying heavily on previous conversation context -> Context-derived active agent
- unsupported_query: Non-agricultural queries -> []

PARAMETER & CLARIFICATION RULES:
- If intent is 'crop_recommendation':
  - The crop recommendation ML model relies on 7 parameters: Nitrogen (N), Phosphorus (P), Potassium (K), Soil pH (ph), Rainfall in mm (rainfall), Temperature in °C (temperature), Humidity in % (humidity).
  - All seven parameters must be explicitly supplied. No defaults or fallbacks are allowed.
  - If any parameter is missing, set requires_clarification = True and clarification_prompt = "Please provide the full set of soil and climate parameters for accurate crop recommendation: Nitrogen (N), Phosphorus (P), Potassium (K) levels (kg/ha), soil pH, average temperature (°C), humidity (%), and confirm the rainfall amount (mm)."
- CRITICAL: Fertilizer-related queries (e.g. 'What fertilizer for wheat?', 'Explain NPK fertilizer') belong to 'soil_nutrient_management' and MUST route to 'general_agent'. NEVER require 7 crop parameters for fertilizer queries!

IMAGE RULES:
- Image Status: {image_note}
- If an image is uploaded (has_image=True), you MUST set requires_image=True and select disease_agent.

CONVERSATION CONTEXT:
{context}

CRITICAL: Return your decision strictly through the structured output format."""),
        ("human", "{query}")
    ])
    chain = prompt | llm.with_structured_output(SupervisorRoutingDecision)
    try:
        decision = await invoke_with_retry(chain, {"query": query_to_check, "context": context, "image_note": image_note})
    except Exception as e:
        print(f"[WARN] Supervisor LLM call failed ({e}); falling back to heuristic routing.")
        q_low = query_to_check.lower()
        is_disease = any(w in q_low for w in ["disease", "fungus", "scab", "blight", "spot", "mildew", "rot", "spray", "pest", "pathogen", "infestation"])
        is_crop_rec = any(phrase in q_low for phrase in [
            "recommend a crop", "which crop", "what crop", "what to plant", "suitable crop",
            "crop to grow", "suggest crop", "crop recommendation", "recommend crop", "crop for my farm"
        ]) or (("soil" in q_low or "npk" in q_low) and any(w in q_low for w in ["grow", "plant", "sow", "which", "recommend"]))
        is_fert = any(w in q_low for w in [
            "fertilizer", "fertiliser", "manure", "urea", "dap", "potash", "compost", "vermicompost",
            "nutrient deficiency", "boron", "zinc", "gypsum", "soil nutrient", "organic carbon"
        ])
        is_scheme = any(w in q_low for w in ["scheme", "pm-kisan", "pmfby", "kusum", "subsidy", "kcc", "subvention", "insurance"])
        is_market = any(w in q_low for w in ["mandi", "price", "rate", "msp", "apmc", "market", "e-nam", "enam"])

        agents = []
        if is_disease:
            agents.append("disease_agent")
        if is_crop_rec:
            agents.append("crop_agent")
        if is_fert or is_scheme or is_market:
            if "general_agent" not in agents:
                agents.append("general_agent")

        if len(agents) > 1:
            decision = SupervisorRoutingDecision(
                intent="multi_intent",
                selected_agents=agents,
                tasks=[f"Address compound inquiry across {', '.join(agents)}"],
                reason="Heuristic routing fallback: multiple distinct domains detected",
                confidence=0.80
            )
        elif is_disease:
            decision = SupervisorRoutingDecision(
                intent="disease_diagnosis" if any(w in q_low for w in ["what", "identify", "look", "symptom", "spot", "ring"]) else "disease_treatment",
                selected_agents=["disease_agent"],
                tasks=["Address plant disease inquiry"],
                reason="Heuristic routing fallback on disease keywords",
                confidence=0.75
            )
        elif is_crop_rec:
            decision = SupervisorRoutingDecision(
                intent="crop_recommendation",
                selected_agents=["crop_agent"],
                tasks=["Recommend suitable crops"],
                reason="Heuristic routing fallback on crop recommendation intent",
                confidence=0.75
            )
        elif is_fert:
            decision = SupervisorRoutingDecision(
                intent="soil_nutrient_management",
                selected_agents=["general_agent"],
                tasks=["Provide fertilizer and nutrient management guidance"],
                reason="Heuristic routing to general_agent for fertilizer query",
                confidence=0.85
            )
        elif is_scheme:
            decision = SupervisorRoutingDecision(
                intent="government_schemes_and_subsidies",
                selected_agents=["general_agent"],
                tasks=["Provide government scheme information"],
                reason="Heuristic routing fallback on scheme keywords",
                confidence=0.85
            )
        elif is_market:
            decision = SupervisorRoutingDecision(
                intent="agricultural_market_prices",
                selected_agents=["general_agent"],
                tasks=["Provide agricultural market price guidance"],
                reason="Heuristic routing fallback on market keywords",
                confidence=0.85
            )
        else:
            decision = SupervisorRoutingDecision(
                intent="general_farming_advice",
                selected_agents=["general_agent"],
                tasks=["Provide agricultural farming advice"],
                reason="Heuristic routing fallback on general farming inquiry",
                confidence=0.70
            )
    
    # Enforce image rule: if image was uploaded, ensure disease_agent is present
    selected = list(decision.selected_agents)
    if has_image and "disease_agent" not in selected:
        selected.append("disease_agent")
        
    return {
        "intent": decision.intent,
        "tasks": decision.tasks,
        "selected_agents": selected,
        "confidence": decision.confidence,
        "requires_image": decision.requires_image or has_image,
        "requires_structured_input": decision.requires_structured_input,
        "missing_parameters": decision.missing_parameters,
        "requires_clarification": decision.requires_clarification,
        "clarification_prompt": decision.clarification_prompt
    }

def reject_node(state: SupervisorState):
    """Handle rejected queries."""
    reason = state.get("guardrail_reason", "Your query is not related to agriculture.")
    response = f"I'm sorry, but I can only assist with agriculture-related questions. Reason: {reason}"
    return {"response": response, "selected_agents": []}

def route_guardrail(state: SupervisorState):
    if state.get("is_valid"):
        return "supervisor"
    return "reject"

# ==========================================
# Graph Definition
# ==========================================

builder = StateGraph(SupervisorState)

builder.add_node("pii_sanitizer", pii_sanitizer_node)
builder.add_node("guardrail", guardrail_node)
builder.add_node("supervisor", supervisor_node)
builder.add_node("reject", reject_node)

builder.add_edge(START, "pii_sanitizer")
builder.add_edge("pii_sanitizer", "guardrail")
builder.add_conditional_edges("guardrail", route_guardrail, {"supervisor": "supervisor", "reject": "reject"})
builder.add_edge("supervisor", END)
builder.add_edge("reject", END)

supervisor_graph = builder.compile()
