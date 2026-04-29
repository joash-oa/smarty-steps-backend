from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.db.models import Learner
from app.services.leaderboard_service import LeaderboardService


def _learner(name, stars, streak):
    learner = MagicMock(spec=Learner)
    learner.name = name
    learner.avatar_emoji = "🚀"
    learner.total_stars = stars
    learner.streak_days = streak
    return learner


@pytest.mark.asyncio
async def test_get_leaderboard_assigns_ranks():
    learners = [_learner("A", 80, 3), _learner("B", 50, 1)]
    dao = MagicMock()
    dao.get_ranked = AsyncMock(return_value=learners)
    svc = LeaderboardService(dao)
    result = await svc.get_leaderboard("all_time")
    assert result["period"] == "all_time"
    ranks = [r["rank"] for r in result["rankings"]]
    assert ranks == [1, 2]


@pytest.mark.asyncio
async def test_get_leaderboard_raises_400_for_invalid_period():
    dao = MagicMock()
    svc = LeaderboardService(dao)
    with pytest.raises(HTTPException) as exc:
        await svc.get_leaderboard("last_year")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_get_leaderboard_returns_empty_list():
    dao = MagicMock()
    dao.get_ranked = AsyncMock(return_value=[])
    svc = LeaderboardService(dao)
    result = await svc.get_leaderboard("weekly")
    assert result["rankings"] == []
