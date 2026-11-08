# CropSage Frontend Redesign: `design.md`

Status: implementation blueprint, ready to build from. Scope: the React frontend in `frontend/` of the Smart Agriculture Multi-Agent AI project (repo `mithun24112005/agri_agent_backend`, commit `69f92b2`).
Owner of the decisions in this file: Mithun. Written 2026-11-07 by Tab.

Ground rules this document is written under:

- Frontend only. No backend route, response schema, auth contract, storage key or gateway behaviour changes.
- No new runtime dependency is required. Two optional font packages are listed in section 21 with their verified versions and licences.
- Every backend claim below was read in source (file and line references are given). Where the code does not return something, the UI does not show it.
- Every contrast ratio below was computed from the exact hex values in section 15, with the WCAG 2.x relative-luminance formula.
- No browser screenshot of the current app was captured for this document. The "current app" description is from source, and the inspiration products are described from the pages and write-ups listed in section 3 (the page of each is marked as opened or blocked).

---

## Contents

1. Project Overview
2. Existing Frontend Technology Audit
3. Design Research and Inspiration References
4. Selected Visual Direction
5. UX Principles
6. Application Information Architecture
7. Authentication Page Design
8. Dashboard Design
9. Chat Interface Design
10. Crop Recommendation Design
11. Disease Detection Design
12. Agricultural Assistant Design
13. Session Memory Design
14. Profile and Settings Design
15. Complete Design Token System
16. Component Library and Architecture
17. Interaction and Animation Guidelines
18. Responsive Design Specifications
19. Accessibility Guidelines
20. Existing Backend Integration Requirements
21. Implementation Guidelines
22. Acceptance Criteria
- Design Review (self-review against the eleven criteria)
- Appendix A: Research log

---

## 1. Project Overview

### 1.1 What the product is

A multi-agent agriculture assistant. A user signs in, starts a conversation, and asks farm questions in text, or attaches a plant photo. A Supervisor agent classifies each message and routes it to one or more specialists:

| Agent (as the backend names it) | What it does (from source) | Input it takes | What the frontend receives |
|---|---|---|---|
| Supervisor (`agent_backend/agents/supervisor/graph.py`, called from `graph/main_graph.py` `classify_and_route`) | Validates the question is agricultural, sanitises it, picks agents | The user's message plus the last 6 messages of the conversation | Not returned as its own field. It runs on every message. |
| Crop Recommendation (`agents/crop/graph.py`, `services/crop_model.py`) | Extracts seven parameters from the text with an LLM, runs a Random Forest, then writes a Markdown explanation | Seven values: N, P, K, pH, temperature, humidity, rainfall | `agent_responses.crop_agent` (Markdown text only) |
| Plant Disease Detection (`agents/disease/graph.py`, `services/disease_detection/`) | Sends the uploaded image to a separate local detector service, then answers with retrieved disease context | An image plus an optional question | `agent_responses.disease_agent` (Markdown text only) |
| General Agriculture (`agents/general/graph.py`) | Answers general agronomy questions, including fertilizer, soil nutrients and irrigation. Fertilizer is not a separate agent. | A question | `agent_responses.general_agent` (text) |

When more than one agent answers, `format_response` in `main_graph.py` merges their text with an LLM into one final answer. When one answers, its text is returned as is.

### 1.2 Users and purpose

- Primary: farmers and growers who want a plain, trustworthy answer and, sometimes, a photo diagnosis.
- Secondary: the project owner, who will demonstrate this as a final-year Computer Science project. The interface has to look finished and explain what each part does without a presenter.
- The app must never look like an agricultural brochure. It is a working tool.

### 1.3 Major features in the current code

Sign in, register, sign out, token refresh (`src/lib/api/client.ts`); conversation list, create, rename, delete, search by title (`src/components/sidebar/ThreadList.tsx`); chat with Markdown responses (`src/components/assistant-ui/Thread.tsx`); image attachment up to 5 MB (`src/lib/runtime/attachments.ts`); three themes (`src/hooks/useTheme.ts`); responsive sidebar drawer below 850 px (`src/styles/index.css`).

### 1.4 Stakeholder requirements added in this brief

Premium neutral-first look; one restrained accent (not green); distinct light and dark designs; agent awareness without clutter; a dedicated crop-recommendation experience with seven named inputs; a dedicated disease-photo experience; dashboard, auth, settings; full responsive behaviour with a usable phone layout.

---

## 2. Existing Frontend Technology Audit

All versions below are the exact versions in `frontend/package.json` and `frontend/package-lock.json` at commit `69f92b2` (the lockfile agrees with the spec for every direct dependency, checked line by line).

### 2.1 Stack and dependencies

| Package | Version | Kind | Used for today | Keep? |
|---|---|---|---|---|
| react | 19.2.8 | runtime | UI | Keep |
| react-dom | 19.2.8 | runtime | DOM renderer, `main.tsx` | Keep |
| @assistant-ui/react | 0.15.17 | runtime | Thread, Composer, Message, ThreadList primitives, local runtime, remote thread-list runtime, attachments, chain-of-thought | Keep (see 2.6 for limits) |
| assistant-stream | 0.3.40 | runtime | `createAssistantStream` for generated titles (`thread-adapter.tsx`) | Keep (transitive contract with assistant-ui) |
| react-markdown | 10.1.0 | runtime | Renders assistant text (`Thread.tsx` `MarkdownText`) | Keep. No `rehype-raw`, so raw HTML in answers is not rendered. |
| remark-gfm | 4.0.1 | runtime | Tables, task lists, strikethrough | Keep |
| lucide-react | 1.35.0 (registry latest is 1.70.0) | runtime | All icons | Keep. Pinned version is fine; upgrade is optional. |
| tailwindcss | 4.3.3 | dev | Imported as `@import "tailwindcss";` in `index.css` | Keep, but use it properly (2.4) |
| @tailwindcss/vite | 4.3.3 | dev | Vite plugin | Keep |
| vite | 8.2.2 | dev | Dev server and build | Keep. The earlier audit's npm report lists a high advisory for 8.2.0 to 8.2.2 (Windows `launch-editor` path, dev tooling). Track it; do not change the pin in this redesign. |
| typescript | 5.9.3 | dev | Type checking, `tsc --noEmit` in `npm run build` | Keep |
| @vitejs/plugin-react | 6.1.1 | dev | React Fast Refresh | Keep |
| eslint 10.9.1, @eslint/js 10.0.1, typescript-eslint 8.68.0, eslint-plugin-react-hooks 7.1.1, eslint-plugin-react-refresh 0.5.5, globals 17.11.0 | dev | Linting | Keep |
| @types/react 19.2.18, @types/react-dom 19.2.5, @types/node 26.4.0 | dev | Types | Keep |

Not installed and not present anywhere in the project: a component kit (no Radix, no shadcn), a motion library (no Framer Motion), a charting library, a router (no react-router), a code highlighter, a date library, a test runner. Section 16 and 21 design around that. No new library is required.

Build and check status, from the earlier audit's logs (`tasks/058a2894…/audit/fe/`):

- `npm run build` passes (`BUILD_RC=0`). The main JS chunk is 724.46 kB (217.90 kB gzip), and Vite warns it exceeds 500 kB.
- `npm run lint` passes (`LINT_RC=0`).
- `npm ci` fails. Re-checked for this document in a throwaway copy with `npm ci --ignore-scripts`: exit with `EUSAGE`, "package.json and package-lock.json are not in sync", missing `@emnapi/core@1.11.3`, `@emnapi/runtime@1.11.3`, `@emnapi/wasi-threads@1.2.3`. The fix is `npm install` once and committing the regenerated lockfile. This is a prerequisite for implementation (section 21, step 0).
- `npm audit` (earlier run): 14 advisories (10 moderate, 4 high). Four of them are direct dev tooling: `vite` (high, 8.2.0 to 8.2.2), `eslint` and `@eslint/js`, `typescript-eslint` (moderate). Others are transitive in lint tooling (`minimatch`, `brace-expansion`, `source-map-js`). The gateway's `zod` (high) is out of scope for this document.
- No frontend test files exist. `package.json` scripts: `dev`, `build`, `lint`, `preview`.

### 2.2 Folder structure (actual)

```text
frontend/
  index.html                       title "CropSage — Agriculture assistant"
  vite.config.ts                   react + tailwind plugins, alias "@" -> src, port 5173
  src/
    main.tsx                       React root, StrictMode, AuthProvider, imports index.css
    App.tsx                        auth gate; AuthenticatedApp builds the runtime
    styles/index.css               ~29 KB, one file, all component styles, tokens as CSS vars
    hooks/useTheme.ts              light | dark | system, localStorage "agrimind.theme"
    types/api.ts                   User, AuthTokens, Session, ChatMessage, ChatHistory, ChatResponse, GatewayErrorPayload
    lib/api/client.ts              fetch wrapper, bearer header, refresh de-dup, ApiError, token storage
    lib/api/auth.ts                register, login, me, logout
    lib/api/sessions.ts            list, create, get, rename, remove
    lib/api/chat.ts                history, send (multipart)
    lib/auth/AuthContext.tsx       user state, signIn, signOut, refreshUser
    lib/runtime/gateway.ts         ChatModelAdapter (send + simulated reveal), historyMessage()
    lib/runtime/thread-adapter.tsx RemoteThreadListAdapter (list/create/rename/delete/title) and history adapter
    lib/runtime/attachments.ts     image AttachmentAdapter (type and 5 MB checks, data-URL on send)
    components/auth/AuthPage.tsx   sign in / create account, one card
    components/sidebar/Sidebar.tsx brand, new chat, thread list, theme strip, user block, logout
    components/sidebar/ThreadList.tsx search, list, rename, delete (window.confirm)
    components/chat/ChatWorkspace.tsx top bar + thread wrapper
    components/chat/EmptyState.tsx greeting, four suggestion cards
    components/assistant-ui/Thread.tsx  messages, markdown, chain-of-thought, composer, attachments, actions
```

### 2.3 Keep, redesign or replace

| File | Verdict | Why |
|---|---|---|
| `lib/api/client.ts`, `auth.ts`, `sessions.ts`, `chat.ts`, `types/api.ts` | Keep, extend | The contract layer is clean and typed. Add an XHR upload helper (11.4) and an error mapper (16). Fix the login message bug (2.7). |
| `lib/auth/AuthContext.tsx` | Keep | Correct shape. |
| `lib/runtime/gateway.ts` | Replace the reveal loop; keep the adapter | The 24-character reveal (`chunkSize = 24`, `setTimeout 14 ms`) is simulated streaming. The README says "No simulated streaming is used" (`frontend/README.md`, "Runtime notes"), so code and docs disagree. The fake `routing` tool call is shown before any backend event exists. Fallback `agentsToDisplay = ["general_agent"]` mislabels guardrail rejections (2.7). |
| `lib/runtime/thread-adapter.tsx` | Keep, change create timing | Creates a server session on every "New conversation" click, including unused ones (`initialize`). Change to create on first send (13.3). |
| `lib/runtime/attachments.ts` | Keep | Type and size checks match the backend (`image_storage.py`). Keep the same accept list. |
| `hooks/useTheme.ts` | Keep, add a pre-paint script | Logic is right. Theme is applied in an effect, so the first paint can be the wrong theme; add the inline script in 17.6. |
| `components/auth/AuthPage.tsx` | Redesign | Brand shows "CropSage" with a leaf icon; error for wrong password is the session-expired text; validation is minimal; no password toggle. |
| `components/sidebar/Sidebar.tsx` | Redesign | Leaf brand, three-way theme strip with text labels, user block that is only an initial and a logout icon. |
| `components/sidebar/ThreadList.tsx` | Redesign | Works. Needs grouping by date, a dialog instead of `window.confirm`, and keyboard-reachable row actions (today the actions are inside a `<details>` menu). |
| `components/chat/ChatWorkspace.tsx` | Redesign | Title-only header; no sidebar toggle on desktop; no message count or last-updated. |
| `components/chat/EmptyState.tsx` | Redesign | Sprout/Wheat icons; one suggestion includes sample numbers that look like a real example. |
| `components/assistant-ui/Thread.tsx` | Replace the presentation, keep the primitives | Uses assistant-ui primitives correctly. Visual classes, the chain-of-thought panel, the fake routing label, the message image height (220 px with `object-fit: cover`, which crops a leaf photo) and the action bar need replacing. |
| `styles/index.css` | Replace in stages (21.3) | Tokens are CSS variables already, but the palette is monochrome, the composer shadow is green-tinted (`rgba(35,58,40,.06)`), `DM Sans` is named but never loaded, and the breakpoint is 850 px. |

### 2.4 Styling approach, measured

- Tailwind v4 is imported (`@import "tailwindcss";`), but none of the 110 `className` strings in the seven TSX files that carry UI use a Tailwind utility (checked by pattern). Tailwind is in effect only as the preflight reset.
- Styling is one hand-written stylesheet with roughly 200 rule blocks and ad hoc variables: `--paper`, `--surface`, `--surface-soft`, `--surface-raised`, `--line`, `--ink`, `--muted`, `--quiet`, `--accent` (which is black, `#171717`), `--accent-dark`, `--accent-pale`, `--danger`, `--shadow`, `--content-width`.
- Dark mode is `:root.dark { … }` overrides (`index.css`). It is a mechanical inversion of the light values (`--accent: #f5f5f5`).
- Icons: lucide only. Leaf and sprout glyphs appear in the brand mark (`Sidebar`, `AuthPage` use `Leaf`), chat header (`Sprout`), empty state (`Sprout`, `Wheat`), and the assistant avatar uses a ✦ character.
- Animation: CSS keyframes `rise`, `spin`, `breathe`, `chain-in`, `pulse`; a `prefers-reduced-motion` block exists.
- Font: `font-family: "DM Sans", "Segoe UI", sans-serif` on `:root`. DM Sans is never imported, so it falls back to Segoe UI or the system sans. The stated typeface is not the rendered typeface.

### 2.5 Routing

There is no router. `App.tsx` chooses between `AuthPage` and `AuthenticatedApp` with a ternary, and `AuthenticatedApp` always shows the chat workspace. On refresh the app re-reads the conversation list; which conversation opens is decided by the runtime, not by the address bar. There are no shareable URLs. Section 6 adds a zero-dependency hash router (`#/chat/<id>`, `#/crop`, `#/disease`, `#/home`, `#/settings`), which keeps a reload on the same page without a new library.

### 2.6 Chat integration (assistant-ui)

- `useRemoteThreadListRuntime` wraps `useLocalRuntime(gatewayModelAdapter)`. The README calls this "LocalRuntime"; the code matches that description.
- `gatewayModelAdapter.run` sends one multipart POST to `/api/chat` and waits for the whole JSON response. There is no token stream from the backend (`routes.py` returns one dict after `graph.ainvoke`; the gateway forwards it with `res.json(responseData)`).
- After the response arrives, the adapter yields the text in 24-character slices every 14 ms. That is client-side typing over a finished answer. It is not streaming, and it should be removed (17.5).
- Before the response, the adapter yields a fake `tool-call` named `routing` with the text "Routing question to specialized field agents". The backend emits no event at that point. The label is invented.
- After the response, one `tool-call` part is created per agent in `selected_agents`. If `selected_agents` is empty, the adapter sets the list to `["general_agent"]` (`gateway.ts`, `agentsToDisplay`). A guardrail rejection returns `selected_agents: []` (`main_graph.py` `run_agents`, the `is_valid` branch, which does not set agents). The UI therefore labels an out-of-scope refusal as coming from the General Agriculture agent. This is a bug.
- The history adapter (`historyMessage`) sets `createdAt: new Date()`, which is the time of loading, not of the message. The backend history has no timestamps (5.5 in section 20).
- `generateTitle` in `thread-adapter.tsx` titles a new conversation from the first 42 characters of the first message. It works. The title is then saved with `PATCH`, so it persists.

### 2.7 Auth and session handling

- Tokens: `agrimind.access-token` and `agrimind.refresh-token` in `localStorage` (`client.ts`). Keep the keys; renaming them signs everyone out.
- Refresh: a 401 on any request except `/api/auth/refresh` triggers one refresh, de-duplicated by a shared promise (`refreshPromise`), then one retry. On failure it clears tokens and dispatches `agrimind:auth-expired`.
- `AuthContext` hydrates with `GET /api/auth/me` on load. Failure clears tokens.
- Confirmed bug, traced in source: a wrong password shows "Your session has expired. Please sign in again." Path: `POST /api/auth/login` returns 401 with `Invalid email or password` (`auth.controller.js`). `request()` in `client.ts` treats every 401 as an expired session, runs the refresh branch (there is no refresh token on a first login, so the refresh throws and the catch calls `notifyAuthExpired()`), and then throws `getErrorMessage(401, …)`. That function returns the session-expired text for 401 before it reads the payload message. The user never sees "Invalid email or password". Fix in 16 (`errors.ts`): skip the refresh branch for `/api/auth/login` and `/api/auth/register`, and map 401 on those paths to the server message.
- Validation: the backend uses zod (`auth.routes.js`, email and minimum 8 characters). A zod failure returns `error.message = "Invalid request data"` (`error.middleware.js`), so the user sees a generic message. The frontend checks only "email not empty" and "password at least 8". The design adds client-side email-format and password checks with exact messages (section 7).
- Logout: `POST /api/auth/logout` with the refresh token, then local clear, even if the request fails (`auth.ts`, `finally`).

### 2.8 API integration

Covered exhaustively in section 20. Summary: one client, one base URL (`VITE_API_BASE_URL`, default `http://localhost:3001`), JSON for everything except chat (multipart). Errors are normalised into `ApiError(message, status, code, payload)`. Status-specific messages exist for 401, 403, 413, 429, 502, 503, 504. A 500 or any other status shows the server's message verbatim. The gateway forwards some FastAPI details into that message, which can include internal exception text (BL-8 in section 20).

### 2.9 Theme implementation

- `useTheme` stores `agrimind.theme` in localStorage, one of `light | dark | system`, default `system`. It sets `html.dark` and `data-theme`, and listens to `prefers-color-scheme` changes when in system mode.
- Sidebar exposes three labelled buttons (Light, System, Dark) with icons. This works; the segmented control in section 14 keeps the same behaviour with better semantics.
- No pre-paint script in `index.html`. On a dark-mode device, the first frame can be light. This is likely and was not measured.

### 2.10 Accessibility snapshot (source-level)

Positive: 26 `aria-*` attributes across the feature files; the composer has `aria-label`; the auth tabs use `role="tablist"` and `aria-selected`; errors use `role="alert"` and success `role="status"`; a reduced-motion block exists.

Gaps: the mobile drawer has no focus management or Escape handling; the thread-row actions are a `<details>` menu that is awkward with a keyboard; delete uses `window.confirm`; the chain-of-thought accordion and icon-only send and attach buttons rely on labels that vary by state; the scroll-to-bottom button has no visible label on hover; the body is `overflow: hidden`, so the only scroll containers must be declared explicitly (section 18).

### 2.11 Visual faults to fix

- Leaf and sprout glyphs in brand, header and empty state (conflicts with the brief).
- Composer shadow `rgba(35,58,40,.06)` is green-tinted. Replace with neutral tokens.
- The accent is black (`#171717`). There is no accent, so primary actions, links, focus and selected state all look the same.
- The chain-of-thought panel says "Researching" and "Researched in N steps". No research step happened on the backend.
- The message image is fixed at 220 px high with `object-fit: cover`. A cropped leaf photo can hide the lesion that the detector looked at.
- Message action icons are very small (13 px) with no visible labels.

### 2.12 Summary of what the existing UI can and cannot show

| Thing the user wants to see | Available in the existing data? | Source |
|---|---|---|
| Answer text | Yes | `response` (POST), `content` (history) |
| Which agents answered | Yes on the response that produced it; **no** on reload | `selected_agents` is on POST only (BL-5) |
| Each agent's raw text | Yes on POST only | `agent_responses` |
| Processing stage | No | No stage events (BL-1) |
| Streaming tokens | No | Single JSON response (BL-1) |
| Message timestamp | No, from the server | History rows have no time (BL-6) |
| Crop name as a field | No | Crop name is only inside Markdown text (BL-2) |
| Top-N crops, probabilities | No | Model returns one label (BL-2) |
| Disease name, confidence as fields | No | Only in text (BL-4) |
| Sources or citations | No | Not returned |
| Structured fertilizer or nutrient data | No | Text only |
| User first name, avatar | No | `User` = id, email, createdAt, isActive |
| Session last-message time | Only "last renamed" | `updatedAt` changes only on `PATCH` (BL-7) |

---

## 3. Design Research and Inspiration References

### 3.1 How each source was examined

- **Opened**: the page was fetched and its text and structural metadata were read. No screenshot was taken or viewed.
- **Opened, secondary**: a design write-up or a documentation page that describes the product was read.
- **Blocked**: the site returned a bot challenge (HTTP 403, "Just a moment…") to the fetch. Only secondary evidence is used for it.

Honest limits: no page in this list was screenshotted or viewed visually, and no product was used logged-in.

### 3.2 Inspiration table

| # | Product | Reference URL | How examined | Elements worth adopting | Layout and navigation | Typography and hierarchy | Cards and components | Interaction | Why it suits CropSage |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Linear | https://linear.app ; https://linear.app/method ; https://linear.app/now/how-we-redesigned-the-linear-ui | Opened (homepage, Method page, and the redesign post, as text) | Calm sidebar with a short list of workspace views (the homepage text lists Inbox, My issues, Projects, Favorites). Themes generated from three values: base, accent and contrast, in LCH (redesign post). A single brand accent on an achromatic UI (homepage, redesign post). Reduced visual noise in sidebar, tabs and headers (redesign post). | Persistent left rail, content on the right, dense but aligned. | Small, tight UI type; strong weight contrast only on titles. | Not verified on the page; the redesign post describes reduced visual noise in sidebar, tabs and headers. | Keyboard-first; quiet hover (not verified). | A product this polished uses restraint. Its theme system (three inputs) suggests how to make light and dark deliberate instead of inverted. |
| 2 | Vercel and Geist | https://vercel.com ; https://vercel.com/geist/introduction ; https://vercel.com/geist/colors | Opened (homepage, Geist introduction and colours pages as text) | Ten colour scales, with a gray scale used for text, icons, fills, borders and dividers by default; gray-alpha only for overlays (colors page). A free typeface family, Geist Sans and Geist Mono (introduction page). "A high contrast, accessible color system" (introduction page). | Clean marketing and dashboard layouts; not used for the app shell. | Geist Sans for UI, Geist Mono for code. | Not verified on the page (the colour pages describe the token rules, not the surfaces). | Not verified. | The gray-first token rule and a free, OFL typeface fit a neutral-first brief. Geist is used as the typeface. |
| 3 | Stripe Dashboard | https://docs.stripe.com/dashboard/basics ; https://www.925studios.co/blog/stripe-dashboard-design-breakdown ; https://www.designsystems.one/design-systems/stripe-design | Opened (Dashboard docs page; two write-ups as text). The live dashboard was not opened. | Primary navigation section at the top of the sidebar; the Home page as analytics plus notifications; a keyboard shortcut for help (`?`), documented on the basics page. Navigation mapped to jobs, not to internal data model; microcopy carries empty states (925studios write-up). | Left sidebar with grouped sections; a home overview with widgets the user can choose. | Clear label-then-value hierarchy in summaries. | Not verified on the live dashboard. | Empty states that explain (the 925studios write-up names microcopy in empty states). | Stripe's dashboard is the reference for calm data presentation and honest empty states. CropSage uses only the parts that have data. |
| 4 | ChatGPT | https://chatgpt.com ; https://www.925studios.co/blog/chatgpt-interface-design-breakdown ; https://help.openai.com/en/articles/6825453-chatgpt-release-notes | Blocked to full read (the site returns a client-rendered shell with almost no server text; title "ChatGPT"). Secondary write-up opened as text. | Left sidebar of past conversations ordered by recency; a blank input at the bottom; streamed text as the default (write-up). | Sidebar plus centred chat column. | Body text at a comfortable measure in a single column. | Not verified on the live site; the write-up names the sidebar, the blank input and streamed text. | Enter to send (common convention; not verified here). | The chat column pattern is what users already know. CropSage follows the conventions (sidebar, centred column, composer at bottom) without copying the look. |
| 5 | Claude | https://claude.ai | Blocked (HTTP 403, bot challenge). Secondary write-up opened as text: https://deardesigner.substack.com/p/my-styrene-soul-a-short-affair-with (Dec 2024) | Calm, single-column conversation with generous line spacing; a composer that is comfortable to write in (write-up). The write-up names Galaxie Copernicus for headings and Tiempo Text for body text. | Single centred column; minimal chrome. | Reading-first typography; the write-up names two serif faces. CropSage does not use them (not free to use under this project's terms, and not the brief). | Quiet surfaces; minimal borders. | Few motions. | The reading comfort and minimal chrome are the aim. The typeface is not copied. |
| 6 | Perplexity | https://www.perplexity.ai ; https://aiuxplayground.com/teardowns/perplexity/citations ; https://www.perplexity.ai/hub/products/search | Blocked (HTTP 403). Secondary teardown opened as text (aiuxplayground); product hub opened in search snippet only. | Compact attribution row under an answer (the teardown describes a favicon stack and a sources count beside the answer's actions); a side panel that lists each source while the answer stays visible. | Answer on the left; sources reachable from the answer. | Answer first, evidence second. | Source chips. | Sources open without leaving the answer. | CropSage has no sources, so the citation row is not adopted. What is adopted: a compact row under each answer that names who answered, and a detail panel that opens on demand. |
| 7 | Notion | https://www.notion.com | Opened (homepage text only, no app pages) | A quiet search-first workspace; plain language on the homepage. | The app-shell pattern (sidebar with search and a page list) is widely documented; it was not verified on Notion's app screens in this research. | Plain, large headings on the homepage. | Not verified. | Not verified. | Used only for information organisation: the conversation list is grouped by time and kept plain. |
| 8 | Climate FieldView | https://climate.com/en-us.html | Opened (homepage text) | "Make data-driven decisions on your farm"; plain-language product sections ("Our Solutions", features). | Marketing site; app not opened. | Plain-language headings. | Not verified. | Not verified. | Agri-tech in plain words: farm decisions, not agriculture decoration. |
| 9 | Cropin | https://www.cropin.com/ | Opened (homepage text) | "How Cropin turns field and satellite data into decisions your teams act on"; four connected product layers. | Marketing site. | Plain headings. | Product "layers" as cards. | Not verified. | Agri-tech framing as decisions, layers and evidence. |
| 10 | Corvian (formerly Farmers Edge) | https://corvian.com/ | Opened (homepage text) | "auditable, monetizable enterprise outcomes"; field-level agronomy framing. | Marketing site. | Plain headings. | Not verified. | Not verified. | The vocabulary of "auditable" recommendations matches the brief's need to separate measurements from model output. |
| 11 | Agrivi | https://www.agrivi.com/ | Opened (homepage HTML and meta) | Farm-management software vocabulary. The homepage theme colour is green (`#5BAD3F`). | Marketing site. | Not used. | Not used. | Not used. | Used as a counter-example: its green-first identity is the look the brief rules out. |

