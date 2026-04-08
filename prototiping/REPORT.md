# Отчёт прототипирования: fuel-tracker-bot

**Дата генерации:** 2026-04-08 18:35 UTC



*Граф:* `fuel_tracker_prototype` — итог прогона: **корректно** (36 корректно / 0 некорректно по сценариям).


## 1. Сводка

| Показатель | Значение |
|------------|----------|
| Всего сценариев | 36 |
| Результат **корректен** | 36 |
| Результат **с ошибкой** | 0 |
| **TP** (standard + OK) | 25 |
| **FN** (standard + FAIL) | 0 |
| **TN** (breaker + FAIL) | 11 |
| **FP** (breaker + OK) | 0 |
| Версия схемы сценариев | 2 |
| Legacy-сценариев (устаревшая версия) | 0 |

### Матрица P/N (как confusion matrix)

Обозначения: **P** — позитивные тесты (должны проходить), **N** — негативные/ломающие тесты (должны падать).  
Столбец **actual**: `+` = тест прошёл (`ok=True`), `-` = тест упал (`ok=False`).

| predicted \ actual | P (+) | N (-) |
|---|---:|---:|
| **P** (ожидаем PASS) | **TP = 25** | **FN = 0** |
| **N** (ожидаем FAIL) | **FP = 0** | **TN = 11** |

Трассировка (LangSmith): при `LANGCHAIN_TRACING_V2=true` и заданном `LANGCHAIN_API_KEY` прогоны LangGraph и узлов с `@traceable` попадают в проект LangSmith.

---

## 2. Граф сценариев

Ниже: **таблица узлов**, цепочка в одну строку, **ASCII-схема** (читается в любом просмотрщике), компактный Mermaid и ссылка на HTML-preview.

Граф **`fuel_tracker_prototype`**: узлы выполняются **сверху вниз** (как в LangGraph). Сырая диаграмма Mermaid ниже в части просмотрщиков показывается как текст — тогда откройте сгенерированный **HTML** (команда в конце раздела) или IDE с Mermaid.

### Таблица узлов

| № | ID узла | Описание | Проверок OK | Всего проверок | мс | Узел |
|---|---------|----------|-------------|----------------|-----|------|
| 1 | `belorusneft_parse` | Парсинг API / даты (Belorusneft) | 6 | 6 | 2.19 | **да** |
| 2 | `plates_import` | Номера, импорт API, дедупликация | 5 | 5 | 47.04 | **да** |
| 3 | `auth_permissions` | Права и токены привязки | 2 | 2 | 19.3 | **да** |
| 4 | `excel_ocr` | Схема чека и строка Excel | 2 | 2 | 10.79 | **да** |
| 5 | `web_backend` | Web backend: роутеры и сервисы | 10 | 15 | 93.39 | **да** |
| 6 | `breaker_probes` | Негативные (ломающие) сценарии | 0 | 6 | 1164.49 | **да** |

### Цепочка (одна строка)

`belorusneft_parse` ✓ (2.19 ms) → `plates_import` ✓ (47.04 ms) → `auth_permissions` ✓ (19.3 ms) → `excel_ocr` ✓ (10.79 ms) → `web_backend` ✓ (93.39 ms) → `breaker_probes` ✓ (1164.49 ms)

### Порядок выполнения

1. **belorusneft_parse** — успех (2.19 ms): _Парсинг API / даты (Belorusneft)_
2. **plates_import** — успех (47.04 ms): _Номера, импорт API, дедупликация_
3. **auth_permissions** — успех (19.3 ms): _Права и токены привязки_
4. **excel_ocr** — успех (10.79 ms): _Схема чека и строка Excel_
5. **web_backend** — успех (93.39 ms): _Web backend: роутеры и сервисы_
6. **breaker_probes** — успех (1164.49 ms): _Негативные (ломающие) сценарии_

### Схема (ASCII)

```text
  [старт]
      |
      v
  +-- belorusneft_parse  [OK]  2.19 ms
      |
      v
  +-- plates_import  [OK]  47.04 ms
      |
      v
  +-- auth_permissions  [OK]  19.3 ms
      |
      v
  +-- excel_ocr  [OK]  10.79 ms
      |
      v
  +-- web_backend  [OK]  93.39 ms
      |
      v
  +-- breaker_probes  [OK]  1164.49 ms
      |
      v
  [конец]
```

### Диаграмма Mermaid (компактная)

```mermaid
%% prototiping.reporting.diagram
flowchart LR
  N0["belorusneft_parse / OK / 2.19ms"]:::okNode
  N1["plates_import / OK / 47.04ms"]:::okNode
  N2["auth_permissions / OK / 19.3ms"]:::okNode
  N3["excel_ocr / OK / 10.79ms"]:::okNode
  N4["web_backend / OK / 93.39ms"]:::okNode
  N5["breaker_probes / OK / 1164.49ms"]:::okNode
  classDef okNode fill:#1a472a,stroke:#234,color:#e8ffe8
  classDef failNode fill:#6b1c1c,stroke:#422,color:#ffe8e8
  N0 --> N1
  N1 --> N2
  N2 --> N3
  N3 --> N4
  N4 --> N5
```

### Интерактивная диаграмма

Сгенерируйте HTML с корректным рендером:

```bash
PYTHONPATH=. python -m prototiping.tools.graph_preview
```

Файл: `prototiping/output/graph_preview.html` (откройте в браузере).


---

## 3. Сценарии: проверяемый код и статус

**№** — порядок прогона в графе (узлы сверху вниз, проверки внутри узла как в `graph/spec.py`).  
**Класс:** `P` = позитивный тест, `N` = негативный (должен падать).  
**Факт:** `+` = тест прошёл, `-` = тест упал.

