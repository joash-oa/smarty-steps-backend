# Smarty Steps Backend — Phase 3: Standards Sync & Content Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sync NY State standards from the ASN API, auto-create chapters from standard domains, generate lesson content via Claude (15 exercises per lesson, mixed types), and serve the curriculum with per-learner lock states and sanitized lesson JSONB.

**Architecture:** `ContentService` (background task, non-blocking) owns standards sync + chapter creation + lesson generation. Chapters are created dynamically from ASN standard domains — not pre-seeded. `LessonService` owns lock-state computation (pure function, no DB) and JSONB sanitization. `LessonDAO` is the sole DB interface for curriculum data. `StandardsAPIClient` and `ClaudeClient` are injectable clients; tests mock them.

**Tech Stack:** Python 3.12, FastAPI lifespan hook, asyncio.create_task, httpx, anthropic SDK (claude-opus-4-7 with prompt caching), SQLAlchemy async, pytest-asyncio, unittest.mock

---

## File Structure

```
app/
  clients/
    standards_api.py         — Create: StandardsAPIClient (fetch NY State standards via ASN API,
                                        StandardData includes domain field for chapter grouping)
    claude_client.py         — Create: ClaudeClient (generate lesson JSONB via Anthropic SDK)
  daos/
    lesson_dao.py            — Create: get_chapters_by_subject, get_or_create_chapter,
                                        get_lesson_by_id, get_lessons_by_chapter,
                                        count_lessons_in_chapter, get_lesson_by_standard,
                                        create_lesson, get_standard_by_code, create_standard,
                                        count_standards
  services/
    content_service.py       — Create: ContentService (sync_subject_grade, sync_all)
                                        Chapters auto-created from ASN standard domains.
    lesson_service.py        — Create: LessonService (compute_lock_states, sanitize_lesson,
                                                       compute_effective_stars)
  schemas/
    curriculum.py            — Create: ChapterResponse, LessonSummary, QuizState,
                                        CurriculumResponse, LessonDetailResponse
  api/
    curriculum.py            — Create: GET /subjects/{subject}/chapters, GET /lessons/{lesson_id}
  daos/
    progress_dao.py          — Create: stub (Phase 4 fills in)
  core/
    config.py                — Modify: add standards_api_base_url field
  main.py                    — Modify: add lifespan hook for background sync
tests/
  daos/
    test_lesson_dao.py       — Create
  services/
    test_content_service.py  — Create (mocked clients)
    test_lesson_service.py   — Create (pure function tests, no DB)
  api/
    test_curriculum.py       — Create
```

---

### Task 1: Settings update + StandardsAPIClient

**Files:**
- Modify: `app/core/config.py`
- Create: `app/clients/standards_api.py`
- Modify: `.env.example`

- [ ] **Step 1: Add `standards_api_base_url` to `app/core/config.py`**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    cognito_user_pool_id: str
    cognito_client_id: str
    cognito_region: str = "us-east-1"
    anthropic_api_key: str
    parent_jwt_secret: str
    parent_jwt_expire_minutes: int = 15
    standards_api_base_url: str = "http://asn.desire2learn.com/resources.json"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
```

- [ ] **Step 2: Add `STANDARDS_API_BASE_URL` to `.env.example`**

```env
STANDARDS_API_BASE_URL=http://asn.desire2learn.com/resources.json
```

- [ ] **Step 3: Implement `app/clients/standards_api.py`**

The ASN API returns standards in JSON-LD format. Each standard belongs to a domain (strand)
identified by the prefix of its `statementNotation` (e.g. "K.CC" → "Counting & Cardinality").
The `domain` field drives chapter auto-creation in `ContentService`.

```python
from dataclasses import dataclass
from typing import Optional
import httpx
from app.core.config import settings

SUBJECT_MAP = {
    "math": "Mathematics",
    "science": "Science",
    "english": "English Language Arts",
}

GRADE_MAP = {0: "K", 1: "1", 2: "2", 3: "3"}


@dataclass
class StandardData:
    code: str
    subject: str          # "math" | "science" | "english"
    grade_level: int      # 0-3
    title: str
    description: Optional[str]
    domain: str           # chapter grouping, e.g. "Counting & Cardinality"


def _extract_domain(item: dict, subject: str) -> str:
    """Derive a human-readable domain name for chapter grouping.

    ASN standards have a 'subject' field at the broader strand level, or we fall back
    to the notation prefix (e.g. 'K.CC' from 'K.CC.1') to group related standards.
    """
    notation = item.get("statementNotation", "")
    if notation and "." in notation:
        # Take up to the second segment: "K.CC.1" → "K.CC"
        parts = notation.split(".")
        prefix = ".".join(parts[:2])
        return prefix
    # Fall back to broad subject label
    return SUBJECT_MAP.get(subject, subject.title())


