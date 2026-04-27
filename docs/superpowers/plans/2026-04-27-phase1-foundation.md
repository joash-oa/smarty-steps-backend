# Smarty Steps Backend — Phase 1: Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Working FastAPI skeleton with PostgreSQL, Cognito auth (register/login/refresh), JWT middleware, health check, Docker Compose local dev, Docker Compose prod, and GitHub Actions CI/CD to staging and prod EC2 instances.

**Architecture:** 3-layer: routers → services → DAOs. No business logic in routers. No DB calls outside DAOs. Services never import FastAPI. DAOs never contain business logic.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy (async) + asyncpg, Alembic, PostgreSQL 16, AWS Cognito (boto3 + python-jose), bcrypt, httpx, uuid7 (Python-side UUID v7), pytest-asyncio, testcontainers[postgres], Docker Compose, EC2, GitHub Actions

---

## File Structure

```
app/
  __init__.py
  main.py                    — FastAPI app, lifespan hook
  core/
    __init__.py
    config.py                — pydantic-settings Settings
  db/
    __init__.py
    session.py               — async engine, sessionmaker, get_db
    models.py                — all SQLAlchemy ORM models (all 7 tables)
  schemas/
    __init__.py
    auth.py                  — RegisterRequest, LoginRequest, RefreshRequest, TokenResponse
  clients/
    __init__.py
    cognito.py               — CognitoClient (register, login, refresh, verify_token)
  services/
    __init__.py
    auth_service.py          — AuthService (register, login, refresh)
  daos/
    __init__.py
    parent_dao.py            — ParentDAO (create, get_by_cognito_id, get_by_email)
  api/
    __init__.py
    deps.py                  — get_db, get_current_parent
    health.py                — GET /health
    auth.py                  — POST /auth/register, /auth/login, /auth/refresh
alembic.ini
alembic/
  env.py
  versions/
    001_initial.py           — pg_uuidv7, all tables, all indexes
.env.example
Dockerfile
docker-compose.yml           — local dev (FastAPI + PostgreSQL)
docker-compose.prod.yml      — EC2 prod (FastAPI only, RDS for DB)
.github/
  workflows/
    ci.yml                   — run tests on every PR
    deploy-staging.yml       — push to main → deploy to staging EC2
    deploy-prod.yml          — manual trigger → deploy to prod EC2
tests/
  __init__.py
  conftest.py                — async test DB, AsyncClient fixture
  api/
    __init__.py
    test_health.py
    test_auth.py
  daos/
    __init__.py
    test_parent_dao.py
```

---

### Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `app/__init__.py`, `app/core/__init__.py`, `app/db/__init__.py`, `app/schemas/__init__.py`, `app/clients/__init__.py`, `app/services/__init__.py`, `app/daos/__init__.py`, `app/api/__init__.py`
- Create: `tests/__init__.py`, `tests/api/__init__.py`, `tests/daos/__init__.py`, `tests/services/__init__.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[tool.poetry]
name = "smarty-steps-backend"
version = "0.1.0"
description = "Smarty Steps learning app backend"
authors = ["Joash Owusu-Ansah"]

[tool.poetry.dependencies]
python = "^3.12"
fastapi = "^0.115.0"
uvicorn = {extras = ["standard"], version = "^0.30.0"}
sqlalchemy = {extras = ["asyncio"], version = "^2.0.0"}
asyncpg = "^0.30.0"
alembic = "^1.13.0"
pydantic-settings = "^2.3.0"
bcrypt = "^4.1.0"
httpx = "^0.27.0"
anthropic = "^0.30.0"
python-jose = {extras = ["cryptography"], version = "^3.3.0"}
boto3 = "^1.34.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.2.0"
pytest-asyncio = "^0.23.0"
anyio = {extras = ["trio"], version = "^4.4.0"}

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

- [ ] **Step 2: Create `.env.example`**

```env
DATABASE_URL=postgresql+asyncpg://smarty:smarty@localhost:5432/smarty_steps
TEST_DATABASE_URL=postgresql+asyncpg://smarty:smarty@localhost:5432/smarty_steps_test
COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
COGNITO_CLIENT_ID=XXXXXXXXXXXXXXXXXXXXXXXXXX
COGNITO_REGION=us-east-1
ANTHROPIC_API_KEY=sk-ant-...
PARENT_JWT_SECRET=change-me-in-production
PARENT_JWT_EXPIRE_MINUTES=15
```

- [ ] **Step 3: Create all `__init__.py` files (all empty)**

```bash
touch app/__init__.py app/core/__init__.py app/db/__init__.py \
  app/schemas/__init__.py app/clients/__init__.py \
  app/services/__init__.py app/daos/__init__.py app/api/__init__.py \
  tests/__init__.py tests/api/__init__.py tests/daos/__init__.py \
  tests/services/__init__.py
