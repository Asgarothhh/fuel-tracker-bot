# src/app/permissions.py
from functools import wraps
from typing import Union
from aiogram import types
from src.app.db import get_db_session
from src.app.models import User, Role, Permission, role_permissions
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable

def user_has_permission(db, telegram_id: int, permission_name: str) -> bool:
    """
    Проверяет наличие права у пользователя по telegram_id.
    Выполняет все запросы внутри переданной сессии db и возвращает булево значение.
    """
    # Получаем id пользователя и его роль (без загрузки ORM-объекта User целиком)
    row = db.query(User.id, User.role_id).filter(User.telegram_id == telegram_id).first()
    if not row:
        return False
    _, role_id = row
    if not role_id:
        return False

    # Проверяем наличие permission через связующую таблицу role_permissions
    perm = (
        db.query(Permission.id)
          .join(role_permissions, role_permissions.c.permission_id == Permission.id)
          .join(Role, role_permissions.c.role_id == Role.id)
          .filter(Role.id == role_id, Permission.name == permission_name)
          .first()
    )
    return bool(perm)


class ActiveUserMiddleware(BaseMiddleware):
    """
    Глобальный фильтр: если пользователь привязан к Telegram,
    но в базе active=False, бот перестает его обслуживать.
    """

    async def __call__(
            self,
            handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
            event: Message | CallbackQuery,
            data: Dict[str, Any]
    ) -> Any:
        user_tg_id = event.from_user.id
        state = data.get("state")

        # 1. ПОЛНОЕ ИСКЛЮЧЕНИЕ ДЛЯ РЕГИСТРАЦИИ И АКТИВАЦИИ
        current_state = await state.get_state() if state else None

        # Проверяем, не вводит ли пользователь команду активации
        is_command = False
        if isinstance(event, Message) and event.text:
            # Разрешаем /start и /link проходить сквозь блок деактивации
            if event.text.startswith('/start') or event.text.startswith('/link'):
                is_command = True

        # Если в процессе регистрации ИЛИ вводит команду — пропускаем к хендлерам
        if is_command or (current_state and current_state.startswith("RegistrationStates:")):
            return await handler(event, data)

        # 2. ОБЫЧНАЯ ПРОВЕРКА БАЗЫ
        with get_db_session() as db:
            user = db.query(User).filter(User.telegram_id == user_tg_id).first()

            # Если юзер есть, но не активен — стоп (кроме случаев выше)
            if user and not user.active:
                if isinstance(event, Message):
                    await event.answer("❌ Ваш аккаунт ожидает активации. Введите код: `/link ваш_код`",
                                       parse_mode="Markdown")
                return

        return await handler(event, data)


def require_permission(permission_name: str):
    """
    Проверка прав для Message и CallbackQuery.
    """
    def decorator(handler):
        @wraps(handler)
        async def wrapper(event: Union[types.Message, types.CallbackQuery], *args, **kwargs):
            user_tg_id = event.from_user.id

            async def deny(text: str):
                if isinstance(event, types.CallbackQuery):
                    await event.answer(text, show_alert=True)
                else:
                    await event.reply(text)

            with get_db_session() as db:
                try:
                    if not user_has_permission(db, user_tg_id, permission_name):
                        await deny("У вас нет прав для выполнения этой команды.")
                        return
                except Exception:
                    print(f"Permission check error for tg_id={user_tg_id}, perm={permission_name}")
                    await deny("Ошибка проверки прав. Обратитесь к администратору.")
                    return

            return await handler(event, *args, **kwargs)
        return wrapper
    return decorator
