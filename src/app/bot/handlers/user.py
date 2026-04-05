import datetime
import logging
import os
from pathlib import Path

from aiogram import F, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile
from sqlalchemy import String, cast

from src.app.bot.keyboards import (
    BTN_ADMIN_HOME,
    BTN_USER_CARS,
    BTN_USER_HELP,
    BTN_USER_HOME,
    BTN_USER_LINK_HELP,
    BTN_USER_PENDING,
    BTN_USER_PROFILE,
    BTN_USER_SEND_CHECK,
    get_fuel_card_confirm_kb,
    get_ocr_confirm_kb,
    get_personal_car_pick_kb,
    reply_keyboard_admin,
    reply_keyboard_user,
)
from src.app.bot.notifications import send_operation_to_user
from src.app.bot.utils import extract_args
from src.app.config import WELCOME_BANNER_PATH
from src.app.db import get_db_session
from src.app.excel_export import export_to_excel_final
from src.app.models import Car, ConfirmationHistory, FuelOperation, User
from src.app.permissions import require_permission, user_has_permission
from src.app.plate_util import find_cars_by_normalized_plate, normalize_plate
from src.app.tokens import verify_and_consume_code
from src.app.welcome_store import mark_welcome_shown, was_welcome_shown
from src.ocr.engine import SmartFuelOCR

logger = logging.getLogger("bot.user")


class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_card = State()


class ReceiptStates(StatesGroup):
    waiting_for_photo = State()
    waiting_for_confirmation = State()
    waiting_for_personal_car_plate = State()
    waiting_for_personal_fueler = State()
    waiting_for_real_fueler = State()  # Кто заправлялся (ФИО) — спор по карте
    waiting_for_disputed_car = State()
    waiting_for_confirmed_car = State()
    waiting_for_new_car_add = State()


USER_HELP_TEXT = (
    "ℹ️ Что умеет бот\n\n"
    "• **Заправки по топливной карте** — бот пришлёт запрос на подтверждение операции из учётной системы.\n"
    "• **Заправки за личные средства** — отправьте фото чека АЗС; после проверки данные попадут в общий Excel.\n"
    "• **Привязка аккаунта** — одноразовый код от администратора.\n\n"
    "Команды:\n"
    "/start — меню\n"
    "/check или кнопка «Отправить чек» — чек за личные средства\n"
    "/link и код — привязать Telegram\n"
    "/myprofile — карты и авто в профиле"
)

WELCOME_CAPTION = (
    "⛽ **Учёт заправок**\n\n"
    "Этот бот помогает фиксировать заправки **по топливной карте** (подтверждение операций из отчётов) "
    "и **за личные средства** (фото чека → распознавание → проверка авто и заправившегося по справочнику → запись в Excel). "
    "Данные сводятся в одном файле для дальнейшего использования, в том числе в путевых листах.\n\n"
    "Нажмите кнопки меню ниже или выполните /start после привязки аккаунта."
)


def _resolve_welcome_banner_path() -> str:
    if WELCOME_BANNER_PATH and os.path.isfile(WELCOME_BANNER_PATH):
        return WELCOME_BANNER_PATH
    default = Path(__file__).resolve().parent.parent / "bot" / "assets" / "welcome.png"
    return str(default) if default.is_file() else ""


