"""Загрузка переменных: корень репозитория, затем prototiping/.env (имеет приоритет)."""
from __future__ import annotations

from dotenv import load_dotenv

from prototiping.lib.paths import PROTO_DIR, ROOT_DIR


def load_prototype_env() -> None:
    load_dotenv(ROOT_DIR / ".env", override=False)
    load_dotenv(PROTO_DIR / ".env", override=True)
