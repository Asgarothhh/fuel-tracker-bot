# Архитектура приложения (`src/`)

## Роль системы

Telegram-бот учитывает заправки по **двум каналам**:

1. **API (карта)** — операции подтягиваются из отчётов, сохраняются в БД, пользователям уходят запросы на подтверждение.
2. **Личные средства** — пользователь присылает фото чека; OCR и LLM формируют черновик операции; после проверок данные попадают в Excel.

Каналы **не смешиваются на уровне бизнес-правил**: чеки за личные средства не привязываются к API Белоруснефти.

## Компоненты (логический вид)

```mermaid
flowchart TB
    subgraph clients["Клиенты"]
        TG[Telegram]
    end

    subgraph runtime["Процесс run_bot.py"]
        DP[aiogram Dispatcher]
        MW[ActiveUserMiddleware]
        H[Handlers: user / admin_*]
        SCH[APScheduler]
    end

    subgraph data["Данные"]
        DB[(SQLAlchemy / БД)]
        XLS[(exports/*.xlsx)]
        WEL[welcome_shown.json]
    end

    subgraph external["Внешние сервисы"]
        BAPI[Belorusneft API]
        OR[OpenRouter LLM]
        TESS[Tesseract]
    end

    TG --> DP
    DP --> MW --> H
    H --> DB
    H --> XLS
    H --> WEL
    SCH --> H
    SCH -.->|импорт по расписанию| BAPI
    H -->|админ импорт| BAPI
    H --> TESS
    H --> OR
```

## Жизненный цикл процесса бота

```mermaid
sequenceDiagram
    participant Main as run_bot.main
    participant Bot as aiogram.Bot
    participant DP as Dispatcher
    participant DB as init_db
    participant SCH as scheduler

    Main->>Bot: создать(token)
    Main->>DP: register_handlers
    Main->>DB: init_db (create_all)
    Main->>SCH: init_scheduler
    Main->>SCH: schedule_daily_import из таблицы schedules
    Main->>DP: start_polling(bot)
    Note over Main: до Ctrl+C
    Main->>Bot: session.close
```

## Потоки данных (упрощённо)

| Поток | Откуда | Куда | Ключевые модули |
|-------|--------|------|-----------------|
| Подтверждение карты | API → БД → Telegram | БД, Excel | `import_logic` / `jobs`, `handlers/user`, `excel_export` |
| Чек за личные средства | Фото → OCR | БД, Excel | `ocr/engine`, `handlers/user`, `excel_export` |
| Привязка аккаунта | Код в чат | `users`, `link_tokens` | `tokens`, `handlers/user` |

## Зависимости между пакетами

```mermaid
graph LR
    run_bot --> bot_register
    run_bot --> scheduler
    run_bot --> db
    bot_register --> handlers
    handlers --> db
    handlers --> models
    handlers --> permissions
    handlers --> ocr_engine
    handlers --> excel_export
    import_logic --> belorusneft_api
    jobs --> belorusneft_api
    jobs --> bot_handlers
    ocr_engine --> models
    ocr_engine --> db
```

`belorusneft_api` — **лист изменений**: при доработках сценария личных средств этот модуль не трогаем.

## Соглашения для разработки

- Сессия БД: предпочтительно **`with get_db_session() as db:`** — commit/rollback/close централизованы в `db.py`.
- Статусы `FuelOperation.status` используются и в UI, и в Excel; новые значения согласовывать с `excel_export.STATUS_RU` и фильтрами в админке.
- Права админа проверяются через `user_has_permission(..., "admin:manage")` и декоратор `@require_permission`.

← [Оглавление](README.md) · [Слой данных →](DATA_LAYER.md)
