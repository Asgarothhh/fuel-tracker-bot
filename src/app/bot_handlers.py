# src/app/bot_handlers.py
from aiogram import types, Dispatcher
from aiogram.types import InputFile, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from io import StringIO, BytesIO
import csv
from datetime import datetime, timezone, timedelta
import logging
from src.app.config import TOKEN_SALT, CODE_TTL_HOURS
from src.app.tokens import verify_and_consume_code, generate_code, hash_code
from src.app.models import LinkToken, User, FuelOperation
from src.app.belorusneft_api import fetch_operational_raw, parse_operations
from src.app.db import get_db_session
from src.app.permissions import require_permission, user_has_permission
from sqlalchemy.exc import IntegrityError

# --- Вспомогательная функция для извлечения аргументов команды ---
def extract_args(message: types.Message) -> str:
    text = message.text or ""
    parts = text.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""

# --- Временное in-memory хранилище plain-кодов (очищается при рестарте) ---
# token_id -> (plain_code, expires_at)
PENDING_PLAINS = {}

# --- Пользовательские обработчики ---

async def cmd_start(message: types.Message):
    print("DEBUG: tg_id =", message.from_user.id, "username=", getattr(message.from_user, "username", None))

    kb_user = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="/link"), KeyboardButton(text="/myprofile")]],
        resize_keyboard=True
    )
    kb_admin = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="/users")],
                  [KeyboardButton(text="/generate_code")],
                  [KeyboardButton(text="/run_import_now")]],
        resize_keyboard=True
    )

    with get_db_session() as db:
        is_admin = user_has_permission(db, message.from_user.id, "admin:manage")

    if is_admin:
        await message.reply("Привет, админ.", reply_markup=kb_admin)
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
    args = extract_args(message)
    if not args:
        await message.reply("Введите код: /link <код>. Код вы получили от администратора.")
        return

    code = args.split()[0]
    with get_db_session() as db:
        ok, result = verify_and_consume_code(db, code, message.from_user.id)
        if not ok:
            reason = result
            user_row = None
        else:
            if isinstance(result, dict) and "user_id" in result:
                user_id = result["user_id"]
            elif hasattr(result, "user_id"):
                user_id = result.user_id
            else:
                user_id = None

            user_row = None
            if user_id:
                user_row = db.query(User.id, User.full_name, User.cards, User.cars).filter(User.id == user_id).first()

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

    if not user_row:
        await message.reply("Привязка выполнена, но не удалось получить данные пользователя.")
        return

    _, full_name, cards, cars = user_row
    cards_s = ", ".join(cards or []) or "—"
    cars_s = ", ".join(cars or []) or "—"
    info = f"Привязка выполнена.\nФИО: {full_name}\nКарты: {cards_s}\nАвто: {cars_s}"
    await message.reply(info)

# --- Админские команды и callbacks ---

@require_permission("admin:manage")
async def cmd_users(message: types.Message):
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
        total = db.query(User).count()
        rows = db.query(User.id, User.full_name, User.telegram_id, User.active).order_by(User.id).offset(offset).limit(page_size).all()

    if not rows:
        await message.reply("Пользователи не найдены.")
        return

    for row in rows:
        user_id, full_name, telegram_id, active = row
        tg = f"@{telegram_id}" if telegram_id else "—"
        status = "Активен" if active else "Неактивен"
        text = f"{user_id}) {full_name} — {tg} — {status}"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Сгенерировать код", callback_data=f"gen_code:{user_id}"),
                InlineKeyboardButton(text="Просмотр", callback_data=f"view_user:{user_id}")
            ]
        ])
        await message.answer(text, reply_markup=kb)

    pages = (total + page_size - 1) // page_size
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"users_page:{page-1}"))
    if page < pages:
        nav_buttons.append(InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"users_page:{page+1}"))
    if nav_buttons:
        await message.answer(f"Страница {page}/{pages}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[nav_buttons]))

@require_permission("admin:manage")
async def cmd_generate_code(message: types.Message):
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
        user_row = db.query(User.id, User.full_name).filter_by(id=user_id).first()
        if not user_row:
            await message.reply(f"Пользователь с id={user_id} не найден.")
            return
        _, full_name = user_row

        code_plain = generate_code()
        code_hash = hash_code(code_plain, TOKEN_SALT)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=CODE_TTL_HOURS)

        token = LinkToken(user_id=user_id, code_hash=code_hash, created_by=admin_id, created_at=datetime.now(timezone.utc), expires_at=expires_at)
        try:
            db.add(token)
            db.flush()
            token_id = token.id
            db.commit()
        except IntegrityError:
            db.rollback()
            await message.reply("Не удалось сгенерировать код (конфликт). Попробуйте ещё раз.")
            return

    PENDING_PLAINS[token_id] = (code_plain, datetime.now(timezone.utc) + timedelta(minutes=10))

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отправить пользователю", callback_data=f"send_code:{token_id}")],
        [InlineKeyboardButton(text="Отозвать код", callback_data=f"revoke_code:{token_id}")]
    ])
    await message.reply(f"Код для пользователя {full_name} (id={user_id}):\n\n{code_plain}\n\nКод показывается один раз.", reply_markup=kb)

