"""
Метаданные сценариев для отчёта: что проверяется, какой код задействован.
Ключ — имя функции из prototiping.checks.suite.

Поле ``id`` (S01, S02, …) нумеруется **в порядке прогона** ``graph/spec.GRAPH_NODES_SPEC``
(узел за узлом, проверка за проверкой), чтобы в отчёте коды шли подряд.
"""
from __future__ import annotations

from typing import TypedDict


class ScenarioMeta(TypedDict):
    """Метаданные одного сценария для таблицы и детализации отчёта.

    Ключ в ``SCENARIO_META`` — ``__name__`` функции ``check_*`` из ``checks.suite``.
    """

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
    "check_parse_operations_empty_items_fallback_cardlist": {
        "id": "S05",
        "graph_node": "belorusneft_parse",
        "title": "Пустой `items` и при этом рабочий `cardList`",
        "code_under_test": "`src/app/belorusneft_api.py` → `parse_operations()`",
        "description": "Выражение `items or data` даёт «пусто»; парсер должен перейти к `cardList`. Иначе реальный ответ API с пустым массивом и данными в картах молча теряется.",
    },
    "check_parse_api_datetime_invalid_inputs": {
        "id": "S06",
        "graph_node": "belorusneft_parse",
        "title": "Некорректные входы `parse_api_datetime`",
        "code_under_test": "`src/app/import_logic.py` → `parse_api_datetime()`",
        "description": "Пустые строки, не-даты, числа, нестроковые объекты — только `None`, без исключений; иначе один битый атрибут в JSON валит весь импорт.",
    },
    "check_normalize_plate": {
        "id": "S07",
        "graph_node": "plates_import",
        "title": "Нормализация госномеров",
        "code_under_test": "`src/app/plate_util.py` → `normalize_plate()`, `plates_equal()`",
        "description": "Удаление пробелов и дефисов, сравнение номеров без учёта форматирования.",
    },
    "check_extract_flat_and_duplicate": {
        "id": "S08",
        "graph_node": "plates_import",
        "title": "Плоские поля и дедупликация импорта API",
        "code_under_test": "`src/app/import_logic.py` → `extract_flat_fields()`, `is_duplicate_api_operation()`",
        "description": "Извлечение карты/АЗС/продукт/кол-ва и обнаружение уже сохранённой операции с тем же составным ключом.",
    },
    "check_extract_flat_fields_malformed_raw": {
        "id": "S09",
        "graph_node": "plates_import",
        "title": "`raw.row` не объект (список/мусор)",
        "code_under_test": "`src/app/import_logic.py` → `extract_flat_fields()`",
        "description": "Если `issueRows` когда-то придёт не тем типом в `raw`, доступ к полям через `row` не должен падать: верхний уровень операции остаётся источником правды.",
    },
    "check_import_api_operations_dry_run": {
        "id": "S10",
        "graph_node": "plates_import",
        "title": "Импорт операций из JSON (dry_run)",
        "code_under_test": "`src/app/import_logic.py` → `import_api_operations(..., dry_run=True)`",
        "description": "Создание операции, привязка пользователя по карте, список уведомлений в Telegram без commit в БД.",
    },
    "check_import_skips_without_date_and_doc": {
        "id": "S11",
        "graph_node": "plates_import",
        "title": "Пропуск строки без даты и без чека",
        "code_under_test": "`src/app/import_logic.py` → `import_api_operations()`",
        "description": "Строка только с продуктом/АЗС без `dateTimeIssue` и `docNumber` должна пропускаться; следующая валидная строка в том же `issueRows` всё равно импортируется (`new_count` не обнуляется целиком).",
    },
    "check_user_has_permission": {
        "id": "S12",
        "graph_node": "auth_permissions",
        "title": "Проверка прав по роли",
        "code_under_test": "`src/app/permissions.py` → `user_has_permission()`",
        "description": "Администратор с ролью и permission `admin:manage`; отказ для несуществующего права и неизвестного пользователя.",
    },
    "check_tokens_flow": {
        "id": "S13",
        "graph_node": "auth_permissions",
        "title": "Коды привязки Telegram",
        "code_under_test": "`src/app/tokens.py` → `create_bulk_codes()`, `verify_and_consume_code()`",
        "description": "Выпуск кода, проверка хэша, пометка токена использованным, запись `telegram_id` у пользователя.",
    },
    "check_receipt_schema": {
        "id": "S14",
        "graph_node": "excel_ocr",
        "title": "Схема данных чека (OCR)",
        "code_under_test": "`src/ocr/schemas.py` → модель `ReceiptData`",
        "description": "Валидация и сериализация типичного набора полей после распознавания чека.",
    },
    "check_excel_operation_row": {
        "id": "S15",
        "graph_node": "excel_ocr",
        "title": "Строка отчёта для Excel",
        "code_under_test": "`src/app/excel_export.py` → `_operation_row()`",
        "description": "Сборка строки по ширине `HEADERS`, подстановка пользователя и типа заправки для операции из API.",
    },
}
