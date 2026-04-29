import pytest
from uuid_extensions import uuid7

from app.daos.learner_dao import LearnerDAO
from app.daos.parent_dao import ParentDAO
from app.daos.progress_dao import ProgressDAO
from app.db.models import Chapter, Lesson, Standard


async def _seed_parent_and_learner(db_session):
    parent = await ParentDAO(db_session).create(
        cognito_id=f"cog-{uuid7()}", email=f"{uuid7()}@test.com", pin_hash="hash"
    )
    learner = await LearnerDAO(db_session).create(
        parent_id=parent.id, name="Test", age=6, grade_level=1, avatar_emoji="🚀"
    )
    return learner


async def _seed_lesson(db_session, subject="math"):
    chapter = Chapter(subject=subject, title="Ch", order_index=99)
    db_session.add(chapter)
    standard = Standard(
        code=f"T-{uuid7()}", subject=subject, grade_level=1, title="S", description="D"
    )
    db_session.add(standard)
    await db_session.flush()
    lesson = Lesson(
        chapter_id=chapter.id,
        standard_id=standard.id,
        subject=subject,
        title="L",
        difficulty="easy",
        order_index=1,
        content={},
    )
    db_session.add(lesson)
    await db_session.flush()
    return chapter, lesson


@pytest.mark.asyncio
async def test_create_and_get_lesson_progress(db_session):
    learner = await _seed_parent_and_learner(db_session)
    _, lesson = await _seed_lesson(db_session)
    dao = ProgressDAO(db_session)
    progress = await dao.create_lesson_progress(
        learner_id=learner.id,
        lesson_id=lesson.id,
        stars=2,
        correct=3,
        total=4,
        time_seconds=120,
    )
    assert progress.stars_earned == 2
    assert progress.completed is True

    fetched = await dao.get_lesson_progress(learner.id, lesson.id)
    assert fetched is not None
    assert fetched.id == progress.id


@pytest.mark.asyncio
async def test_update_lesson_progress(db_session):
    learner = await _seed_parent_and_learner(db_session)
    _, lesson = await _seed_lesson(db_session)
    dao = ProgressDAO(db_session)
    progress = await dao.create_lesson_progress(
        learner_id=learner.id,
        lesson_id=lesson.id,
        stars=1,
        correct=2,
        total=4,
        time_seconds=60,
    )
    updated = await dao.update_lesson_progress(
        progress, stars=3, correct=4, total=4, time_seconds=90
    )
    assert updated.stars_earned == 3


@pytest.mark.asyncio
async def test_get_all_progress_for_learner(db_session):
    learner = await _seed_parent_and_learner(db_session)
    _, lesson_one = await _seed_lesson(db_session)
    _, lesson_two = await _seed_lesson(db_session)
    dao = ProgressDAO(db_session)
    await dao.create_lesson_progress(
        learner.id, lesson_one.id, stars=2, correct=3, total=4, time_seconds=60
    )
    await dao.create_lesson_progress(
        learner.id, lesson_two.id, stars=1, correct=2, total=4, time_seconds=45
    )
    all_progress = await dao.get_all_progress_for_learner(learner.id)
    assert len(all_progress) == 2


@pytest.mark.asyncio
async def test_count_completed_lessons_in_chapter(db_session):
    learner = await _seed_parent_and_learner(db_session)
    chapter, lesson_one = await _seed_lesson(db_session)
    lesson_two = Lesson(
        chapter_id=chapter.id,
        standard_id=lesson_one.standard_id,
        subject="math",
        title="L2",
        difficulty="medium",
        order_index=2,
        content={},
    )
    db_session.add(lesson_two)
    await db_session.flush()

    dao = ProgressDAO(db_session)
    await dao.create_lesson_progress(
        learner.id, lesson_one.id, stars=3, correct=4, total=4, time_seconds=60
    )
    count = await dao.count_completed_lessons_in_chapter(learner.id, chapter.id)
    assert count == 1


@pytest.mark.asyncio
async def test_create_and_get_chapter_quiz(db_session):
    learner = await _seed_parent_and_learner(db_session)
    chapter = Chapter(subject="math", title="Quiz Ch", order_index=98)
    db_session.add(chapter)
    await db_session.flush()
    dao = ProgressDAO(db_session)
    quiz = await dao.create_chapter_quiz(
        learner_id=learner.id,
        chapter_id=chapter.id,
        difficulty="medium",
        content={"exercises": []},
    )
    assert quiz.id is not None
    fetched = await dao.get_chapter_quiz(learner.id, chapter.id)
    assert fetched is not None
    assert fetched.id == quiz.id


@pytest.mark.asyncio
async def test_get_quiz_by_id_returns_none_when_missing(db_session):
    dao = ProgressDAO(db_session)
    result = await dao.get_quiz_by_id(uuid7())
    assert result is None
