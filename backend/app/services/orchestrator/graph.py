"""
Story Flow Orchestrator — LangGraph (v2).

Main path: parse -> prompt_reinforcement -> context_rag -> llm -> context_verify
  -> (ok) output -> kg_update -> hint_recommendation -> user_management -> wait_for_user -> parse
  -> (not ok) context_rag -> llm (retry loop, capped)

Inject services via config["configurable"]["orchestrator_deps"] (see deps.OrchestratorDeps).
Optional streaming: config["configurable"]["llm_stream_callback"] = callable(str) -> None.
"""
from __future__ import annotations

from typing import Any, Callable

try:
    from langgraph.checkpoint.memory import MemorySaver
except ImportError:
    from langgraph.checkpoint.memory import InMemorySaver as MemorySaver
from langgraph.graph import START, StateGraph
from langgraph.types import Command

from .deps import OrchestratorDeps
from .state import OrchestratorState
from .nodes import (
    parse_instruction,
    wait_for_user,
)
from .nodes.prompt_reinforcement import prompt_reinforcement
from .nodes.context_rag import context_rag
from .nodes.llm import llm_generate
from .nodes.context_verify import context_verify
from .nodes.output import output
from .nodes.kg_update import kg_update
from .nodes.hint_recommendation import hint_recommendation
from .nodes.user_management import user_management


def _route_after_verify(state: OrchestratorState) -> str:
    if state.get("verify_ok"):
        return "ok"
    return "retry"


def build_story_flow_graph(checkpointer=None, *, for_langgraph_api: bool = False):
    """
    Build the Story Flow graph.

    - Local / scripts: pass a checkpointer (default: in-memory) for thread_id + interrupts.
    - LangGraph API / ``langgraph dev`` / Studio: set ``for_langgraph_api=True`` — do **not**
      pass a custom checkpointer; the platform injects persistence and rejects InMemorySaver.
    """
    workflow = StateGraph(OrchestratorState)

    workflow.add_node("parse_instruction", parse_instruction)
    workflow.add_node("prompt_reinforcement", prompt_reinforcement)
    workflow.add_node("context_rag", context_rag)
    workflow.add_node("llm_generate", llm_generate)
    workflow.add_node("context_verify", context_verify)
    workflow.add_node("output", output)
    workflow.add_node("kg_update", kg_update)
    workflow.add_node("hint_recommendation", hint_recommendation)
    workflow.add_node("user_management", user_management)
    workflow.add_node("wait_for_user", wait_for_user)

    workflow.add_edge(START, "parse_instruction")
    workflow.add_edge("parse_instruction", "prompt_reinforcement")
    workflow.add_edge("prompt_reinforcement", "context_rag")
    workflow.add_edge("context_rag", "llm_generate")
    workflow.add_edge("llm_generate", "context_verify")

    workflow.add_conditional_edges(
        "context_verify",
        _route_after_verify,
        {
            "ok": "output",
            "retry": "context_rag",
        },
    )

    workflow.add_edge("output", "kg_update")
    workflow.add_edge("kg_update", "hint_recommendation")
    workflow.add_edge("hint_recommendation", "user_management")
    workflow.add_edge("user_management", "wait_for_user")
    workflow.add_edge("wait_for_user", "parse_instruction")

    if for_langgraph_api:
        return workflow.compile(
            interrupt_after=["wait_for_user"],
        )
    memory = checkpointer if checkpointer is not None else MemorySaver()
    return workflow.compile(
        checkpointer=memory,
        interrupt_after=["wait_for_user"],
    )


_default_checkpointer = MemorySaver()
story_flow_graph = build_story_flow_graph(_default_checkpointer)


def _invoke_config(
    session_id: str,
    *,
    deps: OrchestratorDeps | None = None,
    llm_stream_callback: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    cfg: dict[str, Any] = {"thread_id": session_id}
    if deps is not None:
        cfg["orchestrator_deps"] = deps
    if llm_stream_callback is not None:
        cfg["llm_stream_callback"] = llm_stream_callback
    return {"configurable": cfg}


def invoke_new_turn(
    session_id: str,
    initial_input: OrchestratorState,
    *,
    deps: OrchestratorDeps | None = None,
    llm_stream_callback: Callable[[str], None] | None = None,
):
    return story_flow_graph.invoke(
        initial_input,
        _invoke_config(session_id, deps=deps, llm_stream_callback=llm_stream_callback),
    )


def resume_with_choice(
    session_id: str,
    user_choice: str | None = None,
    user_input_text: str | None = None,
    *,
    deps: OrchestratorDeps | None = None,
    llm_stream_callback: Callable[[str], None] | None = None,
):
    payload: dict[str, Any] = {}
    if user_choice is not None:
        payload["user_choice"] = user_choice
    if user_input_text is not None:
        payload["user_input_text"] = user_input_text
    return story_flow_graph.invoke(
        Command(resume=payload),
        _invoke_config(session_id, deps=deps, llm_stream_callback=llm_stream_callback),
    )


def get_state(session_id: str, checkpoint_id: str | None = None):
    config = {"configurable": {"thread_id": session_id}}
    if checkpoint_id:
        config["configurable"]["checkpoint_id"] = checkpoint_id
    return story_flow_graph.get_state(config)
