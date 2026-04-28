# Smarty Steps Backend — Phase 2: Learners & Profiles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Parents can create and manage learner profiles (CRUD), and verify their 4-digit PIN to obtain a short-lived parent-dashboard JWT.

**Architecture:** 3-layer. `LearnerService` owns all ownership checks and age/grade validation. `ParentService` does bcrypt PIN verification and python-jose JWT issuance. `LearnerDAO` and `ParentDAO` (extended) are the sole DB interfaces. `get_current_parent_dashboard` dep added to `deps.py` for Phase 5 parent-dashboard routes.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async, bcrypt, python-jose, pytest-asyncio, unittest.mock

---

## File Structure

```
app/
  daos/
    parent_dao.py            — Modify: add get_by_id method
    learner_dao.py           — Create: create, get_by_parent, get_by_id, update, update_stats
  services/
    learner_service.py       — Create: create, list_for_parent, get (ownership), update
    parent_service.py        — Create: verify_pin_and_issue_token
  schemas/
    learner.py               — Create: CreateLearnerRequest, UpdateLearnerRequest, LearnerResponse, LearnerListResponse
    parent.py                — Create: VerifyPinRequest, ParentTokenResponse
  api/
    deps.py                  — Modify: add get_current_parent_dashboard
    learners.py              — Create: POST /learners, GET /learners, GET /learners/{id}, PATCH /learners/{id}
    parent.py                — Create: POST /parent/verify-pin
  main.py                    — Modify: register learners + parent routers
tests/
  conftest.py                — Modify: add authed_client fixture
  daos/
    test_parent_dao.py       — Modify: add test_get_by_id
    test_learner_dao.py      — Create
  services/
    test_learner_service.py  — Create
    test_parent_service.py   — Create
  api/
    test_learners.py         — Create
    test_parent.py           — Create
```

---

### Task 1: Learner + Parent schemas

**Files:**
- Create: `app/schemas/learner.py`
- Create: `app/schemas/parent.py`

No tests needed — pure Pydantic; validator logic is covered implicitly by API integration tests in Task 7.

- [ ] **Step 1: Write `app/schemas/learner.py`**

```python
from __future__ import annotations
from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel, field_validator


class CreateLearnerRequest(BaseModel):
    name: str
    age: int
    grade_level: int
    avatar_emoji: str = "🚀"

    @field_validator("age")
    @classmethod
    def age_in_range(cls, v: int) -> int:
        if not 5 <= v <= 8:
            raise ValueError("Age must be between 5 and 8")
        return v

    @field_validator("grade_level")
    @classmethod
    def grade_in_range(cls, v: int) -> int:
        if not 0 <= v <= 3:
            raise ValueError("Grade level must be between 0 and 3")
        return v


class UpdateLearnerRequest(BaseModel):
    name: Optional[str] = None
    avatar_emoji: Optional[str] = None
    grade_level: Optional[int] = None

    @field_validator("grade_level")
    @classmethod
    def grade_in_range(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not 0 <= v <= 3:
            raise ValueError("Grade level must be between 0 and 3")
        return v


class LearnerResponse(BaseModel):
    id: UUID
    name: str
    age: int
    grade_level: int
    avatar_emoji: str
    total_stars: int
    level: int
    xp: int
    streak_days: int
    last_active_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class LearnerListResponse(BaseModel):
    learners: list[LearnerResponse]
```

- [ ] **Step 2: Write `app/schemas/parent.py`**

```python
from pydantic import BaseModel, field_validator


class VerifyPinRequest(BaseModel):
    pin: str

    @field_validator("pin")
    @classmethod
    def pin_must_be_4_digits(cls, v: str) -> str:
        if not v.isdigit() or len(v) != 4:
            raise ValueError("PIN must be exactly 4 digits")
        return v


class ParentTokenResponse(BaseModel):
    token: str
```

- [ ] **Step 3: Commit**

```bash
git add app/schemas/learner.py app/schemas/parent.py
git commit -m "feat: add learner and parent Pydantic schemas"
```

---

### Task 2: Extend ParentDAO with get_by_id

