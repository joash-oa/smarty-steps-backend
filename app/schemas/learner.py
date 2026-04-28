from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


class CreateLearnerRequest(BaseModel):
    name: str
    age: int
    grade_level: int
    avatar_emoji: str = "🚀"

    @field_validator("age")
    @classmethod
    def age_in_range(cls, v: int) -> int:
        if not 5 <= v <= 8:
            raise ValueError("Age must be between 5 and 8")
        return v

    @field_validator("grade_level")
    @classmethod
    def grade_in_range(cls, v: int) -> int:
        if not 0 <= v <= 3:
            raise ValueError("Grade level must be between 0 and 3")
        return v


class UpdateLearnerRequest(BaseModel):
    name: Optional[str] = None
    avatar_emoji: Optional[str] = None
    grade_level: Optional[int] = None

    @field_validator("grade_level")
    @classmethod
    def grade_in_range(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not 0 <= v <= 3:
            raise ValueError("Grade level must be between 0 and 3")
        return v


class LearnerResponse(BaseModel):
    id: UUID
    name: str
    age: int
    grade_level: int
    avatar_emoji: str
    total_stars: int
    level: int
    xp: int
    streak_days: int
    last_active_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class LearnerListResponse(BaseModel):
    learners: list[LearnerResponse]
