from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.db.models import Chapter, Learner, Lesson, LessonProgress
from app.services.curriculum_service import CurriculumService


def _chapter(order_index=0):
    chapter = MagicMock(spec=Chapter)
    chapter.id = uuid4()
    chapter.title = f"Chapter {order_index}"
    chapter.order_index = order_index
    return chapter


def _lesson(chapter_id, order_index=0):
    lesson = MagicMock(spec=Lesson)
    lesson.id = uuid4()
    lesson.title = f"Lesson {order_index}"
    lesson.difficulty = "easy"
    lesson.order_index = order_index
    lesson.chapter_id = chapter_id
    return lesson


def _progress(lesson_id, stars=3, completed=True):
    prog = MagicMock(spec=LessonProgress)
    prog.lesson_id = lesson_id
    prog.stars_earned = stars
    prog.completed = completed
    return prog


def _learner():
    learner = MagicMock(spec=Learner)
    learner.id = uuid4()
    return learner


@pytest.mark.asyncio
async def test_get_curriculum_returns_chapters_with_lessons():
    learner = _learner()
    chapter = _chapter(order_index=0)
    lesson = _lesson(chapter.id, order_index=0)

    lesson_dao = MagicMock()
    lesson_dao.get_chapters_by_subject = AsyncMock(return_value=[chapter])
    lesson_dao.get_lessons_by_chapter = AsyncMock(return_value=[lesson])

    progress_dao = MagicMock()
    progress_dao.get_all_progress_for_learner = AsyncMock(return_value=[])
    progress_dao.get_chapter_quiz = AsyncMock(return_value=None)

    learner_svc = MagicMock()
    learner_svc.get = AsyncMock(return_value=learner)

    svc = CurriculumService(lesson_dao=lesson_dao, progress_dao=progress_dao)
    result = await svc.get_curriculum(MagicMock(), learner.id, "math", learner_svc)

    assert result["subject"] == "math"
    assert len(result["chapters"]) == 1
    assert result["chapters"][0]["id"] == chapter.id
    assert len(result["chapters"][0]["lessons"]) == 1


@pytest.mark.asyncio
async def test_get_curriculum_quiz_locked_when_lessons_incomplete():
    learner = _learner()
    chapter = _chapter()
    lesson = _lesson(chapter.id)

    lesson_dao = MagicMock()
    lesson_dao.get_chapters_by_subject = AsyncMock(return_value=[chapter])
    lesson_dao.get_lessons_by_chapter = AsyncMock(return_value=[lesson])

    progress_dao = MagicMock()
    progress_dao.get_all_progress_for_learner = AsyncMock(return_value=[])
    progress_dao.get_chapter_quiz = AsyncMock(return_value=None)

    learner_svc = MagicMock()
    learner_svc.get = AsyncMock(return_value=learner)

    svc = CurriculumService(lesson_dao=lesson_dao, progress_dao=progress_dao)
    result = await svc.get_curriculum(MagicMock(), learner.id, "math", learner_svc)

    quiz_state = result["chapters"][0]["quiz"]
    assert quiz_state["locked"] is True
    assert quiz_state["generated"] is False


@pytest.mark.asyncio
async def test_get_curriculum_quiz_unlocked_when_all_lessons_complete():
    learner = _learner()
    chapter = _chapter()
    lesson = _lesson(chapter.id)
    progress = _progress(lesson.id, stars=3, completed=True)

    lesson_dao = MagicMock()
    lesson_dao.get_chapters_by_subject = AsyncMock(return_value=[chapter])
    lesson_dao.get_lessons_by_chapter = AsyncMock(return_value=[lesson])

    progress_dao = MagicMock()
    progress_dao.get_all_progress_for_learner = AsyncMock(return_value=[progress])
    progress_dao.get_chapter_quiz = AsyncMock(return_value=None)

    learner_svc = MagicMock()
    learner_svc.get = AsyncMock(return_value=learner)

    svc = CurriculumService(lesson_dao=lesson_dao, progress_dao=progress_dao)
    result = await svc.get_curriculum(MagicMock(), learner.id, "math", learner_svc)

    quiz_state = result["chapters"][0]["quiz"]
    assert quiz_state["locked"] is False
    assert quiz_state["generated"] is False


@pytest.mark.asyncio
async def test_get_lesson_raises_when_not_found():
    from app.core.exceptions import LessonNotFoundError

    lesson_dao = MagicMock()
    lesson_dao.get_lesson_by_id = AsyncMock(return_value=None)

    svc = CurriculumService(lesson_dao=lesson_dao, progress_dao=MagicMock())
    with pytest.raises(LessonNotFoundError):
        await svc.get_lesson(uuid4())


@pytest.mark.asyncio
async def test_get_lesson_returns_sanitized_content():
    lesson = MagicMock(spec=Lesson)
    lesson.id = uuid4()
    lesson.title = "Counting"
    lesson.difficulty = "easy"
    lesson.stars_available = 3
    lesson.content = {
        "exercises": [
            {
                "id": "ex_1",
                "type": "multiple_choice",
                "correct_option_id": "a",
                "prompt": "Q?",
                "options": [{"id": "a", "text": "A"}],
            }
        ]
    }

    lesson_dao = MagicMock()
    lesson_dao.get_lesson_by_id = AsyncMock(return_value=lesson)

    svc = CurriculumService(lesson_dao=lesson_dao, progress_dao=MagicMock())
    result = await svc.get_lesson(lesson.id)

    assert result["id"] == lesson.id
    assert "correct_option_id" not in result["content"]["exercises"][0]
