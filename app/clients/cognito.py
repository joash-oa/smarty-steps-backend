import boto3
from botocore.exceptions import ClientError
from jose import jwt, jwk
from jose.utils import base64url_decode
import httpx
from functools import lru_cache
from app.core.config import settings


class CognitoAuthError(Exception):
    pass


class CognitoConflictError(Exception):
    pass


class CognitoClient:
    def __init__(self):
        self.client = boto3.client("cognito-idp", region_name=settings.cognito_region)
        self.user_pool_id = settings.cognito_user_pool_id
        self.client_id = settings.cognito_client_id
        self._jwks_url = (
            f"https://cognito-idp.{settings.cognito_region}.amazonaws.com"
            f"/{settings.cognito_user_pool_id}/.well-known/jwks.json"
        )

    async def register(self, email: str, password: str) -> str:
        """Sign up a new user. Returns the Cognito sub (user ID)."""
        try:
            response = self.client.sign_up(
                ClientId=self.client_id,
                Username=email,
                Password=password,
                UserAttributes=[{"Name": "email", "Value": email}],
            )
            self.client.admin_confirm_sign_up(
                UserPoolId=self.user_pool_id,
                Username=email,
            )
            return response["UserSub"]
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code == "UsernameExistsException":
                raise CognitoConflictError("Email already registered")
            raise CognitoAuthError(str(e))

    def login(self, email: str, password: str) -> dict:
        """Returns {'access_token': str, 'refresh_token': str}."""
        try:
            response = self.client.initiate_auth(
                AuthFlow="USER_PASSWORD_AUTH",
                AuthParameters={"USERNAME": email, "PASSWORD": password},
                ClientId=self.client_id,
            )
            result = response["AuthenticationResult"]
            return {
                "access_token": result["AccessToken"],
                "refresh_token": result["RefreshToken"],
            }
        except ClientError:
            raise CognitoAuthError("Invalid credentials")

    def refresh(self, refresh_token: str) -> dict:
        """Returns {'access_token': str}."""
        try:
            response = self.client.initiate_auth(
                AuthFlow="REFRESH_TOKEN_AUTH",
                AuthParameters={"REFRESH_TOKEN": refresh_token},
                ClientId=self.client_id,
            )
            result = response["AuthenticationResult"]
            return {"access_token": result["AccessToken"]}
        except ClientError:
            raise CognitoAuthError("Invalid or expired refresh token")

    @lru_cache(maxsize=1)
    def _get_jwks(self) -> dict:
        response = httpx.get(self._jwks_url)
        return response.json()

    def verify_token(self, access_token: str) -> dict:
        """Verify Cognito access token. Returns decoded claims."""
        try:
            header = jwt.get_unverified_header(access_token)
            jwks = self._get_jwks()
            key = next(k for k in jwks["keys"] if k["kid"] == header["kid"])
            public_key = jwk.construct(key)
            message, encoded_sig = access_token.rsplit(".", 1)
            decoded_sig = base64url_decode(encoded_sig.encode())
            if not public_key.verify(message.encode(), decoded_sig):
                raise CognitoAuthError("Invalid token signature")
            claims = jwt.get_unverified_claims(access_token)
            return claims
        except (StopIteration, Exception) as e:
            raise CognitoAuthError(f"Token verification failed: {e}")


_cognito_client: CognitoClient | None = None


def get_cognito_client() -> CognitoClient:
    global _cognito_client
    if _cognito_client is None:
        _cognito_client = CognitoClient()
    return _cognito_client
