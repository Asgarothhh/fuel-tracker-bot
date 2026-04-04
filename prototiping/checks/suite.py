"""
Проверки функционала приложения без изменения основного кода.
Каждая функция возвращает словарь: name, ok, detail (для графа и отчёта).
"""
from __future__ import annotations

from datetime import datetime, timezone

from src.app.belorusneft_api import parse_operations
from src.app.import_logic import (
    ImportBatch,
    api_local_yesterday_datetime,
    extract_flat_fields,
    import_api_operations,
    is_duplicate_api_operation,
    parse_api_datetime,
)
from src.app.models import FuelCard, FuelOperation, User
from src.app.permissions import user_has_permission
from src.app.plate_util import normalize_plate, plates_equal
from src.app.excel_export import _operation_row, HEADERS
from src.app.config import TOKEN_SALT
from src.app.tokens import generate_code, hash_code, verify_and_consume_code, create_bulk_codes
from src.ocr.schemas import ReceiptData

from prototiping.db.memory import memory_db_session, seed_admin_permission


def _result(name: str, ok: bool, detail: str = "") -> dict:
    return {"name": name, "ok": ok, "detail": detail}


def check_parse_operations_items() -> dict:
    payload = {
        "items": [
            {
                "dateTimeIssue": "2024-06-01T12:00:00Z",
                "productName": "АИ-95",
                "productQuantity": "10.5",
                "azsNumber": "1",
                "carNum": "1234 AA-7",
                "docNumber": "DOC-1",
                "cardNumber": "CARD-1",
            }
        ]
    }
    ops = parse_operations(payload)
    if len(ops) != 1:
        return _result("parse_operations(items)", False, f"expected 1 op, got {len(ops)}")
    if ops[0].get("doc_number") != "DOC-1":
        return _result("parse_operations(items)", False, "doc_number mismatch")
    return _result("parse_operations(items)", True, "items branch OK")


def check_parse_operations_cardlist() -> dict:
    payload = {
        "cardList": [
            {
                "cardNumber": "777",
                "issueRows": [
                    {
                        "dateTimeIssue": "2024-06-02T08:00:00+00:00",
                        "productName": "ДТ",
                        "productQuantity": "20",
                        "azsNumber": "9",
                        "carNum": "5555 BB-1",
                        "docNumber": "R-99",
                    }
                ],
            }
        ]
    }
    ops = parse_operations(payload)
    if len(ops) != 1 or ops[0].get("card_number") != "777":
        return _result("parse_operations(cardList)", False, str(ops))
    return _result("parse_operations(cardList)", True, "cardList/issueRows OK")


def check_parse_api_datetime() -> dict:
    dt = parse_api_datetime("2020-01-15T10:20:30Z")
    if dt is None or dt.tzinfo is None:
        return _result("parse_api_datetime", False, "Z suffix parse failed")
    return _result("parse_api_datetime", True, str(dt))


def check_api_local_yesterday() -> dict:
    y = api_local_yesterday_datetime()
    if y.hour != 0 or y.minute != 0:
        return _result("api_local_yesterday_datetime", False, "expected midnight")
    return _result("api_local_yesterday_datetime", True, y.isoformat())


def check_normalize_plate() -> dict:
    if normalize_plate(" 12-34 aa\t7 ") != "1234AA7":
        return _result("normalize_plate", False, normalize_plate(" 12-34 aa\t7 "))
    if not plates_equal("ab 1234", "AB-1234"):
        return _result("plates_equal", False, "should match")
    return _result("plate_util", True, "normalize + plates_equal OK")


def check_extract_flat_and_duplicate() -> dict:
    op = {
        "doc_number": "D1",
        "date_time": datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        "card_number": "C1",
        "raw": {
            "row": {
                "azsNumber": "A1",
                "productName": "P1",
                "productQuantity": "5",
            }
        },
    }
    flat = extract_flat_fields(op)
    if flat["doc"] != "D1" or flat["card"] != "C1":
        return _result("extract_flat_fields", False, str(flat))
    with memory_db_session() as db:
        fo = FuelOperation(
            source="api",
            doc_number="D1",
            date_time=flat["date_time"],
            api_data={
                "cardNumber": "C1",
                "row": {
                    "azsNumber": "A1",
                    "productName": "P1",
                    "productQuantity": "5",
                },
            },
            status="loaded_from_api",
        )
        db.add(fo)
        db.flush()
        if not is_duplicate_api_operation(db, flat):
            return _result("is_duplicate_api_operation", False, "should detect duplicate")
    return _result("extract_flat + duplicate", True, "dedup key OK")


