from langgraph.graph import StateGraph, START, END
from graph.state import SupervisorState
from langchain_core.prompts import ChatPromptTemplate
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field
from typing import List, Literal

llm = init_chat_model("groq:openai/gpt-oss-120b")

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
    response = await chain.ainvoke({"query": state["user_query"]})
    return {"sanitized_query": response.content}

async def guardrail_node(state: SupervisorState):
    """Check if the query is relevant to agriculture."""
    query_to_check = state.get("sanitized_query") or state["user_query"]
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Determine if the following query is related to agriculture, farming, crops, plants, or plant diseases. Return a structured decision."),
        ("human", "{query}")
    ])
    chain = prompt | llm.with_structured_output(GuardrailDecision)
    decision = await chain.ainvoke({"query": query_to_check})
    return {
        "is_valid": decision.is_valid,
        "guardrail_reason": decision.reason
    }

async def supervisor_node(state: SupervisorState):
    """Classify the intent and select appropriate agents."""
    query_to_check = state.get("sanitized_query") or state["user_query"]
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are the Supervisor Agent for a smart agriculture platform.
Your job is to analyze the user query and select the appropriate sub-agents.
Available agents:
- disease_agent: Identifies and treats plant diseases (requires image or description).
- crop_agent: Recommends the best crop based on soil/weather data.
- general_agent: General farming advice, best practices, and market information.

If the query requires multiple agents, select all relevant ones and mark intent as 'multi_domain'."""),
        ("human", "{query}")
    ])
    chain = prompt | llm.with_structured_output(SupervisorDecision)
    decision = await chain.ainvoke({"query": query_to_check})
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
