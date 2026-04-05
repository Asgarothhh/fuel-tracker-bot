# Пакет `prototiping.db`

In-memory SQLite и демо-сценарии для **разделов отчёта** про базу данных. Проверки в `checks/suite.py` используют те же примитивы (`memory_db_session`, `make_memory_engine`), что и отчёт.

---

## `db/memory.py`

### `make_memory_engine()`

Создаёт SQLAlchemy `Engine` для **`sqlite://`** с `StaticPool` (одна общая память в процессе).

**Возвращает:** `sqlalchemy.engine.Engine`

**Пример:**

```python
from prototiping.db.memory import make_memory_engine, init_schema

engine = make_memory_engine()
init_schema(engine)
# дальше — Session или raw connection по необходимости
engine.dispose()
```

---

### `make_session_factory(engine)`

Оборачивает engine в фабрику сессий (`sessionmaker`).

**Параметры:**

| Имя | Тип | Описание |
|-----|-----|----------|
| `engine` | `Engine` | Результат `make_memory_engine()` |

**Возвращает:** настроенный класс сессии (результат `sessionmaker(...)`).

**Пример:**

```python
from prototiping.db.memory import make_memory_engine, init_schema, make_session_factory

engine = make_memory_engine()
init_schema(engine)
Session = make_session_factory(engine)
db = Session()
try:
    # db.query(...)
    db.commit()
finally:
    db.close()
```

---

### `init_schema(engine)`

Создаёт все таблицы из `src.app.models.Base.metadata`.

**Параметры:**

| Имя | Тип |
|-----|-----|
| `engine` | `Engine` |

**Пример:** см. выше — всегда вызывайте после `make_memory_engine()`.

---

### `memory_db_session()`

Контекстный менеджер: новый engine, схема, одна сессия, **`commit`** при успешном выходе, **`rollback`** при исключении.

**Возвращает (yield):** `sqlalchemy.orm.Session`

**Пример (типичный для проверок):**

```python
from prototiping.db.memory import memory_db_session
from src.app.models import User

with memory_db_session() as db:
    db.add(User(full_name="Test", telegram_id=1, active=True, cars=[], cards=[], extra_ids={}))
    db.flush()
    # assert ...
# после блока данные закоммичены в эту in-memory БД; engine закрыт
```

---

### `seed_admin_permission(session)`

Создаёт permission `admin:manage`, роль `admin`, пользователя с `telegram_id=100001` и привязкой к роли.

**Параметры:**

| Имя | Тип |
|-----|-----|
| `session` | `Session` |

**Возвращает:** `tuple[User, Role, Permission]` после `flush`.

**Пример:**

```python
from prototiping.db.memory import memory_db_session, seed_admin_permission
from src.app.permissions import user_has_permission

with memory_db_session() as db:
    user, role, perm = seed_admin_permission(db)
    assert user_has_permission(db, user.telegram_id, "admin:manage")
```

---

## `db/evolution.py`

### `_counts(session)` *(внутренняя)*

Считает строки в таблицах `Permission`, `Role`, `User`, `Car`, `FuelCard`, `FuelOperation`, `LinkToken`.

**Возвращает:** `dict[str, int]` — имя таблицы → число строк.

Используется только внутри `build_db_evolution_markdown`.

---

### `build_db_evolution_markdown()`

Собирает Markdown: пошаговое наполнение демо-БД и таблица счётчиков + JSON по шагам.

**Параметры:** нет.

**Возвращает:** `str` — фрагмент для плейсхолдера `{{DB_EVOLUTION}}` в шаблоне отчёта.

**Пример (ручной вызов):**

```python
from prototiping.db.evolution import build_db_evolution_markdown

md = build_db_evolution_markdown()
print(md[:500])
```

Обычно вызывается из `prototiping.reporting.build.render_report()`, а не из прикладного кода.

---

## `db/snapshot.py`

### `_json_safe(value)` *(внутренняя)*

Приводит значение к JSON-совместимому виду (`datetime` → ISO-строка, прочее → `str`).

---

### `_row_dict(obj)` *(внутренняя)*

Словарь по колонкам ORM-объекта для превью в отчёте.

---

### `seed_demo_database(session)`

Заполняет БД демо-пользователем, авто, картой, двумя операциями (API + OCR), токеном; делает **`commit`**.

**Параметры:**

| Имя | Тип |
|-----|-----|
| `session` | `Session` |

**Пример:**

```python
from prototiping.db.memory import make_memory_engine, init_schema, make_session_factory
from prototiping.db.snapshot import seed_demo_database

engine = make_memory_engine()
init_schema(engine)
Session = make_session_factory(engine)
s = Session()
seed_demo_database(s)
s.close()
engine.dispose()
```

---

### `build_db_snapshot_section_markdown()`

Строит Markdown с превью строк по таблицам после `seed_demo_database`.

**Возвращает:** `str` для `{{DB_SNAPSHOT}}`.

**Пример:**

```python
from prototiping.db.snapshot import build_db_snapshot_section_markdown

print(build_db_snapshot_section_markdown()[:800])
```

---

← [Оглавление](../README.md)
