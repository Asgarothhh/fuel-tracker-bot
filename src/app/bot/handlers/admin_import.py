import logging
from datetime import datetime, timezone, timedelta
from io import BytesIO

from aiogram import types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from openpyxl import Workbook
from sqlalchemy import cast, String

from src.app.belorusneft_api import fetch_operational_raw, parse_operations
from src.app.db import get_db_session
from src.app.models import FuelOperation, FuelCard, Car, User
from src.app.permissions import require_permission, user_has_permission
from src.app.bot.keyboards import (
    BTN_ADMIN_IMPORT,
    BTN_ADMIN_IMPORT_TEST,
    BTN_ADMIN_SCHEDULES,
    BTN_ADMIN_SCHEDULE_SET,
    BTN_ADMIN_SCHEDULE_DEL,
    BTN_ADMIN_USERS,
    BTN_ADMIN_PENDING,
    BTN_ADMIN_EXPORT_EXCEL,
    BTN_ADMIN_GEN_CODE,
    BTN_ADMIN_EXPORT_CODES,
    BTN_ADMIN_HELP,
)
from src.app.bot.utils import extract_args
from src.app.bot.handlers import admin_schedules as admin_schedules_mod
from src.app.bot.handlers import admin_users as admin_users_mod

logger = logging.getLogger(__name__)

ADMIN_HELP_TEXT = (
    "📖 *Справка администратора*\n\n"
    "*Импорт:*\n"
    "• «Обновить импорт» — загрузка операций за вчера из API.\n"
    "• «Тестовый импорт» — dry-run, смотрите логи.\n\n"
    "*Расписание:*\n"
    "/schedule_set имя HH:MM (UTC)\n"
    "/schedule_remove имя\n\n"
    "*Пользователи:*\n"
    "/users — список, /generate_code id, /export_codes\n\n"
    "*Операции:*\n"
    "• «Неподтверждённые» — очередь.\n"
    "/assign_op <op_id> <user_id>\n\n"
    "• «Экспорт в Excel» — выгрузка всех операций в файл."
)


@require_permission("admin:manage")
async def cmd_admin_help(message: types.Message):
    await message.reply(ADMIN_HELP_TEXT, parse_mode="HTML")


@require_permission("admin:manage")
async def cmd_pending_ops(message: types.Message):
    with get_db_session() as db:
        ops = (
            db.query(FuelOperation)
            .filter(FuelOperation.status != "confirmed")
            .order_by(FuelOperation.id.desc())
            .limit(30)
            .all()
        )
    if not ops:
        await message.reply("Нет операций вне статуса «confirmed».")
        return
    lines = [f"#{o.id} | {o.status} | чек {o.doc_number or '—'} | {o.date_time or '—'}" for o in ops[:25]]
    body = "\n".join(lines)
    if len(ops) > 25:
        body += "\n…"
    await message.reply("Очередь (не confirmed):\n" + body)


@require_permission("admin:manage")
async def btn_export_excel(message: types.Message):
    await message.answer("⏳ Формирую Excel…")
    with get_db_session() as db:
        operations = db.query(FuelOperation).order_by(FuelOperation.date_time.desc()).all()

    if not operations:
        await message.answer("Нет данных.")
        return

    wb = Workbook()
    ws = wb.active
    ws.title = "Заправки"
    headers = [
        "ID", "Дата", "Время", "Источник", "Статус",
        "Карта", "Топливо", "Объём (л)", "Стоимость",
        "АЗС", "Госномер (API)", "Водитель (API)",
        "Факт. госномер", "Подтвердил",
    ]
    ws.append(headers)

    for op in operations:
        api = op.api_data if isinstance(op.api_data, dict) else {}
        row_inner = api.get("row") if isinstance(api.get("row"), dict) else {}
        card_o = api.get("card") if isinstance(api.get("card"), dict) else {}
        card = api.get("cardNumber") or card_o.get("cardNumber") or "—"
        pname = api.get("productName") or row_inner.get("productName") or "—"
        pq = api.get("productQuantity") or row_inner.get("productQuantity") or "—"
        cost = api.get("productCost") or row_inner.get("productCost") or "—"
        azs = api.get("azsNumber") or row_inner.get("azsNumber") or "—"
        car_api = api.get("carNum") or row_inner.get("carNum") or op.car_from_api or "—"
        drv = api.get("driverName") or row_inner.get("driverName") or "—"
        ws.append([
            op.id,
            op.date_time.strftime("%d.%m.%Y") if op.date_time else "—",
            op.date_time.strftime("%H:%M") if op.date_time else "—",
            op.source,
            op.status,
            card,
            pname,
            pq,
            cost,
            azs,
            car_api,
            drv,
            op.actual_car or "—",
            op.confirmed_user.full_name if op.confirmed_user else "—",
        ])

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    name = f"Fuel_Report_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.xlsx"
    await message.answer_document(BufferedInputFile(buf.read(), filename=name), caption="Выгрузка операций")


