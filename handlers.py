"""
Обработчики команд, сообщений и callback-запросов для UniversityChooseBot.
"""

import logging
from typing import Union
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest

from questionnaire import (
    QuestionnaireStates,
    ChoiceCallback,
    DirectionToggleCallback,
    DirectionDoneCallback,
    QuickAnswerCallback,
    NavCallback,
    SummaryActionCallback,
    EDUCATION_STAGES,
    ADMISSION_TERMS,
    DIRECTIONS,
    COUNTRIES,
    LANGUAGES,
    BUDGETS,
    START_MESSAGE,
    QUESTION_TEXTS,
    COMPLETION_MESSAGE,
    CANCEL_MESSAGE,
    get_start_keyboard,
    get_single_choice_keyboard,
    get_directions_keyboard,
    get_text_input_keyboard,
    get_summary_keyboard,
    get_recommendations_keyboard,
    get_consultation_keyboard,
    format_summary,
)
from ai_service import generate_recommendations, answer_followup_question

logger = logging.getLogger(__name__)
router = Router()


async def render_step(
    step: int,
    state: FSMContext,
    target: Union[Message, CallbackQuery],
    edit: bool = False,
) -> None:
    """
    Универсальная функция рендеринга шага анкеты.
    Управляет FSM-состоянием, подготавливает клавиатуру и отправляет либо редактирует сообщение.
    """
    data = await state.get_data()
    text = ""
    keyboard: InlineKeyboardMarkup | None = None

    if step == 1:
        await state.set_state(QuestionnaireStates.education_stage)
        text = QUESTION_TEXTS[1]
        keyboard = get_single_choice_keyboard(1, EDUCATION_STAGES, data.get("education_stage"))

    elif step == 2:
        await state.set_state(QuestionnaireStates.admission_term)
        text = QUESTION_TEXTS[2]
        keyboard = get_single_choice_keyboard(2, ADMISSION_TERMS, data.get("admission_term"))

    elif step == 3:
        await state.set_state(QuestionnaireStates.directions)
        selected_indices = set(data.get("directions_indices", []))
        text = QUESTION_TEXTS[3]
        keyboard = get_directions_keyboard(selected_indices)

    elif step == 4:
        await state.set_state(QuestionnaireStates.countries)
        text = QUESTION_TEXTS[4]
        keyboard = get_single_choice_keyboard(4, COUNTRIES, data.get("countries"))

    elif step == 5:
        await state.set_state(QuestionnaireStates.languages)
        text = QUESTION_TEXTS[5]
        keyboard = get_single_choice_keyboard(5, LANGUAGES, data.get("languages"))

    elif step == 6:
        await state.set_state(QuestionnaireStates.budget)
        text = QUESTION_TEXTS[6]
        keyboard = get_single_choice_keyboard(6, BUDGETS, data.get("budget"))

    elif step == 7:
        await state.set_state(QuestionnaireStates.exams)
        saved = data.get("exams")
        text = QUESTION_TEXTS[7]
        if saved:
            text += f"\n\n<i>Ранее сохранённый ответ:</i>\n«{saved}»"
        keyboard = get_text_input_keyboard(7, quick_options=["Пока не знаю / Ещё не выбрал"])

    elif step == 8:
        await state.set_state(QuestionnaireStates.achievements)
        saved = data.get("achievements")
        text = QUESTION_TEXTS[8]
        if saved:
            text += f"\n\n<i>Ранее сохранённый ответ:</i>\n«{saved}»"
        keyboard = get_text_input_keyboard(8, quick_options=["Пока нет достижений", "Нет"])

    elif step == 9:
        await state.set_state(QuestionnaireStates.preferences)
        saved = data.get("preferences")
        text = QUESTION_TEXTS[9]
        if saved:
            text += f"\n\n<i>Ранее сохранённый ответ:</i>\n«{saved}»"
        keyboard = get_text_input_keyboard(9, quick_options=["Нет дополнительных пожеланий", "Нет"])

    elif step == 10:
        await state.set_state(QuestionnaireStates.summary)
        text = format_summary(data)
        keyboard = get_summary_keyboard()

    # Отправка или редактирование
    if isinstance(target, CallbackQuery):
        msg = target.message
        if edit and msg:
            try:
                await msg.edit_text(text, reply_markup=keyboard)
                return
            except TelegramBadRequest as e:
                # Если текст и клавиатура не изменились, просто пропускаем
                if "message is not modified" in str(e).lower():
                    return
                logger.warning(f"Failed to edit message: {e}")
        # Если не получилось отредактировать или edit=False, отправляем новое сообщение
        if msg:
            await msg.answer(text, reply_markup=keyboard)
    else:
        # target — обычный Message
        await target.answer(text, reply_markup=keyboard)


