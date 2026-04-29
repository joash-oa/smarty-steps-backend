from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import LearnerNotFoundError, LearnerOwnershipError
from app.db.models import Learner, Parent
from app.services.learner_service import LearnerService


def _parent(pid=None):
    p = MagicMock(spec=Parent)
    p.id = pid or uuid4()
    return p


def _learner(lid=None, parent_id=None):
    learner = MagicMock(spec=Learner)
    learner.id = lid or uuid4()
    learner.parent_id = parent_id or uuid4()
    return learner


@pytest.mark.asyncio
async def test_get_raises_404_when_not_found():
    dao = MagicMock()
    dao.get_by_id = AsyncMock(return_value=None)
    svc = LearnerService(dao)
    with pytest.raises(LearnerNotFoundError):
        await svc.get(_parent(), uuid4())


@pytest.mark.asyncio
async def test_get_raises_403_when_wrong_parent():
    parent = _parent()
    learner = _learner(parent_id=uuid4())  # different parent
    dao = MagicMock()
    dao.get_by_id = AsyncMock(return_value=learner)
    svc = LearnerService(dao)
    with pytest.raises(LearnerOwnershipError):
        await svc.get(parent, learner.id)


@pytest.mark.asyncio
async def test_get_returns_learner_when_owned():
    parent = _parent()
    learner = _learner(parent_id=parent.id)
    dao = MagicMock()
    dao.get_by_id = AsyncMock(return_value=learner)
    svc = LearnerService(dao)
    result = await svc.get(parent, learner.id)
    assert result is learner


@pytest.mark.asyncio
async def test_list_delegates_to_dao():
    parent = _parent()
    learners = [_learner(parent_id=parent.id)]
    dao = MagicMock()
    dao.get_by_parent = AsyncMock(return_value=learners)
    svc = LearnerService(dao)
    result = await svc.list_for_parent(parent)
    assert result is learners
    dao.get_by_parent.assert_awaited_once_with(parent.id)
