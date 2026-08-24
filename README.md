# Smart Agriculture Multi-Agent Backend

A robust, AI-powered smart agriculture assistant backend built using **FastAPI** and **LangGraph**. This system orchestrates multiple specialized sub-agents to provide farmers and agriculturists with accurate disease diagnosis, crop recommendations, and general farming advice.

## 🌟 Key Features

*   **Multi-Agent Orchestration**: A central Supervisor Agent dynamically routes user queries to the most appropriate specialized sub-agents (Disease, Crop, or General). It supports complex, multi-domain queries by running multiple agents concurrently and synthesizing their responses.
*   **Session-Scoped Short-Term Memory**: Built-in persistence using SQLite checkpointers. The system remembers context within a specific `session_id`, allowing users to ask natural follow-up questions (e.g., "What is the best chemical control for it?") without needing to re-upload images or restate the problem.
*   **Disease Agent (Vision + RAG)**: 
    *   Integrates with a dedicated Machine Learning API to classify plant diseases from uploaded images.
    *   Uses a Retrieval-Augmented Generation (RAG) pipeline backed by a **Qdrant** vector database to provide detailed overviews, symptoms, causes, and treatment methods for identified diseases.
*   **Crop Recommendation Agent**: 
    *   Extracts agronomic parameters (N, P, K, temperature, humidity, pH, rainfall) from conversational text.
    *   Utilizes a local pre-trained **Random Forest** classification model to recommend the optimal crop for the specified conditions.
*   **General Agent**: 
    *   Powered by **Tavily Search** to scour the web for live, up-to-date general farming advice, market trends, and sustainable practices.
*   **Production-Grade Guardrails**:
    *   **PII Sanitization**: Automatically scrubs Personally Identifiable Information (names, emails, locations) before sending queries to external LLMs.
    *   **Domain Restriction**: A strict guardrail rejects queries unrelated to agriculture, saving compute and enforcing system boundaries.
*   **Resilience & Error Handling**: Includes exponential backoff and retry logic for intermittent LLM API errors to ensure maximum uptime.
*   **Observability**: Full integration with **LangSmith** for end-to-end tracing of agent states, tool execution, and LLM latency.

---

## 🛠️ Tech Stack

*   **Frameworks**: FastAPI, LangGraph, LangChain
*   **LLM Provider**: Groq (Llama-3 models)
*   **Vector Database**: Qdrant
*   **Machine Learning**: Scikit-Learn (Random Forest)
*   **Tools**: Tavily (Web Search)
*   **Persistence**: SQLite (LangGraph Checkpointers)

---

## 🚀 Setup & Installation

### 1. Prerequisites
*   Python 3.10+
*   `uv` package manager (recommended for fast dependency resolution)

### 2. Install Dependencies
```bash
uv venv
# Activate the virtual environment
# Windows: .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate

uv pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the root directory and configure the following variables:
```env
GROQ_API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key

# LangSmith Tracing (Optional but recommended)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langchain_api_key
LANGCHAIN_PROJECT=smart-agriculture
```

---

## 💻 Running the Application

Start the FastAPI backend server using `uvicorn`:

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8001
```

*   **API Endpoint**: `http://127.0.0.1:8001/chat` (Accepts `multipart/form-data`)
*   **Health Check**: `http://127.0.0.1:8001/health`
*   **Interactive Swagger UI**: `http://127.0.0.1:8001/docs`

---

## 🧪 Testing

The API requires a `multipart/form-data` request with `query`, `session_id`, and an optional `file`. For detailed testing scenarios, including multi-agent mixed queries and cross-session isolation tests, please refer to the [`Testing.md`](./Testing.md) guide included in this repository.