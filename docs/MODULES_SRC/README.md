# Документация модулей `src/` (для разработчиков)

Ниже — разбор **боевого кода** приложения: точки входа, слои данных, Telegram-слой, фоновые задачи, OCR и вспомогательные сервисы. Предполагается знакомство с Python, asyncio и SQLAlchemy.

## Оглавление

| Документ | Содержание |
|----------|------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Общая архитектура, диаграммы компонентов и потоков данных |
| [DATA_LAYER.md](DATA_LAYER.md) | `db.py`, `models.py`, сессии, схема сущностей (ER) |
| [TELEGRAM_LAYER.md](TELEGRAM_LAYER.md) | Регистрация хендлеров, middleware, карта обработчиков, FSM |
| [IMPORT_AND_JOBS.md](IMPORT_AND_JOBS.md) | Импорт API, `jobs.py`, планировщик, граница с `belorusneft_api` |
| [OCR_INTERNALS.md](OCR_INTERNALS.md) | Детальный пайплайн `SmartFuelOCR`, последовательности |
| [SERVICES_AND_CONFIG.md](SERVICES_AND_CONFIG.md) | Excel, токены привязки, госномера, приветствие, конфиг, CLI |

## Дерево каталога `src/`

```text
src/
├── run_bot.py              # Точка входа процесса бота + polling + планировщик
├── migrate_old_ops.py      # Разовые/миграционные скрипты (см. файл)
├── ocr/
│   ├── engine.py           # SmartFuelOCR
│   └── schemas.py          # Pydantic ReceiptData
└── app/
    ├── config.py           # Переменные окружения
    ├── db.py               # Engine, SessionLocal, get_db_session, init_db
    ├── models.py           # SQLAlchemy-модели
    ├── permissions.py      # RBAC + ActiveUserMiddleware
    ├── tokens.py           # LinkToken: генерация и проверка кодов
    ├── plate_util.py       # Нормализация госномеров
    ├── welcome_store.py    # Флаг «приветствие показано»
    ├── excel_export.py     # Запись в XLSX
    ├── import_logic.py     # import_api_operations (парсинг + дедуп + batch)
    ├── jobs.py             # run_import_job (альтернативный путь импорта)
    ├── scheduler.py        # APScheduler + SQLAlchemy job store
    ├── seed.py             # Роли и права
    ├── manage.py           # init_db + seed (CLI)
    ├── bot_handlers.py     # Устаревший тонкий реэкспорт (см. TELEGRAM_LAYER)
    ├── belorusneft_api.py  # Клиент/парсер API (не менять по договорённости)
    ├── bot/
    │   ├── register.py     # Сборка Dispatcher
    │   ├── keyboards.py
    │   ├── notifications.py
    │   ├── utils.py
    │   └── handlers/
    │       ├── user.py
    │       ├── admin_import.py
    │       ├── admin_users.py
    │       └── admin_schedules.py
    └── …                   # legacy_ssl, bot_ref и др.
```

Дальше: [ARCHITECTURE.md →](ARCHITECTURE.md)
