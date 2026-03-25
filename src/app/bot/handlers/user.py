from aiogram import types
from aiogram.filters import Command
from aiogram import Bot
from src.app.db import get_db_session
from src.app.models import User
from src.app.permissions import user_has_permission, require_permission
from src.app.tokens import verify_and_consume_code
from src.app.bot.keyboards import (
    reply_keyboard_user,
    reply_keyboard_admin,
    BTN_USER_PROFILE,
    BTN_USER_LINK_HELP,
    BTN_USER_HELP,
    BTN_USER_HOME,
    BTN_ADMIN_HOME,
)
from aiogram import Bot, F, types
from src.app.models import FuelOperation
from src.app.bot.utils import extract_args
from src.app.bot.keyboards import get_operation_confirm_keyboard # Ваша функция инлайн-кнопок
import logging

logger = logging.getLogger(__name__)

USER_HELP_TEXT = (
    "ℹ️ Что умеет бот\n\n"
    "• Заправки по карте — вам придёт запрос на подтверждение.\n"
    "• Привязка аккаунта — код от администратора.\n\n"
    "Команды:\n"
    "/start — меню\n"
    "/link и код — привязать Telegram\n"
    "/myprofile — карты и авто в профиле"
)


async def cmd_start(message: types.Message):
    with get_db_session() as db:
        is_admin = user_has_permission(db, message.from_user.id, "admin:manage")

    if is_admin:
        await message.reply(
            "Панель администратора. Кнопки ниже или команды в меню бота.",
            reply_markup=reply_keyboard_admin(),
            parse_mode="Markdown",
        )
    else:
        await message.reply(
            "Добро пожаловать. Привяжите аккаунт кодом от администратора или откройте подсказку кнопкой ниже.",
            reply_markup=reply_keyboard_user(),
            parse_mode="Markdown",
        )


async def cmd_myprofile(message: types.Message):
    tg = message.from_user.id
    with get_db_session() as db:
        row = db.query(User.id, User.full_name, User.cards, User.cars).filter(User.telegram_id == tg).first()
    if not row:
        await message.reply("Профиль не найден. Получите код у администратора и выполните /link <код>.")
        return
    _, full_name, cards, cars = row
    cards_s = ", ".join(cards or []) or "—"
    cars_s = ", ".join(cars or []) or "—"
    await message.reply(f"ФИО: {full_name}\nКарты: {cards_s}\nАвто: {cars_s}")


async def cmd_link(message: types.Message):
    args = extract_args(message)
    if not args:
        await message.reply("Введите: /link <код> (код выдаёт администратор).")
        return

    code = args.split()[0]
    with get_db_session() as db:
        ok, result = verify_and_consume_code(db, code, message.from_user.id)
        if not ok:
            reason = result
            user_row = None
        else:
            user_id = None
            if isinstance(result, dict) and "user_id" in result:
                user_id = result["user_id"]
            elif hasattr(result, "user_id"):
                user_id = result.user_id
            user_row = None
            if user_id:
                user_row = db.query(User.id, User.full_name, User.cards, User.cars).filter(User.id == user_id).first()

    if not ok:
        if reason == "invalid_or_used":
            await message.reply("Код неверен или уже использован.")
        elif reason == "expired":
            await message.reply("Код просрочен. Запросите новый у администратора.")
        elif reason == "already_linked_to_other":
            await message.reply("Эта запись уже привязана к другому Telegram.")
        else:
            await message.reply("Ошибка привязки. Обратитесь к администратору.")
        return

    if not user_row:
        await message.reply("Привязка выполнена, но не удалось загрузить профиль.")
        return

    _, full_name, cards, cars = user_row
    cards_s = ", ".join(cards or []) or "—"
    cars_s = ", ".join(cars or []) or "—"
    await message.reply(f"Готово.\nФИО: {full_name}\nКарты: {cards_s}\nАвто: {cars_s}")


async def cmd_user_help(message: types.Message):
    await message.reply(USER_HELP_TEXT, parse_mode="Markdown")


async def cmd_link_help(message: types.Message):
    await message.reply(
        "Чтобы привязать этот Telegram к вашей учётной записи:\n"
        "1) Получите одноразовый код у администратора.\n"
        "2) Отправьте боту сообщение в формате:\n"
        "   /link ВАШ_КОД\n\n"
        "Или нажмите /start и используйте подсказки в меню."
    )


async def btn_user_profile(message: types.Message):
    await cmd_myprofile(message)


async def btn_user_home(message: types.Message):
    await cmd_start(message)


@require_permission("admin:manage")
async def btn_admin_home(message: types.Message):
    await message.reply("Админ-панель:", reply_markup=reply_keyboard_admin())

async def send_operation_to_user(bot: Bot, telegram_id: int, operation_id: int):
    """Теперь функция принимает 'bot' как аргумент"""
    try:
        text = (
            f"⛽ *Новая операция по карте*\n\n"
            f"Обнаружена заправка #{operation_id}.\n"
            f"Пожалуйста, подтвердите данные."
        )
        await bot.send_message(
            chat_id=telegram_id,
            text=text,
            reply_markup=get_operation_confirm_keyboard(operation_id),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка отправки: {e}")


async def callback_op_confirm(call: types.CallbackQuery):
    """Водитель подтвердил заправку"""
    operation_id = int(call.data.split(":")[1])

    with get_db_session() as db:
        op = db.query(FuelOperation).filter_by(id=operation_id).first()
        if op:
            op.status = "confirmed"
            db.commit()
            # Здесь можно вызвать автоматический экспорт в Excel, если нужно по ТЗ
            await call.message.edit_text(f"✅ Операция #{operation_id} подтверждена.")
        else:
            await call.answer("Операция не найдена", show_alert=True)
    await call.answer()


async def callback_op_reject(call: types.CallbackQuery):
    """Водитель отклонил заправку (спорная ситуация)埋"""
    operation_id = int(call.data.split(":")[1])

    with get_db_session() as db:
        op = db.query(FuelOperation).filter_by(id=operation_id).first()
        if op:
            op.status = "disputed"  # или "requires_manual"
            db.commit()
            await call.message.edit_text(f"❌ Операция #{operation_id} помечена как спорная. Админ разберется.")
    await call.answer()


def register_user_handlers(dp):
    dp.message.register(cmd_start, Command(commands=["start"]))
    dp.message.register(cmd_link, Command(commands=["link"]))
    dp.message.register(cmd_myprofile, Command(commands=["myprofile"]))
    dp.message.register(cmd_user_help, Command(commands=["help"]))
    dp.message.register(btn_user_profile, lambda m: m.text == BTN_USER_PROFILE)
    dp.message.register(cmd_link_help, lambda m: m.text == BTN_USER_LINK_HELP)
    dp.message.register(cmd_user_help, lambda m: m.text == BTN_USER_HELP)
    dp.message.register(btn_user_home, lambda m: m.text == BTN_USER_HOME)
    dp.message.register(btn_admin_home, lambda m: m.text == BTN_ADMIN_HOME)
    dp.callback_query.register(callback_op_confirm, F.data.startswith("op_confirm:"))
    dp.callback_query.register(callback_op_reject, F.data.startswith("op_reject:"))

