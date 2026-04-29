import pytest

from app.daos.learner_dao import LearnerDAO
from app.db.models import Chapter, Lesson, Standard

LESSON_CONTENT = {
    "exercises": [
        {
            "id": "ex_1",
            "type": "multiple_choice",
            "difficulty": "easy",
            "prompt": "Q?",
            "mascot_hint": "H",
            "options": [{"id": "a", "text": "A"}, {"id": "b", "text": "B"}],
            "correct_option_id": "b",
            "explanation": "Because.",
        },
    ]
}


async def _seed(db_session, parent, subject="math"):
    learner = await LearnerDAO(db_session).create(
        parent_id=parent.id, name="T", age=6, grade_level=1, avatar_emoji="🚀"
    )
    chapter = Chapter(subject=subject, title="Ch", order_index=80)
    db_session.add(chapter)
    standard = Standard(
        code=f"S-{id(db_session)}", subject=subject, grade_level=1, title="S", description="D"
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
        content=LESSON_CONTENT,
    )
    db_session.add(lesson)
    await db_session.flush()
    return learner, chapter, lesson


@pytest.mark.asyncio
async def test_check_answer_correct(authed_client, db_session):
    client, parent = authed_client
    _, _, lesson = await _seed(db_session, parent)
    response = await client.post(
        f"/lessons/{lesson.id}/check-answer",
        json={"exercise_id": "ex_1", "answer": {"selected_option_id": "b"}},
    )
    assert response.status_code == 200
    assert response.json()["correct"] is True
    assert response.json()["explanation"] == "Because."


@pytest.mark.asyncio
async def test_check_answer_wrong(authed_client, db_session):
    client, parent = authed_client
    _, _, lesson = await _seed(db_session, parent)
    response = await client.post(
        f"/lessons/{lesson.id}/check-answer",
        json={"exercise_id": "ex_1", "answer": {"selected_option_id": "a"}},
    )
    assert response.status_code == 200
    assert response.json()["correct"] is False
    assert response.json()["explanation"] is None


@pytest.mark.asyncio
async def test_submit_lesson_returns_stars(authed_client, db_session):
    client, parent = authed_client
    learner, _, lesson = await _seed(db_session, parent)
    response = await client.post(
        f"/learners/{learner.id}/progress",
        json={
            "lesson_id": str(lesson.id),
            "time_seconds": 60,
            "answers": {"ex_1": {"selected_option_id": "b"}},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["stars_earned"] == 3
    assert body["correct"] == 1
    assert body["total"] == 1
    assert body["xp_earned"] == 40


@pytest.mark.asyncio
async def test_submit_lesson_422_for_missing_answers(authed_client, db_session):
    client, parent = authed_client
    learner, _, lesson = await _seed(db_session, parent)
    response = await client.post(
        f"/learners/{learner.id}/progress",
        json={
            "lesson_id": str(lesson.id),
            "time_seconds": 60,
            "answers": {},  # ex_1 missing
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_progress_summary(authed_client, db_session):
    client, parent = authed_client
    learner, _, _ = await _seed(db_session, parent)
    response = await client.get(f"/learners/{learner.id}/progress")
    assert response.status_code == 200
    assert "summary" in response.json()
