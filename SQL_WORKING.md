# SQL_WORKING.md

## Memory, Sessions & Persistence Guide

This document explains **everything that happens to data** in the CropSage platform: how a user is authenticated, how a chat session is created, how every message is stored, how the AI remembers earlier turns, where images live, and how to inspect or clean everything with SQL.

It is written for developers and operators who need to understand or debug the system without reading the entire codebase first.

---

## Table of Contents

1. [The 60-Second Mental Model](#1-the-60-second-mental-model)
2. [Memory Layers at a Glance](#2-memory-layers-at-a-glance)
3. [Architecture & Data Ownership](#3-architecture--data-ownership)
4. [Part A — User Identity & Authentication Memory](#4-part-a--user-identity--authentication-memory)
5. [Part B — Chat Sessions (Conversation Index)](#5-part-b--chat-sessions-conversation-index)
6. [Part C — A Chat Turn & Conversation Memory](#6-part-c--a-chat-turn--conversation-memory)
7. [Part D — What the AI Actually Remembers](#7-part-d--what-the-ai-actually-remembers)
8. [Part E — Image Memory](#8-part-e--image-memory)
9. [Part F — Chat History Retrieval](#9-part-f--chat-history-retrieval)
10. [Part G — Database Reference](#10-part-g--database-reference)
11. [Part H — SQL Cookbook](#11-part-h--sql-cookbook)
12. [Part I — Configuration & Operations](#12-part-i--configuration--operations)
13. [Part J — Known Limitations & Gotchas](#13-part-j--known-limitations--gotchas)
14. [Part K — Troubleshooting](#14-part-k--troubleshooting)
15. [Appendix — File Map & Glossary](#15-appendix--file-map--glossary)

---

## 1. The 60-Second Mental Model

CropSage uses **two separate PostgreSQL databases** with two completely different responsibilities:

| Database | Owner | Purpose |
|---|---|---|
| `agri_auth` | Express gateway + Prisma | Who the user is, login tokens, and the list of chat sessions |
| `agri_memory` | FastAPI + LangGraph | The actual conversation content and agent state |

The most important idea:

> **A chat session ID is the bridge between the two databases.**
>
> The gateway creates a `Session` row in `agri_auth` and gives it a UUID. That same UUID is sent to FastAPI as `session_id`, and FastAPI uses it as the LangGraph `thread_id` in `agri_memory`.

So the flow is:

```text
User account  ->  agri_auth.User
Login tokens  ->  agri_auth.RefreshToken
Chat thread   ->  agri_auth.Session.id  ==  agri_memory.checkpoints.thread_id
Messages      ->  LangGraph checkpoints in agri_memory
Images        ->  agent_backend/storage/uploads/ (file system)
```

Nothing in `agri_auth` stores message text. Nothing in `agri_memory` stores the user's email or password. The two databases are joined **logically by the session UUID**, not by a database foreign key.

---

## 2. Memory Layers at a Glance

| Layer | What it holds | Where it lives | Written by | Survives restart? |
|---|---|---|---|---|
| Account identity | Email, password hash, active flag | `agri_auth."User"` | Gateway | Yes |
| Login sessions | SHA-256 hashes of refresh tokens | `agri_auth."RefreshToken"` | Gateway | Yes |
| Chat thread index | Session title, owner, timestamps | `agri_auth."Session"` | Gateway | Yes |
| Full conversation | Every human/AI message and agent state | `agri_memory` checkpoint tables | FastAPI / LangGraph | Yes |
| Structured agent memory | Last disease result, last crop result | Inside LangGraph state | FastAPI / LangGraph | Yes |
| Uploaded images | JPEG/PNG/WebP/GIF files | `agent_backend/storage/uploads/` | FastAPI | Yes |
| Active context window | Last 6 prior messages | Process memory during a request | FastAPI | No — rebuilt each turn |
| Domain knowledge | Crop and disease documents | Qdrant | Ingestion scripts | Yes |
| Rate limiting | Request counters | Redis | Gateway | Depends on Redis persistence |
| UI state | Tokens and thread cache | Browser `localStorage` / React | Frontend | Until browser storage is cleared |

**Important distinctions:**

- **Redis is not conversation memory.** It only stores rate-limit counters.
- **Qdrant is not conversation memory.** It stores agricultural knowledge used for RAG.
- **`agri_auth.Session` is not a login session.** It is a chat thread. Login sessions are represented by `RefreshToken` rows.
- **The browser does not own the conversation.** It fetches history from FastAPI through the gateway.

---

## 3. Architecture & Data Ownership

```mermaid
flowchart TB
    Browser["React Frontend<br/>localStorage: access + refresh tokens"]

    subgraph GW["Express Gateway :3001"]
        Auth["Auth Controller"]
        SessionCtl["Session Controller"]
        ChatCtl["Chat Controller"]
        Prisma["Prisma Client"]
    end

    subgraph AUTHDB["PostgreSQL: agri_auth"]
        UserTbl["User"]
        SessionTbl["Session"]
        TokenTbl["RefreshToken"]
    end

    subgraph AI["FastAPI Backend :8001"]
        Routes["/chat<br/>/chat/{session_id}"]
        Graph["LangGraph Main Graph<br/>classify -> run_agents -> format"]
    end

    subgraph MEMDB["PostgreSQL: agri_memory"]
        Checkpoints["checkpoints"]
        Blobs["checkpoint_blobs"]
        Writes["checkpoint_writes"]
        Migrations["checkpoint_migrations"]
    end

    subgraph FILES["Local File System"]
        Uploads["agent_backend/storage/uploads/"]
    end

    subgraph EXTERNAL["External Services"]
        Redis["Redis<br/>rate limits only"]
        Qdrant["Qdrant<br/>agricultural knowledge"]
        Groq["Groq LLM"]
        Tavily["Tavily Search"]
    end

    Browser -->|"Bearer access token"| GW
    Auth --> Prisma
    SessionCtl --> Prisma
    ChatCtl --> Prisma
    Prisma --> UserTbl
    Prisma --> SessionTbl
    Prisma --> TokenTbl

    ChatCtl -->|"X-Internal-API-Key<br/>query + session_id + file"| Routes
    Routes --> Graph
    Graph <-->|"thread_id = session_id"| Checkpoints
    Checkpoints --- Blobs
    Checkpoints --- Writes
    Checkpoints --- Migrations
    Routes --> Uploads
    GW --> Redis
    Graph --> Qdrant
    Graph --> Groq
    Graph --> Tavily
```

### Who is allowed to do what

| Operation | Enforced by | Check |
|---|---|---|
| Read a user's sessions | Gateway | `Session.userId === req.user.id` |
| Send a message | Gateway | Session exists and belongs to `req.user.id` |
| Read chat history | Gateway | Session exists and belongs to `req.user.id` |
| Call FastAPI directly | FastAPI | `X-Internal-API-Key` must equal `INTERNAL_API_SECRET` |
| Read a checkpoint | FastAPI | Only by `thread_id`; no user ID is stored in `agri_memory` |

The gateway is the **authorization boundary**. FastAPI trusts the internal API key and the `session_id` it receives. This is why the internal key must never be exposed to the browser.

---

## 4. Part A — User Identity & Authentication Memory

### 4.1 Registration

**Endpoint:** `POST /api/auth/register`

```json
{
  "email": "farmer@example.com",
  "password": "minimum-8-characters"
}
```

Flow:

1. Zod validates that the email is valid and the password has at least 8 characters.
2. The gateway checks `User.email` for an existing row.
3. The password is hashed with **Argon2** (`argon2.hash`).
4. A new `User` row is inserted.
5. Response: `201 { "status": "success", "message": "Registration successful" }`.

No chat session is created during registration. No tokens are returned.

### 4.2 Login

**Endpoint:** `POST /api/auth/login`

```json
{
  "email": "farmer@example.com",
  "password": "minimum-8-characters"
}
```

Flow:

1. The gateway loads the user by email.
2. If the user is missing or `isActive = false`, it returns `401 Invalid email or password`.
3. Argon2 verifies the password against `User.passwordHash`.
4. The gateway creates:
   - an **access token** — a JWT signed with `JWT_ACCESS_SECRET`, valid for `JWT_ACCESS_EXPIRES_IN` (default **15 minutes**);
   - a **refresh token** — 40 random bytes rendered as an 80-character hex string.
5. The raw refresh token is **never stored**. Only its SHA-256 hash is stored in `RefreshToken.tokenHash`.
6. The refresh token row expires after **7 days** (hardcoded in `token.service.js`).
7. Response:

```json
{
  "accessToken": "eyJ...",
  "refreshToken": "a1b2c3..."
}
```

The frontend stores both in `localStorage`:

- `agrimind.access-token`
- `agrimind.refresh-token`

### 4.3 Authenticated requests

Every protected request sends:

```http
Authorization: Bearer <accessToken>
```

The auth middleware:

1. Verifies the JWT signature and expiry.
2. Confirms `type === "access"`.
3. Loads the user from `agri_auth."User"`.
4. Rejects if the user no longer exists or is inactive.
5. Attaches `req.user = { id: user.id }`.

The frontend automatically calls `POST /api/auth/refresh` when it receives a `401`, then retries the original request once.

### 4.4 Refresh token rotation

**Endpoint:** `POST /api/auth/refresh`

```json
{ "refreshToken": "a1b2c3..." }
```

Flow:

1. Hash the submitted refresh token with SHA-256.
2. Look up the hash in `RefreshToken`.
3. Reject if not found, already revoked, expired, or the user is inactive.
4. Generate a new access token and a new refresh token.
5. In a single Prisma transaction:
   - mark the old refresh token row as revoked (`revokedAt = now()`);
   - insert the new refresh token hash.
6. Return the new pair.

This is **rotation**: every refresh token can be used once.

If an already-revoked token is presented, the gateway logs a security warning and rejects the request. It does **not** currently revoke the whole token family.

### 4.5 Logout

**Endpoint:** `POST /api/auth/logout` (requires a valid access token)

```json
{ "refreshToken": "a1b2c3..." }
```

The gateway hashes the refresh token and sets `revokedAt = now()` on the matching row.

**Important:** the access token itself is a stateless JWT. Logout does **not** blacklist it. It remains valid until its 15-minute expiry. The frontend removes both tokens from `localStorage`.

### 4.6 Authentication tables

#### `agri_auth."User"`

| Column | Type | Notes |
|---|---|---|
| `id` | `TEXT` / UUID | Primary key |
| `email` | `TEXT` | Unique |
| `passwordHash` | `TEXT` | Argon2 hash |
| `isActive` | `BOOLEAN` | Default `true` |
| `createdAt` | `TIMESTAMP(3)` | Default `now()` |
| `updatedAt` | `TIMESTAMP(3)` | Auto-updated by Prisma |

#### `agri_auth."RefreshToken"`

| Column | Type | Notes |
|---|---|---|
| `id` | `TEXT` / UUID | Primary key |
| `userId` | `TEXT` | FK to `User.id`, cascade delete |
| `tokenHash` | `TEXT` | Unique SHA-256 hash |
| `expiresAt` | `TIMESTAMP(3)` | Now + 7 days |
| `createdAt` | `TIMESTAMP(3)` | Default `now()` |
| `revokedAt` | `TIMESTAMP(3)` | `NULL` while active |

#### `agri_auth."Session"`

| Column | Type | Notes |
|---|---|---|
| `id` | `TEXT` / UUID | Primary key, also the LangGraph `thread_id` |
| `title` | `TEXT` | Display title |
| `userId` | `TEXT` | FK to `User.id`, cascade delete |
| `createdAt` | `TIMESTAMP(3)` | Default `now()` |
| `updatedAt` | `TIMESTAMP(3)` | Auto-updated on row update |

### 4.7 What is *not* stored for authentication

- Plain-text passwords — never stored.
- Raw refresh tokens — only SHA-256 hashes.
- Access tokens — stateless JWTs, never stored in the database.
- Login IP addresses or device fingerprints — not stored by the current code.
- A server-side login-session table — login state is the refresh-token row.

---

## 5. Part B — Chat Sessions (Conversation Index)

A **chat session** is a conversation thread. It is metadata only: title, owner, and timestamps. The messages are not in this table.

### 5.1 Create a session

**Endpoint:** `POST /api/sessions` (requires auth)

```json
{ "title": "New conversation" }
```

Flow:

1. The title is required.
2. Prisma inserts a `Session` row with a new UUID and `userId = req.user.id`.
3. Response: the full session row.

No call is made to FastAPI at this point. No checkpoint is created yet.

### 5.2 List sessions

**Endpoint:** `GET /api/sessions`

Returns all sessions owned by the authenticated user, ordered by `updatedAt DESC`.

### 5.3 Get one session

**Endpoint:** `GET /api/sessions/:id`

Returns `404` if missing, `403` if the session belongs to another user.

### 5.4 Rename a session

**Endpoint:** `PATCH /api/sessions/:id`

```json
{ "title": "Apple orchard follow-up" }
```

Updates the title and Prisma automatically updates `updatedAt`.

### 5.5 Delete a session

**Endpoint:** `DELETE /api/sessions/:id`

Deletes the `Session` row from `agri_auth` only.

> **Critical:** this does **not** delete the LangGraph checkpoints in `agri_memory`, and it does **not** delete uploaded images from `storage/uploads/`. There is no cross-database foreign key. See [Known Limitations](#13-known-limitations--gotchas) and the cleanup queries in [Part H](#11-part-h--sql-cookbook).

### 5.6 How the frontend uses sessions

- On first load, the assistant UI initializes a thread and calls `POST /api/sessions` with the title `"New conversation"`.
- If the user sends a message before a session exists, `gateway.ts` creates one automatically.
- The active session ID is kept in a module-level variable (`activeOrPendingSessionId`) so the first message is not lost due to React state timing.
- The sidebar lists sessions from `GET /api/sessions`; `lastMessageAt` is mapped from `Session.updatedAt`.
- Renaming and deleting are user-driven. The backend does not auto-generate titles.

### 5.7 Session lifecycle summary

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant G as Gateway
    participant A as agri_auth

    U->>F: Click "New conversation"
    F->>G: POST /api/sessions {title}
    G->>A: INSERT "Session"
    A-->>G: session row (id = UUID)
    G-->>F: session row
    Note over F,G: session.id becomes the LangGraph thread_id

    U->>F: Send first message
    F->>G: POST /api/chat {query, session_id}
    G->>A: SELECT "Session" WHERE id = session_id
    A-->>G: owner check
    G->>G: proxy to FastAPI with internal key
```

---

## 6. Part C — A Chat Turn & Conversation Memory

This is the core of the system.

### 6.1 End-to-end request path

```mermaid
sequenceDiagram
    autonumber
    participant B as Browser
    participant G as Express Gateway
    participant A as agri_auth
    participant R as Redis
    participant F as FastAPI
    participant C as agri_memory
    participant L as LLM / Agents
    participant D as storage/uploads

    B->>G: POST /api/chat (JWT + query + session_id + optional image)
    G->>G: requireAuth
    G->>A: SELECT "Session" WHERE id = session_id
    A-->>G: session or null
    G->>G: verify session.userId === req.user.id
    G->>R: rate-limit check (user + IP)
    alt image present
        G->>F: multipart with file
    else text only
        G->>F: multipart without file
    end

    F->>F: verify X-Internal-API-Key
    F->>D: save image (if any)
    F->>C: load latest checkpoint for thread_id = session_id
    C-->>F: previous state (messages, disease_result, crop_result, ...)
    F->>L: classify + run selected agents
    L-->>F: agent responses
    F->>C: write new checkpoints (human message, node writes, AI message)
    F-->>G: JSON response
    G-->>B: JSON response
```

### 6.2 Gateway validation

`gateway/src/controllers/chat.controller.js`:

1. Requires `query` and `session_id`.
2. Loads the session from `agri_auth."Session"`.
3. Returns `404` if missing, `403` if owned by another user.
4. Forwards the request to FastAPI using `proxyChatRequest`.
5. The proxy sends multipart form data with:
   - `query`
   - `session_id`
   - optional `file`
   - `X-Internal-API-Key`
   - `X-Request-ID` for log correlation.

The proxy deliberately does **not** retry `/chat` automatically because the endpoint is stateful.

### 6.3 FastAPI entry point

`agent_backend/api/routes.py`:

1. Validates the internal API key.
2. Trims `session_id`; rejects empty values or values longer than 255 characters.
3. If an image is present, validates and saves it to durable storage.
4. Builds the initial state:

```python
human_message = HumanMessage(
    content=query,
    additional_kwargs={"image_attachment": image_attachment} if image_attachment else {},
)

initial_state = {
    "user_query": query,
    "has_image": image_attachment is not None,
    "messages": [human_message],
}
```

5. Builds the LangGraph config:

```python
config = {
    "configurable": {
        "thread_id": session_id,
        "image_path": image_attachment["path"] if image_attachment else None,
    }
}
```

6. Calls:

```python
result = await graph.ainvoke(initial_state, config=config)
```

Because a checkpointer is attached, `ainvoke` does not start from a blank state. LangGraph loads the latest checkpoint for `thread_id = session_id` and merges the new input into it. The `messages` field uses the `add_messages` reducer, so the new human message is **appended** to the existing history.

7. Returns:

```json
{
  "status": "success",
  "query": "...",
  "response": "...",
  "session_id": "...",
  "selected_agents": ["disease_agent"],
  "agent_responses": { "disease_agent": "..." }
}
```

8. If the turn fails before completion, the just-saved image is deleted.

### 6.4 The main graph

`agent_backend/graph/main_graph.py` compiles:

```text
START -> classify -> run_agents -> format -> END
```

| Node | Responsibility |
|---|---|
| `classify` | Build recent conversation context and call the Supervisor sub-graph |
| `run_agents` | Execute the selected specialist agent(s) |
| `format` | Return a single answer, or synthesize multiple answers with the LLM |

The Supervisor sub-graph is:

```text
START -> pii_sanitizer -> guardrail -> supervisor -> END
                                  \-> reject ------> END
```

### 6.5 When checkpoints are written

LangGraph writes a checkpoint at each graph super-step. In practice, one chat turn produces multiple checkpoint rows:

- an **input** checkpoint when `ainvoke` receives the new human message;
- one or more **loop** checkpoints as nodes execute;
- a final checkpoint containing the AI reply and updated structured state.

Each checkpoint row is linked to its predecessor through `parent_checkpoint_id`, forming an append-only history of the thread. This is what makes the conversation durable across server restarts and even across multiple FastAPI instances sharing the same `agri_memory` database.

### 6.6 Main graph state

Defined in `agent_backend/graph/state.py` as `MainAgentState`.

| Field | Type | Persisted? | Meaning |
|---|---|---|---|
| `messages` | list, `add_messages` reducer | Yes | Full human/AI message history |
| `user_query` | string | Yes | Current turn's raw query |
| `has_image` | bool | Yes | Whether the current turn included an image |
| `sanitized_query` | string | Yes | PII-scrubbed query used by agents |
| `intent` | string | Yes | `disease`, `crop`, `general`, or `multi_domain` |
| `tasks` | list | Yes | Task breakdown from the supervisor |
| `selected_agents` | list | Yes | Agents chosen for the current turn |
| `is_valid` | bool | Yes | Guardrail decision |
| `guardrail_reason` | string | Yes | Why the query was accepted/rejected |
| `agent_responses` | dict | Yes, reset each turn | Raw output per agent for the current turn |
| `disease_result` | dict | Yes, carried forward | Last `{prediction, disease_id, crop}` |
| `crop_result` | dict | Yes, carried forward | Last `{recommended_crop, derived_features}` |
| `general_result` | dict | Declared, currently unused | No node writes it |
| `final_response` | string | Yes, reset each turn | Final answer returned to the client |

The distinction between **per-turn fields** and **carried-forward fields** is the key to understanding memory:

- `user_query`, `has_image`, `sanitized_query`, `intent`, `tasks`, `selected_agents`, `is_valid`, `guardrail_reason`, `agent_responses`, and `final_response` are overwritten on every turn.
- `messages`, `disease_result`, and `crop_result` survive and are available to later turns.

### 6.7 PII sanitization and the guardrail

Every turn runs the PII sanitizer on the **current query only**:

```text
"You are a privacy filter. Rewrite the following text, replacing names,
emails, phone numbers, and locations with [REDACTED]..."
```

The sanitized text is stored in `sanitized_query` and used by the supervisor and agents. The original text remains in the `HumanMessage` and therefore in the checkpoint. **PII is masked for inference, not removed from storage.**

The guardrail then decides whether the query is agriculture-related:

| Condition | Result |
|---|---|
| An image is attached | Automatically valid |
| There is prior conversation context | Automatically valid |
| Otherwise | LLM checks whether the query is agriculture-related |

The "prior conversation context" rule means that **only the first message of a session is actually domain-checked**. Any follow-up in an existing thread passes the guardrail, even if it is off-topic. This is intentional so vague follow-ups such as "what did you mean by that?" work.

### 6.8 The rolling context window

`classify_and_route` builds the context string passed to the supervisor:

```python
messages = state.get("messages", [])
if len(messages) > 1:
    recent = messages[-7:-1]
    context = "\n".join(f"{role}: {content}" for msg in recent)
```

Because the current query is the last message, `messages[-7:-1]` means:

> **up to the last 6 messages before the current one** = 3 user turns + 3 assistant turns.

If the session has fewer messages, all prior messages are used.

This is a **sliding window**. Everything is stored, but only the most recent 3 turns are included in the supervisor's prompt. Older messages can scroll out of the active context.

> `MAX_CONVERSATION_MESSAGES=20` exists in `config/settings.py` and `.env.example`, but it is **not used anywhere in the current code**. The real limit is the hardcoded `messages[-7:-1]` slice.

### 6.9 What each agent remembers

| Agent | Receives | Memory behavior |
|---|---|---|
| **Supervisor** | Current sanitized query + last 6 prior messages | Can route follow-ups using recent context |
| **Disease Agent** | Current query + optional image path + prior `disease_result.prediction` when no new image | Reuses the last diagnosed disease indefinitely, even if it is older than the 6-message window |
| **Crop Agent** | Current query, from which NPK/weather values are extracted | `crop_result` is saved but **not fed back**; a follow-up without parameters uses defaults |
| **General Agent** | Current sanitized query only | Does not receive prior messages or prior agent results |
| **Response formatter** | Current turn's `agent_responses` | Does not see older turns |

#### Disease follow-up example

```text
Turn 1: User uploads a leaf image.
        Disease Agent predicts Apple Scab.
        State stores:
        disease_result = {
            "prediction": "Apple___Apple_scab",
            "disease_id": "apple_scab",
            "crop": "Apple"
        }

Turn 5: User asks "What is the chemical control for it?"
        No new image is attached.
        run_agents passes the stored prediction into the Disease Agent.
        The agent maps it and retrieves the relevant RAG context.
```

The confidence score and full `detection_result` are **not** part of `disease_result`, so a follow-up cannot quote the original confidence or top alternative predictions. Only `prediction`, `disease_id`, and `crop` survive.

#### Crop follow-up caveat

`run_agents` reads `crop_result` but the branch is effectively a no-op:

```python
prior_crop = state.get("crop_result")
if prior_crop and prior_crop.get("recommended_crop"):
    # Actually crop_agent relies strictly on NPK input parameters for now.
    pass
```

So the last crop is stored, but a new crop question re-extracts parameters from the current text. If the user says "what about that crop?" without repeating N/P/K/weather values, the extractor falls back to defaults (`N=0, P=0, K=0, temp=25, humidity=60, ph=6.5, rainfall=100`), which may produce a different recommendation.

### 6.10 The final answer and the AI message

`format_response`:

- If `final_response` is already set (guardrail rejection), returns `{}`.
- If exactly one agent ran, returns that agent's response directly.
- If multiple agents ran, calls the LLM to synthesize one Markdown answer.

In both normal cases it appends an AI message:

```python
return {
    "final_response": final_text,
    "messages": [("ai", final_text)]
}
```

That AI message is what appears in `GET /api/chat/{session_id}` later.

---

## 7. Part D — What the AI Actually Remembers

This table answers the most common question: **"Why did the assistant forget what I said earlier?"**

| Information | Stored in DB? | In active context? | How far back? |
|---|---|---|---|
| All raw messages | Yes | Only last 6 prior messages | Full history in DB, 3 turns in prompt |
| Current query | Yes | Yes | Current turn |
| PII-sanitized query | Yes | Yes | Current turn |
| Intent / selected agents | Yes | Current turn only | Current turn |
| Raw agent responses | Yes | Current turn only | Current turn |
| Last disease prediction | Yes | Yes, when no new image | Until overwritten |
| Disease confidence / alternatives | No | No | Lost after the turn |
| Last crop recommendation | Yes | Not actively reused | Stored until overwritten |
| General agent's prior answers | Yes, as messages | Only the supervisor sees them (if inside the last 6 messages); the General Agent itself does not | 3 turns for routing |
| Uploaded image bytes | Yes, on disk | Only when the turn includes it | File persists |
| Image metadata | Yes, in message kwargs | Yes, for history rendering | Full history |
| Domain knowledge | Qdrant | Retrieved per disease/crop query | Not conversation-specific |

### Why the window is limited

The LLM has a finite context window. Sending the entire history on every turn would:

- increase latency;
- increase token cost;
- eventually exceed the model limit and fail the request.

The sliding window keeps requests fast and predictable. The trade-off is that old details are not reasoned over unless they are stored in a structured field such as `disease_result`.

### How to extend memory

The current design supports these upgrades without changing the database:

1. **Widen the window** — change `messages[-7:-1]` to a larger slice.
2. **Summarize old turns** — periodically generate a summary and prepend it to the context.
3. **Add pinned facts** — extend the state with a `facts` dictionary and include it in agent prompts.
4. **Use the existing structured fields** — `disease_result` is already a working example of pinned entity memory.

---

## 8. Part E — Image Memory

Images are **not** stored inside PostgreSQL. The checkpoint stores only a path and metadata.

### 8.1 Upload path

1. Frontend sends the image as `multipart/form-data` under the `file` field.
2. Gateway Multer:
   - buffers the file in memory;
   - accepts only `image/*`;
   - enforces a **5 MB** limit.
3. FastAPI `save_uploaded_image`:
   - accepts only JPEG, PNG, WebP, and GIF;
   - enforces **5 MB** again;
   - writes the file to `agent_backend/storage/uploads/<uuid>.<ext>`.
4. The returned metadata is attached to the human message:

```python
additional_kwargs = {
    "image_attachment": {
        "path": "D:/major_backend/agent_backend/storage/uploads/<uuid>.jpg",
        "filename": "leaf.jpg",
        "content_type": "image/jpeg",
        "size": 123456
    }
}
```

5. The checkpoint stores the **metadata**, not the bytes.

### 8.2 Image lifecycle

| Event | What happens |
|---|---|
| Turn succeeds | Image file stays on disk indefinitely |
| Turn fails before completion | `finally` block deletes the just-saved image |
| History is requested | FastAPI reads the file and converts it to a base64 data URL |
| File is missing | The image is silently omitted from history |
| Session is deleted | Image file is **not** deleted |
| Server restarts | Image remains because it is on disk |

### 8.3 Important consequences

- `agri_memory` backups do **not** include images. Back up `storage/uploads/` separately.
- If FastAPI runs on multiple machines, `storage/uploads/` must be a shared volume or object storage; otherwise a history request routed to another instance will not find the image.
- Deleting a session leaves orphaned image files. See the cleanup section.

---

## 9. Part F — Chat History Retrieval

**Endpoint:** `GET /api/chat/:session_id` (gateway) → `GET /chat/{session_id}` (FastAPI)

### 9.1 Gateway checks

1. Requires a valid access token.
2. Loads the session from `agri_auth."Session"`.
3. Returns `404` if missing, `403` if the user does not own it.
4. Proxies to FastAPI with the internal key.

### 9.2 FastAPI retrieval

```python
config = {"configurable": {"thread_id": session_id}}
state_snapshot = await graph.aget_state(config)
messages = state_snapshot.values.get("messages", [])
```

`aget_state` returns the **latest checkpoint** for the thread. It does not replay the whole checkpoint chain.

The endpoint then formats messages:

- `human` → `{ "role": "user", "content": ... }`
- `ai` → `{ "role": "assistant", "content": ... }`

For human messages with an `image_attachment`, it adds:

```json
{
  "image": {
    "data_url": "data:image/jpeg;base64,...",
    "filename": "leaf.jpg",
    "content_type": "image/jpeg",
    "size": 123456
  }
}
```

### 9.3 What history includes and excludes

| Included | Excluded |
|---|---|
| All human messages | Tool-call messages |
| All AI messages | System messages |
| Image data URLs for human messages | `agent_responses` per agent |
| Full history, no pagination | `disease_result` / `crop_result` internals |

Because the agent activity cards are built from the live `POST /api/chat` response, they are **not reconstructed on reload**. After a page refresh, the user sees the human/AI text and images, but not the "Disease Diagnosis Agent" / "Crop Advisory Agent" step cards.

### 9.4 Response shape

```json
{
  "session_id": "3f1c...",
  "messages": [
    { "role": "user", "content": "What is wrong with this leaf?" },
    { "role": "assistant", "content": "The leaf shows signs of..." }
  ]
}
```

If no checkpoint exists, the response is:

```json
{ "session_id": "...", "messages": [] }
```

This is normal for a newly created session that has never received a message.

---

## 10. Part G — Database Reference

### 10.1 `agri_auth` schema (Prisma)

```sql
-- Users
CREATE TABLE "User" (
    "id"           TEXT NOT NULL,
    "email"        TEXT NOT NULL,
    "passwordHash" TEXT NOT NULL,
    "isActive"     BOOLEAN NOT NULL DEFAULT true,
    "createdAt"    TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt"    TIMESTAMP(3) NOT NULL,
    CONSTRAINT "User_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX "User_email_key" ON "User"("email");

-- Chat threads
CREATE TABLE "Session" (
    "id"        TEXT NOT NULL,
    "title"     TEXT NOT NULL,
    "userId"    TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    CONSTRAINT "Session_pkey" PRIMARY KEY ("id")
);

-- Refresh tokens
CREATE TABLE "RefreshToken" (
    "id"        TEXT NOT NULL,
    "userId"    TEXT NOT NULL,
    "tokenHash" TEXT NOT NULL,
    "expiresAt" TIMESTAMP(3) NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "revokedAt" TIMESTAMP(3),
    CONSTRAINT "RefreshToken_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX "RefreshToken_tokenHash_key" ON "RefreshToken"("tokenHash");

ALTER TABLE "Session"
    ADD CONSTRAINT "Session_userId_fkey"
    FOREIGN KEY ("userId") REFERENCES "User"("id")
    ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE "RefreshToken"
    ADD CONSTRAINT "RefreshToken_userId_fkey"
    FOREIGN KEY ("userId") REFERENCES "User"("id")
    ON DELETE CASCADE ON UPDATE CASCADE;
```

### 10.2 `agri_memory` schema (LangGraph `AsyncPostgresSaver`)

These tables are created automatically by `checkpointer.setup()` during FastAPI startup. Do not create them by hand unless you are restoring a backup.

```sql
-- Schema version tracking
CREATE TABLE IF NOT EXISTS checkpoint_migrations (
    v INTEGER PRIMARY KEY
);

-- One row per checkpoint (state snapshot)
CREATE TABLE IF NOT EXISTS checkpoints (
    thread_id            TEXT NOT NULL,
    checkpoint_ns        TEXT NOT NULL DEFAULT '',
    checkpoint_id        TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type                 TEXT,
    checkpoint           JSONB NOT NULL,
    metadata             JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

-- Serialized channel values (messages, agent state, etc.)
CREATE TABLE IF NOT EXISTS checkpoint_blobs (
    thread_id     TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    channel       TEXT NOT NULL,
    version       TEXT NOT NULL,
    type          TEXT NOT NULL,
    blob          BYTEA,
    PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
);

-- Pending/intermediate writes produced by graph tasks
CREATE TABLE IF NOT EXISTS checkpoint_writes (
    thread_id     TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id       TEXT NOT NULL,
    task_path     TEXT NOT NULL DEFAULT '',
    idx           INTEGER NOT NULL,
    channel       TEXT NOT NULL,
    type          TEXT,
    blob          BYTEA NOT NULL,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);

CREATE INDEX IF NOT EXISTS checkpoints_thread_id_idx
    ON checkpoints(thread_id);
CREATE INDEX IF NOT EXISTS checkpoint_blobs_thread_id_idx
    ON checkpoint_blobs(thread_id);
CREATE INDEX IF NOT EXISTS checkpoint_writes_thread_id_idx
    ON checkpoint_writes(thread_id);
```

### 10.3 How to read the checkpoint tables

| Table | What it means in plain English |
|---|---|
| `checkpoints` | "At step N of thread X, the graph looked like this." Each row has a JSONB snapshot and metadata. |
| `checkpoint_blobs` | The heavy channel values (message lists, structured state) serialized by LangGraph's serializer. |
| `checkpoint_writes` | Intermediate writes produced by individual graph tasks before the next checkpoint is committed. |
| `checkpoint_migrations` | Which LangGraph schema migrations have been applied. |

`checkpoints.metadata` typically contains:

```json
{
  "source": "input | loop | update | fork",
  "step": 3,
  "parents": {}
}
```

- `source = input` — checkpoint created from a new `ainvoke` input.
- `source = loop` — checkpoint created after a graph step.
- `source = update` — checkpoint created by a state update.
- `source = fork` — checkpoint created by forking history.

`checkpoint_ns` is normally empty (`''`) for the main graph. It becomes non-empty only for nested graphs that use their own checkpoint namespace.

### 10.4 Relationship between the two databases

```text
agri_auth."User"
      |
      | 1:N
      v
agri_auth."Session"  --- id (UUID) --->  agri_memory.checkpoints.thread_id
      ^                                        |
      |                                        | 1:N
      |                                        v
agri_auth."RefreshToken"              checkpoint_blobs / checkpoint_writes
```

There is **no physical foreign key** between `agri_auth."Session".id` and `agri_memory.checkpoints.thread_id`. The relationship is maintained by application code.

### 10.5 Data growth characteristics

| Data | Growth rate | Cleanup |
|---|---|---|
| `User` | One row per account | Manual |
| `Session` | One row per conversation | Deleting a session |
| `RefreshToken` | One row per login/refresh | Expiry + manual cleanup |
| `checkpoints` | Multiple rows per chat turn | No automatic cleanup |
| `checkpoint_blobs` | Grows with message history and state size | Tied to checkpoints |
| `checkpoint_writes` | Grows with graph execution | Tied to checkpoints |
| Uploaded images | One file per image upload | No automatic cleanup |

A long-lived, heavily used deployment will accumulate checkpoints and images indefinitely. Plan a retention policy before production.

---

## 11. Part H — SQL Cookbook

### 11.1 Connect to the databases

```bash
# Authentication database
psql "postgresql://postgres:postgres@localhost:5432/agri_auth"

# Conversation memory database
psql "postgresql://postgres:postgres@localhost:5432/agri_memory"
```

Adjust the username, password, host, and port to match your `.env` files.

### 11.2 Authentication queries

#### List users

```sql
SELECT id, email, "isActive", "createdAt", "updatedAt"
FROM "User"
ORDER BY "createdAt" DESC;
```

#### List sessions with their owners

```sql
SELECT
    s.id            AS session_id,
    s.title,
    u.email         AS owner_email,
    s."createdAt",
    s."updatedAt"
FROM "Session" s
JOIN "User" u ON u.id = s."userId"
ORDER BY s."updatedAt" DESC;
```

#### List sessions for one user

```sql
SELECT id, title, "createdAt", "updatedAt"
FROM "Session"
WHERE "userId" = '<user-uuid>'
ORDER BY "updatedAt" DESC;
```

#### Inspect refresh tokens

```sql
SELECT
    id,
    "userId",
    "createdAt",
    "expiresAt",
    "revokedAt",
    ("revokedAt" IS NULL AND "expiresAt" > now()) AS is_active
FROM "RefreshToken"
ORDER BY "createdAt" DESC;
```

#### Count sessions per user

```sql
SELECT u.email, count(s.id) AS session_count
FROM "User" u
LEFT JOIN "Session" s ON s."userId" = u.id
GROUP BY u.email
ORDER BY session_count DESC;
```

#### Find a session by title fragment

```sql
SELECT s.id, s.title, u.email
FROM "Session" s
JOIN "User" u ON u.id = s."userId"
WHERE s.title ILIKE '%apple%'
ORDER BY s."updatedAt" DESC;
```

### 11.3 Conversation memory queries

#### List all conversation threads

```sql
SELECT
    thread_id,
    count(*)                       AS checkpoint_count,
    max((metadata->>'step')::int)  AS max_step,
    max(checkpoint_id)             AS latest_checkpoint
FROM checkpoints
WHERE checkpoint_ns = ''
GROUP BY thread_id
ORDER BY latest_checkpoint DESC;
```

#### Show the latest checkpoint for a session

```sql
SELECT
    checkpoint_id,
    parent_checkpoint_id,
    metadata->>'source' AS source,
    metadata->>'step'   AS step,
    metadata
FROM checkpoints
WHERE thread_id = '<session-uuid>'
  AND checkpoint_ns = ''
ORDER BY checkpoint_id DESC
LIMIT 1;
```

#### Show the checkpoint timeline for a session

```sql
SELECT
    checkpoint_id,
    parent_checkpoint_id,
    metadata->>'source' AS source,
    metadata->>'step'   AS step
FROM checkpoints
WHERE thread_id = '<session-uuid>'
  AND checkpoint_ns = ''
ORDER BY checkpoint_id ASC;
```

#### Inspect the channel names present in a checkpoint

```sql
SELECT
    c.checkpoint_id,
    c.metadata->>'source' AS source,
    c.metadata->>'step'   AS step,
    k.channel
FROM checkpoints c
CROSS JOIN LATERAL jsonb_object_keys(c.checkpoint->'channel_values') AS k(channel)
WHERE c.thread_id = '<session-uuid>'
ORDER BY c.checkpoint_id DESC, k.channel;
```

> Depending on the LangGraph version and value type, some channel values are stored inline in `checkpoint->'channel_values'`, while larger values are serialized into `checkpoint_blobs`. If this query returns no rows, the values are blob-backed. Message text is serialized by LangGraph's serializer (typically msgpack) and is not meant to be queried as plain SQL text.

#### Count checkpoint rows per thread

```sql
SELECT thread_id, count(*) AS checkpoints
FROM checkpoints
GROUP BY thread_id
ORDER BY checkpoints DESC;
```

#### Estimate checkpoint storage per thread

```sql
SELECT
    c.thread_id,
    count(*) AS checkpoint_rows,
    pg_size_pretty(sum(pg_column_size(c.checkpoint))::bigint) AS checkpoint_json_size
FROM checkpoints c
GROUP BY c.thread_id
ORDER BY sum(pg_column_size(c.checkpoint)) DESC;
```

#### Estimate blob storage per thread

```sql
SELECT
    thread_id,
    count(*) AS blob_rows,
    pg_size_pretty(sum(coalesce(length(blob), 0))::bigint) AS blob_size
FROM checkpoint_blobs
GROUP BY thread_id
ORDER BY sum(coalesce(length(blob), 0)) DESC;
```

#### Estimate write storage per thread

```sql
SELECT
    thread_id,
    count(*) AS write_rows,
    pg_size_pretty(sum(coalesce(length(blob), 0))::bigint) AS write_size
FROM checkpoint_writes
GROUP BY thread_id
ORDER BY sum(coalesce(length(blob), 0)) DESC;
```

#### Total database size

```sql
SELECT pg_size_pretty(pg_database_size('agri_memory')) AS agri_memory_size;
SELECT pg_size_pretty(pg_database_size('agri_auth'))   AS agri_auth_size;
```

#### Table-level sizes

```sql
SELECT
    relname AS table_name,
    pg_size_pretty(pg_total_relation_size(relid)) AS total_size
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
```

### 11.4 Detecting orphaned checkpoints

A checkpoint is orphaned when its `thread_id` no longer exists in `agri_auth."Session"`.

Because the databases are separate, a plain `JOIN` will not work. Use one of these approaches.

#### Option A — Compare two result sets manually

In `agri_auth`:

```sql
SELECT id FROM "Session";
```

In `agri_memory`:

```sql
SELECT DISTINCT thread_id
FROM checkpoints
WHERE thread_id <> '__health_check__';
```

Any `thread_id` in the second result that is not in the first result is orphaned.

#### Option B — Use `dblink` from `agri_memory`

```sql
CREATE EXTENSION IF NOT EXISTS dblink;

SELECT DISTINCT c.thread_id
FROM checkpoints c
LEFT JOIN dblink(
    'dbname=agri_auth user=postgres password=<password> host=localhost port=5432',
    'SELECT id FROM "Session"'
) AS s(id text) ON s.id = c.thread_id
WHERE s.id IS NULL
  AND c.thread_id <> '__health_check__'
ORDER BY c.thread_id;
```

> `dblink` must be available on the PostgreSQL server. Avoid hardcoding credentials in scripts; use a `.pgpass` file or a secure secret store.

#### Option C — Export and compare with a script

```bash
# Bash / macOS / Linux
psql "$AUTH_URL"   -Atc 'SELECT id FROM "Session";'                   > sessions.txt
psql "$MEMORY_URL" -Atc 'SELECT DISTINCT thread_id FROM checkpoints;' > threads.txt
comm -13 <(sort sessions.txt) <(sort threads.txt)
```

On Windows PowerShell, export both lists to files and compare them with `Compare-Object`:

```powershell
psql $env:AUTH_URL   -Atc 'SELECT id FROM "Session";'                   > sessions.txt
psql $env:MEMORY_URL -Atc 'SELECT DISTINCT thread_id FROM checkpoints;' > threads.txt
Compare-Object (Get-Content sessions.txt) (Get-Content threads.txt)
```

Lines shown with `=>` (present only in `threads.txt`) are orphaned checkpoints.

### 11.5 Cleanup queries

> **Warning:** these statements permanently delete conversation memory. Run them inside a transaction, verify the affected rows first, and take a backup before deleting anything in production.

#### Delete memory for one known session

```sql
BEGIN;

DELETE FROM checkpoints
WHERE thread_id = '<session-uuid>';

DELETE FROM checkpoint_blobs
WHERE thread_id = '<session-uuid>';

DELETE FROM checkpoint_writes
WHERE thread_id = '<session-uuid>';

COMMIT;
```

There are no foreign keys between these tables, so order does not matter. Deleting the whole thread is safe. Avoid deleting individual checkpoint rows unless you understand LangGraph's version chain.

#### Delete an entire chat session and its memory

Step 1 — in `agri_auth`:

```sql
DELETE FROM "Session"
WHERE id = '<session-uuid>';
```

Step 2 — in `agri_memory`:

```sql
BEGIN;

DELETE FROM checkpoints       WHERE thread_id = '<session-uuid>';
DELETE FROM checkpoint_blobs  WHERE thread_id = '<session-uuid>';
DELETE FROM checkpoint_writes WHERE thread_id = '<session-uuid>';

COMMIT;
```

Step 3 — delete the session's image files from `agent_backend/storage/uploads/`. The database does not track which session owns which file, so this is a manual or scripted operation based on the checkpoint's image metadata.

#### Delete a user and all owned sessions

`User` deletion cascades to `Session` and `RefreshToken` in `agri_auth`:

```sql
DELETE FROM "User"
WHERE id = '<user-uuid>';
```

This does **not** delete `agri_memory` checkpoints. Capture the user's session IDs first:

```sql
SELECT id FROM "Session" WHERE "userId" = '<user-uuid>';
```

Then delete those `thread_id`s from `agri_memory` using the previous query.

#### Clean up expired and revoked refresh tokens

```sql
-- Preview
SELECT count(*)
FROM "RefreshToken"
WHERE "expiresAt" < now()
   OR "revokedAt" IS NOT NULL;

-- Delete
DELETE FROM "RefreshToken"
WHERE "expiresAt" < now()
   OR "revokedAt" IS NOT NULL;
```

If you need an audit trail, archive the rows before deleting them.

#### Delete the health-check placeholder

The health endpoint reads `thread_id = '__health_check__'` but does not write a checkpoint. If a row ever appears (for example, from a custom test), it can be removed:

```sql
DELETE FROM checkpoints       WHERE thread_id = '__health_check__';
DELETE FROM checkpoint_blobs  WHERE thread_id = '__health_check__';
DELETE FROM checkpoint_writes WHERE thread_id = '__health_check__';
```

### 11.6 Backup and restore

#### Backup both databases

```bash
pg_dump -U postgres -d agri_auth   -Fc -f agri_auth.dump
pg_dump -U postgres -d agri_memory -Fc -f agri_memory.dump
```

#### Backup uploaded images

```bash
# Linux/macOS
tar -czf uploads.tar.gz -C agent_backend/storage uploads

# Windows PowerShell
Compress-Archive -Path agent_backend\storage\uploads -DestinationPath uploads.zip
```

#### Restore

```bash
pg_restore -U postgres -d agri_auth   --clean --if-exists agri_auth.dump
pg_restore -U postgres -d agri_memory --clean --if-exists agri_memory.dump
```

Restore `agri_auth` and `agri_memory` together. Restoring only one database can leave session IDs without memory or memory without session metadata.

### 11.7 Useful transaction checks

#### Is a session visible to the gateway but missing memory?

```sql
-- agri_auth
SELECT id, title FROM "Session" WHERE id = '<session-uuid>';
```

```sql
-- agri_memory
SELECT count(*) FROM checkpoints WHERE thread_id = '<session-uuid>';
```

If the first returns a row and the second returns `0`, the session exists but has never received a message (or its memory was deleted).

#### Does a memory thread have no session owner?

Use the orphan detection queries above. This is the expected result of deleting a `Session` without cleaning `agri_memory`.

---

## 12. Part I — Configuration & Operations

### 12.1 Environment variables

#### Gateway (`gateway/.env`)

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `3001` in `.env.example`; code fallback `3000` | Gateway port |
| `DATABASE_URL` | — | PostgreSQL connection string for `agri_auth` |
| `JWT_ACCESS_SECRET` | — | Signs access JWTs |
| `JWT_ACCESS_EXPIRES_IN` | `15m` | Access token lifetime |
| `JWT_REFRESH_SECRET` | — | Read into config but **not used** by the current token service |
| `JWT_REFRESH_EXPIRES_IN` | `7d` | Read into config but **not used**; expiry is hardcoded to 7 days |
| `INTERNAL_API_SECRET` | — | Must match the FastAPI value |
| `FASTAPI_BASE_URL` | `http://localhost:8001` | FastAPI base URL |
| `REDIS_URL` | `redis://localhost:6379` | Rate-limit store |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | CORS origin |
| `RATE_LIMIT_LOGIN` | `10` | Login attempts per 15 minutes per IP |
| `RATE_LIMIT_REGISTER` | `5` | Registrations per hour per IP |
| `RATE_LIMIT_CHAT` | `30` | Text chats per minute per user+IP |
| `RATE_LIMIT_IMAGE` | `10` | Image chats per minute per user+IP |

#### FastAPI (`agent_backend/.env`)

| Variable | Default | Purpose |
|---|---|---|
| `SESSION_CHECKPOINTER_BACKEND` | `postgres` | Only `postgres` is accepted |
| `SESSION_CHECKPOINT_DATABASE_URL` | — | PostgreSQL connection string for `agri_memory` |
| `MAX_CONVERSATION_MESSAGES` | `20` | Declared but **unused** by the current code |
| `INTERNAL_API_SECRET` | — | Must match the gateway value |
| `GROQ_API_KEY` | — | LLM access |
| `HF_TOKEN` | — | Embeddings access |
| `TAVILY_API_KEY` | — | Web search |
| `QDRANT_URL` | `http://localhost:6333` | Vector database |
| `DISEASE_API_URL` | `http://127.0.0.1:8000` | Local disease detection service |
| `DISEASE_CONFIDENCE_THRESHOLD` | `0.50` | Detection threshold |
| `LANGSMITH_TRACING` / `LANGSMITH_API_KEY` / `LANGSMITH_PROJECT` | optional | Tracing |

### 12.2 Startup order

```text
1. PostgreSQL
   docker compose up -d postgres
   The init script creates agri_auth and agri_memory on first volume initialization.

2. agri_auth schema
   cd gateway
   npx prisma migrate deploy

3. Redis
   Start Redis with your local setup.
   Note: docker-compose.yml defines only the PostgreSQL service, not Redis.

4. FastAPI
   cd agent_backend
   uv run python main.py
   On startup, create_checkpointer() calls checkpointer.setup(),
   which creates the checkpoint tables and applies LangGraph migrations.

5. Express gateway
   cd gateway
   npm run dev

6. Frontend
   cd frontend
   npm run dev
```

The two services can start in either order, but the gateway's `/api/chat` proxy will fail until FastAPI is healthy.

### 12.3 Database initialization

The Docker init script only runs on a **fresh** PostgreSQL volume:

```bash
docker/postgres/init-databases.sh
```

It creates:

- `agri_auth`
- `agri_memory`

If the volume already exists, the script will not run again. Create the databases manually:

```sql
CREATE DATABASE agri_auth;
CREATE DATABASE agri_memory;
```

Then run `npx prisma migrate deploy` and restart FastAPI so `checkpointer.setup()` can create the checkpoint tables.

### 12.4 Health checks

| Service | Endpoint | What it proves |
|---|---|---|
| Gateway | `GET /health` | Express process is alive |
| Gateway | `GET /health/ready` | Prisma can execute `SELECT 1` against `agri_auth` |
| FastAPI | `GET /health` | App is alive and the checkpointer can read from `agri_memory` |

FastAPI health response:

```json
{
  "status": "ok",
  "message": "Smart Agriculture Backend is healthy",
  "memory": "available"
}
```

If `memory` is `"unavailable"`, inspect `SESSION_CHECKPOINT_DATABASE_URL`, the PostgreSQL container, and the checkpoint tables.

### 12.5 Restart behavior

| Event | Effect |
|---|---|
| FastAPI restarts | Graph is recompiled with a fresh checkpointer; all existing threads remain available |
| Gateway restarts | Auth and session metadata remain in `agri_auth`; access tokens remain valid until expiry |
| PostgreSQL restarts | All memory persists; Redis rate-limit counters may reset depending on Redis persistence |
| Browser refresh | Tokens remain in `localStorage`; history is re-fetched from FastAPI |

### 12.6 Migrations

- **`agri_auth`**: managed by Prisma migrations in `gateway/prisma/migrations/`.
- **`agri_memory`**: managed automatically by `AsyncPostgresSaver.setup()` at FastAPI startup.

Do not manually alter checkpoint table columns. If you upgrade `langgraph-checkpoint-postgres`, restart FastAPI and let `setup()` apply the new migrations.

---

## 13. Part J — Known Limitations & Gotchas

These are behaviors that are easy to miss when reading the code or the higher-level README.

1. **Deleting a chat session does not delete its memory.**
   `DELETE /api/sessions/:id` removes only the `agri_auth."Session"` row. Checkpoints remain in `agri_memory`, and image files remain on disk. This is the most important operational gotcha.

2. **`Session.updatedAt` does not change when a message is sent.**
   The chat controller never updates the session row. Only renaming updates `updatedAt`. As a result, the sidebar's `lastMessageAt` ordering reflects creation/rename time, not the latest message.

3. **`MAX_CONVERSATION_MESSAGES` is dead configuration.**
   The value is defined in settings but never read. The actual context window is the hardcoded `messages[-7:-1]` slice in `graph/main_graph.py`.

4. **Only the first message of a session is domain-checked.**
   If `conversation_context` is non-empty, the guardrail automatically passes. An image also bypasses the guardrail. Follow-up messages in an existing thread are not re-checked.

5. **PII is masked for inference, not removed from storage.**
   The raw query is stored in the human message. `sanitized_query` is a separate field used by agents. If PII must not be retained, add storage-level redaction or encryption.

6. **Disease follow-up memory is partial.**
   Only `prediction`, `disease_id`, and `crop` are stored in `disease_result`. Confidence and top alternative predictions are lost after the turn.

7. **Crop memory is stored but not reused.**
   `crop_result` is written to state, but the follow-up branch is a `pass`. A crop follow-up without restated parameters uses defaults.

8. **The General Agent has no conversation memory.**
   It receives only the current sanitized query. The supervisor may use recent context for routing, but the General Agent's answer does not see prior messages.

9. **History does not include agent activity.**
   `GET /api/chat/:session_id` returns only human/AI text and images. The per-agent tool cards shown in the UI are built from the live `POST /api/chat` response and disappear after a reload.

10. **No pagination on history.**
    The endpoint returns every message in the thread. Long conversations produce large responses, especially when images are base64-encoded.

11. **No cross-database transaction.**
    Creating a session in `agri_auth` and writing the first checkpoint in `agri_memory` are separate operations. A crash between them can leave a session with no memory, or memory with no session if a session is deleted manually.

12. **No per-thread locking.**
    Two simultaneous `/chat` requests for the same `session_id` can interleave. LangGraph serializes checkpoint versions, but the application does not prevent concurrent turns on one thread. The last writer wins.

13. **Logout does not revoke the access token.**
    The JWT remains valid until its 15-minute expiry. Only the refresh token is revoked. There is no access-token blacklist.

14. **Refresh-token configuration is partially unused.**
    `JWT_REFRESH_SECRET` and `JWT_REFRESH_EXPIRES_IN` are loaded into the gateway config but the token service does not use them. Refresh tokens are random opaque strings, not JWTs, and expiry is hardcoded to 7 days.

15. **Refresh-token reuse does not revoke the token family.**
    The gateway logs a warning and rejects the reused token, but it does not revoke all of the user's other refresh tokens.

16. **Checkpoint data grows without bound.**
    There is no TTL or automatic retention. Every turn writes multiple checkpoint rows and blobs. Long-lived deployments need a retention policy.

17. **Images are local files, not database rows.**
    `agri_memory` backups do not include them. Multi-instance deployments need shared storage. Deleting a session leaves the files behind.

18. **The memory database has no user ID.**
    `agri_memory` identifies conversations only by `thread_id`. Authorization relies entirely on the gateway's session ownership check and the internal API key.

19. **A failed turn can leave a partial checkpoint.**
    LangGraph writes the input checkpoint before running the graph. If an agent raises, the human message may already be persisted, so history can show a user message without an assistant reply.

20. **The `__health_check__` thread is a read-only probe.**
    It is used by `GET /health` to verify the checkpointer and should not contain checkpoints. If you see one, it came from a custom test or an accidental write.

---

## 14. Part K — Troubleshooting

| Symptom | Likely cause | What to check |
|---|---|---|
| FastAPI `/health` returns `"memory": "unavailable"` | Wrong DB URL, PostgreSQL down, or tables missing | `SESSION_CHECKPOINT_DATABASE_URL`, container health, `\dt` in `agri_memory` |
| `Unsupported checkpointer backend` | `SESSION_CHECKPOINTER_BACKEND` is not `postgres` | Set it to `postgres` |
| `SESSION_CHECKPOINT_DATABASE_URL is required` | Env var missing | Add the `agri_memory` connection string |
| `403 Forbidden: Invalid internal API key` | Gateway and FastAPI secrets differ | Compare `INTERNAL_API_SECRET` in both `.env` files |
| Chat returns `404 Session not found` | Session ID does not exist in `agri_auth` | `SELECT * FROM "Session" WHERE id = '...';` |
| Chat returns `403` | Session belongs to another user | Check `Session.userId` against the JWT `sub` |
| History is empty but chat works | No checkpoint yet, or wrong session ID | `SELECT count(*) FROM checkpoints WHERE thread_id = '...';` |
| History shows only the user message | The turn failed after the input checkpoint | Check FastAPI logs and the `checkpoint_writes` / `checkpoints` rows |
| Sidebar order does not update after chatting | `Session.updatedAt` is not touched by chat | Expected behavior; rename the session or update it manually |
| Images disappear after a restart | File was deleted or storage path changed | Check `agent_backend/storage/uploads/` and the stored path |
| Images missing on another backend instance | Local storage is not shared | Use a shared volume or object storage |
| `401` on every request after login | Access token expired and refresh failed | Inspect `RefreshToken.revokedAt` / `expiresAt` |
| Login works but refresh fails | Refresh token was already rotated or revoked | Use the latest refresh token only |
| `503` from the gateway | Redis is unavailable | Check `REDIS_URL` and the Redis container |
| `504 AI Service timeout` | LangGraph or an external API took longer than 60s | Check FastAPI logs, Groq/Tavily latency |
| `502 AI Service unavailable` | FastAPI is down or unreachable | Check `FASTAPI_BASE_URL` and the FastAPI process |
| `500 Graph execution failed` | Agent error, model error, or checkpoint issue | FastAPI traceback; verify checkpoint tables |
| Checkpoint tables do not exist | FastAPI never started successfully | Restart FastAPI and check `checkpointer.setup()` logs |
| Session delete leaves data behind | Cross-database cleanup is manual | Run the cleanup queries in Part H |

### Debugging checklist

1. Confirm PostgreSQL is running and both databases exist.
2. Confirm `agri_auth` has the Prisma tables: `\dt` should show `User`, `Session`, `RefreshToken`.
3. Confirm `agri_memory` has the checkpoint tables: `\dt` should show `checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, `checkpoint_migrations`.
4. Confirm the session ID exists in `agri_auth."Session"`.
5. Confirm checkpoints exist for that `thread_id` in `agri_memory`.
6. Confirm the gateway and FastAPI share the same `INTERNAL_API_SECRET`.
7. Confirm FastAPI `/health` reports `"memory": "available"`.
8. Check the gateway request ID in the logs and correlate it with FastAPI logs.

---

## 15. Appendix — File Map & Glossary

### 15.1 Where the logic lives

| Concern | File |
|---|---|
| Prisma schema | `gateway/prisma/schema.prisma` |
| Auth routes | `gateway/src/routes/auth.routes.js` |
| Auth logic | `gateway/src/controllers/auth.controller.js` |
| Password hashing | `gateway/src/utils/password.js` |
| Token creation/verification | `gateway/src/services/token.service.js` |
| Auth middleware | `gateway/src/middleware/auth.middleware.js` |
| Session routes | `gateway/src/routes/session.routes.js` |
| Session CRUD | `gateway/src/controllers/session.controller.js` |
| Chat routes | `gateway/src/routes/chat.routes.js` |
| Chat authorization/proxy | `gateway/src/controllers/chat.controller.js` |
| FastAPI proxy client | `gateway/src/services/fastapi.service.js` |
| Rate limiting | `gateway/src/middleware/rateLimit.middleware.js` |
| FastAPI app & lifespan | `agent_backend/main.py` |
| Chat endpoints | `agent_backend/api/routes.py` |
| Checkpointer factory | `agent_backend/graph/persistence.py` |
| Main graph | `agent_backend/graph/main_graph.py` |
| Graph state definitions | `agent_backend/graph/state.py` |
| Supervisor graph | `agent_backend/agents/supervisor/graph.py` |
| Disease graph | `agent_backend/agents/disease/graph.py` |
| Crop graph | `agent_backend/agents/crop/graph.py` |
| General graph | `agent_backend/agents/general/graph.py` |
| Image storage | `agent_backend/services/image_storage.py` |
| Settings | `agent_backend/config/settings.py` |
| Frontend token storage | `frontend/src/lib/api/client.ts` |
| Frontend auth context | `frontend/src/lib/auth/AuthContext.tsx` |
| Frontend chat adapter | `frontend/src/lib/runtime/gateway.ts` |
| Frontend thread adapter | `frontend/src/lib/runtime/thread-adapter.tsx` |

### 15.2 Glossary

| Term | Meaning |
|---|---|
| **Auth session** | A login state represented by a refresh token row. Not the same as a chat session. |
| **Chat session** | A conversation thread stored in `agri_auth."Session"`. Its ID is the LangGraph `thread_id`. |
| **Thread** | LangGraph's term for an isolated conversation. In this project, one thread = one chat session. |
| **Checkpoint** | A saved snapshot of the graph state at a point in time. |
| **Checkpoint namespace (`checkpoint_ns`)** | Distinguishes nested graphs. Empty for the main graph. |
| **Blob** | A serialized channel value stored in `checkpoint_blobs` (messages, structured state, etc.). |
| **Write** | An intermediate task output stored in `checkpoint_writes`. |
| **Working memory** | The last 6 prior messages included in the current prompt. |
| **Long-term memory** | Everything stored in PostgreSQL, even if not currently in the prompt. |
| **Pinned entity memory** | Structured fields such as `disease_result` that persist beyond the sliding window. |
| **Thread ID** | The UUID used to isolate a conversation. Equal to `Session.id`. |

### 15.3 The one-sentence summary

> CropSage stores identity and session metadata in `agri_auth`, stores the complete conversation and agent state as LangGraph checkpoints in `agri_memory`, links the two by the session UUID, and feeds the AI only the most recent three turns plus a few pinned structured results.

---

*End of document.*
