import os
import sqlite3
from pathlib import Path
from config.settings import settings
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from contextlib import asynccontextmanager

@asynccontextmanager
async def create_checkpointer():
    """
    Factory for creating the appropriate checkpointer based on settings.
    Currently supports SQLite. PostgreSQL can be added here seamlessly.
    """
    backend = settings.session_checkpointer_backend.lower()
    
    if backend == "sqlite":
        # Ensure the directory exists
        db_path = settings.session_checkpoint_db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # AsyncSqliteSaver handles connection pools automatically
        async with AsyncSqliteSaver.from_conn_string(db_path) as checkpointer:
            yield checkpointer
    
    else:
        raise ValueError(f"Unsupported checkpointer backend: {backend}")
