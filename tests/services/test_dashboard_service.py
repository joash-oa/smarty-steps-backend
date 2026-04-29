from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.db.models import Learner, Parent
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


@pytest.mark.asyncio
async def test_get_stats_delegates_to_dao():
    parent = _parent()
    learner = _learner(parent_id=parent.id)

    learner_svc = MagicMock()
    learner_svc.get = AsyncMock(return_value=learner)

    fake_stats = {
        "time_per_subject": {"math": 100, "science": 0, "english": 0},
        "mastered": [{"lesson_id": str(uuid4()), "title": "L", "subject": "math"}],
        "needs_practice": [],
        "recent_activity": [],
    }
    dashboard_dao = MagicMock()
    dashboard_dao.get_stats = AsyncMock(return_value=fake_stats)

    svc = DashboardService(dashboard_dao)
    result = await svc.get_stats(parent, learner.id, learner_svc)

    dashboard_dao.get_stats.assert_awaited_once_with(learner.id)
    assert result["time_per_subject"]["math"] == 100


@pytest.mark.asyncio
async def test_get_stats_403_when_learner_not_owned():
    parent = _parent()

    learner_svc = MagicMock()
    learner_svc.get = AsyncMock(side_effect=HTTPException(status_code=403, detail="Not owned"))

    svc = DashboardService(MagicMock())
    with pytest.raises(HTTPException) as exc:
        await svc.get_stats(parent, uuid4(), learner_svc)
    assert exc.value.status_code == 403
