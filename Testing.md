# Testing Guide: Smart Agriculture Backend

This guide outlines the steps to test the backend API using Postman and how to monitor the AI agent executions in LangSmith.

I have already started the backend server for you in the background. It is running at `http://127.0.0.1:8001`.

---

## 1. Testing with Postman

Since the `/chat` endpoint accepts both text and optional image uploads, it requires a `multipart/form-data` request.

### Setting up the Request
1. Open Postman and create a new **POST** request.
2. Set the URL to: `http://127.0.0.1:8001/chat`
3. Go to the **Body** tab.
4. Select **form-data**.

### Test Case 1: Disease Agent (Text Only)
*This tests the text-only disease RAG pipeline.*
- Key: `query` (Type: Text) | Value: `What are the symptoms of apple scab?`
- Click **Send**.

### Test Case 2: Disease Agent (With Image)
*This tests the Disease ML API integration + RAG explanation.*
- Key: `query` (Type: Text) | Value: `What is wrong with my plant?`
- Key: `file` (Type: File) | Value: Select an infected leaf image from your computer. *(Ensure the key type is changed from Text to File by hovering over the key field).*
- Click **Send**.

### Test Case 3: Crop Recommendation Agent
*This tests the feature extraction, Random Forest model, and agronomic reasoning.*
- Key: `query` (Type: Text) | Value: `I have a field with Nitrogen 90, Phosphorus 42, Potassium 43. The temperature is 21C, humidity is 82%, pH is 6.5, and rainfall is 202mm. What crop should I grow?`
- Click **Send**.

### Test Case 4: General Agent
*This tests the Tavily web search integration and guardrails.*
- Key: `query` (Type: Text) | Value: `What are some natural ways to improve soil fertility?`
- Click **Send**.

### Test Case 5: Guardrail Rejection
*This tests the PII and agriculture context guardrails.*
- Key: `query` (Type: Text) | Value: `What is the capital of France?`
- Click **Send**. You should receive a polite rejection explaining that the system only handles agricultural queries.

---

## 2. Monitoring with LangSmith

Since you have added your LangSmith API key and tracing is enabled, every test you run in Postman will automatically be recorded in LangSmith.

### How to view the traces:
1. Log in to your LangSmith account at [smith.langchain.com](https://smith.langchain.com/).
2. On the dashboard, look for the project named **`smart-agriculture`** (defined in your `.env`).
3. Click on the project to view the **Traces** tab.
4. You will see a chronological list of every request made to the `/chat` endpoint.

### What to look for in a Trace:
- Click on any specific trace to see the **LangGraph Execution Flow**.
- You will be able to see the exact steps taken by the orchestrator:
  - **`call_supervisor`**: See how it classified the intent and selected the agent.
  - **`execute_agents`**: See the input to the specific agent (e.g., the extracted parameters for the crop model or the image path).
  - **LLM Calls**: You can expand the LLM nodes to see the exact prompt generated (including the Qdrant context or web search evidence) and the raw response from the Groq `llama-3.3-70b-versatile` model.
  - **`response_node`**: See how the final output was formatted before being sent back to Postman.
