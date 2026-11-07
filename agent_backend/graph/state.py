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

def merge_dict(a: Optional[Dict[str, Any]], b: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Reducer function to merge dictionaries in LangGraph parallel fan-out."""
    res = dict(a) if a else {}
    if b:
        res.update(b)
    return res

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
    confidence: Optional[float]
    requires_image: Optional[bool]
    requires_structured_input: Optional[bool]
    missing_parameters: Optional[List[str]]
    requires_clarification: Optional[bool]
    clarification_prompt: Optional[str]

class DiseaseState(TypedDict):
    image_path: Optional[str]
    prediction: Optional[str] # Canonical PlantVillage disease string (e.g. Apple___Apple_scab)
    detection_result: Optional[Dict[str, Any]] # Rich local detector output
    question: str
    disease_id: Optional[str]
    crop: Optional[str]
    disease_title: Optional[str]
    is_healthy: Optional[bool]
    rag_status: Optional[str]
    sources: Optional[List[str]]
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
    confidence: Optional[float]
    requires_image: Optional[bool]
    requires_structured_input: Optional[bool]
    missing_parameters: Optional[List[str]]
    requires_clarification: Optional[bool]
    clarification_prompt: Optional[str]
    validated_crop_parameters: Optional[Dict[str, float]]
    
    # Context across turns
    agricultural_context: Optional[Dict[str, Any]]
    
    # Results from executed agents (with merge_dict reducer for parallel execution)
    agent_responses: Annotated[Dict[str, Any], merge_dict]
    disease_result: Optional[Dict[str, Any]]
    crop_result: Optional[Dict[str, Any]]
    general_result: Optional[Dict[str, Any]]
    
    # Final Output
    final_response: Optional[str]
