"""
Прогон графа по спецификации; Rich в консоль; JSON-трассировка для отчёта и graph_preview.
"""
from __future__ import annotations

import json
import time

from prototiping.graph.spec import GRAPH_NODES_SPEC, GRAPH_TITLE, verify_spec_matches_all_checks
from prototiping.lib.paths import TRACE_JSON


def _print_rich_console(graph_title: str, nodes_trace: list[dict], overall_ok: bool) -> None:
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich.tree import Tree
    except ImportError:
        print(f"[prototiping] граф «{graph_title}»: overall={'OK' if overall_ok else 'FAIL'}")
        for n in nodes_trace:
            st = "OK" if n["ok"] else "FAIL"
            print(f"  [{st}] {n['id']} — {n['title']} ({n['elapsed_ms']} ms)")
        return

    console = Console()
    root = Tree(f"[bold]{graph_title}[/bold] — {'[green]успех[/green]' if overall_ok else '[red]есть ошибки[/red]'}")

    for n in nodes_trace:
        style = "green" if n["ok"] else "red"
        icon = "✓" if n["ok"] else "✗"
        branch = root.add(
            f"[{style}]{icon} [bold]{n['id']}[/bold] — {n['title']} "
            f"([dim]{n['elapsed_ms']} ms[/dim])"
        )
        for c in n["checks"]:
            cstyle = "green" if c["ok"] else "red"
            cicon = "✓" if c["ok"] else "✗"
            detail = (c.get("detail") or "").replace("\n", " ")
            if len(detail) > 80:
                detail = detail[:77] + "…"
            branch.add(f"[{cstyle}]{cicon}[/] `{c['fn']}` — {c.get('name', '')} [dim]{detail}[/]")

    summary = Table(show_header=True, header_style="bold")
    summary.add_column("Узел")
    summary.add_column("Статус")
    summary.add_column("мс", justify="right")
    for n in nodes_trace:
        summary.add_row(
            n["id"],
            "[green]OK[/]" if n["ok"] else "[red]FAIL[/]",
            str(n["elapsed_ms"]),
        )

    console.print()
    console.print(Panel(root, title="[bold]Прототипирование: граф сценариев[/]", border_style="cyan"))
    console.print(Panel(summary, title="Сводка по узлам", border_style="dim"))
    console.print()


def run_prototype_traced(*, console: bool = True, write_trace_json: bool = True) -> dict:
    verify_spec_matches_all_checks()

    nodes_trace: list[dict] = []
    flat_results: list[dict] = []

    for spec in GRAPH_NODES_SPEC:
        t0 = time.perf_counter()
        check_out: list[dict] = []
        for fn in spec["checks"]:
            raw = fn()
            entry = {
                "fn": fn.__name__,
                "name": raw.get("name", fn.__name__),
                "ok": bool(raw.get("ok")),
                "detail": (raw.get("detail") or "").strip(),
            }
            check_out.append(entry)
            flat_results.append(raw)

        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        node_ok = all(c["ok"] for c in check_out)
        nodes_trace.append(
            {
                "id": spec["id"],
                "title": spec["title"],
                "ok": node_ok,
                "elapsed_ms": elapsed_ms,
                "checks": check_out,
            }
        )

    overall_ok = all(n["ok"] for n in nodes_trace)
    payload = {
        "graph": GRAPH_TITLE,
        "overall_ok": overall_ok,
        "nodes": nodes_trace,
    }

    if console:
        _print_rich_console(GRAPH_TITLE, nodes_trace, overall_ok)

    if write_trace_json:
        try:
            TRACE_JSON.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass

    return {**payload, "flat_results": flat_results}


def load_last_trace() -> dict | None:
    if not TRACE_JSON.is_file():
        return None
    try:
        return json.loads(TRACE_JSON.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
