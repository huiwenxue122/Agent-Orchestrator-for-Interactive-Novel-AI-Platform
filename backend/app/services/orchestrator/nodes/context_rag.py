"""
Context RAG — retrieval + KG read; outputs ``assembled_context`` (materials, not final LLM prompt).
"""
from __future__ import annotations

import json

from langchain_core.runnables import RunnableConfig

from ..deps import get_orchestrator_deps
from ..state import OrchestratorState


def _context_blob(ctx: dict) -> str:
    try:
        return json.dumps(ctx, ensure_ascii=False)[:8000]
    except (TypeError, ValueError):
        return str(ctx)[:8000]


def context_rag(state: OrchestratorState, config: RunnableConfig) -> dict:
    deps = get_orchestrator_deps(config)
    reinforced = state.get("reinforced_prompt") or {}
    base = deps.context.build(state, reinforced)
    kg_relations = deps.kg.query_for_rag(state)
    assembled = {
        **base,
        "kg_relations": kg_relations,
        "context_json": _context_blob({**base, "kg_relations": kg_relations}),
    }
    return {"assembled_context": assembled}