| № | Код | Класс | Факт | Тип | Версия | Узел графа | Сценарий | Проверяемый код | Корректно | При ошибке |
|---|-----|-------|------|-----|--------|------------|----------|-----------------|-----------|------------|
| 1 | S01 | P | + | standard | 2 | `belorusneft_parse` | Парсинг ответа API: ветка items/data | `src/app/belorusneft_api.py` → `parse_operations()` | да | — |
| 2 | S02 | P | + | standard | 2 | `belorusneft_parse` | Парсинг ответа API: cardList / issueRows | `src/app/belorusneft_api.py` → `parse_operations()` | да | — |
| 3 | S03 | P | + | standard | 2 | `belorusneft_parse` | Разбор даты/времени из строки API | `src/app/import_logic.py` → `parse_api_datetime()` | да | — |
| 4 | S04 | P | + | standard | 2 | `belorusneft_parse` | Календарное «вчера» в зоне UTC+3 | `src/app/import_logic.py` → `api_local_yesterday_datetime()` | да | — |
| 5 | S05 | P | + | standard | 2 | `belorusneft_parse` | Пустой `items` и при этом рабочий `cardList` | `src/app/belorusneft_api.py` → `parse_operations()` | да | — |
| 6 | S06 | P | + | standard | 2 | `belorusneft_parse` | Некорректные входы `parse_api_datetime` | `src/app/import_logic.py` → `parse_api_datetime()` | да | — |
| 7 | S07 | P | + | standard | 2 | `plates_import` | Нормализация госномеров | `src/app/plate_util.py` → `normalize_plate()`, `plates_equal()` | да | — |
| 8 | S08 | P | + | standard | 2 | `plates_import` | Плоские поля и дедупликация импорта API | `src/app/import_logic.py` → `extract_flat_fields()`, `is_duplicate_api_operation()` | да | — |
| 9 | S09 | P | + | standard | 2 | `plates_import` | `raw.row` не объект (список/мусор) | `src/app/import_logic.py` → `extract_flat_fields()` | да | — |
| 10 | S10 | P | + | standard | 2 | `plates_import` | Импорт операций из JSON (dry_run) | `src/app/import_logic.py` → `import_api_operations(..., dry_run=True)` | да | — |
| 11 | S11 | P | + | standard | 2 | `plates_import` | Пропуск строки без даты и без чека | `src/app/import_logic.py` → `import_api_operations()` | да | — |
| 12 | S12 | P | + | standard | 2 | `auth_permissions` | Проверка прав по роли | `src/app/permissions.py` → `user_has_permission()` | да | — |
| 13 | S13 | P | + | standard | 2 | `auth_permissions` | Коды привязки Telegram | `src/app/tokens.py` → `create_bulk_codes()`, `verify_and_consume_code()` | да | — |
| 14 | S14 | P | + | standard | 2 | `excel_ocr` | Схема данных чека (OCR) | `src/ocr/schemas.py` → модель `ReceiptData` | да | — |
| 15 | S15 | P | + | standard | 2 | `excel_ocr` | Строка отчёта для Excel | `src/app/excel_export.py` → `_operation_row()` | да | — |
| 16 | S22 | P | + | standard | 2 | `web_backend` | Web health endpoint | `web/backend/main.py` → `health_check()` | да | — |
| 17 | S23 | P | + | standard | 2 | `web_backend` | Web dependency get_db | `web/backend/dependencies.py` → `get_db()` | да | — |
| 18 | S24 | P | + | standard | 2 | `web_backend` | Web users list endpoint | `web/backend/routers/users.py` → `get_users()` | да | — |
| 19 | S25 | P | + | standard | 2 | `web_backend` | Web users role fallback | `web/backend/routers/users.py` → `get_all_users()` | да | — |
| 20 | S26 | P | + | standard | 2 | `web_backend` | Web edit user | `web/backend/routers/users.py` → `edit_user()` | да | — |
| 21 | S27 | P | + | standard | 2 | `web_backend` | Web delete user | `web/backend/routers/users.py` → `delete_user()` | да | — |
| 22 | S28 | P | + | standard | 2 | `web_backend` | Web format_operation mapping | `web/backend/routers/operations.py` → `format_operation()` | да | — |
| 23 | S29 | P | + | standard | 2 | `web_backend` | Web operations pending filter | `web/backend/routers/operations.py` → `get_operations()` | да | — |
| 24 | S30 | P | + | standard | 2 | `web_backend` | Web operation actions flow | `web/backend/routers/operations.py` → `confirm/reject/reassign` | да | — |
| 25 | S31 | P | + | standard | 2 | `web_backend` | Web excel report builder | `web/backend/services/excel_report.py` → `build_full_fuel_report_excel()` | да | — |
| 26 | S32 | N | - | breaker | 2 | `web_backend` | Breaker web: unknown tab | `web/backend/routers/operations.py` → `get_operations()` | да | — |
| 27 | S33 | N | - | breaker | 2 | `web_backend` | Breaker web: edit missing user | `web/backend/routers/users.py` → `edit_user()` | да | — |
| 28 | S34 | N | - | breaker | 2 | `web_backend` | Breaker web: delete missing operation | `web/backend/routers/operations.py` → `delete_operation()` | да | — |
| 29 | S35 | N | - | breaker | 2 | `web_backend` | Breaker web: reassign missing operation | `web/backend/routers/operations.py` → `reassign_operation()` | да | — |
| 30 | S36 | N | - | breaker | 2 | `web_backend` | Breaker web: excel on empty DB | `web/backend/routers/reports.py` → `download_full_excel_report()` | да | — |
| 31 | S16 | N | - | breaker | 2 | `breaker_probes` | Breaker: цикл импорта permissions/bot | `src/app/permissions.py` (probe import) | да | — |
| 32 | S17 | N | - | breaker | 2 | `breaker_probes` | Breaker: обход дедупа через формат АЗС | `src/app/import_logic.py` → `import_api_operations()`, `is_duplicate_api_operation()` | да | — |
| 33 | S18 | N | - | breaker | 2 | `breaker_probes` | Breaker: обход дедупа через регистр doc_number | `src/app/import_logic.py` → `import_api_operations()`, `is_duplicate_api_operation()` | да | — |
| 34 | S19 | N | - | breaker | 2 | `breaker_probes` | Breaker: обход дедупа через формат количества | `src/app/import_logic.py` → `import_api_operations()`, `is_duplicate_api_operation()` | да | — |
| 35 | S20 | N | - | breaker | 2 | `breaker_probes` | Breaker: маппинг пользователя по неактивной карте | `src/app/import_logic.py` → `import_api_operations()` | да | — |
| 36 | S21 | N | - | breaker | 2 | `breaker_probes` | Breaker: наивный datetime без timezone | `src/app/import_logic.py` → `parse_api_datetime()` | да | — |

