"""Публичный API сборки отчёта: ``render_report``, ``write_report``.

Пример::

    from pathlib import Path
    from prototiping.reporting import write_report

    write_report(verbose=True)
    write_report(Path("custom.md"), verbose=False)
"""
from prototiping.reporting.build import render_report, write_report

__all__ = ["render_report", "write_report"]
