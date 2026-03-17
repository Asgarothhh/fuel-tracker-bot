# src/app/jobs.py
from datetime import datetime, timedelta, timezone
import logging
from src.app.belorusneft_api import fetch_operational_raw, parse_operations
from src.app.db import get_db_session
from src.app.models import FuelOperation, Schedule
from sqlalchemy.exc import SQLAlchemyError

def run_import_job(schedule_name: str, dry_run: bool = False):
    """
    Запускается планировщиком. Берёт расписание по name (для логики/last_run),
    запрашивает данные за предыдущий календарный день (по UTC+3 -> учитываем смещение),
    парсит, дедуплицирует и сохраняет новые операции.
    """
    log = logging.getLogger(__name__)
    try:
        # определяем дату предыдущего дня в локальном API времени (UTC+3)
        now_utc = datetime.now(timezone.utc)
        # API docs say service timezone UTC+3; чтобы получить "вчера" по API, смещаем:
        api_tz_offset = 3
        local_now = now_utc + timedelta(hours=api_tz_offset)
        target_date_local = (local_now - timedelta(days=1)).date()
        # формируем datetime для передачи в fetch_operational_raw (функция ожидает datetime)
        target_dt = datetime.combine(target_date_local, datetime.min.time())
        # вызываем API
        raw = fetch_operational_raw(target_dt)
        status = raw.get("status")
        if status != 200:
            log.error("Import job %s: API returned status %s", schedule_name, status)
            return

        payload = raw.get("json")
        if not payload:
            log.info("Import job %s: no JSON payload", schedule_name)
            return

        ops = parse_operations(payload)
        log.info("Import job %s: parsed %d operations", schedule_name, len(ops))

        if dry_run:
            log.info("Dry-run enabled: not saving operations")
            return

        new_count = 0
        with get_db_session() as db:
            for op in ops:
                # нормализация
                doc = op.get("doc_number")
                if doc is not None:
                    doc = str(doc)
                dt_raw = op.get("date_time")
                dt_obj = None
                if dt_raw:
                    try:
                        dt_obj = datetime.fromisoformat(dt_raw)
                    except Exception:
                        dt_obj = None

                # дедупликация: сначала по doc+date, затем по card+azs+quantity
                filters = [FuelOperation.source == "api"]
                if doc:
                    filters.append(FuelOperation.doc_number == doc)
                if dt_obj and hasattr(FuelOperation, "date_time"):
                    filters.append(FuelOperation.date_time == dt_obj)

                exists = db.query(FuelOperation).filter(*filters).first()
                if exists:
                    continue

                # fallback: более мягкая проверка (card+azs+quantity)
                card = op.get("card_number")
                azs = op.get("azs")
                qty = op.get("quantity")
                if card and azs and qty:
                    exists2 = db.query(FuelOperation).filter(
                        FuelOperation.source == "api",
                        FuelOperation.api_data.contains({"cardNumber": card})  # если JSONB
                    ).first()
                    if exists2:
                        continue

                # сохраняем
                new_op = FuelOperation(
                    source="api",
                    api_data=op.get("raw"),
                    imported_at=datetime.now(timezone.utc),
                    status="loaded"
                )
                if hasattr(FuelOperation, "doc_number") and doc:
                    setattr(new_op, "doc_number", doc)
                if hasattr(FuelOperation, "date_time") and dt_obj:
                    setattr(new_op, "date_time", dt_obj)
                db.add(new_op)
                new_count += 1
            db.commit()

        log.info("Import job %s: new operations saved: %d", schedule_name, new_count)

        # обновляем last_run в schedules
        with get_db_session() as db:
            sched = db.query(Schedule).filter_by(name=schedule_name).first()
            if sched:
                sched.last_run = datetime.now(timezone.utc)
                db.commit()

    except SQLAlchemyError as e:
        log.exception("DB error in import job %s: %s", schedule_name, e)
    except Exception as e:
        log.exception("Unexpected error in import job %s: %s", schedule_name, e)
