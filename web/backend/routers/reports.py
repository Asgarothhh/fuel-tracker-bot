from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from web.backend.dependencies import get_db
from web.backend.services.excel_report import build_full_fuel_report_excel

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.get("/excel")
def download_full_excel_report(db: Session = Depends(get_db)):
    buf, count = build_full_fuel_report_excel(db)
    if buf is None:
        raise HTTPException(status_code=404, detail="В базе данных нет операций для выгрузки.")

    name = f"Full_Fuel_Report_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.xlsx"
    data = buf.getvalue()
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )
