"""Точка входа: PYTHONPATH=. python -m prototiping → сборка REPORT.md (Rich: этапы в консоли)."""
from __future__ import annotations

from prototiping.reporting.build import write_report

if __name__ == "__main__":
    write_report(verbose=True)