---

## 4. Детали по сценариям

Нумерация заголовков совпадает с колонкой **№** в таблице выше.

### 1. Парсинг ответа API: ветка items/data

- **Код (scenarios):** `S01`
- **Класс (ожидаемо):** `P`
- **Факт:** `+`
- **Тип:** `standard`
- **Версия сценария:** `2`
- **Узел графа:** `belorusneft_parse`
- **Проверяемый код:** `src/app/belorusneft_api.py` → `parse_operations()`
- **Что проверяется:** Проверка разбора JSON с массивом `items`: дата, продукт, чек, карта, госномер.
- **Результат:** **Корректно**
- **Комментарий / детали:** items branch OK

### 2. Парсинг ответа API: cardList / issueRows

- **Код (scenarios):** `S02`
- **Класс (ожидаемо):** `P`
- **Факт:** `+`
- **Тип:** `standard`
- **Версия сценария:** `2`
- **Узел графа:** `belorusneft_parse`
- **Проверяемый код:** `src/app/belorusneft_api.py` → `parse_operations()`
- **Что проверяется:** Текущая структура ответа Белоруснефти: вложенные `issueRows`, номер карты с уровня `cardList`.
- **Результат:** **Корректно**
- **Комментарий / детали:** cardList/issueRows OK

### 3. Разбор даты/времени из строки API

- **Код (scenarios):** `S03`
- **Класс (ожидаемо):** `P`
- **Факт:** `+`
- **Тип:** `standard`
- **Версия сценария:** `2`
- **Узел графа:** `belorusneft_parse`
- **Проверяемый код:** `src/app/import_logic.py` → `parse_api_datetime()`
- **Что проверяется:** ISO-строка с суффиксом `Z` корректно превращается в `datetime` с timezone.
- **Результат:** **Корректно**
- **Комментарий / детали:** 2020-01-15 10:20:30+00:00

### 4. Календарное «вчера» в зоне UTC+3

- **Код (scenarios):** `S04`
- **Класс (ожидаемо):** `P`
- **Факт:** `+`
- **Тип:** `standard`
- **Версия сценария:** `2`
- **Узел графа:** `belorusneft_parse`
- **Проверяемый код:** `src/app/import_logic.py` → `api_local_yesterday_datetime()`
- **Что проверяется:** Дата для запросов к API в локальной зоне контракта (смещение +3 ч от UTC).
- **Результат:** **Корректно**
- **Комментарий / детали:** 2026-04-07T00:00:00

### 5. Пустой `items` и при этом рабочий `cardList`

- **Код (scenarios):** `S05`
- **Класс (ожидаемо):** `P`
- **Факт:** `+`
- **Тип:** `standard`
- **Версия сценария:** `2`
- **Узел графа:** `belorusneft_parse`
- **Проверяемый код:** `src/app/belorusneft_api.py` → `parse_operations()`
- **Что проверяется:** Выражение `items or data` даёт «пусто»; парсер должен перейти к `cardList`. Иначе реальный ответ API с пустым массивом и данными в картах молча теряется.
- **Результат:** **Корректно**
- **Комментарий / детали:** cardList used

### 6. Некорректные входы `parse_api_datetime`

- **Код (scenarios):** `S06`
- **Класс (ожидаемо):** `P`
- **Факт:** `+`
- **Тип:** `standard`
- **Версия сценария:** `2`
- **Узел графа:** `belorusneft_parse`
- **Проверяемый код:** `src/app/import_logic.py` → `parse_api_datetime()`
- **Что проверяется:** Пустые строки, не-даты, числа, нестроковые объекты — только `None`, без исключений; иначе один битый атрибут в JSON валит весь импорт.
- **Результат:** **Корректно**
- **Комментарий / детали:** garbage → None, no exception

### 7. Нормализация госномеров

- **Код (scenarios):** `S07`
- **Класс (ожидаемо):** `P`
- **Факт:** `+`
- **Тип:** `standard`
- **Версия сценария:** `2`
- **Узел графа:** `plates_import`
- **Проверяемый код:** `src/app/plate_util.py` → `normalize_plate()`, `plates_equal()`
- **Что проверяется:** Удаление пробелов и дефисов, сравнение номеров без учёта форматирования.
- **Результат:** **Корректно**
- **Комментарий / детали:** normalize + plates_equal OK

### 8. Плоские поля и дедупликация импорта API

- **Код (scenarios):** `S08`
- **Класс (ожидаемо):** `P`
- **Факт:** `+`
- **Тип:** `standard`
- **Версия сценария:** `2`
- **Узел графа:** `plates_import`
- **Проверяемый код:** `src/app/import_logic.py` → `extract_flat_fields()`, `is_duplicate_api_operation()`
- **Что проверяется:** Извлечение карты/АЗС/продукт/кол-ва и обнаружение уже сохранённой операции с тем же составным ключом.
- **Результат:** **Корректно**
- **Комментарий / детали:** dedup key OK

### 9. `raw.row` не объект (список/мусор)

- **Код (scenarios):** `S09`
- **Класс (ожидаемо):** `P`
- **Факт:** `+`
- **Тип:** `standard`
- **Версия сценария:** `2`
- **Узел графа:** `plates_import`
- **Проверяемый код:** `src/app/import_logic.py` → `extract_flat_fields()`
- **Что проверяется:** Если `issueRows` когда-то придёт не тем типом в `raw`, доступ к полям через `row` не должен падать: верхний уровень операции остаётся источником правды.
- **Результат:** **Корректно**
- **Комментарий / детали:** list row ignored

### 10. Импорт операций из JSON (dry_run)