```

- [ ] **Step 4: Install dependencies**

```bash
poetry install
```

Expected: dependencies installed, `poetry.lock` created.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml poetry.lock .env.example app/ tests/
git commit -m "feat: scaffold project structure"
```

---

### Task 2: Core config

**Files:**
- Create: `app/core/config.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_config.py`:

```python
from app.core.config import settings

def test_settings_loads():
    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert settings.cognito_user_pool_id != ""
    assert settings.cognito_client_id != ""
    assert settings.parent_jwt_secret != ""
```

- [ ] **Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/test_config.py -v
```

Expected: `ImportError: cannot import name 'settings' from 'app.core.config'`

- [ ] **Step 3: Implement `app/core/config.py`**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    test_database_url: str
    cognito_user_pool_id: str
    cognito_client_id: str
    cognito_region: str = "us-east-1"
    anthropic_api_key: str
    parent_jwt_secret: str
    parent_jwt_expire_minutes: int = 15

    model_config = {"env_file": ".env"}


settings = Settings()
```

- [ ] **Step 4: Create `.env` from `.env.example` (local only, not committed)**

```bash
cp .env.example .env
# Fill in real values for local dev
```

- [ ] **Step 5: Run test to verify it passes**

```bash
poetry run pytest tests/test_config.py -v
```

Expected: `PASSED`

- [ ] **Step 6: Commit**

```bash
git add app/core/config.py
git commit -m "feat: add pydantic-settings config"
```

---

### Task 3: DB session + ORM models

**Files:**
- Create: `app/db/session.py`
- Create: `app/db/models.py`

- [ ] **Step 1: Write `app/db/session.py`**

No test needed — this is infrastructure wired at startup. We'll verify it works in Task 5 (health check test hits the DB).

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings

engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

- [ ] **Step 2: Write `app/db/models.py`**

UUIDs are generated in Python using the `uuid7` library (`import uuid7; uuid7.uuid7()`). No `pg_uuidv7` extension required — standard `postgres:16` works.

