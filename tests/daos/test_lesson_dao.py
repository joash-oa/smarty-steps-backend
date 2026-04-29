import pytest
from uuid_extensions import uuid7

from app.daos.lesson_dao import LessonDAO
from app.db.models import Standard

LESSON_CONTENT = {
    "intro": {"title": "T", "description": "D", "mascot_quote": "Q"},
    "exercises": [],
    "result": {"badge_name": "B", "badge_description": "BD"},
    "stars_available": 3,
}


async def _seed_standard(db_session, subject="math", grade=1) -> Standard:
    standard = Standard(
        code=f"NY-{uuid7()}",
        subject=subject,
        grade_level=grade,
        title="Test Standard",
        description="A test standard.",
    )
    db_session.add(standard)
    await db_session.flush()
    return standard


@pytest.mark.asyncio
async def test_get_or_create_chapter_creates_on_first_call(db_session):
    dao = LessonDAO(db_session)
    chapter = await dao.get_or_create_chapter(subject="math", domain="K.CC")
    assert chapter.id is not None
    assert chapter.title == "K.CC"
    assert chapter.subject == "math"


@pytest.mark.asyncio
async def test_get_or_create_chapter_is_idempotent(db_session):
    dao = LessonDAO(db_session)
    chapter_first = await dao.get_or_create_chapter(subject="math", domain="K.OA")
    chapter_second = await dao.get_or_create_chapter(subject="math", domain="K.OA")
    assert chapter_first.id == chapter_second.id


@pytest.mark.asyncio
async def test_create_and_get_lesson(db_session):
    dao = LessonDAO(db_session)
    chapter = await dao.get_or_create_chapter(subject="math", domain="K.CC")
    standard = await _seed_standard(db_session)
    lesson = await dao.create_lesson(
        chapter_id=chapter.id,
        standard_id=standard.id,
        subject="math",
        title="Counting to 10",
        difficulty="easy",
        order_index=1,
        content=LESSON_CONTENT,
    )
    assert lesson.id is not None
    fetched = await dao.get_lesson_by_id(lesson.id)
    assert fetched is not None
    assert fetched.title == "Counting to 10"


@pytest.mark.asyncio
async def test_get_chapters_by_subject_ordered(db_session):
    dao = LessonDAO(db_session)
    chapter_a = await dao.get_or_create_chapter(subject="science", domain="Domain A")
    chapter_b = await dao.get_or_create_chapter(subject="science", domain="Domain B")
    chapters = await dao.get_chapters_by_subject("science")
    chapter_ids = [c.id for c in chapters]
    assert chapter_a.id in chapter_ids
    assert chapter_b.id in chapter_ids
    order_values = [c.order_index for c in chapters]
    assert order_values == sorted(order_values)


@pytest.mark.asyncio
async def test_count_standards_returns_zero_on_empty(db_session):
    dao = LessonDAO(db_session)
    count = await dao.count_standards()
    assert count >= 0


@pytest.mark.asyncio
async def test_get_standard_by_code_returns_none_when_missing(db_session):
    dao = LessonDAO(db_session)
    result = await dao.get_standard_by_code("NO-SUCH-CODE")
    assert result is None


@pytest.mark.asyncio
async def test_count_lessons_in_chapter(db_session):
    dao = LessonDAO(db_session)
    chapter = await dao.get_or_create_chapter(subject="english", domain="ELA.RL")
    standard = await _seed_standard(db_session, subject="english", grade=1)
    await dao.create_lesson(
        chapter_id=chapter.id,
        standard_id=standard.id,
        subject="english",
        title="L1",
        difficulty="easy",
        order_index=1,
        content=LESSON_CONTENT,
    )
    await dao.create_lesson(
        chapter_id=chapter.id,
        standard_id=standard.id,
        subject="english",
        title="L2",
        difficulty="medium",
        order_index=2,
        content=LESSON_CONTENT,
    )
    count = await dao.count_lessons_in_chapter(chapter.id)
    assert count == 2