- **Код (scenarios):** `S10`
- **Класс (ожидаемо):** `P`
- **Факт:** `+`
- **Тип:** `standard`
- **Версия сценария:** `2`
- **Узел графа:** `plates_import`
- **Проверяемый код:** `src/app/import_logic.py` → `import_api_operations(..., dry_run=True)`
- **Что проверяется:** Создание операции, привязка пользователя по карте, список уведомлений в Telegram без commit в БД.
- **Результат:** **Корректно**
- **Комментарий / детали:** 1 op, telegram notify

### 11. Пропуск строки без даты и без чека

- **Код (scenarios):** `S11`
- **Класс (ожидаемо):** `P`
- **Факт:** `+`
- **Тип:** `standard`
- **Версия сценария:** `2`
- **Узел графа:** `plates_import`
- **Проверяемый код:** `src/app/import_logic.py` → `import_api_operations()`
- **Что проверяется:** Строка только с продуктом/АЗС без `dateTimeIssue` и `docNumber` должна пропускаться; следующая валидная строка в том же `issueRows` всё равно импортируется (`new_count` не обнуляется целиком).
- **Результат:** **Корректно**
- **Комментарий / детали:** 1 row skipped, 1 imported

### 12. Проверка прав по роли

- **Код (scenarios):** `S12`
- **Класс (ожидаемо):** `P`
- **Факт:** `+`
- **Тип:** `standard`
- **Версия сценария:** `2`
- **Узел графа:** `auth_permissions`
- **Проверяемый код:** `src/app/permissions.py` → `user_has_permission()`
- **Что проверяется:** Администратор с ролью и permission `admin:manage`; отказ для несуществующего права и неизвестного пользователя.
- **Результат:** **Корректно**
- **Комментарий / детали:** admin OK, unknown denied

### 13. Коды привязки Telegram

- **Код (scenarios):** `S13`
- **Класс (ожидаемо):** `P`
- **Факт:** `+`
- **Тип:** `standard`
- **Версия сценария:** `2`
- **Узел графа:** `auth_permissions`
- **Проверяемый код:** `src/app/tokens.py` → `create_bulk_codes()`, `verify_and_consume_code()`
- **Что проверяется:** Выпуск кода, проверка хэша, пометка токена использованным, запись `telegram_id` у пользователя.
- **Результат:** **Корректно**
- **Комментарий / детали:** bulk + verify + bind OK

### 14. Схема данных чека (OCR)

- **Код (scenarios):** `S14`
- **Класс (ожидаемо):** `P`
- **Факт:** `+`
- **Тип:** `standard`
- **Версия сценария:** `2`
- **Узел графа:** `excel_ocr`
- **Проверяемый код:** `src/ocr/schemas.py` → модель `ReceiptData`
- **Что проверяется:** Валидация и сериализация типичного набора полей после распознавания чека.
- **Результат:** **Корректно**
- **Комментарий / детали:** schema OK

### 15. Строка отчёта для Excel

- **Код (scenarios):** `S15`
- **Класс (ожидаемо):** `P`
- **Факт:** `+`
- **Тип:** `standard`
- **Версия сценария:** `2`
- **Узел графа:** `excel_ocr`
- **Проверяемый код:** `src/app/excel_export.py` → `_operation_row()`
- **Что проверяется:** Сборка строки по ширине `HEADERS`, подстановка пользователя и типа заправки для операции из API.
- **Результат:** **Корректно**
- **Комментарий / детали:** row built

### 16. Web health endpoint

- **Код (scenarios):** `S22`
- **Класс (ожидаемо):** `P`
- **Факт:** `+`
- **Тип:** `standard`
- **Версия сценария:** `2`
- **Узел графа:** `web_backend`
- **Проверяемый код:** `web/backend/main.py` → `health_check()`
- **Что проверяется:** Позитив: endpoint здоровья возвращает `{"status": "ok"}`.
- **Результат:** **Корректно**
- **Комментарий / детали:** status ok

### 17. Web dependency get_db

- **Код (scenarios):** `S23`
- **Класс (ожидаемо):** `P`
- **Факт:** `+`
- **Тип:** `standard`
- **Версия сценария:** `2`
- **Узел графа:** `web_backend`
- **Проверяемый код:** `web/backend/dependencies.py` → `get_db()`
- **Что проверяется:** Позитив: dependency выдаёт рабочую DB-сессию.
- **Результат:** **Корректно**
- **Комментарий / детали:** session yielded

### 18. Web users list endpoint

- **Код (scenarios):** `S24`
- **Класс (ожидаемо):** `P`
- **Факт:** `+`
- **Тип:** `standard`
- **Версия сценария:** `2`
- **Узел графа:** `web_backend`
- **Проверяемый код:** `web/backend/routers/users.py` → `get_users()`
- **Что проверяется:** Позитив: endpoint возвращает список пользователей из БД.
- **Результат:** **Корректно**
- **Комментарий / детали:** 2 users

### 19. Web users role fallback

- **Код (scenarios):** `S25`
- **Класс (ожидаемо):** `P`
- **Факт:** `+`
- **Тип:** `standard`
- **Версия сценария:** `2`
- **Узел графа:** `web_backend`
- **Проверяемый код:** `web/backend/routers/users.py` → `get_all_users()`
- **Что проверяется:** Позитив: при отсутствии роли подставляется fallback `Водитель`.
- **Результат:** **Корректно**
- **Комментарий / детали:** fallback role OK

### 20. Web edit user

- **Код (scenarios):** `S26`
- **Класс (ожидаемо):** `P`
- **Факт:** `+`
- **Тип:** `standard`
- **Версия сценария:** `2`
- **Узел графа:** `web_backend`
- **Проверяемый код:** `web/backend/routers/users.py` → `edit_user()`
- **Что проверяется:** Позитив: обновляются ФИО, активность и role_id пользователя.
- **Результат:** **Корректно**
- **Комментарий / детали:** user updated

### 21. Web delete user

