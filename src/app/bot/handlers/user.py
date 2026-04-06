import datetime
import os
from time import timezone
from aiogram.types import FSInputFile
from aiogram import types
from aiogram.filters import Command
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from src.app.bot.notifications import send_operation_to_user
from aiogram.filters import CommandStart
from sqlalchemy import cast, String
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
    BTN_USER_SEND_CHECK, BTN_USER_PENDING, BTN_USER_CARS, BTN_USER_LINK_ACCOUNT, BTN_USER_CHANGE_CARD
)
from aiogram import Bot, F, types
from src.app.models import FuelOperation
from src.app.bot.utils import extract_args
from src.app.bot.keyboards import get_fuel_card_confirm_kb
import logging

logger = logging.getLogger(__name__)


class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_card = State()


class CardUpdateStates(StatesGroup):
    waiting_for_new_card = State()


class ReceiptStates(StatesGroup):
    waiting_for_photo = State()
    waiting_for_confirmation = State()
    waiting_for_car = State()
    waiting_for_real_fueler = State()  # Кто заправлялся (ФИО)
    waiting_for_disputed_car = State()  # Какое авто (при споре)
    waiting_for_confirmed_car = State()  # Какое авто (при подтверждении)
    waiting_for_new_car_add = State()

class LinkStates(StatesGroup):
    waiting_for_code = State()


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


async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()

    # Путь к баннеру
    banner_path = os.path.join("E:/PythonProjects/fuel-tracker-bot/src/app/bot/assets/Frame 1 (2).png")

    if os.path.exists(banner_path):
        try:
            # Используем answer_photo один раз, чтобы поприветствовать
            await message.answer_photo(
                photo=FSInputFile(banner_path),
                caption="⛽️ **Система учета топлива Fuel Tracker**",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке баннера: {e}")

    with get_db_session() as db:
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()

        if user:
            if user.active:
                is_admin = user_has_permission(db, message.from_user.id, "admin:manage")
                if is_admin:
                    await message.answer(
                        "👑 **Панель администратора**",
                        reply_markup=reply_keyboard_admin(),
                        parse_mode="Markdown",
                    )
                else:
                    await message.answer(
                        f"✅ С возвращением, {user.full_name}!",
                        reply_markup=reply_keyboard_user(), # Сюда добавили скобки
                        parse_mode="Markdown",
                    )
            else:
                # ИСПРАВЛЕНИЕ: Добавляем кнопку привязки для неактивных
                from src.app.bot.keyboards import reply_keyboard_unauthorized
                await message.answer(
                    "⏳ Ваш аккаунт ожидает активации.\n\n"
                    "Если у вас есть код, нажмите кнопку ниже или введите его: `/link код`",
                    reply_markup=reply_keyboard_unauthorized(), # <--- ЭТО ВАЖНО
                    parse_mode="Markdown"
                )
            return

    # Логика для новых пользователей (совсем нет в базе)
    await message.answer(
        "👋 **Добро пожаловать!**\n\nДля начала работы необходимо зарегистрироваться.\n"
        "Введите ваше **ФИО** (полностью):",
        reply_markup=types.ReplyKeyboardRemove(), # Убираем старые кнопки, если были
        parse_mode="Markdown"
    )
    await state.set_state(RegistrationStates.waiting_for_name)

async def process_reg_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text.strip())
    await message.reply("Теперь введите номер вашей топливной карты (только цифры):")
    await state.set_state(RegistrationStates.waiting_for_card)


# 2. Хендлер нажатия на кнопку
async def btn_change_card(message: types.Message, state: FSMContext):
    await message.answer(
        "💳 **Введите новый номер вашей топливной карты:**\n\n"
        "*(Если у вас несколько карт, введите их через запятую)*",
        parse_mode="Markdown",
        reply_markup=types.ReplyKeyboardRemove()  # Временно прячем меню
    )
    await state.set_state(CardUpdateStates.waiting_for_new_card)


