SUPPORTED_LANGUAGES = ("ru", "uz", "en")
BUNDLE_CACHE: dict[str, dict[str, str]] = {}


TEXT = {
    "choose_language": {
        "ru": "Выберите язык интерфейса:",
        "uz": "Interfeys tilini tanlang:",
        "en": "Choose interface language:",
    },
    "choose_level": {
        "ru": "Выберите стартовый уровень:",
        "uz": "Boshlang'ich darajani tanlang:",
        "en": "Choose your starting level:",
    },
    "choose_time": {
        "ru": "Сколько минут в день удобно заниматься?",
        "uz": "Kuniga necha daqiqa o'qish qulay?",
        "en": "How many minutes a day feels realistic?",
    },
    "choose_style": {
        "ru": "Какой формат вам ближе?",
        "uz": "Qaysi usul sizga mos?",
        "en": "Which learning style fits you best?",
    },
    "onboarded": {
        "ru": "Маршрут готов. Можно начинать.",
        "uz": "Yo'l tayyor. Boshlash mumkin.",
        "en": "Your path is ready.",
    },
    "menu_title": {
        "ru": "Главное меню",
        "uz": "Asosiy menyu",
        "en": "Main menu",
    },
    "menu_subtitle": {
        "ru": "Продолжайте урок, быстрый повтор, диалоги и библиотеку из одной клавиатуры.",
        "uz": "Dars, tezkor takror, dialog va kutubxona bitta klaviaturada.",
        "en": "Continue lessons, quick review, dialogue practice, and the library from one keyboard.",
    },
    "menu_resume_lesson": {
        "ru": "Есть незавершённый урок.",
        "uz": "Tugallanmagan dars bor.",
        "en": "You can resume a lesson.",
    },
    "menu_resume_quiz": {
        "ru": "Короткий квиз ещё открыт.",
        "uz": "Qisqa quiz hali ochiq.",
        "en": "A short quiz is still open.",
    },
    "menu_hint": {
        "ru": "Кнопка Menu и кнопка Mini App ниже открывают полную версию.",
        "uz": "Menu tugmasi va pastdagi Mini App tugmasi to'liq ilovani ochadi.",
        "en": "The Menu button and the Mini App button open the full app.",
    },
    "lesson_heading": {
        "ru": "Урок",
        "uz": "Dars",
        "en": "Lesson",
    },
    "lesson_resumed": {
        "ru": "Продолжаем с текущего шага.",
        "uz": "Joriy bosqichdan davom etamiz.",
        "en": "Resuming from the current step.",
    },
    "lesson_no_resume": {
        "ru": "Сохранённый шаг недоступен. Открываю актуальный урок.",
        "uz": "Saqlangan bosqich topilmadi. Joriy dars ochiladi.",
        "en": "The saved step is no longer available. Opening the current lesson.",
    },
    "lesson_complete": {
        "ru": "Урок завершён. Повтор добавлен в очередь.",
        "uz": "Dars tugadi. Takror navbatga qo'shildi.",
        "en": "Lesson complete. A review item was scheduled.",
    },
    "lesson_finished_empty": {
        "ru": "В уроке пока нет упражнений. Откройте полную версию или перейдите к следующему материалу.",
        "uz": "Bu darsda hozircha mashq yo'q. To'liq ilovani oching yoki keyingi materialga o'ting.",
        "en": "This lesson has no exercises yet. Open the full app or move to the next material.",
    },
    "lesson_prompt_text": {
        "ru": "Введите ответ по-корейски.",
        "uz": "Javobni koreys tilida yozing.",
        "en": "Type your answer in Korean.",
    },
    "correct": {
        "ru": "Верно.",
        "uz": "To'g'ri.",
        "en": "Correct.",
    },
    "wrong": {
        "ru": "Пока нет. Этот пункт вернётся в повторении.",
        "uz": "Hali emas. Bu element keyin takrorlanadi.",
        "en": "Not quite. This item will come back in review.",
    },
    "no_lesson": {
        "ru": "Сейчас нет доступного урока.",
        "uz": "Hozircha ochiq dars yo'q.",
        "en": "No lesson is available right now.",
    },
    "no_review": {
        "ru": "Сейчас нет срочного повтора.",
        "uz": "Hozir tezkor takror yo'q.",
        "en": "No quick review is due right now.",
    },
    "no_mistakes": {
        "ru": "Очередь ошибок пока пуста.",
        "uz": "Xatolar navbati hozircha bo'sh.",
        "en": "Your mistake queue is empty right now.",
    },
    "review_saved": {
        "ru": "Следующий интервал: {interval}.",
        "uz": "Keyingi interval: {interval}.",
        "en": "Next interval: {interval}.",
    },
    "review_done": {
        "ru": "Быстрый повтор закрыт.",
        "uz": "Tezkor takror tugadi.",
        "en": "Quick review complete.",
    },
    "mistakes_done": {
        "ru": "Очередь ошибок закрыта.",
        "uz": "Xatolar navbati tugadi.",
        "en": "Mistake review complete.",
    },
    "grammar_title": {
        "ru": "Грамматика",
        "uz": "Grammatika",
        "en": "Grammar",
    },
    "grammar_empty": {
        "ru": "Пока нет опубликованных заметок по грамматике.",
        "uz": "Hozircha grammatika bo'yicha material yo'q.",
        "en": "No grammar notes are published yet.",
    },
    "words_title": {
        "ru": "Слова",
        "uz": "So'zlar",
        "en": "Words",
    },
    "words_empty": {
        "ru": "Пока нет опубликованных слов.",
        "uz": "Hozircha e'lon qilingan so'zlar yo'q.",
        "en": "No vocabulary is published yet.",
    },
    "dialogue_title": {
        "ru": "Диалоги",
        "uz": "Dialoglar",
        "en": "Dialogue",
    },
    "dialogue_empty": {
        "ru": "Сценарии по этой теме пока не готовы.",
        "uz": "Bu mavzu uchun ssenariylar hozircha tayyor emas.",
        "en": "No scenarios are ready for this topic yet.",
    },
    "quiz_title": {
        "ru": "Короткий квиз",
        "uz": "Qisqa quiz",
        "en": "Short quiz",
    },
    "quiz_empty": {
        "ru": "Для короткого квиза пока не хватает материала.",
        "uz": "Qisqa quiz uchun hozircha yetarli material yo'q.",
        "en": "There is not enough content for a short quiz yet.",
    },
    "quiz_complete": {
        "ru": "Квиз завершён.",
        "uz": "Quiz tugadi.",
        "en": "Quiz complete.",
    },
    "quiz_show_answer": {
        "ru": "Ответ: {answer}",
        "uz": "Javob: {answer}",
        "en": "Answer: {answer}",
    },
    "progress_title": {
        "ru": "Прогресс",
        "uz": "Progress",
        "en": "Progress",
    },
    "streak_title": {
        "ru": "Серия",
        "uz": "Seriya",
        "en": "Streak",
    },
    "settings_title": {
        "ru": "Настройки",
        "uz": "Sozlamalar",
        "en": "Settings",
    },
    "settings_saved": {
        "ru": "Настройки обновлены.",
        "uz": "Sozlamalar yangilandi.",
        "en": "Settings updated.",
    },
    "settings_language_section": {
        "ru": "Язык интерфейса и объяснений",
        "uz": "Interfeys va tushuntirish tili",
        "en": "Interface and explanation language",
    },
    "settings_reminder_section": {
        "ru": "Напоминания",
        "uz": "Eslatmalar",
        "en": "Reminders",
    },
    "settings_learning_section": {
        "ru": "Стиль обучения",
        "uz": "O'rganish usuli",
        "en": "Learning style",
    },
    "settings_difficulty_section": {
        "ru": "Сложность",
        "uz": "Qiyinlik",
        "en": "Difficulty",
    },
    "help_title": {
        "ru": "Команды",
        "uz": "Buyruqlar",
        "en": "Commands",
    },
    "help_hint": {
        "ru": "Mini App удобнее для длинных уроков, деталей слов и сценариев.",
        "uz": "Uzoq darslar, so'z tafsilotlari va ssenariylar uchun Mini App qulayroq.",
        "en": "The Mini App is better for long lessons, word details, and scenario playback.",
    },
    "curriculum_title": {
        "ru": "Карта маршрута",
        "uz": "Yo'l xaritasi",
        "en": "Curriculum map",
    },
    "generic_error": {
        "ru": "Не удалось загрузить данные. Попробуйте ещё раз.",
        "uz": "Ma'lumotni yuklab bo'lmadi. Yana urinib ko'ring.",
        "en": "Could not load this right now. Please try again.",
    },
    "missing_content": {
        "ru": "Контент пока недоступен.",
        "uz": "Kontent hozircha mavjud emas.",
        "en": "This content is not available yet.",
    },
    "admin_only": {
        "ru": "Эта команда доступна только авторизованным администраторам.",
        "uz": "Bu buyruq faqat ruxsatli adminlar uchun.",
        "en": "This command is only available to authorized admins.",
    },
    "label_next": {
        "ru": "Дальше",
        "uz": "Keyingi",
        "en": "Next",
    },
    "label_due": {
        "ru": "К сроку",
        "uz": "Navbatda",
        "en": "Due",
    },
    "label_module": {
        "ru": "Модуль",
        "uz": "Modul",
        "en": "Module",
    },
    "label_current": {
        "ru": "Сейчас",
        "uz": "Hozir",
        "en": "Current",
    },
    "label_next_milestone": {
        "ru": "Следующая цель",
        "uz": "Keyingi maqsad",
        "en": "Next milestone",
    },
    "label_usage": {
        "ru": "Использование",
        "uz": "Ishlatish",
        "en": "Usage",
    },
    "label_watch": {
        "ru": "Осторожно",
        "uz": "E'tibor",
        "en": "Watch",
    },
    "label_note": {
        "ru": "Заметка",
        "uz": "Izoh",
        "en": "Note",
    },
    "label_ui": {
        "ru": "Интерфейс",
        "uz": "Interfeys",
        "en": "UI",
    },
    "label_explain": {
        "ru": "Объяснения",
        "uz": "Izohlar",
        "en": "Explain",
    },
    "label_library": {
        "ru": "Библиотека",
        "uz": "Kutubxona",
        "en": "Library",
    },
    "unknown_deep_link": {
        "ru": "Ссылка устарела или больше недоступна. Показываю актуальное меню.",
        "uz": "Havola eskirgan yoki endi mavjud emas. Joriy menyu ko'rsatiladi.",
        "en": "That link is outdated or no longer available. Showing the current menu.",
    },
    "interval_days": {
        "ru": "{days} дн.",
        "uz": "{days} kun",
        "en": "{days} day(s)",
    },
}


