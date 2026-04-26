# Phase C Implementation

## 1. Architecture Summary

Phase C turns the existing starter admin into an operational content system:

- FastAPI keeps learner APIs intact and adds a real admin content domain under `/api/admin/content`.
- SQLAlchemy models are extended only where operations required it: access governance, author/editor tracking, block/line normalization, relation tables, and import/export-safe metadata.
- Validation, preview, duplication, access resolution, and import/export all live in backend services instead of router code.
- The Mini App admin is now a list/detail CMS with dedicated editors for lessons, vocabulary, grammar, scenarios, dialogues, and exercises, plus generic managers for structure/localization/premium/tag data.
- The bot remains learner-facing and only adds admin deep link, published content preview, and shareable deep links.

## 2. Repo/File-Level Plan

### New files

- `apps/api/app/admin_schemas.py`
- `apps/api/app/services/admin_content_service.py`
- `apps/api/app/services/content_access.py`
- `apps/api/app/services/content_validation.py`
- `apps/api/alembic/versions/0003_phase_c_content_ops.py`
- `apps/web/src/admin/types.ts`
- `apps/web/src/admin/config.ts`
- `apps/web/src/admin/utils.ts`
- `docs/PHASE_C_IMPLEMENTATION.md`
- `docs/examples/phase-c-lesson-package.json`
- `docs/examples/phase-c-vocabulary.csv`
- `docs/examples/phase-c-grammar-package.json`

### Modified files

- `apps/api/app/models/schema.py`
- `apps/api/app/schemas.py`
- `apps/api/app/main.py`
- `apps/api/app/routers/admin.py`
- `apps/api/app/routers/admin_content.py`
- `apps/api/app/routers/curriculum.py`
- `apps/api/app/services/lesson_service.py`
- `apps/api/app/services/scenario_service.py`
- `apps/web/src/lib/api.ts`
- `apps/web/src/types.ts`
- `apps/web/src/components/LessonPlayer.tsx`
- `apps/web/src/screens/AdminScreen.tsx`
- `apps/web/src/screens/LearnScreen.tsx`
- `apps/web/src/screens/ScenariosScreen.tsx`
- `apps/bot/bot/api.py`
- `apps/bot/bot/keyboards.py`
- `apps/bot/bot/main.py`

## 3. Backend Route Plan

Primary Phase C admin routes:

- `GET /api/admin/content/dashboard`
- `GET /api/admin/content/options`
- `POST /api/admin/content/status/bulk`
- `POST /api/admin/content/validation/{entity}`
- `GET /api/admin/content/validation/{entity}/{id}`
- `GET /api/admin/content/preview/{entity}/{id}`
- `GET /api/admin/content/export/{entity}?format=json|csv`
- `GET /api/admin/content/templates/{entity}?format=json|csv`
- `POST /api/admin/content/import/{entity}`
- `GET /api/admin/content/{entity}`
- `POST /api/admin/content/{entity}`
- `GET /api/admin/content/{entity}/{id}`
- `PUT /api/admin/content/{entity}/{id}`
- `DELETE /api/admin/content/{entity}/{id}`
- `POST /api/admin/content/{entity}/{id}/duplicate`
- `POST /api/admin/content/{entity}/{id}/publish`
- `POST /api/admin/content/{entity}/{id}/unpublish`
- `POST /api/admin/content/{entity}/reorder`

Supported entities:

- `paths`
- `courses`
- `modules`
- `lessons`
- `lesson-blocks`
- `exercises`
- `exercise-options`
- `vocabulary`
- `grammar`
- `example-sentences`
- `scenarios`
- `dialogues`
- `dialogue-lines`
- `tags`
- `localization`
- `premium-packs`

## 4. Updated Schema/Model Plan

### Governance fields added to learner-facing content

- `access_state`
- `resolved_access_state`
- `created_by_admin_id`
- `updated_by_admin_id`

Applied to:

- `learning_paths`
- `courses`
- `modules`
- `lessons`
- `exercises`
- `vocabulary`
- `grammar_points`
- `example_sentences`
- `scenarios`
- `dialogues`

Why:

- `access_state` lets admin explicitly set `free`, `premium`, `hidden`, `internal`, or `inherit`.
- `resolved_access_state` makes learner queries operational without expensive recursive inheritance checks.
- `created_by_admin_id` and `updated_by_admin_id` make editor attribution practical without introducing a full revision system.

### Lesson metadata additions

- `cover_metadata`
- `audience_metadata`
- `prerequisite_lesson_ids`

Why:

- Supports lesson editor requirements without introducing unrelated media or versioning systems.

### Exercise metadata additions

- `instructions`
- `tags`

Why:

- Exercise authoring needs learner instructions and searchable content tags distinct from the prompt.

### Vocabulary metadata additions

- `notes`
- `variants`

Why:

- Supports synonyms/variants and editor notes in RU/UZ/EN workflows.

### Grammar metadata additions

- `usage_notes`

Why:

