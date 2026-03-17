# scripts/migrate_old_ops.py
import json
import logging
from datetime import datetime, timezone
from sqlalchemy import cast, String
from src.app.db import get_db_session
from src.app.models import FuelOperation, FuelCard, Car, User

logging.basicConfig(level=logging.INFO, filename="migrate_old_ops.log", filemode="a",
                    format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("migrate_old_ops")

DRY_RUN = False   # <- переключите на False чтобы применить изменения
BATCH_SIZE = 100

def extract_field(api_data, *path):
    """Безопасно извлечь вложенное поле из api_data (словарь или JSON-строка)."""
    if not api_data:
        return None
    if isinstance(api_data, str):
        try:
            api = json.loads(api_data)
        except Exception:
            return None
    else:
        api = api_data
    cur = api
    for p in path:
        if cur is None:
            return None
        if isinstance(cur, dict):
            cur = cur.get(p)
        else:
            return None
    return cur

def find_user_by_card(db, card_number):
    """Найти пользователя по номеру карты.
    Сначала проверяем fuel_cards.user_id, затем ищем в users.cards (JSON) через приведение в текст.
    """
    if not card_number:
        return None

    # 1) fuel_cards table
    try:
        fc = db.query(FuelCard).filter_by(card_number=card_number).first()
    except Exception:
        fc = None

    if fc and getattr(fc, "user_id", None):
        return db.query(User).filter_by(id=fc.user_id).first()

    # 2) User.cards JSON contains — безопасно: приводим JSON к тексту и ищем подстроку
    try:
        # cast JSON -> text and use LIKE '%card_number%'
        user = db.query(User).filter(cast(User.cards, String).like(f"%{card_number}%")).first()
        if user:
            return user
    except Exception as e:
        logger.exception("find_user_by_card: error searching users.cards by LIKE: %s", e)

    return None

def ensure_fuel_card(db, card_number, presumed_user):
    if not card_number:
        return None
    fc = db.query(FuelCard).filter_by(card_number=card_number).first()
    if fc:
        # attach user if missing
        if presumed_user and not fc.user_id:
            if not DRY_RUN:
                fc.user_id = presumed_user.id
                db.flush()
            logger.info("Linked existing FuelCard %s -> user %s", card_number, presumed_user.id)
        return fc
    # create
    fc = FuelCard(card_number=card_number, active=True)
    if presumed_user:
        fc.user_id = presumed_user.id
    if not DRY_RUN:
        db.add(fc)
        db.flush()
    logger.info("Created FuelCard %s (user=%s)", card_number, getattr(presumed_user, "id", None))
    return fc

def ensure_car_and_link(db, car_plate, presumed_user):
    if not car_plate:
        return None
    plate = car_plate.strip().upper()
    car = db.query(Car).filter_by(plate=plate).first()
    if not car:
        car = Car(plate=plate)
        if not DRY_RUN:
            db.add(car)
            db.flush()
        logger.info("Created Car %s", plate)
    if presumed_user:
        owners = car.owners or []
        if presumed_user.id not in owners:
            owners.append(presumed_user.id)
            if not DRY_RUN:
                car.owners = owners
            logger.info("Added owner %s to Car %s", presumed_user.id, plate)
        # update user.cars
        user_cars = presumed_user.cars or []
        if plate not in user_cars:
            user_cars.append(plate)
            if not DRY_RUN:
                presumed_user.cars = user_cars
            logger.info("Added car %s to User %s", plate, presumed_user.id)
    return car

def process_batch(db, ops):
    changed = []
    for op in ops:
        api = op.api_data
        # extract fields (adapt to your API structure)
        card_num = extract_field(api, "card", "cardNumber") or extract_field(api, "row", "cardNumber") or extract_field(api, "cardNumber")
        car_num = extract_field(api, "row", "carNum") or extract_field(api, "carNum") or extract_field(api, "car")
        doc = extract_field(api, "row", "docNumber") or extract_field(api, "docNumber")
        dt_raw = extract_field(api, "row", "dateTimeIssue") or extract_field(api, "date_time") or extract_field(api, "dateTimeIssue")
        dt_obj = None
        if dt_raw:
            try:
                dt_obj = datetime.fromisoformat(dt_raw)
            except Exception:
                dt_obj = None

        # find presumed user
        try:
            presumed_user = find_user_by_card(db, card_num)
        except Exception as e:
            logger.exception("Error in find_user_by_card for card %s: %s", card_num, e)
            presumed_user = None

        # ensure fuel card
        try:
            fc = ensure_fuel_card(db, card_num, presumed_user)
        except Exception as e:
            logger.exception("Error ensuring fuel card %s: %s", card_num, e)
            fc = None

        # ensure car and link
        try:
            car = ensure_car_and_link(db, car_num, presumed_user)
        except Exception as e:
            logger.exception("Error ensuring car %s: %s", car_num, e)
            car = None

        # update operation fields if missing or different
        updated = {}
        if doc and getattr(op, "doc_number", None) != str(doc):
            updated["doc_number"] = str(doc)
        if dt_obj and getattr(op, "date_time", None) != dt_obj:
            updated["date_time"] = dt_obj
        if car_num:
            plate_norm = car_num.strip().upper()
            if getattr(op, "car_from_api", None) != plate_norm:
                updated["car_from_api"] = plate_norm
        if presumed_user and getattr(op, "presumed_user_id", None) != presumed_user.id:
            updated["presumed_user_id"] = presumed_user.id

        if updated:
            logger.info("Op %s: will update %s", op.id, updated)
            if not DRY_RUN:
                for k, v in updated.items():
                    setattr(op, k, v)
                db.flush()
            changed.append((op.id, updated))
    return changed

def main():
    total_changed = 0
    offset = 0

    while True:
        with get_db_session() as db:
            ops = db.query(FuelOperation).filter(FuelOperation.source == "api") \
                     .order_by(FuelOperation.imported_at.desc()) \
                     .offset(offset).limit(BATCH_SIZE).all()

            if not ops:
                break

            logger.info("Processing batch offset=%s size=%s", offset, len(ops))

            try:
                changed = process_batch(db, ops)
                if changed:
                    logger.info("Batch changed %d ops", len(changed))
                    total_changed += len(changed)
                if not DRY_RUN:
                    db.commit()
            except Exception as exc:
                # откатываем и логируем ошибку, затем продолжаем со следующей пачкой
                try:
                    db.rollback()
                except Exception:
                    logger.exception("Rollback failed after exception")
                logger.exception("Error processing batch at offset %s: %s", offset, exc)
                # если хотите остановиться при первой ошибке — раскомментируйте следующую строку:
                # break
            finally:
                pass

        offset += BATCH_SIZE

    logger.info("Done. Total changed: %d (dry_run=%s)", total_changed, DRY_RUN)

if __name__ == "__main__":
    main()