```python
import uuid7
from sqlalchemy import (
    Column, String, Integer, Boolean, Text, ForeignKey,
    DateTime, UniqueConstraint, Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class Parent(Base):
    __tablename__ = "parents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7.uuid7)
    cognito_id = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    pin_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    learners = relationship("Learner", back_populates="parent", cascade="all, delete-orphan")


class Learner(Base):
    __tablename__ = "learners"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7.uuid7)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("parents.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    grade_level = Column(Integer, nullable=False)
    avatar_emoji = Column(String, nullable=False, server_default="🚀")
    total_stars = Column(Integer, server_default="0")
    level = Column(Integer, server_default="1")
    xp = Column(Integer, server_default="0")
    streak_days = Column(Integer, server_default="0")
    last_active_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    parent = relationship("Parent", back_populates="learners")

    __table_args__ = (
        Index("idx_learners_parent_id", "parent_id"),
        Index("idx_learners_total_stars", "total_stars"),
        Index("idx_learners_last_active", "last_active_at"),
    )


class Standard(Base):
    __tablename__ = "standards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7.uuid7)
    code = Column(String, unique=True, nullable=False)
    subject = Column(String, nullable=False)
    grade_level = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_standards_subject_grade", "subject", "grade_level"),
    )


class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7.uuid7)
    subject = Column(String, nullable=False)
    title = Column(String, nullable=False)
    order_index = Column(Integer, nullable=False)

    lessons = relationship("Lesson", back_populates="chapter", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_chapters_subject_order", "subject", "order_index"),
    )


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7.uuid7)
    chapter_id = Column(UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False)
    standard_id = Column(UUID(as_uuid=True), ForeignKey("standards.id", ondelete="SET NULL"), nullable=True)
    subject = Column(String, nullable=False)
    title = Column(String, nullable=False)
    difficulty = Column(String, nullable=False, server_default="easy")
    order_index = Column(Integer, nullable=False)
    content = Column(JSONB, nullable=False)
    stars_available = Column(Integer, server_default="3")

    chapter = relationship("Chapter", back_populates="lessons")

    __table_args__ = (
        Index("idx_lessons_chapter_order", "chapter_id", "order_index"),
        Index("idx_lessons_standard", "standard_id"),
    )


class LessonProgress(Base):
    __tablename__ = "lesson_progress"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7.uuid7)
    learner_id = Column(UUID(as_uuid=True), ForeignKey("learners.id", ondelete="CASCADE"), nullable=False)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    completed = Column(Boolean, server_default="false")
    stars_earned = Column(Integer, server_default="0")
    score_correct = Column(Integer, nullable=True)
    score_total = Column(Integer, nullable=True)
    time_seconds = Column(Integer, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("learner_id", "lesson_id", name="uq_lesson_progress"),
        Index("idx_lesson_progress_learner", "learner_id"),
    )


class ChapterQuiz(Base):
    __tablename__ = "chapter_quizzes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7.uuid7)
    learner_id = Column(UUID(as_uuid=True), ForeignKey("learners.id", ondelete="CASCADE"), nullable=False)
    chapter_id = Column(UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False)
    difficulty = Column(String, nullable=False)
    content = Column(JSONB, nullable=False)
    stars_earned = Column(Integer, server_default="0")
    score_correct = Column(Integer, nullable=True)
    score_total = Column(Integer, nullable=True)
    time_seconds = Column(Integer, nullable=True)
    completed = Column(Boolean, server_default="false")
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("learner_id", "chapter_id", name="uq_chapter_quiz"),
    )
```

- [ ] **Step 3: Commit**

```bash
git add app/db/session.py app/db/models.py
git commit -m "feat: add DB session and ORM models"
```

---

### Task 4: Alembic setup + initial migration

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/versions/001_initial.py`

- [ ] **Step 1: Initialize Alembic**

```bash
poetry run alembic init alembic
```

Expected: `alembic.ini` and `alembic/` directory created.

- [ ] **Step 2: Update `alembic.ini` — set DB URL placeholder**

In `alembic.ini`, replace the `sqlalchemy.url` line:

```ini
sqlalchemy.url = driver://user:pass@localhost/dbname
```

with:

```ini
# URL is set programmatically in env.py from app settings
sqlalchemy.url =
```

- [ ] **Step 3: Replace `alembic/env.py`**

```python
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
from app.core.config import settings
from app.db.models import Base

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

- [ ] **Step 4: Create `alembic/versions/001_initial.py`**

No `pg_uuidv7` extension needed — UUIDs are generated by Python. PKs use `gen_random_uuid()` as a safe DB-side fallback for any raw SQL inserts.

