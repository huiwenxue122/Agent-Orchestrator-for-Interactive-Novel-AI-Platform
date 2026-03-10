"""
1. Parse User Instruction — validate session, resolve current IF-Line node, normalize user choice.
"""
from __future__ import annotations

from ..state import OrchestratorState


def parse_instruction(state: OrchestratorState) -> dict:
    """
    - First turn: use seed/opening from session; no user_choice.
    - Later turns: user_choice / user_input_text already in state (from resume).
    - Call Session/IF-Line Manager to validate session and get current_node_id / parent_node_id.
    """
    # TODO: inject session_manager; validate state["session_id"], load IF-Line node
    # session_manager.get_current_node(state["session_id"]) -> current_node_id, parent_node_id
    return {
        "is_initial_turn": state.get("user_choice") is None and state.get("user_input_text") is None,
    }
