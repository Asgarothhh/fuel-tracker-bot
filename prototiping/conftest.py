"""
Pytest: загрузка окружения для каталога prototiping/ и вложенных tests/.
"""
from __future__ import annotations

import os

from prototiping.lib.env import load_prototype_env

load_prototype_env()

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("BOT_TOKEN", "000000:prototype-dummy-token")
os.environ.setdefault("TOKEN_SALT", "prototype-test-salt")
os.environ.setdefault("BEL_PASSWORD", "dummy")
os.environ.setdefault("BEL_EMITENT_ID", "1")
os.environ.setdefault("BEL_CONTRACT_ID", "1")


def pytest_addoption(parser):
    parser.addoption(
        "--no-prototype-report",
        action="store_true",
        default=False,
        help="Не перезаписывать prototiping/REPORT.md после прогона",
    )


def pytest_sessionfinish(session, exitstatus):
    if session.config.getoption("--no-prototype-report"):
        return
    try:
        from prototiping.reporting.build import write_report

        path = write_report()
        print(f"\nprototiping: отчёт записан → {path}\n")
    except Exception as e:
        import sys

        print(f"[prototiping] не удалось записать REPORT.md: {e}", file=sys.stderr)