def check_import_api_operations_dry_run() -> dict:
    payload = {
        "cardList": [
            {
                "cardNumber": "IMP-100",
                "issueRows": [
                    {
                        "dateTimeIssue": "2025-03-01T10:00:00+00:00",
                        "productName": "АИ-92",
                        "productQuantity": "15.25",
                        "azsNumber": "AZ-1",
                        "carNum": "1111 XX-7",
                        "docNumber": "IMP-DOC-1",
                    }
                ],
            }
        ]
    }
    with memory_db_session() as db:
        u = User(
            full_name="Driver",
            telegram_id=999888777,
            active=True,
            cars=[],
            cards=["IMP-100"],
            extra_ids={},
        )
        db.add(u)
        db.flush()
        card = FuelCard(card_number="IMP-100", user_id=u.id, active=True)
        db.add(card)
        db.flush()
        batch: ImportBatch = import_api_operations(db, payload, dry_run=True)
        db.rollback()
        if batch.new_count != 1:
            return _result("import_api_operations dry_run", False, f"new_count={batch.new_count}")
        if not batch.notify_users or batch.notify_users[0][0] != 999888777:
            return _result("import_api_operations notify", False, str(batch.notify_users))
    return _result("import_api_operations dry_run", True, "1 op, telegram notify")


def check_user_has_permission() -> dict:
    with memory_db_session() as db:
        seed_admin_permission(db)
        if not user_has_permission(db, 100001, "admin:manage"):
            return _result("user_has_permission(admin)", False, "expected True")
        if user_has_permission(db, 100001, "nonexistent:perm"):
            return _result("user_has_permission(deny)", False, "expected False")
        if user_has_permission(db, 999999, "admin:manage"):
            return _result("user_has_permission(unknown user)", False, "expected False")
    return _result("user_has_permission", True, "admin OK, unknown denied")


def check_tokens_flow() -> dict:
    with memory_db_session() as db:
        u = User(
            full_name="Link User",
            telegram_id=None,
            active=True,
            cars=[],
            cards=[],
            extra_ids={},
        )
        db.add(u)
        db.flush()
        codes = create_bulk_codes(db, u.id, 1, created_by=1)
        db.commit()
        plain = codes[0]
        h = hash_code(plain, TOKEN_SALT)
        from src.app.models import LinkToken

        tok = db.query(LinkToken).filter_by(code_hash=h).first()
        if not tok:
            return _result("create_bulk_codes", False, "token missing")
        ok, data = verify_and_consume_code(db, plain, telegram_id=555_444_333)
        if not ok:
            return _result("verify_and_consume_code", False, str(data))
        db.expire_all()
        u2 = db.query(User).filter_by(id=u.id).first()
        if u2.telegram_id != 555_444_333:
            return _result("user telegram bind", False, str(u2.telegram_id))
    return _result("tokens", True, "bulk + verify + bind OK")


def check_receipt_schema() -> dict:
    r = ReceiptData(
        fuel_type="АИ-95",
        quantity=40.0,
        price_per_liter=None,
        doc_number="CHK-1",
        azs_number=None,
        date="04.04.2026",
        time="12:00:00",
        total_sum=None,
        pump_no=None,
        azs_address=None,
        additional_info=None,
    )
    d = r.model_dump()
    if d.get("doc_number") != "CHK-1":
        return _result("ReceiptData", False, str(d))
    return _result("ReceiptData pydantic", True, "schema OK")


def check_excel_operation_row() -> dict:
    with memory_db_session() as db:
        u = User(full_name="Excel User", telegram_id=1, active=True, cars=[], cards=[], extra_ids={})
        db.add(u)
        db.flush()
        api = {
            "cardNumber": "C-1",
            "row": {
                "productName": "ДТ",
                "productQuantity": 30,
                "productCost": 100,
                "azsNumber": "77",
                "carNum": "7000 AA-7",
                "driverName": "Иванов",
            },
        }
        op = FuelOperation(
            source="api",
            api_data=api,
            doc_number="X-1",
            date_time=datetime(2026, 4, 1, 14, 30, tzinfo=timezone.utc),
            presumed_user_id=u.id,
            status="confirmed",
            car_from_api="7000AA7",
        )
        db.add(op)
        db.flush()
        row = _operation_row(db, op)
        if len(row) != len(HEADERS):
            return _result("_operation_row width", False, f"len={len(row)} expected {len(HEADERS)}")
        if "Excel User" not in row:
            return _result("_operation_row", False, str(row)[:200])
        if row[1] != "Топливная карта":
            return _result("_operation_row fuel type", False, row[1])
    return _result("excel_export._operation_row", True, "row built")


ALL_CHECKS = [
    check_parse_operations_items,
    check_parse_operations_cardlist,
    check_parse_api_datetime,
    check_api_local_yesterday,
    check_normalize_plate,
    check_extract_flat_and_duplicate,
    check_import_api_operations_dry_run,
    check_user_has_permission,
    check_tokens_flow,
    check_receipt_schema,
    check_excel_operation_row,
]
