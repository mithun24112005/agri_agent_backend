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
        await checkpointer.setup() # Initialize SQLite DB schema
        
        app.state.checkpointer = checkpointer
        app.state.graph = build_main_graph(checkpointer=checkpointer)
        print("Graph compiled with persistence.")
        
        yield
    # Shutdown logic
    print("Shutting down Smart Agriculture Backend...")
    # SQLite connections are typically managed within contexts or cleaned up automatically,
    # but we can do any explicit cleanup here if needed.

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
    # Optionally verify checkpointer is loaded
    memory_status = "available" if hasattr(request.app.state, "checkpointer") else "unavailable"
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
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
