"""
Wait-for-user node: no-op. interrupt_after this node; on resume, user_choice/user_input_text merged and flow goes to parse_instruction.
"""
from __future__ import annotations

from ..state import OrchestratorState


def wait_for_user(state: OrchestratorState) -> dict:
    """
    Pass-through. After this node we interrupt; when resumed, Command(resume={...}) merges into state and next node is parse_instruction.
    """
    return {}