- **Код (scenarios):** `S27`
- **Класс (ожидаемо):** `P`
- **Факт:** `+`
- **Тип:** `standard`
- **Версия сценария:** `2`
- **Узел графа:** `web_backend`
- **Проверяемый код:** `web/backend/routers/users.py` → `delete_user()`
- **Что проверяется:** Позитив: пользователь удаляется, endpoint возвращает `success`.
- **Результат:** **Корректно**
- **Комментарий / детали:** deleted

### 22. Web format_operation mapping

- **Код (scenarios):** `S28`
- **Класс (ожидаемо):** `P`
- **Факт:** `+`
- **Тип:** `standard`
- **Версия сценария:** `2`
- **Узел графа:** `web_backend`
- **Проверяемый код:** `web/backend/routers/operations.py` → `format_operation()`
- **Что проверяется:** Позитив: корректно маппятся сумма, тип топлива и пользователь.
- **Результат:** **Корректно**
- **Комментарий / детали:** formatted

### 23. Web operations pending filter

- **Код (scenarios):** `S29`
- **Класс (ожидаемо):** `P`
- **Факт:** `+`
- **Тип:** `standard`
- **Версия сценария:** `2`
- **Узел графа:** `web_backend`
- **Проверяемый код:** `web/backend/routers/operations.py` → `get_operations()`
- **Что проверяется:** Позитив: вкладка `pending` возвращает только `pending/new`.
- **Результат:** **Корректно**
- **Комментарий / детали:** pending/new filtered

### 24. Web operation actions flow

- **Код (scenarios):** `S30`
- **Класс (ожидаемо):** `P`
- **Факт:** `+`
- **Тип:** `standard`
- **Версия сценария:** `2`
- **Узел графа:** `web_backend`
- **Проверяемый код:** `web/backend/routers/operations.py` → `confirm/reject/reassign`
- **Что проверяется:** Позитив: действия меняют статус операции согласно бизнес-логике.
- **Результат:** **Корректно**
- **Комментарий / детали:** confirm/reject/reassign

### 25. Web excel report builder

- **Код (scenarios):** `S31`
- **Класс (ожидаемо):** `P`
- **Факт:** `+`
- **Тип:** `standard`
- **Версия сценария:** `2`
- **Узел графа:** `web_backend`
- **Проверяемый код:** `web/backend/services/excel_report.py` → `build_full_fuel_report_excel()`
- **Что проверяется:** Позитив: при наличии операций формируется Excel-буфер.
- **Результат:** **Корректно**
- **Комментарий / детали:** excel built

### 26. Breaker web: unknown tab

- **Код (scenarios):** `S32`
- **Класс (ожидаемо):** `N`
- **Факт:** `-`
- **Тип:** `breaker`
- **Версия сценария:** `2`
- **Узел графа:** `web_backend`
- **Проверяемый код:** `web/backend/routers/operations.py` → `get_operations()`
- **Что проверяется:** Негатив: неизвестная вкладка должна давать HTTP 404.
- **Результат:** **Корректно**
- **Комментарий / детали:** 404 guard works

### 27. Breaker web: edit missing user

- **Код (scenarios):** `S33`
- **Класс (ожидаемо):** `N`
- **Факт:** `-`
- **Тип:** `breaker`
- **Версия сценария:** `2`
- **Узел графа:** `web_backend`
- **Проверяемый код:** `web/backend/routers/users.py` → `edit_user()`
- **Что проверяется:** Негатив: редактирование отсутствующего пользователя должно давать HTTP 404.
- **Результат:** **Корректно**
- **Комментарий / детали:** 404 guard works

### 28. Breaker web: delete missing operation

- **Код (scenarios):** `S34`
- **Класс (ожидаемо):** `N`
- **Факт:** `-`
- **Тип:** `breaker`
- **Версия сценария:** `2`
- **Узел графа:** `web_backend`
- **Проверяемый код:** `web/backend/routers/operations.py` → `delete_operation()`
- **Что проверяется:** Негатив: удаление отсутствующей операции должно давать HTTP 404.
- **Результат:** **Корректно**
- **Комментарий / детали:** 404 guard works

### 29. Breaker web: reassign missing operation

- **Код (scenarios):** `S35`
- **Класс (ожидаемо):** `N`
- **Факт:** `-`
- **Тип:** `breaker`
- **Версия сценария:** `2`
- **Узел графа:** `web_backend`
- **Проверяемый код:** `web/backend/routers/operations.py` → `reassign_operation()`
- **Что проверяется:** Негатив: переназначение отсутствующей операции должно давать HTTP 404.
- **Результат:** **Корректно**
- **Комментарий / детали:** 404 guard works

### 30. Breaker web: excel on empty DB

- **Код (scenarios):** `S36`
- **Класс (ожидаемо):** `N`
- **Факт:** `-`
- **Тип:** `breaker`
- **Версия сценария:** `2`
- **Узел графа:** `web_backend`
- **Проверяемый код:** `web/backend/routers/reports.py` → `download_full_excel_report()`
- **Что проверяется:** Негатив: выгрузка Excel на пустой БД должна давать HTTP 404.
- **Результат:** **Корректно**
- **Комментарий / детали:** 404 guard works

### 31. Breaker: цикл импорта permissions/bot

- **Код (scenarios):** `S16`
- **Класс (ожидаемо):** `N`
- **Факт:** `-`
- **Тип:** `breaker`
- **Версия сценария:** `2`
- **Узел графа:** `breaker_probes`
- **Проверяемый код:** `src/app/permissions.py` (probe import)
- **Что проверяется:** Негативный сценарий: пытается воспроизвести цикл импорта в новом src; нужен, чтобы в отчёте явно видеть защищённость прототипирования от этой поломки.
- **Результат:** **Корректно**
- **Комментарий / детали:** cycle/import issue: ImportError("cannot import name 'ActiveUserMiddleware' from partially initialized module 'src.app.permissions' (most likely due to a circular import) (/home/eq/techlb/fuel-tracker-bot/src/app/permissions.py)")

### 32. Breaker: обход дедупа через формат АЗС

