# KoreanLearn Architecture

## 1. Architecture Overview

Assumptions:

- Telegram is the primary identity provider. The backend stores Telegram users and verifies Mini App init data.
- The first production deployment is a single VPS or small cloud deployment using Docker Compose, PostgreSQL, Redis, API, bot, worker, and static web serving.
- AI features are bounded services behind deterministic validation, rate limits, moderation, and fallbacks. AI does not replace the curriculum.
- Starter code includes representative seed content and generators; a real production launch should expand the content catalog through the admin tools.

Text architecture diagram:

```text
Telegram User
  | /start, commands, reminders
  v
Telegram Bot (aiogram)
  | REST API calls
  v
FastAPI Backend API
  |-- User Service
  |-- Curriculum Service
  |-- Lesson Engine
  |-- Review / SRS Engine
  |-- Exercise Service
  |-- AI Personalization Service
  |-- Localization Service
  |-- Gamification Service
  |-- Notifications / Reminder Service
  |-- Billing / Premium Access Service
  |-- Analytics Service
  |-- Admin Content Service
  |
  | SQLAlchemy
  v
PostgreSQL

FastAPI Backend API <--> Redis
  |                cache, rate limits, job coordination
  v
Reminder Worker
  | Telegram Bot API sendMessage
  v
Telegram

Telegram Mini App (React + Vite + Tailwind)
  | Telegram WebApp init data
  | REST API
  v
FastAPI Backend API

Admin UI (React route /admin)
  | Bearer admin token
  v
Admin Content API

Analytics events
  | local analytics_events table now
  | optional PostHog export later
  v
Analytics Dashboard
```

Service boundaries:

- User Service: Telegram identity, profile, onboarding, goals, preferences, locale.
- Curriculum Service: courses, paths, modules, prerequisites, premium/free visibility.
- Lesson Engine: lesson state, exercises, answer checking, completion.
- Review Engine: SM-2-inspired SRS, mistake queue, next review scheduling.
- Exercises Service: typed exercise rendering and scoring.
- AI Personalization Service: writing correction, adaptive explanations, generation support, guarded by deterministic checks and limits.
- Localization Service: RU/UZ/EN explanations and interface strings.
- Gamification Service: XP, streaks, daily missions, achievements.
- Notifications Service: reminders, timezone, quiet hours, weekly summary.
- Billing Service: premium entitlements and Telegram payment integration points.
- Analytics Service: normalized product events.
- Admin Content Service: protected CRUD and preview endpoints.

## 2. Repository Structure

```text
apps/
  api/
    app/
      core/          settings, db, auth, rate limiting
      models/        SQLAlchemy schema
      routers/       REST API routes
      services/      business logic
      content/       demo seed content
      main.py
      reminder_worker.py
    Dockerfile
    requirements.txt
  bot/
    bot/
      main.py
      api.py
      keyboards.py
      texts.py
    Dockerfile
    requirements.txt
  web/
    src/
      components/
      screens/
      lib/
    Dockerfile
    package.json
docs/
  ARCHITECTURE.md
docker-compose.yml
.env.example
```

## 3. Database Schema

Core user tables:

- `users`: Telegram identity, interface language, onboarding status, premium flag, XP, streak.
- `user_profiles`: level, learning style, daily minutes, timezone.
- `user_preferences`: reminders, difficulty, quiet hours, explanation language.
- `user_goals`: many goals per user.
- `reminders`: daily/review/streak/weekly reminder settings and next send time.

Curriculum/content:

- `learning_paths`: localized name/description, target goal, level, ordering.
- `user_path_progress`: selected path, current module/lesson, percent complete.
- `courses`: localized course metadata.
- `modules`: course modules with prerequisites and estimate.
- `lessons`: module lessons with localized title/explanation, difficulty, politeness, premium flag.
- `lesson_progress`: per-user lesson status.
- `exercises`: typed exercise payload, answer key, localized prompt/explanation.
- `exercise_options`: optional answer options.
- `vocabulary`: Korean text, reading, translations, topic, tags, politeness, review metadata.
- `grammar_points`: Korean grammar point, localized explanation, transfer mistakes by language.
- `dialogues`: scenario dialogue lines and localized context.
- `scenarios`: Korea-life scenario metadata.
- `example_sentences`: Korean examples with localized translations and register metadata.
- `lesson_assets`: S3-compatible audio/image asset references.
- `premium_packs`: premium catalog and content rules.

