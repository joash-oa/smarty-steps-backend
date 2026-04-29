from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Learner


class LearnerDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        parent_id: UUID,
        name: str,
        age: int,
        grade_level: int,
        avatar_emoji: str,
    ) -> Learner:
        learner = Learner(
            parent_id=parent_id,
            name=name,
            age=age,
            grade_level=grade_level,
            avatar_emoji=avatar_emoji,
        )
        self.session.add(learner)
        await self.session.flush()
        await self.session.refresh(learner)
        return learner

    async def get_by_parent(self, parent_id: UUID) -> list[Learner]:
        result = await self.session.execute(select(Learner).where(Learner.parent_id == parent_id))
        return list(result.scalars().all())

    async def get_by_id(self, learner_id: UUID) -> Optional[Learner]:
        result = await self.session.execute(select(Learner).where(Learner.id == learner_id))
        return result.scalar_one_or_none()

    async def update(
        self,
        learner: Learner,
        name: Optional[str] = None,
        avatar_emoji: Optional[str] = None,
        grade_level: Optional[int] = None,
    ) -> Learner:
        if name is not None:
            learner.name = name
        if avatar_emoji is not None:
            learner.avatar_emoji = avatar_emoji
        if grade_level is not None:
            learner.grade_level = grade_level
        await self.session.flush()
        await self.session.refresh(learner)
        return learner

    async def update_stats(
        self,
        learner: Learner,
        star_delta: int,
        xp_delta: int,
        new_streak: int,
        new_last_active_at,
    ) -> Learner:
        learner.total_stars = (learner.total_stars or 0) + star_delta
        learner.xp = (learner.xp or 0) + xp_delta
        learner.level = (learner.xp // 100) + 1
        learner.streak_days = new_streak
        learner.last_active_at = new_last_active_at
        await self.session.flush()
        await self.session.refresh(learner)
        return learner
