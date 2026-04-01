"""
ask_clarification — when verify marks fail or retries are exhausted; user-visible prompt, then interrupt.
"""
from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from ..state import OrchestratorState


def ask_clarification(state: OrchestratorState, config: RunnableConfig) -> dict:
    fb = (state.get("verify_feedback") or "").strip()
    if not fb:
        fb = "这一段没法在不动笔的情况下安全推进。"

    lines = [
        "笔锋在此轻轻一顿——需要你的一点回应，故事才能继续。",
        "",
        f"原因：{fb}",
        "",
        "你可以：换一句更具体的行动、补充一个关键细节，或选一条更温和的分支。",
    ]
    text = "\n".join(lines)

    return {
        "clarification_question": text,
        "final_segment_text": text,
        "hints": [],
        "verify_status": "clarification",
        "post_processed_text": text,
        "side_effects_status": "skipped",
    }
