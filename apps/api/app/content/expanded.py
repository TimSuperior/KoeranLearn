from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.schema import Dialogue, ExampleSentence, Exercise, ExerciseOption, GrammarPoint, Lesson, LocalizationEntry, Module, Scenario, Vocabulary


def loc(ru: str, uz: str, en: str) -> dict[str, str]:
    return {"ru": ru, "uz": uz, "en": en}


LESSON_TOPICS = [
    ("hangul-vowels", "hangul-start", "Гласные хангыль", "Hangul unlilari", "Hangul vowels", "ㅏ ㅓ ㅗ ㅜ ㅡ ㅣ"),
    ("hangul-consonants", "hangul-start", "Согласные хангыль", "Hangul undoshlari", "Hangul consonants", "ㄱ ㄴ ㄷ ㄹ ㅁ ㅂ ㅅ ㅇ"),
    ("batchim-basics", "hangul-start", "Основы 받침", "받침 asosi", "Batchim basics", "집, 밥, 옷"),
    ("greetings-politeness", "hangul-start", "Приветствия и вежливость", "Salomlashuv va hurmat", "Greetings and politeness", "안녕하세요. 감사합니다."),
    ("self-introduction", "hangul-start", "Самопредставление", "O'zini tanishtirish", "Self introduction", "저는 학생이에요."),
    ("countries-nationality", "hangul-start", "Страны и национальность", "Davlat va millat", "Countries and nationality", "저는 우즈베키스탄 사람이에요."),
    ("topic-particle", "grammar-foundation", "Частица 은/는", "은/는 zarrasi", "Topic particle 은/는", "저는 학생이에요."),
    ("subject-particle", "grammar-foundation", "Частица 이/가", "이/가 zarrasi", "Subject particle 이/가", "친구가 와요."),
    ("object-particle", "grammar-foundation", "Частица 을/를", "을/를 zarrasi", "Object particle 을/를", "김치를 먹어요."),
    ("basic-word-order", "grammar-foundation", "Порядок слов", "So'z tartibi", "Basic word order", "저는 커피를 마셔요."),
    ("existence-itda", "grammar-foundation", "있어요/없어요", "있어요/없어요", "Existence 있어요/없어요", "물이 있어요."),
    ("location-e", "grammar-foundation", "Место 에", "Joy 에", "Location 에", "학교에 가요."),
    ("action-location-eseo", "grammar-foundation", "Действие 에서", "Harakat 에서", "Action location 에서", "식당에서 먹어요."),
    ("present-tense", "grammar-foundation", "Настоящее время", "Hozirgi zamon", "Present tense", "공부해요."),
    ("past-tense", "grammar-foundation", "Прошедшее время", "O'tgan zamon", "Past tense", "공부했어요."),
    ("future-plan", "grammar-foundation", "Будущий план", "Kelasi reja", "Future plan", "공부할 거예요."),
    ("short-negation", "grammar-foundation", "Краткое отрицание 안", "Qisqa inkor 안", "Short negation 안", "안 가요."),
    ("long-negation", "grammar-foundation", "Отрицание -지 않아요", "-지 않아요 inkori", "Long negation -지 않아요", "먹지 않아요."),
    ("native-numbers", "daily-survival", "Исконно корейские числа", "Sof koreys sonlari", "Native Korean numbers", "하나, 둘, 셋"),
    ("sino-numbers", "daily-survival", "Китайско-корейские числа", "Sino-koreys sonlari", "Sino-Korean numbers", "일, 이, 삼"),
    ("counters", "daily-survival", "Счётные слова", "Sanoq birliklari", "Counters", "한 개, 두 명"),
    ("ordering-food", "daily-survival", "Заказ еды", "Ovqat buyurtma qilish", "Ordering food", "김치찌개 하나 주세요."),
    ("shopping-price", "daily-survival", "Покупки и цены", "Xarid va narx", "Shopping and prices", "이거 얼마예요?"),
    ("transport-directions", "daily-survival", "Транспорт и направления", "Transport va yo'nalish", "Transport and directions", "지하철역이 어디예요?"),
    ("daily-routine", "daily-survival", "Ежедневный распорядок", "Kundalik tartib", "Daily routine", "아침에 일어나요."),
    ("school-life", "daily-survival", "Учёба", "O'qish hayoti", "School life", "수업이 있어요."),
    ("work-basics", "daily-survival", "Работа", "Ish asoslari", "Work basics", "회사에 가요."),
    ("clinic-basics", "daily-survival", "В клинике", "Klinikada", "At a clinic", "머리가 아파요."),
    ("phone-address", "daily-survival", "Телефон и адрес", "Telefon va manzil", "Phone and address", "전화번호가 뭐예요?"),
    ("common-mistakes", "daily-survival", "Частые ошибки", "Ko'p xatolar", "Common beginner mistakes", "저는 김치를 먹어요."),
]