```python
"""Initial schema — all 7 tables + indexes

Revision ID: 001
Revises:
Create Date: 2026-04-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "parents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("cognito_id", sa.String, unique=True, nullable=False),
        sa.Column("email", sa.String, unique=True, nullable=False),
        sa.Column("pin_hash", sa.String, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "learners",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("parent_id", UUID(as_uuid=True), sa.ForeignKey("parents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("age", sa.Integer, nullable=False),
        sa.Column("grade_level", sa.Integer, nullable=False),
        sa.Column("avatar_emoji", sa.String, nullable=False, server_default="🚀"),
        sa.Column("total_stars", sa.Integer, server_default="0"),
        sa.Column("level", sa.Integer, server_default="1"),
        sa.Column("xp", sa.Integer, server_default="0"),
        sa.Column("streak_days", sa.Integer, server_default="0"),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_learners_parent_id", "learners", ["parent_id"])
    op.create_index("idx_learners_total_stars", "learners", ["total_stars"])
    op.create_index("idx_learners_last_active", "learners", ["last_active_at"])

    op.create_table(
        "standards",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String, unique=True, nullable=False),
        sa.Column("subject", sa.String, nullable=False),
        sa.Column("grade_level", sa.Integer, nullable=False),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_standards_subject_grade", "standards", ["subject", "grade_level"])

    op.create_table(
        "chapters",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("subject", sa.String, nullable=False),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("order_index", sa.Integer, nullable=False),
    )
    op.create_index("idx_chapters_subject_order", "chapters", ["subject", "order_index"])

    op.create_table(
        "lessons",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("chapter_id", UUID(as_uuid=True), sa.ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("standard_id", UUID(as_uuid=True), sa.ForeignKey("standards.id", ondelete="SET NULL"), nullable=True),
        sa.Column("subject", sa.String, nullable=False),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("difficulty", sa.String, nullable=False, server_default="easy"),
        sa.Column("order_index", sa.Integer, nullable=False),
        sa.Column("content", JSONB, nullable=False),
        sa.Column("stars_available", sa.Integer, server_default="3"),
    )
    op.create_index("idx_lessons_chapter_order", "lessons", ["chapter_id", "order_index"])
    op.create_index("idx_lessons_standard", "lessons", ["standard_id"])

    op.create_table(
        "lesson_progress",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("learner_id", UUID(as_uuid=True), sa.ForeignKey("learners.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lesson_id", UUID(as_uuid=True), sa.ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("completed", sa.Boolean, server_default="false"),
        sa.Column("stars_earned", sa.Integer, server_default="0"),
        sa.Column("score_correct", sa.Integer, nullable=True),
        sa.Column("score_total", sa.Integer, nullable=True),
        sa.Column("time_seconds", sa.Integer, nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("learner_id", "lesson_id", name="uq_lesson_progress"),
    )
    op.create_index("idx_lesson_progress_learner", "lesson_progress", ["learner_id"])

    op.create_table(
        "chapter_quizzes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("learner_id", UUID(as_uuid=True), sa.ForeignKey("learners.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chapter_id", UUID(as_uuid=True), sa.ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("difficulty", sa.String, nullable=False),
        sa.Column("content", JSONB, nullable=False),
        sa.Column("stars_earned", sa.Integer, server_default="0"),
        sa.Column("score_correct", sa.Integer, nullable=True),
        sa.Column("score_total", sa.Integer, nullable=True),
        sa.Column("time_seconds", sa.Integer, nullable=True),
        sa.Column("completed", sa.Boolean, server_default="false"),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("learner_id", "chapter_id", name="uq_chapter_quiz"),
    )


def downgrade() -> None:
    op.drop_table("chapter_quizzes")
    op.drop_table("lesson_progress")
    op.drop_table("lessons")
    op.drop_table("chapters")
    op.drop_table("standards")
    op.drop_table("learners")
    op.drop_table("parents")
    op.execute("DROP EXTENSION IF EXISTS pg_uuidv7")
```

- [ ] **Step 5: Start local PostgreSQL and run migration**

```bash
docker run -d --name smarty-pg \
  -e POSTGRES_USER=smarty \
  -e POSTGRES_PASSWORD=smarty \
  -e POSTGRES_DB=smarty_steps \
  -p 5432:5432 postgres:16

poetry run alembic upgrade head
```

