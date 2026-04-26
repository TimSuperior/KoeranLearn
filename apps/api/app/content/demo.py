from __future__ import annotations

from sqlalchemy.orm import Session

from app.content.expanded import ensure_expanded_content
from app.models.schema import (
    Achievement,
    Course,
    Dialogue,
    ExampleSentence,
    Exercise,
    ExerciseOption,
    GrammarPoint,
    LearningPath,
    Lesson,
    Module,
    PremiumPack,
    Scenario,
    Vocabulary,
)


def loc(ru: str, uz: str, en: str) -> dict[str, str]:
    return {"ru": ru, "uz": uz, "en": en}


PATHS = [
    ("hangul-basics", loc("Хангыль и основы", "Hangul va asoslar", "Hangul and basics"), "korean_from_zero", "A0", False),
    ("survival-korean", loc("Корейский для выживания", "Kundalik zarur koreys tili", "Survival Korean"), "daily_life", "A0", False),
    ("core-grammar", loc("Базовая грамматика", "Asosiy grammatika", "Core grammar"), "grammar_focused", "A1", False),
    ("daily-life-korea", loc("Жизнь в Корее", "Koreyada kundalik hayot", "Daily life in Korea"), "daily_life", "A1", False),
    ("student-korea", loc("Студент в Корее", "Koreyada talaba", "Student in Korea"), "study_in_korea", "A1", True),
    ("work-eps", loc("Работа и EPS", "Ish va EPS", "Work and EPS"), "work_eps", "A1", True),
    ("theme-vocab", loc("Словарь по темам", "Mavzuli lug'at", "Vocabulary by themes"), "vocabulary_focused", "A0", False),
    ("politeness", loc("Вежливость и стили речи", "Hurmat va nutq uslublari", "Politeness and speech levels"), "daily_life", "A1", False),
]


