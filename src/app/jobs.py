# src/app/jobs.py
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy.exc import SQLAlchemyError
from src.app.belorusneft_api import fetch_operational_raw, parse_operations
from src.app.bot.handlers.user import send_operation_to_user
from src.app.db import get_db_session
from src.app.models import FuelOperation, User, FuelCard, Car, Schedule


async def run_import_job(schedule_name: str, dry_run: bool = False):
    log = logging.getLogger(__name__)
    new_count = 0
    try:
        # 1. Получаем данные (за вчера)
        now_utc = datetime.now(timezone.utc)
        api_tz_offset = 3
        local_now = now_utc + timedelta(hours=api_tz_offset)
        target_date_local = (local_now - timedelta(days=1)).date()
        target_dt = datetime.combine(target_date_local, datetime.min.time())

        raw = fetch_operational_raw(target_dt)
        operations = parse_operations(raw)

        with get_db_session() as db:
            for op_data in operations:
                doc = str(op_data.get("doc_number") or "")
                dt_obj = op_data.get("date_time")

                # Проверка на дубликаты
                exists = db.query(FuelOperation).filter_by(doc_number=doc, date_time=dt_obj).first()
                if exists:
                    continue

                driver_name = op_data.get("driver_name")
                card_num = op_data.get("card_number")
                car_num = op_data.get("car_num")

                # --- АВТОМАТИЧЕСКОЕ СОЗДАНИЕ СВЯЗЕЙ ---
                user_obj = None
                if driver_name:
                    user_obj = db.query(User).filter_by(full_name=driver_name).first()
                    if not user_obj:
                        user_obj = User(full_name=driver_name, active=True)
                        db.add(user_obj)
                        db.flush()  # Получаем user_obj.id

                if card_num:
                    card_obj = db.query(FuelCard).filter_by(card_number=card_num).first()
                    if not card_obj:
                        card_obj = FuelCard(card_number=card_num, user_id=user_obj.id if user_obj else None)
                        db.add(card_obj)
                    elif user_obj and not card_obj.user_id:
                        card_obj.user_id = user_obj.id

                if car_num:
                    car_obj = db.query(Car).filter_by(plate=car_num).first()
                    if not car_obj:
                        car_obj = Car(plate=car_num, owners=[user_obj.id] if user_obj else [])
                        db.add(car_obj)
                    elif user_obj:
                        owners = list(car_obj.owners or [])
                        if user_obj.id not in owners:
                            owners.append(user_obj.id)
                            car_obj.owners = owners

                # Создаем операцию
                new_op = FuelOperation(
                    source="api",
                    api_data=op_data.get("raw"),
                    doc_number=doc,
                    date_time=dt_obj,
                    car_from_api=car_num,
                    presumed_user_id=user_obj.id if user_obj else None,
                    status="pending",
                    imported_at=datetime.now(timezone.utc)
                )
                db.add(new_op)
                db.flush()

                # Уведомляем только если привязан Telegram
                if user_obj and user_obj.telegram_id:
                    try:
                        await send_operation_to_user(user_obj.telegram_id, new_op.id)
                    except Exception as e:
                        log.error(f"Уведомление не отправлено {user_obj.telegram_id}: {e}")

                new_count += 1

            # Обновляем расписание
            sched = db.query(Schedule).filter_by(name=schedule_name).first()
            if sched:
                sched.last_run = datetime.now(timezone.utc)

            db.commit()

        log.info(f"Импорт завершен. Добавлено: {new_count}")
        return new_count

    except Exception as e:
        log.exception(f"Критическая ошибка в run_import_job: {e}")
        return 0