Expected: `Running upgrade -> 001, Initial schema — all tables + pg_uuidv7 extension`

- [ ] **Step 6: Commit**

```bash
git add alembic.ini alembic/
git commit -m "feat: add Alembic and initial migration with all tables"
```

---

### Task 5: pytest conftest + test DB fixtures

**Files:**
- Create: `tests/conftest.py`

- [ ] **Step 1: Write `tests/conftest.py`**

Uses `testcontainers[postgres]` — no manual DB setup. A PostgreSQL 16 container spins up automatically for the test session, schema created via `Base.metadata.create_all`, rolled back after each test.

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add tests/conftest.py
git commit -m "feat: add pytest conftest with testcontainers postgres and async fixtures"
```

---

### Task 6: FastAPI app + health check

**Files:**
- Create: `app/main.py`
- Create: `app/api/health.py`
- Create: `tests/api/test_health.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/api/test_health.py
import pytest

@pytest.mark.asyncio
async def test_health_returns_200(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/api/test_health.py -v
```

Expected: `FAILED` — `ImportError` or `404` (app not wired yet).

- [ ] **Step 3: Implement `app/api/health.py`**

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 4: Implement `app/main.py`**

```python
from fastapi import FastAPI
from app.api import health

app = FastAPI(title="Smarty Steps")

app.include_router(health.router)
```

- [ ] **Step 5: Run test to verify it passes**

```bash
poetry run pytest tests/api/test_health.py -v
```

Expected: `PASSED`

- [ ] **Step 6: Commit**

```bash
git add app/main.py app/api/health.py tests/api/test_health.py
git commit -m "feat: add FastAPI app and health check endpoint"
```

---

### Task 7: ParentDAO

**Files:**
- Create: `app/daos/parent_dao.py`
- Create: `tests/daos/test_parent_dao.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/daos/test_parent_dao.py
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
poetry run pytest tests/daos/test_parent_dao.py -v
```

Expected: `ImportError: cannot import name 'ParentDAO'`

- [ ] **Step 3: Implement `app/daos/parent_dao.py`**

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Parent


class ParentDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, cognito_id: str, email: str, pin_hash: str) -> Parent:
        parent = Parent(cognito_id=cognito_id, email=email, pin_hash=pin_hash)
        self.session.add(parent)
        await self.session.flush()
        await self.session.refresh(parent)
        return parent

    async def get_by_cognito_id(self, cognito_id: str) -> Parent | None:
        result = await self.session.execute(
            select(Parent).where(Parent.cognito_id == cognito_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Parent | None:
        result = await self.session.execute(
            select(Parent).where(Parent.email == email)
        )
        return result.scalar_one_or_none()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
poetry run pytest tests/daos/test_parent_dao.py -v
```

Expected: `PASSED` (2 tests)

- [ ] **Step 5: Commit**

```bash
git add app/daos/parent_dao.py tests/daos/test_parent_dao.py
git commit -m "feat: add ParentDAO with create and get methods"
```

---

### Task 8: Cognito client

**Files:**
- Create: `app/clients/cognito.py`

The Cognito client wraps `boto3` calls. Tests for this client are integration-only (require real Cognito pool) — unit tests for `AuthService` in Task 9 will mock this client instead.

- [ ] **Step 1: Implement `app/clients/cognito.py`**

```python
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
            # Auto-confirm for now (dev pools may have auto-confirm enabled)
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
        except ClientError as e:
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
```

- [ ] **Step 2: Commit**

```bash
git add app/clients/cognito.py
git commit -m "feat: add CognitoClient (register, login, refresh, verify_token)"
```

---

### Task 9: Auth schemas + service + router

**Files:**
- Create: `app/schemas/auth.py`
- Create: `app/services/auth_service.py`
- Create: `app/api/deps.py`
- Create: `app/api/auth.py`
- Create: `tests/api/test_auth.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/api/test_auth.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

REGISTER_PAYLOAD = {"email": "parent@example.com", "password": "Pass123!", "pin": "1234"}


@pytest.mark.asyncio
async def test_register_returns_tokens(client):
    mock_cognito = MagicMock()
    mock_cognito.register = MagicMock(return_value="cognito-sub-abc")
    mock_cognito.login = MagicMock(return_value={
        "access_token": "fake-access",
        "refresh_token": "fake-refresh",
    })
    with patch("app.api.auth.get_cognito_client", return_value=mock_cognito):
        response = await client.post("/auth/register", json=REGISTER_PAYLOAD)
    assert response.status_code == 201
    body = response.json()
    assert body["access_token"] == "fake-access"
    assert body["refresh_token"] == "fake-refresh"
    assert body["token_type"] == "Bearer"


@pytest.mark.asyncio
async def test_register_rejects_invalid_pin(client):
    response = await client.post("/auth/register", json={
        **REGISTER_PAYLOAD, "pin": "12"
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_returns_tokens(client):
    mock_cognito = MagicMock()
    mock_cognito.login = MagicMock(return_value={
        "access_token": "fake-access",
        "refresh_token": "fake-refresh",
    })
    with patch("app.api.auth.get_cognito_client", return_value=mock_cognito):
        response = await client.post("/auth/login", json={
            "email": "parent@example.com", "password": "Pass123!"
        })
    assert response.status_code == 200
    assert response.json()["access_token"] == "fake-access"


@pytest.mark.asyncio
async def test_login_401_on_bad_credentials(client):
    from app.clients.cognito import CognitoAuthError
    mock_cognito = MagicMock()
    mock_cognito.login = MagicMock(side_effect=CognitoAuthError("bad"))
    with patch("app.api.auth.get_cognito_client", return_value=mock_cognito):
        response = await client.post("/auth/login", json={
            "email": "x@x.com", "password": "wrong"
        })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_returns_new_access_token(client):
    mock_cognito = MagicMock()
    mock_cognito.refresh = MagicMock(return_value={"access_token": "new-access"})
    with patch("app.api.auth.get_cognito_client", return_value=mock_cognito):
        response = await client.post("/auth/refresh", json={"refresh_token": "old-refresh"})
    assert response.status_code == 200
    assert response.json()["access_token"] == "new-access"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
poetry run pytest tests/api/test_auth.py -v
```

Expected: `ImportError` or `404` (routes not registered).

- [ ] **Step 3: Implement `app/schemas/auth.py`**

```python
from pydantic import BaseModel, field_validator


class RegisterRequest(BaseModel):
    email: str
    password: str
    pin: str

    @field_validator("pin")
    @classmethod
    def pin_must_be_4_digits(cls, v: str) -> str:
        if not v.isdigit() or len(v) != 4:
            raise ValueError("PIN must be exactly 4 digits")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "Bearer"
```

- [ ] **Step 4: Implement `app/services/auth_service.py`**

```python
import bcrypt
from app.clients.cognito import CognitoClient, CognitoConflictError, CognitoAuthError
from app.daos.parent_dao import ParentDAO
from fastapi import HTTPException


class AuthService:
    def __init__(self, cognito: CognitoClient, parent_dao: ParentDAO):
        self.cognito = cognito
        self.parent_dao = parent_dao

    async def register(self, email: str, password: str, pin: str) -> dict:
        existing = await self.parent_dao.get_by_email(email)
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")
        try:
            cognito_id = self.cognito.register(email, password)
        except CognitoConflictError:
            raise HTTPException(status_code=409, detail="Email already registered")

        pin_hash = bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()
        await self.parent_dao.create(cognito_id=cognito_id, email=email, pin_hash=pin_hash)

        tokens = self.cognito.login(email, password)
        return tokens

    def login(self, email: str, password: str) -> dict:
        try:
            return self.cognito.login(email, password)
        except CognitoAuthError:
            raise HTTPException(status_code=401, detail="Invalid credentials")

    def refresh(self, refresh_token: str) -> dict:
        try:
            return self.cognito.refresh(refresh_token)
        except CognitoAuthError:
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
```

- [ ] **Step 5: Implement `app/api/deps.py`**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.daos.parent_dao import ParentDAO
from app.clients.cognito import get_cognito_client, CognitoAuthError
from app.db.models import Parent

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
```

- [ ] **Step 6: Implement `app/api/auth.py`**

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.daos.parent_dao import ParentDAO
from app.clients.cognito import get_cognito_client
from app.services.auth_service import AuthService
from app.schemas.auth import RegisterRequest, LoginRequest, RefreshRequest, TokenResponse

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
```

- [ ] **Step 7: Register auth router in `app/main.py`**

```python
from fastapi import FastAPI
from app.api import health, auth

app = FastAPI(title="Smarty Steps")

app.include_router(health.router)
app.include_router(auth.router)
```

- [ ] **Step 8: Run tests to verify they pass**

```bash
poetry run pytest tests/api/test_auth.py -v
```

Expected: all 5 tests `PASSED`

- [ ] **Step 9: Run full test suite**

```bash
poetry run pytest -v
```

Expected: all tests pass, no warnings.

- [ ] **Step 10: Commit**

```bash
git add app/schemas/auth.py app/services/auth_service.py \
  app/api/deps.py app/api/auth.py app/main.py \
  tests/api/test_auth.py
git commit -m "feat: add auth register/login/refresh with Cognito integration"
```

---

### Task 10: Dockerfile + Docker Compose local

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`

- [ ] **Step 1: Create `Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN pip install poetry==1.8.3 && \
    poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-dev --no-interaction

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Create `docker-compose.yml` (local dev)**

```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - .:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  db:
    image: postgres:16
    environment:
      POSTGRES_USER: smarty
      POSTGRES_PASSWORD: smarty
      POSTGRES_DB: smarty_steps
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U smarty -d smarty_steps"]
      interval: 5s
      timeout: 5s
      retries: 5
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

- [ ] **Step 3: Build and smoke-test locally**

```bash
docker compose up --build -d
curl http://localhost:8000/health
```

Expected: `{"status":"ok"}`

- [ ] **Step 4: Commit**

```bash
git add Dockerfile docker-compose.yml
git commit -m "feat: add Dockerfile and docker-compose for local dev"
```

---

### Task 11: Docker Compose prod + GitHub Actions

**Files:**
- Create: `docker-compose.prod.yml`
- Create: `.github/workflows/ci.yml`
- Create: `.github/workflows/deploy-staging.yml`
- Create: `.github/workflows/deploy-prod.yml`

- [ ] **Step 1: Create `docker-compose.prod.yml`**

```yaml
services:
  api:
    image: ghcr.io/${GITHUB_REPOSITORY}:${IMAGE_TAG:-latest}
    ports:
      - "8000:8000"
    env_file: .env
    restart: unless-stopped
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```

Note: prod uses Amazon RDS — no `db` service. The `.env` on the EC2 instance points to RDS.

- [ ] **Step 2: Create `.github/workflows/ci.yml`**

No postgres service needed — testcontainers spins up its own Docker container during the test run. The CI runner just needs Docker available (ubuntu-latest has it).

```yaml
name: CI

on:
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install poetry && poetry install
      - name: Run tests
        env:
          DATABASE_URL: postgresql+asyncpg://unused:unused@localhost:5432/unused
          COGNITO_USER_POOL_ID: dummy
          COGNITO_CLIENT_ID: dummy
          COGNITO_REGION: us-east-1
          ANTHROPIC_API_KEY: dummy
          PARENT_JWT_SECRET: test-secret
        run: poetry run pytest -v
```

- [ ] **Step 3: Create `.github/workflows/deploy-staging.yml`**

```yaml
name: Deploy — Staging

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build and push Docker image
        run: |
          echo "${{ secrets.GITHUB_TOKEN }}" | docker login ghcr.io -u ${{ github.actor }} --password-stdin
          docker build -t ghcr.io/${{ github.repository }}:staging .
          docker push ghcr.io/${{ github.repository }}:staging
      - name: Deploy to staging EC2
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.EC2_STAGING_HOST }}
          username: ec2-user
          key: ${{ secrets.EC2_SSH_KEY }}
          script: |
            echo "${{ secrets.GITHUB_TOKEN }}" | docker login ghcr.io -u ${{ github.actor }} --password-stdin
            cd /opt/smarty-steps
            IMAGE_TAG=staging docker compose -f docker-compose.prod.yml pull
            IMAGE_TAG=staging docker compose -f docker-compose.prod.yml up -d
