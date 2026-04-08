"""
OCR для отчёта: изображения из export/ и exports/; копии в report_assets/.

Обработка — **только** через публичный API приложения: ``SmartFuelOCR.run_pipeline()``
(тот же путь, что и в боте: препроцессинг, Tesseract, LLM, дубликаты, сохранение в БД сессии).
"""
from __future__ import annotations

import hashlib
import json
from contextlib import nullcontext
from pathlib import Path
import os
import re
import shutil
import sys
import traceback
import signal

from prototiping.lib.paths import EXPORT_DIR, REPORT_ASSETS, ROOT_DIR, ROOT_EXPORTS_DIR

IMAGE_GLOBS = ("*.jpg", "*.jpeg", "*.png", "*.webp", "*.heic", "*.HEIC", "*.JPG", "*.PNG")


def _exc_block(title: str, message: str, exc: BaseException | None = None) -> str:
    """Markdown-блок с заголовком ошибки и опционально трассировкой исключения.

    :param title: Заголовок (кратко, без ``####`` — он добавляется).
    :type title: str
    :param message: Текст для списка «Сообщение».
    :type message: str
    :param exc: Если задано — добавляется тип и блок `` ```text`` с traceback.
    :type exc: BaseException | None

    :returns: Фрагмент Markdown (с завершающими переносами).
    :rtype: str

    Пример::

        >>> b = _exc_block("Ошибка", "тест", None)
        >>> "Ошибка" in b and "тест" in b
        True
    """
    lines = [
        f"#### ❌ {title}",
        "",
        f"- **Сообщение:** {message}",
    ]
    if exc is not None:
        lines.append(f"- **Тип исключения:** `{type(exc).__name__}`")
        lines.append("")
        lines.append("```text")
        lines.append("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)).rstrip())
        lines.append("```")
    lines.append("")
    return "\n".join(lines)


def _gather_images() -> list[Path]:
    """Собирает пути к изображениям из ``prototiping/export/`` и корневого ``exports/`` без дубликатов.

    :returns: Отсортированный по имени список ``pathlib.Path`` (существующие файлы).
    :rtype: list[pathlib.Path]

    Пример::

        >>> paths = _gather_images()
        >>> isinstance(paths, list)
        True
    """
    ordered = [EXPORT_DIR, ROOT_EXPORTS_DIR]
    seen_resolved: set[str] = set()
    out: list[Path] = []
    for folder in ordered:
        if not folder.is_dir():
            continue
        batch = []
        for pattern in IMAGE_GLOBS:
            batch.extend(folder.glob(pattern))
        for p in sorted(set(batch), key=lambda x: x.name.lower()):
            try:
                key = str(p.resolve())
            except OSError:
                key = str(p)
            if key in seen_resolved:
                continue
            seen_resolved.add(key)
            out.append(p)
    return out


def _apply_tesseract_path() -> str | None:
    """Выставляет ``pytesseract.pytesseract.tesseract_cmd`` из env или ``shutil.which``.

    :returns: Путь к бинарнику ``tesseract`` или ``None``, если не найден.
    :rtype: str | None

    Пример::

        >>> cmd = _apply_tesseract_path()
        >>> cmd is None or isinstance(cmd, str)
        True
    """
    import shutil

    import pytesseract

    cmd = os.environ.get("TESSERACT_CMD") or shutil.which("tesseract")
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd
    return cmd


def _source_tag(src: Path) -> str:
    """Метка каталога-источника для читаемого имени в ``report_assets/``."""
    try:
        sr = src.resolve()
        er = EXPORT_DIR.resolve()
        rr = ROOT_EXPORTS_DIR.resolve()
    except OSError:
        return "other"
    try:
        sr.relative_to(er)
        return "export"
    except ValueError:
        pass
    try:
        sr.relative_to(rr)
        return "exports"
    except ValueError:
        pass
    return "other"


def _report_asset_filename(idx: int, src: Path) -> str:
    """Имя копии в ``report_assets/``: номер, источник, стем, короткий хеш пути (уникальность).

    Формат: ``01_export_ИмяФайла_a1b2c3.png`` — сразу видно порядок, откуда файл взят,
    и не путаются одноимённые файлы из разных папок.

    Пример::

        >>> from pathlib import Path
        >>> p = Path("receipt 1.jpg")
        >>> out = _report_asset_filename(1, p)
        >>> out.startswith("01_other_receipt_1_") and out.endswith(".jpg")
        True
    """
    tag = _source_tag(src)
    try:
        path_key = str(src.resolve())
    except OSError:
        path_key = str(src)
    short_h = hashlib.md5(path_key.encode("utf-8", errors="replace")).hexdigest()[:6]
    stem = re.sub(r"[^a-zA-Z0-9._-]+", "_", src.stem)
    if len(stem) > 48:
        stem = stem[:48]
    ext = src.suffix.lower()
    if not ext:
        ext = ".bin"
    return f"{idx:02d}_{tag}_{stem}_{short_h}{ext}"


def _truncate(s: str, max_len: int = 6000) -> str:
    """Обрезка длинного текста с пометкой для отчёта.

    :param s: Входная строка (пробелы по краям срезаются).
    :type s: str
    :param max_len: Максимальная длина результата.
    :type max_len: int

    :returns: Исходная строка или укороченная с суффиксом «обрезано».
    :rtype: str

    Пример::

        >>> len(_truncate("x" * 5000, max_len=80)) < 120
        True
    """
    s = s.strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 20] + "\n… [обрезано для отчёта]"


