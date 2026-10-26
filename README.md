<div align="center">

# 🌾 CropSage — Enterprise Smart Agriculture Multi-Agent AI System

**A production-grade, distributed AI assistant that diagnoses plant diseases via computer vision, recommends optimal crops using machine learning, and resolves complex agronomic questions — orchestrated by LangGraph over specialized autonomous agents.**

[![React](https://img.shields.io/badge/Frontend-React%2019%20%7C%20TypeScript%20%7C%20Vite-61DAFB?logo=react&logoColor=black)](frontend/)
[![Express](https://img.shields.io/badge/API%20Gateway-Express.js%20%7C%20Prisma%20ORM-000000?logo=express&logoColor=white)](gateway/)
[![FastAPI](https://img.shields.io/badge/AI%20Core-FastAPI%20%7C%20LangGraph-009688?logo=fastapi&logoColor=white)](agent_backend/)
[![PostgreSQL](https://img.shields.io/badge/Dual%20DB-PostgreSQL%20(agri__auth%20%2B%20agri__memory)-336791?logo=postgresql&logoColor=white)](docker/postgres/)
[![Redis](https://img.shields.io/badge/Caching%20%26%20Rate%20Limit-Redis-DC382D?logo=redis&logoColor=white)](gateway/)
[![Qdrant](https://img.shields.io/badge/Vector%20DB-Qdrant-DC244C?logo=qdrant&logoColor=white)](agent_backend/agents/)
[![ML](https://img.shields.io/badge/ML%20Inference-scikit--learn%20%7C%20MobileNet%2FEfficientNet-F7931E?logo=scikitlearn&logoColor=white)](agent_backend/models/)

</div>

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Resume-Ready Architectural Highlights](#-resume-ready-architectural-highlights)
- [System Architecture](#-system-architecture)
- [Deep Dive: The Three Core Subsystems](#-deep-dive-the-three-core-subsystems)
  - [1. `agent_backend/` — FastAPI, LangGraph & Machine Learning Core](#1-agent_backend--fastapi-langgraph--machine-learning-core)
  - [2. `gateway/` — Node.js / Express API Gateway, Security & Prisma ORM](#2-gateway--nodejs--express-api-gateway-security--prisma-orm)
  - [3. `frontend/` — React 19, TypeScript, Vite & Real-Time Assistant UI](#3-frontend--react-19-typescript-vite--real-time-assistant-ui)
- [Dual-Database Architecture (PostgreSQL)](#-dual-database-architecture-postgresql)
- [API Reference](#-api-reference)
- [Local Development & Setup Guide](#-local-development--setup-guide)
- [Docker & Containerized Infrastructure](#-docker--containerized-infrastructure)
- [Verification & Automated Testing](#-verification--automated-testing)
- [Production Engineering Patterns](#-production-engineering-patterns)

---

## 📖 Overview

**CropSage** is an end-to-end, multi-tier enterprise agricultural intelligence platform. Designed as a fault-tolerant distributed system, it combines modern full-stack web engineering, distributed caching, relational persistence, vector databases, and multi-agent AI orchestration.

Instead of relying on a monolithic prompt or single LLM call, CropSage deploys a **hierarchical multi-agent network (LangGraph)** that:
1. Sanitizes user input against PII and enforces strict agricultural domain guardrails.
2. Accurately routes user requests across specialized domain sub-agents (**Disease Diagnostics**, **Crop Recommendation**, and **Live Agronomic Research**).
3. Executes local scikit-learn models and deep learning vision classifiers alongside high-throughput vector similarity search (Qdrant).
4. Maintains full multi-turn conversational memory persisted across server restarts in PostgreSQL.
5. Shields internal microservices behind a high-concurrency Express.js API Gateway with token rotation and Redis sliding-window rate limiters.

---

## 💼 Resume-Ready Architectural Highlights

*Use these quantified technical impact bullet points for your software engineering or AI platform resume:*

- **Hierarchical Multi-Agent Orchestration**: Architected and deployed an autonomous multi-agent graph with **LangGraph** and **FastAPI**, implementing supervisor routing, dynamic fan-out, and unified response synthesis across 3 domain specialists with sub-second decision latency.
- **Enterprise Dual-Database Migration**: Successfully executed a production migration from legacy embedded SQLite files to a dual **PostgreSQL** topology (`agri_auth` for identity/sessions via **Prisma ORM**; `agri_memory` for checkpoint state machines via **AsyncPostgresSaver**), eliminating lock contention and guaranteeing ACID durability.
- **Computer Vision & Retrieval-Augmented Generation (RAG)**: Integrated an image-classification pipeline (MobileNetV2 / EfficientNetB4) with **Qdrant Vector Database** indexing dense domain embeddings (bge-m3) to deliver grounded disease management advice with intent-driven chunk filtering.
- **Tabular Machine Learning Integration**: Engineered a real-time parameter extraction and inference pipeline wrapping a **scikit-learn Random Forest** model to recommend optimal crops based on 7 environmental variables (N, P, K, pH, rainfall, temperature, humidity).
- **Zero-Trust Security & Distributed Rate Limiting**: Designed a hardened **Node.js Express Gateway** featuring Argon2 password hashing, short-lived JWTs (15m) with rotating refresh tokens (7d), single-use token blacklisting, and **Redis-backed sliding-window rate limiting** with graceful failover.
- **Streaming Real-Time Frontend UI**: Developed a high-performance **React 19 / TypeScript** single-page application utilizing `@assistant-ui/react` runtime adapters, streaming tool-call executions, optimistic state rendering, and zero-flicker theme switching.

---

## 🏗️ System Architecture

The monorepo is cleanly decoupled into three foundational tiers:

```mermaid
flowchart TB
    subgraph CLIENT["🌐 Presentation Tier (frontend/)"]
        direction TB
        Browser["React 19 + TypeScript SPA (:5173)"]
        AUI["@assistant-ui/react Runtime Engine"]
        Browser --- AUI
    end

    subgraph GATEWAY["🛡️ Security & Proxy Tier (gateway/)"]
        direction TB
        ExpApp["Express.js Reverse Proxy (:3001)"]
        AuthModule["JWT Auth (Argon2 / Rotation)"]
        RateLimit["Redis Sliding-Window Rate Limiter (:6379)"]
        PrismaClient["Prisma ORM Client"]
        
        ExpApp --> AuthModule
        ExpApp --> RateLimit
        AuthModule --> PrismaClient
    end

    subgraph DATA_AUTH["🗄️ Identity Store"]
        PostgresAuth[("PostgreSQL: agri_auth (:5432)<br/>Tables: User, Session, RefreshToken")]
    end

    subgraph BACKEND["🧠 AI Agent Tier (agent_backend/)"]
        direction TB
        FastAPIApp["FastAPI REST Core (:8001)"]
        
        subgraph ORCHESTRATION["LangGraph Multi-Agent Engine"]
            direction TB
            Supervisor["Supervisor Router + PII Guardrail"]
            CropAgent["Crop Agent (scikit-learn RF)"]
            DiseaseAgent["Disease Agent (Vision + RAG)"]
            GeneralAgent["General Agent (Tavily Live Web Search)"]
            Synthesizer["Final Response Synthesizer"]
            
            Supervisor -->|intent = crop| CropAgent
            Supervisor -->|intent = disease| DiseaseAgent
            Supervisor -->|intent = general| GeneralAgent
            CropAgent & DiseaseAgent & GeneralAgent --> Synthesizer
        end
        
        FastAPIApp --> Supervisor
    end

    subgraph STORAGE_AI["💾 AI State & Vector Stores"]
        PostgresMemory[("PostgreSQL: agri_memory (:5432)<br/>Checkpoints, Blobs, Writes")]
        QdrantStore[("Qdrant Vector Database (:6333)<br/>crop_knowledge & plant_diseases")]
    end

    subgraph UPSTREAM["☁️ External LLM & Tool APIs"]
        GroqLLM["Groq Cloud (gpt-oss-120b / llama-3.3-70b)"]
        TavilyAPI["Tavily Search API (Live Agronomy Data)"]
        HFHub["HuggingFace (bge-m3 embeddings)"]
    end

    %% Inter-tier communication
    Browser -->|"HTTP/JSON + Cookies (JWT)"| ExpApp
    PrismaClient --> PostgresAuth
    ExpApp -->|"Internal API Key (HMAC Secret) + Multipart/JSON"| FastAPIApp
    FastAPIApp <-->|"Session Checkpointing (AsyncPostgresSaver)"| PostgresMemory
    CropAgent & DiseaseAgent <-->|"k-NN Vector Similarity Search"| QdrantStore
    GeneralAgent --> TavilyAPI
    CropAgent & DiseaseAgent & Synthesizer --> GroqLLM
    DiseaseAgent --> HFHub
```

---

## 🔍 Deep Dive: The Three Core Subsystems

### 1. `agent_backend/` — FastAPI, LangGraph & Machine Learning Core

The agent backend orchestrates all computational intelligence, model inferences, and conversational graphs.

```
agent_backend/
├── agents/                     # Specialized autonomous domain agents
│   ├── crop/                   # Crop recommendation sub-graph & ML inference
│   │   ├── graph.py            # LangGraph crop sub-graph definition
│   │   ├── model.py            # scikit-learn Random Forest model wrapper
│   │   ├── retriever.py        # Qdrant crop agronomy context retriever
│   │   └── prompt.py           # Agronomic reasoning prompts
│   ├── disease/                # Plant disease vision classification + RAG
│   │   ├── graph.py            # LangGraph disease diagnostic workflow
│   │   ├── retriever.py        # Vector retriever for plant pathology
│   │   └── prompt.py           # Pathology response prompts
│   ├── general/                # General agricultural research agent
│   │   ├── graph.py            # Tavily-backed dynamic search graph
│   │   └── prompt.py           # Evidence-first synthesis prompts
│   ├── supervisor/             # Intent classifier & domain safety router
│   │   ├── graph.py            # Router sub-graph
│   │   ├── guardrail.py        # PII regex scrubber & topic classification
│   │   └── prompt.py           # Routing and agent selection rules
│   └── response/               # Multi-agent response aggregation & synthesis
├── api/                        # FastAPI route handlers
│   └── routes.py               # /chat, /chat/{session_id}, /health
├── config/                     # Pydantic v2 settings & environment validation
│   └── settings.py             # Strongly typed system settings
├── graph/                      # Core graph compilation & state persistence
│   ├── main_graph.py           # Main orchestration state machine
│   ├── state.py                # TypedDict definitions for graph states
│   └── persistence.py          # AsyncPostgresSaver connection pooling
├── models/                     # Serialized scikit-learn model artifacts (.pkl)
├── services/                   # Vision inference & temporary file handlers
├── sitecustomize.py            # Windows SelectorEventLoop patch for psycopg
├── main.py                     # FastAPI application factory & lifespan context
└── pyproject.toml              # Modern Python packaging configuration (uv)
```

#### Key Capabilities & Engineering Patterns:
- **Supervisor Routing State Machine**: Classifies incoming queries into `crop`, `disease`, `general`, or `multi_domain`. If an input contains sensitive data (emails, credit cards, phones, personal identifiers), it is automatically scrubbed into `[REDACTED]`. Non-farming inquiries are intercepted by a lightweight guardrail to prevent token waste.
- **Random Forest Crop Predictor**: Ingests natural-language soil and environmental reports, extracts numeric vectors (`[N, P, K, temperature, humidity, pH, rainfall]`), applies `MinMaxScaler` normalization, and predicts the highest-probability crop with explanation grounding from `crop_knowledge` in Qdrant.
- **Plant Pathology Vision + RAG**: Supports image uploads via multipart streaming. Routes leaf images to an image-classification service, pulls verified pathological profiles from the `plant_diseases` Qdrant vector collection, and delivers multi-section disease summaries (symptoms, pathology, organic remedies, and chemical controls).
- **PostgreSQL Session Checkpointer**: Replaces SQLite with `langgraph-checkpoint-postgres`. Thread states are serialized into `agri_memory` tables (`checkpoints`, `checkpoint_blobs`, `checkpoint_writes`), enabling persistent conversational context across infinite horizontal backend instances.
- **Windows ProactorEventLoop Bypass**: Features a transparent `sitecustomize.py` and `run.py` patch resolving the well-known Windows `asyncio.ProactorEventLoop` socket limitation with `psycopg` async pool drivers.

---

### 2. `gateway/` — Node.js / Express API Gateway, Security & Prisma ORM

The Gateway acts as the zero-trust ingress controller, insulating the internal AI service while managing identity, tenancy, and resource quotas.

```
gateway/
├── prisma/                     # Database schema and migration management
│   ├── schema.prisma           # Prisma PostgreSQL schema
│   ├── migrations/             # Timestamped SQL migrations
│   │   └── 20261026185411_init_postgresql/migration.sql
│   └── archived_sqlite/        # Safely preserved historical SQLite schema
├── src/
│   ├── config/                 # Gateway environment, database & Redis clients
│   │   ├── database.js         # PrismaClient singleton with graceful shutdown
│   │   ├── env.js              # Validated environment settings
│   │   └── redis.js            # Node-Redis client with backoff reconnect
│   ├── controllers/            # Route business logic
│   │   ├── auth.controller.js  # Registration, login, refresh, logout
│   │   ├── chat.controller.js  # Tenancy validation & proxy dispatching
│   │   └── session.controller.js # CRUD for user conversation threads
│   ├── middleware/             # Express middlewares
│   │   ├── auth.middleware.js  # Bearer token parser & user context injector
│   │   ├── error.middleware.js # Standardized JSON error response handler
│   │   ├── rateLimit.middleware.js # Distributed Redis sliding-window limiters
│   │   └── requestLogger.js    # Correlation ID & latency tracker
│   ├── routes/                 # Express route definitions
│   │   ├── auth.routes.js      # /api/auth/*
│   │   ├── chat.routes.js      # /api/chat/*
│   │   └── session.routes.js   # /api/sessions/*
│   ├── services/               # Microservice proxies
│   │   └── fastapi.service.js  # Axios client with internal secret signing
│   ├── utils/                  # Cryptography, token generation & error types
│   ├── app.js                  # Express app definition & readiness endpoints
│   └── server.js               # HTTP listener & process lifecycle handlers
├── package.json                # Gateway dependencies and scripts
└── .env.example                # Canonical environment template
```

#### Key Capabilities & Engineering Patterns:
- **Identity & Refresh Token Rotation**: Implements RFC 6749 compliant token rotation. Access tokens are short-lived (15 minutes). Refresh tokens (7 days) are cryptographically hashed using SHA-256 before database storage. Using an old or revoked refresh token immediately invalidates all active sessions for that user family.
- **Distributed Redis Rate Limiting**: Features sliding-window algorithms preventing API abuse. Protects registration and login endpoints (`5 requests / 15 minutes`) and chat inference endpoints (`20 requests / minute` for text, `5 requests / minute` for image uploads). If Redis is temporarily unreachable, the gateway enters a safe, bounded in-memory fallback.
- **Strict Tenancy Enforcement**: Chat sessions are strictly relational in PostgreSQL (`agri_auth.Session`). Before dispatching any request to the AI tier, the gateway validates that `Session.userId === Request.user.id`, preventing horizontal privilege escalation.
- **Multipart Proxy Streamer**: Buffers incoming leaf photo uploads using in-memory Multer with a 5MB payload ceiling, appending trace IDs and signing requests with `X-Internal-API-Key` before dispatching to FastAPI.

---

### 3. `frontend/` — React 19, TypeScript, Vite & Real-Time Assistant UI

A modern agricultural field desk web application offering conversational AI, multi-modal image inspection, and persistent session management.

```
frontend/
├── src/
│   ├── components/             # Reusable UI components
│   │   ├── assistant-ui/       # Thread, Message, Composer, & Tool visualizers
│   │   ├── auth/               # Split-screen responsive Login & Registration
│   │   ├── chat/               # ChatWorkspace, Topbar, & Thread containers
│   │   └── sidebar/            # Conversation search, thread list, & theme strip
│   ├── hooks/                  # Custom React hooks
│   │   └── useTheme.ts         # Reactive Light / Dark / System theme hook
│   ├── lib/
│   │   ├── api/                # Type-safe Fetch clients
│   │   │   ├── client.ts       # Axios-like wrapper with automatic token refresh
│   │   │   ├── auth.ts         # User auth API methods
│   │   │   ├── chat.ts         # Chat proxy API methods
│   │   │   └── sessions.ts     # Session list, create, rename, delete API methods
│   │   ├── auth/               # React Context & Session hydration
│   │   │   └── AuthContext.tsx # Global authentication provider
│   │   └── runtime/            # Assistant-UI custom integration boundary
│   │       ├── attachments.ts  # Image attachment validation & drag-and-drop
│   │       ├── gateway.ts      # Custom ChatModelAdapter with active-session resolver
│   │       └── thread-adapter.tsx # RemoteThreadListAdapter bridging to Express/Postgres
│   ├── styles/                 # Clean, responsive CSS design tokens
│   ├── types/                  # Shared TypeScript interfaces & API schemas
│   ├── App.tsx                 # Root application routing & runtime shell
│   └── main.tsx                # React DOM mount point
├── package.json                # Frontend dependencies
├── tsconfig.json               # Strict TypeScript configuration
└── vite.config.ts              # Vite bundling configuration
```

#### Key Capabilities & Engineering Patterns:
- **`@assistant-ui/react` Integration**: Connects modern chat primitives directly to a custom `ChatModelAdapter`. Supports live streaming text chunking (14ms intervals for comfortable reading pace), multi-agent tool execution badges (`routing`, `crop_agent`, `disease_agent`), and inline markdown rendering (`react-markdown` + `remark-gfm`).
- **Resilient New-Conversation Hydration**: Implements an active/pending session resolver in `gateway.ts` and `thread-adapter.tsx` that ensures first-turn messages in a newly initialized thread never drop or error due to React state-scheduling race conditions.
- **Seamless Token Refresh Interceptor**: The API client automatically intercepts `401 Unauthorized` responses, halts queued requests, calls `/api/auth/refresh`, updates local storage, and transparently replays the original requests without user disruption.
- **Accessible Multi-Modal Field Workspace**: Responsive layout supporting drag-and-drop leaf photo uploads, conversation filtering, inline session renaming, destructive deletion confirmation, and system-adaptive light/dark theming.

---

## 🗄️ Dual-Database Architecture (PostgreSQL)

To adhere to clean architecture and data segregation principles, the system separates authentication/gateway state from AI execution memory across two distinct databases:

```
PostgreSQL Server (Default: localhost:5432)
├── Database: agri_auth          (Owned by Express API Gateway & Prisma ORM)
│   ├── Table: User             (User identity, argon2 password hash, timestamps)
│   ├── Table: Session          (Chat threads, foreign key -> User.id)
│   └── Table: RefreshToken     (SHA-256 hashed refresh tokens, expiry, revocation)
│
└── Database: agri_memory        (Owned by Python FastAPI & LangGraph)
    ├── Table: checkpoints      (Serialized thread state snapshots per turn)
    ├── Table: checkpoint_blobs (Heavy binary state payloads & messages)
    └── Table: checkpoint_writes(Intermediate node execution outputs)
```

### pgAdmin Read-Only Verification Queries

To inspect the system state in **pgAdmin 4**, connect to your PostgreSQL instance and execute these queries:

#### Inspect Gateway Authentication & Active Sessions (`agri_auth`):
```sql
-- Check registered users and account creation dates
SELECT id, email, "createdAt", "updatedAt" FROM "User" ORDER BY "createdAt" DESC;

-- Inspect active chat threads and their owners
SELECT s.id AS session_id, s.title, u.email AS owner_email, s."createdAt", s."updatedAt"
FROM "Session" s
JOIN "User" u ON s."userId" = u.id
ORDER BY s."updatedAt" DESC;

-- Verify refresh token rotation security status
SELECT id, "userId", "expiresAt", revoked, "createdAt" 
FROM "RefreshToken" 
ORDER BY "createdAt" DESC LIMIT 10;
```

#### Inspect Multi-Agent AI Checkpoints (`agri_memory`):
```sql
-- View all recorded conversation checkpoints and step IDs
SELECT thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id 
FROM checkpoints 
ORDER BY checkpoint_id DESC LIMIT 15;

-- Check latest state write operations per agent node
SELECT thread_id, task_id, idx, channel 
FROM checkpoint_writes 
ORDER BY idx DESC LIMIT 20;
```

---

## 🔌 API Reference

### Express API Gateway (Port `3001`)

| Method | Endpoint | Auth | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/auth/register` | Public | Register new user account (`email`, `password`) |
| `POST` | `/api/auth/login` | Public | Authenticate user; returns JWT `accessToken` & `refreshToken` |
| `POST` | `/api/auth/refresh` | Public | Rotate refresh token; issues fresh `accessToken` |
| `POST` | `/api/auth/logout` | Bearer | Revokes current refresh token |
| `GET` | `/api/sessions` | Bearer | List all conversation sessions belonging to authenticated user |
| `POST` | `/api/sessions` | Bearer | Create a new session thread (`title`) |
| `GET` | `/api/sessions/:id` | Bearer | Fetch metadata for a specific session |
| `PATCH` | `/api/sessions/:id` | Bearer | Rename a session thread (`title`) |
| `DELETE`| `/api/sessions/:id` | Bearer | Delete a session thread |
| `POST` | `/api/chat` | Bearer | Send chat prompt (`query`, `session_id`, optional `file` image) |
| `GET` | `/api/chat/:session_id` | Bearer | Fetch serialized message history for thread |
| `GET` | `/health/ready` | Public | Kubernetes/Docker readiness probe (validates PostgreSQL `SELECT 1`) |

### FastAPI AI Backend (Port `8001`)

| Method | Endpoint | Auth | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Public | Backend health probe (validates LangGraph checkpointer connectivity) |
| `POST` | `/chat` | Internal Key | Executes LangGraph multi-agent orchestration for incoming query |
| `GET` | `/chat/{session_id}` | Internal Key | Pulls raw state snapshot from PostgreSQL checkpointer |

---

## 🚀 Local Development & Setup Guide

### Prerequisites
- **Node.js**: `v20.x` or higher
- **Python**: `3.12` or `3.13`
- **PostgreSQL**: `v15` or higher (running locally on port `5432`)
- **Redis**: `v7.x` (running on `localhost:6379`)
- **Qdrant**: Running on port `6333`

---

### 1. Database Initialization
Ensure PostgreSQL is running, then create the two independent databases:
```sql
CREATE DATABASE agri_auth;
CREATE DATABASE agri_memory;
```

---

### 2. Gateway Setup (`gateway/`)
```bash
cd gateway

# 1. Install dependencies
npm install

# 2. Configure environment
cp .env.example .env
# Edit .env to supply your DATABASE_URL, REDIS_URL, and JWT secrets

# 3. Apply Prisma migrations
npx prisma migrate deploy

# 4. Launch development gateway (Port 3001)
npm run dev
```

---

### 3. Agent Backend Setup (`agent_backend/`)
```bash
cd agent_backend

# 1. Set up virtual environment using uv or standard venv
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 2. Install dependencies
pip install -e .

# 3. Configure environment
cp .env.example .env
# Ensure SESSION_CHECKPOINTER_BACKEND=postgres
# Ensure SESSION_CHECKPOINT_DATABASE_URL="postgresql://postgres:root@localhost:5432/agri_memory"
# Provide GROQ_API_KEY, TAVILY_API_KEY, and HF_TOKEN

# 4. Launch Qdrant vector database (via local docker compose)
docker compose -f agents/docker-compose.yml up -d

# 5. Launch FastAPI backend (Port 8001)
python run.py
```

---

### 4. Frontend Setup (`frontend/`)
```bash
cd frontend

# 1. Install dependencies
npm install

# 2. Verify compilation
npm run build

# 3. Launch Vite development server (Port 5173)
npm run dev
```

Open your browser at `http://localhost:5173` to interact with CropSage.

---

## 🐳 Docker & Containerized Infrastructure

A root-level [`docker-compose.yml`](docker-compose.yml) and automated initialization script [`docker/postgres/init-databases.sh`](docker/postgres/init-databases.sh) are provided for containerized deployments:

```bash
# Start PostgreSQL container with automatic dual database initialization
docker compose up -d postgres

# Start Qdrant vector database
docker compose -f agent_backend/agents/docker-compose.yml up -d
```

---

## 🧪 Verification & Automated Testing

The codebase includes end-to-end integration and unit tests covering persistence, security boundaries, and multi-agent execution:

```bash
# Run Gateway PostgreSQL integration test suite
cd gateway
node tests/test_postgres_gateway.js

# Run Agent Backend PostgreSQL persistence test suite
cd agent_backend
pytest tests/test_postgres_persistence.py -v

# Run Frontend TypeScript & lint verification
cd frontend
npm run build
npm run lint
```

---

## 🛡️ Production Engineering Patterns

- **Decoupled Security Boundary**: Public clients never make unauthenticated or direct requests to the AI backend. All interactions flow through the Gateway with trace ID correlation (`X-Request-ID`).
- **Resilient Memory State Machines**: Multi-agent sessions are immutable checkpoint state machines. If a worker process restarts mid-turn, the next execution reads the last validated checkpoint from PostgreSQL without data loss.
- **Deterministic Guardrails**: Natural-language inputs are guarded by PII sanitizers and topic validators before triggering model inference, preventing injection attacks and token exhaustion.
- **Fail-Safe Service Degradation**: If auxiliary services (Redis or Qdrant) experience transient connectivity issues, graceful fallback handlers log structured errors and return helpful diagnostics instead of crashing.

---

<div align="center">
  <sub>Engineered with precision for resilient, real-world smart agriculture intelligence.</sub>
</div>