VOCABULARY = [
    ("hello", "안녕하세요", "annyeonghaseyo", loc("Здравствуйте", "Salom (odobli)", "Hello"), "greetings"),
    ("thanks", "감사합니다", "gamsahamnida", loc("Спасибо", "Rahmat", "Thank you"), "greetings"),
    ("sorry", "죄송합니다", "joesonghamnida", loc("Извините", "Kechirasiz", "I am sorry"), "greetings"),
    ("yes", "네", "ne", loc("да", "ha", "yes"), "basics"),
    ("no", "아니요", "aniyo", loc("нет", "yo'q", "no"), "basics"),
    ("person", "사람", "saram", loc("человек", "odam", "person"), "people"),
    ("friend", "친구", "chingu", loc("друг", "do'st", "friend"), "people"),
    ("teacher", "선생님", "seonsaengnim", loc("учитель", "o'qituvchi", "teacher"), "people"),
    ("student", "학생", "haksaeng", loc("студент", "talaba", "student"), "study"),
    ("school", "학교", "hakgyo", loc("школа", "maktab", "school"), "study"),
    ("university", "대학교", "daehakgyo", loc("университет", "universitet", "university"), "study"),
    ("class", "수업", "sueop", loc("урок", "dars", "class"), "study"),
    ("home", "집", "jip", loc("дом", "uy", "home"), "daily_life"),
    ("room", "방", "bang", loc("комната", "xona", "room"), "daily_life"),
    ("water", "물", "mul", loc("вода", "suv", "water"), "food"),
    ("rice", "밥", "bap", loc("рис/еда", "guruch/ovqat", "rice/meal"), "food"),
    ("kimchi", "김치", "gimchi", loc("кимчи", "kimchi", "kimchi"), "food"),
    ("coffee", "커피", "keopi", loc("кофе", "qahva", "coffee"), "food"),
    ("restaurant", "식당", "sikdang", loc("столовая/ресторан", "oshxona/restoran", "restaurant"), "food"),
    ("market", "시장", "sijang", loc("рынок", "bozor", "market"), "shopping"),
    ("price", "가격", "gagyeok", loc("цена", "narx", "price"), "shopping"),
    ("money", "돈", "don", loc("деньги", "pul", "money"), "shopping"),
    ("card", "카드", "kadeu", loc("карта", "karta", "card"), "shopping"),
    ("cash", "현금", "hyeongeum", loc("наличные", "naqd pul", "cash"), "shopping"),
    ("subway", "지하철", "jihacheol", loc("метро", "metro", "subway"), "transport"),
    ("bus", "버스", "beoseu", loc("автобус", "avtobus", "bus"), "transport"),
    ("taxi", "택시", "taeksi", loc("такси", "taksi", "taxi"), "transport"),
    ("station", "역", "yeok", loc("станция", "bekat", "station"), "transport"),
    ("where", "어디", "eodi", loc("где/куда", "qayer", "where"), "questions"),
    ("what", "무엇", "mueot", loc("что", "nima", "what"), "questions"),
    ("when", "언제", "eonje", loc("когда", "qachon", "when"), "questions"),
    ("how_much", "얼마", "eolma", loc("сколько", "qancha", "how much"), "questions"),
    ("today", "오늘", "oneul", loc("сегодня", "bugun", "today"), "time"),
    ("tomorrow", "내일", "naeil", loc("завтра", "ertaga", "tomorrow"), "time"),
    ("yesterday", "어제", "eoje", loc("вчера", "kecha", "yesterday"), "time"),
    ("morning", "아침", "achim", loc("утро", "ertalab", "morning"), "time"),
    ("evening", "저녁", "jeonyeok", loc("вечер/ужин", "kechqurun/kechki ovqat", "evening/dinner"), "time"),
    ("work", "일", "il", loc("работа", "ish", "work"), "work"),
    ("company", "회사", "hoesa", loc("компания", "kompaniya", "company"), "work"),
    ("factory", "공장", "gongjang", loc("завод", "zavod", "factory"), "work"),
    ("boss", "사장님", "sajangnim", loc("директор/начальник", "boshliq", "boss"), "work"),
    ("coworker", "동료", "dongnyo", loc("коллега", "hamkasb", "coworker"), "work"),
    ("hospital", "병원", "byeongwon", loc("больница", "shifoxona", "hospital"), "health"),
    ("medicine", "약", "yak", loc("лекарство", "dori", "medicine"), "health"),
    ("pain", "아파요", "apayo", loc("болит", "og'riyapti", "hurts"), "health"),
    ("phone", "전화", "jeonhwa", loc("телефон/звонок", "telefon/qo'ng'iroq", "phone/call"), "daily_life"),
    ("address", "주소", "juso", loc("адрес", "manzil", "address"), "daily_life"),
    ("foreigner", "외국인", "oegugin", loc("иностранец", "chet ellik", "foreigner"), "daily_life"),
    ("korean_language", "한국어", "hangugeo", loc("корейский язык", "koreys tili", "Korean language"), "basics"),
    ("russia", "러시아", "reosia", loc("Россия", "Rossiya", "Russia"), "countries"),
    ("uzbekistan", "우즈베키스탄", "ujeubekiseutan", loc("Узбекистан", "O'zbekiston", "Uzbekistan"), "countries"),
    ("america", "미국", "miguk", loc("США", "AQSh", "USA"), "countries"),
    ("korea", "한국", "hanguk", loc("Корея", "Koreya", "Korea"), "countries"),
    ("go", "가다", "gada", loc("идти/ехать", "bormoq", "to go"), "verbs"),
    ("come", "오다", "oda", loc("приходить", "kelmoq", "to come"), "verbs"),
    ("eat", "먹다", "meokda", loc("есть", "yemoq", "to eat"), "verbs"),
    ("drink", "마시다", "masida", loc("пить", "ichmoq", "to drink"), "verbs"),
    ("study", "공부하다", "gongbuhada", loc("учиться", "o'qimoq", "to study"), "verbs"),
    ("work_do", "일하다", "ilhada", loc("работать", "ishlamoq", "to work"), "verbs"),
    ("buy", "사다", "sada", loc("покупать", "sotib olmoq", "to buy"), "verbs"),
    ("know", "알다", "alda", loc("знать", "bilmoq", "to know"), "verbs"),
    ("not_know", "모르다", "moreuda", loc("не знать", "bilmaslik", "not to know"), "verbs"),
    ("good", "좋다", "jota", loc("хороший", "yaxshi", "good"), "adjectives"),
    ("expensive", "비싸다", "bissada", loc("дорогой", "qimmat", "expensive"), "adjectives"),
    ("cheap", "싸다", "ssada", loc("дешевый", "arzon", "cheap"), "adjectives"),
]


