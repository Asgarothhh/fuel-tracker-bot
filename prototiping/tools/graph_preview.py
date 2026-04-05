"""HTML-превью графа: Mermaid + таблицы проверок (данные из трассировки)."""
from __future__ import annotations

import html
import json
from datetime import datetime, timezone

from prototiping.lib.env import load_prototype_env
from prototiping.lib.paths import GRAPH_PREVIEW_HTML, TRACE_JSON
from prototiping.reporting.diagram import build_mermaid_source_for_browser

MERMAID_ESM = "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs"
GRAPH_PREVIEW_FILENAME = "graph_preview.html"  # имя файла; путь — ``GRAPH_PREVIEW_HTML`` в ``lib.paths``

GRAPH_PREVIEW_CSS = """
:root { color-scheme: dark; }
html { scroll-behavior: smooth; }
body {
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  margin: 0;
  padding: 1.5rem;
  max-width: 1200px;
  margin-inline: auto;
  background: #0f0f0f;
  color: #e8e8e8;
  line-height: 1.5;
}
h1 { font-size: 1.35rem; font-weight: 650; margin-top: 0; }
h2 { font-size: 1.1rem; margin-top: 2rem; padding-bottom: 0.35rem; border-bottom: 1px solid #333; }
h3 { font-size: 1rem; margin: 0 0 0.5rem 0; }
.nav { margin: 1rem 0; font-size: 0.95rem; display: flex; flex-wrap: wrap; gap: 0.75rem 1.25rem; }
.nav a { color: #8ec5ff; text-decoration: none; }
.nav a:hover { text-decoration: underline; }
.nav-top { font-size: 0.9rem; margin: 0 0 1rem 0; }
.nav-top a { color: #8ec5ff; }
.status { display: inline-block; padding: 0.2rem 0.65rem; border-radius: 6px; font-weight: 600; }
.status.ok { background: #1e4d2e; color: #d4f4dc; }
.status.fail { background: #5c1f1f; color: #ffd4d4; }
.diagram-wrap {
  background: #141414;
  padding: 1rem 1.25rem;
  border-radius: 10px;
  border: 1px solid #2a2a2a;
  margin-top: 0.5rem;
  overflow-x: auto;
}
.diagram-wrap .mermaid { margin: 0; }
pre.raw {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.78rem;
  color: #9a9a9a;
  background: #141414;
  padding: 1rem;
  border-radius: 8px;
  border: 1px solid #2a2a2a;
}
.node-card {
  border: 1px solid #333;
  border-radius: 10px;
  padding: 1rem 1.1rem;
  margin-bottom: 1.5rem;
  background: #161616;
}
.node-card.ok { border-left: 4px solid #2d8a44; }
.node-card.fail { border-left: 4px solid #b33; }
.badge { font-size: 0.75rem; padding: 0.15rem 0.5rem; border-radius: 4px; margin-right: 0.5rem; }
.badge.ok { background: #1e4d2e; color: #d4f4dc; }
.badge.fail { background: #5c1f1f; color: #ffd4d4; }
.node-meta { color: #aaa; font-size: 0.9rem; margin: 0 0 1rem 0; }
.table-scroll { overflow-x: auto; -webkit-overflow-scrolling: touch; margin: 0 -0.25rem; }
table.checks { width: 100%; min-width: 720px; border-collapse: collapse; font-size: 0.82rem; }
table.checks th, table.checks td { border: 1px solid #2a2a2a; padding: 0.45rem 0.55rem; vertical-align: top; }
table.checks th { background: #222; text-align: left; font-weight: 600; }
tr.row-ok td { background: #0f1a12; }
tr.row-fail td { background: #1a0f0f; }
td.code, td.desc { max-width: 14rem; word-break: break-word; }
td.detail { max-width: 18rem; }
.pill { display: inline-block; padding: 0.1rem 0.45rem; border-radius: 4px; font-weight: 700; font-size: 0.75rem; }
.pill-ok { background: #1e4d2e; color: #d4f4dc; }
.pill-fail { background: #6b1c1c; color: #fcc; }
code { font-size: 0.85em; background: #252525; padding: 0.12rem 0.3rem; border-radius: 4px; }
footer.page-meta { margin-top: 2.5rem; padding-top: 1rem; border-top: 1px solid #333; font-size: 0.8rem; color: #888; }
"""


