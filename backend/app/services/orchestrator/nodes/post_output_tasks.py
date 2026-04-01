"""
post_output_tasks — post-output side effects only (not part of generation quality chain).

Sequentially runs: kg_update → hint_recommendation → user_management.
"""
from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from .hint_recommendation import hint_recommendation
from .kg_update import kg_update
from .user_management import user_management
from ..state import OrchestratorState


def post_output_tasks(state: OrchestratorState, config: RunnableConfig) -> dict:
    acc: dict = {}
    acc.update(kg_update(state, config))
    merged: OrchestratorState = {**state, **acc}  # type: ignore[misc]
    acc.update(hint_recommendation(merged, config))
    merged = {**merged, **acc}
    acc.update(user_management(merged, config))
    acc["side_effects_status"] = "done"
    return acc
