from aiogram import types
from aiogram.filters import Command
from aiogram import Bot
from src.app.db import get_db_session
from src.app.models import User, FuelOperation, Car, ConfirmationHistory
from src.app.permissions import user_has_permission, require_permission
from src.app.tokens import verify_and_consume_code
from src.ocr.engine import SmartFuelOCR
from src.app.bot.keyboards import (
    reply_keyboard_user,
    reply_keyboard_admin,
    get_ocr_confirm_kb,
    get_car_selection_kb,
    BTN_USER_PROFILE,
    BTN_USER_LINK_HELP,
    BTN_USER_HELP,
    BTN_USER_HOME,
    BTN_ADMIN_HOME,
    BTN_USER_SEND_CHECK,
)
from aiogram import Bot, F, types
from src.app.models import FuelOperation
from src.app.bot.utils import extract_args
from src.app.bot.keyboards import get_operation_confirm_keyboard # Ваша функция инлайн-кнопок
import logging

logger = logging.getLogger(__name__)

class ReceiptStates(StatesGroup):
    waiting_for_photo = State()
    waiting_for_confirmation = State()
    waiting_for_car = State()


logger = logging.getLogger("bot.user")

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


async def btn_send_receipt_start(message: types.Message, state: FSMContext):
    """Начало сценария: запрос фото чека (ТЗ 8.2)"""
    # Проверка, привязан ли пользователь
    with get_db_session() as db:
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        if not user:
            await message.reply("Сначала привяжите аккаунт через /link <код>.")
            return

    await state.set_state(ReceiptStates.waiting_for_photo)
    await message.answer("📸 Пожалуйста, отправьте фотографию чека АЗС.")


async def handle_receipt_photo(message: types.Message, state: FSMContext):
    """Прием фото и запуск OCR пайплайна"""
    if not message.photo:
        await message.answer("Пожалуйста, отправьте изображение (фото).")
        return

    photo = message.photo[-1]
    file_info = await message.bot.get_file(photo.file_id)

    # Создаем временную директорию
    os.makedirs("temp_ocr", exist_ok=True)
    file_path = f"temp_ocr/{photo.file_id}.jpg"
    await message.bot.download_file(file_info.file_path, file_path)

    msg_wait = await message.answer("⏳ Распознаю данные чека (это может занять до 10 сек)...")

    try:
        with get_db_session() as db:
            processor = SmartFuelOCR(db)
            ocr_result = processor.run_pipeline(file_path, telegram_user_id=message.from_user.id)

        if not ocr_result:
            await message.answer("❌ Не удалось распознать чек. Попробуйте сделать фото четче.")
            await state.clear()
            return

        if isinstance(ocr_result, dict) and ocr_result.get("status") == "duplicate":
            await message.answer(f"⚠️ {ocr_result.get('message')}")
            await state.clear()
            return

        # Успех: сохраняем ID операции в FSM
        op_id = ocr_result.get('id')
        await state.update_data(op_id=op_id)

        text = (
            f"📋 *Данные чека распознаны:*\n\n"
            f"⛽ Топливо: {ocr_result.get('fuel_type', '—')}\n"
            f"💧 Кол-во: {ocr_result.get('quantity', '0')} л.\n"
            f"💰 Сумма: {ocr_result.get('total_sum', '0')} руб.\n"
            f"📅 Дата: {ocr_result.get('date')} {ocr_result.get('time')}\n\n"
            f"Все верно?"
        )

        await state.set_state(ReceiptStates.waiting_for_confirmation)
        await message.answer(text, reply_markup=get_ocr_confirm_kb(op_id), parse_mode="Markdown")

    except Exception as e:
        logger.error(f"OCR Error: {e}")
        await message.answer("❌ Произошла ошибка при обработке чека.")
        await state.clear()
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        await msg_wait.delete()


async def callback_ocr_confirm(call: types.CallbackQuery, state: FSMContext):
    """Данные верны -> Переход к выбору авто (ТЗ 9.6)"""
    data = await state.get_data()
    op_id = data.get("op_id")

    with get_db_session() as db:
        user = db.query(User).filter(User.telegram_id == call.from_user.id).first()
        if not user or not user.cars:
            await call.message.answer("У вас в профиле нет привязанных авто. Обратитесь к админу.")
            await state.clear()
            return

        cars_list = db.query(Car).filter(Car.plate.in_(user.cars)).all()

    await state.set_state(ReceiptStates.waiting_for_car)
    await call.message.edit_text("🚗 Выберите автомобиль:", reply_markup=get_car_selection_kb(cars_list))
    await call.answer()


async def callback_select_car(call: types.CallbackQuery, state: FSMContext):
    """Финальный этап: сохранение авто и закрытие операции"""
    car_id = int(call.data.split("_")[-1])
    data = await state.get_data()
    op_id = data.get("op_id")

    with get_db_session() as db:
        op = db.query(FuelOperation).get(op_id)
        car = db.query(Car).get(car_id)
        user = db.query(User).filter(User.telegram_id == call.from_user.id).first()

        if op and car:
            op.actual_car = car.plate
            op.confirmed_user_id = user.id
            op.status = "confirmed"
            op.confirmed_at = datetime.now(timezone.utc)

            # Запись в историю для аудита
            history = ConfirmationHistory(
                operation_id=op.id,
                from_user_id=user.id,
                to_user_id=user.id,
                answer="confirmed",
                stage_result=f"Подтверждено пользователем для авто {car.plate}"
            )
            db.add(history)
            db.commit()
            await call.message.edit_text(f"✅ Заправка авто {car.plate} успешно зарегистрирована!")
        else:
            await call.message.edit_text("❌ Ошибка: операция не найдена.")

    await state.clear()
    await call.answer()


async def callback_ocr_cancel(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text("❌ Регистрация чека отменена.")
    await state.clear()
    await call.answer()


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
    dp.message.register(btn_user_profile, F.text == BTN_USER_PROFILE)
    dp.message.register(cmd_link_help, F.text == BTN_USER_LINK_HELP)
    dp.message.register(cmd_user_help, F.text == BTN_USER_HELP)
    dp.message.register(btn_user_home, F.text == BTN_USER_HOME)
    dp.message.register(btn_admin_home, F.text == BTN_ADMIN_HOME)
    dp.message.register(btn_send_receipt_start, F.text == BTN_USER_SEND_CHECK)
    dp.message.register(handle_receipt_photo, ReceiptStates.waiting_for_photo, F.photo)
    dp.callback_query.register(callback_ocr_confirm, F.data.startswith("ocr_confirm_"))
    dp.callback_query.register(callback_ocr_cancel, F.data.startswith("ocr_cancel_"))
    dp.callback_query.register(callback_select_car, F.data.startswith("select_car_"))
    dp.message.register(btn_user_profile, lambda m: m.text == BTN_USER_PROFILE)
    dp.message.register(cmd_link_help, lambda m: m.text == BTN_USER_LINK_HELP)
    dp.message.register(cmd_user_help, lambda m: m.text == BTN_USER_HELP)
    dp.message.register(btn_user_home, lambda m: m.text == BTN_USER_HOME)
    dp.message.register(btn_admin_home, lambda m: m.text == BTN_ADMIN_HOME)
    dp.callback_query.register(callback_op_confirm, F.data.startswith("op_confirm:"))
    dp.callback_query.register(callback_op_reject, F.data.startswith("op_reject:"))

