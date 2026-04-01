"""FastAPI routes: health + story turn."""
from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, Depends

from app.schemas.story import StoryTurnRequest, StoryTurnResponse
from app.services.story_service import StoryService

health_router = APIRouter(tags=["health"])
story_router = APIRouter(prefix="/api/story", tags=["story"])


@health_router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@lru_cache
def get_story_service() -> StoryService:
    return StoryService()


@story_router.post("/turn", response_model=StoryTurnResponse)
def story_turn(
    body: StoryTurnRequest,
    svc: StoryService = Depends(get_story_service),
) -> StoryTurnResponse:
    return svc.run_turn(body)
