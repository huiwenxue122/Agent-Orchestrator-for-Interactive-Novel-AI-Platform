"""
LLM generate — calls injected StoryLLMService; optional streaming callback via config.
"""
from __future__ import annotations

from langchain_core.runnables import RunnableConfig

from ..deps import get_orchestrator_deps
from ..state import OrchestratorState


def llm_generate(state: OrchestratorState, config: RunnableConfig) -> dict:
    deps = get_orchestrator_deps(config)
    reinforced = state.get("reinforced_prompt") or {}
    ctx = state.get("assembled_context") or {}
    ctx_block = ctx.get("context_json") or str(ctx)[:8000]

    system_prompt = (
        (reinforced.get("system_suffix") or "").strip()
        + "\n\nUse the following retrieved context (summaries, dialogue, KG relations). "
        "Do not contradict established facts.\n\n"
        + ctx_block
    )
    user_prompt = reinforced.get("user_line") or "Continue the story."

    configurable = config.get("configurable") or {}
    on_token = configurable.get("llm_stream_callback")

    text = deps.llm.generate_segment(
        state,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        on_token=on_token,
    )
    return {"generated_text": text}
