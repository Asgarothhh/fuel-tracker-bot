# src/app/tokens.py
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from src.app.config import CODE_LENGTH, CODE_TTL_HOURS, TOKEN_SALT
from src.app.models import LinkToken, User
from .db import get_db_session

def generate_code(length=CODE_LENGTH) -> str:
    return ''.join(secrets.choice("0123456789") for _ in range(length))

def hash_code(code: str, salt: str) -> str:
    h = hashlib.sha256()
    h.update((salt + code).encode('utf-8'))
    return h.hexdigest()

def create_bulk_codes(db, user_id: int, count: int, created_by: int):
    codes = []
    for _ in range(count):
        code = generate_code()
        token_hash = hash_code(code, TOKEN_SALT)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=CODE_TTL_HOURS)
        token = LinkToken(
            user_id=user_id,
            token_hash=token_hash,
            created_by=created_by,
            expires_at=expires_at
        )
        db.add(token)
        codes.append(code)
    db.flush()
    return codes

def verify_and_consume_code(db, code: str, telegram_id: int):
    token_hash = hash_code(code, TOKEN_SALT)
    token = db.query(LinkToken).filter_by(token_hash=token_hash, used=False).first()
    if not token:
        return False, "invalid_or_used"
    if token.expires_at < datetime.now(timezone.utc):
        return False, "expired"
    user = db.query(User).get(token.user_id)
    if user.telegram_id and user.telegram_id != telegram_id:
        return False, "already_linked_to_other"
    # consume
    token.used = True
    token.used_by = telegram_id
    token.used_at = datetime.now(timezone.utc)
    user.telegram_id = telegram_id
    db.add(user)
    db.add(token)
    db.flush()
    return True, user