async def callback_users_page(call: types.CallbackQuery):
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
        row = db.query(User.id, User.full_name, User.telegram_id, User.cards, User.cars, User.active).filter(User.id == user_id).first()
    if not row:
        await call.message.answer("Пользователь не найден.")
        await call.answer()
        return
    uid, full_name, telegram_id, cards, cars, active = row
    tg = f"@{telegram_id}" if telegram_id else "—"
    cards_s = ", ".join(cards or []) or "—"
    cars_s = ", ".join(cars or []) or "—"
    text = (
        f"ID: {uid}\n"
        f"ФИО: {full_name}\n"
        f"Telegram: {tg}\n"
        f"Карты: {cards_s}\n"
        f"Авто: {cars_s}\n"
        f"Активен: {'Да' if active else 'Нет'}\n"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Сгенерировать код", callback_data=f"gen_code:{uid}")],
        [InlineKeyboardButton(text="Закрыть", callback_data="noop")]
    ])
    await call.message.answer(text, reply_markup=kb)
    await call.answer()

async def callback_generate_code(call: types.CallbackQuery):
    user_id = int(call.data.split(":", 1)[1])
    admin_id = call.from_user.id
    with get_db_session() as db:
        row = db.query(User.id, User.full_name, User.telegram_id).filter(User.id == user_id).first()
        if not row:
            await call.message.answer("Пользователь не найден.")
            await call.answer()
            return
        uid, full_name, telegram_id = row

        code_plain = generate_code()
        code_hash = hash_code(code_plain, TOKEN_SALT)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=CODE_TTL_HOURS)
        token = LinkToken(user_id=uid, code_hash=code_hash, created_by=admin_id, created_at=datetime.now(timezone.utc), expires_at=expires_at)
        try:
            db.add(token)
            db.flush()
            token_id = token.id
            db.commit()
        except IntegrityError:
            db.rollback()
            await call.message.answer("Не удалось сгенерировать код (конфликт). Попробуйте ещё раз.")
            await call.answer()
            return

    PENDING_PLAINS[token_id] = (code_plain, datetime.now(timezone.utc) + timedelta(minutes=10))

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отправить пользователю", callback_data=f"send_code:{token_id}")],
        [InlineKeyboardButton(text="Отозвать код", callback_data=f"revoke_code:{token_id}")]
    ])
    await call.message.answer(f"Код для {full_name} (id={uid}):\n\n{code_plain}\n\nКод показывается один раз.", reply_markup=kb)
    await call.answer()

async def callback_send_code(call: types.CallbackQuery):
    token_id = int(call.data.split(":", 1)[1])

    # очистка просроченных
    entry = PENDING_PLAINS.get(token_id)
    if entry and entry[1] <= datetime.now(timezone.utc):
        del PENDING_PLAINS[token_id]
        entry = None
    plain_code = entry[0] if entry else None

    with get_db_session() as db:
        token = db.query(LinkToken).filter_by(id=token_id).first()
        if not token:
            await call.message.answer("Токен не найден.")
            await call.answer()
            return
        user_row = db.query(User.id, User.full_name, User.telegram_id).filter(User.id == token.user_id).first()

    if user_row and user_row[2]:
        tg_id = user_row[2]
        if plain_code:
            try:
                await call.bot.send_message(tg_id, f"Вам выдан код для привязки аккаунта: {plain_code}\nВведите его в боте: /link <код>")
                await call.message.answer("Код отправлен пользователю.")
            except Exception:
                await call.message.answer("Не удалось отправить сообщение пользователю (возможно, пользователь не начинал диалог с ботом).")
        else:
            await call.message.answer("Plain-код недоступен (время истекло). Передайте код вручную или сгенерируйте новый.")
    else:
        if user_row:
            await call.message.answer(f"У пользователя {user_row[1]} нет привязанного Telegram. Передайте ему код вручную.")
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
        token.status = "revoked"
        token.note = (token.note or "") + f"\nRevoked by admin {admin_id} at {datetime.now(timezone.utc).isoformat()}"
        db.commit()
    await call.message.answer("Код отозван.")
    await call.answer()