OBJECTS = [
    ("water", "물", "вода", "suv", "water"),
    ("coffee", "커피", "кофе", "qahva", "coffee"),
    ("tea", "차", "чай", "choy", "tea"),
    ("rice", "밥", "рис/еда", "guruch/ovqat", "rice/meal"),
    ("kimchi", "김치", "кимчи", "kimchi", "kimchi"),
    ("soup", "국", "суп", "sho'rva", "soup"),
    ("bread", "빵", "хлеб", "non", "bread"),
    ("milk", "우유", "молоко", "sut", "milk"),
    ("apple", "사과", "яблоко", "olma", "apple"),
    ("banana", "바나나", "банан", "banan", "banana"),
    ("market", "시장", "рынок", "bozor", "market"),
    ("store", "가게", "магазин", "do'kon", "store"),
    ("restaurant", "식당", "ресторан", "restoran", "restaurant"),
    ("school", "학교", "школа", "maktab", "school"),
    ("university", "대학교", "университет", "universitet", "university"),
    ("class", "수업", "урок", "dars", "class"),
    ("home", "집", "дом", "uy", "home"),
    ("room", "방", "комната", "xona", "room"),
    ("station", "역", "станция", "bekat", "station"),
    ("subway", "지하철", "метро", "metro", "subway"),
    ("bus", "버스", "автобус", "avtobus", "bus"),
    ("taxi", "택시", "такси", "taksi", "taxi"),
    ("ticket", "표", "билет", "chipta", "ticket"),
    ("card", "카드", "карта", "karta", "card"),
    ("cash", "현금", "наличные", "naqd pul", "cash"),
    ("phone", "전화", "телефон", "telefon", "phone"),
    ("address", "주소", "адрес", "manzil", "address"),
    ("passport", "여권", "паспорт", "pasport", "passport"),
    ("medicine", "약", "лекарство", "dori", "medicine"),
    ("hospital", "병원", "больница", "shifoxona", "hospital"),
    ("head", "머리", "голова", "bosh", "head"),
    ("stomach", "배", "живот", "qorin", "stomach"),
    ("work", "일", "работа", "ish", "work"),
    ("company", "회사", "компания", "kompaniya", "company"),
    ("factory", "공장", "завод", "zavod", "factory"),
    ("boss", "사장님", "начальник", "boshliq", "boss"),
    ("coworker", "동료", "коллега", "hamkasb", "coworker"),
    ("friend", "친구", "друг", "do'st", "friend"),
    ("teacher", "선생님", "учитель", "o'qituvchi", "teacher"),
    ("student", "학생", "студент", "talaba", "student"),
    ("book", "책", "книга", "kitob", "book"),
    ("notebook", "공책", "тетрадь", "daftar", "notebook"),
    ("pen", "펜", "ручка", "ruchka", "pen"),
    ("bag", "가방", "сумка", "sumka", "bag"),
    ("clothes", "옷", "одежда", "kiyim", "clothes"),
    ("shoes", "신발", "обувь", "oyoq kiyim", "shoes"),
    ("umbrella", "우산", "зонт", "soyabon", "umbrella"),
    ("weather", "날씨", "погода", "ob-havo", "weather"),
    ("time", "시간", "время", "vaqt", "time"),
    ("today", "오늘", "сегодня", "bugun", "today"),
]


