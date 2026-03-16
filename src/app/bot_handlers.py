# src/app/bot_handlers.py
from aiogram import types, Dispatcher
from aiogram.types import InputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from io import StringIO, BytesIO
import csv
from datetime import datetime, timezone, timedelta
from src.app.config import ADMIN_TELEGRAM_ID, TOKEN_SALT, CODE_TTL_HOURS
from src.app.tokens import verify_and_consume_code, generate_code, hash_code
from src.app.models import LinkToken, User, FuelOperation
from src.app.belorusneft_api import fetch_operational_report, parse_operations
from src.app.db import get_db_session
from src.app.permissions import require_permission
from sqlalchemy.exc import IntegrityError

# --- Вспомогательная функция для извлечения аргументов команды ---
def extract_args(message: types.Message) -> str:
    text = message.text or ""
    parts = text.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""

# --- Пользовательские обработчики ---

async def cmd_start(message: types.Message):
    await message.reply("Привет! Для привязки аккаунта используйте /link <код> или нажмите кнопку 'Ввести код' в меню.")

async def cmd_link(message: types.Message):
    args = extract_args(message)
    if not args:
        await message.reply("Введите код: /link <код>. Код вы получили от администратора.")
        return

    code = args.split()[0]
    with get_db_session() as db:
        ok, result = verify_and_consume_code(db, code, message.from_user.id)

    if not ok:
        if result == "invalid_or_used":
            await message.reply("Код неверен или уже использован. Обратитесь к администратору.")
        elif result == "expired":
            await message.reply("Код просрочен. Попросите администратора сгенерировать новый.")
        elif result == "already_linked_to_other":
            await message.reply("Эта запись уже привязана к другому Telegram. Обратитесь в поддержку.")
        else:
            await message.reply("Ошибка привязки. Обратитесь к администратору.")
        return

    user = result
    cards = ", ".join(user.cards or []) or "—"
    cars = ", ".join(user.cars or []) or "—"
    info = f"Привязка выполнена.\nФИО: {user.full_name}\nКарты: {cards}\nАвто: {cars}"
    await message.reply(info)

# --- Админские команды и callbacks ---

@require_permission("admin:manage")
async def cmd_users(message: types.Message):
    """
    Выводит список пользователей (страница из 10) с инлайн-кнопками:
    [Сгенерировать код] [Просмотр]
    """
    args = extract_args(message)
    page = 1
    try:
        if args:
            page = max(1, int(args))
    except ValueError:
        page = 1

    page_size = 10
    offset = (page - 1) * page_size

    with get_db_session() as db:
        users = db.query(User).order_by(User.id).offset(offset).limit(page_size).all()
        total = db.query(User).count()

    if not users:
        await message.reply("Пользователи не найдены.")
        return

    for u in users:
        tg = f"@{u.telegram_id}" if u.telegram_id else "—"
        status = "Активен" if u.active else "Неактивен"
        text = f"{u.id}) {u.full_name} — {tg} — {status}"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Сгенерировать код", callback_data=f"gen_code:{u.id}"),
                InlineKeyboardButton(text="Просмотр", callback_data=f"view_user:{u.id}")
            ]
        ])
        await message.answer(text, reply_markup=kb)

    # навигация по страницам
    pages = (total + page_size - 1) // page_size
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"users_page:{page-1}"))
    if page < pages:
        nav_buttons.append(InlineKeyboardButton("Вперёд ▶️", callback_data=f"users_page:{page+1}"))
    if nav_buttons:
        await message.answer(f"Страница {page}/{pages}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[nav_buttons]))

@require_permission("admin:manage")
async def cmd_generate_code(message: types.Message):
    """
    Команда для генерации одного кода для конкретного пользователя:
    /generate_code <user_id>
    """
    args = extract_args(message)
    if not args:
        await message.reply("Использование: /generate_code <user_id>")
        return
    try:
        user_id = int(args.split()[0])
    except ValueError:
        await message.reply("Неверный user_id. Использование: /generate_code <user_id>")
        return

    admin_id = message.from_user.id
    with get_db_session() as db:
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            await message.reply(f"Пользователь с id={user_id} не найден.")
            return

        # сгенерировать код и сохранить хеш
        code_plain = generate_code()
        code_hash = hash_code(code_plain, TOKEN_SALT)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=CODE_TTL_HOURS)
        token = LinkToken(user_id=user_id, token_hash=code_hash, created_by=admin_id, created_at=datetime.now(timezone.utc), expires_at=expires_at)
        try:
            db.add(token)
            db.flush()
            db.commit()
        except IntegrityError:
            db.rollback()
            await message.reply("Не удалось сгенерировать код (конфликт). Попробуйте ещё раз.")
            return

    # показать код админу один раз и дать кнопку отправки пользователю
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("Отправить пользователю", callback_data=f"send_code:{token.id}")],
        [InlineKeyboardButton("Отозвать код", callback_data=f"revoke_code:{token.id}")]
    ])
    await message.reply(f"Код для пользователя {user.full_name} (id={user.id}):\n\n{code_plain}\n\nКод показывается один раз.", reply_markup=kb)

