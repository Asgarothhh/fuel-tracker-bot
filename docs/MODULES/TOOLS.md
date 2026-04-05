# Пакет `prototiping.tools`

Утилиты командной строки. Сейчас основная — **генерация HTML-превью графа**.

Полное описание страницы (Mermaid 11, структура, CDN, кастомизация): **[GRAPH_PREVIEW_HTML.md](../GRAPH_PREVIEW_HTML.md)**.

---

## `tools/graph_preview.py`

### `_load_trace()` *(внутренняя)*

Читает `TRACE_JSON`, если файл есть и JSON валиден; иначе выполняет `run_prototype_traced(console=False, write_trace_json=True)` после `load_prototype_env()`.

**Возвращает:** `dict | None`.

---

### `build_scenarios_sections_html(trace)`

Строит HTML-блок: карточки по узлам и таблицы проверок с метаданными из `checks/scenarios.py`.

**Параметры:**

| Имя | Описание |
|-----|----------|
| `trace` | Словарь трассировки (`nodes`, `graph`, `overall_ok`) |

**Возвращает:** фрагмент HTML (`<section>…</section>`).

**Пример (в коде, не CLI):**

```python
import json
from pathlib import Path
from prototiping.lib.paths import TRACE_JSON
from prototiping.tools.graph_preview import build_scenarios_sections_html

trace = json.loads(TRACE_JSON.read_text(encoding="utf-8"))
html_chunk = build_scenarios_sections_html(trace)
assert "node-card" in html_chunk
```

---

### `build_html(trace)`

Полная HTML-страница: стили, **Mermaid 11** (ESM CDN), `<div class="mermaid">`, секция сценариев, сырой текст в `<pre><code>`, подвал с временем сборки.

**Параметры:**

| Имя | Описание |
|-----|----------|
| `trace` | Словарь трассировки |

**Возвращает:** `str` (`<!DOCTYPE html>…`).

**Пример:**

```python
from prototiping.graph.trace import run_prototype_traced
from prototiping.tools.graph_preview import build_html

trace = run_prototype_traced(console=False, write_trace_json=False)
page = build_html(trace)
Path("preview.html").write_text(page, encoding="utf-8")
```

---

### `main()`

Точка входа CLI: выставляет те же `os.environ.setdefault`, что и отчёт, загружает трассировку, пишет `OUTPUT_DIR / graph_preview.html` (имя в константе `GRAPH_PREVIEW_FILENAME`), печатает абсолютный путь в stdout.

**Запуск:**

```bash
cd /path/to/fuel-tracker-bot
PYTHONPATH=. python -m prototiping.tools.graph_preview
```

---

## `tools/__init__.py`

Служебный пакет; отдельных символов не реэкспортирует.

---

← [Оглавление](../README.md)
