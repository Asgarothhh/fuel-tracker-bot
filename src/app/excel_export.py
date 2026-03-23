"""
Выгрузка подтверждённых и спорных операций в Excel (структура по ТЗ).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from openpyxl import Workbook, load_workbook

from src.app.db import get_db_session
from src.app.models import FuelOperation, User, ConfirmationHistory

logger = logging.getLogger(__name__)

EXPORT_DIR = Path(__file__).parent.parent.parent / "exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)
MASTER_FILE = EXPORT_DIR / "Fuel_Report_Master.xlsx"

SHEET_CARDS = "Заправки_по_картам"
SHEET_DISPUTED = "Заправки_спорные"
SHEET_PERSONAL = "Заправки_личные_средства"
SHEET_REF = "Справочники"

HEADERS = [
    "ID", "Тип", "Источник", "Дата", "Время", "Карта", "Топливо", "Литры", "Сумма", "АЗС", "Чек",
    "Авто(API)", "Водитель(API)", "OCR", "Предполагаемый", "Фактический", "Факт.Авто",
    "Инициатор", "Подтвердил", "Статус", "Дата подтв", "Прим", "Готовность",
]


def _first_confirmation_sender_name(db, op_id: int) -> str:
    h = (
        db.query(ConfirmationHistory)
        .filter_by(operation_id=op_id)
        .order_by(ConfirmationHistory.id.asc())
        .first()
    )
    if not h or not h.to_user_id:
        return "—"
    u = db.query(User).filter_by(id=h.to_user_id).first()
    return u.full_name if u else "—"


def _ocr_text(op: FuelOperation) -> str:
    if not op.ocr_data:
        return ""
    if isinstance(op.ocr_data, dict):
        return op.ocr_data.get("raw_text") or op.ocr_data.get("text") or ""
    return str(op.ocr_data)


def _operation_row(db, op: FuelOperation) -> list:
    api = op.api_data or {}
    if not isinstance(api, dict):
        api = {}
    row = api.get("row") or {}
    if not isinstance(row, dict):
        row = {}
    card_o = api.get("card") or {}
    card_num = api.get("cardNumber") or (card_o.get("cardNumber") if isinstance(card_o, dict) else None)
    presumed = db.query(User).filter_by(id=op.presumed_user_id).first() if op.presumed_user_id else None
    confirmed = db.query(User).filter_by(id=op.confirmed_user_id).first() if op.confirmed_user_id else None
    first_r = db.query(User).filter_by(id=op.first_recipient_user_id).first() if op.first_recipient_user_id else None

    fuel_type = "Топливная карта" if op.source == "api" else "Личные средства"
    dt = op.date_time
    return [
        op.id,
        fuel_type,
        op.source or "",
        dt.strftime("%d.%m.%Y") if dt else "",
        dt.strftime("%H:%M:%S") if dt else "",
        card_num or "—",
        api.get("productName") or row.get("productName") or "—",
        api.get("productQuantity") or row.get("productQuantity") or 0,
        api.get("productCost") or row.get("productCost") or 0,
        api.get("azsNumber") or row.get("azsNumber") or row.get("AzsCode") or "—",
        op.doc_number or "—",
        op.car_from_api or "—",
        api.get("driverName") or row.get("driverName") or "—",
        _ocr_text(op),
        presumed.full_name if presumed else "—",
        confirmed.full_name if confirmed else "—",
        op.actual_car or op.car_from_api or "—",
        first_r.full_name if first_r else _first_confirmation_sender_name(db, op.id),
        confirmed.full_name if confirmed else "—",
        op.status or "",
        op.confirmed_at.strftime("%d.%m.%Y %H:%M") if op.confirmed_at else "—",
        "",
        "Да" if op.ready_for_waybill or op.status == "confirmed" else "Нет",
    ]


def _ensure_workbook(path: Path):
    if not path.exists():
        wb = Workbook()
        ws0 = wb.active
        ws0.title = SHEET_CARDS
        ws0.append(HEADERS)
        wb.create_sheet(SHEET_DISPUTED)
        wb[SHEET_DISPUTED].append(HEADERS)
        wb.create_sheet(SHEET_PERSONAL)
        wb[SHEET_PERSONAL].append(HEADERS)
        wb.create_sheet(SHEET_REF)
        wb[SHEET_REF].append(["Справочник", "Значение"])
        wb[SHEET_REF].append(["Обновлено", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")])
        return wb
    wb = load_workbook(path)
    if SHEET_CARDS not in wb.sheetnames:
        ws = wb.create_sheet(SHEET_CARDS)
        ws.append(HEADERS)
    if SHEET_DISPUTED not in wb.sheetnames:
        ws = wb.create_sheet(SHEET_DISPUTED)
        ws.append(HEADERS)
    if SHEET_PERSONAL not in wb.sheetnames:
        ws = wb.create_sheet(SHEET_PERSONAL)
        ws.append(HEADERS)
    if SHEET_REF not in wb.sheetnames:
        ws = wb.create_sheet(SHEET_REF)
        ws.append(["Справочник", "Значение"])
    return wb


def _sheet_has_id(ws, op_id: int) -> bool:
    for row in ws.iter_rows(min_row=2, max_col=1, values_only=True):
        if row and row[0] == op_id:
            return True
    return False


def export_to_excel_final(op_id: int) -> None:
    """
    Подтверждённые операции — лист Заправки_по_картам.
    Спорные/ручные/отклонённые — Заправки_спорные.
    """
    with get_db_session() as db:
        op = db.query(FuelOperation).filter_by(id=op_id).first()
        if not op:
            return
        st = op.status or ""
        disputed = st in ("requires_manual", "rejected_by_other", "import_error")
        if disputed:
            if op.exported_disputed_excel:
                return
            sheet_name = SHEET_DISPUTED
        elif st == "confirmed":
            if op.exported_to_excel:
                return
            sheet_name = SHEET_CARDS
        else:
            logger.debug("[excel] skip export op_id=%s status=%s", op_id, st)
            return

        row = _operation_row(db, op)
        try:
            wb = _ensure_workbook(MASTER_FILE)
            ws = wb[sheet_name]
            if not _sheet_has_id(ws, op_id):
                ws.append(row)
            wb.save(MASTER_FILE)
            if disputed:
                op.exported_disputed_excel = True
            else:
                op.exported_to_excel = True
                op.ready_for_waybill = True
            db.commit()
            logger.info("[excel] op_id=%s sheet=%s", op_id, sheet_name)
        except PermissionError as e:
            logger.error("[excel] файл Excel занят: %s", e)
            raise
        except Exception as e:
            logger.exception("[excel] ошибка записи op_id=%s: %s", op_id, e)
            raise
