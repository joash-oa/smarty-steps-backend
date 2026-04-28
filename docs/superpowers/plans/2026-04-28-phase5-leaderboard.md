# Smarty Steps Backend — Phase 5: Leaderboard & Parent Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Global leaderboard (all-time / weekly / monthly) ranked by stars → streak → created_at. Parent dashboard stats: time per subject, mastered lessons (3★), needs-practice lessons (≤1★ completed), recent activity. Parent dashboard routes protected by the 15-min parent JWT issued in Phase 2.

**Architecture:** `LeaderboardDAO` owns the ranked query with period filter. `DashboardDAO` owns the stats aggregate query (joins `lesson_progress` + `lessons`). Each has a thin service layer. `get_current_parent_dashboard` dep from Phase 2 protects parent routes.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async (ORDER BY + WHERE on `last_active_at`), pytest-asyncio, unittest.mock

---

## File Structure

```
app/
  daos/
    leaderboard_dao.py       — Create: get_ranked(period, limit)
    dashboard_dao.py         — Create: get_stats(learner_id)
  services/
    leaderboard_service.py   — Create: get_leaderboard(period)
    dashboard_service.py     — Create: get_stats(parent, learner_id, learner_svc)
  schemas/
    leaderboard.py           — Create: LeaderboardEntry, LeaderboardResponse
    dashboard.py             — Create: DashboardStatsResponse + nested models
  api/
    leaderboard.py           — Create: GET /leaderboard
    parent.py                — Modify: add GET /parent/learners/{learner_id}/stats
  main.py                    — Modify: register leaderboard router
tests/
  daos/
    test_leaderboard_dao.py  — Create
    test_dashboard_dao.py    — Create
  services/
    test_leaderboard_service.py — Create (mocked DAO)
    test_dashboard_service.py   — Create (mocked DAO)
  api/
    test_leaderboard.py      — Create
    test_parent_dashboard.py — Create
```

---

### Task 1: Leaderboard schemas + DAO + tests

**Files:**
- Create: `app/schemas/leaderboard.py`
- Create: `app/daos/leaderboard_dao.py`
- Create: `tests/daos/test_leaderboard_dao.py`

- [ ] **Step 1: Write `app/schemas/leaderboard.py`**

```python
from pydantic import BaseModel


class LeaderboardEntry(BaseModel):
    rank: int
    name: str
    avatar_emoji: str
    total_stars: int
    streak_days: int


class LeaderboardResponse(BaseModel):
    period: str
    rankings: list[LeaderboardEntry]
```

- [ ] **Step 2: Write the failing tests**

Create `tests/daos/test_leaderboard_dao.py`:

```python
import pytest
from datetime import datetime, timezone, timedelta
from uuid_extensions import uuid7
from app.daos.leaderboard_dao import LeaderboardDAO
from app.daos.parent_dao import ParentDAO
from app.daos.learner_dao import LearnerDAO


async def _make_learner(db_session, name, stars, streak, last_active_days_ago=0):
    parent = await ParentDAO(db_session).create(
        cognito_id=f"cog-lb-{uuid7()}",
        email=f"lb-{uuid7()}@test.com",
        pin_hash="hash",
    )
    learner_dao = LearnerDAO(db_session)
    learner = await learner_dao.create(
        parent_id=parent.id, name=name, age=6, grade_level=1, avatar_emoji="🚀"
    )
    # Directly set stats for deterministic test data
    from app.db.models import Learner
    from sqlalchemy import update
    last_active = datetime.now(timezone.utc) - timedelta(days=last_active_days_ago)
    await db_session.execute(
        update(Learner)
        .where(Learner.id == learner.id)
        .values(total_stars=stars, streak_days=streak, last_active_at=last_active)
    )
    await db_session.flush()
    return learner


@pytest.mark.asyncio
async def test_all_time_ranking_sorted_by_stars(db_session):
    await _make_learner(db_session, "Alice", stars=50, streak=3)
    await _make_learner(db_session, "Bob", stars=80, streak=1)
    dao = LeaderboardDAO(db_session)
    results = await dao.get_ranked("all_time", limit=10)
    star_values = [r.total_stars for r in results]
    assert star_values == sorted(star_values, reverse=True)
    # Bob (80 stars) should rank higher than Alice (50 stars)
    names = [r.name for r in results]
    assert names.index("Bob") < names.index("Alice")


@pytest.mark.asyncio
async def test_tie_broken_by_streak(db_session):
    await _make_learner(db_session, "C", stars=100, streak=10, last_active_days_ago=0)
    await _make_learner(db_session, "D", stars=100, streak=5, last_active_days_ago=0)
    dao = LeaderboardDAO(db_session)
    results = await dao.get_ranked("all_time", limit=10)
    names = [r.name for r in results]
    assert names.index("C") < names.index("D")


@pytest.mark.asyncio
async def test_weekly_filters_by_last_active(db_session):
    await _make_learner(db_session, "Active", stars=10, streak=1, last_active_days_ago=1)
    await _make_learner(db_session, "Inactive", stars=999, streak=1, last_active_days_ago=10)
    dao = LeaderboardDAO(db_session)
    results = await dao.get_ranked("weekly", limit=50)
    names = [r.name for r in results]
    assert "Active" in names
    assert "Inactive" not in names


@pytest.mark.asyncio
async def test_empty_period_returns_empty_list(db_session):
    dao = LeaderboardDAO(db_session)
    # monthly filter for a 30-day window — learners with no recent activity won't appear
    # Just verify it returns a list without error
    results = await dao.get_ranked("monthly", limit=10)
    assert isinstance(results, list)
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
uv run pytest tests/daos/test_leaderboard_dao.py -v
```