PHRASE_PATTERNS = [
    ("please", "{ko} 주세요.", "Дайте {ru}, пожалуйста.", "{uz} bering, iltimos.", "Please give me {en}."),
    ("exists", "{ko} 있어요.", "{ru} есть.", "{uz} bor.", "There is {en}."),
    ("missing", "{ko} 없어요.", "{ru} нет.", "{uz} yo'q.", "There is no {en}."),
    ("where", "{ko} 어디예요?", "Где {ru}?", "{uz} qayerda?", "Where is {en}?"),
    ("price", "{ko} 얼마예요?", "Сколько стоит {ru}?", "{uz} qancha turadi?", "How much is {en}?"),
    ("like", "{ko} 좋아해요.", "Мне нравится {ru}.", "Men {uz}ni yoqtiraman.", "I like {en}."),
    ("need", "{ko} 필요해요.", "Нужен/нужна {ru}.", "Menga {uz} kerak.", "I need {en}."),
    ("know", "{ko} 알아요.", "Я знаю {ru}.", "Men {uz}ni bilaman.", "I know {en}."),
]


GRAMMAR_BASE = [
    ("topic-neun-context", "N은/는", "particles"),
    ("subject-i-ga-context", "N이/가", "particles"),
    ("object-eul-reul-context", "N을/를", "particles"),
    ("location-e-context", "N에", "particles"),
    ("action-eseo-context", "N에서", "particles"),
    ("and-hago-context", "N하고", "connectors"),
    ("also-do-context", "N도", "particles"),
    ("to-from-context", "N부터 N까지", "particles"),
    ("polite-ayo-context", "V/A-아요/어요", "endings"),
    ("formal-seumnida-context", "V/A-습니다", "endings"),
    ("past-eosseoyo-context", "V/A-았어요/었어요", "tense"),
    ("future-geoyeyo-context", "V-(으)ㄹ 거예요", "tense"),
    ("want-sipda-context", "V-고 싶어요", "patterns"),
    ("can-su-itda-context", "V-(으)ㄹ 수 있어요", "patterns"),
    ("short-negation-context", "안 V/A", "negation"),
    ("long-negation-context", "V/A-지 않아요", "negation"),
    ("because-aseo-context", "V/A-아서/어서", "connectors"),
    ("but-jiman-context", "V/A-지만", "connectors"),
    ("request-juseyo-context", "N 주세요", "requests"),
    ("please-use-seyo-context", "V-(으)세요", "requests"),
]


GRAMMAR_CONTEXTS = [
    ("intro", "самопредставлении", "tanishtirishda", "self-introduction"),
    ("food", "заказе еды", "ovqat buyurtmasida", "ordering food"),
    ("transport", "транспорте", "transportda", "transport"),
    ("work", "работе", "ishda", "work"),
]


