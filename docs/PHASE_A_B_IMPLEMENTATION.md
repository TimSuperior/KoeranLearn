# Phase A/B Implementation Notes

## Architecture Summary

The stack remains Telegram-first:

- `apps/bot`: aiogram bot with localized lightweight commands and Mini App deep links.
- `apps/api`: FastAPI, SQLAlchemy, Alembic, structured JSON logging, session auth, scenario/dialogue services, admin CMS APIs.
- `apps/web`: React/Vite/Tailwind Telegram Mini App with authenticated API client, scenario/dialogue player, settings editor, exercise renderer registry, and admin CMS starter.
- PostgreSQL is the production database; SQLite remains suitable for local dev and tests.

## Phase Plan

Phase A:

- Bot commands have distinct handlers for lesson, dialogue, quiz, plan, streak, review, mistakes, grammar, words, progress, premium, help, and settings.
- Scenarios/dialogues are delivered through `Scenario`, `Dialogue`, `UserScenarioProgress`, and `UserBookmark`.
- Content CRUD is handled by generic admin content endpoints for paths, courses, modules, lessons, blocks, exercises, options, vocabulary, grammar, examples, scenarios, dialogues, dialogue lines, and localization.
- Localization entries are namespaced and exposed as bundles with RU/UZ/EN fallback.
- Exercises now use backend evaluator strategies and frontend type-specific renderers.
- Seed expansion produces at least 30 lessons, 250 exercises, 400 vocabulary/phrase items, 80 grammar units, 50 scenarios/dialogues, and 300 examples.

Phase B:

- Telegram Mini App init data is verified once; the API issues access tokens plus HttpOnly refresh sessions.
- User endpoints derive identity from auth context or trusted internal bot headers.
- Admin uses role-based login sessions, not static bearer tokens.
- Alembic owns schema lifecycle.
- JSON logs include request IDs and central error handling.
- PostgreSQL backup/restore scripts and a Compose `backup` profile are included.

## Main Repo Changes

New files:

- `apps/api/alembic/*`
- `apps/api/app/core/logging.py`
- `apps/api/app/routers/admin_content.py`
- `apps/api/app/routers/learning.py`
- `apps/api/app/routers/localization.py`
- `apps/api/app/routers/scenarios.py`
- `apps/api/app/routers/settings.py`
- `apps/api/app/services/exercise_evaluator.py`
- `apps/api/app/services/localization.py`
- `apps/api/app/services/scenario_service.py`
- `apps/api/app/content/expanded.py`
- `apps/web/src/components/ErrorBoundary.tsx`
- `apps/web/src/components/exercises/ExerciseRenderer.tsx`
- `apps/web/src/screens/ScenariosScreen.tsx`
- `scripts/backup_postgres.sh`
- `scripts/restore_postgres.sh`
- `docs/BACKUP.md`

Modified files:

- API models, schemas, auth, admin, lessons, review, reminders, writing, premium, main startup.
- Bot API client, handlers, keyboards, localized text.
- Mini App API client, Shell navigation, LessonPlayer, Settings, Admin, Home, App routing.
- Docker Compose, `.env.example`, API requirements.

Deprecated/remove:

- Static admin bearer token as the primary admin auth path.
- Public user endpoint behavior that trusted arbitrary `telegram_id`.
- Generic equality-only exercise validation.
- `create_all` as the default schema lifecycle.

## Database Model Plan

Added/extended:

- `auth_sessions`: persisted refresh sessions for user/admin.
- `admin_users.password_hash`, `last_login_at`: role-based admin auth.
- `users.role`: user/admin-capable subject model.
- `lesson_blocks`: editable lesson content blocks.
- Content status fields: `status`, `is_deleted`, `objectives`, `answer_validation`.
- Scenario metadata: roles, target vocab/grammar IDs, tags, audience languages, ordering.
- `dialogue_lines`: normalized editable dialogue lines while keeping JSON `Dialogue.lines` for compatibility.
- `user_scenario_progress`: start/continue/complete state.
- `user_bookmarks`: favorites/bookmarks.
- `admin_audit_logs`: mutation audit trail.

## Alembic Migration Plan

- `apps/api/alembic/versions/0001_initial_schema.py` is the baseline migration.
- Docker Compose runs `alembic upgrade head` before starting the API.
- Startup no longer calls `create_all` unless `AUTO_CREATE_TABLES=true`.
- Seed data remains separate from migrations and runs only through `SEED_DEMO_DATA=true`.

Existing environments should:

1. Back up the database.
2. Run `alembic stamp head` if the current schema already matches.
3. Run future additive migrations normally.

## Auth/Session Design

- `POST /api/auth/telegram-webapp` verifies Telegram init data and returns a short-lived access token.
- Refresh token is stored in `auth_sessions` as an HMAC hash and sent as an HttpOnly cookie.
- `POST /api/auth/refresh` rotates access credentials from the refresh cookie.
- `POST /api/auth/logout` revokes the refresh session.
- User endpoints use `get_current_user_or_internal`.
- The bot uses `X-Internal-Token` plus `X-Telegram-Id`; public clients cannot use raw IDs without auth.

## Admin Auth Design