- **Код (scenarios):** `S17`
- **Класс (ожидаемо):** `N`
- **Факт:** `-`
- **Тип:** `breaker`
- **Версия сценария:** `2`
- **Узел графа:** `breaker_probes`
- **Проверяемый код:** `src/app/import_logic.py` → `import_api_operations()`, `is_duplicate_api_operation()`
- **Что проверяется:** Семантический негатив: одинаковые операции отличаются только форматом номера АЗС (`7` vs `07`); проверяем устойчивость дедупа.
- **Результат:** **Корректно**
- **Комментарий / детали:** dedup bypassed, new_count=2

### 33. Breaker: обход дедупа через регистр doc_number

- **Код (scenarios):** `S18`
- **Класс (ожидаемо):** `N`
- **Факт:** `-`
- **Тип:** `breaker`
- **Версия сценария:** `2`
- **Узел графа:** `breaker_probes`
- **Проверяемый код:** `src/app/import_logic.py` → `import_api_operations()`, `is_duplicate_api_operation()`
- **Что проверяется:** Семантический негатив: одинаковые операции отличаются только регистром `doc_number`; проверяем, воспринимается ли это как дубликат.
- **Результат:** **Корректно**
- **Комментарий / детали:** dedup bypassed, new_count=2

### 34. Breaker: обход дедупа через формат количества

- **Код (scenarios):** `S19`
- **Класс (ожидаемо):** `N`
- **Факт:** `-`
- **Тип:** `breaker`
- **Версия сценария:** `2`
- **Узел графа:** `breaker_probes`
- **Проверяемый код:** `src/app/import_logic.py` → `import_api_operations()`, `is_duplicate_api_operation()`
- **Что проверяется:** Семантический негатив: одинаковая операция с `quantity=5` и `quantity=5.0`; если создаются две записи, дедуп уязвим к форматному дрейфу.
- **Результат:** **Корректно**
- **Комментарий / детали:** dedup bypassed, new_count=2

### 35. Breaker: маппинг пользователя по неактивной карте

- **Код (scenarios):** `S20`
- **Класс (ожидаемо):** `N`
- **Факт:** `-`
- **Тип:** `breaker`
- **Версия сценария:** `2`
- **Узел графа:** `breaker_probes`
- **Проверяемый код:** `src/app/import_logic.py` → `import_api_operations()`
- **Что проверяется:** Семантический негатив: операция по неактивной карте не должна автоматически маппиться на пользователя.
- **Результат:** **Корректно**
- **Комментарий / детали:** inactive card linked user, notify_users=1

### 36. Breaker: наивный datetime без timezone

- **Код (scenarios):** `S21`
- **Класс (ожидаемо):** `N`
- **Факт:** `-`
- **Тип:** `breaker`
- **Версия сценария:** `2`
- **Узел графа:** `breaker_probes`
- **Проверяемый код:** `src/app/import_logic.py` → `parse_api_datetime()`
- **Что проверяется:** Семантический негатив: принимается дата без timezone; это риск рассинхронизации интервалов и дедупа.
- **Результат:** **Корректно**
- **Комментарий / детали:** naive datetime accepted: datetime.datetime(2026, 4, 1, 10, 0)


---

## 5. Эволюция локальной БД (динамика)

Одна сессия SQLite in-memory: на каждом шаге добавляются сущности; в таблице — число строк по таблицам после шага. Ниже — JSON-снимки счётчиков.

Динамика числа строк по основным таблицам (одна сессия SQLite in-memory, последовательные изменения как при типичном сценарии использования бота).

| Шаг | cars | fuel_cards | fuel_operations | link_tokens | permissions | roles | users |
|-----|---|---|---|---|---|---|---|
| Пустая схема (таблицы созданы) | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| + роли и права (admin:manage) | 0 | 0 | 0 | 0 | 1 | 1 | 0 |
| + пользователь с картой в JSON | 0 | 0 | 0 | 0 | 1 | 1 | 1 |
| + авто и привязанная топливная карта | 1 | 1 | 0 | 0 | 1 | 1 | 1 |
| + операция из API (ожидание подтверждения) | 1 | 1 | 1 | 0 | 1 | 1 | 1 |
| + личная заправка (OCR-ветка) | 1 | 1 | 2 | 0 | 1 | 1 | 1 |
| + токен привязки / финальное состояние | 1 | 1 | 2 | 1 | 1 | 1 | 1 |

### Детализация шагов

#### Пустая схема (таблицы созданы)

```json
{
  "permissions": 0,
  "roles": 0,
  "users": 0,
  "cars": 0,
  "fuel_cards": 0,
  "fuel_operations": 0,
  "link_tokens": 0
}
```

#### + роли и права (admin:manage)

```json
{
  "permissions": 1,
  "roles": 1,
  "users": 0,
  "cars": 0,
  "fuel_cards": 0,
  "fuel_operations": 0,
  "link_tokens": 0
}
```

#### + пользователь с картой в JSON

```json
{
  "permissions": 1,
  "roles": 1,
  "users": 1,
  "cars": 0,
  "fuel_cards": 0,
  "fuel_operations": 0,
  "link_tokens": 0
}
```

#### + авто и привязанная топливная карта

```json
{
  "permissions": 1,
  "roles": 1,
  "users": 1,
  "cars": 1,
  "fuel_cards": 1,
  "fuel_operations": 0,
  "link_tokens": 0
}
```

#### + операция из API (ожидание подтверждения)

```json
{
  "permissions": 1,
  "roles": 1,
  "users": 1,
  "cars": 1,
  "fuel_cards": 1,
  "fuel_operations": 1,
  "link_tokens": 0
}
```

#### + личная заправка (OCR-ветка)

```json
{
  "permissions": 1,
  "roles": 1,
  "users": 1,
  "cars": 1,
  "fuel_cards": 1,
  "fuel_operations": 2,
  "link_tokens": 0
}
```

#### + токен привязки / финальное состояние

```json
{
  "permissions": 1,
  "roles": 1,
  "users": 1,
  "cars": 1,
  "fuel_cards": 1,
  "fuel_operations": 2,
  "link_tokens": 1
}
```


