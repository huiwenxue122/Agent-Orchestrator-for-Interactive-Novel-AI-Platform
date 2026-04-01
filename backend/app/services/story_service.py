"""
Story turn service — invokes the LangGraph orchestrator and maps state → API response.

Does not modify graph logic; uses ``invoke_new_turn`` for new threads and
``resume_with_choice`` when a checkpoint exists (interrupt after ``wait_for_user``).
"""
from __future__ import annotations

from typing import Any

from langgraph.types import StateSnapshot

from app.schemas.story import StoryTurnRequest, StoryTurnResponse
from app.services.orchestrator.deps import OrchestratorDeps, default_orchestrator_deps
from app.services.orchestrator.graph import (
    invoke_new_turn,
    resume_with_choice,
    story_flow_graph,
)


class StoryService:
    def __init__(self, deps: OrchestratorDeps | None = None) -> None:
        self._deps = deps or default_orchestrator_deps()

    def _pending_after_interrupt(self, session_id: str) -> bool:
        snap = story_flow_graph.get_state({"configurable": {"thread_id": session_id}})
        return bool(snap.next)

    @staticmethod
    def _graph_current_node_id(snap: StateSnapshot) -> str:
        """Map checkpoint ``next`` to a human-readable graph position (IF-Line node stays in state)."""
        n = snap.next
        if not n:
            return "end"
        first = n[0] if isinstance(n, (tuple, list)) else str(n)
        # After interrupt, the runnable waiting to fire is usually parse_instruction (loop back).
        if first == "parse_instruction":
            return "wait_for_user"
        return first

    def run_turn(self, req: StoryTurnRequest) -> StoryTurnResponse:
        if self._pending_after_interrupt(req.session_id):
            state = resume_with_choice(
                req.session_id,
                user_choice=req.user_choice,
                user_input_text=req.user_input_text,
                deps=self._deps,
            )
        else:
            initial: dict[str, Any] = {
                "session_id": req.session_id,
                "current_node_id": "root",
                "user_input_text": req.user_input_text,
                "user_choice": req.user_choice,
            }
            state = invoke_new_turn(req.session_id, initial, deps=self._deps)
        snap = story_flow_graph.get_state({"configurable": {"thread_id": req.session_id}})
        return self.state_to_response(req.session_id, state, snap)

    @staticmethod
    def state_to_response(
        session_id: str,
        state: dict[str, Any],
        snap: StateSnapshot,
    ) -> StoryTurnResponse:
        cq = state.get("clarification_question")
        graph_node = StoryService._graph_current_node_id(snap)
        if cq:
            status = "needs_clarification"
        elif graph_node == "wait_for_user":
            status = "waiting_for_user"
        else:
            status = "ok"
        return StoryTurnResponse(
            session_id=session_id,
            status=status,
            current_node_id=graph_node,
            generated_text=state.get("generated_text") or "",
            post_processed_text=state.get("post_processed_text") or "",
            clarification_question=cq,
            verify_status=state.get("verify_status"),
            retry_count=int(state.get("retry_count") or 0),
        )
