# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Halqa App is a FastAPI backend with JWT authentication and PostgreSQL. Python 3.14+, Windows development environment.

## Commands

```powershell
# Activate virtual environment (PowerShell)
.\venv\Scripts\Activate.ps1

# Run the dev server
uvicorn main:app --reload

# Install a new dependency
pip install <package>

# Database migrations (Alembic)
alembic revision --autogenerate -m "describe change"   # after editing models
alembic upgrade head                                   # apply to DB
alembic check                                          # verify models match DB
```

API docs available at `/docs` (Swagger UI) and `/redoc` when the server is running. The `/login` endpoint uses OAuth2 password form (`username` field = email).

## Architecture

```
main.py                — FastAPI app setup, includes routers, global exception handlers
                         (IntegrityError→409, SQLAlchemyError→500, Exception→500)
database.py            — SQLAlchemy engine, SessionLocal, Base, get_db dependency
alembic/               — migrations; env.py wires target_metadata to Base and reads
                         DATABASE_URL from .env (env var overrides .env)
routers/users.py       — user routes (register, login, me, patch me, users) via APIRouter
routers/halaqas.py     — halaqa routes (create, list public, get by id, join/leave/members,
                         create/list posts) + shared membership helpers (require_member,
                         require_can_view)
routers/posts.py       — post routes (get single post with comments, create/list comments)
routers/goals.py       — goal routes (create, my goals, patch/delete owner-only,
                         checkin/checkins/streak/stats) + streak math helpers
models/user.py         — User ORM model (incl. timezone, IANA name, default UTC)
models/halaqa.py       — Halaqa ORM model (FK to users via created_by)
models/membership.py   — Membership ORM model (user_id + halaqa_id unique, role member/admin)
models/post.py         — Post ORM model (FK halaqa_id, author_id; author_name/comment_count
                         properties for response serialization)
schemas/user.py        — UserCreate, UserResponse, Token
schemas/halaqa.py      — HalaqaCreate, HalaqaResponse
schemas/membership.py  — MemberResponse
models/comment.py      — Comment ORM model (FK post_id, author_id; flat, no nesting)
schemas/post.py        — PostCreate, PostResponse, PostDetailResponse
models/goal.py         — Goal ORM model (halaqa_id nullable = personal goal; is_private,
                         target_days optional)
schemas/comment.py     — CommentCreate, CommentResponse
models/checkin.py      — CheckIn ORM model (Date column; unique goal_id+user_id+date;
                         cascade-deleted with its Goal)
schemas/goal.py        — GoalCreate, GoalUpdate, GoalResponse
schemas/checkin.py     — CheckInCreate, CheckInResponse, StreakResponse, StatsResponse
core/config.py         — loads env vars from .env via python-dotenv
core/auth.py           — password hashing, JWT, get_current_user (+ _optional) dependencies
core/pagination.py     — PageParams dependency + paginate(); every list endpoint takes
                         ?page=1&limit=20 (limit max 100)
core/dates.py          — user_today (today in the user's timezone), is_valid_timezone;
                         all check-in/streak "today" math uses the goal owner's timezone,
                         never the server clock
```

ALL schema changes go through Alembic — never manual ALTER TABLE or `create_all` (removed from `main.py`). Workflow: edit models → `alembic revision --autogenerate -m "..."` → review the generated script → `alembic upgrade head`. New model modules must be imported by `models/__init__.py` so autogenerate sees them. Baseline revision: `29bb7452f172`.

Package `__init__.py` files in `models/` and `schemas/` re-export their classes for convenience imports. `get_current_user` lives in `core/auth.py` and is shared by both routers.

## Dependencies

`requirements.txt` is generated via `pip freeze` — regenerate after installing anything. Key packages: fastapi, uvicorn, sqlalchemy, alembic, psycopg2-binary, python-jose, passlib, bcrypt, python-multipart, python-dotenv, pydantic, tzdata (required for zoneinfo on Windows), httpx2 (tests only).

All timestamp columns are `DateTime(timezone=True)`; the engine forces `timezone=utc` per session so API responses serialize datetimes with a trailing `Z`.

## Code Conventions

- Pydantic `BaseModel` for all request/response schemas
- Modern Python union syntax (`dict | None`, not `Optional[dict]`)
- Separate request models from response models (e.g., `UserCreate` vs `UserResponse`) to avoid exposing sensitive fields
- `from_attributes = True` on response models for ORM compatibility
