# GRAPH_PREVIEW_HTML: страница `graph_preview.html`

Аналог того, как [REPORT_TEMPLATE.md](REPORT_TEMPLATE.md) описывает сборку **Markdown**-отчёта: здесь — как получается **HTML**-превью графа сценариев и что в нём внутри.

---

## Назначение

Одна статическая страница для **браузера**: интерактивная диаграмма **Mermaid**, таблицы по узлам и проверкам (метаданные из `checks/scenarios.py`), исходник Mermaid для копирования. Данные берутся из той же трассировки, что и для `REPORT.md` — файл `prototiping/.last_prototype_trace.json`.

---

## Как сгенерировать

Из **корня репозитория** (нужен `PYTHONPATH=.`):

```bash
PYTHONPATH=. python -m prototiping.tools.graph_preview
```

В stdout печатается **абсолютный путь** к файлу. По умолчанию:

`prototiping/output/graph_preview.html`

Откройте его в браузере (двойной клик или `xdg-open`, и т.п.).

Тот же файл **автоматически пересобирается** в конце `write_report()` — то есть при `PYTHONPATH=. python -m prototiping` и при `pytest prototiping` без `--no-prototype-report` (после записи `REPORT.md`). Сначала в `output/graph_preview.html` кладётся короткая заглушка, затем она заменяется полной страницей.

**Когда появляется JSON трассировки**

- после `PYTHONPATH=. python -m prototiping`, или  
- после `PYTHONPATH=. pytest prototiping` (если не передан `--no-prototype-report`), или  
- если файла ещё нет — команда `graph_preview` сама выполнит короткий прогон графа и запишет JSON.

---

## Откуда берётся код

| Часть | Модуль | Роль |
|--------|--------|------|
| Полная HTML-страница | `prototiping/tools/graph_preview.py` → `build_html()` | Разметка, CSS, подключение Mermaid, сборка секций |
| Текст диаграммы Mermaid | `prototiping/reporting/diagram.py` → `build_mermaid_source_for_browser()` | `flowchart LR`, узлы, стили `okNode` / `failNode` |
| Таблицы сценариев | `graph_preview.py` → `build_scenarios_sections_html()` | Читает `trace["nodes"]` и `SCENARIO_META` |

Исходник Mermaid в отчёте Markdown (`{{GRAPH_VISUAL}}`) и в HTML **один и тот же** (генерируется `diagram.py`).

---

## Структура страницы

1. **Заголовок** — имя графа, итог прогона (OK / есть ошибки), подсказка про `.last_prototype_trace.json`.
2. **Навигация** — якоря на блоки ниже.
3. **Диаграмма** — контейнер `.diagram-wrap`, внутри `<div class="mermaid mermaid-render">` с сырым текстом Mermaid (не экранированным как HTML — так требует Mermaid).
4. **Подробно по узлам** — `<section id="scenarios-detail">`: для каждого узла карточка и таблица проверок (№, код S01…, функция, заголовок, код под тест, описание, результат, детали).
5. **Исходник Mermaid** — `<pre><code>` с **экранированным** текстом (безопасно копировать).
6. **Подвал** — время генерации (UTC) и URL ESM Mermaid.

---

## Mermaid и сеть

Страница подключает **Mermaid 11** с CDN (jsDelivr), модуль ESM:

`https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs`

Скрипт инициализации: `startOnLoad: false`, затем `mermaid.run({ querySelector: ".mermaid-render" })`, тема `dark`, `securityLevel: "strict"`.

**Офлайн:** без интернета диаграмма не отрисуется; таблицы и блок с исходником остаются читаемыми. Для офлайна можно скачать бандл Mermaid и подставить локальный путь в `graph_preview.py` (константа `MERMAID_ESM`).

---

## Кастомизация

- **Стили** — константа `GRAPH_PREVIEW_CSS` в `graph_preview.py`.
- **Имя файла** — `GRAPH_PREVIEW_FILENAME` в том же модуле.
- **Содержимое диаграммы** — править `build_mermaid_source_for_browser()` в `diagram.py` (тогда изменится и фрагмент в `REPORT.md`).

Не дублируйте логику узлов в HTML вручную: расширяйте трассировку и `SCENARIO_META`, а секции подтянутся из `build_scenarios_sections_html()`.

---

## См. также

- [MODULES/TOOLS.md](MODULES/TOOLS.md) — сигнатуры функций CLI-модуля  
- [REPORT_TEMPLATE.md](REPORT_TEMPLATE.md) — шаблон Markdown-отчёта  
- [MODULES/GRAPH.md](MODULES/GRAPH.md) — прогон графа и JSON трассировки  

---

← [Оглавление](README.md)
