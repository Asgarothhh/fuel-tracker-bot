# OCR / DEDUP_AND_VALIDATION

Алгоритм дедупликации OCR и правила валидации данных чека.

## Дедуп-уровень 1: хэш изображения

```python
duplicate_hash = self.db.query(FuelOperation).filter(
    FuelOperation.ocr_data['image_hash'].cast(String) == img_hash
).first()
```

Назначение:

- не записывать один и тот же файл повторно.

Плюсы:

- быстрый и однозначный критерий.

Минусы:

- не ловит "тот же чек, но другой файл/скрин".

## Дедуп-уровень 2: бизнес-ключ

```python
dt_obj = datetime.strptime(f"{structured_data.date} {structured_data.time}", "%d.%m.%Y %H:%M:%S")
duplicate_biz = self.db.query(FuelOperation).filter(
    and_(
        FuelOperation.doc_number == structured_data.doc_number,
        FuelOperation.date_time == dt_obj,
        FuelOperation.ocr_data['quantity'].cast(String) == str(structured_data.quantity),
    )
).first()
```

Назначение:

- ловить логический дубликат даже при другом image hash.

## Валидация полей до записи

Критичные поля для качества:

- `doc_number`
- `date`
- `time`
- `quantity`

Если формат даты/времени невалидный:

- conversion в `datetime` упадет;
- сохранение операции не выполнится.

## Результаты дедупа в контракте `run_pipeline`

- дубль -> `{"status":"duplicate","message":"..."}`
- не дубль -> переход к сохранению.

Это позволяет боту явно разделять UX:

- duplicate warning,
- success confirm flow.

## Риски и ложные срабатывания

### Ложный duplicate по бизнес-ключу

Возможен если:

- OCR ошибся в `doc_number`, но попал в существующий;
- `quantity` округлился не так, как ожидается.

### Ложный non-duplicate

Возможен если:

- OCR распознал тот же чек по-разному (`quantity` формат, time sec).

## Рекомендации улучшения дедупа

1. Нормализовать `quantity` до согласованного string/decimal формата.
2. Добавить в бизнес-ключ `total_sum` или `azs_number` как доп. эвристики.
3. Вести метрику duplicate-hit-rate для контроля качества.

## Test cases (рекомендуемые)

1. Один и тот же файл повторно -> duplicate_hash.
2. Разные файлы одного чека -> duplicate_biz.
3. Разные чеки с близкими полями -> не duplicate.
4. Неполная дата/время -> корректный отказ/fallback.

## Подробный разбор `_check_duplicates`

### Входные параметры

- `img_hash: str`
- `structured_data: ReceiptData`

### Выход

- `(True, reason)` если дубль обнаружен;
- `(False, "")` если дубля нет.

### Порядок проверок

1. hash check;
2. business check.

Это важно:

- hash проверка быстрая;
- business проверка дороже, но ловит "тот же чек другим файлом".

## Валидация и нормализация даты/времени

```python
dt_str = f"{structured_data.date} {structured_data.time}"
dt_obj = datetime.strptime(dt_str, "%d.%m.%Y %H:%M:%S")
```

Если parse падает:

- `dt_obj = None`;
- бизнес-дедуп может потерять точность.

## Нормализация количества и риск сравнения строк

Текущее сравнение:

```python
FuelOperation.ocr_data['quantity'].cast(String) == str(structured_data.quantity)
```

Риск:

- `45` vs `45.0` vs `45,0` могут давать разные строки.

Рекомендация:

- нормализовать через decimal/фиксированный формат перед сравнением.

## Дополнительные критерии (если улучшать)

Можно включить:

- `total_sum`
- `azs_number`
- `pump_no`

Но важно не пережать и не получить false-negative duplicates.

## Валидаторы на уровне UI/manual path

Manual parser в `user.py` уже проверяет:

- обязательные поля;
- формат даты;
- формат времени;
- numeric quantity.

Это снижает риск мусорных записей до OCR-dedup стадии.

## Таблица trade-offs дедупа

| Критерий | Плюс | Минус |
|---|---|---|
| image hash | точный для файла | не ловит тот же чек в другом файле |
| doc+datetime+qty | ловит логические дубли | чувствителен к OCR ошибкам |
| расширенный ключ | меньше дублей | выше риск пропуска легитимных операций |