GRAMMAR_POINTS = [
    ("topic-neun", "은/는", "particles", loc("Тема 은/는", "Mavzu 은/는", "Topic marker 은/는")),
    ("subject-i-ga", "이/가", "particles", loc("Подлежащее 이/가", "Ega 이/가", "Subject marker 이/가")),
    ("object-eul-reul", "을/를", "particles", loc("Объект 을/를", "To'ldiruvchi 을/를", "Object marker 을/를")),
    ("location-e", "에", "particles", loc("Место/направление 에", "Joy/yo'nalish 에", "Location/direction 에")),
    ("from-to", "에서/까지", "particles", loc("От/до 에서/까지", "Dan/gacha 에서/까지", "From/to 에서/까지")),
    ("polite-yo", "-아요/어요", "endings", loc("Вежливое окончание -아요/어요", "Odobli tugash -아요/어요", "Polite ending -아요/어요")),
    ("formal-seumnida", "-습니다/ㅂ니다", "endings", loc("Формальное окончание", "Rasmiy tugash", "Formal polite ending")),
    ("casual-a-eo", "-아/어", "endings", loc("Разговорное окончание", "Oddiy yaqin nutq", "Casual ending")),
    ("past-tense", "-았/었어요", "tense", loc("Прошедшее время", "O'tgan zamon", "Past tense")),
    ("future-plan", "-(으)ㄹ 거예요", "tense", loc("Будущее/план", "Kelasi reja", "Future plan")),
    ("negation-an", "안 + V/A", "negation", loc("Краткое отрицание 안", "Qisqa inkor 안", "Short negation 안")),
    ("negation-ji-anta", "-지 않다", "negation", loc("Полное отрицание -지 않다", "To'liq inkor -지 않다", "Long negation -지 않다")),
    ("want-go-sipda", "-고 싶다", "patterns", loc("Хочу -고 싶다", "Xohlamoq -고 싶다", "Want to -고 싶다")),
    ("can-eul-su-itda", "-(으)ㄹ 수 있다", "patterns", loc("Мочь -ㄹ 수 있다", "Qila olmoq -ㄹ 수 있다", "Can -ㄹ 수 있다")),
    ("honorific-si", "-시-", "honorifics", loc("Уважительный суффикс -시-", "Hurmat qo'shimchasi -시-", "Honorific -시-")),
    ("counter-gaejan", "개/잔/명", "counters", loc("Счётные слова", "Sanoq birliklari", "Counters")),
    ("native-numbers", "하나/둘/셋", "numbers", loc("Исконно корейские числа", "Sof koreys sonlari", "Native Korean numbers")),
    ("sino-numbers", "일/이/삼", "numbers", loc("Китайско-корейские числа", "Sino-koreys sonlari", "Sino-Korean numbers")),
    ("because-aseo", "-아/어서", "connectors", loc("Причина -아/어서", "Sabab -아/어서", "Because -아/어서")),
    ("but-jiman", "-지만", "connectors", loc("Но -지만", "Lekin -지만", "But -지만")),
]


SCENARIOS = [
    ("convenience-store", loc("В магазине 24/7", "24/7 do'konda", "At a convenience store"), "shop_staff"),
    ("subway-station", loc("В метро", "Metroda", "At the subway station"), "stranger"),
    ("ordering-food", loc("Заказ еды", "Ovqat buyurtma qilish", "Ordering food"), "shop_staff"),
    ("university-office", loc("В учебном офисе", "Universitet ofisida", "At the university office"), "professor"),
    ("factory-first-day", loc("Первый день на работе", "Ishdagi birinchi kun", "First day at work"), "boss"),
    ("clinic-visit", loc("В клинике", "Klinikada", "Clinic visit"), "doctor"),
    ("bank-account", loc("Открытие счёта", "Bank hisobi ochish", "Opening a bank account"), "staff"),
    ("phone-plan", loc("Тариф телефона", "Telefon tarifi", "Phone plan"), "staff"),
    ("housing", loc("Аренда жилья", "Uy ijarasi", "Housing rental"), "landlord"),
    ("delivery", loc("Доставка", "Yetkazib berish", "Delivery"), "courier"),
    ("friend-chat", loc("Разговор с другом", "Do'st bilan suhbat", "Chatting with a friend"), "friend"),
    ("professor-email", loc("Письмо профессору", "Professorga xat", "Email to professor"), "professor"),
    ("immigration", loc("Иммиграционный офис", "Migratsiya idorasi", "Immigration office"), "staff"),
    ("eps-safety", loc("Инструктаж по безопасности", "Xavfsizlik instruktaji", "Safety briefing"), "coworker"),
    ("lost-item", loc("Потерянная вещь", "Yo'qolgan buyum", "Lost item"), "stranger"),
]


