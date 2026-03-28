from src.app.db import get_db_session
from src.app.models import User, FuelCard, Car, FuelOperation

def clear_test_data():
    """Удаляет всех пользователей и связанные данные."""
    with get_db_session() as db:
        # Включаем каскадное удаление, если оно не настроено в БД,
        # или просто удаляем всё по порядку
        db.query(FuelOperation).delete()
        db.query(FuelCard).delete()
        db.query(Car).delete()
        db.query(User).delete()
        db.commit()
        print("🗑 База данных очищена от тестовых записей.")

if __name__ == "__main__":
    clear_test_data()