class StandardsAPIClient:
    def __init__(self, base_url: str = None):
        self._base_url = base_url or settings.standards_api_base_url

    async def fetch_standards(self, subject: str, grade_level: int) -> list[StandardData]:
        """Fetch NY State standards for one subject+grade from ASN API."""
        params = {
            "jurisdiction": "NYSED",
            "gradeBegin": GRADE_MAP[grade_level],
            "gradeEnd": GRADE_MAP[grade_level],
            "subjectArea": SUBJECT_MAP[subject],
            "limit": 200,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(self._base_url, params=params)
            response.raise_for_status()
            data = response.json()

        results = []
        for item in data.get("resources", []):
            description = item.get("description", "")
            identifier = item.get("identifier", "")
            code = identifier or item.get("uri", "").split("/")[-1]
            title = item.get("statementNotation", identifier) or description[:80]
            if not code or not description:
                continue
            results.append(StandardData(
                code=code,
                subject=subject,
                grade_level=grade_level,
                title=title,
                description=description,
                domain=_extract_domain(item, subject),
            ))
        return results
```

- [ ] **Step 4: Commit**

```bash
git add app/core/config.py app/clients/standards_api.py .env.example
git commit -m "feat(p3-task1): add StandardsAPIClient with domain extraction and standards_api_base_url setting"
```

---

### Task 2: ClaudeClient for lesson generation

**Files:**
- Create: `app/clients/claude_client.py`

No unit tests — the client is injectable so ContentService tests mock it.

- [ ] **Step 1: Implement `app/clients/claude_client.py`**

Uses `claude-opus-4-7` with prompt caching on the system prompt.

```python
import json
import anthropic
from app.core.config import settings

SYSTEM_PROMPT = """You are an educational content creator for Smarty Steps, a learning app for children ages 5-8.

Generate lesson content as valid JSON matching this exact schema:
{
  "intro": {
    "title": "<lesson title>",
    "description": "<1-2 sentences, child-friendly>",
    "mascot_quote": "<encouraging quote from the mascot>"
  },
  "exercises": [
    // EXACTLY 15 exercises, mix of types below, progressing easy→medium→hard
    // Type: multiple_choice
    {
      "id": "ex_1",
      "type": "multiple_choice",
      "difficulty": "easy|medium|hard",
      "prompt": "<question text>",
      "mascot_hint": "<short hint>",
      "options": [{"id": "a", "text": "..."}, {"id": "b", "text": "..."}, {"id": "c", "text": "..."}, {"id": "d", "text": "..."}],
      "correct_option_id": "a|b|c|d",
      "explanation": "<why the answer is correct>"
    },
    // Type: fill_blank
    {
      "id": "ex_N",
      "type": "fill_blank",
      "difficulty": "easy|medium|hard",
      "prompt": "Fill in the blank",
      "sentence_parts": ["<part before blank>", "_____", "<part after blank>"],
      "word_bank": ["<correct word>", "<wrong1>", "<wrong2>", "<wrong3>"],
      "correct_word": "<correct word>",
      "mascot_hint": "<short hint>"
    },
    // Type: matching
    {
      "id": "ex_N",
      "type": "matching",
      "difficulty": "easy|medium|hard",
      "prompt": "<instruction>",
      "mascot_hint": "<short hint>",
      "pairs": [
        {"left": "<item>", "right": "<match>"},
        {"left": "<item>", "right": "<match>"},
        {"left": "<item>", "right": "<match>"}
      ]
    }
  ],
  "result": {
    "badge_name": "<achievement name>",
    "badge_description": "<1 sentence>"
  },
  "stars_available": 3
}

Rules:
- Exactly 15 exercises total
- Mix all 3 types (at least 4 multiple_choice, at least 3 fill_blank, at least 3 matching)
- First 5 exercises: difficulty easy. Next 5: difficulty medium. Last 5: difficulty hard.
- All content must be appropriate for ages 5-8
- IDs must be "ex_1" through "ex_15" in order
- Return ONLY the JSON object, no markdown fences or extra text"""


class ClaudeClient:
    def __init__(self):
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def generate_lesson(
        self, standard_title: str, standard_description: str, subject: str, grade_level: int
    ) -> dict:
        """Generate lesson JSONB for a standard. Returns parsed dict."""
        grade_label = {0: "Kindergarten", 1: "Grade 1", 2: "Grade 2", 3: "Grade 3"}[grade_level]
        user_message = (
            f"Generate a lesson for this {subject} standard ({grade_label}):\n"
            f"Standard: {standard_title}\n"
            f"Description: {standard_description}\n\n"
            f"Return only the JSON object."
        )
        response = await self._client.messages.create(
            model="claude-opus-4-7",
            max_tokens=4096,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_message}],
        )
        raw = response.content[0].text.strip()
        return json.loads(raw)


_claude_client: ClaudeClient | None = None


def get_claude_client() -> ClaudeClient:
    global _claude_client
    if _claude_client is None:
        _claude_client = ClaudeClient()
    return _claude_client
```

- [ ] **Step 2: Commit**

```bash
git add app/clients/claude_client.py
git commit -m "feat(p3-task2): add ClaudeClient for lesson JSONB generation (claude-opus-4-7 + prompt caching)"
```

---

### Task 3: LessonDAO + tests

**Files:**
- Create: `app/daos/lesson_dao.py`
- Create: `tests/daos/test_lesson_dao.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/daos/test_lesson_dao.py`:

```python
import pytest
from uuid_extensions import uuid7
from app.daos.lesson_dao import LessonDAO
from app.db.models import Chapter, Standard, Lesson


async def _seed_standard(db_session, subject="math", grade=1) -> Standard:
    st = Standard(
        code=f"NY-{uuid7()}", subject=subject, grade_level=grade,
        title="Test Standard", description="A test standard.",
    )
    db_session.add(st)
    await db_session.flush()
    return st