LESSONS = [
    {
        "slug": "hangul-greetings-001",
        "module": "hangul-start",
        "title": loc("Первые приветствия", "Birinchi salomlashuvlar", "First greetings"),
        "summary": loc("안녕하세요 и выбор вежливости", "안녕하세요 va odob darajasi", "안녕하세요 and politeness choice"),
        "korean_text": "안녕하세요. 감사합니다.",
        "explanation": loc(
            "Корейское приветствие сразу показывает дистанцию и вежливость. Для незнакомых людей используйте 안녕하세요.",
            "Koreyscha salomlashuv darhol masofa va hurmatni ko'rsatadi. Begonalarga 안녕하세요 ishlating.",
            "Korean greetings immediately signal distance and politeness. Use 안녕하세요 with strangers.",
        ),
        "transfer_notes": {
            "ru": ["Не переводите 안녕하세요 как вопрос о здоровье.", "В русском вежливость часто передаётся местоимением, в корейском - окончанием."],
            "uz": ["Assalomu alaykumga o'xshash vazifada, lekin grammatik tuzilishi boshqa.", "Hurmat ko'pincha fe'l tugashida ko'rinadi."],
            "en": ["Do not treat it like a literal health question.", "English relies on word choice; Korean relies heavily on endings."],
        },
        "topic": "greetings",
        "grammar_category": "politeness",
    },
    {
        "slug": "particles-topic-subject-001",
        "module": "grammar-foundation",
        "title": loc("은/는 и 이/가 без путаницы", "은/는 va 이/가 farqi", "은/는 vs 이/가 without confusion"),
        "summary": loc("Тема против нового факта", "Mavzu va yangi fakt", "Topic versus new subject information"),
        "korean_text": "저는 학생이에요. 학생이 와요.",
        "explanation": loc(
            "은/는 задаёт тему разговора, 이/가 часто выделяет подлежащее или новую информацию.",
            "은/는 suhbat mavzusini belgilaydi, 이/가 ko'pincha ega yoki yangi ma'lumotni ajratadi.",
            "은/는 sets the conversation topic; 이/가 often marks the subject or new information.",
        ),
        "transfer_notes": {
            "ru": ["В русском нет частиц, поэтому не ищите прямой падежный эквивалент."],
            "uz": ["O'zbek kelishik qo'shimchalari yordam beradi, lekin 은/는 mavzu vazifasini alohida bajaradi."],
            "en": ["English subject position is not enough to explain the contrast."],
        },
        "topic": "particles",
        "grammar_category": "particles",
    },
    {
        "slug": "sentence-order-001",
        "module": "grammar-foundation",
        "title": loc("Порядок слов: кто что делает", "So'z tartibi: kim nima qiladi", "Sentence order: who does what"),
        "summary": loc("Корейский глагол обычно в конце", "Koreys tilida fe'l odatda oxirida", "Korean verbs usually come last"),
        "korean_text": "저는 김치를 먹어요.",
        "explanation": loc(
            "Базовый порядок: тема/подлежащее + объект + глагол. Частицы помогают понять роль слова.",
            "Asosiy tartib: mavzu/ega + obyekt + fe'l. Qo'shimchalar so'z rolini ko'rsatadi.",
            "Basic order: topic/subject + object + verb. Particles identify each word's role.",
        ),
        "transfer_notes": {
            "ru": ["Русский порядок свободнее, но корейский конец предложения особенно важен."],
            "uz": ["O'zbek tili ham SOV bo'lgani uchun tartib tanish, lekin koreys zarralari alohida e'tibor talab qiladi."],
            "en": ["Do not put the verb after the subject like English SVO."],
        },
        "topic": "sentence_order",
        "grammar_category": "word_order",
    },
    {
        "slug": "food-ordering-001",
        "module": "daily-survival",
        "title": loc("Заказать еду вежливо", "Ovqatni odob bilan buyurtma qilish", "Order food politely"),
        "summary": loc("- 주세요 и счётные слова", "- 주세요 va sanoq birliklari", "- 주세요 and counters"),
        "korean_text": "김치찌개 하나 주세요.",
        "explanation": loc(
            "주세요 делает просьбу вежливой. Для предметов и порций часто нужен счётчик.",
            "주세요 iltimosni odobli qiladi. Buyum va porsiyalar uchun sanoq birligi kerak bo'lishi mumkin.",
            "주세요 makes a request polite. Items and portions often need a counter.",
        ),
        "transfer_notes": {
            "ru": ["Не говорите только 김치찌개 하나; без 주세요 звучит резко."],
            "uz": ["Iltimos ma'nosi ko'pincha 주세요 orqali beriladi."],
            "en": ["Please is not just a separate word; the request pattern matters."],
        },
        "topic": "food",
        "grammar_category": "requests",
    },
    {
        "slug": "work-politeness-001",
        "module": "daily-survival",
        "title": loc("На работе: формально или вежливо", "Ishda: rasmiy yoki odobli", "At work: formal or polite"),
        "summary": loc("Boss, coworker, friend contexts", "Boshliq, hamkasb, do'st kontekstlari", "Boss, coworker, friend contexts"),
        "korean_text": "사장님, 내일 일할 수 있습니다.",
        "explanation": loc(
            "С начальником лучше использовать формально-вежливый стиль. С другом такая форма может звучать слишком официально.",
            "Boshliq bilan rasmiy-odobli uslub yaxshi. Do'st bilan bu juda rasmiy eshitilishi mumkin.",
            "With a boss, formal polite style is safer. With a friend, it can sound too formal.",
        ),
        "transfer_notes": {
            "ru": ["Окончание часто важнее, чем выбор местоимения."],
            "uz": ["Hurmat fe'l shaklida ko'rinadi; faqat siz/sen bilan cheklanmaydi."],
            "en": ["Korean register is more grammaticalized than English politeness."],
        },
        "topic": "work",
        "grammar_category": "speech_levels",
        "is_premium": True,
    },
]


