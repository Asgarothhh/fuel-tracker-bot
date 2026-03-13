# src/app/bot_handlers.py
from aiogram import types, Dispatcher
from aiogram.types import InputFile
from aiogram.filters import Command
from io import StringIO, BytesIO
import csv
from datetime import datetime, timezone, timedelta

from src.app.config import ADMIN_TELEGRAM_ID, TOKEN_SALT, CODE_TTL_HOURS
from src.app.db import get_db_session
from src.app.tokens import verify_and_consume_code, create_bulk_codes, generate_code, hash_code
from src.app.permissions import require_permission
from src.app.models import LinkToken, User

# --- Вспомогательная функция для извлечения аргументов команды ---
def extract_args(message: types.Message) -> str:
    text = message.text or ""
    parts = text.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""

# --- Пользовательские обработчики ---

async def cmd_start(message: types.Message):
    await message.reply("Привет! Для привязки аккаунта используйте /link <код>.")

async def cmd_link(message: types.Message):
    args = extract_args(message)
    if not args:
        await message.reply("Введите код: /link <код>. Код вы получили от HR.")
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


# --- Админские команды ---

@require_permission("admin:manage")
async def cmd_generate_codes(message: types.Message):
    """
    Поддерживает два варианта:
    1) /generate_codes <user_id> <count>  -> генерирует count кодов и привязывает к user_id
    2) /generate_codes <count>           -> генерирует count кодов в пул (user_id = NULL)
    """
    args_list = extract_args(message).split()
    if not args_list:
        await message.reply("Использование: /generate_codes <user_id> <count> или /generate_codes <count> (создать пул).")
        return

    created_by = message.from_user.id

    # Вариант: только count -> создаём пул (unassigned)
    if len(args_list) == 1:
        try:
            count = int(args_list[0])
        except ValueError:
            await message.reply("Неверный параметр. Укажите число: /generate_codes <count>.")
            return

        codes = []
        with get_db_session() as db:
            for _ in range(count):
                code = generate_code()
                token_hash = hash_code(code, TOKEN_SALT)
                expires_at = datetime.now(timezone.utc) + timedelta(hours=CODE_TTL_HOURS)
                token = LinkToken(user_id=None, token_hash=token_hash, created_by=created_by, expires_at=expires_at)
                db.add(token)
                codes.append(code)
            db.flush()
        text = f"Сгенерировано {len(codes)} кодов в пул (unassigned).\nКоды:\n" + "\n".join(codes)
        await message.reply(text)
        return

    # Вариант: user_id и count
    if len(args_list) >= 2:
        try:
            user_id = int(args_list[0])
            count = int(args_list[1])
        except ValueError:
            await message.reply("Неверные параметры. Использование: /generate_codes <user_id> <count>")
            return

        with get_db_session() as db:
            target = db.query(User).filter_by(id=user_id).first()
            if not target:
                await message.reply(f"Пользователь с id={user_id} не найден.")
                return
            codes = create_bulk_codes(db, user_id=user_id, count=count, created_by=created_by)
            text = f"Сгенерировано {len(codes)} кодов для user_id={user_id}.\n\nКоды:\n" + "\n".join(codes)
            await message.reply(text)
            return

    await message.reply("Неверный формат команды. Использование: /generate_codes <user_id> <count> или /generate_codes <count>.")

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
            "created_at", "expires_at", "used", "used_by", "used_at"
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
                "yes" if t.used else "no",
                t.used_by or "",
                t.used_at.isoformat() if t.used_at else ""
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
    dp.message.register(cmd_generate_codes, Command(commands=["generate_codes"]))
    dp.message.register(cmd_export_codes, Command(commands=["export_codes"]))
