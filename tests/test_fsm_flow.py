"""
Интеграционные тесты для цепочки FSM и сценариев анкеты.
"""

import pytest
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey

from questionnaire import (
    QuestionnaireStates,
    EDUCATION_STAGES,
    ADMISSION_TERMS,
    DIRECTIONS,
    COUNTRIES,
    LANGUAGES,
    BUDGETS,
    format_summary,
)


@pytest.fixture
def fsm_context():
    storage = MemoryStorage()
    key = StorageKey(bot_id=1, chat_id=12345, user_id=12345)
    return FSMContext(storage=storage, key=key)


@pytest.mark.asyncio
async def test_full_questionnaire_fsm_flow(fsm_context: FSMContext):
    """
    Симуляция полного прохождения всех 9 вопросов и формирования резюме.
    """
    # 1. Шаг 1: Текущий этап образования
    await fsm_context.set_state(QuestionnaireStates.education_stage)
    await fsm_context.update_data(education_stage=EDUCATION_STAGES[0])
    
    current_state = await fsm_context.get_state()
    assert current_state == QuestionnaireStates.education_stage.state

    # 2. Шаг 2: Срок поступления
    await fsm_context.set_state(QuestionnaireStates.admission_term)
    await fsm_context.update_data(admission_term=ADMISSION_TERMS[0])

    # 3. Шаг 3: Направления (множественный выбор)
    await fsm_context.set_state(QuestionnaireStates.directions)
    selected_indices = [0, 2]  # Инженерия, IT
    chosen_names = [DIRECTIONS[i] for i in selected_indices]
    await fsm_context.update_data(
        directions_indices=selected_indices,
        directions=chosen_names,
    )

    # 4. Шаг 4: Страны и регионы
    await fsm_context.set_state(QuestionnaireStates.countries)
    await fsm_context.update_data(countries=COUNTRIES[1])  # Европа

    # 5. Шаг 5: Язык обучения
    await fsm_context.set_state(QuestionnaireStates.languages)
    await fsm_context.update_data(languages=LANGUAGES[1])  # На английском

    # 6. Шаг 6: Бюджет
    await fsm_context.set_state(QuestionnaireStates.budget)
    await fsm_context.update_data(budget=BUDGETS[2])  # От 2000 до 5000

    # 7. Шаг 7: Экзамены (свободный текст)
    await fsm_context.set_state(QuestionnaireStates.exams)
    exams_text = "ЕГЭ математика 88, информатика 90, IELTS 7.0"
    await fsm_context.update_data(exams=exams_text)

    # 8. Шаг 8: Достижения (свободный текст)
    await fsm_context.set_state(QuestionnaireStates.achievements)
    achievements_text = "Призер регионального этапа ВсОШ"
    await fsm_context.update_data(achievements=achievements_text)

    # 9. Шаг 9: Пожелания и ограничения (свободный текст)
    await fsm_context.set_state(QuestionnaireStates.preferences)
    preferences_text = "Возможность подрабатывать во время учёбы"
    await fsm_context.update_data(preferences=preferences_text)

    # 10. Экран 10: Резюме
    await fsm_context.set_state(QuestionnaireStates.summary)
    data = await fsm_context.get_data()

    # Проверяем сохранённые данные
    assert data["education_stage"] == EDUCATION_STAGES[0]
    assert data["admission_term"] == ADMISSION_TERMS[0]
    assert "IT и программирование." in data["directions"]
    assert data["countries"] == COUNTRIES[1]
    assert data["languages"] == LANGUAGES[1]
    assert data["budget"] == BUDGETS[2]
    assert data["exams"] == exams_text
    assert data["achievements"] == achievements_text
    assert data["preferences"] == preferences_text

    # Формируем резюме и проверяем содержание
    summary = format_summary(data)
    assert exams_text in summary
    assert achievements_text in summary
    assert preferences_text in summary

    # Подтверждение анкеты завершает FSM
    await fsm_context.clear()
    cleared_state = await fsm_context.get_state()
    cleared_data = await fsm_context.get_data()
    assert cleared_state is None
    assert cleared_data == {}


@pytest.mark.asyncio
async def test_back_navigation_preserves_data(fsm_context: FSMContext):
    """
    Проверка того, что при возвращении назад данные не теряются.
    """
    # Пользователь ответил на первые 2 вопроса
    await fsm_context.update_data(
        education_stage="Учусь в колледже.",
        admission_term="В ближайший год.",
    )
    await fsm_context.set_state(QuestionnaireStates.directions)

    # Пользователь нажимает «Назад» к вопросу 2
    await fsm_context.set_state(QuestionnaireStates.admission_term)
    data = await fsm_context.get_data()
    assert data["education_stage"] == "Учусь в колледже."
    assert data["admission_term"] == "В ближайший год."

    # Пользователь меняет ответ на вопрос 2
    await fsm_context.update_data(admission_term="Через два года или позже.")
    data_after = await fsm_context.get_data()
    assert data_after["education_stage"] == "Учусь в колледже."
    assert data_after["admission_term"] == "Через два года или позже."


@pytest.mark.asyncio
async def test_cancel_clears_fsm(fsm_context: FSMContext):
    """
    Проверка, что отмена анкеты сбрасывает состояние и данные.
    """
    await fsm_context.set_state(QuestionnaireStates.budget)
    await fsm_context.update_data(education_stage="Учусь в школе.", budget="Только бесплатное обучение.")

    await fsm_context.clear()
    assert await fsm_context.get_state() is None
    assert await fsm_context.get_data() == {}