@require_permission("admin:manage")
async def cmd_run_import_now_dry(message: types.Message):
    from src.app.jobs import run_import_job

    try:
        run_import_job("manual_dry_run", dry_run=True)
        await message.reply("Тестовый импорт (dry-run) выполнен. Смотрите логи; БД не менялась.")
    except Exception as e:
        logger.exception("dry-run import")
        await message.reply(f"Ошибка: {e}")


@require_permission("admin:manage")
async def cmd_run_import_now(message: types.Message):
    date = datetime.now() - timedelta(days=1)
    new_count = 0
    try:
        raw = fetch_operational_raw(date)
        status = raw.get("status")
        json_payload = raw.get("json")
        debug_files = raw.get("debug_files") or []

        if status != 200:
            await message.reply(f"HTTP {status}. Debug: {', '.join(debug_files)}")
            return

        if not json_payload:
            await message.reply(f"Нет JSON. Debug: {', '.join(debug_files)}")
            return

        ops = parse_operations(json_payload)
        if not ops:
            await message.reply("В ответе 0 операций.")
            return

        with get_db_session() as db:
            for op in ops:
                dt_raw = op.get("date_time") or op.get("dateTimeIssue")
                dt_obj = None
                if dt_raw:
                    try:
                        dt_obj = datetime.fromisoformat(str(dt_raw).replace("Z", "+00:00"))
                    except Exception:
                        dt_obj = None

                doc_raw = op.get("doc_number") or op.get("docNumber")
                doc = str(doc_raw).strip() if doc_raw is not None else None

                filters = [FuelOperation.source == "api"]
                if doc:
                    filters.append(FuelOperation.doc_number == doc)
                if dt_obj:
                    filters.append(FuelOperation.date_time == dt_obj)

                if db.query(FuelOperation).filter(*filters).first():
                    continue

                card_num = op.get("card_number") or op.get("cardNumber") or op.get("card")
                if card_num is not None:
                    card_num = str(card_num).strip()

                fuel_card = None
                if card_num:
                    fuel_card = db.query(FuelCard).filter_by(card_number=card_num).first()
                    if not fuel_card:
                        fuel_card = FuelCard(card_number=card_num, active=True)
                        db.add(fuel_card)
                        db.flush()

                presumed_user = None
                if fuel_card and fuel_card.user_id:
                    presumed_user = db.query(User).filter_by(id=fuel_card.user_id).first()
                elif card_num:
                    try:
                        presumed_user = (
                            db.query(User).filter(cast(User.cards, String).like(f"%{card_num}%")).first()
                        )
                    except Exception:
                        presumed_user = None
                    if presumed_user and fuel_card:
                        fuel_card.user_id = presumed_user.id

                car_plate_norm = None
                car_plate = op.get("carNum") or op.get("car_num") or op.get("car")
                if car_plate:
                    car_plate_norm = str(car_plate).strip().upper()
                    car = db.query(Car).filter_by(plate=car_plate_norm).first()
                    if not car:
                        car = Car(plate=car_plate_norm)
                        db.add(car)
                        db.flush()
                    if presumed_user:
                        owners = list(car.owners or [])
                        if presumed_user.id not in owners:
                            owners.append(presumed_user.id)
                            car.owners = owners
                        user_cars = list(presumed_user.cars or [])
                        if car_plate_norm not in user_cars:
                            user_cars.append(car_plate_norm)
                            presumed_user.cars = user_cars

                new_op = FuelOperation(
                    source="api",
                    api_data=op.get("raw") or op,
                    imported_at=datetime.now(timezone.utc),
                    status="loaded",
                )
                if doc:
                    new_op.doc_number = doc
                if dt_obj:
                    new_op.date_time = dt_obj
                if presumed_user:
                    new_op.presumed_user_id = presumed_user.id
                if car_plate_norm:
                    new_op.car_from_api = car_plate_norm

                db.add(new_op)
                new_count += 1

            db.commit()

        admin_rows = []
        with get_db_session() as db2:
            for u in db2.query(User).filter(User.telegram_id != None).all():
                try:
                    if user_has_permission(db2, u.telegram_id, "admin:manage"):
                        admin_rows.append(u)
                except Exception:
                    continue

        if new_count > 0 and admin_rows:
            with get_db_session() as db3:
                recent_ops = (
                    db3.query(
                        FuelOperation.id,
                        FuelOperation.doc_number,
                        FuelOperation.date_time,
                        FuelOperation.api_data,
                    )
                    .order_by(FuelOperation.imported_at.desc())
                    .limit(new_count)
                    .all()
                )
                recent_ops_raw = []
                for op_id, doc_number, date_time, api_data in recent_ops:
                    api = api_data or {}
                    recent_ops_raw.append({
                        "id": op_id,
                        "doc": doc_number or api.get("docNumber") or api.get("doc_number"),
                        "dt": date_time.isoformat() if date_time else api.get("dateTimeIssue"),
                        "card": api.get("cardNumber") or api.get("card_number") or "—",
                        "azs": api.get("azsNumber") or api.get("azs") or "—",
                        "qty": api.get("productQuantity") or api.get("quantity") or "—",
                    })

            for admin in admin_rows:
                for op in recent_ops_raw:
                    text = (
                        "Новая операция из API:\n"
                        f"ID: {op['id']}\n"
                        f"Дата: {op['dt']}\n"
                        f"Карта: {op['card']}\n"
                        f"АЗС: {op['azs']}\n"
                        f"Чек: {op['doc']}\n"
                        f"Кол-во: {op['qty']}"
                    )
                    kb = InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_op:{op['id']}")],
                            [InlineKeyboardButton(text="👤 Назначить", callback_data=f"assign_op:{op['id']}")],
                            [InlineKeyboardButton(text="⚠️ Спорная", callback_data=f"mark_dispute:{op['id']}")],
                        ]
                    )
                    try:
                        await message.bot.send_message(admin.telegram_id, text, reply_markup=kb)
                    except Exception:
                        logger.warning("Не удалось уведомить админа %s", admin.id)

        await message.reply(f"Импорт завершён. Новых операций: {new_count}")

    except Exception as e:
        logger.exception("run_import_now")
        await message.reply(f"Ошибка импорта: {e}")