BUTTONS = {
    "lesson": {"ru": "Урок", "uz": "Dars", "en": "Lesson"},
    "review": {"ru": "Повтор", "uz": "Takror", "en": "Review"},
    "dialogue": {"ru": "Диалог", "uz": "Dialog", "en": "Dialogue"},
    "library": {"ru": "Библиотека", "uz": "Kutubxona", "en": "Library"},
    "quiz": {"ru": "Квиз", "uz": "Quiz", "en": "Quiz"},
    "progress": {"ru": "Прогресс", "uz": "Progress", "en": "Progress"},
    "streak": {"ru": "Серия", "uz": "Seriya", "en": "Streak"},
    "settings": {"ru": "Настройки", "uz": "Sozlamalar", "en": "Settings"},
    "help": {"ru": "Помощь", "uz": "Yordam", "en": "Help"},
    "menu": {"ru": "Меню", "uz": "Menyu", "en": "Menu"},
    "app": {"ru": "Mini App", "uz": "Mini App", "en": "Mini App"},
    "resume": {"ru": "Продолжить", "uz": "Davom etish", "en": "Continue"},
    "quick_review": {"ru": "Быстрый повтор", "uz": "Tezkor takror", "en": "Quick review"},
    "mistakes": {"ru": "Ошибки", "uz": "Xatolar", "en": "Mistakes"},
    "open_app": {"ru": "Открыть Mini App", "uz": "Mini App ochish", "en": "Open Mini App"},
    "open_lesson": {"ru": "Открыть урок", "uz": "Darsni ochish", "en": "Open lesson"},
    "open_review": {"ru": "Открыть повтор", "uz": "Takrorni ochish", "en": "Open review"},
    "open_dialogue": {"ru": "Открыть сценарий", "uz": "Ssenariyni ochish", "en": "Open scenario"},
    "open_library": {"ru": "Открыть библиотеку", "uz": "Kutubxonani ochish", "en": "Open library"},
    "open_settings": {"ru": "Открыть настройки", "uz": "Sozlamalarni ochish", "en": "Open settings"},
    "details": {"ru": "Подробнее", "uz": "Batafsil", "en": "Details"},
    "retry": {"ru": "Повторить", "uz": "Qayta urinish", "en": "Retry"},
    "more": {"ru": "Ещё", "uz": "Yana", "en": "More"},
    "knew": {"ru": "Знал", "uz": "Bildim", "en": "Knew it"},
    "missed": {"ru": "Не вспомнил", "uz": "Esga tushmadi", "en": "Missed it"},
    "show_answer": {"ru": "Показать ответ", "uz": "Javobni ko'rsatish", "en": "Show answer"},
    "back": {"ru": "Назад", "uz": "Orqaga", "en": "Back"},
    "language": {"ru": "Язык", "uz": "Til", "en": "Language"},
    "explanations": {"ru": "Объяснения", "uz": "Izohlar", "en": "Explanations"},
    "reminders_on": {"ru": "Напоминания: вкл", "uz": "Eslatma: yoqilgan", "en": "Reminders: on"},
    "reminders_off": {"ru": "Напоминания: выкл", "uz": "Eslatma: o'chirilgan", "en": "Reminders: off"},
    "reminder_time": {"ru": "Время", "uz": "Vaqt", "en": "Time"},
    "style": {"ru": "Стиль", "uz": "Uslub", "en": "Style"},
    "difficulty": {"ru": "Сложность", "uz": "Qiyinlik", "en": "Difficulty"},
    "save": {"ru": "Сохранить", "uz": "Saqlash", "en": "Save"},
    "admin": {"ru": "Admin Mini App", "uz": "Admin Mini App", "en": "Admin Mini App"},
}