Learning state:

- `review_items`: item type/id, ease, interval, repetitions, next review date, mastery, mistake count.
- `review_history`: every review attempt.
- `writing_submissions`: text correction requests, deterministic/AI result, status.
- `achievements`: catalog.
- `user_achievements`: unlocked achievements.

Commerce/admin/analytics:

- `subscriptions`: active premium state.
- `payments`: Telegram payment records.
- `analytics_events`: event name, user, timestamp, properties.
- `admin_users`: protected admin accounts and roles.
- `localization_entries`: app/admin localization strings.

## 4. API Endpoints

Public/user API:

- `GET /health`
- `POST /api/auth/telegram-webapp`: verify Telegram Mini App init data and return session user.
- `POST /api/onboarding/start`
- `POST /api/onboarding/complete`
- `GET /api/onboarding/me/{telegram_id}`
- `GET /api/paths`
- `GET /api/lessons/continue/{telegram_id}`
- `GET /api/lessons/{lesson_id}`
- `POST /api/lessons/{lesson_id}/start`
- `POST /api/exercises/{exercise_id}/submit`
- `GET /api/review/queue/{telegram_id}`
- `POST /api/review/{review_item_id}/submit`
- `GET /api/progress/{telegram_id}`
- `GET /api/grammar`
- `GET /api/grammar/{grammar_id}`
- `GET /api/vocab`
- `POST /api/writing/correct`
- `GET /api/reminders/{telegram_id}`
- `PUT /api/reminders/{telegram_id}`
- `GET /api/premium/catalog`
- `GET /api/premium/access/{telegram_id}`
- `POST /api/analytics/events`

Bot helper API:

- Same REST surface as public API, using Telegram ID as the principal.
- Deep-link parameters are parsed in the bot and passed as `source` analytics properties.

Admin API:

- `GET /api/admin/overview`
- `GET /api/admin/lessons`
- `POST /api/admin/lessons`
- `PUT /api/admin/lessons/{lesson_id}`
- `GET /api/admin/analytics`
- `GET /api/admin/content-preview/lesson/{lesson_id}`

OpenAPI is generated by FastAPI at `/docs` and `/openapi.json`.

## 5. Telegram Bot Flows

Onboarding:

1. `/start [deep_link]`
2. Detect Telegram `language_code`.
3. Ask interface language: RU / UZ / EN.
4. Ask goal: zero, daily life, study, work/EPS, grammar, vocabulary.
5. Ask level: complete beginner, knows Hangul, knows basics.
6. Ask daily time: 5 / 10 / 20 / 30 minutes.
7. Ask learning style: grammar-first / mixed / phrase-first.
8. Create profile, select path, show "Start lesson" and "Open Mini App".

Main commands:

- `/menu`: 1-2 tap navigation.
- `/lesson`: continue next lesson.
- `/review`: due SRS queue.
- `/mistakes`: mistake-only review.
- `/grammar`: grammar topic lookup.
- `/words`: vocabulary topic lookup.
- `/dialogue`: scenario lesson.
- `/quiz`: quick quiz.
- `/progress`: progress and next action.
- `/streak`: streak and missions.
- `/plan`: path/module/lesson state.
- `/settings`: language, reminders, difficulty, goals.
- `/premium`: premium catalog and payment entry point.
- `/help`: concise help.

Deep links:

- `lesson_<id>`
- `scenario_<id>`
- `premium_<campaign_id>`
- `challenge_<id>`

## 6. Mini App Screens