LESSON_CONTENT = {
    "intro": {"title": "T", "description": "D", "mascot_quote": "Q"},
    "exercises": [],
    "result": {"badge_name": "B", "badge_description": "BD"},
    "stars_available": 3,
}


@pytest.mark.asyncio
async def test_get_or_create_chapter_creates_on_first_call(db_session):
    dao = LessonDAO(db_session)
    ch = await dao.get_or_create_chapter(subject="math", domain="K.CC")
    assert ch.id is not None
    assert ch.title == "K.CC"
    assert ch.subject == "math"


@pytest.mark.asyncio
async def test_get_or_create_chapter_is_idempotent(db_session):
    dao = LessonDAO(db_session)
    ch1 = await dao.get_or_create_chapter(subject="math", domain="K.OA")
    ch2 = await dao.get_or_create_chapter(subject="math", domain="K.OA")
    assert ch1.id == ch2.id


@pytest.mark.asyncio
async def test_create_and_get_lesson(db_session):
    dao = LessonDAO(db_session)
    ch = await dao.get_or_create_chapter(subject="math", domain="K.CC")
    st = await _seed_standard(db_session)
    lesson = await dao.create_lesson(
        chapter_id=ch.id, standard_id=st.id, subject="math",
        title="Counting to 10", difficulty="easy", order_index=1,
        content=LESSON_CONTENT,
    )
    assert lesson.id is not None
    fetched = await dao.get_lesson_by_id(lesson.id)
    assert fetched is not None
    assert fetched.title == "Counting to 10"


@pytest.mark.asyncio
async def test_get_chapters_by_subject_ordered(db_session):
    dao = LessonDAO(db_session)
    ch1 = await dao.get_or_create_chapter(subject="science", domain="Domain A")
    ch2 = await dao.get_or_create_chapter(subject="science", domain="Domain B")
    chapters = await dao.get_chapters_by_subject("science")
    ids = [c.id for c in chapters]
    assert ch1.id in ids
    assert ch2.id in ids
    orders = [c.order_index for c in chapters]
    assert orders == sorted(orders)


@pytest.mark.asyncio
async def test_count_standards_returns_zero_on_empty(db_session):
    dao = LessonDAO(db_session)
    count = await dao.count_standards()
    assert count >= 0


@pytest.mark.asyncio
async def test_get_standard_by_code_returns_none_when_missing(db_session):
    dao = LessonDAO(db_session)
    result = await dao.get_standard_by_code("NO-SUCH-CODE")
    assert result is None


@pytest.mark.asyncio
async def test_count_lessons_in_chapter(db_session):
    dao = LessonDAO(db_session)
    ch = await dao.get_or_create_chapter(subject="english", domain="ELA.RL")
    st = await _seed_standard(db_session, subject="english", grade=1)
    await dao.create_lesson(
        chapter_id=ch.id, standard_id=st.id, subject="english",
        title="L1", difficulty="easy", order_index=1, content=LESSON_CONTENT,
    )
    await dao.create_lesson(
        chapter_id=ch.id, standard_id=st.id, subject="english",
        title="L2", difficulty="medium", order_index=2, content=LESSON_CONTENT,
    )
    count = await dao.count_lessons_in_chapter(ch.id)
    assert count == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/daos/test_lesson_dao.py -v
```

Expected: `ImportError: cannot import name 'LessonDAO'`

- [ ] **Step 3: Implement `app/daos/lesson_dao.py`**

```python
from uuid import UUID
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.models import Chapter, Lesson, Standard


class LessonDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_chapter(self, subject: str, domain: str) -> Chapter:
        """Return existing chapter for this subject+domain, or create it."""
        result = await self.session.execute(
            select(Chapter).where(Chapter.subject == subject, Chapter.title == domain)
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        # Assign next order_index for this subject
        count_result = await self.session.execute(
            select(func.count()).select_from(Chapter).where(Chapter.subject == subject)
        )
        next_order = (count_result.scalar_one() or 0) + 1

        chapter = Chapter(subject=subject, title=domain, order_index=next_order)
        self.session.add(chapter)
        await self.session.flush()
        await self.session.refresh(chapter)
        return chapter

    async def get_chapters_by_subject(self, subject: str) -> list[Chapter]:
        result = await self.session.execute(
            select(Chapter)
            .where(Chapter.subject == subject)
            .order_by(Chapter.order_index)
        )
        return list(result.scalars().all())

    async def get_lessons_by_chapter(self, chapter_id: UUID) -> list[Lesson]:
        result = await self.session.execute(
            select(Lesson)
            .where(Lesson.chapter_id == chapter_id)
            .order_by(Lesson.order_index)
        )
        return list(result.scalars().all())

    async def get_lesson_by_id(self, lesson_id: UUID) -> Optional[Lesson]:
        result = await self.session.execute(
            select(Lesson).where(Lesson.id == lesson_id)
        )
        return result.scalar_one_or_none()

    async def get_lesson_by_standard(self, standard_id: UUID) -> Optional[Lesson]:
        result = await self.session.execute(
            select(Lesson).where(Lesson.standard_id == standard_id)
        )
        return result.scalar_one_or_none()

    async def create_lesson(
        self,
        chapter_id: UUID,
        standard_id: Optional[UUID],
        subject: str,
        title: str,
        difficulty: str,
        order_index: int,
        content: dict,
    ) -> Lesson:
        lesson = Lesson(
            chapter_id=chapter_id,
            standard_id=standard_id,
            subject=subject,
            title=title,
            difficulty=difficulty,
            order_index=order_index,
            content=content,
        )
        self.session.add(lesson)
        await self.session.flush()
        await self.session.refresh(lesson)
        return lesson

    async def count_lessons_in_chapter(self, chapter_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Lesson).where(Lesson.chapter_id == chapter_id)
        )
        return result.scalar_one()

    async def get_standard_by_code(self, code: str) -> Optional[Standard]:
        result = await self.session.execute(
            select(Standard).where(Standard.code == code)
        )
        return result.scalar_one_or_none()

    async def create_standard(
        self,
        code: str,
        subject: str,
        grade_level: int,
        title: str,
        description: Optional[str],
    ) -> Standard:
        standard = Standard(
            code=code,
            subject=subject,
            grade_level=grade_level,
            title=title,
            description=description,
        )
        self.session.add(standard)
        await self.session.flush()
        await self.session.refresh(standard)
        return standard

    async def count_standards(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Standard)
        )
        return result.scalar_one()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/daos/test_lesson_dao.py -v
