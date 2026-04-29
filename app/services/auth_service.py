import bcrypt

from app.clients.cognito import CognitoAuthError, CognitoClient, CognitoConflictError
from app.core.exceptions import DuplicateEmailError, InvalidCredentialsError, InvalidTokenError
from app.daos.parent_dao import ParentDAO


class AuthService:
    def __init__(self, cognito: CognitoClient, parent_dao: ParentDAO):
        self.cognito = cognito
        self.parent_dao = parent_dao

    async def register(self, email: str, password: str, pin: str) -> dict:
        existing = await self.parent_dao.get_by_email(email)
        if existing:
            raise DuplicateEmailError
        try:
            cognito_id = self.cognito.register(email, password)
        except CognitoConflictError:
            raise DuplicateEmailError

        pin_hash = bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()
        await self.parent_dao.create(cognito_id=cognito_id, email=email, pin_hash=pin_hash)

        tokens = self.cognito.login(email, password)
        return tokens

    def login(self, email: str, password: str) -> dict:
        try:
            return self.cognito.login(email, password)
        except CognitoAuthError:
            raise InvalidCredentialsError

    def refresh(self, refresh_token: str) -> dict:
        try:
            return self.cognito.refresh(refresh_token)
        except CognitoAuthError:
            raise InvalidTokenError