## Практический сценарий: duplicate hash

1. Пользователь отправил файл A.
2. OCR сохранил `image_hash`.
3. Пользователь отправил файл A снова.
4. Hash check вернул duplicate.
5. Бот показал предупреждение, без новой записи.

## Практический сценарий: duplicate biz

1. Пользователь отправил фото чека.
2. Потом отправил фото этого же чека с другого ракурса.
3. Hash отличается, но `doc+datetime+qty` совпали.
4. duplicate_biz сработал.

## Практический сценарий: false negative

1. На втором фото OCR распознал `quantity` иначе (`45` vs `45.5` из-за шума).
2. hash другой.
3. business-key не совпал.
4. Создана вторая запись.

Это кейс для улучшения алгоритма.

## Практический сценарий: false positive

1. Два разных чека с похожими `doc_number/date_time/quantity`.
2. business-key совпал.
3. Второй чек отклонен как duplicate.

Для таких кейсов нужен баланс критериев и/или ручной review path.

## Нагрузочные замечания

- hash check обычно дешевый (индексация JSON зависит от СУБД/плана);
- business check с кастами JSON может быть тяжелее при большом объеме.

Рекомендация:

- периодически оценивать query latency.

## Чеклист ревью изменения дедупа

1. Не сломана сигнатура `_check_duplicates`.
2. Не изменен формат duplicate-return контракта.
3. Пройдены 4 базовых test cases (hash, biz, non-dup, invalid time).
4. Обновлена документация и troubleshooting.

## Расширенный набор тест-кейсов

1. `doc_number` пустой, но hash совпадает -> duplicate.
2. hash разный, `doc+dt+qty` совпали -> duplicate_biz.
3. hash разный, `doc+dt` совпали, `qty` отличается сильно -> not duplicate.
4. `time` без секунд -> нормализация/валидация.
5. `quantity` как строка с запятой -> expected normalization path.
6. поврежденный чек с отсутствующим `doc_number` -> fallback decision.

## Пример unit-теста на duplicate_hash

```python
def test_duplicate_hash(db, ocr):
    # arrange existing operation with image_hash
    op = FuelOperation(source="personal_receipt", ocr_data={"image_hash": "abc"})
    db.add(op); db.commit()
    # act
    is_dup, reason = ocr._check_duplicates("abc", structured_data_mock())
    # assert
    assert is_dup is True
    assert "уже обрабатывался" in reason
```

## Пример unit-теста на duplicate_biz

```python
def test_duplicate_biz(db, ocr):
    dt = datetime.strptime("05.04.2026 14:30:00", "%d.%m.%Y %H:%M:%S")
    op = FuelOperation(
        source="personal_receipt",
        doc_number="123",
        date_time=dt,
        ocr_data={"quantity": "45.2"},
    )
    db.add(op); db.commit()
    s = structured_data(doc="123", date="05.04.2026", time="14:30:00", qty=45.2)
    is_dup, _ = ocr._check_duplicates("different_hash", s)
    assert is_dup is True
```

## Рекомендованная стратегия улучшений

1. Сначала добавить метрики duplicate-hit.
2. Потом изменить нормализацию (не меняя return contract).
3. Проверить ретроспективно выборку ложных дублей.
4. Только затем менять критерии business-key.

## Чеклист приемки дедуп-изменений

- duplicate return контракт не изменился;
- smoke-кейсы hash/biz/none проходят;
- false-positive частота не выросла;
- docs и troubleshooting обновлены;
- команда понимает rollback plan при regressions.

## Rollback план (если дедуп стал хуже)

1. Вернуть предыдущий алгоритм сравнения `quantity`.
2. Оставить сбор метрик для анализа.
3. Прогнать контрольный набор чеков.
4. Согласовать следующий шаг улучшений.

## Заключение

Текущий дедуп сочетает:

- быстрый hash-контур;
- доменный business-контур.

Это рабочий компромисс для текущего production-потока OCR, но требует регулярной калибровки на реальных данных и инцидентах.

При любых изменениях дедуп-правил обязательно:

- сохранять стабильный внешний контракт;
- обновлять документацию;
- подтверждать эффект тестами и метриками.

Дополнительно полезно вести еженедельный review:

- выборки ложных duplicate;
- выборки пропущенных duplicate;
- сравнение качества до/после изменений.
