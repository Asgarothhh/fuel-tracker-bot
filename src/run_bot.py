# src/run_bot.py
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from src.app.config import BOT_TOKEN
from src.app.bot_handlers import register_handlers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Регистрируем обработчики из модуля
    register_handlers(dp)

    # Рекомендуемые команды (опционально)
    try:
        await bot.set_my_commands([
            BotCommand(command="start", description="Старт / помощь"),
            BotCommand(command="link", description="Привязать аккаунт: /link <код>"),
            BotCommand(command="myprofile", description="Показать профиль"),
            BotCommand(command="users", description="Список пользователей (админ)"),
            BotCommand(command="generate_code", description="Сгенерировать код для пользователя (админ)"),
            BotCommand(command="export_codes", description="Экспорт кодов (админ)"),
            BotCommand(command="run_import_now", description="Запустить импорт операций (админ)")
        ])
    except Exception as e:
        logger.warning("Не удалось установить команды бота: %s", e)

    try:
        logger.info("Starting polling...")
        await dp.start_polling(bot)
    finally:
        # корректно закрываем сессию бота
        await bot.session.close()
        logger.info("Bot stopped, session closed.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown requested, exiting...")
