from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.cognito import CognitoAuthError, get_cognito_client
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