# 3. Хендлер получения самого номера карты
async def process_new_card(message: types.Message, state: FSMContext):
    new_cards_raw = message.text.strip()
    # Разбиваем по запятой и удаляем лишние пробелы, если ввели несколько
    cards_list = [c.strip() for c in new_cards_raw.split(",") if c.strip()]

    with get_db_session() as db:
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        if user:
            user.cards = cards_list  # Сохраняем массив карт (JSON/Array)
            db.commit()
            await message.answer(
                f"✅ **Карта успешно обновлена!**\nТекущие карты: {', '.join(cards_list)}",
                parse_mode="Markdown",
                reply_markup=reply_keyboard_user()  # Возвращаем меню
            )
        else:
            await message.answer("❌ Ошибка: Профиль не найден.", reply_markup=reply_keyboard_user())

    await state.clear()


async def process_reg_card(message: types.Message, state: FSMContext):
    card_num = message.text.strip()
    if not card_num.isdigit():
        await message.reply("Номер карты должен состоять только из цифр. Попробуйте снова:")
        return

    data = await state.get_data()
    full_name = data['full_name']

    with get_db_session() as db:
        # Ищем, нет ли уже такого пользователя (созданного через API импорт)
        existing_user = db.query(User).filter(
            (User.full_name.ilike(full_name)) |
            (cast(User.cards, String).like(f"%{card_num}%"))
        ).first()

        if existing_user and not existing_user.telegram_id:
            existing_user.telegram_id = message.from_user.id
            cards = list(existing_user.cards or [])
            if card_num not in cards: cards.append(card_num)
            existing_user.cards = cards
        elif not existing_user:
            new_user = User(
                full_name=full_name,
                telegram_id=message.from_user.id,
                cards=[card_num],
                role_id=2,
                active=False
            )
            db.add(new_user)
        else:
            await message.reply("Пользователь с такими данными уже зарегистрирован.")
            await state.clear()
            return

        db.commit()
        await message.reply("Регистрация завершена! Ожидайте активации администратором.")
    await state.clear()


async def callback_fuel_card_reject(call: types.CallbackQuery, state: FSMContext):
    operation_id = int(call.data.split("_")[-1])

    # Сохраняем ID операции в контекст, чтобы знать, к чему привязать ФИО
    await state.update_data(disputed_op_id=operation_id)
    await state.set_state(ReceiptStates.waiting_for_real_fueler)

    await call.message.answer("Понял. Напишите, пожалуйста, ФИО сотрудника, который заправлялся по этой карте?")
    await call.answer()


async def old_cmd_start(message: types.Message):
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


async def cmd_pending(message: types.Message):
    """Показывает все операции, которые ожидают подтверждения от этого пользователя"""
    with get_db_session() as db:
        user = db.query(User).filter_by(telegram_id=message.from_user.id).first()
        if not user:
            await message.answer("Ваш профиль не найден.")
            return

        # Ищем неподтвержденные операции
        # (Зависит от того, как в вашей модели называется поле связи.
        # Предполагаем наличие поля assumed_user_id или поиск по истории)

        # Простой вариант: берем все операции со статусом "new" или "disputed",
        # где пользователь фигурирует последним в ConfirmationHistory как получатель (to_user_id)
        # Либо, если у вас в FuelOperation есть поле вроде assumed_user_id:

        pending_ops = db.query(FuelOperation).filter(
            FuelOperation.status.in_(["new", "loaded", "pending"]),
            # Замените assumed_user_id на ваше поле, если оно называется иначе (например, target_user_id)
            # В ТЗ указано "предполагаемый пользователь"
            FuelOperation.presumed_user_id == user.id
        ).all()

        if not pending_ops:
            await message.answer("🎉 У вас нет ожидающих подтверждения заправок.")
            return

        await message.answer(f"У вас {len(pending_ops)} ожидающих подтверждения операций. Высылаю карточки:")

        from src.app.bot.notifications import send_operation_to_user
        for op in pending_ops:
            await send_operation_to_user(message.bot, user.telegram_id, op.id)

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


