from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    LEADERBOARD_MAX_RESULTS,
    LEADERBOARD_MONTHLY_DAYS,
    LEADERBOARD_WEEKLY_DAYS,
)
from app.db.models import Learner


class LeaderboardDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_ranked(self, period: str, limit: int = LEADERBOARD_MAX_RESULTS) -> list[Learner]:
        query = (
            select(Learner)
            .order_by(
                Learner.total_stars.desc(),
                Learner.streak_days.desc(),
                Learner.created_at.asc(),
            )
            .limit(limit)
        )
        if period == "weekly":
            cutoff = datetime.now(timezone.utc) - timedelta(days=LEADERBOARD_WEEKLY_DAYS)
            query = query.where(Learner.last_active_at >= cutoff)
        elif period == "monthly":
            cutoff = datetime.now(timezone.utc) - timedelta(days=LEADERBOARD_MONTHLY_DAYS)
            query = query.where(Learner.last_active_at >= cutoff)

        result = await self.session.execute(query)
        return list(result.scalars().all())