TOPICS = {
    "all": {"ru": "Все", "uz": "Barchasi", "en": "All"},
    "daily_life": {"ru": "Повседневное", "uz": "Kundalik", "en": "Daily life"},
    "food": {"ru": "Еда", "uz": "Ovqat", "en": "Food"},
    "shopping": {"ru": "Покупки", "uz": "Xarid", "en": "Shopping"},
    "transport": {"ru": "Транспорт", "uz": "Transport", "en": "Transport"},
    "study": {"ru": "Учёба", "uz": "O'qish", "en": "Study"},
    "work": {"ru": "Работа", "uz": "Ish", "en": "Work"},
    "health": {"ru": "Здоровье", "uz": "Salomatlik", "en": "Health"},
}


LANGUAGE_NAMES = {
    "ru": {"ru": "Русский", "uz": "Ruscha", "en": "Russian"},
    "uz": {"ru": "Узбекский", "uz": "O'zbekcha", "en": "Uzbek"},
    "en": {"ru": "Английский", "uz": "Inglizcha", "en": "English"},
}


LEVELS = {
    "complete_beginner": {"ru": "С нуля", "uz": "Noldan", "en": "From zero"},
    "knows_hangul": {"ru": "Знаю хангыль", "uz": "Hangulni bilaman", "en": "Knows Hangul"},
    "knows_basics": {"ru": "Знаю основы", "uz": "Asoslarni bilaman", "en": "Knows basics"},
}