async def cmd_link(message: types.Message, state: FSMContext):
    # 1. Проверяем, не является ли сообщение просто текстом кнопки
    if message.text == BTN_USER_LINK_ACCOUNT:
        await message.answer(
            "🔑 **Введите код привязки**\n\nОтправьте код администратора ответным сообщением.",
            parse_mode="Markdown",
            reply_markup=types.ReplyKeyboardRemove()
        )
        await state.set_state(LinkStates.waiting_for_code)
        return  # Важно выйти здесь!

    # 2. Если это команда /link [код]
    args = extract_args(message)
    if args:
        code = args.split()[0]
        # Если в коде случайно оказался текст кнопки (защита от дурака)
        if code == BTN_USER_LINK_ACCOUNT:
            await message.answer("Пожалуйста, введите сам цифровой/буквенный код.")
            return

        return await process_link_logic(message, code, state)

    # 3. Если просто /link без ничего
    await message.answer(
        "🔑 **Введите код привязки**\n\nОтправьте код администратора ответным сообщением.",
        parse_mode="Markdown",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(LinkStates.waiting_for_code)


async def process_link_message(message: types.Message, state: FSMContext):
    code = message.text.strip()
    await process_link_logic(message, code, state)


# 3. Общая логика обработки (твой исходный код с проверками)
async def process_link_logic(message: types.Message, code: str, state: FSMContext):
    await state.clear()  # Сбрасываем состояние сразу

    with get_db_session() as db:
        # 1. Проверяем код
        ok, result = verify_and_consume_code(db, code, message.from_user.id)

        if not ok:
            # Твоя логика ошибок
            error_msgs = {
                "invalid_or_used": "Код неверен или уже использован.",
                "expired": "Код просрочен.",
                "already_linked_to_other": "Эта запись уже привязана к другому Telegram."
            }
            await message.reply(error_msgs.get(result, "Ошибка привязки."))
            return

        # 2. Получаем ID пользователя
        user_id = result.get("user_id") if isinstance(result, dict) else getattr(result, "user_id", None)

        if not user_id:
            await message.reply("Ошибка: запись пользователя не найдена.")
            return

        # 3. Активация
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.active = True
            if not user.role_id:
                user.role_id = 2
            db.commit()

            cards_s = ", ".join(user.cards or []) or "—"
            cars_s = ", ".join(user.cars or []) or "—"

            await message.reply(
                f"✅ **Аккаунт успешно активирован!**\n\n"
                f"ФИО: {user.full_name}\n"
                f"Карты: {cards_s}\n"
                f"Авто: {cars_s}",
                reply_markup=reply_keyboard_user(),
                parse_mode="Markdown"
            )
        else:
            await message.reply("Привязка выполнена, но профиль не найден в базе.")


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
    try:
        with get_db_session() as db:
            op = db.query(FuelOperation).get(operation_id)
            if not op: return

            api = op.api_data if isinstance(op.api_data, dict) else {}
            row = api.get("row") if isinstance(api.get("row"), dict) else {}

            dt = op.date_time.strftime("%d.%m.%Y %H:%M") if op.date_time else "—"
            fuel = api.get("productName") or row.get("productName") or "—"
            qty = api.get("productQuantity") or row.get("productQuantity") or "—"
            azs = api.get("azsNumber") or row.get("azsNumber") or row.get("AzsCode") or "—"
            doc = op.doc_number or api.get("docNumber") or row.get("docNumber") or "—"

        text = (
            f"По вашей топливной карте обнаружена заправка за {dt}.\n"
            f"Топливо: {fuel}.\n"
            f"Количество: {qty} л.\n"
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


# --- ПУНКТ 8 ТЗ: ПОДТВЕРЖДЕНИЕ ---
async def callback_fuel_card_confirm(call: types.CallbackQuery, state: FSMContext):
    operation_id = int(call.data.split("_")[-1])

    with get_db_session() as db:
        user = db.query(User).filter_by(telegram_id=call.from_user.id).first()
        op = db.query(FuelOperation).get(operation_id)

        # Если у водителя еще нет привязанных машин
        if not user.cars:
            await state.update_data(conf_op_id=operation_id)
            await state.set_state(ReceiptStates.waiting_for_confirmed_car)
            await call.message.answer("Подтвердите госномер автомобиля (например, 1234 AB-7):")
        else:
            op.status = "confirmed"
            op.confirmed_at = datetime.datetime.now(datetime.timezone.utc)
            op.confirmed_user_id = user.id
            if not op.car_from_api:
                first_car = user.cars[0]
                # Проверка: если это объект Car — берем атрибут, если строка — берем саму строку
                op.car_from_api = getattr(first_car, 'gov_number', first_car)
            db.commit()
            await call.message.edit_text(f"✅ Операция подтверждена для {op.car_from_api}")
    await call.answer()


async def process_confirmed_car(message: types.Message, state: FSMContext):
    data = await state.get_data()
    op_id = data.get("conf_op_id")
    car_number = message.text.strip().upper()

    with get_db_session() as db:
        user = db.query(User).filter_by(telegram_id=message.from_user.id).first()
        op = db.query(FuelOperation).get(op_id)

        # Создаем или находим машину и привязываем к юзеру
        car = db.query(Car).filter_by(gov_number=car_number).first()
        if not car:
            car = Car(gov_number=car_number)
            db.add(car)
            db.flush()

        if car not in user.cars:
            user.cars.append(car)

        op.status = "confirmed"
        op.car_from_user = car_number
        db.commit()

    await message.answer(f"✅ Машина {car_number} привязана к профилю. Операция подтверждена!")
    await state.clear()


# --- ПУНКТ 9 ТЗ: ОТКЛОНЕНИЕ (ПИНГ-ПОНГ) ---
async def callback_fuel_card_reject(call: types.CallbackQuery, state: FSMContext):
    operation_id = int(call.data.split("_")[-1])

    with get_db_session() as db:
        current_user = db.query(User).filter_by(telegram_id=call.from_user.id).first()
        op = db.query(FuelOperation).get(operation_id)

        # 2. ИЩЕМ, КТО ПЕРЕНАПРАВИЛ НАМ ЭТУ ОПЕРАЦИЮ (ОБРАТНЫЙ ПИНГ-ПОНГ)
        last_redirect = db.query(ConfirmationHistory).filter(
            ConfirmationHistory.operation_id == operation_id,
            ConfirmationHistory.to_user_id == current_user.id,
            ConfirmationHistory.answer == "redirected"
        ).order_by(ConfirmationHistory.id.desc()).first()

        if last_redirect and last_redirect.from_user_id != current_user.id:
            # ТЗ п.8.1.12 Возвращаем первоначальному пользователю
            prev_user = db.query(User).get(last_redirect.from_user_id)

            history = ConfirmationHistory(
                operation_id=op.id,
                from_user_id=current_user.id,
                to_user_id=prev_user.id,
                answer="rejected_bounce",
                stage_result=f"Отклонено {current_user.full_name}, возврат к {prev_user.full_name}"
            )
            db.add(history)
            db.commit()

            await call.message.edit_text(
                f"❌ Вы отклонили операцию. Запрос возвращен сотруднику ({prev_user.full_name}), который вас указал.")

            # ТЗ п.9.8 Уведомляем предыдущего пользователя и запрашиваем заново
            if prev_user.telegram_id:
                await call.bot.send_message(
                    prev_user.telegram_id,
                    f"⚠️ Сотрудник **{current_user.full_name}** ответил, что НЕ заправлялся по операции #{operation_id}.\n"
                    f"Пожалуйста, проверьте данные и укажите корректного сотрудника.",
                    reply_markup=get_fuel_card_confirm_kb(operation_id),  # ✅ ИСПОЛЬЗУЕМ РАБОЧУЮ КЛАВИАТУРУ
                    parse_mode="Markdown"
                )
            return

    # Если редиректа не было (это самый первый получатель из API)
    await state.update_data(disputed_op_id=operation_id)
    await state.set_state(ReceiptStates.waiting_for_disputed_car)
    await call.message.edit_text("Оформляем отклонение. Подскажите, какой автомобиль был заправлен фактически?")
    await call.answer()


async def process_disputed_car(message: types.Message, state: FSMContext):
    await state.update_data(disputed_car=message.text.strip())
    await state.set_state(ReceiptStates.waiting_for_real_fueler)
    await message.answer("Кто фактически заправлялся? Введите ФИО сотрудника:")


async def process_real_fueler_name(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    op_id = data.get("disputed_op_id")
    car_plate_input = data.get("disputed_car")
    full_name_input = message.text.strip()

    with get_db_session() as db:
        op = db.query(FuelOperation).get(op_id)

        # Защита от бесконечного пинг-понга (> 3 перенаправлений)
        redirect_count = db.query(ConfirmationHistory).filter_by(operation_id=op_id, answer="redirected").count()
        if redirect_count >= 3:
            op.status = "requires_manual"
            db.commit()
            await message.answer(
                "⚠️ Операция перенаправлялась слишком много раз. Она помечена как спорная и передана администратору.")
            await state.clear()
            return

        potential_users = db.query(User).filter(User.full_name.ilike(f"%{full_name_input}%")).all()

        if not potential_users:
            await message.answer(f"❌ Сотрудник '{full_name_input}' не найден в базе. Попробуйте ввести иначе:")
            return

        if len(potential_users) > 1:
            names = "\n".join([f"- {u.full_name}" for u in potential_users])
            await message.answer(f"🧐 Найдено несколько похожих сотрудников. Уточните ФИО:\n{names}")
            return

        target_user = potential_users[0]

        if target_user.telegram_id == message.from_user.id:
            await message.answer(
                "❌ Вы не можете перенаправить операцию на самого себя. Введите ФИО другого сотрудника:")
            return

        if target_user and target_user.telegram_id:
            op.car_from_api = car_plate_input.upper() if car_plate_input else op.car_from_api
            history = ConfirmationHistory(
                operation_id=op.id,
                from_user_id=db.query(User).filter_by(telegram_id=message.from_user.id).first().id,
                to_user_id=target_user.id,
                answer="redirected",
                stage_result=f"Перенаправлено на {target_user.full_name}"
            )
            db.add(history)
            db.commit()

            from src.app.bot.notifications import send_operation_to_user
            await send_operation_to_user(bot, target_user.telegram_id, op_id)
            await message.answer(f"✅ Запрос перенаправлен сотруднику {target_user.full_name}.")
            await state.clear()
        else:
            op.status = "requires_manual"
            db.commit()
            await message.answer("⚠️ У найденного сотрудника не привязан Telegram. Данные переданы администратору.")
            await state.clear()


async def process_confirmed_car(message: types.Message, state: FSMContext):
    data = await state.get_data()
    op_id = data.get("conf_op_id")
    car_number = message.text.strip().upper()  # Приводим к верхнему регистру для порядка

    with get_db_session() as db:
        user = db.query(User).filter_by(telegram_id=message.from_user.id).first()
        op = db.query(FuelOperation).get(op_id)

        if user and op:
            # 1. Проверяем, есть ли уже такая машина в базе, или создаем новую
            car = db.query(Car).filter_by(gov_number=car_number).first()
            if not car:
                car = Car(gov_number=car_number)
                db.add(car)
                db.flush()  # Получаем ID машины

            # 2. Привязываем машину к пользователю, если еще не привязана
            if car not in user.cars:
                user.cars.append(car)

            # 3. Обновляем данные операции
            op.status = "confirmed"
            op.confirmed_at = datetime.datetime.now(datetime.timezone.utc)
            op.car_from_user = car_number

            db.commit()

            await message.answer(
                f"✅ Номер {car_number} сохранен в ваш профиль.\n"
                f"Операция подтверждена. Спасибо!"
            )
            await state.clear()
        else:
            await message.answer("Произошла ошибка: не удалось найти данные операции.")
            await state.clear()


async def btn_user_cars_menu(message: types.Message, state: FSMContext):
    """Показывает авто юзера и просит ввести новое для добавления."""
    with get_db_session() as db:
        user = db.query(User).filter_by(telegram_id=message.from_user.id).first()
        if not user: return
        cars_s = "\n".join([f"• {c}" for c in (user.cars or [])]) or "Нет привязанных авто."

    await message.answer(
        f"🚗 *Ваши автомобили:*\n{cars_s}\n\nЧтобы добавить новое авто, просто напишите его госномер (например, 1234 AB-7):",
        parse_mode="Markdown")
    await state.set_state(ReceiptStates.waiting_for_new_car_add)


async def process_add_new_car(message: types.Message, state: FSMContext):
    new_car = message.text.strip().upper()
    with get_db_session() as db:
        user = db.query(User).filter_by(telegram_id=message.from_user.id).first()
        if user:
            u_cars = list(user.cars or [])
            if new_car not in u_cars:
                u_cars.append(new_car)
                user.cars = u_cars
                db.commit()
                await message.answer(f"✅ Автомобиль {new_car} успешно добавлен в ваш профиль!")
            else:
                await message.answer("Этот автомобиль уже есть в вашем профиле.")
    await state.clear()


def register_user_handlers(dp):
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(process_reg_name, RegistrationStates.waiting_for_name)
    dp.message.register(process_reg_card, RegistrationStates.waiting_for_card)
    dp.message.register(cmd_start, Command(commands=["start"]))
    dp.message.register(cmd_link, Command(commands=["link"]))
    dp.message.register(cmd_link, F.text == BTN_USER_LINK_ACCOUNT)
    dp.message.register(process_link_message, LinkStates.waiting_for_code)
    dp.message.register(btn_change_card, F.text == BTN_USER_CHANGE_CARD)
    dp.message.register(process_new_card, CardUpdateStates.waiting_for_new_card)
    dp.message.register(cmd_myprofile, Command(commands=["myprofile"]))
    dp.message.register(cmd_user_help, Command(commands=["help"]))
    dp.message.register(btn_send_receipt_start, Command(commands=["check"]))
    dp.message.register(btn_user_profile, F.text == BTN_USER_PROFILE)
    dp.message.register(cmd_link_help, F.text == BTN_USER_LINK_HELP)
    dp.message.register(cmd_user_help, F.text == BTN_USER_HELP)
    dp.message.register(btn_user_home, F.text == BTN_USER_HOME)
    dp.message.register(btn_admin_home, F.text == BTN_ADMIN_HOME)
    dp.message.register(btn_send_receipt_start, F.text == BTN_USER_SEND_CHECK)
    dp.message.register(handle_receipt_photo, ReceiptStates.waiting_for_photo, F.photo)
    dp.message.register(process_confirmed_car, ReceiptStates.waiting_for_confirmed_car)
    dp.message.register(process_disputed_car, ReceiptStates.waiting_for_disputed_car)
    dp.message.register(process_real_fueler_name, ReceiptStates.waiting_for_real_fueler)
    dp.message.register(btn_user_cars_menu, F.text == BTN_USER_CARS)
    dp.message.register(process_add_new_car, ReceiptStates.waiting_for_new_car_add)
    dp.message.register(cmd_pending, Command(commands=["pending"]))
    dp.callback_query.register(callback_fuel_card_confirm, F.data.startswith("fuel_card_yes_"))
    dp.callback_query.register(callback_fuel_card_reject, F.data.startswith("fuel_card_no_"))
    dp.callback_query.register(callback_ocr_confirm, F.data.startswith("ocr_confirm_"))
    dp.callback_query.register(callback_ocr_cancel, F.data.startswith("ocr_cancel_"))
    dp.callback_query.register(callback_select_car, F.data.startswith("select_car_"))
    # dp.message.register(btn_user_profile, lambda m: m.text == BTN_USER_PROFILE)
    # dp.message.register(cmd_link_help, lambda m: m.text == BTN_USER_LINK_HELP)
    # dp.message.register(cmd_user_help, lambda m: m.text == BTN_USER_HELP)
    # dp.message.register(btn_user_home, lambda m: m.text == BTN_USER_HOME)
    # dp.message.register(btn_admin_home, lambda m: m.text == BTN_ADMIN_HOME)
    dp.callback_query.register(callback_op_confirm, F.data.startswith("op_confirm:"))
    dp.callback_query.register(callback_op_reject, F.data.startswith("op_reject:"))
    dp.message.register(cmd_pending, F.text == BTN_USER_PENDING)


