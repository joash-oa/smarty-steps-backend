from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.cognito import CognitoAuthError, get_cognito_client
from app.core.config import settings
from app.daos.parent_dao import ParentDAO
from app.db.models import Parent
from app.db.session import get_db

bearer_scheme = HTTPBearer()


async def get_current_parent(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Parent:
    cognito = get_cognito_client()
    try:
        claims = cognito.verify_token(credentials.credentials)
    except CognitoAuthError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    cognito_id = claims.get("sub")
    parent = await ParentDAO(db).get_by_cognito_id(cognito_id)
    if not parent:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Parent not found")
    return parent


async def get_current_parent_dashboard(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Parent:
    try:
        payload = jwt.decode(
            credentials.credentials, settings.parent_jwt_secret, algorithms=["HS256"]
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )

    if payload.get("scope") != "parent_dashboard":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token scope")

    parent_id = payload.get("sub")
    parent = await ParentDAO(db).get_by_id(UUID(parent_id))
    if not parent:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Parent not found")
    return parent
