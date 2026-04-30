from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.db.models import ChapterQuiz, Learner
from app.services.quiz_service import QuizService

MOCK_QUIZ_CONTENT = {
    "exercises": [
        {
            "id": "ex_1",
            "type": "multiple_choice",
            "difficulty": "medium",
            "prompt": "Q?",
            "mascot_hint": "H",
            "options": [{"id": "a", "text": "A"}, {"id": "b", "text": "B"}],
            "correct_option_id": "a",
            "explanation": "E",
        },
        {
            "id": "ex_2",
            "type": "fill_blank",
            "difficulty": "easy",
            "prompt": "Fill",
            "sentence_parts": ["A", "_____", "B"],
            "word_bank": ["x", "y"],
            "correct_word": "x",
            "mascot_hint": "H",
        },
    ]
}


def _quiz(stars=0, completed=False):
    quiz = MagicMock(spec=ChapterQuiz)
    quiz.id = uuid4()
    quiz.stars_earned = stars
    quiz.completed = completed
    quiz.content = MOCK_QUIZ_CONTENT
    quiz.learner_id = uuid4()
    quiz.chapter_id = uuid4()
    return quiz


def _learner():
    learner = MagicMock(spec=Learner)
    learner.id = uuid4()
    learner.xp = 0
    learner.total_stars = 0
    learner.level = 1
    learner.streak_days = 0
    learner.last_active_at = None
    return learner


@pytest.mark.asyncio
async def test_get_quiz_raises_404_when_not_found():
    progress_dao = MagicMock()
    progress_dao.get_quiz_by_id = AsyncMock(return_value=None)
    svc = QuizService(
        lesson_dao=MagicMock(),
        progress_dao=progress_dao,
        claude=MagicMock(),
        learner_dao=MagicMock(),
    )
    with pytest.raises(HTTPException) as exc:
        await svc.get_quiz(uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_quiz_returns_sanitized_content():
    quiz = _quiz()
    progress_dao = MagicMock()
    progress_dao.get_quiz_by_id = AsyncMock(return_value=quiz)
    svc = QuizService(
        lesson_dao=MagicMock(),
        progress_dao=progress_dao,
        claude=MagicMock(),
        learner_dao=MagicMock(),
    )
    result = await svc.get_quiz(quiz.id)
    # correct answers must be stripped
    assert "correct_option_id" not in result["exercises"][0]
    assert "correct_word" not in result["exercises"][1]


@pytest.mark.asyncio
async def test_check_quiz_answer_correct():
    quiz = _quiz()
    progress_dao = MagicMock()
    progress_dao.get_quiz_by_id = AsyncMock(return_value=quiz)
    svc = QuizService(
        lesson_dao=MagicMock(),
        progress_dao=progress_dao,
        claude=MagicMock(),
        learner_dao=MagicMock(),
    )
    result = await svc.check_quiz_answer(quiz.id, "ex_1", {"selected_option_id": "a"})
    assert result["correct"] is True


@pytest.mark.asyncio
async def test_submit_quiz_best_score_only():
    """Re-submit with fewer stars → learner totals NOT updated."""
    learner = _learner()
    quiz = _quiz(stars=3, completed=True)
    quiz.learner_id = learner.id  # align ownership
    learner.xp = 70
    learner.total_stars = 6

    progress_dao = MagicMock()
    progress_dao.get_quiz_by_id = AsyncMock(return_value=quiz)
    progress_dao.update_quiz = AsyncMock(return_value=quiz)

    learner_dao = MagicMock()
    learner_dao.update_stats = AsyncMock()

    learner_svc = MagicMock()
    learner_svc.get = AsyncMock(return_value=learner)

    svc = QuizService(
        lesson_dao=MagicMock(),
        progress_dao=progress_dao,
        claude=MagicMock(),
        learner_dao=learner_dao,
    )
    result = await svc.submit_quiz(
        parent=MagicMock(),
        quiz_id=quiz.id,
        time_seconds=120,
        answers={"ex_1": {"selected_option_id": "z"}, "ex_2": {"selected_word": "z"}},
        learner_svc=learner_svc,
    )
    # 0 effective stars < 6 existing → no update
    learner_dao.update_stats.assert_not_awaited()
    assert result["stars_earned"] == 0
