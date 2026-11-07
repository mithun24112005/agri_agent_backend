"""
LLM Execution Resilience and Multi-Model Fallback Manager (Phase 4 / v2.1).
Provides controlled retries, timeout handling, separate handling for transient RPM vs TPD quota exhaustion,
and automatic fallback between configured models (e.g. openai/gpt-oss-120b -> openai/gpt-oss-20b).
Logs latency and error categories without exposing sensitive tokens or headers.
"""

import os
import time
import asyncio
from typing import Any, Optional, Dict, List, Type
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

PRIMARY_MODEL = os.getenv("PRIMARY_LLM_MODEL", os.getenv("SUPERVISOR_LLM_MODEL", "groq:openai/gpt-oss-120b"))
FALLBACK_MODEL = os.getenv("FALLBACK_LLM_MODEL", "groq:openai/gpt-oss-20b")

_models_cache: Dict[str, Any] = {}

def get_chat_model(model_name: str):
    """Retrieve or initialize a chat model instance."""
    if model_name not in _models_cache:
        _models_cache[model_name] = init_chat_model(model_name)
    return _models_cache[model_name]

def classify_llm_error(error_str: str) -> str:
    """Classify error into actionable failure categories without sensitive exposure."""
    err_low = error_str.lower()
    if "tpd" in err_low or "tokens per day" in err_low or "daily quota" in err_low:
        return "QUOTA_EXHAUSTED_DAILY_TPD"
    if "rate limit" in err_low or "rpm" in err_low or "429" in err_low:
        return "RATE_LIMIT_TRANSIENT_RPM"
    if "tool call validation" in err_low or "tool choice" in err_low or "400" in err_low:
        return "TOOL_SCHEMA_VALIDATION_ERROR"
    if "timeout" in err_low or "timed out" in err_low:
        return "TIMEOUT_ERROR"
    if "500" in err_low or "503" in err_low:
        return "PROVIDER_SERVICE_UNAVAILABLE"
    return "UNKNOWN_LLM_ERROR"

async def invoke_resiliently(
    prompt: ChatPromptTemplate,
    input_data: Dict[str, Any],
    structured_output: Optional[Type[BaseModel]] = None,
    timeout_seconds: float = 15.0,
    max_retries: int = 2
) -> Any:
    """
    Execute an LLM chain with multi-model fallback and quota resilience.
    1. Attempts primary model with timeout.
    2. If daily quota (TPD) is exhausted, immediately switches to fallback model.
    3. If transient RPM occurs, waits briefly and retries.
    4. If primary model fails completely, executes on fallback model.
    """
    models_to_try = [PRIMARY_MODEL]
    if FALLBACK_MODEL and FALLBACK_MODEL != PRIMARY_MODEL:
        models_to_try.append(FALLBACK_MODEL)

    last_error = None

    for model_name in models_to_try:
        model = get_chat_model(model_name)
        if structured_output:
            chain = prompt | model.with_structured_output(structured_output)
        else:
            chain = prompt | model

        for attempt in range(max_retries + 1):
            start_time = time.perf_counter()
            try:
                result = await asyncio.wait_for(chain.ainvoke(input_data), timeout=timeout_seconds)
                latency_ms = (time.perf_counter() - start_time) * 1000
                print(f"[LLM SUCCESS] Model: {model_name} | Latency: {latency_ms:.1f}ms | Attempt: {attempt + 1}")
                return result
            except Exception as e:
                latency_ms = (time.perf_counter() - start_time) * 1000
                err_category = classify_llm_error(str(e))
                last_error = e

                print(f"[LLM FAILURE] Model: {model_name} | Category: {err_category} | Latency: {latency_ms:.1f}ms | Attempt: {attempt + 1}")

                # Immediate fallback on quota exhaustion (do not waste retries)
                if err_category == "QUOTA_EXHAUSTED_DAILY_TPD":
                    print(f"[LLM RESILIENCE] Daily TPD limit reached on {model_name}. Switching immediately to fallback model.")
                    break  # Break inner retry loop to try next model

                # Transient rate limit (RPM) -> wait 2s and retry
                if err_category == "RATE_LIMIT_TRANSIENT_RPM" and attempt < max_retries:
                    wait_time = 2.0 * (attempt + 1)
                    print(f"[LLM RESILIENCE] Transient RPM rate limit. Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                    continue

                # Tool schema mismatch (HTTP 400) -> retry once, then switch
                if err_category == "TOOL_SCHEMA_VALIDATION_ERROR" and attempt < max_retries:
                    await asyncio.sleep(1.0)
                    continue

                if attempt == max_retries:
                    print(f"[LLM RESILIENCE] Retries exhausted for {model_name}.")

    raise RuntimeError(f"All configured LLM providers failed. Last failure category: {classify_llm_error(str(last_error))}. Root: {last_error}")

