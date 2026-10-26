import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import unittest
from unittest.mock import patch
import uuid
from typing import TypedDict

from config.settings import settings
from graph.persistence import create_checkpointer
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import StateGraph, START, END


class SimpleState(TypedDict):
    value: str
    step: int


def append_step(state: SimpleState) -> SimpleState:
    return {
        "value": f"{state.get('value', '')} -> processed",
        "step": state.get("step", 0) + 1,
    }


def make_test_graph(checkpointer):
    builder = StateGraph(SimpleState)
    builder.add_node("process", append_step)
    builder.add_edge(START, "process")
    builder.add_edge("process", END)
    return builder.compile(checkpointer=checkpointer)


class TestPostgresPersistence(unittest.IsolatedAsyncioTestCase):
    """
    Integration and unit tests for PostgreSQL-backed LangGraph checkpointer.
    Tests verify configuration, initialization, state persistence, restart durability,
    and thread isolation against PostgreSQL database 'agri_memory'.
    """

    def test_postgres_config_selected(self):
        """Settings must configure postgres as checkpointer backend with non-empty URL."""
        self.assertEqual(settings.session_checkpointer_backend.lower(), "postgres")
        self.assertIsNotNone(settings.session_checkpoint_database_url)
        url = settings.session_checkpoint_database_url
        if hasattr(url, "get_secret_value"):
            url = url.get_secret_value()
        self.assertTrue(url.startswith("postgresql://") or url.startswith("postgres://"))

    async def test_missing_database_url_raises(self):
        """Missing SESSION_CHECKPOINT_DATABASE_URL must raise clear ValueError."""
        with patch.object(settings, "session_checkpoint_database_url", None):
            with self.assertRaises(ValueError) as ctx:
                async with create_checkpointer():
                    pass
            self.assertIn("SESSION_CHECKPOINT_DATABASE_URL is required", str(ctx.exception))

    async def test_unsupported_backend_raises(self):
        """Any checkpointer backend other than 'postgres' must raise clear ValueError."""
        with patch.object(settings, "session_checkpointer_backend", "sqlite"):
            with self.assertRaises(ValueError) as ctx:
                async with create_checkpointer():
                    pass
            self.assertIn("Unsupported checkpointer backend: 'sqlite'", str(ctx.exception))

    async def test_checkpointer_initialization(self):
        """create_checkpointer() connects and runs setup() against real PostgreSQL."""
        async with create_checkpointer() as checkpointer:
            self.assertIsInstance(checkpointer, AsyncPostgresSaver)

    async def test_write_and_retrieve_state(self):
        """A test graph can persist and retrieve state via PostgreSQL."""
        test_thread = f"test-thread-{uuid.uuid4()}"
        config = {"configurable": {"thread_id": test_thread}}

        async with create_checkpointer() as checkpointer:
            graph = make_test_graph(checkpointer)
            result = await graph.ainvoke({"value": "seed_msg", "step": 0}, config=config)
            self.assertEqual(result["value"], "seed_msg -> processed")
            self.assertEqual(result["step"], 1)

            saved_state = await graph.aget_state(config)
            self.assertEqual(saved_state.values["value"], "seed_msg -> processed")
            self.assertEqual(saved_state.values["step"], 1)

    async def test_persistence_across_restarts(self):
        """State written in one checkpointer session survives across a second fresh connection."""
        test_thread = f"test-thread-durability-{uuid.uuid4()}"
        config = {"configurable": {"thread_id": test_thread}}

        # Session 1: run graph with checkpointer1
        async with create_checkpointer() as checkpointer1:
            graph1 = make_test_graph(checkpointer1)
            await graph1.ainvoke({"value": "durable_data", "step": 10}, config=config)

        # Session 2: completely new checkpointer instance reading from PostgreSQL
        async with create_checkpointer() as checkpointer2:
            graph2 = make_test_graph(checkpointer2)
            saved_state = await graph2.aget_state(config)
            self.assertIsNotNone(saved_state)
            self.assertEqual(saved_state.values["value"], "durable_data -> processed")
            self.assertEqual(saved_state.values["step"], 11)

    async def test_thread_isolation(self):
        """Data written to thread A is never visible in thread B."""
        thread_a = f"test-thread-A-{uuid.uuid4()}"
        thread_b = f"test-thread-B-{uuid.uuid4()}"
        config_a = {"configurable": {"thread_id": thread_a}}
        config_b = {"configurable": {"thread_id": thread_b}}

        async with create_checkpointer() as checkpointer:
            graph = make_test_graph(checkpointer)
            await graph.ainvoke({"value": "alice_secret", "step": 1}, config=config_a)

            state_b = await graph.aget_state(config_b)
            self.assertEqual(state_b.values, {})

    async def test_historical_state_retrieval(self):
        """Multiple checkpoints on the same thread can be retrieved from history."""
        test_thread = f"test-thread-history-{uuid.uuid4()}"
        config = {"configurable": {"thread_id": test_thread}}

        async with create_checkpointer() as checkpointer:
            graph = make_test_graph(checkpointer)

            await graph.ainvoke({"value": "initial", "step": 1}, config=config)
            await graph.ainvoke({"value": "second", "step": 2}, config=config)

            history = [s async for s in graph.aget_state_history(config)]
            self.assertGreaterEqual(len(history), 2)
            steps = [s.values.get("step") for s in history if "step" in s.values]
            self.assertIn(2, steps)
            self.assertIn(3, steps)


if __name__ == "__main__":
    unittest.main()
