import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo

from bot.texts import button, difficulty_label, style_choices, time_choices, topic_label, tr


def webapp_url(route: str | None = None, **params: str) -> str:
    current = os.getenv("TELEGRAM_WEBAPP_URL", "http://localhost:5173")
    parts = urlsplit(current)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    if route:
        query["screen"] = route
    for key, value in params.items():
        if value:
            query[key] = value
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def startapp_url(start_param: str, mode: str = "fullscreen") -> str | None:
    bot_username = os.getenv("TELEGRAM_BOT_USERNAME", "").strip()
    short_name = os.getenv("TELEGRAM_MINI_APP_SHORT_NAME", "").strip()
    if not bot_username:
        return None
    base = f"https://t.me/{bot_username}/{short_name}" if short_name else f"https://t.me/{bot_username}"
    query = {"startapp": start_param}
    if mode != "normal":
        query["mode"] = mode
    return f"{base}?{urlencode(query)}"


def route_start_param(route: str, **params: str) -> str:
    if route in {"learn", "lesson"} and params.get("lesson"):
        return f"lesson_{params['lesson']}"
    if route == "scenarios" and params.get("scenario"):
        return f"scenario_{params['scenario']}"
    if route == "library" and params.get("grammar"):
        return f"grammar_{params['grammar']}"
    if route == "library" and params.get("word"):
        return f"word_{params['word']}"
    if route == "review" and params.get("mode") == "mistakes":
        return "review_mistakes"
    if route == "review":
        return "review_due"
    if route == "settings":
        return "settings"
    if route == "progress":
        return "progress"
    if route == "scenarios":
        return "dialogue"
    if route == "library" and params.get("tab") == "grammar":
        return "grammar"
    if route == "library":
        return "vocab"
    if route == "admin":
        return "admin"
    return "screen_home"


def main_reply_keyboard(language: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=button("lesson", language)), KeyboardButton(text=button("review", language))],
            [KeyboardButton(text=button("dialogue", language)), KeyboardButton(text=button("library", language))],
            [KeyboardButton(text=button("quiz", language)), KeyboardButton(text=button("progress", language))],
            [KeyboardButton(text=button("streak", language)), KeyboardButton(text=button("settings", language))],
            [
                KeyboardButton(text=button("help", language)),
                KeyboardButton(text=button("app", language), web_app=WebAppInfo(url=webapp_url("home"))),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder=tr("menu_title", language),
    )


def onboarding_language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Русский", callback_data="onboarding:lang:ru"),
                InlineKeyboardButton(text="O'zbek", callback_data="onboarding:lang:uz"),
                InlineKeyboardButton(text="English", callback_data="onboarding:lang:en"),
            ]
        ]
    )


def options_keyboard(prefix: str, options: list[tuple[str, str]], columns: int = 1) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    current_row: list[InlineKeyboardButton] = []
    for label, value in options:
        current_row.append(InlineKeyboardButton(text=label, callback_data=f"{prefix}:{value}"))
        if len(current_row) == columns:
            rows.append(current_row)
            current_row = []
    if current_row:
        rows.append(current_row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def content_actions_keyboard(
    callbacks: list[tuple[str, str]] | None = None,
    *,
    web_route: str | None = None,
    web_label: str | None = None,
    web_params: dict[str, str] | None = None,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if callbacks:
        row: list[InlineKeyboardButton] = []
        for label, callback_data in callbacks:
            row.append(InlineKeyboardButton(text=label, callback_data=callback_data))
            if len(row) == 2:
                rows.append(row)
                row = []
        if row:
            rows.append(row)
    if web_route or web_label:
        rows.append(
            [
                InlineKeyboardButton(
                    text=web_label or "Mini App",
                    web_app=WebAppInfo(url=webapp_url(web_route, **(web_params or {}))),
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def mini_app_keyboard(route: str | None = None, label: str | None = None, **params: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label or "Mini App", web_app=WebAppInfo(url=webapp_url(route, **params)))],
        ]
    )


def admin_mini_app_keyboard(language: str) -> InlineKeyboardMarkup:
    return mini_app_keyboard("admin", button("admin", language))


def share_link_keyboard(label: str, route: str, **params: str) -> InlineKeyboardMarkup:
    deep_link = startapp_url(route_start_param(route, **params))
    if deep_link:
        return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=label, url=deep_link)]])
    return mini_app_keyboard(route, label, **params)