- Grammar authoring needed structured notes separate from transfer/common-error sections.

### Scenario/dialogue metadata additions

- `scenarios.audience_metadata`
- `dialogue_lines.reveal_mode`
- `dialogue_lines.highlighted_expressions`

Why:

- Dialogue authoring needs per-line reveal control and expression highlighting.

### Premium pack metadata additions

- `order_index`
- `status`
- `is_deleted`

Why:

- Premium packs now participate in list/detail admin management instead of being a static catalog row type.

### New tables

- `lesson_vocabulary_links`
- `lesson_grammar_links`
- `lesson_scenario_links`
- `scenario_vocabulary_links`
- `scenario_grammar_links`
- `content_tags`

Why:

- Real relation management for editor pickers and future scaling.
- `content_tags` gives admin a manageable tag registry while keeping assignment lightweight.

### Existing normalized structures now used operationally

- `lesson_blocks`
- `dialogue_lines`

Why:

- These tables already existed conceptually. Phase C makes them the active authoring surface.

## 5. Admin Screen List / UX Spec

Mini App admin now includes:

- content dashboard
- core entity managers for lessons, vocabulary, grammar, scenarios, dialogues, exercises
- example sentence manager
- structure managers for paths, courses, modules, tags, localization, premium packs
- import/export center
- preview center
- validation panel
- bulk status/access actions
- reordering controls in list view and nested editors

UX pattern:

- left pane: searchable/filterable list with selection and bulk actions
- center pane: detail editor
- right pane: preview + validation
- separate import/export mode for package workflows

## 6. Content Editor Specs

### Lesson editor

- title, slug, summary, objectives
- module assignment, difficulty, duration, tags, prerequisites
- relation pickers for vocab/grammar/scenarios
- block CRUD with ordering
- block types: explanation, vocabulary, grammar, example sentence, exercise, recap, quiz, scenario link

### Vocabulary editor

- Korean, reading, RU/UZ/EN translations
- usage notes, notes, topic, difficulty, tags
- variants/synonyms
- structured example sentence list
- relation pickers for lessons/scenarios

### Grammar editor

- grammar pattern, title, explanation, usage notes
- common mistakes by language
- alternatives, category, difficulty, tags
- relation pickers for lessons/scenarios

### Scenario editor

- title, slug, description, topic, difficulty, audience
- roles, tags, context labels
- relation pickers for lessons/vocab/grammar
- nested dialogue CRUD with ordering

### Dialogue editor

- scenario association
- title, context, explanation
- line CRUD with ordering
- line fields: speaker, Korean, RU/UZ/EN, notes, reveal mode, useful-expression flag, highlighted expressions

### Exercise editor

- type, slug, prompt, instructions, explanation
- lesson/grammar/vocab linkage
- topic, difficulty, tags
- answer-definition editors for option, reorder, pair, and text-based exercise types

## 7. Free/Premium Visibility Model

Implemented model:

- `status`: `draft | published | archived`
- `access_state`: `free | premium | hidden | internal | inherit`
- `resolved_access_state`: materialized effective state used by learner queries

Rules:

- `draft` is never learner-visible
- `archived` plus `is_deleted=true` is excluded by default
- `hidden` and `internal` are excluded from learner APIs even if published
- `premium` stays learner-visible only to entitled users
- `inherit` resolves from parent where a parent exists

Inheritance path:

- path -> course -> module -> lesson -> exercise
- scenario -> dialogue

Operational note:

- a startup sync backfills `resolved_access_state` for existing seeded content so old premium rows remain premium after the Phase C schema update

## 8. Import/Export Format Spec

### JSON package

Envelope:

```json
{
  "schema_version": "phase_c.v1",
  "entity": "lessons",
  "exported_at": "2026-04-24T12:00:00Z",
  "count": 1,
  "items": []
}
```

Item payload includes:

- base entity data
- `relation_ids`
- nested `children`
- publish/access/order metadata

### CSV support

Implemented for:

- `vocabulary`
- `grammar`

Why only these in CSV:

- they are the bulk-edit cases with stable flat enough shapes
- lessons/scenarios/dialogues are too nested for safe CSV fidelity

### Import behavior

Supported:

- dry-run validation
- apply mode
- conflict strategies: `skip`, `overwrite`, `create_new`, `merge`
- row-level error reporting
- downloadable templates

## 9. Validation / Publish Workflow Spec

Validation service:

- `app/services/content_validation.py`

Current blocking publish rules:

- lesson: title, objectives, module, at least one block
- lesson block: valid type; exercise/scenario link blocks need referenced ids
- vocabulary: Korean text and at least one learner-language translation
- grammar: Korean pattern, fully localized title, fully localized explanation
- scenario: localized title and at least one dialogue
- dialogue: scenario association and at least one line
- dialogue line: speaker + Korean text
- exercise: valid type, prompt, answer definition, and type-specific option/pair/token checks
- localization: namespace/key/language/value

Preview-before-publish:

- admin can validate current draft
- admin can preview saved content as `free` or `premium` viewer
- publish endpoint re-validates server-side before changing status

## 10. Limited Telegram Bot Support Spec

Implemented commands:

- `/admin`
- `/preview_lesson <lesson_id>`
- `/preview_scenario <scenario_id_or_slug>`
- `/share_lesson <lesson_id>`
- `/share_scenario <scenario_id_or_slug>`

Deliberately not implemented:

- content mutation in chat
- bot-side CMS editing flows

## 11. Key Code References

- admin schemas: `apps/api/app/admin_schemas.py`
- admin services: `apps/api/app/services/admin_content_service.py`
- validation: `apps/api/app/services/content_validation.py`
- access resolution: `apps/api/app/services/content_access.py`
- admin router: `apps/api/app/routers/admin_content.py`
- admin Mini App: `apps/web/src/screens/AdminScreen.tsx`
- admin client types: `apps/web/src/admin/types.ts`
- admin editor utilities: `apps/web/src/admin/utils.ts`

## 12. Example DTOs / Schemas

See:

- `apps/api/app/admin_schemas.py`
- `apps/api/app/schemas.py`

Relevant DTO groups:

- `AdminContentWriteRequest`
- `AdminContentListResponse`
- `ValidationResult`
- `PreviewResponse`
- `ImportRequest`
- `ImportResult`
- learner DTO extensions: `LessonBlockDTO`, richer `LessonDTO`, richer `ExerciseDTO`

## 13. Example Admin CRUD Endpoints

Create lesson:

```http
POST /api/admin/content/lessons
Authorization: Bearer <admin-token>
```

Validate lesson draft:

```http
POST /api/admin/content/validation/lessons
Authorization: Bearer <admin-token>
```

Preview scenario as free user:

```http
GET /api/admin/content/preview/scenarios/12?viewer_access=free
Authorization: Bearer <admin-token>
```

Bulk set lessons premium:

```http
POST /api/admin/content/status/bulk
Authorization: Bearer <admin-token>
```

## 14. Example Lesson Editor Structure

Frontend container:

- `apps/web/src/screens/AdminScreen.tsx`

Payload shape sent to backend:

```json
{
  "data": {
    "slug": "survival-greetings-01",
    "module_id": 1,
    "title": { "ru": "", "uz": "", "en": "" },
    "summary": { "ru": "", "uz": "", "en": "" },
    "objectives": [],
    "difficulty": "A0",
    "topic": "survival",
    "status": "draft",
    "access_state": "inherit"
  },
  "relation_ids": {
    "related_vocabulary": [1, 2],
    "related_grammar": [3],
    "related_scenarios": [4]
  },
  "children": {
    "blocks": []
  }
}
```

## 15. Example Import Service

- `app/services/admin_content_service.py`
- function: `import_entity`

Responsibilities:

- parse JSON/CSV package
- normalize nested payload
- validate row
- detect conflicts
- apply selected conflict strategy
- produce preview/errors summary

## 16. Example Export Service

- `app/services/admin_content_service.py`
- functions: `export_entity`, `template_export`

Responsibilities:

- serialize detail-safe content package
- emit JSON envelope
- flatten CSV for vocab/grammar
- supply downloadable template content

## 17. Example Validation Service

- `app/services/content_validation.py`

Responsibilities:

- entity-specific publish rules
- relation existence checks
- localization completeness checks
- typed issue reporting with `error` vs `warning`

## 18. Example Preview Endpoint

Route:

- `GET /api/admin/content/preview/{entity}/{id}`

Implementation:

- router: `apps/api/app/routers/admin_content.py`
- service: `apps/api/app/services/admin_content_service.py`

Lesson preview returns:

- objectives
- blocks
- exercise payloads
- relation ids
- deep link
- learner visibility and lock state

## 19. Example Content Package JSON

See:

- `docs/examples/phase-c-lesson-package.json`
- `docs/examples/phase-c-grammar-package.json`

## 20. Local Run Instructions

### Backend

```bash
cd apps/api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

### Web

```bash
cd apps/web
npm install
npm run dev
```

### Bot

```bash
cd apps/bot
pip install -r requirements.txt
python -m bot.main
```

### Full stack

```bash
docker compose up --build
```

## 21. Assumptions and Risks

- The frontend admin was rewritten without a local TypeScript toolchain available in this thread, so backend Python syntax was compiled, but frontend should still be run through `npm install && npm run build` locally before release.
- Existing seed/demo content still exists; Phase C removes the admin dependency on `demo.py`, but the seed files remain useful for local bootstrapping.
- Exercise links from grammar/vocab are managed primarily through the exercise editor; there is not yet a separate grammar-to-many-exercises relation table.
- The preview panel is operational but currently JSON-forward; it is meant for publishing QA rather than final polished learner presentation.
- Import merge is intentionally shallow and pragmatic; if richer merge semantics are needed later, the conflict resolver should become entity-specific.
