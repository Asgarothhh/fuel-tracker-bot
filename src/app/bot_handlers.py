import os
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from io import StringIO, BytesIO
import csv

from aiogram import types, Dispatcher, F
from aiogram.types import (
    InputFile, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, BufferedInputFile
)
from aiogram.filters import Command
from io import StringIO, BytesIO
import csv
from datetime import datetime, timezone

from app.config import ADMIN_TELEGRAM_ID
from app.db import get_db_session
from app.tokens import verify_and_consume_code, create_bulk_codes
from app.permissions import require_permission


# --- Обработчики процесса подтверждения ---

async def callback_user_yes(call: types.CallbackQuery):
    """Обработка кнопки 'Да, это я'"""
    op_id = int(call.data.split(":")[1])
    with get_db_session() as db:
        user = db.query(User).filter_by(telegram_id=call.from_user.id).first()
        op = db.query(FuelOperation).filter_by(id=op_id).first()

        # Если в данных API уже есть госномер, заправка подтверждается сразу
        if op.car_from_api:
            op.status = "confirmed"
            op.confirmed_user_id = user.id
            op.confirmed_at = datetime.now(timezone.utc)
            db.commit()
            await call.message.edit_text(call.message.text + "\n\n✅ Подтверждено автоматически.")
            export_to_excel_final(op.id)
        else:
            # Если госномера нет, переходим в состояние ожидания ввода госномера
            db.merge(UserState(telegram_id=call.from_user.id, operation_id=op_id, step="ask_car"))
            db.commit()
            await call.message.answer("На каком автомобиле была заправка? Введите госномер (например, 1234 AB-7):")
    await call.answer()


async def callback_user_no(call: types.CallbackQuery):
    """Обработка кнопки 'Нет, не я' (Логика Пинг-понга)"""
    op_id = int(call.data.split(":")[1])
    with get_db_session() as db:
        user = db.query(User).filter_by(telegram_id=call.from_user.id).first()
        # Ищем, кто прислал этот запрос (для возврата)
        hist = db.query(ConfirmationHistory).filter_by(operation_id=op_id, to_user_id=user.id).order_by(
            ConfirmationHistory.id.desc()).first()

        if hist and hist.from_user_id:
            # Если задачу переслал другой юзер, возвращаем её ему
            prev_user = db.query(User).filter_by(id=hist.from_user_id).first()
            if prev_user and prev_user.telegram_id:
                await call.message.edit_text("❌ Задача возвращена инициатору.")
                await call.bot.send_message(
                    prev_user.telegram_id,
                    f"⚠️ Пользователь {user.full_name} отклонил заправку (ID {op_id}). Укажите верного заправщика (ФИО или госномер):"
                )
                db.merge(UserState(telegram_id=prev_user.telegram_id, operation_id=op_id, step="ask_person"))
        else:
            # Если это первый круг, просим текущего юзера указать, кто заправлялся
            db.merge(UserState(telegram_id=call.from_user.id, operation_id=op_id, step="ask_person"))
            await call.message.edit_text("❌ Укажите, кто заправлялся (ФИО или госномер):")

        db.commit()
    await call.answer()


async def handle_user_text(message: types.Message):
    """Обработка текстовых ответов на основе состояний (UserState)"""
    with get_db_session() as db:
        st = db.query(UserState).filter_by(telegram_id=message.from_user.id).first()
        if not st:
            return  # Если это просто текст, игнорируем

        op = db.query(FuelOperation).filter_by(id=st.operation_id).first()
        user = db.query(User).filter_by(telegram_id=message.from_user.id).first()
        text = message.text.strip()

        if st.step == "ask_car":
            op.actual_car = text.upper()
            op.status = "confirmed"
            op.confirmed_user_id = user.id
            op.confirmed_at = datetime.now(timezone.utc)
            db.delete(st)
            db.commit()
            await message.reply(f"✅ Госномер {text.upper()} сохранен. Заправка подтверждена.")
            export_to_excel_final(op.id)

        elif st.step == "ask_person":
            # Ищем человека по ФИО или госномерам его машин
            found = db.query(User).filter(User.full_name.ilike(f"%{text}%")).first()
            if not found:
                car = db.query(Car).filter(Car.plate.ilike(f"%{text}%")).first()
                if car and car.owners:
                    found = db.query(User).filter_by(id=car.owners[0]).first()

            if found and found.telegram_id:
                db.delete(st)
                db.commit()
                # Пересылаем операцию новому кандидату
                await send_operation_to_user(found.telegram_id, op.id, from_user_id=user.id)
                await message.reply(f"🚀 Запрос перенаправлен пользователю {found.full_name}.")
            else:
                await message.reply("Пользователь не найден. Попробуйте уточнить ФИО или введите госномер автомобиля:")


