# Fuel Tracker Bot

Монорепозиторий системы учёта заправок: Telegram-бот и доменная логика в `src/`, HTTP API и веб-клиент в `web/`, отдельный контур сценарных проверок в `prototiping/`. Одна модель данных и импорт операций обслуживают и бота, и API.

## Возможности

- **Telegram-бот** — привязка пользователей, карты, авто, сценарии подтверждения операций, в т.ч. личные чеки с OCR.
- **Импорт из API Белоруснефть** — периодический и ручной импорт, дедупликация, согласование с существующими записями.
- **OCR чеков** — Tesseract + LLM-структурирование, дедуп по хэшу и бизнес-ключам; подробности в [docs/OCR/README.md](docs/OCR/README.md).
- **Excel-отчёты** — выгрузка согласованных данных для отчётности.
- **Web** — FastAPI backend и React (Vite) frontend для операций, пользователей и отчётов.
- **Прототипирование** — граф сценариев P/N, метрики TP/FN/TN/FP, `REPORT.md` и превью графа без обязательных правок production-кода.

## Стек

| Область | Технологии |
|---------|------------|
| Бот | Python 3, aiogram 3, APScheduler |
| Данные | SQLAlchemy 2, PostgreSQL (через `DATABASE_URL`) |
| OCR | OpenCV, pytesseract, Pillow, LangChain/OpenRouter |
| Web API | FastAPI, Uvicorn |
| Frontend | React, Vite, Ant Design |
| Проверки | LangGraph, pytest, in-memory SQLite в `prototiping/` |

## Требования

- Python 3.11+ (рекомендуется).
- **PostgreSQL** — строка подключения в `DATABASE_URL`.
- **Tesseract** и языковые пакеты `rus`/`eng` — для OCR (см. [docs/OCR/TROUBLESHOOTING.md](docs/OCR/TROUBLESHOOTING.md)).
- Для OCR с LLM — ключ **OpenRouter** (`OPENROUTER_API_KEY`).

## Установка

```bash
git clone <repository-url>
cd fuel-tracker-bot
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r web/backend/requirements.txt   # доп. зависимости веб-слоя (openpyxl и др.)
```

Создайте файл `.env` в корне (или положите переменные в окружение процесса). Минимально для бота и API:

| Переменная | Назначение |
|------------|------------|
| `DATABASE_URL` | PostgreSQL, например `postgresql+psycopg2://user:pass@host:5432/dbname` |
| `BOT_TOKEN` | токен Telegram-бота |
| `TOKEN_SALT` | соль для кодов привязки |
| `ADMIN_TELEGRAM_ID` | ID администратора в Telegram |

Импорт API Белоруснефть и прочие переменные — см. [src/app/config.py](src/app/config.py) и [docs/BOT_SRC/MODULES/SERVICES_AND_CONFIG.md](docs/BOT_SRC/MODULES/SERVICES_AND_CONFIG.md).

Инициализация схемы БД выполняется при старте бота (`init_db` в [src/run_bot.py](src/run_bot.py)); при необходимости используйте Alembic из проекта.

## Запуск

### Telegram-бот

Из корня репозитория (нужен `PYTHONPATH` для пакета `src`):

```bash
export PYTHONPATH=.
python src/run_bot.py
```

### Backend API (FastAPI)

```bash
export PYTHONPATH=.
uvicorn web.backend.main:app --reload --host 0.0.0.0 --port 8000
```

Проверка: `GET http://localhost:8000/api/health` → `{"status":"ok"}`. CORS в [web/backend/main.py](web/backend/main.py) настроен под `localhost:5173` и `localhost:3000`.

### Frontend (Vite)

```bash
cd web/frontend
npm install
npm run dev
```

### Прототипирование и отчёты

```bash
export PYTHONPATH=.
python -m prototiping
pytest prototiping -q
python -m prototiping.tools.graph_preview
```

Артефакты: `prototiping/REPORT.md`, `prototiping/.last_prototype_trace.json`, `prototiping/output/graph_preview.html`.

## Документация

Центральная карта: **[docs/README.md](docs/README.md)**.

| Раздел | Содержание |
|--------|------------|
| [docs/BOT_SRC/](docs/BOT_SRC/README.md) | Бот, `src/app`, права, импорт, Excel |
| [docs/WEB/](docs/WEB/README.md) | API, сервисы, интеграция с frontend |
| [docs/PROTOTIPING/](docs/PROTOTIPING/README.md) | Сценарии P/N, граф, отчёты |
| [docs/OCR/](docs/OCR/README.md) | Pipeline OCR, контракты, дедуп, troubleshooting |
| [docs/STRUCTURE.md](docs/STRUCTURE.md) | Дерево `docs/` и пакета `prototiping/` |

**Имена папок:** в репозитории каталог документации по прототипированию называется `docs/PROTOTIPING/` (рядом с ним Python-пакет `prototiping/` — это разные имена, ссылки везде ведут на актуальные пути).

## Архитектура на одном экране

```mermaid
flowchart LR
    TG[Telegram] --> BOT[src/app бот]
    FE[Web frontend] --> API[FastAPI web/backend]
    BOT --> DB[(PostgreSQL)]
    API --> DB
    BOT --> XLS[Excel export]
    PT[prototiping] --> BOT
    PT --> API
```
