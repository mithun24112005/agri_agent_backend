# Testing Guide: Session-Scoped Short-Term Memory

This guide outlines how to manually verify the new session memory features.

## 1. Start the Server

```bash
cd d:\agent_backend
uv run uvicorn main:app --host 0.0.0.0 --port 8001
```

## 2. Verify Health Check

Run a `GET` request to `http://127.0.0.1:8001/health`

**Expected Output:**
```json
{
  "status": "ok",
  "message": "Smart Agriculture Backend is healthy",
  "memory": "available"
}
```

## 3. Test Disease Follow-up (No Image)

### Turn 1: Upload image
- **Method**: `POST`
- **URL**: `http://127.0.0.1:8001/chat`
- **Body**: `form-data`
  - `query`: "What disease is this?"
  - `session_id`: "test-session-123"
  - `file`: Select a test leaf image

**Expected:** The Disease Agent correctly identifies the disease and returns information.

### Turn 2: Follow-up question (No Image)
- **Method**: `POST`
- **URL**: `http://127.0.0.1:8001/chat`
- **Body**: `form-data`
  - `query`: "What is the best chemical control for it?"
  - `session_id`: "test-session-123"
  - `file`: [Leave empty]

**Expected:** The Supervisor recognizes "it" refers to the previously detected disease due to conversation history. The Disease Agent answers the question using the stored `disease_result` WITHOUT needing a new image upload.

## 4. Test Crop Agent (State & Params)

- **Method**: `POST`
- **URL**: `http://127.0.0.1:8001/chat`
- **Body**: `form-data`
  - `query`: "Recommend a crop for N=40 P=50 K=50 temperature=28 humidity=75 ph=6.5 rainfall=200"
  - `session_id`: "test-session-123"

**Expected:** The Crop Agent parses the parameters correctly, returns a crop recommendation (e.g., Rice, Papaya), and provides an explanation.

## 5. Test Multi-Agent Routing (Mixed Queries)

- **Method**: `POST`
- **URL**: `http://127.0.0.1:8001/chat`
- **Body**: `form-data`
  - `query`: "Can you tell me the current market price of wheat in India, and also what crop should I plant if my soil has N=20, P=30, K=10, temperature is 22C, humidity is 60, ph is 7.0 and rainfall is 100?"
  - `session_id`: "test-session-123"

**Expected:** The Supervisor should classify intent as `multi_domain` and route to `['general_agent', 'crop_agent']`. The General Agent uses Tavily to fetch wheat prices, and the Crop Agent makes a recommendation based on the soil parameters. The final response should seamlessly combine both answers.

## 6. Test Multi-Agent Routing (Disease + General)

- **Method**: `POST`
- **URL**: `http://127.0.0.1:8001/chat`
- **Body**: `form-data`
  - `query`: "What disease is this? Also, what are some general sustainable farming practices to prevent soil erosion?"
  - `session_id`: "test-session-123"
  - `file`: Select a test leaf image

**Expected:** The Supervisor routes to `['disease_agent', 'general_agent']`. The response synthesizes the disease diagnosis (from the image) with the sustainable farming advice.

## 7. Test Guardrail Rejection

- **Method**: `POST`
- **URL**: `http://127.0.0.1:8001/chat`
- **Body**: `form-data`
  - `query`: "What is the capital of France?"
  - `session_id`: "test-session-123"

**Expected:** The query should be rejected by the Guardrail with a message stating it can only assist with agriculture-related questions.

## 8. Test Cross-Session Isolation

- **Method**: `POST`
- **URL**: `http://127.0.0.1:8001/chat`
- **Body**: `form-data`
  - `query`: "What was the chemical control you suggested earlier?"
  - `session_id`: "different-session-456"
  - `file`: [Leave empty]

**Expected:** The agent should state it does not know what you are referring to or that the query lacks context, proving that memory is isolated to `test-session-123`.

## 9. Test Restart Persistence

1. Restart the `uvicorn` server.
2. Send a follow-up question for `test-session-123`.

**Expected:** The agent should still remember the context because the checkpoints are saved to `storage/checkpoints/langgraph.db`.