async def send_operation_to_user(tg_id: int, op_id: int, from_user_id: int = None):
    """Отправка запроса пользователю с полными данными из ТЗ"""
    with get_db_session() as db:
        op = db.query(FuelOperation).filter_by(id=op_id).first()
        target_user = db.query(User).filter_by(telegram_id=tg_id).first()
        if not op or not target_user: return

        api = op.api_data or {}
        fuel = api.get("productName") or "—"
        qty = api.get("productQuantity") or "0"
        azs = api.get("azsNumber") or "—"
        dt = op.date_time.strftime("%d.%m.%Y %H:%M") if op.date_time else "—"

        text = (
            f"⛽️ *Подтвердите заправку*\n"
            f"📅 Дата: {dt}\n"
            f"⛽ Топливо: {fuel} ({qty} л.)\n"
            f"📍 АЗС: {azs}\n"
            f"💳 Карта: {api.get('cardNumber', '—')}\n"
            f"🧾 Чек: {op.doc_number or '—'}\n\n"
            f"Это ваша заправка?"
        )

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, это я", callback_data=f"user_yes:{op_id}")],
            [InlineKeyboardButton(text="❌ Нет, не я", callback_data=f"user_no:{op_id}")]
        ])

        # Фиксируем в истории, кому отправили
        db.add(ConfirmationHistory(operation_id=op_id, from_user_id=from_user_id, to_user_id=target_user.id, stage_result="sent"))
        db.commit()
        await types.Bot.get_current().send_message(tg_id, text, reply_markup=kb, parse_mode="Markdown")

# in-memory plain codes (shown once)
PENDING_PLAINS = {}  # token_id -> (plain_code, expires_at)


# --- User handlers ---
async def cmd_start(message: types.Message):
    kb_user = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="/link"), KeyboardButton(text="/myprofile")]],
        resize_keyboard=True
    )

    kb_admin = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📥 Обновить импорт"), KeyboardButton(text="🔎 Тестовый импорт")],
            [KeyboardButton(text="🗓 Расписания"), KeyboardButton(text="➕ Установить расписание")],
            [KeyboardButton(text="🗑 Удалить расписание"), KeyboardButton(text="👥 Пользователи")],
            [KeyboardButton(text="🔐 Сгенерировать код"), KeyboardButton(text="📤 Экспорт кодов")],
            [KeyboardButton(text="📊 Экспорт в Excel")]
        ],
        resize_keyboard=True
    )

    with get_db_session() as db:
        is_admin = user_has_permission(db, message.from_user.id, "admin:manage")

    if is_admin:
        await message.reply("Привет, админ. Выберите действие кнопкой или введите команду:", reply_markup=kb_admin)
    else:
        await message.reply("Привет! Для привязки аккаунта используйте /link <код>.", reply_markup=kb_user)


async def cmd_myprofile(message: types.Message):
    tg = message.from_user.id
    with get_db_session() as db:
        row = db.query(User.id, User.full_name, User.cards, User.cars).filter(User.telegram_id == tg).first()
    if not row:
        await message.reply("Профиль не найден. Привяжите аккаунт кодом /link <код>.")
        return
    _, full_name, cards, cars = row
    cards_s = ", ".join(cards or []) or "—"
    cars_s = ", ".join(cars or []) or "—"
    await message.reply(f"ФИО: {full_name}\nКарты: {cards_s}\nАвто: {cars_s}")


