# src/app/tokens.py
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Tuple, Dict, Any, Optional

from src.app.config import CODE_LENGTH, CODE_TTL_HOURS, TOKEN_SALT
from src.app.models import LinkToken, User
from .db import get_db_session


def generate_code(length: int = CODE_LENGTH) -> str:
    return ''.join(secrets.choice("0123456789") for _ in range(length))


def hash_code(code: str, salt: str) -> str:
    h = hashlib.sha256()
    h.update((salt + code).encode("utf-8"))
    return h.hexdigest()


def _ensure_aware_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        # treat naive datetimes from DB as UTC
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def create_bulk_codes(db, user_id: int, count: int, created_by: int) -> list:
    """
    Создать несколько токенов в переданной сессии db и вернуть список plain-кодов.
    """
    codes = []
    now_utc = datetime.now(timezone.utc)
    for _ in range(count):
        code = generate_code()
        code_hash = hash_code(code, TOKEN_SALT)
        expires_at = now_utc + timedelta(hours=CODE_TTL_HOURS)
        token = LinkToken(
            user_id=user_id,
            code_hash=code_hash,
            created_by=created_by,
            created_at=now_utc,
            expires_at=expires_at,
            status="new"
        )
        db.add(token)
        codes.append(code)
    db.flush()
    return codes


def verify_and_consume_code(db, plain_code: str, telegram_id: int):
    """
    Проверить плейн-код, пометить токен как использованный, привязать telegram_id к пользователю
    и вернуть данные пользователя. Возвращает (True, {"user_id":..., "full_name":...}) или (False, "reason").
    """
    code_hash = hash_code(plain_code, TOKEN_SALT)

    # Берём строку с блокировкой, чтобы избежать race condition
    token = db.query(LinkToken).filter_by(code_hash=code_hash).with_for_update().first()
    if not token:
        return False, "invalid_or_used"

    # Если есть булево поле used или статус 'used' — отклоняем
    if getattr(token, "used", False) or getattr(token, "status", None) == "used":
        return False, "invalid_or_used"

    # Нормализуем expires_at и сравниваем с текущим UTC
    expires_at = _ensure_aware_utc(getattr(token, "expires_at", None))
    now_utc = datetime.now(timezone.utc)
    if expires_at and expires_at <= now_utc:
        token.status = "expired"
        db.commit()
        return False, "expired"

    # Привязка: помечаем токен как использованный
    token.status = "used"
    if hasattr(token, "used"):
        token.used = True
    token.used_at = now_utc
    token.telegram_id = telegram_id

    # --- ВАЖНО: обновляем запись пользователя, чтобы сохранить telegram_id в users ---
    user = db.query(User).filter_by(id=token.user_id).with_for_update().first()
    if user:
        user.telegram_id = telegram_id
        # при желании можно активировать пользователя:
        # user.active = True

    # Коммитим все изменения в одной транзакции
    db.commit()

    # Возвращаем минимальные данные (не ORM-объект)
    return True, {"user_id": token.user_id, "full_name": getattr(user, "full_name", None)}

