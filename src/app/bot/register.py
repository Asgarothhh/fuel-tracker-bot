from aiogram import Dispatcher
from src.app.permissions import ActiveUserMiddleware
from src.app.bot.handlers.user import register_user_handlers
from src.app.bot.handlers.admin_schedules import register_schedule_handlers
from src.app.bot.handlers.admin_users import register_admin_user_handlers
from src.app.bot.handlers.admin_import import register_admin_import_handlers


def register_handlers(dp: Dispatcher) -> None:
    """
    Порядок: сначала команды и колбэки, затем текстовые кнопки
    (чтобы /команды не перехватывались общими фильтрами).
    """
    dp.message.middleware(ActiveUserMiddleware())
    dp.callback_query.middleware(ActiveUserMiddleware())
    register_schedule_handlers(dp)
    register_admin_user_handlers(dp)
    register_admin_import_handlers(dp)
    register_user_handlers(dp)