SCENARIO_TOPICS = [
    ("convenience-store-drink", "convenience_store", "staff", "편의점에서 물 사기", "Покупка воды в магазине", "Do'konda suv olish", "Buying water at a convenience store"),
    ("cafe-order", "food", "staff", "카페에서 주문하기", "Заказ в кафе", "Kafeda buyurtma", "Ordering at a cafe"),
    ("restaurant-table", "food", "staff", "식당에서 자리 묻기", "Столик в ресторане", "Restoranda joy so'rash", "Asking for a table"),
    ("market-price", "shopping", "seller", "시장에서 가격 묻기", "Цена на рынке", "Bozorda narx so'rash", "Asking prices at a market"),
    ("card-payment", "shopping", "cashier", "카드로 계산하기", "Оплата картой", "Karta bilan to'lash", "Paying by card"),
    ("subway-ticket", "transport", "staff", "지하철 표 사기", "Билет на метро", "Metro chiptasi", "Buying a subway ticket"),
    ("bus-stop", "transport", "stranger", "버스 정류장 묻기", "Где автобусная остановка", "Avtobus bekatini so'rash", "Asking for a bus stop"),
    ("taxi-address", "transport", "driver", "택시에서 주소 말하기", "Адрес в такси", "Taksida manzil aytish", "Giving an address in a taxi"),
    ("school-office", "study", "staff", "학교 사무실 방문", "В школьном офисе", "Maktab ofisida", "Visiting a school office"),
    ("class-schedule", "study", "classmate", "수업 시간 확인", "Расписание занятий", "Dars vaqtini tekshirish", "Checking class time"),
    ("library-card", "study", "staff", "도서관 카드 만들기", "Библиотечная карта", "Kutubxona kartasi", "Getting a library card"),
    ("dormitory-room", "study", "manager", "기숙사 방 묻기", "Комната в общежитии", "Yotoqxona xonasi", "Asking about a dorm room"),
    ("company-arrival", "work", "coworker", "회사 첫 출근", "Первый день в компании", "Ishdagi birinchi kun", "First day at a company"),
    ("factory-safety", "work", "supervisor", "공장 안전 안내", "Инструктаж на заводе", "Zavod xavfsizlik yo'riqnomasi", "Factory safety briefing"),
    ("shift-time", "work", "manager", "근무 시간 묻기", "Время смены", "Smena vaqtini so'rash", "Asking about shift time"),
    ("payday", "work", "manager", "월급날 확인", "День зарплаты", "Maosh kunini tekshirish", "Checking payday"),
    ("clinic-headache", "health", "doctor", "머리가 아파요", "Болит голова", "Bosh og'riyapti", "Headache at a clinic"),
    ("pharmacy-medicine", "health", "pharmacist", "약국에서 약 사기", "Покупка лекарства", "Dorixonada dori olish", "Buying medicine"),
    ("bank-account", "services", "staff", "은행 계좌 만들기", "Открытие счёта", "Bank hisobi ochish", "Opening a bank account"),
    ("phone-number", "services", "staff", "전화번호 묻기", "Номер телефона", "Telefon raqamini so'rash", "Asking for a phone number"),
    ("immigration-card", "services", "staff", "외국인등록증 문의", "Карта иностранца", "Chet ellik kartasi", "Alien registration card"),
    ("housing-rent", "housing", "landlord", "월세 묻기", "Аренда жилья", "Ijara haqida so'rash", "Asking about rent"),
    ("delivery-call", "daily_life", "courier", "배달 전화 받기", "Звонок доставки", "Yetkazib berish qo'ng'irog'i", "Taking a delivery call"),
    ("lost-wallet", "daily_life", "police", "지갑을 잃어버렸어요", "Потерян кошелёк", "Hamyon yo'qoldi", "Lost wallet"),
    ("weather-chat", "daily_life", "friend", "날씨 이야기", "Разговор о погоде", "Ob-havo haqida suhbat", "Talking about weather"),
]


EXERCISE_TYPES = [
    "multiple_choice",
    "fill_blank",
    "sentence_reorder",
    "match_pairs",
    "choose_particle",
    "choose_verb_ending",
    "translation_selection",
    "dialogue_continuation",
    "reading_comprehension",
    "true_false",
    "flashcard_review",
]


def ensure_expanded_content(db: Session, modules: dict[str, Module]) -> None:
    _ensure_lessons(db, modules)
    _ensure_vocabulary(db)
    _ensure_grammar(db)
    _ensure_exercises(db)
    _ensure_scenarios(db)
    _ensure_examples(db)
    _ensure_localization(db)


