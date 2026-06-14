from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from bot.texts import button, difficulty_label, style_choices, time_choices, topic_label, tr


def main_reply_keyboard(language: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=button("words", language))],
        ],
        is_persistent=True,
        resize_keyboard=True,
        input_field_placeholder=tr("words_title", language),
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
    del web_route
    del web_label
    del web_params
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
    return InlineKeyboardMarkup(inline_keyboard=rows)


def option_button_text(option: dict, language: str) -> str:
    label = option.get("label", {}).get(language) or option.get("label", {}).get("en") or option.get("value", "")
    return " ".join(str(label).split())


def should_use_two_columns(labels: list[str]) -> bool:
    if not 1 < len(labels) <= 4:
        return False
    return all(label and len(label) <= 18 and "\n" not in label for label in labels)


def lesson_exercise_keyboard(exercise: dict, language: str, namespace: str = "lesson") -> InlineKeyboardMarkup | None:
    options = sorted(exercise.get("options") or [], key=lambda item: item.get("order_index", 0))
    if not options:
        return None
    labels = [option_button_text(option, language) for option in options]
    columns = 2 if should_use_two_columns(labels) else 1
    rows: list[list[InlineKeyboardButton]] = []
    current_row: list[InlineKeyboardButton] = []
    for index, option in enumerate(options):
        current_row.append(
            InlineKeyboardButton(
                text=labels[index],
                callback_data=f"{namespace}:answer:{exercise['id']}:{index}",
            )
        )
        if len(current_row) == columns:
            rows.append(current_row)
            current_row = []
    if current_row:
        rows.append(current_row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def review_keyboard(review_item_id: int, queue_kind: str, language: str) -> InlineKeyboardMarkup:
    return content_actions_keyboard(
        [
            (button("knew", language), f"review:submit:{queue_kind}:{review_item_id}:4"),
            (button("missed", language), f"review:submit:{queue_kind}:{review_item_id}:1"),
        ]
    )


def result_action_keyboard(prefix: str, language: str, *, later: bool = False) -> InlineKeyboardMarkup:
    callbacks = [(tr("label_next", language), f"{prefix}:next")]
    if later:
        callbacks = [(tr("action_later", language), f"{prefix}:later")]
    return content_actions_keyboard(callbacks)


def lesson_result_keyboard(prefix: str, language: str) -> InlineKeyboardMarkup:
    return content_actions_keyboard(
        [
            (tr("label_next", language), f"{prefix}:next"),
            (tr("action_later", language), f"{prefix}:later"),
        ]
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
