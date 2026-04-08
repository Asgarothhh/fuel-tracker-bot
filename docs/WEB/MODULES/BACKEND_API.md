# WEB / BACKEND_API

## Роутеры

- `web/backend/routers/users.py` (`/api/users`)
- `web/backend/routers/operations.py` (`/api/operations`)
- `web/backend/routers/reports.py` (`/api/reports`)
- `web/backend/main.py` (`/api/health`)

## Карта endpoint'ов

```mermaid
flowchart LR
    U[/api/users] --> DB[(User)]
    O[/api/operations] --> DB[(FuelOperation)]
    R[/api/reports/excel] --> X[excel_report]
    H[/api/health] --> OK[status=ok]
```

## Endpoints: подробный справочник

### Health

| Method | Path | Body | Response | Notes |
|---|---|---|---|---|
| `GET` | `/api/health` | - | `{"status":"ok"}` | Быстрая проверка, что API-процесс жив |

### Пользователи (`/api/users`)

| Method | Path | Body | Response | Errors |
|---|---|---|---|---|
| `GET` | `/api/users` | - | `list[UserResponse]` | - |
| `GET` | `/api/users/` | - | `list[dict]` (упрощенный формат для UI) | - |
| `PUT` | `/api/users/{user_id}` | `UserEditRequest` (`full_name`, `active`, `role_id`) | `UserResponse` | `404 User not found` |
| `DELETE` | `/api/users/{user_id}` | - | `{"status":"success"}` | `404 User not found` |

Практические замечания:
- В проекте есть два GET-роута (`/api/users` и `/api/users/`) с разными форматами ответа; frontend должен использовать один стабильный контракт.
- `PUT` обновляет только `full_name`, `active`, `role_id`; поля `cars/cards/telegram_id` здесь не редактируются.

### Операции (`/api/operations`)

#### Получение списков

| Method | Path | Query/Body | Response | Errors |
|---|---|---|---|---|
| `GET` | `/api/operations/{tab_name}` | `tab_name` in `pending/disputed/api/recent` | `list[OperationResponse-like]` | `404 Unknown tab` |

Интерпретация `tab_name`:
- `pending` -> статусы `pending` и `new`
- `disputed` -> статус `disputed`
- `api` -> `source == "api"`
- `recent` -> без дополнительного фильтра (все записи)

#### Действия над операцией

| Method | Path | Body | Response | Errors |
|---|---|---|---|---|
| `POST` | `/api/operations/{op_id}/confirm` | - | `{"status":"success"}` | `404 Operation not found` |
| `POST` | `/api/operations/{op_id}/reject` | - | `{"status":"success"}` | `404 Operation not found` |
| `POST` | `/api/operations/{op_id}/reassign` | `ReassignRequest` (`new_user_id`) | `{"status":"success"}` | `404 Operation not found` |
| `DELETE` | `/api/operations/{op_id}` | - | `{"status":"success"}` | `404 Operation not found` |
| `POST` | `/api/operations/import-from-api` | - | `dict` (`ok`, `new_count`, ...) | `400` при ошибке импорта |

Семантика действий:
- `confirm` -> `status = "confirmed"`
- `reject` -> `status = "rejected"`
- `reassign` -> `presumed_user_id = new_user_id`, затем `status = "pending"` (операция возвращается в очередь проверки)

### Отчеты (`/api/reports`)

| Method | Path | Body | Response | Errors |
|---|---|---|---|---|
| `GET` | `/api/reports/excel` | - | XLSX-файл (`Content-Disposition: attachment`) | `404`, если нет операций |

Технически:
- Данные берет `build_full_fuel_report_excel(db)`.
- При успехе возвращается бинарный ответ с `media_type=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`.

## Поведенческие заметки

- unknown operation tab -> HTTP 404
- missing user/op for mutate endpoints -> HTTP 404
- excel download on empty DB -> HTTP 404
- import-from-api service error -> HTTP 400 + `detail`

Эти кейсы покрыты N-сценариями в прототипировании (`S32...S36`).

## Примеры реализации

```python
# web/backend/routers/operations.py
@router.get("/{tab_name}")
def get_operations(tab_name: str, db: Session = Depends(get_db)):
    ...
    else:
        raise HTTPException(status_code=404, detail="Unknown tab")
```

```python
# web/backend/routers/reports.py
@router.get("/excel")
def download_full_excel_report(db: Session = Depends(get_db)):
    buf, count = build_full_fuel_report_excel(db)
    if buf is None:
        raise HTTPException(status_code=404, detail="...")
```

## Связанные документы

- [web services](SERVICES.md)
- [prototiping web checks](../../PROTOTIPING/MODULES/CHECKS.md)
- [frontend calls](FRONTEND_INTEGRATION.md)
