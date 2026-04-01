"""
retry_guard — decides whether another RAG+LLM attempt is allowed after verify requested retry.
"""
from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from ..constants import DEFAULT_MAX_RETRIES, RETRY_GUARD_ALLOWED, RETRY_GUARD_EXHAUSTED
from ..state import OrchestratorState


def retry_guard(state: OrchestratorState, config: RunnableConfig) -> dict:
    max_r = state.get("max_retries")
    if max_r is None:
        max_r = DEFAULT_MAX_RETRIES
    max_r = int(max_r)
    rc = int(state.get("retry_count") or 0)

    if rc < max_r:
        return {
            "retry_count": rc + 1,
            # Same strings as route_after_retry_guard return + conditional_edges keys (graph.py).
            "retry_guard_route": RETRY_GUARD_ALLOWED,
            "rag_retry_count": rc + 1,
        }
    return {
        "retry_guard_route": RETRY_GUARD_EXHAUSTED,
    }
