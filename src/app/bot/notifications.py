import logging
from aiogram import Bot
from src.app.bot.keyboards import get_fuel_card_confirm_kb
from src.app.db import get_db_session
from src.app.models import FuelOperation

logger = logging.getLogger(__name__)


async def send_operation_to_user(bot: Bot, telegram_id: int, operation_id: int):
    """
    Отправляет уведомление пользователю о новой заправке по карте (ТЗ 9.5).
    """
    try:
        with get_db_session() as db:
            op = db.query(FuelOperation).get(operation_id)
            if not op:
                return

            text = (
                f"⛽ **Новая операция по карте!**\n\n"
                f"📅 Дата: {op.date_time.strftime('%d.%m.%Y %H:%M')}\n"
                f"💳 Карта: `{op.doc_number}`\n"  
                f"🚗 Авто (API): {op.car_from_api or 'Не указано'}\n\n"
                "Это ваша заправка? Подтвердите для формирования путевого листа."
            )

            await bot.send_message(
                telegram_id,
                text,
                reply_markup=get_fuel_card_confirm_kb(op.id),
                parse_mode="Markdown"
            )
            logger.info(f"Уведомление по операции {operation_id} отправлено пользователю {telegram_id}")

    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления пользователю {telegram_id}: {e}")