import pytest

from app.daos.parent_dao import ParentDAO


@pytest.mark.asyncio
async def test_create_and_get_parent_by_cognito_id(db_session):
    dao = ParentDAO(db_session)
    parent = await dao.create(
        cognito_id="cognito-123",
        email="test@example.com",
        pin_hash="$2b$12$hashed",
    )
    assert parent.id is not None
    assert parent.email == "test@example.com"

    fetched = await dao.get_by_cognito_id("cognito-123")
    assert fetched is not None
    assert fetched.id == parent.id


@pytest.mark.asyncio
async def test_get_by_email_returns_none_when_missing(db_session):
    dao = ParentDAO(db_session)
    result = await dao.get_by_email("missing@example.com")
    assert result is None


@pytest.mark.asyncio
async def test_get_by_id_returns_parent(db_session):
    dao = ParentDAO(db_session)
    parent = await dao.create(
        cognito_id="cog-get-by-id",
        email="getbyid@example.com",
        pin_hash="$2b$12$hash",
    )
    fetched = await dao.get_by_id(parent.id)
    assert fetched is not None
    assert fetched.id == parent.id


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_missing(db_session):
    from uuid_extensions import uuid7

    dao = ParentDAO(db_session)
    result = await dao.get_by_id(uuid7())
    assert result is None
