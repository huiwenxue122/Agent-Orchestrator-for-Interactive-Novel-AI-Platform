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

    # ----- Context Assembly output -----
    assembled_context: Optional[dict]  # { global_summary, recent_summary, kg_relations, ... }

    # ----- LLM & post-process -----
    generated_text: Optional[str]
    post_processed_text: Optional[str]

    # ----- Update State output -----
    kg_snapshot_id: Optional[str]
    emotion_tone: Optional[str]

    # ----- Hint output (pushed to frontend) -----
    hints: Optional[list[dict]]  # 3 items: { "id", "text", "type?", ... }

    # ----- Turn control -----
    is_initial_turn: bool

    # ----- Verify / retry (context_verify -> context_rag loop) -----
    verify_ok: Optional[bool]
    rag_retry_count: Optional[int]
    verify_feedback: Optional[str]

    # ----- Output -----
    final_segment_text: Optional[str]


def merge_state(left: dict, right: dict) -> dict:
    """Merge right into left; right overwrites None/absent keys. Used as reducer if needed."""
    out = dict(left)
    for k, v in right.items():
        if v is not None or k not in out:
            out[k] = v
    return out
