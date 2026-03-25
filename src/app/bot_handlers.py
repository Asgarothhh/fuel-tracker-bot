# src/app.bot_handlers.py
import logging

logger = logging.getLogger(__name__)



# Оставляем регистрацию хэндлеров
from src.app.bot import register_handlers
__all__ = ["register_handlers"]