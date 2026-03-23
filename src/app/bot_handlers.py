# src/app/bot_handlers.py
from src.app.bot.handlers.user import register_user_handlers
from src.app.bot.notifications import send_operation_to_user


def register_handlers(dp):
    register_user_handlers(dp)


__all__ = ["register_handlers", "send_operation_to_user"]
