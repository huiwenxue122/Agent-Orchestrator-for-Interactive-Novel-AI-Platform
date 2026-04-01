"""
Injectable services for the Story Flow orchestrator.
Pass via invoke config: {"configurable": {"thread_id": "...", "orchestrator_deps": deps}}.
"""
from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from .state import OrchestratorState


class VerifyResult:
    __slots__ = ("ok", "feedback", "filtered_text")

    def __init__(self, ok: bool, feedback: str | None = None, filtered_text: str | None = None):
        self.ok = ok
        self.feedback = feedback
        self.filtered_text = filtered_text


# ----- Protocols -----


class SessionService(Protocol):
    def ensure_session(self, state: OrchestratorState) -> None: ...

    def on_segment_committed(self, state: OrchestratorState, segment_text: str) -> None: ...


class PromptReinforcementService(Protocol):
    def reinforce(self, state: OrchestratorState) -> dict[str, Any]: ...


class ContextRAGService(Protocol):
    def build(self, state: OrchestratorState, reinforced: dict[str, Any]) -> dict[str, Any]: ...


class KnowledgeGraphService(Protocol):
    def query_for_rag(self, state: OrchestratorState) -> list[dict[str, Any]]: ...

    def apply_segment(self, state: OrchestratorState, segment_text: str) -> str: ...


class StoryLLMService(Protocol):
    def generate_segment(
        self,
        state: OrchestratorState,
        *,
        system_prompt: str,
        user_prompt: str,
        on_token: Callable[[str], None] | None = None,
    ) -> str: ...


class VerifyService(Protocol):
    def verify(self, state: OrchestratorState, text: str) -> VerifyResult: ...


class HintService(Protocol):
    def suggest(self, state: OrchestratorState) -> list[dict[str, Any]]: ...


class UserManagementService(Protocol):
    def on_hints_presented(self, state: OrchestratorState, hints: list[dict[str, Any]]) -> None: ...


# ----- Default implementations -----


class InMemorySessionService:
    """Minimal session bookkeeping for dev/tests."""

    def __init__(self) -> None:
        self._seen: set[str] = set()

    def ensure_session(self, state: OrchestratorState) -> None:
        sid = state.get("session_id")
        if not sid:
            raise ValueError("session_id is required")
        self._seen.add(sid)

    def on_segment_committed(self, state: OrchestratorState, segment_text: str) -> None:
        _ = segment_text


class DefaultPromptReinforcement:
    def reinforce(self, state: OrchestratorState) -> dict[str, Any]:
        choice = state.get("user_choice")
        custom = state.get("user_input_text")
        parts: list[str] = []
        if choice:
            parts.append(f"The player selected branch / hint: {choice}.")
        if custom:
            parts.append(f"The player wrote a custom action: {custom}.")
        if not parts:
            parts.append("Opening turn: continue from the story setup without a prior player branch.")
        user_line = " ".join(parts)
        style = state.get("style_tags")
        style_suffix = ""
        if style:
            if isinstance(style, list):
                style_suffix = " Preferred tone/tags: " + ", ".join(str(s) for s in style)
            else:
                style_suffix = f" Preferred tone/tags: {style}"
        return {
            "user_line": user_line,
            "system_suffix": (
                "You are writing the next short segment of an interactive novel. "
                "Stay consistent with prior facts; do not resolve all tension in one beat."
                + style_suffix
            ),
        }


class DefaultContextRAG:
    def build(self, state: OrchestratorState, reinforced: dict[str, Any]) -> dict[str, Any]:
        return {
            "global_summary": state.get("story_world_summary") or "",
            "recent_summary": state.get("recent_story_summary") or "",
            "recent_dialogue": state.get("recent_dialogue") or [],
            "reinforced_user_line": reinforced.get("user_line", ""),
        }


class InMemoryKnowledgeGraph:
    def __init__(self) -> None:
        self._relations: dict[str, list[dict[str, Any]]] = {}

    def query_for_rag(self, state: OrchestratorState) -> list[dict[str, Any]]:
        sid = state.get("session_id") or ""
        return list(self._relations.get(sid, []))

    def apply_segment(self, state: OrchestratorState, segment_text: str) -> str:
        sid = state.get("session_id") or "default"
        snapshot_id = f"kg_{uuid.uuid4().hex[:12]}"
        self._relations.setdefault(sid, []).append(
            {
                "snapshot_id": snapshot_id,
                "snippet": (segment_text or "")[:200],
            }
        )
        return snapshot_id