@require_permission("admin:manage")
async def callback_confirm_op(call: types.CallbackQuery):
    try:
        op_id = int(call.data.split(":", 1)[1])
    except Exception:
        await call.answer("Неверный ID.", show_alert=True)
        return
    with get_db_session() as db:
        op = db.query(FuelOperation).filter_by(id=op_id).first()
        if not op:
            await call.answer("Не найдено.", show_alert=True)
            return
        op.status = "confirmed"
        op.confirmed_at = datetime.now(timezone.utc)
        db.commit()
    try:
        await call.message.edit_reply_markup()
    except Exception:
        pass
    await call.message.answer(f"Операция {op_id} подтверждена.")
    await call.answer()


@require_permission("admin:manage")
async def callback_assign_op(call: types.CallbackQuery):
    try:
        op_id = int(call.data.split(":", 1)[1])
    except Exception:
        await call.answer("Неверный ID.", show_alert=True)
        return
    await call.message.answer(f"Назначение: /assign_op {op_id} <user_id>")
    await call.answer()


@require_permission("admin:manage")
async def callback_mark_dispute(call: types.CallbackQuery):
    try:
        op_id = int(call.data.split(":", 1)[1])
    except Exception:
        await call.answer("Неверный ID.", show_alert=True)
        return
    with get_db_session() as db:
        op = db.query(FuelOperation).filter_by(id=op_id).first()
        if not op:
            await call.answer("Не найдено.", show_alert=True)
            return
        op.status = "requires_manual"
        db.commit()
    try:
        await call.message.edit_reply_markup()
    except Exception:
        pass
    await call.message.answer(f"Операция {op_id} — ручная обработка.")
    await call.answer()


