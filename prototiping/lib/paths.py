"""Корневые пути пакета prototiping (единая точка для путей к файлам)."""
from __future__ import annotations

from pathlib import Path

# prototiping/
PROTO_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = PROTO_DIR.parent

EXPORT_DIR = PROTO_DIR / "export"
ROOT_EXPORTS_DIR = ROOT_DIR / "exports"
REPORT_ASSETS = PROTO_DIR / "report_assets"
OUTPUT_DIR = PROTO_DIR / "output"

REPORT_MD = PROTO_DIR / "REPORT.md"
TRACE_JSON = PROTO_DIR / ".last_prototype_trace.json"
REPORT_TEMPLATE = PROTO_DIR / "reporting" / "template.md"
