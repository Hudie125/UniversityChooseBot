"""
Автоматические тесты для UniversityChooseBot:
- Проверка структуры данных и списков вариантов
- Проверка построения клавиатур
- Проверка логики множественного выбора
- Проверка корректности и полноты итогового резюме
- Проверка экранирования спецсимволов HTML
"""

import pytest
from questionnaire import (
    EDUCATION_STAGES,
    ADMISSION_TERMS,
    DIRECTIONS,
    COUNTRIES,
    LANGUAGES,
    BUDGETS,
    QUESTION_TEXTS,
    START_MESSAGE,
    COMPLETION_MESSAGE,
    CANCEL_MESSAGE,
    get_start_keyboard,
    get_single_choice_keyboard,
    get_directions_keyboard,
    get_text_input_keyboard,
    get_summary_keyboard,
    format_summary,
)


def test_question_counts_and_options():
    """Проверяем, что все 9 вопросов и их варианты заданы в полном объёме."""
    assert len(QUESTION_TEXTS) == 9
    for i in range(1, 10):
        assert i in QUESTION_TEXTS
        assert len(QUESTION_TEXTS[i]) > 0

    assert len(EDUCATION_STAGES) == 5
    assert "Учусь в школе." in EDUCATION_STAGES
    assert "Другое." in EDUCATION_STAGES

    assert len(ADMISSION_TERMS) == 3
    assert "В ближайший год." in ADMISSION_TERMS

    assert len(DIRECTIONS) == 12
    assert "Инженерия." in DIRECTIONS
    assert "IT и программирование." in DIRECTIONS
    assert "Пока не знаю." in DIRECTIONS

    assert len(COUNTRIES) == 6
    assert "Россия." in COUNTRIES
    assert "Рассматриваю любую страну." in COUNTRIES

    assert len(LANGUAGES) == 5
    assert "На русском." in LANGUAGES
    assert "На английском." in LANGUAGES

    assert len(BUDGETS) == 6
    assert "Только бесплатное обучение." in BUDGETS
    assert "Более 10 000 евро в год." in BUDGETS


def test_start_keyboard():
    """Проверка клавиатуры приветственного экрана."""
    kb = get_start_keyboard()
    assert len(kb.inline_keyboard) == 1
    assert "Подобрать мне обучение" in kb.inline_keyboard[0][0].text
    assert "start_quiz" in kb.inline_keyboard[0][0].callback_data


def test_single_choice_keyboard_step1():
    """Проверка клавиатуры для шага 1 (без кнопки «Назад», но с «Отменить»)."""
    kb = get_single_choice_keyboard(1, EDUCATION_STAGES)
    # 5 вариантов ответов + 1 строка навигации
    assert len(kb.inline_keyboard) == 6
    nav_row = kb.inline_keyboard[-1]
    # На шаге 1 только кнопка «Отменить анкету»
    assert len(nav_row) == 1
    assert "Отменить анкету" in nav_row[0].text


def test_single_choice_keyboard_step2_with_back():
    """Проверка клавиатуры для шагов 2+ (содержит «Назад» и «Отменить»)."""
    kb = get_single_choice_keyboard(2, ADMISSION_TERMS, current_value="В ближайший год.")
    # 3 варианта + 1 строка навигации
    assert len(kb.inline_keyboard) == 4
    # Первый вариант должен быть подсвечен галочкой
    assert "✓ В ближайший год." in kb.inline_keyboard[0][0].text
    # Навигация
    nav_row = kb.inline_keyboard[-1]
    assert len(nav_row) == 2
    assert "Назад" in nav_row[0].text
    assert "Отменить анкету" in nav_row[1].text