### 3.3 What was rejected from the research, and why

- Green-first agri palettes (Agrivi's theme colour) and leaf or sprout imagery: rejected by the brief.
- Photographic farm hero images: no content in the app would be backed by them, and they do not help a user with a task.
- Sources and citation rows (Perplexity): the backend returns no sources.
- Glass, gradient and blur effects (common in 2025 AI marketing sites): they reduce contrast and add nothing to the task.
- Copying any product's typeface: Geist is used because it is free to use (OFL) and built for interfaces. The others were not verified as free.

---

## 4. Selected Visual Direction

### 4.1 Name and one-sentence statement

**Quiet Instrument.** A neutral, data-honest workspace: a charcoal-and-white system with one teal accent, where every visible element is either something the user typed or something the backend returned.

### 4.2 What it borrows, and from where

| Element | Borrowed from | How it is used here |
|---|---|---|
| Hairline borders and near-flat surfaces | Linear | Cards and panels use 1 px borders with at most a faint shadow |
| Gray-first token scale and a sparing accent | Vercel Geist | Text, icons, borders and dividers are gray; accent is for actions and focus only |
| Label-then-value summaries and honest empty states | Stripe Dashboard | Crop inputs, dashboard tiles, empty states that say what is missing |
| Sidebar plus centred conversation column | ChatGPT (conventions, not the look) | Familiar chat layout |
| Compact row under each answer | Perplexity (the pattern only) | Agent attribution row |
| Three-input theme generation | Linear (LCH theme post) | Dark and light are designed separately with the same token names (15.2) |

### 4.3 Colour direction

- Neutrals carry the interface. Light: `#F7F7F8` canvas, `#FFFFFF` surfaces, `#15171C` text. Dark: `#101215` canvas, `#16191D` surfaces, `#ECEEF2` text. Both sets are designed separately: light is cool-neutral with a slightly lighter sidebar; dark is layered (canvas, sidebar darker, surface, raised) and uses borders as its main elevation, not shadows.
- Accent: **deep teal `#0F6B66` in light, `#5FC2B9` in dark.** Why teal and not green: the brief rules out bright green and leaf themes; teal reads as water and clean technology, has 6.33:1 contrast on white for text, and stays clearly apart from the success green (`#11703F`, hue around 150 degrees) because the teal sits near 175 degrees and is used only for interaction. Why not terracotta or indigo: terracotta sits too close to the error red; indigo is the default AI look.
- Accent is restricted to: primary buttons, the send button, links, focus rings, the selected nav item, the active theme option, the crop agent identity dot. Nothing else.
- Semantic colours (success, warning, error, info) are used for status only, never as decoration.
- Agent identity uses three muted hues plus neutral (crop = accent teal, disease = plum, general = slate blue, supervisor = neutral). Each has a text-safe contrast (table in section 19).

### 4.4 Shape, type and density

- Radius scale 4, 6, 8, 12, 16 px, pill for chips and avatars. Consistent: inputs and buttons 8 px, cards 12 px, composer and dialogs 16 px.
- Typeface: Geist Sans for all UI and body text; Geist Mono for code, numeric values in tables, and the crop form's units. Body 15/24 px; chat body 16/26 px on phones.
- Density: comfortable on desktop (40 px rows, 36 px buttons). A touch layout of 44 px targets on phones and tablets.
- Whitespace: 24 px between sections, 16 px inside cards, 12 px between related items.

### 4.5 Things this direction refuses

Gradients behind text; glass blur on the main surfaces; emoji in the interface (the chat can carry them as typed); leaf, sprout or wheat decoration (the wheat icon is allowed only as the crop agent's functional icon, section 9.6); stock hero photography; more than one accent colour; bouncing or looping decorative motion; a second typeface.

---

## 5. UX Principles

1. **Say only what happened.** Show a state only when the data or the request supports it. No stage names, no confidence numbers, no crop rankings unless the backend returns them.
2. **Keep the inputs and the output apart.** A user's soil measurements and the model's suggestion never share a card, a colour or a heading.
3. **Missing is visible, never silently filled.** Required inputs are blank until the user types, and blank inputs block submission with a named list.
4. **One primary action per view.** The chat composer, the crop "Get recommendation" button, the disease "Analyse photo" button.
5. **Name who answered.** A small, consistent attribution row under each answer, from `selected_agents`, with no fake attribution when the field is empty.
6. **Honest waiting.** Show the elapsed time and what the request is (sending, analysing), with a plain note after 20 s and 45 s. Never show a progress bar that is not tied to real progress.
7. **Recover in place.** Errors appear where the user is working, with the input kept, and offer one next step.
8. **Sentence case, plain words, no internal names.** No "agent", "thread", "session id", "tool call", "routing", "checkpoint" in the interface unless the user is in a developer view.
9. **Quiet by default.** Motion is short and only for state changes. Reduced motion removes movement and keeps meaning.
10. **Mobile is a first-class layout.** Each view has its own phone design; the desktop layout is never shrunk.

---

## 6. Application Information Architecture

### 6.1 Views and their addresses

Routing is a zero-dependency hash router (`hooks/useHashRoute.ts`, section 16). The app is auth-gated; signed-out users only see the auth view.

| Address | View | Who sees it | Notes |
|---|---|---|---|
| `#/home` (default) | Dashboard | Signed in | Welcome, quick actions, recent conversations, capabilities |
| `#/chat` | Chat, empty state (draft) | Signed in | No server session until the first send |
| `#/chat/<sessionId>` | Chat, existing conversation | Signed in | Loads history via `GET /api/chat/:id`; unknown or foreign id shows "This conversation isn't available" |
| `#/crop` | Crop recommendation | Signed in | Form plus result |
| `#/disease` | Plant photo analysis | Signed in | Upload plus result |
| `#/settings` | Profile and settings | Signed in | Profile, appearance, account, sign out |
| (no hash) on sign-in | Auth: sign in | Signed out | Tabs for Sign in and Create account |

The auth view's two tabs are inside one address (`/` with the form switching), so the URL does not change between sign-in and register.

### 6.2 Sitemap

```text
CropSage
├── Sign in / Create account          (signed out)
└── Signed in
    ├── Home                          #/home
    ├── Conversations (sidebar, all views)
    │   ├── New conversation          #/chat
    │   ├── Search (titles)
    │   └── Conversation              #/chat/<id>
    ├── Crop recommendation           #/crop
    ├── Plant photo analysis          #/disease
    └── Settings                      #/settings
        ├── Profile
        ├── Appearance (Light / Dark / System)
        ├── Account (email, sign out)
        └── About
```

### 6.3 Global navigation

Desktop (≥ 1024 px): a left sidebar with, from top to bottom:

1. Brand: the CropSage mark and wordmark (links to Home).
2. Primary action: "New conversation" button.
3. Search field (filters conversation titles).
4. Section "Work": Home, Crop recommendation, Plant photo analysis.
5. Section "Conversations": grouped list (Today, Yesterday, Previous 7 days, Older).
6. Footer: user block (initial avatar, display name, email) that opens Settings; a collapse button.

Tablet (768 to 1023 px): the sidebar collapses to a 60 px rail with icons, tooltips on focus and hover, and a button to expand it as an overlay.

Phone (< 768 px): no persistent sidebar. A top bar with a menu button opens the same sidebar as a drawer. Bottom navigation is not used; the composer occupies the bottom in chat, and the dashboard uses its own tap targets.

### 6.4 Where each user job lives

| Job | Entry points | Destination |
|---|---|---|
| Ask a general farm question | New conversation; a suggestion chip; the composer on any chat | `#/chat` or `#/chat/<id>` |
| Get a crop recommendation | Home card; sidebar "Crop recommendation" | `#/crop` |
| Diagnose a plant photo | Home card; sidebar "Plant photo analysis"; the paperclip in chat | `#/disease` or an image in chat |
| Find a past conversation | Sidebar list; search | `#/chat/<id>` |
| Change theme or sign out | Settings; the user block | `#/settings` |

---

## 7. Authentication Page Design

### 7.1 Layout

Single screen, no marketing panel. The product name and one line of purpose are above the form. The page is centred; the card is 400 px wide on desktop and full width minus 24 px on phones.

```text
Desktop (≥ 1024 px), canvas #F7F7F8

                           ┌────────────────────────────────────┐
                           │  [mark] CropSage                   │
                           │  Crop and plant health, explained. │
                           │                                    │
                           │  ┌────────────┬─────────────────┐  │
                           │  │ Sign in    │ Create account  │  │
                           │  └────────────┴─────────────────┘  │
                           │                                    │
                           │  Welcome back                      │
                           │  Sign in to continue your work.    │
                           │                                    │
                           │  Email                             │
                           │  ┌──────────────────────────────┐  │
                           │  │ you@example.com              │  │
                           │  └──────────────────────────────┘  │
                           │  Password                          │
                           │  ┌──────────────────────────┬──┐   │
                           │  │ ••••••••••               │👁 │   │
                           │  └──────────────────────────┴──┘   │
                           │                                    │
                           │  [          Sign in           ]    │
                           │                                    │
                           │  Your conversations stay on your   │
                           │  account. Terms and privacy.       │
                           └────────────────────────────────────┘
```

Phone (< 768 px): the same card, full width, the tabs full width, the submit button 48 px tall, the mark and title at the top with 32 px of space.

### 7.2 Copy

| Element | Text |
|---|---|
| Product line | CropSage |
| Purpose line | Crop and plant health, explained. |
| Tab 1 | Sign in |
| Tab 2 | Create account |
| Sign-in heading | Welcome back |
| Sign-in sub | Sign in to continue your work. |
| Register heading | Create your account |
| Register sub | Use an email you can sign in with. Passwords are at least 8 characters. |
| Email label | Email |
| Email placeholder | you@example.com |
| Password label | Password |
| Password placeholder (register) | At least 8 characters |
| Password placeholder (sign in) | Your password |
| Confirm label | Confirm password |
| Submit (sign in) | Sign in |
| Submit (register) | Create account |
| Submit busy | Signing in… / Creating account… |
| Footnote | Your conversations stay on your account. |
| Success after register (shown on Sign in tab) | Account created. Sign in to continue. |

### 7.3 Fields and states

| Field | Type, attributes | Validation (client, before any request) | Messages |
|---|---|---|---|
| Email | `type="email"`, `autocomplete="email"`, `inputmode="email"`, `spellcheck="false"`, `autocapitalize="none"` | Required; must match a basic pattern `^[^\s@]+@[^\s@]+\.[^\s@]+$` after trim | Required: "Enter your email address." Format: "That email doesn't look right. Check for typos." |
| Password (sign in) | `type="password"`, `autocomplete="current-password"` | Required | "Enter your password." |
| Password (register) | `type="password"`, `autocomplete="new-password"`, `minlength="8"` | Required; at least 8 characters | "Use at least 8 characters." |
| Confirm (register) | `type="password"`, `autocomplete="new-password"` | Must match | "The passwords don't match." |

Validation timing: on submit, plus on blur after the first submit attempt. Errors clear on the next keystroke in that field. Each invalid field gets `aria-invalid="true"` and `aria-describedby` pointing to its message. Focus moves to the first invalid field on submit.

Password visibility: an icon button at the end of the password field (`Eye` / `EyeOff` from lucide), 44 px square on phones, 36 px on desktop. It toggles `type` between `password` and `text`, has `aria-label` "Show password" or "Hide password", and `aria-pressed`. It resets to hidden when the tab changes or the view unmounts. It is not on the confirm field (the confirm field must match exactly; a visible toggle on one field is enough) — the confirm field follows the first field's visibility state.

Submit button states: default (accent), hover (accent-hover), pressed (accent-pressed), focus (2 px ring), disabled while busy (opacity 0.6, `aria-disabled`), busy (spinner icon 16 px in place of the arrow, label changes as in 7.2).

### 7.4 Server errors (mapped by status and by code)

Use `errors.ts` (section 16). Auth endpoints never show the session-expired text.

| Situation | Status and code from server | Message shown |
|---|---|---|
| Wrong email or password | 401, `AUTHENTICATION_FAILED`, "Invalid email or password" | "Email or password isn't right." (keep the server's meaning; do not say which one is wrong) |
| Email already registered | 400, `VALIDATION_ERROR` or the ValidationError code, "Email is already registered" | "That email already has an account. Sign in instead." with a button that switches to Sign in and keeps the email |
| Zod validation failed | 400, `VALIDATION_ERROR`, "Invalid request data" | Use the client message from 7.3; if none applies: "Check the highlighted fields." |
| Too many attempts | 429, `RATE_LIMIT_EXCEEDED` | "Too many attempts. Wait a few minutes, then try again." (login limit is 10 per 15 minutes per IP; register is 5 per hour per IP) |
| Rate limiter unavailable | 503, `SERVICE_UNAVAILABLE` | "Sign-in is temporarily unavailable. Try again in a minute." |
| Network failure | status 0, `NETWORK_ERROR` | "We couldn't reach CropSage. Check your connection and try again." |
| Server error | 500 | "Something went wrong on our side. Try again." (never the server text) |
| Session expired while signed in | 401 on a signed-in request | Return to Sign in with the notice "Your session ended. Sign in again to continue." |

Error banner: below the form, above the submit button, 13/20 px, error token text on error-subtle background, 8 px radius, 12 px padding, with a 16 px alert icon. `role="alert"`. Success (register): `role="status"`, success token on success-subtle.

### 7.5 Loading, transitions and motion

- Submit shows busy state; inputs stay enabled (the user can correct text); the tab switch is disabled during the request.
- Tab switch: content cross-fades over 120 ms (opacity only). Reduced motion: no fade.
- Successful sign-in: the card fades out over 160 ms and the app shell fades in over 180 ms. Reduced motion: instant.

### 7.6 Accessibility on this view

Labels are visible (not placeholders only). `autocomplete` is set. The tab list uses `role="tablist"`, each tab `role="tab"` with `aria-selected` and `aria-controls`, and the panel `role="tabpanel"`. Arrow keys move between the two tabs. The footnote is not required reading and is not announced twice.

---

## 8. Dashboard Design

### 8.1 Purpose

The first screen after sign-in. It must make clear, in one glance, that this is an AI agriculture assistant with three specialists, and it must offer the three things a user came to do. It must not invent statistics.

### 8.2 Layout

Desktop (≥ 1024 px): sidebar (268 px) plus a main column with a max width of 1040 px and 32 px side padding.

```text
┌────────────┬───────────────────────────────────────────────────────────┐
│ [CS] CropSage│  Good morning, Mithun                                  │
│            │  Ask about crops, soil and plant health.                 │
│ [+ New     │                                                          │
│    chat]   │  QUICK START                                             │
│ [Search]   │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐      │
│            │  │ 🌾 Recommend  │ │ 🔬 Analyse   │ │ 💬 Ask a      │      │
│ WORK       │  │   a crop      │ │   a plant    │ │   question    │      │
│  Home      │  │ Enter soil &  │ │ photo        │ │ Fertilizer,   │      │
│  Crop rec. │  │ climate values│ │ Upload a leaf│ │ soil, water   │      │
│  Plant ph. │  └──────────────┘ └──────────────┘ └──────────────┘      │
│            │                                                          │
│ CONVERSATIONS  RECENT CONVERSATIONS            CAPABILITIES            │
│  Today     │  ┌──────────────────────────┐   ┌───────────────────────┐ │
│  Crop …    │  │ Crop recommendation · 3 │   │ Crop Recommendation    │ │
│  Yesterday │  │ Updated Nov 5           │   │ seven inputs → a crop  │ │
│            │  ├──────────────────────────┤   ├───────────────────────┤ │
│ ───────    │  │ Powdery mildew          │   │ Plant Disease Detect.  │ │
│ [◐] [user] │  │ Updated Nov 3           │   │ photo → likely issue   │ │
└────────────┴──┴──────────────────────────┴───┤ General Agriculture    │─┘
                                               │ questions, fertilizer  │
                                               └───────────────────────┘
```

Tablet (768 to 1023 px): the sidebar is a 60 px rail. Quick start is three cards in one row; recent conversations and capabilities stack.

Phone (< 768 px): one column. Greeting, then a horizontal list of three quick-start cards (each 80% of the width, snapping), then "Recent" (up to 5 rows), then "What CropSage does" as three stacked rows.

### 8.3 Components

| Component | Content | Data source |
|---|---|---|
| `WelcomeHeader` | Greeting by local hour: "Good morning" (05:00 to 11:59), "Good afternoon" (12:00 to 17:59), "Good evening" (18:00 to 04:59), then the first name, then one line of purpose | `User.email` local-part, or the display name when it exists (section 14); time from device |
| `QuickStartCard` ×3 | Title, one-line description, icon, whole-card link | Static |
| `RecentConversationRow` ×≤5 | Title, "Updated {relative date}" from `updatedAt` | `GET /api/sessions` |
| `CapabilityRow` ×3 | Name, one line of what the user gives it and what they get back, icon | Static copy from section 8.5 |
| `WorkSummary` (optional, see 8.6) | Counts of conversations and of crop or photo analyses the app started | Counted client-side from session titles |
| `EmptyDashboard` | For users with no conversations | Static |

### 8.4 Quick-start cards

| Card | Title | Description | Destination |
|---|---|---|---|
| Crop | Recommend a crop | Enter soil and climate values. The crop model suggests a crop and explains it. | `#/crop` |
| Disease | Analyse a plant photo | Upload a leaf photo. Get the likely condition, with treatment and prevention notes. | `#/disease` |
| General | Ask a question | Fertilizer, soil nutrients, irrigation, organic practice, crop management. | `#/chat` (new draft) |

Card: surface background, 1 px border, 12 px radius, 20 px padding, 40 px icon tile (accent-subtle background, accent icon). Hover: border-strong and shadow-sm, 120 ms. Focus: 2 px accent ring. Whole card is one `<a>` (keyboard: Tab then Enter).

### 8.5 Capabilities overview (copy, derived from source)

| Specialist | One line (what you give, what you get) | Footnote |
|---|---|---|
| Crop Recommendation | Seven soil and climate values in, one suggested crop and an explanation out. | Uses a trained Random Forest model. |
| Plant Disease Detection | A leaf photo in, the likely condition and treatment and prevention notes out. | Photo analysis runs on a separate detection service. |
| General Agriculture | Any agronomy question out. Fertilizer and soil nutrients are answered here. | Answers are advice to check locally, not certified guidance. |

The Supervisor is described once, in the "How CropSage works" line under the capabilities: "Each question is checked for relevance to agriculture and sent to the right specialist. Questions outside agriculture are declined." This is true to the code (`classify_and_route`, guardrail branch) and makes the design's routing visible without showing a fake routing step.

### 8.6 Agricultural insights: decision

The brief asks for insights "ONLY from data that exists". The app has no crop, weather, field or soil records. The only data is the user's sessions. The dashboard therefore shows no agricultural insight tiles, and it shows one honest summary instead:

- "Your work": number of conversations (`sessions.length`), number of crop recommendations started and number of plant photo analyses started. These two counts are derived from the titles the app itself sets (`Crop recommendation · {date}`, `Plant photo · {date}`, section 10.6), so they count only sessions this app created. Label the counts with that wording ("Started from CropSage") so nobody reads them as field data.
- Hide the summary when there are no sessions.

If the backend later adds per-field or per-season data, a real insight card can be added with its own section. It is not designed here.

### 8.7 States

- Loading: three skeleton rows for the recent list (section 16, `Skeleton`), quick-start cards render immediately.
- Error loading sessions: "We couldn't load your conversations." with "Try again" (re-calls the list). Quick-start cards still work.
- Empty (no sessions): Recent section shows "No conversations yet. Start with a question or a photo." and the quick-start cards carry the page.

### 8.8 Interactions

- Click or Enter on a recent row opens `#/chat/<id>`.
- The greeting does not animate. Quick-start and recent rows fade in over 160 ms on first load only (reduced motion: none).

---

## 9. Chat Interface Design

Chat is the core of the product. Everything here is built on the assistant-ui primitives the app already uses (`ThreadPrimitive`, `MessagePrimitive`, `ComposerPrimitive`, `ActionBarPrimitive`, `ThreadListPrimitive`), with new presentation.

### 9.1 Desktop layout (≥ 1024 px)

```text
┌──────────────┬──────────────────────────────────────────────────────────────┐
│ [CS] CropSage│  ☰  Powdery mildew on squash          Updated 2 days ago  ⋯  │ 56 px top bar
│              ├──────────────────────────────────────────────────────────────┤
│ [+ New chat] │                                                              │
│ [Search    ] │          ┌──────────────────────────────────────┐            │
│              │          │ (user) Image: leaf.jpg  [thumb]      │            │
│ Today        │          │ What is this and how do I treat it?  │            │
│  • Powdery…  │          └──────────────────────────────────────┘            │
│  • Squash N… │                                                              │
│ Yesterday    │   ✦  Answered by [Plant Disease Detection]                    │
│  • Rice soil │      Likely powdery mildew. Look for white, flour-like …     │
│              │      ## Treatment                                             │
│ Previous 7d  │      - Remove heavily affected leaves …                       │
│  …           │      [Copy]  [Retry only after an error]                       │
│              │                                                              │
│              │                              ↓ Jump to latest (when scrolled) │
│ ──────────── │  ┌────────────────────────────────────────────────────────┐   │
│ [◐] Mithun   │  │ [thumb] leaf.jpg · 214 KB                          ✕   │   │ image chip (only when attached)
│    ⚙        │  │ Ask about crops, soil, plant health…                   │   │
│              │  │ 📎                                              [ ↑ ] │   │
│              │  └────────────────────────────────────────────────────────┘   │
│              │  AI can be wrong. Check important decisions with a local      │
│              │  agronomist or extension service.                             │
└──────────────┴──────────────────────────────────────────────────────────────┘
```

Column measure: the message column and composer are both 760 px maximum, centred in the main area, with 24 px horizontal padding. At 1280 px and above, the same column stays 760 px; the extra space is canvas, not wider text.

### 9.2 Conversation sidebar

- Top: the CropSage mark and wordmark (links to `#/home`); then the "New chat" button (section 9.3 below); then the search field.
- Search: a single input, placeholder "Search conversations", 36 px tall. It filters titles, case-insensitively, as the user types (no server call). The list shows "No conversations match "{query}"." when empty. Clear button appears when the field has text.
- List: grouped by `updatedAt` into Today, Yesterday, Previous 7 days, Older. Group headers are 12/16 px, 600 weight, `text-tertiary`. Groups with no items are hidden.
- Row: 32 px tall on desktop, 44 px on touch; title in 14/20 px, one line with ellipsis; `aria-current="true"` on the active row. The active row has `surface` background with `shadow-xs`; hover is `sunken`.
- Row actions: a "more" icon button (32 px, visible on hover and on keyboard focus, always visible on touch) opens a menu with **Rename** and **Delete**. The menu is a popover, not a `<details>` element, closes on Escape and on outside click, and moves focus into the first item.
- Rename: the title becomes an input in place; Enter saves, Escape cancels; an empty title saves as "New conversation". Save uses `PATCH /api/sessions/:id`.
- Delete: opens the dialog in 16 (`ConfirmDialog`): title "Delete this conversation?", body "Its messages will be removed. This can't be undone.", buttons "Cancel" (default focus) and "Delete" (danger). Replaces `window.confirm`.
- Footer: the user block (section 14) and the theme control's shortcut (opens Settings).

### 9.3 New conversation

- Button label: "New chat" (desktop and phone), with a 16 px plus icon, primary style on the sidebar (secondary style is also acceptable; choose one, and use primary on the empty-chat state only).
- Behaviour: navigates to `#/chat` as a draft. **No server session is created on click.** The first send creates the session (`POST /api/sessions` with the title derived from the message), then sends the message. This fixes the current behaviour where each click creates a session row that may stay empty.
- If the user is already on a draft, clicking "New chat" does nothing visible except focus moving to the composer.
- Keyboard shortcut: `Ctrl/⌘ + Shift + O` (documented in Settings → About). Not `Ctrl+N`, which browsers reserve.

### 9.4 Chat header

- Height 56 px, background `canvas`, no border until the message list scrolls (then a 1 px `border` line appears, 120 ms).
- Left: sidebar toggle (desktop: collapses the sidebar to the rail; phone: opens the drawer); 36 px icon button with `aria-label` "Show conversations" / "Hide conversations" and `aria-expanded`.
- Title: 15/22 px, 600 weight, one line with ellipsis, centred on phone and left on desktop. Clicking it turns it into an input (same rules as rename).
- Meta line under the title, 12/16 px, `text-tertiary`: "Updated {relative time} · {n} messages". The count is the length of the loaded history (real). The relative time comes from `updatedAt`. Hide the meta line on a draft.
- Right: a "⋯" menu with Rename and Delete, the same actions as the sidebar.

### 9.5 Messages

**User message**

- Right-aligned, max width `min(560px, 82%)`, background `--color-bubble-user`, text `--color-text-primary`, radius 16 px with the bottom-right corner at 6 px, padding 10 px 14 px. Body 15/24 px.
- Attached image above the text: 240 px maximum height on desktop, 200 px on phone, `object-fit: contain`, background `--color-sunken`, radius 12 px, 1 px `border`. Tapping opens the image full size in a dialog (`ImageLightbox`, Esc closes). Never `object-fit: cover`.
- Timestamp: shown on hover (desktop) and always below the bubble on phone, 12/16 px, `text-tertiary`, right-aligned, format "10:42" (local). Only messages sent in this browser session have a time (the history endpoint has no times; BL-6). History messages show no time. This is honest and is the only option without a backend change.
- Actions: none on user messages except "Edit and resend" which is out of scope for this release (it would re-run a turn and add a duplicate user turn server-side, BL-9).

**Assistant message**

- No bubble. Full column width. A 24 px avatar tile (monogram "CS" in `--color-text-primary` on `--color-sunken`, radius 6 px, 11/12 px, 600 weight) sits in a left gutter of 36 px on desktop; on phone the avatar moves into the header line of the message.
- Attribution row above the text: see 9.6.
- Body: Markdown (9.7). Text 15/24 px desktop, 16/26 px phone, `text-primary`.
- Error: see 9.9.
- Actions row (below the body, 12 px gap): **Copy** (icon 14 px + label "Copy" on desktop, icon-only with `aria-label` on phone), copies the Markdown source as plain text; a "Copied" confirmation for 1.5 s in the same button (`aria-live="polite"` on that button's label). Show "Retry" only on error. **Regenerate is not shown** on successful answers (the server appends a second user turn to the conversation, BL-9).
- Feedback (thumbs up and down): **not shipped** in this release because no feedback endpoint exists. The control spec is kept here so it can be enabled later behind `VITE_FEEDBACK_ENABLED` (default `false`). When enabled, it uses the same action row with two 32 px icon buttons (`ThumbsUp`, `ThumbsDown`), `aria-pressed`, and it calls the feedback endpoint. Local-only feedback is not allowed: it would look saved when it is not.

**Timestamps and grouping**

No day separators are rendered for history, because history rows have no dates. A date separator (e.g. "Today") is shown between messages only for messages sent in this session, when the day changes. This keeps the transcript honest.

### 9.6 Agent awareness

#### 9.6.1 Data it is built from

Only the `selected_agents` and `agent_responses` fields of the `POST /api/chat` response. Nothing else. The supervisor is not in the response.

#### 9.6.2 Agent badges

`AgentBadge` is a pill: 24 px tall (phone 28 px), padding 0 10 px 0 8 px, radius full, 1 px `border`, `surface` background, 12/16 px text at 500 weight in `text-secondary`, with an icon 14 px and a 6 px dot in the agent's identity colour.

| Backend key (`selected_agents`) | Label shown | Icon (lucide) | Identity token |
|---|---|---|---|
| `crop_agent` | Crop Recommendation | `Wheat` (functional icon; the only wheat in the UI) | `--color-agent-crop` |
| `disease_agent` | Plant Disease Detection | `Microscope` | `--color-agent-disease` |
| `general_agent` | General Agriculture | `MessageSquareText` | `--color-agent-general` |
| Any other key | Hidden (do not invent a label) | — | — |

Error state of an agent: when its `agent_responses` value starts with `Agent error:`, the badge shows a `TriangleAlert` icon in `--color-warning` and the label "{label} · couldn't finish". The raw text is in the details (9.6.4), not in the badge.

#### 9.6.3 Where it appears

- One row directly above the answer text: "Answered by" in 12/16 px `text-tertiary`, then the badges with 6 px gap. Wraps on phone.
- Single agent: "Answered by [Crop Recommendation]".
- Two or three agents: "Combined from [A] [B]" and the disclosure below.
- No agents (empty `selected_agents`, e.g. a declined question): no row. The declined answer is shown as a plain assistant message with no attribution. The current fallback to `general_agent` is removed.

#### 9.6.4 Details disclosure (multi-agent and error cases)

A disclosure labelled "See each specialist's answer" (chevron icon, 13/20 px, accent text, 32 px tall) opens one section per key in `agent_responses`, in the order of `selected_agents`. Each section has: the badge as heading (level 3), then the agent's text rendered with the same Markdown rules (9.7). The combined answer above is the LLM-merged text (`format_response`), and this disclosure shows the source texts it was built from. Label this clearly: "These are the specialists' own answers before they were combined."

For a single agent, no disclosure; the answer already is that agent's text.

#### 9.6.5 Processing stages

The backend exposes **no stage or progress events** (BL-1). Therefore:

- No stage list, no step names, no "routing" step, no "researching" label. The current `routing` tool call and "Researched in N steps" panel are removed.
- While waiting, the assistant area shows the generic pending state (9.8). It shows the elapsed time and, after 20 s and 45 s, a plain sentence about the wait.
- Agent badges appear only after the response arrives, because the agents are not known before.

If a later backend release adds stage events, section 16's `AgentActivityIndicator` is the place to add them. It is built now as a presentational component that accepts a `stages` prop, and renders nothing when the prop is absent (see 16).

#### 9.6.6 Supervisor

The Supervisor is not shown per message. It is described once on the dashboard (8.5) and in Settings → About. Showing "via Supervisor" on each answer would present a step the response does not report.

#### 9.6.7 After reload

Agent attribution is not in history responses (BL-5). The UI stores the attribution it received, keyed by `sessionId` and the assistant message's index in the transcript, in `localStorage` under `cropsage.attribution.v1`. The cache holds only `selected_agents` and the `agent_responses` keys (not the texts). It is cleared on sign-out. If a message has no cached attribution, no row is shown. This is a cache of data the app already received; it invents nothing. (The index can drift if history is edited server-side; the rule is to show nothing when the cached key count does not match the message, which is cheap to check.)

### 9.7 Markdown rendering

Renderer: `react-markdown` 10.1.0 with `remark-gfm` 4.0.1 (already installed). Do not add `rehype-raw`; raw HTML in answers stays as text. Link URLs are passed through react-markdown's default URL transform, which the code does not override.

| Element | Style |
|---|---|
| Paragraph | 15/24 px (phone 16/26), margin 0 0 12 px, last child 0 |
| Heading h1 inside a message | 18/26 px, 600, margin 20 px 0 8 px (answers should rarely use h1) |
| Heading h2 | 16/24 px, 600, margin 20 px 0 6 px |
| Heading h3 | 15/22 px, 600, margin 16 px 0 4 px, `text-secondary` |
| Unordered and ordered lists | padding-left 22 px, items spaced 4 px, markers `text-tertiary` |
| Blockquote | 2 px left border `--color-border-strong`, padding-left 12 px, `text-secondary` |
| Inline code | Geist Mono 13 px, background `--color-sunken`, radius 4 px, padding 1 px 5 px |
| Code block | Geist Mono 13/20 px, background `--color-sunken`, border 1 px `--color-border`, radius 8 px, padding 12 px 14 px, horizontal scroll (never wrap), top-right copy button (icon 14 px, 28 px square, visible on hover and focus) |
| Table (GFM) | Wrapped in a scroll container (`overflow-x: auto`, `role="region"`, `tabindex="0"`, labelled by the nearest heading or "Table"). Header row 13/20 px 600, `text-secondary`, background `--color-sunken`. Cells padding 8 px 12 px, border-bottom 1 px `--color-border`. Numeric-looking cells use `font-variant-numeric: tabular-nums` and right alignment when the whole column is numeric. Maximum width is the message column; the table never shrinks text below 13 px. |
| Link | Accent text, underline on hover, `target="_blank"`, `rel="noopener noreferrer"`, and a 12 px external icon |
| Horizontal rule | 1 px `--color-border`, margin 16 px 0 |
| Image | Not rendered from Markdown (no image support in answers) |

Syntax highlighting is not used (no highlighter is installed, and none is added). Code blocks are monochrome; that is intentional for an agriculture app whose code blocks are rare.

### 9.8 Loading state (pending response)

Shown in the assistant position immediately after a send. It replaces the attribution row and the body.

- Line 1: a 14 px spinner (accent colour, 1 s rotation; reduced motion: a static `Loader` icon with a slow opacity pulse of 2 s) and the text "Working on your question…" (13/20 px, `text-secondary`). For an image send: "Analysing your photo…". For a crop send: "Running the crop model and writing the explanation…".
- Line 2 (after 1 s): elapsed time, "12 s", tabular numbers, `text-tertiary`.
- After 20 s: line 3, "Complex questions can take up to a minute."
- After 45 s: line 3 changes to "Still working. You can keep this tab open." 
- Skeleton: two grey bars (sunken background, 12 px and 12 px tall, widths 70% and 45%) under line 1; shimmer disabled under reduced motion. Skeleton is shown only while waiting, never as the final answer.
- The send button becomes **Stop** (`ComposerPrimitive.Cancel`) with `aria-label="Stop response"`. The composer textarea stays editable so the next message can be drafted.
- No progress bar. No percentage. No stage names.

### 9.9 Errors and retry

Errors render in the assistant position, in place of the body.

```text
⚠  That didn't go through.                          
   The assistant is temporarily unavailable. Your question is still here.
   [ Try again ]   
```

- Text comes from the error mapper (16 `errors.ts`), never from the server's raw message for a 5xx. Mapping:

| Condition | Message (sentence case) |
|---|---|
| 413 (image too large) | "That photo is over 5 MB. Choose a smaller one." |
| 400 with an image message | Show the server's message if it is one of the two known image sentences ("Please upload a JPEG, PNG, WebP, or GIF image.", "The image must be 5 MB or smaller.") else "That image couldn't be read. Try a JPEG or PNG." |
| 400 other | "That message couldn't be sent. Check it and try again." |
| 429 | "You're sending messages quickly. Wait a moment, then try again." |
| 502 | "The assistant is temporarily unavailable." |
| 503 | "The assistant is busy right now. Try again shortly." |
| 504 | "That took too long. Try again, or ask a shorter question." |
| 401 mid-chat | Return to sign-in with the session notice (7.4) |
| 0 network | "We couldn't reach CropSage. Check your connection." |
| 500 or other | "Something went wrong. Try again." |

- Retry: "Try again" re-sends the same text and the same attached image. It is shown only for failures before a response arrived. It is **not** a Regenerate action; a failed request was not stored as a completed turn. There is **no automatic retry** on any status: the chat request is not idempotent, and a request that timed out after the server finished could store the turn twice (BL-9). Every retry is a user tap.
- The user's text and image stay in the composer's history (the failed bubble remains) so nothing is lost.
- Partial results do not exist (single response), so there is no "partial answer" state.

### 9.10 Composer

```text
┌────────────────────────────────────────────────────────────────┐
│ [thumb] leaf.jpg · 214 KB                                   ✕  │  image chip (optional)
│                                                                │
│ Ask about crops, soil, plant health…                           │  textarea, auto-grows
│                                                                │
│ 📎                                                    [  ↑  ]  │  toolbar: attach (left), send (right)
└────────────────────────────────────────────────────────────────┘
```

- Container: `--color-surface`, 1 px `--color-control-border`, radius 16 px, padding 12 px 12 px 10 px, shadow `--shadow-sm`. Focus-within: border `--color-accent`, 2 px outline offset 0 (visible focus ring on the container). No green shadow.
- Textarea: 16 px on phone (prevents iOS zoom), 15 px on desktop; line-height 24 px; min height 24 px (one line); auto-grows to 7 lines (168 px), then scrolls. `rows="1"`, `aria-label="Message CropSage"`, placeholder "Ask about crops, soil, plant health…".
- Enter sends; Shift+Enter inserts a newline; while composing text with an IME (`isComposing`), Enter does not send.
- Attach button: 36 px (phone 44 px), icon `Paperclip` 18 px, `aria-label="Attach a photo"`, opens the file picker with `accept="image/jpeg,image/png,image/webp,image/gif"`. On phone, the picker shows "Take photo" and library options through the native sheet (`capture` is not forced).
- Send button: 36 px circle (phone 44 px), accent background, `ArrowUp` 18 px, `aria-label="Send message"`. Disabled (opacity 0.45, `aria-disabled="true"`) when there is no text and no image. Pressed: accent-pressed. While a response is running: becomes **Stop** (`Square` icon, `aria-label="Stop response"`), background `--color-surface` with border, to avoid two accent buttons.
- Image chip: 56 px thumbnail (`object-fit: contain`, `--color-sunken` background), file name (14/20, one line, ellipsis) and size (12/16, `text-tertiary`), remove button 44 px touch target with `aria-label="Remove photo {name}"`. Only one image per message. Replacing an image: attach again (the old chip is replaced).
- Attachment errors: shown in a warning-or-error banner above the composer (role `alert`), e.g. "That photo is over 5 MB. Choose a smaller one." or "Please choose a JPEG, PNG, WebP, or GIF image." Existing wording is kept.
- Disclaimer under the composer: 12/16 px, `text-tertiary`, centred on desktop: "CropSage can make mistakes. Check important decisions with a local agronomist or extension service."
- Drag and drop onto the chat: supported. Dragging an image over the chat area shows a dashed accent outline and the label "Drop the photo to attach it". Dropping a non-image shows the attachment error. Drop target = the whole thread column.
- Paste an image from the clipboard: supported where the platform provides it (the composer `onPaste` reads `clipboardData.files`).

### 9.11 Suggested prompts (empty state)

Four chips in a 2×2 grid on desktop, a single horizontal scroll row on phone. Chips insert their text into the composer; they **do not send**, so the user can edit. Prompts contain no sample numbers.

| Chip | Inserted text |
|---|---|
| Which crop suits my soil? | "Which crop suits my soil? My soil and climate values are: " (caret at end) |
| Diagnose a plant photo | Opens `#/disease` (this is a navigation chip, not a text chip) |
| Control powdery mildew | "How do I control powdery mildew with practical, farm-safe steps?" |
| Fertilizer for a crop | "What fertilizer does [crop] need at [growth stage] on [soil type]?" (brackets are for the user to replace) |

Chip: 40 px tall (phone 44 px), 14/20 px, surface background, 1 px border, radius 8 px, icon 16 px at left.

### 9.12 Empty conversation

```text
                 Ask a question about your crops or soil.
   Crop choice, soil nutrients, irrigation, fertilizer, or a leaf photo.

   [ Which crop suits my soil? ]  [ Diagnose a plant photo ]
   [ Control powdery mildew ]     [ Fertilizer for a crop ]
```

Heading 24/32 px 600 (phone 20/28 px), subline 15/24 px `text-secondary`. No illustration, no leaf.

### 9.13 Scrolling

- The message list is the scroll container. The composer is outside it, pinned to the bottom of the column.
- Auto-scroll to the newest message only if the user is within 120 px of the bottom when a message arrives, or when the user sends.
- If the user has scrolled up, show a "Jump to latest" pill (32 px tall, surface, shadow-md, `ArrowDown` icon) centred above the composer. Clicking it smooth-scrolls to the bottom (`behavior: smooth`, or `auto` under reduced motion).
- Opening a conversation scrolls to the bottom immediately (no animation).

### 9.14 Live announcements

- A visually hidden `aria-live="polite"` region announces "Answer ready" when a response finishes and "Couldn't get an answer. {message}" on error. It does not read the answer aloud and it does not announce partial text (there is none).

### 9.15 Chat states summary

| State | Assistant area | Composer |
|---|---|---|
| Draft, empty | Empty conversation (9.12) | Enabled, focus on load |
| Sending | Pending (9.8) | Editable; send becomes Stop |
| Answer | Attribution (if known), Markdown, actions | Enabled |
| Error | Error block with Try again (9.9) | Enabled; failed text kept |
| Image attached | Image chip in composer | Send enabled even with empty text (an image-only send uses the default question, 11.5) |
| Offline | Banner above the composer: "You're offline. Messages will send when you reconnect." Send disabled | Disabled send, text kept |

---

## 10. Crop Recommendation Design

### 10.1 Purpose and honesty rules

The crop experience is a form that produces one chat turn, and a result panel that shows what the model returned. The rules:

1. The seven values are the user's inputs. They are labelled as inputs everywhere.
2. The seven values are **not** fertilizer prescriptions. N, P and K are shown as "soil nutrient levels you entered", never as "application rates" or "required fertilizer".
3. Nothing is pre-filled. No example values. No default values, because the backend silently fills missing fields with defaults (BL-3).
4. The result shows only what the backend returned: the Markdown explanation. No confidence, no top-N list, no probabilities (none are returned).

### 10.2 Layout

Desktop (≥ 1024 px): two columns. Left: form card, 420 px wide, sticky under the top bar. Right: result panel, fluid, maximum 780 px.

```text
┌───────────── Crop recommendation ────────────────────────────────────────────┐
│ ┌──── Enter your field values ─────┐  ┌──── Result ─────────────────────────┐│
│ │ Soil                              │  │                                    ││
│ │  Nitrogen (N)     [   90  ] kg/ha │  │  (empty)                           ││
│ │  Phosphorus (P)   [   42  ] kg/ha │  │  Enter the seven values and        ││
│ │  Potassium (K)    [   43  ] kg/ha │  │  choose Get recommendation.       ││
│ │  Soil pH          [  6.5  ]       │  │                                    ││
│ │ Climate                           │  │                                    ││
│ │  Temperature      [   25  ] °C    │  │                                    ││
│ │  Humidity         [   80  ] %     │  │                                    ││
│ │  Rainfall         [  200  ] mm    │  │                                    ││
│ │ ────────────────────────────────  │  │                                    ││
│ │ Missing: none                     │  │                                    ││
│ │ [        Get recommendation     ] │  │                                    ││
│ └───────────────────────────────────┘  └────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────────────┘
```

Tablet (768 to 1023 px): form on top at full width (two columns of fields inside), result below.

Phone (< 768 px): one column. Fields in a single column, 48 px tall inputs, and a sticky bottom bar with the submit button and a "Missing: …" line.

### 10.3 Field specification

| # | Label (visible) | Name in code | Unit (shown after the input) | Input attributes | Accepts | Client rule | Helper text (one line) |
|---|---|---|---|---|---|---|---|
| 1 | Nitrogen (N) | `N` | kg/ha | `inputmode="decimal"`, `step="0.1"`, `min="0"`, `max="1000"` | decimal ≥ 0 | Required; number; 0 to 1000 | "Soil nitrogen you measured or plan to supply." |
| 2 | Phosphorus (P) | `P` | kg/ha | as above | decimal ≥ 0 | Required; 0 to 1000 | "Soil phosphorus, in the same unit as your test." |
| 3 | Potassium (K) | `K` | kg/ha | as above | decimal ≥ 0 | Required; 0 to 1000 | "Soil potassium, in the same unit as your test." |
| 4 | Soil pH | `ph` | (pH scale) | `step="0.1"`, `min="0"`, `max="14"` | decimal | Required; 0 to 14 | "From a soil test. 7 is neutral." |
| 5 | Average temperature | `temperature` | °C | `step="0.1"`, `min="-50"`, `max="60"` | decimal | Required; -50 to 60 | "Typical average over the growing season." |
| 6 | Humidity | `humidity` | % | `step="1"`, `min="0"`, `max="100"` | decimal | Required; 0 to 100 | "Average relative humidity." |
| 7 | Rainfall | `rainfall` | mm | `step="1"`, `min="0"`, `max="5000"` | decimal ≥ 0 | Required; 0 to 5000 | "Total rainfall over the growing season." |

Note on the ranges: the training data's ranges are not in this repository, so no "outside the training range" warnings are designed. The validation is physical plausibility only. Add model-range warnings only after the ranges are read from the training data (open item in section 21).

Units are shown as a read-only suffix inside the field (13 px, `text-tertiary`, Geist Mono). The label always states the unit in the same way: "Nitrogen (N), kg/ha" is the accessible name; the visible label is "Nitrogen (N)" and the unit suffix sits in the field.

Field grouping: two `<fieldset>` groups with `<legend>` "Soil" (fields 1 to 4) and "Climate" (fields 5 to 7). Legends are 13/20 px 600 `text-secondary`.

A note under the Soil legend, 13/20 px `text-secondary`: "These are soil nutrient levels you entered, used by the crop model. They are not a fertilizer recommendation." This sentence is required and cannot be removed.

### 10.4 Validation and missing-parameter feedback

- Empty state of the form: all fields blank, placeholder shows a format example that is not a value ("e.g. 90" is **not** used; placeholder is the label's unit only, e.g. "kg/ha"). This satisfies "no hardcoded examples".
- Missing-parameter summary: a line above the button, 13/20 px: "Missing: Nitrogen (N), Rainfall" (lists the labels of empty fields in form order). When none are missing: "All seven values entered." in `text-tertiary`.
- Button: "Get recommendation". Disabled while any field is missing or invalid (`aria-disabled="true"`, and the summary explains why). Disabled buttons still focus, so the explanation is reachable.
- Field errors: shown on blur or on submit attempt. Message examples: "Enter a number." / "Use a value from 0 to 14 for pH." / "Humidity must be between 0 and 100." Errors are `aria-describedby` and `aria-invalid`.
- Decimal separator: accept "." and "," (comma converted to dot before validation); show the value as typed.
- Units are never converted by the UI. The user types the unit the field states.

### 10.5 What is sent (the request)

The form builds one text message and posts it to the existing chat endpoint with a new session. The values are written as the user typed them. Example with user values (not a default): the form builds

`Recommend a crop for these field conditions. Soil: nitrogen (N) 90 kg/ha, phosphorus (P) 42 kg/ha, potassium (K) 43 kg/ha, soil pH 6.5. Climate: average temperature 25 °C, humidity 80 %, rainfall 200 mm.`

Why this exact shape: the backend extracts the seven parameters from free text with an LLM (BL-3). Stating all seven, each with its name and unit, is the best available input to that extraction. It does not guarantee correct extraction; the result is labelled accordingly (10.7).

"What was sent" is a disclosure under the result (text in `text-tertiary`, `<details>`), showing the exact message text. It makes the request visible for a user who wants to verify the inputs.

### 10.6 Session

- Title: "Crop recommendation · {date}" where date is the local short date ("Nov 7").
- The session is a normal conversation: it appears in the sidebar, can be reopened at `#/chat/<id>`, and its messages load from history.
- Counted on the dashboard as a crop recommendation (8.6).

### 10.7 Result panel

Shown after the response arrives (until then the loading state in 10.8 is shown).

```text
┌──── Result ─────────────────────────────────────────────────────────┐
│ Crop recommendation                                   Nov 7, 10:42  │
│ Answered by [Crop Recommendation]                                   │
│                                                                     │
│ (Markdown explanation returned by the crop agent: headings, lists,  │
│  and the crop name as written by the model)                         │
│                                                                     │
│ ─────────────────────────────────────────────────────────────────── │
│ ▸ Values you submitted                                              │
│   Nitrogen 90 kg/ha · Phosphorus 42 kg/ha · Potassium 43 kg/ha · …   │
│ ▸ What was sent                                                     │
│ [Copy]   [Edit values]   [Open conversation]                        │
│ The recommendation comes from a crop model using the values above.  │
│ Confirm planting decisions with local agronomy advice.              │
└─────────────────────────────────────────────────────────────────────┘
```

Components and rules:

- Header: title "Crop recommendation" (18/26 px 600), the time sent (12/16 px `text-tertiary`).
- Attribution row: "Answered by [Crop Recommendation]" (the crop badge, 9.6.2).
- Body: the crop agent's Markdown, rendered by the Markdown rules in 9.7. Do not re-parse it, do not extract the crop name from it, do not restyle its headings beyond 9.7.
- **Values you submitted**: a read-only definition list (label, value with unit in Geist Mono). Heading text says "Values you submitted", never "Model inputs" or "Used by the model", because the response does not echo the values the model used (BL-3).
- "What was sent": the exact message (10.5).
- Actions: **Copy** (copies the Markdown text), **Edit values** (returns the form to edit, keeping the entered values), **Open conversation** (goes to `#/chat/<id>`, where the follow-up questions can be asked).
- Footnote, 12/16 px `text-tertiary`: "The recommendation comes from a crop model using the values above. Confirm planting decisions with local agronomy advice."

**Not shown, by design:** top recommended crops (one label is returned), confidence or probability (not returned), a crop-name headline (not a separate field; the name appears only in the Markdown text, and parsing it would be a guess), charts, colour-coded suitability scores (no data).

### 10.8 Loading state

The form is disabled (fields `readonly` with `aria-busy="true"` on the form; the submit becomes "Running…" with a spinner). The result panel shows the pending state from 9.8 with the line "Running the crop model and writing the explanation…" and the elapsed time.

### 10.9 Errors

Use the mapping in 9.9. The inputs are kept. The error appears in the result panel. A 400 response for the crop message is shown as "That message couldn't be sent. Check the values and try again." (the form has validated them, so a 400 is unexpected). A 503/504 shows the retry button.

### 10.10 Responsive behaviour

- Desktop: two columns as above; the form column is sticky with `top: 72px` (under the top bar).
- Tablet: stacked; the form uses a two-column field grid (Soil fields left, Climate right) so it is not one tall column.
- Phone: single column; the submit button is in a sticky bottom bar (`position: sticky; bottom: 0`, safe-area padding `env(safe-area-inset-bottom)`), with the "Missing:" summary above it. The result appears below the form; on submit, the page scrolls to the result header.

---

## 11. Disease Detection Design

### 11.1 Purpose

A farmer takes a photo of a plant and gets the likely condition with simple treatment and prevention notes. The experience is built around one photo, one button and one clear result.

### 11.2 Layout

Desktop (≥ 1024 px): two columns. Left (400 px): photo area, optional note, "Analyse photo" button. Right: result panel (fluid, max 780 px).

Phone: one column. Photo area first (full width), then the note field, then the sticky "Analyse photo" button.

```text
┌──── Photo ──────────────────────────┐ ┌──── Result ───────────────────────────┐
│ ┌─────────────────────────────────┐ │ │                                        │
│ │                                 │ │ │ Likely condition                       │
│ │   [ image preview, contain ]    │ │ │ (Markdown from the disease agent)      │
│ │                                 │ │ │                                        │
│ └─────────────────────────────────┘ │ │ Treatment and prevention               │
│ leaf-apple.jpg · 1.2 MB      [✕]    │ │ (Markdown, same rules)                  │
│                                     │ │                                        │
│ Anything you've noticed? (optional) │ │ ▸ What was sent                         │
│ [ Yellow spots on older leaves…   ] │ │ [Copy] [Analyse another]  [Open chat]  │
│                                     │ │                                        │
│ [        Analyse photo          ]   │ │ Automated photo analysis. For a         │
│                                     │ │ confirmed diagnosis or chemical         │
│ Tips: one leaf, daylight, in focus  │ │ treatment, check with an extension      │
└─────────────────────────────────────┘ │ service or agronomist.                  │
                                        └────────────────────────────────────────┘
```

### 11.3 Upload area

- Empty state (no photo): a dashed-border drop zone, 220 px tall on desktop, 180 px on phone, `--color-surface` background, icon `ImagePlus` 28 px, the title "Add a photo of the plant", the line "Drop an image here, or choose one", and the buttons **Choose photo** (primary) and, on phone, **Take photo** (secondary, which opens the camera on devices that support it through `accept` plus a second input with `capture="environment"`).
- Dashed border: 1.5 px `--color-control-border` (3:1 against the surface; it is also a control boundary, so it passes 1.4.11).
- Drag-and-drop: `dragenter` and `dragover` set the zone to `drag-active` (border accent, background `--color-accent-subtle`, label "Drop to add the photo"). `drop` takes the first file. A non-image file shows an inline error, nothing is attached.
- Keyboard: the zone is a button-like element with `role="button"`, `tabindex="0"`, activated by Enter or Space to open the file picker.
- Accept: `image/jpeg,image/png,image/webp,image/gif` (matches `attachments.ts` and `image_storage.py`). The gif is accepted by the backend; the detector's support for gif is not verified, so the help text recommends JPEG or PNG.
- Size: 5 MB maximum (matches the gateway's 5 MB multer limit and the backend's check). Over the limit: "That photo is over 5 MB. Choose a smaller one."

### 11.4 Preview, progress and analysis states

Preview: once a file is chosen, the drop zone is replaced by the preview. The image uses `object-fit: contain` on a `--color-sunken` background, maximum height 360 px (desktop) or 280 px (phone), radius 12 px. Never cropped. Below it: file name (14/20 px, one line) and size (12/16 px). Remove button (44 px touch target, `X` icon, `aria-label="Remove photo"`).

Upload progress: the chat endpoint is a single multipart POST. The current `fetch` cannot report upload progress. The design uses `XMLHttpRequest` for this one call (same endpoint, same fields, same headers) because `XMLHttpRequest.upload.onprogress` reports real bytes sent. The UI then shows:

| Phase | Shown as | Source |
|---|---|---|
| Uploading | Determinate bar, accent fill, 4 px tall, radius full, with "Uploading 64%" (tabular numbers) | `upload.onprogress` (real bytes) |
| Uploaded, waiting for the analysis | Indeterminate bar (a 30% segment sliding, 1.4 s; reduced motion: a static full-width bar at 40% opacity) and "Analysing your photo…" with elapsed time | the response has not arrived |
| Done | Bar removed; result panel fills | response |

The indeterminate bar is used only after the upload completes, because the server does no reportable progress (BL-1). This is honest: no fake percentage after the upload.

Analysis state copy after 20 s: "Image analysis can take a minute." After 45 s: "Still analysing. You can keep this tab open."

### 11.5 The note and the default question

- Field label: "Anything you've noticed? (optional)". Placeholder: "e.g. yellow spots on older leaves" (this is a placeholder of a kind of observation, not an example result). Helper: "Helps the analysis. Leave it empty to just analyse the photo." Maximum 500 characters with a counter that appears at 400.
- The gateway requires a non-empty `query` (`chat.controller.js`: "Query is required"). When the note is empty, the UI sends this fixed default question: "What plant disease is shown in this photo, and what treatment and prevention do you recommend?" The default is shown in "What was sent" so it is never hidden.

### 11.6 Result panel

- Header: "Plant photo analysis" (18/26 px 600), time, attribution row with the disease badge (9.6.2).
- Thumbnail of the analysed photo (the same image, `contain`, max height 200 px), next to the header on desktop.
- Body: the disease agent's Markdown. The Markdown is expected to contain the likely condition and treatment/prevention sections; the UI does not parse them. Headings are rendered as written (9.7).
- **Not shown**: a confidence percentage (the response has no confidence field; the detector computes one, but the chat route does not return it; BL-4), the canonical label (not returned), a top-3 list (not returned), a healthy/diseased badge (not returned as a field).
- Actions: **Copy**, **Analyse another** (clears the photo, keeps the note cleared, returns to the drop zone), **Open conversation** (for follow-up questions; the conversation contains the photo).
- Footer note, 12/16 px `text-tertiary`: "Automated photo analysis. For a confirmed diagnosis or any chemical treatment, check with a local extension service or agronomist."
- Unsupported or unclear image: the server returns 400 with a message (for invalid images) or the agent's text says it cannot identify the plant. The design presents the 400 as an error in 11.7; a text answer that says "cannot identify" is shown as written, with no special styling.

### 11.7 Errors

| Situation | Message | Action |
|---|---|---|
| Not an image (client check) | "Please choose a JPEG, PNG, WebP, or GIF image." | Choose another file |
| Over 5 MB | "That photo is over 5 MB. Choose a smaller one." | Choose another file |
| 400 image invalid | "That photo couldn't be analysed. Try a clear, close photo of one leaf in daylight." | Analyse again or choose another |
| 503 detection service unavailable | "The plant-analysis service is unavailable right now. Try again shortly." | Try again (keeps the photo) |
| 504 timeout | "The analysis took too long. Try again with a smaller photo or the same photo." | Try again |
| 502 service error | "The plant-analysis service returned an error. Try again shortly." | Try again |
| 500 | "Something went wrong analysing the photo. Try again." | Try again |

Error block sits in the result panel, with the photo kept in place so retry is one tap.

### 11.8 Photo tips (always visible, 13/20 px, `text-secondary`)

"One leaf, in daylight, in sharp focus. Fill the frame with the affected leaf. Avoid shadows and glare. Add a close second photo of the underside if you can (send it as a new analysis)."

Tips are shown as a short list of three items on desktop, one paragraph on phone.

### 11.9 Responsive

- Desktop: two columns; the photo column is sticky.
- Phone: the drop zone becomes "Choose photo" and "Take photo" full-width buttons (48 px); preview replaces the zone once chosen; the "Analyse photo" button is sticky at the bottom with the safe-area padding.
- Image previews never exceed the viewport width; `max-width: 100%`.

---

## 12. Agricultural Assistant Design

### 12.1 Purpose

The general chat for fertilizer, soil nutrients, irrigation, organic farming, crop management and general agronomy. It runs on the same chat as all other questions; the General Agriculture agent answers most of these. Fertilizer is a topic of that agent, not a separate agent.

### 12.2 Entry

The empty state's suggestion chips (9.11). The topic starters below are the same chips, grouped in the empty state as one row on desktop and a horizontal scroll row on phone:

| Topic | Starter text (inserted, not sent) |
|---|---|
| Fertilizer | "What fertilizer does [crop] need at [growth stage] on [soil type]?" |
| Soil nutrients | "What do low nitrogen and low phosphorus look like in a [crop], and how do I correct them?" |
| Irrigation | "How often should I irrigate [crop] in [season] with [soil type]?" |
| Organic farming | "What organic options control [pest or disease] on [crop]?" |
| Crop management | "What should I watch for at [growth stage] of [crop]?" |
| Knowledge | "Explain [agronomic term] in plain words." |

### 12.3 Rendering

- Responses are Markdown (9.7). Tables render as GFM tables with the scroll container (9.7), so a fertilizer schedule written as a table is readable on a phone.
- **No nutrient status indicators, no coloured gauges, no structured advisory cards** in this release. The backend returns text only (BL-13). The design will not invent fields. A later structured response would be a new contract, decided separately.
- Headings the model writes (for example "Application rate" or "Timing") render as ordinary headings.

### 12.4 Advisory footer

A static line below the composer on every chat (9.10 disclaimer), so the caveat is always present: "CropSage can make mistakes. Check important decisions with a local agronomist or extension service." No per-answer confidence labels: the system does not return a confidence, so none can be shown honestly.

### 12.5 Follow-up questions

Conversations keep their history, and the supervisor sees the last 6 messages (BL-10). Specialists see only the current message. The empty state and the composer placeholder do not promise memory. A short line in the conversation's "About this conversation" popover (13 and 14) says: "Restate the crop, field and stage in follow-up questions. This makes the answer more accurate."

---

## 13. Session Memory Design

### 13.1 What the product actually remembers (from source)

- Each conversation is one server session (`sessions` row) whose messages are stored in the agent's checkpoint, keyed by the session id (`graph.ainvoke` with `thread_id = session_id`).
- The supervisor receives the previous 6 messages as context for routing (`main_graph.py`, `classify_and_route`). Specialists receive only the current question (or its sanitised version).
- Disease context: a previous disease result is reused only when the new message has no image (`run_agents`, `prior_disease`).
- Conversations persist across reloads and devices, because they are on the server.

The UI copy must not say "CropSage remembers everything". It says: "Conversations are saved to your account." and, in the About popover, the follow-up tip in 12.5.

### 13.2 Conversation list

- Sorted by `updatedAt`. The server changes that field on rename, not on each message (BL-7), so the order is "recently renamed or created", not "recently used". The row label therefore reads "Updated {date}" and the list is never described as sorted by activity. If the backend later updates the field on each message, no UI change is needed.
- Titles: auto-generated from the first 42 characters of the first message (existing `generateTitle`). Renaming is available.
- Search: title only (9.2). Searching message text would need a backend search endpoint (none exists); it is not designed here.

### 13.3 Starting a conversation

- A draft is a client state only. The first send creates the session with the title derived from the first message (or "Crop recommendation · date" / "Plant photo · date" for those modes), then posts the message.
- If session creation fails, the message stays in the composer and the error shows (9.9).

### 13.4 Session context visibility

- Header meta line: "Updated {relative time} · {n} messages" (9.4). The count is real.
- Popover "About this conversation" from the header's ⋯ menu: created date (from the session's `createdAt`), updated date, message count, and the follow-up tip (12.5). No IDs, no session tokens, no internal names.

### 13.5 Continuity UX

- Opening a conversation loads the full history (`GET /api/chat/:id`). Images in history arrive as data URLs; a conversation with many photos is heavy (BL-17); show a skeleton and load images lazily with `loading="lazy"` on the `<img>`.
- A conversation that cannot be loaded (404 or 403) shows "This conversation isn't available. It may have been deleted." and a button to start a new chat. It does not expose the status code.

### 13.6 Deleting and renaming

Covered in 9.2 and 9.4. Deleting the open conversation returns to the draft (`#/chat`) with a short notice "Conversation deleted." (toast-style status, 4 s, `role="status"`).

### 13.7 What is not exposed

Session ids, checkpoint or thread identifiers, token counts, model names, the disease detector's raw labels, the supervisor's routing output, and the `agent_responses` keys beyond the badges. These are internals (the brief asks for this).

---

## 14. Profile and Settings Design

### 14.1 Information available

`User` = `id`, `email`, `createdAt`, `isActive` (`types/api.ts`, `getMe` in `auth.controller.js`). There is no name, avatar, phone or preference endpoint. Therefore:

- **Display name**: derived from the email local-part, exactly as today (`user.email.split("@")[0]`). For `ada@example.com` it is shown as "Ada". A future display-name field would need a backend change; it is not designed here. Until then the UI uses the local-part only.
- **Avatar**: a 32 px circle with the first letter of the local-part, uppercase, on `--color-sunken`, 13/20 px, 600 weight. No photo upload.
- **Member since**: `createdAt`, formatted "Member since Oct 30, 2026".

### 14.2 Settings layout

Desktop: a single column (max 640 px) with section cards. Phone: the same sections, full width.

```text
Settings

┌ Profile ───────────────────────────────────────────────┐
│ (A)  Ada                                               │
│      you@example.com                                   │
│      Member since Oct 30, 2026                         │
└────────────────────────────────────────────────────────┘

┌ Appearance ────────────────────────────────────────────┐
│ Theme                                                   │
│ ( Light ) ( Dark ) ( System )   ← segmented, radio group │
│ Applies on this device.                                 │
└────────────────────────────────────────────────────────┘

┌ Account ───────────────────────────────────────────────┐
│ Email                    ada@example.com   (read only)  │
│                                                         │
│ [ Sign out ]                                             │
└────────────────────────────────────────────────────────┘

┌ About ─────────────────────────────────────────────────┐
│ CropSage web app · version 0.1.0                       │
│ Keyboard: Ctrl/⌘ + Shift + O  New chat                 │
│ How CropSage works: each question is checked for       │
│ relevance to agriculture and sent to the right         │
│ specialist. Questions outside agriculture are declined.│
└────────────────────────────────────────────────────────┘
```

### 14.3 Theme selection

- Segmented control (radio group, `role="radiogroup"`, each option a `role="radio"` with `aria-checked`): Light, Dark, System. Each option has an icon (`Sun`, `Moon`, `MonitorCog`) and text. 40 px tall, radius 8 px. Selected: `surface` background with `shadow-xs` and accent-text label; unselected: `text-secondary`. Arrow keys move the selection.
- Behaviour unchanged: stored in `agrimind.theme`, applied immediately, follows the OS in System mode. Immediate application with no reload.
- The same control is available as a compact three-state button in the sidebar footer (icon only, with `aria-label` "Theme: System. Change theme").

### 14.4 Account

- Email: read only, with a "Copy" button. No change-email and no change-password in this release (no endpoints exist). Do not render disabled placeholders for them.
- Sign out: secondary button, 40 px. Calls `POST /api/auth/logout` and clears local state; on any failure it still clears local state (existing behaviour). Confirmation: none (sign-out is reversible by signing in). The sign-out button sits at the bottom of the Account section, separated by 24 px.

### 14.5 About

- Version string from the app's `package.json` version (`0.1.0`), read at build time.
- The keyboard shortcut.
- The "How CropSage works" paragraph (copy in 14.2). It is the only place where the Supervisor is described for users.
- Link: "Privacy" and "Terms" are not linked because no such pages exist in this repository. Do not add links to pages that do not exist.

### 14.6 Sidebar user block

- Left: avatar (32 px) and two lines: display name (14/20, 500) and email (12/16, `text-tertiary`, one line with ellipsis).
- Right: a "⋯" icon button (36 px) that opens a small menu: Settings, Theme (sub-items Light, Dark, System with check marks), Sign out. Keyboard accessible, Escape closes.

---

## 15. Complete Design Token System

### 15.1 Naming, where the values live, and Tailwind

- Every token is a CSS custom property with a category prefix: `--color-*`, `--space-*`, `--radius-*`, `--shadow-*`, `--text-*` (size, line height and weight as one shorthand), `--font-*`, `--z-*`, `--size-*`, `--motion-*`, `--ease-*`.
- Light values are declared on `:root`; dark values on `:root.dark` (the class `useTheme` already toggles on `<html>`). Components never test the theme; they only read tokens.
- Tailwind v4 (installed) stays imported. It is used for layout utilities where they read better (flex, grid, gap, a few spacings). Colours, radii, shadows and type come from the variables in section 15.11. No `@theme` colour mapping is used: a Tailwind theme entry with the same name as the runtime variable would reference itself, so it is not written.
- Migration aliases, kept for one release and then removed: `--paper` → `--color-canvas`; `--surface` → `--color-surface`; `--surface-soft` → `--color-sunken`; `--surface-raised` → `--color-raised`; `--line` → `--color-border`; `--ink` → `--color-text-primary`; `--muted` → `--color-text-secondary`; `--quiet` → `--color-text-tertiary`; `--accent` → `--color-accent`; `--danger` → `--color-error`; `--shadow` → `--shadow-md`; `--content-width` → `--size-column`.

### 15.2 Colour tokens

Light and dark are two palettes, designed separately. The dark theme is not an inversion: it uses a layered canvas (canvas, darker sidebar, surface, raised), borders as its main elevation, a lighter teal accent that holds contrast on dark, and slightly brighter semantic colours.

| Token | Role | Light | Dark |
|---|---|---|---|
| `--color-canvas` | App background | `#F7F7F8` | `#101215` |
| `--color-sidebar` | Sidebar background | `#F1F2F4` | `#0C0E11` |
| `--color-surface` | Cards, composer, menus, inputs | `#FFFFFF` | `#16191D` |
| `--color-raised` | Popovers, dialogs, raised cards | `#FFFFFF` | `#1C2025` |
| `--color-sunken` | Code, table headers, chips, image wells | `#EEF0F3` | `#0B0D10` |
| `--color-bubble-user` | User message bubble | `#EEF0F3` | `#1A1E24` |
| `--color-text-primary` | Headings, body, values | `#15171C` | `#ECEEF2` |
| `--color-text-secondary` | Supporting text, nav items | `#4A5160` | `#A9B0BC` |
| `--color-text-tertiary` | Meta, timestamps, helper text | `#5E6777` | `#7F8794` |
| `--color-text-disabled` | Disabled text only (exempt) | `#98A2B3` | `#5C6470` |
| `--color-border` | Decorative dividers, card edges | `#E3E6EB` | `#272C33` |
| `--color-border-strong` | Blockquote rule, secondary button edge | `#C9CED6` | `#3A414B` |
| `--color-control-border` | Input, textarea, dashed drop zone (3:1 required) | `#7D8698` | `#737B8A` |
| `--color-accent` | Primary actions, links, focus, selected nav | `#0F6B66` | `#5FC2B9` |
| `--color-accent-hover` | Primary hover fill | `#0B5652` | `#7AD3CB` |
| `--color-accent-pressed` | Primary pressed fill | `#094744` | `#4FB0A7` |
| `--color-accent-subtle` | Accent tint behind chips and drag-over | `#E3F1F0` | `#15302E` |
| `--color-accent-on` | Text and icons on accent fills | `#FFFFFF` | `#06201E` |
| `--color-success` | Success text and icons | `#11703F` | `#4CC38A` |
| `--color-success-subtle` | Success banner background | `#E6F4EC` | `#12281E` |
| `--color-warning` | Warning text and icons | `#8A4B00` | `#E9B45E` |
| `--color-warning-subtle` | Warning banner background | `#FDF3E2` | `#2B2214` |
| `--color-error` | Error text, icons, destructive fill | `#B42318` | `#F2877F` |
| `--color-error-hover` | Destructive hover fill | `#9F1F15` | `#E36F67` |
| `--color-error-on` | Text on destructive fill | `#FFFFFF` | `#101215` |
| `--color-error-subtle` | Error banner background | `#FDEBE9` | `#2E1A19` |
| `--color-info` | Info text and icons | `#1D5CA8` | `#7DB3F2` |
| `--color-info-subtle` | Info banner background | `#E8F0FA` | `#14202F` |
| `--color-agent-crop` | Crop Recommendation identity dot and icon | `#0F6B66` | `#5FC2B9` |
| `--color-agent-disease` | Plant Disease Detection identity | `#7A3E8C` | `#C49AD6` |
| `--color-agent-general` | General Agriculture identity | `#2F5C9E` | `#8DB3EA` |
| `--color-agent-supervisor` | Supervisor (About text only) | `#4A5160` | `#A9B0BC` |
| `--color-focus-ring` | Focus outline (2 px, offset 2 px) | `#0F6B66` | `#5FC2B9` |
| `--color-scrim` | Modal and drawer scrim | `rgba(21,23,28,0.40)` | `rgba(0,0,0,0.60)` |

Accent discipline: the accent appears on primary buttons, the send button, links, the focus ring, the selected navigation item, the selected theme option, and the crop identity. Nothing else. Success green is used for status text and icons only, and it is kept apart from the accent by hue (teal is near 175 degrees, the success green near 150) and by use.

### 15.3 Typography

Families:

- `--font-sans`: `"Geist Variable", Geist, ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif`
- `--font-mono`: `"Geist Mono Variable", "Geist Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace`

Loading: `@fontsource-variable/geist` and `@fontsource-variable/geist-mono` (optional, section 21.4). Without them the stack falls back to the system UI font, which keeps the layout. `DM Sans` is removed from the stack.

| Token | Size / line height | Weight | Tracking | Use |
|---|---|---|---|---|
| `--text-display` | 36 / 44 px (phone 30 / 38) | 600 | −0.02 em | Auth heading only |
| `--text-h1` | 24 / 32 px (phone 20 / 28) | 600 | −0.015 em | View titles (Crop, Plant photo, Settings, Welcome) |
| `--text-h2` | 18 / 26 px | 600 | −0.01 em | Section and result titles |
| `--text-h3` | 15 / 22 px | 600 | 0 | Card titles, group headers in the sidebar |
| `--text-body-lg` | 16 / 26 px | 400 | 0 | Chat body on phone |
| `--text-body` | 15 / 24 px | 400 | 0 | Chat body and paragraphs on desktop |
| `--text-ui` | 14 / 20 px | 500 | 0 | Buttons, nav items, list rows |
| `--text-small` | 13 / 20 px | 500 | 0 | Labels, helper text, table headers, field units |
| `--text-caption` | 12 / 16 px | 500 | 0.01 em | Timestamps, meta, group headers, badges |
| `--text-code` | 13 / 20 px (mono) | 400 | 0 | Code blocks, numeric values in tables |
| `--text-code-inline` | 13 px (mono) | 400 | 0 | Inline code |

Weights: 400, 500, 600 only. No 700. Numeric values use `font-variant-numeric: tabular-nums`. Inputs are 16 px on phone (prevents iOS zoom; 18.4).

Measure: the chat column caps line length (about 90 characters at 15 px). Paragraph text in cards is capped at 68 characters (`max-width: 68ch`).

### 15.4 Spacing

Base unit 4 px: `--space-0` 0, `--space-1` 4 px, `--space-2` 8 px, `--space-3` 12 px, `--space-4` 16 px, `--space-5` 20 px, `--space-6` 24 px, `--space-8` 32 px, `--space-10` 40 px, `--space-12` 48 px, `--space-16` 64 px.

Conventions: 8 px between a label and its helper; 12 px between related list items; 16 px inside compact cards; 20 px inside standard cards; 24 px between sections; 32 px between page blocks on desktop; 16 px page padding on phone.

### 15.5 Radius

| Token | Value | Use |
|---|---|---|
| `--radius-xs` | 4 px | Inline code, small chips |
| `--radius-sm` | 6 px | Monogram avatar, menu items |
| `--radius-md` | 8 px | Buttons, inputs, list rows, code blocks, suggestion chips |
| `--radius-lg` | 12 px | Cards, images, result panels |
| `--radius-xl` | 16 px | Composer, dialogs, user bubble (top corners and left) |
| `--radius-full` | 999 px | Badges, the send button, segmented track |

### 15.6 Shadows and elevation

Light and dark token values are in 15.11. Light shadows are soft neutral; dark shadows are deeper and used sparingly.

| Token | Use |
|---|---|
| `--shadow-xs` | Active sidebar row, selected segment |
| `--shadow-sm` | Composer, hovered interactive card |
| `--shadow-md` | Menus, popovers, the jump-to-latest pill |
| `--shadow-lg` | Dialogs, mobile drawer |

Rule: a card at rest has a border and no shadow. Shadows appear on hover (interactive cards), on floating layers, and on the composer. In dark mode, elevation comes mainly from the surface steps (canvas, surface, raised).

### 15.7 Layout and sizes

| Token | Value | Use |
|---|---|---|
| `--size-sidebar` | 268 px | Expanded sidebar (≥ 1024 px) |
| `--size-sidebar-rail` | 60 px | Collapsed rail (768 to 1023 px) |
| `--size-drawer` | min(86vw, 320 px) | Mobile drawer width |
| `--size-topbar` | 56 px | Chat header and mobile top bar |
| `--size-column` | 760 px | Message column and composer |
| `--size-column-wide` | 1040 px | Dashboard main column |
| `--size-form` | 420 px | Crop form column |
| `--size-result` | 780 px | Result panel maximum |
| `--size-auth` | 400 px | Auth card |
| `--size-dialog` | 440 px | Confirm dialog |
| `--size-touch` | 44 px | Minimum touch target on phone and tablet |
| `--size-control` | 36 px | Default button and icon button (desktop) |
| `--size-control-sm` | 32 px | Small button and row action (desktop) |
| `--size-input` | 40 px | Input height (desktop); 44 px on phone |
| `--size-icon` | 16 px | Default icon; 14 px in badges; 18 px in composer; 20 px in headers |

### 15.8 Z-index

| Token | Value | Layer |
|---|---|---|
| `--z-base` | 0 | Content |
| `--z-sticky` | 10 | Composer, sticky crop and disease bars |
| `--z-topbar` | 20 | Chat header |
| `--z-scrim` | 39 | Drawer scrim |
| `--z-drawer` | 40 | Mobile drawer |
| `--z-popover` | 50 | Menus, popovers |
| `--z-dialog` | 60 | Dialogs, lightbox |
| `--z-toast` | 70 | Status notices |

### 15.9 Motion

| Token | Value | Use |
|---|---|---|
| `--motion-fast` | 120 ms | Hover, pressed, colour, focus |
| `--motion-base` | 180 ms | Menus, popovers, banners, appearing answers |
| `--motion-slow` | 240 ms | Drawer, sidebar collapse |
| `--motion-page` | 160 ms | View cross-fade |
| `--ease-out` | `cubic-bezier(0.2, 0, 0, 1)` | Entering and moving |
| `--ease-in` | `cubic-bezier(0.4, 0, 1, 1)` | Leaving |
| `--ease-in-out` | `cubic-bezier(0.4, 0, 0.2, 1)` | Sidebar collapse and expand |

### 15.10 Focus, hover, active, disabled, loading

Focus: `outline: 2px solid var(--color-focus-ring); outline-offset: 2px;` on every interactive element, shown for keyboard focus only (`:focus-visible`). Inputs add a border change to `--color-accent`. Per-control state rules are in 17.3.

### 15.11 Full token CSS (single source)

```css
/* src/styles/tokens.css */

:root {
  color-scheme: light;

  --color-canvas: #F7F7F8;
  --color-sidebar: #F1F2F4;
  --color-surface: #FFFFFF;
  --color-raised: #FFFFFF;
  --color-sunken: #EEF0F3;
  --color-bubble-user: #EEF0F3;

  --color-text-primary: #15171C;
  --color-text-secondary: #4A5160;
  --color-text-tertiary: #5E6777;
  --color-text-disabled: #98A2B3;

  --color-border: #E3E6EB;
  --color-border-strong: #C9CED6;
  --color-control-border: #7D8698;

  --color-accent: #0F6B66;
  --color-accent-hover: #0B5652;
  --color-accent-pressed: #094744;
  --color-accent-subtle: #E3F1F0;
  --color-accent-on: #FFFFFF;

  --color-success: #11703F;
  --color-success-subtle: #E6F4EC;
  --color-warning: #8A4B00;
  --color-warning-subtle: #FDF3E2;
  --color-error: #B42318;
  --color-error-hover: #9F1F15;
  --color-error-on: #FFFFFF;
  --color-error-subtle: #FDEBE9;
  --color-info: #1D5CA8;
  --color-info-subtle: #E8F0FA;

  --color-agent-crop: #0F6B66;
  --color-agent-disease: #7A3E8C;
  --color-agent-general: #2F5C9E;
  --color-agent-supervisor: #4A5160;

  --color-focus-ring: #0F6B66;
  --color-scrim: rgba(21, 23, 28, 0.40);

  --shadow-xs: 0 1px 0 rgba(21, 23, 28, 0.04);
  --shadow-sm: 0 1px 2px rgba(21, 23, 28, 0.06), 0 1px 1px rgba(21, 23, 28, 0.04);
  --shadow-md: 0 4px 12px -2px rgba(21, 23, 28, 0.10), 0 2px 4px -2px rgba(21, 23, 28, 0.06);
  --shadow-lg: 0 16px 40px -12px rgba(21, 23, 28, 0.20), 0 4px 12px -4px rgba(21, 23, 28, 0.08);
}

:root.dark {
  color-scheme: dark;

  --color-canvas: #101215;
  --color-sidebar: #0C0E11;
  --color-surface: #16191D;
  --color-raised: #1C2025;
  --color-sunken: #0B0D10;
  --color-bubble-user: #1A1E24;

  --color-text-primary: #ECEEF2;
  --color-text-secondary: #A9B0BC;
  --color-text-tertiary: #7F8794;
  --color-text-disabled: #5C6470;

  --color-border: #272C33;
  --color-border-strong: #3A414B;
  --color-control-border: #737B8A;

  --color-accent: #5FC2B9;
  --color-accent-hover: #7AD3CB;
  --color-accent-pressed: #4FB0A7;
  --color-accent-subtle: #15302E;
  --color-accent-on: #06201E;

  --color-success: #4CC38A;
  --color-success-subtle: #12281E;
  --color-warning: #E9B45E;
  --color-warning-subtle: #2B2214;
  --color-error: #F2877F;
  --color-error-hover: #E36F67;
  --color-error-on: #101215;
  --color-error-subtle: #2E1A19;
  --color-info: #7DB3F2;
  --color-info-subtle: #14202F;

  --color-agent-crop: #5FC2B9;
  --color-agent-disease: #C49AD6;
  --color-agent-general: #8DB3EA;
  --color-agent-supervisor: #A9B0BC;

  --color-focus-ring: #5FC2B9;
  --color-scrim: rgba(0, 0, 0, 0.60);

  --shadow-xs: 0 1px 0 rgba(0, 0, 0, 0.30);
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.40);
  --shadow-md: 0 8px 20px -6px rgba(0, 0, 0, 0.60);
  --shadow-lg: 0 24px 48px -12px rgba(0, 0, 0, 0.70);
}

:root {
  --font-sans: "Geist Variable", Geist, ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --font-mono: "Geist Mono Variable", "Geist Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;

  --text-display: 600 36px/44px var(--font-sans);
  --text-h1: 600 24px/32px var(--font-sans);
  --text-h2: 600 18px/26px var(--font-sans);
  --text-h3: 600 15px/22px var(--font-sans);
  --text-body-lg: 400 16px/26px var(--font-sans);
  --text-body: 400 15px/24px var(--font-sans);
  --text-ui: 500 14px/20px var(--font-sans);
  --text-small: 500 13px/20px var(--font-sans);
  --text-caption: 500 12px/16px var(--font-sans);
  --text-code: 400 13px/20px var(--font-mono);

  --radius-xs: 4px;
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --radius-full: 999px;

  --space-0: 0;
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;
  --space-16: 64px;

  --z-base: 0;
  --z-sticky: 10;
  --z-topbar: 20;
  --z-scrim: 39;
  --z-drawer: 40;
  --z-popover: 50;
  --z-dialog: 60;
  --z-toast: 70;

  --motion-fast: 120ms;
  --motion-base: 180ms;
  --motion-slow: 240ms;
  --motion-page: 160ms;
  --ease-out: cubic-bezier(0.2, 0, 0, 1);
  --ease-in: cubic-bezier(0.4, 0, 1, 1);
  --ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);

  --size-sidebar: 268px;
  --size-sidebar-rail: 60px;
  --size-topbar: 56px;
  --size-column: 760px;
  --size-column-wide: 1040px;
  --size-form: 420px;
  --size-result: 780px;
  --size-auth: 400px;
  --size-dialog: 440px;
  --size-touch: 44px;
  --size-control: 36px;
  --size-control-sm: 32px;
  --size-input: 40px;
}
```

Usage note: `font: var(--text-body);` sets family, size, line height and weight together. Components that need one part override only that part after the shorthand.

### 15.12 Breakpoints

| Name | Width | Layout |
|---|---|---|
| (base) | 0 to 639 px | Phone |
| `sm` | 640 px | Large phone, landscape |
| `md` | 768 px | Tablet: sidebar as rail |
| `lg` | 1024 px | Laptop: sidebar expanded, two-column tools |
| `xl` | 1280 px | Desktop: wider gutters, same column widths |
| `2xl` | 1536 px | Large desktop: extra space is canvas |

These replace the existing `850px` and `640px` queries (18.1). Media queries cannot read CSS variables, so the widths are written in each query and listed here as the reference.

### 15.13 Data visualisation

No chart library is installed, and the backend returns no numeric series (the crop output is a label; the dashboard has no metrics). No charts are designed. If one is added later it needs its own library decision; its colours would be `--color-accent` for the primary series, `--color-text-tertiary` for axes and `--color-border` for gridlines.

---

## 16. Component Library and Architecture

### 16.1 Target folder structure

New files are marked **new**; existing files are kept, modified, or replaced (matching 2.3).

```text
frontend/src/
  main.tsx                          keep
  App.tsx                           modify: view by hash route; auth gate kept; lazy crop, disease, settings
  styles/
    tokens.css                      new: section 15.11
    base.css                        new: body, scrollbars, focus, reduced motion, sr-only
    index.css                       replace in stages, delete at P10
    components/*.css                new, one per area
  hooks/
    useTheme.ts                     keep (export ThemeMode)
    useHashRoute.ts                 new
    useElapsed.ts                   new
    useMediaQuery.ts                new (layout decisions only)
    useConversationGroups.ts        new
    useAgentAttribution.ts          new (cache, 9.6.7)
  lib/
    api/client.ts                   modify: auth routes skip refresh (FB-1)
    api/auth.ts, sessions.ts        keep
    api/chat.ts                     modify: add sendWithProgress (XHR, same fields and headers)
    api/errors.ts                   new: mapError
    auth/AuthContext.tsx            keep
    runtime/gateway.ts              modify: remove reveal loop and routing step; no fallback agent (FB-2, FB-3, FB-4)
    runtime/thread-adapter.tsx      modify: no session on initialize (FB-5)
    runtime/attachments.ts          keep
    format/time.ts, greeting.ts     new
    content/prompts.ts              new: suggestions, crop message builder, default disease question, titles
  types/api.ts                      keep; add AgentKey alias
  components/
    layout/AppLayout.tsx            new
    layout/Sidebar.tsx              replace (from components/sidebar/Sidebar.tsx)
    layout/TopBar.tsx               new
    layout/ThemeToggle.tsx          new
    layout/UserMenu.tsx             new
    sidebar/ConversationList.tsx    replace (from ThreadList.tsx)
    sidebar/ConversationRow.tsx     new
    chat/ChatLayout.tsx             new
    chat/ChatHeader.tsx             new
    chat/ThreadView.tsx             replace (presentation of assistant-ui Thread)
    chat/ChatMessage.tsx            new
    chat/AssistantAnswer.tsx        new
    chat/MessageActions.tsx         new
    chat/MessageComposer.tsx        replace (inline Composer)
    chat/ImageChip.tsx              new
    chat/ImageLightbox.tsx          new
    chat/AgentBadge.tsx             new
    chat/AgentActivityIndicator.tsx new (pending state; optional stages prop)
    chat/AgentDetails.tsx           new
    chat/EmptyState.tsx             replace
    chat/SuggestedPrompts.tsx       new
    chat/JumpToLatest.tsx           new
    markdown/Markdown.tsx           new
    markdown/CodeBlock.tsx          new
    markdown/MarkdownTable.tsx      new
    crop/CropPage.tsx               new
    crop/CropParameterForm.tsx      new
    crop/CropFieldGroup.tsx         new
    crop/CropNumberField.tsx        new
    crop/CropRecommendationResult.tsx new
    crop/MissingInputsNotice.tsx    new
    disease/DiseasePage.tsx         new
    disease/ImageUpload.tsx         new
    disease/UploadProgress.tsx      new
    disease/DiseaseAnalysisResult.tsx new
    auth/AuthPage.tsx               replace in place
    auth/PasswordField.tsx          new
    settings/SettingsPage.tsx       new
    settings/ProfileCard.tsx, AppearanceCard.tsx, AccountCard.tsx, AboutCard.tsx   new
    dashboard/DashboardPage.tsx     new
    dashboard/WelcomeHeader.tsx, QuickStartCard.tsx, RecentList.tsx, CapabilityList.tsx, WorkSummary.tsx   new
    ui/Button.tsx, IconButton.tsx, Field.tsx, TextInput.tsx, TextArea.tsx, Dialog.tsx, ConfirmDialog.tsx,
       Menu.tsx, Disclosure.tsx, SegmentedControl.tsx, Banner.tsx, Spinner.tsx, Skeleton.tsx, StatusDot.tsx, Toast.tsx   new
    states/EmptyState.tsx, LoadingState.tsx, ErrorState.tsx   new
```

### 16.2 Component specification

| Component | Responsibility | Key props or data | Dependencies | Reusable | Status |
|---|---|---|---|---|---|
| `AppLayout` | Shell: sidebar or drawer, main region, scrim | `children`, route | `Sidebar`, `useMediaQuery` | One per app | New; replaces `.app-shell` in `App.tsx` |
| `Sidebar` | Brand, New chat, search, nav, conversation groups, user block | `collapsed`, `sessions`, `activeId`, `onNavigate` | `ConversationList`, `UserMenu`, `ThemeToggle` | Once | Replace `sidebar/Sidebar.tsx` |
| `TopBar` | Phone top bar: menu, title, actions | `title`, `onMenu`, `actions` | `IconButton` | Yes | New |
| `ThemeToggle` | Light, dark, system | `value`, `onChange`, `variant: "segmented" \| "icon"` | `SegmentedControl`, `useTheme` | Yes | New; logic from `useTheme` (kept) |
| `UserMenu` | Initial avatar, name, email; menu to Settings, theme, sign out | `user`, `onSignOut` | `Menu`, `ThemeToggle` | Yes | New |
| `ChatLayout` | Grid for header, message list, composer; owns scroll region | `header`, `children`, `composer` | — | Yes | New |
| `ChatHeader` | Sidebar toggle, editable title, meta line, ⋯ menu | `title`, `updatedAt`, `messageCount`, `isDraft`, `onRename`, `onDelete` | `Menu`, `TextInput` | Yes | New |
| `ConversationList` | Search, groups, rows | `sessions`, `activeId`, `query`, `onOpen`, `onRename`, `onDelete` | `ConversationRow`, `useConversationGroups` | Yes | Replace `ThreadList.tsx` |
| `ConversationRow` | One conversation with its actions | `session`, `active`, handlers | `IconButton`, `Menu` | Yes | New |
| `ChatMessage` | User or assistant variant | `message` (16.4) | `AssistantAnswer`, user bubble | Yes | New |
| `AssistantAnswer` | Attribution row, body, details, actions, error | `text`, `agents`, `agentResponses`, `error`, `onRetry` | `AgentBadge`, `AgentDetails`, `Markdown`, `MessageActions` | Yes | New |
| `MessageComposer` | Textarea, attach, send or stop, image chip, hint, drag target | `value`, `onSend`, `onStop`, `image`, `onImage`, `isRunning` | `TextArea`, `ImageChip`, `IconButton` | Yes | Replace inline `Composer` |
| `AgentActivityIndicator` | Pending state with elapsed time and wait notes; optional `stages` | `label`, `startedAt`, `stages?` | `useElapsed`, `Spinner` | Yes | New; renders no stages today |
| `AgentBadge` | Pill with icon, dot, label; error variant | `agent: AgentKey`, `state?: "done" \| "error"` | lucide icons | Yes | New; replaces the `agentLabels` map |
| `AgentDetails` | Disclosure with each specialist's text | `agentResponses`, `order` | `Disclosure`, `Markdown` | Yes | New |
| `ImageUpload` | Drop zone, picker, camera input, preview, remove, checks | `file`, `onFile`, `onRemove`, `accept`, `maxBytes` | `Banner` | Yes | New (disease page) |
| `ImageChip` | Composer attachment chip | `name`, `size`, `previewUrl`, `onRemove` | `IconButton` | Yes | New |
| `CropParameterForm` | Seven inputs in two groups, validation, missing summary, submit | `values`, `onChange`, `onSubmit`, `busy` | `CropFieldGroup`, `CropNumberField`, `MissingInputsNotice`, `Button` | Single use | New |
| `CropRecommendationResult` | Crop agent Markdown, submitted values, what was sent, actions | `markdown`, `submitted`, `sentText`, `sentAt`, `sessionId` | `Markdown`, `Disclosure`, `MessageActions` | Single use | New |
| `DiseaseAnalysisResult` | Disease agent Markdown with thumbnail, footer note, actions | `markdown`, `thumbnailUrl`, `sentText`, `onAnother`, `sessionId` | `Markdown`, `Disclosure` | Single use | New |
| `FertilizerAdvisory` | **Not created.** No structured fertilizer data exists (BL-11). Fertilizer answers are Markdown; tables use `MarkdownTable`. | — | — | — | Decision recorded (16.3) |
| `AgriculturalDataTable` | Implemented as `MarkdownTable` (scroll region and styles for GFM tables) | `children` | `Markdown` | Yes | New |
| `EmptyState` (chat) | Heading, subline, suggested prompts | `prompts`, `onPrompt` | `SuggestedPrompts` | Yes | Replace `chat/EmptyState.tsx` |
| `LoadingState` (generic) | Spinner, text, optional elapsed | `label`, `startedAt?` | `Spinner`, `useElapsed` | Yes | New |
| `ErrorState` (generic) | Icon, sentence, next action | `message`, `onRetry?`, `retryLabel?` | `Button` | Yes | New (chat errors use `AssistantAnswer`) |
| `Markdown` | GFM rendering with component overrides | `text`, `variant: "answer" \| "compact"` | `react-markdown`, `remark-gfm`, `CodeBlock`, `MarkdownTable` | Yes | New; replaces `MarkdownText` |
| `Dialog`, `ConfirmDialog` | Native `<dialog>`, focus return, Escape | `open`, `title`, `onClose`, `danger?` | native dialog | Yes | New (replaces `window.confirm`) |
| `Button` | Variants and sizes | `variant: primary \| secondary \| ghost \| danger`, `size: sm \| md \| lg`, `busy`, `icon` | — | Yes | New |
| `IconButton` | Icon-only button; label required | `label` (becomes `aria-label`), `size` | `Button` | Yes | New |
| `Field`, `TextInput`, `TextArea` | Label, control, helper, error, `aria-describedby` wiring | `label`, `helper`, `error`, `unit?` | — | Yes | New |
| `PasswordField` | Password with visibility toggle | `autoComplete`, `value`, `onChange`, `error` | `Field`, `IconButton` | Yes | New |
| `Menu` | Popover menu, arrow keys, Escape | `trigger`, `items` | native popover where available | Yes | New |
| `Disclosure` | Button that shows a region | `summary`, `defaultOpen` | — | Yes | New (replaces `<details>`) |
| `SegmentedControl` | Radio group styled as segments | `options`, `value`, `onChange`, `label` | — | Yes | New |
| `Banner` | Inline status with icon | `tone: info \| success \| warning \| error`, `title?`, `action?` | — | Yes | New |
| `Spinner`, `Skeleton`, `StatusDot` | Loading and status primitives | `size`, `lines`, `tone` | — | Yes | New |
| `Toast` | Status notice, auto-dismiss 4 s | `message`, `tone` | — | Yes | New |
| Dashboard parts | See 8.3 | see 8.3 | sessions API | Parts yes | New |
| Settings cards | See 14.2 | `user`, `theme` | `ThemeToggle` | Parts yes | New |
| `AuthPage` | Sign in and create account | auth context | `Field`, `PasswordField`, `Banner`, `Button` | Once | Replace in place (same export) |

### 16.3 Decisions on the suggested components

- **FertilizerAdvisory**: not created. The backend has no structured fertilizer data (BL-11). A component built for fields the backend does not send would be dead code, or would invent data.
- **AgriculturalDataTable**: implemented as `MarkdownTable`. No separate data-table component, because no structured table data is returned.
- **AgentActivityIndicator**: the pending-state component. It accepts a `stages` array that is never passed today, so it renders no stage list. The prop exists for a future backend stage event; it does not imply that one exists.
- **LoadingState and ErrorState**: generic primitives for dashboard, settings and other non-chat views. Chat uses its own states (`AgentActivityIndicator`, the error block in `AssistantAnswer`), because a chat error must sit in the message stream.
- **ImageUpload** is used by the disease page; the chat composer uses the lighter `ImageChip`.

### 16.4 Data shapes the components use

```ts
// src/types/api.ts: existing names kept; one alias added
export type AgentKey = "crop_agent" | "disease_agent" | "general_agent";

// UI message model, built from the POST response or from history
export interface UiAssistantMessage {
  id: string;
  role: "assistant";
  text: string;                              // response (POST) or content (history)
  agents: AgentKey[];                        // selected_agents (POST), attribution cache (history), [] when unknown
  agentResponses: Record<string, string>;    // POST only; empty after reload
  error?: { kind: "retryable" | "fatal"; message: string };
  sentAt?: string;                           // ISO; only for messages sent in this session
}
export interface UiUserMessage {
  id: string;
  role: "user";
  text: string;
  image?: { name: string; size: number; previewUrl: string; dataUrl?: string };
  sentAt?: string;
}
```

### 16.5 Keep, change, remove in the chat code

- Keep the assistant-ui primitives: `ThreadPrimitive`, `MessagePrimitive`, `ComposerPrimitive`, `ActionBarPrimitive`, `ThreadListPrimitive`, `ThreadListItemPrimitive`, `ErrorPrimitive`, `useAui`, `useAuiState`. Their behaviour (send, cancel, attachments, suggestions, scroll, remote thread list) is why the library stays.
- Remove from `Thread.tsx`: `ChainOfThought` (its "Researching" label is not backed by any event), `ActivityTool` (its labels differ from the agreed names and it shows raw agent text as "Findings"), `ActivityReasoning` (returns null), and the Reload action on successful messages (BL-9).
- Remove from `gateway.ts`: the `routing` tool call, the 24-character reveal loop, the `general_agent` fallback.

### 16.6 Hooks and helpers

| Name | Contract |
|---|---|
| `useHashRoute()` | Returns `{ route, navigate }`. Parses `#/home`, `#/chat`, `#/chat/:id`, `#/crop`, `#/disease`, `#/settings`. Unknown → `#/home`. Listens to `hashchange`. |
| `useElapsed(start)` | Whole seconds since `start`, updated each second; pauses while `document.hidden`; 0 when `start` is null. |
| `useMediaQuery(query)` | `matchMedia` subscription, used for layout decisions only. |
| `useConversationGroups(sessions, now)` | Groups by local day of `updatedAt`: Today, Yesterday, Previous 7 days, Older. Empty groups omitted. |
| `mapError(status, code, serverMessage, ctx)` | `ctx`: `auth`, `chat`, `crop`, `disease`, `sessions`. Returns a user sentence from 7.4, 9.9, 10.9, 11.7. Never returns server text for 5xx. Returns server text only for the two known image sentences (9.9). |
| `sendWithProgress(form, onProgress, signal)` | XHR POST to `/api/chat`, same fields and bearer header; resolves to the parsed `ChatResponse` or throws `ApiError`; 401 uses the same refresh path as `client.ts`. |
| `attributionCache` | `get(sessionId, index)`, `set(sessionId, index, { agents, keys })`, `clear()`. Key `cropsage.attribution.v1`. |

### 16.7 Content helpers (`content/prompts.ts`)

- Suggestion texts (9.11) and topic starters (12.2).
- The crop message builder (10.5): values as typed, fixed unit strings, no rounding, no defaults.
- The disease default question (11.5).
- Title builders: first 42 characters of the first message; "Crop recommendation · Nov 7"; "Plant photo · Nov 7".

### 16.8 Where the existing files go

| Existing | New home | Change |
|---|---|---|
| `components/auth/AuthPage.tsx` | same path | Markup and copy replaced; logic kept |
| `components/sidebar/Sidebar.tsx` | `components/layout/Sidebar.tsx` | Rewritten |
| `components/sidebar/ThreadList.tsx` | `components/sidebar/ConversationList.tsx` and `ConversationRow.tsx` | Rewritten; `window.confirm` removed |
| `components/chat/ChatWorkspace.tsx` | `components/chat/ChatLayout.tsx` and `ChatHeader.tsx` | Rewritten |
| `components/chat/EmptyState.tsx` | same path, uses `SuggestedPrompts` | Icons and prompts changed |
| `components/assistant-ui/Thread.tsx` | split into `ThreadView`, `ChatMessage`, `AssistantAnswer`, `MessageComposer`, `Markdown`, `AgentBadge`, `AgentDetails` | Primitives kept; presentation replaced |
| `hooks/useTheme.ts` | same path | Kept |
| `lib/runtime/gateway.ts` | same path | Adapter kept; reveal and routing removed |
| `lib/runtime/thread-adapter.tsx` | same path | No session on initialize |
| `lib/runtime/attachments.ts` | same path | Kept |
| `lib/api/*` | same paths | Kept; `errors.ts` and `sendWithProgress` added |
| `styles/index.css` | `tokens.css` plus component stylesheets | Staged (21.3) |

---

## 17. Interaction and Animation Guidelines

### 17.1 Principles

- Motion explains a change: something appeared, moved, or left. It never decorates.
- Short durations: 120 ms for feedback, 180 ms for appearance, 240 ms for large movement.
- Only `transform` and `opacity` animate. No layout animation on message text.
- Reduced motion removes translation and scale; opacity changes stay at 120 ms or less; spinners become static icons with a slow opacity pulse.

### 17.2 Motion inventory

| Moment | Motion | Duration and easing | Reduced motion |
|---|---|---|---|
| Hover on button or row | Background colour | 120 ms `--ease-out` | Same (colour) |
| Press | Pressed background; no scale | 120 ms | Same |
| Focus ring | Outline appears | 0 ms | Same |
| New assistant answer | Opacity 0 → 1 and translateY 4 px → 0 | 180 ms `--ease-out` | Opacity only, 120 ms |
| New user message | Opacity 0 → 1 | 120 ms | Same |
| History on open | None | — | — |
| Spinner | Rotate, 1 s per turn, linear, infinite | 1 s | Static icon with opacity pulse, 2 s |
| Skeleton | Sweep, 1.4 s | — | Disabled (static grey) |
| Indeterminate upload bar | 30% segment slides across | 1.4 s ease-in-out | Static bar at 40% opacity |
| Determinate upload bar | Width | 120 ms linear | Same |
| Menu or popover | Opacity 0 → 1, translateY −4 px → 0 | 180 ms `--ease-out` | Opacity only |
| Dialog open | Opacity; scale 0.98 → 1 | 180 ms `--ease-out` | Opacity only |
| Dialog close | Opacity to 0 | 120 ms `--ease-in` | Same |
| Drawer open (phone) | Slide in from left | 240 ms `--ease-out` | Instant |
| Drawer scrim | Opacity to `--color-scrim` | 240 ms | Opacity, 120 ms |
| Sidebar collapse (desktop) | Width 268 px → 60 px | 240 ms `--ease-in-out` | Instant |
| View change | Cross-fade | 160 ms | Instant |
| Sign-in success | Card fades out; shell fades in | 160 ms, then 180 ms | Instant |
| Toast | Opacity and translateY 8 px → 0 in; out at 4 s | 180 ms in, 120 ms out | Opacity only |
| Drag-over drop zone | Border and background | 120 ms | Same (colour) |
| Jump-to-latest pill | Opacity and translateY 8 px → 0 | 180 ms | Opacity only |
| Dashboard cards on first load | Opacity; 4 px rise; 40 ms stagger | 160 ms | Opacity only, no stagger |

### 17.3 State rules per control

| Control | Default | Hover | Pressed | Focus-visible | Disabled | Loading |
|---|---|---|---|---|---|---|
| Primary button | Fill `--color-accent`, text `--color-accent-on` | `--color-accent-hover` | `--color-accent-pressed` | 2 px ring, offset 2 px | Opacity 0.45, `aria-disabled` | Spinner replaces leading icon; label changes ("Signing in…") |
| Secondary button | Surface, 1 px `--color-border-strong`, text primary | Sunken fill | Sunken fill, border secondary | Ring | Opacity 0.45 | Spinner |
| Ghost button | Transparent, text secondary | Sunken fill | Border fill | Ring | Opacity 0.45 | Spinner |
| Danger button | Fill `--color-error`, text `--color-error-on` | `--color-error-hover` | Hover fill, one step darker | Ring | Opacity 0.45 | Spinner |
| Icon button | Transparent | Sunken fill | Border fill | Ring | Opacity 0.45 | Spinner in place of icon |
| Text input | Surface, 1 px `--color-control-border` | Border `--color-text-tertiary` | — | Border `--color-accent` and ring | Sunken fill, text disabled, border `--color-border` | — |
| Input invalid | Border `--color-error` | — | — | Ring in error colour | — | — |
| Sidebar row | Transparent | Sunken fill | Sunken fill | Ring | — | — |
| Sidebar row active | Surface, `--shadow-xs`, text primary | — | — | Ring | — | — |
| Suggestion chip | Surface, 1 px border | Sunken fill | Sunken fill | Ring | Opacity 0.45 | — |
| Interactive card | Surface, 1 px border | Border-strong and `--shadow-sm` | Border-strong | Ring | — | — |
| Send button | Accent circle, arrow | Accent hover | Accent pressed | Ring | Opacity 0.45 (no text and no image) | Replaced by Stop while running |
| Segmented option | Text secondary | Text primary | — | Ring | Opacity 0.45 | — |

### 17.4 Scrolling and layout

- Smooth scroll to the newest message only for the jump pill and after the user sends. Opening a conversation sets the position instantly.
- Textarea growth is immediate, so the composer does not jitter.

### 17.5 Things to remove

- The 24-character reveal loop and its 14 ms timer (`gateway.ts`).
- The chain-of-thought accordion and its `chain-in` animation.
- The `breathe` keyframe on the empty-state glyph. The empty state is static.

### 17.6 Theme on first paint

Add to `index.html` `<head>`, before the stylesheets:

```html
<script>
  (function () {
    try {
      var saved = localStorage.getItem("agrimind.theme");
      var mode = saved === "light" || saved === "dark" || saved === "system" ? saved : "system";
      var dark = mode === "dark" || (mode === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
      document.documentElement.classList.toggle("dark", dark);
      document.documentElement.dataset.theme = mode;
      document.documentElement.style.colorScheme = dark ? "dark" : "light";
    } catch (e) {}
  })();
</script>
```

The storage key stays `agrimind.theme`. Renaming it would reset saved themes.

### 17.7 Presence

No typing indicator and no stage ticker. The pending state (9.8) is the only presence signal, and it is honest about elapsed time.

## 18. Responsive Design Specifications

### 18.1 Breakpoint behaviour

| Range | Device | Sidebar | Main and chat | Crop | Disease | Dashboard |
|---|---|---|---|---|---|---|
| 0 to 639 px | Phone | Drawer (min 86vw, max 320 px) from the top bar | Full width, 16 px padding | One column; submit in a sticky bottom bar | One column; "Analyse photo" sticky at the bottom | One column; quick start as a horizontal snap row |
| 640 to 767 px | Large phone, landscape | Drawer | Full width, 24 px padding | One column | One column | Two columns for quick start |
| 768 to 1023 px | Tablet | Rail (60 px); expands as an overlay | 760 px column, centred | Form full width; seven fields in two columns; result below | Photo and result stacked | Three quick-start columns; recent and capabilities stacked |
| 1024 to 1279 px | Laptop | Expanded (268 px) | 760 px column, centred, 32 px padding | Two columns: form 420 px, result fluid | Two columns: photo 400 px, result fluid | Three columns; recent and capabilities side by side |
| 1280 px and up | Desktop | Expanded (268 px) | As laptop | Two columns | Two columns | As laptop |

### 18.2 Sidebar behaviour

- **Desktop**: expanded by default. A collapse button (`PanelLeft`, 32 px) sits in the sidebar header. The collapsed state is saved under `cropsage.sidebar.v1`. Collapsing animates the width (240 ms).
- **Tablet**: the 60 px rail shows icons only, with a visible tooltip on focus and hover. Expanding overlays the content with a scrim.
- **Phone**: a drawer, opened from the top-bar menu button. Focus moves to the first focusable element on open and returns to the menu button on close. Escape and a scrim tap close it. The page does not scroll while it is open. Choosing a conversation closes it.

### 18.3 Chat on each device

- **Phone**: header 56 px with the menu button, a one-line title, and the ⋯ menu. Messages full width. Assistant text 16/26 px. User bubble up to 88% of the width. The composer is pinned to the bottom with `padding-bottom: max(12px, env(safe-area-inset-bottom))`.
- **Tablet and desktop**: a centred 760 px column; the composer sits in the same column.
- The message list is the only scroll region. The page itself does not scroll: `body { overflow: hidden }` is kept and the chat grid uses `height: 100dvh` with `100vh` as fallback.

### 18.4 Composer on phone

- Textarea 16 px (no iOS focus zoom); 15 px on desktop.
- Attach and send buttons 44 px on phone, 36 px on desktop.
- Keeping the composer above the on-screen keyboard: use `visualViewport` height where the browser does not resize the layout viewport (iOS Safari). Fallback to `100dvh`.

### 18.5 Forms

- Phone inputs 44 px tall, 16 px font, label above, helper below, error below the helper (`role="alert"` on the error text only, not on the helper).
- Crop form: one column on phone with 16 px between fields; two columns on tablet (Soil and Climate side by side); single column in the 420 px form column on desktop.
- The "Missing:" line and the submit button sit inside the sticky bottom bar on phone.

### 18.6 Tables, code and long content

- Markdown tables: a horizontal scroll region with `tabindex="0"`, a thin visible scrollbar, text never below 13 px.
- Code blocks: horizontal scroll, never wrap.
- Long words and URLs in paragraph text: `overflow-wrap: anywhere` (not in code).

### 18.7 Disease image uploads

- Phone: photo area full width; when empty, "Choose photo" and "Take photo" side by side (48 px tall); preview at most 280 px high, `object-fit: contain`.
- Tablet and desktop: drop zone 220 px tall; preview at most 360 px high.
- The upload progress bar is full width under the preview.

### 18.8 Dashboard cards

- Quick start: three cards on desktop; on phone a horizontal scroll-snap row with each card 80% of the width and 12 px gap.
- Recent list rows: 44 px on phone, 40 px on desktop.
- Capabilities: stacked rows on phone; side column on desktop.

### 18.9 Safe areas and viewport

- Full-height layouts use `100dvh` with `100vh` as fallback in the same rule.
- `env(safe-area-inset-*)` applies to the top bar, composer, sticky bars and the drawer.
- The viewport meta stays `width=device-width, initial-scale=1.0`. Pinch zoom is not disabled.

### 18.10 Text scaling

Layouts reflow at 200% text size and at 320 CSS px width without horizontal scrolling in main content. Tables and code scroll inside their own region.

---

## 19. Accessibility Guidelines

Target: WCAG 2.2 Level AA. The ratios below were computed from the exact hex values in section 15.2 with the WCAG 2.x formula: relative luminance, then (L1 + 0.05) / (L2 + 0.05). Thresholds: normal text 4.5:1; large text 3:1; non-text UI boundaries and focus indicators 3:1 where they identify a control.

### 19.1 Computed contrast table

Every pairing the UI uses. "exempt" rows are shown for transparency; they never carry information on their own.

| Theme | Foreground | FG hex | Background | BG hex | Ratio | Needed | Result | Used for |
|---|---|---|---|---|---|---|---|---|
| light | `text_primary` | #15171C | `canvas` | #F7F7F8 | 16.75:1 | 4.5:1 | PASS | body text |
| light | `text_primary` | #15171C | `surface` | #FFFFFF | 17.93:1 | 4.5:1 | PASS | body text on cards |
| light | `text_primary` | #15171C | `bubble_user` | #EEF0F3 | 15.70:1 | 4.5:1 | PASS | user bubble text |
| light | `text_secondary` | #4A5160 | `canvas` | #F7F7F8 | 7.44:1 | 4.5:1 | PASS | secondary text |
| light | `text_secondary` | #4A5160 | `sidebar` | #F1F2F4 | 7.11:1 | 4.5:1 | PASS | sidebar item text |
| light | `text_secondary` | #4A5160 | `surface` | #FFFFFF | 7.96:1 | 4.5:1 | PASS | secondary on card |
| light | `text_tertiary` | #5E6777 | `canvas` | #F7F7F8 | 5.33:1 | 4.5:1 | PASS | meta / timestamps |
| light | `text_tertiary` | #5E6777 | `surface` | #FFFFFF | 5.70:1 | 4.5:1 | PASS | meta on card |
| light | `text_tertiary` | #5E6777 | `sunken` | #EEF0F3 | 5.00:1 | 4.5:1 | PASS | meta on sunken/code |
| light | `text_tertiary` | #5E6777 | `sidebar` | #F1F2F4 | 5.09:1 | 4.5:1 | PASS | section labels |
| light | `text_tertiary` | #5E6777 | `bubble_user` | #EEF0F3 | 5.00:1 | 4.5:1 | PASS | meta on user bubble |
| light | `accent_on` | #FFFFFF | `accent` | #0F6B66 | 6.33:1 | 4.5:1 | PASS | primary button text |
| light | `accent_on` | #FFFFFF | `accent_hover` | #0B5652 | 8.51:1 | 4.5:1 | PASS | hover state text |
| light | `accent_on` | #FFFFFF | `accent_pressed` | #094744 | 10.52:1 | 4.5:1 | PASS | pressed state text |
| light | `accent` | #0F6B66 | `surface` | #FFFFFF | 6.33:1 | 4.5:1 | PASS | accent text / links |
| light | `accent` | #0F6B66 | `canvas` | #F7F7F8 | 5.92:1 | 4.5:1 | PASS | accent text on canvas |
| light | `accent` | #0F6B66 | `accent_subtle` | #E3F1F0 | 5.46:1 | 4.5:1 | PASS | accent text on tint |
| light | `accent` | #0F6B66 | `sidebar` | #F1F2F4 | 5.65:1 | 4.5:1 | PASS | active nav text |
| light | `error` | #B42318 | `surface` | #FFFFFF | 6.57:1 | 4.5:1 | PASS | error text |
| light | `error` | #B42318 | `error_subtle` | #FDEBE9 | 5.71:1 | 4.5:1 | PASS | error banner |
| light | `success` | #11703F | `surface` | #FFFFFF | 6.15:1 | 4.5:1 | PASS | success text |
| light | `success` | #11703F | `success_subtle` | #E6F4EC | 5.42:1 | 4.5:1 | PASS | success banner |
| light | `warning` | #8A4B00 | `surface` | #FFFFFF | 6.80:1 | 4.5:1 | PASS | warning text |
| light | `warning` | #8A4B00 | `warning_subtle` | #FDF3E2 | 6.19:1 | 4.5:1 | PASS | warning banner |
| light | `info` | #1D5CA8 | `surface` | #FFFFFF | 6.67:1 | 4.5:1 | PASS | info text |
| light | `info` | #1D5CA8 | `info_subtle` | #E8F0FA | 5.80:1 | 4.5:1 | PASS | info banner |
| light | `agent_disease` | #7A3E8C | `surface` | #FFFFFF | 7.25:1 | 4.5:1 | PASS | agent badge |
| light | `agent_general` | #2F5C9E | `surface` | #FFFFFF | 6.68:1 | 4.5:1 | PASS | agent badge |
| light | `agent_crop` | #0F6B66 | `surface` | #FFFFFF | 6.33:1 | 4.5:1 | PASS | agent badge |
| light | `agent_supervisor` | #4A5160 | `surface` | #FFFFFF | 7.96:1 | 4.5:1 | PASS | agent badge |
| light | `control_border` | #7D8698 | `surface` | #FFFFFF | 3.66:1 | 3.0:1 | PASS | input boundary (1.4.11) |
| light | `control_border` | #7D8698 | `canvas` | #F7F7F8 | 3.42:1 | 3.0:1 | PASS | input boundary on canvas |
| light | `accent` | #0F6B66 | `canvas` | #F7F7F8 | 5.92:1 | 3.0:1 | PASS | focus ring vs canvas |
| light | `accent` | #0F6B66 | `surface` | #FFFFFF | 6.33:1 | 3.0:1 | PASS | focus ring vs card |
| light | `text_disabled` | #98A2B3 | `surface` | #FFFFFF | 2.58:1 | - | exempt | disabled (exempt) |
| light | `border_strong` | #C9CED6 | `surface` | #FFFFFF | 1.58:1 | - | exempt | decorative divider (exempt) |
| light | `error_on` | #FFFFFF | `error` | #B42318 | 6.57:1 | 4.5:1 | PASS | danger button text |
| light | `error_on` | #FFFFFF | `error_hover` | #9F1F15 | 7.83:1 | 4.5:1 | PASS | danger hover text |
| dark | `text_primary` | #ECEEF2 | `canvas` | #101215 | 16.15:1 | 4.5:1 | PASS | body text |
| dark | `text_primary` | #ECEEF2 | `surface` | #16191D | 15.18:1 | 4.5:1 | PASS | body text on cards |
| dark | `text_primary` | #ECEEF2 | `bubble_user` | #1A1E24 | 14.40:1 | 4.5:1 | PASS | user bubble text |
| dark | `text_secondary` | #A9B0BC | `canvas` | #101215 | 8.60:1 | 4.5:1 | PASS | secondary text |
| dark | `text_secondary` | #A9B0BC | `sidebar` | #0C0E11 | 8.86:1 | 4.5:1 | PASS | sidebar item text |
| dark | `text_secondary` | #A9B0BC | `surface` | #16191D | 8.08:1 | 4.5:1 | PASS | secondary on card |
| dark | `text_tertiary` | #7F8794 | `canvas` | #101215 | 5.18:1 | 4.5:1 | PASS | meta / timestamps |
| dark | `text_tertiary` | #7F8794 | `surface` | #16191D | 4.87:1 | 4.5:1 | PASS | meta on card |
| dark | `text_tertiary` | #7F8794 | `sunken` | #0B0D10 | 5.37:1 | 4.5:1 | PASS | meta on sunken/code |
| dark | `text_tertiary` | #7F8794 | `sidebar` | #0C0E11 | 5.33:1 | 4.5:1 | PASS | section labels |
| dark | `text_tertiary` | #7F8794 | `bubble_user` | #1A1E24 | 4.62:1 | 4.5:1 | PASS | meta on user bubble |
| dark | `accent_on` | #06201E | `accent` | #5FC2B9 | 8.03:1 | 4.5:1 | PASS | primary button text |
| dark | `accent_on` | #06201E | `accent_hover` | #7AD3CB | 9.74:1 | 4.5:1 | PASS | hover state text |
| dark | `accent_on` | #06201E | `accent_pressed` | #4FB0A7 | 6.57:1 | 4.5:1 | PASS | pressed state text |
| dark | `accent` | #5FC2B9 | `surface` | #16191D | 8.32:1 | 4.5:1 | PASS | accent text / links |
| dark | `accent` | #5FC2B9 | `canvas` | #101215 | 8.85:1 | 4.5:1 | PASS | accent text on canvas |
| dark | `accent` | #5FC2B9 | `accent_subtle` | #15302E | 6.63:1 | 4.5:1 | PASS | accent text on tint |
| dark | `accent` | #5FC2B9 | `sidebar` | #0C0E11 | 9.12:1 | 4.5:1 | PASS | active nav text |
| dark | `error` | #F2877F | `surface` | #16191D | 7.18:1 | 4.5:1 | PASS | error text |
| dark | `error` | #F2877F | `error_subtle` | #2E1A19 | 6.69:1 | 4.5:1 | PASS | error banner |
| dark | `success` | #4CC38A | `surface` | #16191D | 7.96:1 | 4.5:1 | PASS | success text |
| dark | `success` | #4CC38A | `success_subtle` | #12281E | 7.03:1 | 4.5:1 | PASS | success banner |
| dark | `warning` | #E9B45E | `surface` | #16191D | 9.37:1 | 4.5:1 | PASS | warning text |
| dark | `warning` | #E9B45E | `warning_subtle` | #2B2214 | 8.31:1 | 4.5:1 | PASS | warning banner |
| dark | `info` | #7DB3F2 | `surface` | #16191D | 8.06:1 | 4.5:1 | PASS | info text |
| dark | `info` | #7DB3F2 | `info_subtle` | #14202F | 7.52:1 | 4.5:1 | PASS | info banner |
| dark | `agent_disease` | #C49AD6 | `surface` | #16191D | 7.51:1 | 4.5:1 | PASS | agent badge |
| dark | `agent_general` | #8DB3EA | `surface` | #16191D | 8.20:1 | 4.5:1 | PASS | agent badge |
| dark | `agent_crop` | #5FC2B9 | `surface` | #16191D | 8.32:1 | 4.5:1 | PASS | agent badge |
| dark | `agent_supervisor` | #A9B0BC | `surface` | #16191D | 8.08:1 | 4.5:1 | PASS | agent badge |
| dark | `control_border` | #737B8A | `surface` | #16191D | 4.14:1 | 3.0:1 | PASS | input boundary (1.4.11) |
| dark | `control_border` | #737B8A | `canvas` | #101215 | 4.40:1 | 3.0:1 | PASS | input boundary on canvas |
| dark | `accent` | #5FC2B9 | `canvas` | #101215 | 8.85:1 | 3.0:1 | PASS | focus ring vs canvas |
| dark | `accent` | #5FC2B9 | `surface` | #16191D | 8.32:1 | 3.0:1 | PASS | focus ring vs card |
| dark | `text_disabled` | #5C6470 | `surface` | #16191D | 2.95:1 | - | exempt | disabled (exempt) |
| dark | `border_strong` | #3A414B | `surface` | #16191D | 1.71:1 | - | exempt | decorative divider (exempt) |
| dark | `error_on` | #101215 | `error` | #F2877F | 7.64:1 | 4.5:1 | PASS | danger button text |
| dark | `error_on` | #101215 | `error_hover` | #E36F67 | 6.02:1 | 4.5:1 | PASS | danger hover text |

What the calculation changed:

- The first dark `bubble-user` draft (`#1F2329`) gave 4.36:1 for tertiary text; it became `#1A1E24` (4.62:1).
- The first input border draft (`#8A93A3`) gave 3.10:1 on white; the final `#7D8698` gives 3.66:1 on white and 3.42:1 on the canvas.
- Disabled text (2.58:1 light, 2.95:1 dark) and decorative dividers are exempt. Disabled state is also marked by the `disabled` attribute and opacity, not by colour alone.
- Accent hover (`#0B5652`) is a fill with white text (8.51:1), never text on white.

### 19.2 Colour is never the only signal

- Agent badges carry a text label and an icon. The dot is decorative.
- Errors carry an icon and words, not only red text.
- Missing required inputs are named in words in the missing summary.
- Selected segments and active nav items change weight and shadow as well as colour.

### 19.3 Keyboard map

| Area | Keys |
|---|---|
| Whole app | Tab and Shift+Tab move through visible controls in visual order; Escape closes menus, dialogs, drawer and lightbox |
| Skip link | First Tab on any view: "Skip to conversation" (phone: "Skip to content") |
| Conversation list | Tab enters the list; ArrowUp and ArrowDown move between rows (roving tabindex); Enter opens |
| Row menu | Enter or Space on ⋯ opens; arrows move; Enter activates; Escape closes and returns focus |
| Composer | Enter sends; Shift+Enter newline; Tab goes attach, then send |
| Message actions | Tab reaches Copy (and Retry after an error) on the active answer |
| Crop form | Tab moves field to field in order; Enter inside a field does not submit; the button submits when focused and enabled |
| Disease drop zone | Enter or Space opens the picker |
| Segmented controls | Arrow keys move and select |
| Dialogs | Focus moves to the first action (Cancel for destructive); Tab cycles inside; Escape closes and returns focus to the trigger |
| Jump to latest | Reachable by Tab; Enter scrolls |

Shortcut: Ctrl/⌘ + Shift + O starts a new chat (listed in Settings).

### 19.4 Screen readers

- Landmarks: `header` (top bar), `nav` (sidebar), `main` (view). The composer is a `form` named "Message".
- One `h1` per view. Sections use `h2`. Answer headings in crop and disease results start at `h3`, keeping the outline valid.
- A polite status region announces "Answer ready" and errors (9.14). The pending text is not a live region (it would announce every second).
- Icon-only buttons always carry a label; `IconButton` requires the prop.
- Photo thumbnails carry `alt`: the file name for chat attachments; "Photo you uploaded" for result thumbnails.
- Tables carry a caption from the nearest heading, or "Table".
- The attribution row is a paragraph with the badge names as text, so it reads "Answered by Crop Recommendation".

### 19.5 Forms

- Every control has a visible label. Placeholders never replace labels.
- Helper and error text are linked with `aria-describedby`; invalid fields set `aria-invalid="true"`.
- Required fields are marked in the label or with `aria-required="true"`, and the missing summary names them.
- Autocomplete tokens are set on auth fields (`email`, `current-password`, `new-password`).
- Validation errors are announced once, on submit, not on each keystroke.

### 19.6 Motion, text and zoom

- Reduced motion honoured everywhere (17.1).
- Text up to 200% without loss; reflow per 18.10.
- Touch targets 44 px on phone and tablet. On desktop, icon-only controls in dense rows are at least 24 px, and the whole row remains clickable.

### 19.7 Language and content

- `<html lang="en">` (already set).
- Sentence case, short sentences, no internal terms in user text (section 5, rule 8).
- Dates as words for the user ("Nov 7"); full timestamp in a `title` attribute on desktop hover.

---

## 20. Existing Backend Integration Requirements

### 20.1 Base, transport and auth

- Base URL: `import.meta.env.VITE_API_BASE_URL`, default `http://localhost:3001` (`client.ts`), trailing slash removed.
- JSON for everything except chat, which is `multipart/form-data`.
- `Authorization: Bearer <accessToken>` on everything except register, login and refresh.
- Refresh: on 401 for a non-auth route, `POST /api/auth/refresh` once (de-duplicated). If it fails, clear tokens and return to sign-in with the session notice.
- The frontend sets no client timeout on chat. The gateway calls the agent backend with a 60 s timeout and answers 504 `AI_SERVICE_TIMEOUT` when it expires (`fastapi.service.js`, line 8 and line 48). See BL-18.
- No CORS or security-header changes are part of this design. The gateway's `FRONTEND_ORIGIN` must include the Vite origin (README).

### 20.2 Endpoints (from source)

| Method and path | Auth | Request | Success | Errors the UI maps | Source |
|---|---|---|---|---|---|
| `POST /api/auth/register` | none | JSON `{ email, password }` (valid email; password at least 8 characters) | `201` `{ status: "success", message: "Registration successful" }` | `400` `VALIDATION_ERROR` (includes "Email is already registered") · `429` `RATE_LIMIT_EXCEEDED` · `503` `SERVICE_UNAVAILABLE` | `auth.routes.js`, `auth.controller.js` |
| `POST /api/auth/login` | none | JSON `{ email, password }` | `200` `{ accessToken, refreshToken }` | `401` `AUTHENTICATION_FAILED` "Invalid email or password" · `400` · `429` · `503` | `auth.controller.js` |
| `POST /api/auth/refresh` | none | JSON `{ refreshToken }` | `200` `{ accessToken, refreshToken }` (rotated) | `401` `AUTHENTICATION_FAILED`: "Invalid refresh token", "Token has been revoked", "Refresh token expired", "User is inactive" | `auth.controller.js` |
| `POST /api/auth/logout` | Bearer | JSON `{ refreshToken }` (optional) | `200` `{ status: "success", message: "Logged out successfully" }` | `401` | `auth.controller.js` |
| `GET /api/auth/me` | Bearer | — | `200` `{ id, email, createdAt, isActive }` | `401` | `auth.controller.js` |
| `GET /api/sessions` | Bearer | — | `200` `Session[]`, newest `updatedAt` first | `401` | `session.controller.js` |
| `POST /api/sessions` | Bearer | JSON `{ title }` (required, non-empty) | `201` `Session` | `400` `VALIDATION_ERROR` | `session.controller.js` |
| `GET /api/sessions/:id` | Bearer | — | `200` `Session` | `404` `NOT_FOUND` · `403` `AUTHORIZATION_FAILED` | `session.controller.js` |
| `PATCH /api/sessions/:id` | Bearer | JSON `{ title }` (required) | `200` `Session` | `400` · `404` · `403` | `session.controller.js` |
| `DELETE /api/sessions/:id` | Bearer | — | `200` `{ status: "success", message: "Session deleted" }` | `404` · `403` | `session.controller.js` |
| `GET /api/chat/:session_id` | Bearer | — | `200` `{ session_id, messages: ChatMessage[] }` | `404` · `403` · `500` | `chat.controller.js`, `routes.py` `get_chat_history` |
| `POST /api/chat` | Bearer | multipart: `query` (required), `session_id` (required), `file` (optional, one image) | `200` `ChatResponse` | `400` `VALIDATION_ERROR` ("Query is required", "Session ID is required", "Only images are allowed", image messages) · `404` · `413` `PAYLOAD_TOO_LARGE` · `429` · `502` `AI_SERVICE_UNAVAILABLE` · `504` `AI_SERVICE_TIMEOUT` · `500` (forwarded text, BL-8) | `chat.routes.js`, `chat.controller.js`, `fastapi.service.js`, `routes.py` `chat_endpoint` |

Response types (from `src/types/api.ts`, checked against what the server returns):

```ts
interface User { id: string; email: string; createdAt: string; isActive: boolean }
interface AuthTokens { accessToken: string; refreshToken: string }
interface Session { id: string; title: string; userId: string; createdAt: string; updatedAt: string }
interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  image?: { data_url: string; filename: string; content_type: string; size: number };
}
interface ChatHistory { session_id: string; messages: ChatMessage[] }
interface ChatResponse {
  status: "success";
  query: string;
  response: string;                         // the text the UI shows
  session_id: string;
  selected_agents: AgentName[];             // [] for declined questions
  agent_responses: Record<string, string>;  // per-agent text; a value may start with "Agent error:"
}
type AgentName = "disease_agent" | "crop_agent" | "general_agent";
```

Error body the UI reads: `error.code`, `error.message`, `error.details` (zod issues). `detail` and `message` at the top level are legacy fallbacks.

### 20.3 Request composition (frontend-owned)

| Use | Fields | Rule |
|---|---|---|
| General chat | `query`, `session_id` | Trimmed. An empty message with no image is not sent. |
| Chat with a photo | `query` (the note, or the default question in 11.5), `session_id`, `file` | The picked file is sent under its own name. |
| Crop recommendation | `query` (the message in 10.5), `session_id` | No `file`. All seven values appear in the text. |
| Session create | `title` | First 42 characters of the first message, or the crop or photo title pattern. Never empty. |
| Rename | `title` | Trimmed; empty becomes "New conversation" (existing rule). |

### 20.4 Backend limitations that constrain the UI

Each item is a fact read in source. None is a request to change the backend in this task.

| ID | What is true | Source | UI consequence |
|---|---|---|---|
| BL-1 | No streaming and no stage events. The chat route runs `graph.ainvoke` and returns one JSON when it finishes. | `routes.py` `chat_endpoint`; `chat.controller.js` | No token streaming, no stage list, no "routing" label. Pending state with elapsed time (9.8). Upload progress is real only during upload (11.4). |
| BL-2 | Crop output is one crop label inside Markdown text. The crop agent calls `predict` (one label) rather than probabilities; the structured `crop_result` stays in graph state and is not in the response. | `services/crop_model.py` `predict_crop`; `agents/crop/graph.py`; `graph/main_graph.py` `run_agents` | No top-N list, probabilities, confidence or crop-name field. Result shows Markdown (10.7). |
| BL-3 | Crop parameters are extracted from free text by an LLM. Missing values fall back to `N=0, P=0, K=0, temperature=25, humidity=60, ph=6.5, rainfall=100`. The response does not echo the values used. | `graph/main_graph.py` `CropParamsExtraction` and its system prompt | Required fields (10.4). The message states all seven values with units (10.5). The result says "Values you submitted" (10.7). The UI cannot prove the model used those values. |
| BL-4 | Disease confidence, canonical label and top predictions are computed internally but the chat route does not return them. Only text comes back. | `services/disease_detection/schemas.py`; `routes.py` | No confidence, label or top-3 in the UI. Markdown only (11.6). |
| BL-5 | `selected_agents` and `agent_responses` come back on `POST` only. History returns role, content and image. | `routes.py` `get_chat_history` | Attribution cache in `localStorage` (9.6.7). No badge when the cache has no entry. |
| BL-6 | History messages have no timestamps. | `routes.py` `get_chat_history` | Times only for messages sent in this session (9.5). |
| BL-7 | Session `updatedAt` changes on `PATCH` only. The chat handler does not write the session row. | `session.controller.js` `updateSession`; `chat.controller.js` | Label "Updated {date}"; never "last message" (13.2). |
| BL-8 | 5xx messages can carry internal text. The gateway forwards FastAPI `detail` (for example "Graph execution failed: …"); zod errors return the generic "Invalid request data". | `fastapi.service.js`; `routes.py` `HTTPException`; `error.middleware.js` | `mapError` never shows 5xx server text (9.9, 7.4). |
| BL-9 | No feedback, regenerate or delete-message endpoint. Each `POST /api/chat` appends a user and an assistant message to the checkpoint. | `routes.py` `initial_state`; `graph/state.py` `add_messages` | No feedback control shipped (9.5). No Regenerate on success. Retry only before a response, never automatic (9.9). |
| BL-10 | Partial context. The supervisor sees the last 6 messages; specialists see only the current (sanitised) question. | `graph/main_graph.py` `classify_and_route` (`messages[-7:-1]`) and `run_agents` | Copy makes no memory promise. Tip to restate crop and stage (12.5). |
| BL-11 | No sources, citations, or structured fertilizer or nutrient data. | Whole response contract | No source row, no nutrient gauges, no FertilizerAdvisory (16.3). |
| BL-12 | The user object is email, id, createdAt and isActive. No name, avatar, preferences, password change or email change. | `auth.controller.js` `getMe` | Display name from the email local-part; no password or email change UI (14.4). |
| BL-13 | Declined questions return `selected_agents: []` and a refusal text. | `graph/main_graph.py` `run_agents` (invalid branch) | No badge on declined answers (9.6.3). The old `general_agent` fallback is removed (FB-2). |
| BL-14 | Rate limits: chat 30 per minute per user; image 10 per minute per user; login 10 per 15 minutes per IP; register 5 per hour per IP. 429 body `RATE_LIMIT_EXCEEDED`. | `env.js`; `rateLimit.middleware.js` | Message "You're sending messages quickly…" (9.9). No automatic retry on 429. |
| BL-15 | Image rules differ by layer. The gateway accepts any `image/*` at multer; the agent backend accepts JPEG, PNG, WebP and GIF; both cap at 5 MB. Gif support in the disease detector is not verified. | `chat.routes.js` `fileFilter`; `image_storage.py` | Accept list is the backend's four types; help text recommends JPEG or PNG (11.3). |
| BL-16 | History returns each image as a base64 data URL inside the JSON. | `routes.py` `image_as_data_url` | Lazy-loaded images and a skeleton while long conversations open (13.5). |
| BL-17 | Tokens live in `localStorage` (`client.ts`), so any script on the origin can read them. `index.html` sets no Content-Security-Policy. | `client.ts`; `index.html` | Not changeable by the UI. Keep Markdown without raw HTML (9.7). Flag for the security review; no design change here. |
| BL-18 | No client timeout on chat; a 60 s gateway timeout to the agent backend. | `fastapi.service.js` line 8 | Elapsed timer and the 45-second note (9.8). |
| BL-19 | Register reveals whether an email exists ("Email is already registered"); login does not ("Invalid email or password"). | `auth.controller.js` | The UI offers "Sign in instead" on register (7.4). The decision belongs to the backend owner. |

### 20.5 Frontend bugs in the existing code (fixed by this design)

| ID | Bug | Where | Fix |
|---|---|---|---|
| FB-1 | A wrong password shows "Your session has expired." | `client.ts` `request()`: the 401 branch runs for `/api/auth/login`; `getErrorMessage(401)` ignores the payload | Auth routes skip refresh; `mapError` for auth (7.4) |
| FB-2 | Declined questions are labelled "General Agriculture". | `gateway.ts` `agentsToDisplay` fallback | No fallback (9.6.3) |
| FB-3 | Simulated typing presented as streaming; the README says there is none. | `gateway.ts` 24-character reveal every 14 ms | Removed (17.5) |
| FB-4 | An invented "routing" step and a "Researched in N steps" panel. | `gateway.ts` routing tool call; `Thread.tsx` `ChainOfThought` | Removed (16.5) |
| FB-5 | A server session is created on every "New conversation" click, including unused ones. | `thread-adapter.tsx` `initialize` | Created on first send (9.3, 13.3) |
| FB-6 | History timestamps are the load time. | `gateway.ts` `historyMessage` `createdAt: new Date()` | No time for history (9.5) |
| FB-7 | Delete uses `window.confirm`. | `ThreadList.tsx` | `ConfirmDialog` (9.2) |
| FB-8 | Message images cropped to 220 px high with `object-fit: cover`. | `index.css` `.message-image` | `contain` with a max height (9.5, 11.4) |
| FB-9 | Leaf and sprout glyphs in brand, header and empty state. | `Sidebar.tsx`, `AuthPage.tsx`, `ChatWorkspace.tsx`, `EmptyState.tsx` | Neutral monogram; no leaf (4.5) |
| FB-10 | Green-tinted composer shadow. | `index.css` `.composer` | Neutral shadow tokens (9.10) |
| FB-11 | The accent is black, so primary, focus and selected look alike. | `index.css` `--accent: #171717` | Teal accent (4.3) |
| FB-12 | The typeface is named but never loaded (DM Sans). | `index.css` `:root` | Geist, optional, with system fallback (15.3) |
| FB-13 | Tailwind is imported but no utilities are used. | `index.css`; 110 `className` strings checked | Tailwind for layout only; tokens are variables (15.1) |
| FB-14 | Breakpoints at 850 px and 640 px only. | `index.css` media queries | Breakpoints in 15.12 |
| FB-15 | Theme applied after first paint. | `useTheme.ts`; `index.html` | Pre-paint script (17.6) |
| FB-16 | The generic zod message reaches the user. | `error.middleware.js` plus `getErrorMessage` | Client validation first (7.3) |
| FB-17 | The sidebar user block is only an initial and a logout icon. | `Sidebar.tsx` | `UserMenu` and Settings (14) |
| FB-18 | "Recent" is really "recently renamed or created". | `session.controller.js` (BL-7) | Honest label (13.2) |
| FB-19 | A raw server message from a 500 reaches the screen. | `getErrorMessage` default branch | `mapError` (16.6) |

---

## 21. Implementation Guidelines

### 21.1 Order of work

**Step 0 (prerequisite, no design work).** Make `npm ci` pass. The lockfile is missing `@emnapi/core@1.11.3`, `@emnapi/runtime@1.11.3` and `@emnapi/wasi-threads@1.2.3` (2.1). Run `npm install` once in `frontend/`, commit the regenerated lockfile, and confirm `npm ci`, `npm run lint` and `npm run build` pass. Do not change any pinned version in this step.

Then, in this order. Each phase ends with `npm run build` and `npm run lint` passing and a manual look in light and dark.

| Phase | Scope | Why this order |
|---|---|---|
| P1 | `tokens.css`, `base.css`, optional fonts, pre-paint script. Existing screens keep working through aliases. | Everything reads tokens |
| P2 | Shell: `AppLayout`, `Sidebar` (existing list logic kept), `TopBar`, drawer, `useHashRoute`, `useMediaQuery` | Views plug into the shell |
| P3 | Primitives: `Button`, `IconButton`, `Field`, `TextInput`, `TextArea`, `PasswordField`, `Dialog`, `ConfirmDialog`, `Menu`, `Disclosure`, `SegmentedControl`, `Banner`, `Spinner`, `Skeleton`, `Toast` | Used by every view |
| P4 | Auth: `AuthPage` rewritten; `errors.ts`; client change for auth routes (FB-1, FB-16) | Smallest, highest-value fix |
| P5 | Chat: `ChatLayout`, `ChatHeader`, `ConversationList`, `ConversationRow`, `ChatMessage`, `AssistantAnswer`, `AgentBadge`, `AgentDetails`, `Markdown`, `MarkdownTable`, `CodeBlock`, `MessageComposer`, `ImageChip`, `ImageLightbox`, `AgentActivityIndicator`, `EmptyState`, `SuggestedPrompts`, `JumpToLatest`; `gateway.ts` (FB-2, FB-3, FB-4); `thread-adapter.tsx` (FB-5); attribution cache | The core; depends on P1 to P4 |
| P6 | Dashboard and its parts | Uses sessions and chat |
| P7 | Crop page and parts; `prompts.ts` builder | Uses chat with composed text |
| P8 | Disease page; `ImageUpload`; `UploadProgress`; `sendWithProgress` (XHR); `DiseaseAnalysisResult` | Uses chat with a file |
| P9 | Settings and cards; `UserMenu`; `ThemeToggle` | Uses user and theme |
| P10 | Remove old code: `index.css` and aliases, old `Thread.tsx` pieces, `ChainOfThought`, `ActivityTool`, `ActivityReasoning`, `window.confirm`, old empty-state icons. Lazy-load crop, disease and settings with `React.lazy`. | Cleanup after parity |
| P11 | Acceptance pass (section 22) on desktop, tablet and phone; light and dark; keyboard only; reduced motion | Acceptance |

### 21.2 File-by-file plan

| File | Action | Notes |
|---|---|---|
| `index.html` | modify | Title "CropSage"; pre-paint script (17.6) |
| `src/main.tsx` | keep | Import order: `tokens.css`, `base.css`, then component styles |
| `src/App.tsx` | modify | Auth gate kept; `AuthenticatedApp` uses `AppLayout` and `useHashRoute`; lazy routes |
| `src/styles/tokens.css` | new | Section 15.11 |
| `src/styles/base.css` | new | Reset beyond Tailwind preflight; body, scrollbars, focus, reduced motion, sr-only |
| `src/styles/index.css` | replace, then delete | Staged (21.3) |
| `src/components/**` | per 16.1 and 16.8 | Create or replace |
| `src/lib/api/client.ts` | modify | Auth routes skip refresh (FB-1) |
| `src/lib/api/chat.ts` | modify | Add `sendWithProgress`; keep `history` and `send` |
| `src/lib/api/errors.ts` | new | `mapError` |
| `src/lib/runtime/gateway.ts` | modify | Remove reveal and routing; no fallback agent |
| `src/lib/runtime/thread-adapter.tsx` | modify | Lazy session creation; title rules |
| `src/lib/content/prompts.ts` | new | Suggestions, crop message builder, default disease question, titles |
| `src/hooks/*.ts` | new or keep | Per 16.6 |
| `src/types/api.ts` | keep; add alias | `AgentKey` |
| `frontend/README.md` | modify after P5 | Correct "LocalRuntime" wording and the "no simulated streaming" statement (now true after FB-3) |
| `package.json` | modify only for optional fonts | 21.4 |
| `package-lock.json` | regenerate once (step 0) | Needed for `npm ci` |

### 21.3 CSS migration

1. Create `tokens.css` with the variables in 15.11, and the aliases in 15.1 inside a `:root` block. Import it before `index.css`. The visible change is the palette and the accent.
2. Move each part of `index.css` into a component stylesheet as its component is rebuilt (P2 to P9). Moved rules use tokens only: no hex values in component stylesheets.
3. Use Tailwind utilities only for layout (flex, grid, gap, a few spacings). Keep colours, radii, shadows and type in component CSS that reads tokens.
4. Delete `index.css` in P10 after a search finds no alias references.

### 21.4 Dependencies

No new dependency is required.

Optional, flagged for Mithun's decision (versions read from the npm registry on 2026-11-07):

| Package | Version | Licence (registry field) | Use |
|---|---|---|---|
| `@fontsource-variable/geist` | 5.3.0 | OFL-1.1 | Geist Sans, variable, self-hosted |
| `@fontsource-variable/geist-mono` | 5.3.0 | OFL-1.1 | Geist Mono, variable, for code and units |

If installed, import both once in `base.css`. If not, the system stack in 15.3 applies and nothing else changes. Confirm the licence file inside the package when installing.

Not added, and not needed by this design: a component kit, a motion library, a router, a chart library, a syntax highlighter, a date library, a test runner.

Installed and used: React 19.2.8, `@assistant-ui/react` 0.15.17, `assistant-stream` 0.3.40, `react-markdown` 10.1.0, `remark-gfm` 4.0.1, `lucide-react` 1.35.0, Tailwind 4.3.3 with `@tailwindcss/vite`, Vite 8.2.2, TypeScript 5.9.3, ESLint with its plugins.

### 21.5 Quality gates per phase

- `npm run lint` passes with no new warnings.
- `npm run build` passes, including the `tsc` checks.
- No hex values outside `tokens.css`.
- No server 5xx text shown: every error path goes through `mapError`.
- Each new interactive component has keyboard and focus behaviour checked by hand.

### 21.6 Bundle size

The current single chunk is 724 kB (218 kB gzip). Target after P10: initial chunk under 500 kB, by lazy-loading crop, disease and settings. This is a target to measure, not a promise.

### 21.7 Things that must not change

- Storage keys `agrimind.access-token`, `agrimind.refresh-token`, `agrimind.theme`.
- API paths and request field names (`query`, `session_id`, `file`, `title`, `email`, `password`, `refreshToken`), and response parsing.
- Auth flow (login, refresh rotation, logout) and the `AuthProvider` contract.
- The assistant-ui runtime wiring (remote thread list, local runtime, attachment adapter). Only adapter internals change.
- The gateway and the backend. Nothing in this design needs a change there.

### 21.8 Open items for Mithun

These are decisions, not blockers for P1 to P6.

1. Install the two optional Geist packages? (Recommended.)
2. Display name: keep the email local-part (current), or add a name field later (needs a backend change).
3. Feedback thumbs: enable only once a feedback endpoint exists.
4. Crop model input ranges: read the training data's min and max, then add soft "outside the training range" notes. Until then only plausibility checks run.
5. Backend requests for later (not part of this design, listed so they are not forgotten): a stage event on chat; the crop value echo that the model actually used; top-N crops with probabilities; disease confidence and label as fields; timestamps on history; a session `updatedAt` that moves with messages; a feedback route.

---

## 22. Acceptance Criteria

Each item is checked by hand on the stated devices unless marked **build**. A view is accepted when all its items pass.

### 22.1 Global

- [ ] **AC-G-01 (build)** `npm ci`, `npm run lint`, `npm run build` all pass from a clean clone.
- [ ] **AC-G-02 (build)** No hex colour literal outside `tokens.css` (search the `src` tree).
- [ ] **AC-G-03** Every colour pair used in the UI is one of the pairs in 19.1, and passes its listed threshold in both themes.
- [ ] **AC-G-04** Light and dark both look designed: no element is simply inverted; dark uses surface steps and borders; accent in dark is `#5FC2B9`.
- [ ] **AC-G-05** The accent colour appears only on the uses listed in 15.2. No bright or leaf green appears anywhere except success status text and icons.
- [ ] **AC-G-06** No leaf, sprout or decorative agricultural graphics in the interface. The wheat icon appears only on the crop agent badge.
- [ ] **AC-G-07** The app name shown is "CropSage" in the title, brand, auth and About. Storage keys are unchanged.
- [ ] **AC-G-08** No internal word in user-facing text: "agent" is allowed only as "specialist" or in the agent names; no "routing", "thread", "session id", "checkpoint", "tool", "stage".
- [ ] **AC-G-09** Theme choice persists across reloads and applies before the first paint (no light flash in dark mode).
- [ ] **AC-G-10** Reduced motion setting removes translation, scale and spinning per 17.2.
- [ ] **AC-G-11** Every visible state in 9.15 and 16.2 has been seen at least once in a manual run.

### 22.2 Authentication (section 7)

- [ ] **AC-A-01** Sign in and Create account are tabs, switchable with the arrow keys; the URL does not change.
- [ ] **AC-A-02** Empty submit shows "Enter your email address." and "Enter your password." and focuses the first invalid field.
- [ ] **AC-A-03** Malformed email shows "That email doesn't look right. Check for typos." before any request is sent.
- [ ] **AC-A-04** Register with a password under 8 characters shows "Use at least 8 characters." before any request.
- [ ] **AC-A-05** Mismatched confirm shows "The passwords don't match."
- [ ] **AC-A-06** A wrong password shows "Email or password isn't right." and never "session expired" (FB-1 fixed). Verified with a real wrong password on a test account.
- [ ] **AC-A-07** Registering an email that exists shows the "Sign in instead" action and keeps the email.
- [ ] **AC-A-08** The password visibility toggle shows and hides the value, has an accurate `aria-label` and `aria-pressed`, and resets when the tab changes.
- [ ] **AC-A-09** During a request the submit shows its busy label and is disabled; the fields stay editable.
- [ ] **AC-A-10** Network failure shows the connection message; a 429 shows the rate message; a 5xx shows the generic message and never server text.
- [ ] **AC-A-11** Successful registration returns to Sign in with "Account created. Sign in to continue."
- [ ] **AC-A-12** Successful sign-in lands on Home with the cross-fade.

### 22.3 Dashboard (section 8)

- [ ] **AC-D-01** Greeting uses the local hour bands in 8.3 and the first name (or the email local-part).
- [ ] **AC-D-02** Three quick-start cards are whole-card links with focus rings; each opens its destination (`#/crop`, `#/disease`, `#/chat`).
- [ ] **AC-D-03** Recent shows at most five conversations ordered by `updatedAt`, each with "Updated {date}".
- [ ] **AC-D-04** The capabilities block describes the three specialists using only the copy in 8.5; no statistics appear that the data does not support.
- [ ] **AC-D-05** "Your work" counts appear only when sessions exist, and the label says they were started from CropSage.
- [ ] **AC-D-06** Empty state for a new account shows the sentence in 8.7 and still offers the three quick-start cards.
- [ ] **AC-D-07** Sessions load failure shows its message with a retry, and the quick-start cards still work.

### 22.4 Chat (section 9)

- [ ] **AC-C-01** New chat creates no server session until the first send (verify the session list before and after clicking New chat).
- [ ] **AC-C-02** The first send creates one session titled from the message (42 characters) and posts the message; reloading returns to that conversation.
- [ ] **AC-C-03** The conversation list groups by Today, Yesterday, Previous 7 days and Older; search filters titles without a request.
- [ ] **AC-C-04** Rename works from the row menu and the header; Escape cancels; an empty name saves as "New conversation".
- [ ] **AC-C-05** Delete opens a dialog (not `window.confirm`), focuses Cancel, and returns focus on close.
- [ ] **AC-C-06** Enter sends; Shift+Enter adds a line; Enter during IME composition does not send.
- [ ] **AC-C-07** Textarea grows to seven lines then scrolls; the composer stays above the on-screen keyboard on iOS Safari.
- [ ] **AC-C-08** Attach accepts JPEG, PNG, WebP and GIF; other types show "Please choose a JPEG, PNG, WebP, or GIF image."; over 5 MB shows "That photo is over 5 MB. Choose a smaller one."
- [ ] **AC-C-09** The image chip shows a thumbnail, name and size, and its remove control has a 44 px target on phone.
- [ ] **AC-C-10** Drag and drop of an image onto the chat attaches it; a non-image drop shows the error.
- [ ] **AC-C-11** A sent photo shows full, uncropped (`contain`) in the message; tapping it opens the lightbox; Escape closes it.
- [ ] **AC-C-12** Markdown renders headings, lists, blockquotes, inline and block code, links (opening in a new tab with `rel`), and GFM tables inside a scroll region.
- [ ] **AC-C-13** Raw HTML in an answer is not rendered as HTML (no raw-HTML plugin is installed; a typed or returned tag does not become an element).
- [ ] **AC-C-14** The pending state shows "Working on your question…", an elapsed count, the 20-second note and the 45-second note; no stage names appear.
- [ ] **AC-C-15** The answer appears only when the response is complete; no character-by-character reveal occurs.
- [ ] **AC-C-16** Attribution row shows the badges for `selected_agents` in the stated order, with the stated labels; no row for an empty list (a declined question shows no badge).
- [ ] **AC-C-17** A multi-agent answer offers "See each specialist's answer", and the disclosure shows each agent's own text; an `Agent error:` value shows the error badge with "couldn't finish".
- [ ] **AC-C-18** After reload, a previously attributed answer shows its badges only from the attribution cache; other answers show no badge (and no invented one).
- [ ] **AC-C-19** Copy copies the Markdown source and confirms for 1.5 seconds.
- [ ] **AC-C-20** No Regenerate control appears on a successful answer; Try again appears only after a failure, and it is never automatic.
- [ ] **AC-C-21** A failed send keeps the text and photo in place, shows the mapped message from 9.9, and sending again works.
- [ ] **AC-C-22** Each status in the 9.9 table produces its listed sentence (verify 413, 400, 429, 502, 503, 504, network and 500 with a test server or a forced failure).
- [ ] **AC-C-23** The suggested prompts insert text into the composer and do not send it; none contains sample numbers.
- [ ] **AC-C-24** Jump to latest appears only when the user has scrolled up, and scrolls to the bottom.
- [ ] **AC-C-25** The header meta line shows "Updated {relative time} · {n} messages" for saved conversations and nothing for drafts.
- [ ] **AC-C-26** Feedback controls are absent (flag off). No local-only feedback appears.
- [ ] **AC-C-27** History images are lazy-loaded and the conversation opens with a skeleton.

### 22.5 Crop recommendation (section 10)

- [ ] **AC-R-01** The form shows exactly seven fields with the labels, units and attributes in 10.3, in two groups named Soil and Climate.
- [ ] **AC-R-02** No field has a value at load. No field has a sample value in its placeholder.
- [ ] **AC-R-03** The "Missing:" line names every empty field in form order; the submit button is disabled until all seven are valid.
- [ ] **AC-R-04** Each field's range rule (10.3) produces its message on blur or submit, and `aria-invalid` is set.
- [ ] **AC-R-05** A comma typed as a decimal separator is accepted.
- [ ] **AC-R-06** The Soil group carries the sentence "These are soil nutrient levels you entered, used by the crop model. They are not a fertilizer recommendation."
- [ ] **AC-R-07** The message sent to the chat endpoint matches the 10.5 template exactly, with the user's values as typed.
- [ ] **AC-R-08** "What was sent" shows the exact message text.
- [ ] **AC-R-09** The result shows the crop agent's Markdown, the "Values you submitted" list, and the footnote. It shows no confidence, no top-N list, no probabilities, and no separate crop-name headline.
- [ ] **AC-R-10** The form and result are side by side on laptop and stacked on phone; on phone the submit sits in the sticky bottom bar.
- [ ] **AC-R-11** "Edit values" returns to the form with the values intact.
- [ ] **AC-R-12** The session appears in the conversation list with the title "Crop recommendation · {date}".

### 22.6 Disease detection (section 11)

- [ ] **AC-P-01** Drop zone, choose and take-photo controls work; Enter or Space opens the picker on the drop zone.
- [ ] **AC-P-02** Dragging an image onto the zone shows the drag-active state and attaches the file; a non-image is refused with the message.
- [ ] **AC-P-03** The preview shows the whole image (`contain`); remove returns to the empty zone.
- [ ] **AC-P-04** Upload progress shows real percentages during upload only; after upload an indeterminate bar with elapsed text appears; no percentage is shown after upload.
- [ ] **AC-P-05** An empty note sends the default question from 11.5, and "What was sent" displays it.
- [ ] **AC-P-06** The result shows the disease agent's Markdown and the thumbnail; no confidence, label or top-3 appears.
- [ ] **AC-P-07** The footer note appears on every result.
- [ ] **AC-P-08** Error sentences from 11.7 appear for the matching statuses; the photo stays in place for retry.
- [ ] **AC-P-09** Phone layout: the two buttons (choose and take photo) are full width and 48 px tall; "Analyse photo" is sticky.

### 22.7 Agricultural assistant (section 12)

- [ ] **AC-S-01** Topic starters insert their text with bracketed placeholders and do not send.
- [ ] **AC-S-02** Fertilizer answers with a Markdown table render with a horizontal scroll on phone.
- [ ] **AC-S-03** No nutrient gauge, status indicator or advisory card appears.
- [ ] **AC-S-04** The composer disclaimer is present on every chat view.
- [ ] **AC-S-05** The follow-up tip appears in the About this conversation popover.

### 22.8 Sessions and memory (section 13)

- [ ] **AC-M-01** The conversation list shows "Updated {date}" and never "last message".
- [ ] **AC-M-02** Opening a deleted or foreign conversation shows "This conversation isn't available. It may have been deleted." with a new-chat button, and no status code.
- [ ] **AC-M-03** Deleting the open conversation returns to a draft with "Conversation deleted."
- [ ] **AC-M-04** The About popover shows created date, updated date and message count, with no identifiers.
- [ ] **AC-M-05** No session identifier, token or internal name appears in any visible text.

### 22.9 Settings and profile (section 14)

- [ ] **AC-T-01** Theme segmented control offers Light, Dark, System; arrow keys move the selection; the choice applies immediately.
- [ ] **AC-T-02** The compact sidebar theme control and the Settings control stay in sync.
- [ ] **AC-T-03** Email is shown read-only with a Copy action; there is no change-password or change-email control.
- [ ] **AC-T-04** Sign out calls the logout route, clears the local state even on failure, and returns to sign-in.
- [ ] **AC-T-05** The About section shows the version, the shortcut and the "How CropSage works" paragraph, and links to no page that does not exist.
- [ ] **AC-T-06** The user menu in the sidebar opens Settings, theme and sign out, with keyboard support.

### 22.10 Responsive (section 18)

- [ ] **AC-R-S1** At 375 px wide (phone): every view is usable with one hand reach to the composer and submit buttons; no horizontal page scroll; touch targets are at least 44 px.
- [ ] **AC-R-S2** At 768 px (tablet): the sidebar is the rail; expanding it overlays the content; the crop form uses two columns of fields.
- [ ] **AC-R-S3** At 1280 px (desktop): sidebar expanded; chat column 760 px centred; crop and disease are two-column.
- [ ] **AC-R-S4** Text at 200% browser zoom reflows without losing controls (18.10).
- [ ] **AC-R-S5** Drawer on phone: focus moves in on open, returns on close, Escape closes, scrim closes, body does not scroll.
- [ ] **AC-R-S6** Landscape phone (640 to 767 px wide): drawer and single column still usable.

### 22.11 Accessibility (section 19)

- [ ] **AC-X-01** Every control in the keyboard map (19.3) is reachable and operable with the keyboard only.
- [ ] **AC-X-02** Focus rings are visible on every interactive element on light and dark backgrounds.
- [ ] **AC-X-03** Screen reader pass (VoiceOver or NVDA): landmarks, headings, labels, the "Answer ready" announcement, badges read as text, and form errors read once.
- [ ] **AC-X-04** Icon-only controls have accessible names.
- [ ] **AC-X-05** Colour is never the only signal for status, agent or error (19.2).

### 22.12 Backend contract (section 20)

- [ ] **AC-B-01 (build)** Every request path, method and field name matches section 20.2; no new route is called.
- [ ] **AC-B-02** Response parsing reads `response`, `selected_agents`, `agent_responses`, `session_id`, `messages` (with optional `image`), `accessToken`, `refreshToken`, `id`, `email`, `createdAt`, `isActive`, `title`, `updatedAt`; no new response field is assumed.
- [ ] **AC-B-03** The chat request sends the seven crop values in the text and no file; a disease request sends one file under its own name.
- [ ] **AC-B-04** No code path shows a 5xx server message to the user (`mapError`).
- [ ] **AC-B-05** The bearer header is sent on every route that needs it; refresh runs at most once per request and is de-duplicated.

### 22.13 Bugs fixed (section 20.5)

- [ ] **AC-F-01** FB-1 to FB-19 are each checked against their "Fix" entry. A short note per item is kept in the pull request.

---

## Design Review

Self-review against the eleven criteria, done after the sections were written. Each row records the rating, the evidence, and the problems found during the review, all of which were fixed in this document.

| Criterion | Requirement | Result | Evidence in this document | Problems found in review and fixed |
|---|---|---|---|---|
| Visual quality | Premium modern AI SaaS look | **Pass** (design specified; not yet rendered) | Sections 4, 15, 17; one accent; Geist; hairline surfaces | Green-tinted shadow and leaf icons removed (FB-9, FB-10). No gradients or glass added. Not visually verified: a render pass is part of P11. |
| Consistency | One design language | **Pass** | Token-only colours (AC-G-02); one radius scale; one motion table; one control-state table | Tailwind utility bridge would have referenced itself; removed, tokens are the only source (15.1). |
| Usability | Simple and intuitive | **Pass** | Sections 5, 9, 10, 11; one primary action per view | Auto-retry on a non-idempotent POST removed (9.9, BL-9). Regenerate removed from successful answers. Retry is a user tap only. |
| Agent awareness | Clearly communicates multi-agent capabilities | **Pass, bounded by the data** | Attribution row, details disclosure, error badge, cache for reload (9.6) | Fake routing step and "Researched in N steps" removed (FB-4). Supervisor not invented per message. Declined answers show no badge (FB-2). |
| Agricultural relevance | Suitable for agricultural workflows | **Pass** | Crop form with units and the "not a fertilizer recommendation" line; disease photo tips; plant-specific copy; topic starters | Sample numbers removed from suggestions (9.11). "Values you submitted", not "model inputs" (10.7). Uncertain outputs carry footers, not invented confidence. |
| Chat experience | High-quality conversational interface | **Pass** | Column, measure, composer, pending state, Markdown rules, error mapping, scroll behaviour | Simulated typing removed (FB-3). No timestamps invented for history (FB-6). Image crop fixed (FB-8). |
| Theme support | Complete light and dark | **Pass** | Two palettes in 15.2 and 15.11; contrast in 19.1 for both | First dark draft failed (tertiary on user bubble, 4.36:1); fixed to `#1A1E24` (4.62:1). Danger text on dark needed its own token; added `--color-error-on`. Pre-paint script added (FB-15). |
| Responsiveness | Desktop, tablet, phone | **Pass** | Sections 6.3, 18 with per-range table; phone layouts for each view | Phone layouts are separate designs, not shrunk desktop. Composer font 16 px against iOS zoom (18.4). |
| Existing libraries | Prioritise installed dependencies | **Pass** | Section 21.4: no new required dependency; optional fonts listed with registry versions | Charting, motion, router, kit and highlighter deliberately not added. Dialog built on native `<dialog>`. Markdown kept. |
| Backend compatibility | Preserve all existing contracts | **Pass** | Section 20.2 endpoint table; 21.7 unchanged list; 22.12 checks | Crop and disease designs do not assume fields the backend does not return (BL-2, BL-4). A stage-indicator prop exists but renders nothing today (16.3). |
| Implementation readiness | Detailed enough to build directly | **Pass, with two prerequisites** | Sections 15 to 17 (exact tokens, state tables), 16 (components, props), 21 (order and file plan) | Prerequisite 1: `npm ci` fails (lockfile); step 0. Prerequisite 2: crop input ranges are unknown, so only plausibility checks are specified. |

Other inconsistencies caught and corrected during writing:

- The sample-looking mock in 8.2 and 14.2 used a real-looking email; replaced with `ada@example.com`.
- The list label "Recent" described an ordering by rename time, not by activity; relabelled "Updated {date}" (FB-18, BL-7).
- The disease note field and the required non-empty `query` (BL-14 and 11.5): the default question is sent and shown, so it is never hidden.
- The composer's Stop state and the send state share one slot; the spec is one control with two states.

Open risks that the design does not close (for Mithun):

- The crop message depends on the backend's LLM extraction (BL-3). The UI reduces the risk but cannot prove the model used the values. Only a backend echo would prove it.
- After reload, attribution depends on the local cache (BL-5).
- Visual quality is specified, not rendered. P11 includes a render pass on real devices.

---

## Appendix A: Research log

Everything examined for this document, with what was done.

| Source | Request | Result | Used for |
|---|---|---|---|
| Linear homepage | Fetch (HTML) and text read | 200; text includes sidebar view names and the product line | Section 3, row 1 |
| Linear Method page | Fetch and text read | 200 | Section 3, row 1 |
| Linear redesign post (`/now/how-we-redesigned-the-linear-ui`) | Fetch and text read | 200; LCH theme system, three inputs (base, accent, contrast), sidebar and header noise reduction | Sections 3, 4.2 |
| Vercel homepage | Fetch (HTML meta) | 200; theme colour `#FAFAFA` | Section 3, row 2 |
| Geist introduction (`vercel.com/geist/introduction`) | Fetch and text read | 200; Geist Sans, Geist Mono, "high contrast, accessible color system" | Section 3, row 2; typeface choice |
| Geist colours (`vercel.com/geist/colors`) | Fetch and text read | 200; ten scales; gray for text, borders and dividers | Section 3, row 2; neutral discipline |
| Stripe Dashboard basics (`docs.stripe.com/dashboard/basics`) | Fetch and text read | 200; primary navigation, Home page, `?` shortcut | Section 3, row 3 |
| Stripe Dashboard breakdown (925studios) | Fetch and text read | 200; navigation maps to jobs, microcopy in empty states | Section 3, row 3 |
| Stripe design system note (designsystems.one) | Fetch and text read | 200; secondary evidence only | Section 3, row 3 (typeface context) |
| ChatGPT (`chatgpt.com`) | Fetch | 200 with an almost empty client shell (title "ChatGPT"); not read in full | Recorded as blocked to full read |
| ChatGPT breakdown (925studios) | Fetch and text read | 200; sidebar of conversations by recency; streaming as default | Section 3, row 4 (secondary) |
| Claude (`claude.ai`) | Fetch | 403, bot challenge | Recorded as blocked |
| Claude write-up (Substack, Dec 2024) | Fetch and text read | 200; names the two typefaces | Section 3, row 5 (secondary; typefaces not adopted) |
| Perplexity (`perplexity.ai`) | Fetch | 403, bot challenge | Recorded as blocked |
| Perplexity citations teardown (aiuxplayground) | Fetch and text read | 200; sources panel and attribution row (secondary) | Section 3, row 6 (secondary) |
| Notion homepage | Fetch and text read | 200; no app pages opened | Section 3, row 7 (limited) |
| Climate FieldView homepage | Fetch and text read | 200 | Section 3, row 8 |
| Cropin homepage | Fetch and text read | 200 | Section 3, row 9 |
| Corvian homepage (formerly Farmers Edge) | Fetch and text read | 200 | Section 3, row 10 |
| Agrivi homepage | Fetch (HTML meta) | 200; theme colour `#5BAD3F` | Section 3, row 11 (counter-example) |
| npm registry: `@fontsource-variable/geist`, `@fontsource-variable/geist-mono`, `geist`, `lucide-react`, `@assistant-ui/react` | Registry metadata read (no install) | `@fontsource-variable/geist` 5.3.0 and `…-mono` 5.3.0, OFL-1.1; `lucide-react` latest 1.70.0; `@assistant-ui/react` latest 0.15.32 | Section 21.4 and 2.1 |
| Frontend source at `69f92b2` | Read in full: all `src` files, `package.json`, `vite.config.ts`, `index.html`, `README.md`, `.env.example`, `index.css` (statistics and pattern search) | — | Section 2 |
| Gateway source (`gateway/src`): controllers, routes, services, middleware, utils, Prisma schema | Read | — | Sections 2, 20 |
| Agent backend source (`agent_backend`): `api/routes.py`, `schemas/chat.py`, `graph/main_graph.py`, `graph/state.py`, `agents/crop/graph.py`, `agents/disease/graph.py`, `services/crop_model.py`, `services/disease_detection/schemas.py`, `services/image_storage.py`, crop notebook (output not read in full) | Read | — | Sections 1, 20 |
| `npm ci` on a throwaway copy of the frontend lockfile and `package.json` | Run with `--ignore-scripts` | Exit with `EUSAGE`; lockfile out of sync (three `@emnapi/*` entries missing) | Section 2.1 and 21.1 step 0 |
| Earlier audit artefacts (`tasks/058a2894…/audit/fe/`: build, lint, npm audit logs) | Read | Build and lint pass; audit totals 14 advisories | Section 2.1 |
| Scratch clone | `git clone` of the local clone of `69f92b2` into the task directory | Clean (`git status` empty before the design file was written) | Delivery |

What was **not** done in this research: no browser session, no screenshot of any product or of the current app, no logged-in product use, no run of the frontend in a browser, no test run. The interface is specified from source and from the pages listed above.