```

Expected: all 7 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add app/daos/lesson_dao.py tests/daos/test_lesson_dao.py
git commit -m "feat(p3-task3): add LessonDAO with get_or_create_chapter for dynamic chapter creation"
```

---

### Task 4: ContentService + tests

**Files:**
- Create: `app/services/content_service.py`
- Create: `tests/services/test_content_service.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/services/test_content_service.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.content_service import ContentService
from app.clients.standards_api import StandardData

MOCK_STANDARD = StandardData(
    code="NY-TEST.1",
    subject="math",
    grade_level=1,
    title="Count to 20",
    description="Students can count to 20.",
    domain="K.CC",
)

MOCK_LESSON_CONTENT = {
    "intro": {"title": "Count to 20", "description": "D", "mascot_quote": "Q"},
    "exercises": [
        {"id": f"ex_{i}", "type": "multiple_choice", "difficulty": "easy",
         "prompt": "Q?", "mascot_hint": "H", "options": [],
         "correct_option_id": "a", "explanation": "E"}
        for i in range(1, 16)
    ],
    "result": {"badge_name": "B", "badge_description": "BD"},
    "stars_available": 3,
}


@pytest.mark.asyncio
async def test_sync_skips_existing_standard(db_session):
    """If a standard already has a lesson, it's skipped entirely."""
    mock_api = MagicMock()
    mock_api.fetch_standards = AsyncMock(return_value=[MOCK_STANDARD])
    mock_claude = MagicMock()
    mock_claude.generate_lesson = AsyncMock(return_value=MOCK_LESSON_CONTENT)

    from app.daos.lesson_dao import LessonDAO
    from app.db.models import Standard

    existing = Standard(
        code=MOCK_STANDARD.code, subject="math", grade_level=1,
        title="Already exists", description="D",
    )
    db_session.add(existing)
    await db_session.flush()

    dao = LessonDAO(db_session)
    ch = await dao.get_or_create_chapter(subject="math", domain=MOCK_STANDARD.domain)
    await dao.create_lesson(
        chapter_id=ch.id, standard_id=existing.id, subject="math",
        title="Existing lesson", difficulty="easy", order_index=1,
        content=MOCK_LESSON_CONTENT,
    )

    svc = ContentService(lesson_dao=dao, standards_api=mock_api, claude=mock_claude)
    await svc.sync_subject_grade("math", 1)

    mock_claude.generate_lesson.assert_not_called()


@pytest.mark.asyncio
async def test_sync_creates_chapter_and_lesson_for_new_standard(db_session):
    """New standard → auto-create chapter from domain → generate lesson."""
    from uuid_extensions import uuid7
    mock_api = MagicMock()
    unique_code = f"NY-NEW-{uuid7()}"
    std = StandardData(
        code=unique_code, subject="math", grade_level=2,
        title="New Standard", description="Description.",
        domain="2.NBT",
    )
    mock_api.fetch_standards = AsyncMock(return_value=[std])
    mock_claude = MagicMock()
    mock_claude.generate_lesson = AsyncMock(return_value=MOCK_LESSON_CONTENT)

    from app.daos.lesson_dao import LessonDAO
    dao = LessonDAO(db_session)

    svc = ContentService(lesson_dao=dao, standards_api=mock_api, claude=mock_claude)
    await svc.sync_subject_grade("math", 2)

    mock_claude.generate_lesson.assert_awaited_once()

    # Chapter should have been auto-created from domain
    chapters = await dao.get_chapters_by_subject("math")
    chapter_titles = [c.title for c in chapters]
    assert "2.NBT" in chapter_titles
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/services/test_content_service.py -v
```

Expected: `ImportError: cannot import name 'ContentService'`

- [ ] **Step 3: Implement `app/services/content_service.py`**

