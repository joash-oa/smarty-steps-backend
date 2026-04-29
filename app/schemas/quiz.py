from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel


class QuizDetailResponse(BaseModel):
    id: UUID
    difficulty: str
    exercises: list[dict]


class CheckQuizAnswerRequest(BaseModel):
    exercise_id: str
    answer: dict[str, Any]


class CheckQuizAnswerResponse(BaseModel):
    correct: bool
    explanation: str | None = None


class SubmitQuizRequest(BaseModel):
    time_seconds: int
    answers: dict[str, dict[str, Any]]


class SubmitQuizResponse(BaseModel):
    stars_earned: int
    effective_stars: int
    correct: int
    total: int
    xp_earned: int
    level_up: bool
    new_level: int
