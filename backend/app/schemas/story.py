"""HTTP request/response models for the story turn API (subset of orchestrator state)."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class StoryTurnRequest(BaseModel):
    session_id: str = Field(..., min_length=1, description="Thread id for LangGraph checkpointing")
    user_input_text: Optional[str] = None
    user_choice: Optional[str] = None


class StoryTurnResponse(BaseModel):
    session_id: str
    status: Literal["ok", "needs_clarification", "waiting_for_user"] = Field(
        ...,
        description="Clarification needed, paused after wait_for_user, or ok/end.",
    )
    current_node_id: str = Field(
        ...,
        description="Graph halt hint for debugging (e.g. wait_for_user when next is parse_instruction).",
    )
    generated_text: str = ""
    post_processed_text: str = ""
    clarification_question: Optional[str] = None
    verify_status: Optional[str] = None
    retry_count: int = 0
