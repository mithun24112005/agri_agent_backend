from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Calculate the project root (assuming this file is in config/settings.py)
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

class Settings(BaseSettings):
    # LLM Providers
    google_api_key: Optional[str] = Field(None, env="GOOGLE_API_KEY")
    groq_api_key: Optional[str] = Field(None, env="GROQ_API_KEY")
    
    # Embeddings
    hf_token: str = Field(..., env="HF_TOKEN")
    
    # Search
    tavily_api_key: str = Field(..., env="TAVILY_API_KEY")
    
    # Vector DB
    qdrant_url: str = Field("http://localhost:6333", env="QDRANT_URL")
    
    # Disease Detection (HF Inference API)
    hf_disease_model: str = Field("linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification", env="HF_DISEASE_MODEL")
    disease_confidence_threshold: float = Field(0.80, env="DISEASE_CONFIDENCE_THRESHOLD")
    hf_timeout_seconds: int = Field(15, env="HF_TIMEOUT_SECONDS")
    hf_max_retries: int = Field(3, env="HF_MAX_RETRIES")
    
    # LangSmith
    langchain_tracing_v2: Optional[str] = Field(None, env="LANGSMITH_TRACING")
    langchain_api_key: Optional[str] = Field(None, env="LANGSMITH_API_KEY")
    langchain_project: Optional[str] = Field(None, env="LANGSMITH_PROJECT")

    # Session Memory
    session_checkpointer_backend: str = Field("sqlite", env="SESSION_CHECKPOINTER_BACKEND")
    session_checkpoint_db_path: str = Field("./storage/checkpoints/langgraph.db", env="SESSION_CHECKPOINT_DB_PATH")
    max_conversation_messages: int = Field(20, env="MAX_CONVERSATION_MESSAGES")

    # Project Paths
    base_dir: Path = PROJECT_ROOT
    agents_dir: Path = PROJECT_ROOT / "agents"
    crop_docs_path: Path = agents_dir / "crop_data"
    crop_model_path: Path = agents_dir / "models" / "crop_recommendation_rf_model.pkl"
    target_encoder_path: Path = agents_dir / "models" / "target_encoder.pkl"
    disease_folder_path: Path = agents_dir / "diseases"
    disease_dataset_path: Path = agents_dir / "diseases_dataset"
    disease_collection_name: str = Field("disease_knowledge_v2", env="DISEASE_COLLECTION_NAME")

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