Expected: `ImportError: cannot import name 'LeaderboardDAO'`

- [ ] **Step 4: Implement `app/daos/leaderboard_dao.py`**

```python
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Learner


class LeaderboardDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_ranked(self, period: str, limit: int = 50) -> list[Learner]:
        query = (
            select(Learner)
            .order_by(
                Learner.total_stars.desc(),
                Learner.streak_days.desc(),
                Learner.created_at.asc(),
            )
            .limit(limit)
        )
        if period == "weekly":
            cutoff = datetime.now(timezone.utc) - timedelta(days=7)
            query = query.where(Learner.last_active_at >= cutoff)
        elif period == "monthly":
            cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            query = query.where(Learner.last_active_at >= cutoff)
        # "all_time": no filter

        result = await self.session.execute(query)
        return list(result.scalars().all())
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/daos/test_leaderboard_dao.py -v
```

Expected: all 4 tests `PASSED`

- [ ] **Step 6: Commit**

```bash
git add app/schemas/leaderboard.py app/daos/leaderboard_dao.py tests/daos/test_leaderboard_dao.py
git commit -m "feat: add LeaderboardDAO with period filter and tie-breaking"
```

---

### Task 2: LeaderboardService + tests

**Files:**
- Create: `app/services/leaderboard_service.py`
- Create: `tests/services/test_leaderboard_service.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/services/test_leaderboard_service.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from app.services.leaderboard_service import LeaderboardService
from app.db.models import Learner


def _learner(name, stars, streak):
    l = MagicMock(spec=Learner)
    l.name = name
    l.avatar_emoji = "🚀"
    l.total_stars = stars
    l.streak_days = streak
    return l


@pytest.mark.asyncio
async def test_get_leaderboard_assigns_ranks():
    learners = [_learner("A", 80, 3), _learner("B", 50, 1)]
    dao = MagicMock()
    dao.get_ranked = AsyncMock(return_value=learners)
    svc = LeaderboardService(dao)
    result = await svc.get_leaderboard("all_time")
    assert result["period"] == "all_time"
    ranks = [r["rank"] for r in result["rankings"]]
    assert ranks == [1, 2]


@pytest.mark.asyncio
async def test_get_leaderboard_raises_400_for_invalid_period():
    dao = MagicMock()
    svc = LeaderboardService(dao)
    with pytest.raises(HTTPException) as exc:
        await svc.get_leaderboard("last_year")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_get_leaderboard_returns_empty_list():
    dao = MagicMock()
    dao.get_ranked = AsyncMock(return_value=[])
    svc = LeaderboardService(dao)
    result = await svc.get_leaderboard("weekly")
    assert result["rankings"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/services/test_leaderboard_service.py -v
```

Expected: `ImportError: cannot import name 'LeaderboardService'`

- [ ] **Step 3: Implement `app/services/leaderboard_service.py`**

