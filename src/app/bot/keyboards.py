"""Тексты reply-кнопок и сборка клавиатур (единое место, без расхождений с регистрацией)."""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- Пользователь ---
BTN_USER_PROFILE = "👤 Мой профиль"
BTN_USER_LINK_HELP = "🔑 Как привязать аккаунт"
BTN_USER_SEND_CHECK = "📸 Отправить чек"
BTN_USER_HELP = "❓ Помощь"
BTN_USER_HOME = "🏠 Главное меню"

# --- Администратор ---
BTN_ADMIN_IMPORT = "📥 Обновить импорт"
BTN_ADMIN_IMPORT_TEST = "🔎 Тестовый импорт"
BTN_ADMIN_SCHEDULES = "🗓 Расписания"
BTN_ADMIN_SCHEDULE_SET = "➕ Установить расписание"
BTN_ADMIN_SCHEDULE_DEL = "🗑 Удалить расписание"
BTN_ADMIN_USERS = "👥 Пользователи"
BTN_ADMIN_PENDING = "📋 Неподтверждённые"
BTN_ADMIN_EXPORT_EXCEL = "📊 Экспорт в Excel"
BTN_ADMIN_GEN_CODE = "🔐 Сгенерировать код"
BTN_ADMIN_EXPORT_CODES = "📤 Экспорт кодов"
BTN_ADMIN_HELP = "📖 Справка администратора"
BTN_ADMIN_HOME = "🏠 Админ-меню"


def reply_keyboard_user() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_USER_PROFILE), KeyboardButton(text=BTN_USER_LINK_HELP)],
            [KeyboardButton(text=BTN_USER_HELP), KeyboardButton(text=BTN_USER_HOME)],
        ],
        resize_keyboard=True,
    )


def reply_keyboard_admin() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_ADMIN_IMPORT), KeyboardButton(text=BTN_ADMIN_IMPORT_TEST)],
            [KeyboardButton(text=BTN_ADMIN_SCHEDULES), KeyboardButton(text=BTN_ADMIN_SCHEDULE_SET)],
            [KeyboardButton(text=BTN_ADMIN_SCHEDULE_DEL), KeyboardButton(text=BTN_ADMIN_USERS)],
            [KeyboardButton(text=BTN_ADMIN_PENDING), KeyboardButton(text=BTN_ADMIN_EXPORT_EXCEL)],
            [KeyboardButton(text=BTN_ADMIN_GEN_CODE), KeyboardButton(text=BTN_ADMIN_EXPORT_CODES)],
            [KeyboardButton(text=BTN_ADMIN_HELP), KeyboardButton(text=BTN_ADMIN_HOME)],
        ],
        resize_keyboard=True,
    )


def get_ocr_confirm_kb(op_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения данных OCR"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"ocr_confirm_{op_id}"),
        InlineKeyboardButton(text="✏️ Исправить", callback_data=f"ocr_edit_{op_id}"),
        InlineKeyboardButton(text="❌ Отменить", callback_data=f"ocr_cancel_{op_id}")
    )

    return builder.as_markup()


def get_car_selection_kb(cars: list) -> InlineKeyboardMarkup:
    """Выбор автомобиля из списка"""
    builder = InlineKeyboardBuilder()
    for car in cars:
        # car может быть объектом модели с полями id и gov_number
        builder.row(InlineKeyboardButton(text=f"🚗 {car.gov_number}", callback_data=f"select_car_{car.id}"))
    return builder.as_markup()


def get_fuel_card_confirm_kb(op_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения заправки по картe"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да, это я", callback_data=f"fuel_card_yes_{op_id}"),
        InlineKeyboardButton(text="❌ Нет, не я", callback_data=f"fuel_card_no_{op_id}")
    )
    return builder.as_markup()
