# PROTOTIPING / CHECKS

## Файлы

- `prototiping/checks/suite.py`
- `prototiping/checks/scenarios.py`

## Что находится в модуле

- функции `check_*`
- единый список `ALL_CHECKS`
- метаданные `SCENARIO_META` (`id`, `kind`, `scenario_version`, ...)

## Классы сценариев

- `standard` -> класс `P`
- `breaker` -> класс `N`

## Текущие группы

- core app checks (`S01...S15`)
- breaker checks (`S16...S21`)
- web checks (`S22...S36`)

## Правила

1. любая `check_*` должна возвращать `{name, ok, detail}`
2. функция обязана быть в `ALL_CHECKS`
3. функция обязана быть в `GRAPH_NODES_SPEC`
4. в `SCENARIO_META` должны быть `kind` и `scenario_version`

## Примеры реализации

```python
# prototiping/checks/suite.py
def _result(name: str, ok: bool, detail: str = "") -> dict:
    return {"name": name, "ok": ok, "detail": detail}

def check_parse_api_datetime() -> dict:
    dt = parse_api_datetime("2020-01-15T10:20:30Z")
    ...
```

```python
# prototiping/checks/scenarios.py
SCENARIO_META = {
    "check_parse_api_datetime": {
        "id": "S03",
        "kind": "standard",
        "scenario_version": SCENARIO_SCHEMA_VERSION,
        ...
    }
}
```

## Связанные документы

- [graph integration](GRAPH.md)
- [overview](OVERVIEW.md)
- [report interpretation](REPORTING.md)