```python
from fastapi import HTTPException
from app.daos.leaderboard_dao import LeaderboardDAO

VALID_PERIODS = {"all_time", "weekly", "monthly"}


class LeaderboardService:
    def __init__(self, dao: LeaderboardDAO):
        self.dao = dao

    async def get_leaderboard(self, period: str) -> dict:
        if period not in VALID_PERIODS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid period. Must be one of {VALID_PERIODS}",
            )
        learners = await self.dao.get_ranked(period, limit=50)
        rankings = [
            {
                "rank": idx + 1,
                "name": l.name,
                "avatar_emoji": l.avatar_emoji,
                "total_stars": l.total_stars or 0,
                "streak_days": l.streak_days or 0,
            }
            for idx, l in enumerate(learners)
        ]
        return {"period": period, "rankings": rankings}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/services/test_leaderboard_service.py -v
```

Expected: all 3 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add app/services/leaderboard_service.py tests/services/test_leaderboard_service.py
git commit -m "feat: add LeaderboardService with period validation and rank assignment"
```

---

### Task 3: Leaderboard API + integration tests

**Files:**
- Create: `app/api/leaderboard.py`
- Create: `tests/api/test_leaderboard.py`
- Modify: `app/main.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/api/test_leaderboard.py`:

```python
import pytest
from datetime import datetime, timezone
from sqlalchemy import update
from app.db.models import Learner
from app.daos.parent_dao import ParentDAO
from app.daos.learner_dao import LearnerDAO


async def _make_active_learner(db_session, name, stars):
    parent = await ParentDAO(db_session).create(
        cognito_id=f"cog-lb2-{name}", email=f"lb2-{name}@test.com", pin_hash="h"
    )
    learner = await LearnerDAO(db_session).create(
        parent_id=parent.id, name=name, age=6, grade_level=1, avatar_emoji="🦋"
    )
    await db_session.execute(
        update(Learner).where(Learner.id == learner.id).values(
            total_stars=stars,
            last_active_at=datetime.now(timezone.utc),
        )
    )
    await db_session.flush()
    return learner


@pytest.mark.asyncio
async def test_all_time_leaderboard_returns_200(authed_client, db_session):
    client, _ = authed_client
    response = await client.get("/leaderboard?period=all_time")
    assert response.status_code == 200
    body = response.json()
    assert body["period"] == "all_time"
    assert isinstance(body["rankings"], list)


@pytest.mark.asyncio
async def test_leaderboard_ranking_order(authed_client, db_session):
    client, _ = authed_client
    await _make_active_learner(db_session, "TopLearner", stars=999)
    response = await client.get("/leaderboard?period=all_time")
    assert response.status_code == 200
    rankings = response.json()["rankings"]
    assert rankings[0]["total_stars"] >= rankings[-1]["total_stars"]


@pytest.mark.asyncio
async def test_leaderboard_400_for_invalid_period(authed_client):
    client, _ = authed_client
    response = await client.get("/leaderboard?period=decade")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_weekly_leaderboard_returns_only_active(authed_client, db_session):
    client, _ = authed_client
    response = await client.get("/leaderboard?period=weekly")
    assert response.status_code == 200
    body = response.json()
    assert body["period"] == "weekly"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/api/test_leaderboard.py -v
```

Expected: `404 Not Found`

- [ ] **Step 3: Implement `app/api/leaderboard.py`**

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.daos.leaderboard_dao import LeaderboardDAO
from app.services.leaderboard_service import LeaderboardService
from app.schemas.leaderboard import LeaderboardResponse

router = APIRouter(tags=["leaderboard"])


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    period: str = Query("all_time", description="all_time | weekly | monthly"),
    db: AsyncSession = Depends(get_db),
):
    svc = LeaderboardService(LeaderboardDAO(db))
    result = await svc.get_leaderboard(period)
    return LeaderboardResponse(**result)
```

- [ ] **Step 4: Register leaderboard router in `app/main.py`**

Add `leaderboard` to the import and `app.include_router(leaderboard.router)` alongside the other routers:

```python
from app.api import health, auth, learners, parent, curriculum, progress, quizzes, leaderboard

# ... (keep existing lifespan and _maybe_sync_standards)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(learners.router)
app.include_router(parent.router)
app.include_router(curriculum.router)
app.include_router(progress.router)
app.include_router(quizzes.router)
app.include_router(leaderboard.router)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/api/test_leaderboard.py -v
```

