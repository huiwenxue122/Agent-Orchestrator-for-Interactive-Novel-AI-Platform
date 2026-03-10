"""
Story Flow Orchestrator — LangGraph definition.
Cycle: parse_instruction -> ... -> hint_generation -> wait_for_user -> parse_instruction.
interrupt_after wait_for_user for Human-in-the-Loop; checkpoint every step for backtrack.
"""
from __future__ import annotations

try:
    from langgraph.checkpoint.memory import MemorySaver
except ImportError:
    from langgraph.checkpoint.memory import InMemorySaver as MemorySaver
from langgraph.graph import START, StateGraph
from langgraph.types import Command

from .state import OrchestratorState
from .nodes import (
    parse_instruction,
    context_assembly,
    llm_generate,
    post_process,
    update_state,
    hint_generation,
    wait_for_user,
)


def build_story_flow_graph(checkpointer=None):
    """
    Build the Story Flow graph. With checkpointer, use config={"configurable": {"thread_id": session_id}}.
    For backtrack, pass checkpoint_id in config to resume from a historical node.
    """
    workflow = StateGraph(OrchestratorState)

    workflow.add_node("parse_instruction", parse_instruction)
    workflow.add_node("context_assembly", context_assembly)
    workflow.add_node("llm_generate", llm_generate)
    workflow.add_node("post_process", post_process)
    workflow.add_node("update_state", update_state)
    workflow.add_node("hint_generation", hint_generation)
    workflow.add_node("wait_for_user", wait_for_user)

    workflow.add_edge(START, "parse_instruction")
    workflow.add_edge("parse_instruction", "context_assembly")
    workflow.add_edge("context_assembly", "llm_generate")
    workflow.add_edge("llm_generate", "post_process")
    workflow.add_edge("post_process", "update_state")
    workflow.add_edge("update_state", "hint_generation")
    workflow.add_edge("hint_generation", "wait_for_user")
    workflow.add_edge("wait_for_user", "parse_instruction")

    memory = checkpointer if checkpointer is not None else MemorySaver()
    compiled = workflow.compile(
        checkpointer=memory,
        interrupt_after=["wait_for_user"],
    )
    return compiled


# Convenience: default in-memory graph for dev
_default_checkpointer = MemorySaver()
story_flow_graph = build_story_flow_graph(_default_checkpointer)


def invoke_new_turn(session_id: str, initial_input: OrchestratorState):
    """Start or continue a turn: invoke graph; will interrupt after hint_generation -> wait_for_user."""
    config = {"configurable": {"thread_id": session_id}}
    return story_flow_graph.invoke(initial_input, config)


def resume_with_choice(session_id: str, user_choice: str | None = None, user_input_text: str | None = None):
    """Resume after user selected a hint (or custom text). Pass resume payload."""
    payload = {}
    if user_choice is not None:
        payload["user_choice"] = user_choice
    if user_input_text is not None:
        payload["user_input_text"] = user_input_text
    config = {"configurable": {"thread_id": session_id}}
    return story_flow_graph.invoke(Command(resume=payload), config)


def get_state(session_id: str, checkpoint_id: str | None = None):
    """Get current or historical state (for backtrack / timeline)."""
    config = {"configurable": {"thread_id": session_id}}
    if checkpoint_id:
        config["configurable"]["checkpoint_id"] = checkpoint_id
    return story_flow_graph.get_state(config)