class OpenAIStoryLLM:
    """Uses OPENAI_API_KEY when set; otherwise stub text."""

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.environ.get("ORCHESTRATOR_LLM_MODEL", "gpt-4o-mini")

    def generate_segment(
        self,
        state: OrchestratorState,
        *,
        system_prompt: str,
        user_prompt: str,
        on_token: Callable[[str], None] | None = None,
    ) -> str:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return (
                f"[Stub LLM — set OPENAI_API_KEY for live generation]\n\n"
                f"{user_prompt}\n\n"
                f"The mist thickens; the path ahead splits three ways."
            )
        try:
            from openai import OpenAI
        except ImportError:
            return "[Stub LLM — install openai package]\n\n" + user_prompt[:500]

        client = OpenAI(api_key=api_key)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        if on_token is None:
            resp = client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=False,
            )
            return (resp.choices[0].message.content or "").strip()
        chunks: list[str] = []
        for event in client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
        ):
            delta = event.choices[0].delta.content or ""
            if delta:
                chunks.append(delta)
                on_token(delta)
        return "".join(chunks).strip()


class DefaultVerifyService:
    """Safety (lightweight) + optional empty-text retry trigger."""

    _BLOCK = re.compile(r"\b(kill yourself|suicide)\b", re.I)

    def verify(self, state: OrchestratorState, text: str) -> VerifyResult:
        t = (text or "").strip()
        if not t:
            return VerifyResult(ok=False, feedback="empty_generation", filtered_text=t)
        if self._BLOCK.search(t):
            return VerifyResult(
                ok=False,
                feedback="safety_block",
                filtered_text="[Segment withheld by safety filter.]",
            )
        return VerifyResult(ok=True, feedback=None, filtered_text=t)


class DefaultHintService:
    def suggest(self, state: OrchestratorState) -> list[dict[str, Any]]:
        tension = state.get("emotion_tone") or "rising"
        return [
            {"id": "A", "text": f"Press forward: confront what was hinted at. ({tension})", "type": "plot"},
            {"id": "B", "text": "Step back and observe; look for another way.", "type": "exploration"},
            {"id": "C", "text": "Speak to the nearest character; shift the emotional line.", "type": "character"},
        ]


@dataclass
class DefaultUserManagement:
    events: list[dict[str, Any]] = field(default_factory=list)

    def on_hints_presented(self, state: OrchestratorState, hints: list[dict[str, Any]]) -> None:
        self.events.append(
            {
                "session_id": state.get("session_id"),
                "hints": [h.get("id") for h in hints],
            }
        )


@dataclass
class OrchestratorDeps:
    session: SessionService
    prompt: PromptReinforcementService
    context: ContextRAGService
    kg: KnowledgeGraphService
    llm: StoryLLMService
    verify: VerifyService
    hints: HintService
    users: UserManagementService


def default_orchestrator_deps() -> OrchestratorDeps:
    return OrchestratorDeps(
        session=InMemorySessionService(),
        prompt=DefaultPromptReinforcement(),
        context=DefaultContextRAG(),
        kg=InMemoryKnowledgeGraph(),
        llm=OpenAIStoryLLM(),
        verify=DefaultVerifyService(),
        hints=DefaultHintService(),
        users=DefaultUserManagement(),
    )


_DEFAULT_DEPS = default_orchestrator_deps()


def get_orchestrator_deps(config: Any | None) -> OrchestratorDeps:
    if config is None:
        return _DEFAULT_DEPS
    get = getattr(config, "get", None)
    if get is None:
        return _DEFAULT_DEPS
    configurable = get("configurable") or {}
    if not isinstance(configurable, dict):
        return _DEFAULT_DEPS
    deps = configurable.get("orchestrator_deps")
    if deps is not None:
        return deps
    return _DEFAULT_DEPS
