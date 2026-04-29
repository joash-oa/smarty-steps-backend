from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Lesson, LessonProgress


class DashboardDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_stats(self, learner_id: UUID) -> dict:
        result = await self.session.execute(
            select(LessonProgress, Lesson)
            .join(Lesson, LessonProgress.lesson_id == Lesson.id)
            .where(
                LessonProgress.learner_id == learner_id,
                LessonProgress.completed == True,  # noqa: E712
            )
            .order_by(LessonProgress.completed_at.desc())
        )
        rows = result.all()

        time_per_subject: dict[str, int] = {"math": 0, "science": 0, "english": 0}
        mastered = []
        needs_practice = []
        recent_activity = []

        for progress, lesson in rows:
            subject = lesson.subject
            if subject in time_per_subject:
                time_per_subject[subject] += progress.time_seconds or 0

            if progress.stars_earned == 3:
                mastered.append(
                    {
                        "lesson_id": str(lesson.id),
                        "title": lesson.title,
                        "subject": lesson.subject,
                    }
                )
            elif progress.stars_earned <= 1:
                needs_practice.append(
                    {
                        "lesson_id": str(lesson.id),
                        "title": lesson.title,
                        "subject": lesson.subject,
                    }
                )

            if len(recent_activity) < 10:
                recent_activity.append(
                    {
                        "lesson_id": str(lesson.id),
                        "title": lesson.title,
                        "stars_earned": progress.stars_earned or 0,
                        "completed_at": progress.completed_at,
                    }
                )

        return {
            "time_per_subject": time_per_subject,
            "mastered": mastered,
            "needs_practice": needs_practice,
            "recent_activity": recent_activity,
        }