def _ensure_lessons(db: Session, modules: dict[str, Module]) -> None:
    if db.query(Lesson).count() >= 30:
        return
    start_index = db.query(Lesson).count()
    for index, (slug, module_slug, ru, uz, en, korean) in enumerate(LESSON_TOPICS):
        if db.query(Lesson).filter(Lesson.slug == slug).first():
            continue
        module = modules.get(module_slug) or db.query(Module).filter(Module.slug == module_slug).first()
        if not module:
            continue
        db.add(
            Lesson(
                slug=slug,
                module_id=module.id,
                title=loc(ru, uz, en),
                summary=loc(f"Практическая тема: {ru}.", f"Amaliy mavzu: {uz}.", f"Practical topic: {en}."),
                objectives=[
                    loc("Узнать форму.", "Shaklni o'rganish.", "Recognize the form."),
                    loc("Понять пример.", "Misolni tushunish.", "Understand the example."),
                    loc("Использовать в коротком ответе.", "Qisqa javobda ishlatish.", "Use it in a short answer."),
                ],
                korean_text=korean,
                explanation=loc(
                    f"Тема {ru} вводится через короткие корейские фразы и сразу связывается с практикой.",
                    f"{uz} mavzusi qisqa koreyscha iboralar orqali amaliyot bilan bog'lanadi.",
                    f"{en} is introduced through short Korean phrases and immediate practice.",
                ),
                transfer_notes={
                    "ru": ["Сначала найдите роль слова, затем перевод."],
                    "uz": ["Avval so'z vazifasini toping, keyin tarjima qiling."],
                    "en": ["Identify the word role before translating."],
                },
                tags=[slug, module_slug],
                difficulty="A0" if index < 18 else "A1",
                topic=slug.split("-")[0],
                grammar_category="hangul" if module_slug == "hangul-start" else "grammar",
                estimated_minutes=5,
                order_index=start_index + index,
                status="published",
            )
        )
    db.flush()


def _ensure_vocabulary(db: Session) -> None:
    if db.query(Vocabulary).count() >= 400:
        return
    created = 0
    for object_slug, ko, ru, uz, en in OBJECTS:
        for pattern_slug, korean_template, ru_template, uz_template, en_template in PHRASE_PATTERNS:
            slug = f"{pattern_slug}-{object_slug}"
            if db.query(Vocabulary).filter(Vocabulary.slug == slug).first():
                continue
            phrase = korean_template.format(ko=ko)
            db.add(
                Vocabulary(
                    slug=slug,
                    korean=phrase,
                    reading=None,
                    translations=loc(ru_template.format(ru=ru), uz_template.format(uz=uz), en_template.format(en=en)),
                    usage_notes=loc(
                        "Это практическая фраза; меняйте существительное по ситуации.",
                        "Bu amaliy ibora; vaziyatga qarab otni almashtiring.",
                        "This is a practical phrase; swap the noun for the situation.",
                    ),
                    topic=_topic_for_object(object_slug),
                    tags=[pattern_slug, _topic_for_object(object_slug)],
                    difficulty="A0" if created < 160 else "A1",
                    example_sentences=[{"korean": phrase, "translations": loc(ru_template.format(ru=ru), uz_template.format(uz=uz), en_template.format(en=en))}],
                    status="published",
                )
            )
            created += 1
            if db.query(Vocabulary).count() + created >= 400:
                db.flush()
                return
    db.flush()


def _ensure_grammar(db: Session) -> None:
    if db.query(GrammarPoint).count() >= 80:
        return
    for base_slug, pattern, category in GRAMMAR_BASE:
        for context_slug, ru_context, uz_context, en_context in GRAMMAR_CONTEXTS:
            slug = f"{base_slug}-{context_slug}"
            if db.query(GrammarPoint).filter(GrammarPoint.slug == slug).first():
                continue
            db.add(
                GrammarPoint(
                    slug=slug,
                    korean_pattern=pattern,
                    title=loc(f"{pattern} в {ru_context}", f"{pattern} {uz_context}", f"{pattern} in {en_context}"),
                    explanation=loc(
                        f"Используйте {pattern}, когда строите фразу в контексте {ru_context}.",
                        f"{uz_context} kontekstida gap tuzganda {pattern} ishlating.",
                        f"Use {pattern} when building a phrase in {en_context}.",
                    ),
                    transfer_notes={
                        "ru": ["Не копируйте порядок слов русского языка."],
                        "uz": ["O'zbekcha tartibni to'g'ridan-to'g'ri ko'chirmang."],
                        "en": ["Do not copy English word order directly."],
                    },
                    common_errors={
                        "ru": ["Пропуск частицы."],
                        "uz": ["Zarrani tushirib qoldirish."],
                        "en": ["Dropping the particle."],
                    },
                    natural_alternatives=[{"context": context_slug, "korean": "안녕하세요.", "label": "polite"}],
                    category=category,
                    difficulty="A0" if category in {"particles", "endings"} else "A1",
                    tags=[category, context_slug],
                    status="published",
                )
            )
    db.flush()


