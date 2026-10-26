import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from graph.persistence import create_checkpointer
from graph.main_graph import build_main_graph

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    print("Starting Smart Agriculture Backend...")
    
    # Initialize checkpointer and compile graph
    async with create_checkpointer() as checkpointer:
        app.state.checkpointer = checkpointer
        app.state.graph = build_main_graph(checkpointer=checkpointer)
        print("Graph compiled with PostgreSQL persistence.")
        
        yield
    # Shutdown logic
    print("Shutting down Smart Agriculture Backend...")

app = FastAPI(
    title="Smart Agriculture Multi-Agent Backend",
    description="Backend API for an AI-powered smart agriculture assistant using LangGraph.",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Router
api_router = APIRouter()

@api_router.get("/health", tags=["Health"])
async def health_check(request: Request):
    memory_status = "unavailable"
    if hasattr(request.app.state, "checkpointer"):
        try:
            # Verify PostgreSQL connectivity non-destructively
            await request.app.state.checkpointer.aget_tuple(
                {"configurable": {"thread_id": "__health_check__", "checkpoint_ns": ""}}
            )
            memory_status = "available"
        except Exception as e:
            print(f"PostgreSQL health check ping failed: {e}")
            memory_status = "unavailable"

    return {
        "status": "ok", 
        "message": "Smart Agriculture Backend is healthy",
        "memory": memory_status
    }

# Include routers
from api.routes import chat_router
app.include_router(api_router)
app.include_router(chat_router)

if __name__ == "__main__":
    import uvicorn
    if sys.platform == "win32":
        try:
            import uvicorn.loops.asyncio
            uvicorn.loops.asyncio.asyncio_loop_factory = lambda use_subprocess=False: asyncio.SelectorEventLoop
        except Exception:
            pass
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