def test_directions_keyboard():
    """Проверка клавиатуры множественного выбора направлений."""
    selected = {0, 2}  # Инженерия и IT
    kb = get_directions_keyboard(selected)
    
    # 12 направлений + 1 кнопка Готово + 1 строка навигации
    assert len(kb.inline_keyboard) == 14
    
    # Индекс 0 отмечен ✅
    assert "✅" in kb.inline_keyboard[0][0].text
    # Индекс 1 не отмечен ⬜
    assert "⬜" in kb.inline_keyboard[1][0].text
    # Индекс 2 отмечен ✅
    assert "✅" in kb.inline_keyboard[2][0].text

    # Кнопка Готово с количеством
    done_row = kb.inline_keyboard[-2]
    assert "Готово (2)" in done_row[0].text

    # Строка навигации
    nav_row = kb.inline_keyboard[-1]
    assert "Назад" in nav_row[0].text
    assert "Отменить анкету" in nav_row[1].text


def test_text_input_keyboard():
    """Проверка клавиатуры для свободного ввода с быстрыми вариантами."""
    kb = get_text_input_keyboard(7, quick_options=["Пока не знаю / Ещё не выбрал"])
    # 1 быстрый вариант + 1 строка навигации
    assert len(kb.inline_keyboard) == 2
    assert "Пока не знаю / Ещё не выбрал" in kb.inline_keyboard[0][0].text
    nav_row = kb.inline_keyboard[-1]
    assert "Назад" in nav_row[0].text
    assert "Отменить анкету" in nav_row[1].text


def test_summary_keyboard():
    """Проверка клавиатуры на этапе итогового резюме."""
    kb = get_summary_keyboard()
    # Должны быть кнопки: Подобрать вузы с помощью ИИ, Назад к вопросу 9, Заполнить заново, Отменить
    buttons_text = [btn.text for row in kb.inline_keyboard for btn in row]
    assert any("Подобрать вузы" in t or "Подтвердить" in t for t in buttons_text)
    assert any("Назад к вопросу 9" in t for t in buttons_text)
    assert any("Заполнить заново" in t for t in buttons_text)
    assert any("Отменить анкету" in t for t in buttons_text)


def test_ai_keyboards():
    """Проверка клавиатур для режима ИИ-консультации."""
    from questionnaire import get_recommendations_keyboard, get_consultation_keyboard
    rec_kb = get_recommendations_keyboard()
    rec_texts = [btn.text for row in rec_kb.inline_keyboard for btn in row]
    assert any("Задать вопрос" in t for t in rec_texts)
    assert any("Моя анкета" in t for t in rec_texts)

    cons_kb = get_consultation_keyboard()
    cons_texts = [btn.text for row in cons_kb.inline_keyboard for btn in row]
    assert any("Завершить консультацию" in t for t in cons_texts)


def test_format_summary_completeness_and_html_escaping():
    """
    Проверяем, что в итоговом резюме присутствуют все 9 пунктов,
    а специальные символы HTML (<, >, &) корректно экранируются.
    """
    data = {
        "education_stage": "Учусь в школе.",
        "admission_term": "В ближайший год.",
        "directions": ["IT и программирование.", "Физика и математика."],
        "countries": "Европа.",
        "languages": "На английском.",
        "budget": "От 2 000 до 5 000 евро в год.",
        "exams": "ЕГЭ <математика> & физика — 90+ баллов",
        "achievements": "Победитель всероса по информатике <1 место>",
        "preferences": "Нужно общежитие & стипендия > 500 евро",
    }

    summary = format_summary(data)

    # Проверка наличия всех 9 пунктов
    for i in range(1, 10):
        assert f"{i}️⃣" in summary

    # Проверка безопасного экранирования HTML
    assert "<математика>" not in summary
    assert "&lt;математика&gt;" in summary
    assert "&amp;" in summary
    assert "&gt; 500" in summary

    # Проверка форматирования списка направлений
    assert "IT и программирование., Физика и математика." in summary


def test_format_summary_empty_defaults():
    """Проверка корректной обработки незаполненных полей в резюме."""
    summary = format_summary({})
    for i in range(1, 10):
        assert f"{i}️⃣" in summary
    assert "<i>Не указано</i>" in summary