def _ensure_exercises(db: Session) -> None:
    if db.query(Exercise).count() >= 250:
        return
    lessons = db.query(Lesson).order_by(Lesson.order_index).all()
    if not lessons:
        return
    count = db.query(Exercise).count()
    index = 0
    while count < 250:
        lesson = lessons[index % len(lessons)]
        exercise_type = EXERCISE_TYPES[index % len(EXERCISE_TYPES)]
        slug = f"{lesson.slug}-{exercise_type}-expanded-{index}"
        if db.query(Exercise).filter(Exercise.slug == slug).first():
            index += 1
            continue
        prompt, answer, options, validation = _exercise_payload(exercise_type)
        exercise = Exercise(
            lesson_id=lesson.id,
            slug=slug,
            exercise_type=exercise_type,
            prompt=prompt,
            payload={"tokens": ["저는", "김치를", "먹어요"]} if exercise_type == "sentence_reorder" else {},
            answer_key={"value": answer},
            answer_validation=validation,
            explanation=loc(
                "Проверьте частицу, порядок слов и вежливое окончание.",
                "Zarra, so'z tartibi va odobli tugashni tekshiring.",
                "Check the particle, word order, and polite ending.",
            ),
            difficulty=lesson.difficulty,
            topic=lesson.topic,
            politeness_level=lesson.politeness_level,
            order_index=index,
            status="published",
        )
        db.add(exercise)
        db.flush()
        for option_index, (value, label, correct) in enumerate(options):
            db.add(ExerciseOption(exercise_id=exercise.id, value=value, label=label, is_correct=correct, order_index=option_index))
        count += 1
        index += 1
    db.flush()


def _ensure_scenarios(db: Session) -> None:
    if db.query(Scenario).count() >= 50:
        return
    total = db.query(Scenario).count()
    index = total
    variants = ["basic", "repeat", "problem"]
    for topic_index, (slug, topic, role, korean_title, ru, uz, en) in enumerate(SCENARIO_TOPICS):
        for variant in variants:
            scenario_slug = f"{slug}-{variant}"
            if db.query(Scenario).filter(Scenario.slug == scenario_slug).first():
                continue
            scenario = Scenario(
                slug=scenario_slug,
                title=loc(f"{ru}: {variant}", f"{uz}: {variant}", f"{en}: {variant}"),
                description=loc("Короткая практическая ситуация с полезными выражениями.", "Foydali iboralar bilan qisqa amaliy vaziyat.", "A short practical situation with useful expressions."),
                context_labels=[role],
                roles=["learner", role],
                topic=topic,
                tags=[topic, role, variant],
                difficulty="A0" if topic_index < 8 else "A1",
                order_index=index,
                is_premium=topic in {"work", "services"} and variant != "basic",
                status="published",
            )
            db.add(scenario)
            db.flush()
            lines = [
                {"speaker": "learner", "korean": "안녕하세요.", "translations": loc("Здравствуйте.", "Salom.", "Hello."), "register": "polite_informal"},
                {"speaker": role, "korean": "네, 무엇을 도와드릴까요?", "translations": loc("Да, чем помочь?", "Ha, qanday yordam beray?", "Yes, how can I help?"), "register": "formal_polite"},
                {"speaker": "learner", "korean": _scenario_request(topic), "translations": loc("Скажите короткую просьбу.", "Qisqa iltimos ayting.", "Make a short request."), "register": "polite_informal"},
            ]
            db.add(
                Dialogue(
                    scenario_id=scenario.id,
                    title=loc(ru, uz, en),
                    context=loc("Роль: учащийся и собеседник.", "Rol: o'quvchi va suhbatdosh.", "Role: learner and conversation partner."),
                    lines=lines,
                    checks=[
                        {
                            "prompt": loc("Какая фраза открывает разговор?", "Suhbatni qaysi ibora boshlaydi?", "Which phrase opens the conversation?"),
                            "answer": "안녕하세요.",
                        }
                    ],
                    useful_expressions=[{"korean": "무엇을 도와드릴까요?", "translations": loc("Чем помочь?", "Qanday yordam beray?", "How can I help?")}],
                    explanation=loc("Сценарий тренирует короткий вежливый обмен.", "Vaziyat qisqa odobli almashuvni mashq qildiradi.", "The scenario trains a short polite exchange."),
                    order_index=0,
                    politeness_level="polite_informal",
                    is_premium=scenario.is_premium,
                    status="published",
                )
            )
            index += 1
            total += 1
            if total >= 50:
                db.flush()
                return
    db.flush()


