from unittest.mock import AsyncMock, MagicMock

import pytest

from app.clients.standards_api import StandardData
from app.services.content_service import ContentService, _difficulty_for_position

MOCK_STANDARD = StandardData(
    code="NY-TEST.1",
    subject="math",
    grade_level=1,
    title="Count to 20",
    description="Students can count to 20.",
    domain="K.CC",
)

MOCK_LESSON_CONTENT = {
    "intro": {"title": "Count to 20", "description": "D", "mascot_quote": "Q"},
    "exercises": [
        {
            "id": f"ex_{i}",
            "type": "multiple_choice",
            "difficulty": "easy",
            "prompt": "Q?",
            "mascot_hint": "H",
            "options": [],
            "correct_option_id": "a",
            "explanation": "E",
        }
        for i in range(1, 16)
    ],
    "result": {"badge_name": "B", "badge_description": "BD"},
    "stars_available": 3,
}


@pytest.mark.asyncio
async def test_sync_skips_standard_that_already_has_lesson(db_session):
    """If a standard already has a lesson, Claude is not called again."""
    mock_api = MagicMock()
    mock_api.fetch_standards = AsyncMock(return_value=[MOCK_STANDARD])
    mock_claude = MagicMock()
    mock_claude.generate_lesson = AsyncMock(return_value=MOCK_LESSON_CONTENT)

    from app.daos.lesson_dao import LessonDAO
    from app.db.models import Standard

    existing_standard = Standard(
        code=MOCK_STANDARD.code,
        subject="math",
        grade_level=1,
        title="Already exists",
        description="D",
    )
    db_session.add(existing_standard)
    await db_session.flush()

    dao = LessonDAO(db_session)
    chapter = await dao.get_or_create_chapter(subject="math", domain=MOCK_STANDARD.domain)
    await dao.create_lesson(
        chapter_id=chapter.id,
        standard_id=existing_standard.id,
        subject="math",
        title="Existing lesson",
        difficulty="easy",
        order_index=1,
        content=MOCK_LESSON_CONTENT,
    )

    service = ContentService(lesson_dao=dao, standards_api=mock_api, claude=mock_claude)
    await service.sync_subject_grade("math", 1)

    mock_claude.generate_lesson.assert_not_called()


@pytest.mark.asyncio
async def test_sync_creates_chapter_and_lesson_for_new_standard(db_session):
    """New standard → auto-create chapter from domain → generate lesson via Claude."""
    from uuid_extensions import uuid7

    mock_api = MagicMock()
    unique_code = f"NY-NEW-{uuid7()}"
    new_standard = StandardData(
        code=unique_code,
        subject="math",
        grade_level=2,
        title="New Standard",
        description="Description.",
        domain="2.NBT",
    )
    mock_api.fetch_standards = AsyncMock(return_value=[new_standard])
    mock_claude = MagicMock()
    mock_claude.generate_lesson = AsyncMock(return_value=MOCK_LESSON_CONTENT)

    from app.daos.lesson_dao import LessonDAO

    dao = LessonDAO(db_session)

    service = ContentService(lesson_dao=dao, standards_api=mock_api, claude=mock_claude)
    await service.sync_subject_grade("math", 2)

    mock_claude.generate_lesson.assert_awaited_once()

    chapters = await dao.get_chapters_by_subject("math")
    chapter_titles = [chapter.title for chapter in chapters]
    assert "2.NBT" in chapter_titles


def test_difficulty_for_position():
    assert _difficulty_for_position(1) == "easy"
    assert _difficulty_for_position(2) == "easy"
    assert _difficulty_for_position(3) == "medium"
    assert _difficulty_for_position(4) == "medium"
    assert _difficulty_for_position(5) == "hard"
    assert _difficulty_for_position(10) == "hard"
