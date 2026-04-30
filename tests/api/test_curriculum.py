import pytest
from uuid_extensions import uuid7

from app.daos.learner_dao import LearnerDAO
from app.db.models import Chapter, Lesson, Standard

LESSON_CONTENT = {
    "intro": {"title": "T", "description": "D", "mascot_quote": "Q"},
    "exercises": [
        {
            "id": "ex_1",
            "type": "multiple_choice",
            "difficulty": "easy",
            "prompt": "Q?",
            "mascot_hint": "H",
            "options": [{"id": "a", "text": "A"}],
            "correct_option_id": "a",
            "explanation": "E",
        },
    ],
    "result": {"badge_name": "B", "badge_description": "BD"},
    "stars_available": 3,
}


async def _seed_curriculum(db_session, subject="math"):
    chapter = Chapter(subject=subject, title="Test Domain", order_index=50)
    db_session.add(chapter)
    await db_session.flush()

    standard = Standard(
        code=f"NY-T-{uuid7()}",
        subject=subject,
        grade_level=1,
        title="Test Standard",
        description="D",
    )
    db_session.add(standard)
    await db_session.flush()

    lesson = Lesson(
        chapter_id=chapter.id,
        standard_id=standard.id,
        subject=subject,
        title="Test Lesson",
        difficulty="easy",
        order_index=1,
        content=LESSON_CONTENT,
    )
    db_session.add(lesson)
    await db_session.flush()
    return chapter, lesson


@pytest.mark.asyncio
async def test_get_curriculum_returns_chapters(authed_client, db_session):
    client, parent = authed_client
    chapter, _ = await _seed_curriculum(db_session)
    learner = await LearnerDAO(db_session).create(
        parent_id=parent.id, name="Test", age=6, grade_level=1, avatar_emoji="🦋"
    )
    response = await client.get(f"/subjects/math/chapters?learner_id={learner.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["subject"] == "math"
    chapter_ids = [c["id"] for c in body["chapters"]]
    assert str(chapter.id) in chapter_ids


@pytest.mark.asyncio
async def test_get_curriculum_returns_400_for_invalid_subject(authed_client, db_session):
    client, parent = authed_client
    learner = await LearnerDAO(db_session).create(
        parent_id=parent.id, name="X", age=5, grade_level=0, avatar_emoji="🚀"
    )
    response = await client.get(f"/subjects/invalid/chapters?learner_id={learner.id}")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_curriculum_returns_403_for_wrong_learner(authed_client):
    client, _ = authed_client
    response = await client.get(f"/subjects/math/chapters?learner_id={uuid7()}")
    assert response.status_code in (403, 404)


@pytest.mark.asyncio
async def test_get_lesson_returns_sanitized_content(authed_client, db_session):
    client, _ = authed_client
    _, lesson = await _seed_curriculum(db_session, subject="science")
    response = await client.get(f"/lessons/{lesson.id}")
    assert response.status_code == 200
    body = response.json()
    exercise = body["content"]["exercises"][0]
    assert "correct_option_id" not in exercise
    assert "explanation" not in exercise


@pytest.mark.asyncio
async def test_get_lesson_returns_404_for_nonexistent(authed_client):
    client, _ = authed_client
    response = await client.get(f"/lessons/{uuid7()}")
    assert response.status_code == 404
