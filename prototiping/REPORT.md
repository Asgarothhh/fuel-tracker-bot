# Отчёт прототипирования: fuel-tracker-bot

**Дата генерации:** 2026-04-04 13:46 UTC



*Граф:* `fuel_tracker_prototype` — итог прогона: **успех** (11 OK / 0 FAIL по проверкам).


## 1. Сводка

| Показатель | Значение |
|------------|----------|
| Всего сценариев | 11 |
| Результат **корректен** | 11 |
| Результат **с ошибкой** | 0 |

Трассировка (LangSmith): при `LANGCHAIN_TRACING_V2=true` и заданном `LANGCHAIN_API_KEY` прогоны LangGraph и узлов с `@traceable` попадают в проект LangSmith.

---

## 2. Граф сценариев

Ниже: **таблица узлов**, цепочка в одну строку, **ASCII-схема** (читается в любом просмотрщике), компактный Mermaid и ссылка на HTML-preview.

Граф **`fuel_tracker_prototype`**: узлы выполняются **сверху вниз** (как в LangGraph). Сырая диаграмма Mermaid ниже в части просмотрщиков показывается как текст — тогда откройте сгенерированный **HTML** (команда в конце раздела) или IDE с Mermaid.

### Таблица узлов

| № | ID узла | Описание | Проверок OK | Всего проверок | мс | Узел |
|---|---------|----------|-------------|----------------|-----|------|
| 1 | `belorusneft_parse` | Парсинг API / даты (Belorusneft) | 4 | 4 | 0.03 | **да** |
| 2 | `plates_import` | Номера, импорт API, дедупликация | 3 | 3 | 38.64 | **да** |
| 3 | `auth_permissions` | Права и токены привязки | 2 | 2 | 17.8 | **да** |
| 4 | `excel_ocr` | Схема чека и строка Excel | 2 | 2 | 5.16 | **да** |

### Цепочка (одна строка)

`belorusneft_parse` ✓ (0.03 ms) → `plates_import` ✓ (38.64 ms) → `auth_permissions` ✓ (17.8 ms) → `excel_ocr` ✓ (5.16 ms)

### Порядок выполнения

1. **belorusneft_parse** — успех (0.03 ms): _Парсинг API / даты (Belorusneft)_
2. **plates_import** — успех (38.64 ms): _Номера, импорт API, дедупликация_
3. **auth_permissions** — успех (17.8 ms): _Права и токены привязки_
4. **excel_ocr** — успех (5.16 ms): _Схема чека и строка Excel_

### Схема (ASCII)

```text
  [старт]
      |
      v
  +-- belorusneft_parse  [OK]  0.03 ms
      |
      v
  +-- plates_import  [OK]  38.64 ms
      |
      v
  +-- auth_permissions  [OK]  17.8 ms
      |
      v
  +-- excel_ocr  [OK]  5.16 ms
      |
      v
  [конец]
```

### Диаграмма Mermaid (компактная)

```mermaid
%% Автогенерация prototiping.tools.graph_preview
flowchart LR
  N0["belorusneft_parse / OK / 0.03ms"]:::okNode
  N1["plates_import / OK / 38.64ms"]:::okNode
  N2["auth_permissions / OK / 17.8ms"]:::okNode
  N3["excel_ocr / OK / 5.16ms"]:::okNode
  classDef okNode fill:#1a472a,stroke:#234,color:#e8ffe8
  classDef failNode fill:#6b1c1c,stroke:#422,color:#ffe8e8
  N0 --> N1
  N1 --> N2
  N2 --> N3
```

### Интерактивная диаграмма

Сгенерируйте HTML с корректным рендером:

```bash
PYTHONPATH=. python -m prototiping.tools.graph_preview
```

Файл: `prototiping/output/graph_preview.html` (откройте в браузере).


---

## 3. Сценарии: проверяемый код и статус

