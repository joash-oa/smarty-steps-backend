from unittest.mock import MagicMock, patch

import pytest

REGISTER_PAYLOAD = {"email": "parent@example.com", "password": "Pass123!", "pin": "1234"}


@pytest.mark.asyncio
async def test_register_returns_tokens(client):
    mock_cognito = MagicMock()
    mock_cognito.register = MagicMock(return_value="cognito-sub-abc")
    mock_cognito.login = MagicMock(
        return_value={
            "access_token": "fake-access",
            "refresh_token": "fake-refresh",
        }
    )
    with patch("app.api.auth.get_cognito_client", return_value=mock_cognito):
        response = await client.post("/auth/register", json=REGISTER_PAYLOAD)
    assert response.status_code == 201
    body = response.json()
    assert body["access_token"] == "fake-access"
    assert body["refresh_token"] == "fake-refresh"
    assert body["token_type"] == "Bearer"


@pytest.mark.asyncio
async def test_register_rejects_invalid_pin(client):
    response = await client.post("/auth/register", json={**REGISTER_PAYLOAD, "pin": "12"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_returns_tokens(client):
    mock_cognito = MagicMock()
    mock_cognito.login = MagicMock(
        return_value={
            "access_token": "fake-access",
            "refresh_token": "fake-refresh",
        }
    )
    with patch("app.api.auth.get_cognito_client", return_value=mock_cognito):
        response = await client.post(
            "/auth/login", json={"email": "parent@example.com", "password": "Pass123!"}
        )
    assert response.status_code == 200
    assert response.json()["access_token"] == "fake-access"


@pytest.mark.asyncio
async def test_login_401_on_bad_credentials(client):
    from app.clients.cognito import CognitoAuthError

    mock_cognito = MagicMock()
    mock_cognito.login = MagicMock(side_effect=CognitoAuthError("bad"))
    with patch("app.api.auth.get_cognito_client", return_value=mock_cognito):
        response = await client.post("/auth/login", json={"email": "x@x.com", "password": "wrong"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_returns_new_access_token(client):
    mock_cognito = MagicMock()
    mock_cognito.refresh = MagicMock(return_value={"access_token": "new-access"})
    with patch("app.api.auth.get_cognito_client", return_value=mock_cognito):
        response = await client.post("/auth/refresh", json={"refresh_token": "old-refresh"})
    assert response.status_code == 200
    assert response.json()["access_token"] == "new-access"
