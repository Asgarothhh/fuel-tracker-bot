import csv
from datetime import datetime, timezone, timedelta
from io import StringIO, BytesIO

from aiogram import types
from aiogram.filters import Command
from aiogram.types import InputFile, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.exc import IntegrityError
from src.app.bot.keyboards import get_admin_user_view_kb
from src.app.config import TOKEN_SALT, CODE_TTL_HOURS
from src.app.db import get_db_session
from src.app.models import LinkToken, User
from src.app.permissions import require_permission
from src.app.tokens import generate_code, hash_code
from src.app.bot.utils import extract_args, PENDING_PLAINS

# Добавьте импорт Bot, если его нет
from aiogram import Bot


async def send_users_list(chat_id: int, bot: Bot, page: int):
    page_size = 10
    offset = (page - 1) * page_size

    with get_db_session() as db:
        total = db.query(User).count()
        rows = (
            db.query(User.id, User.full_name, User.telegram_id, User.active)
            .order_by(User.id.desc())  # <-- РЕШЕНИЕ ЗАДАЧИ 3 (Новые сверху)
            .offset(offset)
            .limit(page_size)
            .all()
        )

    if not rows:
        await bot.send_message(chat_id, "Пользователи не найдены.")
        return

    # Отправляем карточку каждого пользователя
    for row in rows:
        user_id, full_name, telegram_id, active = row
        tg = f"id:{telegram_id}" if telegram_id else "—"
        status = "Активен" if active else "Неактивен"
        text = f"{user_id}) {full_name} — {tg} — {status}"
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="Сгенерировать код", callback_data=f"gen_code:{user_id}"),
                    InlineKeyboardButton(text="Просмотр", callback_data=f"view_user:{user_id}"),
                ]
            ]
        )
        await bot.send_message(chat_id, text, reply_markup=kb)

    # Пагинация
    pages = (total + page_size - 1) // page_size
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"users_page:{page - 1}"))
    if page < pages:
        nav_buttons.append(InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"users_page:{page + 1}"))

    if nav_buttons:
        await bot.send_message(
            chat_id,
            f"Страница {page}/{pages}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[nav_buttons]),
        )


@require_permission("admin:manage")
async def cmd_users(message: types.Message):
    args = extract_args(message)
    page = 1
    if args:
        try:
            page = max(1, int(args.split()[0]))
        except ValueError:
            pass

    # Вызываем нашу новую функцию
    await send_users_list(message.chat.id, message.bot, page)


@require_permission("admin:manage")
async def callback_users_page(call: types.CallbackQuery):
    page = int(call.data.split(":", 1)[1])

    # Удаляем старое сообщение с кнопками пагинации, чтобы не засорять чат
    await call.message.delete()

    # Вызываем нашу новую функцию (РЕШЕНИЕ ЗАДАЧИ 1)
    await send_users_list(call.message.chat.id, call.bot, page)
    await call.answer()


@require_permission("admin:manage")
async def cmd_generate_code(message: types.Message):
    args = extract_args(message)
    if not args:
        await message.reply("Использование: /generate_code <user_id>")
        return
    try:
        user_id = int(args.split()[0])
    except ValueError:
        await message.reply("Неверный user_id. Пример: /generate_code 42")
        return

    admin_id = message.from_user.id
    with get_db_session() as db:
        user_row = db.query(User.id, User.full_name).filter_by(id=user_id).first()
        if not user_row:
            await message.reply(f"Пользователь id={user_id} не найден.")
            return
        _, full_name = user_row

        code_plain = generate_code()
        code_hash = hash_code(code_plain, TOKEN_SALT)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=CODE_TTL_HOURS)

        token = LinkToken(
            user_id=user_id,
            code_hash=code_hash,
            created_by=admin_id,
            created_at=datetime.now(timezone.utc),
            expires_at=expires_at,
        )
        try:
            db.add(token)
            db.flush()
            token_id = token.id
            db.commit()
        except IntegrityError:
            db.rollback()
            await message.reply("Не удалось сгенерировать код. Попробуйте снова.")
            return

    PENDING_PLAINS[token_id] = (code_plain, datetime.now(timezone.utc) + timedelta(minutes=10))

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Отправить пользователю", callback_data=f"send_code:{token_id}")],
            [InlineKeyboardButton(text="Отозвать код", callback_data=f"revoke_code:{token_id}")],
        ]
    )
    await message.reply(
        f"Код для {full_name} (id={user_id}):\n\n{code_plain}\n\nПоказывается один раз.",
        reply_markup=kb,
    )


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
        writer.writerow(
            [
                "token_id",
                "user_id",
                "user_full_name",
                "code_hash",
                "created_by",
                "created_at",
                "expires_at",
                "status",
                "telegram_id",
                "used_at",
                "note",
            ]
        )
        for t in tokens:
            user = db.query(User).filter_by(id=t.user_id).first() if t.user_id else None
            writer.writerow(
                [
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
                    t.note or "",
                ]
            )
        csv_bytes = output.getvalue().encode("utf-8")
        output.close()

        bio = BytesIO(csv_bytes)
        bio.name = f"link_tokens_{user_id or 'all'}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.csv"
        bio.seek(0)
        await message.reply_document(InputFile(bio, filename=bio.name))