async def callback_users_page(call: types.CallbackQuery):
    # перенаправляем на команду /users с нужной страницей
    page = int(call.data.split(":", 1)[1])
    await call.message.delete()
    fake_msg = types.Message(**{
        "message_id": call.message.message_id,
        "date": call.message.date,
        "chat": call.message.chat,
        "from_user": call.from_user,
        "text": f"/users {page}"
    })
    await cmd_users(fake_msg)
    await call.answer()

async def callback_view_user(call: types.CallbackQuery):
    user_id = int(call.data.split(":", 1)[1])
    with get_db_session() as db:
        user = db.query(User).filter_by(id=user_id).first()
    if not user:
        await call.message.answer("Пользователь не найден.")
        await call.answer()
        return
    tg = f"@{user.telegram_id}" if user.telegram_id else "—"
    cards = ", ".join(user.cards or []) or "—"
    cars = ", ".join(user.cars or []) or "—"
    text = (
        f"ID: {user.id}\n"
        f"ФИО: {user.full_name}\n"
        f"Telegram: {tg}\n"
        f"Карты: {cards}\n"
        f"Авто: {cars}\n"
        f"Активен: {'Да' if user.active else 'Нет'}\n"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("Сгенерировать код", callback_data=f"gen_code:{user.id}")],
        [InlineKeyboardButton("Закрыть", callback_data="noop")]
    ])
    await call.message.answer(text, reply_markup=kb)
    await call.answer()

async def callback_generate_code(call: types.CallbackQuery):
    # Генерация кода по нажатию кнопки в списке пользователей
    user_id = int(call.data.split(":", 1)[1])
    admin_id = call.from_user.id
    with get_db_session() as db:
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            await call.message.answer("Пользователь не найден.")
            await call.answer()
            return

        code_plain = generate_code()
        code_hash = hash_code(code_plain, TOKEN_SALT)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=CODE_TTL_HOURS)
        token = LinkToken(user_id=user_id, token_hash=code_hash, created_by=admin_id, created_at=datetime.now(timezone.utc), expires_at=expires_at)
        try:
            db.add(token)
            db.flush()
            db.commit()
        except IntegrityError:
            db.rollback()
            await call.message.answer("Не удалось сгенерировать код (конфликт). Попробуйте ещё раз.")
            await call.answer()
            return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("Отправить пользователю", callback_data=f"send_code:{token.id}")],
        [InlineKeyboardButton("Отозвать код", callback_data=f"revoke_code:{token.id}")]
    ])
    # редактируем сообщение администратора, показываем код
    await call.message.answer(f"Код для {user.full_name} (id={user.id}):\n\n{code_plain}\n\nКод показывается один раз.", reply_markup=kb)
    await call.answer()

async def callback_send_code(call: types.CallbackQuery):
    token_id = int(call.data.split(":", 1)[1])
    with get_db_session() as db:
        token = db.query(LinkToken).filter_by(id=token_id).first()
        if not token:
            await call.message.answer("Токен не найден.")
            await call.answer()
            return
        user = db.query(User).filter_by(id=token.user_id).first() if token.user_id else None

    # Если у пользователя уже есть telegram_id — отправляем напрямую
    if user and user.telegram_id:
        # Мы не храним plain-код в БД, поэтому админ должен был сохранить код при создании.
        # Если plain-код недоступен, отправляем инструкцию.
        await call.message.answer(f"Отправляю инструкцию пользователю {user.full_name} (tg={user.telegram_id}).")
        try:
            await call.bot.send_message(user.telegram_id, "Вам выдан код для привязки аккаунта. Введите его в боте командой /link <код>.")
            await call.message.answer("Сообщение отправлено пользователю.")
        except Exception:
            await call.message.answer("Не удалось отправить сообщение пользователю (возможно, пользователь не начинал диалог с ботом).")
    else:
        # Если telegram_id неизвестен — даём инструкцию админу
        if user:
            await call.message.answer(f"У пользователя {user.full_name} нет привязанного Telegram. Передайте ему код вручную и попросите выполнить /link <код>.")
        else:
            await call.message.answer("Пользователь не найден. Невозможно отправить код.")
    await call.answer()

