from app.core.config import settings


def test_settings_loads():
    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert settings.cognito_user_pool_id != ""
    assert settings.cognito_client_id != ""
    assert settings.parent_jwt_secret != ""