def _ensure_examples(db: Session) -> None:
    if db.query(ExampleSentence).count() >= 300:
        return
    vocab_items = db.query(Vocabulary).order_by(Vocabulary.id).limit(300).all()
    count = db.query(ExampleSentence).count()
    for index, vocab in enumerate(vocab_items):
        if count >= 300:
            break
        db.add(
            ExampleSentence(
                korean=vocab.korean,
                translations=vocab.translations,
                explanation=loc(
                    "Пример можно использовать как готовую фразу.",
                    "Misolni tayyor ibora sifatida ishlatish mumkin.",
                    "The example can be used as a ready phrase.",
                ),
                vocabulary_id=vocab.id,
                context_labels=[vocab.topic],
                politeness_level="polite_informal",
                status="published",
            )
        )
        count += 1
    db.flush()


def _exercise_payload(exercise_type: str):
    if exercise_type == "multiple_choice":
        return loc("Что значит 물?", "물 nimani anglatadi?", "What does 물 mean?"), "water", [("water", loc("вода", "suv", "water"), True), ("school", loc("школа", "maktab", "school"), False)], {"strategy": "one_of"}
    if exercise_type == "fill_blank":
        return loc("저__ 학생이에요.", "저__ 학생이에요.", "저__ 학생이에요."), "는", [], {"strategy": "one_of"}
    if exercise_type == "sentence_reorder":
        return loc("Соберите: I eat kimchi.", "Tuzing: Men kimchi yeyman.", "Reorder: I eat kimchi."), ["저는", "김치를", "먹어요"], [], {"strategy": "ordered_list"}
    if exercise_type == "match_pairs":
        return loc("Сопоставьте слова.", "So'zlarni moslang.", "Match the words."), {"물": "water", "학교": "school"}, [], {"strategy": "unordered_pairs"}
    if exercise_type == "choose_particle":
        return loc("저__ 한국에 가요.", "저__ 한국에 가요.", "저__ 한국에 가요."), "는", [("는", loc("는", "는", "는"), True), ("를", loc("를", "를", "를"), False)], {"strategy": "one_of"}
    if exercise_type == "choose_verb_ending":
        return loc("먹다 → polite", "먹다 → odobli", "먹다 → polite"), "먹어요", [("먹어요", loc("먹어요", "먹어요", "먹어요"), True), ("먹어", loc("먹어", "먹어", "먹어"), False)], {"strategy": "one_of"}
    if exercise_type == "translation_selection":
        return loc("Выберите перевод: 물 주세요.", "Tarjimani tanlang: 물 주세요.", "Choose the translation: 물 주세요."), "water_please", [("water_please", loc("Воду, пожалуйста.", "Suv bering.", "Water, please."), True), ("where_school", loc("Где школа?", "Maktab qayerda?", "Where is school?"), False)], {"strategy": "one_of"}
    if exercise_type == "dialogue_continuation":
        return loc("A: 안녕하세요. B: ?", "A: 안녕하세요. B: ?", "A: 안녕하세요. B: ?"), "안녕하세요", [("안녕하세요", loc("안녕하세요", "안녕하세요", "안녕하세요"), True), ("비싸요", loc("비싸요", "비싸요", "비싸요"), False)], {"strategy": "one_of"}
    if exercise_type == "reading_comprehension":
        return loc("저는 학생이에요. Кто я?", "저는 학생이에요. Men kimman?", "저는 학생이에요. Who am I?"), "student", [("student", loc("студент", "talaba", "student"), True), ("teacher", loc("учитель", "o'qituvchi", "teacher"), False)], {"strategy": "one_of"}
    if exercise_type == "true_false":
        return loc("물 значит вода.", "물 suv degani.", "물 means water."), "true", [("true", loc("Верно", "To'g'ri", "True"), True), ("false", loc("Неверно", "Noto'g'ri", "False"), False)], {"strategy": "one_of"}
    return loc("Вспомните значение 학교.", "학교 ma'nosini eslang.", "Recall the meaning of 학교."), "school", [], {"strategy": "one_of"}


