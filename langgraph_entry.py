"""
LangGraph CLI / Studio entry: exposes the compiled graph for `langgraph dev`.

The orchestrator lives under `backend/app/`; this file prepends `backend/` to sys.path
so `import app.services...` works when the CLI loads this module by file path.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app.services.orchestrator.graph import build_story_flow_graph  # noqa: E402

# LangGraph API / Studio: no custom checkpointer (platform manages persistence).
story_flow_graph = build_story_flow_graph(for_langgraph_api=True)

__all__ = ["story_flow_graph"]
