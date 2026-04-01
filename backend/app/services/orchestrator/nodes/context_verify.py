"""
context_verify — sets verify_status for routing: ok | retry | fail (no retry counting here).
"""
from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from ..constants import VERIFY_ROUTE_OK
from ..deps import get_orchestrator_deps
from ..state import OrchestratorState


def context_verify(state: OrchestratorState, config: RunnableConfig) -> dict:
    deps = get_orchestrator_deps(config)
    raw = (state.get("generated_text") or "").strip()
    result = deps.verify.verify(state, raw)
    text = result.filtered_text if result.filtered_text is not None else raw
    outcome = result.outcome

    return {
        "post_processed_text": text,
        "verify_status": outcome,
        "verify_ok": outcome == VERIFY_ROUTE_OK,
        "verify_feedback": result.feedback,
    }
