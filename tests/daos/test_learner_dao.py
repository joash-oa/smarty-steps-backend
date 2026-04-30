import pytest
from uuid_extensions import uuid7

from app.daos.learner_dao import LearnerDAO
from app.daos.parent_dao import ParentDAO


async def _make_parent(db_session, suffix=""):
    return await ParentDAO(db_session).create(
        cognito_id=f"cog-learner-{uuid7()}{suffix}",
        email=f"parent-{uuid7()}@test.com",
        pin_hash="$2b$12$hash",
    )


@pytest.mark.asyncio
async def test_create_and_get_by_parent(db_session):
    parent = await _make_parent(db_session)
    dao = LearnerDAO(db_session)
    learner = await dao.create(
        parent_id=parent.id,
        name="Emma",
        age=6,
        grade_level=1,
        avatar_emoji="🦋",
    )
    assert learner.id is not None
    assert learner.name == "Emma"
    assert learner.total_stars == 0
    assert learner.level == 1
    assert learner.xp == 0

    learners = await dao.get_by_parent(parent.id)
    assert len(learners) == 1
    assert learners[0].id == learner.id


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_missing(db_session):
    dao = LearnerDAO(db_session)
    result = await dao.get_by_id(uuid7())
    assert result is None


@pytest.mark.asyncio
async def test_get_by_parent_returns_empty_list(db_session):
    dao = LearnerDAO(db_session)
    result = await dao.get_by_parent(uuid7())
    assert result == []


@pytest.mark.asyncio
async def test_update_stats_persists_provided_level(db_session):
    """update_stats must persist the caller-supplied new_level, not recompute it."""
    from datetime import datetime, timezone

    parent = await _make_parent(db_session, "-stats")
    dao = LearnerDAO(db_session)
    learner = await dao.create(
        parent_id=parent.id,
        name="Sam",
        age=6,
        grade_level=1,
        avatar_emoji="⭐",
    )
    updated = await dao.update_stats(
        learner,
        star_delta=3,
        xp_delta=50,
        new_streak=2,
        new_last_active_at=datetime.now(timezone.utc),
        new_level=99,
    )
    assert updated.total_stars == 3
    assert updated.xp == 50
    assert updated.level == 99
    assert updated.streak_days == 2


@pytest.mark.asyncio
async def test_update_learner_fields(db_session):
    parent = await _make_parent(db_session, "-upd")
    dao = LearnerDAO(db_session)
    learner = await dao.create(
        parent_id=parent.id,
        name="Jake",
        age=7,
        grade_level=2,
        avatar_emoji="🚀",
    )
    updated = await dao.update(learner, name="Jake Updated", avatar_emoji="🌟", grade_level=3)
    assert updated.name == "Jake Updated"
    assert updated.avatar_emoji == "🌟"
    assert updated.grade_level == 3
    assert updated.age == 7  # unchanged