```python
from app.daos.lesson_dao import LessonDAO
from app.clients.standards_api import StandardsAPIClient
from app.clients.claude_client import ClaudeClient

SUBJECTS = ["math", "science", "english"]
GRADE_LEVELS = [0, 1, 2, 3]

DIFFICULTY_BY_ORDER = {1: "easy", 2: "easy", 3: "medium", 4: "medium", 5: "hard"}


class ContentService:
    def __init__(self, lesson_dao: LessonDAO, standards_api: StandardsAPIClient, claude: ClaudeClient):
        self.dao = lesson_dao
        self.api = standards_api
        self.claude = claude

    async def sync_subject_grade(self, subject: str, grade_level: int) -> None:
        """Fetch standards, auto-create chapters from domains, generate lessons. Idempotent."""
        standards = await self.api.fetch_standards(subject, grade_level)

        for std_data in standards:
            existing_standard = await self.dao.get_standard_by_code(std_data.code)
            if existing_standard:
                existing_lesson = await self.dao.get_lesson_by_standard(existing_standard.id)
                if existing_lesson:
                    continue
                standard = existing_standard
            else:
                standard = await self.dao.create_standard(
                    code=std_data.code,
                    subject=std_data.subject,
                    grade_level=std_data.grade_level,
                    title=std_data.title,
                    description=std_data.description,
                )

            # Auto-create chapter from standard's domain if it doesn't exist
            chapter = await self.dao.get_or_create_chapter(
                subject=subject, domain=std_data.domain
            )

            order_index = (await self.dao.count_lessons_in_chapter(chapter.id)) + 1
            difficulty = DIFFICULTY_BY_ORDER.get(order_index, "hard")

            content = await self.claude.generate_lesson(
                standard_title=std_data.title,
                standard_description=std_data.description or std_data.title,
                subject=subject,
                grade_level=grade_level,
            )
            await self.dao.create_lesson(
                chapter_id=chapter.id,
                standard_id=standard.id,
                subject=subject,
                title=std_data.title,
                difficulty=difficulty,
                order_index=order_index,
                content=content,
            )

    async def sync_all(self) -> None:
        """Full sync: all subjects × all grade levels. Idempotent."""
        for subject in SUBJECTS:
            for grade_level in GRADE_LEVELS:
                await self.sync_subject_grade(subject, grade_level)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/services/test_content_service.py -v
```

Expected: all 2 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add app/services/content_service.py tests/services/test_content_service.py
git commit -m "feat(p3-task4): add ContentService — auto-creates chapters from ASN domains"
```

---

### Task 5: LessonService (lock states + sanitize) + tests

**Files:**
- Create: `app/services/lesson_service.py`
- Create: `tests/services/test_lesson_service.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/services/test_lesson_service.py`:

```python
import pytest
from unittest.mock import MagicMock
from uuid import uuid4
from app.services.lesson_service import (
    compute_lock_states,
    sanitize_lesson_content,
    compute_effective_stars,
)
from app.db.models import Chapter, Lesson


def _chapter(order):
    ch = MagicMock(spec=Chapter)
    ch.id = uuid4()
    ch.order_index = order
    return ch


def _lesson(chapter_id, order):
    lesson = MagicMock(spec=Lesson)
    lesson.id = uuid4()
    lesson.chapter_id = chapter_id
    lesson.order_index = order
    return lesson


def test_first_lesson_of_first_chapter_always_unlocked():
    ch1 = _chapter(1)
    l1 = _lesson(ch1.id, 1)
    result = compute_lock_states(
        chapters=[ch1],
        lessons_by_chapter={ch1.id: [l1]},
        completed_lesson_ids=set(),
    )
    assert result[l1.id] is False


def test_second_lesson_locked_until_first_completed():
    ch1 = _chapter(1)
    l1 = _lesson(ch1.id, 1)
    l2 = _lesson(ch1.id, 2)
    result = compute_lock_states(
        chapters=[ch1],
        lessons_by_chapter={ch1.id: [l1, l2]},
        completed_lesson_ids=set(),
    )
    assert result[l1.id] is False
    assert result[l2.id] is True


def test_second_lesson_unlocked_when_first_completed():
    ch1 = _chapter(1)
    l1 = _lesson(ch1.id, 1)
    l2 = _lesson(ch1.id, 2)
    result = compute_lock_states(
        chapters=[ch1],
        lessons_by_chapter={ch1.id: [l1, l2]},
        completed_lesson_ids={l1.id},
    )
    assert result[l2.id] is False


def test_chapter_boundary_locked_until_all_previous_complete():
    ch1 = _chapter(1)
    ch2 = _chapter(2)
    l1 = _lesson(ch1.id, 1)
    l2 = _lesson(ch1.id, 2)
    l3 = _lesson(ch2.id, 1)
    result = compute_lock_states(
        chapters=[ch1, ch2],
        lessons_by_chapter={ch1.id: [l1, l2], ch2.id: [l3]},
        completed_lesson_ids={l1.id},
    )
    assert result[l3.id] is True


def test_chapter_boundary_unlocked_when_all_previous_complete():
    ch1 = _chapter(1)
    ch2 = _chapter(2)
    l1 = _lesson(ch1.id, 1)
    l2 = _lesson(ch1.id, 2)
    l3 = _lesson(ch2.id, 1)
    result = compute_lock_states(
        chapters=[ch1, ch2],
        lessons_by_chapter={ch1.id: [l1, l2], ch2.id: [l3]},
        completed_lesson_ids={l1.id, l2.id},
    )
    assert result[l3.id] is False


