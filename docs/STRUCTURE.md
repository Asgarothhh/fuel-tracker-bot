# Структура документации и `prototiping/`

## Новая структура документации (`docs/`)

```text
docs/
├── README.md                 общий навигатор
├── PROTOTIPING/
│   ├── README.md
│   └── MODULES/
├── BOT_SRC/
│   ├── README.md
│   └── MODULES/
├── WEB/
│   ├── README.md
│   └── MODULES/
├── OCR/
│   ├── README.md
│   ├── PIPELINE.md
│   ├── DATA_CONTRACTS.md
│   ├── INTEGRATION.md
│   ├── DEDUP_AND_VALIDATION.md
│   └── TROUBLESHOOTING.md
└── ... (legacy подробные документы)
```

---

# Структура `prototiping/` по папкам

Корень пакета: **`prototiping/`** (рядом с `src/` в репозитории).

## Дерево каталогов (упрощённо)

```text
prototiping/
├── docs/                    ← legacy-справка внутри модуля (может отличаться от `docs/`)
│   ├── README.md
│   ├── QUICKSTART.md
│   ├── REPORT_TEMPLATE.md
│   ├── GRAPH_PREVIEW_HTML.md
│   ├── HOW_IT_WORKS.md
│   ├── ADDING_SCENARIOS.md
│   └── MODULES/
│       ├── DB.md
│       ├── CHECKS.md
│       ├── GRAPH.md
│       ├── REPORTING.md
│       ├── LIB.md
│       ├── TOOLS.md
│       └── TESTS.md
├── checks/                  ← проверки и метаданные для отчёта
│   ├── suite.py             функции check_* и список ALL_CHECKS
│   └── scenarios.py         SCENARIO_META (id S01…, kind P/N, версии)
├── graph/                   ← граф сценариев
│   ├── spec.py              GRAPH_NODES_SPEC, GRAPH_EDGE_ORDER
│   ├── trace.py             run_prototype_traced(), JSON-трассировка
│   └── app.py               LangGraph: build_scenario_graph(), invoke
├── db/                      ← in-memory БД для проверок и разделов отчёта
│   ├── memory.py
│   ├── evolution.py
│   └── snapshot.py
├── reporting/               ← сборка REPORT.md
│   ├── template.md          шаблон с плейсхолдерами {{…}}
│   ├── build.py             render_report(), write_report()
│   ├── diagram.py           Mermaid / ASCII для отчёта
│   └── ocr.py               секция OCR (картинки, Tesseract, LLM)
├── lib/                     ← пути и .env
│   ├── paths.py
│   └── env.py
├── tools/
│   └── graph_preview.py     CLI → output/graph_preview.html
├── tests/                   pytest
│   └── test_prototype_graph.py
├── conftest.py              env для pytest + запись отчёта после сессии
├── __main__.py              python -m prototiping
├── REPORT.md                сгенерированный отчёт (не править руками)
├── .last_prototype_trace.json
└── output/graph_preview.html
```

## Роли папок (таблица)

| Папка / файл | Назначение |
|--------------|------------|
| **`checks/`** | Вся «логика теста»: что вызываем из `src/`, что считаем успехом. |
| **`graph/`** | Как сгруппировать проверки в узлы и в каком порядке их гонять. |
| **`db/`** | Общая схема SQLite in-memory и демо-данные для разделов отчёта про БД. |
| **`reporting/`** | Склейка текста отчёта, графики, OCR-секция. |
| **`lib/`** | `PROTO_DIR`, `ROOT_DIR`, загрузка `prototiping/.env`. |
| **`tools/`** | Утилиты командной строки (HTML-превью). |
| **`tests/`** | Pytest: целостность графа и каждая `check_*` по отдельности. |

## Зависимости между частями

```mermaid
flowchart LR
    subgraph checks_layer["checks"]
        SUITE["suite.py"]
        SCEN["scenarios.py"]
    end

    subgraph graph_layer["graph"]
        SPEC["spec.py"]
        TR["trace.py"]
        APP["app.py"]
    end

    SUITE --> SPEC
    SUITE --> TR
    SUITE --> APP
    SPEC --> TR
    SPEC --> APP
    SCEN --> BUILD["reporting/build.py"]
    TR --> BUILD
```

- **`spec.py`** импортирует функции из **`suite.py`** (не наоборот).
- **`scenarios.py`** не импортирует граф; отчёт читает метаданные по **имени функции** `check_*`.

---

## Справочник API по подпакетам

Справочник по `prototiping/*` теперь находится в **`docs/PROTOTIPING/MODULES/`** (см. [docs/README.md](README.md)).

---

← [Как это работает](PROTOTIPING/HOW_IT_WORKS.md) · [Оглавление](README.md) · [Добавление сценариев →](PROTOTIPING/ADDING_SCENARIOS.md)
