"""
Модуль анкеты для UniversityChooseBot:
- FSM-состояния анкеты
- Тексты вопросов и подсказок
- Списки вариантов ответов
- Inline-клавиатуры для каждого шага
- Форматирование итогового резюме
"""

import html
from typing import List, Set
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters.callback_data import CallbackData


# --- FSM Состояния ---

class QuestionnaireStates(StatesGroup):
    education_stage = State()      # Вопрос 1
    admission_term = State()       # Вопрос 2
    directions = State()           # Вопрос 3 (множественный выбор)
    countries = State()            # Вопрос 4
    languages = State()            # Вопрос 5
    budget = State()               # Вопрос 6
    exams = State()                # Вопрос 7 (свободный текст)
    achievements = State()         # Вопрос 8 (свободный текст)
    preferences = State()          # Вопрос 9 (свободный текст)
    summary = State()              # Экран резюме и подтверждения
    ai_consultation = State()      # Интерактивный диалог с ИИ-консультантом


# --- CallbackData структуры ---

class ChoiceCallback(CallbackData, prefix="ch"):
    step: int
    index: int


class DirectionToggleCallback(CallbackData, prefix="dt"):
    index: int


class DirectionDoneCallback(CallbackData, prefix="dd"):
    pass


class QuickAnswerCallback(CallbackData, prefix="qa"):
    step: int
    text: str


class NavCallback(CallbackData, prefix="nav"):
    action: str  # "back", "cancel", "start_quiz"
    from_step: int


class SummaryActionCallback(CallbackData, prefix="sum"):
    action: str  # "confirm", "restart", "cancel"


# --- Варианты ответов по вопросам ---

EDUCATION_STAGES = [
    "Учусь в школе.",
    "Уже окончил школу.",
    "Учусь в колледже.",
    "Учусь в университете.",
    "Другое.",
]

ADMISSION_TERMS = [
    "В ближайший год.",
    "Через два года или позже.",
    "Пока не определился.",
]

DIRECTIONS = [
    "Инженерия.",
    "Архитектура и строительство.",
    "IT и программирование.",
    "Физика и математика.",
    "Экономика и финансы.",
    "Бизнес и менеджмент.",
    "Медицина.",
    "Биология и химия.",
    "Дизайн и творчество.",
    "Право и международные отношения.",
    "Гуманитарные направления.",
    "Пока не знаю.",
]

COUNTRIES = [
    "Россия.",
    "Европа.",
    "Азия.",
    "Северная Америка.",
    "Рассматриваю любую страну.",
    "Пока не знаю.",
]

LANGUAGES = [
    "На русском.",
    "На английском.",
    "На местном языке после подготовки.",
    "Рассматриваю несколько вариантов.",
    "Пока не знаю.",
]

BUDGETS = [
    "Только бесплатное обучение.",
    "До 2 000 евро в год.",
    "От 2 000 до 5 000 евро в год.",
    "От 5 000 до 10 000 евро в год.",
    "Более 10 000 евро в год.",
    "Пока не знаю.",
]


# --- Тексты вопросов ---

START_MESSAGE = (
    "Привет! Я <b>UniversityChooseBot</b> — твой персональный помощник по поступлению.\n\n"
    "Я помогу тебе разобраться, какие направления обучения, страны и университеты "
    "могут подойти именно тебе.\n\n"
    "Учту твои интересы, образование, оценки, экзамены, достижения, бюджет и личные пожелания.\n\n"
    "Сначала ответь на несколько вопросов. Затем мы сможем подключить ИИ, чтобы "
    "подготовить персональные рекомендации."
)

