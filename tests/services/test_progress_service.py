from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.db.models import Learner, Lesson, LessonProgress, Parent
from app.services.progress_service import ProgressService

LESSON_CONTENT = {
    "exercises": [
        {
            "id": "ex_1",
            "type": "multiple_choice",
            "correct_option_id": "b",
            "explanation": "Because.",
        },
        {"id": "ex_2", "type": "fill_blank", "correct_word": "on"},
    ]
}

ANSWERS_ALL_CORRECT = {
    "ex_1": {"selected_option_id": "b"},
    "ex_2": {"selected_word": "on"},
}

ANSWERS_ALL_WRONG = {
    "ex_1": {"selected_option_id": "a"},
    "ex_2": {"selected_word": "under"},
}


def _lesson(content=LESSON_CONTENT, chapter_id=None):
    lesson = MagicMock(spec=Lesson)
    lesson.id = uuid4()
    lesson.chapter_id = chapter_id or uuid4()
    lesson.content = content
    return lesson


def _learner():
    learner = MagicMock(spec=Learner)
    learner.id = uuid4()
    learner.xp = 0
    learner.total_stars = 0
    learner.level = 1
    learner.streak_days = 0
    learner.last_active_at = None
    return learner


def _parent(learner):
    parent = MagicMock(spec=Parent)
    parent.id = uuid4()
    return parent


@pytest.mark.asyncio
async def test_check_answer_correct():
    lesson = _lesson()
    lesson_dao = MagicMock()
    lesson_dao.get_lesson_by_id = AsyncMock(return_value=lesson)
    svc = ProgressService(lesson_dao=lesson_dao, progress_dao=MagicMock(), learner_dao=MagicMock())
    result = await svc.check_lesson_answer(lesson.id, "ex_1", {"selected_option_id": "b"})
    assert result["correct"] is True
    assert result["explanation"] == "Because."


@pytest.mark.asyncio
async def test_check_answer_wrong():
    lesson = _lesson()
    lesson_dao = MagicMock()
    lesson_dao.get_lesson_by_id = AsyncMock(return_value=lesson)
    svc = ProgressService(lesson_dao=lesson_dao, progress_dao=MagicMock(), learner_dao=MagicMock())
    result = await svc.check_lesson_answer(lesson.id, "ex_1", {"selected_option_id": "z"})
    assert result["correct"] is False
    assert result["explanation"] is None


@pytest.mark.asyncio
async def test_check_answer_raises_404_for_missing_exercise():
    lesson = _lesson()
    lesson_dao = MagicMock()
    lesson_dao.get_lesson_by_id = AsyncMock(return_value=lesson)
    svc = ProgressService(lesson_dao=lesson_dao, progress_dao=MagicMock(), learner_dao=MagicMock())
    with pytest.raises(HTTPException) as exc:
        await svc.check_lesson_answer(lesson.id, "ex_99", {})
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_submit_raises_422_when_exercise_missing():
    lesson = _lesson()
    lesson_dao = MagicMock()
    lesson_dao.get_lesson_by_id = AsyncMock(return_value=lesson)
    learner_dao = MagicMock()
    learner = _learner()
    learner_dao.get_by_id = AsyncMock(return_value=learner)
    learner_svc = MagicMock()
    learner_svc.get = AsyncMock(return_value=learner)
    svc = ProgressService(lesson_dao=lesson_dao, progress_dao=MagicMock(), learner_dao=learner_dao)
    parent = _parent(learner)
    with pytest.raises(HTTPException) as exc:
        await svc.submit_lesson(
            parent=parent,
            learner_id=learner.id,
            lesson_id=lesson.id,
            time_seconds=60,
            answers={"ex_1": {"selected_option_id": "b"}},  # missing ex_2
            learner_svc=learner_svc,
        )
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_submit_best_score_only_upsert():
    """Second attempt with fewer stars → learner totals NOT updated."""
    lesson = _lesson()
    lesson_dao = MagicMock()
    lesson_dao.get_lesson_by_id = AsyncMock(return_value=lesson)
    lesson_dao.count_lessons_in_chapter = AsyncMock(return_value=1)

    learner = _learner()
    learner.xp = 40
    learner.total_stars = 3

    learner_dao = MagicMock()
    learner_dao.update_stats = AsyncMock(return_value=learner)

    # Existing progress: 3 stars
    existing_prog = MagicMock(spec=LessonProgress)
    existing_prog.stars_earned = 3
    existing_prog.lesson_id = lesson.id
    progress_dao = MagicMock()
    progress_dao.get_lesson_progress = AsyncMock(return_value=existing_prog)
    progress_dao.get_chapter_quiz = AsyncMock(return_value=MagicMock())  # quiz exists

    learner_svc = MagicMock()
    learner_svc.get = AsyncMock(return_value=learner)

    svc = ProgressService(lesson_dao=lesson_dao, progress_dao=progress_dao, learner_dao=learner_dao)
    result = await svc.submit_lesson(
        parent=_parent(learner),
        learner_id=learner.id,
        lesson_id=lesson.id,
        time_seconds=60,
        answers=ANSWERS_ALL_WRONG,  # 0 stars — worse than existing 3 stars
        learner_svc=learner_svc,
    )
    # delta is negative → no update to learner totals
    learner_dao.update_stats.assert_not_awaited()
    assert result["stars_earned"] == 0
