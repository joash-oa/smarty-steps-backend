from datetime import datetime, timedelta, timezone

import bcrypt
import pytest
from jose import jwt
from uuid_extensions import uuid7

from app.api import deps
from app.core.config import settings
from app.daos.learner_dao import LearnerDAO
from app.daos.parent_dao import ParentDAO
from app.daos.progress_dao import ProgressDAO
from app.db.models import Chapter, Lesson, Standard
from app.main import app


def _make_dashboard_token(parent_id: str) -> str:
    payload = {
        "sub": parent_id,
        "scope": "parent_dashboard",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
    }
    return jwt.encode(payload, settings.parent_jwt_secret, algorithm="HS256")


async def _seed_dashboard_data(db_session, parent):
    learner = await LearnerDAO(db_session).create(
        parent_id=parent.id, name="DashLearner", age=7, grade_level=2, avatar_emoji="🌟"
    )
    chapter = Chapter(subject="math", title="D Ch", order_index=70)
    db_session.add(chapter)
    standard = Standard(
        code=f"DASH-{id(db_session)}", subject="math", grade_level=2, title="S", description="D"
    )
    db_session.add(standard)
    await db_session.flush()
    lesson = Lesson(
        chapter_id=chapter.id,
        standard_id=standard.id,
        subject="math",
        title="Test Lesson",
        difficulty="easy",
        order_index=1,
        content={},
    )
    db_session.add(lesson)
    await db_session.flush()
    await ProgressDAO(db_session).create_lesson_progress(
        learner_id=learner.id,
        lesson_id=lesson.id,
        stars=3,
        correct=5,
        total=5,
        time_seconds=150,
    )
    return learner


@pytest.mark.asyncio
async def test_dashboard_stats_returns_200(client, db_session):
    parent = await ParentDAO(db_session).create(
        cognito_id=f"cog-dash-{uuid7()}",
        email=f"dash-{uuid7()}@test.com",
        pin_hash=bcrypt.hashpw(b"1234", bcrypt.gensalt()).decode(),
    )
    app.dependency_overrides[deps.get_current_parent_dashboard] = lambda: parent

    learner = await _seed_dashboard_data(db_session, parent)
    token = _make_dashboard_token(str(parent.id))

    response = await client.get(
        f"/parent/learners/{learner.id}/stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "time_per_subject" in body
    assert "mastered" in body
    assert "needs_practice" in body
    assert "recent_activity" in body
    assert body["time_per_subject"]["math"] >= 150
    assert len(body["mastered"]) >= 1

    app.dependency_overrides.pop(deps.get_current_parent_dashboard, None)


@pytest.mark.asyncio
async def test_dashboard_stats_returns_403_for_wrong_learner(client, db_session):
    parent = await ParentDAO(db_session).create(
        cognito_id=f"cog-dash2-{uuid7()}",
        email=f"dash2-{uuid7()}@test.com",
        pin_hash=bcrypt.hashpw(b"1234", bcrypt.gensalt()).decode(),
    )
    app.dependency_overrides[deps.get_current_parent_dashboard] = lambda: parent
    response = await client.get(
        f"/parent/learners/{uuid7()}/stats",
        headers={"Authorization": "Bearer fake"},
    )
    assert response.status_code in (403, 404)

    app.dependency_overrides.pop(deps.get_current_parent_dashboard, None)


@pytest.mark.asyncio
async def test_dashboard_rejects_cognito_jwt(authed_client, db_session):
    """Cognito JWT must NOT work on dashboard routes."""
    client, parent = authed_client
    learner = await LearnerDAO(db_session).create(
        parent_id=parent.id, name="X", age=5, grade_level=0, avatar_emoji="🚀"
    )
    response = await client.get(
        f"/parent/learners/{learner.id}/stats",
        headers={"Authorization": "Bearer cognito-jwt-would-fail-here"},
    )
    assert response.status_code == 401