def _ocr_max_files() -> int | None:
    """Опционально ограничить число файлов в отчёте: ``PROTOTIPE_OCR_MAX_FILES``."""
    raw = os.environ.get("PROTOTIPE_OCR_MAX_FILES", "").strip()
    if not raw:
        return None


def _ocr_timeout_sec() -> int | None:
    """Таймаут одного файла OCR: ``PROTOTIPE_OCR_TIMEOUT_SEC``."""
    raw = os.environ.get("PROTOTIPE_OCR_TIMEOUT_SEC", "").strip()
    if not raw:
        return None
    try:
        n = int(raw)
        return n if n > 0 else None
    except ValueError:
        return None


def _ocr_fail_fast() -> bool:
    """Остановить OCR-секцию на первом критическом фейле.

    Управляется env ``PROTOTIPE_OCR_FAIL_FAST`` (1/true/yes/on).
    """
    raw = os.environ.get("PROTOTIPE_OCR_FAIL_FAST", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}
    try:
        n = int(raw)
        return n if n > 0 else None
    except ValueError:
        return None


def _extract_ocr_log_context(src: Path, max_lines: int = 14) -> str:
    """Возвращает релевантный кусок ``ocr_processing.log`` по конкретному файлу."""
    log_path = ROOT_DIR / "ocr_processing.log"
    if not log_path.is_file():
        return ""
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    if not lines:
        return ""
    src_name = src.name
    start_idx = -1
    for i, line in enumerate(lines):
        if "Начало обработки:" in line and (src_name in line or str(src) in line):
            start_idx = i
    if start_idx == -1:
        interesting = [ln for ln in lines if "ERROR - Критическая ошибка OCR" in ln or "WARNING -" in ln]
        if not interesting:
            return ""
        return "\n".join(interesting[-max_lines:])
    end_idx = len(lines)
    for j in range(start_idx + 1, len(lines)):
        if "Начало обработки:" in lines[j]:
            end_idx = j
            break
    chunk = lines[start_idx:end_idx]
    if len(chunk) > max_lines:
        chunk = chunk[-max_lines:]
    return "\n".join(chunk)


def _format_pipeline_result_md(result: dict | None, *, src: Path) -> str:
    """Markdown по возвращаемому значению ``run_pipeline``."""
    if result is None:
        log_ctx = _extract_ocr_log_context(src)
        extra = ""
        if log_ctx:
            extra = (
                "\n**Фрагмент `ocr_processing.log` для этого файла:**\n\n"
                f"```text\n{_truncate(log_ctx, max_len=3000)}\n```\n\n"
            )
        return (
            "#### Результат `run_pipeline`\n\n"
            "Вернулось **`None`** (ошибка на одном из шагов или сохранения в БД). "
            "Ниже приложен релевантный фрагмент `ocr_processing.log`.\n\n"
            f"{extra}"
        )
    if result.get("status") == "duplicate":
        return (
            "#### Результат `run_pipeline`: дубликат\n\n"
            f"- **Сообщение:** {result.get('message', '')}\n\n"
            f"```json\n{json.dumps(result, ensure_ascii=False, indent=2)}\n```\n\n"
        )
    raw_dbg = result.get("raw_text_debug")
    parts = ["#### Результат `run_pipeline`: успех\n\n"]
    if isinstance(raw_dbg, str) and raw_dbg.strip():
        parts.append("**Сырой текст (Tesseract), из ответа пайплайна:**\n\n```text\n")
        parts.append(_truncate(raw_dbg))
        parts.append("\n```\n\n")
    parts.append("**JSON (как вернул пайплайн, включая поля чека):**\n\n```json\n")
    parts.append(json.dumps(result, ensure_ascii=False, indent=2))
    parts.append("\n```\n\n")
    return "".join(parts)


