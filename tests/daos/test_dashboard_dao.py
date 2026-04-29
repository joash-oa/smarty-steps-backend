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
async def test_get_stats_returns_structure(db_session):
    learner, lesson = await _seed(db_session)
    dao = DashboardDAO(db_session)
    stats = await dao.get_stats(learner.id)
    assert "time_per_subject" in stats
    assert "mastered" in stats
    assert "needs_practice" in stats
    assert "recent_activity" in stats


@pytest.mark.asyncio
async def test_mastered_includes_3_star_lessons(db_session):
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
    stats = await dao.get_stats(learner.id)
    mastered_ids = [m["lesson_id"] for m in stats["mastered"]]
    assert str(lesson.id) in mastered_ids


@pytest.mark.asyncio
async def test_needs_practice_includes_low_star_completed_lessons(db_session):
    learner, lesson = await _seed(db_session)
    progress_dao = ProgressDAO(db_session)
    await progress_dao.create_lesson_progress(
        learner_id=learner.id,
        lesson_id=lesson.id,
        stars=1,
        correct=2,
        total=5,
        time_seconds=90,
    )
    dao = DashboardDAO(db_session)
    stats = await dao.get_stats(learner.id)
    needs_practice_ids = [n["lesson_id"] for n in stats["needs_practice"]]
    assert str(lesson.id) in needs_practice_ids


@pytest.mark.asyncio
async def test_time_per_subject_aggregates_correctly(db_session):
    learner, lesson = await _seed(db_session)
    progress_dao = ProgressDAO(db_session)
    await progress_dao.create_lesson_progress(
        learner_id=learner.id,
        lesson_id=lesson.id,
        stars=2,
        correct=3,
        total=5,
        time_seconds=200,
    )
    dao = DashboardDAO(db_session)
    stats = await dao.get_stats(learner.id)
    assert stats["time_per_subject"]["math"] >= 200