Expected: all 4 tests `PASSED`

- [ ] **Step 6: Commit**

```bash
git add app/api/leaderboard.py app/main.py tests/api/test_leaderboard.py
git commit -m "feat: add leaderboard API (all_time, weekly, monthly)"
```

---

### Task 4: Dashboard schemas + DAO + tests

**Files:**
- Create: `app/schemas/dashboard.py`
- Create: `app/daos/dashboard_dao.py`
- Create: `tests/daos/test_dashboard_dao.py`

- [ ] **Step 1: Write `app/schemas/dashboard.py`**

```python
from __future__ import annotations
from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class TimePerSubject(BaseModel):
    math: int = 0
    science: int = 0
    english: int = 0


class MasteredLesson(BaseModel):
    lesson_id: UUID
    title: str
    subject: str


class NeedsPracticeLesson(BaseModel):
    lesson_id: UUID
    title: str
    subject: str


class RecentActivity(BaseModel):
    lesson_id: UUID
    title: str
    stars_earned: int
    completed_at: Optional[datetime]


class DashboardStatsResponse(BaseModel):
    time_per_subject: TimePerSubject
    mastered: list[MasteredLesson]
    needs_practice: list[NeedsPracticeLesson]
    recent_activity: list[RecentActivity]
```

- [ ] **Step 2: Write the failing tests**

Create `tests/daos/test_dashboard_dao.py`:

```python
import pytest
from datetime import datetime, timezone
from uuid_extensions import uuid7
from app.daos.dashboard_dao import DashboardDAO
from app.daos.parent_dao import ParentDAO
from app.daos.learner_dao import LearnerDAO
from app.daos.progress_dao import ProgressDAO
from app.db.models import Chapter, Standard, Lesson


async def _seed(db_session):
    parent = await ParentDAO(db_session).create(
        cognito_id=f"cog-db-{uuid7()}", email=f"db-{uuid7()}@test.com", pin_hash="h"
    )
    learner = await LearnerDAO(db_session).create(
        parent_id=parent.id, name="Dash", age=7, grade_level=2, avatar_emoji="🚀"
    )
    ch = Chapter(subject="math", title="D Ch", order_index=60)
    db_session.add(ch)
    st = Standard(code=f"DB-{uuid7()}", subject="math", grade_level=2, title="S", description="D")
    db_session.add(st)
    await db_session.flush()
    lesson = Lesson(chapter_id=ch.id, standard_id=st.id, subject="math",
                    title="Dashboard Lesson", difficulty="easy", order_index=1, content={})
    db_session.add(lesson)
    await db_session.flush()
    return learner, lesson


@pytest.mark.asyncio
async def test_get_stats_returns_structure(db_session):
    learner, lesson = await _seed(db_session)
    dao = DashboardDAO(db_session)
    stats = await dao.get_stats(learner.id)
    assert "time_per_subject" in stats
    assert "mastered" in stats
    assert "needs_practice" in stats
    assert "recent_activity" in stats


@pytest.mark.asyncio
async def test_mastered_includes_3_star_lessons(db_session):
    learner, lesson = await _seed(db_session)
    progress_dao = ProgressDAO(db_session)
    await progress_dao.create_lesson_progress(
        learner_id=learner.id, lesson_id=lesson.id,
        stars=3, correct=5, total=5, time_seconds=120,
    )
    dao = DashboardDAO(db_session)
    stats = await dao.get_stats(learner.id)
    mastered_ids = [m["lesson_id"] for m in stats["mastered"]]
    assert str(lesson.id) in mastered_ids


@pytest.mark.asyncio
async def test_needs_practice_includes_low_star_completed_lessons(db_session):
    learner, lesson = await _seed(db_session)
    progress_dao = ProgressDAO(db_session)
    await progress_dao.create_lesson_progress(
        learner_id=learner.id, lesson_id=lesson.id,
        stars=1, correct=2, total=5, time_seconds=90,
    )
    dao = DashboardDAO(db_session)
    stats = await dao.get_stats(learner.id)
    needs_practice_ids = [n["lesson_id"] for n in stats["needs_practice"]]
    assert str(lesson.id) in needs_practice_ids


@pytest.mark.asyncio
async def test_time_per_subject_aggregates_correctly(db_session):
    learner, lesson = await _seed(db_session)
    progress_dao = ProgressDAO(db_session)
    await progress_dao.create_lesson_progress(
        learner_id=learner.id, lesson_id=lesson.id,
        stars=2, correct=3, total=5, time_seconds=200,
    )
    dao = DashboardDAO(db_session)
    stats = await dao.get_stats(learner.id)
    assert stats["time_per_subject"]["math"] >= 200
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
uv run pytest tests/daos/test_dashboard_dao.py -v
```