**Files:**
- Modify: `app/daos/parent_dao.py`
- Modify: `tests/daos/test_parent_dao.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/daos/test_parent_dao.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/daos/test_parent_dao.py::test_get_by_id_returns_parent -v
```

Expected: `AttributeError: 'ParentDAO' object has no attribute 'get_by_id'`

- [ ] **Step 3: Add `get_by_id` to `app/daos/parent_dao.py`**

```python
from uuid import UUID
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

    async def get_by_id(self, parent_id: UUID) -> Parent | None:
        result = await self.session.execute(
            select(Parent).where(Parent.id == parent_id)
        )
        return result.scalar_one_or_none()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/daos/test_parent_dao.py -v
```

Expected: all tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add app/daos/parent_dao.py tests/daos/test_parent_dao.py
git commit -m "feat: add ParentDAO.get_by_id"
```

---

### Task 3: LearnerDAO + tests

**Files:**
- Create: `app/daos/learner_dao.py`
- Create: `tests/daos/test_learner_dao.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/daos/test_learner_dao.py`:

```python
import pytest
from uuid_extensions import uuid7
from app.daos.learner_dao import LearnerDAO
from app.daos.parent_dao import ParentDAO


async def _make_parent(db_session, suffix=""):
    return await ParentDAO(db_session).create(
        cognito_id=f"cog-learner-{uuid7()}{suffix}",
        email=f"parent-{uuid7()}@test.com",
        pin_hash="$2b$12$hash",
    )


@pytest.mark.asyncio
async def test_create_and_get_by_parent(db_session):
    parent = await _make_parent(db_session)
    dao = LearnerDAO(db_session)
    learner = await dao.create(
        parent_id=parent.id,
        name="Emma",
        age=6,
        grade_level=1,
        avatar_emoji="🦋",
    )
    assert learner.id is not None
    assert learner.name == "Emma"
    assert learner.total_stars == 0
    assert learner.level == 1
    assert learner.xp == 0

    learners = await dao.get_by_parent(parent.id)
    assert len(learners) == 1
    assert learners[0].id == learner.id


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_missing(db_session):
    dao = LearnerDAO(db_session)
    result = await dao.get_by_id(uuid7())
    assert result is None


@pytest.mark.asyncio
async def test_get_by_parent_returns_empty_list(db_session):
    dao = LearnerDAO(db_session)
    result = await dao.get_by_parent(uuid7())
    assert result == []


@pytest.mark.asyncio
async def test_update_learner_fields(db_session):
    parent = await _make_parent(db_session, "-upd")
    dao = LearnerDAO(db_session)
    learner = await dao.create(
        parent_id=parent.id,
        name="Jake",
        age=7,
        grade_level=2,
        avatar_emoji="🚀",
    )
    updated = await dao.update(learner, name="Jake Updated", avatar_emoji="🌟", grade_level=3)
    assert updated.name == "Jake Updated"
    assert updated.avatar_emoji == "🌟"
    assert updated.grade_level == 3
    assert updated.age == 7  # unchanged
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/daos/test_learner_dao.py -v
```

Expected: `ImportError: cannot import name 'LearnerDAO'`

- [ ] **Step 3: Implement `app/daos/learner_dao.py`**

```python
from uuid import UUID
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Learner


class LearnerDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        parent_id: UUID,
        name: str,
        age: int,
        grade_level: int,
        avatar_emoji: str,
    ) -> Learner:
        learner = Learner(
            parent_id=parent_id,
            name=name,
            age=age,
            grade_level=grade_level,
            avatar_emoji=avatar_emoji,
        )
        self.session.add(learner)
        await self.session.flush()
        await self.session.refresh(learner)
        return learner

    async def get_by_parent(self, parent_id: UUID) -> list[Learner]:
        result = await self.session.execute(
            select(Learner).where(Learner.parent_id == parent_id)
        )
        return list(result.scalars().all())

    async def get_by_id(self, learner_id: UUID) -> Optional[Learner]:
        result = await self.session.execute(
            select(Learner).where(Learner.id == learner_id)
        )
        return result.scalar_one_or_none()

    async def update(
        self,
        learner: Learner,
        name: Optional[str] = None,
        avatar_emoji: Optional[str] = None,
        grade_level: Optional[int] = None,
    ) -> Learner:
        if name is not None:
            learner.name = name
        if avatar_emoji is not None:
            learner.avatar_emoji = avatar_emoji
        if grade_level is not None:
            learner.grade_level = grade_level
        await self.session.flush()
        await self.session.refresh(learner)
        return learner

    async def update_stats(
        self,
        learner: Learner,
        star_delta: int,
        xp_delta: int,
        new_streak: int,
        new_last_active_at,
    ) -> Learner:
        learner.total_stars = (learner.total_stars or 0) + star_delta
        learner.xp = (learner.xp or 0) + xp_delta
        learner.level = (learner.xp // 100) + 1
        learner.streak_days = new_streak
        learner.last_active_at = new_last_active_at
        await self.session.flush()
        await self.session.refresh(learner)
        return learner
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/daos/test_learner_dao.py -v
```

Expected: all 4 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add app/daos/learner_dao.py tests/daos/test_learner_dao.py
git commit -m "feat: add LearnerDAO with CRUD and update_stats"
```

---

### Task 4: LearnerService + tests

**Files:**
- Create: `app/services/learner_service.py`
- Create: `tests/services/test_learner_service.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/services/test_learner_service.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from fastapi import HTTPException
from app.services.learner_service import LearnerService
from app.db.models import Learner, Parent


def _parent(pid=None):
    p = MagicMock(spec=Parent)
    p.id = pid or uuid4()
    return p


def _learner(lid=None, parent_id=None):
    l = MagicMock(spec=Learner)
    l.id = lid or uuid4()
    l.parent_id = parent_id or uuid4()
    return l


@pytest.mark.asyncio
async def test_get_raises_404_when_not_found():
    dao = MagicMock()
    dao.get_by_id = AsyncMock(return_value=None)
    svc = LearnerService(dao)
    with pytest.raises(HTTPException) as exc:
        await svc.get(_parent(), uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_raises_403_when_wrong_parent():
    parent = _parent()
    learner = _learner(parent_id=uuid4())  # different parent
    dao = MagicMock()
    dao.get_by_id = AsyncMock(return_value=learner)
    svc = LearnerService(dao)
    with pytest.raises(HTTPException) as exc:
        await svc.get(parent, learner.id)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_get_returns_learner_when_owned():
    parent = _parent()
    learner = _learner(parent_id=parent.id)
    dao = MagicMock()
    dao.get_by_id = AsyncMock(return_value=learner)
    svc = LearnerService(dao)
    result = await svc.get(parent, learner.id)
    assert result is learner


@pytest.mark.asyncio
async def test_list_delegates_to_dao():
    parent = _parent()
    learners = [_learner(parent_id=parent.id)]
    dao = MagicMock()
    dao.get_by_parent = AsyncMock(return_value=learners)
    svc = LearnerService(dao)
    result = await svc.list_for_parent(parent)
    assert result is learners
    dao.get_by_parent.assert_awaited_once_with(parent.id)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/services/test_learner_service.py -v
```

Expected: `ImportError: cannot import name 'LearnerService'`

- [ ] **Step 3: Implement `app/services/learner_service.py`**

```python
from uuid import UUID
from typing import Optional
from fastapi import HTTPException
from app.daos.learner_dao import LearnerDAO
from app.db.models import Learner, Parent


class LearnerService:
    def __init__(self, learner_dao: LearnerDAO):
        self.dao = learner_dao

    async def create(
        self,
        parent: Parent,
        name: str,
        age: int,
        grade_level: int,
        avatar_emoji: str,
    ) -> Learner:
        return await self.dao.create(
            parent_id=parent.id,
            name=name,
            age=age,
            grade_level=grade_level,
            avatar_emoji=avatar_emoji,
        )

    async def list_for_parent(self, parent: Parent) -> list[Learner]:
        return await self.dao.get_by_parent(parent.id)

    async def get(self, parent: Parent, learner_id: UUID) -> Learner:
        learner = await self.dao.get_by_id(learner_id)
        if learner is None:
            raise HTTPException(status_code=404, detail="Learner not found")
        if learner.parent_id != parent.id:
            raise HTTPException(status_code=403, detail="Learner not owned by parent")
        return learner

    async def update(
        self,
        parent: Parent,
        learner_id: UUID,
        name: Optional[str],
        avatar_emoji: Optional[str],
        grade_level: Optional[int],
    ) -> Learner:
        learner = await self.get(parent, learner_id)
        return await self.dao.update(
            learner,
            name=name,
            avatar_emoji=avatar_emoji,
            grade_level=grade_level,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/services/test_learner_service.py -v
```

Expected: all 4 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add app/services/learner_service.py tests/services/test_learner_service.py
git commit -m "feat: add LearnerService with ownership checks"
```

---

### Task 5: ParentService + tests

**Files:**
- Create: `app/services/parent_service.py`
- Create: `tests/services/test_parent_service.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/services/test_parent_service.py`:

```python
import pytest
import bcrypt
from unittest.mock import MagicMock
from fastapi import HTTPException
from jose import jwt
from app.services.parent_service import ParentService
from app.db.models import Parent
from app.core.config import settings


def _parent_with_pin(pin: str = "1234"):
    p = MagicMock(spec=Parent)
    p.pin_hash = bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()
    return p


def test_correct_pin_returns_jwt():
    parent = _parent_with_pin("1234")
    svc = ParentService()
    token = svc.verify_pin_and_issue_token(parent, "1234")
    claims = jwt.decode(token, settings.parent_jwt_secret, algorithms=["HS256"])
    assert claims["scope"] == "parent_dashboard"


def test_wrong_pin_raises_401():
    parent = _parent_with_pin("1234")
    svc = ParentService()
    with pytest.raises(HTTPException) as exc:
        svc.verify_pin_and_issue_token(parent, "9999")
    assert exc.value.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/services/test_parent_service.py -v
```

Expected: `ImportError: cannot import name 'ParentService'`

- [ ] **Step 3: Implement `app/services/parent_service.py`**

```python
import bcrypt
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from jose import jwt
from app.core.config import settings
from app.db.models import Parent


class ParentService:
    def verify_pin_and_issue_token(self, parent: Parent, pin: str) -> str:
        is_valid = bcrypt.checkpw(pin.encode(), parent.pin_hash.encode())
        if not is_valid:
            raise HTTPException(status_code=401, detail="Incorrect PIN")
        payload = {
            "sub": str(parent.id),
            "scope": "parent_dashboard",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.parent_jwt_expire_minutes),
        }
        return jwt.encode(payload, settings.parent_jwt_secret, algorithm="HS256")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/services/test_parent_service.py -v