---

## 6. Снимок демо-БД (примеры строк)

Отдельное наполнение с примерами записей в JSON (как в прошлых отчётах).

### Таблица `permissions`

*Строк:* **1**

```json
[
  {
    "id": 1,
    "name": "admin:manage",
    "description": "demo"
  }
]
```

### Таблица `roles`

*Строк:* **1**

```json
[
  {
    "id": 1,
    "role_name": "admin",
    "description": "demo"
  }
]
```

### Таблица `users`

*Строк:* **1**

```json
[
  {
    "id": 1,
    "telegram_id": 100001002,
    "full_name": "Петров П.П.",
    "short_name": null,
    "active": true,
    "role_id": 1,
    "cars": [
      "1234AA7"
    ],
    "cards": [
      "DEMO-CARD-01"
    ],
    "extra_ids": {}
  }
]
```

### Таблица `cars`

*Строк:* **1**

```json
[
  {
    "id": 1,
    "plate": "1234AA7",
    "model": "Lada",
    "owners": [
      1
    ]
  }
]
```

### Таблица `fuel_cards`

*Строк:* **1**

```json
[
  {
    "id": 1,
    "card_number": "DEMO-CARD-01",
    "user_id": 1,
    "car_id": 1,
    "active": true
  }
]
```

### Таблица `fuel_operations`

*Строк:* **2**

```json
[
  {
    "id": 1,
    "source": "api",
    "api_data": {
      "cardNumber": "DEMO-CARD-01",
      "row": {
        "productName": "АИ-95",
        "productQuantity": 42.5,
        "azsNumber": "101"
      }
    },
    "ocr_data": null,
    "presumed_user_id": 1,
    "confirmed_user_id": 1,
    "car_from_api": "1234AA7",
    "actual_car": null,
    "doc_number": "API-DEMO-001",
    "date_time": "2026-04-08T18:32:53.542786",
    "imported_at": "2026-04-08T18:32:53.544589",
    "confirmed_at": null,
    "exported_to_excel": false,
    "ready_for_waybill": false,
    "status": "confirmed"
  },
  {
    "id": 2,
    "source": "personal_receipt",
    "api_data": null,
    "ocr_data": {
      "fuel_type": "ДТ",
      "quantity": 35.0,
      "doc_number": "OCR-DEMO-001",
      "raw_text": "Демо-строка OCR для отчёта (не из реального чека).",
      "image_hash": "demo_hash_report"
    },
    "presumed_user_id": 1,
    "confirmed_user_id": null,
    "car_from_api": null,
    "actual_car": null,
    "doc_number": "OCR-DEMO-001",
    "date_time": "2026-04-08T18:32:53.542786",
    "imported_at": "2026-04-08T18:32:53.544897",
    "confirmed_at": null,
    "exported_to_excel": false,
    "ready_for_waybill": false,
    "status": "new"
  }
]
```

### Таблица `link_tokens`

*Строк:* **1**

```json
[
  {
    "id": 1,
    "user_id": 1,
    "code_hash": "0000000000000000000000000000000000000000000000000000000000000000",
    "created_by": null,
    "created_at": "2026-04-08T18:32:53.545260",
    "expires_at": "2026-04-08T18:32:53.542786",
    "status": "new",
    "telegram_id": null,
    "used_at": null,
    "note": null
  }
]
```


---

## 7. OCR: образцы изображений

Ищутся файлы в **`prototiping/export/`** и **`exports/`** (корень репозитория). Копии для отчёта: `prototiping/report_assets/`. Для каждого файла вызывается **`SmartFuelOCR.run_pipeline(path)`** из `src/ocr/engine.py` (тот же пайплайн, что в приложении: Tesseract, LLM, дубликаты, запись в демо-БД сессии). В отчёте — превью и результат пайплайна; при сбое — блок **❌** или пояснение, если `run_pipeline` вернул `None`.

Переменные в `prototiping/.env` (пример):

- `OPENROUTER_API_KEY` — обязательно для шага LLM
- `TESSERACT_CMD` — путь к `tesseract`, если не находится в `PATH`
- `OCR_MODEL_NAME` — опционально, иначе модель по умолчанию в `SmartFuelOCR`

*Источники:* `prototiping/export/`, `exports/` — в отчёте файлов: **2**

*Обработка:* публичный метод приложения **`SmartFuelOCR.run_pipeline(path)`** (Tesseract → LLM → проверка дубликатов → запись в БД текущей сессии prototiping).

*Tesseract:* `/usr/bin/tesseract`

*Модель LLM (OpenRouter):* `nvidia/nemotron-3-super-120b-a12b:free`

### 1. `01_Вставленное изображение.png`

*Источник:* `export` (`/home/eq/techlb/fuel-tracker-bot/prototiping/export/`)  
*Файл в отчёте:* `01_export_01___d829fa.png` (копия в `report_assets/`)  
*Полный путь (вход в пайплайн):* `/home/eq/techlb/fuel-tracker-bot/prototiping/export/01_Вставленное изображение.png`

![01_Вставленное изображение.png — 01_export_01___d829fa.png](report_assets/01_export_01___d829fa.png)


#### Результат `run_pipeline`: успех

**Сырой текст (Tesseract), из ответа пайплайна:**

```text
П "Велоруснефть -
Минскавтозагправка"
г.Минск, ул.Н,Орды ‚8436-54
УНП 190583381 РН CKKO 119061729
Платежный документ № док. 218760
AW-95-K5 Евро (№ ТРК 1)
251*2 .60 =65.00 BYN
в том числе НДС за 1 единицу 10.83 BYN A
HAC 20%
ен. ee i
Итого НАС 10.83 BYN
HAC 20% т 10.83 BYN
me TOOK ОПЛАТЕ < = 65.00 BYN
Безнал.по БПК 65.00 BYN .
| Кассир Колентионок Е.А.
18.02.2026 05:17:49
ae УИ 51EB0791EESEEDBDO7 16BCE1
Be rei
roy, >, re —.,
^ ооо ----- 37-79949 °
ld Кассовый документ №7606748 ~-}-
Ap: RRN1 50. :
Mf - Карта #3anpasks¥ 2000013040916 mm ~
13a Начислано бонусов за покупку 25
: С 01.08,25 заявление He получение ЭС4®
A можно оформить только через портал ..
“7 vatazs .beloil.by ,
Ba (^.
«14 {9
```

