from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel


class CheckAnswerRequest(BaseModel):
    exercise_id: str
    answer: dict[str, Any]


class CheckAnswerResponse(BaseModel):
    correct: bool
    explanation: str | None = None


class SubmitLessonRequest(BaseModel):
    lesson_id: UUID
    time_seconds: int
    answers: dict[str, dict[str, Any]]


class SubmitLessonResponse(BaseModel):
    stars_earned: int
    correct: int
    total: int
    xp_earned: int
    level_up: bool
    new_level: int


class SubjectSummary(BaseModel):
    subject: str
    lessons_completed: int
    lessons_total: int
    total_stars: int
    chapters_completed: int


class ProgressSummaryResponse(BaseModel):
    summary: list[SubjectSummary]


class LessonProgressDetail(BaseModel):
    id: UUID
    title: str
    difficulty: str
    completed: bool
    stars_earned: int
    score_correct: int | None = None
    score_total: int | None = None


class ChapterProgressDetail(BaseModel):
    id: UUID
    title: str
    order_index: int
    quiz_completed: bool
    quiz_stars_earned: int
    quiz_effective_stars: int
    lessons: list[LessonProgressDetail]


class SubjectProgressResponse(BaseModel):
    subject: str
    chapters: list[ChapterProgressDetail]
