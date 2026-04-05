"""Загрузка переменных: корень репозитория, затем prototiping/.env (имеет приоритет)."""
from __future__ import annotations

from dotenv import load_dotenv

from prototiping.lib.paths import PROTO_DIR, ROOT_DIR


def load_prototype_env() -> None:
    """Подмешивает ``.env`` из корня репозитория, затем ``prototiping/.env`` (перекрывает).

    :returns: ``None``.

    Пример::

        from prototiping.lib.env import load_prototype_env
        load_prototype_env()
    """
    load_dotenv(ROOT_DIR / ".env", override=False)
    load_dotenv(PROTO_DIR / ".env", override=True)
