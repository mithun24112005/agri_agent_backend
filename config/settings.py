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
    
    # External Services
    disease_api_url: str = Field("http://127.0.0.1:8000", env="DISEASE_API_URL")
    
    # LangSmith
    langchain_tracing_v2: Optional[str] = Field(None, env="LANGSMITH_TRACING")
    langchain_api_key: Optional[str] = Field(None, env="LANGSMITH_API_KEY")
    langchain_project: Optional[str] = Field(None, env="LANGSMITH_PROJECT")

    # Project Paths
    base_dir: Path = PROJECT_ROOT
    agents_dir: Path = PROJECT_ROOT / "agents"
    crop_docs_path: Path = agents_dir / "crop_data"
    crop_model_path: Path = agents_dir / "models" / "crop_recommendation_rf_model.pkl"
    target_encoder_path: Path = agents_dir / "models" / "target_encoder.pkl"
    disease_folder_path: Path = agents_dir / "diseases"

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
