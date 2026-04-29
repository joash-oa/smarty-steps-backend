import pytest
from uuid_extensions import uuid7

from app.daos.learner_dao import LearnerDAO
from app.db.models import Chapter, ChapterQuiz

QUIZ_CONTENT = {
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
    ]
}


async def _seed_quiz(db_session, parent, learner=None):
    if learner is None:
        learner = await LearnerDAO(db_session).create(
            parent_id=parent.id, name="T", age=6, grade_level=1, avatar_emoji="🚀"
        )
    chapter = Chapter(subject="math", title="Quiz Ch", order_index=75)
    db_session.add(chapter)
    await db_session.flush()
    quiz = ChapterQuiz(
        learner_id=learner.id,
        chapter_id=chapter.id,
        difficulty="medium",
        content=QUIZ_CONTENT,
    )
    db_session.add(quiz)
    await db_session.flush()
    return learner, quiz


@pytest.mark.asyncio
async def test_get_quiz_returns_sanitized(authed_client, db_session):
    client, parent = authed_client
    _, quiz = await _seed_quiz(db_session, parent)
    response = await client.get(f"/chapter-quizzes/{quiz.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["difficulty"] == "medium"
    assert "correct_option_id" not in body["exercises"][0]


@pytest.mark.asyncio
async def test_get_quiz_returns_404_when_not_found(authed_client):
    client, _ = authed_client
    response = await client.get(f"/chapter-quizzes/{uuid7()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_check_quiz_answer_correct(authed_client, db_session):
    client, parent = authed_client
    _, quiz = await _seed_quiz(db_session, parent)
    response = await client.post(
        f"/chapter-quizzes/{quiz.id}/check-answer",
        json={"exercise_id": "ex_1", "answer": {"selected_option_id": "a"}},
    )
    assert response.status_code == 200
    assert response.json()["correct"] is True


@pytest.mark.asyncio
async def test_submit_quiz_returns_effective_stars(authed_client, db_session):
    client, parent = authed_client
    learner, quiz = await _seed_quiz(db_session, parent)
    response = await client.post(
        f"/chapter-quizzes/{quiz.id}/submit",
        json={
            "time_seconds": 120,
            "answers": {"ex_1": {"selected_option_id": "a"}},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["stars_earned"] == 3
    assert body["effective_stars"] == 6
    assert body["xp_earned"] == 70
