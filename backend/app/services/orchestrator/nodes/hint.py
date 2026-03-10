"""
6. Hint Generation — Narrative-Aware Hint Generator -> 3 options (README Hint Engine).
"""
from __future__ import annotations

from ..state import OrchestratorState


def hint_generation(state: OrchestratorState) -> dict:
    """
    Call Hint Recommender: candidate generation -> ranking -> pick 3.
    TODO: inject hint_recommender (narrative tension, user preference, diversity).
    """
    return {
        "hints": [
            {"id": "A", "text": "Option A placeholder", "type": "plot"},
            {"id": "B", "text": "Option B placeholder", "type": "character"},
            {"id": "C", "text": "Option C placeholder", "type": "exploration"},
        ],
    }
