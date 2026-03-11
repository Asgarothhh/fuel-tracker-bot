# src/run_bot.py
import asyncio
from aiogram import Bot, Dispatcher
from app.config import BOT_TOKEN
from app.bot_handlers import register_handlers

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Регистрируем обработчики
    register_handlers(dp)

    try:
        print("Starting polling...")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
