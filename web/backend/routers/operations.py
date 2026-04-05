from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from web.backend.dependencies import get_db
from web.backend.schemas import OperationResponse, ReassignRequest
from web.backend.services.api_import_web import run_api_import_sync
from src.app.models import FuelOperation, User

router = APIRouter(prefix="/api/operations", tags=["Operations"])


def format_operation(op: FuelOperation) -> dict:
    # Пытаемся достать данные из JSON (api_data для загрузок из АЗС или ocr_data для чеков)
    data = op.api_data if op.api_data else (op.ocr_data or {})

    # В Belorusneft API сумма обычно лежит в 'sum' или 'amount'
    amount = data.get('sum') or data.get('amount') or 0.0
    # Тип топлива обычно 'service_name' или 'fuel_type'
    fuel_type = data.get('service_name') or data.get('fuel_type') or "—"

    return {
        "id": op.id,
        "doc_number": op.doc_number or "—",
        "date_time": op.date_time,
        "amount": float(amount),
        "fuel_type": str(fuel_type),
        "car": op.car_from_api or op.actual_car or "—",
        "user_name": op.presumed_user.full_name if op.presumed_user else "Не определен",
        "status": op.status
    }


@router.get("/{tab_name}")
def get_operations(tab_name: str, db: Session = Depends(get_db)):
    query = db.query(FuelOperation).options(joinedload(FuelOperation.presumed_user))

    if tab_name == "pending":
        query = query.filter(FuelOperation.status.in_(["pending", "new"]))
    elif tab_name == "disputed":
        query = query.filter(FuelOperation.status == "disputed")
    elif tab_name == "api":
        query = query.filter(FuelOperation.source == "api")
    elif tab_name == "recent":
        pass  # Показываем всё
    else:
        raise HTTPException(status_code=404, detail="Unknown tab")

    ops = query.order_by(FuelOperation.date_time.desc()).all()
    return [format_operation(op) for op in ops]


# Эндпоинты для действий (confirm/reject/delete) остаются как были в прошлом сообщении


# --- ДЕЙСТВИЯ ИЗ МЕНЮ "ТРИ ТОЧКИ" ---

@router.post("/{op_id}/confirm")
def confirm_operation(op_id: int, db: Session = Depends(get_db)):
    op = db.query(FuelOperation).filter(FuelOperation.id == op_id).first()
    if not op: raise HTTPException(status_code=404, detail="Operation not found")
    op.status = "confirmed"
    db.commit()
    return {"status": "success"}


@router.post("/{op_id}/reject")
def reject_operation(op_id: int, db: Session = Depends(get_db)):
    op = db.query(FuelOperation).filter(FuelOperation.id == op_id).first()
    if not op: raise HTTPException(status_code=404, detail="Operation not found")
    op.status = "rejected"
    db.commit()
    return {"status": "success"}


@router.post("/{op_id}/reassign")
def reassign_operation(op_id: int, payload: ReassignRequest, db: Session = Depends(get_db)):
    op = db.query(FuelOperation).filter(FuelOperation.id == op_id).first()
    if not op: raise HTTPException(status_code=404, detail="Operation not found")
    op.presumed_user_id = payload.new_user_id
    op.status = "pending"  # После переназначения кидаем снова на проверку
    db.commit()
    return {"status": "success"}


@router.delete("/{op_id}")
def delete_operation(op_id: int, db: Session = Depends(get_db)):
    op = db.query(FuelOperation).filter(FuelOperation.id == op_id).first()
    if not op: raise HTTPException(status_code=404, detail="Operation not found")
    db.delete(op)
    db.commit()
    return {"status": "success"}


@router.post("/import-from-api")
def import_operations_from_api(db: Session = Depends(get_db)):
    """Та же логика загрузки, что ручной импорт в боте (admin_import), без Telegram."""
    result = run_api_import_sync(db)
    if not result.get("ok"):
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=result.get("error") or result.get("message") or "Импорт не выполнен",
        )
    return result