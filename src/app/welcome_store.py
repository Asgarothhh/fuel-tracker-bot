"""Один раз на Telegram ID: показ приветствия с картинкой при первом /start."""

from __future__ import annotations

import json
from pathlib import Path

_STORE = Path(__file__).resolve().parent.parent.parent / "exports" / "welcome_shown.json"


def was_welcome_shown(telegram_id: int) -> bool:
    if not _STORE.exists():
        return False
    try:
        data = json.loads(_STORE.read_text(encoding="utf-8"))
        return int(telegram_id) in [int(x) for x in data.get("ids", [])]
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False


def mark_welcome_shown(telegram_id: int) -> None:
    _STORE.parent.mkdir(parents=True, exist_ok=True)
    ids: list[int] = []
    if _STORE.exists():
        try:
            raw = json.loads(_STORE.read_text(encoding="utf-8"))
            ids = [int(x) for x in raw.get("ids", [])]
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            ids = []
    tid = int(telegram_id)
    if tid not in ids:
        ids.append(tid)
    _STORE.write_text(json.dumps({"ids": ids}, ensure_ascii=False), encoding="utf-8")
