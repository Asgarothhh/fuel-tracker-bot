"""
Проверки функционала приложения без изменения основного кода.
Каждая функция возвращает словарь: name, ok, detail (для графа и отчёта).
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException

from src.app.belorusneft_api import parse_operations
from src.app.import_logic import (
    ImportBatch,
    api_local_yesterday_datetime,
    extract_flat_fields,
    import_api_operations,
    is_duplicate_api_operation,
    parse_api_datetime,
)
from src.app.models import FuelCard, FuelOperation, User, Role, Permission, role_permissions
from src.app.plate_util import normalize_plate, plates_equal
from src.app.excel_export import _operation_row, HEADERS
from src.app.config import TOKEN_SALT
from src.app.tokens import generate_code, hash_code, verify_and_consume_code, create_bulk_codes
from src.ocr.schemas import ReceiptData
from web.backend.dependencies import get_db as web_get_db
from web.backend.main import health_check
from web.backend.routers.operations import (
    confirm_operation as web_confirm_operation,
    delete_operation as web_delete_operation,
    format_operation as web_format_operation,
    get_operations as web_get_operations,
    reassign_operation as web_reassign_operation,
    reject_operation as web_reject_operation,
)
from web.backend.routers.reports import download_full_excel_report as web_download_full_excel_report
from web.backend.routers.users import (
    delete_user as web_delete_user,
    edit_user as web_edit_user,
    get_all_users as web_get_all_users,
    get_users as web_get_users,
)
from web.backend.schemas import ReassignRequest, UserEditRequest
from web.backend.services.excel_report import build_full_fuel_report_excel

from prototiping.db.memory import memory_db_session, seed_admin_permission


def _result(name: str, ok: bool, detail: str = "") -> dict:
    """Единый формат результата проверки для графа и отчёта.

    :param name: Короткое имя шага (отображается в трассировке).
    :type name: str
    :param ok: Успех или провал сценария.
    :type ok: bool
    :param detail: Пояснение (особенно при ``ok=False``).
    :type detail: str

    :returns: ``{"name": str, "ok": bool, "detail": str}``.
    :rtype: dict

    Пример::

        d = _result("step", True, "ok")
        assert d["ok"] is True
    """
    return {"name": name, "ok": ok, "detail": detail}


def _user_has_permission_compat(db, telegram_id: int, permission_name: str) -> bool:
    """Локальная совместимая проверка прав без импорта ``src.app.permissions``.

    Нужна только для прототипирования: модуль ``src.app.permissions`` теперь
    тянет bot-слой и может образовать цикл импорта при изолированном прогоне
    checks/reporting.
    """
    row = db.query(User.id, User.role_id).filter(User.telegram_id == telegram_id).first()
    if not row:
        return False
    _, role_id = row
    if not role_id:
        return False
    perm = (
        db.query(Permission.id)
        .join(role_permissions, role_permissions.c.permission_id == Permission.id)
        .join(Role, role_permissions.c.role_id == Role.id)
        .filter(Role.id == role_id, Permission.name == permission_name)
        .first()
    )
    return bool(perm)


def check_parse_operations_items() -> dict:
    """S01: ``parse_operations`` для JSON с массивом ``items``.

    Принимает: ничего (тестовый payload внутри).

    :returns: Результат ``_result``: разбор одной операции, ``doc_number`` = DOC-1.
    :rtype: dict
    """
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
    """S02: ``parse_operations`` для ``cardList`` / ``issueRows``.

    Принимает: ничего.

    :returns: Результат ``_result``; при успехе одна операция, ``card_number`` с уровня карты.
    :rtype: dict
    """
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
    """S03: ``parse_api_datetime`` для ISO-строки с суффиксом ``Z``.

    Принимает: ничего.

    :returns: Результат ``_result``; при успехе в ``detail`` — строка ``datetime``.
    :rtype: dict
    """
    dt = parse_api_datetime("2020-01-15T10:20:30Z")
    if dt is None or dt.tzinfo is None:
        return _result("parse_api_datetime", False, "Z suffix parse failed")
    return _result("parse_api_datetime", True, str(dt))


def check_api_local_yesterday() -> dict:
    """S04: ``api_local_yesterday_datetime`` (календарное вчера в UTC+3).

    Принимает: ничего.

    :returns: Результат ``_result``; при успехе полночь локальной даты в ``detail``.
    :rtype: dict
    """
    y = api_local_yesterday_datetime()
    if y.hour != 0 or y.minute != 0:
        return _result("api_local_yesterday_datetime", False, "expected midnight")
    return _result("api_local_yesterday_datetime", True, y.isoformat())


def check_parse_operations_empty_items_fallback_cardlist() -> dict:
    """S05: пустой ``items`` не должен блокировать разбор ``cardList`` (типичная ошибка при ``if items is not None``).

    Принимает: ничего.

    :returns: Результат ``_result``.
    :rtype: dict
    """
    payload = {
        "items": [],
        "cardList": [
            {
                "cardNumber": "EMPTY-ITEMS-CARD",
                "issueRows": [
                    {
                        "dateTimeIssue": "2025-01-15T12:00:00+00:00",
                        "docNumber": "DOC-EMPTY-ITEMS-FALLBACK",
                        "productName": "АИ-95",
                        "productQuantity": "1",
                        "azsNumber": "1",
                    }
                ],
            }
        ],
    }
    try:
        ops = parse_operations(payload)
    except Exception as e:
        return _result("parse_operations empty items → cardList", False, repr(e))
    if len(ops) != 1:
        return _result("parse_operations empty items → cardList", False, f"len={len(ops)} ops={ops!r}")
    if ops[0].get("doc_number") != "DOC-EMPTY-ITEMS-FALLBACK":
        return _result("parse_operations empty items → cardList", False, str(ops[0]))
    if ops[0].get("card_number") != "EMPTY-ITEMS-CARD":
        return _result("parse_operations empty items → cardList", False, "card_number mismatch")
    return _result("parse_operations empty items → cardList", True, "cardList used")


def check_parse_api_datetime_invalid_inputs() -> dict:
    """S06: мусор в ``parse_api_datetime`` не должен ронять импорт (только ``None``).

    Принимает: ничего.

    :returns: Результат ``_result``.
    :rtype: dict
    """
    bad_values: list = [
        "",
        "   ",
        "not-a-date-at-all",
        "2020-13-45T99:99:99",
        12345,
        {},
        [],
    ]
    for b in bad_values:
        try:
            r = parse_api_datetime(b)
        except Exception as e:
            return _result("parse_api_datetime invalid", False, f"{b!r} raised {e!r}")
        if r is not None:
            return _result("parse_api_datetime invalid", False, f"{b!r} -> {r!r} expected None")
    return _result("parse_api_datetime invalid", True, "garbage → None, no exception")


def check_normalize_plate() -> dict:
    """S07: ``normalize_plate`` и ``plates_equal``.

    Принимает: ничего.

    :returns: Результат ``_result``.
    :rtype: dict
    """
    if normalize_plate(" 12-34 aa\t7 ") != "1234AA7":
        return _result("normalize_plate", False, normalize_plate(" 12-34 aa\t7 "))
    if not plates_equal("ab 1234", "AB-1234"):
        return _result("plates_equal", False, "should match")
    return _result("plate_util", True, "normalize + plates_equal OK")


def check_extract_flat_and_duplicate() -> dict:
    """S08: ``extract_flat_fields`` и ``is_duplicate_api_operation`` на in-memory БД.

    Принимает: ничего.

    :returns: Результат ``_result``.
    :rtype: dict
    """
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


def check_extract_flat_fields_malformed_raw() -> dict:
    """S09: ``raw.row`` не словарь — не падаем, поля берутся с верхнего уровня операции.

    Принимает: ничего.

    :returns: Результат ``_result``.
    :rtype: dict
    """
    op = {
        "doc_number": "MALFORMED-RAW-DOC",
        "date_time": datetime(2025, 3, 3, 8, 0, tzinfo=timezone.utc),
        "card_number": "CARD-MALF-RAW",
        "raw": {"row": [1, 2, 3]},
    }
    try:
        flat = extract_flat_fields(op)
    except Exception as e:
        return _result("extract_flat malformed raw.row", False, repr(e))
    if flat["doc"] != "MALFORMED-RAW-DOC" or flat["card"] != "CARD-MALF-RAW":
        return _result("extract_flat malformed raw.row", False, str(flat))
    if flat["date_time"] != op["date_time"]:
        return _result("extract_flat malformed raw.row", False, "date_time lost")
    return _result("extract_flat malformed raw.row", True, "list row ignored")


def check_import_api_operations_dry_run() -> dict:
    """S10: ``import_api_operations(..., dry_run=True)`` с пользователем и картой.

    Принимает: ничего.

    :returns: Результат ``_result``; ожидается одна новая операция и уведомление на ``telegram_id``.
    :rtype: dict
    """
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


def check_import_skips_without_date_and_doc() -> dict:
    """S11: строка без даты и без номера чека пропускается; следующая строка всё ещё импортируется.

    Принимает: ничего.

    :returns: Результат ``_result``.
    :rtype: dict
    """
    payload = {
        "cardList": [
            {
                "cardNumber": "SKIP-MIX-CARD",
                "issueRows": [
                    {
                        "productName": "ДТ",
                        "productQuantity": "5",
                        "azsNumber": "9",
                    },
                    {
                        "dateTimeIssue": "2025-04-04T11:00:00+00:00",
                        "docNumber": "DOC-AFTER-SKIPPED-ROW",
                        "productName": "АИ-92",
                        "productQuantity": "3",
                        "azsNumber": "3",
                    },
                ],
            }
        ]
    }
    with memory_db_session() as db:
        try:
            batch: ImportBatch = import_api_operations(db, payload, dry_run=True)
        except Exception as e:
            return _result("import skip no date+doc", False, repr(e))
        db.rollback()
    if batch.new_count != 1:
        return _result("import skip no date+doc", False, f"new_count={batch.new_count}")
    return _result("import skip no date+doc", True, "1 row skipped, 1 imported")


def check_user_has_permission() -> dict:
    """S12: ``user_has_permission`` для админа и граничных случаев.

    Принимает: ничего.

    :returns: Результат ``_result``.
    :rtype: dict
    """
    with memory_db_session() as db:
        seed_admin_permission(db)
        if not _user_has_permission_compat(db, 100001, "admin:manage"):
            return _result("user_has_permission(admin)", False, "expected True")
        if _user_has_permission_compat(db, 100001, "nonexistent:perm"):
            return _result("user_has_permission(deny)", False, "expected False")
        if _user_has_permission_compat(db, 999999, "admin:manage"):
            return _result("user_has_permission(unknown user)", False, "expected False")
    return _result("user_has_permission", True, "admin OK, unknown denied")


def check_breaker_permissions_module_import_cycle_probe() -> dict:
    """S16: негативный сценарий: пробуем прямой импорт ``src.app.permissions``.

    Это "ломающий" тест: если в новом ``src`` есть cycle import, считаем это
    за сработавший breaker (ok=False, чтобы классифицировать как TN).
    """
    try:
        from src.app.permissions import ActiveUserMiddleware  # noqa: F401
    except Exception as e:
        return _result("breaker: permissions import cycle probe", False, f"cycle/import issue: {e!r}")
    return _result("breaker: permissions import cycle probe", True, "import succeeded, no cycle detected")


def check_breaker_parse_operations_type_poison() -> dict:
    """S17: семантический негатив: дедуп обходит формат АЗС (`7` vs `07`).

    По бизнес-смыслу это одна и та же АЗС; если импортируются 2 операции,
    значит ключ дедупликации уязвим к форматному дрейфу.
    """
    payload = {
        "cardList": [
            {
                "cardNumber": "DEDUP-AZS-CARD",
                "issueRows": [
                    {
                        "dateTimeIssue": "2026-04-01T10:00:00+00:00",
                        "docNumber": "DOC-AZS-777",
                        "productName": "ДТ",
                        "productQuantity": "5",
                        "azsNumber": "7",
                    },
                    {
                        "dateTimeIssue": "2026-04-01T10:00:00+00:00",
                        "docNumber": "DOC-AZS-777",
                        "productName": "ДТ",
                        "productQuantity": "5",
                        "azsNumber": "07",
                    },
                ],
            }
        ]
    }
    with memory_db_session() as db:
        try:
            batch: ImportBatch = import_api_operations(db, payload, dry_run=True)
        except Exception as e:
            return _result("breaker: dedup azs format gap", False, f"import crashed: {e!r}")
        db.rollback()
    if batch.new_count > 1:
        return _result("breaker: dedup azs format gap", False, f"dedup bypassed, new_count={batch.new_count}")
    return _result("breaker: dedup azs format gap", True, "dedup resisted azs formatting drift")


def check_breaker_parse_operations_card_rows_type_poison() -> dict:
    """S18: семантический негатив: дедуп обходит регистр в `doc_number`.

    По бизнес-смыслу номер чека обычно регистронезависим.
    """
    payload = {
        "cardList": [
            {
                "cardNumber": "DEDUP-DOC-CASE-CARD",
                "issueRows": [
                    {
                        "dateTimeIssue": "2026-04-02T10:00:00+00:00",
                        "docNumber": "AbC-901",
                        "productName": "АИ-95",
                        "productQuantity": "7",
                        "azsNumber": "A-2",
                    },
                    {
                        "dateTimeIssue": "2026-04-02T10:00:00+00:00",
                        "docNumber": "abc-901",
                        "productName": "АИ-95",
                        "productQuantity": "7",
                        "azsNumber": "A-2",
                    },
                ],
            }
        ]
    }
    with memory_db_session() as db:
        try:
            batch: ImportBatch = import_api_operations(db, payload, dry_run=True)
        except Exception as e:
            return _result("breaker: dedup doc case gap", False, f"import crashed: {e!r}")
        db.rollback()
    if batch.new_count > 1:
        return _result("breaker: dedup doc case gap", False, f"dedup bypassed, new_count={batch.new_count}")
    return _result("breaker: dedup doc case gap", True, "dedup resisted doc case drift")


def check_breaker_import_quantity_format_dedup_gap() -> dict:
    """S19: негативный сценарий: дедуп по количеству `5` vs `5.0`.

    Семантически это одна и та же операция. Если импорт создаёт 2 записи, значит
    дедуп-ключ слишком строгий по строковому формату.
    """
    payload = {
        "cardList": [
            {
                "cardNumber": "DEDUP-QTY-CARD",
                "issueRows": [
                    {
                        "dateTimeIssue": "2026-04-01T10:00:00+00:00",
                        "docNumber": "DUP-QTY-1",
                        "productName": "ДТ",
                        "productQuantity": "5",
                        "azsNumber": "A-1",
                    },
                    {
                        "dateTimeIssue": "2026-04-01T10:00:00+00:00",
                        "docNumber": "DUP-QTY-1",
                        "productName": "ДТ",
                        "productQuantity": "5.0",
                        "azsNumber": "A-1",
                    },
                ],
            }
        ]
    }
    with memory_db_session() as db:
        try:
            batch: ImportBatch = import_api_operations(db, payload, dry_run=True)
        except Exception as e:
            return _result("breaker: dedup qty format gap", False, f"import crashed: {e!r}")
        db.rollback()
    if batch.new_count > 1:
        return _result("breaker: dedup qty format gap", False, f"dedup bypassed, new_count={batch.new_count}")
    return _result("breaker: dedup qty format gap", True, "dedup resisted qty formatting drift")


def check_breaker_import_invalid_cardlist_shape() -> dict:
    """S20: семантический негатив: неактивная карта не должна мапиться на пользователя."""
    payload = {
        "cardList": [
            {
                "cardNumber": "INACTIVE-CARD-1",
                "issueRows": [
                    {
                        "dateTimeIssue": "2026-04-03T10:00:00+00:00",
                        "docNumber": "INACTIVE-CARD-DOC-1",
                        "productName": "АИ-92",
                        "productQuantity": "9",
                        "azsNumber": "A-3",
                    }
                ],
            }
        ]
    }
    with memory_db_session() as db:
        u = User(
            full_name="Inactive Card User",
            telegram_id=123123123,
            active=True,
            cars=[],
            cards=["INACTIVE-CARD-1"],
            extra_ids={},
        )
        db.add(u)
        db.flush()
        db.add(FuelCard(card_number="INACTIVE-CARD-1", user_id=u.id, active=False))
        db.flush()
        try:
            batch: ImportBatch = import_api_operations(db, payload, dry_run=True)
        except Exception as e:
            return _result("breaker: inactive card user-link", False, f"import crashed: {e!r}")
        linked = len(batch.notify_users)
        db.rollback()
    if linked > 0:
        return _result("breaker: inactive card user-link", False, f"inactive card linked user, notify_users={linked}")
    return _result("breaker: inactive card user-link", True, "inactive card did not link user")


def check_breaker_parse_api_datetime_naive_timezone() -> dict:
    """S21: негативный сценарий: наивная дата без timezone.

    Семантически API-время должно быть timezone-aware. Наивный datetime опасен для
    дедупа и сопоставления интервалов.
    """
    dt = parse_api_datetime("2026-04-01 10:00:00")
    if dt is not None and dt.tzinfo is None:
        return _result("breaker: parse_api_datetime naive tz", False, f"naive datetime accepted: {dt!r}")
    return _result("breaker: parse_api_datetime naive tz", True, "naive datetime rejected or normalized")


def check_web_health_check() -> dict:
    r = health_check()
    if r.get("status") != "ok":
        return _result("web health", False, str(r))
    return _result("web health", True, "status ok")


def check_web_get_db_yields_session() -> dict:
    gen = web_get_db()
    try:
        db = next(gen)
        if db is None:
            return _result("web get_db", False, "no session yielded")
    except Exception as e:
        return _result("web get_db", False, repr(e))
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
    return _result("web get_db", True, "session yielded")


def check_web_get_users_endpoint() -> dict:
    with memory_db_session() as db:
        db.add(User(full_name="U1", telegram_id=1, active=True, cars=[], cards=[], extra_ids={}))
        db.add(User(full_name="U2", telegram_id=2, active=False, cars=[], cards=[], extra_ids={}))
        db.flush()
        out = web_get_users(db=db)
        if len(out) != 2:
            return _result("web users list", False, f"len={len(out)}")
    return _result("web users list", True, "2 users")


def check_web_get_all_users_role_fallback() -> dict:
    with memory_db_session() as db:
        db.add(User(full_name="No Role", telegram_id=5, active=True, cars=[], cards=[], extra_ids={}))
        db.flush()
        out = web_get_all_users(db=db)
        if not out or out[0].get("role") != "Водитель":
            return _result("web users role fallback", False, str(out))
    return _result("web users role fallback", True, "fallback role OK")


def check_web_edit_user_updates_fields() -> dict:
    with memory_db_session() as db:
        role = Role(role_name="dispatcher", description="d")
        db.add(role)
        db.flush()
        u = User(full_name="Before", telegram_id=99, active=True, role_id=None, cars=[], cards=[], extra_ids={})
        db.add(u)
        db.flush()
        out = web_edit_user(
            user_id=u.id,
            payload=UserEditRequest(full_name="After", active=False, role_id=role.id),
            db=db,
        )
        if out.full_name != "After" or out.active is not False or out.role_id != role.id:
            return _result("web edit user", False, f"{out.full_name}/{out.active}/{out.role_id}")
    return _result("web edit user", True, "user updated")


def check_web_delete_user_success() -> dict:
    with memory_db_session() as db:
        u = User(full_name="To Delete", telegram_id=77, active=True, cars=[], cards=[], extra_ids={})
        db.add(u)
        db.flush()
        r = web_delete_user(user_id=u.id, db=db)
        left = db.query(User).filter(User.id == u.id).count()
        if r.get("status") != "success" or left != 0:
            return _result("web delete user", False, f"status={r}, left={left}")
    return _result("web delete user", True, "deleted")


def check_web_format_operation_api_fields() -> dict:
    with memory_db_session() as db:
        u = User(full_name="Fmt User", telegram_id=301, active=True, cars=[], cards=[], extra_ids={})
        db.add(u)
        db.flush()
        op = FuelOperation(
            source="api",
            api_data={"sum": "25.5", "service_name": "АИ-95"},
            doc_number="FMT-1",
            date_time=datetime(2026, 4, 1, 9, 0, tzinfo=timezone.utc),
            presumed_user_id=u.id,
            status="pending",
            car_from_api="1111AA7",
        )
        db.add(op)
        db.flush()
        d = web_format_operation(op)
        if d["amount"] != 25.5 or d["fuel_type"] != "АИ-95" or d["user_name"] != "Fmt User":
            return _result("web format_operation", False, str(d))
    return _result("web format_operation", True, "formatted")


def check_web_get_operations_pending_filter() -> dict:
    with memory_db_session() as db:
        db.add(FuelOperation(source="api", status="pending", date_time=datetime.now(timezone.utc)))
        db.add(FuelOperation(source="api", status="new", date_time=datetime.now(timezone.utc)))
        db.add(FuelOperation(source="api", status="confirmed", date_time=datetime.now(timezone.utc)))
        db.flush()
        out = web_get_operations("pending", db=db)
        if len(out) != 2:
            return _result("web operations pending", False, f"len={len(out)}")
    return _result("web operations pending", True, "pending/new filtered")


def check_web_confirm_reject_reassign_flow() -> dict:
    with memory_db_session() as db:
        u = User(full_name="New User", telegram_id=880, active=True, cars=[], cards=[], extra_ids={})
        op = FuelOperation(source="api", status="new", date_time=datetime.now(timezone.utc))
        db.add_all([u, op])
        db.flush()
        web_confirm_operation(op.id, db=db)
        web_reject_operation(op.id, db=db)
        web_reassign_operation(op.id, payload=ReassignRequest(new_user_id=u.id), db=db)
        db.refresh(op)
        if op.status != "pending" or op.presumed_user_id != u.id:
            return _result("web op actions", False, f"status={op.status}, uid={op.presumed_user_id}")
    return _result("web op actions", True, "confirm/reject/reassign")


def check_web_excel_builder_has_sheets() -> dict:
    with memory_db_session() as db:
        db.add(FuelOperation(source="api", status="confirmed", date_time=datetime.now(timezone.utc), api_data={}))
        db.flush()
        buf, count = build_full_fuel_report_excel(db)
        if buf is None or count != 1:
            return _result("web excel builder", False, f"buf={buf is not None}, count={count}")
    return _result("web excel builder", True, "excel built")


def check_breaker_web_unknown_tab_404() -> dict:
    with memory_db_session() as db:
        try:
            web_get_operations("mystery", db=db)
        except HTTPException as e:
            if e.status_code == 404:
                return _result("breaker web unknown tab", False, "404 guard works")
            return _result("breaker web unknown tab", True, f"unexpected code {e.status_code}")
        except Exception as e:
            return _result("breaker web unknown tab", True, repr(e))
    return _result("breaker web unknown tab", True, "no guard raised")


def check_breaker_web_edit_user_not_found_404() -> dict:
    with memory_db_session() as db:
        try:
            web_edit_user(9999, UserEditRequest(full_name="X", active=True, role_id=1), db=db)
        except HTTPException as e:
            if e.status_code == 404:
                return _result("breaker web edit missing", False, "404 guard works")
            return _result("breaker web edit missing", True, f"unexpected code {e.status_code}")
        except Exception as e:
            return _result("breaker web edit missing", True, repr(e))
    return _result("breaker web edit missing", True, "no guard raised")


def check_breaker_web_delete_op_not_found_404() -> dict:
    with memory_db_session() as db:
        try:
            web_delete_operation(7777, db=db)
        except HTTPException as e:
            if e.status_code == 404:
                return _result("breaker web delete op missing", False, "404 guard works")
            return _result("breaker web delete op missing", True, f"unexpected code {e.status_code}")
        except Exception as e:
            return _result("breaker web delete op missing", True, repr(e))
    return _result("breaker web delete op missing", True, "no guard raised")


def check_breaker_web_reassign_not_found_404() -> dict:
    with memory_db_session() as db:
        try:
            web_reassign_operation(8888, ReassignRequest(new_user_id=1), db=db)
        except HTTPException as e:
            if e.status_code == 404:
                return _result("breaker web reassign missing", False, "404 guard works")
            return _result("breaker web reassign missing", True, f"unexpected code {e.status_code}")
        except Exception as e:
            return _result("breaker web reassign missing", True, repr(e))
    return _result("breaker web reassign missing", True, "no guard raised")


def check_breaker_web_excel_empty_404() -> dict:
    with memory_db_session() as db:
        try:
            web_download_full_excel_report(db=db)
        except HTTPException as e:
            if e.status_code == 404:
                return _result("breaker web excel empty", False, "404 guard works")
            return _result("breaker web excel empty", True, f"unexpected code {e.status_code}")
        except Exception as e:
            return _result("breaker web excel empty", True, repr(e))
    return _result("breaker web excel empty", True, "no guard raised")


def check_tokens_flow() -> dict:
    """S13: выпуск кода привязки, ``verify_and_consume_code``, запись ``telegram_id``.

    Принимает: ничего.

    :returns: Результат ``_result``.
    :rtype: dict
    """
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
    """S14: модель Pydantic ``ReceiptData`` и ``model_dump``.

    Принимает: ничего.

    :returns: Результат ``_result``.
    :rtype: dict
    """
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
    """S15: ``excel_export._operation_row`` для операции из API.

    Принимает: ничего.

    :returns: Результат ``_result``; ширина строки = ``len(HEADERS)``.
    :rtype: dict
    """
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
    check_parse_operations_empty_items_fallback_cardlist,
    check_parse_api_datetime_invalid_inputs,
    check_normalize_plate,
    check_extract_flat_and_duplicate,
    check_extract_flat_fields_malformed_raw,
    check_import_api_operations_dry_run,
    check_import_skips_without_date_and_doc,
    check_user_has_permission,
    check_tokens_flow,
    check_receipt_schema,
    check_excel_operation_row,
    check_breaker_permissions_module_import_cycle_probe,
    check_breaker_parse_operations_type_poison,
    check_breaker_parse_operations_card_rows_type_poison,
    check_breaker_import_quantity_format_dedup_gap,
    check_breaker_import_invalid_cardlist_shape,
    check_breaker_parse_api_datetime_naive_timezone,
    check_web_health_check,
    check_web_get_db_yields_session,
    check_web_get_users_endpoint,
    check_web_get_all_users_role_fallback,
    check_web_edit_user_updates_fields,
    check_web_delete_user_success,
    check_web_format_operation_api_fields,
    check_web_get_operations_pending_filter,
    check_web_confirm_reject_reassign_flow,
    check_web_excel_builder_has_sheets,
    check_breaker_web_unknown_tab_404,
    check_breaker_web_edit_user_not_found_404,
    check_breaker_web_delete_op_not_found_404,
    check_breaker_web_reassign_not_found_404,
    check_breaker_web_excel_empty_404,
]
