"""
2. Context Assembly — KG + Vector DB + Sliding Window Summary (README context budget).
"""
from __future__ import annotations

from ..state import OrchestratorState


def context_assembly(state: OrchestratorState) -> dict:
    """
    Assemble: global summary, recent chapter summary, current IF-Line last N rounds, KG retrieval.
    TODO: inject context_engine, kg_service, vector_store.
    """
    # Placeholder: real implementation calls Context Memory Engine + KG query
    return {
        "assembled_context": {
            "global_summary": "",
            "recent_summary": "",
            "kg_relations": [],
            "recent_dialogue": [],
        },
    }