async def cmd_link(message: types.Message):
    args = message.get_args().strip()
    if not args:
        await message.reply("Введите код: /link <код>. Код вы получили от администратора.")
        return
    code = args.split()[0]
    with get_db_session() as db:
        ok, result = verify_and_consume_code(db, code, message.from_user.id)
    if not ok:
        if reason == "invalid_or_used":
            await message.reply("Код неверен или уже использован. Обратитесь к администратору.")
        elif reason == "expired":
            await message.reply("Код просрочен. Попросите администратора сгенерировать новый.")
        elif reason == "already_linked_to_other":
            await message.reply("Эта запись уже привязана к другому Telegram. Обратитесь в поддержку.")
        else:
            await message.reply("Ошибка привязки. Обратитесь к администратору.")
        return
    user = result
    cards = ", ".join(user.cards or []) or "—"
    cars = ", ".join(user.cars or []) or "—"
    info = f"Привязка выполнена.\nФИО: {user.full_name}\nКарты: {cards}\nАвто: {cars}"
    await message.reply(info)

# --- Админские команды ---

# --- Admin: schedules ---
@require_permission("admin:manage")
async def cmd_generate_codes(message: types.Message):
    args = message.get_args().strip().split()
    if len(args) < 2:
        await message.reply("Использование: /generate_codes <user_id> <count>")
        return
    try:
        user_id = int(args[0])
        count = int(args[1])
    except ValueError:
        await message.reply("Неверные параметры. user_id и count должны быть числами.")
        return

    created_by = message.from_user.id
    from app.models import User
    with get_db_session() as db:
        target = db.query(User).filter_by(id=user_id).first()
        if not target:
            await message.reply(f"Пользователь с id={user_id} не найден.")
            return
        codes = create_bulk_codes(db, user_id=user_id, count=count, created_by=created_by)
        text = f"Сгенерировано {len(codes)} кодов для user_id={user_id}.\n\n"
        text += "Коды (передайте пользователю безопасно):\n"
        text += "\n".join(codes)
        await message.reply(text)

@require_permission("admin:manage")
async def cmd_export_codes(message: types.Message):
    args = message.get_args().strip().split()
    user_id = None
    if args and args[0]:
        try:
            user_id = int(args[0])
        except ValueError:
            await message.reply("Неверный user_id. Использование: /export_codes [user_id]")
            return

    from app.models import LinkToken, User
    with get_db_session() as db:
        query = db.query(LinkToken)
        if user_id:
            query = query.filter(LinkToken.user_id == user_id)
        tokens = query.all()

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "token_id", "user_id", "user_full_name", "code_hash", "created_by",
            "created_at", "expires_at", "status", "telegram_id", "used_at", "note"
        ])
        for t in tokens:
            user = db.query(User).filter_by(id=t.user_id).first()
            writer.writerow([
                t.id,
                t.user_id,
                user.full_name if user else "",
                getattr(t, "code_hash", "") or "",
                t.created_by or "",
                t.created_at.isoformat() if t.created_at else "",
                t.expires_at.isoformat() if t.expires_at else "",
                getattr(t, "status", "") or "",
                t.telegram_id or "",
                t.used_at.isoformat() if getattr(t, "used_at", None) else "",
                t.note or ""
            ])
        csv_bytes = output.getvalue().encode("utf-8")
        bio = BytesIO(csv_bytes)
        bio.name = f"link_tokens_{user_id or 'all'}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.csv"
        bio.seek(0)
        await message.reply_document(InputFile(bio, filename=bio.name))
        output.close()

@require_permission("admin:manage")
async def callback_assign_op(call: types.CallbackQuery):
    try:
        op_id = int(call.data.split(":", 1)[1])
    except Exception:
        await call.answer("Неверный идентификатор операции.", show_alert=True)
        return
    await call.message.answer(f"Чтобы назначить операцию {op_id} пользователю, выполните команду:\n/assign_op {op_id} <user_id>")
    await call.answer()


@require_permission("admin:manage")
async def callback_mark_dispute(call: types.CallbackQuery):
    try:
        op_id = int(call.data.split(":", 1)[1])
    except Exception:
        await call.answer("Неверный идентификатор операции.", show_alert=True)
        return
    with get_db_session() as db:
        op = db.query(FuelOperation).filter_by(id=op_id).first()
        if not op:
            await call.answer("Операция не найдена.", show_alert=True)
            return
        op.status = "requires_manual"
        db.commit()
    try:
        await call.message.edit_reply_markup()
    except Exception:
        pass
    await call.message.answer(f"Операция {op_id} помечена как спорная и переведена в ручную обработку.")
    await call.answer()