TIMES = {
    "5": {"ru": "5 мин", "uz": "5 daqiqa", "en": "5 min"},
    "10": {"ru": "10 мин", "uz": "10 daqiqa", "en": "10 min"},
    "20": {"ru": "20 мин", "uz": "20 daqiqa", "en": "20 min"},
    "30": {"ru": "30 мин", "uz": "30 daqiqa", "en": "30 min"},
}


STYLES = {
    "grammar_first": {"ru": "Сначала грамматика", "uz": "Avval grammatika", "en": "Grammar first"},
    "mixed": {"ru": "Смешанный", "uz": "Aralash", "en": "Mixed"},
    "phrase_first": {"ru": "Сначала фразы", "uz": "Avval iboralar", "en": "Phrase first"},
}


DIFFICULTY = {
    "easy": {"ru": "Легко", "uz": "Oson", "en": "Easy"},
    "normal": {"ru": "Нормально", "uz": "O'rtacha", "en": "Normal"},
    "hard": {"ru": "Сложно", "uz": "Qiyin", "en": "Hard"},
}


COMMANDS = {
    "start": {"ru": "запуск и глубокие ссылки", "uz": "ishga tushirish va deep link", "en": "start and deep links"},
    "menu": {"ru": "главная навигация", "uz": "asosiy navigatsiya", "en": "main navigation"},
    "lesson": {"ru": "продолжить урок", "uz": "darsni davom ettirish", "en": "continue lesson"},
    "review": {"ru": "быстрый повтор", "uz": "tezkor takror", "en": "quick review"},
    "mistakes": {"ru": "повтор ошибок", "uz": "xatolarni takrorlash", "en": "mistake review"},
    "grammar": {"ru": "краткий просмотр грамматики", "uz": "grammatika ko'rinishi", "en": "preview grammar"},
    "words": {"ru": "краткий просмотр слов", "uz": "so'zlar ko'rinishi", "en": "preview words"},
    "dialogue": {"ru": "сценарии и диалоги", "uz": "ssenariy va dialoglar", "en": "scenario practice"},
    "quiz": {"ru": "короткая смешанная практика", "uz": "qisqa aralash mashq", "en": "short mixed practice"},
    "progress": {"ru": "общий прогресс", "uz": "umumiy progress", "en": "overall progress"},
    "streak": {"ru": "серия и XP", "uz": "seriya va XP", "en": "streak and XP"},
    "settings": {"ru": "полезные настройки", "uz": "foydali sozlamalar", "en": "useful settings"},
    "help": {"ru": "список команд", "uz": "buyruqlar ro'yxati", "en": "command list"},
}


