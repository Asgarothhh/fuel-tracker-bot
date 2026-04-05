"""
Импорт операций из Belorusneft API — та же последовательность шагов, что cmd_run_import_now
в bot/handlers/admin_import.py (без отправки в Telegram).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy import cast, String

from src.app.belorusneft_api import fetch_operational_raw, parse_operations
from src.app.models import FuelOperation, User, FuelCard, Car

logger = logging.getLogger(__name__)


def run_api_import_sync(db) -> Dict[str, Any]:
    """
    Загрузка за «вчера» (как в боте), запись в БД, commit внутри вызывающего кода.
    Возвращает dict: ok, new_count, error (optional), http_status (optional), debug_files.
    """
    date = datetime.now() - timedelta(days=1)
    new_count = 0
    debug_files: List[str] = []

    try:
        raw = fetch_operational_raw(date)
        status = raw.get("status")
        json_payload = raw.get("json")
        debug_files = list(raw.get("debug_files") or [])

        if status != 200:
            return {
                "ok": False,
                "new_count": 0,
                "error": f"HTTP {status}",
                "http_status": status,
                "debug_files": debug_files,
            }

        if not json_payload:
            return {
                "ok": False,
                "new_count": 0,
                "error": "Нет JSON в ответе",
                "debug_files": debug_files,
            }

        ops = parse_operations(json_payload)
        if not ops:
            return {"ok": True, "new_count": 0, "message": "В ответе 0 операций.", "debug_files": debug_files}

        for op in ops:
            op_row = op.get("row") if isinstance(op.get("row"), dict) else {}
            op_card = op.get("card") if isinstance(op.get("card"), dict) else {}

            dt_raw = op.get("date_time") or op.get("dateTimeIssue") or op_row.get("dateTimeIssue")
            dt_obj = None
            if dt_raw:
                try:
                    dt_obj = datetime.fromisoformat(str(dt_raw).replace("Z", "+00:00"))
                except Exception:
                    pass

            doc_raw = op.get("doc_number") or op.get("docNumber") or op_row.get("docNumber")
            doc = str(doc_raw).strip() if doc_raw is not None else None

            driver_name = op.get("driverName") or op.get("driver_name") or op_row.get("driverName")
            card_num = op.get("cardNumber") or op.get("card_number") or op_card.get("cardNumber")
            if not card_num and isinstance(op.get("card"), (str, int)):
                card_num = op.get("card")
            if card_num:
                card_num = str(card_num).strip()

            car_plate = op.get("carNum") or op.get("car_num") or op.get("car") or op_row.get("carNum")
            car_plate_norm = str(car_plate).strip().upper() if car_plate else None

            presumed_user = None
            if driver_name:
                drv_clean = str(driver_name).strip()
                presumed_user = db.query(User).filter(User.full_name.ilike(drv_clean)).first()
                if not presumed_user:
                    presumed_user = User(full_name=drv_clean, active=True)
                    db.add(presumed_user)
                    db.flush()

            if not presumed_user and card_num:
                presumed_user = db.query(User).filter(cast(User.cards, String).like(f"%{card_num}%")).first()

            if card_num:
                fuel_card = db.query(FuelCard).filter_by(card_number=card_num).first()
                if not fuel_card:
                    fuel_card = FuelCard(card_number=card_num, active=True)
                    db.add(fuel_card)
                    db.flush()
                if presumed_user:
                    fuel_card.user_id = presumed_user.id
                    u_cards = list(presumed_user.cards or [])
                    if card_num not in u_cards:
                        u_cards.append(card_num)
                        presumed_user.cards = u_cards

            if car_plate_norm:
                car_obj = db.query(Car).filter_by(plate=car_plate_norm).first()
                if not car_obj:
                    car_obj = Car(plate=car_plate_norm)
                    db.add(car_obj)
                    db.flush()
                if presumed_user:
                    owners = list(car_obj.owners or [])
                    if presumed_user.id not in owners:
                        owners.append(presumed_user.id)
                        car_obj.owners = owners
                    u_cars = list(presumed_user.cars or [])
                    if car_plate_norm not in u_cars:
                        u_cars.append(car_plate_norm)
                        presumed_user.cars = u_cars

            filters = [FuelOperation.source == "api"]
            if doc:
                filters.append(FuelOperation.doc_number == doc)
            if dt_obj:
                filters.append(FuelOperation.date_time == dt_obj)
            if db.query(FuelOperation).filter(*filters).first():
                continue

            new_op = FuelOperation(
                source="api",
                api_data=op.get("raw") or op,
                imported_at=datetime.now(timezone.utc),
                status="loaded",
            )
            if doc:
                new_op.doc_number = doc
            if dt_obj:
                new_op.date_time = dt_obj
            if presumed_user:
                new_op.presumed_user_id = presumed_user.id
            if car_plate_norm:
                new_op.car_from_api = car_plate_norm

            db.add(new_op)
            db.flush()
            new_count += 1

        return {
            "ok": True,
            "new_count": new_count,
            "message": f"Импорт завершён. Новых заправок: {new_count}",
            "debug_files": debug_files,
        }

    except Exception as e:
        logger.exception("run_api_import_sync")
        return {"ok": False, "new_count": 0, "error": str(e), "debug_files": debug_files}
