"""
Output — final segment exposed to SSE / IF-Line persistence.
"""
from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from ..state import OrchestratorState


def output(state: OrchestratorState, config: RunnableConfig) -> dict:
    text = state.get("post_processed_text") or state.get("generated_text") or ""
    return {
        "final_segment_text": text.strip(),
    }
