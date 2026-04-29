import pytest
from jose import jwt

from app.core.config import settings


@pytest.mark.asyncio
async def test_verify_pin_returns_token(authed_client):
    client, _ = authed_client
    # authed_client fixture creates parent with PIN "1234" (hashed)
    response = await client.post("/parent/verify-pin", json={"pin": "1234"})
    assert response.status_code == 200
    body = response.json()
    assert "token" in body
    claims = jwt.decode(body["token"], settings.parent_jwt_secret, algorithms=["HS256"])
    assert claims["scope"] == "parent_dashboard"


@pytest.mark.asyncio
async def test_verify_pin_returns_401_for_wrong_pin(authed_client):
    client, _ = authed_client
    response = await client.post("/parent/verify-pin", json={"pin": "9999"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_verify_pin_rejects_non_4_digit(authed_client):
    client, _ = authed_client
    response = await client.post("/parent/verify-pin", json={"pin": "12"})
    assert response.status_code == 422
