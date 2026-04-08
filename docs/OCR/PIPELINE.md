# OCR / PIPELINE

Пошаговый разбор `SmartFuelOCR.run_pipeline` из `src/ocr/engine.py`.

## Сигнатура и контракт

```python
def run_pipeline(self, image_path: str, telegram_user_id: int = None):
    ...
```

Возвращает:

- `dict` с распознанными полями + `id` при успехе;
- `{"status":"duplicate","message":"..."}` при дубле;
- `None` при критической ошибке OCR/LLM/БД.

## Этап 1: подготовка контекста

```python
img_hash = self._get_image_hash(image_path)
```

`_get_image_hash` вычисляет md5 файла; это первый уровень дедупа.

## Этап 2: загрузка и предобработка изображения

```python
img = self.load_and_convert_image(image_path)
processed_img = self.preprocess(img)
```

Внутри `preprocess`:

- resize до контрольной ширины;
- `cvtColor` в grayscale;
- `CLAHE`;
- `GaussianBlur + addWeighted` (шарпинг);
- `bilateralFilter`;
- `threshold(..., OTSU)`.

## Этап 3: Tesseract OCR

```python
raw_text = self.extract_raw_text(processed_img)
```

Конфиг:

```python
config = "--psm 6 -l rus+eng"
```

## Этап 4: LLM-структурирование

```python
structured_data = self.structure_with_llm(raw_text)
```

Используется:

- `ChatPromptTemplate`
- `ChatOpenAI` (OpenRouter)
- `PydanticOutputParser(ReceiptData)`

## Этап 5: дедупликация

```python
is_dup, reason = self._check_duplicates(img_hash, structured_data)
if is_dup:
    return {"status": "duplicate", "message": reason}
```

Алгоритм дедупа:

1. поиск по `ocr_data['image_hash']`;
2. поиск по бизнес-ключу `doc_number + date_time + quantity`.

## Этап 6: сохранение в БД

```python
full_ocr_json = structured_data.model_dump()
full_ocr_json["image_hash"] = img_hash
full_ocr_json["raw_text_debug"] = raw_text

new_op = FuelOperation(
    source="personal_receipt",
    ocr_data=full_ocr_json,
    doc_number=structured_data.doc_number,
    date_time=datetime.strptime(
        f"{structured_data.date} {structured_data.time}",
        "%d.%m.%Y %H:%M:%S",
    ),
    status="new",
    imported_at=datetime.now(timezone.utc),
)
self.db.add(new_op)
self.db.flush()
self.db.commit()
full_ocr_json["id"] = new_op.id
return full_ocr_json
```

Почему `flush()`:

- получить `id` до `commit`, чтобы сразу вернуть его в результате.

## Исключения и fallback-поведение

### Ошибка до дедупа (decode/ocr/llm)

```python
except Exception as e:
    self.logger.error(f"Критическая ошибка OCR: {e}")
    return None
```

### Ошибка записи в БД

```python
except Exception as e:
    self.db.rollback()
    self.logger.error(f"Ошибка сохранения в БД: {e}")
    return None
```

## Интеграционный вызов из бота

```python
ocr_result = await asyncio.wait_for(
    asyncio.to_thread(processor.run_pipeline, file_path, telegram_user_id=message.from_user.id),
    timeout=OCR_PIPELINE_TIMEOUT_SEC,
)
```

Это выполняется в `src/app/bot/handlers/user.py`.

## Мини последовательность "успех"

1. Фото скачано во временный файл.
2. `run_pipeline` вернул `dict` с `id`.
3. FSM сохраняет `op_id`.
4. Пользователь подтверждает/исправляет.
5. После confirm запись идет в Excel.

## Мини последовательность "ошибка"

1. `run_pipeline -> None`.
2. Бот создает черновик `_create_manual_draft_op`.
3. Пользователь переводится в manual path.
4. Операция может быть завершена без авто-OCR.

## Подробный walkthrough по функциям класса

### `__init__(db_session, model_name=...)`

Что инициализирует:

- ссылку на SQLAlchemy session (`self.db`);
- логирование в файл и консоль;
- LLM-клиент (`ChatOpenAI`) c `base_url` OpenRouter;
- parser `PydanticOutputParser(ReceiptData)`;
- путь к `tesseract` из env или PATH.

Практический код:

```python
self.llm = ChatOpenAI(
    model=model_name,
    api_key=os.environ["OPENROUTER_API_KEY"],
    base_url="https://openrouter.ai/api/v1",
    temperature=0,
)
```

### `setup_logging()`

Цель:

- единый логгер `SmartFuelOCR`;
- сообщения и в `ocr_processing.log`, и в stderr/stdout.

Полезно при прод-debug:

- видеть ошибки OCR без доступа к БД;
- быстро коррелировать с bot-log по времени.

### `load_and_convert_image(image_path)`

Реализация:

```python
pil_img = Image.open(path).convert("RGB")
open_cv_image = np.array(pil_img)
open_cv_image = open_cv_image[:, :, ::-1].copy()
```

Почему важно:

- весь downstream в OpenCV/BGR;
- корректно обрабатываются HEIF/HEIC через `pillow_heif.register_heif_opener()`.

### `extract_raw_text(processed_img)`

```python
config = "--psm 6 -l rus+eng"
text = pytesseract.image_to_string(processed_img, config=config)
```

`--psm 6` подходит для блоков текста в чеках; для других макетов может понадобиться tuning.

## Разделение ошибок по этапам

### Этап decode/preprocess

Типовые исключения:

- битый файл;
- неподдерживаемый формат;
- ошибки cv2/pillow.

Симптом:

- `Критическая ошибка OCR` до log-линии "Текст извлечен...".

### Этап tesseract

Типовые причины:

- неверный `TESSERACT_CMD`;
- tesseract не в PATH;
- проблемы с языковыми пакетами.

Симптом:

- пустой/мусорный `raw_text_debug`;
- ошибки процесса tesseract в логе.

### Этап LLM

Типовые причины:

- отсутствует `OPENROUTER_API_KEY`;
- сетевые ошибки;
- ответ не соответствует `ReceiptData`.

Симптом:

- исключение из `chain.invoke`;
- `structured_data` некорректен.

### Этап save

Типовые причины:

- invalid `date/time` после парса;
- ошибка транзакции БД;
- конфликты/блокировки.

Симптом:

- rollback в логе;
- `run_pipeline -> None`.

## Таблица вход/выход по этапам

| Этап | Вход | Выход | Где смотреть |
|---|---|---|---|
| load | `image_path` | `np.ndarray` BGR | `load_and_convert_image` |
| preprocess | BGR image | бинаризованное изображение | `preprocess` |
| OCR | processed image | `raw_text` string | `extract_raw_text` |
| LLM parse | `raw_text` | `ReceiptData` | `structure_with_llm` |
| dedup | hash + receipt | bool + reason | `_check_duplicates` |
| save | receipt model | `FuelOperation.id` | `run_pipeline` |

## Что можно улучшать без изменения контракта

1. Тюнинг `preprocess` параметров.
2. Тюнинг tesseract `psm` и языков.
3. Prompt improvements в `structure_with_llm`.
4. Доп. логирование latency по этапам.

## Что ломает совместимость

1. Изменение формата `date/time` без синхронизации parser/save.
2. Удаление `raw_text_debug`.
3. Изменение структуры `ocr_data`, которую читает export.
4. Изменение результата duplicate-ветки.

## Пример расширенного логирования этапов

```python
t0 = time.perf_counter()
img = self.load_and_convert_image(image_path)
t1 = time.perf_counter()
processed_img = self.preprocess(img)
t2 = time.perf_counter()
raw_text = self.extract_raw_text(processed_img)
t3 = time.perf_counter()
structured_data = self.structure_with_llm(raw_text)
t4 = time.perf_counter()
self.logger.info(
    "latency load=%.3f preprocess=%.3f ocr=%.3f llm=%.3f",
    t1 - t0, t2 - t1, t3 - t2, t4 - t3
)
```

## Проверка pipeline локально (пошагово)

```python
from src.app.db import get_db_session
from src.ocr.engine import SmartFuelOCR

with get_db_session() as db:
    ocr = SmartFuelOCR(db)
    img = ocr.load_and_convert_image("temp_ocr/sample.jpg")
    proc = ocr.preprocess(img)
    txt = ocr.extract_raw_text(proc)
    parsed = ocr.structure_with_llm(txt)
    print(parsed.model_dump())
```

## Ручной контроль качества OCR

Перед выкладкой изменений:

1. 3 хороших чека (ожидаем success).
2. 2 шумных/смазанных чека (ожидаем fallback/manual или частичные данные).
3. 1 duplicate файл (ожидаем duplicate).
4. 1 тот же чек другим файлом (ожидаем duplicate_biz).

## Связь с downstream-процессами

После `run_pipeline`:

- bot-handler строит preview карточку;
- user подтверждает/правит;
- операция получает финальный статус;
- запись уходит в excel-export;
- web может читать эту же операцию через API.

## Мини anti-patterns

1. Делать тяжелый CPU OCR прямо в event loop без `to_thread`.
2. Коммитить в БД без try/except rollback.
3. Не сохранять `raw_text_debug`.
4. Изменять контракт `ReceiptData` без обновления manual path.