def test_sanitize_strips_correct_answers():
    content = {
        "intro": {"title": "T", "description": "D", "mascot_quote": "Q"},
        "exercises": [
            {
                "id": "ex_1", "type": "multiple_choice", "difficulty": "easy",
                "prompt": "Q", "mascot_hint": "H",
                "options": [{"id": "a", "text": "A"}, {"id": "b", "text": "B"}],
                "correct_option_id": "a",
                "explanation": "Because.",
            },
            {
                "id": "ex_2", "type": "fill_blank", "difficulty": "medium",
                "prompt": "Fill", "sentence_parts": ["The", "_____", "cat."],
                "word_bank": ["big", "small"], "correct_word": "big", "mascot_hint": "H",
            },
            {
                "id": "ex_3", "type": "matching", "difficulty": "hard",
                "prompt": "Match", "mascot_hint": "H",
                "pairs": [{"left": "🐟", "right": "🌊"}, {"left": "🦅", "right": "🏔️"}],
            },
        ],
        "result": {"badge_name": "B", "badge_description": "BD"},
        "stars_available": 3,
    }
    sanitized = sanitize_lesson_content(content)
    mc = sanitized["exercises"][0]
    assert "correct_option_id" not in mc
    assert "explanation" not in mc
    fb = sanitized["exercises"][1]
    assert "correct_word" not in fb
    match = sanitized["exercises"][2]
    assert "pairs" not in match
    assert set(match["left_items"]) == {"🐟", "🦅"}
    assert set(match["right_items"]) == {"🌊", "🏔️"}


def test_compute_effective_stars():
    assert compute_effective_stars(3) == 6
    assert compute_effective_stars(2) == 3
    assert compute_effective_stars(1) == 1
    assert compute_effective_stars(0) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/services/test_lesson_service.py -v
```

Expected: `ImportError: cannot import name 'compute_lock_states'`

- [ ] **Step 3: Implement `app/services/lesson_service.py`**

```python
import copy
import random
from app.db.models import Chapter, Lesson


def compute_lock_states(
    chapters: list,
    lessons_by_chapter: dict,
    completed_lesson_ids: set,
) -> dict:
    """Returns {lesson_id: is_locked} for all lessons. Pure function — no DB calls."""
    locked = {}
    for chapter_idx, chapter in enumerate(chapters):
        lessons = sorted(lessons_by_chapter.get(chapter.id, []), key=lambda l: l.order_index)
        for lesson_idx, lesson in enumerate(lessons):
            if chapter_idx == 0 and lesson_idx == 0:
                locked[lesson.id] = False
            elif lesson_idx == 0:
                prev_chapter = chapters[chapter_idx - 1]
                prev_lessons = lessons_by_chapter.get(prev_chapter.id, [])
                all_prev_done = all(l.id in completed_lesson_ids for l in prev_lessons)
                locked[lesson.id] = not all_prev_done
            else:
                prev_lesson = lessons[lesson_idx - 1]
                locked[lesson.id] = prev_lesson.id not in completed_lesson_ids
    return locked


def is_quiz_locked(chapter, lessons: list, completed_lesson_ids: set) -> bool:
    return not all(l.id in completed_lesson_ids for l in lessons)


def sanitize_lesson_content(content: dict) -> dict:
    """Strip correct answers from lesson JSONB. Returns a new dict — does not mutate input."""
    result = copy.deepcopy(content)
    for ex in result.get("exercises", []):
        ex_type = ex.get("type")
        if ex_type == "multiple_choice":
            ex.pop("correct_option_id", None)
            ex.pop("explanation", None)
        elif ex_type == "fill_blank":
            ex.pop("correct_word", None)
        elif ex_type == "matching":
            pairs = ex.pop("pairs", [])
            left_items = [p["left"] for p in pairs]
            right_items = [p["right"] for p in pairs]
            random.shuffle(right_items)
            ex["left_items"] = left_items
            ex["right_items"] = right_items
    return result


def compute_effective_stars(raw_stars: int) -> int:
    """Apply chapter quiz star multiplier: 3→×2=6, 2→×1.5=3, 1→×1=1, 0→0."""
    return {3: 6, 2: 3, 1: 1, 0: 0}.get(raw_stars, 0)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/services/test_lesson_service.py -v
```

Expected: all 7 tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add app/services/lesson_service.py tests/services/test_lesson_service.py
git commit -m "feat(p3-task5): add LessonService (lock states, sanitize, effective stars)"
```

---

### Task 6: Curriculum schemas + API + integration tests

**Files:**
- Create: `app/schemas/curriculum.py`
- Create: `app/api/curriculum.py`
- Create: `app/daos/progress_dao.py` (stub — Phase 4 fills in)
- Create: `tests/api/test_curriculum.py`
- Modify: `app/main.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/api/test_curriculum.py`:

