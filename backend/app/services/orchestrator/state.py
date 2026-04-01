"""
Orchestrator state schema for the Story Flow LangGraph.
Aligns with README_E.md: IF-Line node fields and context assembly budget.
"""
from typing import Optional

from typing_extensions import TypedDict


class OrchestratorState(TypedDict, total=False):
    """State passed through the story flow graph. All fields optional for incremental updates."""

    # ----- Session & IF-Line (Session Manager) -----
    session_id: str
    current_node_id: str
    parent_node_id: Optional[str]
    user_choice: Optional[str]  # Hint A/B/C or custom; set on resume
    user_input_text: Optional[str]
    style_tags: Optional[list[str]]  # or pass as list in state for prompt reinforcement

    # ----- Optional long-term fields (filled by session / context services) -----
    story_world_summary: Optional[str]
    recent_story_summary: Optional[str]
    recent_dialogue: Optional[list[str]]

    # ----- Prompt reinforcement output -----
    reinforced_prompt: Optional[dict]

    # ----- Context RAG (retrieved / structured context materials, not final LLM prompt) -----
    assembled_context: Optional[dict]

    # ----- Explicit LLM input (built by assemble_prompt; primary input for llm_generate) -----
    assembled_prompt: Optional[dict]  # { "system": str, "user": str, "meta"?: dict }

    # ----- LLM & post-process -----
    generated_text: Optional[str]
    post_processed_text: Optional[str]

    # ----- Update State output (post-output side effects) -----
    kg_snapshot_id: Optional[str]
    emotion_tone: Optional[str]

    # ----- Hint output (pushed to frontend) -----
    hints: Optional[list[dict]]  # 3 items: { "id", "text", "type?", ... }

    # ----- Turn control -----
    is_initial_turn: bool

    # ----- Verify & retry (context_verify + retry_guard) -----
    verify_ok: Optional[bool]  # backward compat: True iff verify_status == "ok"
    verify_status: Optional[str]  # "ok" | "retry" | "fail" | "clarification" (after ask_clarification)
    verify_feedback: Optional[str]
    retry_count: Optional[int]  # increments in retry_guard when a retry is granted
    max_retries: Optional[int]  # default applied in retry_guard if missing
    retry_guard_route: Optional[str]  # RETRY_GUARD_ALLOWED | RETRY_GUARD_EXHAUSTED (see constants.py)

    # Deprecated alias: kept for backward compat with older traces/docs; mirror retry_count in parse
    rag_retry_count: Optional[int]

    # ----- Clarification path (verify fail or retry exhausted) -----
    clarification_question: Optional[str]

    # ----- Post-output side effects -----
    side_effects_status: Optional[str]  # e.g. "done" | "skipped"

    # ----- Output -----
    final_segment_text: Optional[str]


def merge_state(left: dict, right: dict) -> dict:
    """Merge right into left; right overwrites None/absent keys. Used as reducer if needed."""
    out = dict(left)
    for k, v in right.items():
        if v is not None or k not in out:
            out[k] = v
    return out
