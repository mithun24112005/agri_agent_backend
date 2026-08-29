# 🧠 How Memory Works in This System

A plain-English explanation of how the backend remembers conversations, what limits exist, and what happens when the chat gets very long.

---

## 📬 Step-by-Step: What Happens When You Send a Message

Think of each conversation like a phone call with a receptionist (the Supervisor) and a team of specialists (Disease, Crop, General agents).

Here is exactly what happens every time you hit **Send**:

```
You → Receptionist Desk (FastAPI)
       ↓
       [1] Save your message to the SQLite database
       ↓
       [2] Fetch the last 6 messages from that database as "context"
       ↓
       [3] PII Filter: Remove personal info (names, emails, etc.)
       ↓
       [4] Guardrail Check: Is this question about agriculture?
           → NO: Politely reject. Stop here.
           → YES: Continue ↓
       ↓
       [5] Supervisor: Decide which specialist(s) to call
       ↓
       [6] Call the specialist agents (in parallel if multiple)
              - Disease Agent (image + RAG database)
              - Crop Agent (Random Forest ML model)
              - General Agent (live Tavily web search)
       ↓
       [7] Merge all specialist answers into one clean response
       ↓
       [8] Save the AI response to the SQLite database
       ↓
       [9] Return the response to you
```

---

## 📦 How Many Messages Can a Session Hold?

### In the Database (Total Storage)
**Unlimited.** The SQLite database stores **every single message** in a session forever (until the database file is deleted). There is no built-in cap. As long as you use the same `session_id`, every conversation turn is saved.

### In the "Active Context" Passed to the AI (Working Memory)
This is where the limit kicks in. At each turn, we only send the **last 6 messages** to the AI agents for context. This is controlled in the code at `graph/main_graph.py`:

```python
# Get up to the last 6 messages (3 turns = 3 questions + 3 answers)
recent = messages[-7:-1]
```

So in practice, the AI has a **rolling window of 3 conversation turns** (3 of your questions + 3 AI answers = 6 messages) as its "active memory" at any given moment.

---

## ❓ Why Only 6 Messages and Not Everything?

Because of the **LLM Context Window** — a hard limit on how much text an AI model can read at once.

Think of it like this: the AI can only hold a certain-sized "cheat sheet" while answering. If you dump the entire chat history onto that cheat sheet, two problems occur:

1. **It might overflow**: If the history is too long, the API throws a "context length exceeded" error and the whole request fails.
2. **It gets expensive and slow**: Every token sent to Groq's API costs money and adds latency. Sending 200 messages to answer a simple follow-up is wasteful.

The solution is a **sliding window**: we only keep the most recent, relevant messages in the active window.

---

## ⚠️ What Happens With a Very Long Chat History?

Let's say you have been chatting for 50 turns. Here is exactly what happens:

| What is stored | What the AI "sees" |
|---|---|
| All 100 messages (50 questions + 50 answers) saved in SQLite database | Only the most recent 6 messages (the last 3 turns) |

### Example:
- **Turn 1**: You uploaded an apple scab image → AI identified Apple Scab.
- **Turn 2-10**: You asked about symptoms, causes, treatments, etc.
- **Turn 48**: You asked "What crop should I grow?" → AI recommended Rice.
- **Turn 49**: You asked "What was the disease you identified at the beginning?"

**The AI will NOT remember Turn 1.** It only sees Turns 46–48. The original disease diagnosis from Turn 1 has scrolled out of the active window.

This is the key trade-off of a sliding window approach.

---

## 🔮 What Are the Solutions for Very Long Chats?

There are standard solutions used in production systems to fix this. This system is built so they can be added without redesigning anything:

### Option 1: Increase the Window Size
Change `messages[-7:-1]` to `messages[-21:-1]` to keep the last 10 turns instead of 3. Simple, but uses more tokens and costs more.

### Option 2: Long-Term Memory / Semantic Summary
At the end of every session (or every N turns), an LLM summarizes the entire conversation into a few bullet points. That summary is saved separately and prepended to every future context window. This way the AI "remembers" a compact version of the entire history forever.

### Option 3: Pinned Facts (Entity Memory)
Important facts extracted from early in the conversation (like "disease = Apple Scab" or "crop recommended = Rice") are saved into a separate structured "facts" dictionary and always included in context — even if the raw messages have scrolled away. The `disease_result` and `crop_result` fields in `MainAgentState` are the early building blocks of this approach — they are **always** passed to the disease and crop agents regardless of how old they are.

---

## 🗄️ Where Is Memory Stored?

| Layer | Location | Persists? |
|---|---|---|
| All raw messages | `storage/checkpoints/langgraph.db` | ✅ Yes, survives server restarts |
| Active context (rolling window) | In-memory at request time | ❌ No, rebuilt each request |
| Disease result (prediction + disease ID) | SQLite checkpoint state | ✅ Yes |
| Crop result (recommended crop) | SQLite checkpoint state | ✅ Yes |

---

## 🔑 Key Takeaway

> The system stores **everything** but only **remembers the last 3 turns** when thinking. This keeps it fast, cheap, and stable. Older messages are in the database waiting to be used — they just aren't fed to the AI at the moment.
