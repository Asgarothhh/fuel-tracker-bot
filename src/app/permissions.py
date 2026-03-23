# src/app/permissions.py
from functools import wraps
from typing import Union
from aiogram import types
from src.app.db import get_db_session
from src.app.models import User, Role, Permission, role_permissions

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
