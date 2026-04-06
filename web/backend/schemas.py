from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# --- ПОЛЬЗОВАТЕЛИ ---
class UserResponse(BaseModel):
    id: int
    full_name: str
    telegram_id: Optional[int] = None
    active: bool
    role_id: Optional[int] = None
    cards: Optional[List[str]] = []
    cars: Optional[List[str]] = []

class UserEditRequest(BaseModel):
    full_name: str
    active: bool
    role_id: int

# --- ОПЕРАЦИИ ---
class OperationResponse(BaseModel):
    id: int
    doc_number: Optional[str]
    date_time: Optional[datetime]
    amount: Optional[float]
    fuel_type: Optional[str]
    car: Optional[str]
    user_name: Optional[str]
    status: str

class ReassignRequest(BaseModel):
    new_user_id: int