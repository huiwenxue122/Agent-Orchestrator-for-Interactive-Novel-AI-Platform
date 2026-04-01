"""
assemble_prompt — single place that builds the final LLM system + user strings.

Semantic split:
- ``assembled_context`` = retrieved / structured materials (from context_rag)
- ``assembled_prompt`` = what ``llm_generate`` consumes (auditable in LangSmith traces)
"""
from __future__ import annotations

import json

from langchain_core.runnables import RunnableConfig

from ..state import OrchestratorState


def _json_preview(obj: object, limit: int = 6000) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False)[:limit]
    except (TypeError, ValueError):
        return str(obj)[:limit]


def assemble_prompt(state: OrchestratorState, config: RunnableConfig) -> dict:
    reinforced = state.get("reinforced_prompt") or {}
    ctx = state.get("assembled_context") or {}

    system_base = (reinforced.get("system_suffix") or "").strip()
    user_task = (reinforced.get("user_line") or "Continue the story.").strip()

    # Highest priority: raw player text and explicit branch choice
    priority_blocks: list[str] = []
    uit = state.get("user_input_text")
    if uit:
        priority_blocks.append(f"【玩家原文 · 最高优先级】\n{uit.strip()}")
    uc = state.get("user_choice")
    if uc:
        priority_blocks.append(f"【所选分支 / Hint】\n{uc.strip()}")

    aux = []
    sw = state.get("story_world_summary")
    if sw:
        aux.append(f"【世界设定】\n{sw.strip()}")
    rs = state.get("recent_story_summary")
    if rs:
        aux.append(f"【近期情节摘要】\n{rs.strip()}")
    rd = state.get("recent_dialogue")
    if rd:
        aux.append(f"【最近对话】\n{_json_preview(rd, 2000)}")

    context_block = ctx.get("context_json") or _json_preview(
        {k: v for k, v in ctx.items() if k != "context_json"},
        8000,
    )

    correction = ""
    rc = int(state.get("retry_count") or 0)
    vf = state.get("verify_feedback")
    if rc > 0 and vf:
        correction = (
            f"\n\n【生成修正提示 · 第 {rc} 次重试】\n"
            f"前次问题：{vf}\n请在不违背玩家意图的前提下修正。"
        )

    system = (
        system_base
        + "\n\n---\n辅助上下文（不得覆盖玩家原文/分支意图）：\n"
        + context_block
        + correction
    )

    user_parts = []
    if priority_blocks:
        user_parts.append("\n\n".join(priority_blocks))
    user_parts.append(f"【续写任务】\n{user_task}")
    user = "\n\n---\n".join(user_parts)

    payload = {
        "system": system.strip(),
        "user": user.strip(),
        "meta": {
            "has_user_input_text": bool(uit),
            "has_user_choice": bool(uc),
            "retry_count_for_prompt": rc,
            "has_verify_correction": bool(correction),
        },
    }
    return {"assembled_prompt": payload}
