# Halqa App — Backend

A spiritual social network for Muslims, stripped of everything toxic about social media: no DMs, no follower counts, no viral feed, no likes. Users gather in **halaqas** (circles), share posts and reflections, set spiritual **goals**, and build **streaks** through daily check-ins.

**Stack:** FastAPI · PostgreSQL · SQLAlchemy · Alembic · JWT (python-jose) · Pydantic v2

## Setup

```powershell
# 1. Activate the virtual environment
.\venv\Scripts\Activate.ps1

# 2. Create .env with:
#    DATABASE_URL=postgresql://user:pass@localhost/halqa_db
#    SECRET_KEY=<random string>
#    ALGORITHM=HS256
#    ACCESS_TOKEN_EXPIRE_MINUTES=30

# 3. Apply database migrations
alembic upgrade head

# 4. Run the dev server
uvicorn main:app --reload
```

Interactive API docs: `http://127.0.0.1:8000/docs` (Swagger) or `/redoc`.

## Conventions

- **Auth**: `POST /login` uses the OAuth2 password form — put your **email** in the `username` field. Send the returned token as `Authorization: Bearer <token>`. 🔒 = auth required, 🔓 = optional (needed only for private-halaqa content).
- **Pagination**: every list endpoint takes `?page=1&limit=20` (limit max 100). An empty list means you've paged past the end.
- **Timezones**: users have an IANA timezone (default `Asia/Karachi`). Check-in dates and streaks are computed on the goal owner's local calendar, not the server clock.
- **Errors**: every error is JSON `{"detail": "..."}` — 401 unauthenticated, 403 not allowed, 404 missing, 409 conflict, 422 validation.

## Endpoints

### Auth & Users

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/register` | — | Create account (`name`, `email`, `password`, optional `timezone`) |
| POST | `/login` | — | Get JWT (OAuth2 form, `username` = email) |
| GET | `/me` | 🔒 | Current user |
| PATCH | `/me` | 🔒 | Update own `name` / `timezone` |
| GET | `/users` | — | List users |

### Halaqas

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/halaqas/` | 🔒 | Create halaqa (creator becomes admin member) |
| GET | `/halaqas/` | — | List public halaqas |
| GET | `/halaqas/{id}` | — | Get one halaqa |
| POST | `/halaqas/{id}/join` | 🔒 | Join (400 if already a member) |
| DELETE | `/halaqas/{id}/leave` | 🔒 | Leave (400 if not a member) |
| GET | `/halaqas/{id}/members` | 🔓 | List members with names and roles |

### Posts & Comments

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/halaqas/{id}/posts` | 🔒 | Create post (members only) |
| GET | `/halaqas/{id}/posts` | 🔓 | Posts, newest first, with `author_name` + `comment_count` |
| GET | `/posts/{id}` | 🔓 | Single post with its comments |
| POST | `/posts/{id}/comments` | 🔒 | Comment (members only, flat — no nesting) |
| GET | `/posts/{id}/comments` | 🔓 | Comments, oldest first, with `author_name` |

### Goals & Check-ins

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/goals/` | 🔒 | Create goal (`halaqa_id` null = personal; must be member to share) |
| GET | `/goals/me` | 🔒 | All my goals, newest first |
| GET | `/halaqas/{id}/goals` | 🔓 | Non-private goals shared in a halaqa |
| PATCH | `/goals/{id}` | 🔒 | Update goal (owner only, partial) |
| DELETE | `/goals/{id}` | 🔒 | Delete goal + its check-ins (owner only) |
| POST | `/goals/{id}/checkin` | 🔒 | Check in (owner only, once per local calendar day) |
| GET | `/goals/{id}/checkins` | 🔓 | Check-ins, newest first |
| GET | `/goals/{id}/streak` | 🔓 | `current_streak` + `checked_in_today` (alive until end of day) |
| GET | `/goals/{id}/stats` | 🔓 | Totals, longest streak, `completion_rate` (0–1) if `target_days` set |

Visibility rules: public halaqa content is readable by anyone; private halaqas are members-only. Private goals are visible only to their owner, wherever they live.

## Migrations

All schema changes go through Alembic — never manual `ALTER TABLE`:

```powershell
alembic revision --autogenerate -m "describe change"   # after editing models
# review the generated script in alembic/versions/
alembic upgrade head
```
