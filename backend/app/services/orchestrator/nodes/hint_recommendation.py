"""
Hint recommendation — uses final segment + emotion_tone + KG-backed state via HintService.
"""
from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from ..deps import get_orchestrator_deps
from ..state import OrchestratorState


def hint_recommendation(state: OrchestratorState, config: RunnableConfig) -> dict:
    deps = get_orchestrator_deps(config)
    hints = deps.hints.suggest(state)
    return {"hints": hints}
