# src/run_bot.py
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from src.app.config import BOT_TOKEN
from src.app.bot_handlers import register_handlers
from src.app.scheduler import init_scheduler, schedule_daily_import
from src.app.db import get_db_session
from src.app.models import Schedule

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

    # Рекомендуемые команды (опционально) — добавляем команды для управления расписанием
    try:
        await bot.set_my_commands([
            BotCommand(command="start", description="Старт / помощь"),
            BotCommand(command="link", description="Привязать аккаунт: /link <код>"),
            BotCommand(command="myprofile", description="Показать профиль"),
            BotCommand(command="users", description="Список пользователей (админ)"),
            BotCommand(command="generate_code", description="Сгенерировать код для пользователя (админ)"),
            BotCommand(command="export_codes", description="Экспорт кодов (админ)"),
            BotCommand(command="run_import_now", description="Запустить импорт операций (админ)"),
            BotCommand(command="schedule_get", description="Показать расписания (админ)"),
            BotCommand(command="schedule_set", description="Установить расписание: /schedule_set <name> <HH:MM UTC> (админ)"),
            BotCommand(command="schedule_remove", description="Удалить расписание: /schedule_remove <name> (админ)")
        ])
    except Exception as e:
        logger.warning("Не удалось установить команды бота: %s", e)

    # Инициализируем планировщик (APScheduler) и загружаем расписания из БД
    try:
        init_scheduler()
        # Загружаем включённые расписания из БД и регистрируем задачи в планировщике
        with get_db_session() as db:
            for s in db.query(Schedule).filter_by(enabled=True).all():
                # cron_hour и cron_minute хранятся в UTC
                schedule_daily_import(s.name, s.cron_hour, s.cron_minute)
                logger.info("Loaded schedule %s -> %02d:%02d UTC", s.name, s.cron_hour, s.cron_minute)
    except Exception as e:
        logger.exception("Ошибка при инициализации планировщика или загрузке расписаний: %s", e)

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
