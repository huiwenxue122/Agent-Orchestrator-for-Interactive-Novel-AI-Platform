"""
3. LLM Generate Story — stream segment; push to frontend via SSE callback.
"""
from __future__ import annotations

from ..state import OrchestratorState


def llm_generate(state: OrchestratorState) -> dict:
    """
    Call AI Engine (LLM Adapter + Prompt Template) with state["assembled_context"] and user_choice.
    Stream tokens; optional stream_callback(state, token) for SSE.
    TODO: inject llm_adapter, prompt_engine; accept config with stream_callback.
    """
    # Placeholder: real implementation streams via callback
    return {
        "generated_text": "(Generated story segment placeholder.)",
    }
