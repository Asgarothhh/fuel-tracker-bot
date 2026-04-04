"""SQLite in-memory engine shared across a single test session (StaticPool)."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.app.models import Base, User, Role, Permission, role_permissions


def make_memory_engine():
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        pool_pre_ping=True,
    )


def make_session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_schema(engine) -> None:
    Base.metadata.create_all(bind=engine)


@contextmanager
def memory_db_session() -> Generator[Session, None, None]:
    engine = make_memory_engine()
    init_schema(engine)
    factory = make_session_factory(engine)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        engine.dispose()


def seed_admin_permission(session: Session) -> tuple[User, Role, Permission]:
    perm = Permission(name="admin:manage", description="test")
    role = Role(role_name="admin", description="test")
    role.permissions.append(perm)
    session.add_all([perm, role])
    session.flush()
    user = User(
        full_name="Admin User",
        telegram_id=100001,
        active=True,
        role_id=role.id,
        cars=[],
        cards=[],
        extra_ids={},
    )
    session.add(user)
    session.flush()
    return user, role, perm