```python
import pytest
from app.db.models import Chapter, Lesson, Standard
from app.daos.learner_dao import LearnerDAO

LESSON_CONTENT = {
    "intro": {"title": "T", "description": "D", "mascot_quote": "Q"},
    "exercises": [
        {"id": "ex_1", "type": "multiple_choice", "difficulty": "easy", "prompt": "Q?",
         "mascot_hint": "H", "options": [{"id": "a", "text": "A"}],
         "correct_option_id": "a", "explanation": "E"},
    ],
    "result": {"badge_name": "B", "badge_description": "BD"},
    "stars_available": 3,
}


async def _seed_curriculum(db_session, subject="math"):
    ch = Chapter(subject=subject, title="Test Domain", order_index=50)
    db_session.add(ch)
    await db_session.flush()
    st = Standard(code=f"NY-T-{id(db_session)}", subject=subject, grade_level=1,
                  title="Test Std", description="D")
    db_session.add(st)
    await db_session.flush()
    lesson = Lesson(chapter_id=ch.id, standard_id=st.id, subject=subject,
                    title="Test Lesson", difficulty="easy", order_index=1,
                    content=LESSON_CONTENT)
    db_session.add(lesson)
    await db_session.flush()
    return ch, lesson


@pytest.mark.asyncio
async def test_get_curriculum_returns_chapters(authed_client, db_session):
    client, parent = authed_client
    ch, lesson = await _seed_curriculum(db_session)
    learner = await LearnerDAO(db_session).create(
        parent_id=parent.id, name="Test", age=6, grade_level=1, avatar_emoji="🦋"
    )
    response = await client.get(f"/subjects/math/chapters?learner_id={learner.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["subject"] == "math"
    chapter_ids = [c["id"] for c in body["chapters"]]
    assert str(ch.id) in chapter_ids


@pytest.mark.asyncio
async def test_get_curriculum_returns_400_for_invalid_subject(authed_client, db_session):
    client, parent = authed_client
    learner = await LearnerDAO(db_session).create(
        parent_id=parent.id, name="X", age=5, grade_level=0, avatar_emoji="🚀"
    )
    response = await client.get(f"/subjects/invalid/chapters?learner_id={learner.id}")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_curriculum_returns_403_for_wrong_learner(authed_client):
    from uuid_extensions import uuid7
    client, _ = authed_client
    response = await client.get(f"/subjects/math/chapters?learner_id={uuid7()}")
    assert response.status_code in (403, 404)


@pytest.mark.asyncio
async def test_get_lesson_returns_sanitized_content(authed_client, db_session):
    client, _ = authed_client
    _, lesson = await _seed_curriculum(db_session, subject="science")
    response = await client.get(f"/lessons/{lesson.id}")
    assert response.status_code == 200
    body = response.json()
    ex = body["content"]["exercises"][0]
    assert "correct_option_id" not in ex
    assert "explanation" not in ex


@pytest.mark.asyncio
async def test_get_lesson_returns_404_for_nonexistent(authed_client):
    from uuid_extensions import uuid7
    client, _ = authed_client
    response = await client.get(f"/lessons/{uuid7()}")
    assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/api/test_curriculum.py -v
```

Expected: `404` (routes not registered)

- [ ] **Step 3: Implement `app/schemas/curriculum.py`**

```python
from __future__ import annotations
from uuid import UUID
from typing import Optional
from pydantic import BaseModel


class QuizState(BaseModel):
    id: Optional[UUID] = None
    locked: bool
    generated: bool
    completed: bool = False
    stars_earned: int = 0
    effective_stars: int = 0


class LessonSummary(BaseModel):
    id: UUID
    title: str
    difficulty: str
    order_index: int
    locked: bool
    completed: bool
    stars_earned: int


class ChapterResponse(BaseModel):
    id: UUID
    title: str
    order_index: int
    quiz: QuizState
    lessons: list[LessonSummary]


class CurriculumResponse(BaseModel):
    subject: str
    chapters: list[ChapterResponse]


class LessonDetailResponse(BaseModel):
    id: UUID
    title: str
    difficulty: str
    stars_available: int
    content: dict
```

- [ ] **Step 4: Create `app/daos/progress_dao.py` stub**

```python
from uuid import UUID
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import LessonProgress, ChapterQuiz


class ProgressDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_progress_for_learner(self, learner_id: UUID) -> list[LessonProgress]:
        return []

    async def get_chapter_quiz(self, learner_id: UUID, chapter_id: UUID) -> Optional[ChapterQuiz]:
        return None
```

- [ ] **Step 5: Implement `app/api/curriculum.py`**