# --- Импорт операций ---

@require_permission("admin:manage")
async def cmd_run_import_now(message: types.Message):
    date = datetime.now() - timedelta(days=1)

    try:
        raw = fetch_operational_raw(date)
        status = raw.get("status")
        json_payload = raw.get("json")
        debug_files = raw.get("debug_files") or []

        if status != 200:
            await message.reply(f"Запрос вернул статус {status}. Debug файлы: {', '.join(debug_files)}")
            return

        if not json_payload:
            await message.reply(f"JSON не получен. Debug файлы: {', '.join(debug_files)}")
            return

        ops = parse_operations(json_payload)
        if not ops:
            await message.reply(f"В ответе найдено элементов: 0 (импорт временно отключён)")
            return

        new_count = 0
        with get_db_session() as db:
            for op in ops:
                # raw date string from API
                dt_raw = op.get("date_time")
                dt_obj = None
                if dt_raw:
                    # try parse ISO-like string to datetime
                    try:
                        dt_obj = datetime.fromisoformat(dt_raw)
                    except Exception:
                        # если не ISO, оставляем None (будем сохранять строку)
                        dt_obj = None

                # doc_number from API (may be int) -> normalize to string
                doc = op.get("doc_number")
                if doc is not None:
                    try:
                        doc = str(doc)
                    except Exception:
                        doc = None

                date_key = dt_obj or dt_raw

                # --- безопасная проверка дублей ---
                filters = [FuelOperation.source == "api"]
                used_filters = []

                if doc:
                    if hasattr(FuelOperation, "doc_number"):
                        # doc_number is string in DB, so compare as string
                        filters.append(FuelOperation.doc_number == doc)
                        used_filters.append("doc_number")
                    else:
                        # fallback: search inside api_data JSON/text
                        try:
                            filters.append(FuelOperation.api_data.contains({"docNumber": doc}))
                            used_filters.append("api_data.contains(docNumber)")
                        except Exception:
                            try:
                                # api_data may be JSON stored as text; use LIKE as last resort
                                filters.append(FuelOperation.api_data.like(f"%{doc}%"))
                                used_filters.append("api_data.like(doc)")
                            except Exception:
                                used_filters.append("no_doc_filter_available")

                if date_key and hasattr(FuelOperation, "date_time"):
                    # date_time is datetime column; ensure dt_obj is datetime for comparison
                    if isinstance(date_key, datetime):
                        filters.append(FuelOperation.date_time == date_key)
                        used_filters.append("date_time")
                    else:
                        # если date_key — строка, попытка сравнить со столбцом datetime может не сработать;
                        # пропускаем фильтр по дате в этом случае
                        used_filters.append("date_key_not_datetime; skipped date filter")

                logging.getLogger(__name__).debug("Checking existing FuelOperation with filters: %s", used_filters)
                exists = db.query(FuelOperation).filter(*filters).first()
                # --- конец проверки дублей ---

                if exists:
                    continue

                # создаём запись; заполняем doc_number/date_time если такие поля есть
                new_op = FuelOperation(
                    source="api",
                    api_data=op.get("raw"),
                    imported_at=datetime.now(timezone.utc),
                    status="loaded"
                )
                if hasattr(FuelOperation, "doc_number") and doc:
                    setattr(new_op, "doc_number", doc)
                if hasattr(FuelOperation, "date_time") and isinstance(date_key, datetime):
                    setattr(new_op, "date_time", date_key)

                db.add(new_op)
                new_count += 1
            db.commit()

        await message.reply(f"Импорт завершён. Новых операций: {new_count}")

    except Exception as e:
        import logging as _logging
        _logging.getLogger(__name__).exception("Error during run_import_now")
        await message.reply(f"Ошибка при выполнении запроса: {e}")



# --- Экспорт токенов ---

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
            "token_id", "user_id", "user_full_name", "code_hash", "created_by",
            "created_at", "expires_at", "status", "telegram_id", "used_at", "note"
        ])
        for t in tokens:
            user = db.query(User).filter_by(id=t.user_id).first() if t.user_id else None
            writer.writerow([
                t.id,
                t.user_id or "",
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
        output.close()

        bio = BytesIO(csv_bytes)
        bio.name = f"link_tokens_{user_id or 'all'}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.csv"
        bio.seek(0)
        await message.reply_document(InputFile(bio, filename=bio.name))

# --- Регистрация обработчиков ---
def register_handlers(dp: Dispatcher):
    dp.message.register(cmd_start, Command(commands=["start"]))
    dp.message.register(cmd_link, Command(commands=["link"]))
    dp.message.register(cmd_myprofile, Command(commands=["myprofile"]))
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
