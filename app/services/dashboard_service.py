from uuid import UUID

from app.daos.dashboard_dao import DashboardDAO
from app.db.models import Parent


class DashboardService:
    def __init__(self, dao: DashboardDAO):
        self.dao = dao

    async def get_stats(self, parent: Parent, learner_id: UUID, learner_svc) -> dict:
        learner = await learner_svc.get(parent, learner_id)
        return await self.dao.get_stats(learner.id)
