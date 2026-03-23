# Хранит экземпляр Bot для фоновых задач (планировщик), где нет текущего контекста aiogram.
_bot = None


def set_bot(bot):
    global _bot
    _bot = bot


def get_bot():
    return _bot
