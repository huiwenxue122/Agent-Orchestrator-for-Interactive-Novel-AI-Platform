"""
User management — after hints are ready; preference / analytics hooks.
"""
from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from ..deps import get_orchestrator_deps
from ..state import OrchestratorState


def user_management(state: OrchestratorState, config: RunnableConfig) -> dict:
    deps = get_orchestrator_deps(config)
    hints = state.get("hints") or []
    deps.users.on_hints_presented(state, hints)
    return {}
