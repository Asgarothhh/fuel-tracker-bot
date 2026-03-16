# src/app/models.py
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, Table, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime, timezone

Base = declarative_base()

# Association Role <-> Permission (many-to-many)
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)

class Permission(Base):
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)  # e.g., "admin:manage"
    description = Column(String(255))

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    role_name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255))
    permissions = relationship("Permission", secondary=role_permissions, backref="roles")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)  # внутренний ID
    telegram_id = Column(Integer, unique=True, nullable=True)
    full_name = Column(String(255), nullable=False)
    short_name = Column(String(100))
    active = Column(Boolean, default=True)
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="SET NULL"), nullable=True)
    role = relationship("Role", backref="users")
    cars = Column(JSON, default=[])   # список госномеров
    cards = Column(JSON, default=[])  # список номеров карт
    extra_ids = Column(JSON, default={})  # дополнительные идентификаторы

class Car(Base):
    __tablename__ = "cars"
    id = Column(Integer, primary_key=True)
    plate = Column(String(50), nullable=False, index=True)  # государственный номер
    model = Column(String(255))
    owners = Column(JSON, default=[])  # список user_id

class FuelCard(Base):
    __tablename__ = "fuel_cards"
    id = Column(Integer, primary_key=True)
    card_number = Column(String(100), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    user = relationship("User", backref="fuel_cards")
    car_id = Column(Integer, ForeignKey("cars.id", ondelete="SET NULL"))
    car = relationship("Car", backref="fuel_cards")
    active = Column(Boolean, default=True)

class FuelOperation(Base):
    __tablename__ = "fuel_operations"
    id = Column(Integer, primary_key=True)
    source = Column(String(50))  # 'belorusneft_api' or 'personal_receipt'
    api_data = Column(JSON, nullable=True)
    ocr_data = Column(JSON, nullable=True)
    presumed_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    presumed_user = relationship("User", foreign_keys=[presumed_user_id])
    confirmed_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    confirmed_user = relationship("User", foreign_keys=[confirmed_user_id])
    car_from_api = Column(String(50))
    actual_car = Column(String(50))
    imported_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    confirmed_at = Column(DateTime, nullable=True)
    exported_to_excel = Column(Boolean, default=False)
    ready_for_waybill = Column(Boolean, default=False)
    status = Column(String(50), default="new")

class ConfirmationHistory(Base):
    __tablename__ = "confirmation_history"
    id = Column(Integer, primary_key=True)
    operation_id = Column(Integer, ForeignKey("fuel_operations.id", ondelete="CASCADE"))
    operation = relationship("FuelOperation", backref="history")
    to_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    to_user = relationship("User")
    answer = Column(String(50))  # 'yes','no','cancel'
    answered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    comment = Column(Text)
    stage_result = Column(String(100))

class LinkToken(Base):
    __tablename__ = "link_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user = relationship("User", backref="link_tokens")
    code_hash = Column(String(128), nullable=False, index=True)  # sha256(code)
    # OPTIONAL: если хотите показывать код один раз, не храните plain в БД.
    created_by = Column(Integer, nullable=True)  # id администратора
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False, default="new")  # new, used, expired, revoked
    telegram_id = Column(Integer, nullable=True, index=True)  # заполняется при авторизации
    used_at = Column(DateTime, nullable=True)
    note = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("code_hash", name="uq_linktoken_codehash"),
        Index("ix_linktokens_status_expires", "status", "expires_at"),
    )

