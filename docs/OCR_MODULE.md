# Модуль OCR (`src/ocr/`)

## Назначение

Пайплайн **SmartFuelOCR** обрабатывает изображение чека АЗС и создаёт запись `FuelOperation` с `source=personal_receipt` и заполненным `ocr_data`.

## Цепочка

1. Загрузка изображения (в т.ч. HEIC через `pillow_heif`).
2. Предобработка OpenCV (масштаб, CLAHE, бинаризация).
3. **Tesseract** (`rus+eng`, PSM 6) → сырой текст.
4. **LLM** (OpenRouter, модель из конструктора `SmartFuelOCR`) → структура `ReceiptData` (`schemas.py`).
5. Проверка дублей (хэш файла в `ocr_data`, совпадение чека+даты+источник `personal_receipt`).
6. Сохранение в БД и возврат словаря полей + поля `id` операции.

## Переменные окружения

| Переменная | Назначение |
|------------|------------|
| `OPENROUTER_API_KEY` | Ключ для LLM (обязательно для структурирования). |
| `TESSERACT_CMD` | Путь к исполняемому файлу `tesseract`, если не в `PATH` (на Linux обычно не нужен). |

Логи OCR пишутся в `ocr_processing.log` в рабочей директории процесса.

## Зависимости

См. `requirements.txt` / окружение проекта: `opencv-python`, `pytesseract`, `langchain-openai`, `pillow-heif`, и т.д.