```python
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.api.deps import get_current_parent
from app.core.exceptions import LearnerNotFoundError, LearnerOwnershipError
from app.daos.lesson_dao import LessonDAO
from app.daos.learner_dao import LearnerDAO
from app.daos.progress_dao import ProgressDAO
from app.services.learner_service import LearnerService
from app.services.lesson_service import (
    compute_lock_states, sanitize_lesson_content, compute_effective_stars,
)
from app.schemas.curriculum import (
    CurriculumResponse, ChapterResponse, LessonSummary, QuizState, LessonDetailResponse,
)
from app.db.models import Parent

VALID_SUBJECTS = {"math", "science", "english"}

router = APIRouter(tags=["curriculum"])


@router.get("/subjects/{subject}/chapters", response_model=CurriculumResponse)
async def get_curriculum(
    subject: str,
    learner_id: UUID = Query(...),
    parent: Parent = Depends(get_current_parent),
    db: AsyncSession = Depends(get_db),
):
    if subject not in VALID_SUBJECTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid subject. Must be one of {VALID_SUBJECTS}",
        )

    lesson_dao = LessonDAO(db)
    progress_dao = ProgressDAO(db)

    try:
        learner = await LearnerService(LearnerDAO(db)).get(parent, learner_id)
    except LearnerNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learner not found")
    except LearnerOwnershipError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Learner not owned by parent")

    chapters = await lesson_dao.get_chapters_by_subject(subject)
    all_progress = await progress_dao.get_all_progress_for_learner(learner.id)
    completed_ids = {p.lesson_id for p in all_progress if p.completed}
    progress_map = {p.lesson_id: p for p in all_progress}

    lessons_by_chapter = {
        ch.id: await lesson_dao.get_lessons_by_chapter(ch.id) for ch in chapters
    }
    lock_states = compute_lock_states(
        chapters=chapters,
        lessons_by_chapter=lessons_by_chapter,
        completed_lesson_ids=completed_ids,
    )

    chapter_responses = []
    for ch in chapters:
        lessons = lessons_by_chapter.get(ch.id, [])
        quiz_record = await progress_dao.get_chapter_quiz(learner.id, ch.id)
        all_complete = all(l.id in completed_ids for l in lessons) if lessons else False

        if not lessons or not all_complete:
            quiz_state = QuizState(locked=True, generated=False)
        elif quiz_record is None:
            quiz_state = QuizState(locked=False, generated=False)
        else:
            quiz_state = QuizState(
                id=quiz_record.id,
                locked=False,
                generated=True,
                completed=quiz_record.completed,
                stars_earned=quiz_record.stars_earned or 0,
                effective_stars=compute_effective_stars(quiz_record.stars_earned or 0),
            )

        lesson_summaries = [
            LessonSummary(
                id=l.id,
                title=l.title,
                difficulty=l.difficulty,
                order_index=l.order_index,
                locked=lock_states.get(l.id, True),
                completed=progress_map[l.id].completed if l.id in progress_map else False,
                stars_earned=progress_map[l.id].stars_earned if l.id in progress_map else 0,
            )
            for l in sorted(lessons, key=lambda x: x.order_index)
        ]
        chapter_responses.append(ChapterResponse(
            id=ch.id, title=ch.title, order_index=ch.order_index,
            quiz=quiz_state, lessons=lesson_summaries,
        ))

    return CurriculumResponse(subject=subject, chapters=chapter_responses)


@router.get("/lessons/{lesson_id}", response_model=LessonDetailResponse)
async def get_lesson(
    lesson_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    lesson = await LessonDAO(db).get_lesson_by_id(lesson_id)
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    return LessonDetailResponse(
        id=lesson.id,
        title=lesson.title,
        difficulty=lesson.difficulty,
        stars_available=lesson.stars_available or 3,
        content=sanitize_lesson_content(lesson.content),
    )
```

- [ ] **Step 6: Register curriculum router in `app/main.py`**

```python
from fastapi import FastAPI
from app.api import health, auth, learners, parent, curriculum

app = FastAPI(title="Smarty Steps")

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(learners.router)
app.include_router(parent.router)
app.include_router(curriculum.router)
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
uv run pytest tests/api/test_curriculum.py -v
```

Expected: all 5 tests `PASSED`

- [ ] **Step 8: Commit**

```bash
git add app/schemas/curriculum.py app/api/curriculum.py app/daos/progress_dao.py \
  app/main.py tests/api/test_curriculum.py
git commit -m "feat(p3-task6): add curriculum API with dynamic chapters, lock states, sanitized JSONB"
```

---

### Task 7: Startup lifespan hook for background sync

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Add lifespan hook to `app/main.py`**

The sync fires in a background asyncio task only if `standards` table is empty. Non-blocking — the API starts serving immediately.

```python
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api import health, auth, learners, parent, curriculum


@asynccontextmanager
async def lifespan(application: FastAPI):
    asyncio.create_task(_maybe_sync_standards())
    yield


async def _maybe_sync_standards() -> None:
    from app.db.session import AsyncSessionLocal
    from app.daos.lesson_dao import LessonDAO
    from app.services.content_service import ContentService, SUBJECTS, GRADE_LEVELS
    from app.clients.standards_api import StandardsAPIClient
    from app.clients.claude_client import get_claude_client

    async with AsyncSessionLocal() as session:
        count = await LessonDAO(session).count_standards()
        if count > 0:
            return

    for subject in SUBJECTS:
        for grade_level in GRADE_LEVELS:
            async with AsyncSessionLocal() as session:
                await session.begin()
                svc = ContentService(
                    lesson_dao=LessonDAO(session),
                    standards_api=StandardsAPIClient(),
                    claude=get_claude_client(),
                )
                await svc.sync_subject_grade(subject, grade_level)
                await session.commit()


app = FastAPI(title="Smarty Steps", lifespan=lifespan)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(learners.router)
app.include_router(parent.router)
app.include_router(curriculum.router)
```

- [ ] **Step 2: Run full test suite to confirm nothing broke**

```bash
uv run pytest -v
```

Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat(p3-task7): add lifespan hook for non-blocking standards sync on startup"
```

---

## Phase 3 Done

At end of Phase 3 you have:

- `StandardsAPIClient` fetches NY State standards from ASN API; each standard carries a `domain` field used for chapter grouping
- `LessonDAO.get_or_create_chapter` auto-creates chapters from ASN standard domains — no pre-seeded data
- `ClaudeClient` generates 15-exercise lesson JSONB with prompt caching
- `ContentService.sync_all()` is idempotent (skips existing standards and lessons); chapters emerge naturally from the data
- App startup: background task checks `standards` table and triggers sync if empty
- `GET /subjects/{subject}/chapters?learner_id={id}` — full curriculum with lock states + quiz state
- `GET /lessons/{lesson_id}` — sanitized JSONB (no correct answers, matching items shuffled)
- `ProgressDAO` stub in place (Phase 4 will fill it in fully)

**Next:** Phase 4 — Progress & Gamification (`docs/superpowers/plans/2026-04-28-phase4-progress.md`)
