# OCR / TROUBLESHOOTING

Практический runbook по диагностике OCR-проблем.

## Частые симптомы и действия

### Симптом: `run_pipeline` возвращает `None`

Проверить:

1. `ocr_processing.log` на traceback/ошибку этапа.
2. `OPENROUTER_API_KEY` (доступен ли процессу).
3. `TESSERACT_CMD` / наличие tesseract в PATH.
4. доступность файла изображения.

Быстрая команда:

```bash
rg "ERROR|Критическая ошибка OCR|traceback" ocr_processing.log
```

### Симптом: постоянные duplicate

Проверить:

1. `image_hash` в новых и старых операциях;
2. `doc_number/date_time/quantity` совпадения;
3. не остались ли тестовые записи в БД.

### Симптом: бот зависает на OCR

Проверить:

1. timeout `OCR_PIPELINE_TIMEOUT_SEC`;
2. размер/формат изображений;
3. латентность LLM-вызова.

## Проверка окружения

```bash
python - <<'PY'
import os, shutil
print("OPENROUTER_API_KEY:", bool(os.getenv("OPENROUTER_API_KEY")))
print("TESSERACT_CMD env:", os.getenv("TESSERACT_CMD"))
print("tesseract in PATH:", shutil.which("tesseract"))
PY
```

## Локальный smoke вызов OCR (из кода)

```python
from src.app.db import get_db_session
from src.ocr.engine import SmartFuelOCR

with get_db_session() as db:
    ocr = SmartFuelOCR(db)
    res = ocr.run_pipeline("temp_ocr/test.jpg")
    print(res)
```

## Диагностика интеграции в bot-flow

Проверить в `user.py`:

- файл реально скачивается (`file_path` существует);
- `asyncio.to_thread` оборачивает sync OCR;
- исключения timeout и generic exception обрабатываются отдельно;
- `finally` удаляет временный файл.

## Если проблемы в отчете prototyping OCR

Проверить:

- `prototiping/reporting/ocr.py` настройки:
  - `PROTOTIPE_OCR_TIMEOUT_SEC`
  - `PROTOTIPE_OCR_FAIL_FAST`
  - `PROTOTIPE_OCR_MAX_FILES`
- наличие изображений в источниках (`exports/` paths).

## Частые корневые причины

1. Неверный формат даты/времени от LLM.
2. Неправильный tesseract бинарник.
3. Недоступный OpenRouter API ключ.
4. Блокировка/ошибка БД при записи операции.
5. Поврежденный файл изображения.

## Рекомендованные лог-поля для расширения

Если дорабатываешь OCR, полезно логировать:

- `image_path`
- `image_hash`
- длительность этапов (preprocess/tesseract/llm/save)
- размер/формат изображения
- итоговый `status` (success/duplicate/none)

## Глубокая диагностика по этапам

### Диагностика загрузки изображения

Проверить локально:

```python
from PIL import Image
img = Image.open("temp_ocr/test.jpg")
print(img.mode, img.size, img.format)
```

Если тут падает, проблема не в OCR/LLM, а в файле.

### Диагностика tesseract отдельно

```python
import pytesseract
from PIL import Image
img = Image.open("temp_ocr/test.jpg")
print(pytesseract.image_to_string(img, config="--psm 6 -l rus+eng")[:1000])
```

Если здесь пусто/мусор:

- тюнинг preprocess;
- проверка языковых пакетов tesseract;
- проверка качества фото.

### Диагностика LLM отдельно

Проверить, что prompt + parser дает валидный `ReceiptData` на известном тексте.

```python
raw_text = "..."
parsed = ocr.structure_with_llm(raw_text)
print(parsed.model_dump())
```

### Диагностика save отдельно

Проверить вручную конверсию даты/времени:

```python
from datetime import datetime
datetime.strptime("05.04.2026 14:30:00", "%d.%m.%Y %H:%M:%S")
```

Если формат другой — save этап упадет.

## Таблица "симптом -> вероятная причина -> действие"

| Симптом | Вероятная причина | Что делать |
|---|---|---|
| `None` сразу | decode/preprocess ошибка | проверить файл/формат |
| `None` после OCR | LLM parse fail | проверить API key и prompt |
| `duplicate` на новых чеках | слишком агрессивный дедуп | проверить business-key |
| timeout в боте | heavy OCR/LLM latency | поднять timeout, оптимизировать preprocess |
| запись есть, Excel нет | file lock/IO error | повторить export, проверить доступ к файлу |