def lesson_exercise_keyboard(exercise: dict, language: str, namespace: str = "lesson") -> InlineKeyboardMarkup | None:
    options = sorted(exercise.get("options") or [], key=lambda item: item.get("order_index", 0))
    if not options:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=option.get("label", {}).get(language) or option.get("label", {}).get("en") or option.get("value", ""),
                    callback_data=f"{namespace}:answer:{exercise['id']}:{index}",
                )
            ]
            for index, option in enumerate(options)
        ]
    )


def review_keyboard(review_item_id: int, queue_kind: str, language: str) -> InlineKeyboardMarkup:
    return content_actions_keyboard(
        [
            (button("knew", language), f"review:submit:{queue_kind}:{review_item_id}:4"),
            (button("missed", language), f"review:submit:{queue_kind}:{review_item_id}:1"),
        ],
        web_route="review",
        web_label=button("open_review", language),
    )


def scenario_topics_keyboard(language: str) -> InlineKeyboardMarkup:
    return options_keyboard(
        "dialogue:topic",
        [
            (topic_label("food", language), "food"),
            (topic_label("shopping", language), "shopping"),
            (topic_label("transport", language), "transport"),
            (topic_label("study", language), "study"),
            (topic_label("work", language), "work"),
            (topic_label("daily_life", language), "daily_life"),
        ],
        columns=2,
    )


def settings_home_keyboard(language: str, reminders_enabled: bool) -> InlineKeyboardMarkup:
    reminder_label = button("reminders_on", language) if reminders_enabled else button("reminders_off", language)
    return content_actions_keyboard(
        [
            (button("language", language), "settings:menu:ui"),
            (button("explanations", language), "settings:menu:exp"),
            (reminder_label, "settings:toggle:reminders"),
            (button("reminder_time", language), "settings:menu:time"),
            (button("style", language), "settings:menu:style"),
            (button("difficulty", language), "settings:menu:difficulty"),
        ],
        web_route="settings",
        web_label=button("open_settings", language),
    )


def settings_language_keyboard(language: str, target: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Русский", callback_data=f"settings:set:{target}:ru"),
                InlineKeyboardButton(text="O'zbek", callback_data=f"settings:set:{target}:uz"),
                InlineKeyboardButton(text="English", callback_data=f"settings:set:{target}:en"),
            ],
            [InlineKeyboardButton(text=button("back", language), callback_data="settings:back")],
        ]
    )


def settings_time_keyboard(language: str) -> InlineKeyboardMarkup:
    presets = [("07:00", "0700"), ("12:00", "1200"), ("19:00", "1900"), ("21:00", "2100")]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=label, callback_data=f"settings:set:time:{value}")
                for label, value in presets[:2]
            ],
            [
                InlineKeyboardButton(text=label, callback_data=f"settings:set:time:{value}")
                for label, value in presets[2:]
            ],
            [InlineKeyboardButton(text=button("back", language), callback_data="settings:back")],
        ]
    )


def settings_style_keyboard(language: str) -> InlineKeyboardMarkup:
    choices = style_choices(language)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"settings:set:style:{value}")]
            for label, value in choices
        ]
        + [[InlineKeyboardButton(text=button("back", language), callback_data="settings:back")]]
    )


def settings_difficulty_keyboard(language: str) -> InlineKeyboardMarkup:
    options = [(difficulty_label(value, language), value) for value in ("easy", "normal", "hard")]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"settings:set:difficulty:{value}")]
            for label, value in options
        ]
        + [[InlineKeyboardButton(text=button("back", language), callback_data="settings:back")]]
    )


def lesson_time_keyboard(language: str) -> InlineKeyboardMarkup:
    return options_keyboard("onboarding:time", time_choices(language), columns=2)
