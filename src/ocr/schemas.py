from pydantic import BaseModel, Field
from typing import Optional, List


class ReceiptData(BaseModel):
    """Схема структрурированных данных из чека"""
    fuel_type: Optional[str] = Field(description="Вид топлива (например, АИ-95, ДТ")
    quantity: Optional[float] = Field(description="Количество литров")
    price_per_liter: Optional[float] = Field(description="Цена за один литр")
    doc_number: Optional[str] = Field(description="Номер чека или номер документа")
    azs_number: Optional[str] = Field(description="Номер АЗС")
    date: Optional[str] = Field(description="Дата чека в формате ДД.ММ.ГГГГ")
    time: Optional[str] = Field(description="Время чека в формате ЧЧ:ММ:СС")
    total_sum: Optional[str] = Field(description="Итоговая сумма к оплате")
    pump_no: Optional[str] = Field(description="Номер колонки (ТРК)")
    azs_address: Optional[str] = Field(description="Адрес заправочной станции")
    additional_info: Optional[str] = Field(description="Любые другие важные текстовые данные")
