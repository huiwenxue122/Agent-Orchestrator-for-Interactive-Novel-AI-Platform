"""
Parse user instruction — session validation; reset per-user-turn counters and routing scratch.
"""
from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from ..constants import DEFAULT_MAX_RETRIES
from ..deps import get_orchestrator_deps
from ..state import OrchestratorState


def parse_instruction(state: OrchestratorState, config: RunnableConfig) -> dict:
    deps = get_orchestrator_deps(config)
    deps.session.ensure_session(state)

    max_r = state.get("max_retries")
    if max_r is None:
        max_r = DEFAULT_MAX_RETRIES

    return {
        "is_initial_turn": state.get("user_choice") is None and state.get("user_input_text") is None,
        "retry_count": 0,
        "rag_retry_count": 0,
        "max_retries": int(max_r),
        "verify_ok": None,
        "verify_status": None,
        "verify_feedback": None,
        "retry_guard_route": None,
        "clarification_question": None,
        "side_effects_status": None,
        "assembled_prompt": None,
    }
