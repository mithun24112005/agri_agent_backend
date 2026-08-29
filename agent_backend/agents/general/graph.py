from langgraph.graph import StateGraph, START, END
from graph.state import GeneralAgentState
from langchain_core.prompts import ChatPromptTemplate
from langchain.chat_models import init_chat_model
from langchain_community.tools.tavily_search import TavilySearchResults
from config.settings import settings

llm = init_chat_model("groq:openai/gpt-oss-120b")
search_tool = TavilySearchResults(max_results=5, search_depth="advanced")

GENERAL_REASONING_PROMPT = """
You are an expert agricultural advisor.

Your task is to answer the user's question using ONLY the provided evidence.

Instructions:
1. Read all the evidence carefully.
2. Combine information from multiple sources.
3. Do not invent facts.
4. If the evidence is insufficient, clearly say so.
5. Explain the answer in simple language suitable for farmers.
6. Use markdown headings and bullet points.
7. Do not mention the evidence or that you are an AI.

User Question:
{question}

Evidence:
{evidence}
"""

def input_validation_node(state: GeneralAgentState):
    question = state["question"].strip()
    if not question:
        raise ValueError("Question cannot be empty.")
    return {"question": question}

async def information_retrieval_node(state: GeneralAgentState):
    # ainvoke to make it async
    results = await search_tool.ainvoke(state["question"])
    return {"search_results": results}

def evidence_processing_node(state: GeneralAgentState):
    search_results = state["search_results"]
    evidence_blocks = []
    
    for idx, result in enumerate(search_results, start=1):
        title = result.get("title", "Unknown Source")
        content = result.get("content", "")
        url = result.get("url", "")
        
        block = f"Source {idx}\nTitle: {title}\nContent:\n{content}\nReference:\n{url}"
        evidence_blocks.append(block.strip())
        
    evidence = "\n\n" + "=" * 80 + "\n\n" + "\n\n".join(evidence_blocks)
    return {"evidence": evidence}

async def agricultural_reasoning_node(state: GeneralAgentState):
    prompt = ChatPromptTemplate.from_template(GENERAL_REASONING_PROMPT)
    chain = prompt | llm
    
    response = await chain.ainvoke({
        "question": state["question"],
        "evidence": state["evidence"]
    })
    return {"answer": response.content}


builder = StateGraph(GeneralAgentState)

builder.add_node("input_validation", input_validation_node)
builder.add_node("information_retrieval", information_retrieval_node)
builder.add_node("evidence_processing", evidence_processing_node)
builder.add_node("agricultural_reasoning", agricultural_reasoning_node)

builder.add_edge(START, "input_validation")
builder.add_edge("input_validation", "information_retrieval")
builder.add_edge("information_retrieval", "evidence_processing")
builder.add_edge("evidence_processing", "agricultural_reasoning")
builder.add_edge("agricultural_reasoning", END)

general_graph = builder.compile()
