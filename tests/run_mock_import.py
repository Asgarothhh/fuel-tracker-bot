import asyncio
import random
from datetime import datetime
from aiogram import Bot
from src.app.config import BOT_TOKEN
from unittest.mock import patch
from src.app.jobs import run_import_job
from tests.mock_generator import create_random_test_entities


async def start_test(my_tg_id: int):
    bot = Bot(token=BOT_TOKEN)
    # 1. Генерируем случайные данные в БД
    card_num, plate = create_random_test_entities(my_tg_id)

    # 2. Формируем "ответ" от API Белоруснефти
    mock_api_data = [{
        "doc_number": f"MOCK-{random.randint(1000, 9999)}",
        "date_time": datetime.now(),
        "card_number": card_num,
        "car_num": plate,
        "driver_name": "Иванов Иван Иванович",
        "raw": {
            "productName": random.choice(["АИ-95", "ДТ"]),
            "productQuantity": round(random.uniform(20.0, 55.0), 2),
            "azsNumber": "77",
            "docNumber": f"MOCK-{random.randint(1000, 9999)}"
        }
    }]

    # 3. Подменяем функции импорта
    with patch("src.app.jobs.fetch_operational_raw") as mocked_fetch, \
            patch("src.app.jobs.parse_operations") as mocked_parse:
        mocked_fetch.return_value = {"status": "success"}
        mocked_parse.return_value = mock_api_data

        print(f"🚀 Запуск мок-импорта для чека {mock_api_data[0]['doc_number']}...")

        # Запускаем твой штатный джоб
        await run_import_job(bot=bot, schedule_name="manual_test")

        print("🏁 Тест завершен. Проверь сообщения в Telegram!")

    await bot.session.close()
    print("🏁 Тест завершен.")


if __name__ == "__main__":
    # Укажи здесь свой настоящий Telegram ID
    YOUR_ID = 834598783
    asyncio.run(start_test(YOUR_ID))