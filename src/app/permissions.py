# src/app/permissions.py
from functools import wraps
from typing import Tuple, Optional
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
    Декоратор для проверки прав пользователя по telegram_id и данным в БД.
    Использование: @require_permission("admin:manage")
    """
    def decorator(handler):
        @wraps(handler)
        async def wrapper(message: types.Message, *args, **kwargs):
            user_tg_id = message.from_user.id

            with get_db_session() as db:
                try:
                    if not user_has_permission(db, user_tg_id, permission_name):
                        await message.reply("У вас нет прав для выполнения этой команды.")
                        return
                except Exception:
                    # В случае ошибки при проверке прав — не давать подробностей, но логировать в консоль
                    # (логирование можно заменить на более продвинутую систему логов)
                    print(f"Permission check error for tg_id={user_tg_id}, perm={permission_name}")
                    await message.reply("Ошибка проверки прав. Обратитесь к администратору.")
                    return

            return await handler(message, *args, **kwargs)
        return wrapper
    return decorator
