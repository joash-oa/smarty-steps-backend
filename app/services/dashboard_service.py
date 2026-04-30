from uuid import UUID

from app.core.constants import (
    DASHBOARD_MASTERED_STARS,
    DASHBOARD_NEEDS_PRACTICE_MAX_STARS,
    DASHBOARD_RECENT_ACTIVITY_LIMIT,
)
from app.daos.dashboard_dao import DashboardDAO
from app.db.models import Parent


class DashboardService:
    def __init__(self, dao: DashboardDAO):
        self.dao = dao

    async def get_stats(self, parent: Parent, learner_id: UUID, learner_svc) -> dict:
        learner = await learner_svc.get(parent, learner_id)
        rows = await self.dao.get_completed_progress_rows(learner.id)

        time_per_subject: dict[str, int] = {"math": 0, "science": 0, "english": 0}
        mastered = []
        needs_practice = []
        recent_activity = []

        for progress, lesson in rows:
            subject = lesson.subject
            if subject in time_per_subject:
                time_per_subject[subject] += progress.time_seconds or 0

            if progress.stars_earned == DASHBOARD_MASTERED_STARS:
                mastered.append(
                    {
                        "lesson_id": str(lesson.id),
                        "title": lesson.title,
                        "subject": lesson.subject,
                    }
                )
            elif progress.stars_earned <= DASHBOARD_NEEDS_PRACTICE_MAX_STARS:
                needs_practice.append(
                    {
                        "lesson_id": str(lesson.id),
                        "title": lesson.title,
                        "subject": lesson.subject,
                    }
                )

            if len(recent_activity) < DASHBOARD_RECENT_ACTIVITY_LIMIT:
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
