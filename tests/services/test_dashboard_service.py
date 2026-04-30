from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import LearnerOwnershipError
from app.db.models import Learner, Lesson, LessonProgress, Parent
from app.services.dashboard_service import DashboardService


def _parent():
    parent = MagicMock(spec=Parent)
    parent.id = uuid4()
    return parent


def _learner(parent_id=None):
    learner = MagicMock(spec=Learner)
    learner.id = uuid4()
    learner.parent_id = parent_id or uuid4()
    return learner


def _row(subject="math", stars=3, time_seconds=60, completed_at=None):
    progress = MagicMock(spec=LessonProgress)
    progress.stars_earned = stars
    progress.time_seconds = time_seconds
    progress.completed_at = completed_at or datetime(2026, 1, 1)

    lesson = MagicMock(spec=Lesson)
    lesson.id = uuid4()
    lesson.title = f"Lesson {uuid4().hex[:4]}"
    lesson.subject = subject

    return (progress, lesson)


def _dao(rows):
    dao = MagicMock()
    dao.get_completed_progress_rows = AsyncMock(return_value=rows)
    return dao


@pytest.mark.asyncio
async def test_get_stats_sums_time_per_subject():
    parent = _parent()
    learner = _learner(parent_id=parent.id)
    learner_svc = MagicMock()
    learner_svc.get = AsyncMock(return_value=learner)

    rows = [
        _row(subject="math", stars=3, time_seconds=100),
        _row(subject="math", stars=2, time_seconds=50),
        _row(subject="science", stars=3, time_seconds=200),
    ]
    svc = DashboardService(_dao(rows))
    result = await svc.get_stats(parent, learner.id, learner_svc)

    assert result["time_per_subject"]["math"] == 150
    assert result["time_per_subject"]["science"] == 200
    assert result["time_per_subject"]["english"] == 0


@pytest.mark.asyncio
async def test_get_stats_categorizes_mastered_and_needs_practice():
    parent = _parent()
    learner = _learner(parent_id=parent.id)
    learner_svc = MagicMock()
    learner_svc.get = AsyncMock(return_value=learner)

    rows = [
        _row(subject="math", stars=3),
        _row(subject="english", stars=1),
        _row(subject="science", stars=2),
    ]
    svc = DashboardService(_dao(rows))
    result = await svc.get_stats(parent, learner.id, learner_svc)

    assert len(result["mastered"]) == 1
    assert result["mastered"][0]["subject"] == "math"
    assert len(result["needs_practice"]) == 1
    assert result["needs_practice"][0]["subject"] == "english"


@pytest.mark.asyncio
async def test_get_stats_limits_recent_activity_to_ten():
    parent = _parent()
    learner = _learner(parent_id=parent.id)
    learner_svc = MagicMock()
    learner_svc.get = AsyncMock(return_value=learner)

    rows = [_row(stars=3) for _ in range(15)]
    svc = DashboardService(_dao(rows))
    result = await svc.get_stats(parent, learner.id, learner_svc)

    assert len(result["recent_activity"]) == 10


@pytest.mark.asyncio
async def test_get_stats_calls_dao_with_learner_id():
    parent = _parent()
    learner = _learner(parent_id=parent.id)
    learner_svc = MagicMock()
    learner_svc.get = AsyncMock(return_value=learner)

    dao = _dao([])
    svc = DashboardService(dao)
    await svc.get_stats(parent, learner.id, learner_svc)

    dao.get_completed_progress_rows.assert_awaited_once_with(learner.id)


@pytest.mark.asyncio
async def test_get_stats_raises_when_learner_not_owned():
    parent = _parent()
    learner_svc = MagicMock()
    learner_svc.get = AsyncMock(side_effect=LearnerOwnershipError())

    svc = DashboardService(MagicMock())
    with pytest.raises(LearnerOwnershipError):
        await svc.get_stats(parent, uuid4(), learner_svc)
