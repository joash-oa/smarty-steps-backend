from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import HTTPException
from jose import jwt

from app.core.config import settings
from app.db.models import Parent


class ParentService:
    def verify_pin_and_issue_token(self, parent: Parent, pin: str) -> str:
        is_valid = bcrypt.checkpw(pin.encode(), parent.pin_hash.encode())
        if not is_valid:
            raise HTTPException(status_code=401, detail="Incorrect PIN")
        payload = {
            "sub": str(parent.id),
            "scope": "parent_dashboard",
            "exp": datetime.now(timezone.utc)
            + timedelta(minutes=settings.parent_jwt_expire_minutes),
        }
        return jwt.encode(payload, settings.parent_jwt_secret, algorithm="HS256")