QUESTION_TEXTS = {
    1: (
        "<b>Вопрос 1 из 9. Текущий этап образования</b>\n\n"
        "На каком этапе образования ты сейчас находишься?"
    ),
    2: (
        "<b>Вопрос 2 из 9. Срок поступления</b>\n\n"
        "Когда ты планируешь поступать?"
    ),
    3: (
        "<b>Вопрос 3 из 9. Интересующие направления</b>\n\n"
        "Какие направления обучения тебе интересны? Можно выбрать несколько.\n\n"
        "<i>Нажимай на кнопки, чтобы отметить нужные варианты (✅), а затем нажми «Готово».</i>"
    ),
    4: (
        "<b>Вопрос 4 из 9. Предпочтительные страны и регионы</b>\n\n"
        "Где ты хотел бы учиться?"
    ),
    5: (
        "<b>Вопрос 5 из 9. Язык обучения</b>\n\n"
        "На каком языке ты готов учиться?"
    ),
    6: (
        "<b>Вопрос 6 из 9. Бюджет на обучение</b>\n\n"
        "Какой бюджет ты рассматриваешь на оплату обучения за один год?\n\n"
        "💡 <i>Обрати внимание: вопрос касается именно платы за обучение (tuition fee), "
        "а не всех расходов на проживание и жизнь.</i>"
    ),
    7: (
        "<b>Вопрос 7 из 9. Экзамены и результаты</b>\n\n"
        "Какие экзамены ты уже сдал или планируешь сдавать? Укажи результаты, если они известны.\n\n"
        "💡 <b>Подсказка:</b>\n"
        "Например: <i>ЕГЭ по математике — планирую 85 баллов; физика — ещё готовлюсь; "
        "IELTS — пока не сдавал; SAT — не планирую.</i> Можешь также написать названия других "
        "экзаменов и предполагаемые баллы.\n\n"
        "<i>Напиши ответ в сообщении или выбери кнопку ниже, если экзамены пока не определены.</i>"
    ),
    8: (
        "<b>Вопрос 8 из 9. Достижения</b>\n\n"
        "Есть ли у тебя достижения, которые могут помочь при поступлении?\n\n"
        "💡 <b>Подсказка:</b>\n"
        "Расскажи об олимпиадах, призовых местах, исследовательских работах, научных проектах, "
        "конкурсах, спортивных достижениях, сертификатах, волонтёрстве, портфолио или других "
        "значимых результатах.\n\n"
        "<i>Если достижений пока нет, так и напиши — это нормально (например, «Нет» или «Пока нет»), "
        "либо нажми быструю кнопку ниже.</i>"
    ),
    9: (
        "<b>Вопрос 9 из 9. Дополнительные пожелания и ограничения</b>\n"
        "<i>(Это последний вопрос анкеты)</i>\n\n"
        "Есть ли у тебя дополнительные пожелания или ограничения, которые нужно учесть "
        "при выборе страны, университета или направления?\n\n"
        "💡 <b>Подсказка:</b>\n"
        "Напиши всё, что для тебя важно и о чём мы ещё не спросили.\n"
        "Например:\n"
        "• хочу остаться работать в стране после выпуска;\n"
        "• мне нужна стипендия;\n"
        "• не хочу сдавать дополнительные вступительные экзамены;\n"
        "• предпочитаю общежитие с отдельной комнатой;\n"
        "• не рассматриваю определённые страны;\n"
        "• хочу получить профессию с высоким доходом;\n"
        "• не хочу заниматься программированием;\n"
        "• важно иметь возможность работать во время учёбы;\n"
        "• не хочу тратить много денег на проживание.\n\n"
        "<i>Можешь написать несколько предложений. Если дополнительных пожеланий нет, "
        "напиши «Нет» или нажми кнопку ниже.</i>"
    ),
}

COMPLETION_MESSAGE = (
    "🎉 <b>Анкета готова!</b>\n\n"
    "Теперь у нас есть информация о твоём образовании, интересах, экзаменах, "
    "достижениях и пожеланиях.\n\n"
    "Следующим шагом подключим ИИ, чтобы проанализировать твой профиль и "
    "подготовить персональные рекомендации по странам, направлениям и университетам."
)

CANCEL_MESSAGE = (
    "❌ <b>Анкетирование отменено.</b>\n\n"
    "Твои текущие ответы были сброшены. Чтобы начать заново в любой момент, "
    "отправь команду /start или нажми кнопку ниже."
)


# --- Построители клавиатур ---

def get_start_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для приветственного экрана."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎯 Подобрать мне обучение",
                    callback_data=NavCallback(action="start_quiz", from_step=0).pack(),
                )
            ]
        ]
    )


