from src.app.db import get_db_session


# Эта функция будет выдавать сессию БД для каждого API запроса
def get_db():
    with get_db_session() as db:
        yield db