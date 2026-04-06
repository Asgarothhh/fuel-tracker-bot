# Учёт заправок 

# Документация репозитория

В каталоге `docs/` собраны материалы по **боевому приложению** (`src/`) и по пакету **прототипирования** (`prototiping/`).

## Приложение: учёт заправок (Telegram-бот)

| Документ | Содержание |
|----------|------------|
| [MODULES_SRC/README.md](MODULES_SRC/README.md) | **Документация для разработчиков** по всем модулям `src/` (архитектура, ER, FSM, диаграммы) |
| [TELEGRAM_BOT.md](TELEGRAM_BOT.md) | Команды, приветствие, структура бота (кратко) |
| [PERSONAL_FUNDS_SCENARIO.md](PERSONAL_FUNDS_SCENARIO.md) | Сценарий «за личные средства» по шагам ТЗ |
| [OCR_MODULE.md](OCR_MODULE.md) | Пайплайн OCR, переменные окружения (кратко) |
| [EXCEL_AND_DATA.md](EXCEL_AND_DATA.md) | Excel, справочники авто и пользователей |

Код клиента **API Белоруснефти** в репозитории не изменялся; интеграция описывается только на уровне архитектуры в исходниках.

---

# Документация прототипирования

Ниже — **как устроен** каталог `prototiping/`, **как запускать** прогоны и отчёты и **как добавлять свои проверки** (сценарии) без путаницы.

Сценарии **не заменяют** код приложения: они импортируют и вызывают уже существующие функции из `src/` (см. [HOW_IT_WORKS.md](HOW_IT_WORKS.md)).

## Оглавление

### Старт и концепция

| Документ | О чём |
|----------|--------|
| [QUICKSTART.md](QUICKSTART.md) | Пошагово: написание тестов/сценариев, примеры, диаграммы |
| [HOW_IT_WORKS.md](HOW_IT_WORKS.md) | Зачем пакет, поток до `REPORT.md`, граф LangGraph, артефакты |
| [STRUCTURE.md](STRUCTURE.md) | Дерево каталогов, роли модулей, диаграммы |
| [ADDING_SCENARIOS.md](ADDING_SCENARIOS.md) | Краткая схема добавления сценария + ссылка на QUICKSTART |
| [REPORT_TEMPLATE.md](REPORT_TEMPLATE.md) | Как собирается отчёт из `reporting/template.md`, все `{{…}}`, как править шаблон |
| [GRAPH_PREVIEW_HTML.md](GRAPH_PREVIEW_HTML.md) | Как собирается `output/graph_preview.html`, Mermaid 11, структура страницы, офлайн |

### Справочник по подпакетам (`docs/MODULES/`)

| Папка / область | Файл |
|-----------------|------|
| `prototiping/db/` | [MODULES/DB.md](MODULES/DB.md) |
| `prototiping/checks/` | [MODULES/CHECKS.md](MODULES/CHECKS.md) |
| `prototiping/graph/` | [MODULES/GRAPH.md](MODULES/GRAPH.md) |
| `prototiping/reporting/` | [MODULES/REPORTING.md](MODULES/REPORTING.md) |
| `prototiping/lib/` | [MODULES/LIB.md](MODULES/LIB.md) |
| `prototiping/tools/` | [MODULES/TOOLS.md](MODULES/TOOLS.md) |
| `prototiping/tests/` + `conftest.py`, `__main__.py` | [MODULES/TESTS.md](MODULES/TESTS.md) |

## Быстрый старт (команды)

Из **корня репозитория** (нужен `PYTHONPATH=.`):

```bash
PYTHONPATH=. python -m prototiping
PYTHONPATH=. pytest prototiping -q
PYTHONPATH=. python -m prototiping.tools.graph_preview
```

Первая команда — `REPORT.md` и Rich в консоли; вторая — pytest и перезапись отчёта; третья — HTML-превью графа (подробнее [GRAPH_PREVIEW_HTML.md](GRAPH_PREVIEW_HTML.md)).

Отчёты и слепки:

- `prototiping/REPORT.md` — человекочитаемый отчёт
- `prototiping/.last_prototype_trace.json` — трассировка последнего прогона
- `prototiping/output/graph_preview.html` — превью графа в браузере

## Одна фраза

**Прототипирование** — это набор **автоматических проверок** кода приложения (`src/`), согласованных со **спецификацией графа** (`graph/spec.py`), с **отчётом** и **HTML-превью**, без обязательного изменения боевого кода ради тестов.

Дальше: [Как это работает →](HOW_IT_WORKS.md)
