from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, APIRouter
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    print("Starting Smart Agriculture Backend...")
    yield
    # Shutdown logic
    print("Shutting down Smart Agriculture Backend...")

app = FastAPI(
    title="Smart Agriculture Multi-Agent Backend",
    description="Backend API for an AI-powered smart agriculture assistant using LangGraph.",
    version="1.0.0",
    lifespan=lifespan
)

# API Router
api_router = APIRouter()

@api_router.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "message": "Smart Agriculture Backend is healthy"}

# Include routers
from api.routes import chat_router
app.include_router(api_router)
app.include_router(chat_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
