"""
4. Post-Process — safety filter, style consistency, KG consistency check.
"""
from __future__ import annotations

from ..state import OrchestratorState


def post_process(state: OrchestratorState) -> dict:
    """
    Safety & Style Filter + consistency check against KG.
    TODO: inject safety_filter, kg_consistency_check.
    """
    text = state.get("generated_text") or ""
    return {
        "post_processed_text": text,
    }