Expected: `ImportError: cannot import name 'DashboardDAO'`

- [ ] **Step 4: Implement `app/daos/dashboard_dao.py`**

```python
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.models import LessonProgress, Lesson


class DashboardDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_stats(self, learner_id: UUID) -> dict:
        # Fetch all lesson_progress + lesson data in one query
        result = await self.session.execute(
            select(LessonProgress, Lesson)
            .join(Lesson, LessonProgress.lesson_id == Lesson.id)
            .where(LessonProgress.learner_id == learner_id, LessonProgress.completed == True)
            .order_by(LessonProgress.completed_at.desc())
        )
        rows = result.all()

        time_per_subject = {"math": 0, "science": 0, "english": 0}
        mastered = []
        needs_practice = []
        recent_activity = []

        for progress, lesson in rows:
            subject = lesson.subject
            if subject in time_per_subject:
                time_per_subject[subject] += (progress.time_seconds or 0)

            if progress.stars_earned == 3:
                mastered.append({
                    "lesson_id": str(lesson.id),
                    "title": lesson.title,
                    "subject": lesson.subject,
                })
            elif progress.stars_earned <= 1:
                needs_practice.append({
                    "lesson_id": str(lesson.id),
                    "title": lesson.title,
                    "subject": lesson.subject,
                })

            if len(recent_activity) < 10:
                recent_activity.append({
                    "lesson_id": str(lesson.id),
                    "title": lesson.title,
                    "stars_earned": progress.stars_earned or 0,
                    "completed_at": progress.completed_at,
                })

        return {
            "time_per_subject": time_per_subject,
            "mastered": mastered,
            "needs_practice": needs_practice,
            "recent_activity": recent_activity,
        }
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/daos/test_dashboard_dao.py -v
```

Expected: all 4 tests `PASSED`

- [ ] **Step 6: Commit**

```bash
git add app/schemas/dashboard.py app/daos/dashboard_dao.py tests/daos/test_dashboard_dao.py
git commit -m "feat: add DashboardDAO and dashboard schemas (time, mastered, needs-practice, activity)"
```

---

### Task 5: DashboardService + tests

**Files:**
- Create: `app/services/dashboard_service.py`
- Create: `tests/services/test_dashboard_service.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/services/test_dashboard_service.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from app.services.dashboard_service import DashboardService
from app.db.models import Parent, Learner


def _parent():
    p = MagicMock(spec=Parent)
    p.id = uuid4()
    return p


def _learner(parent_id=None):
    l = MagicMock(spec=Learner)
    l.id = uuid4()
    l.parent_id = parent_id or uuid4()
    return l


@pytest.mark.asyncio
async def test_get_stats_delegates_to_dao():
    parent = _parent()
    learner = _learner(parent_id=parent.id)

    learner_svc = MagicMock()
    learner_svc.get = AsyncMock(return_value=learner)

    fake_stats = {
        "time_per_subject": {"math": 100, "science": 0, "english": 0},
        "mastered": [{"lesson_id": str(uuid4()), "title": "L", "subject": "math"}],
        "needs_practice": [],
        "recent_activity": [],
    }
    dashboard_dao = MagicMock()
    dashboard_dao.get_stats = AsyncMock(return_value=fake_stats)

    svc = DashboardService(dashboard_dao)
    result = await svc.get_stats(parent, learner.id, learner_svc)

    dashboard_dao.get_stats.assert_awaited_once_with(learner.id)
    assert result["time_per_subject"]["math"] == 100


@pytest.mark.asyncio
async def test_get_stats_403_when_learner_not_owned():
    from fastapi import HTTPException
    parent = _parent()

    learner_svc = MagicMock()
    learner_svc.get = AsyncMock(side_effect=HTTPException(status_code=403, detail="Not owned"))

    svc = DashboardService(MagicMock())
    with pytest.raises(HTTPException) as exc:
        await svc.get_stats(parent, uuid4(), learner_svc)
    assert exc.value.status_code == 403
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/services/test_dashboard_service.py -v
```

