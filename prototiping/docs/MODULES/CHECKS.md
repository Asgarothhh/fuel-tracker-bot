# Пакет `prototiping.checks`

Два модуля: **`suite.py`** — исполняемые проверки и список **`ALL_CHECKS`**; **`scenarios.py`** — метаданные для таблицы и деталей в `REPORT.md`.

---

## `checks/scenarios.py`

### класс `ScenarioMeta` (TypedDict)

Структура одной записи в `SCENARIO_META`:

| Поле | Тип | Назначение |
|------|-----|------------|
| `id` | `str` | Код сценария в отчёте: `S01`, `S02`, … по порядку прогона графа |
| `graph_node` | `str` | `id` узла из `graph/spec.py` (для справки в тексте) |
| `title` | `str` | Заголовок в отчёте |
| `code_under_test` | `str` | Краткая отсылка к файлам/функциям (Markdown) |
| `description` | `str` | Развёрнутое описание для читателя отчёта |

**Пример записи:**

```python
"check_parse_api_datetime": {
    "id": "S03",
    "graph_node": "belorusneft_parse",
    "title": "Разбор даты/времени из строки API",
    "code_under_test": "`src/app/import_logic.py` → `parse_api_datetime()`",
    "description": "ISO-строка с суффиксом `Z` …",
},
```

---

### константа `SCENARIO_META`

Словарь **`имя_функции` → `ScenarioMeta`**. Ключ **обязан** совпадать с `check_что_то.__name__`.

**Пример чтения из кода отчёта:**

```python
from prototiping.checks.scenarios import SCENARIO_META

meta = SCENARIO_META["check_tokens_flow"]
assert meta["id"] == "S13"
```

---

## `checks/suite.py`

### `_result(name, ok, detail="")`

Унифицированный ответ проверки для графа и отчёта.

**Параметры:**

| Имя | Тип | Описание |
|-----|-----|----------|
| `name` | `str` | Короткое имя шага |
| `ok` | `bool` | Успех / провал |
| `detail` | `str` | Пояснение (обязательно полезно при `ok=False`) |

**Возвращает:** `dict` с ключами `name`, `ok`, `detail`.

**Пример:**

```python
from prototiping.checks.suite import _result

def check_my_step() -> dict:
    if 1 + 1 != 2:
        return _result("my_step", False, "math broken")
    return _result("my_step", True, "ok")
```

---

### `ALL_CHECKS`

Список **всех** функций проверок **в том же составе**, что объединение списков `checks` в `GRAPH_NODES_SPEC`. Порядок в списке должен совпадать с порядком обхода узлов и проверок в спеке (иначе `verify_spec_matches_all_checks()` выбросит ошибку).

**Пример:**

```python
from prototiping.checks.suite import ALL_CHECKS

names = [f.__name__ for f in ALL_CHECKS]
assert "check_parse_operations_items" in names
```

---

### Функции `check_*` (сценарии S01–S15)

Каждая **без аргументов**, возвращает **`_result(...)`**. Ниже — краткий справочник; полные заголовки и описания см. в `scenarios.py`.

| Функция | Код | Суть |
|---------|-----|------|
| `check_parse_operations_items` | S01 | `parse_operations` + ветка `items` |
| `check_parse_operations_cardlist` | S02 | `parse_operations` + `cardList`/`issueRows` |
| `check_parse_api_datetime` | S03 | `parse_api_datetime` + суффикс `Z` |
| `check_api_local_yesterday` | S04 | `api_local_yesterday_datetime` |
| `check_parse_operations_empty_items_fallback_cardlist` | S05 | пустой `items`, данные в `cardList` |
| `check_parse_api_datetime_invalid_inputs` | S06 | мусор в `parse_api_datetime` → `None` |
| `check_normalize_plate` | S07 | `normalize_plate` / `plates_equal` |
| `check_extract_flat_and_duplicate` | S08 | `extract_flat_fields` + дедуп в БД |
| `check_extract_flat_fields_malformed_raw` | S09 | `raw.row` не словарь |
| `check_import_api_operations_dry_run` | S10 | `import_api_operations(..., dry_run=True)` |
| `check_import_skips_without_date_and_doc` | S11 | пропуск строки без даты и чека |
| `check_user_has_permission` | S12 | `user_has_permission` |
| `check_tokens_flow` | S13 | токены привязки Telegram |
| `check_receipt_schema` | S14 | Pydantic `ReceiptData` |
| `check_excel_operation_row` | S15 | `_operation_row` для Excel |

**Пример прямого вызова одной проверки (отладка):**

```python
from prototiping.checks.suite import check_parse_api_datetime

r = check_parse_api_datetime()
assert r["ok"] is True
print(r["detail"])
```

**Пример в стиле pytest (как в `tests/test_prototype_graph.py`):**

```python
from prototiping.checks.suite import check_tokens_flow

def test_tokens():
    r = check_tokens_flow()
    assert r.get("ok"), r
```

---

## Экспорт `checks/__init__.py`

```python
from prototiping.checks import ALL_CHECKS
```

---

← [Оглавление](../README.md)
