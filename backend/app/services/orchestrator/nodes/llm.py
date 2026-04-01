"""
LLM generate — consumes ``assembled_prompt`` only (built by assemble_prompt).
"""
from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from ..deps import get_orchestrator_deps
from ..state import OrchestratorState


def llm_generate(state: OrchestratorState, config: RunnableConfig) -> dict:
    deps = get_orchestrator_deps(config)
    payload = state.get("assembled_prompt") or {}
    system_prompt = (payload.get("system") or "").strip()
    user_prompt = (payload.get("user") or "Continue the story.").strip()

    configurable = config.get("configurable") or {}
    on_token = configurable.get("llm_stream_callback")

    text = deps.llm.generate_segment(
        state,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        on_token=on_token,
    )
    return {"generated_text": text}
