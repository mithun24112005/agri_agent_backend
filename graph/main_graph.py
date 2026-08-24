from langgraph.graph import StateGraph, START, END
from graph.state import MainAgentState
from langchain_core.runnables import RunnableConfig
from agents.supervisor.graph import supervisor_graph
from agents.disease.graph import disease_graph
from agents.crop.graph import crop_graph
from agents.general.graph import general_graph
from agents.response.graph import response_node

from langchain_core.prompts import ChatPromptTemplate
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field
import traceback
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
            if attempt < retries - 1 and ("Tool choice" in error_str or "400" in error_str or "429" in error_str or "500" in error_str or "503" in error_str):
                wait_time = 2 ** attempt
                print(f"[RETRY] Main graph attempt {attempt + 1}/{retries} failed: {error_str[:100]}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                raise

class CropParamsExtraction(BaseModel):
    N: float = Field(default=0.0)
    P: float = Field(default=0.0)
    K: float = Field(default=0.0)
    temperature: float = Field(default=25.0)
    humidity: float = Field(default=60.0)
    ph: float = Field(default=6.5)
    rainfall: float = Field(default=100.0)

async def classify_and_route(state: MainAgentState):
    """Invoke the supervisor sub-graph to classify and route."""
    messages = state.get("messages", [])
    
    # Format recent messages into a context string (excluding the current one)
    # The current query is the last human message.
    context = ""
    if len(messages) > 1:
        # Get up to the last 6 messages, excluding the very last one (which is the current query)
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
    
    selected = sup_result.get("selected_agents", [])
    is_valid = sup_result.get("is_valid", True)
    
    print(f"[SUPERVISOR] is_valid={is_valid}, intent={sup_result.get('intent')}, agents={selected}")
    
    return {
        "sanitized_query": sup_result.get("sanitized_query"),
        "is_valid": is_valid,
        "guardrail_reason": sup_result.get("guardrail_reason"),
        "intent": sup_result.get("intent"),
        "tasks": sup_result.get("tasks", []),
        "selected_agents": selected,
        "agent_responses": {},
        "final_response": None
    }

async def run_agents(state: MainAgentState, config: RunnableConfig):
    """Execute the selected sub-agents."""
    selected_agents = state.get("selected_agents", [])
    is_valid = state.get("is_valid", True)
    
    print(f"[EXECUTOR] Running agents: {selected_agents}, is_valid={is_valid}")
    
    # If not valid, return rejection directly
    if not is_valid:
        reason = state.get("guardrail_reason", "Your query is not related to agriculture.")
        rej_resp = f"I'm sorry, but I can only assist with agriculture-related questions. Reason: {reason}"
        return {
            "final_response": rej_resp,
            "messages": [("ai", rej_resp)]
        }
    
    if not selected_agents:
        return {"final_response": "No agents were selected to handle your query."}
    
    responses = {}
    state_updates = {}
    
    # Extract image_path from config
    configurable = config.get("configurable", {})
    image_path = configurable.get("image_path")
    
    for agent in selected_agents:
        try:
            if agent == "disease_agent":
                disease_input = {
                    "question": state.get("sanitized_query") or state["user_query"],
                    "image_path": image_path
                }
                
                # Pass prior context if available and no new image
                prior_disease = state.get("disease_result")
                if not image_path and prior_disease and "prediction" in prior_disease:
                    disease_input["prediction"] = prior_disease["prediction"]
                    
                print(f"[EXECUTOR] Calling disease_agent with: {disease_input}")
                res = await disease_graph.ainvoke(disease_input)
                responses["disease_agent"] = res.get("response", "Disease agent did not return a response.")
                
                # Save structured result
                if res.get("prediction"):
                    state_updates["disease_result"] = {
                        "prediction": res.get("prediction"),
                        "disease_id": res.get("disease_id"),
                        "crop": res.get("crop")
                    }
                
            elif agent == "crop_agent":
                prompt = ChatPromptTemplate.from_messages([
                    ("system", "Extract soil and environmental parameters from the text. Use defaults if not mentioned: N=0, P=0, K=0, temp=25, humidity=60, ph=6.5, rainfall=100."),
                    ("human", "{query}")
                ])
                chain = prompt | llm.with_structured_output(CropParamsExtraction)
                query_to_check = state.get("sanitized_query") or state["user_query"]
                params = await invoke_with_retry(chain, {"query": query_to_check})
                
                crop_input = {"input_parameters": params.model_dump()}
                
                # Add prior crop result context to query
                prior_crop = state.get("crop_result")
                if prior_crop and prior_crop.get("recommended_crop"):
                    # We inject the prior crop into the prompt implicitly by modifying query?
                    pass # Actually crop_agent relies strictly on NPK input parameters for now.
                    
                print(f"[EXECUTOR] Calling crop_agent with: {crop_input}")
                res = await crop_graph.ainvoke(crop_input)
                responses["crop_agent"] = res.get("explanation", "Crop agent did not return a response.")
                
                # Save structured result
                if res.get("recommended_crop"):
                    state_updates["crop_result"] = {
                        "recommended_crop": res.get("recommended_crop"),
                        "derived_features": res.get("derived_features")
                    }
                    
            elif agent == "general_agent":
                general_input = {
                    "question": state.get("sanitized_query") or state["user_query"]
                }
                print(f"[EXECUTOR] Calling general_agent with: {general_input}")
                res = await general_graph.ainvoke(general_input)
                responses["general_agent"] = res.get("answer", "General agent did not return a response.")
        except Exception as e:
            print(f"[EXECUTOR] Error in {agent}: {e}")
            traceback.print_exc()
            responses[agent] = f"Agent error: {e}"
            
    print(f"[EXECUTOR] Collected responses from: {list(responses.keys())}")
    state_updates["agent_responses"] = responses
    return state_updates

async def format_response(state: MainAgentState):
    """Format the final response."""
    # If final_response was already set (e.g. by rejection), skip
    if state.get("final_response"):
        return {}
    
    agent_responses = state.get("agent_responses", {})
    
    if not agent_responses:
        return {"final_response": "I couldn't process your request. No agent responses were generated."}

    # Single agent - return directly
    if len(agent_responses) == 1:
        agent_name = list(agent_responses.keys())[0]
        final_resp = agent_responses[agent_name]
        return {
            "final_response": final_resp,
            "messages": [("ai", final_resp)]
        }

    # Multiple agents - merge with LLM
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are the final response formatter for a smart agriculture assistant.
Below are responses generated by specialized sub-agents based on the user's query.
Synthesize these responses into a single, cohesive, and easy-to-read response.
Keep all important information and format nicely in Markdown.
Do not mention the names of the sub-agents."""),
        ("human", "User Query:\n{query}\n\nSub-agent Responses:\n{responses}")
    ])
    
    responses_text = "\n\n".join(f"[{name}]\n{response}" for name, response in agent_responses.items())
    
    chain = prompt | llm
    result = await invoke_with_retry(chain, {
        "query": state["user_query"],
        "responses": responses_text
    })
    
    return {
        "final_response": result.content,
        "messages": [("ai", result.content)]
    }

# ==========================================
# Main Orchestration Graph
# ==========================================

builder = StateGraph(MainAgentState)

builder.add_node("classify", classify_and_route)
builder.add_node("run_agents", run_agents)
builder.add_node("format", format_response)

builder.add_edge(START, "classify")
builder.add_edge("classify", "run_agents")
builder.add_edge("run_agents", "format")
builder.add_edge("format", END)

def build_main_graph(checkpointer=None):
    return builder.compile(checkpointer=checkpointer)
