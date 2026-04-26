# Smarty Steps Backend

Backend code repo for the Smarty Steps learning app.

## Rules

- Keep context window usage under 60%. Use `/compact` or suggest starting a new conversation before reaching that threshold.
- Always invoke the `superpowers:using-superpowers` skill at the start of every new conversation.
- Always invoke the `superpowers:test-driven-development` skill before writing any implementation code.
- Always separate code into three layers: **API (routers)** → **Service (business logic)** → **DB (DAOs)**. No business logic in routers. No DB calls in routers. Services never import FastAPI. DAOs never contain business logic.

## Architecture

```
app/
  api/          # FastAPI routers — HTTP only, no logic
  services/     # Business logic — no FastAPI, no SQLAlchemy queries
  daos/         # SQLAlchemy queries — no logic (Data Access Objects)
  models/       # SQLAlchemy ORM models
  schemas/      # Pydantic request/response schemas
```
