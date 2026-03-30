import logging
from aiogram import Bot
from src.app.bot.keyboards import get_fuel_card_confirm_kb
from src.app.db import get_db_session
from src.app.models import FuelOperation

logger = logging.getLogger(__name__)


async def send_operation_to_user(bot: Bot, telegram_id: int, operation_id: int):
    """
    Отправляет уведомление пользователю о новой заправке по карте согласно ТЗ.
    """
    try:
        with get_db_session() as db:
            op = db.query(FuelOperation).get(operation_id)
            if not op:
                logger.error(f"❌ Операция {operation_id} не найдена!")
                return

            # Безопасное извлечение данных из JSON (api_data)
            api = op.api_data if isinstance(op.api_data, dict) else {}
            # Иногда данные лежат во вложенном ключе 'row'
            row = api.get("row") if isinstance(api.get("row"), dict) else {}

            # Собираем переменные для текста (берем либо из корня api, либо из row, либо из полей модели)
            dt = op.date_time.strftime("%d.%m.%Y %H:%M") if op.date_time else "—"
            fuel = api.get("productName") or row.get("productName") or "—"
            qty = api.get("productQuantity") or row.get("productQuantity") or "—"
            azs = api.get("azsNumber") or row.get("azsNumber") or row.get("AzsCode") or "—"
            # Чек — это doc_number в модели или в API
            doc = op.doc_number or api.get("docNumber") or row.get("docNumber") or "—"

        # Строго по ТЗ
        text = (
            f"По вашей топливной карте обнаружена заправка за {dt}.\n"
            f"Топливо: {fuel}.\n"
            f"Количество: {qty}.\n"
            f"АЗС: {azs}.\n"
            f"Чек: {doc}.\n\n"
            f"Это действительно была ваша заправка?"
        )

        await bot.send_message(
            chat_id=telegram_id,
            text=text,
            reply_markup=get_fuel_card_confirm_kb(operation_id)
        )
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления: {e}")