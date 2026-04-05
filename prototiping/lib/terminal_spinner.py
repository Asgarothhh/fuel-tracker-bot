"""Спиннер в терминале (stderr): кадры dots4 и прошедшее время."""
from __future__ import annotations

import shutil
import sys
import threading
import time

DOTS4_FRAMES = (
    "⠄",
    "⠆",
    "⠇",
    "⠋",
    "⠙",
    "⠸",
    "⠰",
    "⠠",
    "⠰",
    "⠸",
    "⠙",
    "⠋",
    "⠇",
    "⠆",
)
DOTS4_INTERVAL_SEC = 80 / 1000.0


class TerminalSpinner:
    """Контекстный менеджер: анимация ожидания и таймер на одной строке (stderr)."""

    def __init__(self, message: str, *, stream=None) -> None:
        self.message = message
        self.stream = stream or sys.stderr
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._t0 = 0.0

    def _clear_line(self) -> None:
        try:
            w = shutil.get_terminal_size().columns
        except OSError:
            w = 100
        self.stream.write("\r" + " " * max(w - 1, 40) + "\r")
        self.stream.flush()

    def _run(self) -> None:
        i = 0
        while not self._stop.is_set():
            frame = DOTS4_FRAMES[i % len(DOTS4_FRAMES)]
            elapsed = time.perf_counter() - self._t0
            line = f"\r{frame} {self.message}  [{elapsed:6.1f}s]"
            self.stream.write(line)
            self.stream.flush()
            self._stop.wait(DOTS4_INTERVAL_SEC)
            i += 1

    def __enter__(self) -> TerminalSpinner:
        self._t0 = time.perf_counter()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *args: object) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._clear_line()
