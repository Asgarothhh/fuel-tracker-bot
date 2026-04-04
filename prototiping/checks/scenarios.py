"""
Метаданные сценариев для отчёта: что проверяется, какой код задействован.
Ключ — имя функции из prototiping.checks.suite.
"""
from __future__ import annotations

from typing import TypedDict


class ScenarioMeta(TypedDict):
    id: str
    graph_node: str
    title: str
    code_under_test: str
    description: str


SCENARIO_META: dict[str, ScenarioMeta] = {
    "check_parse_operations_items": {
        "id": "S01",
        "graph_node": "belorusneft_parse",
        "title": "Парсинг ответа API: ветка items/data",
        "code_under_test": "`src/app/belorusneft_api.py` → `parse_operations()`",
        "description": "Проверка разбора JSON с массивом `items`: дата, продукт, чек, карта, госномер.",
    },
    "check_parse_operations_cardlist": {
        "id": "S02",
        "graph_node": "belorusneft_parse",
        "title": "Парсинг ответа API: cardList / issueRows",
        "code_under_test": "`src/app/belorusneft_api.py` → `parse_operations()`",
        "description": "Текущая структура ответа Белоруснефти: вложенные `issueRows`, номер карты с уровня `cardList`.",
    },
    "check_parse_api_datetime": {
        "id": "S03",
        "graph_node": "belorusneft_parse",
        "title": "Разбор даты/времени из строки API",
        "code_under_test": "`src/app/import_logic.py` → `parse_api_datetime()`",
        "description": "ISO-строка с суффиксом `Z` корректно превращается в `datetime` с timezone.",
    },
    "check_api_local_yesterday": {
        "id": "S04",
        "graph_node": "belorusneft_parse",
        "title": "Календарное «вчера» в зоне UTC+3",
        "code_under_test": "`src/app/import_logic.py` → `api_local_yesterday_datetime()`",
        "description": "Дата для запросов к API в локальной зоне контракта (смещение +3 ч от UTC).",
    },
    "check_normalize_plate": {
        "id": "S05",
        "graph_node": "plates_import",
        "title": "Нормализация госномеров",
        "code_under_test": "`src/app/plate_util.py` → `normalize_plate()`, `plates_equal()`",
        "description": "Удаление пробелов и дефисов, сравнение номеров без учёта форматирования.",
    },
    "check_extract_flat_and_duplicate": {
        "id": "S06",
        "graph_node": "plates_import",
        "title": "Плоские поля и дедупликация импорта API",
        "code_under_test": "`src/app/import_logic.py` → `extract_flat_fields()`, `is_duplicate_api_operation()`",
        "description": "Извлечение карты/АЗС/продукт/кол-ва и обнаружение уже сохранённой операции с тем же составным ключом.",
    },
    "check_import_api_operations_dry_run": {
        "id": "S07",
        "graph_node": "plates_import",
        "title": "Импорт операций из JSON (dry_run)",
        "code_under_test": "`src/app/import_logic.py` → `import_api_operations(..., dry_run=True)`",
        "description": "Создание операции, привязка пользователя по карте, список уведомлений в Telegram без commit в БД.",
    },
    "check_user_has_permission": {
        "id": "S08",
        "graph_node": "auth_permissions",
        "title": "Проверка прав по роли",
        "code_under_test": "`src/app/permissions.py` → `user_has_permission()`",
        "description": "Администратор с ролью и permission `admin:manage`; отказ для несуществующего права и неизвестного пользователя.",
    },
    "check_tokens_flow": {
        "id": "S09",
        "graph_node": "auth_permissions",
        "title": "Коды привязки Telegram",
        "code_under_test": "`src/app/tokens.py` → `create_bulk_codes()`, `verify_and_consume_code()`",
        "description": "Выпуск кода, проверка хэша, пометка токена использованным, запись `telegram_id` у пользователя.",
    },
    "check_receipt_schema": {
        "id": "S10",
        "graph_node": "excel_ocr",
        "title": "Схема данных чека (OCR)",
        "code_under_test": "`src/ocr/schemas.py` → модель `ReceiptData`",
        "description": "Валидация и сериализация типичного набора полей после распознавания чека.",
    },
    "check_excel_operation_row": {
        "id": "S11",
        "graph_node": "excel_ocr",
        "title": "Строка отчёта для Excel",
        "code_under_test": "`src/app/excel_export.py` → `_operation_row()`",
        "description": "Сборка строки по ширине `HEADERS`, подстановка пользователя и типа заправки для операции из API.",
    },
}
