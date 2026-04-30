import asyncio
import logging
import os
from typing import Any

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllPrivateChats,
    CallbackQuery,
    ErrorEvent,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    Message,
    WebAppInfo,
)

from bot.api import ApiClient
from bot.keyboards import (
    admin_mini_app_keyboard,
    content_actions_keyboard,
    lesson_exercise_keyboard,
    lesson_time_keyboard,
    main_reply_keyboard,
    onboarding_language_keyboard,
    options_keyboard,
    review_keyboard,
    scenario_topics_keyboard,
    settings_difficulty_keyboard,
    settings_home_keyboard,
    settings_language_keyboard,
    settings_style_keyboard,
    settings_time_keyboard,
    share_link_keyboard,
    webapp_url,
)
from bot.texts import (
    action_from_label,
    button,
    cache_bundle,
    command_descriptions,
    difficulty_label,
    language_name,
    level_choices,
    normalize_language,
    style_choices,
    style_label,
    topic_label,
    tr,
)

logging.basicConfig(level=logging.INFO)
api = ApiClient()
LOGGER = logging.getLogger(__name__)
QUIZ_SESSION_SIZE = 3


class Onboarding(StatesGroup):
    language = State()
    level = State()
    daily_minutes = State()
    learning_style = State()


class LessonFlow(StatesGroup):
    answering_text = State()


def localize(value: Any, language: str, fallback: str = "") -> str:
    if isinstance(value, dict):
        return str(value.get(language) or value.get("en") or fallback)
    if value is None:
        return fallback
    return str(value)


def shorten(value: str | None, limit: int = 120) -> str:
    if not value:
        return ""
    collapsed = " ".join(str(value).split())
    if len(collapsed) <= limit:
        return collapsed
    return f"{collapsed[: limit - 1].rstrip()}…"


def admin_telegram_ids() -> set[str]:
    raw = os.getenv("BOT_ADMIN_TELEGRAM_IDS") or os.getenv("TELEGRAM_ADMIN_IDS") or ""
    return {chunk.strip() for chunk in raw.split(",") if chunk.strip()}


def is_authorized_admin(telegram_id: int | str) -> bool:
    return str(telegram_id) in admin_telegram_ids()


def parse_start_payload(text: str | None) -> str | None:
    if not text or " " not in text:
        return None
    return text.split(" ", 1)[1].strip() or None


def parse_deep_link(payload: str | None) -> dict[str, str] | None:
    if not payload:
        return None
    if payload.startswith("lesson_"):
        lesson_id = payload.split("_", 1)[1]
        return {"type": "lesson", "id": lesson_id} if lesson_id.isdigit() else None
    if payload.startswith("scenario_"):
        return {"type": "scenario", "id": payload.split("_", 1)[1]}
    if payload.startswith("grammar_"):
        return {"type": "grammar", "id": payload.split("_", 1)[1]}
    if payload.startswith("word_"):
        return {"type": "word", "id": payload.split("_", 1)[1]}
    if payload.startswith("dialogue_"):
        return {"type": "dialogue", "topic": payload.split("_", 1)[1]}
    if payload in {"review", "review_due"}:
        return {"type": "review"}
    if payload == "review_mistakes":
        return {"type": "mistakes"}
    if payload == "review_grammar":
        return {"type": "review_grammar"}
    if payload == "review_listening":
        return {"type": "review_listening"}
    if payload == "review_vocab":
        return {"type": "review_vocab"}
    if payload in {"settings", "screen_settings"}:
        return {"type": "settings"}
    if payload in {"library", "screen_library"}:
        return {"type": "library"}
    if payload in {"quiz", "quiz_mixed"}:
        return {"type": "quiz"}
    if payload in {"dialogue", "screen_scenarios"}:
        return {"type": "dialogue"}
    return None


def format_interval(language: str, interval_days: int) -> str:
    return tr("interval_days", language, days=interval_days)


def progress_indicator(current: int, total: int) -> str:
    return f"{current}/{max(total, 1)}"


def lesson_meta_line(lesson: dict, language: str) -> str:
    minutes = lesson.get("estimated_minutes") or 0
    difficulty = lesson.get("difficulty") or "A0"
    return f"{minutes} min • {difficulty}" if minutes else difficulty


def reply_target(event: Message | CallbackQuery) -> Message:
    return event.message if isinstance(event, CallbackQuery) else event


def chat_user_id(message: Message) -> int:
    return int(message.chat.id)


async def user_language(telegram_id: int | str) -> str:
    try:
        summary = await api.user_summary(telegram_id)
        language = normalize_language(summary.get("interface_language"))
        try:
            cache_bundle(language, await api.localization_bundle(telegram_id, "bot", language))
        except Exception:
            LOGGER.debug("Failed to refresh bot localization bundle", exc_info=True)
        return language
    except Exception:
        return "en"


async def ensure_menu_button(bot: Bot, chat_id: int, language: str) -> None:
    try:
        await bot.set_chat_menu_button(
            chat_id=chat_id,
            menu_button=MenuButtonWebApp(text=button("app", language), web_app=WebAppInfo(url=webapp_url("home"))),
        )
    except Exception:
        LOGGER.debug("Failed to set chat menu button", exc_info=True)


