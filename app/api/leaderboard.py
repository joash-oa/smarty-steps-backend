from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.daos.leaderboard_dao import LeaderboardDAO
from app.db.session import get_db
from app.schemas.leaderboard import LeaderboardResponse
from app.services.leaderboard_service import LeaderboardService

router = APIRouter(tags=["leaderboard"])


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    period: str = Query("all_time", description="all_time | weekly | monthly"),
    db: AsyncSession = Depends(get_db),
):
    svc = LeaderboardService(LeaderboardDAO(db))
    result = await svc.get_leaderboard(period)
    return LeaderboardResponse(**result)
