from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Lesson, LessonProgress


class DashboardDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_completed_progress_rows(
        self, learner_id: UUID
    ) -> list[tuple[LessonProgress, Lesson]]:
        result = await self.session.execute(
            select(LessonProgress, Lesson)
            .join(Lesson, LessonProgress.lesson_id == Lesson.id)
            .where(
                LessonProgress.learner_id == learner_id,
                LessonProgress.completed == True,  # noqa: E712
            )
            .order_by(LessonProgress.completed_at.desc())
        )
        return list(result.all())
