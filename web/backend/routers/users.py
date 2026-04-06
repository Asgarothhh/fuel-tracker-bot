from fastapi import APIRouter, Depends, HTTPException
from web.backend.schemas import UserResponse, UserEditRequest
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from web.backend.dependencies import get_db
from src.app.models import User, Role

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("", response_model=list[UserResponse])
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.id).all()
    return users


@router.get("/")
def get_all_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    result = []
    for u in users:
        result.append({
            "id": u.id,
            "full_name": u.full_name,
            "role": u.role.role_name if u.role else "Водитель",
            "cars": u.cars if u.cars else [], # Это JSON поле из твоей модели
            "active": u.active,
            "telegram_id": u.telegram_id
        })
    return result

@router.put("/{user_id}", response_model=UserResponse)
def edit_user(user_id: int, payload: UserEditRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user: raise HTTPException(status_code=404, detail="User not found")

    user.full_name = payload.full_name
    user.active = payload.active
    user.role_id = payload.role_id
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user: raise HTTPException(status_code=404, detail="User not found")
    # Можно использовать soft delete (user.active = False), но раз просили удалять:
    db.delete(user)
    db.commit()
    return {"status": "success"}