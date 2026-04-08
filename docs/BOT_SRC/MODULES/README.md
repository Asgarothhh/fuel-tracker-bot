# BOT_SRC / MODULES INDEX

Подробный справочник по боевому коду `src/`.

## Ядро

- [ARCHITECTURE](ARCHITECTURE.md)
- [SRC_FILES](SRC_FILES.md)
- [DATA_LAYER](DATA_LAYER.md)
- [TELEGRAM_LAYER](TELEGRAM_LAYER.md)
- [IMPORT_AND_JOBS](IMPORT_AND_JOBS.md)
- [OCR_INTERNALS](OCR_INTERNALS.md)
- [SERVICES_AND_CONFIG](SERVICES_AND_CONFIG.md)

## Верхнеуровневые обзоры

- [OVERVIEW](OVERVIEW.md)
- [TELEGRAM](TELEGRAM.md)
- [DATA_AND_PERMISSIONS](DATA_AND_PERMISSIONS.md)
- [IMPORT_AND_REPORTS](IMPORT_AND_REPORTS.md)

## Семантическая навигация

- Если нужно понять "что запускается при старте" -> [ARCHITECTURE](ARCHITECTURE.md)
- Если нужно понять "как данные живут в БД" -> [DATA_LAYER](DATA_LAYER.md)
- Если нужно понять "как команды/колбэки проходят через aiogram" -> [TELEGRAM_LAYER](TELEGRAM_LAYER.md)
- Если нужно понять "как прилетают операции из API и как экспортируются" -> [IMPORT_AND_JOBS](IMPORT_AND_JOBS.md) -> [IMPORT_AND_REPORTS](IMPORT_AND_REPORTS.md)

## Карта "вопрос -> документ"

| Вопрос разработчика | Куда идти |
|---|---|
| Как поднимается приложение и где границы подсистем? | `ARCHITECTURE.md` |
| Где искать конкретный файл из `src` и что он делает? | `SRC_FILES.md` |
| Как устроены ORM таблицы, сессии и транзакции? | `DATA_LAYER.md` |
| Как устроен Telegram routing и middleware? | `TELEGRAM_LAYER.md`, `TELEGRAM.md` |
| Как реализованы права и link-коды? | `DATA_AND_PERMISSIONS.md` |
| Как работает импорт из API, scheduler и jobs? | `IMPORT_AND_JOBS.md` |
| Где описан поток от импорта до Excel? | `IMPORT_AND_REPORTS.md`, `../EXCEL_AND_DATA.md` |
| Как работает OCR внутренне? | `OCR_INTERNALS.md`, `../OCR_MODULE.md` |

## Рекомендуемая последовательность чтения для онбординга

### День 1: обзор и доменная модель

1. `ARCHITECTURE.md`
2. `SRC_FILES.md`
3. `DATA_LAYER.md`

### День 2: telegram и права

1. `TELEGRAM_LAYER.md`
2. `TELEGRAM.md`
3. `DATA_AND_PERMISSIONS.md`

### День 3: импорт, отчеты, OCR

1. `IMPORT_AND_JOBS.md`
2. `IMPORT_AND_REPORTS.md`
3. `OCR_INTERNALS.md`

## Паттерны документации в этом разделе

Во всех файлах желательно искать и поддерживать:

- "Что делает модуль" (назначение);
- "Ключевые функции" (сигнатуры и смысл);
- "Поток данных" (диаграмма/список шагов);
- "Edge-cases" (что ломается и как обрабатывается);
- "Связанные документы" (семантическая навигация).

## Политика обновления docs при изменении кода

1. Если добавлен новый публичный flow -> обновить минимум `OVERVIEW`, `SRC_FILES`, профильный модуль.
2. Если изменен контракт статусов/полей -> обновить `DATA_LAYER` и связанные модули.
3. Если добавлены новые callback команды -> обновить `TELEGRAM`/`TELEGRAM_BOT`.
4. Если изменен импорт/дедуп/экспорт -> обновить `IMPORT_AND_*` + `EXCEL_AND_DATA`.

## Мини-чеклист готовности документации

- Документ содержит реальные имена функций/файлов.
- Есть хотя бы один практический code snippet.
- Есть секция "как дебажить" или "типовые ошибки".
- Есть ссылки на соседние документы для продолжения чтения.

## Сопоставление модулей и исходников

| Документ | Основные исходники |
|---|---|
| `ARCHITECTURE.md` | `run_bot.py`, `scheduler.py`, `bot/register.py` |
| `SRC_FILES.md` | весь `src/*.py`, `src/app/**/*.py`, `src/ocr/*.py` |
| `DATA_LAYER.md` | `db.py`, `models.py` |
| `DATA_AND_PERMISSIONS.md` | `permissions.py`, `tokens.py`, `models.py` |
| `TELEGRAM_LAYER.md` | `bot/register.py`, `bot/handlers/*`, `keyboards.py` |
| `TELEGRAM.md` | `bot/register.py`, `permissions.py` |
| `IMPORT_AND_JOBS.md` | `jobs.py`, `scheduler.py`, `belorusneft_api.py`, `import_logic.py` |
| `IMPORT_AND_REPORTS.md` | `import_logic.py`, `excel_export.py` |
| `OCR_INTERNALS.md` | `src/ocr/engine.py`, `src/ocr/schemas.py` |
| `SERVICES_AND_CONFIG.md` | `config.py`, `tokens.py`, `plate_util.py`, `welcome_store.py` |

## Когда обновлять какой документ

### Изменили Telegram команды/кнопки/FSM

Обновить:

- `TELEGRAM.md`
- `TELEGRAM_LAYER.md`
- `../TELEGRAM_BOT.md`

### Изменили модель/статусы операций

Обновить:

- `DATA_LAYER.md`
- `IMPORT_AND_REPORTS.md`
- `../EXCEL_AND_DATA.md`

### Изменили импорт API

Обновить:

- `IMPORT_AND_JOBS.md`
- `IMPORT_AND_REPORTS.md`

### Изменили OCR пайплайн

Обновить:

- `OCR_INTERNALS.md`
- `../OCR_MODULE.md`
- `../PERSONAL_FUNDS_SCENARIO.md`

## Практика ведения больших docs

1. Сверять имена функций с кодом перед каждым коммитом.
2. Не оставлять "..." в примерах, если есть конкретная логика.
3. Добавлять edge-cases, а не только happy-path.
4. Добавлять ссылки на соседние файлы в конце каждого раздела.

## Финальная проверка перед релизом docs

- Все ссылки между `BOT_SRC` файлами открываются.
- В ключевых файлах есть блоки: функции, flow, edge-cases, troubleshooting.
- Стиль заголовков и терминов единообразный (русский язык, одинаковые названия секций).
- При изменении `src` обновлен `SRC_FILES.md` и профильные модульные документы.
- Добавлены примеры кода для всех новых публичных функций и сценариев.

## Примечание

Этот индекс поддерживается как "точка входа": сначала читаем его, затем уходим в профильный модуль.
