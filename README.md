# KoreanLearn Telegram Platform

Telegram-first Korean learning system for Russian, Uzbek, and English speakers.

This starter monorepo includes:

- FastAPI backend API with SQLAlchemy models, seed content, onboarding, lessons, reviews, writing correction fallback, premium checks, reminders, analytics, and admin endpoints.
- Aiogram Telegram bot for short lesson/review flows.
- Docker Compose setup for API, bot, PostgreSQL, Redis, and reminder worker.
- Product/architecture documentation in `docs/ARCHITECTURE.md`.

## Quick Start

1. Copy environment settings:

```bash
cp .env.example .env
```

2. Set at minimum:

```bash
TELEGRAM_BOT_TOKEN=123456:replace-me
BOT_ADMIN_TELEGRAM_IDS=123456789
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=change-me
INTERNAL_SERVICE_TOKEN=change-me
```

3. Run the stack:

```bash
docker compose up --build
```

4. Open:

- API: http://localhost:8000/docs
- Health: http://localhost:8000/health

For local backend development outside Docker:

```bash
cd apps/api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Demo Behavior

On backend startup, demo content is seeded automatically when `SEED_DEMO_DATA=true`.

The demo path supports:

- Telegram-style onboarding for RU/UZ/EN users.
- Lesson continuation and exercise submission.
- SRS review queue creation and future scheduling.
- Grammar/vocab libraries with localized explanations.
- Text-only writing correction with deterministic checks and AI-ready interface.
- Premium access locking through backend entitlement checks.
- Reminder records and a worker loop that can send Telegram reminders if a bot token is configured.
- Role-based admin CMS APIs.
- Phase A/B upgrade notes in `docs/PHASE_A_B_IMPLEMENTATION.md`.
- Phase C content operations notes in `docs/PHASE_C_IMPLEMENTATION.md`.
- Backup and restore runbook in `docs/BACKUP.md`.

See `docs/ARCHITECTURE.md` for the detailed product architecture, schema, API, UX flows, analytics, roadmap, testing, deployment, and content format.

## Migrations

The API now uses Alembic:

```bash
cd apps/api
alembic upgrade head
```

Docker Compose runs migrations before starting the API. `AUTO_CREATE_TABLES=true` is only a local escape hatch.

## Admin Login

Set:

```bash
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=replace-me
INTERNAL_SERVICE_TOKEN=replace-me
```

The first admin login bootstraps an owner account when no `admin_users` exist.
