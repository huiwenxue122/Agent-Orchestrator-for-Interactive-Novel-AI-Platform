"""
Parse user instruction — session validation, per-turn counters.
"""
from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from ..deps import get_orchestrator_deps
from ..state import OrchestratorState


def parse_instruction(state: OrchestratorState, config: RunnableConfig) -> dict:
    deps = get_orchestrator_deps(config)
    deps.session.ensure_session(state)
    return {
        "is_initial_turn": state.get("user_choice") is None and state.get("user_input_text") is None,
        "rag_retry_count": 0,
        "verify_ok": None,
        "verify_feedback": None,
    }
