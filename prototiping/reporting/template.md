# Отчёт прототипирования: fuel-tracker-bot

**Дата генерации:** {{GENERATED_AT}}

{{FAIL_ALERT}}

{{GRAPH_SUMMARY}}

## 1. Сводка

| Показатель | Значение |
|------------|----------|
| Всего сценариев | {{TOTAL}} |
| Результат **корректен** | {{OK_COUNT}} |
| Результат **с ошибкой** | {{FAIL_COUNT}} |
| **TP** (standard + OK) | {{TP_COUNT}} |
| **FN** (standard + FAIL) | {{FN_COUNT}} |
| **TN** (breaker + FAIL) | {{TN_COUNT}} |
| **FP** (breaker + OK) | {{FP_COUNT}} |
| Версия схемы сценариев | {{SCHEMA_VERSION}} |
| Legacy-сценариев (устаревшая версия) | {{LEGACY_SCENARIOS_COUNT}} |

### Матрица P/N (как confusion matrix)

Обозначения: **P** — позитивные тесты (должны проходить), **N** — негативные/ломающие тесты (должны падать).  
Столбец **actual**: `+` = тест прошёл (`ok=True`), `-` = тест упал (`ok=False`).

{{CONFUSION_MATRIX}}

Трассировка (LangSmith): при `LANGCHAIN_TRACING_V2=true` и заданном `LANGCHAIN_API_KEY` прогоны LangGraph и узлов с `@traceable` попадают в проект LangSmith.

---

## 2. Граф сценариев

Ниже: **таблица узлов**, цепочка в одну строку, **ASCII-схема** (читается в любом просмотрщике), компактный Mermaid и ссылка на HTML-preview.

{{GRAPH_VISUAL}}

---

## 3. Сценарии: проверяемый код и статус

**№** — порядок прогона в графе (узлы сверху вниз, проверки внутри узла как в `graph/spec.py`).  
**Класс:** `P` = позитивный тест, `N` = негативный (должен падать).  
**Факт:** `+` = тест прошёл, `-` = тест упал.

{{SCENARIOS_TABLE}}

---

## 4. Детали по сценариям

Нумерация заголовков совпадает с колонкой **№** в таблице выше.

{{SCENARIOS_DETAIL}}

---

## 5. Эволюция локальной БД (динамика)

Одна сессия SQLite in-memory: на каждом шаге добавляются сущности; в таблице — число строк по таблицам после шага. Ниже — JSON-снимки счётчиков.

{{DB_EVOLUTION}}

---

## 6. Снимок демо-БД (примеры строк)

Отдельное наполнение с примерами записей в JSON (как в прошлых отчётах).

{{DB_SNAPSHOT}}

---

## 7. OCR: образцы изображений

Ищутся файлы в **`prototiping/export/`** и **`exports/`** (корень репозитория). Копии для отчёта: `prototiping/report_assets/`. Для каждого файла вызывается **`SmartFuelOCR.run_pipeline(path)`** из `src/ocr/engine.py` (тот же пайплайн, что в приложении: Tesseract, LLM, дубликаты, запись в демо-БД сессии). В отчёте — превью и результат пайплайна; при сбое — блок **❌** или пояснение, если `run_pipeline` вернул `None`.

Переменные в `prototiping/.env` (пример):

- `OPENROUTER_API_KEY` — обязательно для шага LLM
- `TESSERACT_CMD` — путь к `tesseract`, если не находится в `PATH`
- `OCR_MODEL_NAME` — опционально, иначе модель по умолчанию в `SmartFuelOCR`

{{OCR_SAMPLES}}

---

*Файл сформирован автоматически.*

- Шаблон: `prototiping/reporting/template.md`
- Сборка: `PYTHONPATH=. python -m prototiping`
- HTML-граф: `PYTHONPATH=. python -m prototiping.tools.graph_preview` → `prototiping/output/graph_preview.html`
- Тесты: `PYTHONPATH=. pytest prototiping` (отчёт в конце сессии; отключить: `--no-prototype-report`)

**Структура каталога `prototiping/`:** `graph/` — LangGraph и трассировка; `checks/` — сценарии; `db/` — SQLite-хелперы и снимки; `reporting/` — шаблон и сборка отчёта; `lib/` — пути и `.env`; `tools/` — вспомогательные скрипты; `tests/` — pytest; `export/`, `report_assets/` — данные и картинки для отчёта.
