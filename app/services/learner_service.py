from typing import Optional
from uuid import UUID

from fastapi import HTTPException

from app.daos.learner_dao import LearnerDAO
from app.db.models import Learner, Parent


class LearnerService:
    def __init__(self, learner_dao: LearnerDAO):
        self.dao = learner_dao

    async def create(
        self,
        parent: Parent,
        name: str,
        age: int,
        grade_level: int,
        avatar_emoji: str,
    ) -> Learner:
        return await self.dao.create(
            parent_id=parent.id,
            name=name,
            age=age,
            grade_level=grade_level,
            avatar_emoji=avatar_emoji,
        )

    async def list_for_parent(self, parent: Parent) -> list[Learner]:
        return await self.dao.get_by_parent(parent.id)

    async def get(self, parent: Parent, learner_id: UUID) -> Learner:
        learner = await self.dao.get_by_id(learner_id)
        if learner is None:
            raise HTTPException(status_code=404, detail="Learner not found")
        if learner.parent_id != parent.id:
            raise HTTPException(status_code=403, detail="Learner not owned by parent")
        return learner

    async def update(
        self,
        parent: Parent,
        learner_id: UUID,
        name: Optional[str],
        avatar_emoji: Optional[str],
        grade_level: Optional[int],
    ) -> Learner:
        learner = await self.get(parent, learner_id)
        return await self.dao.update(
            learner,
            name=name,
            avatar_emoji=avatar_emoji,
            grade_level=grade_level,
        )
