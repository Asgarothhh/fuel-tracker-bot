"""Точка входа: ``PYTHONPATH=. python -m prototiping`` → сборка ``REPORT.md`` (Rich-этапы).

Вызывает ``write_report(verbose=True)``.
"""
from __future__ import annotations

from prototiping.reporting.build import write_report

if __name__ == "__main__":
    write_report(verbose=True)
