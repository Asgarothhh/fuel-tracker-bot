# Пакет `prototiping.lib`

Общие **пути** к файлам пакета и загрузка **переменных окружения** для прототипа.

---

## `lib/paths.py`

Все значения — объекты `pathlib.Path`.

| Константа | Описание |
|-----------|----------|
| `PROTO_DIR` | Каталог `prototiping/` |
| `ROOT_DIR` | Корень репозитория (`PROTO_DIR.parent`) |
| `EXPORT_DIR` | `prototiping/export/` — вход для OCR-отчёта |
| `ROOT_EXPORTS_DIR` | `exports/` в корне репозитория |
| `REPORT_ASSETS` | `prototiping/report_assets/` — копии изображений для отчёта |
| `OUTPUT_DIR` | `prototiping/output/` — каталог артефактов |
| `GRAPH_PREVIEW_HTML` | `prototiping/output/graph_preview.html` — превью графа |
| `REPORT_MD` | `prototiping/REPORT.md` |
| `TRACE_JSON` | `prototiping/.last_prototype_trace.json` |
| `REPORT_TEMPLATE` | `prototiping/reporting/template.md` |

**Пример:**

```python
from prototiping.lib.paths import PROTO_DIR, REPORT_MD, TRACE_JSON

print(REPORT_MD.is_file())  # True после сборки отчёта
text = TRACE_JSON.read_text(encoding="utf-8") if TRACE_JSON.is_file() else ""
```

---

## `lib/env.py`

### `load_prototype_env()`

Загружает переменные окружения:

1. `ROOT_DIR / ".env"` — без перезаписи уже заданных ключей;
2. `PROTO_DIR / ".env"` — с `override=True` (имеет приоритет).

**Параметры:** нет.

**Возвращает:** `None`.

**Пример:**

```python
import os
from prototiping.lib.env import load_prototype_env

load_prototype_env()
key = os.environ.get("OPENROUTER_API_KEY")
```

Вызывается при импорте `prototiping.conftest`, в `graph_preview.main`, в `reporting.build` (через цепочку импортов) — обычно не нужно вызывать вручную, кроме отдельных скриптов.

---

## `lib/__init__.py`

Реэкспорт: `PROTO_DIR`, `ROOT_DIR`.

```python
from prototiping.lib import PROTO_DIR, ROOT_DIR
```

---

← [Оглавление](../README.md)
