from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Learner


class LeaderboardDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_ranked(self, period: str, limit: int = 50) -> list[Learner]:
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
            cutoff = datetime.now(timezone.utc) - timedelta(days=7)
            query = query.where(Learner.last_active_at >= cutoff)
        elif period == "monthly":
            cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            query = query.where(Learner.last_active_at >= cutoff)

        result = await self.session.execute(query)
        return list(result.scalars().all())
