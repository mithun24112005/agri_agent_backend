# Gateway Testing & Startup Guide

This document provides step-by-step instructions for starting the complete architecture (Gateway, FastAPI, Streamlit, and backing services) and verifying that authentication, rate limiting, and the proxy work correctly.

---

## 1. Prerequisites

Before starting, ensure you have the following installed:
- **Node.js** (v18+)
- **Redis** (running locally or via Docker)
- **Python 3.13** (with `uv` installed)
- **Docker** (to run Qdrant and Redis)

### Start Backend Services (Redis & Qdrant)

If you use Docker, start them in detached mode:

```bash
# Start Redis (Port 6379)
docker run -p 6379:6379 -d redis

# Start Qdrant (Port 6333) - executed from agent_backend
cd ../agent_backend
docker compose -f agents/docker-compose.yml up -d
```

---

## 2. Start the Services

You will need to open **three separate terminal windows** to run the services.

### Terminal 1: Start the FastAPI AI Backend
If your virtual environment is active (e.g. you ran `.venv\Scripts\Activate` and see `(agent_backend)`), use `python -m`:
```bash
cd ../agent_backend
python -m uvicorn main:app --host 0.0.0.0 --port 8001
```
*(If you have NOT activated the environment, you can use `uv run uvicorn main:app --host 0.0.0.0 --port 8001`)*
*(Wait for "Application startup complete" to appear)*

### Terminal 2: Start the Express Gateway
```bash
cd ../gateway
npm install
npx prisma generate
npx prisma migrate deploy
npm run dev
```
*(You should see "Server running on http://localhost:3001" and "Redis connected for rate limiting")*

### Terminal 3: Start the Streamlit Frontend
If your virtual environment is active:
```bash
cd ../agent_backend
python -m streamlit run frontend/app.py --server.port 8501
```
*(If you have NOT activated the environment, you can use `uv run streamlit run frontend/app.py --server.port 8501`)*
*(This will automatically open your browser to http://localhost:8501)*

---

## 3. Manual Testing via Streamlit (E2E)

1. **Register a User:**
   - Go to the "Register" tab in the UI.
   - Enter a test email (e.g., `farmer@example.com`) and a password (min 8 characters).
   - Click "Register". You should see a success message.

2. **Login:**
   - Go to the "Login" tab.
   - Enter your credentials and login.
   - You should be redirected to the main chat interface, and the sidebar will show your email.

3. **Check System Health:**
   - Look at the sidebar. Under "System Status", it should show **Gateway: Connected**.

4. **Create a Session:**
   - Click **➕ New Chat** in the sidebar. A new session ("New Chat") will appear.

5. **Test the Chat Proxy (No Image):**
   - Ask a question: *"What are the NPK requirements for growing tomatoes?"*
   - Verify that the chat streams back normally and the Agent Activity expander shows the selected agents.
   
6. **Test the Chat Proxy (With Image):**
   - Click "Browse files" on the image uploader.
   - Select an image (e.g., `AppleScab1.JPG` from the `assets` folder).
   - Type *"What disease is this?"* and hit Enter.
   - Verify the AI successfully receives the image, classifies it, and replies.

7. **Logout:**
   - Click **Logout** in the sidebar. You should be returned to the Login screen.

---

## 4. API Testing via cURL (Security & Auth)

Open a new terminal window to test the API directly and verify the security guardrails.

### Test 1: Verify FastAPI is protected
The FastAPI backend should block requests that don't have the `X-Internal-API-Key`.
```bash
curl -X POST http://127.0.0.1:8001/chat \
  -F "query=Hello" \
  -F "session_id=fake-session"
```
**Expected Result:** `{"detail":"Forbidden: Invalid internal API key"}` (HTTP 403)

### Test 2: Register & Login via Gateway
Register (if you haven't already):
```bash
curl -X POST http://127.0.0.1:3001/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"curl_test@example.com", "password":"password123"}'
```

Login and extract tokens:
```bash
curl -X POST http://127.0.0.1:3001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"curl_test@example.com", "password":"password123"}'
```
**Expected Result:** A JSON response containing `accessToken`, `refreshToken`, and `user`.

**Save the `accessToken` and `refreshToken` for the next steps.**
```bash
export ACCESS_TOKEN="your_access_token_here"
export REFRESH_TOKEN="your_refresh_token_here"
```

### Test 3: Test Session Creation (Protected Route)
```bash
curl -X POST http://127.0.0.1:3001/api/sessions \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "API Test Session"}'
```
**Expected Result:** A JSON object with a new `id` and `title`. Save this ID:
```bash
export SESSION_ID="the_id_returned_above"
```

### Test 4: Test Chat Proxy via Gateway
```bash
curl -X POST http://127.0.0.1:3001/api/chat \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "query=What is crop rotation?" \
  -F "session_id=$SESSION_ID"
```
**Expected Result:** The LLM's response successfully proxied back from FastAPI.

### Test 5: Test Refresh Token Rotation
```bash
curl -X POST http://127.0.0.1:3001/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d "{\"refreshToken\": \"$REFRESH_TOKEN\"}"
```
**Expected Result:** A *new* `accessToken` and *new* `refreshToken`.

**Test Rotation Security:** Run the EXACT SAME command again with the OLD `$REFRESH_TOKEN`.
**Expected Result:** `{"error":{"code":"UNAUTHORIZED","message":"Invalid or revoked refresh token"}}`

### Test 6: Test Rate Limiting
Run the following login command rapidly 11 times in a row:
```bash
for i in {1..12}; do curl -X POST http://127.0.0.1:3001/api/auth/login -H "Content-Type: application/json" -d '{"email":"test@test.com", "password":"pass"}'; done
```
**Expected Result:** On the 11th request, you should receive:
`{"error":{"code":"RATE_LIMIT_EXCEEDED","message":"Too many requests, please try again later."}}` (HTTP 429)

### Test 7: Redis Fail-Safe Test
Stop your Redis server:
```bash
docker stop <redis_container_id>
```
Now attempt to hit an endpoint (like register or chat):
```bash
curl -X POST http://127.0.0.1:3001/api/auth/register -H "Content-Type: application/json" -d '{"email":"fail@example.com", "password":"password123"}'
```
**Expected Result:**
`{"error":{"code":"SERVICE_UNAVAILABLE","message":"Service is temporarily unavailable (Rate limiter down)."}}` (HTTP 503)
*(Restart Redis and verify it works again.)*

---

## 5. Common Troubleshooting

- **503 Service Unavailable:** Redis is down. Check your Redis container.
- **403 Forbidden on FastAPI:** Make sure the `INTERNAL_API_SECRET` in `agent_backend/.env` exactly matches `INTERNAL_API_SECRET` in `gateway/.env`.
- **413 Payload Too Large:** The image uploaded to the chat exceeds the 5MB limit.
- **Prisma Error (P2021/P2002):** The SQLite database isn't initialized or in sync. Delete `agent_backend/storage/auth/auth.db` and run `npx prisma migrate dev --name init`.
