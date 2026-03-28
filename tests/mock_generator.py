import random
from faker import Faker
from src.app.db import get_db_session
from src.app.models import User, FuelCard, Car

fake = Faker('ru_RU')

def create_random_test_entities(target_tg_id: int):
    with get_db_session() as db:
        # 1. Ищем пользователя
        user = db.query(User).filter_by(telegram_id=target_tg_id).first()
        if not user:
            print(f"👤 Создаю нового пользователя {target_tg_id}...")
            user = User(
                full_name=fake.name(),
                telegram_id=target_tg_id,
                active=True,
                cars=[],   # Инициализируем списки, чтобы профиль не ломался
                cards=[]
            )
            db.add(user)
            db.flush()
        else:
            print(f"👤 Пользователь {user.full_name} найден.")

        # 2. ЛОГИКА КАРТ: берем существующую или создаем одну навсегда
        card = db.query(FuelCard).filter_by(user_id=user.id).first()
        if not card:
            card_num = str(fake.random_number(digits=8, fix_len=True))
            card = FuelCard(card_number=card_num, user_id=user.id)
            db.add(card)
            db.flush()
        else:
            card_num = card.card_number

        # Синхронизируем с профилем пользователя (JSON поле)
        user_cards = list(user.cards or [])
        if card_num not in user_cards:
            user_cards.append(card_num)
            user.cards = user_cards

        # 3. ЛОГИКА АВТО: берем существующее или создаем одно
        user_cars_list = list(user.cars or [])
        if user_cars_list:
            plate = user_cars_list[0] # Берем первое авто из списка пользователя
        else:
            plate = f"{fake.random_int(1000, 9999)} {fake.lexify('??').upper()}-7"
            new_car = Car(plate=plate, owners=[user.id])
            db.add(new_car)
            user_cars_list.append(plate)
            user.cars = user_cars_list
            db.flush()

        db.commit()

        print(f"✅ Тест-кейс готов:")
        print(f"   💳 Рабочая карта: {card_num}")
        print(f"   🚗 Рабочее авто: {plate}")

        return card_num, plate