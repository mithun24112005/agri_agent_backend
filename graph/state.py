from typing import TypedDict, Optional, List, Dict, Any, Literal, Annotated
from langgraph.graph.message import add_messages

# ==========================================
# Common States
# ==========================================

class Message(TypedDict):
    role: str
    content: str

# ==========================================
# Agent Specific States
# ==========================================

class SupervisorState(TypedDict):
    user_query: str
    sanitized_query: Optional[str]
    is_valid: bool
    guardrail_reason: Optional[str]
    intent: Optional[str]
    tasks: List[str]
    selected_agents: List[str]
    response: Optional[str]
    conversation_context: Optional[str]
    has_image: Optional[bool]

class DiseaseState(TypedDict):
    image_path: Optional[str]
    prediction: Optional[str] # Might be None if text-only query
    question: str
    disease_id: Optional[str]
    crop: Optional[str]
    intents: Optional[List[str]]
    context: Optional[str]
    response: Optional[str]

class CropAgentState(TypedDict):
    input_parameters: Dict[str, Any]
    derived_features: Optional[Dict[str, Any]]
    prediction_result: Optional[Dict[str, Any]]
    recommended_crop: Optional[str]
    retrieval_result: Optional[Dict[str, Any]]
    crop_context: Optional[str]
    explanation: Optional[str]

class GeneralAgentState(TypedDict):
    question: str
    search_results: Optional[List[Dict[str, Any]]]
    evidence: Optional[str]
    answer: Optional[str]
    formatted_response: Optional[Dict[str, Any]]

# ==========================================
# Main Graph State
# ==========================================

class MainAgentState(TypedDict):
    # History
    messages: Annotated[list, add_messages]

    # Input
    user_query: str
    has_image: Optional[bool]
    
    # State from supervisor
    sanitized_query: Optional[str]
    intent: Optional[str]
    tasks: List[str]
    selected_agents: List[str]
    is_valid: bool
    guardrail_reason: Optional[str]
    
    # Results from executed agents
    agent_responses: Dict[str, Any]
    disease_result: Optional[Dict[str, Any]]
    crop_result: Optional[Dict[str, Any]]
    general_result: Optional[Dict[str, Any]]
    
    # Final Output
    final_response: Optional[str]