EXERCISE_TEMPLATES = [
    ("multiple_choice_meaning", loc("Что значит 안녕하세요?", "안녕하세요 nimani anglatadi?", "What does 안녕하세요 mean?"), "hello_polite", [("hello_polite", loc("Здравствуйте", "Salom (odobli)", "Hello (polite)")), ("bye", loc("До свидания", "Xayr", "Goodbye"))]),
    ("multiple_choice_grammar", loc("Какая частица показывает тему?", "Qaysi zarra mavzuni ko'rsatadi?", "Which particle marks the topic?"), "eun_neun", [("eun_neun", loc("은/는", "은/는", "은/는")), ("eul_reul", loc("을/를", "을/를", "을/를"))]),
    ("fill_blank", loc("저__ 학생이에요.", "저__ 학생이에요.", "저__ 학생이에요."), "는", []),
    ("sentence_reordering", loc("Соберите: I eat kimchi.", "Tuzing: Men kimchi yeyman.", "Reorder: I eat kimchi."), ["저는", "김치를", "먹어요"], []),
    ("match_korean_translation", loc("Сопоставьте 한국어.", "한국어 mosligini toping.", "Match 한국어."), {"한국어": "korean_language"}, []),
    ("match_word_usage", loc("Где уместно 사장님?", "사장님 qayerda mos?", "Where is 사장님 appropriate?"), "boss", [("boss", loc("начальник", "boshliq", "boss")), ("friend", loc("близкий друг", "yaqin do'st", "close friend"))]),
    ("choose_particle", loc("저__ 한국에 가요.", "저__ 한국에 가요.", "저__ 한국에 가요."), "는", []),
    ("choose_verb_ending", loc("먹다 → polite informal", "먹다 → odobli norasmiy", "먹다 → polite informal"), "먹어요", []),
    ("choose_politeness_level", loc("Для профессора выберите стиль.", "Professor uchun uslubni tanlang.", "Choose the register for a professor."), "formal_polite", [("casual", loc("반말", "yaqin oddiy", "casual")), ("formal_polite", loc("формально-вежливый", "rasmiy-odobli", "formal polite"))]),
    ("identify_unnatural_sentence", loc("Что звучит неловко в магазине?", "Do'konda qaysi gap noqulay?", "Which sounds awkward in a shop?"), "김치찌개 하나", [("김치찌개 하나", loc("без 주세요", "주세요 yo'q", "missing 주세요")), ("김치찌개 하나 주세요", loc("естественно", "tabiiy", "natural"))]),
    ("reading_comprehension", loc("저는 학생이에요. Кто я?", "저는 학생이에요. Men kimman?", "저는 학생이에요. Who am I?"), "student", [("student", loc("студент", "talaba", "student")), ("teacher", loc("учитель", "o'qituvchi", "teacher"))]),
    ("dialogue_continuation", loc("A: 안녕하세요. B: ?", "A: 안녕하세요. B: ?", "A: 안녕하세요. B: ?"), "안녕하세요", []),
    ("mistake_correction", loc("Исправьте: 저는 김치 먹어요.", "Tuzating: 저는 김치 먹어요.", "Correct: 저는 김치 먹어요."), "저는 김치를 먹어요.", []),
    ("translation_to_korean", loc("Переведите: Я студент.", "Tarjima qiling: Men talabaman.", "Translate: I am a student."), "저는 학생이에요.", []),
    ("translation_from_korean", loc("Переведите: 물 주세요.", "Tarjima qiling: 물 주세요.", "Translate: 물 주세요."), {"ru": "Дайте воду, пожалуйста.", "uz": "Suv bering, iltimos.", "en": "Water, please."}, []),
    ("dictation_text", loc("Введите услышанное: 안녕하세요", "Eshitilganni yozing: 안녕하세요", "Type what you hear: 안녕하세요"), "안녕하세요", []),
    ("flashcard_review", loc("Вспомните значение 물.", "물 ma'nosini eslang.", "Recall the meaning of 물."), "water", []),
    ("example_sentence_review", loc("Что делает 먹어요 в предложении?", "Gapda 먹어요 nima qiladi?", "What does 먹어요 do in the sentence?"), "verb_eat_polite", []),
]