def get_single_choice_keyboard(
    step: int,
    options: List[str],
    current_value: str | None = None,
) -> InlineKeyboardMarkup:
    """
    Клавиатура с одиночным выбором.
    Отмечает галочкой уже сохранённый ранее ответ, если он есть.
    """
    rows: List[List[InlineKeyboardButton]] = []
    for idx, opt in enumerate(options):
        # Если ранее этот пункт уже был выбран, подсвечиваем его
        label = f"✓ {opt}" if current_value == opt else opt
        rows.append([
            InlineKeyboardButton(
                text=label,
                callback_data=ChoiceCallback(step=step, index=idx).pack(),
            )
        ])

    # Нижняя строка навигации
    nav_row: List[InlineKeyboardButton] = []
    if step > 1:
        nav_row.append(
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=NavCallback(action="back", from_step=step).pack(),
            )
        )
    nav_row.append(
        InlineKeyboardButton(
            text="❌ Отменить анкету",
            callback_data=NavCallback(action="cancel", from_step=step).pack(),
        )
    )
    rows.append(nav_row)

    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_directions_keyboard(selected_indices: Set[int]) -> InlineKeyboardMarkup:
    """
    Клавиатура для вопроса 3 (множественный выбор направлений).
    """
    rows: List[List[InlineKeyboardButton]] = []
    for idx, name in enumerate(DIRECTIONS):
        icon = "✅" if idx in selected_indices else "⬜"
        rows.append([
            InlineKeyboardButton(
                text=f"{icon} {name}",
                callback_data=DirectionToggleCallback(index=idx).pack(),
            )
        ])

    # Кнопка подтверждения множественного выбора
    count_selected = len(selected_indices)
    done_label = f"Готово ({count_selected})" if count_selected > 0 else "Готово"
    rows.append([
        InlineKeyboardButton(
            text=f"👉 {done_label}",
            callback_data=DirectionDoneCallback().pack(),
        )
    ])

    # Строка навигации
    rows.append([
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=NavCallback(action="back", from_step=3).pack(),
        ),
        InlineKeyboardButton(
            text="❌ Отменить анкету",
            callback_data=NavCallback(action="cancel", from_step=3).pack(),
        ),
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_text_input_keyboard(
    step: int,
    quick_options: List[str] | None = None,
) -> InlineKeyboardMarkup:
    """
    Клавиатура для шагов со свободным текстовым вводом (Вопросы 7, 8, 9).
    Включает быстрые кнопки ответа и навигацию («Назад», «Отменить анкету»).
    """
    rows: List[List[InlineKeyboardButton]] = []
    if quick_options:
        for opt in quick_options:
            rows.append([
                InlineKeyboardButton(
                    text=opt,
                    callback_data=QuickAnswerCallback(step=step, text=opt).pack(),
                )
            ])

    # Навигация
    rows.append([
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=NavCallback(action="back", from_step=step).pack(),
        ),
        InlineKeyboardButton(
            text="❌ Отменить анкету",
            callback_data=NavCallback(action="cancel", from_step=step).pack(),
        ),
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_summary_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для экрана итогового резюме."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 Подобрать вузы с помощью ИИ",
                    callback_data=SummaryActionCallback(action="confirm").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ Назад к вопросу 9",
                    callback_data=NavCallback(action="back", from_step=10).pack(),
                ),
                InlineKeyboardButton(
                    text="🔄 Заполнить заново",
                    callback_data=SummaryActionCallback(action="restart").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить анкету",
                    callback_data=SummaryActionCallback(action="cancel").pack(),
                )
            ],
        ]
    )


def get_recommendations_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после выдачи рекомендаций ИИ."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💬 Задать вопрос ИИ-консультанту",
                    callback_data=SummaryActionCallback(action="ask_ai").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Моя анкета",
                    callback_data=SummaryActionCallback(action="show_summary").pack(),
                ),
                InlineKeyboardButton(
                    text="🔄 Заполнить заново",
                    callback_data=SummaryActionCallback(action="restart").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ Завершить",
                    callback_data=SummaryActionCallback(action="cancel").pack(),
                )
            ],
        ]
    )


def get_consultation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура в режиме активного диалога с ИИ-консультантом."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📋 Моя анкета",
                    callback_data=SummaryActionCallback(action="show_summary").pack(),
                ),
                InlineKeyboardButton(
                    text="🔄 Заполнить заново",
                    callback_data=SummaryActionCallback(action="restart").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ Завершить консультацию",
                    callback_data=SummaryActionCallback(action="cancel").pack(),
                )
            ],
        ]
    )


def format_summary(data: dict) -> str:
    """
    Форматирует итоговое резюме по всем 9 пунктам с безопасным экранированием HTML.
    """
    def sanitize(val: any) -> str:
        if val is None or val == "":
            return "<i>Не указано</i>"
        if isinstance(val, list):
            if not val:
                return "<i>Не указано</i>"
            return ", ".join(html.escape(str(item)) for item in val)
        return html.escape(str(val))

    ed_stage = sanitize(data.get("education_stage"))
    adm_term = sanitize(data.get("admission_term"))
    dirs = sanitize(data.get("directions"))
    ctrs = sanitize(data.get("countries"))
    langs = sanitize(data.get("languages"))
    bdgt = sanitize(data.get("budget"))
    exms = sanitize(data.get("exams"))
    achv = sanitize(data.get("achievements"))
    pref = sanitize(data.get("preferences"))

    summary_text = (
        "📋 <b>Итоговое резюме анкеты</b>\n\n"
        f"1️⃣ <b>Текущий этап образования:</b>\n{ed_stage}\n\n"
        f"2️⃣ <b>Планируемый срок поступления:</b>\n{adm_term}\n\n"
        f"3️⃣ <b>Интересующие направления:</b>\n{dirs}\n\n"
        f"4️⃣ <b>Предпочтительные страны и регионы:</b>\n{ctrs}\n\n"
        f"5️⃣ <b>Язык обучения:</b>\n{langs}\n\n"
        f"6️⃣ <b>Бюджет на обучение (в год):</b>\n{bdgt}\n\n"
        f"7️⃣ <b>Экзамены и результаты:</b>\n{exms}\n\n"
        f"8️⃣ <b>Достижения:</b>\n{achv}\n\n"
        f"9️⃣ <b>Дополнительные пожелания и ограничения:</b>\n{pref}\n\n"
        "<i>Пожалуйста, проверь данные. Если всё верно, нажми «Подтвердить анкету». "
        "Ты также можешь вернуться назад или заполнить анкету заново.</i>"
    )
    return summary_text
