"""
Story Flow Orchestrator — LangGraph (v3).

Main quality chain:
  parse → prompt_reinforcement → context_rag → assemble_prompt → llm_generate → context_verify

Routing:
  verify ok → output → post_output_tasks (side effects) → wait_for_user → parse
  verify retry → retry_guard → context_rag | ask_clarification
  verify fail → ask_clarification → wait_for_user → parse

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

from .constants import (
    RETRY_GUARD_ALLOWED,
    RETRY_GUARD_EXHAUSTED,
    VERIFY_ROUTE_FAIL,
    VERIFY_ROUTE_OK,
    VERIFY_ROUTE_RETRY,
)
from .deps import OrchestratorDeps
from .state import OrchestratorState
from .nodes import (
    parse_instruction,
    wait_for_user,
)
from .nodes.prompt_reinforcement import prompt_reinforcement
from .nodes.context_rag import context_rag
from .nodes.assemble_prompt import assemble_prompt
from .nodes.llm import llm_generate
from .nodes.context_verify import context_verify
from .nodes.retry_guard import retry_guard
from .nodes.ask_clarification import ask_clarification
from .nodes.output import output
from .nodes.post_output_tasks import post_output_tasks


def route_after_verify(state: OrchestratorState) -> str:
    vs = state.get("verify_status")
    if vs == VERIFY_ROUTE_OK:
        return VERIFY_ROUTE_OK
    if vs == VERIFY_ROUTE_RETRY:
        return VERIFY_ROUTE_RETRY
    if vs == VERIFY_ROUTE_FAIL:
        return VERIFY_ROUTE_FAIL
    return VERIFY_ROUTE_FAIL


def route_after_retry_guard(state: OrchestratorState) -> str:
    r = state.get("retry_guard_route")
    if r == RETRY_GUARD_ALLOWED:
        return RETRY_GUARD_ALLOWED
    return RETRY_GUARD_EXHAUSTED


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
    workflow.add_node("assemble_prompt", assemble_prompt)
    workflow.add_node("llm_generate", llm_generate)
    workflow.add_node("context_verify", context_verify)
    workflow.add_node("retry_guard", retry_guard)
    workflow.add_node("ask_clarification", ask_clarification)
    workflow.add_node("output", output)
    workflow.add_node("post_output_tasks", post_output_tasks)
    workflow.add_node("wait_for_user", wait_for_user)

    workflow.add_edge(START, "parse_instruction")
    workflow.add_edge("parse_instruction", "prompt_reinforcement")
    workflow.add_edge("prompt_reinforcement", "context_rag")
    workflow.add_edge("context_rag", "assemble_prompt")
    workflow.add_edge("assemble_prompt", "llm_generate")
    workflow.add_edge("llm_generate", "context_verify")

    workflow.add_conditional_edges(
        "context_verify",
        route_after_verify,
        {
            VERIFY_ROUTE_OK: "output",
            VERIFY_ROUTE_RETRY: "retry_guard",
            VERIFY_ROUTE_FAIL: "ask_clarification",
        },
    )

    workflow.add_conditional_edges(
        "retry_guard",
        route_after_retry_guard,
        {
            RETRY_GUARD_ALLOWED: "context_rag",
            RETRY_GUARD_EXHAUSTED: "ask_clarification",
        },
    )

    workflow.add_edge("output", "post_output_tasks")
    workflow.add_edge("post_output_tasks", "wait_for_user")
    workflow.add_edge("ask_clarification", "wait_for_user")
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
