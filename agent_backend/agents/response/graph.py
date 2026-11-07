from langchain_core.prompts import ChatPromptTemplate
from langchain.chat_models import init_chat_model
from graph.state import MainAgentState
import asyncio

import os

response_model_name = os.getenv("RESPONSE_LLM_MODEL", os.getenv("MAIN_LLM_MODEL", "groq:openai/gpt-oss-120b"))
llm = init_chat_model(response_model_name)

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
                print(f"[RETRY] Response aggregator attempt {attempt + 1}/{retries} failed: {error_str[:100]}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                raise

RESPONSE_AGGREGATION_PROMPT = """You are the master response aggregator for a smart agriculture advisory platform.
Your task is to synthesize the responses from specialized agricultural sub-agents into a single, cohesive, authoritative, and farmer-friendly advisory.

SYNTHESIS GUIDELINES:
1. Cohesive Integration:
   - Combine all insights logically under clear, actionable Markdown sections.
   - Do NOT mention internal agent names (e.g., 'crop_agent', 'disease_agent', 'general_agent'). Present the guidance as a unified advisory team.
2. Conflict Detection & Agronomic Reconciliation:
   - Carefully check for contradictory advice across agents (for example, heavy flooding advised for one practice vs moisture-reduction advised for fungal disease control).
   - If a contradiction or tension exists, explicitly reconcile it for the farmer (e.g., explain how to use targeted drip irrigation rather than overhead spraying to protect against moisture-spread pathogens).
3. Partial Failure Handling:
   - If any sub-agent response indicates a timeout or error, smoothly acknowledge that specific aspect could not be fully analyzed without technical jargon or stack traces.
4. Citation & Reference Preservation:
   - Preserve all citations, reference tags (e.g., [Ref: ...]), and source dataset attributions.
5. Grounding & Safety:
   - DO NOT fabricate chemical dosages or unverified government schemes. Keep all advice strictly grounded in the sub-agent responses.
   - Format cleanly in Markdown with tables, lists, or bold highlights where appropriate.
"""

async def response_node(state: MainAgentState):
    """Merge and reconcile outputs from executed sub-agents into a final farmer-facing response."""
    # 1. Guardrail rejection
    if not state.get("is_valid", True):
        reason = state.get("guardrail_reason", "The query is outside the scope of agricultural assistance.")
        rej_resp = f"I'm sorry, but I can only assist with agriculture, farming, crops, soils, and plant health questions. Reason: {reason}"
        return {
            "final_response": rej_resp,
            "messages": [("ai", rej_resp)]
        }
    
    agent_responses = state.get("agent_responses", {})
    requires_clarification = state.get("requires_clarification", False)
    clarification_prompt = state.get("clarification_prompt")
    
    # 2. Pure clarification needed (no sub-agents ran)
    if requires_clarification and clarification_prompt and not agent_responses:
        return {
            "final_response": clarification_prompt,
            "messages": [("ai", clarification_prompt)]
        }
    
    # 3. No agent responses generated
    if not agent_responses:
        fallback = "I could not find a specialized agricultural agent to handle this specific query. Please try asking about crop recommendations, plant disease symptoms, or general farming practices."
        return {
            "final_response": fallback,
            "messages": [("ai", fallback)]
        }

    # 4. Single agent response
    if len(agent_responses) == 1:
        agent_name = list(agent_responses.keys())[0]
        agent_out = agent_responses[agent_name]
        
        # If clarification is also needed for another domain, append it
        if requires_clarification and clarification_prompt:
            final_resp = f"{agent_out}\n\n---\n\n### ℹ️ Additional Information Needed\n{clarification_prompt}"
        else:
            final_resp = agent_out
            
        return {
            "final_response": final_resp,
            "messages": [("ai", final_resp)]
        }

    # 5. Multiple agents ran: synthesize and resolve conflicts
    prompt = ChatPromptTemplate.from_messages([
        ("system", RESPONSE_AGGREGATION_PROMPT),
        ("human", "User Query:\n{query}\n\nSub-agent Responses:\n{responses}")
    ])
    
    responses_text = "\n\n".join(f"[{name}]\n{response}" for name, response in agent_responses.items())
    
    chain = prompt | llm
    result = await invoke_with_retry(chain, {
        "query": state.get("sanitized_query") or state["user_query"],
        "responses": responses_text
    })
    
    final_resp = result.content
    if requires_clarification and clarification_prompt:
        final_resp = f"{final_resp}\n\n---\n\n### ℹ️ Additional Information Needed\n{clarification_prompt}"
        
    return {
        "final_response": final_resp,
        "messages": [("ai", final_resp)]
    }
