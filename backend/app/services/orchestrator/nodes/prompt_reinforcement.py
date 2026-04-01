"""
Prompt reinforcement — style + user branch folded into structured prompt fields.
"""
from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from ..deps import get_orchestrator_deps
from ..state import OrchestratorState


def prompt_reinforcement(state: OrchestratorState, config: RunnableConfig) -> dict:
    deps = get_orchestrator_deps(config)
    reinforced = deps.prompt.reinforce(state)
    return {"reinforced_prompt": reinforced}
