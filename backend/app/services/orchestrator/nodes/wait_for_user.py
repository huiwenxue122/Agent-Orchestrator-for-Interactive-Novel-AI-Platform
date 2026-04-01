"""
Wait for user — no-op body; interrupt_after this node for Human-in-the-Loop.
"""
from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from ..state import OrchestratorState


def wait_for_user(state: OrchestratorState, config: RunnableConfig) -> dict:
    return {}
