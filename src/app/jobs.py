# src/app/jobs.py
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.exc import SQLAlchemyError
from src.app.belorusneft_api import fetch_operational_raw, parse_operations
from src.app.db import get_db_session
from src.app.models import FuelOperation, Schedule, User, FuelCard, Car
from src.app.bot_handlers import send_operation_to_user


async def run_import_job(schedule_name: str, dry_run: bool = False): # <-- Проверьте наличие dry_run=False    log = logging.getLogger(__name__)
    try:
        # 1. Получаем данные из API (за вчера)
        now_utc = datetime.now(timezone.utc)
        api_tz_offset = 3
        local_now = now_utc + timedelta(hours=api_tz_offset)
        target_date_local = (local_now - timedelta(days=1)).date()
        target_dt = datetime.combine(target_date_local, datetime.min.time())

        raw = fetch_operational_raw(target_dt)
        operations = parse_operations(raw)

        new_count = 0
        with get_db_session() as db:
            for op_data in operations:
                # 2. Проверка на дубли (Дата + Чек)
                doc = str(op_data.get("doc_number") or "")
                dt_obj = op_data.get("date_time")

                exists = db.query(FuelOperation).filter(
                    FuelOperation.date_time == dt_obj,
                    FuelOperation.doc_number == doc
                ).first()

                if exists:
                    continue

                # 3. Создаем операцию
                new_op = FuelOperation(
                    source="api",
                    api_data=op_data.get("raw"),
                    date_time=dt_obj,
                    doc_number=doc,
                    status="awaiting_user_confirmation",
                    car_from_api=op_data.get("car_num")
                )

                # 4. Логика поиска предполагаемого пользователя
                found_user = None
                card_num = op_data.get("card_number")
                car_num = op_data.get("car_num")

                # Поиск по карте
                if card_num:
                    card_obj = db.query(FuelCard).filter_by(card_number=card_num).first()
                    if card_obj: found_user = db.query(User).filter_by(id=card_obj.user_id).first()

                # Поиск по госномеру авто (если по карте не нашли)
                if not found_user and car_num:
                    car_obj = db.query(Car).filter_by(plate=car_num).first()
                    if car_obj and car_obj.owners:
                        found_user = db.query(User).filter_by(id=car_obj.owners[0]).first()

                if found_user:
                    new_op.presumed_user_id = found_user.id

                db.add(new_op)
                db.flush()  # Получаем ID

                # 5. Сразу отправляем в Telegram
                if found_user and found_user.telegram_id:
                    await send_operation_to_user(found_user.telegram_id, new_op.id)

                new_count += 1

            # Обновляем время запуска
            sched = db.query(Schedule).filter_by(name=schedule_name).first()
            if sched: sched.last_run = now_utc
            db.commit()

        log.info(f"Job {schedule_name} finished. New ops: {new_count}")
    except Exception as e:
        log.exception(f"Error in job {schedule_name}: {e}")