TOP_LEVEL_ACTIONS = ("lesson", "review", "dialogue", "library", "quiz", "progress", "streak", "settings", "help", "app")


def cache_bundle(language: str, bundle: dict[str, str]) -> None:
    BUNDLE_CACHE[normalize_language(language)] = dict(bundle)


def normalize_language(language: str | None = "en") -> str:
    if language in SUPPORTED_LANGUAGES:
        return str(language)
    return "en"


def tr(key: str, language: str | None = "en", **kwargs: str | int | float) -> str:
    lang = normalize_language(language)
    bundle = BUNDLE_CACHE.get(lang, {})
    template = bundle.get(f"text.{key}") or TEXT.get(key, {}).get(lang) or TEXT.get(key, {}).get("en") or key
    if kwargs:
        return template.format(**kwargs)
    return template


def button(key: str, language: str | None = "en") -> str:
    lang = normalize_language(language)
    bundle = BUNDLE_CACHE.get(lang, {})
    return bundle.get(f"button.{key}") or BUTTONS.get(key, {}).get(lang) or BUTTONS.get(key, {}).get("en") or key


def topic_label(topic: str, language: str | None = "en") -> str:
    lang = normalize_language(language)
    bundle = BUNDLE_CACHE.get(lang, {})
    return bundle.get(f"topic.{topic}") or TOPICS.get(topic, {}).get(lang) or TOPICS.get(topic, {}).get("en") or topic.replace("_", " ")


def language_name(language_code: str, interface_language: str | None = "en") -> str:
    lang = normalize_language(interface_language)
    return LANGUAGE_NAMES.get(language_code, {}).get(lang) or LANGUAGE_NAMES.get(language_code, {}).get("en") or language_code


def level_choices(language: str | None = "en") -> list[tuple[str, str]]:
    lang = normalize_language(language)
    return [(LEVELS[value][lang], value) for value in ("complete_beginner", "knows_hangul", "knows_basics")]


def time_choices(language: str | None = "en") -> list[tuple[str, str]]:
    lang = normalize_language(language)
    return [(TIMES[value][lang], value) for value in ("5", "10", "20", "30")]


def style_choices(language: str | None = "en") -> list[tuple[str, str]]:
    lang = normalize_language(language)
    return [(STYLES[value][lang], value) for value in ("grammar_first", "mixed", "phrase_first")]


def difficulty_label(value: str, language: str | None = "en") -> str:
    lang = normalize_language(language)
    return DIFFICULTY.get(value, {}).get(lang) or DIFFICULTY.get(value, {}).get("en") or value.replace("_", " ")


def style_label(value: str, language: str | None = "en") -> str:
    lang = normalize_language(language)
    return STYLES.get(value, {}).get(lang) or STYLES.get(value, {}).get("en") or value.replace("_", " ")


def command_descriptions(language: str | None = "en") -> list[tuple[str, str]]:
    lang = normalize_language(language)
    ordered = ("start", "menu", "lesson", "review", "mistakes", "grammar", "words", "dialogue", "quiz", "progress", "streak", "settings", "help")
    return [(name, COMMANDS[name][lang]) for name in ordered]


def action_from_label(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower()
    for action in TOP_LEVEL_ACTIONS:
        labels = {BUTTONS[action][language].lower() for language in SUPPORTED_LANGUAGES}
        if normalized in labels:
            return action
    return None