@require_permission("admin:manage")
async def cmd_assign_op(message: types.Message):
    args = extract_args(message).split()
    if len(args) < 2:
        await message.reply("Использование: /assign_op <op_id> <user_id>")
        return
    try:
        op_id = int(args[0])
        user_id = int(args[1])
    except ValueError:
        await message.reply("Числа: op_id и user_id.")
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
        fn = user.full_name
    await message.reply(f"Операция {op_id} → пользователь {fn} (id={user_id}).")


@require_permission("admin:manage")
async def btn_update_import(message: types.Message):
    await cmd_run_import_now(message)


@require_permission("admin:manage")
async def btn_test_import(message: types.Message):
    await cmd_run_import_now_dry(message)


@require_permission("admin:manage")
async def btn_schedule_list(message: types.Message):
    await admin_schedules_mod.cmd_schedule_get(message)


@require_permission("admin:manage")
async def btn_schedule_set(message: types.Message):
    await message.reply("Команда: /schedule_set <имя> <HH:MM UTC>\nПример: /schedule_set daily 02:00")


@require_permission("admin:manage")
async def btn_schedule_remove(message: types.Message):
    await message.reply("Команда: /schedule_remove <имя>")


@require_permission("admin:manage")
async def btn_users(message: types.Message):
    await admin_users_mod.cmd_users(message)


@require_permission("admin:manage")
async def btn_generate_code(message: types.Message):
    await message.reply("Команда: /generate_code <user_id>")


@require_permission("admin:manage")
async def btn_export_codes(message: types.Message):
    await admin_users_mod.cmd_export_codes(message)


@require_permission("admin:manage")
async def btn_pending(message: types.Message):
    await cmd_pending_ops(message)


def register_admin_import_handlers(dp):
    dp.message.register(cmd_run_import_now, Command(commands=["run_import_now"]))
    dp.message.register(cmd_run_import_now_dry, Command(commands=["run_import_now_dry"]))
    dp.message.register(cmd_assign_op, Command(commands=["assign_op"]))
    dp.message.register(cmd_pending_ops, Command(commands=["pending_ops"]))

    dp.message.register(btn_update_import, lambda m: m.text == BTN_ADMIN_IMPORT)
    dp.message.register(btn_test_import, lambda m: m.text == BTN_ADMIN_IMPORT_TEST)
    dp.message.register(btn_schedule_list, lambda m: m.text == BTN_ADMIN_SCHEDULES)
    dp.message.register(btn_schedule_set, lambda m: m.text == BTN_ADMIN_SCHEDULE_SET)
    dp.message.register(btn_schedule_remove, lambda m: m.text == BTN_ADMIN_SCHEDULE_DEL)
    dp.message.register(btn_users, lambda m: m.text == BTN_ADMIN_USERS)
    dp.message.register(btn_pending, lambda m: m.text == BTN_ADMIN_PENDING)
    dp.message.register(btn_export_excel, lambda m: m.text == BTN_ADMIN_EXPORT_EXCEL)
    dp.message.register(btn_generate_code, lambda m: m.text == BTN_ADMIN_GEN_CODE)
    dp.message.register(btn_export_codes, lambda m: m.text == BTN_ADMIN_EXPORT_CODES)
    dp.message.register(cmd_admin_help, lambda m: m.text == BTN_ADMIN_HELP)

    dp.callback_query.register(callback_confirm_op, lambda c: c.data and c.data.startswith("confirm_op:"))
    dp.callback_query.register(callback_assign_op, lambda c: c.data and c.data.startswith("assign_op:"))
    dp.callback_query.register(callback_mark_dispute, lambda c: c.data and c.data.startswith("mark_dispute:"))
