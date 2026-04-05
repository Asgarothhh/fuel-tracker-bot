# Пакет `prototiping.reporting`

Сборка **`REPORT.md`**, визуализация графа в Markdown и секция **OCR**.

---

## `reporting/__init__.py`

Публичный API:

```python
from prototiping.reporting import render_report, write_report
```

---

## `reporting/build.py`

### `_get_console(verbose)` *(внутренняя)*

При `verbose=True` возвращает `rich.console.Console`, иначе `None`.

---

### `_step(console, msg, *, style="cyan")` *(внутренняя)*

Печать этапа сборки отчёта.

---

### `collect_results_from_trace(trace_full)`

Склеивает узлы и проверки из трассировки в плоский список строк для таблицы.

**Параметры:**

| Имя | Описание |
|-----|----------|
| `trace_full` | Результат `run_prototype_traced` |

**Возвращает:** `list[dict]` — поля из `SCENARIO_META` + `graph_node`, `check_name`, `ok`, `detail`, `run_order`.

**Пример:**

```python
from prototiping.graph.trace import run_prototype_traced
from prototiping.reporting.build import collect_results_from_trace

t = run_prototype_traced(console=False, write_trace_json=False)
rows = collect_results_from_trace(t)
assert rows[0]["run_order"] == 1
```

---

### `_escape_md_cell(s)` *(внутренняя)*

Экранирование `|` и переносов для ячеек Markdown-таблицы.

---

### `build_table(rows)`

**Параметры:** `rows` — как у `collect_results_from_trace`.

**Возвращает:** строка Markdown с таблицей (колонки №, Код, узел, …).

**Пример:**

```python
from prototiping.reporting.build import build_table

md = build_table(
    [
        {
            "id": "S01",
            "run_order": 1,
            "graph_node": "n",
            "title": "T",
            "code_under_test": "c",
            "ok": True,
            "detail": "",
        }
    ]
)
```

---

### `build_details(rows)`

Те же `rows` → развёрнутые секции `### N. заголовок` для раздела деталей отчёта.

---

### `_safe_section(builder, title, console)` *(внутренняя)*

Выполняет `builder()` (функция без аргументов → `str`); при исключении возвращает блок ошибки Markdown.

---

### `render_report(*, verbose=False)`

Полный текст отчёта: прогон графа, подстановка всех плейсхолдеров шаблона.

**Пример:**

```python
from prototiping.reporting.build import render_report

body = render_report(verbose=False)
assert "{{" not in body
```

---

### `write_report(path=None, *, verbose=False)`

Сначала целевой файл **сразу перезаписывается** короткой заглушкой («идёт сборка»), затем выполняется `render_report` и файл снова перезаписывается полным отчётом (по умолчанию `prototiping/REPORT.md`).

**Пример:**

```python
from pathlib import Path
from prototiping.reporting.build import write_report

write_report(verbose=True)
write_report(Path("/tmp/out.md"), verbose=False)
```

---

## `reporting/diagram.py`

### `_ascii_pipeline(nodes)` *(внутренняя)*

ASCII-схема цепочки узлов в блоке ` ```text `.

---

### `build_mermaid_source_for_browser(trace)`

**Параметры:** `trace` — словарь трассировки или `None`.

**Возвращает:** строка Mermaid `flowchart LR` без HTML-обёртки (для браузера / `mermaid.run`).

**Пример:**

```python
from prototiping.reporting.diagram import build_mermaid_source_for_browser

src = build_mermaid_source_for_browser(None)
assert "flowchart" in src
```

---

### `build_graph_visual_markdown(trace)`

Таблица узлов, цепочка, ASCII, блок Mermaid, инструкция для HTML — фрагмент для `{{GRAPH_VISUAL}}`.

**Пример:**

```python
from prototiping.graph.trace import run_prototype_traced
from prototiping.reporting.diagram import build_graph_visual_markdown

md = build_graph_visual_markdown(
    run_prototype_traced(console=False, write_trace_json=False)
)
```

---

## `reporting/ocr.py`

### `_exc_block`, `_gather_images`, `_apply_tesseract_path`, `_truncate`, `_source_tag`, `_report_asset_filename` *(внутренние)*

Вспомогательные функции для `build_ocr_section_markdown` (ошибки, поиск картинок, Tesseract, обрезка текста, имена в `report_assets/` вида `NN_export_stem_abc123.png`).

---

### `build_ocr_section_markdown()`

Собирает секцию OCR: копирует изображения из `prototiping/export/` и `exports/`, при наличии ключей и Tesseract запускает цепочку OCR + LLM.

**Параметры:** `console` — Rich-консоль из `render_report` (прогресс по файлам); `use_spinner` — анимация ожидания на stderr (`None` → если stderr — TTY). Env: `OPENROUTER_API_KEY`, `TESSERACT_CMD`, `OCR_MODEL_NAME`, пути из `lib.paths`.

**Поведение:** для каждого файла вызывается **`SmartFuelOCR.run_pipeline(path)`** из `src/ocr/engine.py` (тот же пайплайн, что в приложении). Опционально `PROTOTIPE_OCR_MAX_FILES` — ограничить число изображений в отчёте.

**Возвращает:** `str` для `{{OCR_SAMPLES}}`. При ошибке инициализации или исключении — блок в Markdown с traceback; при `run_pipeline` → `None` — пояснение про `ocr_processing.log`.

**Пример:**

```python
from prototiping.reporting.ocr import build_ocr_section_markdown

md = build_ocr_section_markdown()  # без Rich
print(md[:200])
```

---

## `reporting/template.md`

Файл-шаблон Markdown с плейсхолдерами `{{…}}`. Подстановка — в `build.render_report`.

**Как править шаблон, какие теги существуют, типичные ошибки:** отдельный документ **[REPORT_TEMPLATE.md](../REPORT_TEMPLATE.md)**.

---

← [Оглавление](../README.md)
