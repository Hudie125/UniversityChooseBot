"""
Модуль интеграции с онлайн-нейросетью для UniversityChooseBot.
Использует бесплатную облачную нейросеть (без нагрузки на компьютер пользователя),
с поддержкой работы через локальный прокси.
"""

import os
import logging
import asyncio
from typing import Dict, Any, List
import aiohttp

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Ты — профессиональный персональный AI-консультант по международному и отечественному "
    "поступлению в вузы (UniversityChooseBot).\n\n"
    "Твоя задача — внимательно изучить анкету абитуриента и составить подробный, "
    "структурированный и реалистичный отчёт с персональными рекомендациями.\n\n"
    "Структура твоего ответа:\n"
    "🎯 <b>1. Оценка профиля и ключевые преимущества</b>\n"
    "— Анализ бэкграунда, сильных сторон и реалистичности поступления в планируемый срок.\n\n"
    "🌍 <b>2. Рекомендуемые страны и регионы</b>\n"
    "— 2-3 наиболее подходящие страны с учётом бюджета, языка и визовых перспектив.\n\n"
    "🏛 <b>3. Топ подходящих университетов и программ</b>\n"
    "— 3-5 конкретных университетов с указанием программ бакалавриата/магистратуры, "
    "соответствия заявленному бюджету обучения и языковым требованиям.\n\n"
    "📋 <b>4. Стратегия по экзаменам и поступлению</b>\n"
    "— Что необходимо досдать/подтвердить, минимальные баллы, дедлайны и требования к документам.\n\n"
    "💰 <b>5. Возможности снижения стоимости и стипендии</b>\n"
    "— Как получить гранты, скидки или стипендии под указанный профиль и достижения.\n\n"
    "💡 <b>6. Практические следующие шаги</b>\n"
    "— Чёткий пошаговый план действий на ближайшие 3-6 месяцев.\n\n"
    "Пиши доброжелательно, экспертно, мотивирующе, на хорошем русском языке. "
    "Используй форматирование с эмодзи и выделением ключевых мыслей."
)


def build_user_prompt(data: Dict[str, Any]) -> str:
    """Формирует текстовый запрос на основе данных анкеты."""
    dirs = data.get("directions", [])
    if isinstance(dirs, list):
        dirs_str = ", ".join(dirs)
    else:
        dirs_str = str(dirs)

    prompt = (
        "Пожалуйста, проанализируй мою анкету и подбери оптимальные варианты обучения:\n\n"
        f"• Текущий этап образования: {data.get('education_stage', 'Не указано')}\n"
        f"• Планируемый срок поступления: {data.get('admission_term', 'Не указано')}\n"
        f"• Интересующие направления: {dirs_str}\n"
        f"• Предпочтительные страны: {data.get('countries', 'Не указано')}\n"
        f"• Язык обучения: {data.get('languages', 'Не указано')}\n"
        f"• Бюджет на обучение (в год): {data.get('budget', 'Не указано')}\n"
        f"• Экзамены и текущие/планируемые баллы: {data.get('exams', 'Пока не определены')}\n"
        f"• Личные достижения и портфолио: {data.get('achievements', 'Нет специфических достижений')}\n"
        f"• Дополнительные пожелания и ограничения: {data.get('preferences', 'Нет')}\n"
    )
    return prompt


