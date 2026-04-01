"""
Context verify — injected VerifyService; retry loop to context_rag when not ok (capped).
"""
from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from ..deps import get_orchestrator_deps
from ..state import OrchestratorState

MAX_RAG_RETRIES = 3


def context_verify(state: OrchestratorState, config: RunnableConfig) -> dict:
    deps = get_orchestrator_deps(config)
    raw = (state.get("generated_text") or "").strip()
    result = deps.verify.verify(state, raw)
    text = result.filtered_text if result.filtered_text is not None else raw
    retries = state.get("rag_retry_count") or 0

    if not result.ok and retries < MAX_RAG_RETRIES:
        return {
            "post_processed_text": text,
            "verify_ok": False,
            "rag_retry_count": retries + 1,
            "verify_feedback": result.feedback,
        }
    if not result.ok and retries >= MAX_RAG_RETRIES:
        return {
            "post_processed_text": text,
            "verify_ok": True,
            "verify_feedback": f"degraded_accept:{result.feedback}",
        }
    return {
        "post_processed_text": text,
        "verify_ok": True,
        "verify_feedback": result.feedback,
    }
