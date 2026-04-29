from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class QuizState(BaseModel):
    id: Optional[UUID] = None
    locked: bool
    generated: bool
    completed: bool = False
    stars_earned: int = 0
    effective_stars: int = 0


class LessonSummary(BaseModel):
    id: UUID
    title: str
    difficulty: str
    order_index: int
    locked: bool
    completed: bool
    stars_earned: int


class ChapterResponse(BaseModel):
    id: UUID
    title: str
    order_index: int
    quiz: QuizState
    lessons: list[LessonSummary]


class CurriculumResponse(BaseModel):
    subject: str
    chapters: list[ChapterResponse]


class LessonDetailResponse(BaseModel):
    id: UUID
    title: str
    difficulty: str
    stars_available: int
    content: dict
