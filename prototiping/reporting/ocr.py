"""
OCR для отчёта: изображения из export/ и exports/; копии в report_assets/.
"""
from __future__ import annotations

import json
from pathlib import Path
import os
import re
import shutil
import traceback

from prototiping.lib.paths import EXPORT_DIR, REPORT_ASSETS, ROOT_EXPORTS_DIR

IMAGE_GLOBS = ("*.jpg", "*.jpeg", "*.png", "*.webp", "*.heic", "*.HEIC", "*.JPG", "*.PNG")


def _exc_block(title: str, message: str, exc: BaseException | None = None) -> str:
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


def _gather_images():
    ordered = [EXPORT_DIR, ROOT_EXPORTS_DIR]
    seen_resolved: set[str] = set()
    out: list = []
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
    import shutil

    import pytesseract

    cmd = os.environ.get("TESSERACT_CMD") or shutil.which("tesseract")
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd
    return cmd


def _truncate(s: str, max_len: int = 6000) -> str:
    s = s.strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 20] + "\n… [обрезано для отчёта]"


def _safe_asset_name(idx: int, original: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9._-]+", "_", Path(original).name)[:80]
    return f"{idx:02d}_{base}"


def build_ocr_section_markdown() -> str:
    REPORT_ASSETS.mkdir(parents=True, exist_ok=True)
    for p in REPORT_ASSETS.glob("[0-9][0-9]_*"):
        try:
            p.unlink()
        except OSError:
            pass

    images = _gather_images()
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
            "Без `OPENROUTER_API_KEY` в `prototiping/.env` шаг LLM не выполняется. "
            "Tesseract также не запускался для этого прогона.\n\nНайденные файлы:\n" + names,
        )

    tess = _apply_tesseract_path()
    lines: list[str] = []
    lines.append(
        f"*Источники:* `prototiping/export/`, `exports/` — обработано файлов: **{len(images)}**\n"
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
    lines.append(f"*Модель LLM (OpenRouter):* `{model}`\n")

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
            dest_name = _safe_asset_name(idx, src.name)
            dest = REPORT_ASSETS / dest_name
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
            lines.append(f"### {idx}. `{src.name}`\n\n*Путь:* `{src}`\n\n![{src.name}]({rel_img})\n")

            try:
                img = ocr.load_and_convert_image(str(src))
                processed = ocr.preprocess(img)
                raw_text = ocr.extract_raw_text(processed)
            except Exception as e:
                lines.append(
                    _exc_block(
                        f"Файл «{src.name}»: Tesseract / препроцессинг",
                        str(e) or "(пустое сообщение)",
                        e,
                    )
                )
                continue

            if not (raw_text or "").strip():
                lines.append(
                    _exc_block(
                        f"Файл «{src.name}»: пустой текст OCR",
                        "Tesseract вернул пустую строку. Проверьте качество изображения и язык (`rus+eng`).",
                    )
                )
                continue

            lines.append("**Сырой текст (Tesseract):**\n\n```text\n")
            lines.append(_truncate(raw_text))
            lines.append("\n```\n\n")

            try:
                structured = ocr.structure_with_llm(raw_text)
                data = structured.model_dump(mode="json")
                lines.append("**Структура (LLM → ReceiptData):**\n\n```json\n")
                lines.append(json.dumps(data, ensure_ascii=False, indent=2))
                lines.append("\n```\n")
            except Exception as e:
                lines.append(
                    _exc_block(
                        f"Файл «{src.name}»: LLM / парсинг в ReceiptData",
                        str(e) or "(пустое сообщение)",
                        e,
                    )
                )
    finally:
        session.close()
        engine.dispose()

    return "\n".join(lines)
