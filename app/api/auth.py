from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.cognito import get_cognito_client
from app.daos.parent_dao import ParentDAO
from app.db.session import get_db
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(cognito=get_cognito_client(), parent_dao=ParentDAO(db))


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, svc: AuthService = Depends(_auth_service)):
    tokens = await svc.register(body.email, body.password, body.pin)
    return TokenResponse(**tokens)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, svc: AuthService = Depends(_auth_service)):
    tokens = svc.login(body.email, body.password)
    return TokenResponse(**tokens)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, svc: AuthService = Depends(_auth_service)):
    tokens = svc.refresh(body.refresh_token)
    return TokenResponse(**tokens)
