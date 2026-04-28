from unittest.mock import MagicMock

import bcrypt
import pytest
from fastapi import HTTPException
from jose import jwt

from app.core.config import settings
from app.db.models import Parent
from app.services.parent_service import ParentService


def _parent_with_pin(pin: str = "1234"):
    p = MagicMock(spec=Parent)
    p.pin_hash = bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()
    return p


def test_correct_pin_returns_jwt():
    parent = _parent_with_pin("1234")
    svc = ParentService()
    token = svc.verify_pin_and_issue_token(parent, "1234")
    claims = jwt.decode(token, settings.parent_jwt_secret, algorithms=["HS256"])
    assert claims["scope"] == "parent_dashboard"


def test_wrong_pin_raises_401():
    parent = _parent_with_pin("1234")
    svc = ParentService()
    with pytest.raises(HTTPException) as exc:
        svc.verify_pin_and_issue_token(parent, "9999")
    assert exc.value.status_code == 401
