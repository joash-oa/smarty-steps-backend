from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ChapterQuiz, LessonProgress


class ProgressDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_progress_for_learner(self, learner_id: UUID) -> list[LessonProgress]:
        return []

    async def get_chapter_quiz(self, learner_id: UUID, chapter_id: UUID) -> Optional[ChapterQuiz]:
        return None
