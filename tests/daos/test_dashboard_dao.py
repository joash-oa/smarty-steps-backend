import pytest
from uuid_extensions import uuid7

from app.daos.dashboard_dao import DashboardDAO
from app.daos.learner_dao import LearnerDAO
from app.daos.parent_dao import ParentDAO
from app.daos.progress_dao import ProgressDAO
from app.db.models import Chapter, Lesson, Standard


async def _seed(db_session):
    parent = await ParentDAO(db_session).create(
        cognito_id=f"cog-db-{uuid7()}", email=f"db-{uuid7()}@test.com", pin_hash="h"
    )
    learner = await LearnerDAO(db_session).create(
        parent_id=parent.id, name="Dash", age=7, grade_level=2, avatar_emoji="🚀"
    )
    chapter = Chapter(subject="math", title="D Ch", order_index=60)
    db_session.add(chapter)
    standard = Standard(
        code=f"DB-{uuid7()}", subject="math", grade_level=2, title="S", description="D"
    )
    db_session.add(standard)
    await db_session.flush()
    lesson = Lesson(
        chapter_id=chapter.id,
        standard_id=standard.id,
        subject="math",
        title="Dashboard Lesson",
        difficulty="easy",
        order_index=1,
        content={},
    )
    db_session.add(lesson)
    await db_session.flush()
    return learner, lesson


@pytest.mark.asyncio
async def test_get_completed_progress_rows_returns_empty_for_no_progress(db_session):
    learner, _ = await _seed(db_session)
    dao = DashboardDAO(db_session)
    rows = await dao.get_completed_progress_rows(learner.id)
    assert rows == []


@pytest.mark.asyncio
async def test_get_completed_progress_rows_returns_completed_lessons(db_session):
    learner, lesson = await _seed(db_session)
    progress_dao = ProgressDAO(db_session)
    await progress_dao.create_lesson_progress(
        learner_id=learner.id,
        lesson_id=lesson.id,
        stars=3,
        correct=5,
        total=5,
        time_seconds=120,
    )
    dao = DashboardDAO(db_session)
    rows = await dao.get_completed_progress_rows(learner.id)
    assert len(rows) == 1
    progress, returned_lesson = rows[0]
    assert returned_lesson.id == lesson.id
    assert progress.stars_earned == 3