# --- Команды /start и /cancel ---

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Обработчик команды /start."""
    await state.clear()
    await message.answer(
        text=START_MESSAGE,
        reply_markup=get_start_keyboard(),
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    """Обработчик команды /cancel."""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer(
            "Сейчас нет активной анкеты. Чтобы начать, отправь /start",
            reply_markup=get_start_keyboard(),
        )
        return

    await state.clear()
    await message.answer(
        text=CANCEL_MESSAGE,
        reply_markup=get_start_keyboard(),
    )


# --- Навигация и запуск ---

@router.callback_query(NavCallback.filter(F.action == "start_quiz"))
async def on_start_quiz(callback: CallbackQuery, state: FSMContext) -> None:
    """Запуск анкеты по кнопке «Подобрать мне обучение»."""
    await state.clear()
    await render_step(1, state, callback, edit=True)
    await callback.answer()


@router.callback_query(NavCallback.filter(F.action == "cancel"))
async def on_cancel_quiz(callback: CallbackQuery, state: FSMContext) -> None:
    """Отмена анкеты через inline-кнопку."""
    await state.clear()
    try:
        if callback.message:
            await callback.message.edit_text(
                text=CANCEL_MESSAGE,
                reply_markup=get_start_keyboard(),
            )
    except TelegramBadRequest:
        if callback.message:
            await callback.message.answer(
                text=CANCEL_MESSAGE,
                reply_markup=get_start_keyboard(),
            )
    await callback.answer("Анкета отменена")


@router.callback_query(NavCallback.filter(F.action == "back"))
async def on_nav_back(callback: CallbackQuery, callback_data: NavCallback, state: FSMContext) -> None:
    """
    Возврат к предыдущему вопросу анкеты с сохранением введённых данных.
    """
    from_step = callback_data.from_step
    target_step = from_step - 1

    if target_step < 1:
        # Если шаг меньше 1, возвращаем на стартовый экран
        await state.clear()
        try:
            if callback.message:
                await callback.message.edit_text(
                    text=START_MESSAGE,
                    reply_markup=get_start_keyboard(),
                )
        except TelegramBadRequest:
            pass
        await callback.answer()
        return

    await render_step(target_step, state, callback, edit=True)
    await callback.answer()


# --- Вопрос 1: Текущий этап образования ---

@router.callback_query(QuestionnaireStates.education_stage, ChoiceCallback.filter(F.step == 1))
async def on_education_choice(
    callback: CallbackQuery,
    callback_data: ChoiceCallback,
    state: FSMContext,
) -> None:
    if 0 <= callback_data.index < len(EDUCATION_STAGES):
        chosen = EDUCATION_STAGES[callback_data.index]
        await state.update_data(education_stage=chosen)
        await render_step(2, state, callback, edit=True)
    await callback.answer()


# --- Вопрос 2: Срок поступления ---

@router.callback_query(QuestionnaireStates.admission_term, ChoiceCallback.filter(F.step == 2))
async def on_admission_choice(
    callback: CallbackQuery,
    callback_data: ChoiceCallback,
    state: FSMContext,
) -> None:
    if 0 <= callback_data.index < len(ADMISSION_TERMS):
        chosen = ADMISSION_TERMS[callback_data.index]
        await state.update_data(admission_term=chosen)
        await render_step(3, state, callback, edit=True)
    await callback.answer()


# --- Вопрос 3: Интересующие направления (множественный выбор) ---

@router.callback_query(QuestionnaireStates.directions, DirectionToggleCallback.filter())
async def on_direction_toggle(
    callback: CallbackQuery,
    callback_data: DirectionToggleCallback,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    selected: set[int] = set(data.get("directions_indices", []))
    idx = callback_data.index
    dont_know_idx = len(DIRECTIONS) - 1  # Индекс «Пока не знаю.»

    if idx == dont_know_idx:
        # Если нажат «Пока не знаю»
        if dont_know_idx in selected:
            selected.remove(dont_know_idx)
        else:
            # Очищаем все другие варианты, оставляем только «Пока не знаю»
            selected = {dont_know_idx}
    else:
        # Если выбрано конкретное направление, убираем «Пока не знаю»
        selected.discard(dont_know_idx)
        if idx in selected:
            selected.remove(idx)
        else:
            selected.add(idx)

    await state.update_data(directions_indices=sorted(list(selected)))

    # Обновляем только кнопки сообщения
    if callback.message:
        try:
            await callback.message.edit_reply_markup(
                reply_markup=get_directions_keyboard(selected)
            )
        except TelegramBadRequest:
            pass

    await callback.answer()


@router.callback_query(QuestionnaireStates.directions, DirectionDoneCallback.filter())
async def on_directions_done(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    selected_indices = data.get("directions_indices", [])

    if not selected_indices:
        await callback.answer(
            "Пожалуйста, выбери хотя бы одно направление или вариант «Пока не знаю».",
            show_alert=True,
        )
        return

    # Сохраняем текстовый список направлений
    chosen_names = [DIRECTIONS[i] for i in sorted(selected_indices)]
    await state.update_data(directions=chosen_names)

    await render_step(4, state, callback, edit=True)
    await callback.answer()


# --- Вопрос 4: Страны и регионы ---

@router.callback_query(QuestionnaireStates.countries, ChoiceCallback.filter(F.step == 4))
async def on_country_choice(
    callback: CallbackQuery,
    callback_data: ChoiceCallback,
    state: FSMContext,
) -> None:
    if 0 <= callback_data.index < len(COUNTRIES):
        chosen = COUNTRIES[callback_data.index]
        await state.update_data(countries=chosen)
        await render_step(5, state, callback, edit=True)
    await callback.answer()


# --- Вопрос 5: Язык обучения ---

@router.callback_query(QuestionnaireStates.languages, ChoiceCallback.filter(F.step == 5))
async def on_language_choice(
    callback: CallbackQuery,
    callback_data: ChoiceCallback,
    state: FSMContext,
) -> None:
    if 0 <= callback_data.index < len(LANGUAGES):
        chosen = LANGUAGES[callback_data.index]
        await state.update_data(languages=chosen)
        await render_step(6, state, callback, edit=True)
    await callback.answer()


# --- Вопрос 6: Бюджет на обучение ---

@router.callback_query(QuestionnaireStates.budget, ChoiceCallback.filter(F.step == 6))
async def on_budget_choice(
    callback: CallbackQuery,
    callback_data: ChoiceCallback,
    state: FSMContext,
) -> None:
    if 0 <= callback_data.index < len(BUDGETS):
        chosen = BUDGETS[callback_data.index]
        await state.update_data(budget=chosen)
        await render_step(7, state, callback, edit=True)
    await callback.answer()


# --- Вопрос 7: Экзамены и результаты ---

@router.callback_query(QuestionnaireStates.exams, QuickAnswerCallback.filter(F.step == 7))
async def on_exams_quick_answer(
    callback: CallbackQuery,
    callback_data: QuickAnswerCallback,
    state: FSMContext,
) -> None:
    await state.update_data(exams=callback_data.text)
    await render_step(8, state, callback, edit=True)
    await callback.answer()


@router.message(QuestionnaireStates.exams, F.text)
async def on_exams_text(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text:
        await message.answer("Пожалуйста, напиши ответ текстом или нажми кнопку ниже.")
        return
    await state.update_data(exams=text)
    await render_step(8, state, message)


# --- Вопрос 8: Достижения ---

@router.callback_query(QuestionnaireStates.achievements, QuickAnswerCallback.filter(F.step == 8))
async def on_achievements_quick_answer(
    callback: CallbackQuery,
    callback_data: QuickAnswerCallback,
    state: FSMContext,
) -> None:
    await state.update_data(achievements=callback_data.text)
    await render_step(9, state, callback, edit=True)
    await callback.answer()


@router.message(QuestionnaireStates.achievements, F.text)
async def on_achievements_text(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text:
        await message.answer("Пожалуйста, напиши ответ текстом или нажми кнопку ниже.")
        return
    await state.update_data(achievements=text)
    await render_step(9, state, message)


# --- Вопрос 9: Дополнительные пожелания и ограничения ---

@router.callback_query(QuestionnaireStates.preferences, QuickAnswerCallback.filter(F.step == 9))
async def on_preferences_quick_answer(
    callback: CallbackQuery,
    callback_data: QuickAnswerCallback,
    state: FSMContext,
) -> None:
    await state.update_data(preferences=callback_data.text)
    await render_step(10, state, callback, edit=True)
    await callback.answer()


@router.message(QuestionnaireStates.preferences, F.text)
async def on_preferences_text(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text:
        await message.answer("Пожалуйста, напиши ответ текстом или нажми кнопку ниже.")
        return
    await state.update_data(preferences=text)
    await render_step(10, state, message)


# --- Экран 10: Резюме, ИИ-подбор и консультация ---

@router.callback_query(QuestionnaireStates.summary, SummaryActionCallback.filter(F.action == "confirm"))
async def on_summary_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """Генерация рекомендаций с помощью онлайн-ИИ."""
    data = await state.get_data()
    msg = callback.message

    loading_text = (
        "⏳ <b>ИИ анализирует твою анкету...</b>\n\n"
        "Подбираю подходящие университеты, образовательные программы, "
        "требования к поступлению и возможности стипендий.\n"
        "Обычно это занимает 5–15 секунд..."
    )
    if msg:
        try:
            await msg.edit_text(loading_text)
        except TelegramBadRequest:
            await msg.answer(loading_text)

    # Генерация персонального отчёта через облачную нейросеть
    recommendations = await generate_recommendations(data)
    await state.update_data(recommendations=recommendations, ai_chat_history=[])
    await state.set_state(QuestionnaireStates.ai_consultation)

    # Разбивка на части, если длина превышает лимит Telegram (4096 символов)
    chunks = []
    if len(recommendations) <= 3900:
        chunks = [recommendations]
    else:
        paragraphs = recommendations.split("\n\n")
        current_chunk = ""
        for p in paragraphs:
            if len(current_chunk) + len(p) + 2 < 3900:
                current_chunk += (p + "\n\n")
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = p + "\n\n"
        if current_chunk:
            chunks.append(current_chunk.strip())

    if not chunks:
        chunks = [recommendations]

    for idx, chunk in enumerate(chunks):
        is_last = (idx == len(chunks) - 1)
        kb = get_recommendations_keyboard() if is_last else None
        if msg:
            try:
                await msg.answer(chunk, reply_markup=kb, parse_mode="HTML")
            except TelegramBadRequest:
                # Если в HTML от нейросети есть незакрытые теги, отправляем без parse_mode
                await msg.answer(chunk, reply_markup=kb, parse_mode=None)

    await callback.answer("Подбор готов!")


@router.callback_query(
    QuestionnaireStates.ai_consultation,
    SummaryActionCallback.filter(F.action == "ask_ai"),
)
async def on_ask_ai_click(callback: CallbackQuery, state: FSMContext) -> None:
    """Подсказка для режима вопроса к ИИ."""
    if callback.message:
        await callback.message.answer(
            "💬 <b>Задай любой вопрос ИИ-консультанту!</b>\n\n"
            "Например:\n"
            "• <i>«Какие стипендии или гранты есть по выбранным направлениям?»</i>\n"
            "• <i>«Сколько в среднем стоит аренда общежития?»</i>\n"
            "• <i>«С какими баллами IELTS берут в этот вуз?»</i>\n\n"
            "Просто отправь свой вопрос текстовым сообщением в чат 👇"
        )
    await callback.answer()


@router.callback_query(
    QuestionnaireStates.ai_consultation,
    SummaryActionCallback.filter(F.action == "show_summary"),
)
async def on_show_summary_click(callback: CallbackQuery, state: FSMContext) -> None:
    """Повторный показ анкеты пользователя."""
    data = await state.get_data()
    summary_text = format_summary(data)
    if callback.message:
        await callback.message.answer(summary_text, reply_markup=get_recommendations_keyboard())
    await callback.answer()


@router.message(QuestionnaireStates.ai_consultation, F.text)
async def on_ai_consultation_message(message: Message, state: FSMContext) -> None:
    """Ответ на уточняющие вопросы пользователя к ИИ."""
    question = (message.text or "").strip()
    if not question:
        return

    data = await state.get_data()
    history = data.get("ai_chat_history", [])

    if message.bot:
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        reply = await answer_followup_question(data, history, question)
    except Exception as e:
        logger.error(f"Error answering followup question: {e}")
        reply = (
            "Извини, произошла временная задержка связи с нейросетью. "
            "Пожалуйста, повтори свой вопрос через несколько секунд."
        )

    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": reply})
    await state.update_data(ai_chat_history=history)

    try:
        await message.answer(reply, reply_markup=get_consultation_keyboard(), parse_mode="HTML")
    except TelegramBadRequest:
        await message.answer(reply, reply_markup=get_consultation_keyboard(), parse_mode=None)


@router.callback_query(
    F.data.in_({
        SummaryActionCallback(action="restart").pack(),
    })
)
async def on_summary_restart(callback: CallbackQuery, state: FSMContext) -> None:
    """Очистка ответов и заполнение заново с 1 вопроса."""
    await state.clear()
    await render_step(1, state, callback, edit=True)
    await callback.answer("Анкета очищена. Заполняем заново!")


@router.callback_query(
    F.data.in_({
        SummaryActionCallback(action="cancel").pack(),
    })
)
async def on_summary_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    """Отмена анкеты и завершение консультации."""
    await state.clear()
    try:
        if callback.message:
            await callback.message.edit_text(
                text=CANCEL_MESSAGE,
                reply_markup=get_start_keyboard(),
            )
    except TelegramBadRequest:
        if callback.message:
            await callback.message.answer(
                text=CANCEL_MESSAGE,
                reply_markup=get_start_keyboard(),
            )
    await callback.answer("Консультация завершена")


# --- Защита от непредвиденных сообщений ---

@router.message(
    QuestionnaireStates.education_stage,
    QuestionnaireStates.admission_term,
    QuestionnaireStates.directions,
    QuestionnaireStates.countries,
    QuestionnaireStates.languages,
    QuestionnaireStates.budget,
)
async def on_unexpected_text_for_button_step(message: Message, state: FSMContext) -> None:
    """
    Если пользователь отправляет текст на шагах, где требуется выбор кнопками.
    """
    await message.answer(
        "ℹ️ Пожалуйста, выбери вариант ответа с помощью <b>кнопок под сообщением</b> выше.\n\n"
        "Если ты хочешь прервать анкетирование, отправь /cancel."
    )


@router.message(
    QuestionnaireStates.exams,
    QuestionnaireStates.achievements,
    QuestionnaireStates.preferences,
)
async def on_unexpected_content_for_text_step(message: Message) -> None:
    """
    Если пользователь отправил стикер, фото или файл вместо текста.
    """
    await message.answer(
        "ℹ️ Пожалуйста, отправь свой ответ <b>текстовым сообщением</b> или воспользуйся кнопками ниже."
    )


@router.callback_query()
async def on_unknown_callback(callback: CallbackQuery) -> None:
    """Обработка устаревших или неизвестных нажатий кнопок."""
    await callback.answer("Кнопка устарела или действие уже выполнено.", show_alert=False)
