# AgriMind frontend

Independent React + TypeScript + Vite frontend for the Smart Agriculture multi-agent backend.

## Architecture

```text
Browser (frontend:5173)
  -> Express gateway (VITE_API_BASE_URL, default http://localhost:3001)
  -> FastAPI agent backend (internal only)
  -> LangGraph supervisor + crop / disease / general agents
```

The browser only calls the Express gateway. It never receives or contains provider credentials, the internal API secret, JWT secrets, database credentials, or model API keys.

## Run locally

From `frontend/`:

```bash
npm install
npm run dev
```

Copy `.env.example` to `.env` when the gateway is not using its code default:

```env
VITE_API_BASE_URL=http://localhost:3001
```

The gateway must allow the Vite origin in its `FRONTEND_ORIGIN` setting (normally `http://localhost:5173`). The existing gateway requires Redis for auth and chat rate limiting. The agent backend also needs its configured provider, Qdrant, and LangGraph dependencies.

Start the backend services in separate terminals using the repository guides:

```bash
cd agent_backend
uv run uvicorn main:app --host 0.0.0.0 --port 8001

cd gateway
npm install
npx prisma generate
npx prisma migrate deploy
npm run dev

cd frontend
npm run dev
```

## Scripts

- `npm run dev` — start Vite on port 5173
- `npm run build` — strict TypeScript check and production build
- `npm run lint` — ESLint
- `npm run preview` — preview the production build

## Runtime notes

assistant-ui is mounted with `LocalRuntime` and a custom `ChatModelAdapter`. The adapter translates assistant-ui messages into the gateway’s multipart fields: `query`, `session_id`, and optional `file`. The assistant-ui remote thread list maps its `remoteId` and `externalId` directly to the gateway’s Prisma session UUID.

History is loaded from `GET /api/chat/:session_id`. The backend already persists the user and assistant messages during `POST /api/chat`, so the frontend history adapter is read-only and does not duplicate writes.

The gateway currently returns a completed response after FastAPI’s `graph.ainvoke`; it does not expose token streaming. The frontend shows the real pending state and then the complete response. No simulated streaming is used. A future streaming gateway can replace the isolated model adapter with an async generator without changing the UI shell.

Images are accepted as JPEG, PNG, WebP, or GIF up to 5 MiB. They stay as local object URLs for preview and are sent as binary multipart data to the gateway.

## Features

- Login, registration, `/me`, rotating refresh tokens, logout, and safe session expiry handling
- Gateway-backed session creation, list, switching, rename, delete, and history loading
- assistant-ui Thread, Composer, Message, ActionBar, ThreadList, Suggestion, attachment, and error primitives
- Markdown with GFM tables, code blocks, lists, links, and blockquotes
- Current-response agent activity derived from `selected_agents`
- Light, dark, and system themes
- Responsive desktop sidebar and mobile drawer
- Centralized errors, abort signals, refresh deduplication, and stale-history cancellation

## Verification

Run `npm run lint` and `npm run build`. Full auth/session/chat/image end-to-end testing requires the gateway, Redis, Prisma database, FastAPI service, Qdrant, and configured external provider credentials to be available.
