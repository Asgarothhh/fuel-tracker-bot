# Обратная совместимость: логика перенесена в пакет src.app.bot
from src.app.bot import register_handlers

__all__ = ["register_handlers"]
