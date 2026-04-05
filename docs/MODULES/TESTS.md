# `prototiping/tests` и связанные файлы

Pytest-тесты пакета и хуки в **корне** `prototiping/`.

---

## `tests/test_prototype_graph.py`

### `test_graph_spec_matches_all_checks()`

Вызывает `verify_spec_matches_all_checks()` — защита от рассинхрона `graph/spec.py` и `checks/suite.ALL_CHECKS`.

---

### фикстура `graph` (scope=`module`)

**Возвращает:** результат `build_scenario_graph()` — один скомпилированный граф на модуль тестов.

**Пример использования фикстуры:**

```python
def test_my_node_order(graph):
    # graph — уже скомпилированный LangGraph
    assert graph is not None
```

---

### `test_scenario_graph_runs_with_rich_console(graph)`

Прогон `run_prototype_traced(console=True, write_trace_json=True)`: все узлы успешны, длина `flat_results` равна `len(ALL_CHECKS)`.

---

### `test_langgraph_invoke_matches_spec(graph)`

Тот же набор проверок через `graph.invoke({})` и `summarize_results`: без провалов, длина `results` совпадает с `ALL_CHECKS`.

---

### `test_individual_check(check_fn)`

Параметризация по `ALL_CHECKS`: каждая функция вызывается отдельно, ожидается `ok=True`.

**Пример ручного повтора одного сценария:**

```bash
PYTHONPATH=. pytest prototiping/tests/test_prototype_graph.py::test_individual_check -k check_tokens_flow -v
```

---

## `prototiping/conftest.py` (корень пакета)

При импорте подмешивает `load_prototype_env()` и задаёт переменные по умолчанию (`DATABASE_URL`, `BOT_TOKEN`, …) для изолированного прогона.

### `pytest_addoption(parser)`

Регистрирует опцию:

```text
--no-prototype-report
```

Если указана, после сессии **`REPORT.md` не перезаписывается**.

**Пример:**

```bash
PYTHONPATH=. pytest prototiping --no-prototype-report -q
```

---

### `pytest_sessionfinish(session, exitstatus)`

После тестов вызывает `write_report()` (если нет `--no-prototype-report`), печатает путь к отчёту или ошибку в stderr.

---

## `prototiping/__main__.py`

Запуск **`python -m prototiping`** → `write_report(verbose=True)` (Rich-этапы в консоли).

```bash
PYTHONPATH=. python -m prototiping
```

---

← [Оглавление](../README.md)
