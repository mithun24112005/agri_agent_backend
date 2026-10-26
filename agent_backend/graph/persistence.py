import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from contextlib import asynccontextmanager
from config.settings import settings

@asynccontextmanager
async def create_checkpointer():
    """
    Factory for creating the PostgreSQL checkpoint saver.
    Uses AsyncPostgresSaver with a connection pool.
    """
    backend = settings.session_checkpointer_backend.lower()

    if backend != "postgres":
        raise ValueError(
            f"Unsupported checkpointer backend: '{backend}'. "
            "Only 'postgres' is supported. Set SESSION_CHECKPOINTER_BACKEND=postgres"
        )

    db_url = settings.session_checkpoint_database_url
    if hasattr(db_url, 'get_secret_value'):
        db_url = db_url.get_secret_value()

    if not db_url:
        raise ValueError(
            "SESSION_CHECKPOINT_DATABASE_URL is required but not configured. "
            "Set it to a PostgreSQL connection string."
        )

    async with AsyncPostgresSaver.from_conn_string(db_url) as checkpointer:
        await checkpointer.setup()
        yield checkpointer