def seed_database(db: Session) -> None:
    if db.query(LearningPath).first():
        modules = {module.slug: module for module in db.query(Module).all()}
        ensure_expanded_content(db, modules)
        db.commit()
        return

    path_by_slug: dict[str, LearningPath] = {}
    for index, (slug, title, goal, level, premium) in enumerate(PATHS):
        path = LearningPath(
            slug=slug,
            title=title,
            description=loc("Короткие уроки на 1-5 минут.", "1-5 daqiqalik qisqa darslar.", "Short 1-5 minute lessons."),
            target_goal=goal,
            level=level,
            order_index=index,
            is_premium=premium,
        )
        db.add(path)
        path_by_slug[slug] = path
    db.flush()

    course = Course(
        slug="starter-korean",
        path_id=path_by_slug["hangul-basics"].id,
        title=loc("Стартовый корейский", "Boshlang'ich koreys tili", "Starter Korean"),
        description=loc("Хангыль, фразы, частицы и первые сценарии.", "Hangul, iboralar, zarralar va birinchi vaziyatlar.", "Hangul, phrases, particles, and first scenarios."),
        order_index=0,
    )
    db.add(course)
    db.flush()

    module_specs = [
        ("hangul-start", loc("Хангыль и приветствия", "Hangul va salomlashuv", "Hangul and greetings"), "A0"),
        ("grammar-foundation", loc("Грамматический фундамент", "Grammatika asosi", "Grammar foundation"), "A0"),
        ("daily-survival", loc("Жизнь в Корее", "Koreyada kundalik hayot", "Daily survival"), "A1"),
    ]
    modules: dict[str, Module] = {}
    for index, (slug, title, difficulty) in enumerate(module_specs):
        module = Module(
            slug=slug,
            course_id=course.id,
            title=title,
            description=loc("Модуль коротких интерактивных уроков.", "Qisqa interaktiv darslar moduli.", "Module of short interactive lessons."),
            difficulty=difficulty,
            estimated_minutes=25,
            order_index=index,
        )
        db.add(module)
        modules[slug] = module
    db.flush()

    for index, lesson_data in enumerate(LESSONS):
        lesson = Lesson(
            slug=lesson_data["slug"],
            module_id=modules[lesson_data["module"]].id,
            title=lesson_data["title"],
            summary=lesson_data["summary"],
            korean_text=lesson_data["korean_text"],
            explanation=lesson_data["explanation"],
            transfer_notes=lesson_data["transfer_notes"],
            tags=[lesson_data["topic"], lesson_data["grammar_category"]],
            difficulty="A0" if index < 3 else "A1",
            topic=lesson_data["topic"],
            grammar_category=lesson_data["grammar_category"],
            politeness_level="polite_informal",
            estimated_minutes=5,
            order_index=index,
            is_premium=lesson_data.get("is_premium", False),
            review_metadata={"creates_review_items": True},
        )
        db.add(lesson)
    db.flush()

    lessons = db.query(Lesson).order_by(Lesson.order_index).all()
    for index, (exercise_type, prompt, answer, options) in enumerate(EXERCISE_TEMPLATES):
        lesson = lessons[index % len(lessons)]
        exercise = Exercise(
            lesson_id=lesson.id,
            slug=f"{lesson.slug}-{exercise_type}-{index}",
            exercise_type=exercise_type,
            prompt=prompt,
            payload={"audio_asset_url": "s3://demo/audio/annyeonghaseyo.mp3"} if exercise_type == "dictation_text" else {},
            answer_key={"value": answer},
            explanation=loc(
                "Проверьте частицу, порядок слов и уровень вежливости.",
                "Zarra, so'z tartibi va hurmat darajasini tekshiring.",
                "Check the particle, word order, and politeness level.",
            ),
            difficulty=lesson.difficulty,
            topic=lesson.topic,
            politeness_level=lesson.politeness_level,
            order_index=index,
            is_premium=lesson.is_premium,
        )
        db.add(exercise)
        db.flush()
        for option_index, (value, label) in enumerate(options):
            db.add(
                ExerciseOption(
                    exercise_id=exercise.id,
                    value=value,
                    label=label,
                    is_correct=value == answer,
                    order_index=option_index,
                )
            )

    for slug, korean, reading, translations, topic in VOCABULARY:
        db.add(
            Vocabulary(
                slug=slug,
                korean=korean,
                reading=reading,
                translations=translations,
                usage_notes=loc(
                    "Обратите внимание на частицу после слова в предложении.",
                    "Gapda bu so'zdan keyingi zarraga e'tibor bering.",
                    "Watch the particle after this word in a sentence.",
                ),
                topic=topic,
                tags=[topic],
                difficulty="A0" if topic in {"greetings", "basics"} else "A1",
                politeness_level="polite_informal" if topic == "greetings" else None,
                example_sentences=[
                    {
                        "korean": f"{korean} 있어요.",
                        "translations": loc(f"{translations['ru']} есть.", f"{translations['uz']} bor.", f"There is {translations['en']}."),
                    }
                ],
                is_premium=topic in {"work", "health"} and slug not in {"work", "hospital"},
            )
        )

    for slug, pattern, category, title in GRAMMAR_POINTS:
        db.add(
            GrammarPoint(
                slug=slug,
                korean_pattern=pattern,
                title=title,
                explanation=loc(
                    f"{pattern} важно для корейского порядка слов и смысла. Смотрите на роль слова, а не только на перевод.",
                    f"{pattern} koreyscha so'z tartibi va ma'nosi uchun muhim. Faqat tarjimaga emas, so'z roliga qarang.",
                    f"{pattern} is important for Korean word order and meaning. Track the word's role, not only the translation.",
                ),
                transfer_notes={
                    "ru": ["Не ищите точный русский падеж для каждой частицы.", "Падеж и тема разговора - разные вещи."],
                    "uz": ["O'zbek qo'shimchalari yordam beradi, lekin koreys mavzu zarrasi alohida ishlaydi."],
                    "en": ["English word order hides distinctions that Korean marks explicitly."],
                },
                common_errors={
                    "ru": ["Опускать частицу из-за дословного перевода."],
                    "uz": ["O'zbekcha kelishikni to'g'ridan-to'g'ri ko'chirish."],
                    "en": ["Using English SVO order and forgetting particles."],
                },
                natural_alternatives=[
                    {"context": "stranger", "korean": "안녕하세요.", "label": "polite_informal"},
                    {"context": "boss", "korean": "안녕하십니까?", "label": "formal_polite"},
                ],
                category=category,
                difficulty="A0" if category in {"particles", "endings"} else "A1",
                politeness_level="polite_informal" if category in {"endings", "honorifics"} else None,
                tags=[category],
                is_premium=category in {"honorifics", "connectors"},
            )
        )

    db.flush()
    vocab_items = db.query(Vocabulary).limit(40).all()
    grammar_items = db.query(GrammarPoint).limit(20).all()
    for vocab in vocab_items:
        db.add(
            ExampleSentence(
                korean=f"저는 {vocab.korean}을/를 알아요.",
                translations=loc(
                    f"Я знаю слово {vocab.translations['ru']}.",
                    f"Men {vocab.translations['uz']} so'zini bilaman.",
                    f"I know the word {vocab.translations['en']}.",
                ),
                explanation=loc(
                    "Форма 을/를 зависит от финального звука слова.",
                    "을/를 shakli so'z oxirgi tovushiga bog'liq.",
                    "The 을/를 form depends on the final sound.",
                ),
                vocabulary_id=vocab.id,
                context_labels=["study"],
                politeness_level="polite_informal",
            )
        )
    for grammar in grammar_items:
        db.add(
            ExampleSentence(
                korean=f"예문: {grammar.korean_pattern}",
                translations=loc("Пример грамматики.", "Grammatika misoli.", "Grammar example."),
                explanation=grammar.explanation,
                grammar_point_id=grammar.id,
                context_labels=["study"],
                politeness_level=grammar.politeness_level or "neutral",
            )
        )

    for slug, title, context in SCENARIOS:
        scenario = Scenario(
            slug=slug,
            title=title,
            description=loc("Практический сценарий для жизни в Корее.", "Koreyadagi hayot uchun amaliy vaziyat.", "Practical Korea-life scenario."),
            context_labels=[context],
            topic="daily_life",
            difficulty="A0" if slug in {"convenience-store", "subway-station"} else "A1",
            is_premium=context in {"professor", "boss", "doctor", "staff"} and slug not in {"university-office"},
        )
        db.add(scenario)
        db.flush()
        db.add(
            Dialogue(
                scenario_id=scenario.id,
                title=title,
                lines=[
                    {"speaker": "A", "korean": "안녕하세요.", "translations": loc("Здравствуйте.", "Salom.", "Hello."), "register": "polite_informal"},
                    {"speaker": "B", "korean": "네, 무엇을 도와드릴까요?", "translations": loc("Да, чем помочь?", "Ha, qanday yordam beray?", "Yes, how can I help?"), "register": "formal_polite"},
                ],
                explanation=loc(
                    "Обратите внимание на вежливый ответ сотрудника.",
                    "Xodimning odobli javobiga e'tibor bering.",
                    "Notice the staff member's polite response.",
                ),
                politeness_level="polite_informal",
                is_premium=scenario.is_premium,
            )
        )

    db.add_all(
        [
            Achievement(
                slug="first-lesson",
                title=loc("Первый урок", "Birinchi dars", "First lesson"),
                description=loc("Завершите первый урок.", "Birinchi darsni tugating.", "Complete your first lesson."),
                trigger={"lesson_completed": 1},
                xp_reward=20,
            ),
            Achievement(
                slug="mistake-reviewer",
                title=loc("Работа над ошибками", "Xatolar ustida ishlash", "Mistake reviewer"),
                description=loc("Повторите 5 ошибок.", "5 ta xatoni takrorlang.", "Review 5 mistakes."),
                trigger={"mistake_reviews": 5},
                xp_reward=30,
            ),
        ]
    )

    ensure_expanded_content(db, modules)

    db.add_all(
        [
            PremiumPack(
                slug="student-korea-pack",
                title=loc("Студент в Корее", "Koreyada talaba", "Student in Korea"),
                description=loc("Офис, профессор, общежитие и документы.", "Ofis, professor, yotoqxona va hujjatlar.", "Office, professor, dorm, and documents."),
                price_minor=599,
                currency="USD",
                content_rules={"paths": ["student-korea"], "writing_limit": 100},
            ),
            PremiumPack(
                slug="work-eps-pack",
                title=loc("Работа / EPS", "Ish / EPS", "Work / EPS"),
                description=loc("Завод, безопасность, начальник и смены.", "Zavod, xavfsizlik, boshliq va smenalar.", "Factory, safety, boss, and shifts."),
                price_minor=799,
                currency="USD",
                content_rules={"paths": ["work-eps"], "writing_limit": 100},
            ),
        ]
    )

    db.commit()