async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()

    tg_id = message.from_user.id
    if not was_welcome_shown(tg_id):
        banner_path = _resolve_welcome_banner_path()
        try:
            if banner_path:
                await message.answer_photo(
                    photo=FSInputFile(banner_path),
                    caption=WELCOME_CAPTION,
                    parse_mode="Markdown",
                )
            else:
                await message.answer(WELCOME_CAPTION, parse_mode="Markdown")
        except Exception as e:
            logger.error("Приветствие: %s", e)
            await message.answer(WELCOME_CAPTION, parse_mode="Markdown")
        mark_welcome_shown(tg_id)

    with get_db_session() as db:
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()

        if user:
            if user.active:
                is_admin = user_has_permission(db, message.from_user.id, "admin:manage")

                if is_admin:
                    await message.reply(
                        "👑 **Панель администратора**. Кнопки ниже или команды в меню бота.",
                        reply_markup=reply_keyboard_admin(),  # Здесь скобки были — это ГУД
                        parse_mode="Markdown",
                    )
                else:
                    await message.reply(
                        f"✅ С возвращением, {user.full_name}!",
                        # ВОТ ТУТ БЫЛА ОШИБКА: добавляем скобки ()
                        reply_markup=reply_keyboard_user(),
                        parse_mode="Markdown",
                    )
            else:
                await message.reply(
                    "⏳ Ваш аккаунт ожидает активации администратором.\n"
                    "Если у вас есть код доступа, введите его сейчас."
                )
            return

    # Логика для новых пользователей
    await message.answer(
        "👋 **Добро пожаловать!**\n\nДля начала работы необходимо зарегистрироваться.\n"
        "Введите ваше **ФИО** (полностью):",
        parse_mode="Markdown"
    )
    await state.set_state(RegistrationStates.waiting_for_name)


async def process_reg_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text.strip())
    await message.reply("Теперь введите номер вашей топливной карты (только цифры):")
    await state.set_state(RegistrationStates.waiting_for_card)


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