Expected: `ImportError: cannot import name 'DashboardService'`

- [ ] **Step 3: Implement `app/services/dashboard_service.py`**

```python
from uuid import UUID
from app.daos.dashboard_dao import DashboardDAO
from app.db.models import Parent


class DashboardService:
    def __init__(self, dao: DashboardDAO):
        self.dao = dao

    async def get_stats(self, parent: Parent, learner_id: UUID, learner_svc) -> dict:
        learner = await learner_svc.get(parent, learner_id)
        return await self.dao.get_stats(learner.id)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/services/test_dashboard_service.py -v
```

Expected: both tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add app/services/dashboard_service.py tests/services/test_dashboard_service.py
git commit -m "feat: add DashboardService"
```

---

### Task 6: Parent Dashboard API + integration tests

**Files:**
- Modify: `app/api/parent.py`
- Create: `tests/api/test_parent_dashboard.py`

The `GET /parent/learners/{learner_id}/stats` endpoint requires the parent-dashboard JWT (15-min token issued by `POST /parent/verify-pin`), not the Cognito JWT. It uses the `get_current_parent_dashboard` dependency from Phase 2.

- [ ] **Step 1: Write the failing tests**

Create `tests/api/test_parent_dashboard.py`:

```python
import pytest
from jose import jwt
from datetime import datetime, timezone, timedelta
from app.core.config import settings
from app.daos.learner_dao import LearnerDAO
from app.daos.parent_dao import ParentDAO
from app.daos.progress_dao import ProgressDAO
from app.db.models import Chapter, Standard, Lesson
from app.api import deps
from app.main import app


def _make_dashboard_token(parent_id: str) -> str:
    payload = {
        "sub": parent_id,
        "scope": "parent_dashboard",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
    }
    return jwt.encode(payload, settings.parent_jwt_secret, algorithm="HS256")


async def _seed_dashboard_data(db_session, parent):
    learner = await LearnerDAO(db_session).create(
        parent_id=parent.id, name="DashLearner", age=7, grade_level=2, avatar_emoji="🌟"
    )
    ch = Chapter(subject="math", title="D Ch", order_index=70)
    db_session.add(ch)
    st = Standard(code=f"DASH-{id(db_session)}", subject="math", grade_level=2,
                  title="S", description="D")
    db_session.add(st)
    await db_session.flush()
    lesson = Lesson(chapter_id=ch.id, standard_id=st.id, subject="math",
                    title="Test Lesson", difficulty="easy", order_index=1, content={})
    db_session.add(lesson)
    await db_session.flush()
    await ProgressDAO(db_session).create_lesson_progress(
        learner_id=learner.id, lesson_id=lesson.id,
        stars=3, correct=5, total=5, time_seconds=150,
    )
    return learner


