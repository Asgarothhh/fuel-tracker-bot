"""
Общая логика импорта операций из JSON API (без отправки в Telegram).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import cast, String

from src.app.belorusneft_api import parse_operations
from src.app.models import FuelOperation, FuelCard, User, Car
from src.app.plate_util import normalize_plate

logger = logging.getLogger(__name__)

API_TZ_OFFSET_HOURS = 3
MAX_PERSON_LOOKUP_ATTEMPTS = 8


def api_local_yesterday_datetime() -> datetime:
    """Календарный «вчера» в зоне UTC+3 (как в ТЗ для Belorusneft)."""
    now_utc = datetime.now(timezone.utc)
    local = now_utc + timedelta(hours=API_TZ_OFFSET_HOURS)
    y = local.date() - timedelta(days=1)
    return datetime.combine(y, datetime.min.time())


def parse_api_datetime(dt_raw: Any) -> Optional[datetime]:
    if dt_raw is None:
        return None
    if isinstance(dt_raw, datetime):
        return dt_raw
    s = str(dt_raw).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except Exception:
        return None


def extract_flat_fields(parsed_op: Dict[str, Any]) -> Dict[str, Any]:
    """Поля для дедупликации и отображения из элемента parse_operations."""
    raw = parsed_op.get("raw") or {}
    inner_row = raw.get("row") if isinstance(raw, dict) else None
    inner = inner_row if isinstance(inner_row, dict) else {}

    def pick(*keys, default=""):
        for k in keys:
            v = parsed_op.get(k)
            if v is not None and v != "":
                return v
            if isinstance(inner, dict):
                v2 = inner.get(k)
                if v2 is not None and v2 != "":
                    return v2
        return default

    card = pick("card_number", "cardNumber", "card")
    doc = pick("doc_number", "docNumber", "doc")
    dt = parse_api_datetime(pick("date_time", "dateTimeIssue", default=None))
    azs = pick("azs", "azsNumber", "AzsCode")
    product = pick("product", "productName")
    qty = pick("quantity", "productQuantity")
    car_raw = pick("car_num", "carNum", "car")

    card_s = str(card).strip() if card is not None else ""
    doc_s = str(doc).strip() if doc is not None else ""
    azs_s = str(azs).strip() if azs is not None else ""
    product_s = str(product).strip() if product is not None else ""
    qty_s = str(qty).strip() if qty is not None else ""

    return {
        "card": card_s,
        "doc": doc_s,
        "date_time": dt,
        "azs": azs_s,
        "product": product_s,
        "quantity": qty_s,
        "car_raw": str(car_raw).strip() if car_raw is not None else "",
    }


def _stored_api_vals(op: FuelOperation) -> Tuple[str, str, str, str]:
    """Извлекает карту/АЗС/продукт/кол-во из сохранённого api_data (в т.ч. cardList+issueRows)."""
    d = op.api_data or {}
    if not isinstance(d, dict):
        return ("", "", "", "")
    row = d.get("row") or {}
    card_o = d.get("card") or {}
    if not isinstance(row, dict):
        row = {}
    if not isinstance(card_o, dict):
        card_o = {}
    card = str(card_o.get("cardNumber") or d.get("cardNumber") or "").strip()
    azs = str(row.get("azsNumber") or row.get("AzsCode") or d.get("azsNumber") or "").strip()
    prod = str(row.get("productName") or d.get("productName") or "").strip()
    qty = str(row.get("productQuantity") or d.get("productQuantity") or "").strip()
    return card, azs, prod, qty


def is_duplicate_api_operation(db, flat: Dict[str, Any]) -> bool:
    """Составной ключ по ТЗ: карта, дата/время, чек, АЗС, вид топлива, количество."""
    q = db.query(FuelOperation).filter(FuelOperation.source == "api")
    if flat.get("date_time"):
        q = q.filter(FuelOperation.date_time == flat["date_time"])
    if flat.get("doc"):
        q = q.filter(FuelOperation.doc_number == flat["doc"])
    for op in q.all():
        c, a, p, qt = _stored_api_vals(op)
        if c == flat["card"] and a == flat["azs"] and p == flat["product"] and qt == flat["quantity"]:
            return True
    return False


@dataclass
class ImportBatch:
    new_count: int = 0
    notify_users: List[Tuple[int, int]] = field(default_factory=list)  # telegram_id, op_id
    notify_admins_ops: List[int] = field(default_factory=list)  # op_id без получателя в Telegram


def import_api_operations(
    db,
    json_payload: Dict[str, Any],
    *,
    dry_run: bool,
) -> ImportBatch:
    """
    Создаёт записи FuelOperation. Не делает commit.
    dry_run=True — только проверка парсера и дедупа, откат вызывает снаружи.
    """
    batch = ImportBatch()
    ops = parse_operations(json_payload)
    logger.info("[import] parse_operations count=%s dry_run=%s", len(ops), dry_run)

    for op in ops:
        flat = extract_flat_fields(op)
        if flat["date_time"] is None and not flat["doc"]:
            logger.warning("[import] skip row without date and doc: %s", op)
            continue

        if is_duplicate_api_operation(db, flat):
            logger.info("[import] duplicate skipped doc=%s dt=%s", flat["doc"], flat["date_time"])
            continue

        card_num = flat["card"] or None
        fuel_card = None
        if card_num:
            fuel_card = db.query(FuelCard).filter_by(card_number=card_num).first()
            if not fuel_card:
                fuel_card = FuelCard(card_number=card_num, active=True)
                db.add(fuel_card)
                db.flush()

        presumed_user = None
        if fuel_card and fuel_card.user_id:
            presumed_user = db.query(User).filter_by(id=fuel_card.user_id).first()
        elif card_num:
            try:
                presumed_user = (
                    db.query(User)
                    .filter(cast(User.cards, String).like(f"%{card_num}%"))
                    .first()
                )
            except Exception:
                presumed_user = None
            if presumed_user and fuel_card:
                fuel_card.user_id = presumed_user.id

        car_plate_norm = None
        if flat["car_raw"]:
            car_plate_norm = normalize_plate(flat["car_raw"])
            if car_plate_norm:
                car = db.query(Car).filter_by(plate=car_plate_norm).first()
                if not car:
                    car = Car(plate=car_plate_norm)
                    db.add(car)
                    db.flush()
                if presumed_user:
                    owners = list(car.owners or [])
                    if presumed_user.id not in owners:
                        owners.append(presumed_user.id)
                        car.owners = owners
                    user_cars = list(presumed_user.cars or [])
                    if car_plate_norm not in user_cars:
                        user_cars.append(car_plate_norm)
                        presumed_user.cars = user_cars

        new_op = FuelOperation(
            source="api",
            api_data=op.get("raw") or op,
            imported_at=datetime.now(timezone.utc),
            status="loaded_from_api",
        )
        if flat["doc"]:
            new_op.doc_number = flat["doc"]
        if flat["date_time"]:
            new_op.date_time = flat["date_time"]
        if presumed_user:
            new_op.presumed_user_id = presumed_user.id
        if car_plate_norm:
            new_op.car_from_api = car_plate_norm

        db.add(new_op)
        db.flush()
        batch.new_count += 1

        if presumed_user and getattr(presumed_user, "telegram_id", None):
            batch.notify_users.append((presumed_user.telegram_id, new_op.id))
        else:
            batch.notify_admins_ops.append(new_op.id)

    return batch
