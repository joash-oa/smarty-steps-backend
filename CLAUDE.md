# Smarty Steps Backend

Backend for Smarty Steps, a learning app for 5–8 year olds covering Math, Science, and English.

## Rules

- Keep context window usage under 60%. Use `/compact` or suggest starting a new conversation before reaching that threshold.
- Always invoke the `superpowers:using-superpowers` skill at the start of every new conversation.
- Always invoke the `superpowers:test-driven-development` skill before writing any implementation code.
- Always separate code into three layers: **API (routers)** → **Service (business logic)** → **DAOs**. No business logic in routers. No DB calls in routers. Services never import FastAPI. DAOs never contain business logic.
- Each task from an implementation plan gets its own branch (e.g. `feat/task-5-conftest`). Never bundle multiple tasks onto one branch.

## Project Structure

```
app/
  api/          # FastAPI routers — HTTP only, no logic
  services/     # Business logic — no FastAPI, no SQLAlchemy queries
  daos/         # Data Access Objects — sole interface to PostgreSQL, no logic
  db/           # SQLAlchemy ORM models (entities) and DB session
  schemas/      # Pydantic request/response schemas
  clients/      # External service clients (Cognito, Claude API)
  core/         # Config, settings
tests/
  api/          # httpx.AsyncClient integration tests
  services/     # Unit tests (mock DAOs)
  daos/         # Integration tests (real test DB)
```

## Stack

- Python + FastAPI
- PostgreSQL (Amazon RDS) — JSONB for lesson/quiz content
- SQLAlchemy + Alembic — all PKs use `uuid7()` via `pg_uuidv7` extension
- AWS Cognito — parent auth, JWT issuance
- EC2 + Docker Compose — compute
- Claude (Anthropic API) — lesson and chapter quiz content generation

## Key Design Decisions

- **Learner auth**: no separate learner accounts — all learner requests use parent Cognito JWT + `learner_id` path param. `LearnerService` verifies ownership on every request.
- **Server-side grading**: correct answers stored in DB JSONB, never sent to client. Sanitized JSONB served to client. `check-answer` endpoints grade per-exercise stateless.
- **Curriculum structure**: chapters auto-created from standard domains fetched from Common Standards/ASN API. One standard = one lesson. 15 exercises per lesson.
- **Content generation**: on startup, if `standards` table is empty → background sync (non-blocking). Standards → Claude → lesson JSONB (15 exercises, mixed types, varying difficulty).
- **Chapter quizzes**: per-learner, LLM-generated after chapter completion. Difficulty set from learner's avg stars. Star multiplier on submission (3★→×2, 2★→×1.5, 1★→×1).
- **Replay**: best-score upsert only. Learner totals updated by delta. Negative delta = no update.
- **Lesson locking**: linear within chapter, chapter boundary locked until all previous chapter lessons complete.

## Design Spec

Full spec: `docs/superpowers/specs/2026-04-25-smarty-steps-backend-design.md`