def _load_trace() -> dict | None:
    """Читает ``TRACE_JSON`` или выполняет короткий прогон графа."""
    if TRACE_JSON.is_file():
        try:
            return json.loads(TRACE_JSON.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    from prototiping.graph.trace import run_prototype_traced

    load_prototype_env()
    return run_prototype_traced(console=False, write_trace_json=True)


def build_scenarios_sections_html(trace: dict) -> str:
    """HTML: узлы и таблицы проверок (метаданные из ``SCENARIO_META``)."""
    from prototiping.checks.scenarios import SCENARIO_META

    parts: list[str] = [
        '<section id="scenarios-detail" class="scenarios" aria-label="Подробности по сценариям">',
        "<h2>Подробно по узлам и проверкам</h2>",
        '<p class="nav-top"><a href="#mermaid-block">↑ Диаграмма</a> · '
        '<a href="#top">↑ Наверх</a></p>',
        '<div class="nodes">',
    ]
    run_no = 0
    for idx, node in enumerate(trace.get("nodes") or [], start=1):
        nid = node["id"]
        n_ok = node.get("ok")
        title = node.get("title", "")
        ms = node.get("elapsed_ms", "")
        status_class = "ok" if n_ok else "fail"
        status_txt = "успех узла" if n_ok else "ошибка в узле"
        nid_e = html.escape(nid)
        parts.append(
            f'<article class="node-card {status_class}" id="node-{nid_e}">'
            f'<h3><span class="badge {status_class}">{html.escape(status_txt)}</span> '
            f"Узел {idx}: <code>{nid_e}</code></h3>"
            f'<p class="node-meta">{html.escape(title)} · <strong>{html.escape(str(ms))} ms</strong></p>'
            '<div class="table-scroll"><table class="checks"><thead><tr>'
            "<th scope='col'>№</th><th scope='col'>Код</th><th scope='col'>Функция</th>"
            "<th scope='col'>Сценарий</th><th scope='col'>Проверяемый код</th>"
            "<th scope='col'>Что проверяется</th><th scope='col'>Результат</th><th scope='col'>Детали</th>"
            "</tr></thead><tbody>"
        )
        for c in node.get("checks") or []:
            run_no += 1
            fn = c.get("fn", "")
            meta = SCENARIO_META.get(fn, {})
            sid = html.escape(str(meta.get("id", "—")))
            fn_e = html.escape(fn)
            stitle = html.escape(str(meta.get("title", "—")))
            code_raw = str(meta.get("code_under_test", "—"))
            desc_raw = str(meta.get("description", "—"))
            code_e = html.escape(code_raw)
            desc_e = html.escape(desc_raw)
            code_short = code_e if len(code_e) <= 140 else code_e[:137] + "…"
            desc_short = desc_e if len(desc_e) <= 220 else desc_e[:217] + "…"
            cok = c.get("ok")
            row_cls = "row-ok" if cok else "row-fail"
            res_txt = "OK" if cok else "FAIL"
            det_raw = c.get("detail") or "—"
            det_cell = html.escape(det_raw).replace("\n", "<br/>")
            parts.append(f'<tr class="{row_cls}">')
            parts.append(
                f"<td>{run_no}</td><td>{sid}</td><td><code>{fn_e}</code></td><td>{stitle}</td>"
            )
            parts.append(
                f'<td class="code" title="{code_e}">{code_short}</td>'
                f'<td class="desc" title="{desc_e}">{desc_short}</td>'
                f'<td><span class="pill {"pill-ok" if cok else "pill-fail"}">{res_txt}</span></td>'
                f'<td class="detail">{det_cell}</td>'
            )
            parts.append("</tr>")
        parts.append("</tbody></table></div></article>")
    parts.append("</div></section>")
    return "\n".join(parts)


def build_html(trace: dict) -> str:
    """Полная страница: Mermaid 11 (ESM CDN), стили, диаграмма, сценарии, сырой исходник."""
    mermaid_src = build_mermaid_source_for_browser(trace)
    graph = html.escape(trace.get("graph", ""))
    ok = trace.get("overall_ok")
    status = "успех" if ok else "есть ошибки"
    status_class = "ok" if ok else "fail"
    scenarios_html = build_scenarios_sections_html(trace)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    mermaid_js_e = html.escape(MERMAID_ESM)
    status_e = html.escape(status)
    gen_e = html.escape(generated)
    mermaid_block = html.escape(mermaid_src)
    script_block = (
        "  <script type=\"module\">\n"
        f'    import mermaid from "{MERMAID_ESM}";\n'
        "    mermaid.initialize({ startOnLoad: false, theme: 'dark', securityLevel: 'loose' });\n"
        '    await mermaid.run({ querySelector: ".mermaid-render" });\n'
        "  </script>\n"
    )

    return (
        "<!DOCTYPE html>\n"
        '<html lang="ru">\n'
        "<head>\n"
        '  <meta charset="utf-8"/>\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1"/>\n'
        '  <meta name="color-scheme" content="dark"/>\n'
        f"  <title>Граф прототипирования — {graph}</title>\n"
        "  <style>\n"
        + GRAPH_PREVIEW_CSS
        + "\n  </style>\n"
        + "</head>\n"
        + '<body id="top">\n'
        + "  <header>\n"
        + f"    <h1>Граф: {graph}</h1>\n"
        + f'    <p>Итог прогона: <span class="status {status_class}" role="status">{status_e}</span></p>\n'
        + "    <p>Источник данных: <code>prototiping/.last_prototype_trace.json</code> "
        + "(обновляется при <code>pytest prototiping</code> или <code>python -m prototiping</code>)</p>\n"
        + "  </header>\n"
        + '  <nav class="nav" aria-label="Разделы страницы">\n'
        + '    <a href="#mermaid-block">Диаграмма Mermaid</a>\n'
        + '    <a href="#scenarios-detail">Подробности по сценариям</a>\n'
        + '    <a href="#mermaid-raw">Исходник Mermaid</a>\n'
        + "  </nav>\n\n"
        + '  <h2 id="mermaid-block">Диаграмма</h2>\n'
        + '  <div class="diagram-wrap">\n'
        + f'    <div class="mermaid mermaid-render">{mermaid_src}</div>\n'
        + "  </div>\n\n"
        + scenarios_html
        + "\n\n"
        + '  <h2 id="mermaid-raw">Исходник Mermaid</h2>\n'
        + '  <p class="nav-top"><a href="#mermaid-block">↑ Диаграмма</a> · <a href="#top">↑ Наверх</a></p>\n'
        + f'  <pre class="raw" tabindex="0"><code>{mermaid_block}</code></pre>\n\n'
        + '  <footer class="page-meta">\n'
        + f"    <p>Сгенерировано prototiping: {gen_e} · Mermaid 11 ESM: <code>{mermaid_js_e}</code></p>\n"
        + "  </footer>\n"
        + script_block
        + "</body>\n"
        + "</html>\n"
    )


def main() -> None:
    """CLI: пишет ``output/graph_preview.html``, печатает абсолютный путь."""
    import os

    load_prototype_env()
    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
    os.environ.setdefault("BOT_TOKEN", "000000:prototype-dummy-token")
    os.environ.setdefault("TOKEN_SALT", "prototype-test-salt")
    os.environ.setdefault("BEL_PASSWORD", "dummy")
    os.environ.setdefault("BEL_EMITENT_ID", "1")
    os.environ.setdefault("BEL_CONTRACT_ID", "1")
    trace = _load_trace()
    if not trace:
        print("Не удалось получить трассировку графа.")
        return
    GRAPH_PREVIEW_HTML.parent.mkdir(parents=True, exist_ok=True)
    GRAPH_PREVIEW_HTML.write_text(build_html(trace), encoding="utf-8")
    print(GRAPH_PREVIEW_HTML.resolve())


if __name__ == "__main__":
    main()
