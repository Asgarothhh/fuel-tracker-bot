# Пакет `prototiping.graph`

Спецификация узлов, прогон с трассировкой и обёртка **LangGraph**.

---

## `graph/spec.py`

### `GRAPH_TITLE`

Строка имени графа в трассировке и отчёте (сейчас `"fuel_tracker_prototype"`).

**Пример:**

```python
from prototiping.graph.spec import GRAPH_TITLE

assert isinstance(GRAPH_TITLE, str)
```

---

### `GRAPH_NODES_SPEC`

Список словарей узла:

```python
{
    "id": "уникальный_id_узла",
    "title": "Человекочитаемый заголовок",
    "checks": [chk.check_foo, chk.check_bar, ...],
}
```

Порядок элементов списка = порядок узлов на диаграмме и в прогоне.

---

### `GRAPH_EDGE_ORDER`

Список `id` узлов по цепочке: `[n["id"] for n in GRAPH_NODES_SPEC]`. Используется в `app.py` для рёбер `START → … → END`.

---

### `all_check_functions()`

**Возвращает:** плоский список всех callable из всех `checks` всех узлов (порядок как в спеке).

**Пример:**

```python
from prototiping.graph.spec import all_check_functions

fns = all_check_functions()
assert all(callable(f) for f in fns)
r = fns[0]()  # первая проверка в графе
assert "ok" in r
```

---

### `verify_spec_matches_all_checks()`

Сравнивает множество функций из спеки с `checks.suite.ALL_CHECKS`.

**Исключения:** `RuntimeError`, если состав или длина не совпадают.

**Пример:**

```python
from prototiping.graph.spec import verify_spec_matches_all_checks

verify_spec_matches_all_checks()  # тихо, если всё синхронизировано
```

---

## `graph/trace.py`

### `_print_rich_console(graph_title, nodes_trace, overall_ok)` *(внутренняя)*

Печать дерева проверок и таблицы сводки через Rich (или упрощённый `print`, если Rich нет).

---

### `run_prototype_traced(*, console=True, write_trace_json=True)`

Главная точка **последовательного** прогона всех проверок по `GRAPH_NODES_SPEC`.

**Параметры:**

| Имя | По умолчанию | Описание |
|-----|----------------|----------|
| `console` | `True` | Печать Rich/лога в консоль |
| `write_trace_json` | `True` | Запись `prototiping/.last_prototype_trace.json` |

**Возвращает:** `dict` с ключами:

- `graph`, `overall_ok`, `nodes` — для отчёта и HTML;
- `flat_results` — сырые ответы `_result` по порядку вызовов.

**Пример:**

```python
from prototiping.graph.trace import run_prototype_traced

payload = run_prototype_traced(console=False, write_trace_json=False)
assert payload["overall_ok"]
for node in payload["nodes"]:
    print(node["id"], node["ok"])
```

---

### `load_last_trace()`

Читает `.last_prototype_trace.json` с диска.

**Возвращает:** `dict | None` (если файла нет или JSON битый).

**Пример:**

```python
from prototiping.graph.trace import load_last_trace

t = load_last_trace()
if t:
    print(t["overall_ok"])
```

---

## `graph/app.py`

### `ScenarioState` (TypedDict)

Состояние графа LangGraph: поле `results` с аннотацией `Annotated[list, operator.add]` для накопления списков от узлов.

---

### `_node_factory(node_id, fns)` *(внутренняя)*

Строит callable узла: вызывает все функции из `fns` и возвращает `{"results": [...]}`.

---

### `build_scenario_graph()`

**Возвращает:** скомпилированный граф LangGraph (`invoke`, `get_graph` и т.д.).

**Пример:**

```python
from prototiping.graph.app import build_scenario_graph

g = build_scenario_graph()
out = g.invoke({}, config={"run_name": "demo", "tags": ["prototyping"]})
```

---

### `run_full_scenario_graph()`

`build_scenario_graph()` + `invoke` с фиксированными тегами для LangSmith.

**Возвращает:** финальное состояние (в т.ч. агрегированный `results`).

---

### `summarize_results(final)`

**Параметры:**

| Имя | Описание |
|-----|----------|
| `final` | Результат `graph.invoke` |

**Возвращает:** `(ok_count: int, fail_count: int, results: list[dict])`

**Пример:**

```python
from prototiping.graph.app import build_scenario_graph, summarize_results

g = build_scenario_graph()
final = g.invoke({})
ok_n, fail_n, results = summarize_results(final)
print(ok_n, fail_n, len(results))
```

---

## Экспорт `graph/__init__.py`

Реэкспорт: `GRAPH_NODES_SPEC`, `GRAPH_TITLE`, `build_scenario_graph`, `load_last_trace`, `run_full_scenario_graph`, `run_prototype_traced`, `summarize_results`, `verify_spec_matches_all_checks`.

---

← [Оглавление](../README.md)
