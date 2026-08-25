from langgraph.graph import StateGraph, START, END
from graph.state import SupervisorState
from langchain_core.prompts import ChatPromptTemplate
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field
from typing import List, Literal
import asyncio

llm = init_chat_model("groq:openai/gpt-oss-120b")

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

class GuardrailDecision(BaseModel):
    is_valid: bool = Field(description="True if the query is related to agriculture, farming, crops, or plant diseases.")
    reason: str = Field(description="Reason for rejection or approval.")

class SupervisorDecision(BaseModel):
    intent: Literal["disease", "crop", "general", "multi_domain"]
    tasks: List[str] = Field(description="Break down the user query into distinct tasks.")
    selected_agents: List[Literal["disease_agent", "crop_agent", "general_agent"]]

# ==========================================
# Nodes
# ==========================================

async def pii_sanitizer_node(state: SupervisorState):
    """Sanitize any PII from the user query."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a privacy filter. Rewrite the following text, replacing names, emails, phone numbers, and locations with [REDACTED]. If no PII exists, return the exact original text. DO NOT answer the user's question."),
        ("human", "{query}")
    ])
    chain = prompt | llm
    response = await invoke_with_retry(chain, {"query": state["user_query"]})
    return {"sanitized_query": response.content}

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
        ("system", "Determine if the following query is related to agriculture, farming, crops, plants, or plant diseases. Return a structured decision. CRITICAL: You MUST use the provided tool/function to output your decision. DO NOT output conversational text."),
        ("human", "{query}")
    ])
    chain = prompt | llm.with_structured_output(GuardrailDecision)
    decision = await invoke_with_retry(chain, {"query": query_to_check})
    
    return {
        "is_valid": decision.is_valid,
        "guardrail_reason": decision.reason
    }

async def supervisor_node(state: SupervisorState):
    """Classify the intent and select appropriate agents."""
    query_to_check = state.get("sanitized_query") or state["user_query"]
    context = state.get("conversation_context") or "No prior context."
    has_image = state.get("has_image", False)
    image_note = "The user has uploaded an image of a plant/leaf for analysis." if has_image else "No image was uploaded."
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are the Supervisor Agent for a smart agriculture platform.
Your job is to analyze the user query and select the appropriate sub-agents.
Available agents:
- disease_agent: Identifies and treats plant diseases (requires image or description).
- crop_agent: Recommends the best crop based on soil/weather data.
- general_agent: General farming advice, best practices, and market information.

If the query requires multiple agents, select all relevant ones and mark intent as 'multi_domain'.

Image Status: {image_note}
If an image is uploaded, you MUST select the disease_agent.

Recent Conversation Context:
{context}

CRITICAL: You MUST use the provided tool/function to output your decision. DO NOT output conversational text. DO NOT greet the user."""),
        ("human", "{query}")
    ])
    chain = prompt | llm.with_structured_output(SupervisorDecision)
    decision = await invoke_with_retry(chain, {"query": query_to_check, "context": context, "image_note": image_note})
    return {
        "intent": decision.intent,
        "tasks": decision.tasks,
        "selected_agents": decision.selected_agents
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