```

Expected: all 2 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add app/services/parent_service.py tests/services/test_parent_service.py
git commit -m "feat: add ParentService for PIN verification and dashboard JWT"
```

---

### Task 6: Update deps.py + conftest.py

**Files:**
- Modify: `app/api/deps.py`
- Modify: `tests/conftest.py`

`deps.py` is created in Phase 1 Task 9. This task adds the `get_current_parent_dashboard` dependency and updates `conftest.py` with a reusable `authed_client` fixture.

- [ ] **Step 1: Add `get_current_parent_dashboard` to `app/api/deps.py`**

The full file after modification (keep existing `get_current_parent` intact, add the new dependency below it):

```python
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError
from app.db.session import get_db
from app.daos.parent_dao import ParentDAO
from app.clients.cognito import get_cognito_client, CognitoAuthError
from app.core.config import settings
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


async def get_current_parent_dashboard(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Parent:
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.parent_jwt_secret,
            algorithms=["HS256"],
        )
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    if payload.get("scope") != "parent_dashboard":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token scope")
    parent_id = payload.get("sub")
    parent = await ParentDAO(db).get_by_id(UUID(parent_id))
    if not parent:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Parent not found")
    return parent
```

- [ ] **Step 2: Add `authed_client` fixture to `tests/conftest.py`**

