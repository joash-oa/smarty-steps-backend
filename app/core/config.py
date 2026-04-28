from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    cognito_user_pool_id: str
    cognito_client_id: str
    cognito_region: str = "us-east-1"
    anthropic_api_key: str
    parent_jwt_secret: str
    parent_jwt_expire_minutes: int = 15

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
