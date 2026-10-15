"""
Главный модуль запуска Telegram-бота UniversityChooseBot.
Точка входа приложения.
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from handlers import router


# Настройка кодировки вывода для консоли Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Загрузка переменных окружения из файла .env
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("UniversityChooseBot")


async def main() -> None:
    bot_token = os.getenv("BOT_TOKEN")

    if not bot_token or bot_token.strip() == "your_telegram_bot_token_here":
        logger.error(
            "\n" + "=" * 60 + "\n"
            "ОШИБКА КОНФИГУРАЦИИ:\n"
            "Переменная окружения BOT_TOKEN не задана или содержит шаблонный токен.\n\n"
            "Инструкция по настройке:\n"
            "1. Создайте файл .env на основе .env.example:\n"
            "   Copy-Item .env.example .env\n"
            "2. Откройте файл .env и укажите ваш токен от @BotFather:\n"
            "   BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz\n"
            "3. Повторно запустите бота командой:\n"
            "   python bot.py\n"
            + "=" * 60
        )
        sys.exit(1)

    proxy_url = os.getenv("PROXY_URL")
    session = None
    if proxy_url and proxy_url.strip():
        from aiogram.client.session.aiohttp import AiohttpSession
        logger.info(f"Используется прокси-сервер: {proxy_url.strip()}")
        session = AiohttpSession(proxy=proxy_url.strip())

    # Инициализация бота с парсингом HTML по умолчанию
    bot = Bot(
        token=bot_token.strip(),
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Инициализация диспетчера с хранилищем состояний в памяти
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Подключение роутера с обработчиками
    dp.include_router(router)

    try:
        # Удаляем вебхук и сбрасываем накопившиеся апдейты
        await bot.delete_webhook(drop_pending_updates=True)
        bot_info = await bot.get_me()
        logger.info(f"Бот успешно запущен: @{bot_info.username} ({bot_info.first_name})")
        logger.info("Ожидание сообщений пользователей... Для остановки нажмите Ctrl+C.")

        # Запуск поллинга
        await dp.start_polling(bot)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Получен сигнал завершения работы.")
    except Exception as e:
        logger.exception(f"Критическая ошибка при работе бота: {e}")
    finally:
        logger.info("Закрытие сессии бота...")
        await bot.session.close()
        logger.info("Бот успешно остановлен.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
