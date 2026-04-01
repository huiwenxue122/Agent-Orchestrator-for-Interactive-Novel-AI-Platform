#!/usr/bin/env python3
"""
Print the compiled Story Flow graph as Mermaid (static structure).

Usage (from **repository root**, i.e. the folder that contains ``backend/``):

  PYTHONPATH=backend python backend/scripts/print_orchestrator_mermaid.py
  PYTHONPATH=backend python backend/scripts/print_orchestrator_mermaid.py --out orchestrator_graph.mmd
  PYTHONPATH=backend python backend/scripts/print_orchestrator_mermaid.py --png graph.png

From inside ``backend/`` use:

  PYTHONPATH=. python scripts/print_orchestrator_mermaid.py --png graph.png

Not valid: ``python scripts/...`` from repo root (file lives under ``backend/scripts/``).
Not valid: ``python backend/scripts/...`` from inside ``backend/`` (doubles ``backend/``).

Paste Mermaid output into https://mermaid.live to render.

PNG (optional): needs system Graphviz + ``pip install pygraphviz`` (or LangGraph's bundled renderer).

This shows the LangGraph orchestration topology, not Neo4j Aura data.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Repo root: .../Agent-Orchestrator-.../
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(_ROOT / "backend"))

from app.services.orchestrator.graph import story_flow_graph  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Print orchestrator LangGraph as Mermaid")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write Mermaid to this file instead of stdout",
    )
    parser.add_argument(
        "--png",
        type=Path,
        default=None,
        metavar="FILE",
        help="Write graph as PNG (requires Graphviz; see script docstring)",
    )
    args = parser.parse_args()

    graph = story_flow_graph.get_graph()
    mermaid = graph.draw_mermaid()

    if args.png:
        try:
            png_bytes = graph.draw_mermaid_png()
        except Exception as e:
            print(
                "PNG export failed. Install Graphviz (e.g. brew install graphviz) "
                "and pygraphviz, or use Mermaid text + https://mermaid.live instead.\n"
                f"Error: {e}",
                file=sys.stderr,
            )
            raise SystemExit(1) from e
        args.png.write_bytes(png_bytes)
        print(f"Wrote {args.png}", file=sys.stderr)
        return

    if args.out:
        args.out.write_text(mermaid, encoding="utf-8")
        print(f"Wrote {args.out}", file=sys.stderr)
    else:
        print(mermaid)


if __name__ == "__main__":
    main()
