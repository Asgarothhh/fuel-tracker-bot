# src/app/permissions.py
from functools import wraps
from src.app.db import get_db_session
from src.app.models import User

def user_has_permission(db, telegram_id: int, permission_name: str) -> bool:
    user = db.query(User).filter_by(telegram_id=telegram_id).first()
    if not user or not user.role:
        return False
    return any(p.name == permission_name for p in user.role.permissions)

def require_permission(permission_name: str):
    def decorator(handler):
        @wraps(handler)
        async def wrapper(message, *args, **kwargs):
            with get_db_session() as db:
                if not user_has_permission(db, message.from_user.id, permission_name):
                    await message.reply("У вас нет прав для выполнения этой команды.")
                    return
            return await handler(message, *args, **kwargs)
        return wrapper
    return decorator
