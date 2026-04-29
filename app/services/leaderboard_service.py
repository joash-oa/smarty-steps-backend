from fastapi import HTTPException

from app.daos.leaderboard_dao import LeaderboardDAO

VALID_PERIODS = {"all_time", "weekly", "monthly"}


class LeaderboardService:
    def __init__(self, dao: LeaderboardDAO):
        self.dao = dao

    async def get_leaderboard(self, period: str) -> dict:
        if period not in VALID_PERIODS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid period. Must be one of {VALID_PERIODS}",
            )
        learners = await self.dao.get_ranked(period, limit=50)
        rankings = [
            {
                "rank": idx + 1,
                "name": learner.name,
                "avatar_emoji": learner.avatar_emoji,
                "total_stars": learner.total_stars or 0,
                "streak_days": learner.streak_days or 0,
            }
            for idx, learner in enumerate(learners)
        ]
        return {"period": period, "rankings": rankings}