def build_ocr_section_markdown(*, console: object | None = None, use_spinner: bool | None = None) -> str:
    """Секция отчёта по OCR: копии в ``report_assets/`` и вызов ``SmartFuelOCR.run_pipeline``.

    Использует те же env, что и приложение: ``OPENROUTER_API_KEY``, ``TESSERACT_CMD``,
    ``OCR_MODEL_NAME``. БД — in-memory сессия prototiping (как и раньше).

    :param console: Rich ``Console`` или ``None`` — прогресс по файлам.
    :param use_spinner: Ожидание на stderr. ``None`` → только при TTY stderr.

    :returns: Markdown для ``{{OCR_SAMPLES}}``.
    :rtype: str

    Пример::

        >>> md = build_ocr_section_markdown()  # doctest: +ELLIPSIS
        >>> isinstance(md, str) and ("OCR" in md or "изображен" in md or "OpenRouter" in md or "Tesseract" in md)
        True
    """
    if use_spinner is None:
        use_spinner = sys.stderr.isatty()

    REPORT_ASSETS.mkdir(parents=True, exist_ok=True)
    for p in REPORT_ASSETS.glob("[0-9][0-9]_*"):
        try:
            p.unlink()
        except OSError:
            pass

    images = _gather_images()
    total_image_count = len(images)
    max_files = _ocr_max_files()
    if max_files is not None:
        images = images[:max_files]

    if not images:
        checked = f"`{EXPORT_DIR}` и `{ROOT_EXPORTS_DIR}`"
        return _exc_block(
            "Проверка OCR: изображения не найдены",
            f"В каталогах {checked} нет файлов с расширениями jpg, jpeg, png, webp, heic. "
            "Положите снимки чека в один из этих путей и пересоберите отчёт.",
        )

    if not os.environ.get("OPENROUTER_API_KEY"):
        names = "\n".join(f"  - `{p}` (источник: `{p.parent.name}/`)" for p in images)
        return _exc_block(
            "Проверка OCR: нет ключа OpenRouter",
            "Без `OPENROUTER_API_KEY` в `prototiping/.env` класс `SmartFuelOCR` не инициализируется "
            "(как в основном приложении).\n\nНайденные файлы:\n" + names,
        )

    tess = _apply_tesseract_path()
    lines: list[str] = []
    file_note = ""
    if max_files is not None and total_image_count > len(images):
        file_note = f" (в каталогах найдено **{total_image_count}**, лимит `PROTOTIPE_OCR_MAX_FILES={max_files}`)"
    lines.append(
        f"*Источники:* `prototiping/export/`, `exports/` — в отчёте файлов: **{len(images)}**{file_note}\n"
    )
    lines.append(
        "*Обработка:* публичный метод приложения **`SmartFuelOCR.run_pipeline(path)`** "
        "(Tesseract → LLM → проверка дубликатов → запись в БД текущей сессии prototiping).\n"
    )
    if tess:
        lines.append(f"*Tesseract:* `{tess}`\n")
    else:
        lines.append(
            _exc_block(
                "Tesseract не найден",
                "Исполняемый файл `tesseract` отсутствует в PATH. "
                "Укажите полный путь в переменной `TESSERACT_CMD` в `prototiping/.env`.",
            )
        )

    model = os.environ.get("OCR_MODEL_NAME", "nvidia/nemotron-3-super-120b-a12b:free")
    timeout_sec = _ocr_timeout_sec()
    fail_fast = _ocr_fail_fast()
    lines.append(f"*Модель LLM (OpenRouter):* `{model}`\n")
    if timeout_sec:
        lines.append(f"*Таймаут OCR на файл:* `{timeout_sec}s`\n")
    if fail_fast:
        lines.append("*Режим OCR:* `fail-fast` (остановка на первой критической ошибке)\n")

    from sqlalchemy.orm import sessionmaker

    from prototiping.db.memory import init_schema, make_memory_engine
    from src.ocr.engine import SmartFuelOCR

    engine = make_memory_engine()
    init_schema(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()

    try:
        try:
            ocr = SmartFuelOCR(session, model_name=model)
        except Exception as e:
            lines.append(
                _exc_block(
                    "Инициализация SmartFuelOCR не удалась",
                    str(e) or "(пустое сообщение)",
                    e,
                )
            )
            return "\n".join(lines)

        import pytesseract
        import shutil as _shutil

        tess_resolved = os.environ.get("TESSERACT_CMD") or _shutil.which("tesseract")
        if tess_resolved:
            pytesseract.pytesseract.tesseract_cmd = tess_resolved
        elif os.name != "nt":
            pytesseract.pytesseract.tesseract_cmd = "tesseract"

        for idx, src in enumerate(images, start=1):
            dest_name = _report_asset_filename(idx, src)
            dest = REPORT_ASSETS / dest_name
            tag = _source_tag(src)
            if console is not None:
                try:
                    console.print(
                        f"  [bold magenta]▶ OCR[/] [{idx}/{len(images)}] "
                        f"[cyan]{tag}[/] — [bold]`{src.name}`[/] → [dim]`{dest_name}`[/]"
                    )
                except Exception:
                    pass
            elif sys.stderr.isatty():
                print(
                    f"  ▶ OCR [{idx}/{len(images)}] {tag}: {src.name} → {dest_name}",
                    file=sys.stderr,
                    flush=True,
                )

            try:
                shutil.copy2(src, dest)
            except OSError as e:
                lines.append(
                    _exc_block(
                        f"Файл «{src.name}»: копирование в report_assets",
                        str(e),
                        e,
                    )
                )
                continue

            rel_img = f"report_assets/{dest_name}"
            lines.append(
                f"### {idx}. `{src.name}`\n\n"
                f"*Источник:* `{tag}` (`{src.parent}/`)  \n"
                f"*Файл в отчёте:* `{dest_name}` (копия в `report_assets/`)  \n"
                f"*Полный путь (вход в пайплайн):* `{src}`\n\n"
                f"![{src.name} — {dest_name}]({rel_img})\n\n"
            )

            try:
                from prototiping.lib.terminal_spinner import TerminalSpinner

                spin_msg = f"SmartFuelOCR.run_pipeline: {src.name}"
                ctx = TerminalSpinner(spin_msg) if use_spinner else nullcontext()
                if timeout_sec and hasattr(signal, "SIGALRM"):
                    class _OcrTimeout(Exception):
                        pass

                    def _alarm_handler(_signum, _frame):
                        raise _OcrTimeout(f"OCR timeout after {timeout_sec}s")

                    prev = signal.getsignal(signal.SIGALRM)
                    signal.signal(signal.SIGALRM, _alarm_handler)
                    signal.alarm(timeout_sec)
                    try:
                        with ctx:
                            result = ocr.run_pipeline(str(src))
                    finally:
                        signal.alarm(0)
                        signal.signal(signal.SIGALRM, prev)
                else:
                    with ctx:
                        result = ocr.run_pipeline(str(src))
            except Exception as e:
                lines.append(
                    _exc_block(
                        f"Файл «{src.name}»: исключение при run_pipeline",
                        str(e) or "(пустое сообщение)",
                        e,
                    )
                )
                if fail_fast:
                    lines.append(
                        "> OCR-секция остановлена из-за `PROTOTIPE_OCR_FAIL_FAST` после первой критической ошибки.\n"
                    )
                    break
                continue

            lines.append(_format_pipeline_result_md(result, src=src))
            if result is None and fail_fast:
                lines.append(
                    "> OCR-секция остановлена из-за `PROTOTIPE_OCR_FAIL_FAST` после первого `run_pipeline -> None`.\n"
                )
                break
    finally:
        session.close()
        engine.dispose()

    return "\n".join(lines)