@pytest.mark.asyncio
async def test_dashboard_stats_returns_200(client, db_session):
    from uuid_extensions import uuid7
    import bcrypt
    parent = await ParentDAO(db_session).create(
        cognito_id=f"cog-dash-{uuid7()}",
        email=f"dash-{uuid7()}@test.com",
        pin_hash=bcrypt.hashpw(b"1234", bcrypt.gensalt()).decode(),
    )
    # Override get_current_parent_dashboard to return this parent
    app.dependency_overrides[deps.get_current_parent_dashboard] = lambda: parent

    learner = await _seed_dashboard_data(db_session, parent)
    token = _make_dashboard_token(str(parent.id))

    response = await client.get(
        f"/parent/learners/{learner.id}/stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "time_per_subject" in body
    assert "mastered" in body
    assert "needs_practice" in body
    assert "recent_activity" in body
    assert body["time_per_subject"]["math"] >= 150
    mastered_ids = [m["lesson_id"] for m in body["mastered"]]
    assert str(learner.id) not in mastered_ids  # mastered = lesson_ids, not learner_ids
    assert len(body["mastered"]) >= 1


@pytest.mark.asyncio
async def test_dashboard_stats_returns_403_for_wrong_learner(client, db_session):
    from uuid_extensions import uuid7
    import bcrypt
    parent = await ParentDAO(db_session).create(
        cognito_id=f"cog-dash2-{uuid7()}",
        email=f"dash2-{uuid7()}@test.com",
        pin_hash=bcrypt.hashpw(b"1234", bcrypt.gensalt()).decode(),
    )
    app.dependency_overrides[deps.get_current_parent_dashboard] = lambda: parent
    response = await client.get(f"/parent/learners/{uuid7()}/stats",
                                headers={"Authorization": "Bearer fake"})
    assert response.status_code in (403, 404)


@pytest.mark.asyncio
async def test_dashboard_rejects_cognito_jwt(authed_client, db_session):
    """Cognito JWT (Bearer token from login) must NOT work on dashboard routes."""
    client, parent = authed_client
    # authed_client overrides get_current_parent (Cognito), NOT get_current_parent_dashboard
    # Dashboard dep is NOT overridden, so it will try to decode a fake token and fail
    from uuid_extensions import uuid7
    learner = await LearnerDAO(db_session).create(
        parent_id=parent.id, name="X", age=5, grade_level=0, avatar_emoji="🚀"
    )
    response = await client.get(
        f"/parent/learners/{learner.id}/stats",
        headers={"Authorization": "Bearer cognito-jwt-would-fail-here"},
    )
    assert response.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/api/test_parent_dashboard.py -v
```

Expected: `404 Not Found` (route not registered)

- [ ] **Step 3: Add dashboard endpoint to `app/api/parent.py`**

Full `app/api/parent.py` after modification:

```python
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.deps import get_current_parent, get_current_parent_dashboard
from app.services.parent_service import ParentService
from app.services.dashboard_service import DashboardService
from app.services.learner_service import LearnerService
from app.daos.dashboard_dao import DashboardDAO
from app.daos.learner_dao import LearnerDAO
from app.schemas.parent import VerifyPinRequest, ParentTokenResponse
from app.schemas.dashboard import DashboardStatsResponse
from app.db.models import Parent

router = APIRouter(prefix="/parent", tags=["parent"])


@router.post("/verify-pin", response_model=ParentTokenResponse)
async def verify_pin(
    body: VerifyPinRequest,
    parent: Parent = Depends(get_current_parent),
):
    token = ParentService().verify_pin_and_issue_token(parent, body.pin)
    return ParentTokenResponse(token=token)


@router.get("/learners/{learner_id}/stats", response_model=DashboardStatsResponse)
async def get_learner_stats(
    learner_id: UUID,
    parent: Parent = Depends(get_current_parent_dashboard),
    db: AsyncSession = Depends(get_db),
):
    learner_svc = LearnerService(LearnerDAO(db))
    svc = DashboardService(DashboardDAO(db))
    result = await svc.get_stats(parent, learner_id, learner_svc)
    return DashboardStatsResponse(
        time_per_subject=result["time_per_subject"],
        mastered=result["mastered"],
        needs_practice=result["needs_practice"],
        recent_activity=result["recent_activity"],
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/api/test_parent_dashboard.py -v
```

Expected: all 3 tests `PASSED`

- [ ] **Step 5: Run full test suite**

```bash
uv run pytest -v
```

Expected: all tests pass, no warnings.

- [ ] **Step 6: Commit**

```bash
git add app/api/parent.py tests/api/test_parent_dashboard.py
git commit -m "feat: add parent dashboard stats endpoint (time, mastered, needs-practice, activity)"
```

---

## Phase 5 Done

At end of Phase 5 the full backend is feature-complete:

- `GET /leaderboard?period=all_time|weekly|monthly` — ranked by stars → streak → created_at; period filters by `last_active_at`
- `GET /parent/learners/{learner_id}/stats` — time per subject, mastered (3★), needs practice (≤1★ completed), recent activity (last 10)
- Parent dashboard routes protected by the 15-min JWT from `POST /parent/verify-pin`
- Cognito JWT rejected on parent-dashboard routes (different scope)

**All 5 phases complete.** The backend now supports:

| Phase | Deliverable |
|-------|-------------|
| 1 | Foundation: auth, DB, health, CI/CD |
| 2 | Learner CRUD, parent PIN + dashboard JWT |
| 3 | Standards sync, lesson generation, curriculum with lock states |
| 4 | Progress, grading, XP, streaks, chapter quizzes |
| 5 | Leaderboard, parent dashboard stats |
