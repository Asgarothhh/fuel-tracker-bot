"""
Пошаговое наполнение локальной SQLite (in-memory) и снимки счётчиков по таблицам для отчёта.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from src.app.models import (
    Car,
    FuelCard,
    FuelOperation,
    LinkToken,
    Permission,
    Role,
    User,
)
from prototiping.db.memory import init_schema, make_memory_engine


def _counts(session) -> dict[str, int]:
    models = [Permission, Role, User, Car, FuelCard, FuelOperation, LinkToken]
    out: dict[str, int] = {}
    for Model in models:
        n = session.scalar(select(func.count()).select_from(Model))
        out[Model.__tablename__] = int(n or 0)
    return out


def build_db_evolution_markdown() -> str:
    engine = make_memory_engine()
    init_schema(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()

    snapshots: list[tuple[str, dict[str, int]]] = []

    try:
        snapshots.append(("Пустая схема (таблицы созданы)", _counts(session)))

        perm = Permission(name="admin:manage", description="demo")
        role = Role(role_name="admin", description="demo")
        role.permissions.append(perm)
        session.add_all([perm, role])
        session.flush()
        snapshots.append(("+ роли и права (admin:manage)", _counts(session)))

        user = User(
            full_name="Демо Пользователь",
            telegram_id=200_001_002,
            active=True,
            role_id=role.id,
            cars=[],
            cards=["EVO-CARD-1"],
            extra_ids={},
        )
        session.add(user)
        session.flush()
        snapshots.append(("+ пользователь с картой в JSON", _counts(session)))

        car = Car(plate="5678BB1", model="Demo", owners=[user.id])
        session.add(car)
        session.flush()
        fc = FuelCard(card_number="EVO-CARD-1", user_id=user.id, car_id=car.id, active=True)
        session.add(fc)
        session.flush()
        snapshots.append(("+ авто и привязанная топливная карта", _counts(session)))

        now = datetime.now(timezone.utc)
        op = FuelOperation(
            source="api",
            status="loaded_from_api",
            doc_number="EVO-API-1",
            date_time=now,
            presumed_user_id=user.id,
            car_from_api="5678BB1",
            api_data={"cardNumber": "EVO-CARD-1", "row": {"productName": "АИ-92"}},
        )
        session.add(op)
        session.flush()
        snapshots.append(("+ операция из API (ожидание подтверждения)", _counts(session)))

        op2 = FuelOperation(
            source="personal_receipt",
            status="new",
            doc_number="EVO-OCR-1",
            date_time=now,
            presumed_user_id=user.id,
            ocr_data={"quantity": 25.0, "raw_text": "эволюция БД"},
        )
        session.add(op2)
        session.flush()
        snapshots.append(("+ личная заправка (OCR-ветка)", _counts(session)))

        lt = LinkToken(
            user_id=user.id,
            code_hash="a" * 64,
            expires_at=now + timedelta(days=1),
            status="new",
        )
        session.add(lt)
        session.commit()
        snapshots.append(("+ токен привязки / финальное состояние", _counts(session)))

        tables = sorted({k for _, snap in snapshots for k in snap.keys()})
        header = "| Шаг | " + " | ".join(tables) + " |"
        sep = "|-----|" + "|".join(["---"] * len(tables)) + "|"
        rows_md = [header, sep]
        for title, snap in snapshots:
            cells = [str(snap.get(t, 0)) for t in tables]
            rows_md.append("| " + title + " | " + " | ".join(cells) + " |")

        detail_lines = ["### Детализация шагов\n"]
        for title, snap in snapshots:
            detail_lines.append(f"#### {title}\n")
            detail_lines.append("```json\n" + json.dumps(snap, ensure_ascii=False, indent=2) + "\n```\n")

        return (
            "Динамика числа строк по основным таблицам (одна сессия SQLite in-memory, "
            "последовательные изменения как при типичном сценарии использования бота).\n\n"
            + "\n".join(rows_md)
            + "\n\n"
            + "\n".join(detail_lines)
        )
    finally:
        session.close()
        engine.dispose()