async def cmd_link(message: types.Message):
    args = extract_args(message)
    if not args:
        await message.reply("Введите: /link <код> (код выдаёт администратор).")
        return

    code = args.split()[0]

    with get_db_session() as db:
        # 1. Проверяем и "гасим" код в базе
        ok, result = verify_and_consume_code(db, code, message.from_user.id)

        if not ok:
            reason = result
            # ... (логика обработки ошибок остается прежней)
            if reason == "invalid_or_used":
                await message.reply("Код неверен или уже использован.")
            elif reason == "expired":
                await message.reply("Код просрочен.")
            elif reason == "already_linked_to_other":
                await message.reply("Эта запись уже привязана к другому Telegram.")
            else:
                await message.reply("Ошибка привязки.")
            return

        # 2. Получаем ID пользователя из результата проверки кода
        user_id = None
        if isinstance(result, dict) and "user_id" in result:
            user_id = result["user_id"]
        elif hasattr(result, "user_id"):
            user_id = result.user_id

        if not user_id:
            await message.reply("Ошибка: запись пользователя не найдена.")
            return

        # 3. Загружаем объект пользователя для редактирования
        user = db.query(User).filter(User.id == user_id).first()

        if user:
            # АКТИВАЦИЯ
            user.active = True

            # НАЗНАЧЕНИЕ РОЛИ (Обязательно!)
            # Если у тебя в базе роль обычного пользователя имеет ID 1, ставь 1.
            # Без role_id Middleware будет считать, что у юзера нет прав.
            if not user.role_id:
                user.role_id = 2

                # СОХРАНЕНИЕ
            db.commit()

            # Подготовка данных для ответа
            full_name = user.full_name
            cards_s = ", ".join(user.cards or []) or "—"
            cars_s = ", ".join(user.cars or []) or "—"  # исправлено: берем из user.cars

            await message.reply(
                f"✅ **Аккаунт успешно активирован!**\n\n"
                f"ФИО: {full_name}\n"
                f"Карты: {cards_s}\n"
                f"Авто: {cars_s}",
                reply_markup=reply_keyboard_user(),  # Сразу даем кнопки пользователя
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
            user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
            presumed_id = user.id if user else None
            processor = SmartFuelOCR(db)
            ocr_result = processor.run_pipeline(
                file_path,
                telegram_user_id=message.from_user.id,
                presumed_user_id=presumed_id,
            )

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
            f"💧 Кол-во: {ocr_result.get('quantity', '—')} л.\n"
            f"💰 Сумма: {ocr_result.get('total_sum', '—')} руб.\n"
            f"🏪 АЗС: {ocr_result.get('azs_number', '—')}\n"
            f"🧾 Чек №: {ocr_result.get('doc_number', '—')}\n"
            f"📅 Дата и время: {ocr_result.get('date', '—')} {ocr_result.get('time', '')}\n\n"
            f"Подтвердите данные или выберите действие:"
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


def _can_edit_personal_receipt_op(db, op: FuelOperation, telegram_id: int) -> bool:
    if not op or op.source != "personal_receipt":
        return False
    if (op.status or "") != "new":
        return False
    u = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not u:
        return False
    if op.presumed_user_id and op.presumed_user_id != u.id:
        return False
    return True


async def callback_ocr_confirm(call: types.CallbackQuery, state: FSMContext):
    """Подтверждение OCR → ввод госномера и проверка по справочнику авто (ТЗ 8.2 п.6–7)."""
    op_id = int(call.data.split("_")[-1])
    with get_db_session() as db:
        op = db.query(FuelOperation).get(op_id)
        if not _can_edit_personal_receipt_op(db, op, call.from_user.id):
            await call.answer("Операция недоступна.", show_alert=True)
            return

    await state.update_data(op_id=op_id)
    await state.set_state(ReceiptStates.waiting_for_personal_car_plate)
    await call.message.edit_text(
        "🚗 Введите **государственный номер** автомобиля "
        "(как в справочнике: допускаются пробелы и дефисы, например `1234 AB-7`).",
        parse_mode="Markdown",
    )
    await call.answer()


async def callback_ocr_edit(call: types.CallbackQuery, state: FSMContext):
    """ТЗ 9.4 — исправить: сбрасываем черновик и просим прислать чек снова."""
    op_id = int(call.data.split("_")[-1])
    with get_db_session() as db:
        op = db.query(FuelOperation).get(op_id)
        if not _can_edit_personal_receipt_op(db, op, call.from_user.id):
            await call.answer("Операция недоступна.", show_alert=True)
            return
        db.delete(op)
        db.commit()

    await state.set_state(ReceiptStates.waiting_for_photo)
    await state.update_data(op_id=None)
    await call.message.edit_text(
        "✏️ Черновик сброшен. Сделайте более читаемое фото чека и отправьте его снова "
        "(кнопка «📸 Отправить чек» или команда /check)."
    )
    await call.answer()


async def callback_select_personal_car(call: types.CallbackQuery, state: FSMContext):
    car_id = int(call.data.split("_")[-1])
    with get_db_session() as db:
        car = db.query(Car).get(car_id)
        if not car:
            await call.answer("Автомобиль не найден.", show_alert=True)
            return
        plate = car.plate

    await state.update_data(selected_car_plate=plate, selected_car_id=car_id)
    await state.set_state(ReceiptStates.waiting_for_personal_fueler)
    await call.message.edit_text(f"Выбрано авто: **{plate}**", parse_mode="Markdown")
    await call.message.answer(
        "👤 Кто **фактически заправлялся**? Введите **ФИО** сотрудника (как в базе организации):",
        parse_mode="Markdown",
    )
    await call.answer()


async def process_personal_car_plate(message: types.Message, state: FSMContext):
    data = await state.get_data()
    op_id = data.get("op_id")
    if not op_id:
        await state.clear()
        return

    norm = normalize_plate(message.text or "")
    if not norm:
        await message.answer("Введите непустой госномер.")
        return

    with get_db_session() as db:
        matches = find_cars_by_normalized_plate(db, norm)

    if not matches:
        await message.answer(
            "❌ Автомобиль с таким номером **не найден** в справочнике. "
            "Проверьте номер или обратитесь к администратору. Введите номер снова:"
        )
        return

    if len(matches) == 1:
        await state.update_data(selected_car_plate=matches[0].plate, selected_car_id=matches[0].id)
        await state.set_state(ReceiptStates.waiting_for_personal_fueler)
        await message.answer(
            "👤 Кто **фактически заправлялся**? Введите **ФИО** сотрудника (как в базе организации):",
            parse_mode="Markdown",
        )
        return

    await message.answer(
        "Найдено несколько записей с таким номером. Выберите автомобиль:",
        reply_markup=get_personal_car_pick_kb(matches),
    )


async def process_personal_fueler_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    op_id = data.get("op_id")
    car_plate = data.get("selected_car_plate")
    if not op_id or not car_plate:
        await message.answer("Сессия устарела. Отправьте чек заново ( /check ).")
        await state.clear()
        return

    q = (message.text or "").strip()
    if not q:
        await message.answer("Введите ФИО.")
        return

    with get_db_session() as db:
        initiator = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        candidates = (
            db.query(User)
            .filter(User.full_name.ilike(f"%{q}%"), User.active.is_(True))
            .all()
        )
        if not candidates:
            await message.answer(f"❌ Сотрудник «{q}» не найден в базе. Введите ФИО точнее:")
            return
        if len(candidates) > 1:
            lines = "\n".join(f"— {u.full_name}" for u in candidates[:15])
            await message.answer(f"Найдено несколько совпадений. Уточните ФИО:\n{lines}")
            return

        fueler = candidates[0]
        op = db.query(FuelOperation).get(op_id)
        if not op or op.source != "personal_receipt":
            await message.answer("Операция не найдена.")
            await state.clear()
            return
        if not _can_edit_personal_receipt_op(db, op, message.from_user.id):
            await message.answer("Эту операцию уже обработали.")
            await state.clear()
            return

        op.actual_car = car_plate
        op.confirmed_user_id = fueler.id
        if initiator:
            op.presumed_user_id = op.presumed_user_id or initiator.id
        op.status = "confirmed"
        op.confirmed_at = datetime.datetime.now(datetime.timezone.utc)

        db.add(
            ConfirmationHistory(
                operation_id=op.id,
                from_user_id=initiator.id if initiator else None,
                to_user_id=fueler.id,
                answer="confirmed",
                stage_result=(
                    f"Личные средства: авто {car_plate}, заправлялся {fueler.full_name}"
                ),
            )
        )
        db.commit()

        try:
            export_to_excel_final(op_id)
        except Exception as e:
            logger.error("Excel export: %s", e)
            await message.answer(
                "✅ Запись подтверждена в боте, но **не удалось записать в Excel** "
                "(файл занят или ошибка диска). Обратитесь к администратору."
            )
            await state.clear()
            return

    await message.answer(
        f"✅ Заправка учтена: авто **{car_plate}**, заправлялся **{fueler.full_name}**. "
        f"Строка добавлена в Excel (лист «Заправки_личные_средства»).",
        parse_mode="Markdown",
    )
    await state.clear()


async def callback_ocr_cancel(call: types.CallbackQuery, state: FSMContext):
    op_id = int(call.data.split("_")[-1])
    with get_db_session() as db:
        op = db.query(FuelOperation).get(op_id)
        if op and _can_edit_personal_receipt_op(db, op, call.from_user.id):
            db.delete(op)
            db.commit()

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
        if not user or not op:
            await call.answer("Данные не найдены.", show_alert=True)
            return

        # Если у водителя еще нет привязанных машин
        if not user.cars:
            await state.update_data(conf_op_id=operation_id)
            await state.set_state(ReceiptStates.waiting_for_confirmed_car)
            await call.message.answer("Подтвердите госномер автомобиля (например, 1234 AB-7):")
        else:
            op.status = "confirmed"
            op.confirmed_at = datetime.datetime.now(datetime.timezone.utc)
            op.confirmed_user_id = user.id
            if not op.car_from_api and user.cars:
                op.car_from_api = user.cars[0]
            db.commit()
            await call.message.edit_text(f"✅ Операция подтверждена для {op.car_from_api}")
    await call.answer()


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


async def process_real_fueler_name(message: types.Message, state: FSMContext):
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

            await send_operation_to_user(message.bot, target_user.telegram_id, op_id)
            await message.answer(f"✅ Запрос перенаправлен сотруднику {target_user.full_name}.")
            await state.clear()
        else:
            op.status = "requires_manual"
            db.commit()
            await message.answer("⚠️ У найденного сотрудника не привязан Telegram. Данные переданы администратору.")
            await state.clear()


async def process_confirmed_car(message: types.Message, state: FSMContext):
    """Госномер при подтверждении операции по карте — только авто из справочника `cars`."""
    data = await state.get_data()
    op_id = data.get("conf_op_id")
    norm = normalize_plate(message.text or "")

    with get_db_session() as db:
        user = db.query(User).filter_by(telegram_id=message.from_user.id).first()
        op = db.query(FuelOperation).get(op_id)

        if not user or not op:
            await message.answer("Произошла ошибка: не удалось найти данные операции.")
            await state.clear()
            return

        matches = find_cars_by_normalized_plate(db, norm)
        if not matches:
            await message.answer(
                "❌ Такого автомобиля нет в справочнике. Введите госномер ещё раз "
                "(или обратитесь к администратору для добавления авто в базу)."
            )
            return
        if len(matches) > 1:
            await message.answer(
                "Найдено несколько совпадений по номеру. Уточните ввод или обратитесь к администратору."
            )
            return

        plate = matches[0].plate
        u_cars = list(user.cars or [])
        if plate not in u_cars:
            u_cars.append(plate)
            user.cars = u_cars

        op.status = "confirmed"
        op.confirmed_at = datetime.datetime.now(datetime.timezone.utc)
        op.confirmed_user_id = user.id
        op.actual_car = plate
        if not op.car_from_api:
            op.car_from_api = plate

        db.commit()

    await message.answer(
        f"✅ Номер {plate} сохранён в профиль. Операция подтверждена. Спасибо!"
    )
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
    dp.message.register(process_personal_car_plate, ReceiptStates.waiting_for_personal_car_plate)
    dp.message.register(process_personal_fueler_name, ReceiptStates.waiting_for_personal_fueler)
    dp.message.register(process_confirmed_car, ReceiptStates.waiting_for_confirmed_car)
    dp.message.register(process_disputed_car, ReceiptStates.waiting_for_disputed_car)
    dp.message.register(process_real_fueler_name, ReceiptStates.waiting_for_real_fueler)
    dp.message.register(btn_user_cars_menu, F.text == BTN_USER_CARS)
    dp.message.register(process_add_new_car, ReceiptStates.waiting_for_new_car_add)
    dp.message.register(cmd_pending, Command(commands=["pending"]))
    dp.callback_query.register(callback_fuel_card_confirm, F.data.startswith("fuel_card_yes_"))
    dp.callback_query.register(callback_fuel_card_reject, F.data.startswith("fuel_card_no_"))
    dp.callback_query.register(callback_ocr_confirm, F.data.startswith("ocr_confirm_"))
    dp.callback_query.register(callback_ocr_edit, F.data.startswith("ocr_edit_"))
    dp.callback_query.register(callback_ocr_cancel, F.data.startswith("ocr_cancel_"))
    dp.callback_query.register(callback_select_personal_car, F.data.startswith("personal_car_"))
    # dp.message.register(btn_user_profile, lambda m: m.text == BTN_USER_PROFILE)
    # dp.message.register(cmd_link_help, lambda m: m.text == BTN_USER_LINK_HELP)
    # dp.message.register(cmd_user_help, lambda m: m.text == BTN_USER_HELP)
    # dp.message.register(btn_user_home, lambda m: m.text == BTN_USER_HOME)
    # dp.message.register(btn_admin_home, lambda m: m.text == BTN_ADMIN_HOME)
    dp.callback_query.register(callback_op_confirm, F.data.startswith("op_confirm:"))
    dp.callback_query.register(callback_op_reject, F.data.startswith("op_reject:"))
    dp.message.register(cmd_pending, F.text == BTN_USER_PENDING)