@require_permission("admin:manage")
async def cmd_assign_op(message: types.Message):
    args = extract_args(message).split()
    if len(args) < 2:
        await message.reply("Использование: /assign_op <op_id> <user_id>")
        return
    try:
        op_id = int(args[0]); user_id = int(args[1])
    except ValueError:
        await message.reply("op_id и user_id должны быть числами.")
        return
    with get_db_session() as db:
        op = db.query(FuelOperation).filter_by(id=op_id).first()
        user = db.query(User).filter_by(id=user_id).first()
        if not op:
            await message.reply("Операция не найдена.")
            return
        if not user:
            await message.reply("Пользователь не найден.")
            return
        op.presumed_user_id = user.id
        db.commit()
    await message.reply(f"Операция {op_id} назначена пользователю {user.full_name} (id={user.id}).")


# --- ReplyKeyboard wrappers (text buttons) ---
@require_permission("admin:manage")
async def btn_update_import(message: types.Message):
    await cmd_run_import_now(message)

@require_permission("admin:manage")
async def btn_test_import(message: types.Message):
    await cmd_run_import_now_dry(message)

@require_permission("admin:manage")
async def btn_schedule_list(message: types.Message):
    await cmd_schedule_get(message)

@require_permission("admin:manage")
async def btn_schedule_set(message: types.Message):
    await message.reply("Использование: /schedule_set <name> <HH:MM UTC>\nПример: /schedule_set belorusneft_daily 01:30 UTC")

@require_permission("admin:manage")
async def btn_schedule_remove(message: types.Message):
    await message.reply("Использование: /schedule_remove <name>\nПример: /schedule_remove belorusneft_daily")

@require_permission("admin:manage")
async def btn_users(message: types.Message):
    await cmd_users(message)

@require_permission("admin:manage")
async def btn_generate_code(message: types.Message):
    await message.reply("Использование: /generate_code <user_id>\nПример: /generate_code 42")

@require_permission("admin:manage")
async def btn_export_codes(message: types.Message):
    await cmd_export_codes(message)


@require_permission("admin:manage")
async def btn_export_excel(message: types.Message):
    """Генерация и отправка файла Excel со всеми заправками"""
    await message.answer("⏳ Собираю данные для отчета, подождите...")

    with get_db_session() as db:
        operations = db.query(FuelOperation).order_by(FuelOperation.date_time.desc()).all()

        if not operations:
            await message.answer("Нет данных для экспорта.")
            return

        wb = Workbook()
        ws = wb.active
        ws.title = "Заправки"

        # Заголовки (согласно вашему ТЗ)
        headers = [
            "ID", "Дата", "Время", "Источник", "Статус",
            "Карта", "Топливо", "Объем (л)", "Стоимость",
            "АЗС", "Госномер (из API)", "Водитель (из API)",
            "Фактический Госномер", "Подтвердил (ФИО)"
        ]
        ws.append(headers)

        for op in operations:
            api = op.api_data or {}
            # Собираем строку данных
            ws.append([
                op.id,
                op.date_time.strftime('%d.%m.%Y') if op.date_time else "—",
                op.date_time.strftime('%H:%M') if op.date_time else "—",
                op.source,
                op.status,
                api.get('cardNumber', '—'),
                api.get('productName', '—'),
                api.get('productQuantity', 0),
                api.get('productCost', 0),
                api.get('azsNumber', '—'),
                api.get('carNum', '—'),
                api.get('driverName', '—'),
                op.actual_car or "—",
                op.confirmed_user.full_name if op.confirmed_user else "—"
            ])

        # Сохраняем в буфер, чтобы не мусорить файлами на диске
        file_buffer = BytesIO()
        wb.save(file_buffer)
        file_buffer.seek(0)

        filename = f"Fuel_Report_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.xlsx"

        await message.answer_document(
            types.BufferedInputFile(file_buffer.read(), filename=filename),
            caption=f"📊 Выгрузка заправок на {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )

# --- Register handlers ---
def register_handlers(dp: Dispatcher):
    # commands
    dp.message.register(cmd_start, Command(commands=["start"]))
    dp.message.register(cmd_link, Command(commands=["link"]))
    dp.message.register(cmd_myprofile, Command(commands=["myprofile"]))
    dp.message.register(cmd_users, Command(commands=["users"]))
    dp.message.register(cmd_generate_code, Command(commands=["generate_code"]))
    dp.message.register(cmd_export_codes, Command(commands=["export_codes"]))
