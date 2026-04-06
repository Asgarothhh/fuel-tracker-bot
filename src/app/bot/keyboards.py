"""Тексты reply-кнопок и сборка клавиатур."""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- Пользователь ---
BTN_USER_PROFILE = "👤 Мой профиль"
BTN_USER_LINK_ACCOUNT = "🔗 Ввести код привязки"
BTN_USER_CHANGE_CARD = "💳 Сменить карту"
BTN_USER_CARS = "🚗 Мои авто" # Новая кнопка
BTN_USER_LINK_HELP = "🔑 Как привязать аккаунт"
BTN_USER_SEND_CHECK = "📸 Отправить чек"
BTN_USER_HELP = "❓ Помощь"
BTN_USER_HOME = "🏠 Главное меню"
BTN_USER_PENDING = "⏳ Мои уведомления"


# --- Администратор ---
BTN_ADMIN_IMPORT = "📥 Обновить импорт"
BTN_ADMIN_IMPORT_TEST = "🔎 Тестовый импорт"
BTN_ADMIN_SCHEDULES = "🗓 Расписания"
BTN_ADMIN_SCHEDULE_SET = "➕ Установить расписание"
BTN_ADMIN_SCHEDULE_DEL = "🗑 Удалить расписание"
BTN_ADMIN_USERS = "👥 Пользователи"
BTN_ADMIN_PENDING = "📋 Неподтверждённые"
BTN_ADMIN_DISPUTED = "⚠️ Спорные" # Новая кнопка
BTN_ADMIN_RECENT = "🕒 Последние операции" # Новая кнопка
BTN_ADMIN_EXPORT_EXCEL = "📊 Экспорт в Excel"
BTN_ADMIN_GEN_CODE = "🔐 Сгенерировать код"
BTN_ADMIN_EXPORT_CODES = "📤 Экспорт кодов"
BTN_ADMIN_HELP = "📖 Справка администратора"
BTN_ADMIN_HOME = "🏠 Админ-меню"

def reply_keyboard_user() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_USER_PENDING), KeyboardButton(text=BTN_USER_SEND_CHECK)],
            [KeyboardButton(text=BTN_USER_PROFILE), KeyboardButton(text=BTN_USER_CARS)],
            [KeyboardButton(text=BTN_USER_HELP), KeyboardButton(text=BTN_USER_LINK_HELP)],
            [KeyboardButton(text=BTN_USER_CHANGE_CARD)],
            [KeyboardButton(text=BTN_USER_LINK_ACCOUNT)]
        ],
        resize_keyboard=True,
    )

# src/app/bot/keyboards.py

def reply_keyboard_unauthorized() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_USER_LINK_ACCOUNT)], # Та самая кнопка
            [KeyboardButton(text=BTN_USER_HELP)]
        ],
        resize_keyboard=True,
    )

def reply_keyboard_admin() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_ADMIN_IMPORT), KeyboardButton(text=BTN_ADMIN_PENDING)],
            [KeyboardButton(text=BTN_ADMIN_DISPUTED), KeyboardButton(text=BTN_ADMIN_RECENT)],
            [KeyboardButton(text=BTN_ADMIN_SCHEDULES), KeyboardButton(text=BTN_ADMIN_USERS)],
            [KeyboardButton(text=BTN_ADMIN_SCHEDULE_SET), KeyboardButton(text=BTN_ADMIN_SCHEDULE_DEL)], # Вернули кнопки расписания
            [KeyboardButton(text=BTN_ADMIN_EXPORT_EXCEL), KeyboardButton(text=BTN_ADMIN_HELP)],
        ],
        resize_keyboard=True,
    )

def get_operation_confirm_keyboard(operation_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"op_confirm:{operation_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"op_reject:{operation_id}")
            ]
        ]
    )

def get_ocr_confirm_kb(op_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"ocr_confirm_{op_id}"),
        InlineKeyboardButton(text="✏️ Исправить", callback_data=f"ocr_edit_{op_id}"),
        InlineKeyboardButton(text="❌ Отменить", callback_data=f"ocr_cancel_{op_id}")
    )
    return builder.as_markup()

def get_car_selection_kb(cars: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for car in cars:
        builder.row(InlineKeyboardButton(text=f"🚗 {getattr(car, 'gov_number', car)}", callback_data=f"select_car_{getattr(car, 'id', 0)}"))
    return builder.as_markup()

def get_fuel_card_confirm_kb(op_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да, это я", callback_data=f"fuel_card_yes_{op_id}"),
        InlineKeyboardButton(text="❌ Нет, не я", callback_data=f"fuel_card_no_{op_id}")
    )
    return builder.as_markup()

def get_admin_user_view_kb(user_id: int, is_active: bool) -> InlineKeyboardMarkup:
    toggle_text = "❌ Заблокировать" if is_active else "✅ Разблокировать"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Сгенерировать код", callback_data=f"gen_code:{user_id}")],
            [InlineKeyboardButton(text=toggle_text, callback_data=f"toggle_active:{user_id}")],
            [InlineKeyboardButton(text="Закрыть", callback_data="noop")]
        ]
    )