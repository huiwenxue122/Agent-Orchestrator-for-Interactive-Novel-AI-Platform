"""FastAPI entrypoint — HTTP → StoryService → LangGraph orchestrator."""
from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import health_router, story_router

app = FastAPI(title="Interactive Novel AI — Story API", version="0.1.0")


@app.get("/")
def root() -> dict[str, str]:
    """Avoid 404 when opening the server base URL in a browser."""
    return {
        "service": "Interactive Novel AI — Story API",
        "docs": "/docs",
        "health": "/health",
        "story_turn": "POST /api/story/turn",
    }


app.include_router(health_router)
app.include_router(story_router)