Append to the existing `tests/conftest.py` (keep all existing fixtures, add at the bottom):

```python
import bcrypt
from app.api import deps
from app.daos.parent_dao import ParentDAO


@pytest_asyncio.fixture
async def authed_client(client, db_session):
    """HTTP client with get_current_parent overridden to return a real parent from the test DB."""
    parent = await ParentDAO(db_session).create(
        cognito_id="test-cognito-id",
        email="testparent@example.com",
        pin_hash=bcrypt.hashpw(b"1234", bcrypt.gensalt()).decode(),
    )
    app.dependency_overrides[deps.get_current_parent] = lambda: parent
    yield client, parent
    # app.dependency_overrides.clear() is called by the client fixture teardown
```

- [ ] **Step 3: Commit**

```bash
git add app/api/deps.py tests/conftest.py
git commit -m "feat: add get_current_parent_dashboard dep and authed_client test fixture"
```

---

### Task 7: Learners API + integration tests

**Files:**
- Create: `app/api/learners.py`
- Create: `tests/api/test_learners.py`
- Modify: `app/main.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/api/test_learners.py`:

```python
import pytest


@pytest.mark.asyncio
async def test_create_learner_returns_201(authed_client):
    client, parent = authed_client
    response = await client.post("/learners", json={
        "name": "Emma",
        "age": 6,
        "grade_level": 1,
        "avatar_emoji": "🦋",
    })
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Emma"
    assert body["age"] == 6
    assert body["grade_level"] == 1
    assert body["total_stars"] == 0
    assert body["level"] == 1
    assert "id" in body


@pytest.mark.asyncio
async def test_create_learner_rejects_age_out_of_range(authed_client):
    client, _ = authed_client
    response = await client.post("/learners", json={
        "name": "Emma", "age": 10, "grade_level": 1
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_learner_rejects_grade_out_of_range(authed_client):
    client, _ = authed_client
    response = await client.post("/learners", json={
        "name": "Emma", "age": 6, "grade_level": 5
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_learners(authed_client):
    client, _ = authed_client
    await client.post("/learners", json={"name": "A", "age": 5, "grade_level": 0})
    await client.post("/learners", json={"name": "B", "age": 8, "grade_level": 3})
    response = await client.get("/learners")
    assert response.status_code == 200
    assert len(response.json()["learners"]) >= 2


@pytest.mark.asyncio
async def test_get_learner_by_id(authed_client):
    client, _ = authed_client
    create_resp = await client.post("/learners", json={"name": "C", "age": 7, "grade_level": 2})
    learner_id = create_resp.json()["id"]
    response = await client.get(f"/learners/{learner_id}")
    assert response.status_code == 200
    assert response.json()["id"] == learner_id


@pytest.mark.asyncio
async def test_get_learner_returns_404_for_nonexistent(authed_client):
    from uuid_extensions import uuid7
    client, _ = authed_client
    response = await client.get(f"/learners/{uuid7()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_patch_learner(authed_client):
    client, _ = authed_client
    create_resp = await client.post("/learners", json={"name": "D", "age": 6, "grade_level": 1})
    learner_id = create_resp.json()["id"]
    response = await client.patch(f"/learners/{learner_id}", json={"name": "D Updated"})
    assert response.status_code == 200
    assert response.json()["name"] == "D Updated"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/api/test_learners.py -v
```

Expected: `404 Not Found` (routes not registered yet)

- [ ] **Step 3: Implement `app/api/learners.py`**