async def pause_text_input(state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state == LessonFlow.answering_text.state:
        await state.set_state(None)


async def read_data(state: FSMContext) -> dict[str, Any]:
    return await state.get_data()


async def write_data(state: FSMContext, **updates: Any) -> dict[str, Any]:
    data = await read_data(state)
    data.update(updates)
    await state.set_data(data)
    return data


async def drop_data_keys(state: FSMContext, *keys: str) -> dict[str, Any]:
    data = await read_data(state)
    for key in keys:
        data.pop(key, None)
    await state.set_data(data)
    return data


async def lesson_resume(state: FSMContext) -> dict[str, Any] | None:
    return (await read_data(state)).get("lesson_resume")


async def remember_lesson_resume(state: FSMContext, lesson_id: int, exercise_index: int) -> None:
    await write_data(state, lesson_resume={"lesson_id": lesson_id, "exercise_index": exercise_index})


async def clear_lesson_resume(state: FSMContext) -> None:
    await drop_data_keys(state, "lesson_resume")
    current_state = await state.get_state()
    if current_state == LessonFlow.answering_text.state:
        await state.set_state(None)


async def quiz_session(state: FSMContext) -> dict[str, Any] | None:
    return (await read_data(state)).get("quiz_session")


async def remember_quiz_session(state: FSMContext, session: dict[str, Any]) -> None:
    await write_data(state, quiz_session=session)


async def clear_quiz_session(state: FSMContext) -> None:
    await drop_data_keys(state, "quiz_session")


async def send_error_message(target: Message, language: str, action: str, route: str = "home") -> None:
    await target.answer(
        tr("generic_error", language),
        reply_markup=content_actions_keyboard(
            [(button("retry", language), f"nav:{action}")],
            web_route=route,
            web_label=button("open_app", language),
        ),
    )


def no_content_keyboard(language: str, *, route: str = "home") -> InlineKeyboardMarkup:
    return content_actions_keyboard(
        [
            (button("lesson", language), "nav:lesson"),
            (button("review", language), "nav:review"),
            (button("dialogue", language), "nav:dialogue"),
            (button("library", language), "nav:library"),
        ],
        web_route=route,
        web_label=button("open_app", language),
    )


def extract_review_prompt(item: dict, language: str) -> str:
    content = item.get("content", {})
    prompt = localize(content.get("prompt"), language)
    if prompt:
        return prompt
    if content.get("korean"):
        translation = localize(content.get("translations"), language)
        return f"{content['korean']} — {translation}".strip(" —")
    if content.get("pattern"):
        title = localize(content.get("title"), language)
        return f"{content['pattern']} — {title}".strip(" —")
    return tr("missing_content", language)


def review_message(item: dict, language: str, queue_kind: str, total: int) -> str:
    title = button("quick_review", language) if queue_kind == "due" else button("mistakes", language)
    prompt = extract_review_prompt(item, language)
    meta = f"{item.get('item_type', 'item')} • {button('mistakes', language)} {item.get('mistake_count', 0)}"
    return f"{title} {progress_indicator(1, total)}\n\n{prompt}\n\n{meta}"


def settings_message(settings: dict, language: str) -> str:
    reminders_state = button("reminders_on", language) if settings.get("reminders_enabled") else button("reminders_off", language)
    return (
        f"{tr('settings_title', language)}\n\n"
        f"{tr('settings_language_section', language)}\n"
        f"{tr('label_ui', language)}: {language_name(settings.get('interface_language', 'en'), language)}\n"
        f"{tr('label_explain', language)}: {language_name(settings.get('explanation_language', 'en'), language)}\n\n"
        f"{tr('settings_reminder_section', language)}\n"
        f"{reminders_state}\n"
        f"{settings.get('reminder_time', '19:00')} • {settings.get('timezone', 'Asia/Seoul')}\n\n"
        f"{tr('settings_learning_section', language)}\n"
        f"{style_label(settings.get('learning_style', 'mixed'), language)}\n\n"
        f"{tr('settings_difficulty_section', language)}\n"
        f"{difficulty_label(settings.get('difficulty', 'normal'), language)}"
    )


def submenu_text(settings: dict, language: str, mode: str) -> str:
    base = settings_message(settings, language)
    prompt_map = {
        "ui": button("language", language),
        "exp": button("explanations", language),
        "time": button("reminder_time", language),
        "style": button("style", language),
        "difficulty": button("difficulty", language),
    }
    return f"{base}\n\n{prompt_map.get(mode, button('settings', language))}"


def progress_message(progress: dict, language: str) -> str:
    path = progress.get("current_path") or {}
    lesson = progress.get("current_lesson") or {}
    path_title = localize(path.get("title"), language, "Korean from zero")
    lesson_title = localize(lesson.get("title"), language, tr("no_lesson", language))
    return (
        f"{tr('progress_title', language)}\n\n"
        f"{path_title}\n"
        f"{path.get('completed_lessons', 0)}/{path.get('total_lessons', 0)} • {round(path.get('percent_complete', 0))}%\n\n"
        f"{tr('label_next', language)}: {lesson_title}\n"
        f"{tr('label_due', language)}: {progress.get('due_reviews', 0)} • {button('mistakes', language)}: {progress.get('mistake_reviews', 0)}\n"
        f"XP: {progress.get('xp', 0)} • {button('streak', language)}: {progress.get('streak_count', 0)}"
    )


def streak_message(summary: dict, language: str) -> str:
    return (
        f"{tr('streak_title', language)}\n\n"
        f"{tr('label_current', language)}: {summary.get('streak_count', 0)}\n"
        f"{tr('label_next_milestone', language)}: {summary.get('next_milestone', 0)}\n"
        f"XP: {summary.get('xp', 0)}\n"
        f"{tr('label_due', language)}: {summary.get('due_reviews', 0)}"
    )


def curriculum_message(plan: dict, language: str) -> str:
    path = plan.get("path") or {}
    module = plan.get("module") or {}
    lesson = plan.get("next_lesson") or {}
    return (
        f"{tr('curriculum_title', language)}\n\n"
        f"{localize(path.get('title'), language, 'Korean from zero')}\n"
        f"{tr('label_module', language)}: {localize(module.get('title'), language, tr('label_module', language))}\n"
        f"{tr('label_next', language)}: {localize(lesson.get('title'), language, tr('no_lesson', language))}\n"
        f"{plan.get('completed_lessons', 0)}/{plan.get('total_lessons', 0)} • {round(plan.get('percent_complete', 0))}%"
    )


def menu_message(language: str, progress: dict | None, lesson_ready: bool, quiz_ready: bool) -> str:
    lines = [tr("menu_title", language), "", tr("menu_subtitle", language)]
    if progress:
        path = progress.get("current_path") or {}
        lesson = progress.get("current_lesson") or {}
        next_lesson = localize(lesson.get("title"), language, tr("no_lesson", language))
        lines.extend(
            [
                "",
                f"{path.get('completed_lessons', 0)}/{path.get('total_lessons', 0)} • {round(path.get('percent_complete', 0))}%",
                f"{tr('label_due', language)}: {progress.get('due_reviews', 0)} • {button('mistakes', language)}: {progress.get('mistake_reviews', 0)}",
                f"{tr('label_next', language)}: {next_lesson}",
            ]
        )
    if lesson_ready:
        lines.extend(["", tr("menu_resume_lesson", language)])
    if quiz_ready:
        lines.extend([tr("menu_resume_quiz", language)])
    lines.extend(["", tr("menu_hint", language)])
    return "\n".join(lines)


def lesson_intro_message(lesson: dict, language: str) -> str:
    title = localize(lesson.get("title"), language, "Lesson")
    summary = localize(lesson.get("summary"), language) or localize(lesson.get("explanation"), language)
    korean_text = shorten(lesson.get("korean_text"), 180)
    lines = [tr("lesson_heading", language), title, lesson_meta_line(lesson, language)]
    if korean_text:
        lines.extend(["", korean_text])
    if summary:
        lines.extend(["", shorten(summary, 220)])
    return "\n".join(lines)


def exercise_message(lesson: dict, exercise: dict, language: str, index: int, total: int) -> str:
    title = localize(lesson.get("title"), language, "Lesson")
    prompt = localize(exercise.get("prompt"), language, tr("missing_content", language))
    instructions = localize(exercise.get("instructions"), language)
    header = f"{title} • {progress_indicator(index + 1, total)}"
    if instructions:
        return f"{header}\n\n{prompt}\n\n{shorten(instructions, 180)}"
    return f"{header}\n\n{prompt}"


def grammar_preview_message(items: list[dict], language: str, focus: dict | None = None) -> str:
    if focus:
        title = localize(focus.get("title"), language)
        explanation = shorten(localize(focus.get("explanation"), language), 240)
        usage = shorten(localize(focus.get("usage_notes"), language), 160)
        common_errors = focus.get("common_errors") or {}
        error_value = common_errors.get(language) or common_errors.get("en") or [""]
        if isinstance(error_value, list):
            error = shorten(error_value[0] if error_value else "", 120)
        else:
            error = shorten(str(error_value), 120)
        lines = [tr("grammar_title", language), "", f"{focus.get('korean_pattern', '')} — {title}".strip(" —")]
        if explanation:
            lines.extend(["", explanation])
        if usage:
            lines.append(f"{tr('label_usage', language)}: {usage}")
        if error:
            lines.append(f"{tr('label_watch', language)}: {error}")
        return "\n".join(lines)

    lines = [tr("grammar_title", language), ""]
    for index, item in enumerate(items[:4], start=1):
        label = localize(item.get("title"), language)
        explanation = shorten(localize(item.get("explanation"), language), 90)
        lines.append(f"{index}. {item.get('korean_pattern', '')} — {label}".strip(" —"))
        if explanation:
            lines.append(f"   {explanation}")
    return "\n".join(lines)


def words_preview_message(items: list[dict], language: str, focus: dict | None = None) -> str:
    if focus:
        translation = localize(focus.get("translations"), language)
        usage = shorten(localize(focus.get("usage_notes"), language), 160)
        notes = shorten(localize(focus.get("notes"), language), 120)
        reading = focus.get("reading") or ""
        lines = [tr("words_title", language), "", focus.get("korean", "")]
        if reading:
            lines.append(reading)
        if translation:
            lines.extend(["", translation])
        if usage:
            lines.append(f"{tr('label_usage', language)}: {usage}")
        if notes:
            lines.append(f"{tr('label_note', language)}: {notes}")
        return "\n".join(lines)

    lines = [tr("words_title", language), ""]
    for index, item in enumerate(items[:5], start=1):
        translation = shorten(localize(item.get("translations"), language), 80)
        lines.append(f"{index}. {item.get('korean', '')} — {translation}".strip(" —"))
    return "\n".join(lines)


def dialogue_preview_message(language: str, scenarios: list[dict], focus: dict | None = None) -> str:
    if focus:
        title = localize(focus.get("title"), language, "Scenario")
        description = shorten(localize(focus.get("description"), language), 220)
        lines = [tr("dialogue_title", language), "", title]
        if description:
            lines.extend(["", description])
        if focus.get("audio_locked"):
            lines.extend(["", "Premium listening is locked in chat. Open the Mini App for the full playback flow."])
            return "\n".join(lines)
        first_dialogue = (focus.get("dialogues") or [{}])[0]
        preview_lines = first_dialogue.get("lines") or []
        if preview_lines:
            lines.append("")
            for line in preview_lines[:3]:
                lines.append(f"{line.get('speaker', 'A')}: {line.get('korean', '')}")
        return "\n".join(lines)

    lines = [tr("dialogue_title", language), ""]
    for index, item in enumerate(scenarios[:4], start=1):
        title = localize(item.get("title"), language, "Scenario")
        description = shorten(localize(item.get("description"), language), 90)
        lines.append(f"{index}. {title}")
        if description:
            lines.append(f"   {description}")
    return "\n".join(lines)


def quiz_item_message(item: dict, language: str, index: int, total: int) -> str:
    source_labels = {
        "lesson": button("lesson", language),
        "review": button("review", language),
        "scenario": button("dialogue", language),
        "mixed": button("quiz", language),
    }
    source = source_labels.get(item.get("source", "mixed"), button("quiz", language))
    lines = [f"{tr('quiz_title', language)} {progress_indicator(index + 1, total)} • {source}", ""]
    if item.get("title"):
        lines.append(item["title"])
        lines.append("")
    lines.append(item.get("prompt") or tr("missing_content", language))
    return "\n".join(lines)


def grammar_keyboard(language: str, items: list[dict], focus: dict | None = None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    entries = [focus] if focus else items[:3]
    for item in entries:
        if not item:
            continue
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{item.get('korean_pattern', '')}",
                    web_app=WebAppInfo(url=webapp_url("library", tab="grammar", grammar=str(item.get("id")))),
                )
            ]
        )
    rows.append([InlineKeyboardButton(text=button("open_library", language), web_app=WebAppInfo(url=webapp_url("library", tab="grammar")))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def words_keyboard(language: str, items: list[dict], focus: dict | None = None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    entries = [focus] if focus else items[:3]
    for item in entries:
        if not item:
            continue
        rows.append(
            [
                InlineKeyboardButton(
                    text=item.get("korean", ""),
                    web_app=WebAppInfo(url=webapp_url("library", tab="words", word=str(item.get("id")))),
                )
            ]
        )
    rows.append([InlineKeyboardButton(text=button("open_library", language), web_app=WebAppInfo(url=webapp_url("library", tab="words")))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def dialogue_keyboard(language: str, scenarios: list[dict], focus: dict | None = None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if focus:
        rows.append(
            [
                InlineKeyboardButton(
                    text=button("open_dialogue", language),
                    web_app=WebAppInfo(url=webapp_url("scenarios", scenario=str(focus.get("slug")))),
                )
            ]
        )
    else:
        primary = next((item for item in scenarios if (item.get("progress") or {}).get("status") == "in_progress"), None) or (scenarios[0] if scenarios else None)
        if primary:
            rows.append(
                [
                    InlineKeyboardButton(
                        text=localize(primary.get("title"), language, button("open_dialogue", language)),
                        web_app=WebAppInfo(url=webapp_url("scenarios", scenario=str(primary.get("slug")))),
                    )
                ]
            )
    rows.extend(scenario_topics_keyboard(language).inline_keyboard)
    rows.append([InlineKeyboardButton(text=button("open_dialogue", language), web_app=WebAppInfo(url=webapp_url("scenarios")))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def quiz_exercise_keyboard(item: dict, language: str) -> InlineKeyboardMarkup:
    exercise = {
        "id": item.get("exercise_id"),
        "options": item.get("options", []),
    }
    return lesson_exercise_keyboard(exercise, language, "quiz") or content_actions_keyboard(
        [(button("retry", language), "nav:quiz")],
        web_route="learn",
        web_label=button("open_lesson", language),
    )


def find_item(items: list[dict], raw_id: str | None) -> dict | None:
    if not raw_id:
        return None
    for item in items:
        if str(item.get("id")) == str(raw_id) or str(item.get("slug")) == str(raw_id):
            return item
    return None


def scenario_quiz_prompt(detail: dict, language: str) -> tuple[str, str] | None:
    if detail.get("audio_locked"):
        return None
    dialogues = detail.get("dialogues") or []
    if dialogues:
        checks = dialogues[0].get("checks") or []
        if checks:
            prompt = localize(checks[0].get("prompt"), language)
            answer = str(checks[0].get("answer") or "")
            if prompt and answer:
                return prompt, answer
        expressions = dialogues[0].get("useful_expressions") or []
        if expressions:
            expression = expressions[0]
            prompt = f"{expression.get('korean', '')} — meaning?"
            answer = localize(expression.get("translations"), language)
            if answer:
                return prompt, answer
    return None


async def fetch_lesson(telegram_id: int | str, lesson_id: int) -> dict:
    return await api.lesson(telegram_id, lesson_id)


def sorted_exercises(lesson: dict) -> list[dict]:
    return sorted(lesson.get("exercises", []), key=lambda item: item.get("order_index", 0))


async def send_menu(message: Message, state: FSMContext) -> None:
    telegram_id = chat_user_id(message)
    language = await user_language(telegram_id)
    await pause_text_input(state)
    await ensure_menu_button(message.bot, telegram_id, language)
    progress = None
    try:
        progress = await api.progress(telegram_id)
    except Exception:
        LOGGER.debug("Could not load menu progress", exc_info=True)
    text = menu_message(language, progress, bool(await lesson_resume(state)), bool(await quiz_session(state)))
    await message.answer(text, reply_markup=main_reply_keyboard(language))


async def send_review_queue(target: Message, telegram_id: int, queue_kind: str, language: str) -> None:
    queue = await api.review_queue(telegram_id, mistakes_only=queue_kind == "mistakes")
    if not queue:
        empty_key = "no_mistakes" if queue_kind == "mistakes" else "no_review"
        route = "review" if queue_kind == "mistakes" else "learn"
        await target.answer(tr(empty_key, language), reply_markup=no_content_keyboard(language, route=route))
        return
    await target.answer(review_message(queue[0], language, queue_kind, len(queue)), reply_markup=review_keyboard(queue[0]["id"], queue_kind, language))


async def send_current_lesson_step(target: Message, lesson: dict, index: int, state: FSMContext, telegram_id: int, language: str) -> None:
    exercises = sorted_exercises(lesson)
    if not exercises:
        await clear_lesson_resume(state)
        await target.answer(tr("lesson_finished_empty", language), reply_markup=no_content_keyboard(language, route="learn"))
        return
    if index >= len(exercises):
        await clear_lesson_resume(state)
        await target.answer(
            tr("lesson_complete", language),
            reply_markup=content_actions_keyboard(
                [(button("review", language), "nav:review"), (button("dialogue", language), "nav:dialogue")],
                web_route="learn",
                web_label=button("open_lesson", language),
            ),
        )
        return

    exercise = exercises[index]
    await remember_lesson_resume(state, lesson["id"], index)
    keyboard = lesson_exercise_keyboard(exercise, language, "lesson")
    if keyboard:
        await state.set_state(None)
        await target.answer(exercise_message(lesson, exercise, language, index, len(exercises)), reply_markup=keyboard)
        return

    await state.set_state(LessonFlow.answering_text)
    await target.answer(
        f"{exercise_message(lesson, exercise, language, index, len(exercises))}\n\n{tr('lesson_prompt_text', language)}"
    )


async def start_lesson_flow(target: Message, state: FSMContext, telegram_id: int, *, lesson_id: int | None = None) -> None:
    language = await user_language(telegram_id)
    lesson = await (fetch_lesson(telegram_id, lesson_id) if lesson_id else api.continue_lesson(telegram_id))
    if not lesson:
        await target.answer(tr("no_lesson", language), reply_markup=no_content_keyboard(language, route="learn"))
        return
    await api.start_lesson(telegram_id, lesson["id"])
    await target.answer(lesson_intro_message(lesson, language))
    await send_current_lesson_step(target, lesson, 0, state, telegram_id, language)


async def resume_lesson_flow(target: Message, state: FSMContext, telegram_id: int) -> bool:
    resume = await lesson_resume(state)
    if not resume:
        return False
    language = await user_language(telegram_id)
    try:
        lesson = await fetch_lesson(telegram_id, int(resume["lesson_id"]))
        exercises = sorted_exercises(lesson)
        index = int(resume["exercise_index"])
        if index < 0 or index >= len(exercises):
            raise IndexError("Exercise index is out of range")
        await target.answer(tr("lesson_resumed", language))
        await send_current_lesson_step(target, lesson, index, state, telegram_id, language)
        return True
    except Exception:
        await clear_lesson_resume(state)
        await target.answer(tr("lesson_no_resume", language))
        return False


async def build_quiz_session(telegram_id: int, language: str) -> dict[str, Any] | None:
    items: list[dict[str, Any]] = []

    try:
        lesson = await api.continue_lesson(telegram_id)
        if lesson:
            exercise = next((row for row in sorted_exercises(lesson) if row.get("options")), None)
            if exercise:
                items.append(
                    {
                        "kind": "exercise",
                        "source": "lesson",
                        "lesson_id": lesson["id"],
                        "exercise_id": exercise["id"],
                        "title": localize(lesson.get("title"), language),
                        "prompt": localize(exercise.get("prompt"), language, tr("missing_content", language)),
                        "options": sorted(exercise.get("options") or [], key=lambda option: option.get("order_index", 0)),
                    }
                )
    except Exception:
        LOGGER.debug("Could not load lesson item for quiz", exc_info=True)

    try:
        review_items = await api.review_queue(telegram_id)
        if review_items:
            review_item = review_items[0]
            items.append(
                {
                    "kind": "review",
                    "source": "review",
                    "review_item_id": review_item["id"],
                    "prompt": extract_review_prompt(review_item, language),
                }
            )
    except Exception:
        LOGGER.debug("Could not load review item for quiz", exc_info=True)

    try:
        scenarios = await api.scenarios(telegram_id)
        selected = next((row for row in scenarios if (row.get("progress") or {}).get("status") == "in_progress"), None) or (scenarios[0] if scenarios else None)
        if selected:
            detail = await api.scenario_detail(telegram_id, str(selected.get("slug")))
            prompt_answer = scenario_quiz_prompt(detail, language)
            if prompt_answer:
                prompt, answer = prompt_answer
                items.append(
                    {
                        "kind": "scenario",
                        "source": "scenario",
                        "scenario_slug": detail.get("slug"),
                        "title": localize(detail.get("title"), language),
                        "prompt": prompt,
                        "answer": answer,
                    }
                )
    except Exception:
        LOGGER.debug("Could not load scenario item for quiz", exc_info=True)

    if not items:
        try:
            extra = await api.start_quiz(telegram_id)
            for exercise in extra.get("exercises", []):
                if exercise.get("options"):
                    items.append(
                        {
                            "kind": "exercise",
                            "source": "mixed",
                            "lesson_id": 0,
                            "exercise_id": exercise["id"],
                            "title": "",
                            "prompt": localize(exercise.get("prompt"), language, tr("missing_content", language)),
                            "options": sorted(exercise.get("options") or [], key=lambda option: option.get("order_index", 0)),
                        }
                    )
                    break
        except Exception:
            LOGGER.debug("Could not load fallback quiz item", exc_info=True)

    if not items:
        return None
    return {"items": items[:QUIZ_SESSION_SIZE], "index": 0}


async def send_quiz_item(target: Message, state: FSMContext, telegram_id: int, language: str) -> None:
    session = await quiz_session(state)
    if not session:
        await target.answer(tr("quiz_empty", language), reply_markup=no_content_keyboard(language, route="learn"))
        return

    index = int(session.get("index", 0))
    items = session.get("items") or []
    if index >= len(items):
        await clear_quiz_session(state)
        await target.answer(
            tr("quiz_complete", language),
            reply_markup=content_actions_keyboard(
                [(button("lesson", language), "nav:lesson"), (button("review", language), "nav:review")],
                web_route="learn",
                web_label=button("open_lesson", language),
            ),
        )
        return

    item = items[index]
    text = quiz_item_message(item, language, index, len(items))
    if item["kind"] == "exercise":
        await target.answer(text, reply_markup=quiz_exercise_keyboard(item, language))
        return
    if item["kind"] == "review":
        await target.answer(
            text,
            reply_markup=content_actions_keyboard(
                [(button("knew", language), "quiz:review:4"), (button("missed", language), "quiz:review:1")],
                web_route="review",
                web_label=button("open_review", language),
            ),
        )
        return
    await target.answer(
        text,
        reply_markup=content_actions_keyboard(
            [(button("knew", language), "quiz:scenario:knew"), (button("show_answer", language), "quiz:scenario:show")],
            web_route="scenarios",
            web_label=button("open_dialogue", language),
            web_params={"scenario": str(item.get("scenario_slug"))},
        ),
    )


async def move_quiz_forward(target: Message, state: FSMContext, language: str) -> None:
    session = await quiz_session(state)
    if not session:
        await target.answer(tr("quiz_empty", language), reply_markup=no_content_keyboard(language, route="learn"))
        return
    session["index"] = int(session.get("index", 0)) + 1
    await remember_quiz_session(state, session)
    await send_quiz_item(target, state, target.chat.id, language)


async def send_settings_overview(target: Message, telegram_id: int, language: str) -> None:
    settings = await api.settings(telegram_id)
    view_language = normalize_language(settings.get("interface_language") or language)
    await target.answer(
        settings_message(settings, view_language),
        reply_markup=settings_home_keyboard(view_language, bool(settings.get("reminders_enabled"))),
    )


async def update_settings_message(callback: CallbackQuery, settings: dict, mode: str | None = None) -> None:
    language = normalize_language(settings.get("interface_language"))
    if mode == "ui":
        await callback.message.edit_text(submenu_text(settings, language, "ui"), reply_markup=settings_language_keyboard(language, "ui"))
        return
    if mode == "exp":
        await callback.message.edit_text(submenu_text(settings, language, "exp"), reply_markup=settings_language_keyboard(language, "exp"))
        return
    if mode == "time":
        await callback.message.edit_text(submenu_text(settings, language, "time"), reply_markup=settings_time_keyboard(language))
        return
    if mode == "style":
        await callback.message.edit_text(submenu_text(settings, language, "style"), reply_markup=settings_style_keyboard(language))
        return
    if mode == "difficulty":
        await callback.message.edit_text(submenu_text(settings, language, "difficulty"), reply_markup=settings_difficulty_keyboard(language))
        return
    await callback.message.edit_text(
        settings_message(settings, language),
        reply_markup=settings_home_keyboard(language, bool(settings.get("reminders_enabled"))),
    )


async def dispatch_navigation(target: Message, state: FSMContext, action: str) -> None:
    if action == "menu":
        await send_menu(target, state)
    elif action == "lesson":
        await cmd_lesson(target, state)
    elif action == "grammar":
        await cmd_grammar(target, state)
    elif action == "words":
        await cmd_words(target, state)
    elif action == "review":
        await cmd_review(target, state)
    elif action == "mistakes":
        await cmd_mistakes(target, state)
    elif action == "dialogue":
        await cmd_dialogue(target, state)
    elif action == "library":
        await cmd_library(target, state)
    elif action == "quiz":
        await cmd_quiz(target, state)
    elif action == "progress":
        await cmd_progress(target, state)
    elif action == "streak":
        await cmd_streak(target, state)
    elif action == "settings":
        await cmd_settings(target, state)
    elif action == "help":
        await cmd_help(target, state)
    elif action == "app":
        language = await user_language(target.chat.id)
        await target.answer(button("open_app", language), reply_markup=content_actions_keyboard(web_route="home", web_label=button("open_app", language)))


async def handle_deep_link(target: Message, state: FSMContext, payload: str | None, language: str) -> bool:
    deep_link = parse_deep_link(payload)
    if not deep_link:
        return False
    action = deep_link["type"]
    if action == "lesson" and deep_link.get("id", "").isdigit():
        await clear_quiz_session(state)
        await start_lesson_flow(target, state, target.chat.id, lesson_id=int(deep_link["id"]))
        return True
    if action == "scenario":
        await send_dialogue_preview(target, target.chat.id, language, focus=deep_link.get("id"))
        return True
    if action == "grammar":
        await send_grammar_preview(target, language, focus=deep_link.get("id"))
        return True
    if action == "word":
        await send_words_preview(target, language, focus=deep_link.get("id"))
        return True
    if action == "review":
        await send_review_queue(target, target.chat.id, "due", language)
        return True
    if action == "mistakes":
        await send_review_queue(target, target.chat.id, "mistakes", language)
        return True
    if action in {"review_grammar", "review_listening", "review_vocab"}:
        mode = action.replace("review_", "")
        await target.answer(
            tr("menu_hint", language),
            reply_markup=content_actions_keyboard(
                web_route="review",
                web_label=button("open_review", language),
                web_params={"mode": mode},
            ),
        )
        return True
    if action == "settings":
        await send_settings_overview(target, target.chat.id, language)
        return True
    if action == "quiz":
        await cmd_quiz(target, state)
        return True
    if action == "dialogue":
        await send_dialogue_preview(target, target.chat.id, language, topic=deep_link.get("topic"))
        return True
    if action == "library":
        await send_library_overview(target, language)
        return True
    return False


async def send_grammar_preview(target: Message, language: str, focus: str | None = None) -> None:
    items = await api.grammar(target.chat.id, language)
    if not items:
        await target.answer(tr("grammar_empty", language), reply_markup=no_content_keyboard(language, route="library"))
        return
    focused = find_item(items, focus)
    await target.answer(grammar_preview_message(items, language, focused), reply_markup=grammar_keyboard(language, items, focused))


async def send_words_preview(target: Message, language: str, focus: str | None = None) -> None:
    items = await api.vocab(target.chat.id, language)
    if not items:
        await target.answer(tr("words_empty", language), reply_markup=no_content_keyboard(language, route="library"))
        return
    focused = find_item(items, focus)
    await target.answer(words_preview_message(items, language, focused), reply_markup=words_keyboard(language, items, focused))


async def send_library_overview(target: Message, language: str) -> None:
    grammar_items = await api.grammar(target.chat.id, language)
    vocab_items = await api.vocab(target.chat.id, language)
    lines = [tr("label_library", language), ""]
    if grammar_items:
        item = grammar_items[0]
        lines.append(f"{tr('grammar_title', language)}: {item.get('korean_pattern', '')} — {localize(item.get('title'), language)}".strip(" —"))
    if vocab_items:
        item = vocab_items[0]
        lines.append(f"{tr('words_title', language)}: {item.get('korean', '')} — {localize(item.get('translations'), language)}".strip(" —"))
    if len(lines) == 2:
        lines.append(tr("missing_content", language))
    await target.answer(
        "\n".join(lines),
        reply_markup=content_actions_keyboard(
            [(tr("grammar_title", language), "nav:grammar"), (tr("words_title", language), "nav:words")],
            web_route="library",
            web_label=button("open_library", language),
        ),
    )


async def send_dialogue_preview(target: Message, telegram_id: int, language: str, *, topic: str | None = None, focus: str | None = None) -> None:
    scenarios = await api.scenarios(telegram_id, topic=topic)
    if focus:
        try:
            detail = await api.scenario_detail(telegram_id, focus)
        except Exception:
            detail = None
        if detail:
            await target.answer(dialogue_preview_message(language, scenarios, detail), reply_markup=dialogue_keyboard(language, scenarios, detail))
            return
        await target.answer(tr("unknown_deep_link", language))
    if not scenarios:
        await target.answer(tr("dialogue_empty", language), reply_markup=no_content_keyboard(language, route="scenarios"))
        return
    await target.answer(dialogue_preview_message(language, scenarios), reply_markup=dialogue_keyboard(language, scenarios))


async def cmd_start(message: Message, state: FSMContext) -> None:
    deep_link = parse_start_payload(message.text)
    summary = await api.start_onboarding(message.from_user, deep_link)
    language = normalize_language(summary.get("interface_language"))
    await ensure_menu_button(message.bot, message.from_user.id, language)

    if summary.get("is_onboarded"):
        await pause_text_input(state)
        if deep_link and await handle_deep_link(message, state, deep_link, language):
            return
        if deep_link:
            await message.answer(tr("unknown_deep_link", language))
        await send_menu(message, state)
        return

    await state.set_state(Onboarding.language)
    await write_data(state, pending_deep_link=deep_link)
    await message.answer(tr("choose_language", language), reply_markup=onboarding_language_keyboard())


async def on_language(callback: CallbackQuery, state: FSMContext) -> None:
    language = normalize_language(callback.data.split(":")[-1])
    await write_data(state, interface_language=language)
    await state.set_state(Onboarding.level)
    await callback.message.edit_text(tr("choose_level", language), reply_markup=options_keyboard("onboarding:level", level_choices(language)))
    await callback.answer()


async def on_level(callback: CallbackQuery, state: FSMContext) -> None:
    data = await read_data(state)
    language = normalize_language(data.get("interface_language"))
    await write_data(state, level=callback.data.split(":")[-1])
    await state.set_state(Onboarding.daily_minutes)
    await callback.message.edit_text(tr("choose_time", language), reply_markup=lesson_time_keyboard(language))
    await callback.answer()


async def on_time(callback: CallbackQuery, state: FSMContext) -> None:
    data = await read_data(state)
    language = normalize_language(data.get("interface_language"))
    await write_data(state, daily_minutes=int(callback.data.split(":")[-1]))
    await state.set_state(Onboarding.learning_style)
    await callback.message.edit_text(
        tr("choose_style", language),
        reply_markup=options_keyboard("onboarding:style", style_choices(language)),
    )
    await callback.answer()


async def on_style(callback: CallbackQuery, state: FSMContext) -> None:
    data = await read_data(state)
    language = normalize_language(data.get("interface_language"))
    payload = {
        **data,
        "goal": "korean_from_zero",
        "learning_style": callback.data.split(":")[-1],
        "timezone": "Asia/Seoul",
        "reminder_time": "19:00",
    }
    await api.complete_onboarding(callback.from_user, payload)
    pending_deep_link = data.get("pending_deep_link")
    await state.clear()
    await ensure_menu_button(callback.message.bot, callback.from_user.id, language)
    await callback.message.edit_text(tr("onboarded", language))
    if pending_deep_link and await handle_deep_link(callback.message, state, str(pending_deep_link), language):
        await callback.answer()
        return
    await send_menu(callback.message, state)
    await callback.answer()


async def cmd_menu(message: Message, state: FSMContext) -> None:
    await send_menu(message, state)


async def cmd_admin(message: Message) -> None:
    telegram_id = chat_user_id(message)
    language = await user_language(telegram_id)
    if not is_authorized_admin(telegram_id):
        await message.answer(tr("admin_only", language))
        return
    await message.answer(button("admin", language), reply_markup=admin_mini_app_keyboard(language))


async def cmd_lesson(message: Message, state: FSMContext) -> None:
    telegram_id = chat_user_id(message)
    await clear_quiz_session(state)
    if await resume_lesson_flow(message, state, telegram_id):
        return
    language = await user_language(telegram_id)
    try:
        await start_lesson_flow(message, state, telegram_id)
    except Exception:
        LOGGER.exception("Failed to start lesson")
        await send_error_message(message, language, "lesson", route="learn")


async def on_lesson_answer(callback: CallbackQuery, state: FSMContext) -> None:
    language = await user_language(callback.from_user.id)
    try:
        _, _, exercise_id_raw, option_index_raw = callback.data.split(":")
        resume = await lesson_resume(state)
        if not resume:
            await callback.answer(tr("lesson_no_resume", language), show_alert=True)
            await cmd_lesson(callback.message, state)
            return
        lesson = await fetch_lesson(callback.from_user.id, int(resume["lesson_id"]))
        exercises = sorted_exercises(lesson)
        exercise = exercises[int(resume["exercise_index"])]
        if int(exercise_id_raw) != int(exercise["id"]):
            await callback.answer(tr("lesson_no_resume", language), show_alert=True)
            await cmd_lesson(callback.message, state)
            return
        option_index = int(option_index_raw)
        options = sorted(exercise.get("options") or [], key=lambda item: item.get("order_index", 0))
        option = options[option_index]
        result = await api.submit_exercise(callback.from_user.id, int(exercise["id"]), int(lesson["id"]), option.get("value"))
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(tr("correct", language) if result.get("is_correct") else tr("wrong", language))
        if result.get("is_correct"):
            await send_current_lesson_step(
                callback.message,
                lesson,
                int(resume["exercise_index"]) + 1,
                state,
                callback.from_user.id,
                language,
            )
        else:
            await send_current_lesson_step(
                callback.message,
                lesson,
                int(resume["exercise_index"]),
                state,
                callback.from_user.id,
                language,
            )
        await callback.answer()
    except Exception:
        LOGGER.exception("Failed to submit lesson answer")
        await callback.answer(tr("generic_error", language), show_alert=True)
        await send_error_message(callback.message, language, "lesson", route="learn")


async def on_text_answer(message: Message, state: FSMContext) -> None:
    telegram_id = chat_user_id(message)
    action = action_from_label(message.text)
    if action:
        await pause_text_input(state)
        await dispatch_navigation(message, state, action)
        return

    resume = await lesson_resume(state)
    if not resume:
        language = await user_language(telegram_id)
        await message.answer(tr("lesson_no_resume", language))
        return

    language = await user_language(telegram_id)
    try:
        lesson = await fetch_lesson(telegram_id, int(resume["lesson_id"]))
        exercise = sorted_exercises(lesson)[int(resume["exercise_index"])]
        result = await api.submit_exercise(telegram_id, int(exercise["id"]), int(lesson["id"]), message.text or "")
        await message.answer(tr("correct", language) if result.get("is_correct") else tr("wrong", language))
        next_index = int(resume["exercise_index"]) + 1 if result.get("is_correct") else int(resume["exercise_index"])
        await send_current_lesson_step(message, lesson, next_index, state, telegram_id, language)
    except Exception:
        LOGGER.exception("Failed to submit text answer")
        await send_error_message(message, language, "lesson", route="learn")


async def cmd_review(message: Message, state: FSMContext) -> None:
    telegram_id = chat_user_id(message)
    await pause_text_input(state)
    language = await user_language(telegram_id)
    try:
        await send_review_queue(message, telegram_id, "due", language)
    except Exception:
        LOGGER.exception("Failed to open review queue")
        await send_error_message(message, language, "review", route="review")


async def cmd_mistakes(message: Message, state: FSMContext) -> None:
    telegram_id = chat_user_id(message)
    await pause_text_input(state)
    language = await user_language(telegram_id)
    try:
        await send_review_queue(message, telegram_id, "mistakes", language)
    except Exception:
        LOGGER.exception("Failed to open mistake queue")
        await send_error_message(message, language, "mistakes", route="review")


async def on_review(callback: CallbackQuery) -> None:
    language = await user_language(callback.from_user.id)
    try:
        _, _, queue_kind, item_id_raw, quality_raw = callback.data.split(":")
        quality = int(quality_raw)
        result = await api.submit_review(callback.from_user.id, int(item_id_raw), quality >= 3, quality)
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(tr("review_saved", language, interval=format_interval(language, result["interval_days"])))
        await send_review_queue(callback.message, callback.from_user.id, queue_kind, language)
        await callback.answer()
    except Exception:
        LOGGER.exception("Failed to submit review")
        await callback.answer(tr("generic_error", language), show_alert=True)
        await send_error_message(callback.message, language, "review", route="review")


async def cmd_grammar(message: Message, state: FSMContext) -> None:
    await pause_text_input(state)
    language = await user_language(chat_user_id(message))
    try:
        await send_grammar_preview(message, language)
    except Exception:
        LOGGER.exception("Failed to open grammar preview")
        await send_error_message(message, language, "library", route="library")


async def cmd_words(message: Message, state: FSMContext) -> None:
    await pause_text_input(state)
    language = await user_language(chat_user_id(message))
    try:
        await send_words_preview(message, language)
    except Exception:
        LOGGER.exception("Failed to open words preview")
        await send_error_message(message, language, "library", route="library")


async def cmd_library(message: Message, state: FSMContext) -> None:
    await pause_text_input(state)
    language = await user_language(chat_user_id(message))
    try:
        await send_library_overview(message, language)
    except Exception:
        LOGGER.exception("Failed to open library overview")
        await send_error_message(message, language, "library", route="library")


async def cmd_dialogue(message: Message, state: FSMContext) -> None:
    telegram_id = chat_user_id(message)
    await pause_text_input(state)
    language = await user_language(telegram_id)
    try:
        await send_dialogue_preview(message, telegram_id, language)
    except Exception:
        LOGGER.exception("Failed to open dialogue preview")
        await send_error_message(message, language, "dialogue", route="scenarios")


async def on_dialogue_topic(callback: CallbackQuery, state: FSMContext) -> None:
    await pause_text_input(state)
    language = await user_language(callback.from_user.id)
    try:
        topic = callback.data.split(":")[-1]
        await send_dialogue_preview(callback.message, callback.from_user.id, language, topic=topic)
        await callback.answer()
    except Exception:
        LOGGER.exception("Failed to filter dialogue topic")
        await callback.answer(tr("generic_error", language), show_alert=True)


async def cmd_quiz(message: Message, state: FSMContext) -> None:
    telegram_id = chat_user_id(message)
    await pause_text_input(state)
    language = await user_language(telegram_id)
    session = await quiz_session(state)
    if not session:
        try:
            session = await build_quiz_session(telegram_id, language)
            if not session:
                await message.answer(tr("quiz_empty", language), reply_markup=no_content_keyboard(language, route="learn"))
                return
            await remember_quiz_session(state, session)
        except Exception:
            LOGGER.exception("Failed to build quiz session")
            await send_error_message(message, language, "quiz", route="learn")
            return
    await send_quiz_item(message, state, telegram_id, language)


async def on_quiz_answer(callback: CallbackQuery, state: FSMContext) -> None:
    language = await user_language(callback.from_user.id)
    try:
        session = await quiz_session(state)
        if not session:
            await callback.answer(tr("quiz_empty", language), show_alert=True)
            return
        index = int(session.get("index", 0))
        item = (session.get("items") or [])[index]
        if item.get("kind") != "exercise":
            await callback.answer(tr("generic_error", language), show_alert=True)
            return
        _, _, exercise_id_raw, option_index_raw = callback.data.split(":")
        if int(exercise_id_raw) != int(item.get("exercise_id", 0)):
            await callback.answer(tr("generic_error", language), show_alert=True)
            return
        option = item.get("options", [])[int(option_index_raw)]
        result = await api.submit_exercise(
            callback.from_user.id,
            int(item["exercise_id"]),
            int(item.get("lesson_id") or 0),
            option.get("value"),
        )
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(tr("correct", language) if result.get("is_correct") else tr("wrong", language))
        if result.get("is_correct"):
            await move_quiz_forward(callback.message, state, language)
        else:
            await send_quiz_item(callback.message, state, callback.from_user.id, language)
        await callback.answer()
    except Exception:
        LOGGER.exception("Failed to submit quiz answer")
        await callback.answer(tr("generic_error", language), show_alert=True)


async def on_quiz_review(callback: CallbackQuery, state: FSMContext) -> None:
    language = await user_language(callback.from_user.id)
    try:
        quality = int(callback.data.split(":")[-1])
        session = await quiz_session(state)
        if not session:
            await callback.answer(tr("quiz_empty", language), show_alert=True)
            return
        item = (session.get("items") or [])[int(session.get("index", 0))]
        await api.submit_review(callback.from_user.id, int(item["review_item_id"]), quality >= 3, quality)
        await callback.message.edit_reply_markup(reply_markup=None)
        await move_quiz_forward(callback.message, state, language)
        await callback.answer()
    except Exception:
        LOGGER.exception("Failed to submit quiz review")
        await callback.answer(tr("generic_error", language), show_alert=True)


async def on_quiz_scenario(callback: CallbackQuery, state: FSMContext) -> None:
    language = await user_language(callback.from_user.id)
    try:
        session = await quiz_session(state)
        if not session:
            await callback.answer(tr("quiz_empty", language), show_alert=True)
            return
        item = (session.get("items") or [])[int(session.get("index", 0))]
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(tr("quiz_show_answer", language, answer=item.get("answer", "")))
        await move_quiz_forward(callback.message, state, language)
        await callback.answer()
    except Exception:
        LOGGER.exception("Failed to handle scenario quiz item")
        await callback.answer(tr("generic_error", language), show_alert=True)


async def cmd_progress(message: Message, state: FSMContext) -> None:
    telegram_id = chat_user_id(message)
    await pause_text_input(state)
    language = await user_language(telegram_id)
    try:
        progress = await api.progress(telegram_id)
        await message.answer(
            progress_message(progress, language),
            reply_markup=content_actions_keyboard(
                [(button("lesson", language), "nav:lesson"), (button("review", language), "nav:review")],
                web_route="home",
                web_label=button("open_app", language),
            ),
        )
    except Exception:
        LOGGER.exception("Failed to load progress")
        await send_error_message(message, language, "progress")


async def cmd_plan(message: Message) -> None:
    telegram_id = chat_user_id(message)
    language = await user_language(telegram_id)
    try:
        plan = await api.plan(telegram_id)
        await message.answer(curriculum_message(plan, language), reply_markup=content_actions_keyboard(web_route="home", web_label=button("open_app", language)))
    except Exception:
        LOGGER.exception("Failed to load curriculum map")
        await send_error_message(message, language, "progress")


async def cmd_streak(message: Message, state: FSMContext) -> None:
    telegram_id = chat_user_id(message)
    await pause_text_input(state)
    language = await user_language(telegram_id)
    try:
        summary = await api.streak(telegram_id)
        await message.answer(
            streak_message(summary, language),
            reply_markup=content_actions_keyboard(
                [(button("lesson", language), "nav:lesson"), (button("review", language), "nav:review")],
                web_route="home",
                web_label=button("open_app", language),
            ),
        )
    except Exception:
        LOGGER.exception("Failed to load streak")
        await send_error_message(message, language, "streak")


async def cmd_settings(message: Message, state: FSMContext) -> None:
    telegram_id = chat_user_id(message)
    await pause_text_input(state)
    language = await user_language(telegram_id)
    try:
        await send_settings_overview(message, telegram_id, language)
    except Exception:
        LOGGER.exception("Failed to load settings")
        await send_error_message(message, language, "settings", route="settings")


async def on_settings_menu(callback: CallbackQuery) -> None:
    current_language = await user_language(callback.from_user.id)
    try:
        settings = await api.settings(callback.from_user.id)
        mode = callback.data.split(":")[-1]
        await update_settings_message(callback, settings, mode)
        await callback.answer()
    except Exception:
        LOGGER.exception("Failed to open settings submenu")
        await callback.answer(tr("generic_error", current_language), show_alert=True)


async def on_settings_toggle(callback: CallbackQuery) -> None:
    current_language = await user_language(callback.from_user.id)
    try:
        settings = await api.settings(callback.from_user.id)
        updated = await api.update_settings(callback.from_user.id, {"reminders_enabled": not settings.get("reminders_enabled", True)})
        await update_settings_message(callback, updated)
        await callback.answer(tr("settings_saved", normalize_language(updated.get("interface_language"))))
    except Exception:
        LOGGER.exception("Failed to toggle settings")
        await callback.answer(tr("generic_error", current_language), show_alert=True)


async def on_settings_set(callback: CallbackQuery) -> None:
    fallback_language = await user_language(callback.from_user.id)
    try:
        _, _, field, raw_value = callback.data.split(":")
        payload: dict[str, Any]
        if field == "ui":
            payload = {"interface_language": raw_value}
        elif field == "exp":
            payload = {"explanation_language": raw_value}
        elif field == "time":
            payload = {"reminder_time": f"{raw_value[:2]}:{raw_value[2:]}"}
        elif field == "style":
            payload = {"learning_style": raw_value}
        elif field == "difficulty":
            payload = {"difficulty": raw_value}
        else:
            payload = {}
        updated = await api.update_settings(callback.from_user.id, payload)
        language = normalize_language(updated.get("interface_language"))
        await ensure_menu_button(callback.message.bot, callback.from_user.id, language)
        await update_settings_message(callback, updated)
        await callback.answer(tr("settings_saved", language))
    except Exception:
        LOGGER.exception("Failed to set settings value")
        await callback.answer(tr("generic_error", fallback_language), show_alert=True)


async def on_settings_back(callback: CallbackQuery) -> None:
    current_language = await user_language(callback.from_user.id)
    try:
        settings = await api.settings(callback.from_user.id)
        await update_settings_message(callback, settings)
        await callback.answer()
    except Exception:
        LOGGER.exception("Failed to return to settings overview")
        await callback.answer(tr("generic_error", current_language), show_alert=True)


async def cmd_help(message: Message, state: FSMContext) -> None:
    await pause_text_input(state)
    language = await user_language(chat_user_id(message))
    commands = command_descriptions(language)
    lines = [tr("help_title", language), ""]
    for command, description in commands:
        lines.append(f"/{command} — {description}")
    lines.extend(["", tr("help_hint", language)])
    await message.answer(
        "\n".join(lines),
        reply_markup=content_actions_keyboard(
            [(button("menu", language), "nav:menu"), (button("settings", language), "nav:settings")],
            web_route="home",
            web_label=button("open_app", language),
        ),
    )


async def on_nav(callback: CallbackQuery, state: FSMContext) -> None:
    action = callback.data.split(":", 1)[1]
    await callback.answer()
    await dispatch_navigation(callback.message, state, action)


async def on_reply_navigation(message: Message, state: FSMContext) -> None:
    action = action_from_label(message.text)
    if not action:
        return
    await dispatch_navigation(message, state, action)


async def cmd_preview_lesson(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=1)
    telegram_id = chat_user_id(message)
    language = await user_language(telegram_id)
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Usage: /preview_lesson <lesson_id>")
        return
    try:
        lesson = await fetch_lesson(telegram_id, int(parts[1]))
        title = localize(lesson.get("title"), language, "Lesson")
        summary = localize(lesson.get("summary"), language)
        await message.answer(
            f"{title}\n\n{shorten(summary, 220)}".strip(),
            reply_markup=share_link_keyboard(button("open_lesson", language), "learn", lesson=str(lesson["id"])),
        )
    except Exception:
        LOGGER.exception("Failed to preview lesson")
        await send_error_message(message, language, "lesson", route="learn")


async def cmd_preview_scenario(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=1)
    telegram_id = chat_user_id(message)
    language = await user_language(telegram_id)
    if len(parts) < 2:
        await message.answer("Usage: /preview_scenario <scenario_id_or_slug>")
        return
    try:
        detail = await api.scenario_detail(telegram_id, parts[1])
        await message.answer(
            dialogue_preview_message(language, [], detail),
            reply_markup=share_link_keyboard(button("open_dialogue", language), "scenarios", scenario=str(detail["slug"])),
        )
    except Exception:
        LOGGER.exception("Failed to preview scenario")
        await send_error_message(message, language, "dialogue", route="scenarios")


async def cmd_share_lesson(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Usage: /share_lesson <lesson_id>")
        return
    await message.answer(webapp_url("learn", lesson=parts[1]), reply_markup=share_link_keyboard("Open lesson", "learn", lesson=parts[1]))


async def cmd_share_scenario(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /share_scenario <scenario_id_or_slug>")
        return
    await message.answer(webapp_url("scenarios", scenario=parts[1]), reply_markup=share_link_keyboard("Open scenario", "scenarios", scenario=parts[1]))


async def on_error(event: ErrorEvent) -> bool:
    LOGGER.error("Bot update failed", exc_info=(type(event.exception), event.exception, event.exception.__traceback__))
    return True


async def configure_bot(bot: Bot) -> None:
    scope = BotCommandScopeAllPrivateChats()
    await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text=button("app", "en"), web_app=WebAppInfo(url=webapp_url("home"))))
    await bot.set_my_commands([BotCommand(command=name, description=description) for name, description in command_descriptions("en")], scope=scope)
    for language in ("ru", "uz"):
        await bot.set_my_commands(
            [BotCommand(command=name, description=description) for name, description in command_descriptions(language)],
            scope=scope,
            language_code=language,
        )


def register(dp: Dispatcher) -> None:
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_admin, Command("admin"))
    dp.message.register(cmd_menu, Command("menu"))
    dp.message.register(cmd_lesson, Command("lesson"))
    dp.message.register(cmd_dialogue, Command("dialogue"))
    dp.message.register(cmd_preview_lesson, Command("preview_lesson"))
    dp.message.register(cmd_preview_scenario, Command("preview_scenario"))
    dp.message.register(cmd_share_lesson, Command("share_lesson"))
    dp.message.register(cmd_share_scenario, Command("share_scenario"))
    dp.message.register(cmd_quiz, Command("quiz"))
    dp.message.register(cmd_plan, Command("plan"))
    dp.message.register(cmd_streak, Command("streak"))
    dp.message.register(cmd_review, Command("review"))
    dp.message.register(cmd_mistakes, Command("mistakes"))
    dp.message.register(cmd_grammar, Command("grammar"))
    dp.message.register(cmd_words, Command("words"))
    dp.message.register(cmd_progress, Command("progress"))
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_settings, Command("settings"))
    dp.message.register(on_text_answer, LessonFlow.answering_text)
    dp.message.register(on_reply_navigation, F.text)
    dp.callback_query.register(on_language, F.data.startswith("onboarding:lang:"))
    dp.callback_query.register(on_level, F.data.startswith("onboarding:level:"))
    dp.callback_query.register(on_time, F.data.startswith("onboarding:time:"))
    dp.callback_query.register(on_style, F.data.startswith("onboarding:style:"))
    dp.callback_query.register(on_nav, F.data.startswith("nav:"))
    dp.callback_query.register(on_lesson_answer, F.data.startswith("lesson:answer:"))
    dp.callback_query.register(on_review, F.data.startswith("review:submit:"))
    dp.callback_query.register(on_dialogue_topic, F.data.startswith("dialogue:topic:"))
    dp.callback_query.register(on_quiz_answer, F.data.startswith("quiz:answer:"))
    dp.callback_query.register(on_quiz_review, F.data.startswith("quiz:review:"))
    dp.callback_query.register(on_quiz_scenario, F.data.startswith("quiz:scenario:"))
    dp.callback_query.register(on_settings_menu, F.data.startswith("settings:menu:"))
    dp.callback_query.register(on_settings_toggle, F.data == "settings:toggle:reminders")
    dp.callback_query.register(on_settings_set, F.data.startswith("settings:set:"))
    dp.callback_query.register(on_settings_back, F.data == "settings:back")
    dp.errors.register(on_error)


async def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")
    bot = Bot(token=token)
    dp = Dispatcher(storage=MemoryStorage())
    register(dp)
    await configure_bot(bot)
    try:
        await dp.start_polling(bot)
    finally:
        await api.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
