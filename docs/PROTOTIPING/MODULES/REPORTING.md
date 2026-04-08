# PROTOTIPING / REPORTING

## Файлы

- `prototiping/reporting/build.py`
- `prototiping/reporting/template.md`
- `prototiping/reporting/diagram.py`
- `prototiping/reporting/ocr.py`
- `prototiping/tools/graph_preview.py`

## Выходные артефакты

- `prototiping/REPORT.md`
- `prototiping/output/graph_preview.html`

## Модель отчета

- summary counts: total / correct / incorrect
- confusion matrix: `TP/FN/TN/FP`
- scenario table: `Класс (P/N)` + `Факт (+/-)` + `is_correct`

## Примеры реализации

```python
# prototiping/reporting/build.py
rows = collect_results_from_trace(trace_full)
cm = compute_confusion(rows)
out = out.replace("{{CONFUSION_MATRIX}}", build_confusion_matrix_md(cm))
```

```python
# prototiping/reporting/ocr.py
timeout_sec = _ocr_timeout_sec()
fail_fast = _ocr_fail_fast()
...
result = ocr.run_pipeline(str(src))
```

## Поведение OCR

Поддерживаемые env:

- `PROTOTIPE_OCR_MAX_FILES`
- `PROTOTIPE_OCR_TIMEOUT_SEC`
- `PROTOTIPE_OCR_FAIL_FAST`

При `run_pipeline -> None` в отчет добавляется релевантный фрагмент `ocr_processing.log`.

## Связанные документы

- [graph producer](GRAPH.md)
- [template reference](../REPORT_TEMPLATE.md)
- [html preview details](../GRAPH_PREVIEW_HTML.md)
- [paths/env internals](LIB.md)