```python
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.daos.learner_dao import LearnerDAO
from app.services.learner_service import LearnerService
from app.schemas.learner import (
    CreateLearnerRequest, UpdateLearnerRequest,
    LearnerResponse, LearnerListResponse,
)
from app.api.deps import get_current_parent
from app.db.models import Parent

router = APIRouter(prefix="/learners", tags=["learners"])


def _svc(db: AsyncSession = Depends(get_db)) -> LearnerService:
    return LearnerService(LearnerDAO(db))


@router.post("", response_model=LearnerResponse, status_code=status.HTTP_201_CREATED)
async def create_learner(
    body: CreateLearnerRequest,
    parent: Parent = Depends(get_current_parent),
    svc: LearnerService = Depends(_svc),
):
    learner = await svc.create(
        parent=parent,
        name=body.name,
        age=body.age,
        grade_level=body.grade_level,
        avatar_emoji=body.avatar_emoji,
    )
    return LearnerResponse.model_validate(learner)


@router.get("", response_model=LearnerListResponse)
async def list_learners(
    parent: Parent = Depends(get_current_parent),
    svc: LearnerService = Depends(_svc),
):
    learners = await svc.list_for_parent(parent)
    return LearnerListResponse(learners=[LearnerResponse.model_validate(l) for l in learners])


@router.get("/{learner_id}", response_model=LearnerResponse)
async def get_learner(
    learner_id: UUID,
    parent: Parent = Depends(get_current_parent),
    svc: LearnerService = Depends(_svc),
):
    learner = await svc.get(parent, learner_id)
    return LearnerResponse.model_validate(learner)


@router.patch("/{learner_id}", response_model=LearnerResponse)
async def update_learner(
    learner_id: UUID,
    body: UpdateLearnerRequest,
    parent: Parent = Depends(get_current_parent),
    svc: LearnerService = Depends(_svc),
):
    learner = await svc.update(
        parent=parent,
        learner_id=learner_id,
        name=body.name,
        avatar_emoji=body.avatar_emoji,
        grade_level=body.grade_level,
    )
    return LearnerResponse.model_validate(learner)
```

- [ ] **Step 4: Register router in `app/main.py`**

```python
from fastapi import FastAPI
from app.api import health, auth, learners

app = FastAPI(title="Smarty Steps")

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(learners.router)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/api/test_learners.py -v
```

Expected: all 7 tests `PASSED`

- [ ] **Step 6: Commit**

```bash
git add app/api/learners.py app/main.py tests/api/test_learners.py
git commit -m "feat: add learner CRUD endpoints"
```

---

### Task 8: Parent verify-pin API + integration tests

**Files:**
- Create: `app/api/parent.py`
- Create: `tests/api/test_parent.py`
- Modify: `app/main.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/api/test_parent.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/api/test_parent.py -v
```

Expected: `404 Not Found` (route not registered)

- [ ] **Step 3: Implement `app/api/parent.py`**

```python
from fastapi import APIRouter, Depends
from app.api.deps import get_current_parent
from app.services.parent_service import ParentService
from app.schemas.parent import VerifyPinRequest, ParentTokenResponse
from app.db.models import Parent

router = APIRouter(prefix="/parent", tags=["parent"])


@router.post("/verify-pin", response_model=ParentTokenResponse)
async def verify_pin(
    body: VerifyPinRequest,
    parent: Parent = Depends(get_current_parent),
):
    token = ParentService().verify_pin_and_issue_token(parent, body.pin)
    return ParentTokenResponse(token=token)
```

- [ ] **Step 4: Register parent router in `app/main.py`**

```python
from fastapi import FastAPI
from app.api import health, auth, learners, parent

app = FastAPI(title="Smarty Steps")

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(learners.router)
app.include_router(parent.router)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/api/test_parent.py -v
```

Expected: all 3 tests `PASSED`

- [ ] **Step 6: Run full test suite**

```bash
uv run pytest -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add app/api/parent.py app/main.py tests/api/test_parent.py
git commit -m "feat: add parent verify-pin endpoint"
```

---

## Phase 2 Done

At end of Phase 2 you have:

- `GET /learners` — list parent's learners
- `POST /learners` — create with age 5–8 / grade 0–3 validation
- `GET /learners/{id}` — 404 if missing, 403 if wrong parent
- `PATCH /learners/{id}` — partial update, same ownership check
- `POST /parent/verify-pin` — bcrypt PIN check → 15-min dashboard JWT
- `LearnerDAO.update_stats` ready for Phase 4 progress submission
- `get_current_parent_dashboard` dep ready for Phase 5 routes

**Next:** Phase 3 — Standards Sync & Content Generation (`docs/superpowers/plans/2026-04-28-phase3-content.md`)