def _topic_for_object(slug: str) -> str:
    if slug in {"water", "coffee", "tea", "rice", "kimchi", "soup", "bread", "milk", "apple", "banana", "restaurant"}:
        return "food"
    if slug in {"market", "store", "card", "cash", "clothes", "shoes", "bag"}:
        return "shopping"
    if slug in {"station", "subway", "bus", "taxi", "ticket"}:
        return "transport"
    if slug in {"school", "university", "class", "teacher", "student", "book", "notebook", "pen"}:
        return "study"
    if slug in {"work", "company", "factory", "boss", "coworker"}:
        return "work"
    if slug in {"medicine", "hospital", "head", "stomach"}:
        return "health"
    return "daily_life"


def _scenario_request(topic: str) -> str:
    if topic == "food":
        return "김치찌개 하나 주세요."
    if topic == "shopping":
        return "이거 얼마예요?"
    if topic == "transport":
        return "지하철역이 어디예요?"
    if topic == "health":
        return "머리가 아파요."
    if topic == "work":
        return "근무 시간이 언제예요?"
    return "물 주세요."


def _ensure_localization(db: Session) -> None:
    entries = {
        "bot.menu": loc("Главное меню", "Asosiy menyu", "Main menu"),
        "bot.lesson": loc("Продолжить урок", "Darsni davom ettirish", "Continue lesson"),
        "bot.dialogue": loc("Диалоги", "Dialoglar", "Dialogues"),
        "bot.quiz": loc("Короткий тест", "Qisqa test", "Short quiz"),
        "bot.plan": loc("Учебный план", "O'quv rejasi", "Learning plan"),
        "bot.streak": loc("Серия занятий", "Ketma-ketlik", "Study streak"),
        "bot.review": loc("Повторение", "Takrorlash", "Review"),
        "bot.mistakes": loc("Ошибки", "Xatolar", "Mistakes"),
        "bot.grammar": loc("Грамматика", "Grammatika", "Grammar"),
        "bot.words": loc("Слова", "So'zlar", "Words"),
        "bot.progress": loc("Прогресс", "Natija", "Progress"),
        "bot.premium": loc("Премиум", "Premium", "Premium"),
        "bot.help": loc("Помощь", "Yordam", "Help"),
        "bot.settings": loc("Настройки", "Sozlamalar", "Settings"),
        "web.home": loc("Главная", "Bosh sahifa", "Home"),
        "web.learn": loc("Учиться", "O'rganish", "Learn"),
        "web.scenarios": loc("Сценарии", "Vaziyatlar", "Scenarios"),
        "web.review": loc("Повторение", "Takrorlash", "Review"),
        "web.library": loc("Библиотека", "Kutubxona", "Library"),
        "web.settings": loc("Настройки", "Sozlamalar", "Settings"),
        "admin.content": loc("Контент", "Kontent", "Content"),
        "admin.localization": loc("Локализация", "Lokalizatsiya", "Localization"),
    }
    for compound_key, localized in entries.items():
        namespace, key = compound_key.split(".", 1)
        for language, value in localized.items():
            exists = (
                db.query(LocalizationEntry)
                .filter(LocalizationEntry.namespace == namespace, LocalizationEntry.key == key, LocalizationEntry.language == language)
                .first()
            )
            if not exists:
                db.add(LocalizationEntry(namespace=namespace, key=key, language=language, value=value, status="published"))
    db.flush()
