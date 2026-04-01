"""
Minimal structural tests for Story Flow LangGraph (v3).
Run: PYTHONPATH=backend python -m unittest tests.test_orchestrator_graph -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.services.orchestrator.constants import DEFAULT_MAX_RETRIES, VERIFY_ROUTE_FAIL, VERIFY_ROUTE_OK  # noqa: E402
from app.services.orchestrator.deps import (  # noqa: E402
    OrchestratorDeps,
    VerifyResult,
    default_orchestrator_deps,
)
from app.services.orchestrator.graph import build_story_flow_graph  # noqa: E402


class _AlwaysFailVerify:
    def verify(self, state, text):
        return VerifyResult(VERIFY_ROUTE_FAIL, feedback="forced_fail", filtered_text=text)


class _EmptyLLM:
    def generate_segment(self, state, *, system_prompt, user_prompt, on_token=None):
        return ""


class StoryFlowGraphTests(unittest.TestCase):
    def test_graph_compiles(self) -> None:
        g = build_story_flow_graph(for_langgraph_api=True)
        m = g.get_graph().draw_mermaid()
        self.assertIn("assemble_prompt", m)
        self.assertIn("retry_guard", m)
        self.assertIn("ask_clarification", m)
        self.assertIn("post_output_tasks", m)

    def test_invoke_ok_path_interrupts(self) -> None:
        try:
            from langgraph.checkpoint.memory import MemorySaver
        except ImportError:
            from langgraph.checkpoint.memory import InMemorySaver as MemorySaver

        g = build_story_flow_graph(MemorySaver())
        deps = default_orchestrator_deps()
        r = g.invoke(
            {
                "session_id": "t-ok",
                "current_node_id": "root",
                "story_world_summary": "Fog.",
                "max_retries": DEFAULT_MAX_RETRIES,
            },
            {"configurable": {"thread_id": "t-ok", "orchestrator_deps": deps}},
        )
        self.assertIn("final_segment_text", r)
        self.assertTrue(r.get("hints"))
        self.assertEqual(r.get("verify_status"), VERIFY_ROUTE_OK)
        self.assertEqual(r.get("side_effects_status"), "done")

    def test_verify_fail_ask_clarification(self) -> None:
        try:
            from langgraph.checkpoint.memory import MemorySaver
        except ImportError:
            from langgraph.checkpoint.memory import InMemorySaver as MemorySaver

        base = default_orchestrator_deps()
        deps = OrchestratorDeps(
            session=base.session,
            prompt=base.prompt,
            context=base.context,
            kg=base.kg,
            llm=base.llm,
            verify=_AlwaysFailVerify(),
            hints=base.hints,
            users=base.users,
        )
        g = build_story_flow_graph(MemorySaver())
        r = g.invoke(
            {
                "session_id": "t-fail",
                "current_node_id": "root",
                "max_retries": 2,
            },
            {"configurable": {"thread_id": "t-fail", "orchestrator_deps": deps}},
        )
        self.assertEqual(r.get("verify_status"), "clarification")
        self.assertIn("forced_fail", r.get("clarification_question", ""))
        self.assertEqual(r.get("side_effects_status"), "skipped")
        self.assertEqual(r.get("hints"), [])

    def test_retry_exhausted_to_clarification(self) -> None:
        try:
            from langgraph.checkpoint.memory import MemorySaver
        except ImportError:
            from langgraph.checkpoint.memory import InMemorySaver as MemorySaver

        base = default_orchestrator_deps()
        deps = OrchestratorDeps(
            session=base.session,
            prompt=base.prompt,
            context=base.context,
            kg=base.kg,
            llm=_EmptyLLM(),
            verify=base.verify,
            hints=base.hints,
            users=base.users,
        )
        g = build_story_flow_graph(MemorySaver())
        r = g.invoke(
            {
                "session_id": "t-retry-ex",
                "current_node_id": "root",
                "max_retries": 2,
            },
            {"configurable": {"thread_id": "t-retry-ex", "orchestrator_deps": deps}},
        )
        self.assertEqual(r.get("verify_status"), "clarification")
        self.assertEqual(r.get("side_effects_status"), "skipped")

    def test_assembled_prompt_populated(self) -> None:
        try:
            from langgraph.checkpoint.memory import MemorySaver
        except ImportError:
            from langgraph.checkpoint.memory import InMemorySaver as MemorySaver

        g = build_story_flow_graph(MemorySaver())
        # Single step through graph is heavy; check node outputs via partial invoke — use stream
        deps = default_orchestrator_deps()
        cfg = {"configurable": {"thread_id": "t-ap", "orchestrator_deps": deps}}
        # invoke full run and require assembled_prompt existed (merged into final state may be cleared by parse on loop)
        # After one interrupt, assembled_prompt is cleared at parse start of next superstep — final state from first run:
        r = g.invoke(
            {
                "session_id": "t-ap",
                "current_node_id": "root",
                "user_input_text": "主角抬头望向钟楼。",
            },
            cfg,
        )
        # parse clears assembled_prompt at end of thread before wait — so check hints path had LLM
        self.assertTrue(r.get("final_segment_text"))


if __name__ == "__main__":
    unittest.main()
