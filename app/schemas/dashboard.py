from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class TimePerSubject(BaseModel):
    math: int = 0
    science: int = 0
    english: int = 0


class MasteredLesson(BaseModel):
    lesson_id: UUID
    title: str
    subject: str


class NeedsPracticeLesson(BaseModel):
    lesson_id: UUID
    title: str
    subject: str


class RecentActivity(BaseModel):
    lesson_id: UUID
    title: str
    stars_earned: int
    completed_at: Optional[datetime]


class DashboardStatsResponse(BaseModel):
    time_per_subject: TimePerSubject
    mastered: list[MasteredLesson]
    needs_practice: list[NeedsPracticeLesson]
    recent_activity: list[RecentActivity]