| ID | Узел графа | Сценарий | Проверяемый код | Корректно | При ошибке |
|----|------------|----------|-----------------|-----------|------------|
| S01 | `belorusneft_parse` | Парсинг ответа API: ветка items/data | `src/app/belorusneft_api.py` → `parse_operations()` | да | — |
| S02 | `belorusneft_parse` | Парсинг ответа API: cardList / issueRows | `src/app/belorusneft_api.py` → `parse_operations()` | да | — |
| S03 | `belorusneft_parse` | Разбор даты/времени из строки API | `src/app/import_logic.py` → `parse_api_datetime()` | да | — |
| S04 | `belorusneft_parse` | Календарное «вчера» в зоне UTC+3 | `src/app/import_logic.py` → `api_local_yesterday_datetime()` | да | — |
| S05 | `plates_import` | Нормализация госномеров | `src/app/plate_util.py` → `normalize_plate()`, `plates_equal()` | да | — |
| S06 | `plates_import` | Плоские поля и дедупликация импорта API | `src/app/import_logic.py` → `extract_flat_fields()`, `is_duplicate_api_operation()` | да | — |
| S07 | `plates_import` | Импорт операций из JSON (dry_run) | `src/app/import_logic.py` → `import_api_operations(..., dry_run=True)` | да | — |
| S08 | `auth_permissions` | Проверка прав по роли | `src/app/permissions.py` → `user_has_permission()` | да | — |
| S09 | `auth_permissions` | Коды привязки Telegram | `src/app/tokens.py` → `create_bulk_codes()`, `verify_and_consume_code()` | да | — |
| S10 | `excel_ocr` | Схема данных чека (OCR) | `src/ocr/schemas.py` → модель `ReceiptData` | да | — |
| S11 | `excel_ocr` | Строка отчёта для Excel | `src/app/excel_export.py` → `_operation_row()` | да | — |

---

## 4. Детали по сценариям

### S01. Парсинг ответа API: ветка items/data

- **Узел графа:** `belorusneft_parse`
- **Проверяемый код:** `src/app/belorusneft_api.py` → `parse_operations()`
- **Что проверяется:** Проверка разбора JSON с массивом `items`: дата, продукт, чек, карта, госномер.
- **Результат:** **Корректно**
- **Комментарий / детали:** items branch OK

### S02. Парсинг ответа API: cardList / issueRows

- **Узел графа:** `belorusneft_parse`
- **Проверяемый код:** `src/app/belorusneft_api.py` → `parse_operations()`
- **Что проверяется:** Текущая структура ответа Белоруснефти: вложенные `issueRows`, номер карты с уровня `cardList`.
- **Результат:** **Корректно**
- **Комментарий / детали:** cardList/issueRows OK

### S03. Разбор даты/времени из строки API

- **Узел графа:** `belorusneft_parse`
- **Проверяемый код:** `src/app/import_logic.py` → `parse_api_datetime()`
- **Что проверяется:** ISO-строка с суффиксом `Z` корректно превращается в `datetime` с timezone.
- **Результат:** **Корректно**
- **Комментарий / детали:** 2020-01-15 10:20:30+00:00

### S04. Календарное «вчера» в зоне UTC+3

- **Узел графа:** `belorusneft_parse`
- **Проверяемый код:** `src/app/import_logic.py` → `api_local_yesterday_datetime()`
- **Что проверяется:** Дата для запросов к API в локальной зоне контракта (смещение +3 ч от UTC).
- **Результат:** **Корректно**
- **Комментарий / детали:** 2026-04-03T00:00:00

### S05. Нормализация госномеров

- **Узел графа:** `plates_import`
- **Проверяемый код:** `src/app/plate_util.py` → `normalize_plate()`, `plates_equal()`
- **Что проверяется:** Удаление пробелов и дефисов, сравнение номеров без учёта форматирования.
- **Результат:** **Корректно**
- **Комментарий / детали:** normalize + plates_equal OK

### S06. Плоские поля и дедупликация импорта API

- **Узел графа:** `plates_import`
- **Проверяемый код:** `src/app/import_logic.py` → `extract_flat_fields()`, `is_duplicate_api_operation()`
- **Что проверяется:** Извлечение карты/АЗС/продукт/кол-ва и обнаружение уже сохранённой операции с тем же составным ключом.
- **Результат:** **Корректно**
- **Комментарий / детали:** dedup key OK

### S07. Импорт операций из JSON (dry_run)

- **Узел графа:** `plates_import`
- **Проверяемый код:** `src/app/import_logic.py` → `import_api_operations(..., dry_run=True)`
- **Что проверяется:** Создание операции, привязка пользователя по карте, список уведомлений в Telegram без commit в БД.
- **Результат:** **Корректно**
- **Комментарий / детали:** 1 op, telegram notify

### S08. Проверка прав по роли

- **Узел графа:** `auth_permissions`
- **Проверяемый код:** `src/app/permissions.py` → `user_has_permission()`
- **Что проверяется:** Администратор с ролью и permission `admin:manage`; отказ для несуществующего права и неизвестного пользователя.
- **Результат:** **Корректно**
- **Комментарий / детали:** admin OK, unknown denied

