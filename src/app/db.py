# src/app/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.app.models import Base
from src.app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def init_db():
    # Создаёт все таблицы, если их нет
    Base.metadata.create_all(bind=engine)

# Контекстный менеджер для сессий
from contextlib import contextmanager

@contextmanager
def get_db_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
