"""
Сбор REPORT.md из reporting/template.md и прогона графа.
При verbose=True — пошаговый вывод в консоль через Rich.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from prototiping.lib.env import load_prototype_env

load_prototype_env()

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("BOT_TOKEN", "000000:prototype-dummy-token")
os.environ.setdefault("TOKEN_SALT", "prototype-test-salt")
os.environ.setdefault("BEL_PASSWORD", "dummy")
os.environ.setdefault("BEL_EMITENT_ID", "1")
os.environ.setdefault("BEL_CONTRACT_ID", "1")

from prototiping.checks.scenarios import SCENARIO_META
from prototiping.lib.paths import REPORT_MD, REPORT_TEMPLATE


def _get_console(verbose: bool):
    if not verbose:
        return None
    try:
        from rich.console import Console

        return Console(stderr=False)
    except ImportError:
        return None


def _step(console, msg: str, *, style: str = "cyan") -> None:
    if console is not None:
        console.print(f"[bold {style}]▶[/] {msg}")
    else:
        print(f"▶ {msg}")


def collect_results_from_trace(trace_full: dict) -> list[dict]:
    rows: list[dict] = []
    for node in trace_full["nodes"]:
        nid = node["id"]
        for c in node["checks"]:
            fn_name = c["fn"]
            meta = SCENARIO_META.get(fn_name)
            if not meta:
                raise KeyError(f"Добавьте описание в checks/scenarios.py для {fn_name}")
            rows.append(
                {
                    **meta,
                    "graph_node": nid,
                    "check_name": fn_name,
                    "ok": c["ok"],
                    "detail": c["detail"],
                }
            )
    return rows


def _escape_md_cell(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ")


def build_table(rows: list[dict]) -> str:
    lines = [
        "| ID | Узел графа | Сценарий | Проверяемый код | Корректно | При ошибке |",
        "|----|------------|----------|-----------------|-----------|------------|",
    ]
    for row in rows:
        ok_cell = "да" if row["ok"] else "**нет**"
        err_hint = "—" if row["ok"] else _escape_md_cell((row["detail"] or "")[:120])
        code_cell = _escape_md_cell(row["code_under_test"])
        lines.append(
            "| {id} | `{node}` | {title} | {code} | {ok} | {err} |".format(
                id=row["id"],
                node=row["graph_node"],
                title=_escape_md_cell(row["title"]),
                code=code_cell,
                ok=ok_cell,
                err=err_hint,
            )
        )
    return "\n".join(lines)


def build_details(rows: list[dict]) -> str:
    parts: list[str] = []
    for row in rows:
        status = "**Корректно**" if row["ok"] else "**Ошибка**"
        detail = row["detail"] or "—"
        fail_block = ""
        if not row["ok"]:
            fail_block = (
                "\n#### ❌ Ошибка проверки\n\n"
                f"- **Текст:** `{detail}`\n"
                f"- **Функция:** `{row['check_name']}`\n\n"
            )
        parts.append(
            f"### {row['id']}. {row['title']}\n\n"
            f"- **Узел графа:** `{row['graph_node']}`\n"
            f"- **Проверяемый код:** {row['code_under_test']}\n"
            f"- **Что проверяется:** {row['description']}\n"
            f"- **Результат:** {status}\n"
            f"- **Комментарий / детали:** {detail}\n"
            f"{fail_block}"
        )
    return "\n".join(parts)


def _safe_section(builder, title: str, console) -> str:
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
    ok_count = sum(1 for r in rows if r["ok"])
    fail_count = len(rows) - ok_count
    if console:
        console.print(
            f"  [dim]Проверок:[/] [green]{ok_count} OK[/] / "
            f"{'[red]' if fail_count else '[dim]'}{fail_count} FAIL[/]"
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

    ocr_md = _safe_section(build_ocr_section_markdown, "OCR", console)

    _step(console, "[7/7] Подстановка в шаблон reporting/template.md…")
    template = REPORT_TEMPLATE.read_text(encoding="utf-8")
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    fail_alert = ""
    if fail_count:
        fail_alert = (
            "> ❌ **Есть проваленные сценарии:** "
            f"**{fail_count}** из {len(rows)}. "
            "Смотрите таблицу (колонка «При ошибке») и раздел 4 с блоками **❌ Ошибка проверки**.\n"
        )

    graph_summary_line = (
        f"*Граф:* `{trace_full.get('graph', '')}` — итог прогона: "
        f"**{'успех' if trace_full.get('overall_ok') else 'есть ошибки'}** "
        f"({ok_count} OK / {fail_count} FAIL по проверкам).\n"
    )

    out = template.replace("{{GENERATED_AT}}", generated)
    out = out.replace("{{FAIL_ALERT}}", fail_alert)
    out = out.replace("{{GRAPH_SUMMARY}}", graph_summary_line)
    out = out.replace("{{TOTAL}}", str(len(rows)))
    out = out.replace("{{OK_COUNT}}", str(ok_count))
    out = out.replace("{{FAIL_COUNT}}", str(fail_count))
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
    console = _get_console(verbose)
    body = render_report(verbose=verbose)
    target = path or REPORT_MD
    if console:
        _step(console, f"Запись файла: [bold]{target}[/]", style="magenta")
    target.write_text(body, encoding="utf-8")
    if console:
        console.print(f"[bold green]Сохранено:[/] {target.resolve()}\n")
    return target


if __name__ == "__main__":
    print(write_report(verbose=False))