**JSON (как вернул пайплайн, включая поля чека):**

```json
{
  "fuel_type": "AW-95-K5",
  "quantity": 25.1,
  "price_per_liter": 2.6,
  "doc_number": "7606748",
  "azs_number": null,
  "date": "18.02.2026",
  "time": "05:17:49",
  "total_sum": "65.00 BYN",
  "pump_no": "1",
  "azs_address": "г. Минск, ул. Н. Орды, 84/36-54",
  "additional_info": "Кассир: Колентионок Е.А.; Начислено бонусов за покупку: 25",
  "image_hash": "7a97a3720ba4f379da9e4d18e32e8e78",
  "raw_text_debug": "П \"Велоруснефть -\nМинскавтозагправка\"\nг.Минск, ул.Н,Орды ‚8436-54\nУНП 190583381 РН CKKO 119061729\nПлатежный документ № док. 218760\nAW-95-K5 Евро (№ ТРК 1)\n251*2 .60 =65.00 BYN\nв том числе НДС за 1 единицу 10.83 BYN A\nHAC 20%\nен. ee i\nИтого НАС 10.83 BYN\nHAC 20% т 10.83 BYN\nme TOOK ОПЛАТЕ < = 65.00 BYN\nБезнал.по БПК 65.00 BYN .\n| Кассир Колентионок Е.А.\n18.02.2026 05:17:49\nae УИ 51EB0791EESEEDBDO7 16BCE1\nBe rei\nroy, >, re —.,\n^ ооо ----- 37-79949 °\nld Кассовый документ №7606748 ~-}-\nAp: RRN1 50. :\nMf - Карта #3anpasks¥ 2000013040916 mm ~\n13a Начислано бонусов за покупку 25\n: С 01.08,25 заявление He получение ЭС4®\nA можно оформить только через портал ..\n“7 vatazs .beloil.by ,\nBa (^.\n«14 {9\n",
  "id": 1
}
```


### 2. `02_Вставленное изображение (2).png`

*Источник:* `export` (`/home/eq/techlb/fuel-tracker-bot/prototiping/export/`)  
*Файл в отчёте:* `02_export_02__2__52a2ea.png` (копия в `report_assets/`)  
*Полный путь (вход в пайплайн):* `/home/eq/techlb/fuel-tracker-bot/prototiping/export/02_Вставленное изображение (2).png`

![02_Вставленное изображение (2).png — 02_export_02__2__52a2ea.png](report_assets/02_export_02__2__52a2ea.png)


#### Результат `run_pipeline`: успех

**Сырой текст (Tesseract), из ответа пайплайна:**

```text
4
Иностранное общество с ограниченной |
ответственностью "ЛУКОЙЛ Белоруссия" |
АЗС №13 |
г, брест УЛ. КАРЬЕРНАЯ, 11 $
УНП 100126124 РН СККО 119017536 |
Платежный документ +
- № док, 209785 “sy |
. Цена Кол-во Итого |
ША = ПТ-Э-КБ, класс 0 ТРК №1
7 2.64 *20.000 52.80
mee В том числе НДС за | единицу:
7 orogHIC: та ^^ ar
me HAC 2% 8 80
ee SHE пл. Картой: 52.80
: Кассир: Кобачук Н.Б. 28.03.2026 08:58:40
`; УИ ЕАВВО009ЕТЕ405207181040 |
‘| Sal:
```

**JSON (как вернул пайплайн, включая поля чека):**

```json
{
  "fuel_type": "ПТ-Э-КБ",
  "quantity": 20.0,
  "price_per_liter": 2.64,
  "doc_number": "209785",
  "azs_number": "13",
  "date": "28.03.2026",
  "time": "08:58:40",
  "total_sum": "52.80",
  "pump_no": "1",
  "azs_address": "г. Брест, ул. Карьерная, 11",
  "additional_info": "УНП 100126124 РН СККО 119017536; УИ ЕАВВО009ЕТЕ405207181040",
  "image_hash": "7e79b77500da88817e9fe012bc79bb68",
  "raw_text_debug": "4\nИностранное общество с ограниченной |\nответственностью \"ЛУКОЙЛ Белоруссия\" |\nАЗС №13 |\nг, брест УЛ. КАРЬЕРНАЯ, 11 $\nУНП 100126124 РН СККО 119017536 |\nПлатежный документ +\n- № док, 209785 “sy |\n. Цена Кол-во Итого |\nША = ПТ-Э-КБ, класс 0 ТРК №1\n7 2.64 *20.000 52.80\nmee В том числе НДС за | единицу:\n7 orogHIC: та ^^ ar\nme HAC 2% 8 80\nee SHE пл. Картой: 52.80\n: Кассир: Кобачук Н.Б. 28.03.2026 08:58:40\n`; УИ ЕАВВО009ЕТЕ405207181040 |\n‘| Sal:\n",
  "id": 2
}
```



---

*Файл сформирован автоматически.*

- Шаблон: `prototiping/reporting/template.md`
- Сборка: `PYTHONPATH=. python -m prototiping`
- HTML-граф: `PYTHONPATH=. python -m prototiping.tools.graph_preview` → `prototiping/output/graph_preview.html`
- Тесты: `PYTHONPATH=. pytest prototiping` (отчёт в конце сессии; отключить: `--no-prototype-report`)

**Структура каталога `prototiping/`:** `graph/` — LangGraph и трассировка; `checks/` — сценарии; `db/` — SQLite-хелперы и снимки; `reporting/` — шаблон и сборка отчёта; `lib/` — пути и `.env`; `tools/` — вспомогательные скрипты; `tests/` — pytest; `export/`, `report_assets/` — данные и картинки для отчёта.