@require_permission("admin:manage")
async def callback_view_user(call: types.CallbackQuery):
    user_id = int(call.data.split(":", 1)[1])
    with get_db_session() as db:
        row = (
            db.query(User.id, User.full_name, User.telegram_id, User.cards, User.cars, User.active)
            .filter(User.id == user_id)
            .first()
        )
    if not row:
        await call.message.answer("Пользователь не найден.")
        await call.answer()
        return
    uid, full_name, telegram_id, cards, cars, active = row
    tg = f"id:{telegram_id}" if telegram_id else "—"
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

    # Используем новую функцию из keyboards.py
    kb = get_admin_user_view_kb(uid, active)
    await call.message.answer(text, reply_markup=kb)
    await call.answer()


@require_permission("admin:manage")
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
        token = LinkToken(
            user_id=uid,
            code_hash=code_hash,
            created_by=admin_id,
            created_at=datetime.now(timezone.utc),
            expires_at=expires_at,
        )
        try:
            db.add(token)
            db.flush()
            token_id = token.id
            db.commit()
        except IntegrityError:
            db.rollback()
            await call.message.answer("Не удалось сгенерировать код.")
            await call.answer()
            return

    PENDING_PLAINS[token_id] = (code_plain, datetime.now(timezone.utc) + timedelta(minutes=10))

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Отправить пользователю", callback_data=f"send_code:{token_id}")],
            [InlineKeyboardButton(text="Отозвать код", callback_data=f"revoke_code:{token_id}")],
        ]
    )
    await call.message.answer(
        f"Код для {full_name} (id={uid}):\n\n{code_plain}\n\nПоказывается один раз.",
        reply_markup=kb,
    )
    await call.answer()


@require_permission("admin:manage")
async def callback_send_code(call: types.CallbackQuery):
    token_id = int(call.data.split(":", 1)[1])

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
                await call.bot.send_message(
                    tg_id,
                    f"Код для привязки аккаунта: {plain_code}\nВведите в боте: /link {plain_code}",
                )
                await call.message.answer("Код отправлен пользователю.")
            except Exception:
                await call.message.answer(
                    "Не удалось отправить (возможно, пользователь не нажимал /start у бота)."
                )
        else:
            await call.message.answer("Время показа кода истекло. Сгенерируйте новый.")
    else:
        if user_row:
            await call.message.answer(f"У {user_row[1]} нет привязанного Telegram — передайте код вручную.")
        else:
            await call.message.answer("Пользователь не найден.")
    await call.answer()


@require_permission("admin:manage")
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


@require_permission("admin:manage")
async def callback_toggle_active(call: types.CallbackQuery):
    user_id = int(call.data.split(":", 1)[1])

    with get_db_session() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            await call.answer("Пользователь не найден.", show_alert=True)
            return

        # Меняем статус на противоположный (Soft Delete / Restore)
        user.active = not user.active
        new_status = user.active
        db.commit()

        # Сразу получаем обновленные данные для карточки
        row = (
            db.query(User.id, User.full_name, User.telegram_id, User.cards, User.cars, User.active)
            .filter(User.id == user_id)
            .first()
        )

    # Обновляем сообщение с новой информацией и кнопкой
    uid, full_name, telegram_id, cards, cars, active = row
    tg = f"id:{telegram_id}" if telegram_id else "—"
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

    kb = get_admin_user_view_kb(uid, active)
    await call.message.edit_text(text, reply_markup=kb)

    status_msg = "восстановлен" if new_status else "заблокирован"
    await call.answer(f"Пользователь {status_msg}!", show_alert=False)


def register_admin_user_handlers(dp):
    dp.message.register(cmd_users, Command(commands=["users"]))
    dp.message.register(cmd_generate_code, Command(commands=["generate_code"]))
    dp.message.register(cmd_export_codes, Command(commands=["export_codes"]))
    dp.callback_query.register(callback_toggle_active, lambda c: c.data and c.data.startswith("toggle_active:"))
    dp.callback_query.register(callback_users_page, lambda c: c.data and c.data.startswith("users_page:"))
    dp.callback_query.register(callback_view_user, lambda c: c.data and c.data.startswith("view_user:"))
    dp.callback_query.register(callback_generate_code, lambda c: c.data and c.data.startswith("gen_code:"))
    dp.callback_query.register(callback_send_code, lambda c: c.data and c.data.startswith("send_code:"))
    dp.callback_query.register(callback_revoke_code, lambda c: c.data and c.data.startswith("revoke_code:"))
    dp.callback_query.register(lambda c: c.answer(), lambda c: c.data == "noop")
