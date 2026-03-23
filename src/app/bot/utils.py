from aiogram import types

# Plain-коды link-токенов (показ один раз), token_id -> (plain, expires_at)
PENDING_PLAINS: dict = {}


def extract_args(message: types.Message) -> str:
    text = message.text or ""
    parts = text.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""