- `POST /api/auth/admin/login` checks `AdminUser.password_hash` and issues an admin access token.
- First admin can be bootstrapped from `ADMIN_EMAIL` and `ADMIN_PASSWORD`.
- Admin APIs depend on `get_current_admin`.
- CMS mutations write `admin_audit_logs`.

## Logging/Error Monitoring

- Backend logs are JSON to stdout.
- `RequestContextMiddleware` adds `x-request-id`, duration, status, method, and path.
- Central exception handler returns request ID.
- Frontend `ErrorBoundary` captures render errors and posts a client error analytics event.
- Sentry is reserved behind `SENTRY_DSN`; dependency is not installed yet.

## Backup Design

- `scripts/backup_postgres.sh`: `pg_dump --format custom`.
- `scripts/restore_postgres.sh`: `pg_restore --clean --if-exists`.
- Compose profile: `docker compose --profile ops run --rm backup`.
- Retention is controlled by `BACKUP_RETENTION_DAYS`.
- S3-compatible sync can be layered with `S3_BACKUP_*`.

## API Endpoint Additions

- Auth: `/api/auth/telegram-webapp`, `/refresh`, `/logout`, `/me`, `/admin/login`, `/admin/me`.
- Scenarios: `/api/scenarios`, `/api/scenarios/{id_or_slug}`, `/start`, `/complete`, `/favorite`, `/api/dialogues/{id}`.
- Learning: `/api/plan/current`, `/api/paths/{id}/switch`, `/api/streak`, `/api/quiz/start`.
- Settings: `/api/settings`.
- Localization: `/api/localization/bundle`, `/entries`, `/missing`.
- Admin CMS: `/api/admin/content/{entity}`, `/{id}`, `/duplicate`, `/publish`, `/unpublish`, `/export/json`, `/import/json`.

## Bot Command Spec

- `/start`: onboard or resolve deep link.
- `/menu`: localized command menu and Mini App.
- `/lesson`: continue current lesson.
- `/dialogue`: browse scenario topics and deep-link Mini App scenarios.
- `/quiz`: starts a short mixed quiz preview and opens Mini App for richer UX.
- `/plan`: current path/module/next lesson summary.
- `/streak`: streak, XP, due reviews, next milestone.
- `/review`: due SRS review.
- `/mistakes`: mistake-only review.
- `/grammar`: localized grammar preview.
- `/words`: localized vocabulary preview.
- `/progress`: XP, streak, completed lessons, due reviews, next lesson.
- `/premium`: premium catalog.
- `/help`: command list.
- `/settings`: reminder summary and settings deep link.

Callback payloads are namespaced and stable:

- `onb:lang:{ru|uz|en}`
- `onb:goal:{goal_slug}`
- `onb:level:{level_slug}`
- `onb:time:{minutes}`
- `onb:style:{style_slug}`
- `ans:{exercise_id}:{lesson_id}:{answer_value}`
- `rev:{review_item_id}:{is_correct}:{quality}`
- `scenario:topic:{topic_slug}`
- `settings:language`
- `action:lesson`

## Mini App Screen Spec

- `home`: dashboard plus dialogue entry.
- `learn`: lesson player with consistent progress and exercise rendering.
- `scenarios`: topic filters, scenario cards, dialogue stepper, translation reveal, useful expressions, completion.
- `settings`: language, reminders, learning style, difficulty.
- `admin`: admin login plus JSON CMS editor and duplicate/save.

## Admin CMS Spec

CMS supports list/search/filter, create/update/delete through API, duplicate, publish/unpublish, import/export, preview via existing lesson preview, status fields, soft delete when supported, and audit logging. Frontend starter exposes entity list, JSON editing, save, and duplicate. Rich per-entity forms can be layered over the same endpoints.

## Content Schema Spec

Canonical Korean content stays in Korean fields. RU/UZ/EN are stored as localized JSON maps for explanation/UI layers. Publish guardrails require localized fields, lesson objectives, exercise answer keys, and dialogue lines.

## Localization Spec

Keys are namespaced: `bot.menu`, `web.scenarios`, `admin.content`. `LocalizationService` loads bundles, normalizes language codes, and falls back to English. Admin missing-key detection is available at `/api/localization/missing`.

## Exercise Spec

Backend strategies:

- `one_of`
- `ordered_list`
- `unordered_pairs`
- `contains`
- `exact`

Frontend renderers cover multiple choice, fill blank, sentence reorder, match pairs, choose particle, choose verb ending, translation selection, dialogue continuation, reading comprehension, true/false, and flashcard review.

## Local Run

```bash
cp .env.example .env
docker compose up --build
```

Local API:

```bash
cd apps/api
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Local web:

```bash
cd apps/web
npm install
npm run dev
```

Backup:

```bash
docker compose --profile ops run --rm backup
```

## Assumptions and Risks

- The initial Alembic baseline creates the upgraded schema for fresh environments; existing non-empty databases should be stamped or migrated with a hand-authored additive migration.
- The admin CMS frontend is a production-capable JSON editor starter, not final polished per-entity forms.
- Telegram bot command UX remains intentionally short; richer flows are pushed to Mini App routes.
- Voice, TTS, transcription, pronunciation scoring, and speech recognition are intentionally excluded.