```

- [ ] **Step 4: Create `.github/workflows/deploy-prod.yml`**

```yaml
name: Deploy — Production

on:
  workflow_dispatch:
    inputs:
      image_tag:
        description: "Image tag to deploy (default: staging)"
        required: false
        default: staging

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to prod EC2
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.EC2_PROD_HOST }}
          username: ec2-user
          key: ${{ secrets.EC2_SSH_KEY }}
          script: |
            echo "${{ secrets.GITHUB_TOKEN }}" | docker login ghcr.io -u ${{ github.actor }} --password-stdin
            cd /opt/smarty-steps
            IMAGE_TAG=${{ github.event.inputs.image_tag }} docker compose -f docker-compose.prod.yml pull
            IMAGE_TAG=${{ github.event.inputs.image_tag }} docker compose -f docker-compose.prod.yml up -d
```

- [ ] **Step 5: Set GitHub secrets**

In GitHub → Settings → Secrets → Actions, add:
- `EC2_STAGING_HOST` — public IP or DNS of staging EC2
- `EC2_PROD_HOST` — public IP or DNS of prod EC2
- `EC2_SSH_KEY` — private SSH key (PEM content) for both instances

- [ ] **Step 6: On each EC2 instance, create `/opt/smarty-steps/.env`**

SSH into each instance and run:

```bash
sudo mkdir -p /opt/smarty-steps
sudo tee /opt/smarty-steps/.env <<EOF
DATABASE_URL=postgresql+asyncpg://<rds-user>:<rds-pass>@<rds-host>:5432/smarty_steps
COGNITO_USER_POOL_ID=<pool-id>
COGNITO_CLIENT_ID=<client-id>
COGNITO_REGION=us-east-1
ANTHROPIC_API_KEY=<key>
PARENT_JWT_SECRET=<secret>
PARENT_JWT_EXPIRE_MINUTES=15
EOF
```

Also copy `docker-compose.prod.yml` to `/opt/smarty-steps/docker-compose.prod.yml` on each instance.

- [ ] **Step 7: Commit and push**

```bash
git add docker-compose.prod.yml .github/
git commit -m "feat: add prod Docker Compose and GitHub Actions CI/CD"
git push origin main
```

Expected: CI workflow runs tests on the PR/push, staging deploy fires on push to main.

---

## Phase 1 Done

At end of Phase 1 you have:

- Full project structure with 3-layer architecture
- All 7 DB tables + indexes via Alembic migration (`pg_uuidv7` enabled)
- `GET /health` → 200 OK
- `POST /auth/register` → creates Cognito user + parent row → returns tokens
- `POST /auth/login` → Cognito auth → tokens
- `POST /auth/refresh` → new access token
- JWT middleware in `deps.py` (`get_current_parent`) ready for all future routes
- `docker-compose.yml` for local dev
- `docker-compose.prod.yml` for EC2
- GitHub Actions: CI on PRs, auto-deploy to staging on `main`, manual deploy to prod

**Next:** Phase 2 — Learners & Profiles (`docs/superpowers/plans/2026-04-27-phase2-learners.md`)