async def query_online_llm(messages: List[Dict[str, str]], timeout_seconds: int = 45) -> str:
    """
    Отправляет запрос к бесплатной облачной нейросети (Pollinations.ai).
    Все вычисления производятся в облаке.
    """
    proxy_url = os.getenv("PROXY_URL")
    http_proxy = None
    if proxy_url:
        # Для aiohttp http-клиента проксируем через http-порт
        http_proxy = proxy_url.replace("socks5://", "http://").replace("socks5h://", "http://")

    # Формируем тело запроса
    payload = {
        "messages": messages,
        "model": "openai",
        "jsonMode": False,
        "seed": 42,
    }

    url = "https://text.pollinations.ai/"

    timeout = aiohttp.ClientTimeout(total=timeout_seconds)
    connector = aiohttp.TCPConnector(ssl=False)

    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        try:
            async with session.post(url, json=payload, proxy=http_proxy) as response:
                if response.status == 200:
                    answer = await response.text()
                    if answer and len(answer.strip()) > 50:
                        return answer.strip()
                logger.warning(f"Pollinations returned status {response.status}")
        except Exception as e:
            logger.warning(f"Primary AI endpoint failed: {e}. Trying fallback model...")

        # Запасной запрос с моделью mistral
        try:
            payload["model"] = "mistral"
            async with session.post(url, json=payload, proxy=http_proxy) as response:
                if response.status == 200:
                    answer = await response.text()
                    if answer and len(answer.strip()) > 50:
                        return answer.strip()
        except Exception as e:
            logger.error(f"Fallback AI endpoint failed: {e}")

    raise RuntimeError("Не удалось получить ответ от онлайн-нейросети.")


async def generate_recommendations(data: Dict[str, Any]) -> str:
    """
    Генерирует детальные рекомендации для пользователя на основе анкеты.
    """
    user_prompt = build_user_prompt(data)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        return await query_online_llm(messages, timeout_seconds=45)
    except Exception as e:
        logger.error(f"Error in generate_recommendations: {e}")
        # Резервный качественный ответ в случае временных сетевых сбоев
        return _generate_fallback_recommendations(data)


async def answer_followup_question(data: Dict[str, Any], chat_history: List[Dict[str, str]], question: str) -> str:
    """
    Отвечает на уточняющие вопросы пользователя в режиме диалога с ИИ-консультантом.
    """
    system_followup = (
        "Ты — персональный AI-консультант по образованию UniversityChooseBot. "
        "Пользователь уже заполнил анкету и получил рекомендации, а теперь задаёт уточняющий вопрос. "
        "Учитывай контекст его анкеты при ответе. Отвечай кратко, по делу и дружелюбно.\n\n"
        f"Данные анкеты пользователя:\n{build_user_prompt(data)}"
    )

    messages = [{"role": "system", "content": system_followup}]
    # Добавляем последние сообщения диалога (до 6 штук)
    for msg in chat_history[-6:]:
        messages.append(msg)
    messages.append({"role": "user", "content": question})

    return await query_online_llm(messages, timeout_seconds=30)


def _generate_fallback_recommendations(data: Dict[str, Any]) -> str:
    """Резервный генератор рекомендаций на случай отсутствия связи с API."""
    stage = data.get("education_stage", "Обучение")
    country = data.get("countries", "Любая страна")
    lang = data.get("languages", "Русский/Английский")
    budget = data.get("budget", "Доступный бюджет")
    dirs = data.get("directions", ["Современные направления"])
    if isinstance(dirs, list):
        dirs_str = ", ".join(dirs)
    else:
        dirs_str = str(dirs)

    return (
        "🎯 <b>1. Оценка твоего профиля</b>\n"
        f"Твой текущий статус: <b>{stage}</b>. Выбранные направления (<b>{dirs_str}</b>) "
        "являются высоко востребованными на глобальном рынке труда.\n\n"
        f"🌍 <b>2. Рекомендуемые направления и регионы: {country}</b>\n"
        f"С учётом языка обучения (<b>{lang}</b>) и бюджета (<b>{budget}</b>), "
        "наиболее перспективными являются государственные вузы с грантовой поддержкой.\n\n"
        "🏛 <b>3. Рекомендуемые университеты</b>\n"
        "• <b>Технические и исследовательские университеты:</b> обрати внимание на программы с преподаванием на английском/местном языке.\n"
        "• <b>Программы обмена и двойных дипломов:</b> отличный способ оптимизировать затраты.\n\n"
        "📋 <b>4. Экзамены и дедлайны</b>\n"
        "Начни подготовку языкового сертификата (IELTS/TOEFL или эквивалент) минимум за 6-9 месяцев до старта подачи документов.\n\n"
        "💡 <b>5. Следующие шаги</b>\n"
        "1. Составь шорт-лист из 4-5 конкретных программ.\n"
        "2. Уточни требования к среднему баллу (GPA).\n"
        "3. Напиши черновик мотивационного письма."
    )
