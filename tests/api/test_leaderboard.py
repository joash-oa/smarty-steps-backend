from datetime import datetime, timezone

import pytest
from sqlalchemy import update

from app.daos.learner_dao import LearnerDAO
from app.daos.parent_dao import ParentDAO
from app.db.models import Learner


async def _make_active_learner(db_session, name, stars):
    parent = await ParentDAO(db_session).create(
        cognito_id=f"cog-lb2-{name}", email=f"lb2-{name}@test.com", pin_hash="h"
    )
    learner = await LearnerDAO(db_session).create(
        parent_id=parent.id, name=name, age=6, grade_level=1, avatar_emoji="🦋"
    )
    await db_session.execute(
        update(Learner)
        .where(Learner.id == learner.id)
        .values(total_stars=stars, last_active_at=datetime.now(timezone.utc))
    )
    await db_session.flush()
    return learner


@pytest.mark.asyncio
async def test_all_time_leaderboard_returns_200(authed_client, db_session):
    client, _ = authed_client
    response = await client.get("/leaderboard?period=all_time")
    assert response.status_code == 200
    body = response.json()
    assert body["period"] == "all_time"
    assert isinstance(body["rankings"], list)


@pytest.mark.asyncio
async def test_leaderboard_ranking_order(authed_client, db_session):
    client, _ = authed_client
    await _make_active_learner(db_session, "TopLearner", stars=999)
    response = await client.get("/leaderboard?period=all_time")
    assert response.status_code == 200
    rankings = response.json()["rankings"]
    assert rankings[0]["total_stars"] >= rankings[-1]["total_stars"]


@pytest.mark.asyncio
async def test_leaderboard_400_for_invalid_period(authed_client):
    client, _ = authed_client
    response = await client.get("/leaderboard?period=decade")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_weekly_leaderboard_returns_only_active(authed_client, db_session):
    client, _ = authed_client
    response = await client.get("/leaderboard?period=weekly")
    assert response.status_code == 200
    body = response.json()
    assert body["period"] == "weekly"