## Проверка состояния БД после OCR

Мини-запросы (через SQLAlchemy shell/скрипт):

```python
op = db.query(FuelOperation).order_by(FuelOperation.id.desc()).first()
print(op.id, op.source, op.status, op.doc_number, op.date_time)
print(op.ocr_data.get("image_hash"), op.ocr_data.get("raw_text_debug", "")[:120])
```

## Проверка duplicate сценария

1. Запусти OCR на одном файле.
2. Повтори запуск на том же файле.
3. Ожидай `status=duplicate`.

Скрипт:

```python
r1 = ocr.run_pipeline("temp_ocr/test.jpg")
r2 = ocr.run_pipeline("temp_ocr/test.jpg")
print("first:", r1.get("id") if isinstance(r1, dict) else r1)
print("second:", r2)
```

## Проверка manual fallback path

1. Передай заведомо плохое/нечитабельное фото.
2. Убедись, что бот предлагает ручной ввод.
3. Введи данные по шаблону.
4. Проверь, что операция может быть подтверждена и выгружена.

## Полезные команды разработчика

```bash
# смотреть последние OCR ошибки
rg "ERROR|Критическая ошибка OCR|duplicate" ocr_processing.log

# проверить наличие ocr_data в последних операциях (пример через sqlite-cli при sqlite)
# sqlite3 app.db "select id, source, status, doc_number from fuel_operations order by id desc limit 20;"
```

## Типичные ошибки конфигурации и быстрые фиксы

### `KeyError: OPENROUTER_API_KEY`

- добавить ключ в env/.env;
- перезапустить процесс.

### `tesseract is not installed`

- установить tesseract;
- задать `TESSERACT_CMD`.

### `ValueError` на `datetime.strptime`

- проверить формат времени из LLM;
- добавить нормализацию (например, `HH:MM -> HH:MM:00`).

## Инцидентный протокол (короткий)

1. Зафиксировать входной файл и timestamp.
2. Снять фрагмент `ocr_processing.log`.
3. Проверить наличие/содержимое `FuelOperation` записи.
4. Проверить, был ли fallback manual path.
5. Завести задачу с root cause и воспроизведением.

## Что логировать при доработке

Рекомендуемые дополнительные поля:

- `telegram_user_id` (если есть),
- размер файла/разрешение,
- duration каждого этапа,
- причина duplicate,
- короткий checksum raw_text.

## Диагностический playbook "5 минут"

1. Проверить env (`OPENROUTER_API_KEY`, `TESSERACT_CMD`).
2. Прогнать локальный smoke OCR на одном файле.
3. Проверить `ocr_processing.log` на последние ERROR.
4. Проверить последнюю запись `FuelOperation`.
5. Проверить статус в bot flow (есть ли fallback/confirm).

## Команды для быстрой проверки файлов

```bash
# существует ли файл, который обрабатывает бот
ls -la temp_ocr | tail -n 20

# есть ли логи OCR
ls -la ocr_processing.log

# последние OCR ошибки
rg "ERROR|Критическая ошибка OCR|duplicate" ocr_processing.log
```

## Если ошибка только на production, а локально ок

Проверить отличия:

- версия tesseract и языковых пакетов;
- наличие HEIF/WEBP поддержки;
- сетевой доступ до OpenRouter;
- переменные окружения в сервисе/юните запуска.

## Пост-инцидент шаблон записи

```text
Incident: OCR None on valid receipts
When: 2026-xx-xx HH:MM UTC
Impact: % failed checks / affected users
Root cause: ...
Fix: ...
Preventive actions: ...
Docs updated: docs/OCR/TROUBLESHOOTING.md
```

## Чеклист "готово к закрытию бага"

- проблема воспроизводилась и больше не воспроизводится;
- есть тест/смок для кейса;
- docs обновлены;
- команда знает, как диагностировать повторно.

## Быстрые run-команды для регресса OCR

```bash
# smoke через prototyping OCR section
PYTHONPATH=. python -m prototiping

# генерация html отчета после прогона
PYTHONPATH=. python -m prototiping.tools.graph_preview
```

## Когда эскалировать проблему

Эскалируй сразу, если:

- массовый рост `run_pipeline -> None`;
- массовые ложные duplicate;
- OCR success есть, но данные системно не доходят до Excel;
- ошибка воспроизводится на чистой среде с валидным env.
