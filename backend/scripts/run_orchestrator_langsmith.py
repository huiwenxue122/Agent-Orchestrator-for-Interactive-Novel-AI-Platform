#!/usr/bin/env python3
"""
LangSmith Step 4 for *this* repo: run the Story Flow LangGraph once so a trace appears
in your LangSmith project (same env vars as the onboarding: LANGSMITH_TRACING, etc.).

This replaces the generic ``create_agent`` weather demo — your graph is custom LangGraph.

Usage (from repo root, with venv activated):

  pip install -r requirements.txt   # includes langsmith after requirements update
  PYTHONPATH=backend python backend/scripts/run_orchestrator_langsmith.py

Ensure `.env` in repo root contains at least:
  LANGSMITH_TRACING=true
  LANGSMITH_API_KEY=...
  LANGSMITH_PROJECT=pr-uncommon-town-37   # or your project name
  OPENAI_API_KEY=...                      # for real LLM (optional: without it, stub text still traces)

Optional:
  LANGSMITH_ENDPOINT=https://api.smith.langchain.com
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = _REPO_ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_REPO_ROOT / ".env")


def main() -> int:
    tracing = os.environ.get("LANGSMITH_TRACING", "").lower() in ("1", "true", "yes")
    if not tracing:
        print(
            "WARN: LANGSMITH_TRACING is not true — traces may not be sent. "
            "Set it in .env (see LangSmith Step 3).",
            file=sys.stderr,
        )
    if not os.environ.get("LANGSMITH_API_KEY"):
        print("ERROR: LANGSMITH_API_KEY missing in environment.", file=sys.stderr)
        return 1

    from app.services.orchestrator import default_orchestrator_deps, invoke_new_turn  # noqa: E402

    deps = default_orchestrator_deps()
    session_id = "langsmith-orchestrator-smoke"
    state = {
        "session_id": session_id,
        "current_node_id": "root",
        "is_initial_turn": True,
        "story_world_summary": "A traveler enters a foggy forest at dusk; distant bells ring.",
    }

    result = invoke_new_turn(session_id, state, deps=deps)

    seg = (result.get("final_segment_text") or "")[:280]
    print("--- final_segment_text (preview) ---")
    print(seg or "(empty)")
    print("--- hints ---")
    for h in result.get("hints") or []:
        print(f"  {h.get('id')}: {h.get('text', '')[:80]}...")
    proj = os.environ.get("LANGSMITH_PROJECT", "(default)")
    print(f"\nOpen LangSmith → Tracing → project `{proj}` for this run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
