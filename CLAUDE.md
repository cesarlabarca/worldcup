# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

World Cup 2026 Predictions Web Application — users register, submit match score predictions, earn points based on accuracy, and compete on a leaderboard. Admins lock matches, confirm knockout-stage team assignments, and enter final scores (which triggers automatic point calculation).

## Development Setup

```bash
# Install dependencies
pip install -r requirements.txt
# or
uv sync

# Populate initial tournament data (run once)
python scripts/load_teams.py
python scripts/load_matches.py

# Start dev server
python -m uvicorn main:app --reload
# App runs at http://localhost:8000
```

## Environment Configuration

`.env` controls the database backend:

```
DB_TYPE=sqlite          # use SQLite locally
SECRET_KEY=changethis   # JWT signing key
```

For PostgreSQL (production), set `DATABASE_URL` to a connection string. The app auto-detects it and switches backends via `db.py`.

## Architecture

### Request flow

- **HTML pages** are served by `routes/frontend.py` — these are the primary user-facing routes (`/`, `/login`, `/register`, `/my-predictions`, `/leaderboard`, `/standings`).
- **JSON API** lives under `/api/*` — auth (`routes/auth.py`), predictions (`routes/predictions.py`), admin operations (`routes/admin.py`), and match/leaderboard data (`main.py`).
- Auth is **cookie-based** for browser sessions (httponly cookie holding the JWT). The same JWT is accepted as a Bearer token for direct API use.

### Database abstraction (`db.py`)

`PostgresWrapper` wraps psycopg2 to expose the same interface as sqlite3, including auto-conversion of `?` placeholders to `%s`. All route handlers call `get_db()`, which returns the right connection based on `DATABASE_URL` presence.

Schema files: `schema_sqlite.sql` (SQLite) and `schema_postgres.sql` (PostgreSQL). Tables: `teams`, `matches`, `users`, `predictions`.

### Point calculation

Triggered in `routes/admin.py` when an admin submits final scores:
- **3 pts** — exact score match
- **1 pt** — correct winner or correct goal difference
- **0 pts** — otherwise

### Admin workflow

1. Lock a match (`/api/admin/lock`) — prevents new predictions
2. Confirm knockout teams (`/api/admin/confirm-match`) — assigns teams to placeholder slots
3. Enter final score (`/api/admin/result`) — calculates and stores points

## No Test Suite

There are no tests currently. To add them, use `pytest` with FastAPI's `TestClient` and a separate test SQLite database.

## Deployment

`Procfile` targets Heroku/Render:
```
uvicorn main:app --host 0.0.0.0 --port $PORT
```
Set `DATABASE_URL` and `SECRET_KEY` as environment variables in production.
