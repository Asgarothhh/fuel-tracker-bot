"""Корневые пути пакета prototiping (единая точка для путей к файлам).

Все константы — ``pathlib.Path``:

- ``PROTO_DIR`` — каталог ``prototiping/``
- ``ROOT_DIR`` — корень репозитория
- ``EXPORT_DIR``, ``ROOT_EXPORTS_DIR`` — входы для OCR-отчёта
- ``REPORT_ASSETS``, ``OUTPUT_DIR`` — артефакты отчёта и HTML
- ``REPORT_MD``, ``TRACE_JSON``, ``REPORT_TEMPLATE``, ``GRAPH_PREVIEW_HTML`` — отчёт, трассировка, HTML-граф
"""
from __future__ import annotations

from pathlib import Path

PROTO_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = PROTO_DIR.parent

EXPORT_DIR = PROTO_DIR / "export"
ROOT_EXPORTS_DIR = ROOT_DIR / "exports"
REPORT_ASSETS = PROTO_DIR / "report_assets"
OUTPUT_DIR = PROTO_DIR / "output"

REPORT_MD = PROTO_DIR / "REPORT.md"
TRACE_JSON = PROTO_DIR / ".last_prototype_trace.json"
REPORT_TEMPLATE = PROTO_DIR / "reporting" / "template.md"
GRAPH_PREVIEW_HTML = OUTPUT_DIR / "graph_preview.html"
