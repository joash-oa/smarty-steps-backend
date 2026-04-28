import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from testcontainers.postgres import PostgresContainer

from app.db.models import Base
from app.db.session import get_db
from app.main import app

_postgres = PostgresContainer("postgres:16", driver="asyncpg")


@pytest.fixture(scope="session", autouse=True)
def postgres_container():
    with _postgres as pg:
        yield pg


@pytest.fixture(scope="session")
def db_url(postgres_container):
    return postgres_container.get_connection_url()


@pytest.fixture(scope="session")
def test_engine(db_url):
    return create_async_engine(db_url, echo=False)


@pytest_asyncio.fixture(autouse=True)
async def db_session(test_engine):
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)() as session:
        yield session
        await session.rollback()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
