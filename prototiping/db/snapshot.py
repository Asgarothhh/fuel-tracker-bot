"""
Сидирование демо-данных в SQLite in-memory и текстовый снимок для отчёта.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from src.app.models import (
    Car,
    FuelCard,
    FuelOperation,
    LinkToken,
    Permission,
    Role,
    User,
)
from prototiping.db.memory import init_schema, make_memory_engine, make_session_factory


def _json_safe(v: Any) -> Any:
    """Приводит значение к JSON-совместимому виду для превью в отчёте.

    :param v: Произвольное значение колонки.
    :returns: ``None``, скаляры, ``list``/``dict`` или ``str(v)``.
    """
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, (list, dict, str, int, float, bool)):
        return v
    return str(v)


def _row_dict(obj) -> dict:
    """Словарь ``имя_колонки → значение`` для ORM-объекта (через ``_json_safe``).

    :param obj: Экземпляр модели SQLAlchemy.
    :returns: Плоский dict по колонкам таблицы.
    """
    out = {}
    for col in obj.__table__.columns:
        out[col.key] = _json_safe(getattr(obj, col.key, None))
    return out


def seed_demo_database(session: Session) -> None:
    """Заполняет сессию демо-пользователем, авто, картой, операциями API/OCR, токеном.

    :param session: Сессия с уже созданной схемой.
    :type session: sqlalchemy.orm.Session

    :returns: ``None`` (делает ``commit``).
    """
    perm = Permission(name="admin:manage", description="demo")
    role = Role(role_name="admin", description="demo")
    role.permissions.append(perm)
    session.add_all([perm, role])
    session.flush()

    user = User(
        full_name="Петров П.П.",
        telegram_id=100_001_002,
        active=True,
        role_id=role.id,
        cars=["1234AA7"],
        cards=["DEMO-CARD-01"],
        extra_ids={},
    )
    session.add(user)
    session.flush()

    car = Car(plate="1234AA7", model="Lada", owners=[user.id])
    session.add(car)
    session.flush()

    fc = FuelCard(card_number="DEMO-CARD-01", user_id=user.id, car_id=car.id, active=True)
    session.add(fc)

    now = datetime.now(timezone.utc)
    op_api = FuelOperation(
        source="api",
        status="confirmed",
        doc_number="API-DEMO-001",
        date_time=now,
        presumed_user_id=user.id,
        confirmed_user_id=user.id,
        car_from_api="1234AA7",
        api_data={
            "cardNumber": "DEMO-CARD-01",
            "row": {
                "productName": "АИ-95",
                "productQuantity": 42.5,
                "azsNumber": "101",
            },
        },
        exported_to_excel=False,
    )
    op_ocr = FuelOperation(
        source="personal_receipt",
        status="new",
        doc_number="OCR-DEMO-001",
        date_time=now,
        presumed_user_id=user.id,
        ocr_data={
            "fuel_type": "ДТ",
            "quantity": 35.0,
            "doc_number": "OCR-DEMO-001",
            "raw_text": "Демо-строка OCR для отчёта (не из реального чека).",
            "image_hash": "demo_hash_report",
        },
    )
    session.add_all([op_api, op_ocr])

    lt = LinkToken(
        user_id=user.id,
        code_hash="0" * 64,
        expires_at=now,
        status="new",
    )
    session.add(lt)
    session.commit()


def build_db_snapshot_section_markdown() -> str:
    """Markdown: снимок строк основных таблиц после ``seed_demo_database``.

    Принимает: ничего.

    :returns: Текст для ``{{DB_SNAPSHOT}}``.
    :rtype: str
    """
    engine = make_memory_engine()
    init_schema(engine)
    factory = make_session_factory(engine)
    session = factory()
    try:
        seed_demo_database(session)
        lines: list[str] = []
        models_order = [Permission, Role, User, Car, FuelCard, FuelOperation, LinkToken]
        for Model in models_order:
            tn = Model.__tablename__
            rows = session.query(Model).all()
            n = len(rows)
            lines.append(f"### Таблица `{tn}`\n\n*Строк:* **{n}**\n")
            if not rows:
                lines.append("_нет записей_\n")
                continue
            preview = [_row_dict(r) for r in rows[:12]]
            lines.append("```json\n" + json.dumps(preview, ensure_ascii=False, indent=2) + "\n```\n")
        return "\n".join(lines)
    finally:
        session.close()
        engine.dispose()
