"""
Сбор REPORT.md из reporting/template.md и прогона графа.
При verbose=True — пошаговый вывод в консоль через Rich.
"""
from __future__ import annotations

import json
import os
import traceback
from collections.abc import Callable
from html import escape as html_escape
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from prototiping.lib.env import load_prototype_env

load_prototype_env()

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("BOT_TOKEN", "000000:prototype-dummy-token")
os.environ.setdefault("TOKEN_SALT", "prototype-test-salt")
os.environ.setdefault("BEL_PASSWORD", "dummy")
os.environ.setdefault("BEL_EMITENT_ID", "1")
os.environ.setdefault("BEL_CONTRACT_ID", "1")

from prototiping.checks.scenarios import SCENARIO_META, SCENARIO_SCHEMA_VERSION
from prototiping.lib.paths import GRAPH_PREVIEW_HTML, REPORT_MD, REPORT_TEMPLATE, TRACE_JSON


def _reset_report_file(target: Path, console: Any | None) -> None:
    started = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    stub = (
        "# Прототипирование — отчёт\n\n"
        f"> **Идёт сборка…** Старт: **{started}** (UTC). "
        "После завершения прогона файл будет полностью перезаписан.\n"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(stub, encoding="utf-8")
    if console:
        _step(console, f"Файл [bold]{target}[/] сброшен (заглушка до готового отчёта)", style="dim")


def _reset_graph_preview_stub(console: Any | None) -> None:
    """Короткая HTML-заглушка до полной страницы (как у REPORT.md)."""
    stub = """<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Граф прототипирования — сборка…</title>
</head>
<body>
  <p>Идёт сборка отчёта. Файл будет заменён полной страницей после завершения прогона.</p>
</body>
</html>
"""
    GRAPH_PREVIEW_HTML.parent.mkdir(parents=True, exist_ok=True)
    GRAPH_PREVIEW_HTML.write_text(stub, encoding="utf-8")
    if console:
        _step(
            console,
            f"Файл [bold]{GRAPH_PREVIEW_HTML}[/] сброшен (заглушка до HTML-графа)",
            style="dim",
        )


def _write_graph_preview_html(console: Any | None) -> None:
    """Пишет ``graph_preview.html`` из ``TRACE_JSON`` (обновляется в ``render_report``)."""
    try:
        from prototiping.tools.graph_preview import build_html

        if not TRACE_JSON.is_file():
            if console:
                _step(
                    console,
                    f"[yellow]![/] нет {TRACE_JSON.name} — HTML-граф не обновлён",
                    style="dim",
                )
            return
        trace = json.loads(TRACE_JSON.read_text(encoding="utf-8"))
        GRAPH_PREVIEW_HTML.write_text(build_html(trace), encoding="utf-8")
        if console:
            _step(console, f"HTML-граф: [bold]{GRAPH_PREVIEW_HTML.resolve()}[/]", style="magenta")
    except Exception as e:
        if console:
            console.print(f"  [red]✗[/] не удалось записать graph_preview.html: {e}")
        err_page = (
            "<!DOCTYPE html><html lang=\"ru\"><head><meta charset=\"utf-8\"/><title>Ошибка сборки</title></head>"
            f"<body><pre>{html_escape(str(e) + chr(10) + traceback.format_exc())}</pre></body></html>\n"
        )
        GRAPH_PREVIEW_HTML.write_text(err_page, encoding="utf-8")


def _get_console(verbose: bool) -> Any | None:
    """Возвращает Rich Console для цветного вывода или None (тихий режим / нет пакета).

    :param verbose: Если False — всегда None; если True — ``Console()`` или None при отсутствии Rich.
    :type verbose: bool

    :returns: Экземпляр ``rich.console.Console`` либо ``None``.
    :rtype: typing.Any | None

    Пример::

        >>> c = _get_console(False)
        >>> c is None
        True
    """
    if not verbose:
        return None
    try:
        from rich.console import Console

        return Console(stderr=False)
    except ImportError:
        return None


def _step(console: Any | None, msg: str, *, style: str = "cyan") -> None:
    """Печать шага сборки (Rich или обычный print).

    :param console: Объект с методом ``print`` (Rich) или ``None``.
    :type console: typing.Any | None
    :param msg: Текст этапа.
    :type msg: str
    :param style: Имя стиля Rich для префикса (игнорируется при ``console is None``).
    :type style: str

    :returns: ``None``.

    Пример::

        >>> _step(None, "тест")  # doctest: +ELLIPSIS
        ▶ тест
    """
    if console is not None:
        console.print(f"[bold {style}]▶[/] {msg}")
    else:
        print(f"▶ {msg}")


def collect_results_from_trace(trace_full: dict) -> list[dict]:
    """Собирает плоский список строк отчёта из трассировки графа (узлы × проверки).

    :param trace_full: Словарь от ``run_prototype_traced``: ключи ``graph``, ``overall_ok``,
        ``nodes``; у каждого узла — ``id``, ``checks`` со полями ``fn``, ``ok``, ``detail``.
    :type trace_full: dict

    :returns: Список словарей: поля из ``SCENARIO_META``, плюс ``graph_node``, ``check_name``,
        ``ok``, ``detail``, ``run_order`` (1…N — порядок прогона).
    :rtype: list[dict]

    :raises KeyError: Если для ``fn`` проверки нет записи в ``checks/scenarios.py``.

    Пример::

        >>> from prototiping.graph.trace import run_prototype_traced
        >>> t = run_prototype_traced(console=False, write_trace_json=False)
        >>> rows = collect_results_from_trace(t)
        >>> isinstance(rows, list) and "id" in rows[0]
        True
    """
    rows: list[dict] = []
    run_order = 0
    for node in trace_full["nodes"]:
        nid = node["id"]
        for c in node["checks"]:
            run_order += 1
            fn_name = c["fn"]
            meta = SCENARIO_META.get(fn_name)
            if not meta:
                meta = {
                    "id": f"LEGACY-{run_order:02d}",
                    "graph_node": nid,
                    "title": f"[legacy] {fn_name}",
                    "code_under_test": "— (нет метаданных, добавьте в `checks/scenarios.py`)",
                    "description": "Сценарий выполнен, но метаданные отсутствуют; отчёт собран в режиме совместимости.",
                    "kind": "standard",
                    "scenario_version": "legacy",
                }
            kind = str(meta.get("kind", "standard"))
            scenario_version = str(meta.get("scenario_version", SCENARIO_SCHEMA_VERSION))
            rows.append(
                {
                    **meta,
                    "graph_node": nid,
                    "check_name": fn_name,
                    "ok": c["ok"],
                    "detail": c["detail"],
                    "run_order": run_order,
                    "kind": kind,
                    "scenario_version": scenario_version,
                    "expected_class": "N" if kind == "breaker" else "P",
                    "actual_sign": "-" if c["ok"] is False else "+",
                    "is_correct": bool(c.get("is_correct", c["ok"])),
                    "is_legacy_version": scenario_version != SCENARIO_SCHEMA_VERSION,
                }
            )
    return rows


def compute_confusion(rows: list[dict]) -> dict[str, int]:
    """Считает TP/FN/TN/FP по типу сценария и фактическому результату.

    - standard: ожидаем ``ok=True``  -> TP/FN
    - breaker:  ожидаем ``ok=False`` -> TN/FP
    """
    tp = fn = tn = fp = 0
    for r in rows:
        kind = r.get("kind", "standard")
        ok = bool(r.get("ok"))
        if kind == "breaker":
            if ok:
                fp += 1
            else:
                tn += 1
            continue
        if ok:
            tp += 1
        else:
            fn += 1
    return {"TP": tp, "FN": fn, "TN": tn, "FP": fp}


def build_confusion_matrix_md(cm: dict[str, int]) -> str:
    """Матрица классификации P/N как в классическом 2x2 виде."""
    return "\n".join(
        [
            "| predicted \\ actual | P (+) | N (-) |",
            "|---|---:|---:|",
            f"| **P** (ожидаем PASS) | **TP = {cm['TP']}** | **FN = {cm['FN']}** |",
            f"| **N** (ожидаем FAIL) | **FP = {cm['FP']}** | **TN = {cm['TN']}** |",
        ]
    )


def _escape_md_cell(s: str) -> str:
    """Экранирование для ячеек Markdown-таблицы (pipe, переносы).

    :param s: Исходная строка.
    :type s: str

    :returns: Строка с ``|`` → ``\\|``, ``\\n`` → пробел.
    :rtype: str

    Пример::

        >>> _escape_md_cell("a|b\\nc")
        'a\\\\|b c'
    """
    return s.replace("|", "\\|").replace("\n", " ")


def build_table(rows: list[dict]) -> str:
    """Markdown-таблица сценариев для вставки в шаблон отчёта.

    :param rows: Элементы как у ``collect_results_from_trace`` (нужны ``id``, ``graph_node``,
        ``title``, ``code_under_test``, ``ok``, ``detail``).
    :type rows: list[dict]

    :returns: Одна строка с заголовком и строками таблицы, разделитель ``\\n``.
    :rtype: str

    Пример::

        >>> md = build_table([{"id": "S01", "graph_node": "n", "title": "t",
        ...     "code_under_test": "c", "ok": True, "detail": "", "run_order": 1}])
        >>> "| 1 |" in md and "| S01 |" in md and "да" in md
        True
    """
    lines = [
        "| № | Код | Класс | Факт | Тип | Версия | Узел графа | Сценарий | Проверяемый код | Корректно | При ошибке |",
        "|---|-----|-------|------|-----|--------|------------|----------|-----------------|-----------|------------|",
    ]
    for i, row in enumerate(rows, start=1):
        is_correct = bool(row.get("is_correct"))
        ok_cell = "да" if is_correct else "**нет**"
        err_hint = "—" if is_correct else _escape_md_cell((row["detail"] or "")[:120])
        code_cell = _escape_md_cell(row["code_under_test"])
        ro = row.get("run_order", i)
        lines.append(
            "| {ro} | {sid} | {cls} | {fact} | {kind} | {ver} | `{node}` | {title} | {code} | {ok} | {err} |".format(
                ro=ro,
                sid=row["id"],
                cls=row.get("expected_class", "P"),
                fact=row.get("actual_sign", "+"),
                kind="breaker" if row.get("kind") == "breaker" else "standard",
                ver=row.get("scenario_version", "legacy"),
                node=row["graph_node"],
                title=_escape_md_cell(row["title"]),
                code=code_cell,
                ok=ok_cell,
                err=err_hint,
            )
        )
    return "\n".join(lines)


def build_details(rows: list[dict]) -> str:
    """Развёрнутый Markdown по каждому сценарию (заголовки, списки, блок при ошибке).

    :param rows: Тот же формат, что для ``build_table``.
    :type rows: list[dict]

    :returns: Склеенные секции ``###`` для плейсхолдера ``{{SCENARIOS_DETAIL}}``.
    :rtype: str

    Пример::

        >>> s = build_details([{"id": "S01", "title": "T", "graph_node": "g",
        ...     "code_under_test": "x", "description": "d", "ok": True, "detail": "ok",
        ...     "check_name": "f", "run_order": 1}])
        >>> "### 1. T" in s and "S01" in s and "Корректно" in s
        True
    """
    parts: list[str] = []
    for i, row in enumerate(rows, start=1):
        is_correct = bool(row.get("is_correct"))
        status = "**Корректно**" if is_correct else "**Некорректно**"
        detail = row["detail"] or "—"
        fail_block = ""
        if not is_correct:
            fail_block = (
                "\n#### ❌ Некорректная обработка сценария\n\n"
                f"- **Текст:** `{detail}`\n"
                f"- **Функция:** `{row['check_name']}`\n\n"
            )
        ro = row.get("run_order", i)
        parts.append(
            f"### {ro}. {row['title']}\n\n"
            f"- **Код (scenarios):** `{row['id']}`\n"
            f"- **Класс (ожидаемо):** `{row.get('expected_class', 'P')}`\n"
            f"- **Факт:** `{row.get('actual_sign', '+')}`\n"
            f"- **Тип:** `{row.get('kind', 'standard')}`\n"
            f"- **Версия сценария:** `{row.get('scenario_version', 'legacy')}`\n"
            f"- **Узел графа:** `{row['graph_node']}`\n"
            f"- **Проверяемый код:** {row['code_under_test']}\n"
            f"- **Что проверяется:** {row['description']}\n"
            f"- **Результат:** {status}\n"
            f"- **Комментарий / детали:** {detail}\n"
            f"{fail_block}"
        )
    return "\n".join(parts)


def _safe_section(builder: Callable[[], str], title: str, console: Any | None) -> str:
    """Выполняет ``builder()``; при исключении возвращает Markdown с трассировкой.

    :param builder: Нуларная функция, возвращающая фрагмент Markdown.
    :type builder: collections.abc.Callable[[], str]
    :param title: Подпись раздела для лога и для блока ошибки.
    :type title: str
    :param console: Rich-консоль или ``None``.
    :type console: typing.Any | None

    :returns: Результат ``builder()`` либо готовый блок «Ошибка при сборке раздела».
    :rtype: str

    Пример::

        >>> _safe_section(lambda: "ok", "t", None)
        'ok'
    """
    import traceback

    try:
        out = builder()
        if console:
            console.print(f"  [green]✓[/] раздел «{title}»")
        return out
    except Exception as e:
        tb = traceback.format_exc()
        if console:
            console.print(f"  [red]✗[/] раздел «{title}»: {e}")
        return (
            f"#### ❌ Ошибка при сборке раздела «{title}»\n\n"
            f"- **Тип:** `{type(e).__name__}`\n"
            f"- **Сообщение:** `{e}`\n\n"
            f"```text\n{tb.rstrip()}\n```\n"
        )


def render_report(*, verbose: bool = False) -> str:
    """Полный текст ``REPORT.md``: прогон графа, подстановка всех плейсхолдеров шаблона.

    :param verbose: Лог в консоль (Rich) и дерево проверок в ``run_prototype_traced``.
    :type verbose: bool

    :returns: Содержимое файла отчёта до записи на диск.
    :rtype: str

    Пример (при ``verbose=False`` в stdout всё равно идут строки ``print`` этапов)::

        from prototiping.reporting.build import render_report

        text: str = render_report(verbose=False)
        text = render_report(verbose=True)  # Rich + этапы
    """
    from prototiping.graph.trace import run_prototype_traced
    from prototiping.reporting.diagram import build_graph_visual_markdown

    console = _get_console(verbose)
    if console:
        console.print()
        console.rule("[bold bright_cyan]Прототипирование — сборка REPORT.md[/]", style="cyan")
        console.print()

    _step(console, "[1/7] Прогон графа сценариев (LangGraph / проверки по узлам)…", style="yellow")
    trace_full = run_prototype_traced(console=verbose, write_trace_json=True)

    _step(console, "[2/7] Сопоставление с метаданными сценариев (checks/scenarios.py)…")
    rows = collect_results_from_trace(trace_full)
    ok_count = sum(1 for r in rows if r.get("is_correct"))
    fail_count = len(rows) - ok_count
    cm = compute_confusion(rows)
    legacy_count = sum(1 for r in rows if r.get("is_legacy_version"))
    if console:
        console.print(
            f"  [dim]Проверок:[/] [green]{ok_count} OK[/] / "
            f"{'[red]' if fail_count else '[dim]'}{fail_count} некорректно[/]"
        )

    _step(console, "[3/7] Раздел «Граф» (таблица, ASCII, Mermaid)…")
    graph_visual = build_graph_visual_markdown(trace_full)

    _step(console, "[4/7] Раздел «Эволюция БД»…")
    from prototiping.db.evolution import build_db_evolution_markdown

    db_evo = _safe_section(build_db_evolution_markdown, "эволюция БД", console)

    _step(console, "[5/7] Раздел «Снимок демо-БД»…")
    from prototiping.db.snapshot import build_db_snapshot_section_markdown

    db_snap = _safe_section(build_db_snapshot_section_markdown, "снимок демо-БД", console)

    _step(console, "[6/7] Раздел «OCR» (изображения, Tesseract, LLM)…")
    from prototiping.reporting.ocr import build_ocr_section_markdown

    ocr_md = _safe_section(
        lambda: build_ocr_section_markdown(console=console),
        "OCR",
        console,
    )

    _step(console, "[7/7] Подстановка в шаблон reporting/template.md…")
    template = REPORT_TEMPLATE.read_text(encoding="utf-8")
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    fail_alert = ""
    if fail_count:
        fail_alert = (
            "> ❌ **Есть некорректно обработанные сценарии:** "
            f"**{fail_count}** из {len(rows)}. "
            "Смотрите таблицу (колонка «При ошибке») и раздел 4.\n"
        )

    graph_summary_line = (
        f"*Граф:* `{trace_full.get('graph', '')}` — итог прогона: "
        f"**{'корректно' if trace_full.get('overall_ok') else 'есть некорректности'}** "
        f"({ok_count} корректно / {fail_count} некорректно по сценариям).\n"
    )

    out = template.replace("{{GENERATED_AT}}", generated)
    out = out.replace("{{FAIL_ALERT}}", fail_alert)
    out = out.replace("{{GRAPH_SUMMARY}}", graph_summary_line)
    out = out.replace("{{TOTAL}}", str(len(rows)))
    out = out.replace("{{OK_COUNT}}", str(ok_count))
    out = out.replace("{{FAIL_COUNT}}", str(fail_count))
    out = out.replace("{{TP_COUNT}}", str(cm["TP"]))
    out = out.replace("{{FN_COUNT}}", str(cm["FN"]))
    out = out.replace("{{TN_COUNT}}", str(cm["TN"]))
    out = out.replace("{{FP_COUNT}}", str(cm["FP"]))
    out = out.replace("{{CONFUSION_MATRIX}}", build_confusion_matrix_md(cm))
    out = out.replace("{{SCHEMA_VERSION}}", str(SCENARIO_SCHEMA_VERSION))
    out = out.replace("{{LEGACY_SCENARIOS_COUNT}}", str(legacy_count))
    out = out.replace("{{GRAPH_VISUAL}}", graph_visual)
    out = out.replace("{{SCENARIOS_TABLE}}", build_table(rows))
    out = out.replace("{{SCENARIOS_DETAIL}}", build_details(rows))
    out = out.replace("{{DB_EVOLUTION}}", db_evo)
    out = out.replace("{{DB_SNAPSHOT}}", db_snap)
    out = out.replace("{{OCR_SAMPLES}}", ocr_md)

    if console:
        console.print("  [green]✓[/] документ собран")
        console.rule("[bold green]Готово[/]", style="green")
        console.print()

    return out


def write_report(path: Path | None = None, *, verbose: bool = False) -> Path:
    """Собирает отчёт и записывает в файл (по умолчанию ``prototiping/REPORT.md``).

    :param path: Путь к выходному ``.md``; ``None`` → ``REPORT_MD`` из ``lib.paths``.
    :type path: pathlib.Path | None
    :param verbose: Передаётся в ``render_report`` (Rich-этапы и лог графа).
    :type verbose: bool

    :returns: Путь, по которому записан файл.
    :rtype: pathlib.Path

    Пример (без побочного вывода в консоль — удобно копировать)::

        from pathlib import Path
        from prototiping.reporting.build import write_report

        write_report(verbose=True)
        write_report(Path("out/report.md"), verbose=False)

    Сразу при вызове целевой файл перезаписывается короткой заглушкой, затем по завершении
    сборки подставляется полный отчёт (старый текст не остаётся видимым во время долгого прогона).
    """
    console = _get_console(verbose)
    target = path or REPORT_MD
    _reset_report_file(target, console)
    _reset_graph_preview_stub(console)
    body = render_report(verbose=verbose)
    if console:
        _step(console, f"Запись файла: [bold]{target}[/]", style="magenta")
    target.write_text(body, encoding="utf-8")
    _write_graph_preview_html(console)
    if console:
        console.print(f"[bold green]Сохранено:[/] {target.resolve()}\n")
    return target


if __name__ == "__main__":
    print(write_report(verbose=False))