async def callback_revoke_code(call: types.CallbackQuery):
    token_id = int(call.data.split(":", 1)[1])
    admin_id = call.from_user.id
    with get_db_session() as db:
        token = db.query(LinkToken).filter_by(id=token_id).first()
        if not token:
            await call.message.answer("Токен не найден.")
            await call.answer()
            return
        token.token_hash = token.token_hash  # noop to mark touched
        token.status = "revoked"
        token.note = (token.note or "") + f"\nRevoked by admin {admin_id} at {datetime.now(timezone.utc).isoformat()}"
        db.commit()
    await call.message.answer("Код отозван.")
    await call.answer()

# --- Импорт операций (оставлено как было, с небольшими правками) ---

@require_permission("admin:manage")
async def cmd_run_import_now(message: types.Message):
    date = datetime.now() - timedelta(days=1)

    try:
        payload = fetch_operational_report(date)
        ops = parse_operations(payload)

        new_count = 0

        with get_db_session() as db:
            for op in ops:
                exists = db.query(FuelOperation).filter_by(
                    source="api",
                    doc_number=op.get("doc_number"),
                    date_time=op.get("date_time")
                ).first()

                if exists:
                    continue

                db.add(FuelOperation(
                    source="api",
                    api_data=op.get("raw"),
                    date_time=op.get("date_time"),
                    imported_at=datetime.now(timezone.utc),
                    status="loaded"
                ))
                new_count += 1

        await message.reply(f"Импорт завершён. Новых операций: {new_count}")

    except Exception as e:
        await message.reply(f"Ошибка импорта: {e}")

# --- Экспорт токенов (оставлен, но адаптирован под текущую модель) ---

@require_permission("admin:manage")
async def cmd_export_codes(message: types.Message):
    args_list = extract_args(message).split()
    user_id = None
    if args_list and args_list[0]:
        try:
            user_id = int(args_list[0])
        except ValueError:
            await message.reply("Неверный user_id. Использование: /export_codes [user_id]")
            return

    with get_db_session() as db:
        query = db.query(LinkToken)
        if user_id:
            query = query.filter(LinkToken.user_id == user_id)
        tokens = query.all()

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "token_id", "user_id", "user_full_name", "token_hash", "created_by",
            "created_at", "expires_at", "status", "telegram_id", "used_at", "note"
        ])
        for t in tokens:
            user = db.query(User).filter_by(id=t.user_id).first() if t.user_id else None
            writer.writerow([
                t.id,
                t.user_id or "",
                user.full_name if user else "",
                t.token_hash,
                t.created_by or "",
                t.created_at.isoformat() if t.created_at else "",
                t.expires_at.isoformat() if t.expires_at else "",
                getattr(t, "status", "") or "",
                t.telegram_id or "",
                t.used_at.isoformat() if getattr(t, "used_at", None) else "",
                t.note or ""
            ])
        csv_bytes = output.getvalue().encode("utf-8")
        output.close()

        bio = BytesIO(csv_bytes)
        bio.name = f"link_tokens_{user_id or 'all'}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.csv"
        bio.seek(0)
        await message.reply_document(InputFile(bio, filename=bio.name))

# --- Регистрация обработчиков ---
def register_handlers(dp: Dispatcher):
    dp.message.register(cmd_start, Command(commands=["start"]))
    dp.message.register(cmd_link, Command(commands=["link"]))
    dp.message.register(cmd_users, Command(commands=["users"]))
    dp.message.register(cmd_generate_code, Command(commands=["generate_code"]))
    dp.message.register(cmd_export_codes, Command(commands=["export_codes"]))
    dp.message.register(cmd_run_import_now, Command(commands=["run_import_now"]))

    # callback handlers
    dp.callback_query.register(callback_users_page, lambda c: c.data and c.data.startswith("users_page:"))
    dp.callback_query.register(callback_view_user, lambda c: c.data and c.data.startswith("view_user:"))
    dp.callback_query.register(callback_generate_code, lambda c: c.data and c.data.startswith("gen_code:"))
    dp.callback_query.register(callback_send_code, lambda c: c.data and c.data.startswith("send_code:"))
    dp.callback_query.register(callback_revoke_code, lambda c: c.data and c.data.startswith("revoke_code:"))
    # noop handler to avoid errors on "Закрыть"
    dp.callback_query.register(lambda c: c.answer(), lambda c: c.data == "noop")