### S09. Коды привязки Telegram

- **Узел графа:** `auth_permissions`
- **Проверяемый код:** `src/app/tokens.py` → `create_bulk_codes()`, `verify_and_consume_code()`
- **Что проверяется:** Выпуск кода, проверка хэша, пометка токена использованным, запись `telegram_id` у пользователя.
- **Результат:** **Корректно**
- **Комментарий / детали:** bulk + verify + bind OK

### S10. Схема данных чека (OCR)

- **Узел графа:** `excel_ocr`
- **Проверяемый код:** `src/ocr/schemas.py` → модель `ReceiptData`
- **Что проверяется:** Валидация и сериализация типичного набора полей после распознавания чека.
- **Результат:** **Корректно**
- **Комментарий / детали:** schema OK

### S11. Строка отчёта для Excel

- **Узел графа:** `excel_ocr`
- **Проверяемый код:** `src/app/excel_export.py` → `_operation_row()`
- **Что проверяется:** Сборка строки по ширине `HEADERS`, подстановка пользователя и типа заправки для операции из API.
- **Результат:** **Корректно**
- **Комментарий / детали:** row built


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
    "date_time": "2026-04-04T13:45:33.040789",
    "imported_at": "2026-04-04T13:45:33.041715",
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
    "date_time": "2026-04-04T13:45:33.040789",
    "imported_at": "2026-04-04T13:45:33.042022",
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
    "created_at": "2026-04-04T13:45:33.042428",
    "expires_at": "2026-04-04T13:45:33.040789",
    "status": "new",
    "telegram_id": null,
    "used_at": null,
    "note": null
  }
]
```


---

## 7. OCR: образцы изображений

Ищутся файлы в **`prototiping/export/`** и **`exports/`** (корень репозитория). Копии для отчёта: `prototiping/report_assets/`. Для каждого файла: превью, сырой текст Tesseract и структура `ReceiptData` через LLM (`src/ocr/engine.py` — `SmartFuelOCR`). При сбое в отчёт выводится блок **❌** с типом исключения и трассировкой.

Переменные в `prototiping/.env` (пример):

- `OPENROUTER_API_KEY` — обязательно для шага LLM
- `TESSERACT_CMD` — путь к `tesseract`, если не находится в `PATH`
- `OCR_MODEL_NAME` — опционально, иначе модель по умолчанию в `SmartFuelOCR`

*Источники:* `prototiping/export/`, `exports/` — обработано файлов: **1**

*Tesseract:* `/usr/bin/tesseract`

*Модель LLM (OpenRouter):* `nvidia/nemotron-3-super-120b-a12b:free`

### 1. `01_Вставленное изображение.png`

*Путь:* `/home/eq/techlb/fuel-tracker-bot/prototiping/export/01_Вставленное изображение.png`

![01_Вставленное изображение.png](report_assets/01_01__.png)

**Сырой текст (Tesseract):**

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


**Структура (LLM → ReceiptData):**

```json

{
  "fuel_type": "AW-95-K5",
  "quantity": 25.1,
  "price_per_liter": 2.6,
  "doc_number": "7606748",
  "azs_number": "CKKO 119061729",
  "date": "18.02.2026",
  "time": "05:17:49",
  "total_sum": "65.00 BYN",
  "pump_no": "1",
  "azs_address": "г. Минск, ул. Н. Орды, 84/36-54",
  "additional_info": "Кассир: Колентионок Е.А.; Начислено бонусов за покупку: 25; Карта: #3anpasks¥ 2000013040916; УНП: 190583381; РН: CKKO 119061729"
}

```


---

*Файл сформирован автоматически.*

- Шаблон: `prototiping/reporting/template.md`
- Сборка: `PYTHONPATH=. python -m prototiping`
- HTML-граф: `PYTHONPATH=. python -m prototiping.tools.graph_preview` → `prototiping/output/graph_preview.html`
- Тесты: `PYTHONPATH=. pytest prototiping` (отчёт в конце сессии; отключить: `--no-prototype-report`)

**Структура каталога `prototiping/`:** `graph/` — LangGraph и трассировка; `checks/` — сценарии; `db/` — SQLite-хелперы и снимки; `reporting/` — шаблон и сборка отчёта; `lib/` — пути и `.env`; `tools/` — вспомогательные скрипты; `tests/` — pytest; `export/`, `report_assets/` — данные и картинки для отчёта.
