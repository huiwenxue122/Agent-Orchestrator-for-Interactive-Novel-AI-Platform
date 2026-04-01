"""
Knowledge graph update — write-through after segment is finalized; light emotion tag for hints.
"""
from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from ..deps import get_orchestrator_deps
from ..state import OrchestratorState


def kg_update(state: OrchestratorState, config: RunnableConfig) -> dict:
    deps = get_orchestrator_deps(config)
    text = (state.get("final_segment_text") or state.get("post_processed_text") or "").strip()
    snapshot_id = deps.kg.apply_segment(state, text)
    deps.session.on_segment_committed(state, text)

    n = len(text)
    if n > 600:
        tone = "climax"
    elif n > 200:
        tone = "rising"
    else:
        tone = "lull"
    return {
        "kg_snapshot_id": snapshot_id,
        "emotion_tone": tone,
    }
