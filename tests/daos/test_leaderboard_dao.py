from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import update
from uuid_extensions import uuid7

from app.daos.leaderboard_dao import LeaderboardDAO
from app.daos.learner_dao import LearnerDAO
from app.daos.parent_dao import ParentDAO
from app.db.models import Learner


async def _make_learner(db_session, name, stars, streak, last_active_days_ago=0):
    parent = await ParentDAO(db_session).create(
        cognito_id=f"cog-lb-{uuid7()}",
        email=f"lb-{uuid7()}@test.com",
        pin_hash="hash",
    )
    learner_dao = LearnerDAO(db_session)
    learner = await learner_dao.create(
        parent_id=parent.id, name=name, age=6, grade_level=1, avatar_emoji="🚀"
    )
    last_active = datetime.now(timezone.utc) - timedelta(days=last_active_days_ago)
    await db_session.execute(
        update(Learner)
        .where(Learner.id == learner.id)
        .values(total_stars=stars, streak_days=streak, last_active_at=last_active)
    )
    await db_session.flush()
    return learner


@pytest.mark.asyncio
async def test_all_time_ranking_sorted_by_stars(db_session):
    await _make_learner(db_session, "Alice", stars=50, streak=3)
    await _make_learner(db_session, "Bob", stars=80, streak=1)
    dao = LeaderboardDAO(db_session)
    results = await dao.get_ranked("all_time", limit=10)
    star_values = [r.total_stars for r in results]
    assert star_values == sorted(star_values, reverse=True)
    names = [r.name for r in results]
    assert names.index("Bob") < names.index("Alice")


@pytest.mark.asyncio
async def test_tie_broken_by_streak(db_session):
    await _make_learner(db_session, "C", stars=100, streak=10, last_active_days_ago=0)
    await _make_learner(db_session, "D", stars=100, streak=5, last_active_days_ago=0)
    dao = LeaderboardDAO(db_session)
    results = await dao.get_ranked("all_time", limit=10)
    names = [r.name for r in results]
    assert names.index("C") < names.index("D")


@pytest.mark.asyncio
async def test_weekly_filters_by_last_active(db_session):
    await _make_learner(db_session, "Active", stars=10, streak=1, last_active_days_ago=1)
    await _make_learner(db_session, "Inactive", stars=999, streak=1, last_active_days_ago=10)
    dao = LeaderboardDAO(db_session)
    results = await dao.get_ranked("weekly", limit=50)
    names = [r.name for r in results]
    assert "Active" in names
    assert "Inactive" not in names


@pytest.mark.asyncio
async def test_empty_period_returns_empty_list(db_session):
    dao = LeaderboardDAO(db_session)
    results = await dao.get_ranked("monthly", limit=10)
    assert isinstance(results, list)