- Home dashboard: current lesson, streak, review due, path progress.
- Continue learning: rich lesson and exercise player.
- Learning paths: modules, prerequisites, completion state, locked premium content.
- Review center: due items, mistakes, topic filters.
- Vocabulary bank: filters by topic/path/lesson/mastery.
- Grammar library: localized grammar cards and transfer mistakes.
- Scenario practice: Korea-life dialogues by context.
- Writing correction: text submission, corrections, register issues, natural alternative.
- Progress analytics: XP, streak, weekly activity, difficult topics.
- Challenges / achievements: daily missions and challenge weeks.
- Premium store: packs and subscription state.
- Settings: language, reminders, timezone, difficulty, goals.
- Admin: protected content list, lesson editor starter, analytics summary.

## 7. Admin Panel Screens

- Content overview: courses, modules, lessons, exercise counts.
- Lesson editor: title, content block JSON, difficulty, tags, free/premium, answer keys.
- Grammar/vocab editors: localized explanations and example sentences.
- Scenario/dialogue editor: role lines, context labels, politeness metadata.
- Asset upload placeholder: S3 references for audio.
- Preview: bot format and Mini App format.
- Campaign/challenge scheduler.
- Analytics: funnels, retention, hard topics by audience language.
- Translation management: RU/UZ/EN completeness and missing fields.

## 8. Event Tracking Schema

All events use:

```json
{
  "event_name": "lesson_completed",
  "telegram_id": "123456789",
  "audience_language": "ru",
  "properties": {
    "lesson_id": 1,
    "path_id": 1,
    "duration_seconds": 240
  },
  "created_at": "2026-04-22T09:00:00Z"
}
```

Tracked events:

- `onboarding_started`
- `onboarding_completed`
- `path_selected`
- `lesson_started`
- `lesson_completed`
- `exercise_attempted`
- `exercise_completed`
- `review_session_started`
- `review_session_completed`
- `review_answered`
- `writing_correction_requested`
- `writing_correction_completed`
- `premium_store_opened`
- `premium_checkout_started`
- `premium_purchase_completed`
- `reminder_sent`
- `streak_updated`
- `admin_content_updated`

Product metrics:

- D1/D7/D30 retention.
- Streak distribution.
- Conversion funnel by language group.
- Content completion by language group.
- Most difficult grammar topics by audience language and exercise type.

## 9. Monetization Flow

Free:

- Limited daily lessons.
- Limited review depth.
- Starter grammar library.
- Starter scenarios.
- Limited writing corrections.

Premium:

- Full curriculum.
- Advanced scenarios.
- Full grammar library.
- Deeper review modes.
- Premium challenge weeks.
- Exam/work/student packs.
- Higher writing correction quota.

Flow:

1. User opens `/premium` or Mini App store.
2. Backend returns catalog with locked/unlocked state.
3. Bot starts Telegram invoice flow or Mini App opens Telegram payment.
4. Payment webhook or successful payment command creates `payments`.
5. `subscriptions` activates entitlement.
6. Every lesson/library/review endpoint checks premium server-side.

## 10. Implementation Roadmap

Phase 1:

- Architecture, schema, onboarding, Telegram auth, bot skeleton, Mini App skeleton.
- Current starter covers this phase.

Phase 2:

- Curriculum engine, lesson engine, exercise checking, basic review engine.
- Current starter includes a functional baseline.

Phase 3:

- Grammar/vocab libraries, progress dashboard, reminders.
- Current starter includes basic APIs and UI.

Phase 4:

- Writing correction, premium model, admin content tools.
- Current starter includes deterministic correction and premium/admin foundations; AI/payment providers need production integration.

Phase 5:

- Analytics, optimization, production hardening.
- Add PostHog export, Alembic migrations, load tests, CI/CD, backups, observability, and content QA workflow.

## 11. MVP Scope vs Phase 2 Scope

MVP:

- Onboarding.
- Personalized initial path.
- Bot lesson flow.
- Mini App dashboard and content browsing.
- Localized grammar/vocab content for RU/UZ/EN.
- SRS queue and mistakes.
- Writing correction fallback.
- Premium locking.
- Reminder worker.
- Admin lesson CRUD starter.

Phase 2:

- Full 100-300 vocabulary items.
- 20-40 grammar points.
- 15-20 scenarios.
- 150+ exercises.
- Richer exercise widgets.
- Robust CMS workflows.
- Telegram payments in production.
- AI provider with prompt-injection isolation and moderation.

## 12. Testing Plan

Backend:

- Unit tests for Telegram init-data verification.
- Unit tests for onboarding path selection.
- Unit tests for exercise answer checking.
- Unit tests for SRS interval updates.
- Unit tests for writing correction fallback and rate limits.
- API tests for premium lock enforcement.

Bot:

- Handler tests with mocked API client.
- Deep-link parsing tests.
- Keyboard reachability tests for core flows.

Frontend:

- Type checking.
- Component tests for dashboard, lesson player, correction form.
- Playwright smoke tests for dashboard, review, premium lock, admin route.

End-to-end:

- New user onboarding to first completed lesson.
- Lesson completion creates review items.
- Review submission reschedules item.
- Mini App auth with valid and invalid init data.
- Reminder worker sends due reminders in a test Telegram API mock.

## 13. Deployment Plan

Initial VPS/cloud:

1. Provision VPS with Docker and Docker Compose.
2. Create `.env` with production secrets.
3. Put API and Mini App behind Nginx/Caddy with HTTPS.
4. Configure Telegram bot webhook or polling. Starter uses polling for simplicity.
5. Configure Mini App URL in BotFather.
6. Run `docker compose up -d --build`.
7. Verify `/health`, `/docs`, bot `/start`, and Mini App auth.
8. Set database backups for PostgreSQL volume.
9. Add log shipping and uptime monitoring.

Production hardening:

- Replace `create_all` with Alembic migrations.
- Use managed PostgreSQL/Redis when scale requires.
- Add object storage for audio assets.
- Add CI pipeline: lint, typecheck, tests, build images.
- Add PostHog export or self-hosted analytics.
- Add admin SSO or stronger auth than static token.

## 14. Sample Lesson JSON Format

```json
{
  "slug": "hangul-greetings-001",
  "title": {
    "ru": "Первые приветствия",
    "uz": "Birinchi salomlashuvlar",
    "en": "First greetings"
  },
  "korean_text": "안녕하세요",
  "difficulty": "A0",
  "politeness_level": "polite_informal",
  "estimated_minutes": 5,
  "premium": false,
  "tags": ["hangul", "greeting", "politeness"],
  "explanation": {
    "ru": "안녕하세요 — вежливое нейтральное приветствие. В корейском уровень вежливости выбирается сразу.",
    "uz": "안녕하세요 — odobli va neytral salomlashuv. Koreys tilida hurmat darajasi darhol tanlanadi.",
    "en": "안녕하세요 is a polite neutral greeting. Korean requires choosing a politeness level from the start."
  },
  "transfer_notes": {
    "ru": ["Не переводите дословно как вопрос о здоровье."],
    "uz": ["Assalomu alaykum kabi keng ishlatiladi, lekin grammatik tuzilishi boshqa."],
    "en": ["It is not literally used like 'Are you peaceful?' in daily English."]
  },
  "exercises": [
    {
      "type": "multiple_choice_meaning",
      "prompt": {"ru": "Что значит 안녕하세요?", "uz": "안녕하세요 nimani anglatadi?", "en": "What does 안녕하세요 mean?"},
      "answer_key": {"value": "hello_polite"},
      "options": [
        {"value": "hello_polite", "label": {"ru": "Здравствуйте", "uz": "Salom (odobli)", "en": "Hello (polite)"}},
        {"value": "bye", "label": {"ru": "До свидания", "uz": "Xayr", "en": "Goodbye"}}
      ]
    }
  ]
}
```
