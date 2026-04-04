"""
Человекочитаемое представление графа сценариев для REPORT.md и HTML-preview.
"""
from __future__ import annotations


def _ascii_pipeline(nodes: list[dict]) -> str:
    lines: list[str] = ["```text", "  [старт]"]
    for n in nodes:
        st = "OK" if n["ok"] else "FAIL"
        lines.append("      |")
        lines.append("      v")
        lines.append(f"  +-- {n['id']}  [{st}]  {n['elapsed_ms']} ms")
    lines.append("      |")
    lines.append("      v")
    lines.append("  [конец]")
    lines.append("```")
    return "\n".join(lines)


def build_mermaid_source_for_browser(trace: dict | None) -> str:
    """Компактный Mermaid без HTML-тегов (для рендера в браузере)."""
    if not trace or not trace.get("nodes"):
        return "flowchart LR\n  empty[Нет данных трассировки]\n"

    lines = [
        "%% Автогенерация prototiping.tools.graph_preview",
        "flowchart LR",
    ]
    ids: list[str] = []
    for i, n in enumerate(trace["nodes"]):
        nid = f"N{i}"
        ids.append(nid)
        mark = "OK" if n["ok"] else "FAIL"
        label = f"{n['id']} / {mark} / {n['elapsed_ms']}ms"
        label = label.replace('"', "'")
        cls = "okNode" if n["ok"] else "failNode"
        lines.append(f'  {nid}["{label}"]:::{cls}')
    lines.append("  classDef okNode fill:#1a472a,stroke:#234,color:#e8ffe8")
    lines.append("  classDef failNode fill:#6b1c1c,stroke:#422,color:#ffe8e8")
    for a, b in zip(ids, ids[1:]):
        lines.append(f"  {a} --> {b}")
    return "\n".join(lines) + "\n"


def build_graph_visual_markdown(trace: dict | None) -> str:
    """Таблица + цепочка + ASCII; Mermaid только как опция для просмотрщиков с поддержкой."""
    if not trace or not trace.get("nodes"):
        return (
            "_Нет данных трассировки. Запустите `pytest prototiping` или "
            "`python -m prototiping` для сборки отчёта._\n"
        )

    nodes: list[dict] = trace["nodes"]
    graph_name = trace.get("graph", "prototype")

    # Таблица
    rows = [
        "| № | ID узла | Описание | Проверок OK | Всего проверок | мс | Узел |",
        "|---|---------|----------|-------------|----------------|-----|------|",
    ]
    for i, n in enumerate(nodes, start=1):
        checks = n.get("checks") or []
        ok_c = sum(1 for c in checks if c.get("ok"))
        tot = len(checks)
        node_ok = "**да**" if n["ok"] else "**нет**"
        desc = (n.get("title") or "").replace("|", "\\|")
        rows.append(
            f"| {i} | `{n['id']}` | {desc} | {ok_c} | {tot} | {n['elapsed_ms']} | {node_ok} |"
        )
    table = "\n".join(rows)

    # Маркированная цепочка
    chain_parts = []
    for n in nodes:
        mark = "✓" if n["ok"] else "✗"
        chain_parts.append(f"`{n['id']}` {mark} ({n['elapsed_ms']} ms)")
    chain_line = " → ".join(chain_parts)
    bullet_chain = "\n".join(
        f"{i}. **{n['id']}** — {'успех' if n['ok'] else 'ошибка'} ({n['elapsed_ms']} ms): _{n.get('title', '')}_"
        for i, n in enumerate(nodes, start=1)
    )

    mermaid = "```mermaid\n" + build_mermaid_source_for_browser(trace).rstrip() + "\n```\n"

    return (
        f"Граф **`{graph_name}`**: узлы выполняются **сверху вниз** (как в LangGraph). "
        "Сырая диаграмма Mermaid ниже в части просмотрщиков показывается как текст — "
        "тогда откройте сгенерированный **HTML** (команда в конце раздела) или IDE с Mermaid.\n\n"
        "### Таблица узлов\n\n"
        + table
        + "\n\n### Цепочка (одна строка)\n\n"
        + chain_line
        + "\n\n### Порядок выполнения\n\n"
        + bullet_chain
        + "\n\n### Схема (ASCII)\n\n"
        + _ascii_pipeline(nodes)
        + "\n\n### Диаграмма Mermaid (компактная)\n\n"
        + mermaid
        + "\n### Интерактивная диаграмма\n\n"
        "Сгенерируйте HTML с корректным рендером:\n\n"
        "```bash\nPYTHONPATH=. python -m prototiping.tools.graph_preview\n```\n\n"
        f"Файл: `prototiping/output/graph_preview.html` (откройте в браузере).\n"
    )
