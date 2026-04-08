# BOT_SRC / OCR_INTERNALS

Краткий модульный указатель для OCR. Детальный технический материал вынесен в отдельный раздел документации: [`docs/OCR`](../../OCR/README.md), чтобы не дублировать контент между доменами.

## OCR в контексте BOT_SRC

- движок: `src/ocr/engine.py` (`SmartFuelOCR`);
- схема данных: `src/ocr/schemas.py` (`ReceiptData`);
- вызов из bot runtime: `src/app/bot/handlers/user.py`;
- downstream запись: `src/app/models.py:FuelOperation`;
- downstream экспорт: `src/app/excel_export.py`.

## Ключевые env для OCR

- `OPENROUTER_API_KEY`
- `TESSERACT_CMD`
- `OCR_PIPELINE_TIMEOUT_SEC` (используется в user-handler runtime)

## Навигация по новому OCR-домену

- Pipeline и функции: [OCR/PIPELINE](../../OCR/PIPELINE.md)
- Контракты данных: [OCR/DATA_CONTRACTS](../../OCR/DATA_CONTRACTS.md)
- Интеграция с ботом/Excel/prototiping: [OCR/INTEGRATION](../../OCR/INTEGRATION.md)
- Дедуп и валидация: [OCR/DEDUP_AND_VALIDATION](../../OCR/DEDUP_AND_VALIDATION.md)
- Troubleshooting: [OCR/TROUBLESHOOTING](../../OCR/TROUBLESHOOTING.md)

## Связанные документы

- [OCR_MODULE](../OCR_MODULE.md)
- [SERVICES_AND_CONFIG](SERVICES_AND_CONFIG.md)
