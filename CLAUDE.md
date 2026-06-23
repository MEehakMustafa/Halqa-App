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
```

API docs available at `/docs` (Swagger UI) and `/redoc` when the server is running. The `/login` endpoint uses OAuth2 password form (`username` field = email).

## Architecture

```
main.py              — FastAPI app setup, includes routers
database.py          — SQLAlchemy engine, SessionLocal, Base, get_db dependency
routers/users.py     — all user routes (register, login, me, users) via APIRouter
models/user.py       — SQLAlchemy ORM models
schemas/user.py      — Pydantic request/response schemas
core/config.py       — loads env vars from .env via python-dotenv
core/auth.py         — password hashing (passlib/bcrypt) and JWT (python-jose)
```

Tables are auto-created via `Base.metadata.create_all()` in `main.py`. No Alembic migrations yet.

Package `__init__.py` files in `models/` and `schemas/` re-export their classes for convenience imports.

## Dependencies

No `requirements.txt` or `pyproject.toml` — dependencies live only in the venv. Key packages: fastapi, uvicorn, sqlalchemy, psycopg2-binary, python-jose, passlib, bcrypt, python-dotenv, pydantic.

## Code Conventions

- Pydantic `BaseModel` for all request/response schemas
- Modern Python union syntax (`dict | None`, not `Optional[dict]`)
- Separate request models from response models (e.g., `UserCreate` vs `UserResponse`) to avoid exposing sensitive fields
- `from_attributes = True` on response models for ORM compatibility
